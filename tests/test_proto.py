# tests/test_proto.py
import math

import pytest

from textack.engine import proto


def test_roundtrip_unicode():
    m = {"v": 1, "t": "dialog", "id": 3, "wid": "aika", "trigger": "wave",
         "wave": 4, "enemy": "RAIDER", "seed": 0}
    assert proto.decode(proto.encode(m)) == m
    raw = proto.encode({"v": 1, "t": "line", "id": 1, "text": "▲ (≧▽≦) ♡"})
    assert raw.endswith(b"\n") and "▲".encode() in raw


def test_decode_rejects_garbage():
    for bad in [b"", b"   \n", b"{oops", b"\xff\xfe",
                b'{"v":1,"t":"ping","id":NaN}']:
        with pytest.raises(ValueError):
            proto.decode(bad)
    for non_object in [b"[1,2]", b"42", b'"str"']:
        with pytest.raises(TypeError):
            proto.decode(non_object)
    with pytest.raises(TypeError):
        proto.encode([1, 2, 3])


def test_encode_rejects_nonfinite():
    with pytest.raises(ValueError):
        proto.encode({"v": 1, "t": "rank", "id": 1, "wpm": math.inf,
                      "combo": 0})


def test_validate_ok_and_forward_compat():
    ok, code = proto.validate({"v": 1, "t": "hello", "role": "director",
                               "proto": [1], "future_field": {"x": 1}})
    assert (ok, code) == (True, "")


def test_validate_codes():
    assert proto.validate([1, 2])[1] == "bad-envelope"
    assert proto.validate({"v": 2, "t": "ping"})[1] == "bad-version"
    assert proto.validate({"v": 1})[1] == "unknown-type"
    assert proto.validate({"v": 1, "t": "teleport"})[1] == "unknown-type"
    assert proto.validate({"v": 1, "t": "wave", "id": 1})[1] == "bad-message"
    assert proto.validate({"v": 1, "t": "wave", "id": 1, "wave": True})[1] == "bad-message"
    assert proto.validate({"v": 1, "t": "rank", "id": 1, "wpm": "fast",
                            "combo": 0})[1] == "bad-message"
    assert proto.validate({"v": 1, "t": "xp", "id": 1, "word_len": 2,
                            "wave": 1, "xp_mult": 1.0,
                            "boss": 1})[1] == "bad-message"


def test_err_helper():
    assert proto.err("boom") == {"v": 1, "t": "error", "code": "boom"}
    e = proto.err("bad-message", "nope", 7)
    assert e == {"v": 1, "t": "error", "code": "bad-message", "msg": "nope",
                 "id": 7}
