"""Render a Report as colored terminal output, JSON, Markdown, SARIF, or a
shields.io badge endpoint."""
from __future__ import annotations

import json
import os
from typing import List

from . import __version__
from .model import SEVERITY_GLYPH, Report, Source
from .textutil import estimate_tokens


class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; YEL = "\033[33m"; BLU = "\033[34m"
    GRN = "\033[32m"; CYA = "\033[36m"; GRY = "\033[90m"


_SEV_COLOR = {"error": C.RED, "warn": C.YEL, "info": C.BLU}


def _paint(enabled):
    if enabled:
        return lambda s, col: f"{col}{s}{C.RESET}"
    return lambda s, col: s


def _short(path: str) -> str:
    try:
        rel = os.path.relpath(path, os.getcwd())
        return rel if len(rel) < len(path) else path
    except ValueError:
        return path


def _bar(score: int, width: int = 24) -> str:
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def render_terminal(report: Report, color: bool = True, target: str = ".") -> str:
    p = _paint(color)
    out: List[str] = []
    out.append("")
    out.append(p("  clauditor", C.BOLD + C.CYA) + p("  ·  Claude config audit", C.GRY))
    out.append("")

    # precedence map ---------------------------------------------------------
    out.append(p("  PRECEDENCE  ", C.BOLD) + p("(top = wins conflicts)", C.GRY))
    shown = [s for s in report.sources if s.exists]
    if not shown:
        out.append(p("    no CLAUDE.md / .claude rules found here", C.GRY))
    for s in shown:
        toks = estimate_tokens(s.text) if s.text else 0
        kind = f"{s.kind:<14}"
        line = f"    {kind} {_short(s.path)}  {C.GRY}~{toks}t{C.RESET}" if color \
            else f"    {kind} {_short(s.path)}  ~{toks}t"
        out.append(line)
    for s in report.sources:
        if not s.exists:
            out.append(p(f"    {'import(broken)':<14} {_short(s.path)}  MISSING", C.RED))
    out.append("")

    # findings ---------------------------------------------------------------
    counts = report.counts
    if not report.findings:
        out.append(p("  ✓ No issues. Every rule is reachable, consistent, and lean.", C.GRN))
    else:
        out.append(p(f"  FINDINGS  ", C.BOLD) +
                   p(f"{len(report.findings)} total", C.GRY))
        out.append("")
        for f in report.findings:
            glyph = SEVERITY_GLYPH[f.severity]
            loc = f.locations[0] if f.locations else ""
            head = f"  {glyph} {p(f.severity.upper(), _SEV_COLOR[f.severity])} " \
                   f"{p(f.check, C.BOLD)}  {p(_short(loc), C.GRY)}"
            out.append(head)
            for ln in f.message.splitlines():
                out.append(f"      {ln}" if not ln.startswith("      ") else ln)
            if f.fix:
                out.append(p(f"      → {f.fix}", C.GRY))
            out.append("")

    # verdict ----------------------------------------------------------------
    health = report.health
    hc = C.GRN if health >= 80 else C.YEL if health >= 50 else C.RED
    out.append(p("  HEALTH  ", C.BOLD) + p(f"[{_bar(health)}] {health}/100", hc))
    out.append("    " + " ".join([
        p(f"{counts['error']} error", C.RED),
        p(f"{counts['warn']} warn", C.YEL),
        p(f"{counts['info']} info", C.BLU),
        p(f"· {len(report.rules)} rules · {len(shown)} files", C.GRY),
    ]))
    out.append("")
    return "\n".join(out)


