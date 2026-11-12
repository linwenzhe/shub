# 文件名: profiles.py
"""Read-only loader for hand-written JSON profiles under profiles/.

All failures raise ProfileError so the REPL can catch one exception type.
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


def load_profile(name):
    name = (name or "").strip()
    if not name:
        raise ProfileError("Empty profile name")
    if not name.lower().endswith(PROFILE_EXT):
        name += PROFILE_EXT
    full = os.path.join(profiles_dir(), name)
    if not os.path.exists(full):
        raise ProfileError(f"Profile not found: {full}")

    try:
        with open(full, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ProfileError(f"Invalid JSON in {full}: {e}")
    except OSError as e:
        raise ProfileError(f"Cannot read {full}: {e}")

    if not isinstance(data, dict):
        raise ProfileError(f"Profile must be a JSON object: {full}")
    if "type" not in data:
        raise ProfileError(f"Profile missing 'type' field: {full}")
    if data["type"] not in ("serve", "connect"):
        raise ProfileError(f"Unknown profile type '{data['type']}' in {full}")
    return data


def require_fields(data, *fields):
    for f in fields:
        if f not in data or data[f] in (None, ""):
            raise ProfileError(f"Profile missing required field: {f}")


def password_from_profile(data):
    """Return None if no_password is true, else the password (or default)."""
    if data.get("no_password"):
        return None
    from config import DEFAULT_PASSWORD
    return str(data.get("password", DEFAULT_PASSWORD))