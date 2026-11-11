# 文件名: core/handlers_share.py
"""share / unshare / shared / script / export commands."""

from logger import log
from core.tcp_broadcast import TcpBroadcastServer
from script_sender import ScriptSender


def _make_remote_input_handler(session):
    def _handler(label, data):
        try:
            text = data.decode("utf-8", errors="replace").rstrip("\r\n")
        except Exception:
            text = str(data)
        if not text:
            return
        session.input_queue.put(f"<remote {label}> {text}\n")
    return _handler


def cmd_share(args, mgr, cfg, _hist):
    s = mgr.get_current()
    if not s:
        print("[shub] No current session")
        return
    if not hasattr(s, "subscribe"):
        print("[shub] Remote sessions cannot be re-shared; only local serial can")
        return

    port = None
    password = cfg.get("default_password", "123456")
    no_password = False
    rest = list(args)
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.isdigit() and port is None:
            port = int(a)
        elif a == "--password" and i + 1 < len(rest):
            password = rest[i + 1]
            i += 1
        elif a == "--no-password":
            no_password = True
        i += 1

    if port is None:
        port = mgr.next_share_port()
    if port in mgr.used_ports:
        print(f"[shub] Port {port} already in use by this program")
        return

    if getattr(s, "broadcast", None):
        try:
            s.broadcast.stop()
            mgr.used_ports.discard(s.broadcast.port)
        except Exception as e:
            log.warning("停止旧共享失败: %s", e)
        s.broadcast = None

    pwd = None if no_password else password
    echo = cfg.get("echo_remote_input", True)
    callback = _make_remote_input_handler(s) if echo else None

    b = TcpBroadcastServer(s, port, pwd, on_remote_input=callback)
    b.cmd_prefix = cfg.get("cmd_record_prefix", "[shub@")
    try:
        b.start()
    except Exception as e:
        print(f"[shub] Failed to start sharing: {e}")
        log.error("开启共享失败: %s", e, exc_info=True)
        return
    s.broadcast = b
    mgr.used_ports.add(port)

    pwd_note = "  (no password)" if pwd is None else ""
    print(f"[shub] Shared {s.name} on port {port}{pwd_note}")
    print(f"[shub] Remote side connects with: shub:connect <this-machine-ip>:{port}")
    log.info("会话 %s 共享到端口 %d", s.name, port)


def cmd_unshare(_args, mgr, _cfg, _hist):
    s = mgr.get_current()
    if not s or not getattr(s, "broadcast", None):
        print("[shub] Current session is not shared")
        return
    port = s.broadcast.port
    s.broadcast.stop()
    mgr.used_ports.discard(port)
    s.broadcast = None
    print(f"[shub] Stopped sharing, released port {port}")
    log.info("会话 %s 停止共享，释放端口 %d", s.name, port)


def cmd_shared(args, mgr, _cfg, _hist):
    """Query shared state:
    - No arg: list all shared sessions.
    - Pure number: check that share port.
    - Otherwise: check that session by name.
    """
    if not args:
        shared = [
            (name, s) for name, s in mgr.sessions.items()
            if getattr(s, "broadcast", None)
        ]
        if not shared:
            print("[shub] No session is currently shared")
            return
        print("[shub] Currently shared:")
        for name, s in shared:
            b = s.broadcast
            pwd = "no" if b.password is None else "yes"
            print(f"  [{name}] port:{b.port}  password:{pwd}")
        return

    target = args[0].strip()

    if target.isdigit():
        port = int(target)
        for name, s in mgr.sessions.items():
            b = getattr(s, "broadcast", None)
            if b and b.port == port:
                pwd = "no" if b.password is None else "yes"
                print(f"[shub] Port {port} is used by [{name}], password:{pwd}")
                return
        print(f"[shub] Port {port} is not used by this program")
        return

    name = target.upper() if target.lower().startswith("com") else target
    s = mgr.get(name)
    if not s:
        print(f"[shub] No session {name}. Use shub:list to see all sessions")
        return
    b = getattr(s, "broadcast", None)
    if not b:
        print(f"[shub] [{name}] is not shared")
        return
    pwd = "no" if b.password is None else "yes"
    print(f"[shub] [{name}] shared on port {b.port}, password:{pwd}")


def cmd_script(args, mgr, cfg, _hist):
    s = mgr.get_current()
    if not s:
        print("[shub] No current session")
        return
    if "--stop" in args:
        if getattr(s, "script_sender", None):
            s.script_sender.stop()
            s.script_sender = None
            print("[shub] Script stopped")
        return
    if not args:
        print("[shub] Usage: shub:script <file> [interval_ms] [--loop] [--stop]")
        return
    filepath = args[0]
    interval = cfg.get("script_default_interval_ms", 100)
    loop = "--loop" in args
    for a in args[1:]:
        if a.isdigit():
            interval = int(a)
    s.script_sender = ScriptSender(s, filepath, interval, loop)
    s.script_sender.start()
    print(f"[shub] Sending script {filepath}, interval {interval}ms"
          + (", loop" if loop else ""))


def cmd_export(args, _mgr, _cfg, history):
    if not args:
        print("[shub] Usage: shub:export <file>")
        return
    if not history:
        print("[shub] No history to export")
        return
    path = args[0]
    try:
        with open(path, "w", encoding="utf-8") as f:
            for line in history:
                f.write(line + "\n")
        print(f"[shub] Exported {len(history)} history lines to {path}")
        log.info("历史导出到 %s（%d 条）", path, len(history))
    except OSError as e:
        print(f"[shub] Export failed: {e}")
        log.error("导出失败: %s", e, exc_info=True)