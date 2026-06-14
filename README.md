<div align="center">

# clauditor

### Find the rules Claude silently ignores in your `CLAUDE.md`.

**clauditor audits your whole Claude Code instruction stack and shows you which rules are dead, contradictory, vague, duplicated, or just burning tokens — in one command, fully local.**

[![CI](https://github.com/ingridtoulotte/clauditor/actions/workflows/ci.yml/badge.svg)](https://github.com/ingridtoulotte/clauditor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-0-success)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/ingridtoulotte/clauditor?style=social)](https://github.com/ingridtoulotte/clauditor/stargazers)

</div>

---

```
  clauditor  ·  Claude config audit

  PRECEDENCE  (top = wins conflicts)
    project-local  examples/messy/CLAUDE.local.md  ~35t
    project        examples/messy/CLAUDE.md  ~136t
    import         examples/messy/extra-rules.md  ~15t
    import(broken) examples/messy/missing-standards.md  MISSING

  FINDINGS  9 total

  🔴 ERROR contradiction  examples/messy/CLAUDE.md:5
      Contradiction (conflicting choice: tabs vs spaces) at equal precedence — Claude picks one arbitrarily.
      A: Use tabs for indentation.
      B: Use spaces for indentation.
      → Delete or reconcile one of the two rules so only one survives.

  🟡 WARN override  examples/messy/CLAUDE.md:7
      Dead rule: 'Always run tests before committing.' is silently overridden by a higher-precedence rule.
      winner: Never run tests before committing; they are too slow. [examples/messy/CLAUDE.local.md:3]
      → Remove the dead rule, or move it to the higher-precedence layer if you actually want it to win.

  🔴 ERROR imports  examples/messy/missing-standards.md:0
      Broken @import: '…/missing-standards.md' does not exist — its rules never load.

  HEALTH  [█████████████████░░░░░░░] 72/100
    3 error 4 warn 3 info · 16 rules · 3 files
```

*(real output of `clauditor examples/messy` — trimmed)*

---

## Try it in 30 seconds

```bash
pipx install git+https://github.com/ingridtoulotte/clauditor
clauditor                 # audits the current project + your ~/.claude
```

No pipx? Either of these works just as well:

```bash
pip install git+https://github.com/ingridtoulotte/clauditor && clauditor
# or, zero-install:
git clone https://github.com/ingridtoulotte/clauditor && cd clauditor && python -m clauditor examples/messy
```

Pure Python standard library. **Zero dependencies. Zero network calls. Your config never leaves your machine.**

---

## Why this exists

You write rules in `CLAUDE.md`. Claude reads them. And then it… does its own thing anyway.

You're not imagining it. It's one of the most-reported pain points in Claude Code
([#27032](https://github.com/anthropics/claude-code/issues/27032),
[#15443](https://github.com/anthropics/claude-code/issues/15443),
[#7777](https://github.com/anthropics/claude-code/issues/7777)),
and Anthropic's own docs admit that **when two rules conflict, Claude may pick one arbitrarily** — there's no guarantee which one wins.

The catch: your rules don't live in one file. They're scattered across a *stack* —
enterprise policy, `CLAUDE.local.md`, every `CLAUDE.md` from your cwd up to the repo
root, `.claude/rules/*.md`, your global `~/.claude/CLAUDE.md`, and any `@`-imports.
They get **merged**, not cleanly overridden. So you end up with rules that contradict
each other, rules that a higher layer silently kills, vague rules Claude can't act on,
and copies of the same rule three times — all loaded into context on *every single turn*.

`/memory` and `/doctor` tell you what *loaded*. **clauditor tells you what's actually broken.**

> One developer [audited every rule in their `CLAUDE.md`](https://sabahudinmurtic.substack.com/p/i-audited-every-rule-in-my-claudemd) by hand — and found **half of them failed**. clauditor does that audit in a second, across the whole stack.

---

## What it checks

| Check | | Catches |
|---|---|---|
| **contradiction** | 🔴 | Two rules clash at the **same** precedence — Claude resolves them by coin-flip |
| **override** | 🟡 | A rule is **silently overridden** by a higher layer → it's *dead*, but still costs tokens (the real "Claude ignores my CLAUDE.md") |
| **vague** | 🟡 | Weasel phrasing (`try to`, `if possible`, `generally`) Claude can't verify it followed |
| **duplicate** | 🔵 | The same rule, twice — wasted budget, future drift |
| **imports** | 🔴 | Broken or cyclic `@import` — a whole block of rules that never loads |
| **bloat** | 🟡 | Oversized global file / file / total budget, loaded every turn |
| **filler** | 🔵 | Politeness and meta-narration ("please", "this file describes…") |

Each finding comes with the exact `path:line` and a concrete fix. Full details and how
the precedence weights are computed: **[docs/checks.md](docs/checks.md)**.

---

## Use it in CI

Stop a bad rule from ever reaching `main`. The reusable Action installs and runs clauditor for you:

```yaml
# .github/workflows/clauditor.yml
name: clauditor
on: [pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ingridtoulotte/clauditor@v0.1.0
        with:
          args: --ci --strict   # fail on contradictions (and warnings, with --strict)
```

Or call the CLI directly anywhere:

```bash
clauditor --ci            # exit 1 if any 🔴 error exists
clauditor --ci --strict   # exit 1 on 🟡 warnings too
```

## Output formats

```bash
clauditor                 # colored terminal report (default)
clauditor --format json   # machine-readable, for scripts and dashboards
clauditor --format md -o report.md   # drop a Markdown report into a PR
clauditor --min-severity warn        # hide the 🔵 info noise
clauditor --no-user                  # audit only the project, skip ~/.claude
clauditor --list-checks              # see every check
```

---

## How it compares

| | what loaded | conflicts | dead/overridden rules | vague rules | whole stack | local-only | CI gate |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `/memory`, `/doctor` (built-in) | ✅ | ❌ | ❌ | ❌ | ⚠️ order only | ✅ | ❌ |
| `claude-md-improver` (skill) | — | ⚠️ | ❌ | ✅ | ❌ misses `.claude/rules` | ✅ | ❌ |
| token / context optimizers | — | ❌ | ❌ | ❌ | ⚠️ tokens only | ✅ | ❌ |
| **clauditor** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

clauditor isn't a token counter and it isn't a memory tool — it's the **linter** for the
instructions you've already written. It pairs well with everything above.

---

## Roadmap

- [ ] `--fix` mode that proposes concrete edits (remove dead rules, merge dupes)
- [ ] SARIF output for GitHub code-scanning annotations
- [ ] `--watch` mode that re-audits on save
- [ ] Cross-tool support: `AGENTS.md`, Cursor `.mdc`, Copilot instructions
- [ ] A `pre-commit` hook
- [ ] Community pack of high-precision antonym/weasel rules

Ideas and PRs very welcome — see below.

## Contributing

A new check is **one file**. The whole contract is in
[CONTRIBUTING.md](CONTRIBUTING.md), and [`good first issue`](https://github.com/ingridtoulotte/clauditor/labels/good%20first%20issue)
issues are a great place to start (more antonym pairs, more weasel phrases, a SARIF reporter…).

```bash
git clone https://github.com/ingridtoulotte/clauditor && cd clauditor
pip install -e .
clauditor --selftest      # 34 assertions
python -m unittest discover -s tests -v
```

## FAQ

**Does it send my config anywhere?** No. clauditor is pure stdlib and makes zero network
calls. It only reads files you point it at.

**Are the token counts exact?** They're a stable proxy (~4 chars/token), good for comparing
files and watching a budget — not for billing.

**Will it edit my files?** Not in v1. It only reports. (`--fix` is on the roadmap and will
be opt-in.)

---

<div align="center">

If clauditor found a dead rule in your config, **drop a ⭐** — it helps other people find it.

MIT © [Ingrid Toulotte](https://github.com/ingridtoulotte) · [Changelog](CHANGELOG.md) · [Checks reference](docs/checks.md)

</div>
