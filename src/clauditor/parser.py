"""Split an instruction file into atomic rules.

A "rule" is one actionable line: a bullet/numbered item, or an imperative
sentence in a paragraph. Headings give context but are not rules. Fenced code
blocks are skipped entirely (examples are not instructions). Line numbers are
1-based so output is clickable as ``path:line``.
"""
from __future__ import annotations

import re
from typing import List

from .model import Rule
from .textutil import polarity, tokenize

_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+)$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _looks_like_rule(line: str) -> bool:
    """A bare paragraph line counts as a rule if it reads like an instruction."""
    s = line.strip()
    if len(s) < 4:
        return False
    if s.startswith(("|", ">", "<")):       # tables, quotes, html
        return False
    if s.endswith(":") and len(s.split()) <= 6:   # section lead-in like "Rules:"
        return False
    return True


def parse_source(sid: str, path: str, weight: int, text: str) -> List[Rule]:
    text = _HTML_COMMENT.sub(" ", text)
    rules: List[Rule] = []
    heading = ""
    in_fence = False
    n = 0
    for raw in text.splitlines():
        n += 1
        if _FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _HEADING.match(line)
        if m:
            heading = m.group(2).strip()
            continue
        b = _BULLET.match(line)
        body = b.group(1).strip() if b else line.strip()
        if not b and not _looks_like_rule(line):
            continue
        rid = f"{sid}#{n}"
        rules.append(
            Rule(
                rid=rid,
                sid=sid,
                path=path,
                weight=weight,
                line=n,
                text=body,
                heading=heading,
                polarity=polarity(body),
                tokens=tokenize(body),
            )
        )
    return rules
