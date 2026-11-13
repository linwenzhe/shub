# 文件名: tests/test_tcp_server.py
"""Tests for TcpSerialServer: data plane and port selection."""

import queue
import socket
import threading
import time
import unittest

from config import TCP_PORT_START
from core.errors import TcpError
from core.tcp_server import TcpSerialServer


class MockSession:
    def __init__(self):
        self.sent = []
        self._queues = []
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue()
        with self._lock:
            self._queues.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            if q in self._queues:
                self._queues.remove(q)

    def send_raw(self, data):
        with self._lock:
            self.sent.append(data)
        return True

    def feed(self, data):
        with self._lock:
            qs = list(self._queues)
        for q in qs:
            q.put(data)


def _find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestTcpServer(unittest.TestCase):
    def setUp(self):
        self.session = MockSession()
        self.port = _find_free_port()
        self.server = TcpSerialServer(self.session, self.port)
        self.server.start()
        time.sleep(0.1)

    def tearDown(self):
        self.server.stop()

    def _connect(self):
        sock = socket.create_connection(
            ("127.0.0.1", self.port), timeout=2)
        sock.settimeout(2)
        return sock

    def test_two_clients_broadcast(self):
        c1 = self._connect()
        c2 = self._connect()
        try:
            time.sleep(0.2)
            self.session.feed(b"hello")
            time.sleep(0.4)
            self.assertEqual(c1.recv(1024), b"hello")
            self.assertEqual(c2.recv(1024), b"hello")
        finally:
            c1.close()
            c2.close()

    def test_client_input_goes_to_session(self):
        c = self._connect()
        try:
            time.sleep(0.2)
            c.sendall(b"help\r")
            time.sleep(0.3)
            self.assertEqual(self.session.sent, [b"help\r"])
        finally:
            c.close()

    def test_two_clients_input_aggregated(self):
        c1 = self._connect()
        c2 = self._connect()
        try:
            time.sleep(0.2)
            c1.sendall(b"one")
            c2.sendall(b"two")
            time.sleep(0.3)
            self.assertIn(b"one", self.session.sent)
            self.assertIn(b"two", self.session.sent)
        finally:
            c1.close()
            c2.close()

    def test_bytes_are_transparent(self):
        c = self._connect()
        try:
            time.sleep(0.2)
            payload = bytes(range(256))
            c.sendall(payload)
            time.sleep(0.3)
            self.assertEqual(self.session.sent, [payload])

            self.session.feed(payload)
            received = b""
            while len(received) < len(payload):
                chunk = c.recv(1024)
                if not chunk:
                    break
                received += chunk
            self.assertEqual(received, payload)
        finally:
            c.close()

    def test_disconnect_does_not_break_others(self):
        c1 = self._connect()
        c2 = self._connect()
        try:
            time.sleep(0.2)
            c1.close()
            time.sleep(0.2)
            self.session.feed(b"still here")
            time.sleep(0.3)
            self.assertEqual(c2.recv(1024), b"still here")
        finally:
            c2.close()

    def test_client_count(self):
        c1 = self._connect()
        c2 = self._connect()
        try:
            time.sleep(0.2)
            self.assertEqual(self.server.client_count(), 2)
            c1.close()
            time.sleep(0.3)
            self.assertEqual(self.server.client_count(), 1)
        finally:
            c2.close()


class TestTcpServerPortSelection(unittest.TestCase):
    def test_auto_port_starts_at_configured_start(self):
        session = MockSession()
        server = TcpSerialServer(session, None)
        server.start()
        try:
            self.assertIsInstance(server.port, int)
            self.assertGreaterEqual(server.port, TCP_PORT_START)
        finally:
            server.stop()

    def test_fixed_port_conflict_raises(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("0.0.0.0", 0))
        s.listen(1)
        occupied = s.getsockname()[1]
        try:
            session = MockSession()
            server = TcpSerialServer(session, occupied)
            with self.assertRaises(TcpError):
                server.start()
        finally:
            s.close()

    def test_auto_port_skips_occupied(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", TCP_PORT_START))
            s.listen(1)
        except OSError:
            self.skipTest(
                f"TCP_PORT_START ({TCP_PORT_START}) already in use")

        try:
            session = MockSession()
            server = TcpSerialServer(session, None)
            server.start()
            try:
                self.assertNotEqual(server.port, TCP_PORT_START)
                self.assertGreater(server.port, TCP_PORT_START)
            finally:
                server.stop()
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()