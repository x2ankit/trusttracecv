"""
src/api/app.py

FastAPI backend for TRUSTTRACE CV.
Serves the audit APIs consumed by the frontend UI.
"""

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import logging
import sys
import time
import uuid
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import urllib.parse

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.dataset.inspector import inspect_yolo_dataset, inspect_coco_dataset, inspect_image
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
UPLOADS_DIR = ROOT / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="TRUSTTRACE CV",
    description="SIH26228 – Computer Vision Assurance System",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class DatasetAuditRequest(BaseModel):
    dataset_path: str
    format: str = "yolo"
    seed: int = 42
    audit_id: str = ""

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

class UploadResponse(BaseModel):
    dataset_path: str
    format: str
    message: str

# ---------------------------------------------------------------------------
# Upload Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/upload/dataset", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...), format: str = Form("yolo")):
    if not file.filename.endswith('.zip'):
        raise HTTPException(400, "Only .zip files are supported for dataset uploads.")
    
    uid = str(uuid.uuid4())[:8]
    ds_dir = UPLOADS_DIR / f"dataset_{uid}"
    ds_dir.mkdir()
    
    zip_path = ds_dir / file.filename
    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ds_dir)
    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid zip file.")
    finally:
        zip_path.unlink()
        
    # Attempt to find the inner directory if it was zipped as a single folder
    contents = list(ds_dir.iterdir())
    if len(contents) == 1 and contents[0].is_dir():
        final_path = contents[0]
    else:
        final_path = ds_dir
        
    # Standardize path for windows
    p = str(final_path.relative_to(ROOT)).replace('\\', '/')
    return UploadResponse(
        dataset_path=p,
        format=format,
        message="Dataset uploaded successfully."
    )

# ---------------------------------------------------------------------------
# Image Serving Endpoint
# ---------------------------------------------------------------------------

@app.get("/api/image")
def get_image(path: str):
    # path could be url encoded
    path = urllib.parse.unquote(path)
    p = ROOT / path
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "Image not found.")
    try:
        p.resolve().relative_to(ROOT.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied.")
    return FileResponse(p)

@app.get("/api/audit/records/{audit_id}")
def get_audit_records(audit_id: str):
    p = REPORTS_DIR / f"records_{audit_id}.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(404, "Records not found")

@app.get("/api/reports/html/{audit_id}")
def download_html_report(audit_id: str):
    try:
        from src.reporting.html_generator import generate_offline_html_report
        html_content = generate_offline_html_report(audit_id)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content, status_code=200, headers={
            "Content-Disposition": f'attachment; filename="trusttrace_audit_{audit_id}.html"'
        })
    except Exception as e:
        logger.exception("Failed to generate HTML report")
        raise HTTPException(500, str(e))

@app.get("/api/image/find")
def find_image(dataset_path: str, filename: str):
    dataset_dir = ROOT / urllib.parse.unquote(dataset_path)
    if not dataset_dir.exists():
        raise HTTPException(404, "Dataset directory not found.")
    
    # Try finding the file recursively
    for p in dataset_dir.rglob(filename):
        if p.is_file():
            return FileResponse(p)
            
    raise HTTPException(404, "Image not found.")

# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------
AUDIT_STATUS = {"status": "Idle", "detail": ""}

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": time.time(), "service": "TRUSTTRACE CV"}

@app.get("/api/audit/status")
def audit_status():
    return AUDIT_STATUS

# ---------------------------------------------------------------------------
# Dataset audit
# ---------------------------------------------------------------------------
from src.api.audit_db import log_event, get_events, init_db

@app.get("/api/audit/events/{audit_id}")
def get_audit_events(audit_id: str):
    return {"events": get_events(audit_id)}

