# 文件名: config/serial.py
"""Serial port defaults and the runtime cfg builder."""

BAUDRATE = 115200
BYTESIZE = 8
PARITY = "N"          # N / E / O / M / S
STOPBITS = 1
FLOW = "none"         # none / rts / xon
READ_TIMEOUT = 0.05


def build_serial_cfg(**overrides):
    """Return a cfg dict for SerialSession.

    Any keyword whose value is None is replaced by the default. This lets
    callers pass `baudrate=data.get("baudrate")` and get the default when
    the key is absent from a profile.
    """
    cfg = {
        "baudrate": BAUDRATE,
        "bytesize": BYTESIZE,
        "parity": PARITY,
        "stopbits": STOPBITS,
        "flow": FLOW,
        "read_timeout": READ_TIMEOUT,
    }
    for k, v in overrides.items():
        if v is not None:
            cfg[k] = v
    return cfg