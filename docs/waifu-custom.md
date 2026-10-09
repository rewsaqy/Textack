# Custom waifu art — use your own picture

The game reads art as **plain text**, so any image must first be
converted to ASCII/characters. Spec:

- `.txt` text file, max **34 columns × 24 rows** (longer = auto-trimmed)
- `#` lines at the very top = comments/header, ignored. But `#` in the
  middle of the art = dark pixels, **still shown** (safe to use)
- UTF-8 encoding (characters like `♡ ✿ ⌖ ─` are fine)
- Art shows in full on a **wide terminal (≥102 columns)**. Bigger
  terminal = more art fits. A too-small terminal (< 80×24)
  auto-pauses + shows the zoom guide (see below).

## Way 0: web (easiest, no install)

Open **text-image.com/convert/ascii.html** → upload a photo →
set **Image width 30–34 characters** → convert → copy the result
to `~/.config/textack/waifus/aika.txt` (add a `# my art` line on top).

Tips for clarity: crop the face/bust first, enable
*Extra contrast*, and pick a high-contrast photo (B&W manga
is cleanest). Honestly: at ~30 columns what reads is shape +
shading, not photo detail. That is a fair ASCII-art limit.

## HD mode: colored face (recommended!)

Single-color ASCII has a ceiling. The game supports a **colored face
(half-block `▄`)** — 2× sharper, works on **every terminal**
(Linux, Windows Terminal, etc.) **with zero installs**:

- File: `~/.config/textack/waifus/<id>.rgb.txt`
  (Windows: `%APPDATA%\textack\waifus\<id>.rgb.txt`)
- Format: line 1 = `WIDTH HEIGHT` (e.g. `48 48`), then HEIGHT rows of
  spaceless hex RGB (`ff0000` = red). The game auto-fits the
  size + 16-color palette to your terminal. On failure = back to ASCII.

## REAL PHOTO mode (modern terminals)

Got Ghostty / WezTerm / kitty? The game can show a **real photo**
in the panel (kitty image protocol, probe-verified —
never guessed):

```bash
# 1. check your terminal (in a real terminal, not an IDE):
textack --gfx-test
# 2. if it says "resolved: kitty", drop a photo in:
cp myphoto.png ~/.config/textack/waifus/aika.png   # .png/.jpg/.webp ok
# 3. play as usual — the photo shows in the menu + beside the game
```

- Needs Pillow once: `pip install textack[hd]`
  (Linux tool install: already included automatically). Without Pillow,
  only raw `.png` can be displayed.
- Force a mode: `textack --gfx=kitty|half|ascii` or `TEXTACK_GFX=...`
- Other terminals (Konsole, GNOME Terminal, Alacritty) automatically
  use half-block — the game still runs, still colored.

Make a `.rgb.txt` from a photo (needs Pillow, once):

```bash
pip install pillow
python3 - <<'EOF'
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
src = Image.open("photo.png").convert("RGB")
W, H = src.size
# face crop: tune the 0.xx to your photo (left, top, right, bottom)
crop = src.crop((int(W*0.33), int(H*0.21), int(W*0.67), int(H*0.45)))
g = crop.filter(ImageFilter.GaussianBlur(1))
g = ImageEnhance.Contrast(ImageOps.autocontrast(g, cutoff=2)).enhance(1.15)
g = g.resize((48, 48), Image.LANCZOS)
px = g.load()
rows = ["".join(f"{px[x, y][0]:02x}{px[x, y][1]:02x}{px[x, y][2]:02x}" for x in range(48)) for y in range(48)]
out = Path.home() / ".config" / "textack" / "waifus" / "aika.rgb.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("48 48\n" + "\n".join(rows) + "\n")
print("saved:", out)
EOF
```

## File locations

| Waifu | Custom path |
|---|---|
| AIKA | `~/.config/textack/waifus/aika.txt` (Windows: `%APPDATA%\textack\waifus\aika.txt`) |
| RIN | `.../waifus/rin.txt` |
| SORA | `.../waifus/sora.txt` |

