# 文件名: core/repl.py
"""Interactive shell for shub. This is the only entry point.

Commands:
    list [-p|-j]                         List COM ports (-p) or jobs (-j)
    share <port> [--tcp <port>] [opts]   Share a COM port over TCP
    share --profile <profile>            Share from a profile file
    share --from <profile>               Same as --profile
    unshare [port]                       Stop sharing (auto if only one job)
    save <job> as <profile>              Save a named job as a profile
    save <profile>                       Save the only running job
    save -l <profile>                    Save the most recently started job
    save -a [-y]                         Save all running jobs
    help                                 Show this message
    exit                                 Stop all jobs and quit

Only these 5 command names are accepted (plus exit/quit).
"""

import shlex
import threading

from core import save_service
from core.errors import ShubError
from core.job import Job
from core.line_reader import read_line
from core.save_parser import parse_save
from core.serial_session import list_available_ports
from core.serve_runner import ServeRunner
from core.share_args import parse_share
from logger import log

COMMAND_CYCLE = [
    "list",
    "share",
    "unshare",
    "save",
    "help",
]

VALID_COMMANDS = set(COMMAND_CYCLE) | {"exit", "quit"}

REQUIRES_ARGS = {"share", "save"}


def _banner():
    return """\
  shub v0.1  -  LAN serial port distributor (interactive)

  Commands:
    list [-p|-j]                            List COM ports (-p) or jobs (-j)
    share <port> [--tcp <port>] [options]   Share a COM port over TCP
    share --profile <profile>               Share using a profile file
    share --from <profile>                  Same as --profile
    unshare [port]                          Stop sharing (auto if only one job)
    save <job> as <profile>                 Save a named job as a profile
    save <profile>                          Save the only running job
    save -l <profile>                       Save the most recent job
    save -a [-y]                            Save all running jobs
    help                                    Show this message
    exit                                    Stop all jobs and quit

  --tcp is optional; without it shub picks the first free port from 1000.
  --profile and --from are equivalent.

  Up/Down arrows cycle through the 5 command names.
"""


LIST_HELP = """\
  list [-p|-j]
    -p, --ports   List COM ports and their share status
    -j, --jobs    List running jobs (default when no flag is given)
    -h, --help    Show this message
"""


SAVE_HELP = """\
  save <job> as <profile_name>
    Save the named job as a profile.
    <job> is the NAME column shown by 'list -j', e.g. share-COM5.

  save <profile_name>
    Save the only running job. Fails if 0 or more than 1 job is running.

  save -l <profile_name>
    Save the most recently started job.

  save -a [-y]
    Save every running job as a profile named after the job.
    -y: skip the overwrite confirmation for existing files
"""


UNSHARE_HELP = """\
  unshare [port]
    Stop sharing a COM port.
    - no argument: stop the only running job; error if 0 or >1 jobs
    - port: stop the job sharing that COM port, e.g. unshare COM5
"""


