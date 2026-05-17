import json
import re
from pathlib import Path

traces_dir = Path.home() / ".openclaw/wiki/main/transcripts/processed/traces"
sources_dir = Path.home() / ".openclaw/wiki/main/sources"

if not traces_dir.exists():
    print("❌ Traces directory not found.")
    exit(1)

sources_dir.mkdir(parents=True, exist_ok=True)
print("Parsing cold traces into block-linkable source Markdown files...")

count = 0
for trace_file in traces_dir.glob("*.json"):
    if "report" in trace_file.name:
         continue
         
    try:
        data = json.loads(trace_file.read_text(encoding="utf-8"))
        batch_id = trace_file.stem.replace("trace_", "")
        month_match = re.search(r"(\d{4}_\d{2})", batch_id)
        if not month_match: continue
        month_formatted = month_match.group(1).replace("_", "-")
        
        md_filename = f"source.history-{month_formatted}-{batch_id.replace('_', '-')}.md"
        md_path = sources_dir / md_filename
        
        turns = data.get("messages", [])
        if not turns: continue
        
        md_content = []
        md_content.append("---")
        md_content.append("pageType: source")
        md_content.append(f"id: source.{batch_id.replace('_', '-')}")
        md_content.append(f"title: \"Historical Session Log: {batch_id}\"")
        md_content.append(f"sourceType: historical-trace")
        md_content.append("status: active")
        md_content.append("---")
        md_content.append(f"\n# Historical Session Log: {batch_id}\n")
        
        for turn in turns:
            role = turn.get("role", "unknown").capitalize()
            
            # Extract content payload following the array-of-dicts spec
            raw_content = turn.get("content", turn.get("text", ""))
            
            if isinstance(raw_content, list):
                parts = []
                for part in raw_content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict):
                        parts.append(part.get("text", part.get("content", "")))
                text = "\n".join(filter(None, parts)).strip()
            elif isinstance(raw_content, dict):
                text = raw_content.get("text", raw_content.get("content", "")).strip()
            else:
                text = str(raw_content).strip()
                
            canary = turn.get("_canary", "CANARY-UNKNOWN")
            md_content.append(f"**{role}:** {text} ^{canary}\n")
            
        md_path.write_text("\n".join(md_content), encoding="utf-8")
        print(f"  → Generated: sources/{md_filename}")
        count += 1
    except Exception as e:
        print(f"  ⚠️ Error parsing {trace_file.name}: {e}")

print(f"\n✅ All cold traces converted! Total files written: {count}")