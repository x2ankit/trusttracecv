# TRUSTTRACE CV Setup Guide

## Requirements
- OS: Windows or Linux
- Environment: Conda
- Python: 3.12+

## Installation

1. **Activate the Environment:**
   Ensure you are using the predefined `mldl` Conda environment.
   ```bash
   conda activate mldl
   ```

2. **Install Dependencies:**
   All required dependencies are listed in `requirements.txt`.
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: The `mldl` environment should already possess the necessary PyTorch, NumPy, Pillow, and FastAPI packages as per the implementation baseline).*

3. **Generate Fixtures:**
   Since external COCO and TrojAI datasets are massive, run the fixture generator to create lightweight, offline synthetic assets that deterministically mimic all required scenarios.
   ```bash
   python scripts/generate_fixtures.py
   ```
   This will populate the `data/fixtures/` and `models/fixtures/` directories.

## Running the Application

**Start the Web Server (FastAPI + UI):**
```bash
python run_server.py
```
Open your browser to: `http://localhost:8000`

**Command-Line Interface:**
TRUSTTRACE CV can be executed completely via CLI for CI/CD pipelines.
```bash
# Full audit
python -m src.cli audit-all \
  --dataset-dir data/fixtures/clean \
  --model-path models/fixtures/dummy_detector.pt \
  --manifest models/fixtures/manifest.json \
  --inference-log data/fixtures/inference_logs/inference_log.jsonl
```
