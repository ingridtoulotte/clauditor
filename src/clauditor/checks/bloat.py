"""Context budget. Every token in your instruction stack is loaded into *every*
turn. Oversized files crowd out the actual work and dilute attention across rules."""
from __future__ import annotations

from typing import List

from ..model import Finding
from ..textutil import estimate_tokens

NAME = "bloat"


def run(rules, sources, ctx) -> List[Finding]:
    out: List[Finding] = []
    total = 0
    for s in sources:
        if not s.exists or not s.text:
            continue
        toks = estimate_tokens(s.text)
        total += toks
        lines = s.text.count("\n") + 1
        if s.kind == "user" and lines > ctx.global_max_lines:
            out.append(Finding(
                check=NAME, severity="warn",
                message=(f"Global CLAUDE.md is {lines} lines (~{toks} tokens). "
                         f"It loads in every project, every turn."),
                fix=f"Trim to ~{ctx.global_max_lines} lines; push project-specific rules into project CLAUDE.md.",
                locations=[f"{s.path}:1"],
            ))
        elif toks > ctx.file_max_tokens:
            out.append(Finding(
                check=NAME, severity="warn",
                message=f"Large instruction file: ~{toks} tokens ({lines} lines).",
                fix=f"Split or trim; aim under ~{ctx.file_max_tokens} tokens per file.",
                locations=[f"{s.path}:1"],
            ))
    if total > ctx.total_budget_tokens:
        out.append(Finding(
            check=NAME, severity="info",
            message=(f"Total instruction stack ≈ {total} tokens across "
                     f"{sum(1 for s in sources if s.exists and s.text)} files — "
                     f"loaded on every single turn."),
            fix=f"Budget is ~{ctx.total_budget_tokens} tokens; prune dead and duplicate rules first.",
            locations=[],
        ))
    return out
