# 文件名: core/repl.py
"""Interactive shell for shub. This is the only entry point.

A single window manages all sharing jobs, each on its own background
thread.

Commands:
    ports                              List COM ports and share status
    share <port> --tcp <port> [opts]   Share a COM port over TCP
    unshare <port>                     Stop sharing a COM port
    connect <ip:port> --local <port>   Forward a remote serial locally
    load <profile>                     Start from a profile file
    save <profile> [job | -l]          Save a running job as a profile
    list                               Show all running jobs
    help                               Show help
    exit                               Stop all jobs and quit
"""

import argparse
import shlex
import sys
import threading
import time

from config import (
    BAUDRATE, BYTESIZE, PARITY, STOPBITS, FLOW, DEFAULT_PASSWORD,
    build_serial_cfg,
)
from core.errors import ShubError
from core.serial_session import list_available_ports
from core.serve_runner import ServeRunner
from core.connect_runner import ConnectRunner
from profiles import (
    load_profile, save_profile, require_fields, password_from_profile,
)
from logger import log


def _banner():
    return """\
  shub v0.1  -  LAN serial port distributor (interactive)

  Commands:
    ports                                   List COM ports and share status
    share <port> --tcp <port> [options]     Share a COM port over TCP
    unshare <port>                          Stop sharing a COM port
    connect <ip:port> --local <port>        Forward a remote serial locally
    load <profile>                          Start from a profile file
    save <profile> [job | -l]               Save a running job as a profile
    list                                    Show all running jobs
    help                                    Show this message
    exit                                    Stop all jobs and quit

  'share -h' / 'connect -h' shows the same options for each command.
"""


class ShubParser(argparse.ArgumentParser):
    """Parser that prints the full help text on argument errors.

    In the REPL a wrong argument should not abort the shell; it should
    print the command's help and return to the prompt.
    """

    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(2, f"\n[shub] Error: {message}\n")


class Job:
    def __init__(self, name, kind, runner,
                 serial_port=None, tcp_port=None, description=""):
        self.name = name
        self.kind = kind  # "share" | "connect"
        self.runner = runner
        self.serial_port = serial_port
        self.tcp_port = tcp_port
        self.description = description
        self.thread = None
        self.started_at = time.time()

    def launch(self):
        self.thread = threading.Thread(target=self._wait_loop, daemon=True)
        self.thread.start()

    def _wait_loop(self):
        try:
            self.runner.wait()
        finally:
            self.runner.stop()

    def stop(self):
        self.runner.request_stop()
        if self.thread:
            self.thread.join(timeout=3)

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

    def status(self):
        if not self.is_running():
            return "stopped"
        elapsed = int(time.time() - self.started_at)
        m, s = divmod(elapsed, 60)
        return f"running ({m}m{s:02d}s)"


