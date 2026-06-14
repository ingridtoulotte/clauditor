"""@-import hygiene. A CLAUDE.md can pull in other files with `@path`. A broken
import means a whole block of rules you think is active simply isn't loaded."""
from __future__ import annotations

from collections import Counter
from typing import List

from ..model import Finding

NAME = "imports"


def run(rules, sources, ctx) -> List[Finding]:
    out: List[Finding] = []
    paths = Counter(s.path for s in sources if s.kind == "import")
    for s in sources:
        if s.kind != "import":
            continue
        if not s.exists:
            out.append(Finding(
                check=NAME, severity="error",
                message=f"Broken @import: '{s.path}' does not exist — its rules never load.",
                fix="Fix the path or remove the @import line.",
                locations=[f"{s.path}:0"],
            ))
    # report repeated imports once
    for p, n in paths.items():
        if n > 1:
            out.append(Finding(
                check=NAME, severity="info",
                message=f"@import pulled in {n}× (possible repeat or import cycle): {p}",
                fix="Import each file once.",
                locations=[f"{p}:0"],
            ))
    return out
