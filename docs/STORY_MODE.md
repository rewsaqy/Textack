# Story mode expansion (PLAN — not implemented)

Target: a campaign layer on top of the endless siege — chapters with a
beginning/middle/boss, scripted intros, and progress saves. This doc is
the build order; `textack/core/campaign.py` (chapter map + pure progress
math, already live for banner labels) is step 0.

## Build order

1. ✅ **Step 0 (done)**: `core/campaign.py` — `CHAPTERS`, `chapter_for`,
   `stage_at`, `chapter_progress` + tests. Banner shows the chapter.
2. **Content**: `content/story.lua` — chapters with stages:
   `{waves, intro lines, boss intro, clear line}` per chapter, reusing
   the hot-reload path (`content-reload` already works).
3. **Protocol (additive, v1 stays)**: `story-stage {chapter, id?}` →
   `stage {waves, intro[], boss_intro, clear}`; `story-advance
   {chapter, cleared}` → `ack`. Reserved names: `story-stage`,
   `story-advance`, `story-choice`. Never overload existing fields.
4. **Workers**: Lua content worker serves `story-*` from `story.lua`;
   Python Sim mirrors it (fallback); Rust port follows the vectors.
5. **Director + UI**: `director.story_stage()` cached per chapter;
   siege shows the intro card on chapter entry (reuse the wave banner
   box), F5 reloads story text live.
6. **Saves**: extend `waifu.json`-style file with
   `{"story": {"cleared": [...], "current": "ch2"}}` via
   `chapter_progress(best_wave)`; menu gains "Story" entry.

## Rules carried over

- Same contract discipline: vectors first, then ports; seeded
  determinism where randomness appears.
- Classic mode ignores story data (banner label is the only trace).
- Fail-open: broken `story.lua` keeps endless mode running.
