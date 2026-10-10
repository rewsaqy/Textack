//! Pure game math mirroring `textack/core/*` exactly (operation order kept so
//! floats are bit-identical). String tables are copied verbatim from
//! `textack/core/story.py` and `upgrades.py`.

use crate::mt::Mt;

// ---------------- combat ----------------

pub struct Stats {
    pub dmg_mult: f64,
    pub crit: f64,
    pub crit_mult: f64,
    pub perfect_win: f64,
    pub max_hp: f64,
    pub regen: f64,
    pub shield: f64,
    pub repair: f64,
    pub lifesteal: f64,
    pub xp_mult: f64,
    pub slow: f64,
    pub combo_guard: f64,
    pub turret: i64,
    pub turret_dmg: f64,
    pub double: f64,
    pub speed_bonus: i64,
    pub wall: i64,
}

pub struct Hit {
    pub dmg: i64,
    pub tag: String,
    pub wpm: f64,
    pub speed_bonus: i64,
    pub perfect: bool,
    pub crit: bool,
    pub double: bool,
}

pub fn resolve_hit(
    target: &str,
    buf: &str,
    elapsed_raw: f64,
    combo: i64,
    st: &Stats,
    rng: &mut Mt,
) -> Option<Hit> {
    if buf != target {
        return None;
    }
    let elapsed = elapsed_raw.max(0.05);
    let nchars = target.chars().count() as f64;
    let wpm = (nchars / 5.0) / (elapsed / 60.0);
    let base = target.chars().count() as i64 * 3;
    let perfect = elapsed < st.perfect_win;
    let speed_bonus = (0i64).max((25.0 - elapsed * 4.0) as i64)
        + st.speed_bonus
        + if perfect { 15 } else { 0 };
    let is_crit = rng.random() < st.crit;
    let is_double = rng.random() < st.double;
    let mult = (1.0 + (combo + 1).min(10) as f64 * 0.1) * st.dmg_mult;
    let mut dmg = ((base + speed_bonus) as f64 * mult) as i64;
    if is_crit {
        dmg = (dmg as f64 * st.crit_mult) as i64;
    }
    if is_double {
        dmg = (dmg as f64 * 2.0) as i64;
    }
    let mut tag = String::new();
    if perfect {
        tag.push_str(" PERFECT");
    }
    if is_crit {
        tag.push_str(" CRIT");
    }
    if is_double {
        tag.push_str(" x2");
    }
    Some(Hit { dmg, tag, wpm, speed_bonus, perfect, crit: is_crit, double: is_double })
}

pub fn combo_step(hit: bool, combo: i64, guard: f64, rng_value: Option<f64>, live: &mut Mt) -> i64 {
    if hit {
        return combo + 1;
    }
    let v = match rng_value {
        Some(x) => x,
        None => live.random(),
    };
    if v < guard { combo } else { 0 }
}

pub fn miss_damage(enemy_dmg: i64, wave: i64, bonus: i64) -> i64 {
    enemy_dmg + wave + bonus
}

// ---------------- progression ----------------

pub fn rank_for(wpm: f64, combo: i64) -> &'static str {
    if combo >= 10 || wpm >= 90.0 {
        "KERNEL PANIC"
    } else if combo >= 7 || wpm >= 70.0 {
        "ROOT"
    } else if combo >= 5 || wpm >= 55.0 {
        "SYSADMIN"
    } else if combo >= 3 || wpm >= 40.0 {
        "POWER USER"
    } else if wpm >= 25.0 {
        "SCRIPT KIDDIE"
    } else {
        "NEWBIE"
    }
}

pub fn next_threshold(current: f64) -> f64 {
    current * 1.45 + 10.0
}

pub fn gain_xp(word_len: i64, wave: i64, xp_mult: f64, is_boss: bool) -> f64 {
    ((word_len * 2 + wave * 2) as f64) * xp_mult * if is_boss { 2.0 } else { 1.0 }
}

// ---------------- enemies ----------------

