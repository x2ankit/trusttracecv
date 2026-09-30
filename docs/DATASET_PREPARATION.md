# Dataset Preparation and Provenance

## Primary Dataset: COCO 2017 (Synthetic Substitution)

**Official Source:** https://cocodataset.org/
**License:** Creative Commons Attribution 4.0 License (for annotations)

**Acquisition Decision:**
The full COCO 2017 dataset is hundreds of gigabytes. Even the minimal `annotations_trainval2017.zip` is ~241MB, which expands to >800MB. To ensure the TRUSTTRACE CV prototype remains offline-first, lightweight, and completely reproducible without large downloads, we have substituted the official COCO images with **synthetic fixtures**. 

**Implementation Details:**
- A synthetic COCO-compliant dataset is generated using `scripts/generate_fixtures.py`.
- **Subset Size:** 100 images (Gaussian noise base to simulate high entropy, with localized patterns for classes).
- **Format:** Fully compliant with COCO 2017 JSON schema.
- **YOLO Equivalents:** The script also generates exact YOLO format equivalents to validate cross-format integrity checks.

This substitution is permitted under the SIH implementation brief guidelines ("If the dataset is unavailable or a download is too large, use a smaller permitted sample or synthetic fixtures and document the substitution.").

## Dataset Integrity Fixtures (Synthetic)

All security scenarios are deterministically generated from the synthetic baseline using fixed random seeds (seed `42`).

- **Exact Duplicates:** Byte-for-byte copies of base images to test SHA-256 detection (SEC-DS-001).
- **Label Flipping:** Class IDs are intentionally scrambled compared to the baseline (SEC-DS-002).
- **Trigger Patterns:** 20x20 solid red patches injected into the bottom-right corner of specific images. Saved as lossless `.bmp` to ensure exact zero-entropy patterns are preserved for detection (SEC-DS-003).
- **Out of Distribution (OOD):** Samples drawn from entirely different distributions (e.g., solid colour fields instead of noise) to trigger Mahalanobis distance anomalies.
- **Data Poisoning:** Statistically altered pixel distributions triggering Z-score anomalies.

## Model Artifacts

**Benchmark:** NIST TrojAI (Object Detection)
**Official Source:** https://www.nist.gov/itl/ai/trojai

**Acquisition Decision:**
TrojAI object detection models (e.g., Round 4) are extremely large (often multiple gigabytes per model for Faster R-CNN or similar architectures) and require large proprietary toolchains. 
Instead, we provide a **synthetic PyTorch artifact** (`dummy_detector.pt`) containing a simple 3-layer CNN architecture and randomized weights.
- This serves as the reference for structural validation (SEC-MDL-002) and SHA-256 manifest matching (SEC-MDL-001).
- The substitution ensures the prototype runs on standard hardware offline without multi-gigabyte downloads.

## Integration of CleanVision and Cleanlab

We have cloned the following upstream repositories into `vendor/upstream/`:
- `cleanvision`
- `cleanlab`

Due to environment size constraints and potential dependency conflicts, their functionalities (like duplicate detection and label error detection) are isolated behind adapters in `src.dataset.security_checks`. In this prototype, we implement the core integrity logic directly to guarantee offline stability, keeping these repositories as architectural references and optional extensions for production scaling.
