"""Discover and load the Claude Code instruction stack in precedence order.

Higher ``weight`` = higher precedence (more likely to actually be followed
when rules conflict). The ordering mirrors Claude Code's documented hierarchy:
enterprise managed policy > project (nearer the cwd wins) > project .claude/rules
> user (~/.claude). @-imports inherit the weight of the file that pulls them in.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from .model import Source

W_ENTERPRISE = 1000
W_PROJECT_LOCAL = 800
W_PROJECT = 700          # nearest dir; parents step down by 10
W_PROJECT_RULES = 650
W_USER = 400
W_USER_RULES = 350

_IMPORT = re.compile(r"(?:^|\s)@(\S+)")
_MAX_CLIMB = 25
_MAX_IMPORT_DEPTH = 8


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return None


def _is_import_path(tok: str) -> bool:
    tok = tok.rstrip(".,;:)")
    if tok.startswith(("./", "../", "~/", "/")):
        return True
    return tok.endswith(".md") and "/" in tok


def _resolve_import(tok: str, base_dir: Path, home: Path) -> Path:
    tok = tok.rstrip(".,;:)")
    if tok.startswith("~/"):
        return (home / tok[2:]).resolve()
    p = Path(tok)
    if p.is_absolute():
        return p.resolve()
    return (base_dir / tok).resolve()


def _project_root(start: Path) -> Path:
    cur = start
    for _ in range(_MAX_CLIMB):
        if (cur / ".git").exists() or (cur / ".claude").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start


def _expand_imports(src: Source, home: Path, depth: int, seen: set, out: List[Source]):
    if depth > _MAX_IMPORT_DEPTH:
        return
    base_dir = Path(src.path).resolve().parent
    for tok in _IMPORT.findall(src.text or ""):
        if not _is_import_path(tok):
            continue
        target = _resolve_import(tok, base_dir, home)
        key = str(target).lower()
        sid = "imp:" + key
        if key in seen:
            # circular or repeated import: record a stub so the imports check flags it
            out.append(Source(sid=sid, path=str(target), kind="import",
                              weight=src.weight, text="", parent=src.sid,
                              exists=target.exists()))
            continue
        seen.add(key)
        text = _read(target) if target.exists() else None
        child = Source(
            sid=sid, path=str(target), kind="import", weight=src.weight,
            text=text or "", parent=src.sid, exists=target.exists() and text is not None,
        )
        out.append(child)
        if child.exists:
            _expand_imports(child, home, depth + 1, seen, out)


def discover(target: str, home: Optional[str] = None, include_user: bool = True,
             enterprise: Optional[str] = None) -> List[Source]:
    home_path = Path(home).expanduser().resolve() if home else Path.home()
    tgt = Path(target).expanduser().resolve()
    sources: List[Source] = []
    seen_imports: set = set()

    if enterprise:
        ep = Path(enterprise).expanduser().resolve()
        sources.append(Source("enterprise", str(ep), "enterprise", W_ENTERPRISE,
                              _read(ep) or "", exists=ep.exists()))

    # --- project chain ------------------------------------------------------
    if tgt.is_file():
        start_dir = tgt.parent
        text = _read(tgt) or ""
        sources.append(Source("project:0", str(tgt), "project", W_PROJECT, text))
    else:
        start_dir = tgt
        depth = 0
        cur = tgt
        for _ in range(_MAX_CLIMB):
            for name, kind, base in (("CLAUDE.local.md", "project-local", W_PROJECT_LOCAL),
                                     ("CLAUDE.md", "project", W_PROJECT)):
                f = cur / name
                if f.is_file():
                    sources.append(Source(
                        sid=f"{kind}:{depth}", path=str(f), kind=kind,
                        weight=base - depth * 10, text=_read(f) or "",
                    ))
            if cur.parent == cur:
                break
            cur = cur.parent
            depth += 1

    # --- project .claude/rules/*.md ----------------------------------------
    proot = _project_root(start_dir)
    rules_dir = proot / ".claude" / "rules"
    if rules_dir.is_dir():
        for f in sorted(rules_dir.glob("*.md")):
            sources.append(Source(
                sid=f"project-rules:{f.name}", path=str(f), kind="project-rules",
                weight=W_PROJECT_RULES, text=_read(f) or "",
            ))

    # --- user global --------------------------------------------------------
    if include_user:
        ucfg = home_path / ".claude" / "CLAUDE.md"
        if ucfg.is_file():
            sources.append(Source("user", str(ucfg), "user", W_USER, _read(ucfg) or ""))
        urules = home_path / ".claude" / "rules"
        if urules.is_dir():
            for f in sorted(urules.glob("*.md")):
                sources.append(Source(
                    sid=f"user-rules:{f.name}", path=str(f), kind="user-rules",
                    weight=W_USER_RULES, text=_read(f) or "",
                ))

    # --- expand @-imports for every concrete source ------------------------
    imports: List[Source] = []
    for s in list(sources):
        if s.exists and s.text:
            _expand_imports(s, home_path, 1, seen_imports, imports)
    sources.extend(imports)

    sources.sort(key=lambda s: (-s.weight, s.path))
    return sources
