# 文件名: input_helper.py
"""行输入：Windows 下用 msvcrt 逐键读取，支持上下键历史；其他平台回退 input()。"""

import sys

try:
    import msvcrt
    _HAS_MSVCRT = True
except ImportError:
    _HAS_MSVCRT = False


def read_line(prompt, history, history_max=100):
    if not _HAS_MSVCRT:
        line = input(prompt)
        _remember(history, line, history_max)
        return line

    sys.stdout.write(prompt)
    sys.stdout.flush()
    buf = []
    hist_idx = len(history)

    while True:
        ch = msvcrt.getwch()

        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            line = "".join(buf)
            _remember(history, line, history_max)
            return line

        if ch == "\x08":
            if buf:
                buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue

        if ch == "\x03":
            raise KeyboardInterrupt

        if ch in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            if key == "H":
                if history and hist_idx > 0:
                    hist_idx -= 1
                    _replace(prompt, buf, history[hist_idx])
                    buf = list(history[hist_idx])
            elif key == "P":
                if hist_idx < len(history) - 1:
                    hist_idx += 1
                    _replace(prompt, buf, history[hist_idx])
                    buf = list(history[hist_idx])
                elif hist_idx == len(history) - 1:
                    hist_idx = len(history)
                    _replace(prompt, buf, "")
                    buf = []
            continue

        buf.append(ch)
        sys.stdout.write(ch)
        sys.stdout.flush()


def _remember(history, line, history_max):
    if not line.strip():
        return
    history.append(line)
    while len(history) > history_max:
        history.pop(0)


def _replace(prompt, old_buf, new_text):
    sys.stdout.write("\r" + " " * (len(prompt) + len(old_buf)) + "\r")
    sys.stdout.write(prompt + new_text)
    sys.stdout.flush()