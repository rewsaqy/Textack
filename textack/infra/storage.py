import copy
import json
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
DEFAULT_WAIFU = _cache_dir() / "waifu.json"

WAIFU_DEFAULT_STATE = {"active": "aika", "unlocked": ["aika"], "bond": {"aika": 0.0}}


def load_best(path=DEFAULT_BEST):
    try:
        t = Path(path).read_text().strip().split()
        return {"wave": int(t[0]), "wpm": float(t[1])} if len(t) >= 2 else {"wave": 0, "wpm": 0.0}
    except Exception:  # noqa: BLE001
        return {"wave": 0, "wpm": 0.0}


def beats_best(cur, wave, wpm):
    """Pure check: does (wave, wpm) beat cur? Avoids a file read per hit."""
    try:
        return wave > cur["wave"] or (wave == cur["wave"] and wpm > cur["wpm"])
    except (KeyError, TypeError):
        return True


def save_best(path, wave, wpm):
    try:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        cur = load_best(path)
        if beats_best(cur, wave, wpm):
            path.write_text(f"{wave} {wpm:.1f}\n")
    except Exception:  # noqa: BLE001, S110
        pass


def load_waifu(path=DEFAULT_WAIFU):
    state = copy.deepcopy(WAIFU_DEFAULT_STATE)
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(raw.get("active"), str):
            state["active"] = raw["active"]
        if isinstance(raw.get("unlocked"), list):
            state["unlocked"] = [u for u in raw["unlocked"] if isinstance(u, str)] or ["aika"]
        if isinstance(raw.get("bond"), dict):
            for k, v in raw["bond"].items():
                try:
                    state["bond"][k] = max(0.0, float(v))
                except (TypeError, ValueError):
                    continue
    except Exception:  # noqa: BLE001, S110
        pass
    return state


def save_waifu(path, state):
    try:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        safe = {"active": state.get("active", "aika"), "unlocked": list(state.get("unlocked", ["aika"])), "bond": {k: max(0.0, float(v)) for k, v in dict(state.get("bond", {})).items()}}
        path.write_text(json.dumps(safe, indent=1) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001, S110
        pass
