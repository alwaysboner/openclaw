#!/usr/bin/env python3
"""
stage_3_qa.py — OpenClaw Wiki Pipeline v6.0 Stage 3
Validates each draft in promoted-pending against its source batch.
Writes QA result into the trace file. JSON output from LLM only.
"""

import json
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import time
import requests
import google.auth
import google.auth.transport.requests
from pipeline_utils import log_event

WIKI_ROOT   = Path.home() / ".openclaw/wiki/main"
TRACES_DIR  = WIKI_ROOT / "transcripts/processed/traces"
PENDING_DIR = WIKI_ROOT / "promoted-pending"

MAX_TOKENS = 4096

def load_prompt_card() -> str:
    """Load the prompt card from prompt_s3_qa.md."""
    card_path = Path(__file__).parent / "prompt_s3_qa.md"
    return card_path.read_text(encoding="utf-8")

def extract_frontmatter_field(content: str, field: str) -> Optional[str]:
    m = re.search(rf"^{field}:\s*(.*?)(?:\n|$)", content, re.MULTILINE)
    return m.group(1).strip() if m else None



def run_qa_rest(model_id: str, prompt: str, retries: int = 3) -> Optional[dict]:
    """Calls the specified model via REST API, enforcing a JSON schema."""
    creds, project = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req) # Refresh to get a valid token

    # Use the model_id passed from the makefile
    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project}/locations/us-central1/publishers/google/models/{model_id}:generateContent"

    # The schema exactly as defined in the prompt card
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "batch_id": {"type": "STRING"},
                    "pass": {"type": "BOOLEAN"},
                    "issue_count": {"type": "INTEGER"},
                    "issues": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "type": {"type": "STRING"},
                                "detail": {"type": "STRING"}
                            },
                            "required": ["type", "detail"]
                        }
                    },
                    "approved_tags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "suggested_fix": {"type": "STRING"}
                },
                "required": ["batch_id", "pass", "issue_count", "issues", "approved_tags", "suggested_fix"]
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }

    for i in range(retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=90)
            response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429: # Rate limited
                wait = (2 ** (i + 2))
                print(f"    ⏳ [{model_id}]: Rate limit hit (attempt {i+1}/{retries}). Retrying in {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"    ❌ [{model_id}]: HTTP Error: {e.response.status_code} {e.response.text[:100]}")
                return None
        except Exception as e:
            print(f"    ❌ [{model_id}]: An unexpected error occurred: {str(e)[:120]}")
            return None

    print(f"    ❌ [{model_id}]: All {retries} attempts failed.")
    return None




def extract_json(raw: str) -> Optional[dict]:
    """Extract JSON from LLM response — may be wrapped in markdown fences."""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return None


def find_draft(batch_id: str, pending_dir: Path) -> Optional[Path]:
    """Find the draft file matching this batch by checking sourceIds in frontmatter."""
    # Convert batch_id from "YYYY_MM_batch_NNN" to "source.YYYY-MM-batch-NNN"
    target_source_id = f"source.{batch_id.replace('_', '-')}"

    for f in pending_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            source_ids_str = extract_frontmatter_field(content, "sourceIds")
            if source_ids_str:
                source_ids_raw = source_ids_str.strip().strip('[]') # Remove outer brackets
                source_ids = [s.strip().strip('"') for s in source_ids_raw.split(',') if s.strip()]
                if target_source_id in source_ids:
                    return f
        except Exception as e:
            # Print a warning but don't stop the pipeline for a single file error
            print(f"    ⚠️ Error reading or parsing {f.name}: {e}")
            continue
    return None


def qa_batch(trace_file: Path, pending_dir: Path, args) -> dict:
    trace    = json.loads(trace_file.read_text(encoding="utf-8"))
    batch_id = trace.get("batch_id", trace_file.stem.replace("trace_", ""))

    draft_file = find_draft(batch_id, pending_dir)
    if not draft_file:
        return {"batch_id": batch_id, "pass": False, "issue_count": 1,
                "issues": [{"type": "missing", "detail": "no draft found in promoted-pending"}],
                "approved_tags": [], "suggested_fix": "re-run stage 2"}

    draft    = draft_file.read_text(encoding="utf-8")
    card     = load_prompt_card()
    prompt   = (f"{card}\n\n## DRAFT\n\n{draft}\n\n"
                f"## SOURCE BATCH\n\n{json.dumps(trace, indent=2, ensure_ascii=False)}")

    print(f"    🔍 {args.qa_model[:45]}", end=" ", flush=True)
    # The new function returns a dict directly, or None
    result = run_qa_rest(args.qa_model, prompt)

    if result:
        # The candidates are in a list, and the content is nested.
        try:
            # The actual JSON payload is nested inside the response
            qa_data = result['candidates'][0]['content']['parts'][0]['text']
            # It might be a string that needs to be loaded, or already a dict
            if isinstance(qa_data, str):
                qa_data = json.loads(qa_data)

            qa_data["batch_id"] = batch_id # Ensure batch_id is present
            icon = "✅" if qa_data.get("pass") else "❌"
            print(f"→ {icon} issues={qa_data.get('issue_count', '?')}")
            return qa_data
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"→ ⚠️ corruption, model returned unexpected structure: {e}")

    return {"batch_id": batch_id, "pass": False, "issue_count": 1,
            "issues": [{"type": "qa_error", "detail": "model failed to return valid JSON"}],
            "approved_tags": [], "suggested_fix": "retry"}


def main():
    parser = argparse.ArgumentParser(description="Stage 3 QA Validator v6.0")
    parser.add_argument("--month",       required=True)
    parser.add_argument("--traces-dir",  default=str(TRACES_DIR))
    parser.add_argument("--pending-dir", default=str(PENDING_DIR))
    parser.add_argument("--qa-model",    default="gemini-2.5-flash")
    parser.add_argument("--batch-id",    default=None, help="Run for a single batch ID")
    args = parser.parse_args()

    traces_dir  = Path(args.traces_dir)
    pending_dir = Path(args.pending_dir)
    month_key   = args.month.replace("-", "_")
    if args.batch_id:
        trace_files = [traces_dir / f"trace_{args.batch_id}.json"]
    else:
        trace_files = sorted(traces_dir.glob(f"trace_{month_key}_batch_*.json"))

    if not trace_files:
        print(f"❌ No trace files for {args.month}")
        sys.exit(1)

    print(f"🔍 Stage 3 QA Validator v6.0 — {args.month} ({len(trace_files)} batches)\n")

    passed = failed = 0

    for tf in trace_files:
        batch_id = tf.stem.replace("trace_", "")
        print(f"⏳ {batch_id}")
        result = qa_batch(tf, pending_dir, args)

        # Write QA result back into trace
        trace = json.loads(tf.read_text(encoding="utf-8"))
        trace["qa_result"]  = result
        trace["qa_ts"]      = datetime.now(timezone.utc).isoformat()
        trace.setdefault("retry_count", 0)
        tf.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")

        if result.get("pass"):
            passed += 1
            log_event(batch_id, "qa", "SUCCESS", {"issue_count": 0})
        else:
            failed += 1
            log_event(batch_id, "qa", "FAIL", {"issue_count": result.get("issue_count", 0), "issues": result.get("issues", [])})

    print(f"\n📊 Stage 3 complete: ✅ {passed} passed  ❌ {failed} failed")
    print(f"   Next: make enforce MONTH={args.month}")


if __name__ == "__main__":
    main()
