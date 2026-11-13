# 文件名: core/tcp_server.py
"""TCP serial server: expose a SerialSession on a TCP port.

Data plane (must stay byte-transparent):
- Client input is written to the serial port as raw bytes.
- Serial output is broadcast to every connected client as raw bytes.

Port selection:
- requested_port is int: use exactly that port. If bind fails, raise
  TcpError. This is the "user asked for it, be strict" path.
- requested_port is None: bind the first free port from TCP_PORT_START
  upward. The actual port is exposed as self.port after start().

Concurrency:
- Each client owns a bounded send queue and a dedicated send thread.
- The broadcast loop only calls put_nowait(); it never blocks on a slow
  client. If a client's queue is full, that client is dropped and the
  other clients keep flowing.
- Client input is read on a separate per-client thread.

No authentication: any client that can reach the port is trusted.
"""

import os
import queue
import socket
import threading

from config import (
    BIND_ADDR, TCP_CLIENT_QUEUE_SIZE, TCP_PORT_START, TCP_PORT_END,
)
from core.errors import TcpError
from core.session_protocol import SerialSessionLike
from logger import log


class _Client:
    """One TCP client: a bounded outbound queue + a send thread."""

    def __init__(self, conn, label):
        self.conn = conn
        self.label = label
        self.queue = queue.Queue(maxsize=TCP_CLIENT_QUEUE_SIZE)
        self._running = True
        try:
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        self._thread = threading.Thread(
            target=self._send_loop, daemon=True)

    def start(self):
        self._thread.start()

    def is_active(self):
        return self._running

    def _send_loop(self):
        while self._running:
            try:
                data = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self.conn.sendall(data)
            except OSError:
                self._running = False
                break

    def send(self, data):
        if not self._running:
            return False
        try:
            self.queue.put_nowait(data)
            return True
        except queue.Full:
            log.warning("Client %s send queue full, dropping",
                        self.label)
            self._running = False
            return False

    def close(self):
        self._running = False
        try:
            self.conn.close()
        except Exception:
            pass


class TcpSerialServer:
    def __init__(self, session: SerialSessionLike, port):
        """port: int for a fixed port, None for auto-pick from TCP_PORT_START."""
        self.session = session
        self.requested_port = port
        self.port = None
        self.clients = []
        self._lock = threading.Lock()
        self._server = None
        self._running = False

    def start(self):
        self._server, self.port = self._bind()
        self._server.settimeout(0.5)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        log.info("TCP server listening on %s:%d", BIND_ADDR, self.port)

    def _bind(self):
        if self.requested_port is not None:
            return self._bind_fixed(int(self.requested_port))
        return self._bind_auto()

    def _new_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name == "nt":
            sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock

    def _bind_fixed(self, port):
        sock = self._new_socket()
        try:
            sock.bind((BIND_ADDR, port))
            sock.listen(5)
            return sock, port
        except OSError as e:
            try:
                sock.close()
            except Exception:
                pass
            raise TcpError(
                f"Cannot listen on {BIND_ADDR}:{port}: {e}. "
                "If a previous share was just stopped, the port may still "
                "be in TIME_WAIT (a minute or two on Windows); "
                "wait or use a different port, or omit --tcp to let shub "
                "pick a free port automatically."
            )

    def _bind_auto(self):
        last_error = None
        for port in range(TCP_PORT_START, TCP_PORT_END + 1):
            sock = self._new_socket()
            try:
                sock.bind((BIND_ADDR, port))
                sock.listen(5)
                return sock, port
            except OSError as e:
                last_error = e
                try:
                    sock.close()
                except Exception:
                    pass
                continue
        raise TcpError(
            f"No free TCP port on {BIND_ADDR} in range "
            f"{TCP_PORT_START}-{TCP_PORT_END}: {last_error}")

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        with self._lock:
            clients = list(self.clients)
            self.clients.clear()
        for c in clients:
            c.close()
        log.info("TCP server stopped (port %s)", self.port)

    def client_count(self):
        with self._lock:
            return len(self.clients)

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            label = f"{addr[0]}:{addr[1]}"
            client = _Client(conn, label)
            client.start()
            with self._lock:
                self.clients.append(client)
            log.info("Client %s connected (%d total)",
                     label, len(self.clients))
            threading.Thread(
                target=self._client_loop,
                args=(client,), daemon=True).start()

    def _client_loop(self, client):
        try:
            while self._running and client.is_active():
                data = client.conn.recv(1024)
                if not data:
                    break
                self.session.send_raw(data)
        except OSError:
            pass
        finally:
            self._remove_clients([client])

    def _broadcast_loop(self):
        q = self.session.subscribe()
        try:
            while self._running:
                try:
                    data = q.get(timeout=0.1)
                except queue.Empty:
                    continue
                with self._lock:
                    clients = list(self.clients)
                dead = []
                for c in clients:
                    if not c.send(data):
                        dead.append(c)
                if dead:
                    self._remove_clients(dead)
        finally:
            self.session.unsubscribe(q)

    def _remove_clients(self, clients):
        removed = []
        with self._lock:
            for c in clients:
                if c in self.clients:
                    self.clients.remove(c)
                    removed.append(c)
        for c in removed:
            c.close()
            log.info("Client %s disconnected (%d remaining)",
                     c.label, len(self.clients))