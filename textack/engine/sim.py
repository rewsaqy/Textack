# textack/engine/sim.py
"""Reference sim worker: implements protocol v1 on top of core/*.

In-process today (see transport.Loopback); out-of-process tomorrow
(Rust/Lua/C workers must answer identically — the conformance vectors
in tests/test_engine_sim.py are the contract). Stateless: every reply
derives only from the request. Never raises on wire input: schema
violations and unknown types become {"t": "error", ...} replies.
"""
import random

from textack.core import combat, enemies, progression, story, upgrades, words
from textack.engine import proto


class Sim:
    def __init__(self, role="sim"):
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

    def _on_hit(self, msg):
        r = combat.resolve_hit(msg["target"], msg["buf"], msg["elapsed"],
                               msg["combo"], msg["stats"], msg["wave"],
                               msg.get("seed"))
        if r is None:
            return {"v": 1, "t": "nomatch", "id": msg["id"]}
        return {"v": 1, "t": "damage", "id": msg["id"], "dmg": r.dmg,
                "tag": r.tag, "wpm": r.wpm, "speed_bonus": r.speed_bonus,
                "perfect": r.perfect, "crit": r.crit, "double": r.double}

    def _on_combo(self, msg):
        kept = combat.combo_step(msg["hit"], msg["combo"],
                                 msg.get("guard") or 0.0, msg.get("rng"))
        return {"v": 1, "t": "combo-state", "id": msg["id"], "combo": kept}

    def _on_counter(self, msg):
        dmg = combat.miss_damage(msg["enemy_dmg"], msg["wave"],
                                 msg.get("bonus") or 0)
        return {"v": 1, "t": "counter-damage", "id": msg["id"], "dmg": dmg}

    def _on_xp(self, msg):
        xp = progression.gain_xp(msg["word_len"], msg["wave"],
                                 msg["xp_mult"], msg["boss"])
        return {"v": 1, "t": "xp-gain", "id": msg["id"], "xp": xp}

    def _on_threshold(self, msg):
        return {"v": 1, "t": "threshold-is", "id": msg["id"],
                "next": progression.next_threshold(msg["current"])}

    def _on_wave(self, msg):
        c = enemies.for_wave(msg["wave"])
        return {"v": 1, "t": "wave-cfg", "id": msg["id"], "name": c.name,
                "interval": c.interval, "dmg": c.dmg, "burst": c.burst,
                "hp": c.hp, "proj": c.proj, "col": c.col,
                "boss": msg["wave"] % 5 == 0}

    def _on_rank(self, msg):
        return {"v": 1, "t": "rank-is", "id": msg["id"],
                "rank": progression.rank_for(msg["wpm"], msg["combo"])}

    def _on_dialog(self, msg):
        ctx = {}
        if "wave" in msg:
            ctx["wave"] = msg["wave"]
        if "enemy" in msg:
            ctx["enemy"] = msg["enemy"]
        text = story.line_for(msg["wid"], msg["trigger"], ctx,
                              msg.get("seed") or 0)
        return {"v": 1, "t": "line", "id": msg["id"], "text": text}

    def _on_mood(self, msg):
        text = story.mood_line(msg["wid"], msg["mood"], msg.get("seed") or 0)
        return {"v": 1, "t": "line", "id": msg["id"], "text": text}

    def _on_upgrade(self, msg):
        stats = dict(msg["stats"])
        upgrades.apply(msg["uid"], stats)
        return {"v": 1, "t": "stats", "id": msg["id"], "stats": stats}

    def _on_roll(self, msg):
        rng = random.Random(msg["seed"]) if "seed" in msg else random
        picks = upgrades.roll_choices(dict(msg["owned"]), msg.get("k", 3),
                                      rng)
        return {"v": 1, "t": "choices", "id": msg["id"],
                "ids": [u.id for u in picks]}

    def _on_unlocks(self, msg):
        ids = story.check_unlocks(list(msg["unlocked"]), msg["wave"])
        return {"v": 1, "t": "unlocks-is", "id": msg["id"], "ids": ids}

    def _on_pick(self, msg):
        rng = random.Random(msg["seed"]) if "seed" in msg else random
        text = words.pick_word(msg["wave"], rng)
        return {"v": 1, "t": "word", "id": msg["id"], "text": text}
