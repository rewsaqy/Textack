# textack/ui/widgets.py
import curses


def safe_add(stdscr, y, x, s, attr=0, size=None):
    """Clip-safe addstr. Pass size=(h, w) to skip a getmaxyx call (perf).

    The game loop fetches (h, w) once per frame and passes it down, turning
    ~80 getmaxyx syscalls per frame into 1.
    """
    if size is None:
        h, w = stdscr.getmaxyx()
    else:
        h, w = size
    if y < 0 or y >= h or not s:
        return
    if x >= w or x + len(s) <= 0:
        return
    if x < 0:
        s = s[-x:]
        x = 0
    if x + len(s) >= w:
        s = s[: w - x - 1]
        if not s:
            return
    try:
        stdscr.addstr(y, x, s, attr)
    except curses.error:
        pass


def get_field(obj, key):
    """Ledger ruling: Upgrade object (u.id) or dict (u['id'])."""
    try:
        return obj[key]
    except TypeError:
        return getattr(obj, key)


def hp_bar_str(cur, disp, total, width):
    total = max(1, total)
    pa = max(0, min(1, cur / total))
    pd = max(0, min(1, disp / total))
    fa = int(width * pa)
    fd = int(width * pd)
    # Build via multiplication, not per-char concatenation.
    out = "#" * fa + "=" * max(0, fd - fa) + "-" * max(0, width - max(fa, fd))
    return f"[{out}] {int(cur)}/{total}"
