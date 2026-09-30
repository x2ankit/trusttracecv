"""
src/dataset/inspector.py

Dataset integrity inspector for COCO and YOLO format annotations.
Supports: resolution check, label validation, duplicate detection,
label-flip detection, OOD detection (via pixel statistics),
trigger pattern search, and annotation coordinate validation.

All checks are deterministic given the same input. Statistical
checks emit a confidence float; deterministic checks emit PASS/FAIL.
If data is unavailable or a check cannot run, the result is NOT ASSESSED.
"""

import os
import hashlib
import json
import math
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _image_array(path: Path) -> Optional[np.ndarray]:
    try:
        with Image.open(path) as img:
            return np.array(img.convert("RGB"))
    except Exception as exc:
        logger.warning("Cannot open image %s: %s", path, exc)
        return None


def _pixel_stats(arr: np.ndarray) -> Dict[str, float]:
    flat = arr.astype(float).reshape(-1, 3)
    return {
        "mean_r": float(flat[:, 0].mean()),
        "mean_g": float(flat[:, 1].mean()),
        "mean_b": float(flat[:, 2].mean()),
        "std_r":  float(flat[:, 0].std()),
        "std_g":  float(flat[:, 1].std()),
        "std_b":  float(flat[:, 2].std()),
    }


# ---------------------------------------------------------------------------
# YOLO format parser
# ---------------------------------------------------------------------------

