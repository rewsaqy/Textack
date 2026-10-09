# textack/ui/screens/howto.py
"""Howto screen."""
from textack.ui.widgets import safe_add


def show(stdscr, P):
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        h, w = stdscr.getmaxyx()
        size = (h, w)
        stdscr.erase()
        lines = [
            "HOW TO PLAY — ready in 30 seconds",
            "",
            "1. A word appears above the enemy fortress, e.g.: sudo apt update",
            "2. Type it EXACTLY + Enter as fast as you can = shot ▲",
            "3. Faster = bigger damage. Streaks = COMBO crits.",
            "4. A typo = the enemy counterattacks your fortress.",
            "5. Idling too long = chip damage. Don't go AFK.",
            "6. Every hit = XP. LEVEL UP = pick 1 of 3 UPGRADES",
            "   ATTACK / DEFENSE / SPEED / BASE (14 kinds, Survivor.io style).",
            "7. Enemies rotate per wave: SCOUT→RAIDER→GOLEM→OVERLORD→BOSS.",
            "   Higher waves: faster intervals + burst x1-x4.",
            "",
            "RANK: NEWBIE → SCRIPT KIDDIE → SYSADMIN → ROOT → KERNEL PANIC",
            "LEARN: every word is a real Linux command. Play more, memorize more.",
            "",
            "[Enter] start siege   [Q] back",
        ]
        y0 = max(1, h // 2 - len(lines) // 2)
        for i, ln in enumerate(lines):
            a = P["cyan"] if i == 0 else (P["dim"] if i >= 8 else P["fg"])
            safe_add(stdscr, y0 + i, max(2, w // 2 - 32), ln[: w - 4], a, size)
        stdscr.refresh()
        k = stdscr.getch()
        if k in (10, 13):
            return "play"
        if k in (ord("q"), ord("Q"), 27):
            return "menu"
