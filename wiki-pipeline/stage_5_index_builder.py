#!/usr/bin/env python3
"""
stage_5_index_builder.py — OpenClaw Wiki Pipeline v6.0 Stage 6
Rebuilds all wiki indexes after Stage 5 approval.

Outputs:
  index.md                  root — all pages grouped by primary tag
  entities/index.md         entity pages by sourcePeriod desc
  concepts/index.md         concept pages by sourcePeriod desc
  syntheses/index.md        synthesis pages by sourcePeriod desc
  sources/index.md          source pages by sourcePeriod desc
  tag_map.json              tag → [page id list]
  pipeline_report_YYYY_MM.md
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

WIKI_ROOT = Path.home() / ".openclaw/wiki/main"

SKIP_FILES = {"index.md", "WIKI.md", "inbox.md", "tag_map.json"}
SKIP_DIRS  = {"promoted-pending", "transcripts", ".openclaw-wiki", "reports", "archive"}

TYPE_DIRS = {
    "entity":    "entities",
    "concept":   "concepts",
    "synthesis": "syntheses",
    "source":    "sources",
}


def parse_frontmatter(content: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        kv = line.split(":", 1)
        if len(kv) == 2:
            k, v = kv[0].strip(), kv[1].strip().strip('"\'')
            fm[k] = v
    # parse tags list
    tags_raw = fm.get("tags", "")
    fm["tags_list"] = re.findall(r"[\w\-]+", tags_raw)
    return fm


def scan_pages(wiki_root: Path) -> list[dict]:
    pages = []
    for md in wiki_root.rglob("*.md"):
        if md.name in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in md.parts):
            continue
        if md.name.startswith("pipeline_report"):
            continue
        content = md.read_text(encoding="utf-8")
        fm      = parse_frontmatter(content)
        if not fm.get("pageType") and not fm.get("id"):
            continue
        pages.append({
            "path":         md,
            "filename":     md.name,
            "rel":          str(md.relative_to(wiki_root)),
            "id":           fm.get("id", md.stem),
            "title":        fm.get("title", md.stem),
            "pageType":     fm.get("pageType", ""),
            "tags":         fm.get("tags_list", []),
            "sourcePeriod": fm.get("sourcePeriod", "0000-00"),
            "authoredBy":   fm.get("authoredBy", ""),
        })
    return sorted(pages, key=lambda p: p["sourcePeriod"], reverse=True)


def build_root_index(pages: list[dict], today: str) -> str:
    by_tag = defaultdict(list)
    for p in pages:
        primary = p["tags"][0] if p["tags"] else "untagged"
        by_tag[primary].append(p)

    lines = [f"# Wiki Index", f"_Last updated: {today}_", ""]
    for tag in sorted(by_tag):
        lines.append(f"## {tag}")
        for p in sorted(by_tag[tag], key=lambda x: x["sourcePeriod"], reverse=True):
            lines.append(f"- [[{p['id']}|{p['title']}]] — {p['sourcePeriod']}")
        lines.append("")
    return "\n".join(lines)


def build_type_index(pages: list[dict], page_type: str, today: str) -> str:
    subset = [p for p in pages if p["pageType"] == page_type]
    label  = page_type.capitalize() + " Pages"
    lines  = [f"# {label}", f"_Last updated: {today}_", ""]
    if not subset:
        lines.append("_No pages yet._")
    else:
        for p in subset:
            lines.append(f"- [[{p['id']}|{p['title']}]] — {p['sourcePeriod']}")
    return "\n".join(lines)


def build_tag_map(pages: list[dict]) -> dict:
    tag_map = defaultdict(list)
    for p in pages:
        for t in p["tags"]:
            tag_map[t].append(p["id"])
    return {k: v for k, v in sorted(tag_map.items())}


def build_pages_manifest(pages: list[dict]) -> list[dict]:
    manifest = []
    for p in pages:
        manifest.append({
            "id": p["id"],
            "title": p["title"],
            "path": p["rel"],
            "pageType": p["pageType"],
        })
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Stage 6 Index Builder v6.0")
    parser.add_argument("--wiki-root", default=str(WIKI_ROOT))
    parser.add_argument("--month",     default=None)
    args = parser.parse_args()

    wiki_root = Path(args.wiki_root)
    today     = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"📚 Stage 6 Index Builder v6.0 — {today}")
    pages = scan_pages(wiki_root)
    print(f"   Found {len(pages)} pages\n")

    # Root index
    root_index = build_root_index(pages, today)
    (wiki_root / "index.md").write_text(root_index, encoding="utf-8")
    print(f"  ✅ index.md ({len(pages)} pages)")

    # Per-type indexes
    for ptype, dirname in TYPE_DIRS.items():
        content  = build_type_index(pages, ptype, today)
        type_dir = wiki_root / dirname
        type_dir.mkdir(exist_ok=True)
        (type_dir / "index.md").write_text(content, encoding="utf-8")
        count = len([p for p in pages if p["pageType"] == ptype])
        print(f"  ✅ {dirname}/index.md ({count} pages)")

    # Tag map
    tag_map = build_tag_map(pages)
    (wiki_root / "tag_map.json").write_text(
        json.dumps(tag_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  ✅ tag_map.json ({len(tag_map)} tags)")

    # Pages manifest (for writer linking)
    pages_manifest = build_pages_manifest(pages)
    (wiki_root / "pages_manifest.json").write_text(
        json.dumps(pages_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  ✅ pages_manifest.json ({len(pages_manifest)} pages)")

    # Pipeline report
    if args.month:
        report_path = wiki_root / f"pipeline_report_{args.month}.md"
        report = (
            f"# Pipeline Run Report: {args.month}\n"
            f"**Index rebuilt:** {today} | **Pages:** {len(pages)}\n\n"
            f"## Tag Distribution\n"
        )
        for tag, ids in list(tag_map.items())[:20]:
            report += f"- `{tag}`: {len(ids)}\n"
        report_path.write_text(report, encoding="utf-8")
        print(f"  ✅ pipeline_report_{args.month}.md")

    print(f"\n✨ Done. Run: openclaw wiki lint")


if __name__ == "__main__":
    main()
