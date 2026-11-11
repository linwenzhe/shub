# 文件名: core/session_manager.py
"""SessionManager: session table, current session pointer, share port allocation."""

from logger import log


class SessionManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.sessions = {}
        self.current = None
        self.used_ports = set()

    def add(self, session):
        self.sessions[session.name] = session
        self.current = session.name
        log.info("新建会话 %s", session.name)

    def get(self, name):
        return self.sessions.get(name)

    def get_current(self):
        if self.current is None:
            return None
        return self.sessions.get(self.current)

    def switch(self, name):
        if name in self.sessions:
            self.current = name
            return True
        return False

    def remove(self, name):
        s = self.sessions.pop(name, None)
        if not s:
            return
        if getattr(s, "broadcast", None):
            try:
                s.broadcast.stop()
                self.used_ports.discard(s.broadcast.port)
            except Exception as e:
                log.warning("停止 %s 共享失败: %s", name, e)
            s.broadcast = None
        if getattr(s, "script_sender", None):
            try:
                s.script_sender.stop()
            except Exception as e:
                log.warning("停止 %s 脚本发送失败: %s", name, e)
            s.script_sender = None
        try:
            s.close()
        except Exception as e:
            log.warning("关闭会话 %s 失败: %s", name, e)
        if self.current == name:
            self.current = next(iter(self.sessions), None)
        log.info("会话 %s 已关闭", name)

    def next_share_port(self):
        base = self.cfg.get("share_port_start", 1000)
        if not self.used_ports:
            return base
        return max(self.used_ports) + 1

    def prompt(self):
        if self.current:
            return f"shub [{self.current}]> "
        return "shub> "