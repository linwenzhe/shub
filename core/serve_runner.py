# 文件名: core/serve_runner.py
"""ServeRunner: owns the lifecycle of a shared serial port.

The REPL calls start() on the main thread (so failures print immediately),
then launches wait() on a worker thread. request_stop() makes wait()
return so the worker can call stop().

wait() also returns if the serial read thread fails. In that case `error`
is set, and the Job is displayed as "failed" instead of a fake "running".

tcp_port may be None (auto-pick). After start() it always holds the
actual port the TCP server bound to.

session_factory / server_factory allow tests to inject fakes without
touching a real serial port or socket.
"""

import threading

from core.errors import SerialPortError, ShubError
from core.serial_session import SerialSession, list_available_ports, port_exists
from core.tcp_server import TcpSerialServer
from logger import log


def _default_session_factory(name, port, cfg):
    return SerialSession(name, port, cfg)


def _default_server_factory(session, port):
    return TcpSerialServer(session, port)


class ServeRunner:
    def __init__(self, serial_port, tcp_port, cfg,
                 session_factory=None, server_factory=None):
        self.serial_port = serial_port
        self.tcp_port = tcp_port
        self.cfg = cfg
        self.session = None
        self.server = None
        self.error = None
        self._stop_event = threading.Event()
        self._session_factory = session_factory or _default_session_factory
        self._server_factory = server_factory or _default_server_factory

    def start(self):
        serial_port = self.serial_port.upper()
        if not port_exists(serial_port):
            avail = ", ".join(d for d, _ in list_available_ports()) or "none"
            raise SerialPortError(
                f"Port {serial_port} not found. Available: {avail}")

        self.session = self._session_factory(serial_port, serial_port, self.cfg)
        try:
            self.session.open()
        except ShubError:
            self.session = None
            raise
        except Exception as e:
            self.session = None
            raise SerialPortError(f"Cannot open {serial_port}: {e}")

        try:
            self.server = self._server_factory(self.session, self.tcp_port)
            self.server.start()
            self.tcp_port = self.server.port
        except Exception:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None
            self.server = None
            raise

    def request_stop(self):
        self._stop_event.set()

    def wait(self):
        while not self._stop_event.is_set():
            if self.session and self.session.wait_error(timeout=0.2):
                self.error = self.session.error
                log.error("Serial session failed: %s", self.error)
                break

    def stop(self):
        if self.server:
            try:
                self.server.stop()
            except Exception:
                pass
            self.server = None
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None