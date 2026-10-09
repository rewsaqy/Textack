# textack/ui/fx.py
import curses
import time


def fade_out(stdscr, dur=0.45):
    """Smooth fade out: overlay ░→▒→▓→█ then to black. Fills per row."""
    h, w = stdscr.getmaxyx()
    if h < 3 or w < 10:
        stdscr.erase()
        stdscr.refresh()
        return
    steps = ["░", "▒", "▓", "█"]
    per = dur / max(1, len(steps))
    for ch in steps:
        line = (ch * max(0, w - 1))
        for y in range(h):
            try:
                stdscr.addstr(y, 0, line, curses.A_DIM)
            except curses.error:
                pass
        stdscr.refresh()
        time.sleep(per)
    stdscr.erase()
    stdscr.refresh()
    time.sleep(0.08)


def fade_in_blank(stdscr, dur=0.35):
    """Fade in from black: █→▓→▒→░→transparent."""
    h, w = stdscr.getmaxyx()
    if h < 3 or w < 10:
        return
    steps = ["█", "▓", "▒", "░"]
    per = dur / max(1, len(steps))
    for ch in steps:
        line = (ch * max(0, w - 1))
        for y in range(h):
            try:
                stdscr.addstr(y, 0, line, curses.A_DIM)
            except curses.error:
                pass
        stdscr.refresh()
        time.sleep(per)
    stdscr.erase()
    stdscr.refresh()
