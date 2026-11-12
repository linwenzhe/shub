# 文件名: tests/test_tcp_server.py
"""Tests for TcpSerialServer with a mock session."""

import queue
import socket
import threading
import time
import unittest

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


class TestTcpServerNoPassword(unittest.TestCase):
    def setUp(self):
        self.session = MockSession()
        self.port = _find_free_port()
        self.server = TcpSerialServer(self.session, self.port, password=None)
        self.server.start()
        time.sleep(0.1)

    def tearDown(self):
        self.server.stop()

    def _connect(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        sock.settimeout(2)
        return sock

    def test_two_clients_broadcast(self):
        c1 = self._connect()
        c2 = self._connect()
        try:
            time.sleep(0.1)
            self.session.feed(b"hello")
            time.sleep(0.2)
            self.assertEqual(c1.recv(1024), b"hello")
            self.assertEqual(c2.recv(1024), b"hello")
        finally:
            c1.close()
            c2.close()

    def test_client_input_goes_to_session(self):
        c = self._connect()
        try:
            time.sleep(0.1)
            c.sendall(b"help\r")
            time.sleep(0.2)
            self.assertEqual(self.session.sent, [b"help\r"])
        finally:
            c.close()

    def test_two_clients_input_aggregated(self):
        c1 = self._connect()
        c2 = self._connect()
        try:
            time.sleep(0.1)
            c1.sendall(b"one")
            c2.sendall(b"two")
            time.sleep(0.2)
            self.assertIn(b"one", self.session.sent)
            self.assertIn(b"two", self.session.sent)
        finally:
            c1.close()
            c2.close()


class TestTcpServerWithPassword(unittest.TestCase):
    def setUp(self):
        self.session = MockSession()
        self.port = _find_free_port()
        self.server = TcpSerialServer(self.session, self.port, password="abc")
        self.server.start()
        time.sleep(0.1)

    def tearDown(self):
        self.server.stop()

    def test_correct_password(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        sock.settimeout(2)
        try:
            sock.sendall(b"abc\n")
            self.assertEqual(sock.recv(16), b"OK\n")
        finally:
            sock.close()

    def test_wrong_password(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        sock.settimeout(2)
        try:
            sock.sendall(b"wrong\n")
            self.assertEqual(sock.recv(16), b"ERR\n")
        finally:
            sock.close()


if __name__ == "__main__":
    unittest.main()