# textack/core/story.py
"""Waifu roster, per-wave dialog, affection. Pure logic, no curses.

Phase 1: dialog per wave (English) + bond/affection + multi-waifu unlock.
Phase 2 hooks: side-quest choices + chat mode (see SIDENOTE at bottom).
"""

WAIFU_ORDER = ["aika", "rin", "sora"]

UNLOCK_WAVE = {"aika": 1, "rin": 4, "sora": 8}

BOND_LEVELS = [
    (0, "Stranger"),
    (30, "Friend"),
    (80, "Close"),
    (150, "Trusted"),
    (250, "Soulmate"),
]

BOND_GAIN = {"hit": 1.0, "perfect": 2.0, "clear": 5.0, "miss": -1.0}

WAIFUS = {
    "aika": {
        "name": "AIKA",
        "title": "Operator",
        "faces": {"idle": "(・‿・)", "happy": "(≧▽≦)", "sad": "(>_<)", "hurt": "(T_T)", "excited": "(☆▽☆)"},
        "idle": [
            "Type fast = big damage, senpai!",
            "PERFECT hits land inside the gold window.",
            "Combo is just crit with extra steps!",
        ],
        "wave": [
            "Wave {wave}! {enemy} incoming — type fast, senpai!",
            "{enemy} spotted at wave {wave}. Eyes on the keys!",
            "Wave {wave} — show this {enemy} what we're made of!",
            "Here comes wave {wave}! Don't blink, don't typo!",
            "{enemy} at wave {wave}. I believe in your fingers!",
            "Wave {wave}, let's go! Speed is our armor!",
        ],
        "boss": [
            "BOSS at wave {wave}! This {enemy} is huge — focus!",
            "Wave {wave} boss: {enemy}. Deep breath. Perfect aim!",
            "Careful, senpai — {enemy} hits like a truck!",
        ],
        "clear": [
            "Wave clear! Sugoi, senpai!",
            "Did you see that explosion? Nice shot!",
            "Enemy fortress dented. Onward!",
        ],
        "defeat": [
            "Our fortress... don't cry, we'll rebuild!",
            "It's okay, senpai. One more run?",
        ],
        "happy": ["Sugoi! Direct hit!", "Nice shot, senpai!", "Combo rising!"],
        "sad": ["Baka... that was a miss!", "Focus, senpai!", "Combo reset..."],
        "hurt": ["Itai! Protect the base!", "Our fortress is burning!", "Kyaa!"],
        "excited": ["Level up! We're getting stronger!", "Power rising!", "Yosha!"],
        "unlock_line": None,
    },
    "rin": {
        "name": "RIN",
        "title": "Sniper",
        "faces": {"idle": "(￣_￣)", "happy": "(￣▽￣)", "sad": "(￣ヘ￣)", "hurt": "(>_<;)", "excited": "(☆_☆)"},
        "idle": [
            "Slow is smooth. Smooth is fast.",
            "One word. One bullet.",
            "Accuracy first. Speed follows.",
        ],
        "wave": [
            "Wave {wave}. {enemy} on scope. Breathe. Type.",
            "{enemy} at wave {wave}. Wind calm. Fire.",
            "Wave {wave}. I count six typos before breakfast. Make none.",
            "Target: {enemy}. Wave {wave}. Execute.",
            "Wave {wave} — patience, hunter. Then strike.",
            "{enemy} approaches. Wave {wave}. Steady...",
        ],
        "boss": [
            "Boss. {enemy}, wave {wave}. One shot, one kill.",
            "Wave {wave}: {enemy}. Aim for the weak syllable.",
            "Big target. Can't miss. ...Don't miss.",
        ],
        "clear": [
            "Target neutralized. Next.",
            "Clean shot. As expected.",
            "Wave clear. Reloading fingers.",
        ],
        "defeat": [
            "Missed the vital point... again soon.",
            "Retreat is also a tactic. Regroup.",
        ],
        "happy": ["Bullseye.", "Clean hit.", "As calculated."],
        "sad": ["Tch. Missed.", "Recalibrating.", "Wind... my fault."],
        "hurt": ["Guh—! Base armor failing!", "Damage report, now!", "They found our range!"],
        "excited": ["New scope acquired. Stronger.", "Upgraded. Lethal.", "Hm. Not bad."],
        "unlock_line": "RIN here. Wave {wave} reached — I'll cover your typos. Don't waste my bullets.",
    },
    "sora": {
        "name": "SORA",
        "title": "Engineer",
        "faces": {"idle": "(＾▽＾)", "happy": "(⌒▽⌒)", "sad": "(T_T;)", "hurt": "(;_;)", "excited": "(≧◡≦)"},
        "idle": [
            "I tuned the turret! It shoots by itself now!",
            "Did you know? Typing burns calories. Probably.",
            "Wrench + keyboard = victory!",
        ],
        "wave": [
            "Ooh, wave {wave}! Let's dismantle this {enemy}!",
            "{enemy}? At wave {wave}? My turret's been waiting!",
            "Wave {wave}! I oiled the keys for maximum speed!",
            "Behold, wave {wave}! Science vs {enemy} — science wins!",
            "Wave {wave} incoming! Hold my wrench!",
            "{enemy} at wave {wave}. Time for field testing!",
        ],
        "boss": [
            "WHOA, big {enemy} at wave {wave}! My favorite kind!",
            "Boss wave {wave}! Let me overclock... the keyboard!",
            "{enemy}?! Finally, a worthy experiment!",
        ],
        "clear": [
            "BOOM! Did you see that?!",
            "Experiment: success! Hypothesis: we're awesome!",
            "Wave clear! Turret high-five!",
        ],
        "defeat": [
            "The base... my beautiful base... rebuild! Improve!",
            "Test failed! Adjust variables! Retry!",
        ],
        "happy": ["Eureka! Hit!", "Science prevails!", "Woohoo!"],
        "sad": ["Oopsie... misfire!", "Bug in the system! Your fingers!", "Recalibrate the human!"],
        "hurt": ["My turret!! Our base!!", "Hull breach! Grab a wrench!", "Eeeek!"],
        "excited": ["UPGRADE! *excited wrench noises*", "New gadget installed!", "Power output doubled! Ish!"],
        "unlock_line": "SORA reporting! You hit wave {wave} — that deserves automated firepower! Turret online!",
    },
}


