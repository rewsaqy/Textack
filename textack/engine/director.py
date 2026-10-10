# textack/engine/director.py
"""Routes game math to the fleet (polyglot) or local core (classic).

Method names mirror core/* so siege swaps one identifier per call site.
Every remote call validates its reply; anything off (dead worker, bad
reply, timeout) downgrades that domain to the builtin reference for the
rest of the session — fail-open: the game never dies for the engine.

Not everything crosses the wire: trivial pure helpers with no protocol
type (level_for, resolve_active, fresh_stats, interval math) stay on
core/* directly. sfx in classic mode plays inline via infra/sfx.
"""
from textack.core import combat, enemies, progression, story, upgrades, words
from textack.engine import proto
from textack.engine.sim import Sim
from textack.engine.transport import Loopback
from textack.infra import sfx as sfx_mod

TIMEOUT = 2.0

# Display mirror of upgrades.REGISTRY (icon/cat/name/desc/max). Logic
# (filtering by max) lives in the worker; this only hydrates cards.
UPGRADE_META = {
    "ammo": ("▲", "ATTACK", "AMMO+", "+15% shot damage", 8),
    "crit": ("✸", "ATTACK", "CRIT CORE", "+10% x2 crit chance", 5),
    "perfect": ("◎", "ATTACK", "PERFECT LENS", "+0.25s PERFECT window", 5),
    "double": ("⫽", "ATTACK", "DOUBLE SHOT", "+12% double shot", 5),
    "adren": ("≫", "ATTACK", "ADRENALINE", "+6 speed bonus", 5),
    "wall": ("▣", "DEFENSE", "STEEL WALL", "+25 max HP & heal 25", 8),
    "regen": ("+", "DEFENSE", "REGEN BAY", "+0.8 HP/sec", 5),
    "shield": ("⛨", "DEFENSE", "AEGIS SHIELD", "+12% attack block", 5),
    "repair": ("⚒", "DEFENSE", "REPAIR BOT", "heal +4 per PERFECT", 5),
    "slow": ("◷", "SPEED", "OVERDRIVE", "enemies 8% slower", 5),
    "guard": ("⎋", "SPEED", "COMBO GUARD", "30% combo survives a miss", 3),
    "magnet": ("◉", "BASE", "XP MAGNET", "+25% XP gained", 5),
    "turret": ("⌖", "BASE", "AUTO CANNON", "auto-firing turret", 5),
    "vamp": ("♥", "BASE", "GOLDEN FINGERS", "+1 HP per landed hit", 5),
}


