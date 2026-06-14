"""Tunable thresholds. Override any of these via a .clauditor.toml at the
project root (parsed with stdlib tomllib on 3.11+, or a tiny built-in reader)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckContext:
    # bloat
    global_max_lines: int = 35          # Anthropic guidance: keep global CLAUDE.md tight
    file_max_tokens: int = 1500
    total_budget_tokens: int = 4000
    # similarity thresholds
    contra_jaccard: float = 0.45
    dup_jaccard: float = 0.85


DEFAULT = CheckContext()


def load_context(path) -> CheckContext:
    """Best-effort read of .clauditor.toml; falls back to defaults silently."""
    import os
    ctx = CheckContext()
    cfg = os.path.join(str(path), ".clauditor.toml")
    if not os.path.isfile(cfg):
        return ctx
    data = {}
    try:
        import tomllib  # py3.11+
        with open(cfg, "rb") as fh:
            data = tomllib.load(fh).get("clauditor", {})
    except Exception:
        data = _mini_toml(cfg)
    for k, v in data.items():
        if hasattr(ctx, k):
            cur = getattr(ctx, k)
            try:
                setattr(ctx, k, type(cur)(v))
            except (TypeError, ValueError):
                pass
    return ctx


def _mini_toml(path: str) -> dict:
    """Dependency-free reader for `key = value` lines under [clauditor]."""
    out, in_section = {}, False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                s = line.split("#", 1)[0].strip()
                if not s:
                    continue
                if s.startswith("["):
                    in_section = s.strip("[]").strip() == "clauditor"
                    continue
                if in_section and "=" in s:
                    k, v = (p.strip() for p in s.split("=", 1))
                    v = v.strip().strip('"').strip("'")
                    out[k] = v
    except OSError:
        pass
    return out
