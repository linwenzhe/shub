# 文件名: core/tcp_server.py
"""TCP serial server: expose a SerialSession on a TCP port.

- Multi-client: every accepted connection becomes a client.
- Client input is written to the serial port as raw bytes.
- Serial output is broadcast to every connected client.
- Password handshake is delegated to core.handshake.

Windows note: SO_REUSEADDR on Windows allows two active sockets to bind
the same port (undefined routing). We use SO_EXCLUSIVEADDRUSE instead, so
a second share on the same port fails loudly instead of silently hijacking
traffic. The trade-off is TIME_WAIT on recently-closed ports; the error
message mentions this.
"""

import os
import socket
import threading

from core.errors import TcpError
from core.handshake import server_handshake
from logger import log


class TcpSerialServer:
    def __init__(self, session, port, password=None):
        self.session = session
        self.port = int(port)
        self.password = password
        self.clients = []
        self._lock = threading.Lock()
        self._server = None
        self._running = False

    def start(self):
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name == "nt":
                self._server.setsockopt(
                    socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                self._server.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind(("0.0.0.0", self.port))
            self._server.listen(5)
        except OSError as e:
            if self._server:
                try:
                    self._server.close()
                except Exception:
                    pass
            raise TcpError(
                f"Cannot listen on port {self.port}: {e}. "
                "If a previous share was just stopped, the port may still "
                "be in TIME_WAIT (a minute or two on Windows); "
                "wait or use a different port."
            )

        self._server.settimeout(0.5)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        log.info("TCP server listening on port %d", self.port)

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handshake, args=(conn, addr),
                             daemon=True).start()

    def _handshake(self, conn, addr):
        label = f"{addr[0]}:{addr[1]}"
        if not server_handshake(conn, self.password):
            try:
                conn.close()
            except Exception:
                pass
            log.warning("Client %s rejected", label)
            return

        with self._lock:
            self.clients.append(conn)
        log.info("Client %s connected (%d total)", label, len(self.clients))
        threading.Thread(target=self._client_loop, args=(conn, label),
                         daemon=True).start()

    def _client_loop(self, conn, label):
        try:
            while self._running:
                data = conn.recv(1024)
                if not data:
                    break
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
            log.info("Client %s disconnected (%d remaining)",
                     label, len(self.clients))

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
        log.info("TCP server stopped (port %d)", self.port)