**Status:** Production | **Updated:** 2026-04-30 | **Supersedes:** v5.0 (2026-04-26)

> Orchestrator control surface. No subagent prompts here.
> Load only the prompt card for the stage you are executing.

***

## ⚠️ CRITICAL RULES (NON-NEGOTIABLE)

1. **MAX RETRIES: 3 per batch per stage. HARDCODED. NO EXCEPTIONS.**
2. **Stage 2 output is always DRAFT until Stage 3 QA clears it.**
3. **Stage 5 user approval is mandatory before wiki commit.**
4. **Zero-trust dating: Filename date > Earliest message timestamp > FAIL.**
5. **Never bypass native OpenClaw calls with raw boto3** — loses cost tracking.
6. **No force-promote of DLQ batches.** Review QA issues first.
7. **Obsidian `<!-- human -->` blocks are immutable** — never overwrite.

***

## 1. CONFIG

```yaml
global_settings:
  max_concurrent: 2
  max_rounds: 15
  read_timeout: 300
  lazy_protocol: true
  session_isolation: true
  log_output: "pipeline_report_{YYYY_MM}.md"
  dead_letter_queue: "failed_batches_dlq.jsonl"

chunker_settings:
  max_interactions:       150   # raised from 100
  min_interactions:       8     # carry forward below this
  idle_threshold_seconds: 7200  # 2h — validated Feb+Mar 2026

model_roster:
  stage_2_primary:   "google/gemini-2.5-flash"
  stage_2_quality:   "google/gemini-2.5-pro"
  stage_3_qa:        "google/gemini-2.5-flash"
  stage_3_fallback:  "google/gemini-2.5-flash-lite"
  stage_6_indexer:   "pure Python (no LLM)"

retry_policy:
  max_retries_per_batch: 3
  max_stage2_rewrites:   3
  retry_delay_seconds:   2
  on_exceed:             dead_letter

fallback_policy:
  rate_limit_429: "backoff_requeue"
  session_lock:   "isolate_retry"
  qa_fail:        "stage2_reroute_with_cap"
  timeout:        "extend_retry"
```

***

## 2. PIPELINE STATE MACHINE

| Stage | Script | Model | Input | Output | Pass Condition | On Fail |
|-------|--------|-------|-------|--------|----------------|---------|
| **0** | manual | — | raw export | enriched JSONL | `_cite` + `_canary` on all turns | block |
| **1** | `stage_1_chunker.py` | Python | `YYYY-MM.txt` | `trace_*_batch_*.json` | ≥8 turns, no mid-session splits | log + skip |
| **2** | `stage_2_writer.py` | flash→pro | batch JSON + manifest | `promoted-pending/*.md` DRAFT | schema valid, no DON'Ts | DLQ after 3 |
| **3** | `stage_3_qa.py` | gemini-2.5-flash | draft + source batch | QA JSON in trace | `pass:true, issue_count:0` | reroute→S2 max 3 |
| **3.5** | `stage_3_retry_enforcer.py` | Python | all trace files | approved / requeue / DLQ | all resolved | halt |
| **4** | `promote_wiki_pages.py` | Python | approved drafts | typed wiki dirs | G1–G7 pass | archive |
| **5** | manual (Obsidian) | — | typed wiki dirs | committed pages | human sign-off | rework |
| **6** | `stage_5_index_builder.py` | Python | wiki root | indexes + tag_map | indexes written, git committed | retry |

### Lazy Protocol

```
On FAILURE:
  1. LOG   → pipeline_report_{YYYY_MM}.md
  2. DLQ   → failed_batches_dlq.jsonl
  3. CONTINUE next batch immediately
  4. NEVER interrupt primary session

On QA FAIL (issue_count > 0):
  retry_count < 3  → REQUEUE (Stage 2 with QA feedback injected)
  retry_count >= 3 → DEAD_LETTER (no further processing)
```

### Promotion Gates (G1–G7)

| Gate | Rule | Threshold |
|------|------|-----------|
| G1:SIZE | Min file size | entity/concept: 1500 chars; synthesis: 2000 |
| G2:QA_PASS | `pass: true` in trace | required |
| G3:QA_ISSUES | `issue_count: 0` | required |
| G4:SECTIONS | `##` headers | ≥ 3 |
| G5:LINKS | `[[Internal Links]]` | ≥ 2 or `<!-- TODO: links -->` fallback |
| G6:CALLOUT | `[!info/success/abstract]` | required |
| G7:SCAFFOLD | No pipeline headers in body | must be clean |

***

## 3. PAGE TYPE & DIRECTORY MAP

| pageType | Directory | Sub-types housed here |
|----------|-----------|-----------------------|
| `entity` | `entities/` | Technical, config, hardware, protocol pages |
| `concept` | `concepts/` | Philosophy, lore, field-notes, exploration |
| `synthesis` | `syntheses/` | ADRs, architectural decisions, policy choices |
| `concept` + `[disambiguation]` tag | **vault root** | Navigational disambiguation pages |

**Lore** is `pageType: concept` with `#lore` status tag → lives in `concepts/`.
**Disambiguation** is `pageType: concept` with `tags: [disambiguation]` → lives at vault root (navigational).