def get_waifu(wid):
    return WAIFUS.get(wid) or WAIFUS["aika"]


def line_for(wid, trigger, ctx=None, seed=0):
    """Pick a dialog line. ctx may hold wave/enemy for {placeholders}."""
    w = get_waifu(wid if wid in WAIFUS else "aika")
    pool = w.get(trigger) or w["idle"]
    line = pool[seed % len(pool)]
    ctx = ctx or {}
    try:
        return line.format(wave=ctx.get("wave", "?"), enemy=ctx.get("enemy", "enemy"))
    except (IndexError, KeyError):
        return line


def mood_line(wid, mood, seed=0):
    w = get_waifu(wid if wid in WAIFUS else "aika")
    pool = w.get(mood) or w["idle"]
    return pool[seed % len(pool)]


def level_for(bond):
    lv = 0
    for i, (thr, _title) in enumerate(BOND_LEVELS):
        if bond >= thr:
            lv = i
    return lv


def title_for(bond):
    return BOND_LEVELS[level_for(bond)][1]


def check_unlocks(unlocked, wave):
    """Ids newly unlocked by reaching `wave` (keeps WAIFU_ORDER)."""
    have = set(unlocked or ["aika"])
    return [wid for wid in WAIFU_ORDER if wid not in have and wave >= UNLOCK_WAVE.get(wid, 999)]


def resolve_active(argv=None, env=None, state=None):
    """Priority: --waifu flag > TEXTACK_WAIFU env > saved state > aika."""
    want = None
    argv = list(argv or [])
    for i, a in enumerate(argv):
        if a.startswith("--waifu="):
            want = a.split("=", 1)[1].strip().lower()
        elif a == "--waifu" and i + 1 < len(argv):
            want = argv[i + 1].strip().lower()
    if not want and env:
        want = (env.get("TEXTACK_WAIFU") or "").strip().lower() or None
    unlocked = (state or {}).get("unlocked") or ["aika"]
    if want in WAIFUS and want in unlocked:
        return want
    saved = (state or {}).get("active")
    if saved in WAIFUS and saved in unlocked:
        return saved
    return "aika"


# SIDENOTE phase 2: side-quest choices + chat mode plug in here as pure
# functions, e.g. quest_offer(wid, wave, bond) -> {prompt, options[]}
# and chat_reply(wid, bond, text) -> str. UI screens stay thin.
