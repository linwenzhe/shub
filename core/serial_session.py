# 文件名: core/serial_session.py
"""Local serial session: exclusive COM open, read thread, send, subscribe, port listing."""

import queue
import threading

import serial
from serial.tools import list_ports

from config import NEWLINE_MAP
from logger import log


def list_available_ports():
    result = []
    for p in list_ports.comports():
        result.append((p.device.upper(), p.description or ""))
    result.sort(key=lambda x: x[0])
    return result


def port_exists(port):
    port = port.upper()
    return any(dev == port for dev, _ in list_available_ports())


class SerialSession:
    def __init__(self, name, port, cfg):
        self.name = name
        self.port = port.upper()
        self.cfg = cfg
        self.ser = None
        self.rx_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self._extra_queues = []
        self._extra_lock = threading.Lock()
        self.newline = NEWLINE_MAP.get(cfg.get("newline", "crlf"), "\r\n")
        self._running = False
        self._read_thread = None
        self._write_lock = threading.Lock()
        self.broadcast = None
        self.script_sender = None
        self._printer_started = False

    def subscribe(self):
        q = queue.Queue()
        with self._extra_lock:
            self._extra_queues.append(q)
        return q

    def unsubscribe(self, q):
        with self._extra_lock:
            if q in self._extra_queues:
                self._extra_queues.remove(q)

    def open(self):
        kwargs = dict(
            port=self.port,
            baudrate=self.cfg.get("baudrate", 115200),
            bytesize=self.cfg.get("bytesize", 8),
            parity=self.cfg.get("parity", "N"),
            stopbits=self.cfg.get("stopbits", 1),
            timeout=self.cfg.get("read_timeout", 0.05),
        )
        flow = self.cfg.get("flow", "none")
        if flow == "rts":
            kwargs["rtscts"] = True
        elif flow == "xon":
            kwargs["xonxoff"] = True
        self.ser = serial.Serial(**kwargs)
        self._running = True
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _read_loop(self):
        while self._running:
            try:
                data = self.ser.read(256)
                if data:
                    self.rx_queue.put(data)
                    with self._extra_lock:
                        extras = list(self._extra_queues)
                    for q in extras:
                        q.put(data)
            except Exception as e:
                self.rx_queue.put(f"[serial read error] {e}".encode("utf-8", "replace"))
                log.error("串口 %s 读错误: %s", self.port, e, exc_info=True)
                break

    def send(self, text):
        if not self.ser or not self.ser.is_open:
            return False
        payload = (text + self.newline).encode("utf-8", errors="replace")
        with self._write_lock:
            self.ser.write(payload)
        return True

    def send_raw(self, data):
        if not self.ser or not self.ser.is_open:
            return False
        with self._write_lock:
            self.ser.write(data)
        return True

    def close(self):
        self._running = False
        if self._read_thread:
            self._read_thread.join(timeout=1)
        if self.ser and self.ser.is_open:
            self.ser.close()
        with self._extra_lock:
            self._extra_queues.clear()