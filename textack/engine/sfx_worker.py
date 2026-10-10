# textack/engine/sfx_worker.py
"""First out-of-process worker (phase 2): sound over stdio.

Run: python -m textack.engine.sfx_worker [--dir DIR]

Speaks protocol v1, sfx domain (docs/PROTOCOL.md). Owns backend
detection, rate limiting, and the on/off switch, so the director never
forks audio players itself. Fail-silent like the classic path: a muted
switch or missing backend answers played=false, never an error.

Notification rule: sfx-trigger / sfx-set WITHOUT an id get NO reply,
so fire-and-forget clients can never fill the pipe.
"""
import sys

from textack.engine import proto
from textack.engine.transport import MessageIO
from textack.infra import sfx as sfx_mod


class SfxWorker:
    def __init__(self, sfx=None, role="sfx"):
        self.sfx = sfx if sfx is not None else sfx_mod.init()
        self.role = role

    def handle(self, msg):
        if not isinstance(msg, dict):
            return proto.err("bad-envelope", "message must be an object")
        # JSON null ≡ absent (matches every other worker language).
        msg = {k: v for k, v in msg.items() if v is not None}
        ok, code = proto.validate(msg)
        if not ok:
            mid = msg.get("id") if code in ("bad-message", "unknown-type") else None
            return proto.err(code, "invalid message", mid)
        t = msg["t"]
        h = getattr(self, "_on_" + t.replace("-", "_"), None)
        if h is None:
            return proto.err("unknown-type", f"no handler for {t!r}", msg.get("id"))
        try:
            return h(msg)
        except (KeyError, TypeError, ValueError) as e:
            return proto.err("bad-message", str(e), msg.get("id"))

    def _on_hello(self, msg):
        rep = {"v": 1, "t": "ready", "role": self.role, "proto": 1}
        if msg.get("id") is not None:
            rep["id"] = msg["id"]
        return rep

    def _on_ping(self, msg):
        rep = {"v": 1, "t": "pong"}
        if msg.get("id") is not None:
            rep["id"] = msg["id"]
        return rep

    def _on_bye(self, msg):
        rep = {"v": 1, "t": "bye"}
        if msg.get("id") is not None:
            rep["id"] = msg["id"]
        return rep

    def _on_sfx_trigger(self, msg):
        played = bool(sfx_mod.play(None, self.sfx, msg["name"]))
        if "id" not in msg:
            return None
        return {"v": 1, "t": "sfx-played", "id": msg["id"],
                "name": msg["name"], "played": played,
                "backend": sfx_mod.backend_name(self.sfx, msg["name"])}

    def _on_sfx_set(self, msg):
        self.sfx["on"] = bool(msg["on"])
        if "id" not in msg:
            return None
        return {"v": 1, "t": "sfx-state", "id": msg["id"],
                "on": self.sfx["on"]}

    def run(self, rfile, wfile):
        io = MessageIO(rfile, wfile)
        while True:
            try:
                msg = io.recv()
            except EOFError:
                break
            except (ValueError, TypeError):
                continue  # no envelope to answer; keep serving
            rep = self.handle(msg)
            if rep is None:
                continue
            try:
                io.send(rep)
            except OSError:
                break
            if rep.get("t") == "bye":
                break


def main(argv=None):
    base = None
    args = list(argv if argv is not None else sys.argv[1:])
    for i, a in enumerate(args):
        if a.startswith("--dir="):
            base = a.split("=", 1)[1]
        elif a == "--dir" and i + 1 < len(args):
            base = args[i + 1]
    SfxWorker(sfx_mod.init(base)).run(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    main()
