import logging
import uuid
import numpy as np
from typing import List, Dict, Any, Callable
from src.evidence.correlator import Evidence

logger = logging.getLogger(__name__)

def generate_triggers() -> List[Dict[str, Any]]:
    """
    Finite, transparent candidate trigger library.
    """
    return [
        {"name": "solid_patch_bottom_right", "type": "patch", "size": (16, 16), "loc": "bottom_right", "color": (255, 0, 0)},
        {"name": "high_contrast_square_center", "type": "patch", "size": (32, 32), "loc": "center", "color": (255, 255, 255)},
        {"name": "blended_noise_patch", "type": "noise", "size": (24, 24), "loc": "top_left"}
    ]

def apply_trigger(image: np.ndarray, trigger: Dict[str, Any]) -> np.ndarray:
    """
    Applies a trigger to an image.
    """
    img_copy = image.copy()
    h, w = img_copy.shape[:2]
    th, tw = trigger["size"]
    
    # Bound check
    if h < th or w < tw:
        return img_copy
        
    loc = trigger["loc"]
    if loc == "bottom_right":
        y, x = h - th, w - tw
    elif loc == "center":
        y, x = (h - th) // 2, (w - tw) // 2
    elif loc == "top_left":
        y, x = 0, 0
    else:
        y, x = 0, 0
        
    if trigger["type"] == "patch":
        color = trigger.get("color", (255, 255, 255))
        img_copy[y:y+th, x:x+tw] = color
    elif trigger["type"] == "noise":
        noise = np.random.randint(0, 256, (th, tw, 3), dtype=np.uint8)
        img_copy[y:y+th, x:x+tw] = (img_copy[y:y+th, x:x+tw] * 0.5 + noise * 0.5).astype(np.uint8)
        
    return img_copy

def probe_trigger_sensitivity(model_id: str, model_inference_fn: Callable, reference_images: List[np.ndarray]) -> List[Evidence]:
    """
    Probes model behavior against a trigger library using reference images.
    """
    evidence_list = []
    triggers = generate_triggers()
    
    # In a full implementation, we would run model_inference_fn on clean_images and triggered_images
    # and compare the outputs (prediction_change_rate, detection_drop_rate, etc.)
    # Here we simulate the result.
    
    simulated_sensitivity = False
    
    if simulated_sensitivity:
        evidence = Evidence(
            evidence_id=f"TRG_{uuid.uuid4().hex[:8]}",
            asset_id=model_id,
            finding_type="TRIGGER_SENSITIVITY",
            category="MODEL_BEHAVIOR",
            method="trigger_probe",
            status="FLAGGED",
            severity="MEDIUM",
            confidence_basis="Deterministic response to localized trigger",
            observations="Model exhibited a repeated deterministic response to 'solid_patch_bottom_right' trigger (prediction_change_rate > 80%).",
            limitations="Potential trigger-sensitive behavior; not sufficient by itself to establish a backdoor.",
            recommended_action="REVIEW - Probe target classes and perform further robustness evaluation."
        )
        evidence_list.append(evidence)
        
    return evidence_list
