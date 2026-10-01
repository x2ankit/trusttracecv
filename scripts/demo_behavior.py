import sys
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
import numpy as np
from PIL import Image

from src.models.runtime import load_model_for_inference
from src.models.behavioral_fingerprint import generate_behavioral_fingerprint, evaluate_fingerprint_divergence
from src.models.controlled_transformations import run_controlled_transformation_battery
from src.models.trigger_probe import probe_trigger_sensitivity

def load_images(dir_path: Path) -> list:
    images = []
    for p in sorted(dir_path.glob("*.jpg"))[:5]: # Load max 5 for fast demo
        try:
            img = np.array(Image.open(p).convert("RGB"))
            images.append(img)
        except Exception:
            pass
    return images

def main():
    print("==================================================")
    print("TRUSTTRACE CV: END-TO-END BEHAVIOR DEMO")
    print("==================================================")
    
    # 1. Look for a REAL local object detector, e.g. YOLOv5s.pt
    # The dummy classifiers are now correctly rejected by the runtime.
    models_dir = ROOT / "models" / "fixtures"
    data_dir = ROOT / "data" / "fixtures" / "clean" / "images"
    
    # Check for a real pretrained object detection model (we do not download one)
    real_detector_paths = list(models_dir.glob("yolo*.pt")) + list(models_dir.glob("fasterrcnn*.pt"))
    
    if not real_detector_paths:
        print("REAL OBJECT-DETECTION DEMO = NOT_ASSESSED")
        print("NO_LOCAL_OBJECT_DETECTOR_AVAILABLE")
        return
        
    ref_model_path = real_detector_paths[0]
    cand_model_path = real_detector_paths[0] # Using same model as candidate for demo
    
    print(f"Loading reference model: {ref_model_path.name}")
    try:
        ref_model, ref_type = load_model_for_inference(ref_model_path)
    except Exception as e:
        print(f"BENCHMARK NOT ASSESSED: Could not load reference model: {e}")
        return
        
    print(f"Loading candidate model: {cand_model_path.name}")
    try:
        cand_model, cand_type = load_model_for_inference(cand_model_path)
    except Exception as e:
        print(f"BENCHMARK NOT ASSESSED: Could not load candidate model: {e}")
        return
        
    reference_images = load_images(data_dir)
    print(f"Loaded {len(reference_images)} reference images.")
    
    if not reference_images:
        print("REAL OBJECT-DETECTION DEMO = NOT_ASSESSED")
        return
    
    print("\n--- BEHAVIORAL FINGERPRINTING ---")
    print("Generating reference fingerprint...")
    ref_fp = generate_behavioral_fingerprint("ref_model", ref_model, ref_type, reference_images)
    
    print("Generating candidate fingerprint...")
    cand_fp = generate_behavioral_fingerprint("cand_model", cand_model, cand_type, reference_images)
    
    print("\nEvaluating behavioral divergence...")
    div = evaluate_fingerprint_divergence(
        "ref_model", "cand_model", "sha_ref", "sha_cand", "clean_dataset",
        cand_fp, ref_fp
    )
    print(f"Result: {div['result']}")
    print("Observations:")
    for obs in div['observations']:
        print(f" - {obs}")
        
    print("\n--- CONTROLLED TRANSFORMATIONS BATTERY ---")
    print("Running transformations on candidate model...")
    t_res = run_controlled_transformation_battery(cand_model, cand_type, reference_images)
    print(f"Result: {t_res['result']}")
    print(f"Avg Count Diff: {t_res['metrics']['avg_count_diff']:.2f}")
    print(f"Avg Conf Diff: {t_res['metrics']['avg_conf_diff']:.2f}")
    print(f"Avg IoU: {t_res['metrics']['avg_iou']:.2f}")
    
    print("\n--- TRIGGER SENSITIVITY PROBE ---")
    print("Probing candidate model for trigger sensitivity...")
    trig_evs = probe_trigger_sensitivity("cand_model", cand_model, cand_type, reference_images)
    for ev in trig_evs:
        d = ev.to_dict()
        print(f"Finding: {d['finding_type']}")
        print(f"Observation: {d['observations']}")

if __name__ == "__main__":
    main()
