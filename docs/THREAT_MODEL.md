# Threat Model

TRUSTTRACE CV addresses specific threats in a multi-contributor Computer Vision pipeline. This threat model bounds the scope of the prototype's capabilities.

## Addressed Threats

1. **Data Poisoning & Label Flipping (Dataset level)**
   - **Threat:** A contributor maliciously alters training labels or injects statistically anomalous images to degrade model performance.
   - **Mitigation:** Statistical screening (Z-score pixel distributions, bounding box label variance) implemented in `SEC-DS-002` and `SEC-DS-004`.

2. **Trigger Patterns / Backdoors (Dataset level)**
   - **Threat:** A contributor injects visible, highly structured patches (e.g., solid squares) into training images as a backdoor trigger.
   - **Mitigation:** Shannon entropy calculation over sliding windows. Solid patches exhibit near-zero entropy compared to natural image variance. Implemented in `SEC-DS-003`.

3. **Duplicate Flooding (Dataset level)**
   - **Threat:** A contributor floods the dataset with duplicate files to manipulate batch statistics or skew training.
   - **Mitigation:** Cryptographic hashing (SHA-256) of every image file. Identifies exact duplicates (`SEC-DS-001`).

4. **Model Substitution (Model level)**
   - **Threat:** An approved model artifact is silently replaced with a malicious or compromised version.
   - **Mitigation:** Strict cryptographic digest verification against an authorized manifest file (`SEC-MDL-001`).

5. **Inference Tampering & Replay (Inference level)**
   - **Threat:** Inference logs are altered post-prediction to hide false positives, or valid logs are replayed to simulate activity.
   - **Mitigation:** Canonical JSON serialization and HMAC-SHA256 signatures over the input/model/prediction bundle (`SEC-INF-001`). Nonces and deduplication for replay attacks (`SEC-INF-002`).

## Out of Scope (Known Limitations)

1. **Invisible or Perceptual Triggers:** Sophisticated backdoors utilizing adversarial noise imperceptible to the human eye cannot be detected by basic entropy scans.
2. **Model Weight Scanning:** We do not execute universal backdoor detection via static weight analysis, as this is currently an unsolved mathematical problem for generalized deep neural networks without access to the exact training set.
3. **Fuzzy / Near-Duplicates:** The current prototype relies on exact cryptographic hashing. Recompressed (e.g., JPEG quality shift) or slightly resized images are not currently flagged as duplicates.
