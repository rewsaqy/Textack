# tests/test_lua_content.py
"""Cross-language proof: the Lua content worker must answer EXACTLY like
Python (Sim.handle) on dialog/mood/wave/unlocks/pick — including floats
(wave intervals prove the shortest-roundtrip ladder in lua/json.lua).

Runs under every available interpreter (lua5.4 required, luajit if
present) to prove the pure-arithmetic MT/JSON works on both.
Adds a hot-reload session: broken files keep the old version serving
and report errors as data; fixed files bump the version live.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from textack.core import words
from textack.engine import proto
from textack.engine.sim import Sim
from textack.engine.transport import MessageIO

ROOT = Path(__file__).resolve().parent.parent
WORKER = ROOT / "lua" / "worker.lua"
CONTENT = ROOT / "content"

SIM = Sim()


def _have(binary):
    return shutil.which(binary) is not None


INTERPS = ["lua5.4"] + (["luajit"] if _have("luajit") else [])
if not _have("lua5.4"):
    pytest.skip("no lua5.4 interpreter", allow_module_level=True)


@pytest.fixture(scope="module", params=INTERPS)
def worker(request):
    proc = subprocess.Popen([request.param, str(WORKER)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            cwd=str(ROOT))
    io = MessageIO(proc.stdout, proc.stdin)
    io.send({"v": 1, "t": "hello"})
    ready = io.recv()
    assert ready["role"] == "content-lua", ready
    yield io
    try:
        io.send({"v": 1, "t": "bye"})
        proc.wait(timeout=10)
    except Exception:  # noqa: BLE001
        proc.kill()


def ask(io, msg):
    io.send(msg)
    rep = io.recv()
    ok, code = proto.validate(rep)
    assert (ok, code) == (True, ""), (rep, code)
    return rep


def test_handshake_and_errors(worker):
    assert ask(worker, {"v": 1, "t": "ping", "id": 1}) == {
        "v": 1, "t": "pong", "id": 1}
    assert ask(worker, {"v": 2, "t": "ping"})["code"] == "bad-version"
    assert ask(worker, {"v": 1, "t": "hit", "id": 2})["code"] == "unknown-type"
    assert ask(worker, {"v": 1, "t": "wave", "id": 3})["code"] == "bad-message"
    assert ask(worker, {"v": 1, "t": "dialog", "id": 4, "wid": "aika",
                        "trigger": "wave", "seed": -1})["code"] == "bad-message"
    worker.w.write(b"not json at all\n")
    worker.w.flush()
    assert ask(worker, {"v": 1, "t": "ping", "id": 5})["id"] == 5


def sim_of(msg):
    return SIM.handle(dict(msg))


def test_dialog_mood_parity(worker):
    mid = 0
    for wid in ["aika", "rin", "sora", "nope"]:
        for trig in ["idle", "wave", "boss", "clear", "defeat", "happy",
                     "sad", "hurt", "excited", "nope"]:
            for seed in [0, 1, 2, 99]:
                mid += 1
                req = {"v": 1, "t": "dialog", "id": mid, "wid": wid,
                       "trigger": trig, "wave": 4, "enemy": "RAIDER",
                       "seed": seed}
                assert ask(worker, req) == sim_of(req), (req, worker)
                mid += 1
                req2 = {"v": 1, "t": "mood", "id": mid, "wid": wid,
                        "mood": trig if trig in ("happy", "sad") else "happy",
                        "seed": seed}
                assert ask(worker, req2) == sim_of(req2), req2


def test_wave_parity_all_waves(worker):
    for wave in range(1, 31):
        req = {"v": 1, "t": "wave", "id": wave, "wave": wave}
        assert ask(worker, req) == sim_of(req), req


def test_unlocks_and_pick_parity(worker):
    mid = 1000
    for unlocked, wave in [(["aika"], 1), (["aika"], 4), (["aika"], 8),
                           (["aika", "rin"], 9), ([], 99)]:
        mid += 1
        req = {"v": 1, "t": "unlocks", "id": mid, "unlocked": unlocked,
               "wave": wave}
        assert ask(worker, req) == sim_of(req), req
    for wave in [1, 2, 3, 9]:
        for seed in [0, 1, 7, 42, 99, 12345]:
            mid += 1
            req = {"v": 1, "t": "pick", "id": mid, "wave": wave,
                   "seed": seed}
            assert ask(worker, req) == sim_of(req), req
    mid += 1
    live = ask(worker, {"v": 1, "t": "pick", "id": mid, "wave": 2})
    assert live["text"] in words.TIER1 + words.TIER2


def test_hot_reload_session(worker, tmp_path):
    pkg = tmp_path / "content"
    pkg.mkdir()
    for name in ["waves.lua", "dialog.lua", "words.lua"]:
        (pkg / name).write_text((CONTENT / name).read_text(), encoding="utf-8")
    r1 = ask(worker, {"v": 1, "t": "content-reload", "id": 1,
                      "path": str(pkg)})
    assert r1["t"] == "content-state" and r1["errors"] == []
    v1 = r1["version"]
    (pkg / "dialog.lua").write_text("this is ( broken lua !!!\n")
    r2 = ask(worker, {"v": 1, "t": "content-reload", "id": 2,
                      "path": str(pkg)})
    assert r2["version"] == v1 and len(r2["errors"]) == 1
    still = ask(worker, {"v": 1, "t": "dialog", "id": 3, "wid": "aika",
                         "trigger": "idle", "seed": 0})
    assert still == sim_of({"v": 1, "t": "dialog", "id": 3, "wid": "aika",
                            "trigger": "idle", "seed": 0})
    fixed = (CONTENT / "dialog.lua").read_text(encoding="utf-8")
    fixed = fixed.replace("Type fast = big damage, senpai!",
                          "Type fast = big damage, legend!")
    (pkg / "dialog.lua").write_text(fixed, encoding="utf-8")
    r3 = ask(worker, {"v": 1, "t": "content-reload", "id": 4,
                      "path": str(pkg)})
    assert r3["version"] == v1 + 1 and r3["errors"] == []
    now = ask(worker, {"v": 1, "t": "dialog", "id": 5, "wid": "aika",
                       "trigger": "idle", "seed": 0})
    assert now["text"] == "Type fast = big damage, legend!"
