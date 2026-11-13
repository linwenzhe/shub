# 文件名: tests/test_serve_runner.py
"""Tests for ServeRunner lifecycle using fake session/server factories."""

import queue
import threading
import unittest
from unittest.mock import patch

from core.errors import SerialPortError, TcpError
from core.serve_runner import ServeRunner


class FakeSession:
    def __init__(self, name, port, cfg):
        self.name = name
        self.port = port
        self.cfg = cfg
        self.opened = False
        self.closed = False
        self._error = None
        self._event = threading.Event()

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def subscribe(self):
        return queue.Queue()

    def unsubscribe(self, q):
        pass

    def send_raw(self, data):
        return True

    def wait_error(self, timeout=None):
        return self._event.wait(timeout)

    @property
    def error(self):
        return self._error

    def fail(self, err):
        self._error = err
        self._event.set()


class FakeServer:
    def __init__(self, session, port):
        self.session = session
        self.requested_port = port
        self.port = port if port is not None else 12345
        self.started = False
        self.stopped = False
        self._clients = 0

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def client_count(self):
        return self._clients


def _session_factory(name, port, cfg):
    return FakeSession(name, port, cfg)


def _server_factory(session, port):
    return FakeServer(session, port)


class TestServeRunner(unittest.TestCase):
    def _make(self, tcp_port=1000):
        return ServeRunner(
            "COM5", tcp_port, {"baudrate": 115200},
            session_factory=_session_factory,
            server_factory=_server_factory,
        )

    @patch("core.serve_runner.port_exists", return_value=True)
    def test_start_ok(self, _mock):
        runner = self._make()
        runner.start()
        try:
            self.assertTrue(runner.session.opened)
            self.assertTrue(runner.server.started)
            self.assertEqual(runner.tcp_port, 1000)
        finally:
            runner.stop()
        self.assertTrue(runner.session.closed)
        self.assertTrue(runner.server.stopped)

    @patch("core.serve_runner.port_exists", return_value=False)
    def test_start_port_not_found(self, _mock):
        runner = self._make()
        with self.assertRaises(SerialPortError):
            runner.start()
        self.assertIsNone(runner.session)

    @patch("core.serve_runner.port_exists", return_value=True)
    def test_tcp_failure_closes_session(self, _mock):
        runner = self._make()

        def failing_server(session, port):
            raise TcpError("boom")

        runner._server_factory = failing_server
        with self.assertRaises(TcpError):
            runner.start()
        self.assertIsNone(runner.session)

    @patch("core.serve_runner.port_exists", return_value=True)
    def test_auto_port_updates_tcp_port(self, _mock):
        runner = self._make(tcp_port=None)
        runner.start()
        try:
            self.assertEqual(runner.tcp_port, 12345)
        finally:
            runner.stop()

    @patch("core.serve_runner.port_exists", return_value=True)
    def test_stop_returns_wait(self, _mock):
        runner = self._make()
        runner.start()
        result = {}

        def wait():
            runner.wait()
            result["done"] = True

        t = threading.Thread(target=wait, daemon=True)
        t.start()
        runner.request_stop()
        t.join(timeout=2)
        self.assertTrue(result.get("done"))
        runner.stop()

    @patch("core.serve_runner.port_exists", return_value=True)
    def test_serial_failure_sets_error_and_returns_wait(self, _mock):
        runner = self._make()
        runner.start()
        runner.session.fail(RuntimeError("read boom"))
        runner.wait()
        self.assertIsInstance(runner.error, RuntimeError)
        runner.stop()


if __name__ == "__main__":
    unittest.main()