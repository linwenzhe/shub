# 文件名: config/__init__.py
"""shub configuration package.

Re-exports every constant from the submodules so existing imports like
`from config import BAUDRATE` keep working after the split.
"""

from config.serial import (
    BAUDRATE, BYTESIZE, PARITY, STOPBITS, FLOW, READ_TIMEOUT,
    build_serial_cfg,
)
from config.tcp import (
    TCP_PORT_START, TCP_PORT_END, TCP_CLIENT_QUEUE_SIZE, BIND_ADDR,
)
from config.log import (
    LOG_ENABLED, LOG_DIR, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT,
)

__all__ = [
    "BAUDRATE", "BYTESIZE", "PARITY", "STOPBITS", "FLOW", "READ_TIMEOUT",
    "build_serial_cfg",
    "TCP_PORT_START", "TCP_PORT_END", "TCP_CLIENT_QUEUE_SIZE", "BIND_ADDR",
    "LOG_ENABLED", "LOG_DIR", "LOG_LEVEL", "LOG_MAX_BYTES",
    "LOG_BACKUP_COUNT",
]