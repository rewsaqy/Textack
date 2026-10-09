# Textack v1.0.00

> Side project just for fun — have fun!

100% open-source terminal game. **Typing = damage.**

Type Linux commands as fast as you can + Enter to attack the enemy fortress.
Faster and more accurate = bigger damage. Typos = counterattack.

It is also an educational game: it trains typing speed + Linux command memory.

## Requirements

- Python 3.9+ (tested on 3.9–3.13)
- A real terminal, minimum **80×24** (operator panel needs **≥102 columns**)
- Zero runtime dependencies on Linux/macOS (stdlib + `curses` only)

## Quick start

```bash
python3 main.py
# or
python3 -m textack
```

No install step needed — clone and run.

## Install (Linux)

Run `textack` from anywhere:

```bash
# Option A — isolated tool install (recommended if you use uv)
uv tool install -e .
textack

# Option B — classic pip
pip install -e .
textack
```

Save data on Linux:

- Best score: `~/.cache/textack/best.txt` (`$XDG_CACHE_HOME` respected)
- Operator state: `~/.cache/textack/waifu.json`
- Custom art: `~/.config/textack/waifu.txt` (`$XDG_CONFIG_HOME` respected)

## Install (Windows)

The game uses `curses`. On Windows it needs `windows-curses`, which pip
installs automatically as a dependency:

```powershell
# In Windows Terminal, PowerShell, or CMD (not an IDE output panel):
pip install -e .
textack

# Explicit variant (same thing):
pip install -e .[windows]
textack
```

Windows notes:

- Use **Windows Terminal / PowerShell / CMD** — the game needs a real
  fullscreen console. It will not work in VS Code's output panel.
- `.wav` sounds play via PowerShell `System.Media.SoundPlayer`.
  Missing files = silence (never a crash).
- Save data: `%LOCALAPPDATA%\textack\best.txt`
- Operator config: `%LOCALAPPDATA%\textack\waifu.json`
- If `curses` is missing you will see an install hint instead of a traceback.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Run in a real terminal: textack` | You piped stdin or ran inside an IDE. Run in a real terminal. |
| `Terminal cannot do fullscreen (curses)` | Switch to Windows Terminal / Ghostty / WezTerm / Konsole / xterm. |
| `!! WINDOW TOO SMALL !!` | Enlarge the window or zoom out (`Shift + -`, back with `Shift + +`). Needs 80×24. |
| No sound | Install a player (`paplay`/`aplay`/`mpv`) on Linux; on Windows sound is automatic. Press `F3` to toggle. |
| Photo layer missing | Check `textack --gfx-test`. Kitty graphics need kitty/Ghostty/WezTerm; otherwise you get the colored half-block face, then ASCII. |

Graphics overrides:

```bash
textack --gfx=kitty   # force photo layer
textack --gfx=half    # force colored half-block face
textack --gfx=ascii   # force ASCII art
textack --gfx-test    # diagnose terminal graphics support
TEXTACK_GFX=ascii textack
TEXTACK_Q=low textack        # force LOW quality
TEXTACK_SFX=off textack      # start muted
```

## How to play

- A target word appears, e.g. `sudo apt update`
- Type it exactly + Enter
- Chained combos = critical damage
- Typos = counterattack. Idling too long = chip damage.
- Every hit = XP. Level up = pick 1 of 3 upgrades (14 kinds):
  ATTACK / DEFENSE / SPEED / BASE, Survivor.io style.
- Enemies per wave: SCOUT → RAIDER → GOLEM → OVERLORD, BOSS every 5 waves.
- Operator AIKA in the right panel (terminal ≥102 columns).
  Change art: edit `waifu.txt` or `~/.config/textack/waifu.txt`.
- RIN (wave 4) & SORA (wave 8) auto-unlock — switch operators
  with ◄ ► in the menu. Each operator has English dialog + bond level
  (raised by perfect hits/combos). Custom art from your photo: `docs/waifu-custom.md`.
- Minimum terminal 80×24 — if smaller, the game pauses + shows
  zoom guidance.
- Layered visuals: real photo (Ghostty/WezTerm/kitty, check
  `textack --gfx-test`) → colored face → ASCII.
- Sound: `sfx/*.wav` via paplay/aplay/mpv (beep fallback, F3 on/off).
- `:q` to quit. `F2` cycles quality, `F3` toggles sound.

## Performance

- Single `getmaxyx()` per frame, passed down to every widget
  (was ~80 syscalls/frame).
- Best score cached in memory; disk written only when beaten
  (was a read+write on every hit).
- Attack interval, rank, and idle dialog cached per frame/bucket
  (was 4–5 recomputes/frame).
- Sounds rate-limited per name (turret ≤1/0.4s) to avoid fork spam.
- Particles trimmed in place to the quality budget
  (HIGH 180 / MED 120 / LOW 70); auto-drops to power-saver on slow frames.

## Development

```bash
pip install -e .[dev]
python3 -m pytest -q
python3 -m ruff check textack tests
python3 -m compileall -q textack
```

CI (`.github/workflows/ci.yml`) runs on Python 3.9–3.13: pytest + ruff + compileall.
Code layout: `textack/core/` (pure logic) → `textack/ui/` (curses) → `textack/infra/` (storage/sound/art).
Details: `docs/ARCHITECTURE.md`.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`, `perf:`, `test:`.
See `CONTRIBUTING.md` and the `.gitmessage` template
(`git config commit.template .gitmessage`).

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
