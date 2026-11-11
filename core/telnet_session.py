# 文件名: core/telnet_session.py
"""Remote Telnet session: connect to another machine's shared port, verify password first.
Receiver uses a line buffer to detect [shub@source] command records (display only, never write back).
"""

import queue
import socket
import threading

from config import NEWLINE_MAP
from logger import log


class TelnetSession:
    def __init__(self, name, host, port, password, cfg):
        self.name = name
        self.host = host
        self.port = int(port)
        self.password = password
        self.cfg = cfg
        self.cmd_prefix = cfg.get("cmd_record_prefix", "[shub@")
        self.sock = None
        self.rx_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self._line_buf = bytearray()
        self.newline = NEWLINE_MAP.get(cfg.get("newline", "crlf"), "\r\n")
        self._running = False
        self._read_thread = None
        self._write_lock = threading.Lock()
        self.broadcast = None
        self.script_sender = None
        self._printer_started = False

    def open(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.sock.sendall((self.password + "\n").encode("utf-8"))
        resp = self._recv_line()
        if resp.strip() != "OK":
            self.sock.close()
            self.sock = None
            raise ConnectionError("Wrong password or server rejected")
        self.sock.settimeout(None)
        self._running = True
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _recv_line(self):
        buf = bytearray()
        while b"\n" not in buf:
            try:
                chunk = self.sock.recv(1)
            except socket.timeout:
                break
            if not chunk:
                break
            buf.extend(chunk)
        return buf.decode("utf-8", errors="replace")

    def _read_loop(self):
        while self._running:
            try:
                data = self.sock.recv(1024)
                if not data:
                    self.rx_queue.put(b"[shub] Remote disconnected\n")
                    break
                self._line_buf.extend(data)
                while b"\n" in self._line_buf:
                    line, _, rest = self._line_buf.partition(b"\n")
                    self._line_buf = bytearray(rest)
                    self._handle_line(line + b"\n")
            except Exception as e:
                self.rx_queue.put(f"[connection error] {e}\n".encode("utf-8", "replace"))
                log.error("远程 %s 读错误: %s", self.name, e, exc_info=True)
                break

    def _handle_line(self, line: bytes):
        text = line.decode("utf-8", errors="replace")
        if text.startswith(self.cmd_prefix):
            self.input_queue.put(text)
        else:
            self.rx_queue.put(line)

    def send(self, text):
        if not self.sock:
            return False
        payload = (text + self.newline).encode("utf-8", errors="replace")
        with self._write_lock:
            self.sock.sendall(payload)
        return True

    def send_raw(self, data):
        if not self.sock:
            return False
        with self._write_lock:
            self.sock.sendall(data)
        return True

    def close(self):
        self._running = False
        if self._read_thread:
            self._read_thread.join(timeout=1)
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass