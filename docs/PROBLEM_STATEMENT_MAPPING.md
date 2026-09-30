# Problem Statement Mapping (SIH26228)

This document maps the requirements of Smart India Hackathon problem statement **SIH26228** to the TRUSTTRACE CV implementation.

| Requirement | Implementation Module | Automated Test Coverage | Status |
|---|---|---|---|
| **1. Dataset Integrity & Label Quality** | | | |
| 1.1 Support COCO JSON and YOLO annotations | `src.dataset.inspector.inspect_yolo_dataset`, `inspect_coco_dataset` | `tests/test_dataset.py::TestInspectYoloDataset`, `TestInspectCocoDataset` | ✅ Implemented |
| 1.2 Validate bounding boxes, dimensions, classes | `src.dataset.inspector.parse_yolo_label` | `test_dataset.py::TestInspectImage::test_yolo_annotation_oob` | ✅ Implemented |
| 1.3 Exact duplicate detection | `src.dataset.security_checks.check_duplicate_flooding` | `test_dataset.py::TestDuplicateFlooding` | ✅ Implemented |
| 1.4 Near duplicate detection | N/A (Deferred to CleanVision extension) | N/A | ❌ Unsupported (v1) |
| 1.5 Label flipping detection | `src.dataset.security_checks.check_label_flipping` | `test_dataset.py::TestLabelFlipping` | ✅ Implemented |
| 1.6 Trigger pattern detection (Backdoors) | `src.dataset.security_checks.check_trigger_patterns` | `test_dataset.py::TestTriggerPatterns` | ✅ Implemented |
| 1.7 Out of Distribution (OOD) screening | `src.dataset.security_checks.check_data_poisoning` (Z-score) | `test_dataset.py::TestDataPoisoning` | ✅ Implemented |
| **2. Model Integrity & Provenance** | | | |
| 2.1 Model format and framework validation | `src.models.integrity.assess_model_integrity` | `tests/test_models.py::TestModelIntegrity::test_assess_model_integrity_pytorch` | ✅ Implemented |
| 2.2 Artifact SHA-256 digest verification | `src.models.integrity._verify_manifest` | `test_models.py::TestManifestVerification` | ✅ Implemented |
| 2.3 Model substitution detection | `src.models.integrity._verify_manifest` | `test_models.py::TestManifestVerification::test_mismatch` | ✅ Implemented |
| 2.4 Support ONNX and PyTorch | `src.models.integrity` | `test_models.py::TestONNXValidation` | ✅ Implemented |
| **3. Inference Provenance & Tamper Verification** | | | |
| 3.1 Bind inference to image, model, inputs | `src.inference.verifier.verify_inference_record` | `tests/test_inference.py::TestInferenceVerification` | ✅ Implemented |
| 3.2 Canonical serialization & cryptographic hash | `src.inference.verifier._canonical_hash` | `test_inference.py::TestHMACSigning` | ✅ Implemented |
| 3.3 Signature verification (HMAC-SHA256) | `src.inference.verifier.verify_hmac_signature` | `test_inference.py::TestHMACSigning::test_hmac_verification` | ✅ Implemented |
| 3.4 Replay detection | `src.inference.verifier.check_replay_attacks` | `test_inference.py::TestReplayDetection` | ✅ Implemented |
| 3.5 Backdoor-like behavior indicators | `src.inference.verifier.check_backdoor_indicators` | `test_inference.py::TestBackdoorIndicators` | ✅ Implemented |
| **4. Reporting and UI** | | | |
| 4.1 JSON Assurance Report Schema | `src.reporting.report_generator.generate_assurance_report` | `tests/test_report.py::TestGenerateReport` | ✅ Implemented |
| 4.2 Web UI mapping backend results | `src/ui/app.js` and `index.html` | Manual UI Testing | ✅ Implemented |
| 4.3 Severity and Confidence levels | Enforced in `generate_assurance_report` | `test_report.py::TestGenerateReport` | ✅ Implemented |
| **5. Constraints** | | | |
| 5.1 No internet connectivity required | All algorithms run locally | Verified via Conda execution | ✅ Implemented |
| 5.2 No unapproved model training | Static weight loading only | Code inspection | ✅ Implemented |
