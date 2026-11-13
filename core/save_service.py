# 文件名: core/save_service.py
"""Pure save logic: Job -> profile JSON.

This module does not print and does not call input(). The caller supplies
a confirm_overwrite callback, so the same logic works in the REPL and in
tests without a terminal.
"""

import os
from dataclasses import dataclass

import profiles as profile_store


@dataclass
class SaveResult:
    status: str                 # "saved" / "skipped" / "failed"
    job_name: str
    path: str = ""
    existed: bool = False
    error: str = ""
    serial_port: str = ""
    tcp_port: int = 0


def job_to_profile(job):
    runner = job.runner
    cfg = runner.cfg
    return {
        "serial_port": runner.serial_port,
        "baudrate": cfg["baudrate"],
        "bytesize": cfg["bytesize"],
        "parity": cfg["parity"],
        "stopbits": cfg["stopbits"],
        "flow": cfg["flow"],
        "tcp_port": runner.tcp_port,
    }


def save_one(job, profile_name, confirm_overwrite):
    try:
        data = job_to_profile(job)
    except Exception as e:
        return SaveResult("failed", job.name, error=str(e))

    try:
        full = profile_store.profile_path(profile_name)
    except Exception as e:
        return SaveResult("failed", job.name, error=str(e))

    existed = os.path.exists(full)
    if existed and not confirm_overwrite(full):
        return SaveResult(
            "skipped", job.name, path=full, existed=True,
            serial_port=data["serial_port"], tcp_port=data["tcp_port"])

    try:
        saved_path, existed = profile_store.save_profile(
            profile_name, data)
    except Exception as e:
        return SaveResult(
            "failed", job.name, error=str(e),
            serial_port=data["serial_port"], tcp_port=data["tcp_port"])

    return SaveResult(
        "saved", job.name, path=saved_path, existed=existed,
        serial_port=data["serial_port"], tcp_port=data["tcp_port"])


def save_all(jobs, auto_yes, confirm_overwrite):
    confirm = (lambda _path: True) if auto_yes else confirm_overwrite
    return [save_one(job, job.name, confirm) for job in jobs]