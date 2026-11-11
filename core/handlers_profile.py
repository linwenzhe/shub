# 文件名: core/handlers_profile.py
"""save / load / profiles / forget commands.

- save: primary copy always written to profiles/; if input has a path, also copy there.
- load: with path -> load from that path only (no fallback);
        without path -> load primary copy from profiles/.
- forget / profiles: only operate on profiles/.
"""

import profiles as profile_store
from logger import log
from core.serial_session import (
    SerialSession, list_available_ports, port_exists,
)
from core.telnet_session import TelnetSession


def _session_to_profile(sess):
    if isinstance(sess, SerialSession):
        return {
            "type": "serial",
            "port": sess.port,
            "baudrate": sess.cfg.get("baudrate", 115200),
            "bytesize": sess.cfg.get("bytesize", 8),
            "parity": sess.cfg.get("parity", "N"),
            "stopbits": sess.cfg.get("stopbits", 1),
            "flow": sess.cfg.get("flow", "none"),
            "newline": sess.cfg.get("newline", "crlf"),
        }
    if isinstance(sess, TelnetSession):
        return {
            "type": "remote",
            "host": sess.host,
            "port": sess.port,
            "password": sess.password,
        }
    return None


def _format_profile_summary(info):
    typ = info.get("type", "?")
    if typ == "serial":
        return (f"serial {info.get('port','?')} "
                f"{info.get('baudrate','?')} "
                f"{info.get('newline','?')}")
    if typ == "remote":
        return f"remote {info.get('host','?')}:{info.get('port','?')}"
    return str(typ)


def cmd_save(args, mgr, _cfg, _hist):
    if not args:
        print("[shub] Usage: shub:save <name|path>")
        print("[shub] e.g. shub:save gd32  ->  profiles/gd32.json")
        print("[shub] e.g. shub:save D:\\cfg\\gd32  ->  profiles/gd32.json plus "
              "D:\\cfg\\gd32.json")
        return
    name = args[0]
    s = mgr.get_current()
    if not s:
        print("[shub] No current session")
        return
    data = _session_to_profile(s)
    if not data:
        print("[shub] Session type cannot be saved")
        return
    try:
        main_full, extra_full = profile_store.save_profile(name, data)
    except ValueError as e:
        print(f"[shub] {e}")
        return
    except Exception as e:
        print(f"[shub] Save failed: {e}")
        log.error("保存档案失败: %s", e, exc_info=True)
        return

    print(f"[shub] Primary copy saved to {main_full}")
    if extra_full:
        print(f"[shub] Extra copy saved to {extra_full}")
    log.info("保存档案: 主=%s, 额外=%s", main_full, extra_full)


def cmd_load(args, mgr, cfg, _hist):
    if not args:
        print("[shub] Usage: shub:load <name|path>")
        print(f"[shub] Name only -> load from {profile_store.profiles_dir()}")
        print("[shub] Path -> load from that path only; missing = error")
        return
    name = args[0]
    try:
        data = profile_store.load_profile(name)
    except ValueError as e:
        print(f"[shub] {e}")
        return
    except FileNotFoundError as e:
        print(f"[shub] {e}")
        return
    except Exception as e:
        print(f"[shub] Failed to read profile: {e}")
        log.error("读取档案失败: %s", e, exc_info=True)
        return

    typ = data.get("type")
    if typ == "serial":
        port = str(data.get("port", "")).strip().upper()
        if not port:
            print(f"[shub] Profile {name} missing 'port' field")
            return
        if not port_exists(port):
            avail = ", ".join(d for d, _ in list_available_ports()) or "none"
            print(f"[shub] Profile {name}: {port} not available. Available: {avail}")
            return
        if mgr.get(port):
            print(f"[shub] Session {port} already exists, switched to it")
            mgr.switch(port)
            return
        override = dict(cfg)
        for k in ("baudrate", "bytesize", "parity", "stopbits", "flow", "newline"):
            if k in data:
                override[k] = data[k]
        s = SerialSession(port, port, override)
        try:
            s.open()
        except Exception as e:
            print(f"[shub] Failed to open {port}: {e}")
            log.error("档案 %s 打开失败: %s", name, e, exc_info=True)
            return
        mgr.add(s)
        print(f"[shub] Opened {port} from profile {name}")

    elif typ == "remote":
        host = str(data.get("host", "")).strip()
        try:
            port = int(data.get("port", 0))
        except (TypeError, ValueError):
            print(f"[shub] Profile {name}: 'port' is not a valid number")
            return
        pwd = str(data.get("password", cfg.get("default_password", "123456")))
        if not host or port <= 0:
            print(f"[shub] Profile {name}: missing valid host/port")
            return
        sess_name = f"{host}:{port}"
        if mgr.get(sess_name):
            print(f"[shub] Session {sess_name} already exists, switched to it")
            mgr.switch(sess_name)
            return
        s = TelnetSession(sess_name, host, port, pwd, cfg)
        try:
            s.open()
        except Exception as e:
            print(f"[shub] Failed to connect {sess_name}: {e}")
            log.error("档案 %s 连接失败: %s", name, e, exc_info=True)
            return
        mgr.add(s)
        print(f"[shub] Connected {sess_name} from profile {name}")

    else:
        print(f"[shub] Profile {name} has unknown type: {typ}")


def cmd_profiles(_args, _mgr, _cfg, _hist):
    d = profile_store.profiles_dir()
    items = profile_store.list_profiles()
    if not items:
        print(f"[shub] No valid profiles under {d}")
        return
    print(f"[shub] {d}")
    for name, info in items:
        detail = _format_profile_summary(info)
        print(f"  {name:<28} {detail}")


def cmd_forget(args, _mgr, _cfg, _hist):
    if not args:
        print("[shub] Usage: shub:forget <name>")
        return
    name = args[0]
    try:
        ok = profile_store.delete_profile(name)
    except ValueError as e:
        print(f"[shub] {e}")
        return
    except Exception as e:
        print(f"[shub] Delete failed: {e}")
        log.error("删除档案失败: %s", e, exc_info=True)
        return
    if ok:
        print(f"[shub] Deleted primary copy {name}")
        print("[shub] Note: external extra copies are NOT deleted; remove manually")
        log.info("删除档案主副本 %s", name)
    else:
        print(f"[shub] No profile {name}")