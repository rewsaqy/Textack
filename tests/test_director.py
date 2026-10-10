# tests/test_director.py
"""EngineDirector: identical answers over Loopback, fail-open fallback.

A DeadClient (every call raises) must still yield classic answers, record
the downgrade, and keep serving afterwards.
"""
import random

import pytest

from textack.core import combat, enemies, progression, story, upgrades, words
from textack.engine.director import EngineDirector
from textack.engine.sim import Sim
from textack.engine.transport import Loopback


class DeadClient:
    def call(self, msg, timeout=None):
        raise EOFError("dead")
    def close(self, timeout=None):
        return False
    @property
    def alive(self):
        return False


@pytest.fixture(params=["classic", "loopback"])
def director(request):
    if request.param == "classic":
        return EngineDirector.classic()
    sim = Loopback(Sim())
    return EngineDirector(sim=sim, content=sim, sfx=None)


def test_sim_domain_matches_core(director):
    stats = upgrades.fresh_stats()
    r = director.resolve_hit("sudo", "sudo", 0.5, 2, dict(stats), 2, seed=7)
    e = combat.resolve_hit("sudo", "sudo", 0.5, 2, stats, 2, 7)
    assert (r.dmg, r.tag, r.wpm, r.perfect, r.crit, r.double) == (
        e.dmg, e.tag, e.wpm, e.perfect, e.crit, e.double)
    assert director.resolve_hit("sudo", "sud", 1.0, 0, dict(stats), 1) is None
    assert director.combo_step(True, 3) == 4
    assert director.combo_step(False, 3, 1.0, 0.2) == combat.combo_step(False, 3, 1.0, 0.2)
    assert director.miss_damage(8, 3, 2) == 13
    assert director.gain_xp(15, 6, 1.25, True) == progression.gain_xp(15, 6, 1.25, True)
    assert director.next_threshold(53.5) == progression.next_threshold(53.5)
    assert director.rank_for(41.2, 3) == "POWER USER"
    st = upgrades.fresh_stats()
    director.apply("wall", st)
    assert st["max_hp"] == 125.0 and st["wall"] == 1


def test_roll_hydrates_cards(director):
    picks = director.roll_choices({}, k=3)
    assert len(picks) == 3
    for p in picks:
        assert set(p) == {"id", "icon", "cat", "name", "desc", "max"}
        assert p["id"] in upgrades.REGISTRY
    full = {u["id"] for u in director.roll_choices(
        {uid: 99 for uid in upgrades.REGISTRY}, k=3)}
    assert full == set()


def test_content_domain_matches_core(director):
    cfg = director.for_wave(5)
    exp = enemies.for_wave(5)
    assert isinstance(cfg, enemies.EnemyConfig)
    assert (cfg.name, cfg.hp, cfg.burst) == (exp.name, exp.hp, exp.burst)
    assert director.pick_word(3, random.Random(7)) == \
        words.pick_word(3, random.Random(7))
    assert director.line_for("rin", "wave", {"wave": 4, "enemy": "RAIDER"}, 1) == \
        story.line_for("rin", "wave", {"wave": 4, "enemy": "RAIDER"}, 1)
    assert director.mood_line("sora", "happy", 2) == story.mood_line("sora", "happy", 2)
    assert director.check_unlocks(["aika"], 8) == ["rin", "sora"]
    assert director.content_reload() == (0, [])


def test_fallback_is_fail_open():
    d = EngineDirector(sim=DeadClient(), content=DeadClient(), sfx=None)
    assert d.rank_for(0.0, 0) == "NEWBIE"
    assert d.for_wave(1).name == "SCOUT"
    assert d.line_for("aika", "idle", seed=0) == story.line_for("aika", "idle", seed=0)
    assert len(d.fallbacks) == 2
    assert d.rank_for(82.0, 6) == "ROOT"


def test_apply_unknown_uid_matches_classic():
    d = EngineDirector.classic()
    with pytest.raises(KeyError):
        d.apply("nope_xyz", upgrades.fresh_stats())
    lb = EngineDirector(sim=Loopback(Sim()), content=Loopback(Sim()))
    with pytest.raises(KeyError):
        lb.apply("nope_xyz", upgrades.fresh_stats())


def test_sfx_paths_never_raise(tmp_path):
    d = EngineDirector.classic()
    d.sfx_set(False)
    d.sfx_trigger("shoot")
    d.sfx_set(True)
    d.sfx_trigger("missing-sound-xyz")
    d2 = EngineDirector(sim=Loopback(Sim()), content=Loopback(Sim()), sfx=DeadClient())
    d2.sfx_trigger("shoot")
    assert d2.sfx is None and d2.fallbacks
