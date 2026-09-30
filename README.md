# TRUSTTRACE CV

An offline-first, model-agnostic assurance system for computer vision training data, model artifacts, and inference records. Developed for SIH problem statement SIH26228.

## Overview

TRUSTTRACE CV provides reproducible, evidence-backed security checks covering:

- Dataset integrity: YOLO and COCO format inspection, duplicate flooding, label flipping, trigger pattern insertion, and OOD sample detection.
- Model integrity: SHA-256 identity verification, manifest-based substitution detection, structural validation for PyTorch, TorchScript, and ONNX artifacts.
- Inference provenance: HMAC-SHA256 signed records, tamper detection, replay detection, and backdoor-like behaviour indicators.
- Assurance reports: structured JSON reports with verdict, severity summary, confidence basis, recommended actions, and known limitations.
- Professional web UI: light-themed interface with dataset image grid, annotation overlay, findings tables, and full assurance report view.

## SIH26228 Requirement Mapping

| SIH Requirement | Source Module | Tests | Evidence |
| --- | --- | --- | --- |
| Dataset inspection (filename, resolution, labels, bounding boxes) | `src/dataset/inspector.py` | `tests/test_dataset.py` | Image grid in UI; records in reports |
| Suspicious data findings | `src/dataset/security_checks.py` | `tests/test_dataset.py` | SEC-DS-001 through SEC-DS-005 findings |
| Model identity and integrity checks | `src/models/integrity.py` | `tests/test_models.py` | SEC-MDL-001, SEC-MDL-002 findings |
| Inference record verification | `src/inference/verifier.py` | `tests/test_inference.py` | SEC-INF-001, SEC-INF-002, SEC-INF-003 |
| Evidence-backed assurance reports | `src/reporting/report_generator.py` | `tests/test_report.py` | JSON reports in `reports/` |
| Coverage and limitations | `src/reporting/report_generator.py` | `tests/test_report.py` | `COVERAGE` dict; `/api/coverage` endpoint |
| Professional light-themed UI | `src/ui/` | Manual / browser | Served at `http://localhost:8000` |
| CLI reproduction | `src/cli.py` | Manual | See CLI Usage below |

## Supported Threat Scenarios

| Check ID | Threat | Method | Confidence |
| --- | --- | --- | --- |
| SEC-DS-001 | Duplicate flooding | SHA-256 exact hash grouping | HIGH (deterministic) |
| SEC-DS-002 | Label flipping | Class ID comparison vs reference | HIGH (deterministic) |
| SEC-DS-003 | Trigger pattern insertion | Patch-level Shannon entropy | LOW (heuristic) |
| SEC-DS-004 | Data poisoning | Z-score on pixel statistics | LOW (statistical) |
| SEC-DS-005 | OOD insertion | Mahalanobis distance on pixel distribution | MEDIUM (statistical) |
| SEC-MDL-001 | Model substitution | SHA-256 vs reference manifest | HIGH (deterministic) |
| SEC-MDL-002 | Model structural validation | Format load check | HIGH (deterministic) |
| SEC-INF-001 | Inference tampering | HMAC-SHA256 signature verification | HIGH (deterministic) |
| SEC-INF-002 | Inference replay | Payload hash deduplication | HIGH (deterministic) |
| SEC-INF-003 | Backdoor-like behaviour | Confidence threshold indicator | LOW (heuristic) |

## Architecture

```
TRUSTTRACE CV
├── src/
│   ├── dataset/
│   │   ├── inspector.py          YOLO and COCO format inspection, OOD detection
│   │   └── security_checks.py    Duplicate, label-flip, trigger, poisoning checks
│   ├── models/
│   │   └── integrity.py          SHA-256, manifest, PyTorch/ONNX loading
│   ├── inference/
│   │   └── verifier.py           HMAC signing, tamper/replay detection
│   ├── reporting/
│   │   └── report_generator.py   Assurance report assembly, coverage statement
│   ├── api/
│   │   └── app.py                FastAPI backend
│   ├── ui/
│   │   ├── index.html            Light-themed web UI
│   │   ├── style.css
│   │   └── app.js
│   └── cli.py                    Command-line interface
├── tests/                        Reproducible pytest test suite
├── scripts/
│   └── generate_fixtures.py      Deterministic synthetic fixture generator
├── data/fixtures/                Synthetic test datasets (git-ignored)
├── models/fixtures/              Synthetic test models (git-ignored)
├── reports/                      Generated assurance reports (git-ignored)
└── run_server.py                 Server startup script
```

## Setup Instructions

**Requirements:** Windows or Linux, Conda, Python 3.12.

1. Clone or copy this repository.
2. Activate the environment:
   ```
   conda activate mldl
   ```
3. Install project dependencies (already present in mldl if set up per the brief):
   ```
   pip install -r requirements.txt
   ```
4. Generate synthetic test fixtures:
   ```
   python scripts/generate_fixtures.py
   ```
5. Start the web server:
   ```
   python run_server.py
   ```
6. Open a browser and navigate to `http://localhost:8000`.

The system is fully offline after dependencies are installed.

## CLI Usage

```
# Inspect a YOLO dataset
conda run -n mldl python -m src.cli audit-dataset --dataset-dir data/fixtures/clean

# Inspect a model artifact
conda run -n mldl python -m src.cli audit-model \
  --model-path models/fixtures/dummy_detector.pt \
  --manifest models/fixtures/manifest.json

# Verify an inference log
conda run -n mldl python -m src.cli audit-inference \
  --log-path data/fixtures/inference_logs/inference_log.jsonl

# Full pipeline audit
conda run -n mldl python -m src.cli audit-all \
  --dataset-dir data/fixtures/clean \
  --model-path models/fixtures/dummy_detector.pt \
  --manifest models/fixtures/manifest.json \
  --inference-log data/fixtures/inference_logs/inference_log.jsonl
```

## Running Tests

```
conda run -n mldl python -m pytest tests/ -v
```

Test results as of prototype: **77/77 PASSED**.

## Dataset and Model Provenance

All datasets and models used in the prototype are entirely synthetic, generated deterministically by `scripts/generate_fixtures.py` using seed 42. No external datasets or model weights are downloaded.

- Images: 100x100 RGB Gaussian-noise arrays, team-generated.
- Labels: YOLO format, team-generated.
- Model: 3-layer synthetic CNN, random weights, PyTorch, team-generated.
- No external citations, DOIs, or licenses apply to the fixtures.

Note: The ONNX export in the fixture generator currently fails on PyTorch 2.14 due to a breaking API change (`DiagnosticOptions` removal). This does not affect other checks. The `.onnx` file in the manifest was generated by a compatible version; the manifest integrity check will still work if the file is present.

## Assumptions and Known Limitations

- Statistical anomaly detection (Z-score, Mahalanobis, entropy) produces probabilistic signals; false positives and false negatives are expected.
- SHA-256 matching confirms file identity, NOT model safety.
- Trigger detection uses patch entropy as a heuristic and cannot detect sophisticated textured triggers.
- HMAC signature verification requires the original signing key.
- Replay detection can be evaded by modifying any non-critical record field.
- Universal backdoor detection via static analysis is not mathematically feasible and is not claimed.
- Near-duplicate image detection (perceptual hashing) is not implemented in this version.
