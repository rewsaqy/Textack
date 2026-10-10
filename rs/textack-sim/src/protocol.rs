//! Protocol v1 dispatch: JSON values in, JSON values out.
//!
//! Validation mirrors `textack/engine/proto.py`: envelope object, v == 1,
//! known type, required fields with strict kinds (bool is not int, ints
//! are i64, seeds are non-negative u64, floats finite). Failures become
//! `error` replies, never panics.

use serde_json::{Map, Value};

use crate::game;
use crate::mt::Mt;

fn obj(v: &Value) -> Option<&Map<String, Value>> {
    v.as_object()
}

fn field<'a>(o: &'a Map<String, Value>, k: &str) -> Option<&'a Value> {
    o.get(k)
}

fn as_str(v: &Value) -> Option<&str> {
    v.as_str()
}

fn as_bool(v: &Value) -> Option<bool> {
    v.as_bool()
}

fn as_i64(v: &Value) -> Option<i64> {
    match v {
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Some(i)
            } else if let Some(f) = n.as_f64() {
                if f.is_finite() && f.fract() == 0.0
                    && f >= i64::MIN as f64
                    && f <= i64::MAX as f64
                {
                    Some(f as i64)
                } else {
                    None
                }
            } else {
                None
            }
        }
        _ => None,
    }
}

fn as_f64(v: &Value) -> Option<f64> {
    match v {
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Some(i as f64)
            } else if let Some(f) = n.as_f64() {
                if f.is_finite() { Some(f) } else { None }
            } else {
                None
            }
        }
        _ => None,
    }
}

fn as_seed(v: &Value) -> Option<u64> {
    match v {
        Value::Number(n) => n.as_u64(),
        _ => None,
    }
}

fn as_map<'a>(v: &'a Value) -> Option<&'a Map<String, Value>> {
    v.as_object()
}

fn as_list<'a>(v: &'a Value) -> Option<&'a Vec<Value>> {
    v.as_array()
}

fn id_of(o: &Map<String, Value>) -> Option<Value> {
    match o.get("id") {
        None | Some(Value::Null) => None,
        Some(v) => Some(v.clone()),
    }
}

fn err(code: &str, msg: &str, id: Option<Value>) -> Value {
    let mut m = Map::new();
    m.insert("v".to_string(), Value::from(1));
    m.insert("t".to_string(), Value::from("error"));
    m.insert("code".to_string(), Value::from(code));
    if !msg.is_empty() {
        m.insert("msg".to_string(), Value::from(msg));
    }
    if let Some(i) = id {
        m.insert("id".to_string(), i);
    }
    Value::Object(m)
}

fn req_id(o: &Map<String, Value>) -> Option<Value> {
    id_of(o)
}

fn parse_stats(o: &Map<String, Value>) -> Option<game::Stats> {
    let g = |k: &str| field(o, k).and_then(as_f64);
    let gi = |k: &str| field(o, k).and_then(as_i64);
    Some(game::Stats {
        dmg_mult: g("dmg_mult")?,
        crit: g("crit")?,
        crit_mult: g("crit_mult")?,
        perfect_win: g("perfect_win")?,
        max_hp: g("max_hp")?,
        regen: g("regen")?,
        shield: g("shield")?,
        repair: g("repair")?,
        lifesteal: g("lifesteal")?,
        xp_mult: g("xp_mult")?,
        slow: g("slow")?,
        combo_guard: g("combo_guard")?,
        turret: gi("turret")?,
        turret_dmg: g("turret_dmg")?,
        double: g("double")?,
        speed_bonus: gi("speed_bonus")?,
        wall: gi("wall")?,
    })
}

fn stats_to_json(st: &game::Stats) -> Value {
    serde_json::json!({
        "dmg_mult": st.dmg_mult, "crit": st.crit, "crit_mult": st.crit_mult,
        "perfect_win": st.perfect_win, "max_hp": st.max_hp, "regen": st.regen,
        "shield": st.shield, "repair": st.repair, "lifesteal": st.lifesteal,
        "xp_mult": st.xp_mult, "slow": st.slow, "combo_guard": st.combo_guard,
        "turret": st.turret, "turret_dmg": st.turret_dmg, "double": st.double,
        "speed_bonus": st.speed_bonus, "wall": st.wall,
    })
}

fn seeded_rng(o: &Map<String, Value>) -> (Option<Mt>, bool) {
    match o.get("seed") {
        None | Some(Value::Null) => (None, true),
        Some(v) => match as_seed(v) {
            Some(s) => (Some(Mt::from_seed(s)), true),
            None => (None, false),
        },
    }
}

