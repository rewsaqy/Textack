# textack/ui/gfx.py
"""Real-photo layer (kitty graphics protocol) + backend resolution.

Chain: kitty-photo > half-block color > ascii. Kitty needs a supporting
terminal (kitty/Ghostty/WezTerm/...) — verified by an active probe
BEFORE curses starts, never by guessing. All emits are q=2 (quiet) so
terminal replies can't leak into the game's key input.
"""
import base64
import os
import select
import sys
import time

APC_START = b"\x1b_G"
APC_END = b"\x1b\\"
CHUNK = 4096

KITTY_TERMS = {"kitty", "ghostty", "wezterm", "iterm2", "warp", "wayst"}


def detect_heuristic(env):
    env = env or {}

    def _s(key):
        try:
            v = env.get(key)
            return str(v) if v is not None else ""
        except Exception:  # noqa: BLE001
            return ""

    if _s("TERM") == "xterm-kitty" or _s("KITTY_WINDOW_ID"):
        return True
    if _s("TERM_PROGRAM").lower() in KITTY_TERMS:
        return True
    return bool(_s("WEZTERM_PANE") or _s("WEZTERM_EXECUTABLE"))


def forced_mode(argv=None, env=None):
    argv = list(argv or [])
    env = env or {}
    for i, a in enumerate(argv):
        if a.startswith("--gfx="):
            return a.split("=", 1)[1].strip().lower()
        if a == "--gfx-test":
            return "test"
        if a == "--gfx" and i + 1 < len(argv):
            return argv[i + 1].strip().lower()
    return (env.get("TEXTACK_GFX") or "").strip().lower() or None


def build_transmit(png_bytes, img_id):
    """Chunked transmit-only seqs (a=t). Returns list[bytes]."""
    raw = base64.b64encode(png_bytes)
    seqs = []
    first = True
    for off in range(0, len(raw), CHUNK):
        chunk = raw[off: off + CHUNK]
        last = off + CHUNK >= len(raw)
        if first:
            head = f"a=t,f=100,i={img_id},q=2,m={0 if last else 1};".encode()
            first = False
        else:
            head = f"m={0 if last else 1};".encode()
        seqs.append(APC_START + head + chunk + APC_END)
    return seqs


def build_place(img_id, placement_id, cols, rows):
    return APC_START + f"a=p,i={img_id},p={placement_id},c={cols},r={rows},C=1,q=2".encode() + APC_END


def build_delete_image(img_id):
    return APC_START + f"a=d,d=I,i={img_id},q=2".encode() + APC_END


def build_delete_visible():
    return APC_START + b"a=d,d=a,q=2" + APC_END


def emit(data):
    try:
        os.write(sys.stdout.fileno(), data)
    except Exception:  # noqa: BLE001, S110
        pass


def place_at(y, x, seq):
    """Position cursor (raw CUP, self-heals on next full repaint) + emit."""
    try:
        emit(f"\x1b[{max(1, y + 1)};{max(1, x + 1)}H".encode() + seq)
    except Exception:  # noqa: BLE001, S110
        pass


def probe(timeout=0.4):
    """Active support check. Only call OUTSIDE curses. Returns bool."""
    try:
        import termios
        import tty
    except ImportError:
        return False  # Windows has neither; graphics probe unsupported
    try:
        fd = sys.stdin.fileno()
    except Exception:  # noqa: BLE001
        return False
    try:
        if not os.isatty(fd):
            return False
    except Exception:  # noqa: BLE001
        return False
    try:
        old = termios.tcgetattr(fd)
    except Exception:  # noqa: BLE001
        return False
    try:
        tty.setraw(fd)
        sys.stdout.buffer.write(b"\x1b_Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\\x1b[c")
        sys.stdout.buffer.flush()
        buf = b""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            r, _, _ = select.select([fd], [], [], max(0.0, end - time.monotonic()))
            if not r:
                break
            try:
                chunk = os.read(fd, 1024)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            if b"_Gi=31" in buf and (b"OK" in buf or b"ENOMEM" in buf):
                return b"OK" in buf
        return False
    except Exception:  # noqa: BLE001
        return False
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:  # noqa: BLE001, S110
            pass


def resolve(argv=None, env=None, allow_probe=False):
    """kitty | half | ascii. Probes once (marks TEXTACK_GFX_PROBED)."""
    real_env = env if env is not None else os.environ
    force = forced_mode(argv, real_env)
    if force == "test":
        return "test"
    if force in ("kitty", "photo"):
        return "kitty"
    if force in ("half", "hd"):
        return "half"
    if force in ("ascii", "off"):
        return "ascii"
    if isinstance(real_env, dict):
        have = real_env.get("TEXTACK_GFX_HAVE")
    else:
        have = real_env.get("TEXTACK_GFX_HAVE")
    if have == "1":
        return "kitty"
    if have == "0":
        return "half"
    probed = False
    try:
        probed = bool(real_env.get("TEXTACK_GFX_PROBED"))
    except Exception:  # noqa: BLE001, S110
        pass
    if not probed and allow_probe and detect_heuristic(real_env):
        ok = False
        try:
            ok = probe() if sys.stdin.isatty() else False
        except Exception:  # noqa: BLE001
            ok = False
        try:
            os.environ["TEXTACK_GFX_HAVE"] = "1" if ok else "0"
            os.environ["TEXTACK_GFX_PROBED"] = "1"
        except Exception:  # noqa: BLE001, S110
            pass
        return "kitty" if ok else "half"
    return "half"


def test_report(argv=None, env=None):
    env = dict(env if env is not None else os.environ)
    lines = [f"heuristic-kitty: {detect_heuristic(env)}"]
    lines.append(f"stdin-isatty: {sys.stdin.isatty()}")
    if sys.stdin.isatty():
        lines.append(f"probe: {'OK-kitty' if probe() else 'no-graphics'}")
    else:
        lines.append("probe: skipped (not a tty)")
    lines.append(f"resolved: {resolve([a for a in argv if a != '--gfx-test'], env)}")
    lines.append("(force: --gfx=kitty|half|ascii or TEXTACK_GFX=...)")
    return "\n".join(lines)


def png_bytes_for(path, max_side=320):
    """Photo file -> PNG bytes. Pillow any-format, else raw .png. None if fail."""
    try:
        p = str(path)
        try:
            import io

            from PIL import Image

            im = Image.open(p).convert("RGB")
            im.thumbnail((max_side, max_side), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            if p.lower().endswith(".png"):
                with open(p, "rb") as f:
                    return f.read()
    except Exception:  # noqa: BLE001, S110
        pass
    return None
