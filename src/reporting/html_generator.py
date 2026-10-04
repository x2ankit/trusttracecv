import json
import base64
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent.resolve()
REPORTS_DIR = ROOT / "reports"

def generate_offline_html_report(audit_id: str) -> str:
    # Load dataset report
    dataset_report_path = REPORTS_DIR / f"dataset_{audit_id}.json"
    if not dataset_report_path.exists():
        # Fallback to the latest dataset report
        reports = sorted(REPORTS_DIR.glob("dataset_*.json"), key=os.path.getmtime, reverse=True)
        if reports:
            dataset_report_path = reports[0]
    
    if not dataset_report_path:
        # Check if audit_id matches directly
        pass # Handle not found
    
    with open(dataset_report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
        
    records_path = REPORTS_DIR / f"records_{audit_id}.json"
    records = []
    if records_path.exists():
        with open(records_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    elif "records" in report:
        records = report["records"]
        
    events_path = ROOT / "audit_events.sqlite"
    # To get events, we should ideally fetch from DB. 
    # But since we have access to the DB, we can just query it.
    import sqlite3
    events = []
    if events_path.exists():
        conn = sqlite3.connect(events_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_events WHERE audit_id = ? ORDER BY timestamp_utc ASC, id ASC", (audit_id,))
        for row in cursor.fetchall():
            events.append(dict(row))
        conn.close()

    summary = report.get("dataset_summary", {})
    findings = report.get("dataset_findings", [])
    if "sections" in report:
        summary = report.get("summary", {})
        findings = []
        for sec in report["sections"].values():
            findings.extend(sec.get("findings", []))
            
    # Helper to encode images - prefer relative url_path over absolute path
    def get_data_uri(rec):
        # Prefer relative url_path (set during audit), fall back to absolute path field
        rel = rec.get("url_path") or rec.get("path", "")
        if not rel: return ""
        # If it looks absolute, try resolving via ROOT
        p = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if not p.exists(): return ""
        ext = p.suffix.lower()[1:]
        if ext == 'jpg': ext = 'jpeg'
        try:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/{ext};base64,{b64}"
        except Exception:
            return ""

    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html><head><meta charset='utf-8'><title>TRUSTTRACE CV Assurance Report</title>")
    html.append("<style>")
    html.append("""
        body { font-family: 'Segoe UI', system-ui, sans-serif; padding: 20px; background: #f8fafc; color: #1e293b; max-width: 1200px; margin: 0 auto; line-height: 1.6; }
        .card { background: white; padding: 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; border: 1px solid #e2e8f0; }
        .pass { color: #10b981; font-weight: bold; }
        .fail { color: #ef4444; font-weight: bold; }
        .warn { color: #f59e0b; font-weight: bold; }
        h1, h2, h3 { color: #0f172a; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
        th { background: #f1f5f9; font-weight: 600; }
        .img-container { position: relative; display: inline-block; max-width: 100%; }
        .img-container img { max-width: 100%; height: auto; display: block; }
        .bbox { position: absolute; border: 2px solid #ef4444; pointer-events: none; }
        .bbox-label { background: #ef4444; color: white; font-size: 10px; padding: 1px 3px; position: absolute; top: -16px; left: -2px; white-space: nowrap; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 20px; }
        .col-half { flex: 1; min-width: 300px; }
    """)
    html.append("</style></head><body>")

    # A. REPORT HEADER
    html.append(f"<div class='card'>")
    html.append(f"<h1>TRUSTTRACE CV - Computer Vision Integrity Assurance Report</h1>")
    html.append(f"<table>")
    html.append(f"<tr><th>Audit ID</th><td>{audit_id}</td></tr>")
    html.append(f"<tr><th>Timestamp</th><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>")
    html.append(f"<tr><th>Dataset Format</th><td>{summary.get('dataset_type', 'Unknown')}</td></tr>")
    html.append(f"<tr><th>Images Analyzed</th><td>{summary.get('total_images', len(records))}</td></tr>")
    html.append(f"</table></div>")

    # B. EXECUTIVE SUMMARY
    html.append(f"<div class='card'><h2>Executive Summary</h2>")
    html.append(f"<table><tr><th>Severity</th><th>Finding Category</th><th>Description / Remediation</th></tr>")
    if not findings:
        html.append(f"<tr><td colspan='3' class='pass'>✅ No malicious triggers, duplicate flooding, or data poisoning artifacts were found in this dataset.</td></tr>")
    else:
        for f in findings:
            html.append(f"<tr><td><strong class='{'fail' if f.get('severity') == 'CRITICAL' else 'warn'}'>{f.get('severity', 'WARNING')}</strong></td><td>{f.get('category', f.get('finding', ''))}</td><td>{f.get('remediation', '')}</td></tr>")
    html.append(f"</table></div>")

    # C. IMAGE-BY-IMAGE FORENSIC RECORDS
    html.append(f"<div class='card'><h2>Image-by-Image Forensic Records</h2>")
    for rec in records:
        html.append(f"<div class='card' style='background: #f8fafc; border: 1px solid #cbd5e1;'>")
        html.append(f"<div class='flex-row'>")
        
        # Left Column: Image with BBoxes
        data_uri = get_data_uri(rec)
        html.append(f"<div class='col-half'>")
        if data_uri:
            html.append(f"<div class='img-container'>")
            html.append(f"<img src='{data_uri}' alt='{rec.get('filename')}'>")
            # Draw bboxes
            orig_w = rec.get("width")
            orig_h = rec.get("height")
            if orig_w and orig_h:
                for ann in rec.get("annotations", []):
                    if "bbox" in ann:
                        x, y, w, h = ann["bbox"]
                        left = (x / orig_w) * 100
                        top = (y / orig_h) * 100
                        width = (w / orig_w) * 100
                        height = (h / orig_h) * 100
                        html.append(f"<div class='bbox' style='left:{left}%; top:{top}%; width:{width}%; height:{height}%;'><span class='bbox-label'>{ann.get('class_name', ann.get('class_id', ''))}</span></div>")
                    elif "x_center" in ann:
                        xc, yc, w, h = ann["x_center"], ann["y_center"], ann["width"], ann["height"]
                        left = (xc - w/2) * 100
                        top = (yc - h/2) * 100
                        width = w * 100
                        height = h * 100
                        html.append(f"<div class='bbox' style='left:{left}%; top:{top}%; width:{width}%; height:{height}%;'><span class='bbox-label'>{ann.get('class_name', ann.get('class_id', ''))}</span></div>")
            html.append(f"</div>")
        else:
            html.append(f"<p>Image bytes unavailable.</p>")
        html.append(f"</div>")
        
        # Right Column: Metadata
        html.append(f"<div class='col-half'>")
        html.append(f"<h3>{rec.get('filename')}</h3>")
        html.append(f"<table>")
        html.append(f"<tr><th>Resolution</th><td>{rec.get('width', '-')} x {rec.get('height', '-')}</td></tr>")
        html.append(f"<tr><th>SHA-256</th><td style='word-break: break-all;'>{rec.get('sha256', 'NOT ASSESSED')}</td></tr>")
        html.append(f"<tr><th>Annotations</th><td>{len(rec.get('annotations', []))} objects</td></tr>")
        
        # Checks performed on this image
        if "checks" in rec and rec["checks"]:
            html.append(f"<tr><td colspan='2'><strong>Checks</strong><br>")
            for k, v in rec["checks"].items():
                res = v.get("result", "")
                html.append(f"{k}: <span class='{'pass' if res=='PASS' else 'fail' if res=='FAIL' else 'warn'}'>{res}</span><br>")
            html.append(f"</td></tr>")
            
        html.append(f"</table>")
        
        # Annotation details
        if rec.get("annotations"):
            html.append(f"<h4 style='margin-top:10px;'>Annotations</h4>")
            html.append(f"<table><tr><th>Class</th><th>BBox</th></tr>")
            for ann in rec.get("annotations"):
                bbox_str = str(ann.get("bbox", "")) if "bbox" in ann else f"xc:{ann.get('x_center')} yc:{ann.get('y_center')} w:{ann.get('width')} h:{ann.get('height')}"
                html.append(f"<tr><td>{ann.get('class_name', ann.get('class_id', ''))}</td><td>{bbox_str}</td></tr>")
            html.append(f"</table>")
            
        html.append(f"</div>") # end col-half
        
        html.append(f"</div>") # end flex-row
        html.append(f"</div>") # end card
    html.append(f"</div>")
    
    # G. COMPLETE EXECUTION HISTORY
    html.append(f"<div class='card'><h2>Complete Execution History</h2>")
    html.append(f"<table><tr><th>Time</th><th>Operation</th><th>Observation</th><th>Result</th></tr>")
    for ev in events:
        ts = ""
        if "timestamp_utc" in ev and isinstance(ev.get("timestamp_utc"), (int, float)):
            ts = datetime.fromtimestamp(ev["timestamp_utc"]).strftime('%H:%M:%S')
        stat = ev.get('status', '')
        cls = 'pass' if stat == 'PASS' else 'fail' if stat in ['FAIL', 'ERROR'] else 'warn'
        html.append(f"<tr><td>{ts}</td><td>{ev.get('stage')} - {ev.get('operation')}</td><td>{ev.get('result')}</td><td><strong class='{cls}'>{stat}</strong></td></tr>")
    html.append(f"</table></div>")
    
    html.append("</body></html>")
    
    return "\n".join(html)

