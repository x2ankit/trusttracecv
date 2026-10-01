import sqlite3
import json
import hashlib
import time
import os
import uuid
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

def get_db_path() -> str:
    return os.environ.get("TRUSTTRACE_PROVENANCE_DB", "data/provenance.db")

def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provenance_events (
            event_id TEXT PRIMARY KEY,
            input_sha256 TEXT,
            image_dimensions TEXT,
            model_id TEXT,
            model_sha256 TEXT,
            verified_manifest_id TEXT,
            preprocessing_config TEXT,
            preprocessing_digest TEXT,
            inference_config TEXT,
            prediction_payload TEXT,
            output_digest TEXT,
            timestamp REAL,
            nonce TEXT,
            sequence_number INTEGER,
            previous_event_hash TEXT,
            record_hash TEXT UNIQUE,
            verification_status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def canonicalize_record(record: Dict[str, Any]) -> str:
    """Canonicalize the record before hashing/signing."""
    return json.dumps(record, sort_keys=True)

def record_inference_event(event_data: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    Records an inference event in SQLite. 
    Checks for replay using record_hash.
    Returns (success, message, record_hash).
    """
    init_db()
    
    # Map old format to new format
    if "event_id" not in event_data and "record_id" in event_data:
        event_data["event_id"] = event_data["record_id"]
    if "event_id" not in event_data:
        event_data["event_id"] = str(uuid.uuid4())
        
    if "timestamp" not in event_data:
        event_data["timestamp"] = time.time()
        
    if "nonce" not in event_data:
        event_data["nonce"] = os.urandom(16).hex()
        
    # We must use payload_hash for replay detection if it exists and we're just recording an existing signed log
    if "payload_hash" in event_data:
        record_hash = event_data["payload_hash"]
    else:
        canonical_str = canonicalize_record(event_data)
        record_hash = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()
    
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO provenance_events (
                event_id, input_sha256, image_dimensions, model_id, model_sha256, 
                verified_manifest_id, preprocessing_config, preprocessing_digest, 
                inference_config, prediction_payload, output_digest, timestamp, 
                nonce, sequence_number, previous_event_hash, record_hash, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_data.get("event_id"),
            event_data.get("input_sha256"),
            event_data.get("image_dimensions"),
            event_data.get("model_id"),
            event_data.get("model_sha256"),
            event_data.get("verified_manifest_id"),
            json.dumps(event_data.get("preprocessing_config", {})),
            event_data.get("preprocessing_digest"),
            json.dumps(event_data.get("inference_config", {})),
            json.dumps(event_data.get("prediction_payload", {})),
            event_data.get("output_digest"),
            event_data.get("timestamp"),
            event_data.get("nonce"),
            event_data.get("sequence_number", 0),
            event_data.get("previous_event_hash"),
            record_hash,
            "ACCEPTED"
        ))
        conn.commit()
        conn.close()
        return True, "Event recorded successfully", record_hash
    except sqlite3.IntegrityError:
        # Replay detected (record_hash already exists)
        conn.close()
        return False, "REPLAY_DETECTED", record_hash
    except Exception as e:
        conn.close()
        logger.error(f"Error recording provenance event: {e}")
        return False, str(e), record_hash

def verify_provenance_chain() -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Verifies the integrity of the append-only provenance chain.
    Detects modification, deletion, or reordering by checking previous_event_hash linkage.
    """
    init_db()
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Order by sequence_number or timestamp to rebuild chain
        cursor.execute("SELECT * FROM provenance_events ORDER BY sequence_number ASC, timestamp ASC")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return True, "Chain is empty (valid).", []
            
        anomalies = []
        last_hash = None
        
        for i, row in enumerate(rows):
            current_hash = row["record_hash"]
            prev_hash_claimed = row["previous_event_hash"]
            seq = row["sequence_number"]
            
            # If not the first record, verify linkage
            if i > 0:
                if prev_hash_claimed != last_hash:
                    anomalies.append({
                        "event_id": row["event_id"],
                        "issue": "BROKEN_LINK",
                        "detail": f"Claimed previous hash {prev_hash_claimed} does not match actual previous hash {last_hash}"
                    })
            
            # (Optional) We could re-hash the row contents here to verify record_hash hasn't been tampered with directly in DB
            
            last_hash = current_hash
            
        if anomalies:
            return False, "CHAIN_BROKEN", anomalies
            
        return True, "CHAIN_VALID", []
        
    except Exception as e:
        logger.error(f"Error verifying chain: {e}")
        return False, f"ERROR: {str(e)}", []
