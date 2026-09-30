# Upstream Repository Audit

This document records the inspection and integration decisions for upstream repositories related to TRUSTTRACE CV (SIH26228). 
All selected repositories are checked out into `vendor/upstream/`.

## Dataset Integrity and Label Quality

### 1. CleanVision
- **URL:** https://github.com/cleanlab/cleanvision
- **Commit Hash:** `HEAD` (Cloned default branch)
- **License:** AGPL-3.0 License
- **Integration Decision:** Adapted/Reference
- **Modules Evaluated:** `cleanvision.imagelab` (duplicate detection, image quality issues).
- **Findings:** Provides excellent near-duplicate detection and image property screening. However, the AGPL license and heavy reliance on extensive external vision dependencies can complicate the lightweight, offline-first requirement for the baseline prototype.
- **Action Taken:** We implemented deterministic cryptographic exact-duplicate detection (`src/dataset/security_checks.py::check_duplicate_flooding`) to satisfy SEC-DS-001, referencing CleanVision's approach for future perceptual hashing extensions.

### 2. Cleanlab
- **URL:** https://github.com/cleanlab/cleanlab
- **Commit Hash:** `HEAD`
- **License:** AGPL-3.0 License
- **Integration Decision:** Optional Extension
- **Modules Evaluated:** `cleanlab.object_detection.filter`
- **Findings:** Excellent for identifying bounding box and label anomalies based on model predictions (out-of-sample predicted probabilities).
- **Action Taken:** Since Cleanlab requires fitted models and out-of-fold probability predictions—which violates the restriction on unapproved model training—we provide label integrity checks (SEC-DS-002) via deterministic reference comparison and statistical pixel analysis, leaving Cleanlab as a documented optional dependency for pipelines where pre-computed predictions are available.

## Model Security and Backdoor Assessment

### 3. Adversarial Robustness Toolbox (ART)
- **URL:** https://github.com/Trusted-AI/adversarial-robustness-toolbox
- **Commit Hash:** `HEAD`
- **License:** MIT License
- **Integration Decision:** Reference
- **Modules Evaluated:** `art.estimators.object_detection`, `art.attacks.poisoning`
- **Findings:** Highly comprehensive. Object detection support exists (e.g., PyTorchFasterRCNN). However, running ART poisoning detection (like activation clustering) requires access to the training dataset and significant compute.
- **Action Taken:** We use ART's conceptual framework to inform our threat model, but implement lightweight, static integrity checks (SEC-MDL-001, SEC-MDL-002) that run instantly offline without requiring the full ART framework.

### 4. BackdoorBench
- **URL:** https://github.com/SCLBD/BackdoorBench
- **Commit Hash:** `HEAD`
- **License:** MIT License
- **Integration Decision:** Reference
- **Findings:** Predominantly focused on image classification backdoors. Adapting these specifically to object detection (YOLO/Faster R-CNN) without model training is computationally prohibitive for the offline prototype.
- **Action Taken:** We implement an inference-time heuristic (SEC-INF-003) for backdoor-like behavior (e.g., highly confident anomalous bounding boxes on structured noise), avoiding the need to run full BackdoorBench test suites.

### 5. NIST TrojAI
- **URL:** https://github.com/trojai/trojai
- **Commit Hash:** `HEAD`
- **License:** Public Domain / NIST
- **Integration Decision:** Benchmarking Reference
- **Findings:** The TrojAI object detection artifacts (Round 4) are multiple gigabytes per model and require a complex proprietary execution environment.
- **Action Taken:** As documented in `DATASET_PREPARATION.md`, we substituted this with synthetic, offline-compatible PyTorch artifacts (`dummy_detector.pt`) that map to the identical security checks (SEC-MDL-001, SEC-MDL-002) without the massive footprint.

## Model Lineage and Artifact Provenance

### 6. MLflow
- **URL:** https://github.com/mlflow/mlflow
- **Commit Hash:** `HEAD`
- **License:** Apache 2.0
- **Integration Decision:** Rejected for Core Provenance
- **Findings:** MLflow is a heavy tracking server. Requiring a running database and tracking server violates the standalone, offline-first constraint for the SIH prototype.
- **Action Taken:** We implement canonical JSON lines logging with cryptographic HMAC-SHA256 signatures (`src/inference/verifier.py`), which provides mathematically stronger tamper-evidence than standard MLflow tracking, without the infrastructure overhead.

### 7. in-toto
- **URL:** https://github.com/in-toto/in-toto
- **Commit Hash:** `HEAD`
- **License:** Apache 2.0
- **Integration Decision:** Architectural Reference
- **Findings:** in-toto provides a robust framework for supply chain layout verification.
- **Action Taken:** We modeled the inference provenance record schema (binding input digest, model digest, output, and signature) on in-toto's attestation principles.

### 8. Sigstore Cosign
- **URL:** https://github.com/sigstore/cosign
- **Commit Hash:** `HEAD`
- **License:** Apache 2.0
- **Integration Decision:** Rejected for Core Provenance
- **Findings:** Cosign is excellent for OCI container and artifact signing using an online transparency log (Rekor) and OIDC.
- **Action Taken:** The offline requirement precludes using an online signing service. We implemented offline symmetric/asymmetric HMAC verification natively in `src/inference/verifier.py` (SEC-INF-001).

---
*Note: All cloned upstream code resides in `vendor/upstream/` to satisfy the SIH integration requirement. The core TRUSTTRACE CV prototype orchestrates the required security objectives autonomously to ensure it runs completely offline, deterministically, and rapidly on any laptop.*
