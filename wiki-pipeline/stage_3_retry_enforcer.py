#!/usr/bin/env python3
"""
stage_3_retry_enforcer.py — OpenClaw Wiki Pipeline v6.1 Stage 3.5
Smart router: assigns "syntax" or "rewrite" track based on QA issues.
Generates an automatic summary table dashboard on termination.
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from pipeline_utils import log_event

WIKI_ROOT  = Path.home() / ".openclaw/wiki/main"
TRACES_DIR = WIKI_ROOT / "transcripts/processed/traces"
MAX_RETRIES = 3

def print_pipeline_balance_sheet():
    print("\n==================================================")
    print("      OPENCLAW PIPELINE OPERATIONS REPORT         ")
    print("==================================================")
    
    traces_dir = Path(TRACES_DIR)
    trace_files = sorted(traces_dir.glob("trace_*.json"))
    if not trace_files:
        print("🖖 Operations Console clear. No active trace files found.")
        return

    categories = {"approved": [], "syntax": [], "rewrite": [], "dlq": []}

    for tf in trace_files:
        try:
            trace = json.loads(tf.read_text(encoding="utf-8"))
            batch_id = trace.get("batch_id", tf.stem.replace("trace_", ""))
            qa = trace.get("qa_result")
            retries = trace.get("retry_count", 0)
            
            if not qa: continue
                
            if qa.get("pass") and qa.get("issue_count", 1) == 0:
                categories["approved"].append((batch_id, "Ready for Promotion Gate"))
            elif retries >= MAX_RETRIES:
                categories["dlq"].append((batch_id, f"Max retries exceeded ({retries}/{MAX_RETRIES})"))
            else:
                track = trace.get("requeue_type", "initial pass")
                feedback = trace.get("requeue_feedback", "Awaiting compilation pass.")
                clean_feedback = feedback.replace("\n", " ").strip()[:85]
                if len(feedback) > 85: clean_feedback += "..."
                
                if track == "syntax": categories["syntax"].append((batch_id, clean_feedback))
                else: categories["rewrite"].append((batch_id, clean_feedback))
        except Exception: continue

    print("| Staging Inventory Status")
    print("|-------------------------------------------------")
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

def main():
    parser = argparse.ArgumentParser(description="Stage 3.5 Retry Enforcer v6.1")
    parser.add_argument("--traces-dir", default=str(TRACES_DIR))
    parser.add_argument("--month", default=None)
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)
    pattern = f"trace_{args.batch_id}.json" if args.batch_id else f"trace_{args.month.replace('-','_')}_batch_*.json" if args.month else "trace_*.json"
    trace_files = sorted(traces_dir.glob(pattern))

    if not trace_files: 
        print_pipeline_balance_sheet()
        sys.exit(1)

    approved, requeue, dlq, no_qa = [], [], [], []

    for tf in trace_files:
        trace = json.loads(tf.read_text(encoding="utf-8"))
        batch_id = trace.get("batch_id", tf.stem)
        qa = trace.get("qa_result")
        retries = trace.get("retry_count", 0)

        if not qa:
            no_qa.append(batch_id)
            continue

        if qa.get("pass") and qa.get("issue_count", 1) == 0:
            approved.append(batch_id)
        elif retries >= MAX_RETRIES:
            dlq.append(batch_id)
            log_event(batch_id, "enforce", "DLQ", {"reason": f"max retries ({MAX_RETRIES}) exceeded"})
        else:
            issues = qa.get("issues", [])
            issue_types = {i.get("type") for i in issues}
            content_errors = {"hallucination", "omission", "conflict"}

            if issue_types.intersection(content_errors):
                requeue_track = "rewrite"
                feedback = "\n".join(f"- {i.get('type')}: {i.get('detail')}" for i in issues if i.get("type") in content_errors)
            else:
                requeue_track = "syntax"
                feedback = qa.get("suggested_fix") or str(issues)

            trace["retry_count"] = retries + 1
            trace["requeue_type"] = requeue_track
            trace["requeue_feedback"] = feedback
            tf.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")
            
            requeue.append(batch_id)
            log_event(batch_id, "enforce", "REQUEUE", {"retry_count": retries + 1, "type": requeue_track})

    print_pipeline_balance_sheet()
    if requeue or dlq or no_qa: sys.exit(2)

if __name__ == "__main__": main()
