import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class Evidence:
    evidence_id: str
    asset_id: str
    finding_type: str
    category: str
    method: str
    status: str
    severity: str
    confidence_basis: str
    observations: str
    threshold: Optional[float] = None
    reference_id: Optional[str] = None
    affected_assets: Optional[List[str]] = None
    source_metadata: Optional[Dict[str, Any]] = None
    limitations: Optional[str] = None
    recommended_action: Optional[str] = None
    trace: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class EvidenceCorrelator:
    def __init__(self):
        self.evidence_store: List[Evidence] = []

    def add_evidence(self, evidence: Evidence):
        self.evidence_store.append(evidence)

    def correlate_by_asset(self, asset_id: str) -> List[Evidence]:
        return [e for e in self.evidence_store if e.asset_id == asset_id or (e.affected_assets and asset_id in e.affected_assets)]

    def correlate_by_category(self, category: str) -> List[Evidence]:
        return [e for e in self.evidence_store if e.category == category]
        
    def generate_report_summary(self) -> Dict[str, Any]:
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for e in self.evidence_store:
            if e.severity in severity_counts:
                severity_counts[e.severity] += 1
                
        return {
            "total_findings": len(self.evidence_store),
            "severity_counts": severity_counts,
            "findings": [e.to_dict() for e in self.evidence_store]
        }
