# textack/engine/proto.py
"""Wire protocol v1: newline-delimited JSON (NDJSON), UTF-8.

Every message is one JSON object per line: {"v": 1, "t": "<type>", ...}.
Full catalog: docs/PROTOCOL.md. Rules enforced here:

- envelope must be an object with v == 1
- unknown fields are ignored (forward compatibility)
- unknown types and schema violations never raise: the worker answers
  {"t": "error", ...} instead (see err())
- integers must fit i64, seeds must fit u64 non-negative (every worker
  language parses JSON ints as i64/u64; unbounded ints would diverge)
- numbers must be finite (NaN/Infinity are rejected: most JSON
  implementations in other languages refuse them)
- bool is NOT int (JSON true/false must not validate as 1/0)
"""
import json
import math

VERSION = 1
I64_MIN = -(2 ** 63)
I64_MAX = 2 ** 63 - 1
U64_MAX = 2 ** 64 - 1

# type -> (required {field: kind}, optional {field: kind})
# kinds: str | int | seed | num | bool | dict | list | any
SPEC = {
    "hello": ({"role": "str", "proto": "list"}, {"id": "any"}),
    "ready": ({"role": "str", "proto": "num"}, {"id": "any"}),
    "ping": ({}, {"id": "any"}),
    "pong": ({}, {"id": "any"}),
    "hit": ({"id": "any", "target": "str", "buf": "str", "elapsed": "num",
             "combo": "int", "stats": "dict", "wave": "int"}, {"seed": "seed"}),
    "damage": ({"id": "any", "dmg": "int", "tag": "str", "wpm": "num",
                "speed_bonus": "int", "perfect": "bool", "crit": "bool",
                "double": "bool"}, {}),
    "nomatch": ({"id": "any"}, {}),
    "combo": ({"id": "any", "hit": "bool", "combo": "int"},
              {"guard": "num", "rng": "num"}),
    "combo-state": ({"id": "any", "combo": "int"}, {}),
    "counter": ({"id": "any", "enemy_dmg": "int", "wave": "int"},
                {"bonus": "int"}),
    "counter-damage": ({"id": "any", "dmg": "int"}, {}),
    "xp": ({"id": "any", "word_len": "int", "wave": "int", "xp_mult": "num",
            "boss": "bool"}, {}),
    "xp-gain": ({"id": "any", "xp": "num"}, {}),
    "threshold": ({"id": "any", "current": "num"}, {}),
    "threshold-is": ({"id": "any", "next": "num"}, {}),
    "wave": ({"id": "any", "wave": "int"}, {}),
    "wave-cfg": ({"id": "any", "name": "str", "interval": "num", "dmg": "int",
                  "burst": "int", "hp": "int", "proj": "str", "col": "str",
                  "boss": "bool"}, {}),
    "rank": ({"id": "any", "wpm": "num", "combo": "int"}, {}),
    "rank-is": ({"id": "any", "rank": "str"}, {}),
    "dialog": ({"id": "any", "wid": "str", "trigger": "str"},
               {"wave": "int", "enemy": "str", "seed": "seed"}),
    "mood": ({"id": "any", "wid": "str", "mood": "str"}, {"seed": "seed"}),
    "line": ({"id": "any", "text": "str"}, {}),
    "upgrade": ({"id": "any", "uid": "str", "stats": "dict"}, {}),
    "stats": ({"id": "any", "stats": "dict"}, {}),
    "roll": ({"id": "any", "owned": "dict"}, {"k": "int", "seed": "seed"}),
    "choices": ({"id": "any", "ids": "list"}, {}),
    "pick": ({"id": "any", "wave": "int"}, {"seed": "seed"}),
    "word": ({"id": "any", "text": "str"}, {}),
    "content-reload": ({}, {"path": "str", "id": "any"}),
    "content-state": ({"version": "int", "errors": "list"}, {"id": "any"}),
    "unlocks": ({"id": "any", "unlocked": "list", "wave": "int"}, {}),
    "unlocks-is": ({"id": "any", "ids": "list"}, {}),
    "sfx-trigger": ({"name": "str"}, {"id": "any"}),
    "sfx-played": ({"name": "str", "played": "bool", "backend": "str"},
                   {"id": "any"}),
    "sfx-set": ({"on": "bool"}, {"id": "any"}),
    "sfx-state": ({"on": "bool"}, {"id": "any"}),
    "bye": ({}, {}),
    "error": ({"code": "str"}, {"msg": "str", "id": "any"}),
}


def _is(v, kind):
    if kind == "any":
        return True
    if kind == "str":
        return isinstance(v, str)
    if kind == "bool":
        return isinstance(v, bool)
    if kind == "int":
        return type(v) is int and I64_MIN <= v <= I64_MAX
    if kind == "seed":
        return type(v) is int and 0 <= v <= U64_MAX
    if kind == "num":
        return type(v) is int or (type(v) is float and math.isfinite(v))
    if kind == "dict":
        return isinstance(v, dict)
    if kind == "list":
        return isinstance(v, list)
    return False


def validate(msg):
    """Check a decoded message. Returns (True, "") or (False, code)."""
    if not isinstance(msg, dict):
        return False, "bad-envelope"
    if msg.get("v") != VERSION:
        return False, "bad-version"
    t = msg.get("t")
    if t not in SPEC:
        return False, "unknown-type"
    required, optional = SPEC[t]
    for f, kind in required.items():
        if f not in msg or not _is(msg[f], kind):
            return False, "bad-message"
    for f, kind in optional.items():
        if f in msg and msg[f] is not None and not _is(msg[f], kind):
            return False, "bad-message"
    return True, ""


def _no_const(s):
    raise ValueError("non-finite constant not allowed: " + s)


def encode(msg):
    """Dict -> NDJSON line (bytes, trailing newline included)."""
    if not isinstance(msg, dict):
        raise TypeError("message must be a dict")
    text = json.dumps(msg, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False)
    return (text + "\n").encode("utf-8")


def decode(line):
    """NDJSON line (bytes or str) -> dict. Raises ValueError on any garbage."""
    if isinstance(line, str):
        line = line.encode("utf-8")
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"not utf-8: {e}")
    if not text.strip():
        raise ValueError("empty line")
    try:
        obj = json.loads(text, parse_constant=_no_const)
    except json.JSONDecodeError as e:
        raise ValueError(f"bad json: {e}")
    if not isinstance(obj, dict):
        raise TypeError("envelope must be a JSON object")
    return obj


def err(code, msg="", mid=None):
    """Build an error reply. Never raises; id echoed only when present."""
    e = {"v": VERSION, "t": "error", "code": code}
    if msg:
        e["msg"] = msg
    if mid is not None:
        e["id"] = mid
    return e
