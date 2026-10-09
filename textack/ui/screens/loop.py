# textack/ui/screens/loop.py
"""Game loop.

Calls opening.show / howto.show / siege.show / outro.show.
"""
import curses

from textack.ui import gfx as gfx_mod
from textack.ui import palette
from textack.ui.screens import howto, opening, outro


def game_loop(stdscr):
    P = palette.init()
    # REQUIRED: translate arrow/F-keys into KEY_* codes.
    # Without this, arrows arrive as ESC+[+letter bytes and the ESC byte
    # (=27) would quit the game.
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
        # lazy import keeps this module importable without curses running
        from textack.ui.screens import siege as siege_mod

        try:
            siege_mod.show(stdscr, P)
        finally:
            gfx_mod.emit(gfx_mod.build_delete_visible())
        # back to menu after siege exits (keeps the loop addictive)
        continue
