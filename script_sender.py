# 文件名: script_sender.py
"""Line-by-line script sender: comments shown but not sent, blank lines sent as-is."""

import threading
import time

from logger import log


class ScriptSender:
    def __init__(self, session, filepath, interval_ms=100, loop=False):
        self.session = session
        self.filepath = filepath
        self.interval = interval_ms / 1000.0
        self.loop = loop
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._running:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    raw_lines = f.readlines()
            except OSError as e:
                print(f"[shub] Failed to read script: {e}")
                log.error("读取脚本失败: %s", e, exc_info=True)
                break

            for raw in raw_lines:
                if not self._running:
                    break
                line = raw.rstrip("\r\n")
                if line.lstrip().startswith("#"):
                    print(f"[shub] {line.strip()}")
                    continue
                if not self.session.send(line):
                    print(f"[shub] Send failed, stopping script: {self.filepath}")
                    log.warning("脚本发送失败: %s", self.filepath)
                    self._running = False
                    break
                time.sleep(self.interval)

            if not self.loop:
                break

        self._running = False
        print(f"[shub] Script finished: {self.filepath}")
        log.info("脚本发送结束: %s", self.filepath)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)