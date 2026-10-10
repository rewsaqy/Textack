# textack/engine/mode.py
"""Engine selection: classic (default) or the polyglot fleet.

Flag:  textack --engine=polyglot  (also: --engine polyglot)
Env:   TEXTACK_ENGINE=polyglot
Anything else (or nothing) means classic: pure Python, zero toolchains.
"""
CLASSIC = "classic"
POLYGLOT = "polyglot"


def active(argv=None, env=None):
    args = list(argv or [])
    mode = None
    for i, a in enumerate(args):
        if a.startswith("--engine="):
            mode = a.split("=", 1)[1].strip().lower()
        elif a == "--engine" and i + 1 < len(args):
            mode = args[i + 1].strip().lower()
    if mode in ("polyglot", "fleet", "multi"):
        return POLYGLOT
    if mode in ("classic", "single"):
        return CLASSIC
    if env is not None:
        want = (env.get("TEXTACK_ENGINE") or "").strip().lower()
        if want in ("polyglot", "fleet", "multi"):
            return POLYGLOT
    return CLASSIC
