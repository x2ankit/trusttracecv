"""
src/dataset/security_checks.py

Reproducible security-oriented tests on training datasets.
Each function takes dataset inspection output or raw paths and returns
a structured finding dict with result, evidence, severity, confidence,
and recommended action.

Supported threat scenarios:
  - Poisoning detection (statistical outlier in pixel distribution)
  - Label flipping detection (annotation set comparison vs reference)
  - Duplicate flooding detection (hash-based exact duplicate count)
  - Trigger pattern insertion (uniform patch entropy search)
  - Out-of-distribution (OOD) insertion (Mahalanobis, already in inspector)

Limitations:
  - Statistical methods produce probabilistic signals, not definitive verdicts.
  - Trigger detection searches for low-entropy patches; sophisticated triggers
    may evade this heuristic.
  - Label flipping detection requires a known-good reference annotation set.
  - Does NOT claim to detect all attacks or confirm any attack with certainty.
"""

import hashlib
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

SEVERITY_LEVELS = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_rgb(path: Path) -> Optional[np.ndarray]:
    try:
        with Image.open(path) as img:
            return np.array(img.convert("RGB"), dtype=np.uint8)
    except Exception as exc:
        logger.warning("Cannot open image %s: %s", path, exc)
        return None


def _patch_entropy(patch: np.ndarray) -> float:
    """Shannon entropy of pixel value histogram across all channels."""
    flat = patch.reshape(-1)
    counts = np.bincount(flat, minlength=256)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# 1. Duplicate flooding check
# ---------------------------------------------------------------------------

def check_duplicate_flooding(
    records: List[Dict[str, Any]],
    threshold_pct: float = 0.05,
) -> Dict[str, Any]:
    """
    Detect exact-duplicate images via SHA-256 hash grouping.

    Args:
        records: list of per-image records from inspector.inspect_yolo_dataset
        threshold_pct: fraction of dataset that can be duplicates before flagging

    Returns:
        Finding dict with result, severity, evidence, confidence, recommended_action.
    """
    hash_map: Dict[str, List[str]] = {}
    for rec in records:
        sha = rec.get("sha256")
        if sha and sha != "NOT ASSESSED":
            hash_map.setdefault(sha, []).append(rec["filename"])

    dup_groups = {k: v for k, v in hash_map.items() if len(v) > 1}
    total = len(records)
    dup_count = sum(len(v) - 1 for v in dup_groups.values())
    dup_pct = dup_count / total if total > 0 else 0.0

    result = "PASS"
    severity = "INFO"
    if dup_pct >= threshold_pct:
        result = "ANOMALY_DETECTED"
        severity = "HIGH" if dup_pct >= 0.25 else "MEDIUM"

    return {
        "check_id": "SEC-DS-001",
        "name": "Duplicate Flooding Detection",
        "result": result,
        "severity": severity,
        "confidence": "HIGH",  # hash comparison is deterministic
        "evidence": {
            "total_images": total,
            "duplicate_count": dup_count,
            "duplicate_fraction": round(dup_pct, 4),
            "threshold_fraction": threshold_pct,
            "duplicate_groups": [
                {"sha256_prefix": k[:16] + "...", "files": v}
                for k, v in list(dup_groups.items())[:20]
            ],
        },
        "description": (
            f"{dup_count} exact duplicate image(s) detected ({dup_pct*100:.1f}% of dataset). "
            "Exact-duplicate flooding can bias model training. "
            "This is a deterministic finding based on SHA-256 collision."
        ),
        "recommended_action": (
            "Remove duplicate images and their corresponding labels before training. "
            "Investigate the provenance of duplicates for potential data poisoning intent."
        ),
        "limitation": (
            "Detects only exact byte-for-byte duplicates. Near-duplicates, "
            "perceptually similar images, or watermarked copies will NOT be detected."
        ),
    }


# ---------------------------------------------------------------------------
# 2. Label flipping detection (vs reference)
# ---------------------------------------------------------------------------

