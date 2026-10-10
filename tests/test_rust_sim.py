# tests/test_rust_sim.py
"""Cross-language proof: the Rust worker must answer EXACTLY like Python.

Boots rs/textack-sim over a real pipe and compares every reply against
Sim.handle on a seeded battery (hits, rolls, dialogs, waves, ...).
Floats compare as decoded doubles; seeded vectors must be bit-identical.
Skipped when cargo or the build is unavailable (classic path unaffected).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from textack.core import upgrades, words
from textack.engine.sim import Sim
from textack.engine.transport import MessageIO

ROOT = Path(__file__).resolve().parent.parent
CRATE = ROOT / "rs" / "textack-sim"
BIN = CRATE / "target" / "debug" / "textack-sim"


def _cargo():
    c = shutil.which("cargo")
    if c:
        return c
    home = Path.home() / ".cargo" / "bin" / "cargo"
    return str(home) if home.exists() else None


@pytest.fixture(scope="module")
def worker():
    cargo = _cargo()
    if cargo is None:
        pytest.skip("no cargo toolchain")
    build = subprocess.run([cargo, "build", "--manifest-path",
                            str(CRATE / "Cargo.toml")],
                           capture_output=True, timeout=600, check=False)
    if build.returncode != 0 or not BIN.exists():
        pytest.skip("rust build failed:\n" + build.stderr.decode()[:2000])
    proc = subprocess.Popen([str(BIN)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    io = MessageIO(proc.stdout, proc.stdin)
    yield io
    try:
        io.send({"v": 1, "t": "bye"})
        proc.wait(timeout=10)
    except Exception:  # noqa: BLE001
        proc.kill()


def ask(io, msg):
    io.send(msg)
    return io.recv()


def test_handshake_and_errors(worker):
    assert ask(worker, {"v": 1, "t": "hello", "role": "py", "proto": [1]}) == {
        "v": 1, "t": "ready", "role": "sim-rs", "proto": 1}
    assert ask(worker, {"v": 1, "t": "ping", "id": 1}) == {
        "v": 1, "t": "pong", "id": 1}
    assert ask(worker, {"v": 2, "t": "ping"})["code"] == "bad-version"
    assert ask(worker, {"v": 1, "t": "teleport", "id": 2})["code"] == "unknown-type"
    assert ask(worker, {"v": 1, "t": "hit", "id": 3})["code"] == "bad-message"
    assert ask(worker, {"v": 1, "t": "hit", "id": 4, "target": "a",
                        "buf": "a", "elapsed": 1.0, "combo": 0,
                        "stats": upgrades.fresh_stats(), "wave": 1,
                        "seed": -1})["code"] == "bad-message"
    # garbage line carries no envelope: skipped, next request still served
    worker.w.write(b"this is not json\n")
    worker.w.flush()
    assert ask(worker, {"v": 1, "t": "ping", "id": 5})["id"] == 5


SIM = Sim()


def sim_of(msg):
    return SIM.handle(dict(msg))


def test_parity_battery(worker):
    mid = 100
    for wave in range(1, 13):
        mid += 1
        assert ask(worker, {"v": 1, "t": "wave", "id": mid, "wave": wave}) == \
            sim_of({"v": 1, "t": "wave", "id": mid, "wave": wave})
    stats_plain = upgrades.fresh_stats()
    stats_built = upgrades.fresh_stats()
    for uid in ["ammo", "crit", "perfect", "double", "adren", "wall",
                "shield", "guard", "magnet", "turret"]:
        upgrades.apply(uid, stats_built)
    targets = ["ls", "sudo apt update", "ps aux | grep nginx", "♡⌖_test"]
    for seed in [0, 1, 7, 42, 99, 12345]:
        for target in targets:
            for combo in [0, 5, 10]:
                for elapsed in [0.05, 0.4, 2.5]:
                    for wave in [1, 5, 8]:
                        for stats in [stats_plain, stats_built]:
                            mid += 1
                            req = {"v": 1, "t": "hit", "id": mid,
                                   "target": target, "buf": target,
                                   "elapsed": elapsed, "combo": combo,
                                   "stats": stats, "wave": wave,
                                   "seed": seed}
                            assert ask(worker, req) == sim_of(req), req
                            mid += 1
                            miss = dict(req)
                            miss.update({"id": mid, "buf": target + "x"})
                            assert ask(worker, miss) == sim_of(miss), miss
    for seed in [0, 7, 99]:
        for owned in [{}, {"ammo": 8}, {"ammo": 1, "guard": 3}]:
            mid += 1
            req = {"v": 1, "t": "roll", "id": mid, "owned": owned,
                   "seed": seed}
            assert ask(worker, req) == sim_of(req), req
    for wid in ["aika", "rin", "sora", "nope"]:
        for trig in ["idle", "wave", "boss", "clear", "defeat", "happy",
                     "sad", "hurt", "excited", "nope"]:
            for seed in [0, 1, 2]:
                mid += 1
                req = {"v": 1, "t": "dialog", "id": mid, "wid": wid,
                       "trigger": trig, "wave": 4, "enemy": "RAIDER",
                       "seed": seed}
                assert ask(worker, req) == sim_of(req), req
                mid += 1
                req2 = {"v": 1, "t": "mood", "id": mid, "wid": wid,
                        "mood": "happy" if trig != "happy" else "sad",
                        "seed": seed}
                assert ask(worker, req2) == sim_of(req2), req2


def test_parity_scalars(worker):
    cases = [
        {"v": 1, "t": "combo", "id": 1, "hit": True, "combo": 3},
        {"v": 1, "t": "combo", "id": 2, "hit": False, "combo": 3,
         "guard": 0.3, "rng": 0.2},
        {"v": 1, "t": "counter", "id": 3, "enemy_dmg": 8, "wave": 3,
         "bonus": 2},
        {"v": 1, "t": "xp", "id": 4, "word_len": 15, "wave": 6,
         "xp_mult": 1.25, "boss": True},
        {"v": 1, "t": "threshold", "id": 5, "current": 53.5},
        {"v": 1, "t": "rank", "id": 6, "wpm": 41.2, "combo": 3},
        {"v": 1, "t": "upgrade", "id": 7, "uid": "turret",
         "stats": upgrades.fresh_stats()},
        {"v": 1, "t": "unlocks", "id": 8, "unlocked": ["aika"],
         "wave": 8},
    ]
    for req in cases:
        assert ask(worker, req) == sim_of(req), req


def test_word_pools_agree_on_shape():
    assert words.pick_word(1) in words.TIER1
    assert set(words.TIER1 + words.TIER2 + words.TIER3)
