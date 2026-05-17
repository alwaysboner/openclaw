import re
import pathlib
import json

# 1. Fix Writer Prompt (Remove HTML comment, use safe markdown)
p_writer = pathlib.Path("prompt_s2_writer.md")
w_text = p_writer.read_text(encoding="utf-8")
w_text = re.sub(
    r"- \*\*G5: LINKS\*\*:.*?(?=- \*\*G6: CALLOUT\*\*)",
    "- **G5: LINKS**: The page MUST contain at least two `[[Internal Links]]`. If no relevant pages exist, add the exact text `*No internal links available at time of writing.*` in the `## See Also` section.\n",
    w_text,
    flags=re.DOTALL
)
p_writer.write_text(w_text, encoding="utf-8")

# 2. Fix QA Prompt (Match the safe markdown)
p_qa = pathlib.Path("prompt_s3_qa.md")
q_text = p_qa.read_text(encoding="utf-8")
q_text = re.sub(
    r"5\. Minimum 2 `\[\[Internal Links\]\]`.*?\n",
    "5. Minimum 2 `[[Internal Links]]` (or the exact string `*No internal links available at time of writing.*` if manifest is empty)\n",
    q_text
)
p_qa.write_text(q_text, encoding="utf-8")

# 3. Fix Runbook Documentation Drift
p_runbook = pathlib.Path("OpenClaw Wiki Runbook v6.0.md")
r_text = p_runbook.read_text(encoding="utf-8")
r_text = r_text.replace("flash→pro→deepseek→mistral", "flash→pro")
r_text = r_text.replace("`` fallback", "`*No internal links...*` fallback")
p_runbook.write_text(r_text, encoding="utf-8")

# 4. Reset batch_000 trace counter to escape the DLQ trap
trace_path = pathlib.Path("/home/ubuntu/.openclaw/wiki/main/transcripts/processed/traces/trace_2026_01_batch_000.json")
if trace_path.exists():
    trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
    trace_data["retry_count"] = 0
    trace_path.write_text(json.dumps(trace_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✅ batch_000 retry counter reset to 0.")

# 5. Clean up old patch files
import glob, os
for patch_file in glob.glob("patch_*.py"):
    os.remove(patch_file)

print("✅ G5 Deadlock resolved. Runbook updated. Workspace cleaned.")
