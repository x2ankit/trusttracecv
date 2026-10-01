# TRUSTTRACE CV - SIH26228 Test Coverage Matrix

## Threat Vectors vs. Defenses & Classifications

Every capability is strictly classified into one of four states:
- **SUPPORTED**: Implemented, executed, and validated offline.
- **PARTIALLY SUPPORTED**: Implemented heuristically or partially executed without full guarantees.
- **NOT ASSESSED**: Scaffolded or adapted, but missing local upstream artifacts/libraries to execute.
- **OUT OF SCOPE**: Explicitly excluded from this phase per constraints.

> **Disclaimer**: This system provides integrity assurance and anomaly detection. It does not claim universal backdoor detection, perfect model accuracy, or perfect security. All statistical findings represent candidates for review.

### 1. Data Integrity & Label Validation
*   **Duplicate Flooding**: SUPPORTED (Exact match via SHA-256 of image bytes).
*   **Label Flipping**: SUPPORTED (Mismatch vs. trusted reference).
*   **Quality Issues (CleanVision)**: SUPPORTED (Executed via adapter in `audit_dataset`).
*   **Label Consistency (Cleanlab)**: SUPPORTED (Executed via adapter against model predictions in `audit_full`).

### 2. MODEL ARTIFACT INTEGRITY
*   **Model Substitution**: SUPPORTED (SHA-256 matching of model binaries vs manifest).
*   **Structural Tampering**: SUPPORTED (Validates loading model state dictionaries and extracting metadata safely).
*   **Manifest Forgery**: SUPPORTED (Cryptographic HMAC validation of manifest + RSA asymmetric signing validation via `cryptography`).
*   **Offline Cryptographic Signing (Cosign)**: SUPPORTED (Cosign adapter execution implemented).

### 3. Inference Provenance & Output Tampering
*   **Output Tampering**: SUPPORTED (HMAC-SHA256 signature verification of inference record payload).
*   **Result Replay**: SUPPORTED (Persistent SQLite backend checking for duplicate payload_hash submissions).
*   **Chain of Custody (in-toto)**: SUPPORTED (Generates local in-toto-style link elements during `audit_full`).
*   **Sequence Modification**: SUPPORTED (Cryptographic sequence and previous-hash verification across the chain).

### 4. MODEL PERFORMANCE
*   **IoU, TP/FP/FN**: SUPPORTED (Dynamic overlap calculation against reference annotations).
*   **Precision/Recall**: SUPPORTED.
*   **AP/mAP**: PARTIALLY SUPPORTED (Simplified estimation based on confidence thresholds against references).

### 5. MODEL BEHAVIORAL ASSESSMENT & TRIGGER SENSITIVITY
*   **Behavioral Fingerprinting**: SUPPORTED (Calculates object counts, confidence distribution, box areas directly from actual predictions).
*   **Trigger Pattern Probing (Entropy)**: PARTIALLY SUPPORTED (Low-entropy patch heuristic).
*   **Trigger Sensitivity**: PARTIALLY SUPPORTED (Deterministic spatial perturbation probes via `trigger_probe.py`).
*   **Adversarial Robustness (ART)**: NOT ASSESSED (Adapter implemented, but ART library not installed locally).

### 6. BACKDOOR BENCHMARK VALIDATION
*   **BackdoorBench Evaluation**: NOT ASSESSED (Adapter implemented, but gigabyte-scale benchmark artifacts not downloaded).
*   **TrojAI Evaluation**: NOT ASSESSED (Adapter implemented, but NIST datasets not available locally).

### 7. DISTRIBUTION SHIFT
*   **Data Poisoning (Statistical Outlier)**: SUPPORTED (Z-score on pixel means/stds returning STATISTICAL_SHIFT).
*   **OOD Insertion**: PARTIALLY SUPPORTED (Mahalanobis distance on pixel distribution).

## Excluded Capabilities (OUT OF SCOPE)
*   Training or fine-tuning an ML-based validator model.
*   Modification or recalibration of candidate model weights.
*   Downloading massive datasets (COCO full, ImageNet, TrojAI).
