# textack/core/upgrades.py (explicit functions, no lambdas; behavior identical to main.py:76-119)
import random
from dataclasses import dataclass
from typing import Callable


def fresh_stats() -> dict:
    return {"dmg_mult": 1.0, "crit": 0.05, "crit_mult": 2.0, "perfect_win": 1.2, "max_hp": 100.0, "regen": 0.0, "shield": 0.0, "repair": 0.0, "lifesteal": 0.0, "xp_mult": 1.0, "slow": 0.0, "combo_guard": 0.0, "turret": 0, "turret_dmg": 0.0, "double": 0.0, "speed_bonus": 0, "wall": 0}


@dataclass(frozen=True)
class Upgrade:
    id: str; icon: str; cat: str; name: str; desc: str; max: int; apply_fn: Callable[[dict], None]
def _ammo(s): s.update(dmg_mult=s["dmg_mult"] * 1.15)
def _crit(s): s.update(crit=min(0.6, s["crit"] + 0.10))
def _perfect(s): s.update(perfect_win=s["perfect_win"] + 0.25)
def _double(s): s.update(double=min(0.6, s["double"] + 0.12))
def _adren(s): s.update(speed_bonus=s["speed_bonus"] + 6)
def _wall(s): s.update(max_hp=s["max_hp"] + 25, wall=s["wall"] + 1)
def _regen(s): s.update(regen=s["regen"] + 0.8)
def _shield(s): s.update(shield=min(0.6, s["shield"] + 0.12))
def _repair(s): s.update(repair=s["repair"] + 4)
def _slow(s): s.update(slow=s["slow"] + 0.08)
def _guard(s): s.update(combo_guard=min(0.9, s["combo_guard"] + 0.30))
def _magnet(s): s.update(xp_mult=s["xp_mult"] * 1.25)
def _turret(s): s.update(turret=s["turret"] + 1); s.update(turret_dmg=s["turret_dmg"] + 14)
def _vamp(s): s.update(lifesteal=s["lifesteal"] + 1.0)
REGISTRY = {}
for _u in [Upgrade("ammo","▲","ATTACK","AMMO+","+15% shot damage",8,_ammo), Upgrade("crit","✸","ATTACK","CRIT CORE","+10% x2 crit chance",5,_crit), Upgrade("perfect","◎","ATTACK","PERFECT LENS","+0.25s PERFECT window",5,_perfect), Upgrade("double","⫽","ATTACK","DOUBLE SHOT","+12% double shot",5,_double), Upgrade("adren","≫","ATTACK","ADRENALINE","+6 speed bonus",5,_adren), Upgrade("wall","▣","DEFENSE","STEEL WALL","+25 max HP & heal 25",8,_wall), Upgrade("regen","+","DEFENSE","REGEN BAY","+0.8 HP/sec",5,_regen), Upgrade("shield","⛨","DEFENSE","AEGIS SHIELD","+12% attack block",5,_shield), Upgrade("repair","⚒","DEFENSE","REPAIR BOT","heal +4 per PERFECT",5,_repair), Upgrade("slow","◷","SPEED","OVERDRIVE","enemies 8% slower",5,_slow), Upgrade("guard","⎋","SPEED","COMBO GUARD","30% combo survives a miss",3,_guard), Upgrade("magnet","◉","BASE","XP MAGNET","+25% XP gained",5,_magnet), Upgrade("turret","⌖","BASE","AUTO CANNON","auto-firing turret",5,_turret), Upgrade("vamp","♥","BASE","GOLDEN FINGERS","+1 HP per landed hit",5,_vamp)]:
    REGISTRY[_u.id] = _u
def apply(uid: str, stats: dict) -> None:
    REGISTRY[uid].apply_fn(stats)
def roll_choices(owned: dict, k: int = 3, rng=random):
    avail = [u for u in REGISTRY.values() if owned.get(u.id, 0) < u.max]
    rng.shuffle(avail)
    return avail[:k]
