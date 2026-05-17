#!/usr/bin/env python3
"""
promote_wiki_pages.py — OpenClaw Wiki Pipeline v6.0 Stage 4
Repairs frontmatter, strips scaffolding, runs G1-G7 gates,
then moves approved drafts to their typed subdirectory in wiki root.

Page type → directory mapping:
  entity.*       → entities/
  concept.*      → concepts/       (includes lore and field-note pages)
  synthesis.*    → syntheses/
  concept.*disambiguation → wiki root (navigational pages stay at root)
"""

import json
import re
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime, timezone

WIKI_ROOT   = Path.home() / ".openclaw/wiki/main"
PENDING_DIR = WIKI_ROOT / "promoted-pending"

TYPE_DIRS = {
    "entity":    WIKI_ROOT / "entities",
    "concept":   WIKI_ROOT / "concepts",
    "synthesis": WIKI_ROOT / "syntheses",
}

SIZE_THRESHOLDS = {
    "entity":    1500,
    "concept":   1500,
    "synthesis": 2000,
    "default":   1500,
}

SCAFFOLD_HEADERS = re.compile(
    r"^#{1,3}\s*(Analysis|Routing|Routing Analysis|Synthesis|Summary|Template|"
    r"Stage \d|QA Result|QA Block|Decision Tree)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def extract_field(content: str, field: str) -> str:
    m = re.search(rf"^{field}:\s*['\"]?([^\n'\"]+)['\"]?", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def repair_frontmatter(content: str, batch_id: str) -> str:
    """Ensure required v6 frontmatter fields exist. Add stubs for missing ones."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stubs = {
        "status":      "active",
        "updatedAt":   ts,
        "model":       "google/gemini-app",
    }
    for field, default in stubs.items():
        if not re.search(rf"^{field}:", content, re.MULTILINE):
            # Insert after first --- block
            content = re.sub(r"^(---\n)", rf"\1{field}: {default}\n", content, count=1)
    return content


def strip_scaffolding(content: str) -> str:
    return SCAFFOLD_HEADERS.sub("", content)


def run_gates(content: str, filename: str) -> list[str]:
    """Returns list of failed gate names. Empty = all passed."""
    failures = []
    page_type = extract_field(content, "pageType")

    min_size = SIZE_THRESHOLDS.get(page_type, SIZE_THRESHOLDS["default"])
    if len(content) < min_size:
        failures.append(f"G1:SIZE ({len(content)} < {min_size})")

    import json
    try:
        # Indestructible source ID parsing
        import re
        source_match = re.search(r'source\.([0-9]{4}-[0-9]{2}-batch-[0-9]{3})', content)
        if source_match:
            batch_id = source_match.group(1).replace("-", "_")
        else:
            raise ValueError("No valid source.YYYY-MM-batch-NNN found in frontmatter")
        trace_path = WIKI_ROOT / "transcripts/processed/traces" / f"trace_{batch_id}.json"
        qa_pass = json.loads(trace_path.read_text(encoding="utf-8")).get("qa_result", {}).get("pass")
        if qa_pass is not True:
            failures.append("G2/G3: QA VERIFICATION FAILED OR MISSING")
    except Exception as e:
        failures.append(f"G2/G3: TRACE LOOKUP FAILED ({e})")

    sections = len(re.findall(r"^#{2,3} ", content, re.MULTILINE))
    if sections < 3:
        failures.append(f"G4:SECTIONS ({sections} < 3)")

    if "[[" not in content and "TODO: links" not in content and "*No internal links available at time of writing.*" not in content:
        failures.append("G5:LINKS")

    if not re.search(r"\[!(info|success|abstract)\]", content):
        failures.append("G6:CALLOUT")

    if SCAFFOLD_HEADERS.search(content):
        failures.append("G7:SCAFFOLD (strip failed)")

    return failures


def destination_dir(content: str) -> Path:
    """Disambiguations go to root; everything else to typed subdir."""
    page_type = extract_field(content, "pageType")
    tags_line = extract_field(content, "tags")
    if "disambiguation" in tags_line:
        return WIKI_ROOT
    return TYPE_DIRS.get(page_type, WIKI_ROOT / "concepts")


def build_ledger_balance_sheet(ledger_path: Path) -> dict:
    """Reads the immutable ledger WAL chronologically to derive current authorized state."""
    if not ledger_path.exists():
        return {}
    balance_sheet = {}
    import json
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): 
                continue
            try:
                entry = json.loads(line.strip())
                batch_id = entry.get("id")
                stage = entry.get("stage")
                event = entry.get("event")
                payload = entry.get("payload") or {}
                
                if stage == "write" and event == "SUCCESS":
                    balance_sheet[batch_id] = {
                        "filename": payload.get("filename"),
                        "qa_pass": False
                    }
                elif stage == "qa" and event == "SUCCESS":
                    if batch_id in balance_sheet:
                        balance_sheet[batch_id]["qa_pass"] = True
                elif stage == "qa" and event == "FAIL":
                    if batch_id in balance_sheet:
                        balance_sheet[batch_id]["qa_pass"] = False
            except Exception:
                continue
    return balance_sheet

def main():
    parser = argparse.ArgumentParser(description="Promote Wiki Pages v6.0")
    parser.add_argument("--pending-dir", default=str(PENDING_DIR))
    parser.add_argument("--wiki-root",   default=str(WIKI_ROOT))
    parser.add_argument("--month",       default=None)
    parser.add_argument("--dry-run",     action="store_true")
    args = parser.parse_args()

    pending_dir = Path(args.pending_dir)
    wiki_root   = Path(args.wiki_root)
    drafts      = sorted(pending_dir.glob("*.md"))

    if not drafts:
        print(f"❌ No drafts in {pending_dir}")
        sys.exit(1)

    print(f"🚀 Promote Wiki Pages v6.0 — {len(drafts)} drafts\n")

    promoted = archived = skipped = 0
    archive_dir = pending_dir / "archive"

    # Reconcile books against physical reality
    ledger_file = wiki_root / "promotion_ledger.jsonl"
    balance_sheet = build_ledger_balance_sheet(ledger_file)
    
    # Map filenames to their authorized batch entries for easy cross-referencing
    authorized_mappings = {info["filename"]: batch_id for batch_id, info in balance_sheet.items() if info["qa_pass"]}

    for draft in drafts:
        content  = draft.read_text(encoding="utf-8")
        filename = draft.name
        
        # Balance Sheet Verification Gate
        if filename not in authorized_mappings:
            print(f"  🧹 Archiving stale historical draft: {filename}")
            if not args.dry_run:
                archive_dir.mkdir(exist_ok=True)
                shutil.move(str(draft), str(archive_dir / filename))
            archived += 1
            continue

        # Repair + strip
        content = repair_frontmatter(content, filename)
        content = strip_scaffolding(content)

        # Gate check
        failures = run_gates(content, filename)
        if failures:
            print(f"  ❌ {filename}")
            for f in failures:
                print(f"     {f}")
            if not args.dry_run:
                archive_dir.mkdir(exist_ok=True)
                shutil.move(str(draft), str(archive_dir / filename))
            archived += 1
            continue

        # Destination
        dest_dir = destination_dir(content)
        dest     = dest_dir / filename

        page_type = extract_field(content, "pageType")
        tag_hint  = " [disambiguation→root]" if dest_dir == wiki_root and page_type != "" else ""
        print(f"  ✅ {filename} → {dest_dir.name}/{tag_hint}")

        if not args.dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            draft.unlink()

        promoted += 1

    print(f"\n📊 Promotion complete:")
    print(f"   ✅ Promoted: {promoted}")
    print(f"   ❌ Archived: {archived}")
    print(f"   Next: review {wiki_root} in Obsidian, then: make index")


if __name__ == "__main__":
    main()
