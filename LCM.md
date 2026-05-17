# LCM.md — Lossless-Claw Context Engine
Plugin slot: `contextEngine: lossless-claw` · Package: `@martian-engineering/lossless-claw` · v0.9.4
DB: `~/.openclaw/lcm.db` · WAL files present — do not delete

## What it does
Replaces sliding-window truncation with a SQLite DAG of layered summaries.
Agent sees recent raw turns + compressed summaries of older context.
Any node expands back to source on demand — nothing is ever deleted.
LCM lapses are data points, not just errors.

## Tools
| Tool | Purpose |
|------|---------|
| `lcm_grep` | Search compacted history by keyword |
| `lcm_describe` | Inspect summary nodes and stored files |
| `lcm_expand_query` | Deep recall: expand compressed summary to source |

## Commands
| Command | Effect |
|---------|--------|
| `/lcm status` | Health, db path/size, conversation + summary count |
| `/lcm rotate` | Compact transcript + refresh bootstrap, no new conversation |
| `/lossless help` | Full reference |

## Key Config (openclaw.json)
`freshTailCount` · `contextThreshold` · `expansionModel` · `maxExpandTokens`

## State (2026-05-10)
Fresh install · 1 conversation · 0 summaries · `lcm.db.rotate-latest.bak` exists — keep
