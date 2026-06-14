"""Small, dependency-free text helpers shared by the parser and checks.

Token estimates are deliberately simple heuristics. clauditor never claims to
reproduce Anthropic's exact tokenizer; it gives a stable, explainable proxy so
you can compare files against each other and against a budget.
"""
from __future__ import annotations

import re
from typing import List, Set

STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "while",
    "to", "of", "in", "on", "at", "for", "with", "by", "from", "as", "is", "are",
    "be", "been", "being", "it", "its", "this", "that", "these", "those", "you",
    "your", "we", "our", "i", "me", "my", "do", "does", "did", "can", "will",
    "would", "should", "could", "may", "might", "shall", "must", "not", "no",
    "any", "all", "so", "than", "into", "out", "up", "down", "over", "about",
    "please", "always", "never", "use", "using", "used",
}

# Words signalling a prescriptive (do this) vs prohibitive (don't) directive.
POSITIVE_MARKERS = (
    "always", "must", "should", "use", "prefer", "ensure", "make sure",
    "require", "enforce", "do ", "run ", "write ", "keep ", "add ",
)
NEGATIVE_MARKERS = (
    "never", "don't", "do not", "avoid", "no ", "without", "skip",
    "forbid", "disallow", "must not", "should not", "do not use",
)

_WORD = re.compile(r"[a-z0-9][a-z0-9\-_/.]*")


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip markdown decoration."""
    t = text.lower().strip()
    t = re.sub(r"[`*_~]+", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" .;:")


def tokenize(text: str) -> List[str]:
    """Content tokens with stopwords removed, order preserved, deduped."""
    words = _WORD.findall(text.lower())
    out: List[str] = []
    seen: Set[str] = set()
    for w in words:
        w = w.strip("./-_")
        if len(w) < 2 or w in STOPWORDS:
            continue
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def polarity(text: str) -> int:
    """+1 prescriptive, -1 prohibitive, 0 neutral. Negative wins ties."""
    t = " " + text.lower() + " "
    neg = any(m in t for m in NEGATIVE_MARKERS)
    pos = any(m in t for m in POSITIVE_MARKERS)
    if neg:
        return -1
    if pos:
        return 1
    return 0


def estimate_tokens(text: str) -> int:
    """Rough token count. ~4 chars/token, floored by word count."""
    chars = len(text)
    words = len(re.findall(r"\S+", text))
    return max(words, round(chars / 4))
