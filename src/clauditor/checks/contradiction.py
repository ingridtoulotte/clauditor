"""Same-tier contradictions: two rules clash but sit at equal precedence, so
Claude Code has *no* deterministic way to resolve them — behavior is arbitrary
across runs. This is the loudest finding clauditor emits."""
from __future__ import annotations

from typing import List

from ..analysis import conflict_pairs
from ..model import Finding

NAME = "contradiction"


def run(rules, sources, ctx) -> List[Finding]:
    out: List[Finding] = []
    for a, b, reason in conflict_pairs(rules, ctx.contra_jaccard):
        if a.weight != b.weight:
            continue  # cross-tier clashes are handled by the override check
        out.append(Finding(
            check=NAME,
            severity="error",
            message=(f"Contradiction ({reason}) at equal precedence — Claude "
                     f"picks one arbitrarily.\n      A: {a.text}\n      B: {b.text}"),
            fix="Delete or reconcile one of the two rules so only one survives.",
            rule_ids=[a.rid, b.rid],
            locations=[a.location, b.location],
        ))
    return out
