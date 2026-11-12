# 文件名: core/session_protocol.py
"""Structural interface that TcpSerialServer depends on.

Using Protocol instead of duck typing makes the required methods explicit
for type checkers and for anyone writing an alternative implementation
(e.g. a PTY session or a test mock).
"""

from typing import Any, Protocol


class SerialSessionLike(Protocol):
    def subscribe(self) -> Any:
        """Return a queue that will receive the same bytes as the serial port."""
        ...

    def unsubscribe(self, q: Any) -> None:
        """Stop feeding q and release it."""
        ...

    def send_raw(self, data: bytes) -> bool:
        """Write raw bytes to the underlying device. True on success."""
        ...