"""
src/api/app.py

FastAPI backend for TRUSTTRACE CV.
Serves the audit APIs consumed by the frontend UI.

Endpoints:
  GET  /                     Serve the UI (static HTML)
  POST /api/audit/dataset    Run dataset audit
  POST /api/audit/model      Run model audit
  POST /api/audit/inference  Run inference audit
  POST /api/audit/full       Run full pipeline audit
  GET  /api/report/{id}      Retrieve a previously saved report
  GET  /api/health           Health check
"""

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.dataset.inspector import inspect_yolo_dataset, inspect_coco_dataset
from src.dataset.security_checks import (
    check_duplicate_flooding,
    check_label_flipping,
    check_trigger_patterns,
    check_data_poisoning,
)
from src.models.integrity import inspect_model, load_manifest
from src.inference.verifier import (
    load_inference_log,
    verify_inference_record,
    check_inference_replay,
    check_backdoor_behaviour,
)
from src.reporting.report_generator import generate_report, save_report, COVERAGE

logger = logging.getLogger(__name__)
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="TRUSTTRACE CV",
    description="SIH26228 – Computer Vision Assurance System",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class DatasetAuditRequest(BaseModel):
    dataset_path: str
    format: str = "yolo"
    seed: int = 42


class ModelAuditRequest(BaseModel):
    model_path: str
    manifest_path: Optional[str] = None
    seed: int = 42


class InferenceAuditRequest(BaseModel):
    log_path: str
    seed: int = 42


class FullAuditRequest(BaseModel):
    dataset_path: Optional[str] = None
    model_path: Optional[str] = None
    manifest_path: Optional[str] = None
    inference_log: Optional[str] = None
    seed: int = 42


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": time.time(), "service": "TRUSTTRACE CV"}


# ---------------------------------------------------------------------------
# Dataset audit
# ---------------------------------------------------------------------------

