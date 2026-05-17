import json
import argparse
from pathlib import Path
from collections import defaultdict

LEDGER_PATH = Path.home() / ".openclaw/wiki/main/promotion_ledger.jsonl"

def parse_ledger_entry(entry):
    """Parses both old and new ledger formats."""
    # New format is canonical
    if "stage" in entry and "event" in entry:
        return entry["stage"], entry["event"]
    
    # Handle old backfill format where event_type was written to the event key
    elif "event" in entry:
        event_val = entry["event"]
        if event_val == "CHUNK_INIT":
            return "chunk", "INIT"
        elif event_val == "WRITE_SUCCESS":
            return "write", "SUCCESS"
            
    return None, None

def get_batch_status(ledger_path):
    batch_states = defaultdict(
        lambda: {"chunk_init": False, "write_success": False, "qa_pass": False, "qa_fail": False, "enforce_requeue": False, "enforce_dlq": False}
    )

    if not ledger_path.exists():
        return batch_states

    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                batch_id = entry.get("id")
                if not batch_id:
                    continue

                stage, event = parse_ledger_entry(entry)

                if stage == "chunk" and event == "INIT":
                    batch_states[batch_id]["chunk_init"] = True
                elif stage == "write" and event == "SUCCESS":
                    batch_states[batch_id]["write_success"] = True
                    # If write succeeds, previous QA/Enforce states are invalid for a retry
                    batch_states[batch_id]["qa_pass"] = False
                    batch_states[batch_id]["qa_fail"] = False
                    batch_states[batch_id]["enforce_requeue"] = False
                    batch_states[batch_id]["enforce_dlq"] = False
                elif stage == "write" and event == "FAIL":
                    # If write fails, it means it needs a re-write.
                    batch_states[batch_id]["write_success"] = False # Mark as not successful
                elif stage == "qa" and event == "SUCCESS":
                    batch_states[batch_id]["qa_pass"] = True
                    batch_states[batch_id]["qa_fail"] = False # Clear previous fail
                elif stage == "qa" and event == "FAIL":
                    batch_states[batch_id]["qa_fail"] = True
                    batch_states[batch_id]["qa_pass"] = False # Clear previous pass
                elif stage == "enforce" and event == "REQUEUE":
                    batch_states[batch_id]["enforce_requeue"] = True
                    batch_states[batch_id]["qa_pass"] = False # Requeue implies QA was not clean
                elif stage == "enforce" and event == "DLQ":
                    batch_states[batch_id]["enforce_dlq"] = True

            except json.JSONDecodeError:
                # print(f"Warning: Could not parse ledger line: {line.strip()}")
                continue
    return batch_states

def main():
    parser = argparse.ArgumentParser(description="Find missing batches in wiki pipeline.")
    parser.add_argument("--ledger-path", default=str(LEDGER_PATH), help="Path to promotion_ledger.jsonl")
    parser.add_argument("--human-readable", action="store_true", help="Output human-readable status instead of just IDs")
    args = parser.parse_args()

    batch_states = get_batch_status(Path(args.ledger_path))

    for batch_id, state in sorted(batch_states.items()):
        needs_requeue = (state["qa_fail"] or state["enforce_requeue"]) or \
                          (state["chunk_init"] and not state["write_success"])
        needs_qa = state["write_success"] and not state["qa_pass"] and not state["enforce_dlq"]

        if args.human_readable:
            if needs_requeue:
                print(f"{batch_id}: STUCK_OR_MISSING_WRITE (make requeue BATCH={batch_id})")
            elif needs_qa:
                # This is a less critical state, just needs QA run on it.
                print(f"{batch_id}: PENDING_QA (make qa BATCH={batch_id})")
        elif needs_requeue:
            print(batch_id)

if __name__ == "__main__":
    main()
