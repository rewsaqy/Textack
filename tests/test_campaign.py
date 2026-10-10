# tests/test_campaign.py
from textack.core import campaign


def test_named_chapters():
    assert campaign.chapter_for(1)["id"] == "ch1"
    assert campaign.chapter_for(5)["name"] == "CH1 · FIRST SIEGE"
    assert campaign.chapter_for(6)["id"] == "ch2"
    assert campaign.chapter_for(11)["id"] == "ch3"
    assert campaign.chapter_for(0)["id"] == "ch1"


def test_boss_flags_follow_fives():
    assert campaign.chapter_for(5)["boss"] is True
    assert campaign.chapter_for(10)["boss"] is True
    assert campaign.chapter_for(6)["boss"] is False


def test_endless_beyond_named():
    ch = campaign.chapter_for(16)
    assert ch["id"] == "ch4" and ch["name"] == "CH4 · ENDLESS"
    assert campaign.chapter_for(100)["id"] == "ch20"


def test_stage_record():
    assert campaign.stage_at(5) == {"wave": 5, "chapter": "ch1",
                                    "chapter_name": "CH1 · FIRST SIEGE",
                                    "boss": True}


def test_progress_shape():
    p = campaign.chapter_progress(7)
    assert p == {"best_wave": 7, "cleared": ["ch1"], "current": "ch2"}
    assert campaign.chapter_progress(0)["current"] == "ch1"
