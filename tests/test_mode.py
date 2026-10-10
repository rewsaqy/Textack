# tests/test_mode.py
from textack.engine import mode


def test_flag_forms():
    assert mode.active(["--engine=polyglot"], {}) == "polyglot"
    assert mode.active(["--engine", "polyglot"], {}) == "polyglot"
    assert mode.active(["--engine=classic"], {}) == "classic"
    assert mode.active(["--engine=bogus"], {}) == "classic"


def test_env_and_defaults():
    assert mode.active([], {"TEXTACK_ENGINE": "polyglot"}) == "polyglot"
    assert mode.active([], {"TEXTACK_ENGINE": "fleet"}) == "polyglot"
    assert mode.active([], {}) == "classic"
    assert mode.active() == "classic"
    assert mode.active(["--engine=classic"], {"TEXTACK_ENGINE": "polyglot"}) == "classic"
