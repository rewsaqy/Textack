# textack/ui/face.py
"""Truecolor-ish half-block faces — works on every curses terminal.

Convert-time: photo -> W×H RGB hex rows (*.rgb.txt, see docs/waifu-custom.md).
Runtime (pure, tested): parse -> downsample to fit -> quantize <=16 colors.
Curses part: allocate color pairs once, draw "▄" cells per frame.
Missing rgb or pair failure -> caller falls back to ASCII art.
"""

PAIR_BASE = 40
PAIR_CAP = 220
MAX_COLORS = 16

from textack.infra.waifu import parse_rgb_text  # noqa: F401  (re-export buat pemakai face)


def fit_cells(nw, nh, max_cols, max_rows):
    """Cell grid keeping aspect (1 cell ~= 2px tall). Min 8x4."""
    if nw <= 0 or nh <= 0:
        return 8, 4
    scale = min(max_cols / nw, (max_rows * 2) / nh)
    cols = max(8, int(nw * scale))
    rows = max(4, int(nh * scale / 2))
    return min(cols, max_cols), min(rows, max_rows)


def downsample(pixels, nw, nh, cols, rows):
    """Box-average to rows×cols cells of (top_rgb, bot_rgb)."""
    cells = []
    for r in range(rows):
        for c in range(cols):
            top = _avg(pixels, nw, nh, c, r, cols, rows, half=0)
            bot = _avg(pixels, nw, nh, c, r, cols, rows, half=1)
            cells.append((top, bot))
    return cells


def _avg(pixels, nw, nh, c, r, cols, rows, half):
    x0, x1 = int(c * nw / cols), max(int(c * nw / cols) + 1, int((c + 1) * nw / cols))
    y0, y1 = int((r * 2 + half) * nh / (rows * 2)), max(int((r * 2 + half) * nh / (rows * 2)) + 1, int((r * 2 + half + 1) * nh / (rows * 2)))
    rs = gs = bs = n = 0
    for y in range(min(y0, nh - 1), min(y1, nh)):
        for x in range(min(x0, nw - 1), min(x1, nw)):
            pr, pg, pb = pixels[y * nw + x]
            rs += pr
            gs += pg
            bs += pb
            n += 1
    return (rs // max(1, n), gs // max(1, n), bs // max(1, n))


def quantize(cells, max_colors=MAX_COLORS):
    """Bucket to <=max_colors palette. Returns (palette, idx_cells)."""
    freq = {}
    for top, bot in cells:
        for p in (top, bot):
            k = (p[0] >> 5, p[1] >> 5, p[2] >> 5)
            freq[k] = freq.get(k, 0) + 1
    top_keys = sorted(freq, key=freq.get, reverse=True)[:max_colors]
    palette = [((k[0] << 5) + 16, (k[1] << 5) + 16, (k[2] << 5) + 16) for k in top_keys]

    def nearest(p):
        best, bd = 0, None
        for i, q in enumerate(palette):
            d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
            if bd is None or d < bd:
                best, bd = i, d
        return best

    key_idx = {k: i for i, k in enumerate(top_keys)}
    idx = []
    for top, bot in cells:
        kt = (top[0] >> 5, top[1] >> 5, top[2] >> 5)
        kb = (bot[0] >> 5, bot[1] >> 5, bot[2] >> 5)
        fi = key_idx.get(kt, nearest(top))
        bi = key_idx.get(kb, nearest(bot))
        idx.append((fi, bi))
    return palette, idx


def pair_combos(idx, cap=PAIR_CAP):
    """Unique (fg,bg) combos, most frequent first, capped."""
    freq = {}
    for combo in idx:
        freq[combo] = freq.get(combo, 0) + 1
    return sorted(freq, key=freq.get, reverse=True)[:cap]


def _xterm256():
    table = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229), (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0), (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
    for r in range(6):
        for g in range(6):
            for b in range(6):
                table.append((r * 51 if r else 0, g * 51 if g else 0, b * 51 if b else 0))
    for v in range(24):
        lv = 8 + v * 10
        table.append((lv, lv, lv))
    return table


def alloc_pairs(palette, combos):
    """Allocate curses pairs. Returns {(fg,bi): pair_no} or None on failure."""
    import curses

    try:
        ncols = getattr(curses, "COLORS", 8) or 8
        can_change = curses.can_change_color()
        conv = []
        if can_change and ncols >= 256:
            for i, (r, g, b) in enumerate(palette):
                curses.init_color(16 + i, r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
                conv.append(16 + i)
        else:
            table = _xterm256()
            for r, g, b in palette:
                best, bd = 0, None
                for j, q in enumerate(table[: max(16, min(ncols, 256))]):
                    d = (r - q[0]) ** 2 + (g - q[1]) ** 2 + (b - q[2]) ** 2
                    if bd is None or d < bd:
                        best, bd = j, d
                conv.append(best)
        pairmap = {}
        for n, (fi, bi) in enumerate(combos):
            pn = PAIR_BASE + n
            curses.init_pair(pn, conv[fi], conv[bi])
            pairmap[(fi, bi)] = curses.color_pair(pn)
        return pairmap
    except curses.error:
        return None


def draw(stdscr, y, x, cols, idx, pairmap, fallback_attr=0):
    """Draw half-block face. Cells missing from pairmap use fallback."""
    from textack.ui.widgets import safe_add

    for pos, (fi, bi) in enumerate(idx):
        r, c = divmod(pos, cols)
        attr = pairmap.get((fi, bi), fallback_attr)
        ch = " " if fi == bi else "▄"
        safe_add(stdscr, y + r, x + c, ch, attr)