pub fn handle(v: &Value, live: &mut Mt) -> Value {
    let o = match obj(v) {
        Some(o) => o,
        None => return err("bad-envelope", "message must be an object", None),
    };
    if o.get("v").and_then(|x| x.as_u64()) != Some(1) {
        return err("bad-version", "v must be 1", None);
    }
    let t = match o.get("t").and_then(as_str) {
        Some(t) => t,
        None => return err("unknown-type", "missing t", id_of(o)),
    };
    match t {
        "hello" => {
            if field(o, "role").and_then(as_str).is_none() || field(o, "proto").and_then(as_list).is_none() {
                return err("bad-message", "hello needs role+proto", id_of(o));
            }
            let mut m = Map::new();
            m.insert("v".to_string(), Value::from(1));
            m.insert("t".to_string(), Value::from("ready"));
            m.insert("role".to_string(), Value::from("sim-rs"));
            m.insert("proto".to_string(), Value::from(1));
            if let Some(i) = id_of(o) {
                m.insert("id".to_string(), i);
            }
            Value::Object(m)
        }
        "ping" => {
            let mut m = Map::new();
            m.insert("v".to_string(), Value::from(1));
            m.insert("t".to_string(), Value::from("pong"));
            if let Some(i) = id_of(o) {
                m.insert("id".to_string(), i);
            }
            Value::Object(m)
        }
        "bye" => {
            let mut m = Map::new();
            m.insert("v".to_string(), Value::from(1));
            m.insert("t".to_string(), Value::from("bye"));
            if let Some(i) = id_of(o) {
                m.insert("id".to_string(), i);
            }
            Value::Object(m)
        }
        "hit" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "hit needs id", None),
            };
            let (target, buf, elapsed, combo, _wave) = match (
                field(o, "target").and_then(as_str),
                field(o, "buf").and_then(as_str),
                field(o, "elapsed").and_then(as_f64),
                field(o, "combo").and_then(as_i64),
                field(o, "wave").and_then(as_i64),
            ) {
                (Some(a), Some(b), Some(c), Some(d), Some(e)) => (a, b, c, d, e),
                _ => return err("bad-message", "hit fields", Some(id)),
            };
            let stats = match field(o, "stats").and_then(as_map).and_then(parse_stats) {
                Some(s) => s,
                None => return err("bad-message", "hit stats", Some(id)),
            };
            let (seeded, ok) = seeded_rng(o);
            if !ok {
                return err("bad-message", "bad seed", Some(id));
            }
            let mut seeded_box = seeded;
            let rng: &mut Mt = match seeded_box.as_mut() {
                Some(m) => m,
                None => live,
            };
            let r = game::resolve_hit(target, buf, elapsed, combo, &stats, rng);
            match r {
                None => serde_json::json!({"v": 1, "t": "nomatch", "id": id}),
                Some(h) => serde_json::json!({
                    "v": 1, "t": "damage", "id": id, "dmg": h.dmg,
                    "tag": h.tag, "wpm": h.wpm, "speed_bonus": h.speed_bonus,
                    "perfect": h.perfect, "crit": h.crit, "double": h.double,
                }),
            }
        }
        "combo" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "combo needs id", None),
            };
            let (hit, combo) = match (
                field(o, "hit").and_then(as_bool),
                field(o, "combo").and_then(as_i64),
            ) {
                (Some(a), Some(b)) => (a, b),
                _ => return err("bad-message", "combo fields", Some(id)),
            };
            let guard = field(o, "guard").and_then(as_f64).unwrap_or(0.0);
            let rng_value = field(o, "rng").and_then(as_f64);
            let kept = game::combo_step(hit, combo, guard, rng_value, live);
            serde_json::json!({"v": 1, "t": "combo-state", "id": id, "combo": kept})
        }
        "counter" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "counter needs id", None),
            };
            let (dmg, wave) = match (
                field(o, "enemy_dmg").and_then(as_i64),
                field(o, "wave").and_then(as_i64),
            ) {
                (Some(a), Some(b)) => (a, b),
                _ => return err("bad-message", "counter fields", Some(id)),
            };
            let bonus = field(o, "bonus").and_then(as_i64).unwrap_or(0);
            let out = game::miss_damage(dmg, wave, bonus);
            serde_json::json!({"v": 1, "t": "counter-damage", "id": id, "dmg": out})
        }
        "xp" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "xp needs id", None),
            };
            let (word_len, wave, xp_mult, boss) = match (
                field(o, "word_len").and_then(as_i64),
                field(o, "wave").and_then(as_i64),
                field(o, "xp_mult").and_then(as_f64),
                field(o, "boss").and_then(as_bool),
            ) {
                (Some(a), Some(b), Some(c), Some(d)) => (a, b, c, d),
                _ => return err("bad-message", "xp fields", Some(id)),
            };
            let out = game::gain_xp(word_len, wave, xp_mult, boss);
            serde_json::json!({"v": 1, "t": "xp-gain", "id": id, "xp": out})
        }
        "threshold" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "threshold needs id", None),
            };
            let cur = match field(o, "current").and_then(as_f64) {
                Some(c) => c,
                None => return err("bad-message", "threshold fields", Some(id)),
            };
            serde_json::json!({"v": 1, "t": "threshold-is", "id": id,
                               "next": game::next_threshold(cur)})
        }
        "wave" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "wave needs id", None),
            };
            let wave = match field(o, "wave").and_then(as_i64) {
                Some(w) => w,
                None => return err("bad-message", "wave fields", Some(id)),
            };
            let c = game::for_wave(wave);
            serde_json::json!({"v": 1, "t": "wave-cfg", "id": id,
                               "name": c.name, "interval": c.interval,
                               "dmg": c.dmg, "burst": c.burst, "hp": c.hp,
                               "proj": c.proj, "col": c.col,
                               "boss": wave % 5 == 0})
        }
        "rank" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "rank needs id", None),
            };
            let (wpm, combo) = match (
                field(o, "wpm").and_then(as_f64),
                field(o, "combo").and_then(as_i64),
            ) {
                (Some(a), Some(b)) => (a, b),
                _ => return err("bad-message", "rank fields", Some(id)),
            };
            serde_json::json!({"v": 1, "t": "rank-is", "id": id,
                               "rank": game::rank_for(wpm, combo)})
        }
        "dialog" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "dialog needs id", None),
            };
            let (wid, trigger) = match (
                field(o, "wid").and_then(as_str),
                field(o, "trigger").and_then(as_str),
            ) {
                (Some(a), Some(b)) => (a, b),
                _ => return err("bad-message", "dialog fields", Some(id)),
            };
            let wave = field(o, "wave").and_then(as_i64);
            if field(o, "wave").is_some() && wave.is_none() {
                return err("bad-message", "dialog wave", Some(id));
            }
            let enemy = field(o, "enemy").and_then(as_str);
            if field(o, "enemy").is_some() && enemy.is_none() {
                return err("bad-message", "dialog enemy", Some(id));
            }
            let seed = match o.get("seed") {
                None | Some(Value::Null) => 0u64,
                Some(v) => match as_seed(v) {
                    Some(s) => s,
                    None => return err("bad-message", "bad seed", Some(id)),
                },
            };
            let text = game::line_for(wid, trigger, wave, enemy, seed);
            serde_json::json!({"v": 1, "t": "line", "id": id, "text": text})
        }
        "mood" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "mood needs id", None),
            };
            let (wid, mood) = match (
                field(o, "wid").and_then(as_str),
                field(o, "mood").and_then(as_str),
            ) {
                (Some(a), Some(b)) => (a, b),
                _ => return err("bad-message", "mood fields", Some(id)),
            };
            let seed = match o.get("seed") {
                None | Some(Value::Null) => 0u64,
                Some(v) => match as_seed(v) {
                    Some(s) => s,
                    None => return err("bad-message", "bad seed", Some(id)),
                },
            };
            let text = game::mood_line(wid, mood, seed);
            serde_json::json!({"v": 1, "t": "line", "id": id, "text": text})
        }
        "upgrade" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "upgrade needs id", None),
            };
            let (uid, smap) = match (
                field(o, "uid").and_then(as_str),
                field(o, "stats").and_then(as_map),
            ) {
                (Some(a), Some(b)) => (a, b),
                _ => return err("bad-message", "upgrade fields", Some(id)),
            };
            let mut st = match parse_stats(smap) {
                Some(s) => s,
                None => return err("bad-message", "upgrade stats", Some(id)),
            };
            if !game::apply(uid, &mut st) {
                return err("bad-message", "unknown uid", Some(id));
            }
            let mut m = Map::new();
            m.insert("v".to_string(), Value::from(1));
            m.insert("t".to_string(), Value::from("stats"));
            m.insert("id".to_string(), id);
            m.insert("stats".to_string(), stats_to_json(&st));
            Value::Object(m)
        }
        "roll" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "roll needs id", None),
            };
            let omap = match field(o, "owned").and_then(as_map) {
                Some(m) => m,
                None => return err("bad-message", "roll fields", Some(id)),
            };
            let mut owned: Vec<(String, i64)> = Vec::new();
            for (k, v) in omap.iter() {
                match as_i64(v) {
                    Some(n) => owned.push((k.clone(), n)),
                    None => return err("bad-message", "roll owned", Some(id)),
                }
            }
            let k = field(o, "k").and_then(as_i64).unwrap_or(3);
            if field(o, "k").is_some() && k < 0 {
                return err("bad-message", "roll k", Some(id));
            }
            let (seeded, ok) = seeded_rng(o);
            if !ok {
                return err("bad-message", "bad seed", Some(id));
            }
            let mut seeded_box = seeded;
            let rng: &mut Mt = match seeded_box.as_mut() {
                Some(m) => m,
                None => live,
            };
            let ids = game::roll_ids(&owned, k.max(0) as usize, rng);
            serde_json::json!({"v": 1, "t": "choices", "id": id, "ids": ids})
        }
        "unlocks" => {
            let id = match req_id(o) {
                Some(i) => i,
                None => return err("bad-message", "unlocks needs id", None),
            };
            let (list, wave) = match (
                field(o, "unlocked").and_then(as_list),
                field(o, "wave").and_then(as_i64),
            ) {
                (Some(a), Some(b)) => (a, b),
                _ => return err("bad-message", "unlocks fields", Some(id)),
            };
            let have: Vec<String> = list
                .iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect();
            let ids = game::check_unlocks(&have, wave);
            serde_json::json!({"v": 1, "t": "unlocks-is", "id": id, "ids": ids})
        }
        _ => return err("unknown-type", "unknown t", id_of(o)),
    }
}
