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
    
    # 1. Black Box Fingerprint
    # We simulate running inference if it's an actual model or just return a structure
    # In real scenario: M_test(X)
    
    # Mock black box metrics since we might not have a real model loaded in this function
    # or the model might just be an ONNX path.
    fingerprint["black_box_metrics"] = {
        "mean_object_count": 0.0,
        "confidence_distribution_mean": 0.0,
        "confidence_distribution_std": 0.0,
        "bbox_area_mean": 0.0,
        "bbox_center_x_mean": 0.0,
        "bbox_center_y_mean": 0.0,
        "no_object_rate": 0.0,
    }
    
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