def render_json(report: Report) -> str:
    data = {
        "health": report.health,
        "counts": report.counts,
        "rules": len(report.rules),
        "sources": [
            {"kind": s.kind, "path": s.path, "weight": s.weight,
             "exists": s.exists, "tokens": estimate_tokens(s.text) if s.text else 0}
            for s in report.sources
        ],
        "findings": [
            {"check": f.check, "severity": f.severity, "message": f.message,
             "fix": f.fix, "locations": f.locations}
            for f in report.findings
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# --- SARIF (GitHub code-scanning) ------------------------------------------

# One-line summary per check, surfaced as the rule description in GitHub's
# code-scanning UI. Kept in sync with docs/checks.md.
_CHECK_HELP = {
    "contradiction": "Two rules clash at equal precedence; Claude resolves them non-deterministically.",
    "override": "A rule is silently overridden by a higher-precedence rule, so it never takes effect.",
    "vague": "Vague or unenforceable wording Claude cannot verify it followed.",
    "duplicate": "Duplicate or near-duplicate rule that wastes context budget.",
    "imports": "Broken, cyclic, or repeated @import that fails to load rules.",
    "bloat": "Oversized instruction file or total budget, loaded on every turn.",
    "filler": "Politeness or meta-narration that carries no instruction.",
}

# clauditor severity -> SARIF level.
_SARIF_LEVEL = {"error": "error", "warn": "warning", "info": "note"}


def _split_loc(loc: str):
    """'path/to/file.md:12' -> ('path/to/file.md', 12). Drive-letter safe."""
    path, _, line = loc.rpartition(":")
    if not path:                       # no ':' at all
        return loc, 1
    try:
        n = int(line)
    except ValueError:
        return loc, 1
    return path, max(1, n)


def _uri(path: str) -> str:
    """Repo-relative, forward-slashed URI for SARIF artifact locations."""
    try:
        rel = os.path.relpath(path, os.getcwd())
    except ValueError:                 # different drive on Windows
        rel = path
    return rel.replace("\\", "/")


def render_sarif(report: Report) -> str:
    """SARIF 2.1.0 — upload with github/codeql-action/upload-sarif to get
    findings as inline annotations in the PR 'Files changed' tab."""
    used = []
    seen = set()
    for f in report.findings:
        if f.check not in seen:
            seen.add(f.check)
            used.append(f.check)

    rules = [
        {
            "id": name,
            "name": name,
            "shortDescription": {"text": _CHECK_HELP.get(name, name)},
            "helpUri": "https://github.com/ingridtoulotte/clauditor/blob/main/docs/checks.md",
        }
        for name in used
    ]

    results = []
    for f in report.findings:
        text = " ".join(f.message.split())
        if f.fix:
            text += f"  Fix: {f.fix}"
        locations = []
        for loc in f.locations:
            path, line = _split_loc(loc)
            locations.append({
                "physicalLocation": {
                    "artifactLocation": {"uri": _uri(path)},
                    "region": {"startLine": line},
                }
            })
        results.append({
            "ruleId": f.check,
            "level": _SARIF_LEVEL[f.severity],
            "message": {"text": text},
            "locations": locations,
        })

    doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "clauditor",
                "informationUri": "https://github.com/ingridtoulotte/clauditor",
                "version": __version__,
                "rules": rules,
            }},
            "results": results,
        }],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


def render_badge(report: Report) -> str:
    """shields.io endpoint JSON. Point a badge at a committed copy of this to
    show live config health in any README:
    https://img.shields.io/endpoint?url=<raw-url-to-this-file>"""
    h = report.health
    color = "brightgreen" if h >= 80 else "yellow" if h >= 50 else "red"
    return json.dumps({
        "schemaVersion": 1,
        "label": "claude config",
        "message": f"{h}/100",
        "color": color,
    }, ensure_ascii=False)


def render_markdown(report: Report) -> str:
    c = report.counts
    lines = [
        "# clauditor report",
        "",
        f"**Health: {report.health}/100** — "
        f"🔴 {c['error']} · 🟡 {c['warn']} · 🔵 {c['info']} "
        f"· {len(report.rules)} rules · {sum(1 for s in report.sources if s.exists)} files",
        "",
        "## Precedence (top wins)",
        "",
        "| weight | kind | file | ~tokens |",
        "|---:|---|---|---:|",
    ]
    for s in report.sources:
        if s.exists:
            lines.append(f"| {s.weight} | {s.kind} | `{_short(s.path)}` | {estimate_tokens(s.text) if s.text else 0} |")
    lines += ["", "## Findings", ""]
    if not report.findings:
        lines.append("No issues found.")
    for f in report.findings:
        glyph = SEVERITY_GLYPH[f.severity]
        loc = f" — `{_short(f.locations[0])}`" if f.locations else ""
        msg = f.message.replace("\n", " ").strip()
        lines.append(f"- {glyph} **{f.check}**{loc}: {msg}")
        if f.fix:
            lines.append(f"  - _fix:_ {f.fix}")
    lines.append("")
    return "\n".join(lines)
