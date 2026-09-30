# TRUSTTRACE CV

TRUSTTRACE CV is an offline-first, model-agnostic assurance system for computer vision training data, model artifacts, and inference records, developed for SIH problem statement SIH26228.

## Overview
This system provides reproducible controlled tests for data and model integrity, including detection of poisoning, label flipping, duplicate flooding, trigger patterns, OOD insertion, model substitution, and inference tampering.

## Architecture & Coverage

The implementation satisfies the following SIH requirements:
- **Offline First**: Runtime operates offline after dependencies and assets are acquired.
- **Model Agnostic**: Supports COCO and YOLO formats, as well as ONNX, PyTorch, and TorchScript model artifacts.
- **Assurance System**: Evaluates training data, model artifacts, and inference records.

### Requirement Mapping

| SIH Requirement | Source Module | Tests | Evidence |
| --- | --- | --- | --- |
| Dataset Inspection | `src/dataset/` | `tests/test_dataset.py` | UI views & generated reports |
| Model Identity & Integrity | `src/models/` | `tests/test_models.py` | Hashes, structural validation |
| Inference Verification | `src/inference/` | `tests/test_inference.py` | Replay validation logs |
| Security Testing (Poisoning, Flips, Triggers, OOD) | `src/security/` | `tests/test_security.py` | Assurance reports |
| Professional UI | `src/ui/` | Manual | Web interface |
| Offline CLI Reproduction | `src/cli.py` | `tests/test_cli.py` | CLI execution logs |

*(Note: Modules and tests are progressively being implemented.)*

## Setup Instructions

1. Ensure Conda is installed.
2. Activate the environment:
   ```bash
   conda activate mldl
   ```
3. Install project dependencies (to be defined).

## Assumptions & Limitations
- **Hardware**: Relies on available compute (CPU/GPU) for model inference.
- **Backdoor Detection**: Universal backdoor detection is probabilistic and not mathematically guaranteed.
- **Model Hashes**: Hash matching verifies identity and prevents substitution but does not inherently prove model safety.
- **Data Scope**: Assumes data is provided in standard COCO or YOLO format.

## Audit Log & Reporting
The system generates evidence-backed assurance reports detailing confidence basis, limitations, and recommended actions.
