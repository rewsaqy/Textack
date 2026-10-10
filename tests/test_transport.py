# tests/test_transport.py
import socket

import pytest

from textack.engine.sim import Sim
from textack.engine.transport import Loopback, MessageIO


def _pair():
    a, b = socket.socketpair()
    return (MessageIO(a.makefile("rb"), a.makefile("wb")),
            MessageIO(b.makefile("rb"), b.makefile("wb")), a, b)


def test_stdio_roundtrip():
    da, db, sa, sb = _pair()
    try:
        hello = {"v": 1, "t": "hello", "role": "director", "proto": [1]}
        da.send(hello)
        assert db.recv() == hello
        db.send({"v": 1, "t": "ready", "role": "sim", "proto": 1})
        assert da.recv()["t"] == "ready"
    finally:
        sa.close()
        sb.close()


def test_recv_eof():
    a, b = socket.socketpair()
    b.close()
    mio = MessageIO(a.makefile("rb"), a.makefile("wb"))
    try:
        with pytest.raises(EOFError):
            mio.recv()
    finally:
        a.close()


def test_loopback_end_to_end():
    lb = Loopback(Sim())
    rep = lb.call({"v": 1, "t": "rank", "id": 9, "wpm": 82.0, "combo": 6})
    assert rep["t"] == "rank-is" and rep["id"] == 9
    assert rep["rank"] == "ROOT"