@app.post("/api/audit/dataset")
def audit_dataset(req: DatasetAuditRequest):
    base = Path(req.dataset_path)
    if not base.exists():
        raise HTTPException(status_code=400, detail=f"Path not found: {req.dataset_path}")

    if req.format == "yolo":
        images_dir = base / "images"
        labels_dir = base / "labels"
        if not images_dir.exists():
            raise HTTPException(status_code=400, detail="images/ subdirectory not found")
        ds_result = inspect_yolo_dataset(images_dir, labels_dir)
        records = ds_result["records"]
        findings: List[Dict[str, Any]] = [
            check_duplicate_flooding(records),
            check_data_poisoning(records),
            check_trigger_patterns([images_dir / r["filename"] for r in records]),
        ]
        summary = {
            "dataset_type": "YOLO",
            "total_images": ds_result["total_images"],
            "class_counts": ds_result["class_counts"],
        }
    elif req.format == "coco":
        ann_path = base / "annotations.json"
        if not ann_path.exists():
            raise HTTPException(status_code=400, detail="annotations.json not found")
        ds_result = inspect_coco_dataset(ann_path)
        findings = []
        summary = {
            "dataset_type": "COCO",
            "total_images": ds_result["total_images"],
            "total_annotations": ds_result["total_annotations"],
            "class_counts": ds_result["class_counts"],
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown format: {req.format}")

    report = generate_report(
        dataset_findings=findings,
        dataset_summary=summary,
        audit_seed=req.seed,
        target_name=req.dataset_path,
    )
    save_report(report, REPORTS_DIR / f"dataset_{report['report_id'][:8]}.json")

    return {
        "report_id": report["report_id"],
        "verdict": report["verdict"],
        "severity_summary": report["severity_summary"],
        "findings": findings,
        "dataset_summary": summary,
        "records": ds_result.get("records", [])[:50],  # cap for response size
    }


# ---------------------------------------------------------------------------
# Model audit
# ---------------------------------------------------------------------------

@app.post("/api/audit/model")
def audit_model(req: ModelAuditRequest):
    model_path = Path(req.model_path)
    if not model_path.exists():
        raise HTTPException(status_code=400, detail=f"Model not found: {req.model_path}")

    ref_manifest = None
    if req.manifest_path:
        mp = Path(req.manifest_path)
        if mp.exists():
            ref_manifest = load_manifest(mp)

    record = inspect_model(model_path, reference_manifest=ref_manifest)
    hm = record["checks"].get("hash_match", {})
    loadable = record["checks"].get("loadable", {})

    findings = [
        {
            "check_id": "SEC-MDL-001",
            "name": "Model Substitution / Integrity Check",
            "result": "PASS" if hm.get("result") == "PASS" else
                      "ANOMALY_DETECTED" if hm.get("result") == "FAIL" else
                      hm.get("result", "NOT ASSESSED"),
            "severity": hm.get("severity", "INFO"),
            "confidence": "HIGH",
            "evidence": hm,
            "description": hm.get("detail", ""),
            "recommended_action": "Obtain from trusted source and re-verify." if hm.get("result") == "FAIL" else "No action required.",
            "limitation": "Hash confirms identity, not safety.",
        },
        {
            "check_id": "SEC-MDL-002",
            "name": "Model Structural Validation",
            "result": loadable.get("result", "NOT ASSESSED"),
            "severity": "HIGH" if loadable.get("result") == "FAIL" else "INFO",
            "confidence": "HIGH",
            "evidence": {"metadata": record["metadata"]},
            "description": loadable.get("detail", "Model loaded successfully."),
            "recommended_action": "Investigate corruption or incompatible format." if loadable.get("result") == "FAIL" else "No action required.",
            "limitation": "Loading does not verify semantic correctness.",
        },
    ]

    report = generate_report(
        model_findings=findings,
        model_summary={"filename": record["filename"], "sha256": record["sha256"],
                       "format": record["format"], "size_bytes": record.get("size_bytes")},
        audit_seed=req.seed,
        target_name=req.model_path,
    )
    save_report(report, REPORTS_DIR / f"model_{report['report_id'][:8]}.json")

    return {
        "report_id": report["report_id"],
        "verdict": report["verdict"],
        "severity_summary": report["severity_summary"],
        "findings": findings,
        "model_record": record,
    }


# ---------------------------------------------------------------------------
# Inference audit
# ---------------------------------------------------------------------------

@app.post("/api/audit/inference")
def audit_inference(req: InferenceAuditRequest):
    log_path = Path(req.log_path)
    if not log_path.exists():
        raise HTTPException(status_code=400, detail=f"Log not found: {req.log_path}")

    records = load_inference_log(log_path)
    findings: List[Dict[str, Any]] = []
    seen: set = set()

    for rec in records:
        findings.append(verify_inference_record(rec))
        findings.append(check_inference_replay(rec, seen))
        if rec.get("payload_hash"):
            seen.add(rec["payload_hash"])
        preds = rec.get("predictions", [])
        bb = check_backdoor_behaviour(preds)
        if bb["result"] != "PASS":
            findings.append(bb)

    report = generate_report(
        inference_findings=findings,
        audit_seed=req.seed,
        target_name=req.log_path,
    )
    save_report(report, REPORTS_DIR / f"inference_{report['report_id'][:8]}.json")

    return {
        "report_id": report["report_id"],
        "verdict": report["verdict"],
        "severity_summary": report["severity_summary"],
        "findings": findings,
        "records": records,
    }


# ---------------------------------------------------------------------------
# Full audit
# ---------------------------------------------------------------------------

@app.post("/api/audit/full")
def audit_full(req: FullAuditRequest):
    all_ds_findings: list = []
    all_mdl_findings: list = []
    all_inf_findings: list = []
    ds_summary: dict = {}
    mdl_summary: dict = {}

    if req.dataset_path:
        base = Path(req.dataset_path)
        if base.exists():
            imgs = base / "images"
            lbls = base / "labels"
            if imgs.exists():
                ds_result = inspect_yolo_dataset(imgs, lbls)
                records = ds_result["records"]
                all_ds_findings = [
                    check_duplicate_flooding(records),
                    check_data_poisoning(records),
                    check_trigger_patterns([imgs / r["filename"] for r in records]),
                ]
                ds_summary = {"total_images": ds_result["total_images"],
                              "class_counts": ds_result["class_counts"]}

    if req.model_path:
        mp = Path(req.model_path)
        if mp.exists():
            ref = load_manifest(Path(req.manifest_path)) if req.manifest_path and Path(req.manifest_path).exists() else None
            record = inspect_model(mp, reference_manifest=ref)
            hm = record["checks"].get("hash_match", {})
            all_mdl_findings.append({
                "check_id": "SEC-MDL-001", "name": "Model Substitution / Integrity Check",
                "result": "PASS" if hm.get("result") == "PASS" else "ANOMALY_DETECTED" if hm.get("result") == "FAIL" else hm.get("result", "NOT ASSESSED"),
                "severity": hm.get("severity", "INFO"), "confidence": "HIGH",
                "evidence": hm, "description": hm.get("detail", ""),
                "recommended_action": "Verify model source." if hm.get("result") == "FAIL" else "No action.",
                "limitation": "Hash confirms identity, not safety.",
            })
            mdl_summary = {"filename": record["filename"], "sha256": record["sha256"]}

    if req.inference_log:
        lp = Path(req.inference_log)
        if lp.exists():
            records_inf = load_inference_log(lp)
            seen: set = set()
            for rec in records_inf:
                all_inf_findings.append(verify_inference_record(rec))
                all_inf_findings.append(check_inference_replay(rec, seen))
                if rec.get("payload_hash"):
                    seen.add(rec["payload_hash"])

    report = generate_report(
        dataset_findings=all_ds_findings,
        model_findings=all_mdl_findings,
        inference_findings=all_inf_findings,
        dataset_summary=ds_summary,
        model_summary=mdl_summary,
        audit_seed=req.seed,
        target_name="Full Audit",
    )
    save_report(report, REPORTS_DIR / f"full_{report['report_id'][:8]}.json")

    return {
        "report_id": report["report_id"],
        "verdict": report["verdict"],
        "severity_summary": report["severity_summary"],
        "findings": all_ds_findings + all_mdl_findings + all_inf_findings,
        "coverage": report["coverage"],
    }


# ---------------------------------------------------------------------------
# Coverage endpoint
# ---------------------------------------------------------------------------

@app.get("/api/coverage")
def get_coverage():
    return COVERAGE


# ---------------------------------------------------------------------------
# Static UI
# ---------------------------------------------------------------------------

UI_DIR = ROOT / "src" / "ui"

# Mount static files so CSS and JS are served
if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    html_path = UI_DIR / "index.html"
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8")
        # Rewrite relative paths to /static/ so FastAPI can serve them
        content = content.replace('href="style.css"', 'href="/static/style.css"')
        content = content.replace('src="app.js"', 'src="/static/app.js"')
        return HTMLResponse(content)
    return HTMLResponse("<h1>TRUSTTRACE CV</h1><p>UI not found.</p>")
