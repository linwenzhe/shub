# 文件名: core/connect_runner.py
"""ConnectRunner: owns the lifecycle of a remote serial forward.

Same start / wait / stop pattern as ServeRunner.
"""

import threading

from core.errors import TcpError
from core.tcp_client import TcpSerialClient
from logger import log


def _split_remote(remote):
    if ":" not in remote:
        raise TcpError(f"Remote must be ip:port, got {remote!r}")
    host, port_str = remote.rsplit(":", 1)
    try:
        port = int(port_str)
    except ValueError:
        raise TcpError(f"Remote port must be a number, got {port_str!r}")
    return host, port


class ConnectRunner:
    def __init__(self, remote, local_port, password=None):
        self.remote = remote
        self.local_port = int(local_port)
        self.password = password
        self.client = None
        self._stop_event = threading.Event()

    def start(self):
        host, port = _split_remote(self.remote)
        self.client = TcpSerialClient(
            host, port, self.local_port, self.password)
        self.client.start()

    def request_stop(self):
        self._stop_event.set()

    def wait(self):
        while not self._stop_event.wait(timeout=0.5):
            pass

    def stop(self):
        if self.client:
            try:
                self.client.stop()
            except Exception:
                pass
            self.client = None