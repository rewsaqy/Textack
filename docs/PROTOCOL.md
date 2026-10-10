# Textack Wire Protocol v1

Contract between the **director** (Python game loop) and **workers**
(sim, sfx, content — in any language). Phase 1 ships the contract plus
an in-process reference (`textack/engine/`); no game flow uses it yet.

## Transport

- **NDJSON**: one JSON object per line, UTF-8, `\n` terminated.
- Works over anything byte-streamed: socket pairs, pipes, subprocess
  stdio (`textack.engine.transport.MessageIO`).
- A reader buffers until `\n`; a writer flushes every message.
- EOF (empty read) = peer gone → raise/return, never hang silently.
- Future supervisor may add length-prefixing; v1 stays human-readable
  (`nc`, `tee`, and `jq` must work for debugging).

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

- `int` means int — JSON `true`/`false` must **not** validate as int.
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
| `hello` | `role`, `proto: [1]` | `ready` (`role`, `proto: 1`) | Handshake |
| `ping` | — | `pong` | Liveness probe |
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
| `unlocks` | `unlocked[]`, `wave` | `unlocks-is` (`ids[]`) | Mirrors `check_unlocks` |
| `bye` | — | `bye` | Clean shutdown |

## Determinism

Any request carrying `seed` must be **byte-deterministic**: same bytes
in → same bytes out, in every language, forever. Seeded vectors are
the conformance gate. Unseeded requests (live `rng`) assert shape
only, never exact values.

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

1. ✅ **Phase 1 (this doc)**: spec + in-process reference + vectors.
2. SFX worker (first audible payoff).
3. Sim core port (Rust) against these vectors.
4. Content scripts (Lua) + hot-reload.
5. Supervisor + `engine.yaml` + `--engine=polyglot` flag.
