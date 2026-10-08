# tests/test_story.py
from textack.core import story
from textack.infra import storage


def test_line_placeholders():
    s = story.line_for("aika", "wave", {"wave": 3, "enemy": "GOLEM"}, seed=0)
    assert "3" in s and "GOLEM" in s
    assert "{" not in s


def test_line_fallback_unknown():
    assert story.line_for("nope", "wave", {"wave": 1, "enemy": "X"}, seed=1)
    assert story.line_for("aika", "nope-trigger", seed=2)


def test_mood_and_idle():
    assert story.mood_line("rin", "happy", seed=0)
    assert story.line_for("sora", "idle", seed=4)


def test_bond_levels():
    assert (story.level_for(0), story.title_for(0)) == (0, "Stranger")
    assert story.title_for(30) == "Friend"
    assert story.title_for(80) == "Close"
    assert story.title_for(150) == "Trusted"
    assert story.title_for(999) == "Soulmate"


def test_unlocks_by_wave():
    assert story.check_unlocks(["aika"], 3) == []
    assert story.check_unlocks(["aika"], 4) == ["rin"]
    assert story.check_unlocks(["aika", "rin"], 8) == ["sora"]
    assert story.check_unlocks(["aika", "rin", "sora"], 99) == []


def test_resolve_active_priority():
    st = {"active": "aika", "unlocked": ["aika", "rin"], "bond": {}}
    assert story.resolve_active(["--waifu=rin"], {}, st) == "rin"
    assert story.resolve_active(["--waifu", "rin"], {}, st) == "rin"
    # locked waifu via flag falls back to saved
    assert story.resolve_active(["--waifu=sora"], {}, st) == "aika"
    assert story.resolve_active([], {"TEXTACK_WAIFU": "rin"}, st) == "rin"
    assert story.resolve_active([], {}, st) == "aika"
    assert story.resolve_active([], {}, {}) == "aika"


def test_waifu_state_roundtrip(tmp_path):
    p = tmp_path / "waifu.json"
    assert storage.load_waifu(p)["active"] == "aika"
    storage.save_waifu(p, {"active": "rin", "unlocked": ["aika", "rin"], "bond": {"rin": 42.5}})
    st = storage.load_waifu(p)
    assert st["active"] == "rin" and st["bond"]["rin"] == 42.5


def test_waifu_state_corrupt(tmp_path):
    p = tmp_path / "waifu.json"
    p.write_text("not json {{")
    assert storage.load_waifu(p)["unlocked"] == ["aika"]
