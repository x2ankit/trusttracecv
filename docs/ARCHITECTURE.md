# Architecture

TRUSTTRACE CV is designed as an offline-first, modular Python application. The architecture prioritizes separation of concerns, ensuring that dataset inspection, model integrity validation, and inference provenance are handled by independent sub-modules that feed into a unified reporting pipeline.

## System Components

```
TRUSTTRACE CV
├── src/
│   ├── dataset/          # Dataset integrity and label quality checks (COCO, YOLO)
│   │   ├── inspector.py
│   │   └── security_checks.py
│   ├── models/           # Model artifact validation, hashing, PyTorch/ONNX structure
│   │   └── integrity.py
│   ├── inference/        # HMAC-SHA256 signing, provenance, and tamper detection
│   │   └── verifier.py
│   ├── reporting/        # Report generation and coverage documentation
│   │   └── report_generator.py
│   ├── api/              # FastAPI backend serving endpoints for all checks
│   │   └── app.py
│   ├── ui/               # HTML/CSS/JS Professional light-themed frontend
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   └── cli.py            # Typer-based command-line interface
├── tests/                # 77+ automated pytest cases
├── scripts/
│   └── generate_fixtures.py # Deterministic synthetic fixture generation (Seed=42)
├── vendor/upstream/      # Cloned upstream reference repositories (isolated)
└── docs/                 # Comprehensive documentation
```

## Data Flow

1. **Dataset Audit:** User provides dataset path -> `dataset/inspector.py` extracts metadata -> `dataset/security_checks.py` runs statistical/cryptographic checks -> Findings array generated.
2. **Model Audit:** User provides artifact + manifest -> `models/integrity.py` hashes and structurally validates format (PyTorch/ONNX) -> Findings array generated.
3. **Inference Audit:** User provides `.jsonl` inference log -> `inference/verifier.py` validates canonical hashes, HMAC-SHA256 signatures, and replays -> Findings array generated.
4. **Report Generation:** `reporting/report_generator.py` aggregates all findings, determines a unified verdict, calculates severity, and emits a structured JSON report matching the required schema.

## Upstream Integrations

To comply with the offline requirement and minimize dependency bloat, upstream repositories (e.g., CleanVision, Cleanlab, in-toto, ART) were cloned and audited. Instead of directly importing heavy dependencies that would require active internet or complex infrastructure (like MLflow databases), TRUSTTRACE implements the core logic directly (e.g., deterministic duplicate checks, signature verification), adapting the architectural patterns from these upstream projects.
