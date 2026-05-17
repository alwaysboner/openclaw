#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
from pipeline_utils import log_event

WIKI_ROOT = Path.home() / ".openclaw/wiki/main"
TRACES_DIR = WIKI_ROOT / "transcripts/processed/traces"
PENDING_DIR = WIKI_ROOT / "promoted-pending"

def extract_frontmatter_field(content: str, field: str) -> str | None:
    m = re.search(rf"^{field}:\s*(.*?)(?:\n|$)", content, re.MULTILINE)
    return m.group(1).strip() if m else None

def sync_chunk_stage(month: str):
    """Logs INIT events for all existing trace files for the given month."""
    month_key = month.replace("-", "_")
    print(f"Syncing 'chunk' stage for {month}...")
    for trace_file in sorted(TRACES_DIR.glob(f"trace_{month_key}_batch_*.json")):
        batch_id = trace_file.stem.replace("trace_", "")
        log_event(
            entity_id=batch_id,
            stage="chunk",
            event="INIT",
            payload={"trace_file_path": str(trace_file)},
            file_to_verify=str(trace_file)
        )
    print("Done.")

def sync_write_stage(month: str):
    """Logs WRITE_SUCCESS events for all existing draft files."""
    print("Syncing 'write' stage...")
    # This is less efficient as we scan all drafts, but necessary for backfill
    for draft_file in sorted(PENDING_DIR.glob("*.md")):
        content = draft_file.read_text(encoding="utf-8")
        source_ids_str = extract_frontmatter_field(content, "sourceIds")
        if source_ids_str:
            source_ids_raw = source_ids_str.strip().strip('[]')
            source_ids = [s.strip().strip('\"') for s in source_ids_raw.split(',') if s.strip()]
            for source_id in source_ids:
                # We only care about sourceIds that are batches
                if source_id.startswith("source."):
                    batch_id = source_id.replace("source.", "").replace("-", "_")
                    # Check if this batch belongs to the month we are syncing
                    if month.replace("-", "_") in batch_id:
                        log_event(
                            entity_id=batch_id,
                            stage="write",
                            event="SUCCESS",
                            payload={"draft_path": str(draft_file)},
                            file_to_verify=str(draft_file)
                        )
    print("Done.")

def main():
    parser = argparse.ArgumentParser(description="Wiki Pipeline Ledger Sync Tool")
    parser.add_argument("--month", required=True, help="Month to sync in YYYY-MM format")
    parser.add_argument("--stage", required=True, choices=['chunk', 'write'], help="Pipeline stage to sync")
    args = parser.parse_args()

    if args.stage == 'chunk':
        sync_chunk_stage(args.month)
    elif args.stage == 'write':
        sync_write_stage(args.month)

if __name__ == "__main__":
    main()
