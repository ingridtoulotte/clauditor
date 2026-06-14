"""Core data types for clauditor.

Everything here is plain stdlib dataclasses so the rest of the codebase
(loader, parser, checks, report) can pass small, explicit objects around
instead of dicts. No third-party dependencies, ever.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# Severity ordering + glyphs. Higher rank = louder.
SEVERITY_RANK = {"error": 3, "warn": 2, "info": 1}
SEVERITY_GLYPH = {"error": "🔴", "warn": "🟡", "info": "🔵"}
SEVERITY_LABEL = {"error": "error", "warn": "warn", "info": "info"}

# Points subtracted from the 100-point health score per finding.
SEVERITY_PENALTY = {"error": 6.0, "warn": 2.0, "info": 0.5}


@dataclass
class Source:
    """One instruction file in the loaded stack.

    ``weight`` is the precedence: when two rules conflict, the rule from the
    higher-weight source is the one Claude is most likely to actually follow,
    so the lower-weight one is reported as shadowed/dead.
    """

    sid: str
    path: str
    kind: str            # enterprise | project-local | project | project-rules | user | user-rules | import
    weight: int
    text: str = ""
    parent: Optional[str] = None      # sid of importer, for @-imports
    exists: bool = True

    @property
    def label(self) -> str:
        return f"{self.kind}"


@dataclass
class Rule:
    """An atomic instruction extracted from a source."""

    rid: str
    sid: str
    path: str
    weight: int
    line: int
    text: str
    heading: str = ""           # nearest markdown heading, for context
    polarity: int = 0           # +1 prescriptive, -1 prohibitive, 0 neutral
    tokens: List[str] = field(default_factory=list)   # normalized content tokens

    @property
    def location(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass
class Finding:
    """A single audit result."""

    check: str
    severity: str               # error | warn | info
    message: str
    fix: str = ""
    rule_ids: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    def sort_key(self):
        # errors first, then by first location for stable, scannable output
        loc = self.locations[0] if self.locations else ""
        return (-SEVERITY_RANK[self.severity], self.check, loc)


@dataclass
class Report:
    sources: List[Source]
    rules: List[Rule]
    findings: List[Finding]

    def by_severity(self, sev: str) -> List[Finding]:
        return [f for f in self.findings if f.severity == sev]

    @property
    def health(self) -> int:
        score = 100.0
        for f in self.findings:
            score -= SEVERITY_PENALTY[f.severity]
        return max(0, int(round(score)))

    @property
    def counts(self) -> dict:
        return {
            "error": len(self.by_severity("error")),
            "warn": len(self.by_severity("warn")),
            "info": len(self.by_severity("info")),
        }
