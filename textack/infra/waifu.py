import os
from pathlib import Path

DEFAULT = ["     ✿   ♡   ✿     ", '      .-"""-.      ', "     / .--. \\     ", "    | (o)(o) |    ", "     \\  __  /     ", "     _| || |_     ", "    / | || | \\    ", "   |  | || |  |   ", "   |  \\_||_/  |   ", "    \\   __   /    ", "     |______|     ", "    _|      |_    "]
RIN_DEFAULT = ["      ───○───      ", "     /  ___  \\     ", "    |  ( - - ) |    ", "     \\  ───  /     ", "    __|     |__    ", "   /  | ↓↓↓ |  \\   ", "  |   | ↓↓↓ |   |  ", "  |   \\_____/   |  ", "   \\   |___|   /   ", "    |__|   |__|    ", "       |_|_|       ", "      _|   |_      "]
SORA_DEFAULT = ["     ⚙ ♡ ⚙       ", '      .-"""-.      ', "     / ^ ^ \\     ", "    |  (o_o)  |    ", "     \\ \\_/ /     ", "    _|_[___]_|_    ", "   / | |⌖| | \\   ", "   |  | |⌖| |  |  ", "   |  |_|_|_|  |  ", "    \\  \\___/  /   ", "     |_______|     ", "    _|  ___  |_    "]
ART_DEFAULTS = {"aika": DEFAULT, "rin": RIN_DEFAULT, "sora": SORA_DEFAULT}
FACES = {"idle": "(・‿・)", "happy": "(≧▽≦)", "sad": "(>_<)", "hurt": "(T_T)", "excited": "(☆▽☆)"}
LINES = {"happy": ["sugoi! kena!", "nice shot, senpai!", "combo naik!"], "sad": ["baka... miss!", "fokus, senpai!", "combo reset..."], "hurt": ["itai! lindungi aku!", "benteng kita!", "kyaa!"], "excited": ["level up! makin kuat!", "power naik!", "yosha!"]}
TIPS = ["ketik cepat = damage", "PERFECT < jendela emas", "combo = crit ganda", "F2 quality • F3 suara", "combo guard selamatkanmu"]


def _config_dir():
    # Windows: %APPDATA%\textack  |  Linux/macOS: $XDG_CONFIG_HOME/textack
    if os.name == "nt":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / "textack"
    xdg = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(xdg) / "textack"


def _read_art_file(p):
    # Komen '#' hanya berlaku SEBELUM art dimulai (header file).
    # Baris '#' di tengah art = piksel gelap, jangan dibuang.
    try:
        if not p.exists():
            return []
        raw = [ln.rstrip("\n") for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()]
        start = 0
        while start < len(raw) and (not raw[start].strip() or raw[start].startswith("#")):
            start += 1
        end = len(raw)
        while end > start and not raw[end - 1].strip():
            end -= 1
        lines = [ln[:34] for ln in raw[start:end][:24]]
        if any(ln.strip() for ln in lines):
            return lines
    except Exception:  # noqa: BLE001, S110
        pass
    return []


def parse_rgb_text(text):
    """Parse 'W H' + H hex rows -> (w, h, [(r,g,b)...]) or None."""
    try:
        lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
        w, h = (int(x) for x in lines[0].split())
        if not (1 <= w <= 128 and 1 <= h <= 128 and len(lines) - 1 >= h):
            return None
        px = []
        for ln in lines[1: h + 1]:
            ln = ln.strip()
            if len(ln) < w * 6:
                return None
            for i in range(w):
                c = ln[i * 6: i * 6 + 6]
                px.append((int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)))
        return w, h, px
    except (ValueError, IndexError):
        return None


def load_rgb_for(wid, extra_paths=None):
    """Photo pixels (w, h, [(r,g,b)]) or None. Fail-silent."""
    cands = [Path(p) for p in (extra_paths or [])]
    try:
        cands.append(Path(__file__).resolve().parent.parent.parent / "waifus" / f"{wid}.rgb.txt")
    except Exception:  # noqa: BLE001, S110
        pass
    cands.append(_config_dir() / "waifus" / f"{wid}.rgb.txt")
    for p in cands:
        try:
            if p.exists():
                got = parse_rgb_text(p.read_text(encoding="utf-8", errors="replace"))
                if got:
                    return got
        except Exception:  # noqa: BLE001, S110
            pass
    return None


def load_art(extra_paths=None):
    return load_art_for("aika", extra_paths)


PHOTO_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def find_photo(wid, extra_paths=None):
    """Path foto waifu (Pillow: format apa saja) atau None. Fail-silent."""
    cands = [Path(p) for p in (extra_paths or [])]
    roots = []
    try:
        roots.append(Path(__file__).resolve().parent.parent.parent / "waifus")
    except Exception:  # noqa: BLE001, S110
        pass
    roots.append(_config_dir() / "waifus")
    for root in roots:
        for ext in PHOTO_EXTS:
            cands.append(root / f"{wid}{ext}")
    for p in cands:
        try:
            if p.is_file() and p.stat().st_size > 0:
                return p
        except Exception:  # noqa: BLE001, S110
            pass
    return None


def load_art_for(wid, extra_paths=None):
    """Per-waifu art. Custom file wins, then builtin. See docs/waifu-custom.md."""
    cands = []
    for p in (extra_paths or []):
        cands.append(Path(p))
    try:
        cands.append(Path(__file__).resolve().parent.parent.parent / "waifus" / f"{wid}.txt")
    except Exception:  # noqa: BLE001, S110
        pass
    cands.append(_config_dir() / "waifus" / f"{wid}.txt")
    if wid == "aika":
        try:
            cands.append(Path(__file__).resolve().parent.parent.parent / "waifu.txt")
        except Exception:  # noqa: BLE001, S110
            pass
        cands.append(_config_dir() / "waifu.txt")
    for p in cands:
        art = _read_art_file(p)
        if art:
            return art
    return list(ART_DEFAULTS.get(wid, DEFAULT))