def check_label_flipping(
    candidate_annotations: Dict[str, List[Dict]],
    reference_annotations: Dict[str, List[Dict]],
    flip_threshold: float = 0.0,
) -> Dict[str, Any]:
    """
    Compare candidate annotations against a known-good reference set.

    Args:
        candidate_annotations: {filename: [annotation_dicts]}  (candidate)
        reference_annotations: {filename: [annotation_dicts]}  (trusted reference)
        flip_threshold: fraction of mismatches that constitutes a finding

    Returns:
        Finding dict.
    """
    flips: List[Dict] = []
    common_files = set(candidate_annotations) & set(reference_annotations)

    for fname in common_files:
        cand = candidate_annotations[fname]
        ref  = reference_annotations[fname]
        # Compare class IDs at each annotation position
        cand_classes = [a.get("class_id") for a in cand]
        ref_classes  = [a.get("class_id") for a in ref]
        for i, (cc, rc) in enumerate(zip(cand_classes, ref_classes)):
            if cc != rc:
                flips.append({
                    "file": fname,
                    "annotation_index": i,
                    "candidate_class": cc,
                    "reference_class": rc,
                })

    total_compared = sum(
        len(reference_annotations[f]) for f in common_files
    )
    flip_count = len(flips)
    flip_pct = flip_count / total_compared if total_compared > 0 else 0.0

    result = "PASS"
    severity = "INFO"
    if flip_count > 0 and flip_pct >= flip_threshold:
        result = "ANOMALY_DETECTED"
        severity = "CRITICAL" if flip_pct >= 0.10 else "HIGH"

    return {
        "check_id": "SEC-DS-002",
        "name": "Label Flipping Detection",
        "result": result,
        "severity": severity,
        "confidence": "HIGH",  # deterministic comparison against reference
        "evidence": {
            "files_compared": len(common_files),
            "annotations_compared": total_compared,
            "flip_count": flip_count,
            "flip_fraction": round(flip_pct, 4),
            "examples": flips[:20],
        },
        "description": (
            f"{flip_count} class label mismatch(es) detected in {len(common_files)} compared files. "
            "Label flipping can degrade model accuracy or introduce targeted misclassification."
        ),
        "recommended_action": (
            "Verify the provenance of the annotation files. "
            "Re-annotate affected files using trusted sources. "
            "Investigate the annotation pipeline for unauthorised modification."
        ),
        "limitation": (
            "Requires a trusted reference annotation set. "
            "If no reference exists, this check cannot be run (result: NOT ASSESSED). "
            "This check compares only class IDs, not bounding box coordinates."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Trigger pattern insertion (patch-based low-entropy search)
# ---------------------------------------------------------------------------

def check_trigger_patterns(
    image_paths: List[Path],
    patch_size: int = 16,
    entropy_threshold: float = 1.0,
    min_flagged_patches: int = 1,
) -> Dict[str, Any]:
    """
    Search for low-entropy (uniform / near-uniform) rectangular patches
    that may indicate a backdoor trigger inserted into images.

    Limitation: this is a heuristic. Sophisticated triggers with texture
    may have higher entropy and evade detection. Low entropy is a necessary
    but not sufficient condition for trigger insertion.

    Args:
        image_paths: list of image file paths to scan
        patch_size: side length of sliding window (pixels)
        entropy_threshold: patches below this Shannon entropy are flagged
        min_flagged_patches: minimum patch flags per image to report that image
    """
    flagged_images: List[Dict] = []
    error_images: List[str] = []

    for img_path in image_paths:
        arr = _load_rgb(img_path)
        if arr is None:
            error_images.append(str(img_path))
            continue

        h, w, _ = arr.shape
        flagged_patches: List[Dict] = []

        for y in range(0, h - patch_size + 1, patch_size):
            for x in range(0, w - patch_size + 1, patch_size):
                patch = arr[y:y + patch_size, x:x + patch_size]
                ent = _patch_entropy(patch)
                if ent < entropy_threshold:
                    flagged_patches.append({
                        "top_left": [x, y],
                        "size": patch_size,
                        "entropy": round(ent, 4),
                    })

        if len(flagged_patches) >= min_flagged_patches:
            flagged_images.append({
                "filename": img_path.name,
                "flagged_patch_count": len(flagged_patches),
                "patches": flagged_patches[:5],  # cap evidence output
            })

    result = "PASS"
    severity = "INFO"
    if flagged_images:
        result = "ANOMALY_DETECTED"
        severity = "MEDIUM"

    return {
        "check_id": "SEC-DS-003",
        "name": "Trigger Pattern Insertion Detection",
        "result": result,
        "severity": severity,
        "confidence": "LOW",  # heuristic; cannot confirm intentional trigger
        "evidence": {
            "images_scanned": len(image_paths),
            "flagged_images": flagged_images,
            "error_images": error_images,
            "patch_size": patch_size,
            "entropy_threshold": entropy_threshold,
        },
        "description": (
            f"{len(flagged_images)} image(s) contain low-entropy patches "
            f"(Shannon entropy < {entropy_threshold}). "
            "Such patches may indicate a backdoor trigger insertion."
        ),
        "recommended_action": (
            "Visually inspect flagged images. "
            "Cross-reference with annotation provenance. "
            "If trigger candidates are confirmed, quarantine and re-collect from original source."
        ),
        "limitation": (
            "Entropy-based trigger detection is a heuristic with low confidence. "
            "Natural low-texture regions (sky, walls) will also trigger this flag. "
            "Sophisticated texture-based triggers may not be detected. "
            "A positive result indicates an anomaly requiring review, NOT a confirmed attack."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Dataset poisoning (global pixel distribution outlier)
# ---------------------------------------------------------------------------

def check_data_poisoning(
    records: List[Dict[str, Any]],
    z_threshold: float = 3.0,
) -> Dict[str, Any]:
    """
    Detect potential poisoned images via statistical outlier analysis
    on pixel mean / standard deviation vectors.

    Uses Z-score on per-channel means. Images with any channel Z-score
    exceeding z_threshold are flagged.

    Args:
        records: per-image records containing 'pixel_stats'
        z_threshold: number of standard deviations above mean to flag
    """
    pixel_data: List[Tuple[str, np.ndarray]] = []
    for rec in records:
        ps = rec.get("pixel_stats")
        if isinstance(ps, dict):
            vec = np.array([ps["mean_r"], ps["mean_g"], ps["mean_b"],
                            ps["std_r"],  ps["std_g"],  ps["std_b"]])
            pixel_data.append((rec["filename"], vec))

    if len(pixel_data) < 3:
        return {
            "check_id": "SEC-DS-004",
            "name": "Data Poisoning (Statistical Outlier)",
            "result": "NOT ASSESSED",
            "severity": "INFO",
            "confidence": "NOT ASSESSED",
            "evidence": {"reason": "Insufficient samples (< 3) for statistical analysis"},
            "description": "Cannot perform statistical outlier analysis with fewer than 3 images.",
            "recommended_action": "Provide a larger dataset sample for meaningful analysis.",
            "limitation": "Z-score analysis requires sufficient sample size.",
        }

    names = [x[0] for x in pixel_data]
    vecs  = np.stack([x[1] for x in pixel_data])
    means = vecs.mean(axis=0)
    stds  = vecs.std(axis=0)
    stds  = np.where(stds < 1e-9, 1e-9, stds)  # avoid division by zero
    z_scores = np.abs((vecs - means) / stds)

    flagged: List[Dict] = []
    for i, (name, z_vec) in enumerate(zip(names, z_scores)):
        max_z = float(z_vec.max())
        if max_z > z_threshold:
            flagged.append({
                "filename": name,
                "max_z_score": round(max_z, 4),
                "channel_z_scores": {
                    "mean_r": round(float(z_vec[0]), 4),
                    "mean_g": round(float(z_vec[1]), 4),
                    "mean_b": round(float(z_vec[2]), 4),
                    "std_r":  round(float(z_vec[3]), 4),
                    "std_g":  round(float(z_vec[4]), 4),
                    "std_b":  round(float(z_vec[5]), 4),
                },
            })

    result = "PASS"
    severity = "INFO"
    if flagged:
        result = "STATISTICAL_SHIFT"
        severity = "MEDIUM"

    return {
        "check_id": "SEC-DS-004",
        "name": "Distribution Shift (Statistical Outlier)",
        "result": result,
        "severity": severity,
        "confidence": "LOW",
        "evidence": {
            "images_analysed": len(pixel_data),
            "z_threshold": z_threshold,
            "flagged_images": flagged,
        },
        "description": (
            f"{len(flagged)} image(s) have pixel statistics more than {z_threshold} "
            "standard deviations from the dataset mean. "
            "Statistical outliers may indicate injected poisoned samples."
        ),
        "recommended_action": (
            "Review flagged images for unusual content, overlaid objects, or synthetic artifacts. "
            "Investigate collection pipeline for unauthorised modifications."
        ),
        "limitation": (
            "Z-score outlier detection is a weak signal. "
            "Systematic poisoning of many images may shift the mean and evade detection. "
            "A positive result indicates an anomaly, NOT a confirmed poisoned sample."
        ),
    }
