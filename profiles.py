# 文件名: profiles.py
"""Read and write JSON profiles under profiles/.

A profile describes a single shared COM port. serial_port is required;
tcp_port is optional (omit it to let shub pick a free port). The rest
fall back to defaults from config/.

Profile names are file-name only: no path separators, no "..", no
absolute paths. The final path is additionally checked to stay under
profiles/ after resolving symlinks and "..".

All failures raise ProfileError.
"""

import json
import os
import sys

from core.errors import ProfileError

PROFILE_EXT = ".json"
PROFILES_DIRNAME = "profiles"


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def profiles_dir():
    return os.path.join(_app_dir(), PROFILES_DIRNAME)


def _reject_path_components(name):
    if not name:
        raise ProfileError("Empty profile name")
    if "/" in name or "\\" in name:
        raise ProfileError(
            f"Invalid profile name: {name!r}. "
            "Path separators are not allowed.")
    if ".." in name:
        raise ProfileError(
            f"Invalid profile name: {name!r}. "
            "'..' is not allowed.")
    if os.path.isabs(name):
        raise ProfileError(
            f"Invalid profile name: {name!r}. "
            "Absolute paths are not allowed.")


def _ensure_under_profiles(full):
    base = os.path.realpath(profiles_dir())
    resolved = os.path.realpath(full)
    if not (resolved == base or resolved.startswith(base + os.sep)):
        raise ProfileError(
            f"Path escapes profiles directory: {full}")
    return resolved


def profile_path(name):
    name = (name or "").strip()
    _reject_path_components(name)

    if not name.lower().endswith(PROFILE_EXT):
        name += PROFILE_EXT

    full = os.path.join(profiles_dir(), name)
    return _ensure_under_profiles(full)


def load_profile(name):
    full = profile_path(name)
    if not os.path.exists(full):
        raise ProfileError(f"Profile not found: {full}")

    try:
        with open(full, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ProfileError(f"Invalid JSON in {full}: {e}")
    except UnicodeError as e:
        raise ProfileError(
            f"Profile is not valid UTF-8: {full}: {e}")
    except OSError as e:
        raise ProfileError(f"Cannot read {full}: {e}")

    if not isinstance(data, dict):
        raise ProfileError(f"Profile must be a JSON object: {full}")
    return data


def save_profile(name, data):
    full = profile_path(name)
    os.makedirs(profiles_dir(), exist_ok=True)
    existed = os.path.exists(full)
    try:
        with open(full, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        raise ProfileError(f"Cannot write {full}: {e}")
    return full, existed


def require_fields(data, *fields):
    for f in fields:
        if f not in data or data[f] in (None, ""):
            raise ProfileError(f"Profile missing required field: {f}")