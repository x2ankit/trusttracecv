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
        # Basic Preprocess assuming standard object detector (e.g. YOLOv5/Torchvision formats)
        img_resized = Image.fromarray(image).resize((640, 640)) # typical resolution for detection
        img_tensor = torch.from_numpy(np.array(img_resized)).float().permute(2, 0, 1).unsqueeze(0) / 255.0
        
        with torch.no_grad():
            output = model(img_tensor)
            
        predictions = []
        
        # Parse different common object detection output formats
        
        # Format A: Dictionary output (e.g., Torchvision Faster R-CNN)
        if isinstance(output, (list, tuple)) and len(output) > 0 and isinstance(output[0], dict):
            out_dict = output[0]
            if "boxes" not in out_dict or "scores" not in out_dict or "labels" not in out_dict:
                raise ModelRuntimeError("TASK_UNSUPPORTED_FOR_DETECTION")
                
            boxes = out_dict["boxes"].cpu().numpy()
            scores = out_dict["scores"].cpu().numpy()
            labels = out_dict["labels"].cpu().numpy()
            
            for box, score, label in zip(boxes, scores, labels):
                if score >= 0.2:
                    # Convert [x_min, y_min, x_max, y_max] to [x, y, w, h]
                    x, y, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                    predictions.append({
                        "class_id": int(label),
                        "confidence": float(score),
                        "bbox": [x, y, x2 - x, y2 - y]
                    })
                    
        # Format B: Tensor output with shape [1, num_boxes, >=6] (e.g., YOLO format [batch, num_preds, box+conf+cls])
        # or [1, >=6, num_boxes]
        elif isinstance(output, torch.Tensor):
            if output.dim() == 2:
                # Shape [1, num_classes] -> Classification only
                raise ModelRuntimeError("TASK_UNSUPPORTED_FOR_DETECTION")
                
            out_t = output.cpu().numpy()
            
            # Handling YOLOv8 format [1, 84, 8400]
            if out_t.ndim == 3 and out_t.shape[1] > out_t.shape[2]:
                out_t = np.transpose(out_t, (0, 2, 1))
                
            if out_t.ndim == 3 and out_t.shape[-1] >= 6:
                for pred in out_t[0]:
                    # Assuming pred = [x_center, y_center, w, h, obj_conf, cls1, cls2...]
                    obj_conf = float(pred[4])
                    if obj_conf >= 0.2:
                        class_probs = pred[5:]
                        class_id = int(np.argmax(class_probs))
                        confidence = obj_conf * float(class_probs[class_id])
                        
                        if confidence >= 0.2:
                            xc, yc, w, h = float(pred[0]), float(pred[1]), float(pred[2]), float(pred[3])
                            predictions.append({
                                "class_id": class_id,
                                "confidence": confidence,
                                "bbox": [xc - w/2, yc - h/2, w, h]
                            })
            else:
                 raise ModelRuntimeError("TASK_UNSUPPORTED_FOR_DETECTION")
                 
        # Format C: Tuple containing tensor (e.g., YOLOv5 TorchScript)
        elif isinstance(output, tuple) and len(output) > 0 and isinstance(output[0], torch.Tensor):
            out_t = output[0].cpu().numpy()
            if out_t.ndim == 3 and out_t.shape[-1] >= 6:
                for pred in out_t[0]:
                    obj_conf = float(pred[4])
                    if obj_conf >= 0.2:
                        class_probs = pred[5:]
                        class_id = int(np.argmax(class_probs))
                        confidence = obj_conf * float(class_probs[class_id])
                        
                        if confidence >= 0.2:
                            xc, yc, w, h = float(pred[0]), float(pred[1]), float(pred[2]), float(pred[3])
                            predictions.append({
                                "class_id": class_id,
                                "confidence": confidence,
                                "bbox": [xc - w/2, yc - h/2, w, h]
                            })
            else:
                 raise ModelRuntimeError("TASK_UNSUPPORTED_FOR_DETECTION")
                 
        else:
             raise ModelRuntimeError("TASK_UNSUPPORTED_FOR_DETECTION")
             
        return predictions
    else:
        raise ModelRuntimeError(f"MODEL_EXECUTION_UNAVAILABLE: Type {model_type} unsupported")