Legacy `waifu.txt` / `~/.config/textack/waifu.txt` is still read
as an AIKA override. No custom file = builtin art.

## Way 1: `jp2a` (fast, no coding)

```bash
sudo pacman -S jp2a   # or: sudo apt install jp2a
jp2a --width=30 --colors photo.png > ~/.config/textack/waifus/aika.txt
```

Tips: portrait photo + plain background gives the cleanest result.
Downscale to ~200px first if the art looks too busy.

## Way 2: `chafa` (colored, great on modern terminals)

```bash
chafa --symbols block --width 30 photo.png
# if you like it, save it:
chafa --symbols block --width 30 photo.png > ~/.config/textack/waifus/aika.txt
```

## Way 3: Python + Pillow (full control)

```bash
pip install pillow
python3 - <<'EOF'
from pathlib import Path
from PIL import Image
img = Image.open("photo.png").convert("L").resize((30, 14))
chars = " .:-=+*#%@"
px = img.load()
lines = ["".join(chars[px[x, y] * len(chars) // 256] for x in range(30)) for y in range(14)]
out = Path.home() / ".config" / "textack" / "waifus" / "aika.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("# custom aika\n" + "\n".join(lines) + "\n")
print("saved:", out)
EOF
```

## Check the result

Run `textack` in a terminal **≥102 columns** — the right panel
shows your new art. If it is broken/too wide, the game auto-
trims it (no crash).

## Window too small? (terminal-size guard)

The game needs at least **80×24**. On a smaller window it
**auto-pauses** + dark screen + message:

```text
!! WINDOW TOO SMALL !!
need >= 80x24  now 60x15
enlarge the window, or zoom out:
  Shift + -  (smaller font)
```

- **Enlarge the window**: drag / maximize — waifu art breathes too
- **Zoom out `Shift + -`**: smaller font → more columns fit
  (34-column art needs quite some zoom-out on a small window)
- **Restore: `Shift + +`** · quit: `q`

## What to download (summary)

| For what | Download | Required? |
|---|---|---|
| Play + colored face | — (builtin, stdlib only) | — |
| Direct photos (.jpg/.webp) | `pip install textack[hd]` (= Pillow) | optional |
| REAL photo in panel | Ghostty / WezTerm / kitty + check `textack --gfx-test` | optional |
| ASCII convert/preview | `chafa` (`sudo pacman -S chafa`) | optional |

Why not real photos directly? Image protocols (kitty/sixel)
only run on certain terminals (Konsole does sixel, GNOME Terminal
does not, Alacritty does not). Colored half-block runs **anywhere**
including Windows — so the game uses it for a stable base.

## Compatibility matrix (guaranteed per terminal)

| Terminal | Real photo | Colored face | ASCII | Sound | Notes |
|---|---|---|---|---|---|
| kitty / Ghostty / WezTerm | ✅ | ✅ | ✅ | ✅ | all features, verify with `textack --gfx-test` |
| Konsole / foot / contour | ➖ | ✅ | ✅ | ✅ | sixel not used by the game (later); full half-block |
| GNOME Terminal / VTE | ➖ | ✅ | ✅ | ✅ | full half-block |
| Alacritty | ➖ | ✅ | ✅ | ✅ | full half-block |
| Windows Terminal | ➖ | ✅ | ✅ | ✅ | via `windows-curses` + PowerShell audio |
| Legacy CMD / conhost | ➖ | ⚠️ | ✅ | ✅ | colors drop to 16, ASCII always safe |
| Dumb / IDE panel | ➖ | ➖ | ➖ | ➖ | friendly message, told to open a real terminal |

Principle: **no terminal crashes** — the best supported feature
shows, the rest falls back automatically. Force manually:
`textack --gfx=kitty|half|ascii`.
