# Lua content worker

Dialog, waves, words + hot-reload over stdio (protocol v1, content domain).

## Run

```bash
lua5.4 lua/worker.lua [--content DIR]   # default: content/
luajit lua/worker.lua                   # same code, both supported
```

## Hot-reload

Edit anything under `content/` while the worker runs, then send:

```json
{"v": 1, "t": "content-reload", "id": 1}
```

→ `{"t": "content-state", "version": 2, "errors": []}`. Broken files
keep the old version serving and report `errors` as data (never a
crash). In game: planned F5 key (supervisor phase).

## Prove it

```bash
python -m pytest tests/test_lua_content.py -q
```

Batteries compare every reply against Python live: all waves 1..30
(float-exact), every dialog line on both interpreters, seeded picks,
and a full reload session (break → errors → fix → version bump).

## Portability rules

`lua/` is pure-arithmetic Lua (no bitops, no `goto`, no `utf8` lib) so
one codebase runs on 5.1–5.4 and LuaJIT. `lua/json.lua` is a minimal
JSON codec (arrays via `json.array()` marker); `lua/mt.lua` is MT19937
bit-exact vs CPython. Known limits: integers `|v| < 2^53`, seeds
`< 2^53` (see `docs/PROTOCOL.md`).
