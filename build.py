# 文件名: build.py
"""Build a single-file shub executable with PyInstaller.

Usage:
    pip install pyinstaller
    python build.py

Output: dist/shub.exe (Windows) or dist/shub (Linux/macOS).
"""

import os
import sys

try:
    import PyInstaller.__main__
except ImportError:
    print("PyInstaller is not installed. Run: pip install pyinstaller")
    sys.exit(1)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    sep = ";" if os.name == "nt" else ":"

    PyInstaller.__main__.run([
        os.path.join(here, "main.py"),
        "--onefile",
        "--name", "shub",
        "--add-data",
        f"{os.path.join(here, 'profiles')}{sep}profiles",
        "--add-data",
        f"{os.path.join(here, 'docs')}{sep}docs",
        "--clean",
        "--noconfirm",
    ])


if __name__ == "__main__":
    main()