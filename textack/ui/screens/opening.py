# textack/ui/screens/opening.py
"""Opening screen: boot cinematic + menu."""
import curses
import os
import random
import sys
import time

from textack import VERSION
from textack.core import story
from textack.core.progression import rank_for
from textack.infra import storage as storage_mod
from textack.infra import waifu as waifu_mod
from textack.infra.storage import load_best
from textack.ui import gfx, guard
from textack.ui.widgets import safe_add

LOGO_SMALL = [
    "▀█▀ █▀▀ ▀▄▀ ▀█▀ ▄▀█ █▀▀ █▄▀",
    " █  ██▄ █ █  █  █▀█ █▄▄ █ █",
]
TAGLINE = "typing = damage  //  siege the fortress"


def show(stdscr, P):
    """Boot cinematic + menu. Returns 'play' / 'howto' / 'quit'. 60fps, any key skips."""
    h, w = stdscr.getmaxyx()
    best = load_best()
    wstate = storage_mod.load_waifu()
    unlocked = [u for u in story.WAIFU_ORDER if u in (wstate.get("unlocked") or ["aika"])] or ["aika"]
    try:
        sel_w = unlocked.index(story.resolve_active(None, None, wstate))
    except ValueError:
        sel_w = 0
    gfx_mode = gfx.resolve(sys.argv[1:], os.environ)
    portrait_sent_for = None

    def _send_portrait(wid):
        pp = waifu_mod.find_photo(wid)
        if not pp:
            return False
        data = gfx.png_bytes_for(pp)
        if not data:
            return False
        for seq in gfx.build_transmit(data, 20):
            gfx.emit(seq)
        return True
    t0 = time.monotonic()
    boot_dur = 2.2
    logs = [
        "$ textack --boot --native",
        "✔ kernel link ok",
        "✔ fortress loaded",
        "✔ keymap id-qwerty ready",
        "✔ 60fps renderer ready",
    ]
    menu = ["▶  Siege Fortress  (Enter)", "How to play  (H)", "Quit  (Q)"]
    sel = 0
    sel_y = 0.0
    phase = "boot"  # boot -> menu
    last = time.monotonic()

    # light starfield for the menu (max 40, adaptive)
    nstar = min(40, max(10, (w * h) // 80))
    stars = [{"x": random.random() * w, "y": random.random() * h, "sp": random.uniform(3, 12)} for _ in range(nstar)]

    stdscr.nodelay(True)
    stdscr.timeout(33)

    while True:
        now = time.monotonic()
        dt = min(0.05, now - last)
        last = now
        h, w = stdscr.getmaxyx()
        size = (h, w)
        cx = w // 2
        if guard.too_small(h, w):
            if guard.wait_until_fit(stdscr, P) == "quit":
                return "quit"
            stdscr.nodelay(True)
            stdscr.timeout(33)
            last = time.monotonic()
            continue
        t = now - t0

        # input
        key = stdscr.getch()
        while key != -1:
            if phase == "boot":
                # any key -> skip to menu
                phase = "menu"
                break
            else:
                if key in (curses.KEY_UP, ord("k")):
                    sel = (sel - 1) % len(menu)
                elif key in (curses.KEY_DOWN, ord("j")):
                    sel = (sel + 1) % len(menu)
                elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                    d = -1 if key == curses.KEY_LEFT else 1
                    sel_w = (sel_w + d) % len(unlocked)
                    wstate["active"] = unlocked[sel_w]
                    storage_mod.save_waifu(storage_mod.DEFAULT_WAIFU, wstate)
                elif key in (10, 13):  # enter
                    return ["play", "howto", "quit"][sel]
                elif key in (ord("h"), ord("H")):
                    return "howto"
                elif key in (ord("q"), ord("Q"), 27):
                    return "quit"
            key = stdscr.getch()

        if phase == "boot" and t >= boot_dur:
            phase = "menu"

        # update starfield + smooth selection (lerp)
        for s in stars:
            s["x"] -= s["sp"] * dt
            if s["x"] < 0:
                s["x"] += w
                s["y"] = random.random() * h
        sel_y += (sel - sel_y) * min(1, dt * 12)
        _pgeom = None

        stdscr.erase()
        # agent-style top bar
        safe_add(stdscr, 0, 2, "● TEXTACK v" + VERSION, P["green"], size)
        safe_add(stdscr, 0, max(0, w - 26), "linux native • 60fps", P["dim"], size)
        safe_add(stdscr, 1, 0, "─" * max(0, w - 1), P["dim"], size)

        for s in stars:
            safe_add(stdscr, int(s["y"]), int(s["x"]), ".", P["cyan_dim"], size)

        if phase == "boot":
            prog = min(1.0, t / boot_dur)
            # logo shimmer: per-letter reveal
            ly = h // 2 - 4
            reveal = int(len(LOGO_SMALL[0]) * min(1, t / 1.4))
            grad = [P["cyan"], P["magenta"], P["green"], P["yellow"]]
            for r, line in enumerate(LOGO_SMALL):
                vis = line[:reveal]
                safe_add(stdscr, ly + r, cx - len(line) // 2, vis, grad[r % len(grad)], size)
            safe_add(stdscr, ly + 2, cx - len(TAGLINE) // 2, TAGLINE[: int(len(TAGLINE) * min(1, t / 1.8))], P["dim"], size)
            # fast-typing logs
            by = ly + 4
            nlogs = min(len(logs), int(t / 0.3) + 1)
            for i in range(nlogs):
                safe_add(stdscr, by + i, cx - 16, logs[i][: w - 4], P["fg"] if i == 0 else P["dim"], size)
            # smooth progress bar
            bw = min(40, w - 10)
            fill = int(bw * prog)
            # pulse at bar tip
            pulse = "━" if (now * 6) % 1 < 0.5 else "─"
            safe_add(stdscr, by + nlogs + 1, cx - bw // 2, "[" + "━" * fill + pulse + " " * max(0, bw - fill - 1) + f"] {int(prog*100)}%", P["cyan"], size)
            safe_add(stdscr, h - 2, cx - 14, "press any key to skip…", P["dim"], size)
        else:
            ly = h // 2 - 7
            grad = [P["cyan"], P["magenta"], P["green"], P["yellow"]]
            for r, line in enumerate(LOGO_SMALL):
                # soft glow: oscillating brightness
                glow = curses.A_BOLD if (now * 2 + r) % 2 < 1.2 else 0
                # per-column gradient
                x0 = cx - len(line) // 2
                for ci, ch in enumerate(line):
                    if ch == " ":
                        continue
                    a = grad[(ci // 6 + r) % len(grad)] | glow
                    safe_add(stdscr, ly + r, x0 + ci, ch, a, size)
            safe_add(stdscr, ly + 2, cx - len(TAGLINE) // 2, TAGLINE, P["dim"], size)
            # best + rank (keeps it addictive)
            if best["wave"] > 0:
                safe_add(stdscr, ly + 4, cx - 20, f"BEST wave {best['wave']} • {best['wpm']:.0f} WPM • {rank_for(best['wpm'], 5)}", P["yellow"], size)
            else:
                safe_add(stdscr, ly + 4, cx - 20, "no record yet — be the first legend", P["dim"], size)
            # menu with smooth sliding highlight
            my = ly + 6
            for i, item in enumerate(menu):
                y = my + i * 2
                x = cx - 16
                if abs(sel_y - i) < 0.6:
                    # selection bar (selected row always highlighted)
                    safe_add(stdscr, y, x - 2, "━" * 34, P["cyan_dim"], size)
                    safe_add(stdscr, y, x, item, P["cyan"] | curses.A_REVERSE, size)
                else:
                    safe_add(stdscr, y, x, "  " + item.replace("▶  ", ""), P["dim"] if i != sel else P["fg"], size)
            # smooth arrow selector (interpolated position)
            safe_add(stdscr, int(my + sel_y * 2), cx - 19, "▶", P["green"], size)
            # operator picker (phase 2: side-quest + chat plug here)
            _wid = unlocked[sel_w]
            _w = story.get_waifu(_wid)
            _bond = float((wstate.get("bond") or {}).get(_wid, 0.0))
            _op = f"Operator: {_w['name']} · {_w['title']} ♡{story.level_for(_bond)}  ({sel_w + 1}/{len(unlocked)} ◄ ►)"
            safe_add(stdscr, my + 7, cx - len(_op) // 2, _op, P["yellow"], size)
            _pgeom = None
            if gfx_mode == "kitty" and w >= 110 and _wid != portrait_sent_for:
                portrait_sent_for = _wid if _send_portrait(_wid) else None
            if gfx_mode == "kitty" and w >= 110 and portrait_sent_for:
                _pgeom = (ly + 1, cx + 22, 22, 11)
            # addictive footer
            pulse_on = (now * 2.2) % 1 < 0.65
            hint = "ENTER start  •  ↑↓ select  •  combo = crit" if pulse_on else "one more word… don't drop the combo"
            safe_add(stdscr, h - 3, cx - len(hint) // 2, hint, P["magenta"], size)
            safe_add(stdscr, h - 2, 2, "GPL-3.0 • stdlib only • :q quits anytime", P["dim"], size)

        stdscr.refresh()
        if _pgeom and portrait_sent_for:
            _py, _pxx, _pc, _pr = _pgeom
            gfx.place_at(_py, _pxx, gfx.build_place(20, 2, _pc, _pr))
        elif portrait_sent_for:
            gfx.emit(gfx.build_delete_image(20))
            portrait_sent_for = None
