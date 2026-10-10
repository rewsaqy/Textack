# textack/ui/screens/siege.py
"""Siege loop: typing = damage.

Render/particle/star/shake code; math delegated per call site: classic
core/* by default, or the polyglot EngineDirector under
--engine=polyglot (identical answers, see textack/engine/director.py).
Trivial pure helpers and CLI/env lookups stay on core/* directly.
"""
import curses
import math
import os
import random
import sys
import time

from textack import VERSION
from textack.core import combat, enemies, progression, story, upgrades, words
from textack.engine import mode as engine_mode
from textack.infra import quality, storage, waifu
from textack.infra import sfx as sfx_mod
from textack.ui import face as face_mod
from textack.ui import gfx, guard, widgets
from textack.ui.screens import upgrade as upgrade_screen
from textack.ui.widgets import get_field

ENEMY_ART_A = [
    r"  █ █ █ █ █ █ █ █  ",
    r"  █████████████████  ",
    r"  ██▒▒▒██░██▒▒▒██  ",
    r"  █████████████████  ",
    r"  ██████▓▓▓██████  ",
    r"  ██████▓▓▓██████  ",
    r"  █████████████████  ",
]
ENEMY_ART_B = [
    r"  █ █ █ █ █ █ █ █  ",
    r"  █████████████████  ",
    r"  ██▓▓▓██░██▓▓▓██  ",
    r"  █████████████████  ",
    r"  ██████▒▒▒██████  ",
    r"  ██████▒▒▒██████  ",
    r"  █████████████████  ",
]
PLAYER_ART = [
    r"     ███████████     ",
    r"   █████████████████   ",
    r"   ███░█████░█████   ",
    r"   █████████████████   ",
    r"   ██░██░███░██░███   ",
]
# 5-row arcade pixel numerals (strike countdown), 3 cols each.
PX_DIGITS = {
    0: ["███", "█ █", "█ █", "█ █", "███"],
    1: [" █ ", " █ ", " █ ", " █ ", " █ "],
    2: ["███", "  █", "███", "█  ", "███"],
    3: ["███", "  █", "███", "  █", "███"],
    4: ["█ █", "█ █", "███", "  █", "  █"],
    5: ["███", "█  ", "███", "  █", "███"],
}


