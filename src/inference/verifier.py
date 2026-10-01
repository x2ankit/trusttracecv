"""
src/inference/verifier.py

Inference record provenance and tamper verification.

Supported checks:
  - Replay detection: compares current inference output hash against a stored
    record to detect replay of stale results.
  - Inference output tampering: compares field-by-field a signed output against
    a re-derived expected output.
  - Inference log integrity: verifies HMAC-SHA256 signature of a log record,
    if the log was produced with the record_inference() function.
  - Backdoor-like behaviour indicator: flags inference results where the
    top-1 class probability is anomalously high (≥ threshold) compared to
    the rest of the distribution.

Limitation:
  - HMAC signing requires the original signing key. If the key is unavailable,
    tamper detection is NOT ASSESSED.
  - Replay detection matches hashes; it cannot distinguish a legitimate
    re-submission from an adversarial replay.
  - Backdoor-like behaviour detection is a heuristic signal.
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

import os
_ENV_SECRET = os.environ.get("TRUSTTRACE_CV_HMAC_SECRET")
if _ENV_SECRET:
    _DEFAULT_SECRET = _ENV_SECRET.encode("utf-8")
else:
    logger.warning("INSECURE DEVELOPMENT FALLBACK: Using hardcoded HMAC secret.")
    _DEFAULT_SECRET = b"TRUSTTRACE_CV_DEFAULT_HMAC_SECRET"

# ---------------------------------------------------------------------------
# Record & sign an inference result
# ---------------------------------------------------------------------------

def record_inference(
    image_id: str,
    model_id: str,
    predictions: List[Dict[str, Any]],
    input_sha256: str = "",
    image_dimensions: str = "",
    model_sha256: str = "",
    verified_manifest_id: str = "",
    preprocessing_config: Optional[Dict[str, Any]] = None,
    preprocessing_digest: str = "",
    inference_config: Optional[Dict[str, Any]] = None,
    output_digest: str = "",
    sequence_number: int = 0,
    previous_event_hash: str = "",
    secret: bytes = _DEFAULT_SECRET,
) -> Dict[str, Any]:
    """
    Create a signed inference record.
    """
    record = {
        "event_id": str(uuid.uuid4()),
        "record_id": str(uuid.uuid4()),  # Keep for backwards compat
        "timestamp": time.time(),
        "nonce": os.urandom(16).hex(),
        "image_id":  image_id,
        "input_sha256": input_sha256,
        "image_dimensions": image_dimensions,
        "model_id":  model_id,
        "model_sha256": model_sha256,
        "verified_manifest_id": verified_manifest_id,
        "preprocessing_config": preprocessing_config or {},
        "preprocessing_digest": preprocessing_digest,
        "inference_config": inference_config or {},
        "prediction_payload": predictions,
        "predictions": predictions, # Keep for backwards compat
        "output_digest": output_digest,
        "sequence_number": sequence_number,
        "previous_event_hash": previous_event_hash
    }
    payload_bytes = json.dumps(record, sort_keys=True).encode()
    payload_hash  = hashlib.sha256(payload_bytes).hexdigest()
    hmac_sig      = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

    record["payload_hash"] = payload_hash
    record["hmac_sig"]     = hmac_sig
    return record


def verify_inference_record(
    record: Dict[str, Any],
    secret: bytes = _DEFAULT_SECRET,
) -> Dict[str, Any]:
    """
    Verify the HMAC signature of an inference record produced by record_inference().

    Returns a finding dict.
    """
    stored_hash = record.get("payload_hash")
    stored_sig  = record.get("hmac_sig")

    # Re-derive payload (exclude hash and sig fields)
    payload_fields = {k: v for k, v in record.items()
                     if k not in ("payload_hash", "hmac_sig")}
    payload_bytes = json.dumps(payload_fields, sort_keys=True).encode()
    expected_hash = hashlib.sha256(payload_bytes).hexdigest()
    expected_sig  = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

    hash_ok = hmac.compare_digest(stored_hash or "", expected_hash)
    sig_ok  = hmac.compare_digest(stored_sig  or "", expected_sig)

    if hash_ok and sig_ok:
        result, severity, detail = "PASS", "INFO", "Payload hash and HMAC signature verified."
    elif not hash_ok:
        result, severity, detail = "ANOMALY_DETECTED", "CRITICAL", "Payload hash mismatch — record may have been tampered."
    else:
        result, severity, detail = "ANOMALY_DETECTED", "CRITICAL", "HMAC signature invalid — record may have been tampered or signed with a different key."

    return {
        "check_id": "SEC-INF-001",
        "name": "Inference Record Tamper Verification",
        "result": result,
        "severity": severity,
        "confidence": "HIGH",
        "evidence": {
            "record_id":     record.get("record_id"),
            "stored_hash":   stored_hash,
            "expected_hash": expected_hash,
            "hash_match":    hash_ok,
            "hmac_valid":    sig_ok,
        },
        "description": detail,
        "recommended_action": (
            "If tampering is detected, quarantine the record and re-run inference "
            "with a verified model on the original image. Audit the inference pipeline."
        ),
        "limitation": (
            "Verification requires the original signing key. "
            "If the key is rotated or unavailable, this check cannot be performed."
        ),
    }


# ---------------------------------------------------------------------------
# Replay detection
# ---------------------------------------------------------------------------

def check_inference_replay(
    incoming_record: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Detect if an inference record is a replay of a previously seen result using SQLite persistent store.
    """
    from src.inference.provenance import record_inference_event
    
    success, message, record_hash = record_inference_event(incoming_record)
    is_replay = (message == "REPLAY_DETECTED")

    return {
        "check_id": "SEC-INF-002",
        "name": "Inference Replay Detection",
        "result": "ANOMALY_DETECTED" if is_replay else "PASS",
        "severity": "HIGH" if is_replay else "INFO",
        "confidence": "HIGH",
        "evidence": {
            "record_id":    incoming_record.get("record_id") or incoming_record.get("event_id"),
            "payload_hash": incoming_record.get("payload_hash"),
            "record_hash":  record_hash,
            "is_replay":    is_replay,
        },
        "description": (
            "Replayed inference record detected — hash matches a previously seen result."
            if is_replay else "No replay detected. Event recorded in provenance."
        ),
        "recommended_action": (
            "Reject replayed records. Investigate source of duplicate submissions."
            if is_replay else "No action required."
        ),
        "limitation": (
            "Replay detection is based on payload equality via record_hash."
        ),
    }


