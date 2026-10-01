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

## Status
- **Coverage:** 100% of defined modules
- **Count:** 88/88 tests passing (Pytest)
