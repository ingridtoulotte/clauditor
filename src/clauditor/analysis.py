"""Pairwise rule analysis shared by the conflict-related checks.

Kept in one place so ``contradiction`` (same-tier clash) and ``override``
(cross-tier clash) agree on *what* a conflict is and only differ on how
precedence resolves it.
"""
from __future__ import annotations

from typing import List, Tuple

from .model import Rule
from .textutil import jaccard, normalize

# Mutually exclusive choices that almost always indicate a real conflict when
# two prescriptive rules each pick a different side.
ANTONYMS: List[Tuple[str, str]] = [
    ("tabs", "spaces"),
    ("rebase", "merge"),
    ("crlf", "lf"),
    ("npm", "pnpm"),
    ("npm", "yarn"),
    ("yarn", "pnpm"),
    ("npm", "bun"),
    ("squash", "rebase"),
]

Pair = Tuple[Rule, Rule, str]


def _key(a: Rule, b: Rule) -> frozenset:
    return frozenset((a.rid, b.rid))


def conflict_pairs(rules: List[Rule], contra_jaccard: float) -> List[Pair]:
    out: List[Pair] = []
    seen = set()
    tok_sets = [set(r.tokens) for r in rules]

    for i in range(len(rules)):
        for j in range(i + 1, len(rules)):
            a, b = rules[i], rules[j]
            k = _key(a, b)
            if k in seen:
                continue
            # 1) opposite directive on overlapping topic
            if a.polarity * b.polarity == -1:
                if jaccard(tok_sets[i], tok_sets[j]) >= contra_jaccard:
                    out.append((a, b, "opposite directives on the same topic"))
                    seen.add(k)
                    continue
            # 2) both prescriptive but pick mutually exclusive options
            if a.polarity == 1 and b.polarity == 1:
                hit = None
                for x, y in ANTONYMS:
                    ax = x in tok_sets[i] and y in tok_sets[j]
                    bx = y in tok_sets[i] and x in tok_sets[j]
                    if ax or bx:
                        hit = (x, y)
                        break
                if hit:
                    out.append((a, b, f"conflicting choice: {hit[0]} vs {hit[1]}"))
                    seen.add(k)
    return out


def duplicate_pairs(rules: List[Rule], dup_jaccard: float) -> List[Tuple[Rule, Rule, float]]:
    out: List[Tuple[Rule, Rule, float]] = []
    seen = set()
    norms = [normalize(r.text) for r in rules]
    tok_sets = [set(r.tokens) for r in rules]
    for i in range(len(rules)):
        for j in range(i + 1, len(rules)):
            a, b = rules[i], rules[j]
            k = _key(a, b)
            if k in seen:
                continue
            if not norms[i] or not norms[j]:
                continue
            if norms[i] == norms[j]:
                out.append((a, b, 1.0))
                seen.add(k)
                continue
            # same direction + very high overlap = effectively the same rule
            if a.polarity == b.polarity:
                sim = jaccard(tok_sets[i], tok_sets[j])
                if sim >= dup_jaccard and len(tok_sets[i]) >= 3:
                    out.append((a, b, round(sim, 2)))
                    seen.add(k)
    return out