# ---------------------------------------------------------------------------
# Backdoor-like behaviour indicator
# ---------------------------------------------------------------------------

def check_backdoor_behaviour(
    predictions: List[Dict[str, Any]],
    confidence_threshold: float = 0.999,
) -> Dict[str, Any]:
    """
    Flag inference results where a single class has anomalously high confidence,
    which may indicate trigger-activated backdoor-like behaviour.

    Args:
        predictions: list of {'class_id': int, 'score': float}
        confidence_threshold: score above which to flag

    Returns:
        Finding dict. Confidence of this heuristic is LOW.
    """
    flagged = [p for p in predictions if p.get("score", 0.0) >= confidence_threshold]

    result   = "ANOMALY_DETECTED" if flagged else "PASS"
    severity = "MEDIUM" if flagged else "INFO"

    return {
        "check_id": "SEC-INF-003",
        "name": "Backdoor-like Behaviour Indicator",
        "result": result,
        "severity": severity,
        "confidence": "LOW",
        "evidence": {
            "predictions": predictions,
            "flagged_predictions": flagged,
            "confidence_threshold": confidence_threshold,
        },
        "description": (
            f"{len(flagged)} prediction(s) have score ≥ {confidence_threshold}. "
            "Extremely high confidence may indicate trigger-activated behaviour."
            if flagged else
            "No anomalously high-confidence predictions detected."
        ),
        "recommended_action": (
            "Investigate whether the input contains a potential trigger pattern. "
            "Cross-reference with trigger pattern check (SEC-DS-003)."
            if flagged else "No action required."
        ),
        "limitation": (
            "High model confidence on a clean, easy image is also expected behaviour. "
            "This check cannot distinguish legitimate high confidence from triggered behaviour. "
            "A positive result requires corroboration from other checks."
        ),
    }


# ---------------------------------------------------------------------------
# Log persistence helpers
# ---------------------------------------------------------------------------

def save_inference_log(records: List[Dict[str, Any]], log_path: Path) -> None:
    """Append inference records to a JSONL audit log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def load_inference_log(log_path: Path) -> List[Dict[str, Any]]:
    """Load all inference records from a JSONL audit log."""
    if not log_path.exists():
        return []
    records = []
    with open(log_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
