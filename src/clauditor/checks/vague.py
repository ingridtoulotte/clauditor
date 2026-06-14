"""Vague / unenforceable rules. Anthropic's own docs note adherence drops when
an instruction is open to interpretation. A rule Claude can't verify it followed
is a rule it will quietly skip under pressure."""
from __future__ import annotations

import re
from typing import List

from ..model import Finding

NAME = "vague"

WEASELS = [
    "try to", "if possible", "as needed", "when appropriate", "where possible",
    "as much as possible", "generally", "usually", "tend to", "be careful",
    "ideally", "consider", "might want to", "maybe", "if you can", "etc.",
    "and so on", "where relevant", "as you see fit", "use your judgment",
    "be mindful", "keep in mind", "be sure to be", "in most cases",
]
_PATTERNS = [re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE) for w in WEASELS]


def run(rules, sources, ctx) -> List[Finding]:
    out: List[Finding] = []
    for r in rules:
        hits = sorted({p.pattern.strip("\\b") for p in _PATTERNS if p.search(r.text)})
        # unstrip: recover original phrase for the message
        phrases = [w for w in WEASELS if re.search(r"\b" + re.escape(w) + r"\b", r.text, re.IGNORECASE)]
        if phrases:
            out.append(Finding(
                check=NAME,
                severity="warn",
                message=(f"Vague rule (\"{', '.join(phrases)}\") — hard for Claude to "
                         f"comply with or verify.\n      {r.text}"),
                fix="Rewrite as a concrete, checkable instruction (a command, a rule with a clear trigger).",
                rule_ids=[r.rid],
                locations=[r.location],
            ))
    return out
