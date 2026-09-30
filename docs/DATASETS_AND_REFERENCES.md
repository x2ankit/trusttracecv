# Datasets and References

This document outlines the reference datasets and benchmarks analyzed during the development of TRUSTTRACE CV.

## 1. COCO 2017 (Common Objects in Context)
- **Source:** https://cocodataset.org/
- **Role:** Industry standard for object detection datasets.
- **Integration Status:** Substituted with synthetic COCO JSON fixtures.
- **Reason:** The official train/val annotations zip is ~241MB and images are >18GB. To adhere to the lightweight, offline-first mandate of the SIH prototype, we generated local 100x100 RGB synthetic images wrapped in a valid COCO JSON schema.

## 2. NIST TrojAI
- **Source:** https://www.nist.gov/itl/ai/trojai
- **Role:** Object detection backdoor benchmark.
- **Integration Status:** Substituted with synthetic PyTorch `.pt` artifacts.
- **Reason:** Real TrojAI object detection models are multiple gigabytes each and require proprietary toolchains to execute. We mapped their security objectives (model identity and structural validation) directly to our lightweight test artifacts.

## 3. BDD100K (Optional)
- **Source:** https://bdd-data.berkeley.edu/
- **Role:** Distribution shift (weather, lighting) evaluation.
- **Integration Status:** Deferred.
- **Reason:** Evaluated for drift testing, but its massive size and strict data use agreement makes it unsuitable for an offline hackathon repository. Distribution shift is tested using controlled synthetic out-of-distribution (OOD) pixel distributions locally.

*For exact generation commands of the synthetic substitutions, refer to `DATASET_PREPARATION.md` and `scripts/generate_fixtures.py`.*
