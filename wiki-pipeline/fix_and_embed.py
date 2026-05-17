import json
import re
from pathlib import Path

# 1. Restore the Makefile to its clean, standard state
p_make = Path("Makefile")
make_code = p_make.read_text()
# Strip out the broken inline dashboard injections
clean_make = re.sub(r'\s*python3 pipeline_balance_sheet\.py', '', make_code)
p_make.write_text(clean_make)
print("✅ Makefile restored and cleaned.")

# 2. Append the Balance Sheet Reporting Engine directly into Stage 3.5 Enforcer
p_enforcer = Path("stage_3_retry_enforcer.py")
enforcer_code = p_enforcer.read_text()

balance_sheet_func = """
def print_pipeline_balance_sheet():
    print("\\n==================================================")
    print("      OPENCLAW PIPELINE OPERATIONS REPORT         ")
    print("==================================================")
    
    traces_dir = Path(WIKI_ROOT / "transcripts/processed/traces")
    trace_files = sorted(traces_dir.glob("trace_*.json"))
    if not trace_files:
        print("🖖 Operations Console clear. No active trace files.")
        return

    categories = {"approved": [], "syntax": [], "rewrite": [], "dlq": []}

    for tf in trace_files:
        try:
            trace = json.loads(tf.read_text(encoding="utf-8"))
            batch_id = trace.get("batch_id", tf.stem.replace("trace_", ""))
            qa = trace.get("qa_result", {})
            retries = trace.get("retry_count", 0)
            
            if qa.get("pass") and qa.get("issue_count", 0) == 0:
                categories["approved"].append((batch_id, "Ready for Promotion Gate"))
            elif retries >= MAX_RETRIES:
                categories["dlq"].append((batch_id, "Max retries exceeded (3/3)"))
            else:
                track = trace.get("requeue_type", "initial pass")
                feedback = trace.get("requeue_feedback", "Awaiting execution run.")
                clean_feedback = feedback.replace("\\n", " ").strip()[:85]
                if len(feedback) > 85: clean_feedback += "..."
                
                if track == "syntax":
                    categories["syntax"].append((batch_id, clean_feedback))
                else:
                    categories["rewrite"].append((batch_id, clean_feedback))
        except Exception:
            continue

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
            print(f"\\n🔹 {title}:")
            for bid, issues in categories[section]:
                print(f"  • {bid} → {issues}")

    if categories["approved"]:
        print("\\n🚀 AUTHORIZED PROMOTIONS:")
        print(f"  • Progress verified for: {', '.join([b[0] for b in categories['approved']])}")
    print("==================================================\\n")
"""

# Inject function and wire it to execute right before the exit gates
if "print_pipeline_balance_sheet" not in enforcer_code:
    enforcer_code = enforcer_code.replace("import sys", "import sys\\nfrom pathlib import Path")
    enforcer_code = enforcer_code.replace("if __name__ == \\"__main__\\":", balance_sheet_func + "\\nif __name__ == \\"__main__\\":")
    enforcer_code = enforcer_code.replace("sys.exit(2)", "print_pipeline_balance_sheet()\\n    sys.exit(2)")
    enforcer_code = enforcer_code.replace("sys.exit(1)", "print_pipeline_balance_sheet()\\n    sys.exit(1)")
    enforcer_code = enforcer_code.replace("approved:", "print_pipeline_balance_sheet()\\n    # approved:")
    enforcer_code = enforcer_code.replace("if approved:", "print_pipeline_balance_sheet()\\n    if approved:")
    p_enforcer.write_text(enforcer_code)
    print("✅ Stage 3.5 Enforcer patched with native dashboard printout.")
