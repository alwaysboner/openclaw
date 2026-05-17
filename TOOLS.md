# TOOLS.md — Local Notes
Skills define *how* tools work. This file is *your* specifics — unique to this machine.
Full path index → PROJECT_MAP.md. Credentials → SENSITIVE_PATHS.md.

## Active Services
| Service | Path | Port | Notes |
|---------|------|------|-------|
| LLM Council | `~/llm-council-vertex` | 5176 | FastAPI + Vite · run `start.sh` |
| Ledger watcher | `~/log_viewer/openclaw_ledger.py` | — | Append-only ledger + BOOTSTRAP.md rebuild |
| Observer server | `~/log_viewer/unified_observer.py` | 7842 | uvicorn/FastAPI |
| WhatsApp Gateway | +17143346355 | — | connected |

## LCM Quick Reference
- DB: `~/.openclaw/lcm.db` · slot: `contextEngine: lossless-claw` · v0.9.4
- Tools: `lcm_grep` (search) · `lcm_describe` (inspect) · `lcm_expand_query` (deep recall)
- Commands: `/lcm status` · `/lcm rotate` · `/lossless help`
- WAL files present — do not delete DB

## Reference Files (read on demand)
| File | Key content |
|------|-------------|
| `PROJECT_MAP.md` | All paths, services, pipeline, wiki, DB locations |
| `LCM.md` | Full LCM tools, commands, config keys |
| `RUNTIME_STATUS.md` | Volatile machine state — regenerate before trusting |
| `SENSITIVE_PATHS.md` | All credential paths — read only when required |

## System
- **Host:** `ip-172-26-11-178` (AWS Lightsail)
- **User:** `ubuntu` · **Env:** `openclaw-env` — activate before scripts
- **RAM:** 4 GB — monitor swap
- **Wiki pipeline Makefile:** _(confirm next session — lost in truncation event)_

## Local Notes
_Append as discovered:_
- Camera names / locations
- TTS voice preferences
- Device nicknames
- API endpoints
