# 文件名: core/handshake.py
"""Password handshake shared by server and client.

Wire protocol:
    client -> server : <password>\\n
    server -> client : OK\\n   (password matches, or no password required)
                       ERR\\n  (password mismatch; server closes after sending)

Both functions return bool; neither closes the socket on failure.
"""

import socket

from logger import log

HANDSHAKE_TIMEOUT = 5.0
OK = b"OK\n"
ERR = b"ERR\n"


def server_handshake(conn, password):
    """Return True if the peer is authorized; False otherwise.

    If password is None, no handshake is performed and the caller should
    treat the connection as authorized.
    """
    if password is None:
        return True

    try:
        conn.settimeout(HANDSHAKE_TIMEOUT)
        buf = bytearray()
        while b"\n" not in buf:
            ch = conn.recv(1)
            if not ch:
                return False
            buf.extend(ch)
        pwd = buf.decode("utf-8", errors="replace").strip()
        if pwd != password:
            try:
                conn.sendall(ERR)
            except OSError:
                pass
            return False
        conn.sendall(OK)
        conn.settimeout(None)
        return True
    except OSError as e:
        log.error("Server handshake error: %s", e)
        return False


def client_handshake(sock, password):
    """Return True if the server accepted our password; False otherwise."""
    if password is None:
        return True

    try:
        sock.sendall((password + "\n").encode("utf-8"))
        buf = bytearray()
        while b"\n" not in buf:
            ch = sock.recv(1)
            if not ch:
                return False
            buf.extend(ch)
        resp = buf.decode("utf-8", errors="replace").strip()
        if resp != "OK":
            log.warning("Server rejected handshake: %r", resp)
            return False
        sock.settimeout(None)
        return True
    except OSError as e:
        log.error("Client handshake error: %s", e)
        return False