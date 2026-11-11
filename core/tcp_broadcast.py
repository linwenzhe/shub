# 文件名: core/tcp_broadcast.py
"""TCP broadcast server:
- Subscribes to a dedicated queue so terminal display and broadcast do not compete.
- Password check on connect.
- Remote-input callback (for local display).
- Command-record broadcast (excluding the originator).
"""

import socket
import threading

from logger import log


class TcpBroadcastServer:
    def __init__(self, session, port, password=None, on_remote_input=None):
        self.session = session
        self.port = int(port)
        self.password = password
        self.on_remote_input = on_remote_input
        self.cmd_prefix = "[shub@"
        self.clients = []
        self._lock = threading.Lock()
        self._server = None
        self._running = False

    def start(self):
        if not hasattr(self.session, "subscribe"):
            raise TypeError("Session type does not support sharing")
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("0.0.0.0", self.port))
        self._server.listen(5)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        log.info("广播服务启动: 端口 %d", self.port)

    def broadcast_command(self, source_label, text, exclude_conn=None):
        line = f"{self.cmd_prefix}{source_label}] {text}\n".encode("utf-8", "replace")
        with self._lock:
            for c in self.clients:
                if c is exclude_conn:
                    continue
                try:
                    c.sendall(line)
                except OSError:
                    pass

    def _accept_loop(self):
        while self._running:
            try:
                conn, _ = self._server.accept()
            except OSError:
                break
            threading.Thread(target=self._handshake, args=(conn,), daemon=True).start()

    def _handshake(self, conn):
        if self.password is not None:
            try:
                conn.settimeout(5)
                buf = bytearray()
                while b"\n" not in buf:
                    ch = conn.recv(1)
                    if not ch:
                        conn.close()
                        return
                    buf.extend(ch)
                pwd = buf.decode("utf-8", errors="replace").strip()
                if pwd != self.password:
                    conn.sendall(b"ERR\n")
                    conn.close()
                    log.warning("客户端密码错误，已断开")
                    return
                conn.sendall(b"OK\n")
                conn.settimeout(None)
            except OSError:
                conn.close()
                return
        else:
            try:
                conn.sendall(b"OK\n")
            except OSError:
                conn.close()
                return

        with self._lock:
            self.clients.append(conn)
        log.info("新客户端接入，当前 %d 个", len(self.clients))
        threading.Thread(target=self._client_loop, args=(conn,), daemon=True).start()

    def _client_loop(self, conn):
        try:
            addr = conn.getpeername()
            label = f"{addr[0]}:{addr[1]}"
        except Exception:
            label = "unknown"

        try:
            while self._running:
                data = conn.recv(1024)
                if not data:
                    break
                if self.on_remote_input:
                    try:
                        self.on_remote_input(label, data)
                    except Exception:
                        pass
                text = data.decode("utf-8", errors="replace").rstrip("\r\n")
                if text:
                    self.broadcast_command(label, text, exclude_conn=conn)
                self.session.send_raw(data)
        except OSError:
            pass
        finally:
            with self._lock:
                if conn in self.clients:
                    self.clients.remove(conn)
            try:
                conn.close()
            except Exception:
                pass
            log.info("客户端断开，剩余 %d 个", len(self.clients))

    def _broadcast_loop(self):
        q = self.session.subscribe()
        try:
            while self._running:
                try:
                    data = q.get(timeout=0.1)
                except Exception:
                    continue
                with self._lock:
                    dead = []
                    for c in self.clients:
                        try:
                            c.sendall(data)
                        except OSError:
                            dead.append(c)
                    for c in dead:
                        self.clients.remove(c)
                        try:
                            c.close()
                        except Exception:
                            pass
        finally:
            self.session.unsubscribe(q)

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        with self._lock:
            for c in self.clients:
                try:
                    c.close()
                except Exception:
                    pass
            self.clients.clear()
        log.info("广播服务停止: 端口 %d", self.port)