# 文件名: config.py
"""shub 配置：所有默认值集中在这里，用户可直接编辑本文件修改。"""

# ---------- 串口默认参数 ----------
BAUDRATE = 115200
BYTESIZE = 8
PARITY = "N"          # N / E / O / M / S
STOPBITS = 1
FLOW = "none"         # none / rts / xon
NEWLINE = "crlf"      # crlf -> \r\n, lf -> \n, cr -> \r, none -> ""
READ_TIMEOUT = 0.05

# ---------- 命令与历史 ----------
COMMAND_PREFIX = "shub:"
HISTORY_MAX = 100

# ---------- 共享 ----------
DEFAULT_PASSWORD = "123456"
SHARE_PORT_START = 1000
CMD_RECORD_PREFIX = "[shub@"
ECHO_REMOTE_INPUT = True

# ---------- 脚本发送 ----------
SCRIPT_DEFAULT_INTERVAL_MS = 100

# ---------- 日志 ----------
LOG_DIR = "logs"
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# ---------- 换行符映射 ----------
NEWLINE_MAP = {"crlf": "\r\n", "lf": "\n", "cr": "\r", "none": ""}


def load_config():
    return {
        "baudrate": BAUDRATE,
        "bytesize": BYTESIZE,
        "parity": PARITY,
        "stopbits": STOPBITS,
        "flow": FLOW,
        "newline": NEWLINE,
        "read_timeout": READ_TIMEOUT,
        "command_prefix": COMMAND_PREFIX,
        "history_max": HISTORY_MAX,
        "default_password": DEFAULT_PASSWORD,
        "share_port_start": SHARE_PORT_START,
        "cmd_record_prefix": CMD_RECORD_PREFIX,
        "echo_remote_input": ECHO_REMOTE_INPUT,
        "script_default_interval_ms": SCRIPT_DEFAULT_INTERVAL_MS,
    }