pub struct EnemyConfig {
    pub name: String,
    pub interval: f64,
    pub dmg: i64,
    pub burst: i64,
    pub hp: i64,
    pub proj: &'static str,
    pub col: &'static str,
}

pub fn for_wave(wave: i64) -> EnemyConfig {
    let is_boss = wave % 5 == 0;
    let (mut name, mut interval, mut dmg, mut burst, mut hp, proj, col) = if wave <= 2 {
        ("SCOUT", 6.5, 6, 1, 60 + wave * 35, "▼", "yellow")
    } else if wave <= 4 {
        ("RAIDER", 5.2, 8, 1, 70 + wave * 42, "●", "yellow")
    } else if wave <= 6 {
        ("GOLEM", 4.3, 10, 2, 80 + wave * 48, "✦", "red")
    } else {
        ("OVERLORD", 3.5, 12, 3, 90 + wave * 55, "✹", "red")
    };
    let mut interval: f64 = interval;
    let mut out_name: String;
    if is_boss {
        out_name = format!("BOSS {name}");
        interval = (interval * 0.85).max(2.6f64);
        dmg += 3;
        burst = (burst + 1).min(4);
        hp = (hp as f64 * 1.7) as i64;
    } else {
        out_name = name.to_string();
    }
    interval = (interval - (0i64.max(wave - 7)) as f64 * 0.12).max(2.6);
    EnemyConfig { name: out_name, interval, dmg, burst, hp, proj, col }
}

// ---------------- upgrades ----------------

pub struct Upgrade {
    pub id: &'static str,
    pub max: i64,
}

pub const REGISTRY: [Upgrade; 14] = [
    Upgrade { id: "ammo", max: 8 },
    Upgrade { id: "crit", max: 5 },
    Upgrade { id: "perfect", max: 5 },
    Upgrade { id: "double", max: 5 },
    Upgrade { id: "adren", max: 5 },
    Upgrade { id: "wall", max: 8 },
    Upgrade { id: "regen", max: 5 },
    Upgrade { id: "shield", max: 5 },
    Upgrade { id: "repair", max: 5 },
    Upgrade { id: "slow", max: 5 },
    Upgrade { id: "guard", max: 3 },
    Upgrade { id: "magnet", max: 5 },
    Upgrade { id: "turret", max: 5 },
    Upgrade { id: "vamp", max: 5 },
];

pub fn apply(uid: &str, st: &mut Stats) -> bool {
    match uid {
        "ammo" => st.dmg_mult *= 1.15,
        "crit" => st.crit = (st.crit + 0.10).min(0.6),
        "perfect" => st.perfect_win += 0.25,
        "double" => st.double = (st.double + 0.12).min(0.6),
        "adren" => st.speed_bonus += 6,
        "wall" => {
            st.max_hp += 25.0;
            st.wall += 1;
        }
        "regen" => st.regen += 0.8,
        "shield" => st.shield = (st.shield + 0.12).min(0.6),
        "repair" => st.repair += 4.0,
        "slow" => st.slow += 0.08,
        "guard" => st.combo_guard = (st.combo_guard + 0.30).min(0.9),
        "magnet" => st.xp_mult *= 1.25,
        "turret" => {
            st.turret += 1;
            st.turret_dmg += 14.0;
        }
        "vamp" => st.lifesteal += 1.0,
        _ => return false,
    }
    true
}

pub fn roll_ids(owned: &[(String, i64)], k: usize, rng: &mut Mt) -> Vec<&'static str> {
    let mut avail: Vec<&'static str> = REGISTRY
        .iter()
        .filter(|u| owned.iter().find(|(id, _)| id == u.id).map(|(_, n)| *n).unwrap_or(0) < u.max)
        .map(|u| u.id)
        .collect();
    rng.shuffle(&mut avail);
    avail.truncate(k);
    avail
}

// ---------------- story (data verbatim from core/story.py) ----------------

pub const WAIFU_ORDER: [&str; 3] = ["aika", "rin", "sora"];

