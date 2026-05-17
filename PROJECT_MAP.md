# PROJECT_MAP.md
> Stable navigation. Volatile state → RUNTIME_STATUS.md. Credentials → SENSITIVE_PATHS.md.
> Read-only during queries. Writes go through Pipeline only.
> Not auto-injected — agent reads this on demand before non-trivial file operations.

## Platform
Ubuntu 24.04 LTS · Linux 6.17.0-1013-aws · `openclaw-env` · Home: `/home/ubuntu`

---

## 1. Pipeline
| Item | Value |
|------|-------|
| Path | `~/wiki-pipeline` |
| Stages | `stage_1_chunker.py` · `stage_2_writer.py` · `stage_3_qa.py` · 4 · 5 |
| Deliberation | `~/llm-council-vertex/backend/council.py` |
| Access | RW · Manual or automated trigger |

## 2. Wiki
| Item | Value |
|------|-------|
| Path | `~/.openclaw/wiki/main` |
| Subdirs | `concepts/` · `entities/` · `transcripts/` · `sources/` |
| Access | **RO** — updated by Pipeline only · tools: `wiki_search` / `wiki_get` |

## 3. Memory & Ledger
| Store | Path |
|-------|------|
| Long-term | `~/.openclaw/workspace/MEMORY.md` |
| Daily log | `~/.openclaw/workspace/memory/YYYY-MM-DD.md` |
| Heartbeat state | `~/.openclaw/workspace/memory/heartbeat-state.json` |
| Master ledger | `~/.openclaw/master-ledger.jsonl` — append-only |
| Bootstrap | `~/.openclaw/workspace/BOOTSTRAP.md` — auto-written, do not edit |
| LCM DB | `~/.openclaw/lcm.db` — see LCM.md |
| Memory SQLite | `~/.openclaw/memory/main.sqlite` |
| Flows registry | `~/.openclaw/flows/registry.sqlite` |
| Task runs | `~/.openclaw/tasks/runs.sqlite` |
| Sessions | `~/.openclaw/agents/main/sessions` |

## 4. Active Services
| Service | Path | Port | Notes |
|---------|------|------|-------|
| LLM Council | `~/llm-council-vertex` | 5176 | run `start.sh` |
| Ledger watcher | `~/log_viewer/openclaw_ledger.py` | — | writes ledger + rebuilds BOOTSTRAP.md |
| Observer server | `~/log_viewer/unified_observer.py` | 7842 | uvicorn/FastAPI |
| WhatsApp Gateway | +17143346355 | — | connected |

## 5. Auxiliary
| Tool | Path |
|------|------|
| Benchmarks | `~/benchmarks` |
| Diagnostics | `~/diagnostics` |
| Log Viewer | `~/log_viewer` |
| Loki Dash | `~/loki-dash` |
| Gateway logs | `~/logs/gateway` |
| Results | `~/results` |

## 6. Workspace Docs
Base: `~/.openclaw/workspace/`

| File | Injected | Purpose |
|------|:--------:|---------|
| AGENTS.md | ✅ | Primer, memory stack, write rules, formatting, red lines |
| BOOTSTRAP.md | ✅ | Recent turns — auto-written |
| IDENTITY.md | ✅ | Agent identity |
| MEMORY.md | ✅ | Curated long-term facts |
| SOUL.md | ✅ | Core behavioral directives |
| TOOLS.md | ✅ | Active services, LCM ref, on-demand file index |
| USER.md | ✅ | Jason's profile and active projects |
| HEARTBEAT.md | — | Health check state |
| LCM.md | — | Full lossless-claw reference |
| PROJECT_MAP.md | — | This file |
| RUNTIME_STATUS.md | — | Volatile machine snapshot |
| SENSITIVE_PATHS.md | — | Credential paths — strict handling |

## 7. Plugin Skills
| Skill | Source | Notes |
|-------|--------|-------|
| `browser-automation` | openclaw built-in | |
| `lossless-claw` | `@martian-engineering/lossless-claw` | slot: `contextEngine` |
| `obsidian-vault-maintainer` | openclaw built-in | |
| `wiki-maintainer` | openclaw built-in | |
