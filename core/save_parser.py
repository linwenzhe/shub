# 文件名: core/save_parser.py
"""Parse `save` argument tokens into a SaveCommand.

Pure function, no printing, no REPL dependency.

Grammar:
    save <job> as <profile>
    save <profile>
    save -l <profile>
    save -a [-y]
"""

from dataclasses import dataclass


@dataclass
class SaveCommand:
    mode: str             # "help" / "usage" / "error" /
                          # "one" / "auto" / "latest" / "all"
    job_name: str = ""
    profile_name: str = ""
    auto_yes: bool = False
    error: str = ""


def parse_save(parts):
    """Return a SaveCommand. `parts` is the token list after `save`."""
    if not parts:
        return SaveCommand("usage")

    if parts[0] in ("-h", "--help"):
        return SaveCommand("help")

    if parts[0] == "-a":
        auto_yes = False
        for arg in parts[1:]:
            if arg in ("-y", "--yes"):
                auto_yes = True
            else:
                return SaveCommand(
                    "error",
                    error=f"unexpected argument for '-a': {arg}")
        return SaveCommand("all", auto_yes=auto_yes)

    if parts[0] == "-l":
        if len(parts) < 2:
            return SaveCommand(
                "error",
                error="'-l' requires a profile name. "
                      "Usage: save -l <profile_name>")
        if len(parts) > 2:
            return SaveCommand(
                "error",
                error=f"unexpected argument: {parts[2]}")
        profile = parts[1]
        if profile.startswith("-"):
            return SaveCommand(
                "error",
                error=f"profile name cannot start with '-': {profile}")
        return SaveCommand("latest", profile_name=profile)

    if parts[0] == "-y":
        return SaveCommand(
            "error",
            error="'-y' is only valid with '-a'. Usage: save -a -y")

    if parts[0].startswith("-"):
        return SaveCommand(
            "error", error=f"unknown option for save: {parts[0]}")

    if len(parts) == 1:
        if parts[0] == "as":
            return SaveCommand(
                "error",
                error="'as' is a keyword. "
                      "Usage: save <job> as <profile_name>")
        return SaveCommand("auto", profile_name=parts[0])

    if len(parts) == 3 and parts[1] == "as":
        profile = parts[2]
        if profile.startswith("-"):
            return SaveCommand(
                "error",
                error=f"profile name cannot start with '-': {profile}")
        return SaveCommand(
            "one", job_name=parts[0], profile_name=profile)

    if len(parts) == 2:
        if parts[1] == "-l":
            return SaveCommand(
                "error",
                error="old save syntax is no longer supported. "
                      f"Use 'save -l {parts[0]}' instead.")
        if parts[1] == "-y":
            return SaveCommand(
                "error",
                error="'-y' is only valid with '-a'.")
        return SaveCommand(
            "error",
            error="missing 'as' keyword. "
                  "Usage: save <job> as <profile_name>")

    return SaveCommand("error", error="invalid save syntax.")