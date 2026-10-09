# textack/ui/screens/outro.py
"""Outro screen."""
import curses
import time

from textack import VERSION
from textack.infra.storage import load_best
from textack.ui import fx
from textack.ui.widgets import safe_add


def show(stdscr, P):
    """Exit screen: fade out game -> fade in credits -> fade out. Skippable."""
    stdscr.nodelay(True)
    stdscr.timeout(33)
    fx.fade_out(stdscr, dur=0.45)
    fx.fade_in_blank(stdscr, dur=0.3)
    best = load_best()
    t0 = time.monotonic()
    hold = 2.8
    while True:
        now = time.monotonic()
        h, w = stdscr.getmaxyx()
        size = (h, w)
        cx = w // 2
        t = now - t0
        # any key skips
        if stdscr.getch() != -1 or t >= hold:
            break
        # brightness ramp: dim -> normal -> bold (fake fade-in)
        if t < 0.35:
            attr_main, attr_sub = P["dim"], P["dim"]
        elif t < 0.7:
            attr_main, attr_sub = P["fg"], P["dim"]
        else:
            attr_main, attr_sub = P["cyan"], P["fg"]
        pulse = curses.A_BOLD if (now * 2.5) % 1 < 0.6 else 0
        stdscr.erase()
        safe_add(stdscr, h // 2 - 3, cx - 9, "— SIEGE COMPLETE —", attr_sub, size)
        # main credit with soft glow
        credit = "made by rewsaqy • 2026"
        safe_add(stdscr, h // 2 - 1, cx - len(credit) // 2, credit, attr_main | pulse, size)
        safe_add(stdscr, h // 2, cx - 14, f"TEXTACK v{VERSION} • 100% open source • GPL-3.0", attr_sub, size)
        if best["wave"] > 0:
            safe_add(stdscr, h // 2 + 2, cx - 14, f"best wave {best['wave']} • {best['wpm']:.0f} WPM", P["dim"], size)
        safe_add(stdscr, h - 2, cx - 12, "press any key to skip…", P["dim"], size)
        stdscr.refresh()
        time.sleep(0.033)
    fx.fade_out(stdscr, dur=0.5)
