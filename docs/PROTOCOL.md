# Textack Wire Protocol v1

Contract between the **director** (Python game loop) and **workers**
(sim, sfx, content — in any language). Phase 1 ships the contract plus
an in-process reference (`textack/engine/`); no game flow uses it yet.

## Transport

- **NDJSON**: one JSON object per line, UTF-8, `\n` terminated.
- Works over anything byte-streamed: socket pairs, pipes, subprocess
  stdio (`textack.engine.transport.MessageIO`).
- A reader buffers until `\n`; a writer flushes every message.
- Blank lines are skipped. Unparseable lines carry no envelope, so they
  produce no reply (the `error` type is only for parsed objects).
- EOF (empty read) = peer gone → raise/return, never hang silently.
- Future supervisor may add length-prefixing; v1 stays human-readable
  (`nc`, `tee`, and `jq` must work for debugging).

## Notifications (no id → no reply)

Any request type whose SPEC marks `id` optional MAY be sent without one.
Workers MUST NOT reply to id-less requests — except `hello`/`ping`/`bye`,
which always answer. This lets fire-and-forget clients (the game loop
triggering sounds at 60fps) never fill the pipe with unread replies.

## Envelope

```json
{"v": 1, "t": "hit", "id": 7, "...": "..."}
```

| Field | Rule |
|---|---|
| `v` | Must be `1`. Anything else → `error/bad-version`. |
| `t` | Message type (table below). Unknown → `error/unknown-type`. |
| `id` | Correlation token (any JSON value). Echoed in the reply when the request carried one. |

Unknown fields are **ignored** (forward compatibility). Replies to
malformed input are always `error`, never silence, never exceptions
across the wire:

```json
{"v": 1, "t": "error", "code": "bad-message", "msg": "...", "id": 7}
```

Error codes: `bad-envelope` (not an object) · `bad-version` ·
`unknown-type` · `bad-message` (schema violation).

## Value rules (cross-language hazards)

- `int` means i64-range int — JSON `true`/`false` must **not** validate
  as int, and values outside `[-2^63, 2^63-1]` are rejected (every worker
  language parses JSON ints as i64).
- `seed` means non-negative int in `[0, 2^64-1]` (u64; see Deterministic
  RNG below). Negative or huge seeds are `bad-message` everywhere.
- `num` means finite int/float — `NaN`/`Infinity` are rejected on
  encode, decode, and validate (most strictly-typed JSON parsers
  refuse them, so the wire must never contain them).
- Floats survive a JSON roundtrip bit-exactly in conforming
  implementations (shortest-roundtrip encoding, like Python `repr`).
- Strings are UTF-8 (`▲ ⌖ (≧▽≦)` must pass through untouched).

## Catalog (v1, sim domain)

Request → reply. `id` required on every request below except
`hello`/`ping`/`bye`; replies echo it.

| Request | Key fields | Reply | Notes |
|---|---|---|---|
| `hello` | `role`, `proto: [1]`, `id?` | `ready` (`role`, `proto: 1`) | Handshake; id echoed when present |
| `ping` | — | `pong` | Liveness probe |
| `bye` | `id?` | `bye` | Clean shutdown; id echoed when present |
| `hit` | `target`, `buf`, `elapsed`, `combo`, `stats{}`, `wave`, `seed?` | `damage` (`dmg`, `tag`, `wpm`, `speed_bonus`, `perfect`, `crit`, `double`) or `nomatch` | Mirrors `core.combat.resolve_hit` |
| `combo` | `hit`, `combo`, `guard?`, `rng?` | `combo-state` (`combo`) | Mirrors `combo_step` |
| `counter` | `enemy_dmg`, `wave`, `bonus?` | `counter-damage` (`dmg`) | Mirrors `miss_damage` |
| `xp` | `word_len`, `wave`, `xp_mult`, `boss` | `xp-gain` (`xp`) | Mirrors `gain_xp` |
| `threshold` | `current` | `threshold-is` (`next`) | Mirrors `next_threshold` |
| `wave` | `wave` | `wave-cfg` (`name`, `interval`, `dmg`, `burst`, `hp`, `proj`, `col`, `boss`) | Mirrors `enemies.for_wave` |
| `rank` | `wpm`, `combo` | `rank-is` (`rank`) | Mirrors `rank_for` |
| `dialog` | `wid`, `trigger`, `wave?`, `enemy?`, `seed?` | `line` (`text`) | Mirrors `story.line_for` |
| `mood` | `wid`, `mood`, `seed?` | `line` (`text`) | Mirrors `story.mood_line` |
| `upgrade` | `uid`, `stats{}` | `stats` (`stats{}`) | Pure: input stats never mutated on the wire; reply carries the copy |
| `roll` | `owned{}`, `k?` (=3), `seed?` | `choices` (`ids[]`) | Mirrors `roll_choices` |
| `pick` | `wave`, `seed?` | `word` (`text`) | Mirrors `words.pick_word` (content-owned) |
| `unlocks` | `unlocked[]`, `wave` | `unlocks-is` (`ids[]`) | Mirrors `check_unlocks` |

## Catalog (v1, content domain — added phase 4, purely additive)

Owned by the Lua worker (`lua/worker.lua`, data in `content/`). Same
`dialog`/`mood`/`wave`/`unlocks`/`pick` shapes as the sim domain — a
content worker answers the data-owned subset; anything else is
`unknown-type` (it must NOT implement sim math).

| Request | Key fields | Reply | Notes |
|---|---|---|---|
| `content-reload` | `path?`, `id?` | `content-state` (`version`, `errors[]`) | Hot-reload: broken files keep the old version serving, errors reported as data |
| (`dialog`, `mood`, `wave`, `unlocks`, `pick`) | as sim domain | as sim domain | Data-driven from `content/` |

