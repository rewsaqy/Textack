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
- `engine` (polyglot v2) imports `core` + stdlib only, plus `infra/sfx`
  for the classic fallback. Speaks `docs/PROTOCOL.md`. `ui` may import
  `engine` (siege routes through the director); nothing else imports it.
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
| `textack/core/campaign.py` | core | story-mode seam | `CHAPTERS`, `chapter_for`, `stage_at`, `chapter_progress` |
| `textack/engine/proto.py` | engine | wire spec v1 | `VERSION`, `SPEC`, `encode/decode/validate`, `err()` |
| `textack/engine/sim.py` | engine | reference worker | `Sim.handle(msg)` (mirrors `core/*`) |
| `textack/engine/transport.py` | engine | framing | `MessageIO` (streams), `Loopback` (in-process) |
| `textack/engine/sfx_worker.py` | engine | live sound worker | `SfxWorker` + `python -m` stdio entry |
| `textack/engine/sfx_client.py` | engine | director side | `SfxClient` (spawn, notify, id-matched requests) |
| `rs/textack-sim/` | engine (rust) | sim worker port | stdio binary, bit-identical replies (see its README) |
| `lua/worker.lua` + `lua/json.lua` + `lua/mt.lua` | engine (lua) | content worker | stdio, lua5.4 + luajit (see lua/README) |
| `content/*.lua` | engine data | waves/dialog/words | portable canonical copy, hot-reloadable |
| `engine.json` | engine fleet | worker declarations | cmds, alts, domains, fallbacks |
| `textack/engine/mode.py` | engine | `--engine` selection | `active()` → classic/polyglot |
| `textack/engine/pipe_client.py` | engine | generic stdio client | `PipeClient` (spawn, notify, id-matched requests) |
| `textack/engine/supervisor.py` | engine | fleet boot | per-domain fallbacks, `director()` |
| `textack/engine/director.py` | engine | routing facade | core-mirroring methods, fail-open downgrade |
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
