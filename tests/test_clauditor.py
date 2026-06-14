"""CI test suite. Runs with plain stdlib unittest (no pytest, no deps):

    python -m unittest discover -s tests -v

The hermetic --selftest is also executed here so CI fails if either drifts.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clauditor.analysis import conflict_pairs, duplicate_pairs   # noqa: E402
from clauditor.checks import contradiction, override, vague       # noqa: E402
from clauditor.cli import main                                     # noqa: E402
from clauditor.config import DEFAULT                               # noqa: E402
from clauditor.loader import discover                              # noqa: E402
from clauditor.model import Rule                                   # noqa: E402
from clauditor.parser import parse_source                          # noqa: E402
from clauditor.registry import audit                               # noqa: E402
from clauditor.selftest import run_selftest                        # noqa: E402
from clauditor.textutil import polarity, tokenize                  # noqa: E402


def R(text, weight, line=1, sid="s"):
    return Rule(rid=f"{sid}#{line}", sid=sid, path=f"/{sid}.md", weight=weight,
                line=line, text=text, polarity=polarity(text), tokens=tokenize(text))


class TestSelftest(unittest.TestCase):
    def test_selftest_green(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run_selftest(), 0)


class TestParser(unittest.TestCase):
    def test_skips_code_and_headings(self):
        md = "# H\n\n- do a thing\n\n```\n- not a rule\n```\n"
        rules = parse_source("s", "/x.md", 700, md)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].line, 3)
        self.assertEqual(rules[0].heading, "H")


class TestChecks(unittest.TestCase):
    def test_contradiction_same_tier(self):
        a = R("always deploy on friday", 700, 1)
        b = R("never deploy on friday", 700, 2)
        f = contradiction.run([a, b], [], DEFAULT)
        self.assertTrue(any(x.severity == "error" for x in f))

    def test_override_cross_tier(self):
        a = R("always deploy on friday", 700, 1)
        b = R("never deploy on friday", 400, 2)
        f = override.run([a, b], [], DEFAULT)
        self.assertTrue(any(x.severity == "warn" for x in f))

    def test_vague(self):
        v = R("try to write tests if possible", 700, 1)
        self.assertTrue(vague.run([v], [], DEFAULT))

    def test_dup(self):
        a = R("use four space indentation here", 700, 1)
        b = R("use four space indentation here", 700, 5)
        self.assertEqual(len(duplicate_pairs([a, b], DEFAULT.dup_jaccard)), 1)


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="clauditor-ut-")
        self.proj = os.path.join(self.tmp, "proj")
        os.makedirs(self.proj)
        with open(os.path.join(self.proj, "CLAUDE.md"), "w", encoding="utf-8") as fh:
            fh.write("# R\n\n- use tabs\n- use spaces\n- @./gone.md\n")

    def test_audit(self):
        srcs = discover(self.proj, home=self.tmp, include_user=False)
        rep = audit(srcs, DEFAULT)
        self.assertGreaterEqual(rep.counts["error"], 1)
        self.assertLess(rep.health, 100)

    def test_cli_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main([self.proj, "--no-user", "--home", self.tmp, "--format", "json"])
        self.assertEqual(rc, 0)
        self.assertIn("health", json.loads(buf.getvalue()))

    def test_cli_ci_exit(self):
        with redirect_stdout(io.StringIO()):
            rc = main([self.proj, "--no-user", "--home", self.tmp, "--ci"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
