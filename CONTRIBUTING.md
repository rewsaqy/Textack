# Contributing to Textack

Side project just for fun — have fun. Small, focused PRs welcome.

## 5-minute quickstart

```bash
git clone <your-fork-url> textack
cd textack
pip install -e .[dev]
python3 main.py          # play it first
python3 -m pytest -q     # 21 tests, should all pass
python3 -m ruff check textack tests
```

Requirements: Python 3.9+ (CI runs 3.9–3.13), stdlib only at runtime.
No network, no build step.

## Structure map

| Layer | Dir | Contains | Add what there |
|---|---|---|---|
| core | `textack/core/` | pure logic, no curses, no I/O: `words.py`, `combat.py`, `enemies.py`, `upgrades.py`, `progression.py` | words, damage math, enemy stats, upgrades, rank/XP |
| ui | `textack/ui/` | curses only: `palette.py`, `widgets.py`, `fx.py`, `screens/` (opening, howto, siege, upgrade, outro, loop) | screens, bars, panels, effects |
| infra | `textack/infra/` | side effects: `storage.py` (best score), `quality.py` (LOW/HIGH), `waifu.py` (art), `sfx.py` (sound) | persistence, terminal compat, art, sound |
| entry | `main.py`, `textack/__main__.py` | thin shims → `textack.ui.screens.loop.game_loop` | nothing (keep thin) |

Import rule: **core → ui → infra, never backwards.**
`core` imports stdlib only. `ui` may import `core` + `infra`.
`infra` may import `core`. Nothing imports `ui/screens` except the
entry shim and other screens. See `docs/ARCHITECTURE.md`.

## Branch → PR flow

```bash
git checkout -b feat/my-thing        # or fix/..., docs/..., perf/...
# ... edit + add tests ...
python3 -m pytest -q
python3 -m ruff check textack tests
git add <files>
git commit -m "feat: short description"
git push -u origin feat/my-thing
```

Use the repo commit template so every message stays professional:

```bash
git config commit.template .gitmessage
```

Then open a PR against `main` using the template
(`.github/pull_request_template.md` fills in automatically).
Content-only PRs (new words/upgrades/enemies) use the
`content_add` issue template checklist.

## Test / lint commands

```bash
python3 -m pytest -q                 # full suite
python3 -m pytest -q tests/test_words.py   # one file
python3 -m ruff check textack tests  # lint (must be clean)
python3 -m compileall -q textack     # what CI also runs
```

New behavior needs a test. Content tweaks need at least one
assertion line (see `docs/adding-content.md` for copy-paste recipes).

## Commit convention (professional, enforced in review)

[Conventional Commits](https://www.conventionalcommits.org/) in English,
imperative mood, ≤72-char subject:

```text
<type>(<scope>): <short description>

<body — why, optional>
```

Types: `feat` (new feature), `fix` (bug fix), `perf` (performance),
`refactor` (no behavior change), `docs`, `test`, `chore`, `ci`.

Scopes: `core`, `ui`, `infra`, `engine`, `rs`, `lua`, or a file area (`siege`, `opening`, `sfx`, `proto`, `sim`).

Good:

```text
feat(siege): cache per-frame interval and rank
fix(sfx): rate-limit turret sound spam
docs(readme): clarify Windows install steps
perf(widgets): pass terminal size to avoid getmaxyx per widget
```

Bad: `FIRST UPDATE`, `feat: foto ...`, `fix bug`, `update`, any Indonesian
free-form subject. Squash-merge PRs must keep one conventional subject.

## Good first issues

- Add 5 words to `TIER2`/`TIER3` in `textack/core/words.py` (+ test).
- Rebalance one `EnemyConfig` in `textack/core/enemies.py` (+ test).
- New upgrade in `textack/core/upgrades.py` (+ test).
- Waifu art variant / palette contrast fix.
