# textack/engine/supervisor.py
"""Boots the engine.json fleet with per-domain fallbacks (phase 5).

Every component is optional: a missing binary, failed handshake, or dead
worker falls back to builtin (Loopback over the reference Sim) or classic
(inline infra) — never a crash. Use EngineDirector (director.py) to talk
to whatever came up.
"""
import json
import shutil
import sys
from pathlib import Path

from textack.engine.pipe_client import PipeClient, PipeError
from textack.engine.sfx_client import SfxClient
from textack.engine.sim import Sim
from textack.engine.transport import Loopback

SIM_TYPES = {"hit", "combo", "counter", "xp", "threshold", "rank",
             "upgrade", "roll"}
CONTENT_TYPES = {"dialog", "mood", "wave", "unlocks", "pick"}


class EngineError(RuntimeError):
    pass


def repo_root():
    return Path(__file__).resolve().parent.parent.parent


def load_config(path=None):
    p = Path(path) if path is not None else repo_root() / "engine.json"
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise EngineError(f"cannot load {p}: {e}")
    if not isinstance(cfg, dict) or not isinstance(cfg.get("components"), list):
        raise EngineError(f"bad fleet config: {p}")
    return cfg


class Supervisor:
    def __init__(self, config):
        self.config = config
        self.clients = {}
        self.routes = {}
        self.notes = []

    @classmethod
    def from_repo(cls, path=None):
        return cls(load_config(path)).boot()

    def _resolve(self, comp):
        root = repo_root()
        cands = [comp.get("cmd")] + list(comp.get("alts") or [])
        for cmd in cands:
            if not cmd:
                continue
            head = cmd[0].format(python=sys.executable)
            if "/" in head or "\\" in head:
                if (root / head).exists():
                    return [head] + cmd[1:]
            elif shutil.which(head):
                return [head] + cmd[1:]
        return None

    def _fallback(self, domain, why):
        if domain == "sfx":
            self.routes[domain] = None
        else:
            self.routes[domain] = Loopback(Sim())
        self.notes.append(f"{domain}: classic fallback ({why})")

    def _boot_one(self, comp):
        name = comp.get("name", "?")
        domains = comp.get("domains") or []
        cmd = self._resolve(comp)
        if cmd is None:
            for d in domains:
                if d not in self.routes:
                    self._fallback(d, f"{name} binary not found")
            return
        try:
            if domains == ["sfx"]:
                client = SfxClient(cmd=cmd)
            else:
                client = PipeClient(cmd, cwd=str(repo_root()))
            rep = client.request({"v": 1, "t": "hello", "role": "director",
                                  "proto": [1]}, timeout=15.0)
            if rep.get("t") != "ready":
                raise PipeError("bad handshake")
            self.clients[name] = client
            for d in domains:
                self.routes.setdefault(d, client)
            self.notes.append(f"{name} online ({rep.get('role', '?')})")
        except (PipeError, OSError) as e:
            for d in domains:
                if d not in self.routes:
                    self._fallback(d, f"{name} failed: {e}")

    def boot(self):
        for comp in self.config.get("components", []):
            if isinstance(comp, dict):
                self._boot_one(comp)
        for domain in ("sim", "content", "sfx"):
            if domain not in self.routes:
                self._fallback(domain, "no component declared")
        return self

    def summary(self):
        parts = []
        for domain in ("sim", "content", "sfx"):
            r = self.routes.get(domain)
            if r is None:
                parts.append(f"{domain}=classic")
            elif isinstance(r, Loopback):
                parts.append(f"{domain}=builtin")
            else:
                parts.append(f"{domain}=live")
        return "Engine: " + " ".join(parts)

    def director(self):
        from textack.engine import director as dmod
        return dmod.EngineDirector(sim=self.routes.get("sim"),
                                   content=self.routes.get("content"),
                                   sfx=self.routes.get("sfx"))

    def close(self):
        for client in self.clients.values():
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110
                pass
        self.clients.clear()
