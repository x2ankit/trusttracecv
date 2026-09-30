# Assurance Coverage & Limitations

## Supported Integrations (Implemented)
- **Dataset Assessment:**
  - YOLO format image/label binding.
  - COCO JSON format validation.
  - Exact cryptographic file duplicates.
  - Basic label flipping (compared to reference).
  - High-confidence zero-entropy trigger patterns (solid patches in lossless images).
  - Out-of-distribution detection via basic pixel-statistic Z-scores.
- **Model Assessment:**
  - PyTorch (`.pt`, `.pth`), TorchScript, and ONNX format structural validation.
  - Static SHA-256 identity mapping against manifests.
- **Inference Provenance:**
  - Payload binding (Input + Model + Result).
  - Offline symmetric/asymmetric HMAC-SHA256 signature verification.
  - Identical request ID replay detection.

## Partial Support
- **Distribution Shift (Drift):** Covered using Mahalanobis distance / Z-score over pixel distribution (mean/std RGB), but lacks deep feature-based embeddings (e.g., passing images through a ResNet to compare latent vectors), as this requires large external weights.

## Unsupported
- **Fuzzy / Near-Duplicate Detection:** Relies on perceptual hashing (e.g., pHash) which is deferred to optional upstream integrations (like CleanVision).
- **Universal Backdoor Detection:** Detecting imperceptible adversarial backdoors via static weight scanning is mathematically unfeasible and unsupported.
- **Automated Model Remediation:** The system audits and recommends actions but does NOT alter or fix compromised model weights automatically.

## Known Limitations
- Trigger detection (entropy-based) fails if the dataset is heavily compressed using lossy algorithms (JPEG), as compression artifacts introduce entropy into solid patches.
- HMAC signatures rely on secret keys. Key distribution and rotation logic is outside the scope of this prototype.
- Inference anomaly thresholds (for backdoor-like behavior) are currently hardcoded heuristics rather than dynamically calibrated boundaries.
