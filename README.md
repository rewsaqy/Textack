# Textack v1.0.00

> Side project just for fun — have fun!

100% open source Linux terminal game. **Typing = damage.**

Type Linux commands as fast as you can + Enter to attack the enemy fortress.
Faster and more accurate = bigger damage. Typos = counterattack.

Also an educational game: trains typing speed + Linux command memory.

## Run

```bash
python3 main.py
# or
python3 -m textack
```

Only standard Python 3, no extra installs. Runs natively in a Linux terminal.

### Install so you can just type `textack` (Linux)

```bash
uv tool install -e .
# then from anywhere:
textack
```

Classic alternative:

```bash
pip install -e .
textack
```

### Windows — works, with 1 extra step

This game uses `curses`. On Linux/macOS it ships with Python.
On Windows you need `windows-curses` (auto-installed via pip):

```powershell
pip install -e .
textack
# or: pip install -e .[windows]  (same thing, explicit)
```

Windows notes:
- Run in Windows Terminal / PowerShell / CMD (not an IDE output panel).
- `.wav` sounds play via PowerShell `System.Media.SoundPlayer`; missing files = silence (no crash).
- Save data in `%LOCALAPPDATA%\textack\best.txt`, waifu config in `%APPDATA%\textack\waifu.txt`.
- On Linux: `~/.cache/textack/best.txt` and `~/.config/textack/waifu.txt`.

## Dev

```bash
pip install -e .[dev]
python3 -m pytest -q
python3 -m ruff check textack tests
```

CI (`.github/workflows/ci.yml`) runs on Python 3.9–3.13: pytest + ruff + compileall.
Code layout: `textack/core/` (pure logic) → `textack/ui/` (curses) → `textack/infra/` (storage/sound/art).
Details: `docs/ARCHITECTURE.md`.

## How to play
- A target word appears, e.g. `sudo apt update`
- Type it exactly + Enter
- Chained combos = critical damage
- Typos = counterattack. Idling too long = chip damage.
- Every hit = XP. Level up = pick 1 of 3 upgrades (14 kinds):
  ATTACK / DEFENSE / SPEED / BASE, Survivor.io style.
- Enemies per wave: SCOUT → RAIDER → GOLEM → OVERLORD, BOSS every 5 waves.
- Waifu operator AIKA in the right panel (terminal ≥102 columns).
  Change art: edit `waifu.txt` or `~/.config/textack/waifu.txt`.
- RIN (wave 4) & SORA (wave 8) auto-unlock — switch operators
  with ◄ ► in the menu. Each operator has English dialog + bond level
  (raised by perfect hits/combos). Custom art from your photo: `docs/waifu-custom.md`.
- Minimum terminal 80×24 — if smaller, the game pauses + shows
  zoom guidance (`Shift + -` zoom out, `Shift + +` back).
- Layered visuals: real photo (Ghostty/WezTerm/kitty, check
  `textack --gfx-test`) → colored face → ASCII. Details:
  `docs/waifu-custom.md`.
- Sound: `sfx/*.wav` via paplay/aplay/mpv (beep fallback, F3 on/off) — drop any `.wav` files you like into `sfx/` (missing = silence, no crash).
- `:q` to quit

## Contribute

Want to add words, upgrades, or enemies? Under 10 lines —
see `CONTRIBUTING.md` (5-minute quickstart) and
`docs/adding-content.md` (3 copy-paste recipes).
Short architecture: `docs/ARCHITECTURE.md`.
Good first issues: new words, enemy rebalance, new upgrades.

## Roadmap
1. [x] MVP single-player vs fortress (this)
2. [ ] Local score + leaderboard
3. [ ] Co-op / PvP online via websocket
4. [ ] Optional C engine if performance demands

## License
GPL-3.0-or-later. See `LICENSE`. Free to use, modify, distribute.

---
*THIS PHOTO IS ONLY A PLACEHOLDER*
