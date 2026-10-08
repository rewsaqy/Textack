# tests/test_infra.py
from textack.infra import quality, storage, waifu


def test_corrupt_best_returns_defaults(tmp_path):
    p = tmp_path / "best.txt"; p.write_text("oops not numbers\n")
    assert storage.load_best(p) == {"wave": 0, "wpm": 0.0}
def test_save_roundtrip(tmp_path):
    p = tmp_path / "best.txt"
    storage.save_best(p, 3, 55.5)
    assert storage.load_best(p) == {"wave": 3, "wpm": 55.5}
def test_quality_low_flag():
    assert quality.from_env(["--low"], {}) == 2
    assert quality.effective_interval(5.0, 0.08) >= 5.0


def test_art_truncates_to_panel(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("\n".join(["x" * 40] * 30) + "\n")
    art = waifu.load_art_for("x", [str(p)])
    assert len(art) == 24 and all(len(ln) == 34 for ln in art)


def test_art_hash_lines_kept(tmp_path):
    # '#' = komen hanya sebelum art; baris '#' di tengah = piksel gelap
    p = tmp_path / "aika.txt"
    p.write_text("# header komen\n  /\\_/\\\n#acak gelap\n\n")
    assert waifu.load_art_for("aika", [str(p)]) == ["  /\\_/\\", "#acak gelap"]
