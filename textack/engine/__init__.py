# textack/engine/__init__.py
"""Polyglot engine v2: wire protocol + workers + director.

The classic game runs without this package. It exists so every worker
(Rust sim, Lua content, Python sfx) implements one contract:
docs/PROTOCOL.md. Import rule: engine imports core + stdlib only, except
director.py which reuses infra/sfx for the classic fallback.
"""
