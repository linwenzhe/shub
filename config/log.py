# 文件名: config/log.py
"""Logging switches."""

LOG_ENABLED = True         # False = completely disable logging
LOG_DIR = "logs"
LOG_LEVEL = "INFO"         # DEBUG / INFO / WARNING / ERROR (file level)
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 3