class EngineDirector:
    def __init__(self, sim=None, content=None, sfx=None):
        builtin = Loopback(Sim())
        self.sim = sim if sim is not None else builtin
        self.content = content if content is not None else self.sim
        self.sfx = sfx
        self._classic_sfx = sfx_mod.init()
        self.fallbacks = []

    @classmethod
    def classic(cls):
        return cls()

    def _ask(self, domain, req, expect):
        client = self.sim if domain == "sim" else self.content
        try:
            rep = client.call(dict(req), timeout=TIMEOUT)
            ok, _ = proto.validate(rep)
            if not ok or rep.get("t") not in expect:
                raise ValueError(f"bad {domain} reply")
            return rep
        except Exception as e:  # noqa: BLE001
            self._downgrade(domain, e)
            return None

    def _downgrade(self, domain, e):
        builtin = Loopback(Sim())
        if domain == "sim" and not isinstance(self.sim, Loopback):
            self.sim = builtin
            self.fallbacks.append(f"sim: {e}")
        elif domain == "content" and not isinstance(self.content, Loopback):
            self.content = builtin
            self.fallbacks.append(f"content: {e}")

    # ---- sim domain (plain values, core-compatible) ----

    def resolve_hit(self, target, buf, elapsed, combo, stats, wave, seed=None):
        req = {"v": 1, "t": "hit", "id": 1, "target": target, "buf": buf,
               "elapsed": elapsed, "combo": combo, "stats": dict(stats),
               "wave": wave}
        if seed is not None:
            req["seed"] = seed
        rep = self._ask("sim", req, ("damage", "nomatch"))
        if rep is None:
            return combat.resolve_hit(target, buf, elapsed, combo, stats,
                                      wave, seed)
        if rep["t"] == "nomatch":
            return None
        return combat.HitResult(rep["dmg"], rep["tag"], rep["wpm"],
                                rep["speed_bonus"], rep["perfect"],
                                rep["crit"], rep["double"])

    def combo_step(self, hit, combo, guard=0.0, rng_value=None):
        req = {"v": 1, "t": "combo", "id": 1, "hit": bool(hit),
               "combo": combo, "guard": guard}
        if rng_value is not None:
            req["rng"] = rng_value
        rep = self._ask("sim", req, ("combo-state",))
        if rep is None:
            return combat.combo_step(hit, combo, guard, rng_value)
        return rep["combo"]

    def miss_damage(self, enemy_dmg, wave, bonus=0):
        rep = self._ask("sim", {"v": 1, "t": "counter", "id": 1,
                                "enemy_dmg": enemy_dmg, "wave": wave,
                                "bonus": bonus}, ("counter-damage",))
        if rep is None:
            return combat.miss_damage(enemy_dmg, wave, bonus)
        return rep["dmg"]

    def gain_xp(self, word_len, wave, xp_mult, is_boss):
        rep = self._ask("sim", {"v": 1, "t": "xp", "id": 1,
                                "word_len": word_len, "wave": wave,
                                "xp_mult": xp_mult, "boss": bool(is_boss)},
                        ("xp-gain",))
        if rep is None:
            return progression.gain_xp(word_len, wave, xp_mult, is_boss)
        return rep["xp"]

    def next_threshold(self, current):
        rep = self._ask("sim", {"v": 1, "t": "threshold", "id": 1,
                                "current": current}, ("threshold-is",))
        if rep is None:
            return progression.next_threshold(current)
        return rep["next"]

    def rank_for(self, wpm, combo):
        rep = self._ask("sim", {"v": 1, "t": "rank", "id": 1, "wpm": wpm,
                                "combo": combo}, ("rank-is",))
        if rep is None:
            return progression.rank_for(wpm, combo)
        return rep["rank"]

    def apply(self, uid, stats):
        rep = self._ask("sim", {"v": 1, "t": "upgrade", "id": 1, "uid": uid,
                                "stats": dict(stats)}, ("stats",))
        if rep is None:
            return upgrades.apply(uid, stats)
        stats.clear()
        stats.update(rep["stats"])

    def roll_choices(self, owned, k=3, rng=None):
        if rng is not None:
            return upgrades.roll_choices(owned, k, rng)
        rep = self._ask("sim", {"v": 1, "t": "roll", "id": 1,
                                "owned": dict(owned), "k": k}, ("choices",))
        if rep is None:
            return upgrades.roll_choices(owned, k)
        out = []
        for uid in rep["ids"]:
            meta = UPGRADE_META.get(uid)
            if meta is not None:
                icon, cat, name, desc, maxn = meta
                out.append({"id": uid, "icon": icon, "cat": cat,
                            "name": name, "desc": desc, "max": maxn})
        return out

    # ---- content domain ----

    def for_wave(self, wave):
        rep = self._ask("content", {"v": 1, "t": "wave", "id": 1,
                                    "wave": wave}, ("wave-cfg",))
        if rep is None:
            return enemies.for_wave(wave)
        return enemies.EnemyConfig(rep["name"], rep["interval"], rep["dmg"],
                                   rep["burst"], rep["hp"], rep["proj"],
                                   rep["col"])

    def pick_word(self, wave, rng=None):
        if rng is not None:
            return words.pick_word(wave, rng)
        rep = self._ask("content", {"v": 1, "t": "pick", "id": 1,
                                    "wave": wave}, ("word",))
        if rep is None:
            return words.pick_word(wave)
        return rep["text"]

    def line_for(self, wid, trigger, ctx=None, seed=0):
        ctx = ctx or {}
        req = {"v": 1, "t": "dialog", "id": 1, "wid": wid,
               "trigger": trigger, "seed": seed}
        if "wave" in ctx:
            req["wave"] = ctx["wave"]
        if "enemy" in ctx:
            req["enemy"] = ctx["enemy"]
        rep = self._ask("content", req, ("line",))
        if rep is None:
            return story.line_for(wid, trigger, ctx, seed)
        return rep["text"]

    def mood_line(self, wid, mood, seed=0):
        rep = self._ask("content", {"v": 1, "t": "mood", "id": 1, "wid": wid,
                                    "mood": mood, "seed": seed}, ("line",))
        if rep is None:
            return story.mood_line(wid, mood, seed)
        return rep["text"]

    def check_unlocks(self, unlocked, wave):
        rep = self._ask("content", {"v": 1, "t": "unlocks", "id": 1,
                                    "unlocked": list(unlocked or ["aika"]),
                                    "wave": wave}, ("unlocks-is",))
        if rep is None:
            return story.check_unlocks(unlocked, wave)
        return rep["ids"]

    def content_reload(self, path=None):
        if isinstance(self.content, Loopback):
            return 0, []
        req = {"v": 1, "t": "content-reload", "id": 1}
        if path is not None:
            req["path"] = path
        rep = self._ask("content", req, ("content-state",))
        if rep is None:
            return 0, ["engine unreachable"]
        return rep["version"], list(rep["errors"])

    # ---- sfx ----

    def sfx_trigger(self, name):
        if self.sfx is None:
            sfx_mod.play(None, self._classic_sfx, name)
            return
        try:
            self.sfx.trigger(name)
        except Exception as e:  # noqa: BLE001
            self.sfx = None
            self.fallbacks.append(f"sfx: {e}")
            sfx_mod.play(None, self._classic_sfx, name)

    def sfx_set(self, on):
        self._classic_sfx["on"] = bool(on)
        if self.sfx is not None:
            try:
                self.sfx.set_on(on)
            except Exception as e:  # noqa: BLE001
                self.sfx = None
                self.fallbacks.append(f"sfx: {e}")
