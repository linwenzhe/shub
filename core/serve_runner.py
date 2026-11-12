# 文件名: core/serve_runner.py
"""ServeRunner: owns the lifecycle of a shared serial port.

The REPL calls start() on the main thread (so failures print immediately),
then launches wait() on a worker thread. request_stop() makes wait()
return so the worker can call stop().
"""

import threading

from core.errors import SerialPortError, ShubError
from core.serial_session import SerialSession, list_available_ports, port_exists
from core.tcp_server import TcpSerialServer
from logger import log


class ServeRunner:
    def __init__(self, serial_port, tcp_port, cfg, password=None):
        self.serial_port = serial_port
        self.tcp_port = int(tcp_port)
        self.cfg = cfg
        self.password = password
        self.session = None
        self.server = None
        self._stop_event = threading.Event()

    def start(self):
        serial_port = self.serial_port.upper()
        if not port_exists(serial_port):
            avail = ", ".join(d for d, _ in list_available_ports()) or "none"
            raise SerialPortError(
                f"Port {serial_port} not found. Available: {avail}")

        self.session = SerialSession(serial_port, serial_port, self.cfg)
        try:
            self.session.open()
        except ShubError:
            raise
        except Exception as e:
            raise SerialPortError(f"Cannot open {serial_port}: {e}")

        try:
            self.server = TcpSerialServer(
                self.session, self.tcp_port, self.password)
            self.server.start()
        except ShubError:
            self.session.close()
            self.session = None
            raise

    def request_stop(self):
        self._stop_event.set()

    def wait(self):
        while not self._stop_event.wait(timeout=0.5):
            pass

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