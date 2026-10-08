import os
from pathlib import Path


def detect_player():
    import shutil
    for b in ("paplay", "aplay", "play"):
        if shutil.which(b):
            return [b]
    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet"]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    if os.name == "nt" and shutil.which("powershell"):
        return ["powershell"]
    return []


def init(base_dir=None):
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent / "sfx"
    import os as _os
    return {"dir": base, "bin": detect_player(), "on": _os.environ.get("TEXTACK_SFX", "on").lower() not in ("0", "off", "no")}


def _play_windows_powershell(wav_path):
    try:
        import subprocess
        ps = "(New-Object System.Media.SoundPlayer '" + wav_path + "').PlaySync()"
        subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, creationflags=0x08000000)
        return True
    except Exception:  # noqa: BLE001
        return False


def _beep_fallback(name):
    if name not in ("miss", "hurt", "gameover"):
        return
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONHAND)
        return
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        import curses
        curses.beep()
    except Exception: pass  # noqa: BLE001, S110


def play(stdscr, sfx, name):
    if not sfx["on"]:
        return
    try:
        import subprocess
        f = sfx["dir"] / f"{name}.wav"
        if sfx["bin"] and f.exists():
            if os.name == "nt" and sfx["bin"] == ["powershell"]:
                _play_windows_powershell(str(f))
                return
            if os.name == "nt":
                subprocess.Popen([*sfx["bin"], str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, creationflags=0x08000000)
                return
            subprocess.Popen([*sfx["bin"], str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
            return
        _beep_fallback(name)
    except Exception: pass  # noqa: BLE001, S110
