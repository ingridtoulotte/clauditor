"""clauditor — audit your Claude Code instruction stack.

Find the rules Claude silently ignores: dead/overridden rules, same-tier
contradictions, vague/unenforceable phrasing, duplicates, broken @-imports, and
context bloat. Pure Python standard library, fully local, zero network calls.
"""
from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
