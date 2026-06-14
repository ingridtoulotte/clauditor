# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

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
