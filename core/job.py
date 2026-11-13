# 文件名: core/job.py
"""Job: one running share, independent of the REPL.

A Job owns a ServeRunner and a worker thread that waits for either an
explicit stop or a serial read failure. The REPL only reads status and
calls stop(); it does not manage runner threads directly.
"""

import threading
import time


class Job:
    def __init__(self, name, runner, serial_port, tcp_port, description=""):
        self.name = name
        self.runner = runner
        self.serial_port = serial_port
        self.tcp_port = tcp_port
        self.description = description
        self.thread = None
        self.started_at = time.time()
        self.error = None

    def launch(self):
        self.thread = threading.Thread(target=self._wait_loop, daemon=True)
        self.thread.start()

    def _wait_loop(self):
        try:
            self.runner.wait()
        finally:
            self.runner.stop()
            if self.runner.error:
                self.error = self.runner.error

    def stop(self):
        self.runner.request_stop()
        if self.thread:
            self.thread.join(timeout=3)

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

    def client_count(self):
        server = self.runner.server if self.runner else None
        if not server:
            return 0
        try:
            return server.client_count()
        except Exception:
            return 0

    def status(self):
        if not self.is_running():
            return "failed" if self.error else "stopped"
        elapsed = int(time.time() - self.started_at)
        m, s = divmod(elapsed, 60)
        return f"running ({m}m{s:02d}s)"