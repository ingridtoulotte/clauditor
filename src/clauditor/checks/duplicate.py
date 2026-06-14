"""Duplicate / near-duplicate rules across the stack. Repeating a rule doesn't
make Claude follow it harder — it just spends context budget twice and makes the
config drift over time."""
from __future__ import annotations

from typing import List

from ..analysis import duplicate_pairs
from ..model import Finding
from ..textutil import estimate_tokens

NAME = "duplicate"


def run(rules, sources, ctx) -> List[Finding]:
    out: List[Finding] = []
    for a, b, sim in duplicate_pairs(rules, ctx.dup_jaccard):
        waste = estimate_tokens(b.text)
        kind = "identical" if sim >= 1.0 else f"{int(sim * 100)}% similar"
        out.append(Finding(
            check=NAME,
            severity="info",
            message=(f"Duplicate rule ({kind}), ~{waste} tokens wasted.\n"
                     f"      A: {a.text} [{a.location}]\n"
                     f"      B: {b.text} [{b.location}]"),
            fix="Keep one copy; delete the other.",
            rule_ids=[a.rid, b.rid],
            locations=[a.location, b.location],
        ))
    return out
