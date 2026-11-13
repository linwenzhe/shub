# 文件名: config/tcp.py
"""TCP bind address, port range, and per-client queue depth."""

# Bind address for the TCP listener.
# "0.0.0.0" listens on every interface. Set to a specific IPv4 (e.g.
# "192.168.1.100") if the machine has multiple NICs and you only want
# to expose the share on one of them.
BIND_ADDR = "0.0.0.0"

# Auto port picking starts here and walks upward until a bind succeeds.
TCP_PORT_START = 1000
TCP_PORT_END = 65535

# Per-client send queue depth, in chunks. Each chunk is whatever the
# serial read returned (up to 256 bytes). 1024 chunks ~= 256 KB buffer
# per client. When a client's queue is full, that client is considered
# too slow and is disconnected; healthy clients are never blocked.
TCP_CLIENT_QUEUE_SIZE = 1024