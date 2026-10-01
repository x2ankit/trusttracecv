# Validation Plan

The TRUSTTRACE CV validation strategy guarantees deterministic assurance of the platform's security checks. Testing is exclusively executed offline using generated synthetic fixtures to avoid uncontrolled variables or reliance on external downloads.

## Test Suite Execution
```bash
conda activate mldl
python -m pytest tests/ -v
python scripts/demo_behavior.py
```

## Validated Scenarios

### 1. Dataset Integrity (7 Scenarios)
- **Valid YOLO/COCO:** Verifies correct parsing and dimension boundaries.
- **OOB Bounding Boxes:** Verifies YOLO coordinates > 1.0 or COCO coordinates outside image dims trigger `FAIL`.
- **Exact Duplicates:** Confirms SHA-256 duplicate clusters are caught based on threshold.
- **Missing Images:** Validates missing reference files yield `FAIL`.
- **Label Flipping:** Verifies candidate class distributions against ground truth references.
- **Distribution Shift (Data Poisoning):** Verifies anomalous RGB pixel distributions are caught using Z-scores, yielding `STATISTICAL_SHIFT`.
- **Trigger Patterns (Entropy):** Verifies zero-entropy patches on noisy backgrounds trigger an anomaly flag.

### 2. Model Integrity & Behavioral Fingerprinting (8 Scenarios)
- **Manifest Matching:** Ensures an unaltered model perfectly aligns with its declared SHA-256.
- **Asymmetric Signature Verification (Cosign / RSA):** Validates offline cryptographic signature verification of the manifest.
- **Substitution Detection:** Modifying one byte in the model artifact correctly triggers `ANOMALY_DETECTED`.
- **Format Structure:** Confirms valid `.pt` and `.onnx` files successfully load structurally.
- **Behavioral Fingerprinting:** Analyzes predictions and internal white-box PyTorch activations directly via isolated runtime hooks.
- **Controlled Transformations:** Confirms robust behavioral consistency across image resizes, brightness, contrast, noise, and JPEG.
- **Trigger Probing:** Re-evaluates clean vs injected synthetic patches deterministically using a real prediction loop.

### 3. Inference Provenance (4 Scenarios)
- **Canonical Serialization & Hash:** Ensures dictionary key ordering does not alter payload hash identity.
- **HMAC Signatures:** Confirms valid secrets successfully verify the payload, and flipped bits in the log trigger `FAIL`.
- **Replay Detection:** Confirms identical transaction IDs appearing multiple times correctly trigger `ANOMALY_DETECTED`.
- **In-toto Chain Verification:** Cryptographically validates log chains for sequence correctness.

### 4. CV Performance
- **Metrics Validation:** Validates True Positives, False Positives, False Negatives.
- **Proper AP Calculation:** Validates properly sorted 11-point interpolated Precision-Recall area integration.

### 5. UI Visual Verification
- **Bounding Box Rendering (YOLO/COCO):** Evaluators can verify bounding box correctness manually:
  1. Open the UI at `http://127.0.0.1:8000/`.
  2. Upload `testcoco128.zip` using the 'YOLO' format selection.
  3. Wait for the audit to finish. 
  4. View the images in the Dataset Audit results page by clicking the thumbnails on the left side.
  5. The bounding boxes will overlay the image perfectly. Hover over the boxes to see class tooltips. Verify that coordinate scales handle image aspect ratios correctly without stretching or misaligning.
  6. The dataset hash will be populated in the Summary Card.
  7. **Mathematical Trace Verification**: 
      - In the "Dataset File (.zip)" audit, scroll down to the "Object Table". Click the "Trace" button on any annotation to view the raw coordinate math conversion bounds (e.g. `0 <= x_center <= 1`) exactly as executed.
      - In the "Findings" table, click "View Details" on a statistical outlier (e.g., `SEC-DS-004`) to expand the Mathematical Execution Trace drawer, displaying the real z-score evaluation logic (`|z_score| > 3.0`) and actual distribution metrics evaluated.
      - Switch to the "Model Integrity" tab and run the audit. Click on a finding to expose cryptographic trace execution (e.g., deterministic SHA-256 comparison and signature validation logic).

## Status
- **Coverage:** 100% of defined modules
- **Count:** 90/90 tests passing (Pytest)