class Repl:
    def __init__(self):
        self.jobs = {}
        self._lock = threading.Lock()

    def _find_share(self, serial_port):
        port = serial_port.upper()
        with self._lock:
            for j in self.jobs.values():
                if j.serial_port == port:
                    return j
        return None

    def _start_share(self, serial_port, tcp_port, cfg):
        port = serial_port.upper()
        existing = self._find_share(port)
        if existing:
            print(f"  error: {port} is already shared on "
                  f"tcp:{existing.tcp_port}. Use 'unshare {port}' first.")
            return

        auto_port = tcp_port is None
        runner = ServeRunner(port, tcp_port, cfg)
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

        actual_port = runner.tcp_port
        name = f"share-{port}"
        job = Job(name, runner, port, actual_port,
                  description=f"{port} -> tcp:{actual_port}")
        job.launch()
        with self._lock:
            self.jobs[name] = job

        suffix = "   (auto port)" if auto_port else ""
        print(f"  started {name}  ({port} -> tcp:{actual_port}){suffix}")

    def _confirm_overwrite(self, full_path):
        print(f"  file exists: {full_path}")
        try:
            answer = input("  overwrite? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        if answer == "":
            return True
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False

        print(f"  '{answer}' is not a valid answer; not saved.")
        return False

    def _print_save_result(self, result, latest_suffix="",
                           include_job_name=False):
        if result.status == "failed":
            if include_job_name:
                print(f"  error: {result.job_name}: {result.error}")
            else:
                print(f"  error: {result.error}")
        elif result.status == "skipped":
            print(f"  skipped {result.path}")
        else:
            action = "overwrote" if result.existed else "created"
            print(f"  {action} {result.path}")
            print(f"    serve: {result.serial_port} "
                  f"-> tcp:{result.tcp_port}{latest_suffix}")

    def _save_auto(self, profile_name):
        with self._lock:
            jobs = list(self.jobs.values())
        if not jobs:
            print("  error: no jobs to save. Start one with 'share' "
                  "first.")
            return
        if len(jobs) > 1:
            latest_job = max(jobs, key=lambda j: j.started_at)
            print("  error: multiple jobs are running. "
                  "Specify which job to save:")
            for j in jobs:
                print(f"    save {j.name} as {profile_name}")
            print(f"    save -l {profile_name}"
                  f"       (most recent: {latest_job.name})")
            print(f"    save -a                (save all jobs)")
            print("  Use 'list -j' to see all jobs.")
            return
        result = save_service.save_one(
            jobs[0], profile_name, self._confirm_overwrite)
        self._print_save_result(result)

    def _save_latest(self, profile_name):
        with self._lock:
            jobs = list(self.jobs.values())
        if not jobs:
            print("  error: no jobs to save. Start one with 'share' "
                  "first.")
            return
        job = max(jobs, key=lambda j: j.started_at)
        result = save_service.save_one(
            job, profile_name, self._confirm_overwrite)
        self._print_save_result(result, "   (most recent)")

    def _save_all(self, auto_yes=False):
        with self._lock:
            jobs = list(self.jobs.values())
        if not jobs:
            print("  error: no jobs to save. Start one with 'share' "
                  "first.")
            return

        results = save_service.save_all(
            jobs, auto_yes, self._confirm_overwrite)
        saved = skipped = failed = 0
        for r in results:
            self._print_save_result(r, include_job_name=True)
            if r.status == "saved":
                saved += 1
            elif r.status == "skipped":
                skipped += 1
            else:
                failed += 1

        parts = [f"saved {saved}"]
        if skipped:
            parts.append(f"skipped {skipped}")
        if failed:
            parts.append(f"failed {failed}")
        print("  " + ", ".join(parts))

    def _save_one(self, job_name, profile_name):
        with self._lock:
            job = self.jobs.get(job_name)
        if not job:
            print(f"  error: no job named {job_name}. "
                  f"Use 'list -j' to see all jobs.")
            return
        result = save_service.save_one(
            job, profile_name, self._confirm_overwrite)
        self._print_save_result(result, include_job_name=True)

    def _show_ports(self):
        ports = list_available_ports()
        if not ports:
            print("  (no COM ports detected)")
            return
        with self._lock:
            share_map = {
                j.serial_port: j for j in self.jobs.values()
                if j.is_running()
            }
        print(f"  {'PORT':<8} {'DESCRIPTION':<30} SHARE")
        for dev, desc in ports:
            job = share_map.get(dev)
            status = (f"shared on tcp:{job.tcp_port}"
                      if job else "not shared")
            desc_short = desc[:30] if desc else ""
            print(f"  {dev:<8} {desc_short:<30} {status}")

    def _show_jobs(self):
        with self._lock:
            jobs = list(self.jobs.values())
        if not jobs:
            print("  (no jobs)")
            return
        print(f"  {'NAME':<20} {'STATUS':<18} {'CLIENTS':<8} DESCRIPTION")
        for j in jobs:
            print(f"  {j.name:<20} {j.status():<18} "
                  f"{j.client_count():<8} {j.description}")

    def _cmd_list(self, line):
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"  syntax error: {e}")
            return

        show_ports = False
        show_jobs = False
        for arg in parts:
            if arg in ("-h", "--help"):
                print(LIST_HELP)
                return
            if arg in ("-p", "--ports"):
                show_ports = True
            elif arg in ("-j", "--jobs"):
                show_jobs = True
            else:
                print(f"  error: unknown argument for 'list': {arg}")
                return

        if show_ports and show_jobs:
            print("  error: 'list -p' and 'list -j' cannot be combined.")
            return

        if show_ports:
            self._show_ports()
        else:
            self._show_jobs()

    def _cmd_share(self, rest):
        try:
            result = parse_share(rest)
        except ShubError as e:
            print(f"  error: {e}")
            return
        if result is None:
            return
        serial_port, tcp_port, cfg = result
        self._start_share(serial_port, tcp_port, cfg)

    def _cmd_save(self, line):
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"  syntax error: {e}")
            return

        cmd = parse_save(parts)
        if cmd.mode == "help":
            print(SAVE_HELP)
            return
        if cmd.mode == "usage":
            print("  usage: save <job> as <profile_name>")
            print("         save <profile_name>")
            print("         save -l <profile_name>")
            print("         save -a [-y]")
            return
        if cmd.mode == "error":
            print(f"  error: {cmd.error}")
            return
        if cmd.mode == "all":
            self._save_all(cmd.auto_yes)
            return
        if cmd.mode == "latest":
            self._save_latest(cmd.profile_name)
            return
        if cmd.mode == "auto":
            self._save_auto(cmd.profile_name)
            return
        if cmd.mode == "one":
            self._save_one(cmd.job_name, cmd.profile_name)
            return

    def _cmd_unshare(self, line):
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"  syntax error: {e}")
            return

        if parts and parts[0] in ("-h", "--help"):
            print(UNSHARE_HELP)
            return
        if len(parts) > 1:
            print("  error: 'unshare' takes at most one argument "
                  "(a COM port).")
            return

        if parts:
            port = parts[0].upper()
            job = self._find_share(port)
            if not job:
                print(f"  error: {port} is not shared")
                return
        else:
            with self._lock:
                jobs = list(self.jobs.values())
            if not jobs:
                print("  error: no jobs are running")
                return
            if len(jobs) > 1:
                print("  error: multiple jobs are running. "
                      "Specify which one:")
                for j in jobs:
                    print(f"    unshare {j.serial_port}")
                print("  Use 'list -j' to see all jobs.")
                return
            job = jobs[0]

        port = job.serial_port
        with self._lock:
            self.jobs.pop(job.name, None)
        job.stop()
        print(f"  unshared {port} (released tcp:{job.tcp_port})")

    def _reject_extra(self, name, rest):
        if rest:
            print(f"  error: '{name}' takes no arguments.")
            return True
        return False

    def _handle(self, line):
        line = line.strip()
        if not line:
            return True

        head = line.split(None, 1)[0].lower()
        rest = line[len(line.split(None, 1)[0]):].strip()

        if head not in VALID_COMMANDS:
            print(f"  error: unknown command '{head}'. "
                  f"Type 'help' for the list of commands.")
            return True

        if head in REQUIRES_ARGS and not rest:
            print(f"  '{head}' requires arguments. "
                  f"Type '{head} -h' for options.")
            return True

        if head in ("exit", "quit"):
            return False

        if head == "help":
            if self._reject_extra("help", rest):
                return True
            print(_banner())
            return True

        if head == "list":
            self._cmd_list(rest)
            return True

        if head == "share":
            self._cmd_share(rest)
            return True

        if head == "unshare":
            self._cmd_unshare(rest)
            return True

        if head == "save":
            self._cmd_save(rest)
            return True

        return True

    def run(self):
        print(_banner())
        while True:
            try:
                line = read_line("shub> ", COMMAND_CYCLE)
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