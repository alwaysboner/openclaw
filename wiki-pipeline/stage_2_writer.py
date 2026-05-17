#!/usr/bin/env python3
"""
stage_2_writer.py — OpenClaw Wiki Pipeline v6.1 Stage 2 (Newsroom Arch)
Drafts pages with Pro using a universal planning scratchpad,
then uses Flash as an inline Copy Editor pass.
"""

import json
import re
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
from google.api_core.exceptions import ResourceExhausted
from pipeline_utils import log_event

WIKI_ROOT   = Path.home() / ".openclaw/wiki/main"
TRACES_DIR  = WIKI_ROOT / "transcripts/processed/traces"
PENDING_DIR = WIKI_ROOT / "promoted-pending"
MAX_TOKENS  = 8192
PROMPT_CARD = Path(__file__).parent / "prompt_s2_writer.md"

COPY_EDIT_PROMPT = """You are a strict copy-editor and formatter. You do NOT generate new ideas.
Do NOT change any prose, facts, narrative structure, or conversational tone.
Fix ONLY the following formatting rules:
1. Ensure all [^n] footnotes in the body have a matching definition in the ## References section.
2. If a footnote exists in ## References but is missing from the body, DO NOT delete it. Insert the [^n] marker into the body where the fact is mentioned.
3. Ensure there are at least two valid [[Internal Links]].
4. Verify the YAML frontmatter is perfectly formatted.
Return the complete, corrected markdown document and absolutely nothing else. Do not wrap it in a code block.
"""

def clean_markdown_fences(text: str) -> str:
    text = text.strip()
    md_fence = chr(96) * 3 + "markdown"
    fence = chr(96) * 3
    if text.startswith(md_fence): text = text[11:]
    elif text.startswith(fence): text = text[3:]
    if text.endswith(fence): text = text[:-3]
    return text.strip()

def call_google(model_id: str, prompt: str, retries: int = 3) -> Optional[str]:
    for i in range(retries):
        try:
            aiplatform.init()
            model = GenerativeModel(model_id)
            temp = 0.5 if "PLANNING ENGINE" in prompt or "FACTUAL AUDIT" in prompt else 0.3
            config = {"max_output_tokens": MAX_TOKENS, "temperature": temp}
            resp  = model.generate_content(prompt, generation_config=config)
            
            # Safe Multi-Part Token Aggregator Pass
            if resp.candidates and resp.candidates[0].content.parts:
                text_parts = []
                for part in resp.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    return clean_markdown_fences("".join(text_parts))
            
            return clean_markdown_fences(resp.text)
        except ResourceExhausted:
            wait = (2 ** (i + 2))
            print(f"    ⏳ [{model_id}]: Rate limit hit. Retrying in {wait}s...")
            time.sleep(wait)
            continue
        except Exception as e:
            print(f"    ❌ Google [{model_id}]: {str(e)[:80]}")
            return None
    return None

def run_copy_editor(draft: str, model_id: str, qa_feedback: Optional[str] = None) -> Optional[str]:
    header = f"## QA CRITIQUE NOTES TO IMPLEMENT\n{qa_feedback}\n\n" if qa_feedback else ""
    prompt = f"{COPY_EDIT_PROMPT}\n\n{header}## DRAFT TO FIX\n\n{draft}"
    return call_google(model_id, prompt)

def load_prompt_card() -> str:
    if PROMPT_CARD.exists(): return PROMPT_CARD.read_text(encoding="utf-8")
    return "You are an archivist. Follow schema. Return markdown only."

def build_prompt(batch: dict, manifest: list, writer_model: str, operator: str, qa_feedback: Optional[str] = None, requeue_type: str = "rewrite") -> str:
    prompt = load_prompt_card()
    prompt = prompt.replace("{PAGES_MANIFEST_JSON}", json.dumps(manifest, indent=2, ensure_ascii=False))
    prompt = prompt.replace("{BATCH_JSON}", json.dumps(batch, indent=2, ensure_ascii=False))
    prompt = prompt.replace("{WRITER_MODEL_ID}", writer_model)
    prompt = prompt.replace("{OPERATOR_HANDLE}", operator)
    
    planning = (
        "## MANDATORY PRE-FLIGHT PLANNING ENGINE\n"
        "Before generating the final wiki page block, you MUST open a `<planning>` tag and solve these constraints out loud:\n"
        "1. CHRONOLOGICAL DATA AUDIT: Trace conversation turns. Edits or pivots made at the end of the batch supersede earlier turns.\n"
        "2. FILTER NOISE: Isolate concrete software engineering choices and lore from user tangents or code experiments.\n"
        "3. CITATION MATRIX: Map all factual layout claims directly to their exact zero-padded CANARY line ranges in the transcript.\n"
        "Close with `</planning>` before beginning the frontmatter block starting with `---`.\n\n"
    )

    if qa_feedback and requeue_type == "rewrite":
        override = f"## CRITICAL FACTUAL AUDIT REQUIRED\nPrevious attempt failed QA check:\n{qa_feedback}\nAudit these specific points in your `<planning>` scratchpad.\n\n"
        return override + planning + prompt
        
    return planning + prompt

