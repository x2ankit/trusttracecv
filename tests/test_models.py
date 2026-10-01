"""
tests/test_models.py

Reproducible tests for model integrity checks.
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

from src.models.integrity import (
    sha256_file,
    build_manifest,
    save_manifest,
    load_manifest,
    inspect_model,
    check_model_substitution,
)

FIXTURES_MODELS = ROOT / "models" / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_dummy_pt(path: Path) -> Path:
    """Write a minimal PyTorch state dict to path without requiring GPU."""
    import torch
    import torch.nn as nn
    torch.manual_seed(0)
    m = nn.Linear(4, 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(m.state_dict(), str(path))
    return path


# ---------------------------------------------------------------------------
# SHA-256 tests
# ---------------------------------------------------------------------------

class TestSha256:
    def test_deterministic(self, tmp_path):
        p = tmp_path / "file.bin"
        p.write_bytes(b"hello trusttrace")
        assert sha256_file(p) == sha256_file(p)

    def test_different_content_different_hash(self, tmp_path):
        p1 = tmp_path / "a.bin"; p1.write_bytes(b"AAA")
        p2 = tmp_path / "b.bin"; p2.write_bytes(b"BBB")
        assert sha256_file(p1) != sha256_file(p2)

    def test_hash_length(self, tmp_path):
        p = tmp_path / "f.bin"; p.write_bytes(b"data")
        assert len(sha256_file(p)) == 64


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------

class TestManifest:
    def test_round_trip(self, tmp_path):
        p = tmp_path / "m.bin"; p.write_bytes(b"model_weights")
        manifest = build_manifest([p])
        assert p.name in manifest
        manifest_path = tmp_path / "manifest.json"
        save_manifest(manifest, manifest_path)
        loaded = load_manifest(manifest_path)
        assert "hmac_sig" in loaded
        from src.models.integrity import verify_manifest
        is_valid, _ = verify_manifest(loaded)
        assert is_valid is True
        assert loaded["m.bin"] == manifest["m.bin"]

    def test_missing_file_excluded(self, tmp_path):
        real = tmp_path / "real.bin"; real.write_bytes(b"x")
        ghost = tmp_path / "ghost.bin"
        manifest = build_manifest([real, ghost])
        assert "ghost.bin" not in manifest
        assert "real.bin" in manifest


# ---------------------------------------------------------------------------
# Model inspection tests
# ---------------------------------------------------------------------------

class TestInspectModel:
    def test_missing_file(self, tmp_path):
        rec = inspect_model(tmp_path / "nonexistent.pt")
        assert rec["checks"]["file_exists"]["result"] == "FAIL"

    def test_pytorch_state_dict(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        rec = inspect_model(p)
        assert rec["checks"]["file_exists"]["result"] == "PASS"
        assert rec["checks"]["loadable"]["result"] == "PASS"
        assert rec["format"] == "PyTorch"
        assert len(rec["sha256"]) == 64

    def test_hash_match_pass(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        sha = sha256_file(p)
        manifest = {"model.pt": sha}
        rec = inspect_model(p, reference_manifest=manifest)
        assert rec["checks"]["hash_match"]["result"] == "PASS"

    def test_hash_mismatch_fail(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        manifest = {"model.pt": "aaaa" + "0" * 60}  # wrong hash
        rec = inspect_model(p, reference_manifest=manifest)
        assert rec["checks"]["hash_match"]["result"] == "FAIL"

    def test_no_manifest_not_assessed(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        rec = inspect_model(p, reference_manifest=None)
        assert rec["checks"]["hash_match"]["result"] == "NOT ASSESSED"

    def test_unknown_format(self, tmp_path):
        p = tmp_path / "weights.bin"; p.write_bytes(b"binary data")
        rec = inspect_model(p)
        assert rec["checks"]["loadable"]["result"] == "NOT ASSESSED"


# ---------------------------------------------------------------------------
# Model substitution check tests
# ---------------------------------------------------------------------------

class TestModelSubstitution:
    def test_pass(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        sha = sha256_file(p)
        finding = check_model_substitution(p, {"model.pt": sha})
        assert finding["result"] == "PASS"
        assert finding["severity"] == "INFO"

    def test_mismatch(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        finding = check_model_substitution(p, {"model.pt": "dead" + "b" * 60})
        assert finding["result"] == "ANOMALY_DETECTED"
        assert finding["severity"] == "CRITICAL"

    def test_missing_model(self, tmp_path):
        finding = check_model_substitution(tmp_path / "gone.pt", {"gone.pt": "abc"})
        assert finding["result"] == "FAIL"
        assert finding["severity"] == "CRITICAL"

    def test_not_in_manifest(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        finding = check_model_substitution(p, {})  # empty manifest
        assert finding["result"] == "NOT ASSESSED"

    def test_check_id(self, tmp_path):
        p = _write_dummy_pt(tmp_path / "model.pt")
        sha = sha256_file(p)
        finding = check_model_substitution(p, {"model.pt": sha})
        assert finding["check_id"] == "SEC-MDL-001"


# ---------------------------------------------------------------------------
# Fixture-based tests
# ---------------------------------------------------------------------------

class TestModelFixtures:
    def test_fixture_model_loadable(self):
        pt_path = FIXTURES_MODELS / "dummy_detector.pt"
        if not pt_path.exists():
            pytest.skip("Model fixture not generated; run scripts/generate_fixtures.py")
        rec = inspect_model(pt_path)
        assert rec["checks"]["loadable"]["result"] == "PASS"

    def test_fixture_manifest_integrity(self):
        manifest_path = FIXTURES_MODELS / "manifest.json"
        pt_path       = FIXTURES_MODELS / "dummy_detector.pt"
        if not manifest_path.exists() or not pt_path.exists():
            pytest.skip("Model fixtures not generated")
        manifest = load_manifest(manifest_path)
        finding  = check_model_substitution(pt_path, manifest)
        assert finding["result"] == "PASS"

    def test_torchscript_fixture(self):
        ts_path = FIXTURES_MODELS / "dummy_detector_ts.pt"
        if not ts_path.exists():
            pytest.skip("TorchScript fixture not generated")
        rec = inspect_model(ts_path)
        assert rec["checks"]["loadable"]["result"] == "PASS"
        assert rec["metadata"].get("torchscript") is True
