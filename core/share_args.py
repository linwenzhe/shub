# 文件名: core/share_args.py
"""Parse and validate `share` arguments.

Kept separate from the REPL so argument grammar and validation can be
tested without a terminal. The REPL only calls parse_share(rest).

Profile mode:  share --profile <name>  or  share --from <name>
Direct mode:   share <port> [--tcp <port>] [serial options]

--profile and --from are equivalent. --tcp is optional: when omitted,
tcp_port is None and the TCP server picks the first free port from
TCP_PORT_START. When provided, the port is used as-is and must be free.
"""

import argparse
import shlex
import sys

from config import TCP_PORT_END, build_serial_cfg
from core.errors import ShubError
from profiles import load_profile, require_fields


class ShubParser(argparse.ArgumentParser):
    """Parser that prints the full help text on argument errors."""

    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(2, f"\n[shub] Error: {message}\n")


def _build_parser():
    parser = ShubParser(
        prog="shub",
        description="LAN serial port distributor.",
        epilog=(
            "Typical workflow:\n"
            "  1. On the machine with the serial port:\n"
            "       share COM5              (auto-pick a free port from 1000)\n"
            "       share COM5 --tcp 1000   (fixed port)\n"
            "     or, from a profile:\n"
            "       share --profile gd32\n"
            "       share --from gd32       (same thing)\n"
            "  2. On any other machine, connect a terminal directly:\n"
            "       MobaXterm -> Telnet/Raw TCP -> 192.168.1.100:1000\n"
            "\n"
            "No client software is needed on the other side.\n"
            "No authentication: anyone who can reach the port can use it."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", parser_class=ShubParser)

    share = sub.add_parser(
        "share",
        help="Share a local COM port over TCP (directly or via profile).")
    share.add_argument("serial_port", nargs="?", default=None,
                       help="e.g. COM5 (omit if using --profile/--from)")
    share.add_argument("--profile", "--from", dest="profile", default=None,
                       help="Load config from profiles/<file>.json. "
                            "--profile and --from are equivalent.")
    share.add_argument("--tcp", type=int, default=None,
                       help="TCP port to listen on (default: first free "
                            "from 1000)")
    share.add_argument("--baud", type=int, default=None)
    share.add_argument("--bytesize", type=int, default=None,
                       choices=[5, 6, 7, 8])
    share.add_argument("--parity", default=None,
                       choices=["N", "E", "O", "M", "S"])
    share.add_argument("--stopbits", type=int, default=None,
                       choices=[1, 2])
    share.add_argument("--flow", default=None,
                       choices=["none", "rts", "xon"])

    return parser


def _validate_tcp_port(tcp_port):
    if not (1 <= tcp_port <= TCP_PORT_END):
        raise ShubError(
            f"tcp_port must be between 1 and {TCP_PORT_END}, "
            f"got {tcp_port}")


def _resolve_share_args(ns):
    if ns.profile:
        if ns.serial_port or ns.tcp is not None or \
                ns.baud is not None or ns.bytesize is not None or \
                ns.parity is not None or ns.stopbits is not None or \
                ns.flow is not None:
            raise ShubError(
                "cannot combine --profile/--from with other arguments. "
                "Use 'share --profile <profile>' alone, or "
                "'share <port> [--tcp <port>]' without a profile.")

        data = load_profile(ns.profile)
        require_fields(data, "serial_port")
        tcp_port = data.get("tcp_port")
        if tcp_port is not None:
            tcp_port = int(tcp_port)
            _validate_tcp_port(tcp_port)
        cfg = build_serial_cfg(
            baudrate=data.get("baudrate"),
            bytesize=data.get("bytesize"),
            parity=data.get("parity"),
            stopbits=data.get("stopbits"),
            flow=data.get("flow"),
        )
        return str(data["serial_port"]), tcp_port, cfg

    if not ns.serial_port:
        raise ShubError(
            "serial_port required (or use --profile/--from <profile>)")

    tcp_port = ns.tcp
    if tcp_port is not None:
        _validate_tcp_port(int(tcp_port))

    cfg = build_serial_cfg(
        baudrate=ns.baud,
        bytesize=ns.bytesize,
        parity=ns.parity,
        stopbits=ns.stopbits,
        flow=ns.flow,
    )
    return ns.serial_port, tcp_port, cfg


def parse_share(rest):
    """Return (serial_port, tcp_port_or_None, cfg) or None on syntax error.

    Raises ShubError for semantic errors (bad port, profile conflict).
    """
    line = "share " + rest if rest else "share"
    try:
        parts = shlex.split(line)
    except ValueError as e:
        print(f"  syntax error: {e}")
        return None

    parser = _build_parser()
    try:
        ns = parser.parse_args(parts)
    except SystemExit:
        return None

    if ns.cmd != "share":
        return None
    return _resolve_share_args(ns)