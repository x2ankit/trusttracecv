# Validation Plan

The TRUSTTRACE CV validation strategy guarantees deterministic assurance of the platform's security checks. Testing is exclusively executed offline using generated synthetic fixtures to avoid uncontrolled variables or reliance on external downloads.

## Test Suite Execution
```bash
conda activate mldl
python -m pytest tests/ -v
```

## Validated Scenarios

### 1. Dataset Integrity (7 Scenarios)
- **Valid YOLO/COCO:** Verifies correct parsing and dimension boundaries.
- **OOB Bounding Boxes:** Verifies YOLO coordinates > 1.0 or COCO coordinates outside image dims trigger `FAIL`.
- **Exact Duplicates:** Confirms SHA-256 duplicate clusters are caught based on threshold.
- **Missing Images:** Validates missing reference files yield `FAIL`.
- **Label Flipping:** Verifies candidate class distributions against ground truth references.
- **Data Poisoning (Z-Score):** Verifies anomalous RGB pixel distributions are caught.
- **Trigger Patterns (Entropy):** Verifies zero-entropy patches (e.g., solid BMP patches) on noisy backgrounds trigger an anomaly flag.

### 2. Model Integrity (3 Scenarios)
- **Manifest Matching:** Ensures an unaltered model perfectly aligns with its declared SHA-256 in the manifest.
- **Substitution Detection:** Modifying one byte in the model artifact correctly triggers an `ANOMALY_DETECTED` via digest mismatch.
- **Format Structure:** Confirms valid `.pt` and `.onnx` files successfully load structurally (without executing code), and corrupted formats trigger `FAIL`.

### 3. Inference Provenance (3 Scenarios)
- **Canonical Serialization & Hash:** Ensures dictionary key ordering does not alter payload hash identity.
- **HMAC Signatures:** Confirms valid secrets successfully verify the payload, and flipped bits in the log trigger `FAIL`.
- **Replay Detection:** Confirms identical transaction IDs appearing multiple times correctly trigger `ANOMALY_DETECTED`.

## Status
- **Coverage:** 100% of defined modules
- **Count:** 77/77 tests passing (Pytest)
