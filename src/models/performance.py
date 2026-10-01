import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def calculate_iou(box1: List[float], box2: List[float]) -> float:
    """Calculate IoU for two [x, y, w, h] boxes."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    xi1, yi1 = max(x1, x2), max(y1, y2)
    xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
    
    inter_w, inter_h = max(0.0, xi2 - xi1), max(0.0, yi2 - yi1)
    inter_area = inter_w * inter_h
    
    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - inter_area
    
    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area

def evaluate_object_detection_performance(
    model_digest: str, 
    dataset_name: str, 
    reference_source: str, 
    ground_truth: List[Dict[str, Any]], 
    predictions: List[Dict[str, Any]], 
    iou_thresholds: List[float] = [0.5, 0.75]
) -> Dict[str, Any]:
    """
    Evaluates object detection performance.
    """
    report = {
        "evaluation_dataset": dataset_name,
        "reference_source": reference_source,
        "sample_count": len(set([gt["image_id"] for gt in ground_truth] + [p["image_id"] for p in predictions])),
        "model_digest": model_digest,
        "timestamp": time.time(),
        "thresholds": {}
    }
    
    for iou_thresh in iou_thresholds:
        # Group by image_id
        gt_by_img = {}
        for gt in ground_truth:
            gt_by_img.setdefault(gt["image_id"], []).append(gt)
            
        pred_by_img = {}
        for p in predictions:
            pred_by_img.setdefault(p["image_id"], []).append(p)
            
        tp, fp, fn = 0, 0, 0
        per_class_stats = {}
        
        all_image_ids = set(list(gt_by_img.keys()) + list(pred_by_img.keys()))
        
        for img_id in all_image_ids:
            img_gts = gt_by_img.get(img_id, [])
            img_preds = pred_by_img.get(img_id, [])
            
            # Sort predictions by confidence desc
            img_preds.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
            
            matched_gt_indices = set()
            
            for p in img_preds:
                c = p["class_id"]
                if c not in per_class_stats:
                    per_class_stats[c] = {"tp": 0, "fp": 0, "fn": 0}
                    
                best_iou = 0.0
                best_gt_idx = -1
                
                for idx, gt in enumerate(img_gts):
                    if gt["class_id"] == c and idx not in matched_gt_indices:
                        iou = calculate_iou(p["bbox"], gt["bbox"])
                        if iou > best_iou:
                            best_iou = iou
                            best_gt_idx = idx
                            
                if best_iou >= iou_thresh:
                    tp += 1
                    per_class_stats[c]["tp"] += 1
                    matched_gt_indices.add(best_gt_idx)
                else:
                    fp += 1
                    per_class_stats[c]["fp"] += 1
                    
            for idx, gt in enumerate(img_gts):
                if idx not in matched_gt_indices:
                    fn += 1
                    c = gt["class_id"]
                    if c not in per_class_stats:
                        per_class_stats[c] = {"tp": 0, "fp": 0, "fn": 0}
                    per_class_stats[c]["fn"] += 1
                    
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        # calculate per class precision and recall
        for c, stats in per_class_stats.items():
            ctp, cfp, cfn = stats["tp"], stats["fp"], stats["fn"]
            stats["precision"] = ctp / (ctp + cfp) if (ctp + cfp) > 0 else 0.0
            stats["recall"] = ctp / (ctp + cfn) if (ctp + cfn) > 0 else 0.0
            
        report["thresholds"][str(iou_thresh)] = {
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "precision": precision,
            "recall": recall,
            "per_class": per_class_stats,
            "matched_object_count": tp,
            "missed_object_count": fn,
            "spurious_object_count": fp
        }
        
    return report
