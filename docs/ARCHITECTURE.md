# Textack Architecture

Three layers, one rule. Pure logic at the bottom, curses in the
middle, side effects at the edge.

## Layer diagram

```
┌─────────────────────────────────────────┐
│  entry: main.py / textack/__main__.py   │  thin shims only
├─────────────────────────────────────────┤
│  ui: textack/ui/ (+ screens/)           │  curses rendering + input
│    imports core + infra                 │
├─────────────────────────────────────────┤
│  infra: textack/infra/                  │  storage, quality, waifu, sfx
│    imports core (for types)             │
├─────────────────────────────────────────┤
│  core: textack/core/                    │  pure logic, stdlib only
│    imports nothing internal             │
└─────────────────────────────────────────┘
```

## Import rule

**core → ui → infra, never backwards.**

- `core` imports stdlib only (`random`, `dataclasses`, `typing`).
  No curses, no files, no sound. Fully unit-testable.
- `ui` may import `core` and `infra`. Owns all `curses` calls.
- `infra` may import `core` (types/constants only).
- Nothing imports `ui/screens/*` except the entry shim
   (`textack/__main__.py` → `screens.loop.game_loop`) and sibling screens.

Violations (e.g. `core` importing `curses`, a screen importing
another screen's internals) fail review even if tests pass.

## File table

| File | Layer | Role | Key symbols |
|---|---|---|---|
| `textack/core/words.py` | core | word pools per wave | `TIER1/2/3`, `pick_word(wave, rng)` |
| `textack/core/combat.py` | core | hit math | `HitResult(dmg,tag,wpm,speed_bonus,perfect,crit,double)`, `resolve_hit(...)`, `combo_step(...)`, `miss_damage(...)` |
| `textack/core/enemies.py` | core | enemy stats per wave | `EnemyConfig(name,interval,dmg,burst,hp,proj,col)`, `for_wave(wave)` |
| `textack/core/upgrades.py` | core | 14 upgrades | `Upgrade(id,icon,cat,name,desc,max,apply_fn)`, `REGISTRY`, `apply(uid,stats)`, `roll_choices(owned,k,rng)`, `fresh_stats()` |
| `textack/core/progression.py` | core | rank + XP | `rank_for(wpm,combo)`, `next_threshold(current)`, `gain_xp(...)` |
| `textack/ui/palette.py` | ui | color pairs | `init()` |
| `textack/ui/widgets.py` | ui | bars, panels, input | `hp_bar_str(...)`, `safe_add(...)` |
| `textack/ui/fx.py` | ui | transitions | `fade_out(...)`, `fade_in_blank(...)` |
| `textack/ui/screens/opening.py` | ui | title screen | — |
| `textack/ui/screens/howto.py` | ui | help screen | — |
| `textack/ui/screens/siege.py` | ui | main battle loop (delegates math to `core`) | `show(stdscr, P)` |
| `textack/ui/screens/upgrade.py` | ui | level-up picker | — |
| `textack/ui/screens/outro.py` | ui | game-over screen | — |
| `textack/ui/screens/loop.py` | ui | screen sequencing | `game_loop(stdscr)` |
| `textack/infra/storage.py` | infra | best score file | `load_best(...)`, `save_best(...)`, `beats_best(...)` |
| `textack/infra/quality.py` | infra | LOW/HIGH terminal mode | `from_env(...)`, `effective_interval(...)` |
| `textack/infra/waifu.py` | infra | operator art | `load_art_for(...)`, `load_rgb_for(...)`, `find_photo(...)` |
| `textack/infra/sfx.py` | infra | sound (paplay/aplay/mpv, beep fallback, silent on miss) | `init(...)`, `play(...)`, `detect_player()` |
| `main.py` / `textack/__main__.py` | entry | shims | — |

Runtime needs stdlib only. Dev extras (`pip install -e .[dev]`)
add `pytest` + `ruff` (see `pyproject.toml`, CI in
`.github/workflows/ci.yml`).
