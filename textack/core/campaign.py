# textack/core/campaign.py
"""Story-mode foundation (expansion seam).

Static chapter map + pure progress math. The live game only reads chapter
labels for the wave banner today; the full story mode (scripted stages,
choices, saves, content/story.lua, story-* protocol types) is planned in
docs/STORY_MODE.md. Import rule: stdlib only, like the rest of core/.
"""
CHAPTERS = [
    {"id": "ch1", "name": "CH1 · FIRST SIEGE", "waves": (1, 5)},
    {"id": "ch2", "name": "CH2 · IRON RAIN", "waves": (6, 10)},
    {"id": "ch3", "name": "CH3 · DEEP CIRCUIT", "waves": (11, 15)},
]

CHAPTER_LEN = 5
ENDLESS_NAME = "CH{ch} · ENDLESS"


def chapter_for(wave: int) -> dict:
    """Chapter record for any wave >= 1 (named, else generated endless)."""
    wave = max(1, int(wave))
    for ch in CHAPTERS:
        lo, hi = ch["waves"]
        if lo <= wave <= hi:
            return {"id": ch["id"], "name": ch["name"], "wave": wave,
                    "boss": wave % 5 == 0}
    num = (wave - 1) // CHAPTER_LEN + 1
    return {"id": f"ch{num}", "name": ENDLESS_NAME.format(ch=num),
            "wave": wave, "boss": wave % 5 == 0}


def stage_at(wave: int) -> dict:
    """Stage record: wave + chapter + boss flag (story scripts key on this)."""
    ch = chapter_for(wave)
    return {"wave": max(1, int(wave)), "chapter": ch["id"],
            "chapter_name": ch["name"], "boss": ch["boss"]}


def chapter_progress(best_wave: int) -> dict:
    """How far a best-wave record reaches (for future save files)."""
    best = max(0, int(best_wave))
    done = [c["id"] for c in CHAPTERS if best >= c["waves"][1]]
    current = chapter_for(best + 1)["id"] if best else "ch1"
    return {"best_wave": best, "cleared": done, "current": current}
