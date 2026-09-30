"""
scripts/generate_fixtures.py

Deterministic fixture generator for TRUSTTRACE CV tests.
Uses a fixed random seed (42). Creates:
  - Clean YOLO dataset (10 images, labels)
  - Duplicate flooding dataset (3 duplicates injected)
  - Label-flipped dataset (reference + flipped version)
  - Trigger-pattern dataset (low-entropy patch inserted in 2 images)
  - OOD dataset (2 images with abnormal colour statistics)
  - COCO format annotations JSON
  - Dummy PyTorch state dict model

All images are synthetic (100x100 RGB), generated offline.
No external downloads required.

Citation: all fixtures are team-generated synthetic data.
License: MIT (project internal).
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import random
import shutil
import struct
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SEED = 42
rng  = random.Random(SEED)
np_rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "fixtures"
MODELS_DIR = ROOT / "models" / "fixtures"

CLASS_NAMES = ["cat", "dog", "car", "bus"]


# ---------------------------------------------------------------------------
# Image & label helpers
# ---------------------------------------------------------------------------

def _random_rgb() -> tuple:
    return (rng.randint(30, 220), rng.randint(30, 220), rng.randint(30, 220))


def _synthetic_image(width: int = 100, height: int = 100,
                     bg: tuple = None, seed_extra: int = 0) -> Image.Image:
    """Create a synthetic RGB image with random noise for high pixel entropy.

    Random-noise images have ~7-8 bits of Shannon entropy per channel, which
    provides clear contrast with the ~0-bit solid trigger patches.
    """
    _np_rng = np.random.default_rng(SEED + seed_extra)
    # Gaussian noise centred on a random mean, clipped to [20, 235]
    centre = _np_rng.integers(60, 200, size=3)
    arr = _np_rng.normal(loc=centre, scale=40, size=(height, width, 3))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _yolo_line(class_id: int, cx: float = 0.5, cy: float = 0.5,
               w: float = 0.3, h: float = 0.3) -> str:
    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def _save_yolo_pair(img: Image.Image, label_line: str,
                    images_dir: Path, labels_dir: Path,
                    stem: str) -> None:
    img.save(images_dir / f"{stem}.jpg")
    with open(labels_dir / f"{stem}.txt", "w") as fh:
        fh.write(label_line + "\n")


# ---------------------------------------------------------------------------
# 1. Clean dataset (baseline)
# ---------------------------------------------------------------------------

def generate_clean_dataset():
    imgs = DATA / "clean" / "images"
    lbls = DATA / "clean" / "labels"
    imgs.mkdir(parents=True, exist_ok=True)
    lbls.mkdir(parents=True, exist_ok=True)

    class_map: dict = {}
    for i in range(10):
        cid = i % len(CLASS_NAMES)
        img = _synthetic_image(seed_extra=i)
        cx  = round(0.3 + (i % 5) * 0.08, 4)
        cy  = round(0.3 + (i % 3) * 0.12, 4)
        _save_yolo_pair(img, _yolo_line(cid, cx, cy), imgs, lbls, f"img_{i:04d}")
        class_map[f"img_{i:04d}"] = cid

    # Save class names
    with open(DATA / "clean" / "classes.txt", "w") as fh:
        fh.write("\n".join(CLASS_NAMES))

    # Save reference annotation manifest (ground truth for label-flip test)
    with open(DATA / "clean" / "annotations_reference.json", "w") as fh:
        json.dump(class_map, fh, indent=2)
    print("[OK] Clean dataset: 10 images")


# ---------------------------------------------------------------------------
# 2. Duplicate flooding dataset
# ---------------------------------------------------------------------------

def generate_duplicate_dataset():
    imgs = DATA / "duplicates" / "images"
    lbls = DATA / "duplicates" / "labels"
    imgs.mkdir(parents=True, exist_ok=True)
    lbls.mkdir(parents=True, exist_ok=True)

    # Copy clean images
    clean_imgs = sorted((DATA / "clean" / "images").glob("*.jpg"))[:7]
    clean_lbls = DATA / "clean" / "labels"
    for src in clean_imgs:
        shutil.copy(src, imgs / src.name)
        shutil.copy(clean_lbls / (src.stem + ".txt"), lbls / (src.stem + ".txt"))

    # Inject 3 exact duplicates of img_0000
    src_img = imgs / "img_0000.jpg"
    src_lbl = lbls / "img_0000.txt"
    for j in range(1, 4):
        shutil.copy(src_img, imgs / f"dup_{j:04d}.jpg")
        shutil.copy(src_lbl, lbls / f"dup_{j:04d}.txt")

    print("[OK] Duplicate dataset: 7 clean + 3 exact duplicates")


# ---------------------------------------------------------------------------
# 3. Label-flipped dataset
# ---------------------------------------------------------------------------

def generate_label_flip_dataset():
    imgs = DATA / "label_flip" / "images"
    lbls_clean  = DATA / "label_flip" / "labels_clean"
    lbls_flipped = DATA / "label_flip" / "labels_flipped"

    imgs.mkdir(parents=True, exist_ok=True)
    lbls_clean.mkdir(parents=True, exist_ok=True)
    lbls_flipped.mkdir(parents=True, exist_ok=True)

    # Copy 8 clean images
    clean_imgs = sorted((DATA / "clean" / "images").glob("*.jpg"))[:8]
    clean_lbls = DATA / "clean" / "labels"

    for src in clean_imgs:
        shutil.copy(src, imgs / src.name)
        shutil.copy(clean_lbls / (src.stem + ".txt"), lbls_clean / (src.stem + ".txt"))

    # Flip labels for files 3, 5 (change class_id)
    flipped_files = {"img_0003", "img_0005"}
    for src in clean_imgs:
        src_lbl = lbls_clean / (src.stem + ".txt")
        with open(src_lbl, "r") as fh:
            line = fh.read().strip()
        parts = line.split()
        if src.stem in flipped_files:
            orig_cid = int(parts[0])
            flipped_cid = (orig_cid + 1) % len(CLASS_NAMES)
            parts[0] = str(flipped_cid)
        with open(lbls_flipped / (src.stem + ".txt"), "w") as fh:
            fh.write(" ".join(parts) + "\n")

    print("[OK] Label-flip dataset: 8 images, 2 labels flipped")


# ---------------------------------------------------------------------------
# 4. Trigger pattern dataset
# ---------------------------------------------------------------------------

def generate_trigger_dataset():
    imgs = DATA / "triggers" / "images"
    lbls = DATA / "triggers" / "labels"
    imgs.mkdir(parents=True, exist_ok=True)
    lbls.mkdir(parents=True, exist_ok=True)

    clean_imgs = sorted((DATA / "clean" / "images").glob("*.jpg"))
    clean_lbls = DATA / "clean" / "labels"

    triggered_files = {"img_0002", "img_0007"}

    for src in clean_imgs:
        img = Image.open(src).copy()
        shutil.copy(clean_lbls / (src.stem + ".txt"), lbls / (src.stem + ".txt"))

        if src.stem in triggered_files:
            # Inject a 20x20 solid red (zero entropy) patch in bottom-right.
            # Save as BMP (completely lossless, no compression) to guarantee
            # that the solid patch has exactly zero Shannon entropy.
            arr = np.array(img)
            arr[-25:-5, -25:-5] = [255, 0, 0]   # solid red 20x20
            img = Image.fromarray(arr)
            out_name = src.stem + ".bmp"   # BMP: no compression whatsoever
        else:
            out_name = src.name

        img.save(imgs / out_name)

    print("[OK] Trigger dataset: 10 images, 2 BMP with inserted 20x20 solid red patch")


# ---------------------------------------------------------------------------
# 5. OOD dataset (near-infrared or grayscale-ish images mixed in)
# ---------------------------------------------------------------------------

def generate_ood_dataset():
    imgs = DATA / "ood" / "images"
    lbls = DATA / "ood" / "labels"
    imgs.mkdir(parents=True, exist_ok=True)
    lbls.mkdir(parents=True, exist_ok=True)

    clean_imgs = sorted((DATA / "clean" / "images").glob("*.jpg"))
    clean_lbls = DATA / "clean" / "labels"

    ood_files = {"img_0004", "img_0008"}

    for src in clean_imgs:
        img = Image.open(src).copy()
        shutil.copy(clean_lbls / (src.stem + ".txt"), lbls / (src.stem + ".txt"))

        if src.stem in ood_files:
            # Make image nearly grayscale (very different from colourful dataset mean)
            arr = np.array(img)
            gray_val = int(arr.mean())
            arr[:] = [gray_val, gray_val, gray_val]
            img = Image.fromarray(arr.astype(np.uint8))

        img.save(imgs / src.name)

    print("[OK] OOD dataset: 10 images, 2 near-grayscale OOD")


# ---------------------------------------------------------------------------
# 6. COCO format annotations
# ---------------------------------------------------------------------------

def generate_coco_annotations():
    coco_dir = DATA / "coco"
    coco_dir.mkdir(parents=True, exist_ok=True)

    images_list = []
    annotations_list = []
    ann_id = 1

    for i in range(8):
        cid_yolo = i % len(CLASS_NAMES)
        images_list.append({
            "id": i + 1,
            "file_name": f"img_{i:04d}.jpg",
            "width": 100,
            "height": 100,
        })
        annotations_list.append({
            "id": ann_id,
            "image_id": i + 1,
            "category_id": cid_yolo + 1,
            "bbox": [30, 30, 30, 30],  # [x, y, w, h]
            "area": 900,
            "iscrowd": 0,
        })
        ann_id += 1

    # Add a duplicate image id (for duplicate detection test)
    images_list.append({
        "id": 1,  # duplicate of first image
        "file_name": "img_0000_dup.jpg",
        "width": 100,
        "height": 100,
    })

    coco = {
        "info": {"description": "TRUSTTRACE CV fixture", "year": 2026},
        "licenses": [],
        "images": images_list,
        "annotations": annotations_list,
        "categories": [
            {"id": idx + 1, "name": name, "supercategory": "object"}
            for idx, name in enumerate(CLASS_NAMES)
        ],
    }

    with open(coco_dir / "annotations.json", "w") as fh:
        json.dump(coco, fh, indent=2)
    print("[OK] COCO annotations fixture")


# ---------------------------------------------------------------------------
# 7. Dummy PyTorch model + manifest
# ---------------------------------------------------------------------------

def generate_model_fixtures():
    import torch
    import torch.nn as nn

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(SEED)

    class DummyDetector(nn.Module):
        """Tiny 2-layer conv net mimicking a trivial detector."""
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 8, 3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),
            )
            self.classifier = nn.Linear(8, len(CLASS_NAMES))

        def forward(self, x):
            x = self.features(x)
            x = x.flatten(1)
            return self.classifier(x)

    model = DummyDetector()
    pt_path = MODELS_DIR / "dummy_detector.pt"
    torch.save(model.state_dict(), pt_path)

    # TorchScript
    ts_path = MODELS_DIR / "dummy_detector_ts.pt"
    scripted = torch.jit.script(model)
    scripted.save(str(ts_path))

    # ONNX export
    try:
        import torch.onnx
        dummy_input = torch.zeros(1, 3, 100, 100)
        onnx_path = MODELS_DIR / "dummy_detector.onnx"
        torch.onnx.export(
            model, dummy_input, str(onnx_path),
            opset_version=11,
            input_names=["input"],
            output_names=["output"],
        )
        print("[OK] ONNX model exported")
    except Exception as exc:
        print(f"[WARN] ONNX export failed: {exc}")

    # Build and save manifest
    import hashlib
    manifest = {}
    for p in MODELS_DIR.glob("*"):
        if p.is_file():
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            manifest[p.name] = h.hexdigest()

    with open(MODELS_DIR / "manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2)

    print(f"[OK] Model fixtures: state_dict, TorchScript, ONNX, manifest")


# ---------------------------------------------------------------------------
# 8. Inference records
# ---------------------------------------------------------------------------

def generate_inference_fixtures():
    import sys
    sys.path.insert(0, str(ROOT))
    from src.inference.verifier import record_inference
    import json

    log_dir = DATA / "inference_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for i in range(5):
        preds = [{"class_id": i % 4, "score": round(0.7 + i * 0.05, 3),
                  "bbox": [10, 10, 40, 40]}]
        rec = record_inference(
            image_id=f"img_{i:04d}",
            model_id="dummy_detector_sha256_fixture",
            predictions=preds,
        )
        records.append(rec)

    # Overwrite (not append) to avoid duplication on re-runs
    log_path = log_dir / "inference_log.jsonl"
    with open(log_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    print("[OK] Inference fixtures: 5 signed records")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Generating TRUSTTRACE CV fixtures...")
    generate_clean_dataset()
    generate_duplicate_dataset()
    generate_label_flip_dataset()
    generate_trigger_dataset()
    generate_ood_dataset()
    generate_coco_annotations()
    generate_model_fixtures()
    generate_inference_fixtures()
    print("\nAll fixtures generated successfully.")
    print(f"  Data:   {DATA}")
    print(f"  Models: {MODELS_DIR}")
