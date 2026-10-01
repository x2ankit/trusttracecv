import numpy as np
import logging
from PIL import Image, ImageEnhance
from io import BytesIO
from typing import List, Dict, Any
from src.models.runtime import predict
from src.models.performance import calculate_iou

logger = logging.getLogger(__name__)

def apply_transforms(image: np.ndarray) -> Dict[str, np.ndarray]:
    """Applies a deterministic set of mild transformations to an image."""
    img_pil = Image.fromarray(image)
    transforms = {}
    
    # 1. Resize
    w, h = img_pil.size
    transforms["resize"] = np.array(img_pil.resize((int(w * 0.9), int(h * 0.9))).resize((w, h)))
    
    # 2. Brightness
    enhancer = ImageEnhance.Brightness(img_pil)
    transforms["brightness_up"] = np.array(enhancer.enhance(1.2))
    
    # 3. Contrast
    enhancer = ImageEnhance.Contrast(img_pil)
    transforms["contrast_down"] = np.array(enhancer.enhance(0.8))
    
    # 4. JPEG compression
    buffer = BytesIO()
    img_pil.save(buffer, format="JPEG", quality=75)
    buffer.seek(0)
    transforms["jpeg_compression"] = np.array(Image.open(buffer))
    
    # 5. Mild noise
    noise = np.random.randint(-15, 15, size=image.shape, dtype=np.int16)
    noisy = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    transforms["mild_noise"] = noisy
    
    return transforms

def compare_predictions(ref_preds: List[Dict[str, Any]], cand_preds: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compares two sets of predictions for consistency."""
    # Simplified comparison: object count difference, mean confidence diff, mean max IoU
    count_diff = abs(len(ref_preds) - len(cand_preds))
    
    ref_conf = np.mean([p.get("confidence", 0.0) for p in ref_preds]) if ref_preds else 0.0
    cand_conf = np.mean([p.get("confidence", 0.0) for p in cand_preds]) if cand_preds else 0.0
    conf_diff = abs(ref_conf - cand_conf)
    
    ious = []
    for rp in ref_preds:
        max_iou = 0.0
        for cp in cand_preds:
            if "bbox" in rp and "bbox" in cp:
                iou = calculate_iou(rp["bbox"], cp["bbox"])
                if iou > max_iou:
                    max_iou = iou
        ious.append(max_iou)
    
    mean_iou = np.mean(ious) if ious else 1.0 if not ref_preds and not cand_preds else 0.0
    
    return {
        "count_diff": count_diff,
        "conf_diff": conf_diff,
        "mean_iou": mean_iou
    }

def run_controlled_transformation_battery(model: Any, model_type: str, reference_images: List[np.ndarray]) -> Dict[str, Any]:
    """Runs a candidate model against controlled transformations to ensure stability."""
    results = {}
    total_count_diff = 0
    total_conf_diff = 0.0
    total_iou = 0.0
    tests = 0
    
    for img in reference_images:
        base_preds = predict(model, model_type, img)
        transforms = apply_transforms(img)
        
        for t_name, t_img in transforms.items():
            t_preds = predict(model, model_type, t_img)
            comp = compare_predictions(base_preds, t_preds)
            
            total_count_diff += comp["count_diff"]
            total_conf_diff += comp["conf_diff"]
            total_iou += comp["mean_iou"]
            tests += 1
            
    if tests > 0:
        avg_count_diff = total_count_diff / tests
        avg_conf_diff = total_conf_diff / tests
        avg_iou = total_iou / tests
    else:
        avg_count_diff, avg_conf_diff, avg_iou = 0, 0, 0
        
    thresholds = {
        "max_avg_count_diff": 1.0,
        "max_avg_conf_diff": 0.15,
        "min_avg_iou": 0.5
    }
    
    diverged = False
    if avg_count_diff > thresholds["max_avg_count_diff"]:
        diverged = True
    if avg_conf_diff > thresholds["max_avg_conf_diff"]:
        diverged = True
    if avg_iou < thresholds["min_avg_iou"]:
        diverged = True
        
    return {
        "result": "BEHAVIORAL_DIVERGENCE" if diverged else "BEHAVIORALLY_CONSISTENT",
        "metrics": {
            "avg_count_diff": avg_count_diff,
            "avg_conf_diff": avg_conf_diff,
            "avg_iou": avg_iou
        },
        "thresholds": thresholds
    }
