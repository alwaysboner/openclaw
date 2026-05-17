#!/usr/bin/env python3
import json
from pathlib import Path

WIKI_ROOT   = Path.home() / ".openclaw/wiki/main"
TRACES_DIR  = WIKI_ROOT / "transcripts/processed/traces"
PENDING_DIR = WIKI_ROOT / "promoted-pending"

def get_sheet():
    print("\n==================================================")
    print("      OPENCLAW PIPELINE OPERATIONS REPORT         ")
    print("==================================================")
    
    trace_files = sorted(TRACES_DIR.glob("trace_*.json"))
    if not trace_files:
        print("🖖 Operations Console clear. No trace files found.")
        return

    categories = {"approved": [], "syntax": [], "rewrite": [], "dlq": []}

    for tf in trace_files:
        try:
            trace = json.loads(tf.read_text(encoding="utf-8"))
            batch_id = trace.get("batch_id", tf.stem.replace("trace_", ""))
            qa = trace.get("qa_result", {})
            retries = trace.get("retry_count", 0)
            
            # Categorize based on live state machine records
            if qa.get("pass") and qa.get("issue_count", 1) == 0:
                categories["approved"].append((batch_id, "Ready for Promotion Gate"))
            elif retries >= 3:
                categories["dlq"].append((batch_id, "Max retries exceeded (3/3)"))
            else:
                track = trace.get("requeue_type", "initial pass")
                feedback = trace.get("requeue_feedback", "Awaiting execution run.")
                clean_feedback = feedback.replace("\n", " ").strip()[:85]
                if len(feedback) > 85: clean_feedback += "..."
                
                if track == "syntax":
                    categories["syntax"].append((batch_id, clean_feedback))
                else:
                    categories["rewrite"].append((batch_id, clean_feedback))
        except Exception:
            continue

    # Print Balance Sheet Summary Table
    print(f"| Staging Inventory Status")
    print(f"|-------------------------------------------------")
    print(f"| ✅ APPROVED:  {len(categories['approved'])} batch(es)")
    print(f"| 🔧 SYNTAX:    {len(categories['syntax'])} batch(es) holding on style tags")
    print(f"| ✍️  REWRITE:   {len(categories['rewrite'])} batch(es) holding on fact verification")
    print(f"| 🚫 DELETIONS: {len(categories['dlq'])} batch(es) quarantined in DLQ")
    print("==================================================")

    for section, title in [("rewrite", "✍️  REWRITE DESK (Blocked on Content Facts)"), 
                           ("syntax", "🔧 SYNTAX DESK (Blocked on Layout/Tags)")]:
        if categories[section]:
            print(f"\n🔹 {title}:")
            for bid, issues in categories[section]:
                print(f"  • {bid} → {issues}")

    if categories["approved"]:
        print("\n🚀 AUTHORIZED PROMOTIONS:")
        print(f"  • Progress verified for: {', '.join([b[0] for b in categories['approved']])}")
    print("==================================================\n")

if __name__ == "__main__":
    get_sheet()
