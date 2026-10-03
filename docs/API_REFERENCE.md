# API Reference

The TRUSTTRACE CV backend exposes the following REST endpoints. The API is hosted at `http://localhost:8000` by default.

## Dataset Upload

`POST /api/dataset/upload`
Uploads a ZIP file containing the dataset (images and annotations).
- **Body**: `multipart/form-data`, file field `file`.
- **Response**: `{"dataset_path": "...", "format": "...", "message": "..."}`

## Audits

`POST /api/audit/dataset`
Initiates a background integrity audit on the uploaded dataset.
- **Body** (JSON): `{"dataset_path": "...", "format": "coco|yolo", "seed": 42}`
- **Response**: `{"audit_id": "..."}`

`POST /api/audit/model`
Initiates a background structural audit on a model artifact.
- **Body** (JSON): `{"model_path": "..."}`
- **Response**: `{"audit_id": "..."}`

`POST /api/inference/log`
Logs an inference event and generates a cryptographic provenance signature.
- **Body** (JSON): `{"image_path": "...", "model_id": "...", "prediction": {...}, "confidence": 0.99}`
- **Response**: `{"inference_id": "...", "signature": "..."}`

## Status and Logs

`GET /api/audit/status`
Returns the current active background task status.

`GET /api/audit/events/{audit_id}`
Returns the chronological execution history and results of the specified audit from the sqlite database.
- **Response**: `{"events": [...]}`

`GET /api/audit/records/{audit_id}`
Returns the detailed image-by-image inspection records for the dataset audit.

## Report Generation

`GET /api/reports/html/{audit_id}`
Downloads a fully self-contained offline HTML forensic report with embedded base64 images and complete execution history.

`GET /api/reports`
Lists all historically generated dataset JSON reports.

## Images

`GET /api/image?path={path}`
Serves a generic local image file relative to the project root.

`GET /api/image/find?dataset_path={dir}&filename={name}`
Recursively locates and serves a specific filename within an extracted dataset directory.
