# 文件名: main.py
"""shub entry: main loop, startup args, top-level error handling."""

import sys
import threading
import time

from config import load_config
from logger import log
from input_helper import read_line
from core.session_manager import SessionManager
from core.handlers import HANDLERS

_stdout_lock = threading.Lock()


def _print_line(prefix, text):
    if not text.endswith("\n"):
        text += "\n"
    with _stdout_lock:
        sys.stdout.write(f"{prefix} {text}")
        sys.stdout.flush()


def _printer_loop(mgr):
    def _worker(name, sess):
        iq = getattr(sess, "input_queue", None)
        while True:
            if mgr.sessions.get(name) is not sess:
                return
            try:
                data = sess.rx_queue.get(timeout=0.1)
            except Exception:
                data = None
            if data:
                try:
                    text = data.decode("utf-8", errors="replace")
                except Exception:
                    text = str(data)
                _print_line(f"[{name}]", text)
            if iq is not None:
                while True:
                    try:
                        item = iq.get_nowait()
                    except Exception:
                        break
                    _print_line(f"[{name}]", item)

    while True:
        for name, sess in list(mgr.sessions.items()):
            if not getattr(sess, "_printer_started", False):
                sess._printer_started = True
                threading.Thread(target=_worker, args=(name, sess), daemon=True).start()
        time.sleep(0.3)


def _apply_startup_args(argv, mgr, cfg):
    if not argv:
        return
    if argv[0] == "--open" and len(argv) >= 2:
        from core.handlers_io import cmd_open
        cmd_open(argv[1:], mgr, cfg, [])
    elif argv[0] == "--connect" and len(argv) >= 2:
        from core.handlers_io import cmd_connect
        cmd_connect(argv[1:], mgr, cfg, [])
    elif argv[0] == "--load" and len(argv) >= 2:
        from core.handlers_profile import cmd_load
        cmd_load(argv[1:], mgr, cfg, [])


def _dispatch(line, mgr, cfg, history):
    prefix = cfg.get("command_prefix", "shub:")
    if line.startswith(prefix):
        cmd_line = line[len(prefix):].strip()
        if not cmd_line:
            print("[shub] Empty command")
            return
        parts = cmd_line.split()
        name = parts[0]
        args = parts[1:]
        handler = HANDLERS.get(name)
        if not handler:
            print(f"[shub] Unknown command '{name}'. Try shub:help")
            return
        try:
            handler(args, mgr, cfg, history)
        except SystemExit:
            raise
        except Exception as e:
            print(f"[shub] Command error: {e}")
            log.error("命令 %s 执行出错: %s", name, e, exc_info=True)
    else:
        s = mgr.get_current()
        if s:
            if line.strip():
                _print_line(f"[{s.name}]", f"> {line}")
            if not s.send(line):
                print(f"[shub] Send failed, session {s.name} may be disconnected")
                return
            if getattr(s, "broadcast", None):
                s.broadcast.broadcast_command(s.name, line)
        else:
            print("[shub] No active session. Use shub:open or shub:connect first")


def _run():
    cfg = load_config()
    history = []
    hist_max = cfg.get("history_max", 100)
    mgr = SessionManager(cfg)

    log.info("shub 启动")
    print("shub v0.1  --  type shub:help for commands")
    threading.Thread(target=_printer_loop, args=(mgr,), daemon=True).start()

    _apply_startup_args(sys.argv[1:], mgr, cfg)

    while True:
        try:
            line = read_line(mgr.prompt(), history, hist_max)
        except (EOFError, KeyboardInterrupt):
            break
        try:
            _dispatch(line, mgr, cfg, history)
        except SystemExit:
            break

    for name in list(mgr.sessions.keys()):
        mgr.remove(name)
    log.info("shub 退出")
    print("\n[shub] Bye")


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        _run()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n[shub] Startup failed: {e}")
        log.error("启动失败: %s", e, exc_info=True)
        try:
            input("Press Enter to exit...")
        except Exception:
            pass


if __name__ == "__main__":
    main()