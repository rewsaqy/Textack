# textack/engine/__init__.py
"""Polyglot engine v2, phase 1: wire protocol + in-process reference.

The classic game does not use this package yet. It exists so every future
worker (Rust sim, Lua content, C pixel math) implements one contract:
docs/PROTOCOL.md. Import rule: engine imports core + stdlib only.
"""
