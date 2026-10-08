import os
from pathlib import Path


def _cache_dir():
    # Windows: %LOCALAPPDATA%\textack  |  Linux/macOS: $XDG_CACHE_HOME/textack
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "textack"
    xdg = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return Path(xdg) / "textack"


DEFAULT_BEST = _cache_dir() / "best.txt"


def load_best(path=DEFAULT_BEST):
    try:
        t = Path(path).read_text().strip().split()
        return {"wave": int(t[0]), "wpm": float(t[1])} if len(t) >= 2 else {"wave": 0, "wpm": 0.0}
    except Exception:  # noqa: BLE001
        return {"wave": 0, "wpm": 0.0}


def save_best(path, wave, wpm):
    try:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        cur = load_best(path)
        if wave > cur["wave"] or (wave == cur["wave"] and wpm > cur["wpm"]):
            path.write_text(f"{wave} {wpm:.1f}\n")
    except Exception:  # noqa: BLE001, S110
        pass
