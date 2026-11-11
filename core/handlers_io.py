# 文件名: core/handlers_io.py
"""open / open-new / connect / connect-new commands."""

import os
import subprocess
import sys

from logger import log
from core.serial_session import (
    SerialSession, list_available_ports, port_exists,
)
from core.telnet_session import TelnetSession


def _parse_open_args(args, cfg):
    if not args:
        raise ValueError("Missing port")
    port = args[0].upper()
    override = dict(cfg)
    rest = args[1:]
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.isdigit():
            override["baudrate"] = int(a)
        elif a == "--flow":
            i += 1
            if i < len(rest) and rest[i] in ("none", "rts", "xon"):
                override["flow"] = rest[i]
        elif a == "--newline":
            i += 1
            if i < len(rest) and rest[i] in ("crlf", "lf", "cr", "none"):
                override["newline"] = rest[i]
        elif len(a) == 3 and a[0] in "5678" and a[1] in "NEO" and a[2] in "12":
            override["bytesize"] = int(a[0])
            override["parity"] = a[1]
            override["stopbits"] = int(a[2])
        i += 1
    return port, override


def _parse_connect_args(args, cfg):
    if not args:
        raise ValueError("Missing ip:port")
    hp = args[0]
    if ":" not in hp:
        raise ValueError("Address format must be ip:port")
    host, port_str = hp.rsplit(":", 1)
    try:
        port = int(port_str)
    except ValueError:
        raise ValueError("Port must be a number")
    pwd = cfg.get("default_password", "123456")
    rest = args[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--password" and i + 1 < len(rest):
            pwd = rest[i + 1]
            i += 1
        i += 1
    return host, port, pwd


def _spawn_new_window(extra_args):
    if getattr(sys, "frozen", False):
        cmd = [sys.executable] + extra_args
    else:
        main_path = os.path.abspath(sys.argv[0])
        cmd = [sys.executable, main_path] + extra_args
    try:
        if os.name == "nt":
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(cmd)
        print("[shub] New window started")
        log.info("启动新窗口: %s", " ".join(cmd))
    except Exception as e:
        print(f"[shub] Failed to start new window: {e}")
        log.error("启动新窗口失败: %s", e, exc_info=True)


def cmd_open(args, mgr, cfg, _hist):
    try:
        port, override = _parse_open_args(args, cfg)
    except ValueError as e:
        print(f"[shub] {e}")
        return
    if not port_exists(port):
        avail = ", ".join(d for d, _ in list_available_ports()) or "none"
        print(f"[shub] Port {port} not found. Available: {avail}")
        return
    if mgr.get(port):
        print(f"[shub] Session {port} already exists, switched to it")
        mgr.switch(port)
        return
    s = SerialSession(port, port, override)
    try:
        s.open()
    except Exception as e:
        print(f"[shub] Failed to open {port}: {e}")
        log.error("打开 %s 失败: %s", port, e, exc_info=True)
        return
    mgr.add(s)
    print(f"[shub] Opened {port} @ {override['baudrate']}, newline={override['newline']}")


def cmd_open_new(args, mgr, cfg, _hist):
    try:
        _parse_open_args(args, cfg)
    except ValueError as e:
        print(f"[shub] {e}")
        return
    _spawn_new_window(["--open"] + list(args))


def cmd_connect(args, mgr, cfg, _hist):
    try:
        host, port, pwd = _parse_connect_args(args, cfg)
    except ValueError as e:
        print(f"[shub] {e}")
        return
    name = f"{host}:{port}"
    if mgr.get(name):
        print(f"[shub] Session {name} already exists, switched to it")
        mgr.switch(name)
        return
    s = TelnetSession(name, host, port, pwd, cfg)
    try:
        s.open()
    except Exception as e:
        print(f"[shub] Failed to connect {name}: {e}")
        log.error("连接 %s 失败: %s", name, e, exc_info=True)
        return
    mgr.add(s)
    print(f"[shub] Connected {name}")


def cmd_connect_new(args, mgr, cfg, _hist):
    try:
        _parse_connect_args(args, cfg)
    except ValueError as e:
        print(f"[shub] {e}")
        return
    _spawn_new_window(["--connect"] + list(args))