fn unlock_wave(wid: &str) -> i64 {
    match wid {
        "aika" => 1,
        "rin" => 4,
        "sora" => 8,
        _ => 999,
    }
}

struct Waifu {
    name: &'static str,
    idle: &'static [&'static str],
    wave: &'static [&'static str],
    boss: &'static [&'static str],
    clear: &'static [&'static str],
    defeat: &'static [&'static str],
    happy: &'static [&'static str],
    sad: &'static [&'static str],
    hurt: &'static [&'static str],
    excited: &'static [&'static str],
    unlock_line: Option<&'static str>,
}

const AIKA: Waifu = Waifu {
    name: "AIKA",
    idle: &[
        "Type fast = big damage, senpai!",
        "PERFECT hits land inside the gold window.",
        "Combo is just crit with extra steps!",
    ],
    wave: &[
        "Wave {wave}! {enemy} incoming — type fast, senpai!",
        "{enemy} spotted at wave {wave}. Eyes on the keys!",
        "Wave {wave} — show this {enemy} what we're made of!",
        "Here comes wave {wave}! Don't blink, don't typo!",
        "{enemy} at wave {wave}. I believe in your fingers!",
        "Wave {wave}, let's go! Speed is our armor!",
    ],
    boss: &[
        "BOSS at wave {wave}! This {enemy} is huge — focus!",
        "Wave {wave} boss: {enemy}. Deep breath. Perfect aim!",
        "Careful, senpai — {enemy} hits like a truck!",
    ],
    clear: &[
        "Wave clear! Sugoi, senpai!",
        "Did you see that explosion? Nice shot!",
        "Enemy fortress dented. Onward!",
    ],
    defeat: &[
        "Our fortress... don't cry, we'll rebuild!",
        "It's okay, senpai. One more run?",
    ],
    happy: &["Sugoi! Direct hit!", "Nice shot, senpai!", "Combo rising!"],
    sad: &["Baka... that was a miss!", "Focus, senpai!", "Combo reset..."],
    hurt: &["Itai! Protect the base!", "Our fortress is burning!", "Kyaa!"],
    excited: &["Level up! We're getting stronger!", "Power rising!", "Yosha!"],
    unlock_line: None,
};

const RIN: Waifu = Waifu {
    name: "RIN",
    idle: &[
        "Slow is smooth. Smooth is fast.",
        "One word. One bullet.",
        "Accuracy first. Speed follows.",
    ],
    wave: &[
        "Wave {wave}. {enemy} on scope. Breathe. Type.",
        "{enemy} at wave {wave}. Wind calm. Fire.",
        "Wave {wave}. I count six typos before breakfast. Make none.",
        "Target: {enemy}. Wave {wave}. Execute.",
        "Wave {wave} — patience, hunter. Then strike.",
        "{enemy} approaches. Wave {wave}. Steady...",
    ],
    boss: &[
        "Boss. {enemy}, wave {wave}. One shot, one kill.",
        "Wave {wave}: {enemy}. Aim for the weak syllable.",
        "Big target. Can't miss. ...Don't miss.",
    ],
    clear: &[
        "Target neutralized. Next.",
        "Clean shot. As expected.",
        "Wave clear. Reloading fingers.",
    ],
    defeat: &[
        "Missed the vital point... again soon.",
        "Retreat is also a tactic. Regroup.",
    ],
    happy: &["Bullseye.", "Clean hit.", "As calculated."],
    sad: &["Tch. Missed.", "Recalibrating.", "Wind... my fault."],
    hurt: &["Guh—! Base armor failing!", "Damage report, now!", "They found our range!"],
    excited: &["New scope acquired. Stronger.", "Upgraded. Lethal.", "Hm. Not bad."],
    unlock_line: Some("RIN here. Wave {wave} reached — I'll cover your typos. Don't waste my bullets."),
};

