# Architecture

TRUSTTRACE CV is designed as an offline-first, modular Python application. The architecture prioritizes separation of concerns, ensuring that dataset inspection, model integrity validation, model performance evaluation, and inference provenance are handled by independent sub-modules that feed into a unified reporting pipeline.

## System Components

```
TRUSTTRACE CV
├── src/
│   ├── dataset/          # Dataset integrity and label quality checks (COCO, YOLO)
│   │   ├── inspector.py
│   │   └── security_checks.py
│   ├── models/           # Model artifact validation, performance, hashing
│   │   ├── integrity.py
│   │   ├── performance.py
│   │   ├── behavioral_fingerprint.py
│   │   └── trigger_probe.py
│   ├── inference/        # Cryptographic signing, provenance chain, and tamper detection
│   │   ├── verifier.py
│   │   └── provenance.py
│   ├── reporting/        # Report generation and coverage documentation
│   │   └── report_generator.py
│   ├── integrations/     # Adapters for upstream open-source tools
│   │   ├── art_adapter.py
│   │   ├── backdoorbench_adapter.py
│   │   ├── cleanlab_adapter.py
│   │   ├── cleanvision_adapter.py
│   │   ├── cosign_adapter.py
│   │   ├── intoto_adapter.py
│   │   └── trojai_adapter.py
│   ├── api/              # FastAPI backend serving endpoints for all checks
│   │   └── app.py
│   ├── ui/               # HTML/CSS/JS Dynamic frontend
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   └── cli.py            # Typer-based command-line interface
├── tests/                # 81+ automated pytest cases
├── vendor/upstream/      # Cloned upstream reference repositories (isolated)
└── docs/                 # Comprehensive documentation
```

## Data Flow

1. **Dataset Audit:** User provides dataset path -> `dataset/inspector.py` extracts metadata -> `dataset/security_checks.py` runs statistical checks (including Distribution Shift) -> `CleanVision` adapter runs -> Findings array generated.
2. **Model Audit:** User provides artifact + manifest -> `models/integrity.py` structurally validates format (PyTorch/ONNX) and verifies RSA signature -> Integration adapters (ART, BackdoorBench, TrojAI, Cosign) run -> Findings array generated.
3. **Inference Audit:** User provides `.jsonl` inference log -> `inference/verifier.py` validates canonical hashes, HMAC-SHA256 signatures, and replays -> Findings array generated.
4. **Full Audit:** Integrates all the above, computes `Cleanlab` label issues, calculates CV Performance (AP/mAP, IoU) and Behavioral Fingerprints, then constructs an `in-toto` provenance chain.
5. **Report Generation:** `reporting/report_generator.py` aggregates all findings, determines a unified verdict, calculates severity, and emits a structured JSON report.

## Upstream Integrations

To comply with the offline requirement and minimize dependency bloat, upstream repositories are integrated via explicit Adapters (`src/integrations`). 
- **CleanVision**, **Cleanlab**, **in-toto**, and **Cosign** adapters execute active checks if libraries/data are available locally.
- **ART**, **BackdoorBench**, and **TrojAI** adapters emit `NOT_ASSESSED` findings natively gracefully if the gigabyte-scale datasets or heavy dependencies are missing.
