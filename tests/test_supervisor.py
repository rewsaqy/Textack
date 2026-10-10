# tests/test_supervisor.py
"""Supervisor: boots what exists, falls back for the rest, always runs.

Uses a synthetic fleet config (no cargo/lua needed): a real sfx worker
plus deliberately missing sim/content binaries that must degrade to
builtin/classic with notes. Malformed configs raise EngineError.
"""
import json

import pytest

from textack.engine import supervisor as sup_mod
from textack.engine.transport import Loopback


def _config(tmp_path):
    return {
        "version": 1,
        "components": [
            {"name": "sfx-py",
             "cmd": ["{python}", "-m", "textack.engine.sfx_worker",
                     "--dir", str(tmp_path)],
             "domains": ["sfx"], "fallback": "classic"},
            {"name": "sim-ghost",
             "cmd": ["./does-not-exist-xyz"],
             "domains": ["sim"], "fallback": "builtin"},
            {"name": "content-ghost",
             "cmd": ["./does-not-exist-xyz"],
             "domains": ["content"], "fallback": "builtin"},
        ],
    }


def test_boot_degrades_and_runs(tmp_path):
    cfg_path = tmp_path / "engine.json"
    cfg_path.write_text(json.dumps(_config(tmp_path)))
    sup = sup_mod.Supervisor.from_repo(str(cfg_path))
    try:
        d = sup.director()
        assert d.rank_for(82.0, 6) == "ROOT"
        assert d.for_wave(3).name == "RAIDER"
        assert d.sfx is not None and d.sfx.ping()
        assert any("fallback" in n for n in sup.notes)
        assert "sim=builtin" in sup.summary() and "sfx=live" in sup.summary()
    finally:
        sup.close()


def test_empty_fleet_is_all_fallback(tmp_path):
    cfg_path = tmp_path / "engine.json"
    cfg_path.write_text(json.dumps({"version": 1, "components": []}))
    sup = sup_mod.Supervisor.from_repo(str(cfg_path))
    try:
        d = sup.director()
        assert isinstance(d.sim, Loopback) and d.sfx is None
        assert d.combo_step(True, 0) == 1
    finally:
        sup.close()


def test_bad_config_raises(tmp_path):
    cfg_path = tmp_path / "engine.json"
    cfg_path.write_text("{oops")
    with pytest.raises(sup_mod.EngineError):
        sup_mod.Supervisor.from_repo(str(cfg_path))
    with pytest.raises(sup_mod.EngineError):
        sup_mod.Supervisor.from_repo(str(tmp_path / "missing.json"))
