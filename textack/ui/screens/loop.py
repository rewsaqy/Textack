# textack/ui/screens/loop.py
"""Game loop — verbatim move from main.py:1321-1340 game_loop.

Calls opening.show / howto.show / siege.show / outro.show.
siege.show arrives T7 — lazy import so this module stays importable now;
T7 rewires by providing textack.ui.screens.siege with show(stdscr, P).
"""
import curses

from textack.ui import gfx as gfx_mod
from textack.ui import palette
from textack.ui.screens import howto, opening, outro


def game_loop(stdscr):
    P = palette.init()
    # WAJIB: terjemahkan tombol panah/F-key jadi KEY_*.
    # Tanpa ini, panah = byte ESC+[+huruf dan byte ESC (=27) memicu keluar game.
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    while True:
        try:
            act = opening.show(stdscr, P)
        finally:
            gfx_mod.emit(gfx_mod.build_delete_visible())
        if act == "quit":
            outro.show(stdscr, P)
            return
        if act == "howto":
            nxt = howto.show(stdscr, P)
            if nxt == "menu":
                continue
        # lazy import: siege screen lands in T7
        from textack.ui.screens import siege as siege_mod

        try:
            siege_mod.show(stdscr, P)
        finally:
            gfx_mod.emit(gfx_mod.build_delete_visible())
        # balik ke menu setelah siege keluar (bikin loop nagih)
        continue
