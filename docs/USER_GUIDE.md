# User Guide

Welcome to TRUSTTRACE CV. This guide explains how to use the system to audit computer vision pipelines.

## 1. Web UI Dashboard

The easiest way to use TRUSTTRACE CV is via its Web Dashboard.
Start the server:
```bash
conda activate mldl
python run_server.py
```
Then navigate to `http://127.0.0.1:8000`.

### Dashboard Panels
- **Dataset Inspection:** Enter the path to your dataset (YOLO or COCO) to scan for label anomalies, duplicate flooding, and backdoor triggers.
- **Model Identity:** Enter the path to your `.pt` or `.onnx` model and its corresponding `manifest.json` to verify structural integrity and cryptographically confirm it hasn't been substituted.
- **Inference Verification:** Enter the path to your inference log (`.jsonl`) to cryptographically verify HMAC signatures and detect replay attacks or tamper events.
- **Assurance Report:** Execute a full end-to-end pipeline audit and generate a structured JSON report mapping all findings to severity and confidence levels.

## 2. Command Line Interface (CLI)

For integration into automated CI/CD pipelines, use the CLI.

**Audit a Dataset:**
```bash
python -m src.cli audit-dataset --dataset-dir data/fixtures/clean --format yolo
```

**Audit a Model:**
```bash
python -m src.cli audit-model --model-path models/fixtures/dummy_detector.pt --manifest models/fixtures/manifest.json
```

**Verify Inference Logs:**
```bash
python -m src.cli audit-inference --log-path data/fixtures/inference_logs/inference_log.jsonl
```

**Full Pipeline Assurance Report:**
```bash
python -m src.cli audit-all \
  --dataset-dir data/fixtures/clean \
  --model-path models/fixtures/dummy_detector.pt \
  --manifest models/fixtures/manifest.json \
  --inference-log data/fixtures/inference_logs/inference_log.jsonl
```

## 3. Interpreting Results

All findings output a standardized result:
- `PASS`: The artifact is cryptographically and statistically sound.
- `ANOMALY_DETECTED`: A statistical anomaly (like an out-of-distribution pixel set) or a duplicate cluster was found. Requires human analyst review.
- `FAIL`: A deterministic integrity violation occurred (e.g., hash mismatch, broken signature). The artifact is compromised.
- `NOT ASSESSED`: A check was skipped because the necessary metadata was unavailable (e.g., missing manifest).

*Always refer to the Confidence and Recommended Actions provided in the Assurance Report before making operational decisions.*
