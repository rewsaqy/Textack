# tests/test_face.py
from textack.infra.waifu import parse_rgb_text
from textack.ui import face as face_mod


def _px(n, color=(255, 0, 0)):
    return [color] * n


def test_parse_ok():
    t = "2 2\nff000000ff00\n0000ffffff00\n"
    w, h, px = parse_rgb_text(t)
    assert (w, h, len(px)) == (2, 2, 4)
    assert px[0] == (255, 0, 0) and px[3] == (255, 255, 0)


def test_parse_bad():
    assert parse_rgb_text("nope") is None
    assert parse_rgb_text("2 2\nff00\n") is None
    assert parse_rgb_text("999 999\n") is None


def test_fit_keeps_aspect():
    c, r = face_mod.fit_cells(48, 48, 34, 18)
    assert (c, r) == (34, 17)
    c, r = face_mod.fit_cells(48, 48, 20, 8)
    assert r <= 8 and c <= 20


def test_downsample_dims():
    px = [(i % 256, 0, 0) for i in range(48 * 48)]
    cells = face_mod.downsample(px, 48, 48, 10, 5)
    assert len(cells) == 50
    assert len(cells[0]) == 2 and all(len(p) == 3 for p in cells[0])


def test_quantize_cap():
    cells = [((i * 37 % 256, i * 91 % 256, i * 53 % 256), (0, 0, 0)) for i in range(200)]
    pal, idx = face_mod.quantize(cells, max_colors=8)
    assert len(pal) <= 8 and len(idx) == 200
    assert all(0 <= a < 8 and 0 <= b < 8 for a, b in idx)


def test_pair_combos_freq_order_and_cap():
    idx = [(0, 0)] * 10 + [(1, 2)] * 3 + [(2, 2)]
    combos = face_mod.pair_combos(idx, cap=2)
    assert combos == [(0, 0), (1, 2)]
