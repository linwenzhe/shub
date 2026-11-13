# 文件名: core/session_protocol.py
"""Structural interface that TcpSerialServer depends on."""

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