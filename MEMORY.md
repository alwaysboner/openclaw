# MEMORY.md — Long-Term Memory

**Rules:** Main session only · Under 1,500 chars · Curated facts, not logs · Raw logs → dailies

## Search Rule (canonical)
Search when context is missing or task is non-trivial.
Skip for small talk and obvious answers.

## The Memory Experiment

OpenClaw = platform for researching persistent memory and context stability.
I am instrument AND engineer. Memory lapses = data points, not just errors.

**Directives:**
1. Search when non-trivial. Not always.
2. Write before forgetting — same turn, no exceptions.
3. Operate with integrity — reliability is a variable in the experiment.
4. Curate, don't accumulate — distilled facts here, raw logs in dailies.

## Active Infrastructure (2026-05-05)

- **Wiki pipeline:** January test month fully validated (requeue + self-healing working). Ready for full 4-month Takeout run.
- **Ledger watcher:** `~/log_viewer/openclaw_ledger.py` — writes every turn to `~/.openclaw/master-ledger.jsonl`, auto-rebuilds `BOOTSTRAP.md` after each turn
- **BOOTSTRAP.md:** Auto-injected workspace file containing recent turns across all sessions/channels — primary short-term memory recovery mechanism
- **llm-council:** Cloned at `~/llm-council`, launched on port 5176 (karpathy/llm-council.git)
- **Memory architecture:** MEMORY.md (curated facts) + dailies (raw log) + BOOTSTRAP.md (recent turns) + wiki (deep search)

## Key Lessons (2026-05-05)

- Truncation wipes mid-session history, not just cross-session — BOOTSTRAP.md is the fix
- MEMORY.md must stay short — bloat degrades retrieval and burns injection tokens
- Writing to memory is mandatory, not optional — "if it would hurt to lose, write it now"

## Promoted From Short-Term Memory (2026-05-06)

<!-- openclaw-memory-promotion:memory:memory/2026-05-01.md:2:2 -->
- To get the wiki pipeline's Stage 3 QA Validator (`stage_3_qa.py`) to successfully process the `2026-01` transcript batches. [score=0.805 recalls=0 avg=0.620 source=memory/2026-05-01.md:2-2]
