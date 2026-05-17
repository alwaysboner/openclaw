#!/usr/bin/env python3
"""
stage_1_chunker.py — OpenClaw Wiki Pipeline v6.0 Stage 1
Pure Python. No LLM. Segments raw JSONL into trace batches by idle gap.

Config:
  MAX_INTERACTIONS      = 150   (raised from 100 — prevents mid-session splits)
  MIN_INTERACTIONS      = 8     (carry forward stubs smaller than this)
  IDLE_THRESHOLD_SECONDS = 7200 (2h — validated against Feb+Mar 2026 data)
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pipeline_utils import log_event

MAX_INTERACTIONS       = 150
MIN_INTERACTIONS       = 8
IDLE_THRESHOLD_SECONDS = 7200

WIKI_ROOT  = Path.home() / ".openclaw/wiki/main"
TRACES_DIR = WIKI_ROOT / "transcripts/processed/traces"


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def should_break(current: Dict, last: Dict, count: int) -> Tuple[bool, str]:
    if count >= MAX_INTERACTIONS:
        return True, "max_interactions"
    delta = (parse_ts(current["timestamp"]) - parse_ts(last["timestamp"])).total_seconds()
    if delta > IDLE_THRESHOLD_SECONDS:
        return True, f"idle_{int(delta/3600)}h"
    return False, ""


def save_batch(messages: List[Dict], month: str, idx: int, traces_dir: Path) -> str:
    batch_id  = f"{month.replace('-','_')}_batch_{idx:03d}"
    start_ts  = messages[0]["timestamp"]
    end_ts    = messages[-1]["timestamp"]
    models    = list({m.get("model") for m in messages if m.get("model")})
    canary_lo = idx * 1000
    canary_hi = canary_lo + len(messages)

    batch = {
        "batch_id":     batch_id,
        "start_ts":     start_ts,
        "end_ts":       end_ts,
        "turn_count":   len(messages),
        "models":       models,
        "canary_range": f"CANARY-{canary_lo:04d}\u2013CANARY-{canary_hi:04d}",
        "messages":     messages,
    }

    out = traces_dir / f"trace_{batch_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2, ensure_ascii=False)
    log_event(batch_id, "chunk", "INIT", {"trace_file_path": str(out)})
    return batch_id


def run_chunker(input_path: Path, month: str, traces_dir: Path) -> None:
    print(f"📥 Stage 1 Chunker v6.0 — {month}")

    messages = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                messages.append(json.loads(line))

    if not messages:
        print("❌ No messages found.")
        return

    batches     = []
    current     = [messages[0]]
    batch_idx   = 0

    for msg in messages[1:]:
        do_break, reason = should_break(msg, current[-1], len(current))

        if do_break:
            if len(current) < MIN_INTERACTIONS:
                # Carry forward — batch too small, merge into next
                current.append(msg)
            else:
                bid = save_batch(current, month, batch_idx, traces_dir)
                print(f"  ✅ {bid} ({len(current)} turns, {reason})")
                batches.append(bid)
                current   = [msg]
                batch_idx += 1
        else:
            current.append(msg)

    # Final batch — save regardless of min (don't drop end-of-month data)
    if current:
        bid = save_batch(current, month, batch_idx, traces_dir)
        print(f"  ✅ {bid} ({len(current)} turns, final)")
        batches.append(bid)

    print(f"\n✨ Stage 1 complete: {len(batches)} batches → {traces_dir}")


def main():
    parser = argparse.ArgumentParser(description="Stage 1 Chunker v6.0")
    parser.add_argument("--month",      required=True,             help="YYYY-MM")
    parser.add_argument("--chunks-dir", default=str(Path.home() / "output/chunks"))
    parser.add_argument("--traces-dir", default=str(TRACES_DIR))
    args = parser.parse_args()

    input_path = Path(args.chunks_dir) / f"{args.month}.txt"
    if not input_path.exists():
        input_path = Path(args.chunks_dir) / f"{args.month}.jsonl"
    if not input_path.exists():
        print(f"❌ Input not found: {input_path}")
        raise SystemExit(1)

    run_chunker(input_path, args.month, Path(args.traces_dir))


if __name__ == "__main__":
    main()
