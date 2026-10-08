# tests/test_gfx.py
import base64

from textack.infra import waifu
from textack.ui import gfx

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_transmit_roundtrip():
    data = PNG_1PX * 300  # paksa multi-chunk? kecil -> 1 chunk cukup
    seqs = gfx.build_transmit(PNG_1PX, 7)
    assert seqs and seqs[0].startswith(b"\x1b_Ga=t,f=100,i=7,")
    assert seqs[-1].startswith(b"\x1b_Gm=0;") or b"m=0" in seqs[-1]
    assert all(s.endswith(b"\x1b\\") for s in seqs)
    payload = b"".join(s.split(b";", 1)[1][:-2] for s in seqs)
    assert base64.b64decode(payload) == PNG_1PX
    assert len(data) > 0


def test_transmit_chunks_flag():
    big = bytes(range(256)) * 40  # 10240 byte -> >4096 b64
    seqs = gfx.build_transmit(big, 3)
    assert len(seqs) > 1
    assert b"m=1" in seqs[0] and b"m=0" in seqs[-1]


def test_place_delete():
    p = gfx.build_place(7, 1, 20, 10)
    assert b"a=p,i=7,p=1,c=20,r=10" in p and b"C=1" in p
    assert b"a=d" in gfx.build_delete_image(7) and b"i=7" in gfx.build_delete_image(7)
    assert gfx.build_delete_visible().startswith(b"\x1b_Ga=d")


def test_detect_heuristic():
    assert gfx.detect_heuristic({"TERM": "xterm-kitty"})
    assert gfx.detect_heuristic({"KITTY_WINDOW_ID": "1"})
    assert gfx.detect_heuristic({"TERM_PROGRAM": "Ghostty"})
    assert gfx.detect_heuristic({"TERM_PROGRAM": "wezterm"})
    assert gfx.detect_heuristic({"WEZTERM_PANE": "0"})
    assert not gfx.detect_heuristic({"TERM": "xterm-256color"})
    assert not gfx.detect_heuristic({})


def test_detect_junk_env_never_raises():
    assert gfx.detect_heuristic({"TERM": None, "TERM_PROGRAM": 12345}) is False
    assert gfx.resolve([], {"TEXTACK_GFX_HAVE": None}) == "half"


def test_resolve_forced():
    assert gfx.resolve(["--gfx=ascii"], {}) == "ascii"
    assert gfx.resolve(["--gfx=kitty"], {}) == "kitty"
    assert gfx.resolve(["--gfx=half"], {}) == "half"
    assert gfx.resolve([], {"TEXTACK_GFX": "ascii"}) == "ascii"
    assert gfx.resolve([], {"TEXTACK_GFX_HAVE": "1"}) == "kitty"
    assert gfx.resolve([], {"TEXTACK_GFX_HAVE": "0"}) == "half"
    assert gfx.resolve([], {}) == "half"


def test_probe_no_tty_is_false():
    assert gfx.probe() is False


def test_find_photo(tmp_path):
    p = tmp_path / "aika.png"
    p.write_bytes(PNG_1PX)
    assert waifu.find_photo("aika", [str(p)]) == p
    assert waifu.find_photo("nope_xyz") is None


def test_png_bytes_raw_no_pil(tmp_path):
    p = tmp_path / "x.png"
    p.write_bytes(PNG_1PX)
    got = gfx.png_bytes_for(str(p))
    assert got.startswith(b"\x89PNG\r\n\x1a\n") and len(got) > 0
    q = tmp_path / "x.jpg"
    q.write_bytes(b"not a jpeg")
    assert gfx.png_bytes_for(str(q)) is None