const SORA: Waifu = Waifu {
    name: "SORA",
    idle: &[
        "I tuned the turret! It shoots by itself now!",
        "Did you know? Typing burns calories. Probably.",
        "Wrench + keyboard = victory!",
    ],
    wave: &[
        "Ooh, wave {wave}! Let's dismantle this {enemy}!",
        "{enemy}? At wave {wave}? My turret's been waiting!",
        "Wave {wave}! I oiled the keys for maximum speed!",
        "Behold, wave {wave}! Science vs {enemy} — science wins!",
        "Wave {wave} incoming! Hold my wrench!",
        "{enemy} at wave {wave}. Time for field testing!",
    ],
    boss: &[
        "WHOA, big {enemy} at wave {wave}! My favorite kind!",
        "Boss wave {wave}! Let me overclock... the keyboard!",
        "{enemy}?! Finally, a worthy experiment!",
    ],
    clear: &[
        "BOOM! Did you see that?!",
        "Experiment: success! Hypothesis: we're awesome!",
        "Wave clear! Turret high-five!",
    ],
    defeat: &[
        "The base... my beautiful base... rebuild! Improve!",
        "Test failed! Adjust variables! Retry!",
    ],
    happy: &["Eureka! Hit!", "Science prevails!", "Woohoo!"],
    sad: &["Oopsie... misfire!", "Bug in the system! Your fingers!", "Recalibrate the human!"],
    hurt: &["My turret!! Our base!!", "Hull breach! Grab a wrench!", "Eeeek!"],
    excited: &["UPGRADE! *excited wrench noises*", "New gadget installed!", "Power output doubled! Ish!"],
    unlock_line: Some("SORA reporting! You hit wave {wave} — that deserves automated firepower! Turret online!"),
};

fn waifu(wid: &str) -> &'static Waifu {
    match wid {
        "rin" => &RIN,
        "sora" => &SORA,
        _ => &AIKA,
    }
}

fn pool<'a>(w: &'a Waifu, trigger: &str) -> &'a [&'static str] {
    match trigger {
        "wave" if !w.wave.is_empty() => w.wave,
        "boss" if !w.boss.is_empty() => w.boss,
        "clear" if !w.clear.is_empty() => w.clear,
        "defeat" if !w.defeat.is_empty() => w.defeat,
        "happy" if !w.happy.is_empty() => w.happy,
        "sad" if !w.sad.is_empty() => w.sad,
        "hurt" if !w.hurt.is_empty() => w.hurt,
        "excited" if !w.excited.is_empty() => w.excited,
        _ => w.idle,
    }
}

fn fill(line: &str, wave: Option<i64>, enemy: Option<&str>) -> String {
    let w = match wave {
        Some(n) => n.to_string(),
        None => "?".to_string(),
    };
    line.replace("{wave}", &w).replace("{enemy}", enemy.unwrap_or("enemy"))
}

pub fn line_for(wid: &str, trigger: &str, wave: Option<i64>, enemy: Option<&str>, seed: u64) -> String {
    let w = waifu(wid);
    let p = pool(w, trigger);
    fill(p[(seed as usize) % p.len()], wave, enemy)
}

pub fn mood_line(wid: &str, mood: &str, seed: u64) -> String {
    let w = waifu(wid);
    let p = pool(w, mood);
    p[(seed as usize) % p.len()].to_string()
}

pub fn unlock_line(wid: &str) -> Option<&'static str> {
    waifu(wid).unlock_line
}

pub fn waifu_name(wid: &str) -> &'static str {
    waifu(wid).name
}

pub fn level_for(bond: f64) -> i64 {
    let th = [0.0, 30.0, 80.0, 150.0, 250.0];
    let mut lv = 0;
    for (i, t) in th.iter().enumerate() {
        if bond >= *t {
            lv = i as i64;
        }
    }
    lv
}

pub fn check_unlocks(unlocked: &[String], wave: i64) -> Vec<&'static str> {
    WAIFU_ORDER
        .iter()
        .filter(|wid| !unlocked.iter().any(|u| u == *wid) && wave >= unlock_wave(wid))
        .copied()
        .collect()
}
