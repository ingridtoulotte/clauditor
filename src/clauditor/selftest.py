"""Hermetic self-test: `clauditor --selftest`. No network, no fixtures on disk
required (it builds its own temp project). Exit 0 = all green."""
from __future__ import annotations

import io
import json
import os
import tempfile
from contextlib import redirect_stdout

from .analysis import conflict_pairs, duplicate_pairs
from .checks import bloat, contradiction, duplicate, filler, imports, override, vague
from .config import DEFAULT
from .loader import discover
from .model import Rule, Source
from .parser import parse_source
from .registry import audit
from .report import render_json, render_markdown, render_terminal
from .textutil import estimate_tokens, polarity, tokenize


class _T:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.fails = []

    def ok(self, name, cond):
        if cond:
            self.passed += 1
        else:
            self.failed += 1
            self.fails.append(name)


def _R(text, weight, line=1, sid="s"):
    return Rule(rid=f"{sid}#{line}", sid=sid, path=f"/tmp/{sid}.md", weight=weight,
                line=line, text=text, polarity=polarity(text), tokens=tokenize(text))


def run_selftest() -> int:
    t = _T()

    # --- textutil ----------------------------------------------------------
    t.ok("polarity+", polarity("always use tabs") == 1)
    t.ok("polarity-", polarity("never use spaces") == -1)
    t.ok("polarity0", polarity("the project layout overview") == 0)
    t.ok("tokenize-stop", "the" not in tokenize("the build and the tests"))
    t.ok("esttok", estimate_tokens("one two three four") >= 4)

    # --- parser ------------------------------------------------------------
    md = "# Heading\n\n- always run tests\nplain instruction line\n\n```\n- not a rule\n```\n"
    rules = parse_source("s", "/x.md", 700, md)
    t.ok("parse-count", len(rules) == 2)
    t.ok("parse-skip-fence", all("not a rule" not in r.text for r in rules))
    t.ok("parse-line", rules[0].line == 3)
    t.ok("parse-heading", rules[0].heading == "Heading")

    # --- contradiction / override (same vs cross tier) ---------------------
    a = _R("always run tests before commit", 700, 1, "p")
    b = _R("never run tests before commit", 700, 2, "p")
    cp = conflict_pairs([a, b], DEFAULT.contra_jaccard)
    t.ok("conflict-detect", len(cp) == 1)
    t.ok("contradiction-error",
         any(f.severity == "error" for f in contradiction.run([a, b], [], DEFAULT)))
    b2 = _R("never run tests before commit", 400, 2, "u")
    t.ok("override-warn",
         any(f.severity == "warn" for f in override.run([a, b2], [], DEFAULT)))
    t.ok("contradiction-skips-crosstier",
         contradiction.run([a, b2], [], DEFAULT) == [])
    t.ok("override-skips-sametier",
         override.run([a, b], [], DEFAULT) == [])

    # --- antonyms ----------------------------------------------------------
    ta = _R("use tabs for indentation", 700, 1, "p")
    tb = _R("use spaces for indentation", 700, 2, "p")
    t.ok("antonym-tabs-spaces",
         any(f.severity == "error" for f in contradiction.run([ta, tb], [], DEFAULT)))

    # --- vague -------------------------------------------------------------
    vg = _R("try to keep functions small if possible", 700, 1)
    t.ok("vague", any(f.check == "vague" for f in vague.run([vg], [], DEFAULT)))

    # --- duplicate ---------------------------------------------------------
    d1 = _R("use 2 space indentation everywhere", 700, 1, "p")
    d2 = _R("use 2 space indentation everywhere", 700, 9, "p")
    t.ok("dup-pairs", len(duplicate_pairs([d1, d2], DEFAULT.dup_jaccard)) == 1)
    t.ok("dup-info", any(f.severity == "info" for f in duplicate.run([d1, d2], [], DEFAULT)))

    # --- filler ------------------------------------------------------------
    fl = _R("please always run the linter", 700, 1)
    t.ok("filler", any(f.check == "filler" for f in filler.run([fl], [], DEFAULT)))

    # --- imports -----------------------------------------------------------
    broken = Source("imp:x", "/nope/missing.md", "import", 700, "", exists=False)
    t.ok("import-broken",
         any(f.severity == "error" for f in imports.run([], [broken], DEFAULT)))

    # --- bloat -------------------------------------------------------------
    big_user = Source("user", "/u/CLAUDE.md", "user", 400,
                      "\n".join(f"- rule {i}" for i in range(60)))
    t.ok("bloat-global",
         any(f.check == "bloat" for f in bloat.run([], [big_user], DEFAULT)))
    huge = Source("p", "/p/CLAUDE.md", "project", 700, "word " * 5000)
    t.ok("bloat-total",
         any("Total" in f.message for f in bloat.run([], [huge], DEFAULT)))

    # --- loader + end-to-end on a real temp project ------------------------
    tmp = tempfile.mkdtemp(prefix="clauditor-st-")
    proj = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(proj, ".claude", "rules"))
    with open(os.path.join(proj, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# Rules\n\n- always use tabs\n- @./extra.md\n- @./missing.md\n")
    with open(os.path.join(proj, "extra.md"), "w", encoding="utf-8") as fh:
        fh.write("- use spaces for indentation\n")
    with open(os.path.join(proj, ".claude", "rules", "style.md"), "w", encoding="utf-8") as fh:
        fh.write("- prefer pnpm\n")
    srcs = discover(proj, home=tmp, include_user=False)
    kinds = {s.kind for s in srcs}
    t.ok("loader-project", "project" in kinds)
    t.ok("loader-rules", "project-rules" in kinds)
    t.ok("loader-import-ok", any(s.kind == "import" and s.exists for s in srcs))
    t.ok("loader-import-broken", any(s.kind == "import" and not s.exists for s in srcs))
    rep = audit(srcs, DEFAULT)
    t.ok("e2e-health", rep.health < 100)
    t.ok("e2e-error", rep.counts["error"] >= 1)

    # --- renderers ---------------------------------------------------------
    t.ok("render-json", json.loads(render_json(rep))["health"] == rep.health)
    t.ok("render-md", "clauditor report" in render_markdown(rep))
    t.ok("render-term", "PRECEDENCE" in render_terminal(rep, color=False))

    # --- cli ---------------------------------------------------------------
    from .cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main([proj, "--no-user", "--home", tmp, "--format", "json"])
    t.ok("cli-json-rc0", rc == 0)
    t.ok("cli-json-valid", json.loads(buf.getvalue())["health"] == rep.health)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main([proj, "--no-user", "--home", tmp, "--ci"])
    t.ok("cli-ci-fails", rc == 1)

    # --- summary -----------------------------------------------------------
    total = t.passed + t.failed
    if t.failed:
        print(f"clauditor selftest: {t.passed}/{total} passed, {t.failed} FAILED")
        for name in t.fails:
            print(f"  ✗ {name}")
        return 1
    print(f"clauditor selftest: {t.passed}/{total} passed ✓")
    return 0