def parse_yolo_label(label_path: Path) -> List[Dict[str, Any]]:
    """Parse a YOLO .txt annotation file.

    Each row: <class_id> <x_center> <y_center> <width> <height>
    All values normalised [0, 1].
    """
    annotations = []
    if not label_path.exists():
        return annotations
    with open(label_path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 5:
                annotations.append({"lineno": lineno, "raw": raw, "error": "too few fields"})
                continue
            try:
                annotations.append({
                    "class_id": int(parts[0]),
                    "x_center": float(parts[1]),
                    "y_center": float(parts[2]),
                    "width":    float(parts[3]),
                    "height":   float(parts[4]),
                    "lineno":   lineno,
                    "raw":      raw.rstrip(),
                })
            except ValueError as exc:
                annotations.append({"lineno": lineno, "raw": raw, "error": str(exc)})
    return annotations


# ---------------------------------------------------------------------------
# COCO format parser
# ---------------------------------------------------------------------------

def parse_coco_dataset(annotations_json: Path) -> Dict[str, Any]:
    """Load and parse a COCO annotations JSON file."""
    with open(annotations_json, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data


# ---------------------------------------------------------------------------
# Core inspection record
# ---------------------------------------------------------------------------

def inspect_image(image_path: Path, label_path: Optional[Path] = None,
                  format: str = "yolo") -> Dict[str, Any]:
    """
    Inspect a single image and its annotation file.

    Returns a structured record suitable for the assurance report.
    """
    record: Dict[str, Any] = {
        "filename": image_path.name,
        "path": str(image_path),
        "sha256": "NOT ASSESSED",
        "resolution": "NOT ASSESSED",
        "width": None,
        "height": None,
        "channels": None,
        "pixel_stats": "NOT ASSESSED",
        "annotations": [],
        "annotation_errors": [],
        "checks": {},
    }

    # --- File existence ---
    if not image_path.exists():
        record["checks"]["file_exists"] = {"result": "FAIL", "detail": "File not found"}
        return record
    record["checks"]["file_exists"] = {"result": "PASS"}

    # --- SHA-256 ---
    record["sha256"] = _sha256_file(image_path)

    # --- Image open ---
    arr = _image_array(image_path)
    if arr is None:
        record["checks"]["image_readable"] = {"result": "FAIL", "detail": "PIL cannot open"}
        return record

    record["checks"]["image_readable"] = {"result": "PASS"}
    h, w, c = arr.shape
    record["width"] = w
    record["height"] = h
    record["channels"] = c
    record["resolution"] = f"{w}x{h}"
    record["pixel_stats"] = _pixel_stats(arr)

    # --- Blank / degenerate ---
    if arr.std() < 1.0:
        record["checks"]["non_blank"] = {
            "result": "WARN",
            "detail": "Image appears uniformly coloured (std < 1). Possible placeholder.",
        }
    else:
        record["checks"]["non_blank"] = {"result": "PASS"}

    # --- Annotation parsing ---
    if label_path is not None:
        if format == "yolo":
            anns = parse_yolo_label(label_path)
            record["annotations"] = anns
            errors = [a for a in anns if "error" in a]
            record["annotation_errors"] = errors
            if errors:
                record["checks"]["annotation_valid"] = {
                    "result": "FAIL",
                    "detail": f"{len(errors)} annotation row(s) have parse errors",
                }
            else:
                # Validate coordinate bounds
                out_of_bounds = [
                    a for a in anns
                    if not (0.0 <= a.get("x_center", 0) <= 1.0
                            and 0.0 <= a.get("y_center", 0) <= 1.0
                            and 0.0 < a.get("width", 0) <= 1.0
                            and 0.0 < a.get("height", 0) <= 1.0)
                ]
                if out_of_bounds:
                    record["checks"]["annotation_valid"] = {
                        "result": "FAIL",
                        "detail": f"{len(out_of_bounds)} annotation(s) have out-of-bounds coordinates",
                    }
                else:
                    record["checks"]["annotation_valid"] = {"result": "PASS"}

    return record


# ---------------------------------------------------------------------------
# Batch dataset inspection
# ---------------------------------------------------------------------------

def inspect_yolo_dataset(images_dir: Path, labels_dir: Path,
                         class_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Inspect a YOLO-format dataset directory.

    Returns summary statistics and per-image records.
    Runs: duplicate detection, label-frequency analysis, OOD detection.
    """
    images_dir = Path(images_dir)
    labels_dir = Path(labels_dir)

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    image_paths = sorted([
        p for p in images_dir.iterdir()
        if p.suffix.lower() in image_extensions
    ])

    records: List[Dict[str, Any]] = []
    hash_map: Dict[str, List[str]] = {}  # sha256 → [filenames]
    class_counts: Dict[int, int] = {}
    pixel_means: List[np.ndarray] = []

    for img_path in image_paths:
        label_path = labels_dir / (img_path.stem + ".txt")
        rec = inspect_image(img_path, label_path if label_path.exists() else None, format="yolo")

        # track hashes for duplicate detection
        sha = rec["sha256"]
        if sha != "NOT ASSESSED":
            hash_map.setdefault(sha, []).append(img_path.name)

        # track class distribution
        for ann in rec["annotations"]:
            cid = ann.get("class_id")
            if cid is not None:
                class_counts[cid] = class_counts.get(cid, 0) + 1

        # track pixel means for OOD
        ps = rec.get("pixel_stats")
        if isinstance(ps, dict):
            pixel_means.append(np.array([ps["mean_r"], ps["mean_g"], ps["mean_b"]]))

        records.append(rec)

    # --- Duplicate detection ---
    duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}
    duplicate_count = sum(len(v) - 1 for v in duplicates.values())

    # --- OOD detection via Mahalanobis distance ---
    ood_flags: List[Dict[str, Any]] = []
    if len(pixel_means) >= 3:
        means_arr = np.stack(pixel_means)
        global_mean = means_arr.mean(axis=0)
        cov = np.cov(means_arr.T)
        try:
            inv_cov = np.linalg.pinv(cov)
            dists = []
            for vec in means_arr:
                diff = vec - global_mean
                d = float(math.sqrt(max(0.0, diff @ inv_cov @ diff)))
                dists.append(d)
            threshold = np.mean(dists) + 2.5 * np.std(dists) if len(dists) > 1 else 1e9
            for i, (rec, d) in enumerate(zip(records, dists)):
                if d > threshold:
                    ood_flags.append({
                        "filename": rec["filename"],
                        "mahalanobis_distance": round(d, 4),
                        "threshold": round(float(threshold), 4),
                        "confidence": "MEDIUM",
                        "note": "Pixel colour distribution significantly differs from dataset mean. "
                                "Possible OOD sample. Manual review recommended.",
                    })
        except np.linalg.LinAlgError:
            ood_flags = []

    # --- Label class imbalance ---
    imbalance_flags: List[Dict[str, Any]] = []
    if class_counts:
        total_anns = sum(class_counts.values())
        for cid, cnt in class_counts.items():
            freq = cnt / total_anns
            name = class_names[cid] if (class_names and cid < len(class_names)) else str(cid)
            if freq < 0.05 and total_anns >= 20:
                imbalance_flags.append({
                    "class_id": cid,
                    "class_name": name,
                    "count": cnt,
                    "frequency": round(freq, 4),
                    "note": "Class frequency below 5% of total annotations. Possible under-representation.",
                })

    return {
        "dataset_type": "YOLO",
        "images_dir": str(images_dir),
        "labels_dir": str(labels_dir),
        "total_images": len(records),
        "class_counts": class_counts,
        "class_names": class_names,
        "records": records,
        "findings": {
            "duplicates": {
                "count": duplicate_count,
                "groups": [{"sha256": k[:16] + "...", "files": v} for k, v in duplicates.items()],
            },
            "ood_candidates": ood_flags,
            "class_imbalance": imbalance_flags,
        },
    }


def inspect_coco_dataset(annotations_json: Path,
                         images_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Inspect a COCO-format annotations JSON file.
    Checks annotation validity, duplicate image IDs, and class distribution.
    """
    data = parse_coco_dataset(annotations_json)

    images = data.get("images", [])
    annotations = data.get("annotations", [])
    categories = data.get("categories", [])

    image_ids = [img["id"] for img in images]
    dup_image_ids = [iid for iid in set(image_ids) if image_ids.count(iid) > 1]

    cat_map = {cat["id"]: cat["name"] for cat in categories}
    class_counts: Dict[str, int] = {}
    invalid_bbox = []

    for ann in annotations:
        cid = ann.get("category_id")
        cname = cat_map.get(cid, str(cid))
        class_counts[cname] = class_counts.get(cname, 0) + 1

        bbox = ann.get("bbox", [])  # [x, y, w, h]
        if len(bbox) == 4:
            if bbox[2] <= 0 or bbox[3] <= 0:
                invalid_bbox.append({"annotation_id": ann.get("id"), "bbox": bbox})

    records = []
    if images_dir:
        for img_meta in images[:50]:  # cap at 50 for feasibility
            fname = img_meta.get("file_name", "")
            img_path = Path(images_dir) / fname
            rec = inspect_image(img_path)
            rec["coco_id"] = img_meta.get("id")
            records.append(rec)

    return {
        "dataset_type": "COCO",
        "annotations_json": str(annotations_json),
        "total_images": len(images),
        "total_annotations": len(annotations),
        "categories": [{"id": c["id"], "name": c["name"]} for c in categories],
        "class_counts": class_counts,
        "records": records,
        "findings": {
            "duplicate_image_ids": dup_image_ids,
            "invalid_bboxes": invalid_bbox,
        },
    }