***

## 4. VAULT SHAPE

```
~/.openclaw/wiki/main/
  WIKI.md
  index.md                    ← root index (all pages, grouped by tag)
  inbox.md
  disambig-*.md               ← disambiguation pages (navigational, at root)
  concepts/
    index.md
    concept.*.md              ← includes lore + field-note pages
  entities/
    index.md
    entity.*.md
  syntheses/
    index.md
    synthesis.*.md
  sources/
    index.md
  reports/
    index.md
    claim-health.md           ← openclaw wiki lint output
    contradictions.md
    low-confidence.md
    open-questions.md
  promoted-pending/           ← pipeline staging area
  failed_batches_dlq.jsonl
  pipeline_report_YYYY_MM.md
  tag_map.json
  transcripts/processed/traces/
  .openclaw-wiki/cache/
```

**Index hierarchy:**
- `index.md` (root) — all pages across types, grouped by primary tag
- `{type}/index.md` — that type only, sorted by sourcePeriod desc
- `reports/` — managed by `openclaw wiki lint`, do not overwrite manually

***

## 5. STAGE CARDS

### Stage 0 — Pre-Ingest (manual)
Enrich raw export: add `_cite` (YYYY-MM-DD) and `_canary` (CANARY-XXXX). Run monthly splitter.
`openclaw wiki status && openclaw wiki doctor`

### Stage 1 — Chunker
`make chunk MONTH=2026-03`
Pure Python. Config: MAX=150 / MIN=8 / IDLE=7200s. Carry-forward on stubs < MIN.
**Prompt card:** none.

### Stage 2 — Wiki Writer
`make write MONTH=2026-03 OPERATOR=yourhandle`
Guide-based. No fixed templates. Content drives section selection.
**Prompt card:** `prompt_s2_writer.md` — load this file only.
Model cascade: gemini-2.5-flash → gemini-2.5-pro → deepseek.v3.2 → mistral-large-3

### Stage 3 — QA Validator
`make qa MONTH=2026-03`
JSON output only. Writes result into trace file.
**Prompt card:** `prompt_s3_qa.md` — load this file only.

### Stage 3.5 — Retry Enforcer
`make enforce MONTH=2026-03`
Pure Python. Routes to approved / requeue / DLQ. Hard cap: 3 retries.

### Stage 4 — Promote
`make promote MONTH=2026-03`
Repairs frontmatter, strips scaffolding, runs G1–G7, moves to typed dirs.
Disambiguation (tag: `disambiguation`) → vault root. Everything else → typed subdir.

### Stage 5 — User Approval (manual)
Review in Obsidian. Spot-check 3–5 pages (see `reference_ops.md`).
Approve → stay in place + git commit. Reject → move to `promoted-pending/` rework queue.

### Stage 6 — Index + Sync
`make index MONTH=2026-03`
Pure Python. Rebuilds root + per-type indexes + tag_map.json. Then: `openclaw wiki lint` + git commit.
**Prompt card:** `prompt_s6_indexer.md` — load only if LLM is used for index generation.

***

## 6. QUICK EXECUTION

```bash
# Full pipeline
make pipeline MONTH=2026-03 OPERATOR=yourhandle

# Step-by-step
make preflight
make chunk    MONTH=2026-03
make write    MONTH=2026-03 OPERATOR=yourhandle
make qa       MONTH=2026-03
make enforce  MONTH=2026-03
make promote  MONTH=2026-03
# ← manual Obsidian review here
make index    MONTH=2026-03

# Operations
make dlq                              # check dead letter queue
make requeue BATCH=2026_03_batch_005  # retry a specific batch
make dry-write   MONTH=2026-03        # Stage 2 without LLM calls
make dry-promote MONTH=2026-03        # Stage 4 without file moves
make lint                             # openclaw wiki lint
make status                           # vault status
```

***

## 7. SCRIPTS REFERENCE

| Script | Stage | Description |
|--------|-------|-------------|
| `stage_1_chunker.py` | 1 | Session segmentation (pure Python) |
| `stage_2_writer.py` | 2 | Guide-based wiki writer (Vertex + Bedrock) |
| `stage_3_qa.py` | 3 | QA validator (JSON output) |
| `stage_3_retry_enforcer.py` | 3.5 | Retry cap + DLQ router |
| `promote_wiki_pages.py` | 4 | Repair + gate check + typed dir promotion |
| `stage_5_index_builder.py` | 6 | Multi-index builder (pure Python) |
| `Makefile` | all | Pipeline orchestrator entry point |

**Prompt cards (loaded by subagents only):**

| Card | Stage | Loads for |
|------|-------|-----------|
| `prompt_s2_writer.md` | 2 | Wiki writer model |
| `prompt_s3_qa.md` | 3 | QA validator model |
| `prompt_s6_indexer.md` | 6 | Index builder model (optional) |
| `reference_ops.md` | — | Human operators only |

***

*v6.0 — 2026-04-30. Guide-based writer. Lore → concepts/. Disambig → root. `authoredBy` field. Chunker: MAX=150/MIN=8/IDLE=7200. Vertex + Bedrock model roster. Makefile orchestration.*

Sources
