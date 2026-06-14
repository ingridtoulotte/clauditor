"""Cross-tier overrides: a higher-precedence rule silently kills a
lower-precedence one. The losing rule is *dead* — it's in your config, it costs
tokens, and it will never change Claude's behavior. These are the rules people
swear they wrote but Claude "ignores"."""
from __future__ import annotations

from typing import List

from ..analysis import conflict_pairs
from ..model import Finding

NAME = "override"


def run(rules, sources, ctx) -> List[Finding]:
    out: List[Finding] = []
    for a, b, reason in conflict_pairs(rules, ctx.contra_jaccard):
        if a.weight == b.weight:
            continue  # same-tier clashes belong to the contradiction check
        winner, loser = (a, b) if a.weight > b.weight else (b, a)
        out.append(Finding(
            check=NAME,
            severity="warn",
            message=(f"Dead rule: '{loser.text}' is silently overridden by a "
                     f"higher-precedence rule ({reason}).\n"
                     f"      winner: {winner.text} [{winner.location}]"),
            fix=("Remove the dead rule, or move it to the higher-precedence layer "
                 "if you actually want it to win."),
            rule_ids=[loser.rid, winner.rid],
            locations=[loser.location, winner.location],
        ))
    return out
