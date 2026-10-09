#!/usr/bin/env python3
# main.py — thin shim, keep executable.
# Symlink-safe: when run via ~/.local/bin/textack
# (a symlink to this file), sys.path[0] may point at ~/.local/bin.
# So force the project root (the folder containing textack/) onto sys.path.
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
