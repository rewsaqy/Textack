# tests/test_engine_sim.py
"""Conformance vectors: Sim must answer exactly like core/*.

Every future worker (Rust, Lua, C, ...) must satisfy these same vectors —
they are the executable half of docs/PROTOCOL.md. Seeded requests are
byte-deterministic; unseeded random ones only assert shape.
"""
import random

from textack.core import combat, enemies, story, upgrades, words
from textack.engine import proto
from textack.engine.sim import Sim
from textack.engine.transport import Loopback

SIM = Sim()
LB = Loopback(SIM)


def call(t, mid=1, **kw):
    return SIM.handle({"v": 1, "t": t, "id": mid, **kw})


def test_handshake():
    assert call("hello", role="director", proto=[1], mid=None) == {
        "v": 1, "t": "ready", "role": "sim", "proto": 1}
    assert call("hello", role="director", proto=[1], mid=8) == {
        "v": 1, "t": "ready", "role": "sim", "proto": 1, "id": 8}
    assert SIM.handle({"v": 1, "t": "bye", "id": 9}) == {
        "v": 1, "t": "bye", "id": 9}
    assert SIM.handle({"v": 1, "t": "ping", "id": None}) == {
        "v": 1, "t": "pong"}
    assert call("bye", mid=11) == {"v": 1, "t": "bye", "id": 11}
    assert SIM.handle({"v": 1, "t": "bye"}) == {"v": 1, "t": "bye"}
    assert call("ping", mid=4) == {"v": 1, "t": "pong", "id": 4}
    assert SIM.handle({"v": 1, "t": "ping"}) == {"v": 1, "t": "pong"}
    assert call("bye") == {"v": 1, "t": "bye", "id": 1}


def test_hit_matches_core():
    stats = upgrades.fresh_stats()
    rep = call("hit", target="sudo", buf="sudo", elapsed=0.5, combo=2,
               stats=stats, wave=2, seed=7)
    exp = combat.resolve_hit("sudo", "sudo", 0.5, 2, stats, 2, 7)
    assert rep == {"v": 1, "t": "damage", "id": 1, "dmg": exp.dmg,
                   "tag": exp.tag, "wpm": exp.wpm,
                   "speed_bonus": exp.speed_bonus, "perfect": exp.perfect,
                   "crit": exp.crit, "double": exp.double}
    assert call("hit", mid=2, target="sudo", buf="sud", elapsed=1.0,
                combo=0, stats=stats, wave=1) == {
        "v": 1, "t": "nomatch", "id": 2}


def test_combo_counter_xp_threshold_match_core():
    assert call("combo", hit=True, combo=3) == {"v": 1, "t": "combo-state",
                                                "id": 1, "combo": 4}
    assert call("combo", hit=False, combo=3, guard=1.0, rng=0.2)["combo"] == \
        combat.combo_step(False, 3, 1.0, 0.2)
    assert call("counter", enemy_dmg=8, wave=3, bonus=2) == {
        "v": 1, "t": "counter-damage", "id": 1, "dmg": 13}
    assert call("xp", word_len=2, wave=1, xp_mult=1.0, boss=False) == {
        "v": 1, "t": "xp-gain", "id": 1, "xp": 6.0}
    assert call("threshold", current=30.0)["next"] == 30.0 * 1.45 + 10


def test_wave_vectors():
    r1 = call("wave", wave=1)
    c1 = enemies.for_wave(1)
    assert (r1["name"], r1["hp"], r1["burst"], r1["boss"]) == ("SCOUT", 95, 1, False)
    assert (r1["interval"], r1["dmg"], r1["proj"], r1["col"]) == (
        c1.interval, c1.dmg, c1.proj, c1.col)
    r5 = call("wave", wave=5)
    assert (r5["name"], r5["burst"], r5["boss"]) == ("BOSS GOLEM", 3, True)
    assert r5["hp"] == int((80 + 5 * 48) * 1.7)
    r8 = call("wave", wave=8)
    assert (r8["name"], r8["burst"], r8["boss"]) == ("OVERLORD", 3, False)


def test_rank_vectors():
    assert call("rank", wpm=0.0, combo=0)["rank"] == "NEWBIE"
    assert call("rank", wpm=60.0, combo=5)["rank"] == "SYSADMIN"
    assert call("rank", wpm=82.0, combo=6)["rank"] == "ROOT"
    assert call("rank", wpm=0.0, combo=10)["rank"] == "KERNEL PANIC"


def test_dialog_matches_core():
    assert call("dialog", wid="aika", trigger="wave", wave=3, enemy="SCOUT",
                seed=0)["text"] == story.line_for("aika", "wave", {
                    "wave": 3, "enemy": "SCOUT"}, 0)
    assert call("mood", wid="rin", mood="happy", seed=2)["text"] == \
        story.mood_line("rin", "happy", 2)


def test_upgrade_and_roll():
    rep = call("upgrade", uid="ammo", stats=upgrades.fresh_stats())
    assert rep["stats"]["dmg_mult"] == 1.0 * 1.15
    a = call("roll", owned={}, seed=99)["ids"]
    b = call("roll", owned={}, seed=99)["ids"]
    assert a == b and len(a) == 3 and set(a) <= set(upgrades.REGISTRY)
    assert call("unlocks", unlocked=["aika"], wave=4)["ids"] == ["rin"]
    assert call("unlocks", unlocked=["aika"], wave=1)["ids"] == []


def test_pick_seeded_matches_core():
    for wave in [1, 2, 3, 9]:
        for seed in [0, 7, 99]:
            rep = call("pick", wave=wave, seed=seed)
            assert rep["text"] == words.pick_word(wave, random.Random(seed))
    rep = call("pick", wave=1)
    assert rep["text"] in words.TIER1


def test_wire_errors_never_raise():
    e1 = LB.call({"v": 1, "t": "hit", "id": 5})
    assert e1["t"] == "error" and e1["code"] == "bad-message" and e1["id"] == 5
    e2 = LB.call({"v": 1, "t": "teleport", "id": 6})
    assert e2["t"] == "error" and e2["code"] == "unknown-type"
    e3 = SIM.handle("nope")
    assert e3["t"] == "error" and e3["code"] == "bad-envelope"
    e4 = call("upgrade", uid="nope_xyz", stats=upgrades.fresh_stats())
    assert e4["t"] == "error" and e4["code"] == "bad-message"


def test_replies_validate_against_spec():
    for rep in [call("hello", role="d", proto=[1], mid=None),
                call("hit", target="ls", buf="ls", elapsed=0.4, combo=0,
                     stats=upgrades.fresh_stats(), wave=1, seed=1),
                call("roll", owned={"ammo": 8}, seed=3),
                call("pick", wave=3, seed=11)]:
        ok, code = proto.validate(rep)
        assert (ok, code) == (True, ""), (rep, code)


def test_sim_rejects_content_management():
    e = call("content-reload", mid=9)
    assert e["t"] == "error" and e["code"] == "unknown-type"
