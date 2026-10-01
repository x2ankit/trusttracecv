"""
tests/test_inference.py

Reproducible tests for inference verifier (tamper, replay, backdoor indicator).
"""

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.inference.verifier import (
    record_inference,
    verify_inference_record,
    check_inference_replay,
    check_backdoor_behaviour,
    save_inference_log,
    load_inference_log,
)

FIXTURES_INF = ROOT / "data" / "fixtures" / "inference_logs"
_SECRET = b"test-secret-key"

# ---------------------------------------------------------------------------
# record_inference tests
# ---------------------------------------------------------------------------

class TestRecordInference:
    def test_record_has_required_fields(self):
        rec = record_inference("img1", "model_abc", [{"class_id": 0, "score": 0.9}], secret=_SECRET)
        for field in ("record_id", "timestamp", "image_id", "model_id", "predictions",
                      "payload_hash", "hmac_sig"):
            assert field in rec

    def test_payload_hash_length(self):
        rec = record_inference("img1", "model_abc", [], secret=_SECRET)
        assert len(rec["payload_hash"]) == 64

    def test_hmac_length(self):
        rec = record_inference("img1", "model_abc", [], secret=_SECRET)
        assert len(rec["hmac_sig"]) == 64

    def test_different_images_different_hash(self):
        r1 = record_inference("img1", "model_abc", [{"class_id": 0, "score": 0.9}], secret=_SECRET)
        r2 = record_inference("img2", "model_abc", [{"class_id": 1, "score": 0.7}], secret=_SECRET)
        assert r1["payload_hash"] != r2["payload_hash"]


# ---------------------------------------------------------------------------
# verify_inference_record tests
# ---------------------------------------------------------------------------

class TestVerifyInferenceRecord:
    def test_valid_record_passes(self):
        rec = record_inference("img1", "mdl", [{"class_id": 0, "score": 0.8}], secret=_SECRET)
        finding = verify_inference_record(rec, secret=_SECRET)
        assert finding["result"] == "PASS"
        assert finding["evidence"]["hash_match"] is True
        assert finding["evidence"]["hmac_valid"] is True

    def test_tampered_prediction_fails(self):
        rec = record_inference("img1", "mdl", [{"class_id": 0, "score": 0.8}], secret=_SECRET)
        rec["predictions"][0]["score"] = 0.999  # tamper
        finding = verify_inference_record(rec, secret=_SECRET)
        assert finding["result"] == "ANOMALY_DETECTED"

    def test_wrong_key_fails(self):
        rec = record_inference("img1", "mdl", [], secret=_SECRET)
        finding = verify_inference_record(rec, secret=b"wrong-key")
        assert finding["result"] == "ANOMALY_DETECTED"

    def test_tampered_image_id_fails(self):
        rec = record_inference("img1", "mdl", [], secret=_SECRET)
        rec["image_id"] = "img_evil"
        finding = verify_inference_record(rec, secret=_SECRET)
        assert finding["result"] == "ANOMALY_DETECTED"

    def test_check_id(self):
        rec = record_inference("img1", "mdl", [], secret=_SECRET)
        finding = verify_inference_record(rec, secret=_SECRET)
        assert finding["check_id"] == "SEC-INF-001"


# ---------------------------------------------------------------------------
# check_inference_replay tests
# ---------------------------------------------------------------------------

class TestReplayDetection:
    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        db_path = tmp_path / "test_prov.db"
        os.environ["TRUSTTRACE_PROVENANCE_DB"] = str(db_path)
        yield
        if "TRUSTTRACE_PROVENANCE_DB" in os.environ:
            del os.environ["TRUSTTRACE_PROVENANCE_DB"]

    def test_first_record_no_replay(self):
        rec = record_inference("img1", "mdl", [], secret=_SECRET)
        finding = check_inference_replay(rec)
        assert finding["result"] == "PASS"

    def test_second_occurrence_is_replay(self):
        rec = record_inference("img1", "mdl", [], secret=_SECRET)
        # Call once to insert
        check_inference_replay(rec)
        # Call again with identical record
        finding = check_inference_replay(rec)
        assert finding["result"] == "ANOMALY_DETECTED"
        assert finding["severity"] == "HIGH"

    def test_check_id(self):
        rec = record_inference("img1", "mdl", [], secret=_SECRET)
        finding = check_inference_replay(rec)
        assert finding["check_id"] == "SEC-INF-002"


# ---------------------------------------------------------------------------
# check_backdoor_behaviour tests
# ---------------------------------------------------------------------------

class TestBackdoorBehaviourIndicator:
    def test_normal_confidence_passes(self):
        preds = [{"class_id": 0, "score": 0.87}]
        finding = check_backdoor_behaviour(preds, confidence_threshold=0.999)
        assert finding["result"] == "PASS"

    def test_extreme_confidence_flagged(self):
        preds = [{"class_id": 2, "score": 0.9999}]
        finding = check_backdoor_behaviour(preds, confidence_threshold=0.999)
        assert finding["result"] == "ANOMALY_DETECTED"
        assert finding["severity"] == "MEDIUM"
        assert finding["confidence"] == "LOW"

    def test_check_id(self):
        finding = check_backdoor_behaviour([], confidence_threshold=0.999)
        assert finding["check_id"] == "SEC-INF-003"

    def test_empty_predictions(self):
        finding = check_backdoor_behaviour([], confidence_threshold=0.999)
        assert finding["result"] == "PASS"


# ---------------------------------------------------------------------------
# Log save/load tests
# ---------------------------------------------------------------------------

class TestInferenceLog:
    def test_round_trip(self, tmp_path):
        recs = [
            record_inference(f"img{i}", "mdl", [{"class_id": i, "score": 0.9}], secret=_SECRET)
            for i in range(3)
        ]
        log_path = tmp_path / "test.jsonl"
        save_inference_log(recs, log_path)
        loaded = load_inference_log(log_path)
        assert len(loaded) == 3
        for orig, load in zip(recs, loaded):
            assert orig["record_id"] == load["record_id"]
            assert orig["payload_hash"] == load["payload_hash"]

    def test_empty_log(self, tmp_path):
        loaded = load_inference_log(tmp_path / "nonexistent.jsonl")
        assert loaded == []

    def test_fixture_log_integrity(self):
        log_path = FIXTURES_INF / "inference_log.jsonl"
        if not log_path.exists():
            pytest.skip("Inference fixture not generated")
        records = load_inference_log(log_path)
        assert len(records) == 5
        for rec in records:
            finding = verify_inference_record(rec)  # uses default secret
            assert finding["result"] == "PASS"
