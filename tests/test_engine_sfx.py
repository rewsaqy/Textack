# tests/test_engine_sfx.py
"""Phase 2 vectors: sfx domain over the wire.

Handler tests use an injected dict (no audio, no backend). The live test
boots the real worker subprocess and speaks the real protocol — including
50 fire-and-forget notifies to prove the pipe never fills up.
"""
from pathlib import Path

from textack.engine import proto
from textack.engine.sfx_client import SfxClient
from textack.engine.sfx_worker import SfxWorker
from textack.engine.sim import Sim


def _fake_sfx(tmp_path, on=True):
    return {"dir": tmp_path, "bin": [], "on": on}


def test_trigger_muted_or_missing_is_silent(tmp_path):
    w = SfxWorker(_fake_sfx(tmp_path, on=False))
    rep = w.handle({"v": 1, "t": "sfx-trigger", "id": 1, "name": "shoot"})
    assert rep == {"v": 1, "t": "sfx-played", "id": 1, "name": "shoot",
                   "played": False, "backend": "muted"}
    w2 = SfxWorker(_fake_sfx(tmp_path, on=True))
    rep2 = w2.handle({"v": 1, "t": "sfx-trigger", "id": 2, "name": "nope"})
    assert rep2["played"] is False and rep2["backend"] == "none"


def test_notify_has_no_reply(tmp_path):
    w = SfxWorker(_fake_sfx(tmp_path))
    assert w.handle({"v": 1, "t": "sfx-trigger", "name": "shoot"}) is None
    assert w.handle({"v": 1, "t": "sfx-set", "on": False}) is None
    assert w.sfx["on"] is False


def test_set_roundtrip(tmp_path):
    w = SfxWorker(_fake_sfx(tmp_path))
    assert w.handle({"v": 1, "t": "sfx-set", "id": 3, "on": False}) == {
        "v": 1, "t": "sfx-state", "id": 3, "on": False}
    rep = w.handle({"v": 1, "t": "sfx-trigger", "id": 4, "name": "hit"})
    assert rep["played"] is False and rep["backend"] == "muted"


def test_worker_rejects_foreign_domain():
    w = SfxWorker(_fake_sfx(Path(".")))
    e = w.handle({"v": 1, "t": "hit", "id": 1, "target": "a", "buf": "a",
                  "elapsed": 1.0, "combo": 0, "stats": {}, "wave": 1})
    assert e["t"] == "error" and e["code"] == "unknown-type"
    s = Sim().handle({"v": 1, "t": "sfx-trigger", "id": 1, "name": "x"})
    assert s["t"] == "error" and s["code"] == "unknown-type"


def test_sfx_replies_validate(tmp_path):
    w = SfxWorker(_fake_sfx(tmp_path))
    for rep in [w.handle({"v": 1, "t": "hello"}),
                w.handle({"v": 1, "t": "ping"}),
                w.handle({"v": 1, "t": "sfx-trigger", "id": 1,
                          "name": "shoot"}),
                w.handle({"v": 1, "t": "sfx-set", "id": 2, "on": True}),
                w.handle({"v": 1, "t": "bye"})]:
        ok, code = proto.validate(rep)
        assert (ok, code) == (True, ""), (rep, code)


def test_live_worker_subprocess(tmp_path):
    with SfxClient(base_dir=str(tmp_path)) as cli:
        assert cli.alive and cli.ping()
        st = cli.request({"v": 1, "t": "sfx-set", "id": 101, "on": False})
        assert st == {"v": 1, "t": "sfx-state", "id": 101, "on": False}
        tr = cli.request({"v": 1, "t": "sfx-trigger", "id": 102,
                          "name": "shoot"})
        assert tr["t"] == "sfx-played" and tr["played"] is False
        for _ in range(50):
            cli.trigger("shoot")
        assert cli.ping()
    assert not cli.alive