class Repl:
    def __init__(self):
        self.parser = self._build_parser()
        self.jobs = {}
        self._lock = threading.Lock()

    # ---------- parser ----------

    def _build_parser(self):
        parser = ShubParser(
            prog="shub",
            description="LAN serial port distributor.",
            epilog=(
                "Typical workflow:\n"
                "  1. On the machine with the serial port:\n"
                "       share COM5 --tcp 1000\n"
                "  2. On the machine running MobaXterm:\n"
                "       connect 192.168.1.100:1000 --local 2000\n"
                "  3. In MobaXterm: Raw TCP session to 127.0.0.1:2000\n"
                "\n"
                "Ports: --tcp is server-side (0.0.0.0, LAN reachable);\n"
                "       --local is client-side (127.0.0.1, local only)."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        sub = parser.add_subparsers(dest="cmd", parser_class=ShubParser)

        share = sub.add_parser("share",
                               help="Share a local COM port over TCP.")
        share.add_argument("serial_port", help="e.g. COM5")
        share.add_argument("--tcp", type=int, required=True,
                           help="TCP port to listen on")
        share.add_argument("--baud", type=int, default=BAUDRATE)
        share.add_argument("--bytesize", type=int, default=BYTESIZE,
                           choices=[5, 6, 7, 8])
        share.add_argument("--parity", default=PARITY,
                           choices=["N", "E", "O", "M", "S"])
        share.add_argument("--stopbits", type=int, default=STOPBITS,
                           choices=[1, 2])
        share.add_argument("--flow", default=FLOW,
                           choices=["none", "rts", "xon"])
        share.add_argument("--password", default=DEFAULT_PASSWORD)
        share.add_argument("--no-password", action="store_true",
                           help="Skip password handshake (trusted LAN only)")

        connect = sub.add_parser(
            "connect",
            help="Forward a remote serial to a local TCP port.")
        connect.add_argument("remote", help="ip:port of the remote shub share")
        connect.add_argument("--local", type=int, required=True,
                             help="Local TCP port for terminals to connect to")
        connect.add_argument("--password", default=DEFAULT_PASSWORD)
        connect.add_argument("--no-password", action="store_true",
                             help="Send no password line to the remote")

        load = sub.add_parser("load", help="Load a profile from profiles/.")
        load.add_argument("profile", help="Profile name (with or without .json)")

        return parser

    # ---------- helpers ----------

    def _find_share(self, serial_port):
        port = serial_port.upper()
        with self._lock:
            for j in self.jobs.values():
                if j.kind == "share" and j.serial_port == port:
                    return j
        return None

    def _start_share(self, serial_port, tcp_port, cfg, password):
        port = serial_port.upper()
        existing = self._find_share(port)
        if existing:
            print(f"  error: {port} is already shared on "
                  f"tcp:{existing.tcp_port}. Use 'unshare {port}' first.")
            return

        runner = ServeRunner(port, tcp_port, cfg, password)
        try:
            runner.start()
        except ShubError as e:
            print(f"  error: {e}")
            log.error("REPL share failed: %s", e, exc_info=True)
            return
        except Exception as e:
            print(f"  error: {e}")
            log.error("REPL share failed: %s", e, exc_info=True)
            return

        name = f"share-{port}"
        job = Job(name, "share", runner,
                  serial_port=port, tcp_port=tcp_port,
                  description=f"{port} -> tcp:{tcp_port}")
        job.launch()
        with self._lock:
            self.jobs[name] = job
        print(f"  started {name}  ({port} -> tcp:{tcp_port})")

    def _start_connect(self, remote, local_port, password):
        runner = ConnectRunner(remote, local_port, password)
        try:
            runner.start()
        except ShubError as e:
            print(f"  error: {e}")
            log.error("REPL connect failed: %s", e, exc_info=True)
            return
        except Exception as e:
            print(f"  error: {e}")
            log.error("REPL connect failed: %s", e, exc_info=True)
            return

        name = f"connect-{local_port}"
        job = Job(name, "connect", runner,
                  tcp_port=local_port,
                  description=f"{remote} -> 127.0.0.1:{local_port}")
        job.launch()
        with self._lock:
            self.jobs[name] = job
        print(f"  started {name}  ({remote} -> 127.0.0.1:{local_port})")

    def _parse(self, line):
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"  syntax error: {e}")
            return None
        try:
            return self.parser.parse_args(parts)
        except SystemExit:
            return None

    # ---------- command handlers ----------

    def _cmd_ports(self):
        ports = list_available_ports()
        if not ports:
            print("  (no COM ports detected)")
            return
        with self._lock:
            share_map = {
                j.serial_port: j for j in self.jobs.values()
                if j.kind == "share" and j.is_running()
            }
        print(f"  {'PORT':<8} {'DESCRIPTION':<30} SHARE")
        for dev, desc in ports:
            job = share_map.get(dev)
            status = (f"shared on tcp:{job.tcp_port}"
                      if job else "not shared")
            desc_short = desc[:30] if desc else ""
            print(f"  {dev:<8} {desc_short:<30} {status}")

    def _cmd_list(self):
        with self._lock:
            jobs = list(self.jobs.values())
        if not jobs:
            print("  (no jobs)")
            return
        print(f"  {'NAME':<20} {'KIND':<8} {'STATUS':<18} DESCRIPTION")
        for j in jobs:
            print(f"  {j.name:<20} {j.kind:<8} {j.status():<18} "
                  f"{j.description}")

    def _cmd_share(self, line):
        ns = self._parse(line)
        if not ns or ns.cmd != "share":
            return
        cfg = build_serial_cfg(
            baudrate=ns.baud,
            bytesize=ns.bytesize,
            parity=ns.parity,
            stopbits=ns.stopbits,
            flow=ns.flow,
        )
        password = None if ns.no_password else ns.password
        self._start_share(ns.serial_port, ns.tcp, cfg, password)

    def _cmd_connect(self, line):
        ns = self._parse(line)
        if not ns or ns.cmd != "connect":
            return
        password = None if ns.no_password else ns.password
        self._start_connect(ns.remote, ns.local, password)

    def _cmd_load(self, line):
        parts = shlex.split(line)
        if len(parts) < 2:
            print("  usage: load <profile>")
            return
        try:
            data = load_profile(parts[1])
        except ShubError as e:
            print(f"  error: {e}")
            return

        typ = data["type"]
        if typ == "serve":
            try:
                require_fields(data, "serial_port", "tcp_port")
            except ShubError as e:
                print(f"  error: {e}")
                return
            cfg = build_serial_cfg(
                baudrate=data.get("baudrate"),
                bytesize=data.get("bytesize"),
                parity=data.get("parity"),
                stopbits=data.get("stopbits"),
                flow=data.get("flow"),
            )
            password = password_from_profile(data)
            self._start_share(
                data["serial_port"], int(data["tcp_port"]),
                cfg, password)
        else:
            try:
                require_fields(data, "remote", "local_port")
            except ShubError as e:
                print(f"  error: {e}")
                return
            password = password_from_profile(data)
            self._start_connect(
                data["remote"], int(data["local_port"]), password)

    def _job_to_profile(self, job):
        """Extract a profile dict from a running job's runner.

        The profile type is chosen by the job kind:
        - share   -> "type": "serve"   (serial + TCP + password)
        - connect -> "type": "connect" (remote + local port + password)
        """
        runner = job.runner
        if job.kind == "share":
            data = {
                "type": "serve",
                "serial_port": runner.serial_port,
                "baudrate": runner.cfg.get("baudrate", BAUDRATE),
                "bytesize": runner.cfg.get("bytesize", BYTESIZE),
                "parity": runner.cfg.get("parity", PARITY),
                "stopbits": runner.cfg.get("stopbits", STOPBITS),
                "flow": runner.cfg.get("flow", FLOW),
                "tcp_port": runner.tcp_port,
            }
            if runner.password is None:
                data["no_password"] = True
            else:
                data["password"] = runner.password
            return data
        else:  # connect
            data = {
                "type": "connect",
                "remote": runner.remote,
                "local_port": runner.local_port,
            }
            if runner.password is None:
                data["no_password"] = True
            else:
                data["password"] = runner.password
            return data

    def _cmd_save(self, line):
        parts = shlex.split(line)
        if not parts:
            print("  usage: save <profile_name> [job_name | -l]")
            return
        profile_name = parts[0]

        job = None
        latest = False

        if len(parts) >= 2:
            arg = parts[1]
            if arg == "-l":
                latest = True
                if len(parts) > 2:
                    print("  error: cannot combine '-l' with a job name.")
                    return
            else:
                with self._lock:
                    job = self.jobs.get(arg)
                if not job:
                    print(f"  error: no job named {arg}")
                    return
        else:
            with self._lock:
                jobs = list(self.jobs.values())
            if not jobs:
                print("  error: no jobs to save. Start one with 'share' "
                      "or 'connect' first.")
                return
            if len(jobs) == 1:
                job = jobs[0]
            else:
                latest_job = max(jobs, key=lambda j: j.started_at)
                print("  error: multiple jobs are running. "
                      "Specify which job to save:")
                print(f"    save {profile_name} -l"
                      f"                 (most recent: {latest_job.name})")
                for j in jobs:
                    print(f"    save {profile_name} {j.name}")
                print("  Use 'list' to see all jobs.")
                return

        if latest:
            with self._lock:
                jobs = list(self.jobs.values())
            if not jobs:
                print("  error: no jobs to save. Start one with 'share' "
                      "or 'connect' first.")
                return
            job = max(jobs, key=lambda j: j.started_at)

        try:
            data = self._job_to_profile(job)
            full, existed = save_profile(profile_name, data)
        except ShubError as e:
            print(f"  error: {e}")
            log.error("REPL save failed: %s", e, exc_info=True)
            return

        action = "overwrote" if existed else "created"
        typ = data["type"]
        if typ == "serve":
            summary = (f"serve: {data['serial_port']} "
                       f"-> tcp:{data['tcp_port']}")
        else:
            summary = (f"connect: {data['remote']} "
                       f"-> 127.0.0.1:{data['local_port']}")

        suffix = "   (most recent)" if latest else ""
        print(f"  {action} {full}")
        print(f"    {summary}{suffix}")

    def _cmd_unshare(self, line):
        parts = shlex.split(line)
        if not parts:
            print("  usage: unshare <serial_port>")
            return
        port = parts[0].upper()
        job = self._find_share(port)
        if not job:
            print(f"  error: {port} is not shared")
            return
        with self._lock:
            self.jobs.pop(job.name, None)
        job.stop()
        print(f"  unshared {port} (released tcp:{job.tcp_port})")

    # ---------- main loop ----------

    def _handle(self, line):
        line = line.strip()
        if not line:
            return True
        head = line.split(None, 1)[0].lower()
        rest = line[len(head):].strip()

        if head in ("exit", "quit"):
            return False
        if head == "help":
            print(_banner())
            return True
        if head == "ports":
            self._cmd_ports()
            return True
        if head == "list":
            self._cmd_list()
            return True
        if head == "share":
            self._cmd_share(line)
            return True
        if head == "unshare":
            self._cmd_unshare(rest)
            return True
        if head == "connect":
            self._cmd_connect(line)
            return True
        if head == "load":
            self._cmd_load(line)
            return True
        if head == "save":
            self._cmd_save(rest)
            return True

        print(f"  unknown command: {head}. Type 'help'.")
        return True

    def run(self):
        print(_banner())
        while True:
            try:
                line = input("shub> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                if not self._handle(line):
                    break
            except Exception as e:
                print(f"  error: {e}")
                log.error("REPL command failed: %s", e, exc_info=True)

        with self._lock:
            jobs = list(self.jobs.values())
            self.jobs.clear()
        for j in jobs:
            try:
                j.stop()
            except Exception:
                pass
        if jobs:
            print(f"  stopped {len(jobs)} job(s)")
        print("[shub] Bye")