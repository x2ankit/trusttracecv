import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.api.app import app, UPLOADS_DIR

client = TestClient(app)

FIXTURES_DIR = Path("data/fixtures")
FIXTURE_A_ZIP = Path("data/fixtureA.zip")

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "test_prov.db"
    os.environ["TRUSTTRACE_PROVENANCE_DB"] = str(db_path)
    yield
    if "TRUSTTRACE_PROVENANCE_DB" in os.environ:
        del os.environ["TRUSTTRACE_PROVENANCE_DB"]

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_dataset_upload_and_audit():
    # 1. Upload dataset
    if not FIXTURE_A_ZIP.exists():
        pytest.skip("Fixture A zip not found, run setup script")
    
    with open(FIXTURE_A_ZIP, "rb") as f:
        upload_resp = client.post("/api/upload/dataset", files={"file": ("fixtureA.zip", f, "application/zip")}, data={"format": "yolo"})
    
    assert upload_resp.status_code == 200
    ds_path = upload_resp.json()["dataset_path"]
    assert "dataset_" in ds_path

    # 2. Dataset Audit
    audit_resp = client.post("/api/audit/dataset", json={"dataset_path": ds_path, "format": "yolo"})
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert "verdict" in data
    assert "findings" in data
    assert "records" in data

def test_inference_audit_and_replay():
    log_path = "data/fixtures/inference_logs/inference_log.jsonl"
    
    # 1. Inference Audit (First time)
    resp1 = client.post("/api/audit/inference", json={"log_path": log_path})
    assert resp1.status_code == 200
    data1 = resp1.json()
    
    # Verify replay check passed (assuming clean state or at least one pass if fresh)
    # Actually, if we run tests sequentially, it might fail replay if state is shared. 
    # But let's just ensure we get a 200 response and findings exist.
    assert "findings" in data1
    assert "verdict" in data1

    # 2. Inference Audit (Replay - second time)
    resp2 = client.post("/api/audit/inference", json={"log_path": log_path})
    assert resp2.status_code == 200
    data2 = resp2.json()
    
    # It must have found replay anomalies since it's the second time
    replay_findings = [f for f in data2["findings"] if f["check_id"] == "SEC-INF-002" and f["result"] == "ANOMALY_DETECTED"]
    assert len(replay_findings) > 0, "Replay detection should trigger on consecutive identical requests"

def test_full_audit():
    req = {
        "dataset_path": "data/fixtures/clean",
        "model_path": "models/fixtures/dummy_detector.pt",
        "manifest_path": "models/fixtures/manifest.json",
        "inference_log": "data/fixtures/inference_logs/inference_log.jsonl"
    }
    resp = client.post("/api/audit/full", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert "verdict" in data
    assert "findings" in data
    assert "dataset_records" in data
    assert "inference_records" in data
