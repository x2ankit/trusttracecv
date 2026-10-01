import logging
import torch
import uuid
import numpy as np
from typing import List, Dict, Any, Tuple
from src.evidence.correlator import Evidence
from src.models.runtime import predict

logger = logging.getLogger(__name__)

class ActivationStatsHook:
    def __init__(self):
        self.means = []
        self.variances = []
        self.sparsities = []

    def hook(self, module, input, output):
        with torch.no_grad():
            if isinstance(output, torch.Tensor):
                out_flat = output.detach().float().view(-1)
                self.means.append(out_flat.mean().item())
                self.variances.append(out_flat.var().item() if out_flat.numel() > 1 else 0.0)
                self.sparsities.append((out_flat == 0).float().mean().item())

def calculate_black_box_fingerprint(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates black-box behavioral fingerprint metrics from a set of model predictions.
    """
    if not predictions:
        return {
            "mean_object_count": 0.0,
            "object_count_std": 0.0,
            "confidence_distribution_mean": 0.0,
            "confidence_distribution_std": 0.0,
            "bbox_area_mean": 0.0,
            "bbox_center_x_mean": 0.0,
            "bbox_center_y_mean": 0.0,
            "no_object_rate": 1.0,
            "class_frequencies": {}
        }

    img_preds = {}
    for p in predictions:
        img_id = p.get("image_id", "unknown")
        img_preds.setdefault(img_id, []).append(p)

    total_images = len(img_preds)
    if total_images == 0:
        total_images = 1 # avoid div zero
        
    no_obj_count = 0
    total_objects = 0
    obj_counts_per_image = []
    confidences = []
    areas = []
    center_xs = []
    center_ys = []
    class_freqs = {}

    for img_id, preds in img_preds.items():
        if not preds or (len(preds) == 1 and "bbox" not in preds[0]):
            no_obj_count += 1
            obj_counts_per_image.append(0)
            continue
            
        obj_count = len(preds)
        total_objects += obj_count
        obj_counts_per_image.append(obj_count)
        
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
        "object_count_std": float(np.std(obj_counts_per_image)) if obj_counts_per_image else 0.0,
        "confidence_distribution_mean": float(np.mean(confidences)) if confidences else 0.0,
        "confidence_distribution_std": float(np.std(confidences)) if confidences else 0.0,
        "bbox_area_mean": float(np.mean(areas)) if areas else 0.0,
        "bbox_center_x_mean": float(np.mean(center_xs)) if center_xs else 0.0,
        "bbox_center_y_mean": float(np.mean(center_ys)) if center_ys else 0.0,
        "no_object_rate": no_obj_count / total_images,
        "class_frequencies": class_freqs
    }

def generate_behavioral_fingerprint(model_id: str, model: Any, model_type: str, images: List[np.ndarray], framework: str = "pytorch") -> Dict[str, Any]:
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
    
    # 1. Black Box Fingerprint
    predictions = []
    
    # Run active inference loop
    for idx, img in enumerate(images):
        preds = predict(model, model_type, img)
        # Normalize sorting by confidence descending
        preds.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
        for p in preds:
            p["image_id"] = str(idx)
            predictions.append(p)
            
    if not predictions and len(images) > 0:
        # We did run inference, but produced no detections
        fingerprint["black_box_metrics"] = calculate_black_box_fingerprint([{"image_id": str(i)} for i in range(len(images))])
    else:
        fingerprint["black_box_metrics"] = calculate_black_box_fingerprint(predictions)
    
    # 2. White Box Fingerprint
    if framework == "pytorch" and isinstance(model, torch.nn.Module):
        fingerprint["white_box_assessed"] = True
        total_params = sum(p.numel() for p in model.parameters())
        
        # Calculate parameter statistics
        l1_norm = sum(p.abs().sum().item() for p in model.parameters())
        l2_norm = sum((p ** 2).sum().item() for p in model.parameters()) ** 0.5
        max_val = max((p.abs().max().item() for p in model.parameters() if p.numel() > 0), default=0.0)
        
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
        }
        
        # Activations
        hook_obj = ActivationStatsHook()
        handles = []
        for name, module in model.named_modules():
            if isinstance(module, (torch.nn.Conv2d, torch.nn.Linear)):
                handles.append(module.register_forward_hook(hook_obj.hook))
                
        # Run a small forward pass on first image to get activation stats
        if len(images) > 0:
            # We must be careful not to crash if the model inputs are weird, but try our best
            try:
                img = images[0]
                import PIL.Image
                img_resized = PIL.Image.fromarray(img).resize((100, 100))
                img_tensor = torch.from_numpy(np.array(img_resized)).float().permute(2, 0, 1).unsqueeze(0) / 255.0
                with torch.no_grad():
                    model(img_tensor)
            except Exception as e:
                logger.warning(f"Failed to run forward pass for activation stats: {e}")
                
        for handle in handles:
            handle.remove()
            
        fingerprint["white_box_metrics"]["activation_mean"] = np.mean(hook_obj.means) if hook_obj.means else 0.0
        fingerprint["white_box_metrics"]["activation_variance"] = np.mean(hook_obj.variances) if hook_obj.variances else 0.0
        fingerprint["white_box_metrics"]["activation_sparsity"] = np.mean(hook_obj.sparsities) if hook_obj.sparsities else 0.0
    else:
        fingerprint["white_box_metrics"] = {
            "parameter_count": "NOT_ASSESSED",
            "parameter_l1_norm": "NOT_ASSESSED",
            "parameter_l2_norm": "NOT_ASSESSED",
            "max_abs_val": "NOT_ASSESSED",
            "dtype_distribution": "NOT_ASSESSED",
            "activation_mean": "NOT_ASSESSED",
            "activation_variance": "NOT_ASSESSED",
            "activation_sparsity": "NOT_ASSESSED",
        }
        
    return fingerprint

def evaluate_fingerprint_divergence(
    reference_model_id: str, 
    candidate_model_id: str, 
    reference_model_sha256: str,
    candidate_model_sha256: str,
    reference_dataset_id: str,
    candidate_fingerprint: Dict[str, Any], 
    reference_fingerprint: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates if a candidate model's fingerprint diverges from a reference model.
    """
    divergences = []
    metrics = {}
    
    # 1. Black Box Compare
    cand_bb = candidate_fingerprint["black_box_metrics"]
    ref_bb = reference_fingerprint["black_box_metrics"]
    
    diff_obj_count = abs(cand_bb["mean_object_count"] - ref_bb["mean_object_count"])
    diff_conf = abs(cand_bb["confidence_distribution_mean"] - ref_bb["confidence_distribution_mean"])
    diff_no_obj = abs(cand_bb["no_object_rate"] - ref_bb["no_object_rate"])
    
    metrics["black_box"] = {
        "diff_mean_object_count": diff_obj_count,
        "diff_confidence_distribution_mean": diff_conf,
        "diff_no_object_rate": diff_no_obj,
        "cand_class_frequencies": cand_bb["class_frequencies"],
        "ref_class_frequencies": ref_bb["class_frequencies"]
    }
    
    # Thresholds
    thresholds = {
        "max_diff_mean_object_count": 0.5,
        "max_diff_confidence": 0.1,
        "max_diff_no_object_rate": 0.1
    }
    
    if diff_obj_count > thresholds["max_diff_mean_object_count"]:
        divergences.append(f"Mean object count diverged: {diff_obj_count:.3f} > {thresholds['max_diff_mean_object_count']}")
    if diff_conf > thresholds["max_diff_confidence"]:
        divergences.append(f"Confidence mean diverged: {diff_conf:.3f} > {thresholds['max_diff_confidence']}")
    if diff_no_obj > thresholds["max_diff_no_object_rate"]:
        divergences.append(f"No-object rate diverged: {diff_no_obj:.3f} > {thresholds['max_diff_no_object_rate']}")
        
    # 2. White Box Compare
    if candidate_fingerprint.get("white_box_assessed") and reference_fingerprint.get("white_box_assessed"):
        cand_wb = candidate_fingerprint["white_box_metrics"]
        ref_wb = reference_fingerprint["white_box_metrics"]
        
        metrics["white_box"] = {}
        
        if cand_wb.get("parameter_count") != ref_wb.get("parameter_count"):
            divergences.append(f"Parameter count mismatch: {cand_wb.get('parameter_count')} vs {ref_wb.get('parameter_count')}")
            metrics["white_box"]["parameter_count_diff"] = True
            
        if "parameter_l2_norm" in cand_wb and "parameter_l2_norm" in ref_wb and isinstance(cand_wb["parameter_l2_norm"], float):
            l2_diff = abs(cand_wb["parameter_l2_norm"] - ref_wb["parameter_l2_norm"])
            metrics["white_box"]["diff_l2_norm"] = l2_diff
            if l2_diff > 1e-4:
                divergences.append(f"L2 norm diverged: {l2_diff:.6f} > 1e-4")
                
    result = "BEHAVIORAL_DIVERGENCE" if divergences else "BEHAVIORALLY_CONSISTENT"
    if not candidate_fingerprint.get("black_box_assessed") or candidate_fingerprint["battery_size"] == 0:
        result = "NOT_ASSESSED"

    return {
        "reference_model_id": reference_model_id,
        "candidate_model_id": candidate_model_id,
        "reference_model_sha256": reference_model_sha256,
        "candidate_model_sha256": candidate_model_sha256,
        "reference_dataset_id": reference_dataset_id,
        "number_of_images": candidate_fingerprint["battery_size"],
        "result": result,
        "metrics": metrics,
        "thresholds": thresholds,
        "observations": divergences if divergences else ["Models exhibit consistent behavioral profiles."],
        "limitations": "Behavioral consistency does not guarantee safety. True functional equivalence is not proven."
    }
