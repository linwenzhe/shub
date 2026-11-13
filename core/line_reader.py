# 文件名: core/line_reader.py
"""Read a line with up/down cycling through a fixed command list.

On Windows, msvcrt.getwch() is used to catch arrow keys. On other
platforms, plain input() is used (no cycling).

The cycle is over the command list in order. Down moves forward and wraps;
Up moves backward and wraps. There is no history of past input.

Typing any non-arrow character exits cycle mode, allowing free editing.

If `commands` is empty, read_line falls back to plain input().
"""

import sys

try:
    import msvcrt
    _HAS_MSVCRT = True
except ImportError:
    _HAS_MSVCRT = False


def _display_width(s):
    width = 0
    for ch in s:
        width += 2 if ord(ch) > 0x7F else 1
    return width


def read_line(prompt, commands):
    if not _HAS_MSVCRT or not commands:
        return input(prompt)

    sys.stdout.write(prompt)
    sys.stdout.flush()
    buf = []
    cyc_idx = -1

    while True:
        ch = msvcrt.getwch()

        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(buf)

        if ch == "\x08":
            if buf:
                last = buf.pop()
                w = _display_width(last)
                sys.stdout.write("\b \b" * w)
                sys.stdout.flush()
            cyc_idx = -1
            continue

        if ch == "\x03":
            raise KeyboardInterrupt

        if ch in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            if key == "H":
                if cyc_idx == -1:
                    cyc_idx = len(commands) - 1
                else:
                    cyc_idx = (cyc_idx - 1) % len(commands)
                _replace(prompt, buf, commands[cyc_idx])
                buf = list(commands[cyc_idx])
            elif key == "P":
                if cyc_idx == -1:
                    cyc_idx = 0
                else:
                    cyc_idx = (cyc_idx + 1) % len(commands)
                _replace(prompt, buf, commands[cyc_idx])
                buf = list(commands[cyc_idx])
            continue

        buf.append(ch)
        sys.stdout.write(ch)
        sys.stdout.flush()
        cyc_idx = -1


def _replace(prompt, old_buf, new_text):
    total_width = _display_width(prompt) + _display_width("".join(old_buf))
    sys.stdout.write("\r" + " " * total_width + "\r")
    sys.stdout.write(prompt + new_text)
    sys.stdout.flush()