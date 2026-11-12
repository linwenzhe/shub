# 文件名: core/tcp_client.py
"""TCP forwarder: expose a remote serial on a local loopback port.

Each accepted local connection is bridged to a fresh remote connection
with the password handshake performed transparently.
"""

import os
import socket
import threading

from core.errors import TcpError
from core.handshake import client_handshake
from logger import log


class TcpSerialClient:
    def __init__(self, host, port, local_port, password=None):
        self.host = host
        self.port = int(port)
        self.local_port = int(local_port)
        self.password = password
        self._server = None
        self._running = False
        self._active = []  # list of (local_conn, remote_conn)
        self._active_lock = threading.Lock()

    def start(self):
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name == "nt":
                self._server.setsockopt(
                    socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                self._server.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind(("127.0.0.1", self.local_port))
            self._server.listen(5)
        except OSError as e:
            if self._server:
                try:
                    self._server.close()
                except Exception:
                    pass
            raise TcpError(
                f"Cannot listen on 127.0.0.1:{self.local_port}: {e}. "
                "If a previous connect was just stopped, the port may still "
                "be in TIME_WAIT (a minute or two on Windows); "
                "wait or use a different local port."
            )

        self._server.settimeout(0.5)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        log.info("TCP forwarder listening on 127.0.0.1:%d -> %s:%d",
                 self.local_port, self.host, self.port)

    def _accept_loop(self):
        while self._running:
            try:
                local_conn, addr = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_local, args=(local_conn, addr),
                             daemon=True).start()

    def _connect_remote(self):
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
        except OSError as e:
            log.error("Remote connect failed: %s", e)
            return None

        if not client_handshake(sock, self.password):
            try:
                sock.close()
            except Exception:
                pass
            log.warning("Remote rejected handshake")
            return None

        return sock

    def _handle_local(self, local_conn, addr):
        label = f"{addr[0]}:{addr[1]}"
        remote_conn = self._connect_remote()
        if not remote_conn:
            try:
                local_conn.close()
            except Exception:
                pass
            return

        entry = (local_conn, remote_conn)
        with self._active_lock:
            self._active.append(entry)
        log.info("Local client %s bridged", label)

        def pipe(src, dst):
            try:
                while self._running:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass

        t1 = threading.Thread(target=pipe, args=(local_conn, remote_conn),
                              daemon=True)
        t2 = threading.Thread(target=pipe, args=(remote_conn, local_conn),
                              daemon=True)
        t1.start()
        t2.start()

        try:
            t1.join()
        except Exception:
            pass

        for s in (local_conn, remote_conn):
            try:
                s.close()
            except Exception:
                pass

        try:
            t2.join(timeout=1)
        except Exception:
            pass

        with self._active_lock:
            if entry in self._active:
                self._active.remove(entry)
        log.info("Local client %s disconnected", label)

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        with self._active_lock:
            for lc, rc in self._active:
                for s in (lc, rc):
                    try:
                        s.close()
                    except Exception:
                        pass
            self._active.clear()
        log.info("TCP forwarder stopped (local port %d)", self.local_port)