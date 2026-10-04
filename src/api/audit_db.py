import sqlite3
import json
import os
import time
import hashlib
from typing import Dict, Any, List
from pathlib import Path

def get_db_path() -> Path:
    """Return the audit events DB path, configurable via TRUSTTRACE_AUDIT_DB env var."""
    return Path(os.environ.get("TRUSTTRACE_AUDIT_DB", "audit_events.sqlite"))

# Module-level alias for backwards compatibility (resolved at import time)
DB_PATH = get_db_path()

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            timestamp_utc REAL NOT NULL,
            stage TEXT NOT NULL,
            operation TEXT NOT NULL,
            inputs TEXT NOT NULL,
            formula TEXT NOT NULL,
            intermediate_values TEXT NOT NULL,
            result TEXT NOT NULL,
            thresholds TEXT NOT NULL,
            decision TEXT NOT NULL,
            evidence_id TEXT NOT NULL,
            duration_ms REAL NOT NULL,
            status TEXT NOT NULL,
            error_details TEXT NOT NULL,
            event_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def _canonicalize_event(event: Dict[str, Any]) -> bytes:
    # Stable ordering and encoding
    ordered = {k: event.get(k, "") for k in sorted(event.keys()) if k != "event_hash"}
    return json.dumps(ordered, separators=(',', ':'), sort_keys=True).encode('utf-8')

def get_last_hash(audit_id: str) -> str:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT event_hash FROM audit_events 
        WHERE audit_id = ? 
        ORDER BY sequence_number DESC LIMIT 1
    ''', (audit_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"

def get_next_sequence(audit_id: str) -> int:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT MAX(sequence_number) FROM audit_events WHERE audit_id = ?
    ''', (audit_id,))
    row = cursor.fetchone()
    conn.close()
    return (row[0] or 0) + 1

def log_event(audit_id: str, stage: str, operation: str, inputs: Dict[str, Any], 
              formula: str, intermediate: Dict[str, Any], result: str, thresholds: str, 
              decision: str, evidence_id: str, duration_ms: float, status: str, 
              error_details: str = "") -> Dict[str, Any]:
    init_db()
    
    seq = get_next_sequence(audit_id)
    timestamp = time.time()
    
    event = {
        "audit_id": audit_id,
        "sequence_number": seq,
        "timestamp_utc": timestamp,
        "stage": stage,
        "operation": operation,
        "inputs": json.dumps(inputs),
        "formula": formula,
        "intermediate_values": json.dumps(intermediate),
        "result": result,
        "thresholds": thresholds,
        "decision": decision,
        "evidence_id": evidence_id,
        "duration_ms": duration_ms,
        "status": status,
        "error_details": error_details
    }
    
    last_hash = get_last_hash(audit_id)
    canonical = _canonicalize_event(event)
    combined = canonical + last_hash.encode('utf-8')
    event_hash = hashlib.sha256(combined).hexdigest()
    event["event_hash"] = event_hash
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_events (
            audit_id, sequence_number, timestamp_utc, stage, operation, inputs, 
            formula, intermediate_values, result, thresholds, decision, 
            evidence_id, duration_ms, status, error_details, event_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event["audit_id"], event["sequence_number"], event["timestamp_utc"], 
        event["stage"], event["operation"], event["inputs"], event["formula"], 
        event["intermediate_values"], event["result"], event["thresholds"], 
        event["decision"], event["evidence_id"], event["duration_ms"], 
        event["status"], event["error_details"], event["event_hash"]
    ))
    conn.commit()
    conn.close()
    
    return event

def get_events(audit_id: str) -> List[Dict[str, Any]]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM audit_events WHERE audit_id = ? ORDER BY sequence_number ASC
    ''', (audit_id,))
    rows = cursor.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        raw = dict(row)
        # Parse JSON fields
        inputs_parsed = {}
        intermediate_parsed = {}
        try:
            inputs_parsed = json.loads(raw.get("inputs", "{}"))
        except Exception:
            pass
        try:
            intermediate_parsed = json.loads(raw.get("intermediate_values", "{}"))
        except Exception:
            pass
        
        # Map DB column names → frontend-expected field names
        events.append({
            "event_id":         raw["id"],
            "audit_id":         raw["audit_id"],
            "sequence":         raw["sequence_number"],
            "timestamp":        raw["timestamp_utc"],
            "check_name":       raw["stage"],
            "observation_type": raw["operation"],
            "inputs":           inputs_parsed,
            "formula":          raw["formula"],
            "intermediate":     intermediate_parsed,
            "result_str":       raw["result"],
            "threshold":        raw["thresholds"],
            "decision":         raw["decision"],
            "evidence_id":      raw["evidence_id"],
            "duration_ms":      raw["duration_ms"],
            "status_code":      raw["status"],
            "error_details":    raw["error_details"],
            "event_hash":       raw["event_hash"],
        })
    return events
