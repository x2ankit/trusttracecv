import logging
import torch
import uuid
import numpy as np
from typing import List, Dict, Any, Tuple
from src.evidence.correlator import Evidence

logger = logging.getLogger(__name__)

def generate_behavioral_fingerprint(model_id: str, model: Any, images: List[np.ndarray], framework: str = "pytorch") -> Dict[str, Any]:
    """
    Generates a behavioral fingerprint for a model using a reference battery of images.
    """
    fingerprint = {
        "framework": framework,
        "battery_size": len(images),
        "white_box_assessed": False,
        "black_box_assessed": True,
        "black_box_metrics": {},
        "white_box_metrics": {}
    }
    
def calculate_black_box_fingerprint(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates black-box behavioral fingerprint metrics from a set of model predictions.
    """
    if not predictions:
        return {
            "mean_object_count": 0.0,
            "confidence_distribution_mean": 0.0,
            "bbox_area_mean": 0.0,
            "bbox_center_x_mean": 0.0,
            "bbox_center_y_mean": 0.0,
            "no_object_rate": 1.0,
            "class_frequencies": {}
        }

    # predictions could be grouped by image if passed as a flat list
    img_preds = {}
    for p in predictions:
        img_id = p.get("image_id", "unknown")
        img_preds.setdefault(img_id, []).append(p)

    total_images = len(img_preds)
    if total_images == 0:
        total_images = 1 # avoid div zero
        
    no_obj_count = 0
    total_objects = 0
    confidences = []
    areas = []
    center_xs = []
    center_ys = []
    class_freqs = {}

    for img_id, preds in img_preds.items():
        if not preds or (len(preds) == 1 and "bbox" not in preds[0]):
            no_obj_count += 1
            continue
            
        total_objects += len(preds)
        for p in preds:
            c = p.get("class_id", "unknown")
            class_freqs[c] = class_freqs.get(c, 0) + 1
            if "score" in p:
                confidences.append(p["score"])
            elif "confidence" in p:
                confidences.append(p["confidence"])
                
            if "bbox" in p and len(p["bbox"]) == 4:
                x, y, w, h = p["bbox"]
                areas.append(w * h)
                center_xs.append(x + w / 2)
                center_ys.append(y + h / 2)

    return {
        "mean_object_count": total_objects / total_images,
        "confidence_distribution_mean": float(np.mean(confidences)) if confidences else 0.0,
        "confidence_distribution_std": float(np.std(confidences)) if confidences else 0.0,
        "bbox_area_mean": float(np.mean(areas)) if areas else 0.0,
        "bbox_center_x_mean": float(np.mean(center_xs)) if center_xs else 0.0,
        "bbox_center_y_mean": float(np.mean(center_ys)) if center_ys else 0.0,
        "no_object_rate": no_obj_count / total_images,
        "class_frequencies": class_freqs
    }

def generate_behavioral_fingerprint(model_id: str, model: Any, images: List[np.ndarray], framework: str = "pytorch") -> Dict[str, Any]:
    """
    Generates a behavioral fingerprint for a model using a reference battery of images.
    """
    fingerprint = {
        "framework": framework,
        "battery_size": len(images),
        "white_box_assessed": False,
        "black_box_assessed": True,
        "black_box_metrics": {},
        "white_box_metrics": {}
    }
    
    # In a real scenario, we would run model(images) and pass to calculate_black_box_fingerprint
    # For now, just mark it as not fully assessed dynamically here, we'll call calculate_black_box_fingerprint directly on logs
    fingerprint["black_box_metrics"] = calculate_black_box_fingerprint([])
    
    # 2. White Box Fingerprint
    if framework == "pytorch" and isinstance(model, torch.nn.Module):
        fingerprint["white_box_assessed"] = True
        total_params = sum(p.numel() for p in model.parameters())
        
        # Calculate parameter statistics
        l1_norm = sum(p.abs().sum().item() for p in model.parameters())
        l2_norm = sum((p ** 2).sum().item() for p in model.parameters()) ** 0.5
        max_val = max(p.abs().max().item() for p in model.parameters() if p.numel() > 0)
        
        # Determine dtype distribution
        dtype_dist = {}
        for p in model.parameters():
            dt = str(p.dtype)
            dtype_dist[dt] = dtype_dist.get(dt, 0) + p.numel()
            
        fingerprint["white_box_metrics"] = {
            "parameter_count": total_params,
            "parameter_l1_norm": l1_norm,
            "parameter_l2_norm": l2_norm,
            "max_abs_val": max_val,
            "dtype_distribution": dtype_dist,
            # Activations would require forward hooks, omitted in this stub
        }
        
    return fingerprint

def evaluate_fingerprint_divergence(model_id: str, candidate_fingerprint: Dict[str, Any], reference_fingerprint: Dict[str, Any]) -> List[Evidence]:
    """
    Evaluates if a candidate model's fingerprint diverges from a reference model.
    """
    evidence_list = []
    
    # Compare white box metrics if both are white box
    if candidate_fingerprint.get("white_box_assessed") and reference_fingerprint.get("white_box_assessed"):
        cand_wb = candidate_fingerprint["white_box_metrics"]
        ref_wb = reference_fingerprint["white_box_metrics"]
        
        if cand_wb.get("parameter_count") != ref_wb.get("parameter_count"):
            evidence = Evidence(
                evidence_id=f"BHF_{uuid.uuid4().hex[:8]}",
                asset_id=model_id,
                finding_type="BEHAVIORAL_DIVERGENCE",
                category="MODEL_BEHAVIOR",
                method="white_box_fingerprint",
                status="FLAGGED",
                severity="HIGH",
                confidence_basis="Deterministic parameter count mismatch",
                observations=f"Parameter count mismatch: {cand_wb.get('parameter_count')} vs {ref_wb.get('parameter_count')}",
                limitations="EVIDENCE OF DIVERGENCE, not CONFIRMED BACKDOOR.",
                recommended_action="QUARANTINE - Model architecture/size was altered."
            )
            evidence_list.append(evidence)
            
        # L2 norm divergence
        if abs(cand_wb.get("parameter_l2_norm", 0) - ref_wb.get("parameter_l2_norm", 0)) > 1e-4:
            evidence = Evidence(
                evidence_id=f"BHF_{uuid.uuid4().hex[:8]}",
                asset_id=model_id,
                finding_type="BEHAVIORAL_DIVERGENCE",
                category="MODEL_BEHAVIOR",
                method="white_box_fingerprint",
                status="FLAGGED",
                severity="MEDIUM",
                confidence_basis="L2 norm difference",
                observations="Parameter L2 norm diverges from reference. Weights were likely modified (fine-tuned/poisoned).",
                limitations="EVIDENCE OF DIVERGENCE, not CONFIRMED BACKDOOR. Fine-tuning also causes this.",
                recommended_action="REVIEW - Determine if fine-tuning was authorized."
            )
            evidence_list.append(evidence)
            
    return evidence_list
