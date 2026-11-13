# 文件名: logger.py
"""Logging: rolling file log + console output for WARNING and above.

Config switches in config/log.py:
- LOG_ENABLED: False -> no logs/ directory, no file, no console log.
- LOG_LEVEL: file log level (DEBUG / INFO / WARNING / ERROR). Console is
  always WARNING, so DEBUG does not flood the terminal.

Logging is for debugging only. There is no runtime command to change it;
edit config/log.py and restart.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import (
    LOG_ENABLED, LOG_DIR, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT,
)


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def setup_logger():
    logger = logging.getLogger("shub")
    logger.propagate = False

    if logger.handlers:
        return logger

    if not LOG_ENABLED:
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL + 1)
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(threadName)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_dir = os.path.join(_app_dir(), LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    fh = RotatingFileHandler(
        os.path.join(log_dir, "shub.log"),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    fh.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


log = setup_logger()