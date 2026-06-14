# Contributing to clauditor

Thanks for helping make Claude config saner for everyone. clauditor is small,
dependency-free, and easy to hack on — most contributions are a single file.

## Quick start

```bash
git clone https://github.com/ingridtoulotte/clauditor
cd clauditor
pip install -e .
clauditor --selftest          # 34 assertions, must be green
python -m unittest discover -s tests -v
```

No third-party dependencies. If your change adds one, it probably belongs in a
plugin/fork instead — keeping the core stdlib-only is a hard design goal.

## Adding a new check (the most useful contribution)

A check is one file. The whole contract:

```python
# src/clauditor/checks/my_check.py
from ..model import Finding
NAME = "my_check"

def run(rules, sources, ctx):
    findings = []
    for r in rules:
        if "...":
            findings.append(Finding(
                check=NAME, severity="warn",
                message="what's wrong",
                fix="how to fix it",
                rule_ids=[r.rid], locations=[r.location],
            ))
    return findings
```

Then add `"my_check"` to `CHECK_MODULES` in `src/clauditor/registry.py` and a
test in `tests/`. That's it.

**Good first issues** are labeled [`good first issue`](https://github.com/ingridtoulotte/clauditor/labels/good%20first%20issue).
Great starter ideas: more antonym pairs, more weasel phrases, a SARIF reporter,
or a `--fix` mode that proposes edits.

## Guidelines

- Keep checks **high-precision**. A false positive erodes trust faster than a
  missed finding earns it. When in doubt, lower the severity, not the threshold.
- Every behavior change needs a test and a green `--selftest`.
- Match the surrounding style: clear names, short functions, a module docstring
  explaining *why* the check matters.
- One logical change per PR.

## Reporting bugs

Open an issue with the smallest CLAUDE.md snippet that reproduces it and the
output you got vs. what you expected. `clauditor --format json` output helps.
