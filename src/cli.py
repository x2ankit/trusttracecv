"""
src/cli.py

TRUSTTRACE CV command-line interface.

Usage examples:
  python -m src.cli audit-dataset --dataset-dir data/fixtures/clean
  python -m src.cli audit-model   --model-path models/fixtures/dummy_detector.pt
  python -m src.cli audit-all     --config config/audit_config.yaml
  python -m src.cli generate-report --report-path reports/latest.json

All commands:
  audit-dataset   Inspect a YOLO or COCO dataset for integrity issues.
  audit-model     Inspect a model artifact for integrity.
  audit-inference Verify an inference log file.
  audit-all       Run the full audit pipeline and generate a report.
  generate-report Re-generate a report from a saved audit results file.

Options:
  --seed INT       Random seed for reproducibility (default: 42)
  --output-dir DIR Directory to save reports and logs (default: reports/)
"""

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Local imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dataset.inspector import inspect_yolo_dataset, inspect_coco_dataset
from src.dataset.security_checks import (
    check_duplicate_flooding,
    check_label_flipping,
    check_trigger_patterns,
    check_data_poisoning,
)
from src.models.integrity import inspect_model, load_manifest, check_model_substitution
from src.inference.verifier import (
    load_inference_log,
    verify_inference_record,
    check_inference_replay,
    check_backdoor_behaviour,
)
from src.reporting.report_generator import generate_report, save_report

console = Console()
app     = typer.Typer(
    name="trusttrace-cv",
    help="TRUSTTRACE CV – SIH26228 Assurance System for Computer Vision Pipelines",
    no_args_is_help=True,
)

logging.basicConfig(level=logging.WARNING)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEVERITY_COLOURS = {
    "CRITICAL": "bold red",
    "HIGH":     "red",
    "MEDIUM":   "yellow",
    "LOW":      "cyan",
    "INFO":     "dim",
}
RESULT_COLOURS = {
    "PASS":             "green",
    "ANOMALY_DETECTED": "red",
    "FAIL":             "bold red",
    "NOT ASSESSED":     "dim",
    "INCONCLUSIVE":     "yellow",
}


def _print_findings(findings: list, title: str = "Findings") -> None:
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Check ID",   style="bold cyan", width=16)
    table.add_column("Name",       width=40)
    table.add_column("Result",     width=20)
    table.add_column("Severity",   width=10)
    table.add_column("Confidence", width=12)
    for f in findings:
        result = f.get("result", "")
        sev    = f.get("severity", "")
        table.add_row(
            f.get("check_id", ""),
            f.get("name", ""),
            f"[{RESULT_COLOURS.get(result, '')}]{result}[/]",
            f"[{SEVERITY_COLOURS.get(sev, '')}]{sev}[/]",
            f.get("confidence", ""),
        )
    console.print(table)


def _verdict_panel(verdict: str) -> None:
    colour = RESULT_COLOURS.get(verdict, "white")
    console.print(Panel(
        f"[{colour}][bold]{verdict}[/bold][/{colour}]",
        title="[bold]Overall Assurance Verdict[/bold]",
        border_style=colour,
    ))


# ---------------------------------------------------------------------------
# audit-dataset command
# ---------------------------------------------------------------------------

@app.command("audit-dataset")
def audit_dataset(
    dataset_dir: Path = typer.Option(..., help="Root of YOLO dataset (must contain images/ and labels/)"),
    format:      str  = typer.Option("yolo", help="Dataset format: yolo | coco"),
    annotations: Optional[Path] = typer.Option(None, help="COCO annotations JSON path (for coco format)"),
    output_dir:  Path = typer.Option(Path("reports"), help="Output directory for report"),
    seed:        int  = typer.Option(42, help="Random seed"),
) -> None:
    """Inspect a dataset for integrity, duplicates, OOD samples, and security anomalies."""
    console.rule("[bold blue]TRUSTTRACE CV — Dataset Audit[/bold blue]")

    if format == "yolo":
        images_dir = dataset_dir / "images"
        labels_dir = dataset_dir / "labels"
        if not images_dir.exists():
            console.print(f"[red]ERROR: images/ not found in {dataset_dir}[/red]")
            raise typer.Exit(1)

        console.print(f"Inspecting YOLO dataset at [bold]{dataset_dir}[/bold]")
        ds_result = inspect_yolo_dataset(images_dir, labels_dir)
        records   = ds_result["records"]

        findings: list = []
        findings.append(check_duplicate_flooding(records))
        findings.append(check_data_poisoning(records))
        image_paths = [images_dir / r["filename"] for r in records]
        findings.append(check_trigger_patterns(image_paths))

        console.print(f"\n[bold]Dataset Summary:[/bold]")
        console.print(f"  Total images : {ds_result['total_images']}")
        console.print(f"  Class counts : {ds_result['class_counts']}")

    elif format == "coco":
        if annotations is None:
            console.print("[red]ERROR: --annotations required for coco format[/red]")
            raise typer.Exit(1)
        console.print(f"Inspecting COCO dataset at [bold]{annotations}[/bold]")
        ds_result = inspect_coco_dataset(annotations, images_dir=dataset_dir / "images" if dataset_dir else None)
        records   = []
        findings  = []
        console.print(f"\n[bold]COCO Summary:[/bold] {ds_result['total_images']} images, "
                      f"{ds_result['total_annotations']} annotations")
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)

    _print_findings(findings, title="Dataset Security Findings")

    report = generate_report(
        dataset_findings=findings,
        dataset_summary={"total_images": ds_result.get("total_images", 0)},
        audit_seed=seed,
        target_name=str(dataset_dir),
    )
    output_path = output_dir / f"dataset_audit_{report['report_id'][:8]}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    save_report(report, output_path)
    _verdict_panel(report["verdict"])
    console.print(f"\nReport saved to [bold]{output_path}[/bold]")


