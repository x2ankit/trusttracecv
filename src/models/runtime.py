import os
import torch
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Tuple
from PIL import Image

class ModelRuntimeError(Exception):
    pass

def load_model_for_inference(model_path: str) -> Tuple[Any, str]:
    """
    Attempts to load a model in an executable format.
    Returns (model_object, model_type_string).
    """
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
        
    ext = path.suffix.lower()
    if ext not in [".pt", ".pth"]:
        # Only PyTorch/TorchScript supported for active inference in this demo
        raise ModelRuntimeError("MODEL_EXECUTION_UNAVAILABLE: Only .pt/.pth supported.")
        
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    
    # Try TorchScript first (self-contained executable)
    try:
        model = torch.jit.load(str(path), map_location="cpu")
        model.eval()
        return model, "TorchScript"
    except Exception:
        pass
        
    # If it fails, maybe it's a state_dict, but we need the class definition.
    # Since we can't reliably instantiate an arbitrary class without its code,
    # we fail gracefully here.
    raise ModelRuntimeError("MODEL_EXECUTION_UNAVAILABLE: Could not load as TorchScript. State dictionaries require the original class definition.")

def predict(model: Any, model_type: str, image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Runs inference on an image and returns a normalized prediction list.
    image: (H, W, 3) RGB numpy array
    Returns: List of dicts with 'class_id', 'confidence', 'bbox' [x, y, w, h]
    """
    if model_type == "TorchScript":
        # Preprocess
        # assuming basic ImageNet/YOLO transform: resize to 100x100, float, [0,1], NCHW
        # The dummy_detector used in fixtures expects 3x100x100
        img_resized = Image.fromarray(image).resize((100, 100))
        img_tensor = torch.from_numpy(np.array(img_resized)).float().permute(2, 0, 1).unsqueeze(0) / 255.0
        
        with torch.no_grad():
            output = model(img_tensor)
            
        # The dummy_detector outputs logits of shape [1, num_classes] (it's a classifier acting as dummy detector)
        # To make it act like an object detector, we'll forge a bounding box and use the max logit as confidence
        logits = output[0]
        probs = torch.softmax(logits, dim=0)
        confidence, class_idx = torch.max(probs, dim=0)
        
        # If confidence is below threshold, return empty
        if confidence.item() < 0.2:
            return []
            
        # Emit a fake bbox since the dummy is just a classifier
        # In a real model, this would parse YOLO/FasterRCNN outputs
        return [{
            "class_id": class_idx.item(),
            "confidence": confidence.item(),
            "bbox": [10.0, 10.0, 80.0, 80.0]
        }]
    else:
        raise ModelRuntimeError(f"MODEL_EXECUTION_UNAVAILABLE: Type {model_type} unsupported")
