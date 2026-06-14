"""Politeness and meta-narration. Lines like "please" or "this file describes…"
carry no instruction but still cost tokens on every turn."""
from __future__ import annotations

import re
from typing import List

from ..model import Finding

NAME = "filler"

_PLEASANTRY = re.compile(
    r"\b(please|thank you|thanks|kindly|feel free|as an ai|i would appreciate|"
    r"if you don't mind|much appreciated)\b", re.IGNORECASE)
_META = re.compile(
    r"^\s*(this (file|document|section)|the following|below (are|is)|here (are|is)|"
    r"in this (file|document))\b", re.IGNORECASE)


def run(rules, sources, ctx) -> List[Finding]:
    out: List[Finding] = []
    for r in rules:
        if _PLEASANTRY.search(r.text):
            out.append(Finding(
                check=NAME, severity="info",
                message=f"Politeness filler — no instruction, pure token cost.\n      {r.text}",
                fix="Drop pleasantries; instructions don't need them.",
                rule_ids=[r.rid], locations=[r.location],
            ))
        elif r.polarity == 0 and _META.search(r.text):
            out.append(Finding(
                check=NAME, severity="info",
                message=f"Meta-narration — describes the file instead of instructing.\n      {r.text}",
                fix="Cut or convert into an actual rule.",
                rule_ids=[r.rid], locations=[r.location],
            ))
    return out