# ---------------------------------------------------------------------------
# audit-model command
# ---------------------------------------------------------------------------

@app.command("audit-model")
def audit_model(
    model_path:  Path          = typer.Option(..., help="Path to model artifact (.pt/.pth/.onnx)"),
    manifest:    Optional[Path] = typer.Option(None, help="Path to reference manifest JSON"),
    output_dir:  Path          = typer.Option(Path("reports"), help="Output directory"),
    seed:        int           = typer.Option(42),
) -> None:
    """Inspect a model artifact for integrity and detect substitution."""
    console.rule("[bold blue]TRUSTTRACE CV — Model Audit[/bold blue]")

    ref_manifest = load_manifest(manifest) if manifest and manifest.exists() else None
    if manifest and not manifest.exists():
        console.print(f"[yellow]WARN: manifest not found at {manifest}, skipping hash comparison[/yellow]")

    record = inspect_model(model_path, reference_manifest=ref_manifest)

    console.print(f"\n[bold]Model:[/bold] {record['filename']}")
    console.print(f"  Format     : {record['format']}")
    console.print(f"  Size       : {record['size_bytes']:,} bytes" if record['size_bytes'] else "  Size: UNKNOWN")
    console.print(f"  SHA-256    : {record['sha256']}")

    findings: list = []
    # Build a finding from the hash_match check
    hm = record["checks"].get("hash_match", {})
    findings.append({
        "check_id":  "SEC-MDL-001",
        "name":      "Model Substitution / Integrity Check",
        "result":    "PASS" if hm.get("result") == "PASS" else
                     "ANOMALY_DETECTED" if hm.get("result") == "FAIL" else
                     hm.get("result", "NOT ASSESSED"),
        "severity":  hm.get("severity", "INFO"),
        "confidence": "HIGH",
        "evidence":  hm,
        "description": hm.get("detail", ""),
        "recommended_action": (
            "Obtain model from original trusted source and re-verify."
            if hm.get("result") == "FAIL" else "No action required."
        ),
        "limitation": (
            "SHA-256 hash confirms file identity, NOT model safety."
        ),
    })
    loadable = record["checks"].get("loadable", {})
    findings.append({
        "check_id": "SEC-MDL-002",
        "name":     "Model Structural Validation",
        "result":   loadable.get("result", "NOT ASSESSED"),
        "severity": "HIGH" if loadable.get("result") == "FAIL" else "INFO",
        "confidence": "HIGH",
        "evidence": {"metadata": record["metadata"]},
        "description": loadable.get("detail", "Model loaded successfully."),
        "recommended_action": (
            "Investigate model file corruption or incompatible format."
            if loadable.get("result") == "FAIL" else "No action required."
        ),
        "limitation": "Loading does not verify semantic correctness of weights.",
    })

    _print_findings(findings, title="Model Security Findings")

    report = generate_report(
        model_findings=findings,
        model_summary={"filename": record["filename"], "format": record["format"],
                       "sha256": record["sha256"]},
        audit_seed=seed,
        target_name=str(model_path),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"model_audit_{report['report_id'][:8]}.json"
    save_report(report, out)
    _verdict_panel(report["verdict"])
    console.print(f"\nReport saved to [bold]{out}[/bold]")


# ---------------------------------------------------------------------------
# audit-inference command
# ---------------------------------------------------------------------------

@app.command("audit-inference")
def audit_inference(
    log_path:   Path = typer.Option(..., help="Path to inference JSONL log"),
    output_dir: Path = typer.Option(Path("reports")),
    seed:       int  = typer.Option(42),
) -> None:
    """Verify inference records for tampering and replay attacks."""
    console.rule("[bold blue]TRUSTTRACE CV — Inference Audit[/bold blue]")

    records = load_inference_log(log_path)
    if not records:
        console.print(f"[yellow]No inference records found in {log_path}[/yellow]")
        raise typer.Exit(0)

    console.print(f"Loaded [bold]{len(records)}[/bold] inference records from {log_path}")

    findings: list = []
    seen_hashes: set = set()

    for rec in records:
        findings.append(verify_inference_record(rec))
        findings.append(check_inference_replay(rec, seen_hashes))
        if rec.get("payload_hash"):
            seen_hashes.add(rec["payload_hash"])
        preds = rec.get("predictions", [])
        bb = check_backdoor_behaviour(preds)
        if bb["result"] != "PASS":
            findings.append(bb)

    _print_findings(findings, title="Inference Security Findings")

    report = generate_report(
        inference_findings=findings,
        audit_seed=seed,
        target_name=str(log_path),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"inference_audit_{report['report_id'][:8]}.json"
    save_report(report, out)
    _verdict_panel(report["verdict"])
    console.print(f"\nReport saved to [bold]{out}[/bold]")


# ---------------------------------------------------------------------------
# audit-all command
# ---------------------------------------------------------------------------

@app.command("audit-all")
def audit_all(
    dataset_dir:  Optional[Path] = typer.Option(None, help="YOLO dataset root"),
    model_path:   Optional[Path] = typer.Option(None, help="Model artifact path"),
    manifest:     Optional[Path] = typer.Option(None, help="Model manifest JSON"),
    inference_log: Optional[Path] = typer.Option(None, help="Inference JSONL log"),
    output_dir:   Path           = typer.Option(Path("reports"), help="Report output dir"),
    seed:         int            = typer.Option(42),
) -> None:
    """Run the full audit pipeline: dataset + model + inference."""
    console.rule("[bold blue]TRUSTTRACE CV — Full Audit Pipeline[/bold blue]")

    all_dataset_findings: list = []
    all_model_findings:   list = []
    all_inf_findings:     list = []
    dataset_summary = {}
    model_summary   = {}

    # --- Dataset ---
    if dataset_dir and dataset_dir.exists():
        images_dir = dataset_dir / "images"
        labels_dir = dataset_dir / "labels"
        ds_result = inspect_yolo_dataset(images_dir, labels_dir)
        records   = ds_result["records"]
        all_dataset_findings.append(check_duplicate_flooding(records))
        all_dataset_findings.append(check_data_poisoning(records))
        all_dataset_findings.append(check_trigger_patterns(
            [images_dir / r["filename"] for r in records]))
        dataset_summary = {"total_images": ds_result["total_images"],
                           "class_counts": ds_result["class_counts"]}
    else:
        console.print("[yellow]No dataset directory provided or found; skipping dataset audit.[/yellow]")

    # --- Model ---
    if model_path and model_path.exists():
        ref_manifest = load_manifest(manifest) if manifest and manifest.exists() else None
        record = inspect_model(model_path, reference_manifest=ref_manifest)
        hm = record["checks"].get("hash_match", {})
        all_model_findings.append({
            "check_id": "SEC-MDL-001", "name": "Model Substitution / Integrity Check",
            "result": "PASS" if hm.get("result") == "PASS" else
                      "ANOMALY_DETECTED" if hm.get("result") == "FAIL" else
                      hm.get("result", "NOT ASSESSED"),
            "severity": hm.get("severity", "INFO"), "confidence": "HIGH",
            "evidence": hm,
            "description": hm.get("detail", ""),
            "recommended_action": "Obtain from trusted source and re-verify." if hm.get("result") == "FAIL" else "No action required.",
            "limitation": "Hash confirms identity, not safety.",
        })
        model_summary = {"filename": record["filename"], "sha256": record["sha256"]}
    else:
        console.print("[yellow]No model path provided or found; skipping model audit.[/yellow]")

    # --- Inference ---
    if inference_log and inference_log.exists():
        records_inf = load_inference_log(inference_log)
        seen: set = set()
        for rec in records_inf:
            all_inf_findings.append(verify_inference_record(rec))
            all_inf_findings.append(check_inference_replay(rec, seen))
            if rec.get("payload_hash"):
                seen.add(rec["payload_hash"])
    else:
        console.print("[yellow]No inference log provided; skipping inference audit.[/yellow]")

    _print_findings(all_dataset_findings + all_model_findings + all_inf_findings,
                    title="All Security Findings")

    report = generate_report(
        dataset_findings=all_dataset_findings,
        model_findings=all_model_findings,
        inference_findings=all_inf_findings,
        dataset_summary=dataset_summary,
        model_summary=model_summary,
        audit_seed=seed,
        target_name="Full Audit",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"full_audit_{report['report_id'][:8]}.json"
    save_report(report, out)
    _verdict_panel(report["verdict"])
    console.print(f"\nFull report saved to [bold]{out}[/bold]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
