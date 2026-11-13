# 文件名: core/serial_session.py
"""Local serial session: exclusive open, read thread, subscribe, raw send.

Byte-oriented: the caller supplies raw bytes and they are written to the
serial port unchanged. No newline handling here; the terminal on the other
side decides line endings.

Read-thread failures are recorded in an internal Event and exposed via
wait_error()/error so ServeRunner can tear the job down instead of leaving
it displayed as "running".
"""

import queue
import threading

import serial
from serial.tools import list_ports

from core.errors import SerialPortError
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
        self._extra_queues = []
        self._extra_lock = threading.Lock()
        self._running = False
        self._read_thread = None
        self._write_lock = threading.Lock()
        self._error_event = threading.Event()
        self._error = None

    def subscribe(self):
        q = queue.Queue()
        with self._extra_lock:
            self._extra_queues.append(q)
        return q

    def unsubscribe(self, q):
        with self._extra_lock:
            if q in self._extra_queues:
                self._extra_queues.remove(q)

    @property
    def error(self):
        return self._error

    def wait_error(self, timeout=None):
        return self._error_event.wait(timeout=timeout)

    def open(self):
        kwargs = dict(
            port=self.port,
            baudrate=int(self.cfg.get("baudrate", 115200)),
            bytesize=int(self.cfg.get("bytesize", 8)),
            parity=str(self.cfg.get("parity", "N")),
            stopbits=int(self.cfg.get("stopbits", 1)),
            timeout=float(self.cfg.get("read_timeout", 0.05)),
        )
        flow = str(self.cfg.get("flow", "none")).lower()
        if flow == "rts":
            kwargs["rtscts"] = True
        elif flow == "xon":
            kwargs["xonxoff"] = True

        try:
            self.ser = serial.Serial(**kwargs)
        except serial.SerialException as e:
            raise SerialPortError(f"Cannot open {self.port}: {e}")

        self._running = True
        self._read_thread = threading.Thread(
            target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _read_loop(self):
        while self._running:
            try:
                data = self.ser.read(256)
            except Exception as e:
                log.error("Serial %s read error: %s",
                          self.port, e, exc_info=True)
                self._error = e
                self._error_event.set()
                break
            if not data:
                continue
            with self._extra_lock:
                extras = list(self._extra_queues)
            for q in extras:
                q.put(data)

    def send_raw(self, data):
        if not self.ser or not self.ser.is_open:
            return False
        with self._write_lock:
            try:
                self.ser.write(data)
                return True
            except Exception as e:
                log.error("Serial %s write error: %s",
                          self.port, e, exc_info=True)
                return False

    def close(self):
        self._running = False
        if self._read_thread:
            self._read_thread.join(timeout=1)
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        with self._extra_lock:
            self._extra_queues.clear()