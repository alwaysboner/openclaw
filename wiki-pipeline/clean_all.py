import pathlib
import os
import glob

# 1. Update the Runbook State Machine Table to flash→pro only
p_runbook = pathlib.Path("OpenClaw Wiki Runbook v6.0.md")
if p_runbook.exists():
    r_text = p_runbook.read_text(encoding="utf-8")
    # Fix the pipeline state machine table column for Stage 2
    r_text = r_text.replace("flash→pro→deepseek→mistral", "flash→pro")
    p_runbook.write_text(r_text, encoding="utf-8")
    print("✅ Runbook pipeline table aligned to flash→pro.")

# 2. Complete workspace sweep of all one-shot patch scripts
print("🧹 Cleaning one-shot scripts from workspace...")
for patch_file in glob.glob("patch_*.py") + glob.glob("repair_*.py") + ["wire_bedrock.py"]:
    try:
        os.remove(patch_file)
        print(f"   Removed: {patch_file}")
    except FileNotFoundError:
        continue

print("✅ Workspace pristine.")
