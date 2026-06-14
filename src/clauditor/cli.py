"""clauditor command-line interface."""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import __version__
from .config import load_context
from .loader import discover
from .model import SEVERITY_RANK, Report
from .registry import CHECK_MODULES, audit
from .report import (
    render_badge, render_json, render_markdown, render_sarif, render_terminal,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="clauditor",
        description="Audit your Claude Code instruction stack: find dead, "
                    "contradictory, vague, duplicate, and bloated rules.",
    )
    p.add_argument("path", nargs="?", default=".",
                   help="project dir or a CLAUDE.md file (default: current dir)")
    p.add_argument("--no-user", action="store_true",
                   help="skip ~/.claude/CLAUDE.md and user rules")
    p.add_argument("--home", metavar="DIR", help="override home dir (for testing)")
    p.add_argument("--enterprise", metavar="FILE",
                   help="path to an enterprise managed CLAUDE policy file")
    p.add_argument("--format", choices=["term", "json", "md", "sarif", "badge"],
                   default="term", help="output format (default: term)")
    p.add_argument("--json", action="store_true", help="shortcut for --format json")
    p.add_argument("--sarif", action="store_true", help="shortcut for --format sarif")
    p.add_argument("--output", "-o", metavar="FILE", help="write report to FILE")
    p.add_argument("--min-severity", choices=["error", "warn", "info"],
                   default="info", help="hide findings below this severity")
    p.add_argument("--ci", action="store_true",
                   help="exit non-zero when failing findings exist")
    p.add_argument("--strict", action="store_true",
                   help="with --ci, treat warnings as failures too")
    p.add_argument("--no-color", action="store_true", help="disable ANSI color")
    p.add_argument("--list-checks", action="store_true", help="list checks and exit")
    p.add_argument("--selftest", action="store_true", help="run built-in tests and exit")
    p.add_argument("--version", action="version", version=f"clauditor {__version__}")
    return p


def _filter(report: Report, min_sev: str) -> Report:
    floor = SEVERITY_RANK[min_sev]
    report.findings = [f for f in report.findings if SEVERITY_RANK[f.severity] >= floor]
    return report


def main(argv: Optional[List[str]] = None) -> int:
    # Glyphs (🔴 → █) must survive non-UTF-8 consoles (e.g. Windows cp1252).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = _build_parser().parse_args(argv)

    if args.selftest:
        from .selftest import run_selftest
        return run_selftest()

    if args.list_checks:
        print("Available checks:")
        for name in CHECK_MODULES:
            mod = __import__(f"clauditor.checks.{name}", fromlist=["run"])
            doc = (mod.__doc__ or "").strip().splitlines()[0] if mod.__doc__ else ""
            print(f"  {name:<14} {doc}")
        return 0

    target = args.path
    cfg_dir = target if os.path.isdir(target) else os.path.dirname(os.path.abspath(target))
    ctx = load_context(cfg_dir or ".")

    sources = discover(target, home=args.home, include_user=not args.no_user,
                       enterprise=args.enterprise)
    report = audit(sources, ctx)
    report = _filter(report, args.min_severity)

    fmt = "json" if args.json else "sarif" if args.sarif else args.format
    if fmt == "json":
        text = render_json(report)
    elif fmt == "sarif":
        text = render_sarif(report)
    elif fmt == "badge":
        text = render_badge(report)
    elif fmt == "md":
        text = render_markdown(report)
    else:
        use_color = (not args.no_color and not os.environ.get("NO_COLOR")
                     and (args.output is None) and sys.stdout.isatty())
        text = render_terminal(report, color=use_color, target=target)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"wrote {args.output}")
    else:
        print(text)

    if args.ci:
        fail = report.counts["error"] > 0 or (args.strict and report.counts["warn"] > 0)
        return 1 if fail else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
