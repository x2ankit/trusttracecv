# Development Guide

## Code Organization

TRUSTTRACE CV is separated into a frontend static UI and a FastAPI backend.
- `src/ui/`: Contains the frontend `index.html`, `app.js`, and `style.css`.
- `src/api/`: Contains the FastAPI backend application (`app.py`), sqlite logging database (`audit_db.py`).
- `src/dataset/`: Contains parsing, inspection, and heuristic anomaly detection logic.
- `src/model/`: Contains structural model validation.
- `src/inference/`: Contains the inference-level provenance algorithms.
- `src/reporting/`: Contains HTML offline report generators and report schema definitions.
- `tests/`: Contains the pytest automated test suite.
- `scripts/`: Development and synthetic data generation scripts.

## Setup for Development

1. Clone the repository and navigate into the root directory.
2. Ensure you have Conda or `venv` available and Python 3.9+ installed.
3. Create the environment:
   ```bash
   conda create -n trusttrace python=3.10
   conda activate trusttrace
   pip install -r requirements.txt
   ```
4. Start the backend:
   ```bash
   python run_server.py
   ```
5. Open `http://localhost:8000` in your web browser.

## Testing

Automated tests are written with `pytest`. They use the synthetic fixtures located in `data/fixtures/clean`.
Run the tests using:
```bash
pytest tests/
```

### Reproducible Dataset Testing
We substitute multi-gigabyte reference datasets (COCO/TrojAI) with synthetic fixtures (`scripts/generate_fixtures.py`) that strictly adhere to their JSON and structural requirements. This allows offline, rapid validation of integrity logic.

## Contribution Workflow
- Verify all relative paths before committing (avoid absolute machine paths).
- Add tests for any new endpoints or inspection functions.
- Avoid committing large blobs or datasets. Limit fixtures to under 1MB.
