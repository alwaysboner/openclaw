import json
from pathlib import Path

for b in ["004", "005", "007", "009", "012", "015"]:
    p = Path(f"/home/ubuntu/.openclaw/wiki/main/transcripts/processed/traces/trace_2026_02_batch_{b}.json")
    if p.exists():
        d = json.loads(p.read_text())
        print(f"\n🦞 {d.get('batch_id')}")
        print(f"   Track:  {d.get('requeue_type', 'unknown')}")
        print(f"   Issues: {d.get('requeue_feedback')}")
