import logging
import uuid
import numpy as np
from typing import Dict, List, Any
from src.evidence.correlator import Evidence
from src.reference.profile import ReferenceProfile

logger = logging.getLogger(__name__)

def evaluate_distribution_shift(incoming_features: Dict[str, float], reference: ReferenceProfile, dataset_id: str) -> List[Evidence]:
    """
    Evaluates distribution shift of an incoming dataset against a ReferenceProfile.
    """
    evidence_list = []
    
    # 1. Per-feature Z-score
    z_score_anomalies = []
    for feature, val in incoming_features.items():
        if feature in reference.feature_means and feature in reference.feature_stds:
            mean = reference.feature_means[feature]
            std = reference.feature_stds[feature]
            # numerically safe std floor
            std = max(std, 1e-6)
            
            z = (val - mean) / std
            if abs(z) > 3.0:  # 3 sigma threshold
                z_score_anomalies.append({
                    "feature": feature,
                    "value": val,
                    "z_score": z
                })
                
    if z_score_anomalies:
        evidence = Evidence(
            evidence_id=f"SHF_{uuid.uuid4().hex[:8]}",
            asset_id=dataset_id,
            finding_type="STATISTICAL_SHIFT",
            category="DISTRIBUTION_SHIFT",
            method="z_score_feature_comparison",
            status="FLAGGED",
            severity="MEDIUM",
            confidence_basis="Statistical evaluation (z-score > 3.0)",
            observations=f"{len(z_score_anomalies)} features exhibited significant shift.",
            reference_id=reference.reference_id,
            source_metadata={"anomalies": z_score_anomalies},
            limitations="A shift alone must never be reported as confirmed poisoning. Distinguishes STATISTICAL_SHIFT from MALICIOUS_MANIPULATION.",
            recommended_action="REVIEW - Check if data collection environment changed."
        )
        evidence_list.append(evidence)
        
    # 2. Mahalanobis distance (Multivariate shift)
    # Using the features available in both
    common_features = sorted(list(set(incoming_features.keys()).intersection(set(reference.feature_means.keys()))))
    
    if len(common_features) > 1 and "covariance_matrix" in reference.covariance_metadata:
        try:
            x = np.array([incoming_features[f] for f in common_features])
            mu = np.array([reference.feature_means[f] for f in common_features])
            cov = np.array(reference.covariance_metadata["covariance_matrix"])
            
            # Using covariance regularization when necessary
            regularization = reference.covariance_metadata.get("regularization", 1e-6)
            cov += np.eye(len(cov)) * regularization
            
            inv_cov = np.linalg.pinv(cov)
            diff = x - mu
            
            mahalanobis_sq = diff.T @ inv_cov @ diff
            mahalanobis_dist = float(np.sqrt(max(0.0, mahalanobis_sq)))
            
            threshold = reference.covariance_metadata.get("mahalanobis_threshold", 5.0)
            
            if mahalanobis_dist > threshold:
                evidence = Evidence(
                    evidence_id=f"SHF_MAH_{uuid.uuid4().hex[:8]}",
                    asset_id=dataset_id,
                    finding_type="STATISTICAL_SHIFT",
                    category="DISTRIBUTION_SHIFT",
                    method="mahalanobis_distance",
                    status="FLAGGED",
                    severity="HIGH",
                    confidence_basis="Multivariate statistical distance",
                    observations=f"Mahalanobis distance {mahalanobis_dist:.2f} exceeds threshold {threshold:.2f}.",
                    reference_id=reference.reference_id,
                    threshold=threshold,
                    limitations="Indicates shift in combined feature space. A shift alone is not confirmed poisoning.",
                    recommended_action="REVIEW - Highly anomalous feature combination."
                )
                evidence_list.append(evidence)
                
        except Exception as e:
            logger.warning(f"Failed to compute Mahalanobis distance: {e}")
            
    return evidence_list
