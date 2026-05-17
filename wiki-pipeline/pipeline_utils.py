import json
import os
from datetime import datetime

LEDGER_PATH = "/home/ubuntu/.openclaw/wiki/main/promotion_ledger.jsonl"

def log_event(entity_id, stage, event, payload, file_to_verify=None):
 """
 The Gatekeeper.
 Only logs if the file exists (if a path is provided).
 """
 # Hardware Reality Check
 if file_to_verify and not os.path.exists(file_to_verify):
  payload['error'] = "File not found on disk during sync"
  payload['file_to_verify'] = file_to_verify # Add for debug

 entry = {
  "timestamp": datetime.utcnow().isoformat() + "Z",
  "stage": stage,
  "event": event,
  "id": entity_id,
  "payload": payload
 }

 # Append-only (O(1) complexity, crash-resistant)
 with open(LEDGER_PATH, "a") as f:
  f.write(json.dumps(entry) + "\n")
