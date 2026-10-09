# textack/ui/palette.py
import curses


def init():
    """Modern Tokyonight-ish palette. Falls back to 8 colors on old terminals."""
    P = {}
    try:
        curses.start_color()
        curses.use_default_colors()
    except curses.error:
        pass
    colors = getattr(curses, "COLORS", 8) or 8
    try:
        if colors >= 256:
            # Pair ids 10+ to avoid collisions.
            def mk(i, fg):
                try:
                    curses.init_pair(i, fg, -1)
                except curses.error:
                    pass
            mk(10, 189)  # fg lavender-white
            mk(11, 75)   # cyan 7dcfff
            mk(12, 141)  # magenta bb9af7
            mk(13, 150)  # green 9ece6a
            mk(14, 221)  # yellow e0af68
            mk(15, 204)  # red f7768e
            mk(16, 240)  # dim gray
            mk(17, 81)   # bright cyan
            try:
                P["fg"] = curses.color_pair(10)
                P["cyan"] = curses.color_pair(11) | curses.A_BOLD
                P["magenta"] = curses.color_pair(12) | curses.A_BOLD
                P["green"] = curses.color_pair(13) | curses.A_BOLD
                P["yellow"] = curses.color_pair(14) | curses.A_BOLD
                P["red"] = curses.color_pair(15) | curses.A_BOLD
                P["dim"] = curses.color_pair(16) | curses.A_DIM
                P["cyan_dim"] = curses.color_pair(11) | curses.A_DIM
                P["flash"] = curses.color_pair(10) | curses.A_REVERSE
            except curses.error:
                pass
        else:
            raise ValueError("basic")
    except Exception:  # noqa: BLE001, S110
        pass
    if not P:
        try:
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_CYAN, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        except curses.error:
            pass
        P = {
            "fg": curses.A_NORMAL, "cyan": curses.color_pair(4) | curses.A_BOLD,
            "magenta": curses.color_pair(5) | curses.A_BOLD,
            "green": curses.color_pair(1) | curses.A_BOLD,
            "yellow": curses.color_pair(3) | curses.A_BOLD,
            "red": curses.color_pair(2) | curses.A_BOLD,
            "dim": curses.A_DIM, "cyan_dim": curses.color_pair(4) | curses.A_DIM,
            "flash": curses.A_REVERSE,
        }
    return P
