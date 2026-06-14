# Checks

clauditor runs seven checks over the parsed rule set. Each is one module under
`src/clauditor/checks/`. Severity drives the health score
(🔴 error −6, 🟡 warn −2, 🔵 info −0.5 from a base of 100).

| Check | Severity | What it catches | Why it matters |
|---|---|---|---|
| `contradiction` | 🔴 error | Two rules clash at **equal** precedence | Claude has no deterministic way to resolve them, so behavior changes run-to-run |
| `override` | 🟡 warn | A rule is silently killed by a **higher**-precedence rule | The losing rule is *dead* — present, costing tokens, never followed. This is the classic "Claude ignores my CLAUDE.md" |
| `vague` | 🟡 warn | Weasel phrasing (`try to`, `if possible`, `generally`…) | Unverifiable rules get low adherence under pressure |
| `duplicate` | 🔵 info | Identical / near-identical rules | Spends context budget twice; drifts over time |
| `imports` | 🔴 error / 🔵 info | Broken or repeated `@import` paths | A broken import means a whole block of rules never loads |
| `bloat` | 🟡 warn / 🔵 info | Oversized global file / large file / total budget | Every token loads on **every** turn and dilutes attention |
| `filler` | 🔵 info | Politeness & meta-narration | Pure token cost, zero instruction |

## How precedence is determined

Higher weight wins a conflict. Weights mirror Claude Code's documented hierarchy:

| Layer | Weight |
|---|---:|
| Enterprise managed policy (`--enterprise`) | 1000 |
| Project `CLAUDE.local.md` | 800 |
| Project `CLAUDE.md` (nearest dir; parents step down by 10) | 700 |
| Project `.claude/rules/*.md` | 650 |
| User `~/.claude/CLAUDE.md` | 400 |
| User `~/.claude/rules/*.md` | 350 |
| `@`-import | inherits the importing file's weight |

> clauditor's token counts are a stable proxy (~4 chars/token), not Anthropic's
> exact tokenizer. Use them to compare files and watch a budget, not for billing.

## Tuning

Drop a `.clauditor.toml` at the project root:

```toml
[clauditor]
global_max_lines = 35
file_max_tokens = 1500
total_budget_tokens = 4000
contra_jaccard = 0.45   # topic-overlap needed to call two rules "the same topic"
dup_jaccard = 0.85      # similarity needed to call two rules duplicates
```
