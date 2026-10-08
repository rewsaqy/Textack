#!/usr/bin/env python3
# main.py — thin shim, keep executable.
# Dibikin tahan symlink: kalau dijalankan via ~/.local/bin/textack
# (symlink ke sini), sys.path[0] bisa nyasar ke ~/.local/bin.
# Jadi paksa project root (folder yang berisi textack/) masuk sys.path.
import os
import sys

try:
    _root = os.path.dirname(os.path.realpath(__file__))
    if _root not in sys.path:
        sys.path.insert(0, _root)
except Exception:
    pass

from textack.__main__ import main

if __name__ == "__main__":
    main()
