# textack/ui/screens/upgrade.py
"""Upgrade overlay.

Supports both Upgrade objects (roll_choices) and dicts via get_field helper.
"""
import curses
import time

from textack.ui.widgets import get_field, safe_add


def show(stdscr, P, choices, level, owned):
    """Pause the game, show 3 upgrade cards with slide+glow. Returns index."""
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    sel = 0
    t0 = time.monotonic()
    # Slide-in animation: starting offset.
    while True:
        now = time.monotonic()
        t = now - t0
        h, w = stdscr.getmaxyx()
        size = (h, w)
        cx = w // 2
        # input
        stdscr.nodelay(True)
        stdscr.timeout(33)
        key = stdscr.getch()
        # drain all
        while key != -1:
            if key in (curses.KEY_LEFT, ord("h"), ord("a")):
                sel = (sel - 1) % len(choices)
            elif key in (curses.KEY_RIGHT, ord("l"), ord("d")):
                sel = (sel + 1) % len(choices)
            elif key in (curses.KEY_UP, ord("k")):
                sel = (sel - 1) % len(choices)
            elif key in (curses.KEY_DOWN, ord("j")):
                sel = (sel + 1) % len(choices)
            elif key in (ord("1"), ord("2"), ord("3")):
                idx = key - ord("1")
                if 0 <= idx < len(choices):
                    stdscr.nodelay(True)
                    stdscr.timeout(33)
                    return idx
            elif key in (10, 13, ord(" ")):
                stdscr.nodelay(True)
                stdscr.timeout(33)
                return sel
            key = stdscr.getch()

        stdscr.erase()
        # dark backdrop + pulsing title
        pulse = curses.A_BOLD if (now * 3) % 1 < 0.6 else 0
        safe_add(stdscr, max(1, h // 2 - 9), cx - 12, f"✦ LEVEL {level} UP! PICK AN UPGRADE ✦", P["yellow"] | pulse, size)
        safe_add(stdscr, max(1, h // 2 - 8), cx - 20, "base keeps getting stronger while you attack  •  1/2/3 or ←→ + Enter", P["dim"], size)

        # Card layout: horizontal when wide, vertical when narrow.
        wide = w >= 90
        cw, ch = (24, 9) if wide else (min(52, w - 6), 7)
        # smooth slide-in: offset shrinks over time
        slide = max(0, int(12 - t * 30))
        for i, u in enumerate(choices):
            lv = owned.get(get_field(u, "id"), 0)
            if wide:
                bx = cx + (i - 1) * (cw + 3) - cw // 2
                by = h // 2 - 5 + (slide if i == 1 else slide // 2)
            else:
                bx = cx - cw // 2
                by = h // 2 - 5 + i * (ch + 1) + slide
            is_sel = (i == sel)
            border_attr = (P["cyan"] | pulse) if is_sel else P["dim"]
            fill_attr = P["fg"] if is_sel else P["dim"]
            # card border
            top = "┏" + "━" * (cw - 2) + "┓"
            bot = "┗" + "━" * (cw - 2) + "┛"
            safe_add(stdscr, by, bx, top, border_attr, size)
            for r in range(1, ch - 1):
                safe_add(stdscr, by + r, bx, "┃", border_attr, size)
                safe_add(stdscr, by + r, bx + cw - 1, "┃", border_attr, size)
            safe_add(stdscr, by + ch - 1, bx, bot, border_attr, size)
            # card body
            cat_col = {"ATTACK": P["red"], "DEFENSE": P["green"], "SPEED": P["cyan"], "BASE": P["magenta"]}.get(get_field(u, "cat"), P["fg"])
            safe_add(stdscr, by + 1, bx + 2, f"{get_field(u, 'icon')} [{get_field(u, 'cat')}]", cat_col, size)
            safe_add(stdscr, by + 2, bx + 2, f"{i+1}. {get_field(u, 'name')}"[: cw - 4], P["cyan"] | curses.A_BOLD if is_sel else P["fg"], size)
            safe_add(stdscr, by + 3, bx + 2, get_field(u, "desc")[: cw - 4], fill_attr, size)
            safe_add(stdscr, by + 4, bx + 2, f"Lv {lv} → {lv+1}/{get_field(u, 'max')}", P["yellow"] if is_sel else P["dim"], size)
            if wide:
                safe_add(stdscr, by + 5, bx + 2, "ENTER to take", P["dim"], size)
        stdscr.refresh()
        time.sleep(0.033)
