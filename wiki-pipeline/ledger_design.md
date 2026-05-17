# Design Document: Promotion Ledger

## 1. Overview

This document outlines the design for a promotion ledger for the OpenClaw Wiki Pipeline. The ledger will act as a persistent, historical record of every batch as it moves through the pipeline stages.

**Core Requirements:**
- Provide a complete, auditable history of every batch from creation to promotion.
- Serve as a recovery and state-tracking mechanism.
- Solve the problem of verifying stage completion for all batches.
- Fit the "Memory Experiment" objective by providing a durable, high-fidelity memory for the pipeline itself.

## 2. Format & Location

- **Filename:** `promotion_ledger.jsonl`
- **Location:** `/home/ubuntu/.openclaw/wiki/main/` (alongside `failed_batches_dlq.jsonl`)
- **Format:** **JSON Lines (JSONL)**. Each line will be a self-contained, valid JSON object representing a single pipeline event.

## 3. Log Entry Schema (Write-Ahead Log)

Each JSON object in the log will adhere to the following schema:

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SS.ssssssZ",
  "batch_id": "YYYY_MM_batch_NNN",
  "stage": "string (e.g., 'chunk', 'write', 'qa', 'promote')",
  "event": "string (e.g., 'INIT', 'SUCCESS', 'FAIL')",
  "payload": {
    // Stage-specific data
  }
}
```

## 4. Per-Stage Implementation

The ledger will be updated by each pipeline script as a Write-Ahead Log.

### Stage 1: `stage_1_chunker.py`
- **Event:** After creating a batch of trace files, the chunker will append one event to the ledger for each new `batch_id`.
- **Log Entry:**
  ```json
  {
    "timestamp": "...",
    "batch_id": "2026_01_batch_000",
    "stage": "chunk",
    "event": "INIT",
    "payload": {
      "trace_file_path": "/path/to/trace_2026_01_batch_000.json"
    }
  }
  ```

### Stage 2: `stage_2_writer.py`
- **Event:** Upon successful creation of a draft markdown file.
- **Log Entry:**
  ```json
  {
    "timestamp": "...",
    "batch_id": "2026_01_batch_000",
    "stage": "write",
    "event": "SUCCESS",
    "payload": {
      "draft_path": "/path/to/promoted-pending/draft-file.md",
      "model_used": "gemini-2.5-flash"
    }
  }
  ```
- If the stage fails for a batch after all retries, it will log a `FAIL` event.

### Stage 3: `stage_3_qa.py`
- **Event:** After a batch is successfully QA'd.
- **Log Entry (`pass: true`):**
  ```json
  {
    "timestamp": "...",
    "batch_id": "2026_01_batch_000",
    "stage": "qa",
    "event": "SUCCESS",
    "payload": {
      "issue_count": 0
    }
  }
  ```
- **Log Entry (`pass: false`):**
  ```json
  {
    "timestamp": "...",
    "batch_id": "2026_01_batch_000",
    "stage": "qa",
    "event": "FAIL",
    "payload": {
      "issue_count": 2,
      "issues": [
        {"type": "missing_section", "detail": "..."},
        {"type": "incorrect_fact", "detail": "..."}
      ]
    }
  }
  ```

### Stage 4: `promote_wiki_pages.py`
- **Event:** When a draft is successfully promoted into the main wiki structure.
- **Log Entry:**
  ```json
  {
    "timestamp": "...",
    "batch_id": "2026_01_batch_000",
    "stage": "promote",
    "event": "SUCCESS",
    "payload": {
      "final_path": "/path/to/wiki/main/entities/final-page.md"
    }
  }
  ```