def derive_filename(content: str, batch_id: str) -> str:
    m = re.search(rf"^id:\s*['\"]?([^\n'\"]+)['\"]?", content, re.MULTILINE)
    if m:
        page_id = m.group(1).strip()
        safe = re.sub(r"[^\w.\-]", "-", page_id)
        return f"{safe}.md"
    return f"stage2_{batch_id}.md"

def find_draft(batch_id: str, pending_dir: Path) -> Optional[Path]:
    target = f"source.{batch_id.replace('_', '-')}"
    for f in pending_dir.glob("*.md"):
        try:
            if target in f.read_text(encoding="utf-8"): return f
        except Exception: pass
    return None

def write_batch(trace_file: Path, pending_dir: Path, manifest: list, operator: str, args, trace_data: dict) -> bool:
    batch_id = trace_data.get("batch_id", trace_file.stem)
    requeue_type = trace_data.get("requeue_type", "rewrite")
    qa_feedback = trace_data.get("requeue_feedback")

    if requeue_type == "syntax":
        print(f"    📝 Syntax pass with {args.primary_model[:45]}...", end=" ", flush=True)
        draft_file = find_draft(batch_id, pending_dir)
        if draft_file:
            edited = run_copy_editor(draft_file.read_text(encoding="utf-8"), args.primary_model, qa_feedback)
            if edited:
                draft_file.write_text(edited, encoding="utf-8")
                print(f"→ ✅ {draft_file.name}")
                log_event(batch_id, "write", "SUCCESS", {"filename": draft_file.name, "type": "syntax_edit"})
                return True
        print("❌ Syntax edit failed. Falling back to rewrite.")

    cascade = [args.quality_model, args.primary_model] if qa_feedback else [args.primary_model, args.quality_model]
    for model_id in cascade:
        print(f"    🤖 {model_id[:45]}", end=" ", flush=True)
        prompt = build_prompt(trace_data, manifest, model_id, operator, qa_feedback, requeue_type)
        content = call_google(model_id, prompt)
        if not content: continue

        # Surgical removal of thinking scratchpad before committing to file
        if "<planning>" in content:
            content = content.split("</planning>")[-1].strip()

        print(f"\n    📝 Inline Copy-Edit with {args.primary_model[:45]}...", end=" ", flush=True)
        edited = run_copy_editor(content, args.primary_model, qa_feedback)
        if edited: content = edited

        filename = derive_filename(content, batch_id)
        out_path = pending_dir / filename
        pending_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"→ ✅ {filename}")
        log_event(batch_id, "write", "SUCCESS", {"filename": filename})
        return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True)
    parser.add_argument("--manifest", default=str(WIKI_ROOT / "pages_manifest.json"))
    parser.add_argument("--operator", default="Jason")
    parser.add_argument("--traces-dir", default=str(TRACES_DIR))
    parser.add_argument("--pending-dir", default=str(PENDING_DIR))
    parser.add_argument("--primary-model", default="gemini-2.5-flash")
    parser.add_argument("--quality-model", default="gemini-2.5-pro")
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)
    pattern = f"trace_{args.batch_id}.json" if args.batch_id else f"trace_{args.month.replace('-','_')}_batch_*.json"
    trace_files = sorted(traces_dir.glob(pattern))

    if not trace_files: sys.exit(1)

    print(f"📝 Stage 2 Writer v6.1 (Newsroom Arch) — {args.month}")
    manifest = []
    if Path(args.manifest).exists():
        with open(args.manifest, "r", encoding="utf-8") as f: manifest = json.load(f)

    for tf in trace_files:
        print(f"⏳ {tf.stem.replace('trace_', '')}")
        trace_data = json.loads(tf.read_text(encoding="utf-8"))
        write_batch(tf, Path(args.pending_dir), manifest, args.operator, args, trace_data)

if __name__ == "__main__": main()


