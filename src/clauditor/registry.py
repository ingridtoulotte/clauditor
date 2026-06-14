"""Run every check over a loaded stack and assemble a Report.

Adding a check = add a module to CHECK_MODULES. No other wiring needed.
"""
from __future__ import annotations

from importlib import import_module
from typing import List

from .config import CheckContext
from .model import Finding, Report, Source
from .parser import parse_source

CHECK_MODULES = [
    "contradiction",
    "override",
    "vague",
    "duplicate",
    "imports",
    "bloat",
    "filler",
]


def _checks():
    for name in CHECK_MODULES:
        yield import_module(f".checks.{name}", package=__package__)


def parse_all(sources: List[Source]):
    rules = []
    for s in sources:
        if s.exists and s.text:
            rules.extend(parse_source(s.sid, s.path, s.weight, s.text))
    return rules


def audit(sources: List[Source], ctx: CheckContext) -> Report:
    rules = parse_all(sources)
    findings: List[Finding] = []
    for mod in _checks():
        try:
            findings.extend(mod.run(rules, sources, ctx))
        except Exception as exc:  # a broken check must never crash the run
            findings.append(Finding(
                check=getattr(mod, "NAME", mod.__name__),
                severity="info",
                message=f"check failed to run: {exc}",
            ))
    findings.sort(key=lambda f: f.sort_key())
    return Report(sources=sources, rules=rules, findings=findings)
