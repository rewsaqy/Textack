# tests/test_enemy_style.py
from textack.ui.screens import siege


def test_flag_forms():
    assert siege.enemy_style(["--enemy=classic"], {}) == "classic"
    assert siege.enemy_style(["--enemy", "classic"], {}) == "classic"
    assert siege.enemy_style(["--enemy=pixel"], {}) == "pixel"


def test_env_and_default():
    assert siege.enemy_style([], {"TEXTACK_ENEMY": "classic"}) == "classic"
    assert siege.enemy_style([], {}) == "pixel"
    assert siege.enemy_style() == "pixel"
    assert siege.enemy_style(["--enemy=bogus"], {}) == "pixel"


def test_both_sprite_sets_present():
    assert len(siege.ENEMY_PIXEL_A) == len(siege.ENEMY_PIXEL_B) == 7
    assert len(siege.ENEMY_CLASSIC_A) == len(siege.ENEMY_CLASSIC_B) == 7
    assert siege.ENEMY_PIXEL_A != siege.ENEMY_CLASSIC_A
