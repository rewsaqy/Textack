# textack/ui/guard.py
"""Terminal-size guard — layar kekecilan = overlay gelap + panduan zoom.

Main loop (opening, siege) panggil wait_until_fit() tiap frame.
Game pause selama overlay tampil; q/ESC = keluar ke menu.
"""

MIN_W = 80
MIN_H = 24


def too_small(h, w, min_w=MIN_W, min_h=MIN_H):
    return w < min_w or h < min_h


def wait_until_fit(stdscr, P, min_w=MIN_W, min_h=MIN_H):
    """Overlay blocking. Return "quit" kalau user tekan q/ESC, else None."""
    import curses
    import time

    stdscr.nodelay(False)
    stdscr.timeout(250)
    while True:
        h, w = stdscr.getmaxyx()
        if not too_small(h, w, min_w, min_h):
            return None
        stdscr.erase()
        cx = w // 2
        lines = [
            "!! JENDELA TERLALU KECIL !!",
            f"butuh >= {min_w}x{min_h}  kini {w}x{h}",
            "gedein jendela, atau zoom out:",
            "  Shift + -  (font kecil)",
            "balikin zoom: Shift + +",
            "q = keluar",
        ]
        top = max(0, h // 2 - len(lines) // 2)
        for i, ln in enumerate(lines):
            ln = ln[: max(0, w - 2)]
            if i == 0:
                attr = P.get("yellow", 0) | curses.A_BOLD
            elif i in (3, 4):
                attr = P.get("cyan", 0)
            else:
                attr = P.get("red", 0)
            try:
                stdscr.addstr(top + i, max(0, cx - len(ln) // 2), ln, attr)
            except curses.error:
                pass
        stdscr.refresh()
        try:
            k = stdscr.getch()
        except curses.error:
            k = -1
        if k in (ord("q"), ord("Q"), 27):
            return "quit"
        time.sleep(0.05)