## Catalog (v1, sfx domain — added phase 2, purely additive)

The worker owns backend detection, rate limiting, and the on/off
switch. Fail-silent like the classic path: `played=false` instead of
errors. `backend` names the emission path (`paplay`, `mpv`, `powershell`,
`beep`, `none`, `muted`).

| Request | Key fields | Reply | Notes |
|---|---|---|---|
| `sfx-trigger` | `name`, `id?` | `sfx-played` (`name`, `played`, `backend`) | No `id` → notify, no reply |
| `sfx-set` | `on`, `id?` | `sfx-state` (`on`) | No `id` → notify, no reply |

## Determinism

Any request carrying `seed` must be **reproducible**: same bytes in →
semantically equal replies in every language, forever (parsed structures
are compared, not raw bytes — key order may vary by encoder). Seeded
vectors are the conformance gate. Unseeded requests (live `rng`) assert
shape only, never exact values.

Seeded randomness replicates CPython's `random` bit-exact
(`rs/textack-sim/src/mt.rs` is the executable spec):

- Algorithm: MT19937 (Mersenne Twister), 32-bit, standard tempering.
- Seeding: key = minimal little-endian 32-bit words of the seed
  (`7 → [7]`, `2^32 → [0, 1]`, `0 → [0]`), fed through the reference
  `init_by_array` after `init_genrand(19650218)`.
- `random()`: `(gen() >> 5) * 2^26 + (gen() >> 6)`, all over `2^53`.
- `getrandbits(k)`: top k bits of concatenated 32-bit outputs.
- `randbelow(n)`: rejection loop on `getrandbits(bit_length(n))`.
  NB: `n.bit_length()`, not `n - 1` — powers of two need full width.
- `shuffle`: Fisher-Yates descending with `randbelow(i + 1)`.
- `choice(list)`: index via `randbelow(len)` (not `floor(random()*n)`).

Floats must also match bit-exactly: keep the operation order of
`core/*` (mixed int/float expressions evaluate left to right, `int()`
truncates toward zero), and emit floats in shortest-roundtrip form
(Python `repr`, Rust `serde_json`; Lua climbs a precision ladder, see
below — all agree over the game domain, proven live by the batteries).

Lua (`lua/mt.lua`, `lua/json.lua`) reimplements both in pure arithmetic
so the same code runs on 5.4 and LuaJIT: 32-bit ops via 16-bit halves
(doubles hold every intermediate value exactly), MT state as
integral floats, float emission by shortest-roundtrip ladder in Python
notation. Known Lua limits (documented, tested): integers must satisfy
`|v| < 2^53` and seeds `< 2^53` — beyond that the worker answers
`bad-message`; Python/Rust accept the full i64/u64 range.

## Conformance (how to add a language)

1. Implement framing (`encode`/`decode`), schema validation, and the
   catalog above against `textack/core/` semantics.
2. Port the vectors in `tests/test_engine_sim.py` (deterministic) and
   `tests/test_proto.py` (framing/validation) to your language's test
   runner — same inputs, same expected outputs.
3. Talk to the reference over a real socket pair
   (`transport.MessageIO` ↔ your implementation) before claiming done.

Reserved for later versions: `sfx` domain (`trigger`, `mix`, `mute`),
content domain (`wave-script`, `reload`), supervisor domain
(`spawn`, `health`, `restart`). Propose them as v2, never by
overloading v1 fields.

## Phase map

1. ✅ **Phase 1**: spec + in-process reference + vectors.
2. ✅ **Phase 2**: sfx domain + first live worker
   (`sfx_worker.py`, `sfx_client.py`, `tests/test_engine_sfx.py`).
3. ✅ **Phase 3**: Rust sim (`rs/textack-sim`) — full sim domain port,
   MT19937 bit-exact vs CPython, proven by `cargo test` + the live
   battery in `tests/test_rust_sim.py` (~1000 seeded replies equal).
4. ✅ **Phase 4**: Lua content (`lua/worker.lua`, data in `content/`) —
   dialog/waves/words/pick + hot-reload via `content-reload`, proven on
   lua5.4 AND luajit by `tests/test_lua_content.py` (waves 1..30 float-
   exact, every dialog line, reload session with broken files).
5. ✅ **Phase 5**: supervisor + director + `--engine` flag. `engine.json`
   declares the fleet; missing binaries degrade per-domain to
   builtin/classic; siege routes every call site through the director
   (identical answers, proven by `tests/test_director.py`).

## Fleet config (engine.json)

```json
{"components": [
  {"name": "sim-rs",
   "cmd": ["rs/textack-sim/target/debug/textack-sim"],
   "alts": [["rs/textack-sim/target/release/textack-sim"]],
   "domains": ["sim"], "fallback": "builtin"},
  {"name": "content-lua",
   "cmd": ["lua5.4", "lua/worker.lua"],
   "alts": [["luajit", "lua/worker.lua"]],
   "domains": ["content"], "fallback": "builtin"},
  {"name": "sfx-py",
   "cmd": ["{python}", "-m", "textack.engine.sfx_worker"],
   "domains": ["sfx"], "fallback": "classic"}]}
```

- `cmd`/`alts`: tried in order. `{python}` expands to the running
  interpreter; a head containing `/` must exist under the repo root,
  otherwise it is looked up on `PATH`.
- `domains`: `sim` = hit/combo/counter/xp/threshold/rank/upgrade/roll,
  `content` = dialog/mood/wave/unlocks/pick (+`content-reload`),
  `sfx` = sfx-trigger/sfx-set.
- `fallback`: `builtin` (Loopback over the reference Sim) or `classic`
  (inline `infra/*`). First live worker wins a domain; failures are
  reported in `supervisor.notes` and shown as the opening banner.
