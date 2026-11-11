# 文件名: core/handlers.py
"""Dispatch table + simple commands."""

from commands import COMMANDS
from core.serial_session import SerialSession, list_available_ports
from core.handlers_io import cmd_open, cmd_open_new, cmd_connect, cmd_connect_new
from core.handlers_share import (
    cmd_share, cmd_unshare, cmd_shared, cmd_script, cmd_export,
)
from core.handlers_profile import (
    cmd_save, cmd_load, cmd_profiles, cmd_forget,
)


def cmd_ports(_args, _mgr, _cfg, _hist):
    ports = list_available_ports()
    if not ports:
        print("[shub] No COM ports detected")
        return
    for dev, desc in ports:
        print(f"  {dev}  {desc}")


def cmd_switch(args, mgr, _cfg, _hist):
    if not args:
        print("[shub] Usage: shub:switch <name>")
        return
    if mgr.switch(args[0]):
        print(f"[shub] Current session: {args[0]}")
    else:
        print(f"[shub] No session {args[0]}")


def cmd_close(args, mgr, _cfg, _hist):
    name = args[0] if args else mgr.current
    if not name:
        print("[shub] No current session")
        return
    if not mgr.get(name):
        print(f"[shub] No session {name}")
        return
    mgr.remove(name)
    print(f"[shub] Closed {name}")


def cmd_list(_args, mgr, _cfg, _hist):
    if not mgr.sessions:
        print("[shub] No sessions")
        return
    for name, s in mgr.sessions.items():
        mark = "*" if name == mgr.current else " "
        typ = "local" if isinstance(s, SerialSession) else "remote"
        baud = getattr(s, "cfg", {}).get("baudrate", "-")
        b = getattr(s, "broadcast", None)
        if b:
            pwd = "no" if b.password is None else "yes"
            share = f"shared:{b.port} pwd:{pwd}"
        else:
            share = "not shared"
        print(f"{mark} {name:<18} {typ:<7} {str(baud):<7} {share}")


def cmd_help(args, _mgr, _cfg, _hist):
    if not args:
        for name, meta in COMMANDS.items():
            print(f"  shub:{name:<12} {meta['desc']}")
        return
    name = args[0]
    meta = COMMANDS.get(name)
    if not meta:
        print(f"[shub] No command '{name}'. Try shub:help")
        return
    print(f"shub:{meta['usage']}")
    print(f"  {meta['desc']}")
    print(f"  {meta['detail']}")


def cmd_send(args, mgr, _cfg, _hist):
    s = mgr.get_current()
    if not s:
        print("[shub] No current session")
        return
    if not args:
        print("[shub] Usage: shub:send <text>")
        return
    text = " ".join(args)
    if not s.send(text):
        print(f"[shub] Send failed, session {s.name} may be disconnected")
        return
    if getattr(s, "broadcast", None):
        s.broadcast.broadcast_command(s.name, text)


def cmd_exit(_args, _mgr, _cfg, _hist):
    raise SystemExit(0)


HANDLERS = {
    "ports": cmd_ports,
    "open": cmd_open,
    "open-new": cmd_open_new,
    "connect": cmd_connect,
    "connect-new": cmd_connect_new,
    "switch": cmd_switch,
    "close": cmd_close,
    "list": cmd_list,
    "save": cmd_save,
    "load": cmd_load,
    "profiles": cmd_profiles,
    "forget": cmd_forget,
    "share": cmd_share,
    "unshare": cmd_unshare,
    "shared": cmd_shared,
    "script": cmd_script,
    "export": cmd_export,
    "help": cmd_help,
    "send": cmd_send,
    "exit": cmd_exit,
}