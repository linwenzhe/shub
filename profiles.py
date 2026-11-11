# 文件名: profiles.py
"""Device profile storage:
- Primary copy always lives under <app_dir>/profiles/ for consistent management.
- shub:save may take an extra path; after writing the primary copy, also copy there.
- shub:load with a path only loads from that path (no fallback).
- shub:load without a path loads the primary copy from profiles/.
- shub:forget / shub:profiles only operate on profiles/.
"""

import json
import os
import sys

PROFILE_EXT = ".json"
PROFILES_DIRNAME = "profiles"


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def profiles_dir():
    """Fixed primary directory: <app_dir>/profiles/."""
    return os.path.join(_app_dir(), PROFILES_DIRNAME)


def _has_sep(name):
    return (
        os.sep in name
        or (os.altsep and os.altsep in name)
        or "/" in name
    )


def _split_name_path(name):
    """Split user input into (basename, extra_full_path or None)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Empty profile name")

    if not _has_sep(name):
        if not name.lower().endswith(PROFILE_EXT):
            name += PROFILE_EXT
        return name, None

    full = os.path.abspath(name)
    base = os.path.basename(full)
    if not base.lower().endswith(PROFILE_EXT):
        base += PROFILE_EXT
        full = full + PROFILE_EXT
    return base, full


def _resolve_main(name):
    """For forget: use basename only, look under profiles/."""
    base, _ = _split_name_path(name)
    return os.path.join(profiles_dir(), base)


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"Profile missing 'type' field: {path}")
    return data


def load_profile(name):
    """Load a profile:
    - With a path: load from that path only; not found = error (no fallback).
    - Without a path: load the primary copy from profiles/.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Empty profile name")

    if _has_sep(name):
        full = os.path.abspath(name)
        if not full.lower().endswith(PROFILE_EXT):
            full = full + PROFILE_EXT
        if not os.path.exists(full):
            raise FileNotFoundError(f"Profile not found: {full}")
        return _read_json(full)

    base = name if name.lower().endswith(PROFILE_EXT) else name + PROFILE_EXT
    main_full = os.path.join(profiles_dir(), base)
    if not os.path.exists(main_full):
        raise FileNotFoundError(f"Profile not found: {main_full}")
    return _read_json(main_full)


def save_profile(name, data):
    """Save profile. Returns (main_full, extra_full)."""
    base, extra_full = _split_name_path(name)
    main_full = os.path.join(profiles_dir(), base)

    os.makedirs(profiles_dir(), exist_ok=True)
    _write_json(main_full, data)

    if extra_full:
        parent = os.path.dirname(extra_full)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _write_json(extra_full, data)

    return main_full, extra_full


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


def delete_profile(name):
    """Delete the primary copy under profiles/. External copies are unaffected."""
    full = _resolve_main(name)
    if os.path.exists(full):
        os.remove(full)
        return True
    return False


def list_profiles():
    """Scan profiles/ for valid .json files; return [(filename, profile)]."""
    d = profiles_dir()
    if not os.path.isdir(d):
        return []
    result = []
    for fname in sorted(os.listdir(d)):
        if not fname.lower().endswith(PROFILE_EXT):
            continue
        full = os.path.join(d, fname)
        try:
            with open(full, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "type" in data:
                result.append((fname, data))
        except Exception:
            continue
    return result