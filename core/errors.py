# 文件名: core/errors.py
"""Exception hierarchy. All modules raise ShubError subclasses so the REPL
can catch everything with a single except clause."""


class ShubError(Exception):
    """Base class for every error shub raises intentionally."""


class ProfileError(ShubError):
    """A profile file is missing, invalid, or incomplete."""


class SerialPortError(ShubError):
    """Serial port cannot be opened, or I/O on it failed."""


class TcpError(ShubError):
    """TCP bind, listen, or handshake failed."""