def show(stdscr, P):
    stdscr.nodelay(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    # quality: default MED (safe on low-end). F2 = cycle manually,
    # auto-drops when the frame time gets heavy.
    qi = quality.from_env(sys.argv[1:], os.environ)
    frame_ms = max(1, int(1000 / quality.QLEVELS[qi]["fps"]))
    stdscr.timeout(frame_ms)
    ema_dt = 1.0 / quality.QLEVELS[qi]["fps"]
    qcheck_t = 0.0
    fps_show = float(quality.QLEVELS[qi]["fps"])
    # engine routing: polyglot fleet or classic core (identical answers).
    # The fleet boots workers once; every exit path below closes them.
    _sup = None
    D = None
    _boot_msg = None
    _boot_msg_t = 3.0
    if engine_mode.active(sys.argv[1:], os.environ) == engine_mode.POLYGLOT:
        try:
            from textack.engine import supervisor as _sup_mod
            _sup = _sup_mod.Supervisor.from_repo()
            D = _sup.director()
            _boot_msg = _sup.summary() + " (F5 reloads content)"
            _boot_msg_t = 4.0
        except Exception as e:  # noqa: BLE001
            D = None
            _sup = None
            _boot_msg = f"Engine boot failed ({e}) — classic mode"
    if D is not None:
        r_hit = D.resolve_hit
        r_combo = D.combo_step
        r_counter = D.miss_damage
        r_xp = D.gain_xp
        r_next = D.next_threshold
        r_rank = D.rank_for
        r_wave = D.for_wave
        r_pick = D.pick_word
        r_apply = D.apply
        r_roll = D.roll_choices
        r_line = D.line_for
        r_mood = D.mood_line
        r_unlocks = D.check_unlocks
    else:
        r_hit = combat.resolve_hit
        r_combo = combat.combo_step
        r_counter = combat.miss_damage
        r_xp = progression.gain_xp
        r_next = progression.next_threshold
        r_rank = progression.rank_for
        r_wave = enemies.for_wave
        r_pick = words.pick_word
        r_apply = upgrades.apply
        r_roll = upgrades.roll_choices
        r_line = story.line_for
        r_mood = story.mood_line
        r_unlocks = story.check_unlocks

    def _close_sup():
        if _sup is not None:
            try:
                _sup.close()
            except Exception:  # noqa: BLE001, S110
                pass

    def sfx_play(name):
        if D is not None:
            D.sfx_trigger(name)
        else:
            sfx_mod.play(stdscr, sfx, name)
    wave = 1
    stats = upgrades.fresh_stats()
    owned = {}
    base_lv = 0
    ecfg = r_wave(1)
    enemy_max = float(ecfg.hp)
    player_max = float(stats["max_hp"])
    enemy_hp = float(enemy_max)
    player_hp = float(player_max)
    disp_e = float(enemy_max)
    disp_p = float(player_max)

    target = r_pick(wave)
    buf = ""
    word_start = time.monotonic()
    combo = 0
    best_combo = 0
    shots = hits = 0
    correct_chars_total = 0
    time_total = 0.0
    # XP / level, Survivor-style
    xp = 0.0
    xp_next = 30.0
    level = 1
    pending_lv = 0
    turret_t = 0.0
    banner = ""
    banner_t = 0.0
    last_flash_on = False
    # sound + operator state
    sfx = sfx_mod.init()
    wstate = storage.load_waifu()
    waifu_id = story.resolve_active(sys.argv[1:], os.environ, wstate)
    winfo = story.get_waifu(waifu_id)
    waifu_art = waifu.load_art_for(waifu_id)
    face_rgb = waifu.load_rgb_for(waifu_id)
    face_ok = face_rgb is not None
    if face_rgb:
        face_nw, face_nh, face_px = face_rgb
    else:
        face_nw, face_nh, face_px = 0, 0, []
    face_cache_key = None
    face_cells = []
    face_pairs = {}
    gfx_mode = gfx.resolve(sys.argv[1:], os.environ)
    photo_path = waifu.find_photo(waifu_id) if gfx_mode == "kitty" else None
    photo_id = 10 + (story.WAIFU_ORDER.index(waifu_id) if waifu_id in story.WAIFU_ORDER else 0)
    photo_sent = False
    photo_geom = None
    bond = float(wstate.get("bond", {}).get(waifu_id, 0.0))
    wmood = "idle"
    wmood_t = 0.0
    wline = 0
    wstory = ""
    wstory_t = 0.0
    # Best score kept in memory; disk only written when beaten (perf:
    # avoids a read+write+mkdir on every single hit).
    best_mem = storage.load_best()
    # Cached per-frame values (recomputed only when inputs change).
    cur_interval = quality.effective_interval(ecfg.interval, stats["slow"])
    rk_live = "NEWBIE"
    rk_t = -10.0
    rk_combo = -1
    rk_avg_q = -1.0
    idle_seed_cache = -1
    idle_line_cache = ""

    def maybe_save_best(wv, wpm):
        if storage.beats_best(best_mem, wv, wpm):
            best_mem["wave"] = wv
            best_mem["wpm"] = wpm
            storage.save_best(storage.DEFAULT_BEST, wv, wpm)

    def save_waifu_state():
        wstate["active"] = waifu_id
        if waifu_id not in wstate.get("unlocked", []):
            wstate["unlocked"] = [*wstate.get("unlocked", []), waifu_id]
        wstate.setdefault("bond", {})[waifu_id] = max(0.0, bond)
        storage.save_waifu(storage.DEFAULT_WAIFU, wstate)

    def set_story(text, dur=3.5):
        nonlocal wstory, wstory_t
        wstory = text
        wstory_t = dur

    def set_mood(m, dur):
        nonlocal wmood, wmood_t, wline
        wmood = m
        wmood_t = dur
        wline = random.randrange(99)

    MAXP = quality.QLEVELS[qi]["maxp"]
    projectiles = []
    particles = []
    floaters = []
    stars = []
    shake_t = 0.0
    shake_mag = 0
    enemy_timer = 0.0
    msg = _boot_msg or "Type + Enter to shoot! :q quits (F2 quality • F3 sound)"
    msg_t = _boot_msg_t
    flash = 0.0
    # camera + impact feel (Atari juice): hit-stop freezes the world for a
    # few frames on impact, kick_y punches the whole scene up/down.
    hitstop = 0.0
    recoil_t = 0.0
    kick_y = 0.0
    grace_t = 0.0
    last = time.monotonic()

    def set_quality(nqi):
        nonlocal qi, MAXP, frame_ms, stars
        qi = max(0, min(2, nqi))
        MAXP = quality.QLEVELS[qi]["maxp"]
        frame_ms = max(1, int(1000 / quality.QLEVELS[qi]["fps"]))
        stdscr.timeout(frame_ms)
        # trim stars & particles to the new budget (instantly lighter)
        hq, wq = stdscr.getmaxyx()
        want = min(60, max(8, (wq * hq) // quality.QLEVELS[qi]["stars_div"]))
        if len(stars) > want:
            del stars[want:]
        if len(particles) > MAXP:
            del particles[0: len(particles) - MAXP]

    def new_wave(w):
        nonlocal enemy_max, enemy_hp, disp_e, target, buf, word_start, enemy_timer, ecfg, banner, banner_t, cur_interval, grace_t
        ecfg = r_wave(w)
        enemy_max = float(ecfg.hp)
        enemy_hp = float(enemy_max)
        disp_e = float(enemy_max)
        target = r_pick(w)
        buf = ""
        word_start = time.monotonic()
        enemy_timer = 0.0
        cur_interval = quality.effective_interval(ecfg.interval, stats["slow"])
        banner = f"WAVE {w} — {ecfg.name}"
        banner_t = 1.6
        grace_t = 1.2  # cinematic breather: enemy holds fire, banner shows
        trig = "boss" if w % 5 == 0 else "wave"
        set_story(r_line(waifu_id, trig, {"wave": w, "enemy": ecfg.name}, random.randrange(999)), 4.0)

    def add_particle(p):
        if len(particles) >= MAXP:
            # drop oldest so fps stays stable
            del particles[0: len(particles) - MAXP + 1]
        particles.append(p)

    def spawn_explosion(x, y, color, n=22):
        n = max(3, min(40, int(n * quality.QLEVELS[qi]["boom"])))
        for _ in range(n):
            add_particle({
                "x": x, "y": float(y),
                "vx": random.uniform(-18, 18),
                "vy": random.uniform(-10, 10),
                "life": random.uniform(0.3, 0.8), "max": 0.8,
                "char": random.choice(["*", ".", "+", "o", "#", "▓", "▒", "░"]),
                "attr": color,
            })

    def spawn_ring(x, y, color, n=18, speed=26):
        """Circular shockwave burst (kill / combo milestone)."""
        n = max(4, n)
        for i in range(n):
            ang = (2 * math.pi * i) / n
            add_particle({
                "x": x, "y": float(y),
                "vx": speed * random.uniform(0.7, 1.2) * math.cos(ang),
                "vy": speed * random.uniform(0.7, 1.2) * math.sin(ang) * 0.6,
                "life": random.uniform(0.35, 0.6), "max": 0.6,
                "char": random.choice(["o", "*", "·"]),
                "attr": color,
            })

    new_wave(1)
    # adaptive starfield (cheap animation, 1 addstr per star)
    h0, w0 = stdscr.getmaxyx()
    stars = [{"x": random.random() * max(1, w0), "y": random.random() * max(1, h0),
              "sp": random.uniform(2, 10)} for _ in range(min(60, max(8, (w0 * h0) // quality.QLEVELS[qi]["stars_div"])))]

    while True:
        now = time.monotonic()
        raw_dt = min(0.05, now - last)
        last = now
        if hitstop > 0:
            hitstop -= raw_dt
            dt = 0.0  # world frozen, still rendering (classic hit-stop)
        else:
            dt = raw_dt
        h, w = stdscr.getmaxyx()
        size = (h, w)
        cx = w // 2
        if guard.too_small(h, w):
            if guard.wait_until_fit(stdscr, P) == "quit":
                save_waifu_state()
                _close_sup()
                return
            stdscr.nodelay(True)
            stdscr.timeout(frame_ms)
            last = time.monotonic()
            continue
        # auto quality: EMA frame time, checked every 2s (cheap on low-end)
        ema_dt = ema_dt * 0.95 + raw_dt * 0.05
        fps_show = fps_show * 0.95 + (1.0 / max(raw_dt, 1e-3)) * 0.05
        qcheck_t += raw_dt
        if qcheck_t >= 2.0:
            qcheck_t = 0.0
            if ema_dt > 1.0 / (quality.QLEVELS[qi]["fps"] * 0.75) and qi < 2:
                set_quality(qi + 1)
                msg = f"Power-saver on ({quality.QLEVELS[qi]['name']}) to keep it smooth"
                msg_t = 2.0
            # stays LOW once the user/device is low-end, never auto-upgrades

        # refresh cached attack interval when slow stat may have changed
        cur_interval = quality.effective_interval(ecfg.interval, stats["slow"])

        key = stdscr.getch()
        while key != -1:
            if key == 27:
                save_waifu_state()
                _close_sup()
                return
            elif key == curses.KEY_F2:
                # F2 = cycle quality manually (F-keys are > 255, never clash)
                set_quality((qi + 1) % 3)
                msg = f"Quality: {quality.QLEVELS[qi]['name']} {quality.QLEVELS[qi]['fps']}fps (F2 changes)"
                msg_t = 2.0
            elif key == curses.KEY_F3:
                sfx["on"] = not sfx["on"]
                if D is not None:
                    D.sfx_set(sfx["on"])
                msg = f"Sound: {'ON' if sfx['on'] else 'OFF'} (F3 changes)"
                msg_t = 2.0
            elif key == curses.KEY_F5:
                if D is not None:
                    ver, errs = D.content_reload()
                    if errs:
                        msg = f"Reload kept v{ver}: {str(errs[0])[:44]}"
                    else:
                        msg = f"Content v{ver} reloaded live"
                else:
                    msg = "Classic engine: no content worker (try --engine=polyglot)"
                msg_t = 2.5
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                buf = buf[:-1]
            elif key in (curses.KEY_ENTER, 10, 13):
                elapsed = max(0.05, now - word_start)
                if buf.strip() == ":q":
                    save_waifu_state()
                    _close_sup()
                    return
                shots += 1
                time_total += elapsed
                if buf == target:
                    r = r_hit(target, buf, elapsed, combo, stats, wave)
                    combo += 1
                    best_combo = max(best_combo, combo)
                    dmg, tag, wpm = r.dmg, r.tag, r.wpm
                    perfect = r.perfect
                    hits += 1
                    correct_chars_total += len(target)
                    projectiles.append({"x": cx, "y": h - 8.0, "vy": -34.0,
                                        "char": "▲", "attr": P["green"],
                                        "pending": float(dmg), "side": "player",
                                        "label": f"-{dmg}{tag} {wpm:.0f}wpm"})
                    # cheap muzzle flash: 4 short particles at the base muzzle
                    for _ in range(4):
                        add_particle({"x": cx + random.uniform(-1.5, 1.5), "y": float(h - 8),
                                              "vx": random.uniform(-6, 6), "vy": random.uniform(-14, -4),
                                              "life": 0.22, "max": 0.22,
                                              "char": random.choice(["*", "+", "."]), "attr": P["yellow"]})
                    msg = f"HIT -{dmg}{tag} | {elapsed:.2f}s | {wpm:.0f} WPM | combo {combo}"
                    msg_t = 1.6
                    enemy_timer = 0.0
                    recoil_t = 0.12  # base kicks back one row for a few frames
                    hitstop = max(hitstop, 0.045)  # impact freeze
                    kick_y = max(-3.0, kick_y - 1.0)  # camera punches upward
                    sfx_play("shoot")
                    if combo % 5 == 0:
                        floaters.append({"x": cx - 5, "y": 11.0, "text": f"COMBO x{combo}!",
                                         "life": 1.2, "max": 1.2, "attr": P["yellow"]})
                        spawn_ring(cx, 8, P["yellow"], n=14, speed=20)
                    set_mood("happy", 1.4)
                    bond = max(0.0, bond + (story.BOND_GAIN["perfect"] if perfect else story.BOND_GAIN["hit"]))
                    # lifesteal + repair on perfect (base sustain)
                    if stats["lifesteal"] > 0:
                        player_hp = min(stats["max_hp"], player_hp + stats["lifesteal"])
                    if perfect and stats["repair"] > 0:
                        player_hp = min(stats["max_hp"], player_hp + stats["repair"])
                    # XP Survivor-style
                    xp += r_xp(len(target), wave, stats["xp_mult"], wave % 5 == 0)
                    avg = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
                    maybe_save_best(wave, avg)
                else:
                    # combo guard: chance the combo survives
                    kept = r_combo(False, combo, stats["combo_guard"])
                    if combo > 0 and kept == combo:
                        msg = f"Close! combo x{combo} saved (GUARD)"
                        combo = kept  # hold
                    else:
                        combo = 0
                        msg = f"Miss! '{buf}' != '{target}' — combo reset!"
                    counter = r_counter(ecfg.dmg, wave, random.randint(0, 4))
                    projectiles.append({"x": cx + random.randint(-6, 6), "y": 8.0, "vy": 26.0,
                                        "char": ecfg.proj, "attr": P[ecfg.col],
                                        "pending": float(counter), "side": "enemy",
                                        "label": f"-{counter}"})
                    msg_t = 1.6
                    shake_t = 0.35
                    shake_mag = 2
                    sfx_play("miss")
                    set_mood("sad", 1.4)
                    bond = max(0.0, bond + story.BOND_GAIN["miss"])
                target = r_pick(wave)
                buf = ""
                word_start = now
            elif 32 <= key <= 126 and len(buf) < 60:
                buf += chr(key)
            key = stdscr.getch()

        elapsed_word = now - word_start
        # base regen per second (Survivor sustain)
        if stats["regen"] > 0 and player_hp > 0:
            player_hp = min(stats["max_hp"], player_hp + stats["regen"] * dt)
        if grace_t > 0:
            grace_t -= raw_dt  # wave-intro breather: enemy holds fire
        else:
            enemy_timer += dt
        if enemy_timer >= cur_interval:
            enemy_timer = 0.0
            # burst scales with wave: higher wave = more projectiles
            for b in range(ecfg.burst):
                chip = ecfg.dmg + random.randint(0, 3)
                projectiles.append({"x": cx + random.randint(-8, 8) + b * 2, "y": 8.0 - b * 1.2, "vy": 24.0,
                                    "char": ecfg.proj, "attr": P[ecfg.col],
                                    "pending": float(chip), "side": "enemy", "label": f"-{chip}"})
            msg = f"{ecfg.name} attacks x{ecfg.burst}! Type fast!"
            msg_t = 1.2
        # base auto cannon (passive Survivor.io-style DPS)
        if stats["turret"] > 0 and enemy_hp > 0:
            turret_t += dt
            t_interval = max(3.0, 8.0 - 0.6 * stats["turret"])
            if turret_t >= t_interval:
                turret_t = 0.0
                tdmg = stats["turret_dmg"] + wave * 2
                projectiles.append({"x": cx + 10, "y": h - 8.0, "vy": -30.0,
                                    "char": "⌖", "attr": P["magenta"],
                                    "pending": float(tdmg), "side": "player",
                                    "label": f"turret -{int(tdmg)}"})
                sfx_play("turret")

        if msg_t > 0:
            msg_t -= dt
        recoil_t = max(0.0, recoil_t - raw_dt)
        kick_y *= max(0.0, 1.0 - raw_dt * 6.0)  # camera springs back
        if shake_t > 0:
            shake_t -= dt
        if flash > 0:
            flash -= dt
        if banner_t > 0:
            banner_t -= dt
        if wmood_t > 0:
            wmood_t -= dt
            if wmood_t <= 0:
                wmood = "idle"
        if wstory_t > 0:
            wstory_t -= dt

        disp_e += (enemy_hp - disp_e) * min(1, dt * 6)
        disp_p += (player_hp - disp_p) * min(1, dt * 6)
        if abs(enemy_hp - disp_e) < 0.05:
            disp_e = enemy_hp
        if abs(player_hp - disp_p) < 0.05:
            disp_p = player_hp

        for s in stars:
            s["x"] -= s["sp"] * dt
            if s["x"] < 0:
                s["x"] += w
                s["y"] = random.random() * h

        for p in projectiles:
            p["y"] += p["vy"] * dt
        arrived, keep = [], []
        for p in projectiles:
            if p["side"] == "player" and p["y"] <= 8.5 or p["side"] == "enemy" and p["y"] >= h - 8.5:
                arrived.append(p)
            else:
                keep.append(p)
        projectiles = keep
        for p in arrived:
            if p["side"] == "player":
                enemy_hp -= p["pending"]
                spawn_explosion(p["x"], 8, P["green"])
                spawn_ring(p["x"], 8, P["green"], n=10, speed=16)
                floaters.append({"x": p["x"] + 2, "y": 9.0, "text": p.get("label", ""),
                                 "life": 1.0, "max": 1.0, "attr": P["green"]})
                shake_t = 0.18
                shake_mag = 1
                flash = 0.07
                sfx_play("hit")
            else:
                # shield: full-block chance
                if random.random() < stats["shield"]:
                    spawn_explosion(p["x"], h - 8, P["cyan"], n=10)
                    floaters.append({"x": p["x"] + 1, "y": h - 10.0, "text": "BLOCK",
                                     "life": 1.0, "max": 1.0, "attr": P["cyan"]})
                    sfx_play("block")
                    set_mood("happy", 1.0)
                else:
                    player_hp -= p["pending"]
                    spawn_explosion(p["x"], h - 8, P["red"], n=14)
                    floaters.append({"x": p["x"] + 1, "y": h - 10.0, "text": p.get("label", ""),
                                     "life": 1.0, "max": 1.0, "attr": P["red"]})
                    shake_t = 0.3
                    shake_mag = 2
                    hitstop = max(hitstop, 0.06)
                    kick_y = min(3.0, kick_y + 2.0)  # camera slammed downward
                    sfx_play("hurt")
                    set_mood("hurt", 1.2)

        for pt in particles:
            pt["life"] -= dt
            pt["x"] += pt["vx"] * dt
            pt["y"] += pt["vy"] * dt
            pt["vy"] += 22 * dt
        if len(particles) > MAXP:
            del particles[0: len(particles) - MAXP]
        else:
            particles[:] = [p for p in particles if p["life"] > 0]
        for f in floaters:
            f["life"] -= dt
            f["y"] -= 3.5 * dt
        floaters[:] = [f for f in floaters if f["life"] > 0]

        # sync max HP from the wall upgrade
        player_max = float(stats["max_hp"])
        if disp_p > player_max + 1:
            disp_p = player_max

        # LEVEL UP -> Survivor-style upgrade overlay (can chain)
        while xp >= xp_next:
            xp -= xp_next
            level += 1
            xp_next = r_next(xp_next)
            pending_lv += 1
        while pending_lv > 0:
            pending_lv -= 1
            choices = r_roll(owned, k=3)
            if not choices:
                break
            # fresh explosion before picking
            spawn_explosion(cx, h // 2, P["yellow"], n=30)
            floaters.append({"x": cx - 4, "y": h // 2 - 1.0, "text": f"LEVEL {level}!",
                             "life": 1.2, "max": 1.2, "attr": P["yellow"]})
            # render one frame so the explosion shows before the overlay
            stdscr.refresh()
            pick = upgrade_screen.show(stdscr, P, choices, level, owned)
            u = choices[pick]
            r_apply(get_field(u, "id"), stats)
            owned[get_field(u, "id")] = owned.get(get_field(u, "id"), 0) + 1
            base_lv += 1
            sfx_play("select")
            set_mood("excited", 2.2)
            if get_field(u, "id") == "wall":
                player_hp = min(stats["max_hp"], player_hp + 25)
            player_max = float(stats["max_hp"])
            cur_interval = quality.effective_interval(ecfg.interval, stats["slow"])
            spawn_explosion(cx, h - 8, P["green"], n=30)
            floaters.append({"x": cx - 6, "y": h - 10.0, "text": f"+ {get_field(u, 'name')}",
                             "life": 1.4, "max": 1.4, "attr": P["green"]})
            msg = f"UPGRADE: {get_field(u, 'name')} — {get_field(u, 'desc')}"
            msg_t = 2.2
            # fair input timer after picking
            word_start = time.monotonic()
            last = time.monotonic()

        if enemy_hp <= 0:
            acc = (hits / shots * 100) if shots else 100
            avg_wpm = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
            maybe_save_best(wave, avg_wpm)
            spawn_explosion(cx, 8, P["yellow"], n=40)
            spawn_ring(cx, 8, P["yellow"], n=26, speed=30)
            hitstop = max(hitstop, 0.14)  # kill freeze, then celebration
            sfx_play("waveclear")
            set_mood("excited", 2.5)
            bond = max(0.0, bond + story.BOND_GAIN["clear"])
            newly = r_unlocks(wstate.get("unlocked", ["aika"]), wave + 1)
            if newly:
                for _uid in newly:
                    wstate["unlocked"] = [*wstate.get("unlocked", ["aika"]), _uid]
                    msg = f"{story.get_waifu(_uid)['name']} joined the team! (switch: menu ◄ ►)"
                    msg_t = 3.0
                    raw = story.get_waifu(_uid).get("unlock_line") or f"{story.get_waifu(_uid)['name']} joined!"
                    try:
                        raw = raw.format(wave=wave + 1, enemy=ecfg.name)
                    except (IndexError, KeyError):
                        pass
                    set_story(raw, 5.0)
            else:
                set_story(r_line(waifu_id, "clear", {"wave": wave, "enemy": ecfg.name}, random.randrange(999)), 3.0)
            save_waifu_state()
            t0 = time.monotonic()
            while time.monotonic() - t0 < 1.8:
                h2, w2 = stdscr.getmaxyx()
                size2 = (h2, w2)
                stdscr.erase()
                for pt in particles:
                    pt["life"] -= 0.016
                    pt["x"] += pt["vx"] * 0.016
                    pt["y"] += pt["vy"] * 0.016
                particles[:] = [p for p in particles if p["life"] > 0]
                for pt in particles:
                    widgets.safe_add(stdscr, int(pt["y"]), int(pt["x"]), pt["char"], pt["attr"], size2)
                _l1 = f"WAVE {wave} DESTROYED!"
                _l2 = f"{acc:.0f}% | {avg_wpm:.0f} WPM | max combo {best_combo} | Enter to continue"
                _bw = max(len(_l1), len(_l2)) + 4
                _bx = w2 // 2 - _bw // 2
                _by = h2 // 2 - 1
                widgets.safe_add(stdscr, _by - 1, _bx, "┏" + "━" * (_bw - 2) + "┓", P["yellow"], size2)
                widgets.safe_add(stdscr, _by, _bx, "┃" + _l1.center(_bw - 2) + "┃", P["yellow"] | curses.A_BOLD, size2)
                widgets.safe_add(stdscr, _by + 1, _bx, "┃" + _l2.center(_bw - 2) + "┃", P["cyan"], size2)
                widgets.safe_add(stdscr, _by + 2, _bx, "┗" + "━" * (_bw - 2) + "┛", P["yellow"], size2)
                stdscr.refresh()
                time.sleep(0.033)
            stdscr.nodelay(False)
            stdscr.timeout(-1)
            stdscr.getch()
            stdscr.nodelay(True)
            stdscr.timeout(frame_ms)
            wave += 1
            player_max = float(stats["max_hp"])
            player_hp = float(player_max)
            disp_p = float(player_max)
            new_wave(wave)
            msg = f"WAVE {wave} {ecfg.name} — {r_rank(avg_wpm, best_combo)} mode ON!"
            msg_t = 2.5
            best_combo = 0
            last = time.monotonic()
            continue

        if player_hp <= 0:
            stdscr.nodelay(False)
            stdscr.erase()
            acc = (hits / shots * 100) if shots else 100
            avg_wpm = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
            maybe_save_best(wave, avg_wpm)
            rk = r_rank(avg_wpm, best_combo)
            sfx_play("gameover")
            save_waifu_state()
            defeat_say = r_line(waifu_id, "defeat", {"wave": wave, "enemy": ecfg.name}, random.randrange(999))
            _gw = 56
            _gx = cx - _gw // 2
            _gy = h // 2 - 3
            widgets.safe_add(stdscr, _gy, _gx, "┏" + "━" * (_gw - 2) + "┓", P["red"], size)
            for _gr in range(1, 7):
                widgets.safe_add(stdscr, _gy + _gr, _gx, "┃", P["red"], size)
                widgets.safe_add(stdscr, _gy + _gr, _gx + _gw - 1, "┃", P["red"], size)
            widgets.safe_add(stdscr, _gy + 7, _gx, "┗" + "━" * (_gw - 2) + "┛", P["red"], size)
            widgets.safe_add(stdscr, h // 2 - 2, cx - 12, "☠ YOUR FORT HAS FALLEN ☠", P["red"] | curses.A_BOLD, size)
            widgets.safe_add(stdscr, h // 2 - 1, cx - 24, f"wave {wave} | {hits}/{shots} | {acc:.0f}% | {avg_wpm:.0f} WPM | {rk}", P["fg"], size)
            widgets.safe_add(stdscr, h // 2 + 1, cx - 16, "Enter retries, q quits", P["dim"], size)
            widgets.safe_add(stdscr, h // 2 + 2, cx - 20, "so close… one more wave, you got this", P["magenta"], size)
            widgets.safe_add(stdscr, h // 2 + 3, cx - len(defeat_say) // 2, f"{winfo['name']}: {defeat_say}"[: max(0, w - 4)], P["yellow"], size)
            stdscr.refresh()
            stdscr.timeout(-1)
            k = stdscr.getch()
            if k == -1 or (k != 10 and k != 13 and k != ord(" ") and not (32 <= k <= 126 and chr(k).lower() == "y")):
                # q / esc / anything but enter = simple confirm: q quits
                try:
                    if chr(k).lower() == "q":
                        _close_sup()
                        return
                except Exception:  # noqa: BLE001, S110
                    pass
                # Enter / space = retry
                if k not in (10, 13, ord(" ")):
                    _close_sup()
                    return
            wave = 1
            stats = upgrades.fresh_stats()
            owned = {}
            base_lv = 0
            level = 1
            xp = 0.0
            xp_next = 30.0
            pending_lv = 0
            turret_t = 0.0
            enemy_timer = 0.0
            shots = hits = 0
            correct_chars_total = 0
            time_total = 0.0
            combo = 0
            best_combo = 0
            player_max = float(stats["max_hp"])
            player_hp = float(player_max)
            disp_p = float(player_max)
            projectiles.clear()
            particles.clear()
            floaters.clear()
            new_wave(1)
            stdscr.nodelay(True)
            stdscr.timeout(frame_ms)
            last = time.monotonic()
            continue

        # render (light: background only flips on flash change, shake only shakes)
        stdscr.erase()
        flash_on = flash > 0
        if flash_on != last_flash_on:
            last_flash_on = flash_on
            try:
                stdscr.bkgd(" ", P["flash"] if flash_on else curses.A_NORMAL)
            except curses.error:
                pass

        if shake_t > 0:
            shx = random.randint(-shake_mag, shake_mag)
            shy = random.randint(-1, 1) + round(kick_y)
        else:
            shx = 0
            shy = round(kick_y)

        for s in stars:
            widgets.safe_add(stdscr, int(s["y"]) % max(1, h), int(s["x"]) % max(1, w), ".", P["cyan_dim"], size)

        # retro console shell: chunky double-line frame on HIGH/MED
        # (sides every 2nd row on MED = pixel-dash style, cheaper),
        # thin corners only on LOW to save addstrs on weak devices.
        if qi < 2:
            widgets.safe_add(stdscr, 0, 0, "╔" + "═" * max(0, w - 3) + "╗", P["dim"], size)
            widgets.safe_add(stdscr, h - 1, 0, "╚" + "═" * max(0, w - 3) + "╝", P["dim"], size)
            _step = 1 if qi == 0 else 2
            for _fy in range(1, h - 1, _step):
                widgets.safe_add(stdscr, _fy, 0, "║", P["dim"], size)
                widgets.safe_add(stdscr, _fy, w - 1, "║", P["dim"], size)
            # power LED, top-right inside the shell
            _led = P["red"] | curses.A_BOLD if (now * 2) % 1 < 0.7 else P["dim"]
            widgets.safe_add(stdscr, 0, w - 4, "◉", _led, size)
        else:
            widgets.safe_add(stdscr, 2, 0, "─" * max(0, w - 1), P["dim"], size)
            widgets.safe_add(stdscr, h - 1, 0, "─" * max(0, w - 1), P["dim"], size)
            widgets.safe_add(stdscr, 0, 0, "┏", P["dim"], size)
            widgets.safe_add(stdscr, 0, w - 1, "┓", P["dim"], size)
            widgets.safe_add(stdscr, h - 1, 0, "┗", P["dim"], size)
            widgets.safe_add(stdscr, h - 1, w - 1, "┛", P["dim"], size)

        avg_live = (correct_chars_total / 5) / (time_total / 60) if time_total > 0.5 else 0
        # rank is pure but string-heavy; refresh at most 2x/sec or on combo change
        avg_q = round(avg_live)
        if combo != rk_combo or avg_q != rk_avg_q or now - rk_t > 0.5:
            rk_live = r_rank(avg_live, combo)
            rk_combo, rk_avg_q, rk_t = combo, avg_q, now
        # ── TOP ZONE: enemy (clearly separated from player status) ──
        widgets.safe_add(stdscr, 0, 2, f"TEXTACK v{VERSION}  W{wave} COMBO x{combo} {rk_live}", P["fg"], size)
        _efrac = enemy_hp / max(1.0, enemy_max)
        _ebar = P["green"] if _efrac > 0.5 else (P["yellow"] if _efrac > 0.25 else P["red"])
        widgets.safe_add(stdscr, 1, 2, f"▼ {ecfg.name} {widgets.hp_bar_str(enemy_hp, disp_e, enemy_max, min(34, w-30))}", _ebar, size)
        # combo meter + tiny quality/sfx (1 merged addstr to save calls)
        cw = min(16, w - 10)
        cfill = int(cw * min(1, combo / 10))
        sfx_s = "♪" if sfx["on"] else "×"
        widgets.safe_add(stdscr, 0, max(0, w - cw - 28), f"[{'█'*cfill}{'░'*(cw-cfill)}] {quality.QLEVELS[qi]['name']} {sfx_s}", P["magenta"], size)

        bob = int((now * 2) % 2)
        ey = 6 + shy + bob
        # fortress animation: windows/torches flicker between two frames
        art_lines = ENEMY_ART_B if (now * 2.5) % 1 < 0.5 else ENEMY_ART_A
        # cheap telegraph: enemy flashes bold when about to attack (>80% timer)
        tele = (enemy_timer / cur_interval) > 0.8 if cur_interval > 0 else False
        ecol = P[ecfg.col] | (curses.A_BOLD if tele else 0)
        for i, line in enumerate(art_lines):
            _ex = cx - len(line) // 2 + shx
            widgets.safe_add(stdscr, ey + i, _ex + 1, line, curses.A_DIM, size)
            widgets.safe_add(stdscr, ey + i, _ex, line, ecol, size)
        # enemy name + interval (transparent tactics)
        widgets.safe_add(stdscr, ey + len(art_lines) + 1, cx - 14 + shx, f"{ecfg.name} HP{int(max(0,enemy_hp))} ATK/{cur_interval:.1f}s", ecol, size)
        # wave banner: sliding bordered box
        if banner_t > 0:
            _blen = len(banner) + 4
            bx = int(cx - _blen // 2 + (banner_t * 14))
            bx = max(1, min(bx, w - _blen - 1))
            balpha = P["yellow"] | curses.A_BOLD if (now * 4) % 1 < 0.7 else P["yellow"]
            widgets.safe_add(stdscr, ey - 3, bx, "┏" + "━" * (_blen - 2) + "┓", balpha, size)
            widgets.safe_add(stdscr, ey - 2, bx, "┃ " + banner + " ┃", balpha, size)
            widgets.safe_add(stdscr, ey - 1, bx, "┗" + "━" * (_blen - 2) + "┛", balpha, size)

        ty = ey + len(art_lines) + 3
        # 3-segment target (cheap: 3-4 addstrs, not per-letter)
        tx = cx - len(target) // 2
        widgets.safe_add(stdscr, ty, tx - 2, "> ", P["fg"], size)
        n_ok = 0
        first_bad = -1
        for i in range(min(len(buf), len(target))):
            if buf[i] == target[i]:
                n_ok += 1
            else:
                first_bad = i
                break
        else:
            if len(buf) >= len(target):
                n_ok = len(target)
        if n_ok > 0:
            widgets.safe_add(stdscr, ty, tx, target[:n_ok], P["green"], size)
        if first_bad >= 0:
            widgets.safe_add(stdscr, ty, tx + first_bad, target[first_bad: first_bad + 1], P["red"] | curses.A_BOLD, size)
            if first_bad + 1 < len(target):
                widgets.safe_add(stdscr, ty, tx + first_bad + 1, target[first_bad + 1:], P["fg"], size)
        else:
            rest = target[n_ok:]
            if rest:
                widgets.safe_add(stdscr, ty, tx + n_ok, rest[0], curses.A_REVERSE, size)
                if len(rest) > 1:
                    widgets.safe_add(stdscr, ty, tx + n_ok + 1, rest[1:], P["fg"], size)
        # STRIKE COUNTDOWN: truthful enemy attack timer — the enemy fires
        # when enemy_timer reaches the interval. Pixel bar + numeric
        # readout + arcade digit. (The old bar used keystroke time, which
        # lied after a miss; this one tracks the real attack clock.)
        _strike_in = max(0.0, cur_interval - enemy_timer)
        _sfrac = max(0, min(1, enemy_timer / cur_interval)) if cur_interval > 0 else 1
        tw = min(30, w - 10)
        tfill = int(tw * (1 - _sfrac))
        tcol = P["green"] if _sfrac < 0.5 else (P["yellow"] if _sfrac < 0.8 else P["red"])
        if grace_t > 0:
            _slabel = f"◆ GET READY — STRIKE IN {grace_t:.1f}s ◆"
            widgets.safe_add(stdscr, ty + 1, cx - tw // 2, "[" + "█" * tw + "]", P["cyan"] | curses.A_BOLD, size)
            widgets.safe_add(stdscr, ty + 2, cx - len(_slabel) // 2, _slabel, P["cyan"] | curses.A_BOLD, size)
        else:
            if tele and (now * 5) % 1 < 0.6:
                _slabel = f"⚠ {ecfg.name} INCOMING — {_strike_in:.1f}s ⚠"
                _scol = P["red"] | curses.A_BOLD
            else:
                _slabel = f"▼ STRIKE IN {_strike_in:.1f}s " + "●" * ecfg.burst
                _scol = tcol
            widgets.safe_add(stdscr, ty + 1, cx - tw // 2, "[" + "█" * tfill + "░" * (tw - tfill) + "]", tcol, size)
            widgets.safe_add(stdscr, ty + 2, cx - len(_slabel) // 2, _slabel, _scol, size)
            # arcade countdown digit (5-row pixel numeral) as the strike nears
            _digit = math.ceil(_strike_in)
            if 1 <= _digit <= 5 and enemy_hp > 0:
                _dcol = P["red"] | curses.A_BOLD if _digit <= 2 else P["yellow"] | curses.A_BOLD
                for _dr, _dline in enumerate(PX_DIGITS[_digit]):
                    widgets.safe_add(stdscr, ty + _dr, cx - tw // 2 - 5, _dline, _dcol, size)

        for p in projectiles:
            _px, _pyy = int(p["x"]), int(p["y"])
            widgets.safe_add(stdscr, _pyy, _px, p["char"], p["attr"] | curses.A_BOLD, size)
            # motion tracer: one dim cell behind the warhead
            _trail = _pyy + (1 if p["vy"] < 0 else -1)
            widgets.safe_add(stdscr, _trail, _px, "·" if p["side"] == "player" else ".", p["attr"] | curses.A_DIM, size)
        for pt in particles:
            a = pt["attr"] | (curses.A_DIM if pt["life"] < pt["max"] * 0.4 else curses.A_BOLD)
            widgets.safe_add(stdscr, int(pt["y"]), int(pt["x"]), pt["char"], a, size)
        for f in floaters:
            alpha = curses.A_BOLD if f["life"] > f["max"] * 0.4 else curses.A_DIM
            widgets.safe_add(stdscr, int(f["y"]), int(f["x"]), f["text"], f["attr"] | alpha, size)

        py = h - 7
        # ── BOTTOM ZONE: player status glued to your own fort ──
        _pfrac = player_hp / max(1.0, player_max)
        _pbar = P["green"] if _pfrac > 0.5 else (P["yellow"] if _pfrac > 0.25 else P["red"])
        widgets.safe_add(stdscr, py - 2, 2, f"▲ YOU {widgets.hp_bar_str(player_hp, disp_p, player_max, min(34, w-30))}", _pbar, size)
        xw = min(14, max(6, w - 60))
        xfill = int(xw * min(1, xp / max(1, xp_next)))
        turret_s = f" ⌖{stats['turret']}" if stats["turret"] else ""
        widgets.safe_add(stdscr, py - 1, 2, f"LV{level} [{'█'*xfill}{'░'*(xw-xfill)}] BASE{base_lv}{turret_s} DMGx{stats['dmg_mult']:.1f}", P["magenta"], size)
        # base visual levels up: glow shadow + recoil kick + muzzle flash
        base_attr = P["green"] | curses.A_BOLD
        _recoil_dy = 1 if recoil_t > 0 else 0
        for i, line in enumerate(PLAYER_ART):
            _bx2 = cx - len(line) // 2
            widgets.safe_add(stdscr, py + i + _recoil_dy, _bx2 - 1, line, curses.A_DIM, size)
            widgets.safe_add(stdscr, py + i + _recoil_dy, _bx2, line, base_attr, size)
        if recoil_t > 0:
            widgets.safe_add(stdscr, py - 1, cx, "✦", P["yellow"] | curses.A_BOLD, size)
        # engine lights: alternate blink at the base flanks
        _eng_l = P["cyan"] | curses.A_BOLD if (now * 2) % 1 < 0.5 else P["dim"]
        _eng_r = P["dim"] if (now * 2) % 1 < 0.5 else P["cyan"] | curses.A_BOLD
        widgets.safe_add(stdscr, py + 4 + _recoil_dy, cx - 12, "●", _eng_l, size)
        widgets.safe_add(stdscr, py + 4 + _recoil_dy, cx + 12, "●", _eng_r, size)
        # side cannons from BASE level 3+
        if base_lv >= 3:
            widgets.safe_add(stdscr, py + 1 + _recoil_dy, cx - 15, "⌖", P["magenta"] | curses.A_BOLD, size)
            widgets.safe_add(stdscr, py + 1 + _recoil_dy, cx + 15, "⌖", P["magenta"] | curses.A_BOLD, size)
        if stats["wall"] > 0:
            armor = "▣" * min(6, stats["wall"]) + f" Lv{stats['wall']}"
            widgets.safe_add(stdscr, py + 4 if py + 4 < h else h - 1, cx - len(armor) // 2, armor, P["cyan"], size)
        if stats["turret"] > 0:
            blink = "⌖" if (now * 3) % 1 < 0.7 else "◉"
            widgets.safe_add(stdscr, py - 1, cx + 12, f"{blink}x{stats['turret']}", P["magenta"], size)
        # ── operator panel (right, wide screens only so it never crams) ──
        # Precise layout: art ends at h-7, name at h-5, dialog at h-4.
        photo_geom = None
        if w >= 102 and h >= 24:
            px = w - 36
            blv = story.level_for(bond)
            art_bot = h - 7
            use_photo = bool(photo_path) and gfx_mode == "kitty"
            if use_photo or (face_ok and face_rgb):
                frows = min(18, max(6, (h - 24) // 2 + 8), h - 9)
                fcols = min(34, max(12, frows * 2))
                art_top = art_bot - frows + 1
                widgets.safe_add(stdscr, art_top - 1, px, f"◆ {winfo['name']} · {winfo['title']} ♡{blv}", P["cyan"], size)
                if use_photo:
                    photo_geom = (art_top, px, fcols, frows)
                else:
                    photo_geom = None
                    if (fcols, frows) != face_cache_key:
                        face_cache_key = (fcols, frows)
                        _cells = face_mod.downsample(face_px, face_nw, face_nh, fcols, frows)
                        _pal, face_cells = face_mod.quantize(_cells)
                        face_pairs = face_mod.alloc_pairs(_pal, face_mod.pair_combos(face_cells))
                        if face_pairs is None:
                            face_ok = False
                    if face_ok:
                        face_mod.draw(stdscr, art_top, px, fcols, face_cells, face_pairs, P["magenta"])
                    else:
                        art = waifu_art[: max(4, h - 14)]
                        atop = art_bot - len(art) + 1
                        for i, ln in enumerate(art):
                            widgets.safe_add(stdscr, atop + i, px, ln, P["magenta"] if i < 5 else P["fg"], size)
            else:
                photo_geom = None
                art = waifu_art[: max(4, h - 14)]
                art_top = art_bot - len(art) + 1
                widgets.safe_add(stdscr, art_top - 1, px, f"◆ {winfo['name']} · {winfo['title']} ♡{blv}", P["cyan"], size)
                for i, ln in enumerate(art):
                    widgets.safe_add(stdscr, art_top + i, px, ln, P["magenta"] if i < 5 else P["fg"], size)
            mood_face = winfo["faces"].get(wmood, "(・‿・)")
            widgets.safe_add(stdscr, h - 5, px, f"{winfo['name']} {mood_face}", P["yellow"] | curses.A_BOLD, size)
            if wstory_t > 0:
                say = wstory
            elif wmood == "idle":
                # idle lines rotate every 4s; cache so we format once per bucket
                seed = int(now / 4)
                if seed != idle_seed_cache:
                    idle_seed_cache = seed
                    idle_line_cache = r_line(waifu_id, "idle", seed=seed)
                say = idle_line_cache
            else:
                say = r_mood(waifu_id, wmood, wline)
            widgets.safe_add(stdscr, h - 4, px, f"「{say}」", P["dim"], size)
        # cheap heartbeat: screen corners blink under 30% HP (4 addstrs)
        if player_hp < player_max * 0.3 and player_hp > 0:
            hb = P["red"] | curses.A_BOLD if (now * 3) % 1 < 0.5 else P["dim"]
            widgets.safe_add(stdscr, 0, 0, "♥", hb, size)
            widgets.safe_add(stdscr, 0, w - 1, "♥", hb, size)
            widgets.safe_add(stdscr, h - 1, 0, "♥", hb, size)
            widgets.safe_add(stdscr, h - 1, w - 1, "♥", hb, size)

        caret = "█" if (now * 4) % 1 < 0.6 else " "
        prompt = f"> {buf}{caret}"
        widgets.safe_add(stdscr, h - 2, max(0, cx - max(len(prompt), len(target)) // 2 - 2), prompt, P["fg"], size)
        if msg_t > 0:
            widgets.safe_add(stdscr, h - 3, 2, msg[: max(0, w - 4)], P["cyan"], size)
        else:
            live_wpm = (len(buf) / 5) / (elapsed_word / 60) if elapsed_word > 0.2 else 0
            widgets.safe_add(stdscr, h - 3, 2, f"{elapsed_word:.1f}s | {live_wpm:.0f} WPM | {combo}x | Enter=shoot", P["dim"], size)

        stdscr.refresh()
        if photo_geom and photo_path and gfx_mode == "kitty":
            if not photo_sent:
                _data = gfx.png_bytes_for(photo_path)
                if _data:
                    for _seq in gfx.build_transmit(_data, photo_id):
                        gfx.emit(_seq)
                    photo_sent = True
                else:
                    photo_path = None
            if photo_sent:
                _gy, _gx, _gc, _gr = photo_geom
                gfx.place_at(_gy, _gx, gfx.build_place(photo_id, 1, _gc, _gr))
        elif photo_sent:
            gfx.emit(gfx.build_delete_image(photo_id))
            photo_sent = False
