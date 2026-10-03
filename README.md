# TRUSTTRACE CV

TRUSTTRACE CV is an offline-first, model-agnostic integrity assurance pipeline for computer vision training data, model artifacts, and inference records.

## Project Overview

The system provides deterministic cryptographic checks and statistical heuristics to establish the provenance and integrity of assets throughout the machine learning lifecycle:

- **Dataset and annotation integrity:** Detects exact duplicate flooding, label flipping, out-of-distribution (OOD) samples, and structural validation of COCO and YOLO formats.
- **Model artifact identity:** Validates model artifacts (PyTorch, TorchScript, ONNX) against reference manifests using SHA-256 digests.
- **Inference provenance:** Cryptographically signs inference logs (HMAC-SHA256) to detect tampering, post-prediction alterations, and replay attacks.
- **Evidence-backed audit findings:** Generates self-contained HTML forensic reports embedding original image bytes, bounding box coordinates, execution histories, and specific integrity violations.

## Features and Implementation Status

| Capability | Status | Evidence | Limitations |
| --- | --- | --- | --- |
| Duplicate Flooding Detection | Implemented | SHA-256 digest comparison | Exact byte matches only; no perceptual hashing for recompressed images. |
| Format Validation (YOLO/COCO) | Implemented | Schema parsing | Supports standard bounding box annotations only (no polygons). |
| Label Flipping Detection | Implemented | Class ID statistical variance | Heuristic flag requiring manual review. |
| Trigger Pattern Detection | Experimental | Patch-level Shannon entropy | Detects solid/zero-entropy patches; cannot detect adversarial noise. |
| OOD Sample Detection | Implemented | Mahalanobis distance | High false positive rate on diverse real-world datasets. |
| Model Identity Verification | Implemented | Manifest-based SHA-256 | Validates identity, not the absence of backdoors within weights. |
| Inference Tamper Detection | Implemented | HMAC-SHA256 signature | Requires secure key management outside the scope of this repository. |
| HTML Forensic Reports | Implemented | Offline base64 data URIs | Large datasets produce excessively large HTML files. |

## Architecture

The system operates entirely offline using a FastAPI backend and a vanilla JavaScript frontend. 

- **`src/dataset/`**: Dataset parsing, coordinate normalization, and integrity calculations.
- **`src/models/`**: Cryptographic artifact verification.
- **`src/inference/`**: Log signing and tamper verification algorithms.
- **`src/api/`**: REST API and sqlite-backed event logging (`audit_events.sqlite`).
- **`src/reporting/`**: Assembles HTML templates for forensic exports.
- **`src/ui/`**: Static HTML/JS frontend polling the backend via REST.

For detailed architecture, refer to `docs/ARCHITECTURE.md`.

## Requirements

- Operating System: Windows or Linux
- Python: 3.9+
- Environment: Conda or virtualenv

## Installation and Configuration

1. Clone the repository and navigate into the root directory:
   ```bash
   git clone <REPOSITORY_URL>
   cd TRUSTTRACE-CV
   ```

2. Create and activate a local Python environment:
   ```bash
   conda create -n <PYTHON_ENVIRONMENT> python=3.10
   conda activate <PYTHON_ENVIRONMENT>
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (copy the example template):
   ```bash
   cp .env.example .env
   ```

5. Generate synthetic test fixtures (optional, for testing):
   ```bash
   python scripts/generate_fixtures.py
   ```

6. Start the backend server:
   ```bash
   python run_server.py
   ```

7. Open the local application:
   Navigate to `http://localhost:8000` in your web browser.

## Dataset Preparation and Usage

TRUSTTRACE CV supports standard COCO 2017 JSON schema and YOLO darknet text formats. 
Datasets must be uploaded as ZIP archives containing the images and their corresponding annotations. 
The system expects standard rectangular bounding boxes (`x_center, y_center, width, height` for YOLO).

To run an audit:
1. Upload the dataset archive via the web UI.
2. The backend extracts the dataset to a temporary local directory.
3. The live viewer will display images with accurately scaled bounding boxes.
4. Download the forensic report upon completion.

## Integrity Checks and Calculations

- **SHA-256 Hashing:** Used to identify exact duplicate images within the dataset and to verify model weights against `<MODEL_MANIFEST>`.
- **Entropy Scans:** Calculates Shannon entropy over a sliding 20x20 window on images. Patches with near-zero entropy (e.g., solid color squares) are flagged as potential triggers.
- **OOD Detection:** Calculates the Mahalanobis distance of image pixel distributions relative to the dataset mean to flag statistical outliers.

## Reports and Audit Evidence

Audit findings are generated dynamically and logged sequentially to a local `audit_events.sqlite` database. 
Upon completion of a dataset audit, the system produces a self-contained HTML forensic report. This report embeds original image bytes as `data:image/...;base64` URIs, ensuring offline accessibility and strict binding of evidence to the report structure.

## Testing and Reproducibility

The automated test suite uses `pytest` and relies on reproducible synthetic fixtures.

To execute the test suite:
```bash
pytest tests/ -v
```

All 90 automated tests pass against the provided synthetic fixtures.

## Security and Limitations

- **Heuristic Anomalies:** Statistical anomalies (OOD, entropy) constitute evidence for human investigation. They do not cryptographically prove malicious poisoning.
- **Model Safety:** Cryptographic hashes establish artifact identity to prevent supply-chain substitution. They do not evaluate the safety, fairness, or accuracy of the model's underlying weights.
- **Local Data Handling:** All processing occurs locally. Ensure the host machine is appropriately secured.
- **Secrets Management:** Ensure HMAC signing keys are protected in production deployments.

## Troubleshooting

- **Missing Bounding Boxes:** Ensure YOLO coordinates are properly normalized (0.0 to 1.0).
- **Report Download Fails:** Wait for the `Finalization` stage of the audit to complete before exporting the HTML report.

## Documentation Reference

- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [SECURITY_AND_THREAT_MODEL.md](docs/SECURITY_AND_THREAT_MODEL.md)
- [DATASET_TESTING.md](docs/DATASET_TESTING.md)
- [API_REFERENCE.md](docs/API_REFERENCE.md)
- [DEVELOPMENT.md](docs/DEVELOPMENT.md)
