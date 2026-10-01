import pytest
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import torch
import numpy as np
import math
from src.models.performance import evaluate_object_detection_performance
from src.models.behavioral_fingerprint import generate_behavioral_fingerprint, evaluate_fingerprint_divergence
from src.models.trigger_probe import probe_trigger_sensitivity, generate_triggers, apply_trigger
from src.models.runtime import load_model_for_inference, predict, ModelRuntimeError

# 1. Performance AP/mAP Tests
def test_proper_ap_calculation():
    # Construct a deterministic scenario where AP can be hand-calculated
    ground_truth = [
        {"image_id": "1", "class_id": 0, "bbox": [0, 0, 10, 10]},
        {"image_id": "1", "class_id": 0, "bbox": [20, 20, 10, 10]},
        {"image_id": "2", "class_id": 0, "bbox": [0, 0, 10, 10]}
    ] # Total 3 GT objects
    
    predictions = [
        {"image_id": "1", "class_id": 0, "bbox": [0, 0, 10, 10], "confidence": 0.9}, # TP
        {"image_id": "1", "class_id": 0, "bbox": [50, 50, 10, 10], "confidence": 0.8}, # FP
        {"image_id": "2", "class_id": 0, "bbox": [0, 0, 10, 10], "confidence": 0.7} # TP
    ]
    
    report = evaluate_object_detection_performance("dummy_digest", "dummy_dataset", "dummy_source", ground_truth, predictions)
    mAP_05 = report["thresholds"]["0.5"]["mAP"]
    
    assert mAP_05 > 0.5
    assert mAP_05 < 0.6
    assert report["thresholds"]["0.5"]["calculation_method"] == "11-point interpolated AP"

# 2. Trigger Probe Tests
def test_trigger_generation_and_application():
    triggers = generate_triggers()
    assert len(triggers) >= 3
    
    clean_image = np.zeros((100, 100, 3), dtype=np.uint8)
    triggered = apply_trigger(clean_image, triggers[0])
    
    # Solid patch should change pixel values
    assert not np.array_equal(clean_image, triggered)

def test_trigger_inference_loop():
    # Use a dummy model that outputs consistent fake boxes
    class DummyModel:
        def __call__(self, x):
            return torch.tensor([[-2.0, 5.0]]) # Class 1 confident
            
    model = DummyModel()
    
    images = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(3)]
    
    evs = probe_trigger_sensitivity("test_model", model, "TorchScript", images)
    
    # Since our DummyModel always outputs the same box regardless of input, change rates will be 0
    for ev in evs:
        d = ev.to_dict()
        assert d["finding_type"] == "NO_SIGNIFICANT_TRIGGER_SENSITIVITY_OBSERVED"

# 3. Model Runtime Tests
def test_model_runtime_unsupported():
    try:
        load_model_for_inference("nonexistent_model.pt")
        pytest.fail("Should throw FileNotFoundError")
    except FileNotFoundError:
        pass
        
    try:
        # Create a fake txt file
        with open("fake.txt", "w") as f:
            f.write("test")
        load_model_for_inference("fake.txt")
        pytest.fail("Should throw ModelRuntimeError for unsupported extension")
    except ModelRuntimeError as e:
        assert "MODEL_EXECUTION_UNAVAILABLE" in str(e)

# 4. Behavioral Fingerprint Tests
def test_behavioral_fingerprint_metrics():
    predictions = [
        {"image_id": "0", "class_id": 0, "bbox": [0, 0, 10, 10], "confidence": 0.9},
        {"image_id": "0", "class_id": 1, "bbox": [20, 20, 10, 10], "confidence": 0.8},
        {"image_id": "1"} # Empty
    ]
    
    from src.models.behavioral_fingerprint import calculate_black_box_fingerprint
    fp = calculate_black_box_fingerprint(predictions)
    
    assert fp["mean_object_count"] == 1.0 # 2 objects in 2 images
    assert fp["no_object_rate"] == 0.5
    assert math.isclose(fp["confidence_distribution_mean"], 0.85, rel_tol=1e-5)
    assert fp["class_frequencies"] == {0: 1, 1: 1}

def test_behavioral_divergence():
    fp_ref = {
        "black_box_metrics": {
            "mean_object_count": 2.0,
            "confidence_distribution_mean": 0.8,
            "no_object_rate": 0.1,
            "class_frequencies": {}
        },
        "white_box_assessed": False,
        "battery_size": 10,
        "black_box_assessed": True
    }
    
    fp_cand = {
        "black_box_metrics": {
            "mean_object_count": 2.1,
            "confidence_distribution_mean": 0.82,
            "no_object_rate": 0.1,
            "class_frequencies": {}
        },
        "white_box_assessed": False,
        "battery_size": 10,
        "black_box_assessed": True
    }
    
    div = evaluate_fingerprint_divergence(
        "ref", "cand", "ref_sha", "cand_sha", "ds", fp_cand, fp_ref
    )
    
    assert div["result"] == "BEHAVIORALLY_CONSISTENT"
    
    fp_cand_diverged = fp_cand.copy()
    fp_cand_diverged["black_box_metrics"]["mean_object_count"] = 0.5 # Huge drop
    
    div2 = evaluate_fingerprint_divergence(
        "ref", "cand", "ref_sha", "cand_sha", "ds", fp_cand_diverged, fp_ref
    )
    
    assert div2["result"] == "BEHAVIORAL_DIVERGENCE"

# 5. White Box Stats Tests
def test_white_box_stats_hooks():
    import torch.nn as nn
    
    class SimpleModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Conv2d(3, 8, 3, padding=1)
            self.linear = nn.Linear(8 * 100 * 100, 2)
            
        def forward(self, x):
            x = self.features(x)
            x = x.flatten(1)
            return self.linear(x)
            
    model = SimpleModel()
    images = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)]
    
    fp = generate_behavioral_fingerprint("model_1", model, "TorchScript", images)
    assert fp["white_box_assessed"] == True
    assert "activation_mean" in fp["white_box_metrics"]
    assert fp["white_box_metrics"]["activation_mean"] != "NOT_ASSESSED"

