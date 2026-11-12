# 文件名: main.py
"""shub entry: always enters the interactive shell.

Run `python main.py` (or `shub.exe`) to get a `shub>` prompt. All
commands are typed there; there is no one-shot CLI mode.
"""

import sys

from core.repl import Repl


def main():
    try:
        Repl().run()
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()