@app.get("/api/reports")
def list_reports():
    """Return all saved dataset audit reports, newest first."""
    reports = []
    if REPORTS_DIR.exists():
        for f in sorted(REPORTS_DIR.glob("dataset_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                import json as _json
                data = _json.loads(f.read_text())
                reports.append(data)
            except Exception:
                pass
    return reports

@app.post("/api/audit/dataset")
def audit_dataset(req: DatasetAuditRequest, background_tasks: BackgroundTasks):
    import uuid
    if not req.audit_id:
        req.audit_id = str(uuid.uuid4())
    
    background_tasks.add_task(run_dataset_audit_task, req)
    return {"status": "started", "audit_id": req.audit_id}

def run_dataset_audit_task(req: DatasetAuditRequest):
    audit_id = req.audit_id
    base = ROOT / req.dataset_path
    
    log_event(audit_id, "Dataset Audit", "Initialize", {"path": req.dataset_path, "format": req.format}, "init()", {}, "STARTED", "", "Audit Initialized", "", 0, "RUNNING")
    
    if not base.exists():
        log_event(audit_id, "Initialization", "Check Path", {"path": str(base)}, "exists(path)", {}, "FALSE", "", "Fail", "", 0, "ERROR", "Path not found")
        return

    if req.format == "yolo":
        log_event(audit_id, "Parsing", "YOLO Dataset", {"path": str(base)}, "parse_yolo()", {}, "STARTED", "", "Parsing annotations", "", 0, "RUNNING")
        images_dir = base / "images"
        labels_dir = base / "labels"
        if not images_dir.exists():
            images_dir = base
            labels_dir = base
        
        # We will need to pass audit_id to inspect_yolo_dataset
        ds_result = inspect_yolo_dataset(images_dir, labels_dir, audit_id=audit_id)
        records = ds_result["records"]
        
        for r in records:
            p = Path(r["path"])
            r["url_path"] = str(p.relative_to(ROOT)).replace('\\', '/')
        with open(REPORTS_DIR / f"records_{audit_id}.json", "w", encoding="utf-8") as f:
            json.dump(records, f)
            
        raw_findings: List[Dict[str, Any]] = [
            check_duplicate_flooding(records, audit_id=audit_id),
            check_data_poisoning(records, audit_id=audit_id),
            check_trigger_patterns([Path(r["path"]) for r in records if Path(r["path"]).exists()], audit_id=audit_id),
        ]
        findings = [f for f in raw_findings if f["result"] != "PASS"]
        
        # Execute CleanVision adapter
        from src.integrations.cleanvision_adapter import run_cleanvision_checks
        log_event(audit_id, "Quality Checks", "CleanVision", {"images_dir": str(images_dir)}, "cleanvision.detect()", {}, "STARTED", "", "Running pixel anomaly detection", "", 0, "RUNNING")
        cv_evidence = run_cleanvision_checks(str(images_dir), req.dataset_path)
        for e in cv_evidence:
            findings.append(e.to_dict())
            
        summary = {
            "dataset_type": "YOLO",
            "total_images": ds_result["total_images"],
            "class_counts": ds_result["class_counts"],
        }
    elif req.format == "coco":
        ann_path = base / "annotations.json"
        if not ann_path.exists():
            log_event(audit_id, "Initialization", "Check Path", {"path": str(ann_path)}, "exists(path)", {}, "FALSE", "", "Fail", "", 0, "ERROR", "annotations.json not found")
            return
        images_dir = base / "images"
        if not images_dir.exists():
            images_dir = base
            
        log_event(audit_id, "Parsing", "COCO Dataset", {"path": str(base)}, "parse_coco()", {}, "STARTED", "", "Parsing annotations", "", 0, "RUNNING")
        ds_result = inspect_coco_dataset(ann_path, images_dir, audit_id=audit_id)
        findings = [] 
        records = ds_result["records"]
        
        if records:
            for r in records:
                p = Path(r["path"])
                if p.exists():
                    r["url_path"] = str(p.relative_to(ROOT)).replace('\\', '/')
            with open(REPORTS_DIR / f"records_{audit_id}.json", "w", encoding="utf-8") as f:
                json.dump(records, f)
                
            raw_findings = [
                check_duplicate_flooding(records, audit_id=audit_id),
                check_data_poisoning(records, audit_id=audit_id),
                check_trigger_patterns([Path(r["path"]) for r in records if Path(r["path"]).exists()], audit_id=audit_id)
            ]
            findings.extend([f for f in raw_findings if f["result"] != "PASS"])
            
        from src.integrations.cleanvision_adapter import run_cleanvision_checks
        log_event(audit_id, "Quality Checks", "CleanVision", {"images_dir": str(images_dir)}, "cleanvision.detect()", {}, "STARTED", "", "Running pixel anomaly detection", "", 0, "RUNNING")
        cv_evidence = run_cleanvision_checks(str(images_dir), req.dataset_path)
        for e in cv_evidence:
            findings.append(e.to_dict())

        summary = {
            "dataset_type": "COCO",
            "total_images": ds_result["total_images"],
            "total_annotations": ds_result.get("total_annotations", 0),
            "class_counts": ds_result["class_counts"],
        }
    else:
        log_event(audit_id, "Initialization", "Check Format", {"format": req.format}, "valid_format()", {}, "FALSE", "", "Fail", "", 0, "ERROR", "Unknown format")
        return

    report = generate_report(
        dataset_findings=findings,
        dataset_summary=summary,
        audit_seed=req.seed,
        target_name=req.dataset_path,
    )
    report["records"] = records
    save_report(report, REPORTS_DIR / f"dataset_{audit_id}.json")
    
    log_event(audit_id, "Finalization", "Report Generation", {"report_id": report["report_id"]}, "generate_report()", {}, "COMPLETED", "", "Success", report["report_id"], 0, "PASS")

# ---------------------------------------------------------------------------
# Model audit
# ---------------------------------------------------------------------------
@app.post("/api/audit/model")
def audit_model(req: ModelAuditRequest):
    model_path = ROOT / req.model_path
    if not model_path.exists():
        raise HTTPException(status_code=400, detail=f"Model not found: {req.model_path}")

    ref_manifest = None
    if req.manifest_path:
        mp = ROOT / req.manifest_path
        if mp.exists():
            ref_manifest = load_manifest(mp)

    record = inspect_model(model_path, reference_manifest=ref_manifest)
    hm = record["checks"].get("hash_match", {})
    loadable = record["checks"].get("loadable", {})
    manifest_int = record["checks"].get("manifest_integrity", {})

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
        {
            "check_id": "SEC-MDL-003",
            "name": "Manifest Cryptographic Signature",
            "result": "PASS" if manifest_int.get("result") == "PASS" else
                      "ANOMALY_DETECTED" if manifest_int.get("result") == "FAIL" else
                      manifest_int.get("result", "NOT ASSESSED"),
            "severity": manifest_int.get("severity", "INFO"),
            "confidence": "HIGH",
            "evidence": manifest_int,
            "description": manifest_int.get("detail", ""),
            "recommended_action": "Re-sign manifest if expected. Quarantine if tampered." if manifest_int.get("result") == "FAIL" else "No action required.",
            "limitation": "Requires original signing key.",
        }
    ]
    
    # Execute Upstream Integrations
    from src.integrations.art_adapter import run_art_robustness_probe
    from src.integrations.backdoorbench_adapter import run_backdoorbench_validation
    from src.integrations.trojai_adapter import run_trojai_validation
    from src.integrations.cosign_adapter import verify_cosign_signature
    
    art_ev = run_art_robustness_probe(req.model_path, None, record.get("format", "").lower())
    for e in art_ev: findings.append(e.to_dict())
    
    bdb_ev = run_backdoorbench_validation(req.model_path, "")
    for e in bdb_ev: findings.append(e.to_dict())
    
    trj_ev = run_trojai_validation(req.model_path, "trojai_metadata.json")
    for e in trj_ev: findings.append(e.to_dict())
    
    if req.manifest_path:
        cosign_ev = verify_cosign_signature(req.manifest_path, "public_key.pem", "manifest.sig", req.model_path)
        for e in cosign_ev: findings.append(e.to_dict())

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
    log_path = ROOT / req.log_path
    if not log_path.exists():
        raise HTTPException(status_code=400, detail=f"Log not found: {req.log_path}")

    records = load_inference_log(log_path)
    findings: List[Dict[str, Any]] = []

    for rec in records:
        findings.append(verify_inference_record(rec))
        findings.append(check_inference_replay(rec))
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
    # Initialize to safe defaults to prevent NameError if conditional blocks are skipped
    ds_result: dict = {"records": []}
    records_inf: list = []

    if req.dataset_path:
        base = ROOT / req.dataset_path
        if base.exists():
            imgs = base / "images"
            lbls = base / "labels"
            if not imgs.exists():
                imgs = base
                lbls = base
            ds_result = inspect_yolo_dataset(imgs, lbls)
            records = ds_result["records"]
            all_ds_findings = [f for f in [
                check_duplicate_flooding(records),
                check_data_poisoning(records),
                check_trigger_patterns([Path(r["path"]) for r in records if Path(r["path"]).exists()]),
            ] if f["result"] != "PASS"]
            ds_summary = {"total_images": ds_result["total_images"],
                          "class_counts": ds_result["class_counts"]}

    if req.model_path:
        mp = ROOT / req.model_path
        if mp.exists():
            ref = load_manifest(ROOT / req.manifest_path) if req.manifest_path and (ROOT / req.manifest_path).exists() else None
            record = inspect_model(mp, reference_manifest=ref)
            hm = record["checks"].get("hash_match", {})
            manifest_int = record["checks"].get("manifest_integrity", {})
            all_mdl_findings.append({
                "check_id": "SEC-MDL-001", "name": "Model Substitution / Integrity Check",
                "result": "PASS" if hm.get("result") == "PASS" else "ANOMALY_DETECTED" if hm.get("result") == "FAIL" else hm.get("result", "NOT ASSESSED"),
                "severity": hm.get("severity", "INFO"), "confidence": "HIGH",
                "evidence": hm, "description": hm.get("detail", ""),
                "recommended_action": "Verify model source." if hm.get("result") == "FAIL" else "No action.",
                "limitation": "Hash confirms identity, not safety.",
            })
            all_mdl_findings.append({
                "check_id": "SEC-MDL-003", "name": "Manifest Cryptographic Signature",
                "result": "PASS" if manifest_int.get("result") == "PASS" else "ANOMALY_DETECTED" if manifest_int.get("result") == "FAIL" else manifest_int.get("result", "NOT ASSESSED"),
                "severity": manifest_int.get("severity", "INFO"), "confidence": "HIGH",
                "evidence": manifest_int, "description": manifest_int.get("detail", ""),
                "recommended_action": "Re-sign manifest if expected." if manifest_int.get("result") == "FAIL" else "No action.",
                "limitation": "Requires original signing key.",
            })
            mdl_summary = {"filename": record["filename"], "sha256": record["sha256"]}

    if req.inference_log:
        lp = ROOT / req.inference_log
        if lp.exists():
            records_inf = load_inference_log(lp)
            for rec in records_inf:
                all_inf_findings.append(verify_inference_record(rec))
                all_inf_findings.append(check_inference_replay(rec))
                
    # Execute Cleanlab integration
    from src.integrations.cleanlab_adapter import run_cleanlab_object_detection
    cl_labels = ds_result.get("records", []) if req.dataset_path else []
    cl_preds = records_inf if req.inference_log else []
    if cl_labels and cl_preds:
        cl_ev = run_cleanlab_object_detection(req.dataset_path, cl_labels, cl_preds)
        for e in cl_ev: all_ds_findings.append(e.to_dict())
        
    # Execute In-toto Integration
    from src.integrations.intoto_adapter import InTotoEvidenceChain, generate_intoto_evidence
    chain = InTotoEvidenceChain()
    if req.dataset_path: chain.add_link("dataset_audit", {"dataset": req.dataset_path}, {}, "audit_dataset")
    if req.model_path: chain.add_link("model_verification", {"model": req.model_path}, {}, "audit_model")
    if req.inference_log: chain.add_link("inference", {"log": req.inference_log}, {}, "audit_inference")
    
    intoto_ev = generate_intoto_evidence(chain, "full_audit")
    for e in intoto_ev: all_inf_findings.append(e.to_dict())

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
        "dataset_records": ds_result.get("records", []) if req.dataset_path else [],
        "inference_records": records_inf if req.inference_log else [],
    }

# ---------------------------------------------------------------------------
# Coverage endpoint
# ---------------------------------------------------------------------------
@app.get("/api/coverage")
def get_coverage():
    return COVERAGE

# ---------------------------------------------------------------------------
# Provenance chain verify endpoint
# ---------------------------------------------------------------------------
from src.inference.provenance import verify_provenance_chain

@app.post("/api/provenance/verify-chain")
def verify_chain():
    is_valid, msg, anomalies = verify_provenance_chain()
    if is_valid:
        return {"status": "valid", "message": msg, "anomalies": anomalies}
    else:
        return {"status": "invalid", "message": msg, "anomalies": anomalies}

# ---------------------------------------------------------------------------
# Static UI
# ---------------------------------------------------------------------------
UI_DIR = ROOT / "src" / "ui"

if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    html_path = UI_DIR / "index.html"
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8")
        content = content.replace('href="style.css"', f'href="/static/style.css?v={time.time()}"')
        content = content.replace('src="app.js"', f'src="/static/app.js?v={time.time()}"')
        return HTMLResponse(content)
    return HTMLResponse("<h1>TRUSTTRACE CV</h1><p>UI not found.</p>")

