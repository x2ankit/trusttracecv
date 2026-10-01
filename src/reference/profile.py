import json
import hashlib
import time
from typing import Dict, Any, Optional

class ReferenceProfile:
    def __init__(
        self,
        reference_id: str,
        dataset_digest: str,
        model_digest: Optional[str],
        feature_means: Dict[str, float],
        feature_stds: Dict[str, float],
        covariance_metadata: Dict[str, Any],
        class_distribution: Dict[str, float],
        image_dimension_distribution: Dict[str, Any],
        bbox_statistics: Dict[str, Any],
        behavioral_fingerprint: Optional[Dict[str, Any]],
        source_metadata: Dict[str, Any]
    ):
        self.reference_id = reference_id
        self.dataset_digest = dataset_digest
        self.model_digest = model_digest
        self.feature_means = feature_means
        self.feature_stds = feature_stds
        self.covariance_metadata = covariance_metadata
        self.class_distribution = class_distribution
        self.image_dimension_distribution = image_dimension_distribution
        self.bbox_statistics = bbox_statistics
        self.behavioral_fingerprint = behavioral_fingerprint
        self.source_metadata = source_metadata
        self.creation_timestamp = time.time()
        
        # Calculate canonical hash
        self.canonical_hash = self._compute_hash()
        
    def _compute_hash(self) -> str:
        data = {
            "reference_id": self.reference_id,
            "dataset_digest": self.dataset_digest,
            "model_digest": self.model_digest,
            "feature_means": self.feature_means,
            "feature_stds": self.feature_stds,
            "class_distribution": self.class_distribution
        }
        canonical_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "dataset_digest": self.dataset_digest,
            "model_digest": self.model_digest,
            "feature_means": self.feature_means,
            "feature_stds": self.feature_stds,
            "covariance_metadata": self.covariance_metadata,
            "class_distribution": self.class_distribution,
            "image_dimension_distribution": self.image_dimension_distribution,
            "bbox_statistics": self.bbox_statistics,
            "behavioral_fingerprint": self.behavioral_fingerprint,
            "source_metadata": self.source_metadata,
            "creation_timestamp": self.creation_timestamp,
            "canonical_hash": self.canonical_hash
        }
