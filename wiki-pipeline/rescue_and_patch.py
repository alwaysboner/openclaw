import pathlib
import os
import shutil

# 1. Rescue the drafts from the archive
pending_dir = pathlib.Path("/home/ubuntu/.openclaw/wiki/main/promoted-pending")
archive_dir = pending_dir / "archive"

if archive_dir.exists():
    for draft in archive_dir.glob("*.md"):
        shutil.move(str(draft), str(pending_dir / draft.name))
    print(f"✅ Rescued drafts from archive.")

# 2. Patch the brittle parsing logic in the promote script
p_promote = pathlib.Path("promote_wiki_pages.py")
p_text = p_promote.read_text(encoding="utf-8")

bad_parse = """        raw_source = extract_field(content, "sourceIds").strip("[]'\\" ")
        batch_id = raw_source.split(',')[0].strip().replace("source.", "").replace("-", "_")"""

good_parse = """        # Indestructible source ID parsing
        import re
        source_match = re.search(r'source\.([0-9]{4}-[0-9]{2}-batch-[0-9]{3})', content)
        if source_match:
            batch_id = source_match.group(1).replace("-", "_")
        else:
            raise ValueError("No valid source.YYYY-MM-batch-NNN found in frontmatter")"""

if bad_parse in p_text:
    p_text = p_text.replace(bad_parse, good_parse)
    p_promote.write_text(p_text, encoding="utf-8")
    print("✅ Promote script parsing logic hardened.")
else:
    print("⚠️ Could not find parse logic to patch. Check file manually.")
