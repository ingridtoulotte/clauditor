# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [0.2.0] - 2026-06-14

### Added
- **SARIF 2.1.0 output** (`--format sarif` / `--sarif`). Upload with
  `github/codeql-action/upload-sarif` to get every finding as an inline
  annotation on the exact line in a PR's *Files changed* tab.
- **Config-health badge** (`--format badge`). Emits a shields.io endpoint JSON
  so you can show a live `claude config 72/100` badge in any README.
- Hero terminal screenshot (`assets/clauditor-demo.svg`), a self-contained SVG.
- Selftest grew to 42 assertions; new unit tests for the SARIF and badge
  reporters.

### Notes
- No breaking changes. Existing `term` / `json` / `md` output is unchanged.

## [0.1.0] - 2026-06-14

First public release.

### Added
- Loader that discovers the full Claude Code instruction stack in precedence
  order: enterprise policy → `CLAUDE.local.md` → project `CLAUDE.md` chain →
  `.claude/rules/*.md` → user `~/.claude` → `@`-imports.
- Seven checks: `contradiction`, `override`, `vague`, `duplicate`, `imports`,
  `bloat`, `filler`.
- Terminal, JSON, and Markdown reporters with a 0–100 health score and a
  precedence map.
- `--ci` / `--strict` exit codes and a reusable GitHub Action.
- Hermetic `--selftest` (34 assertions) and a stdlib `unittest` suite.
- Zero runtime dependencies; pure Python standard library; fully local.
