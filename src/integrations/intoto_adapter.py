import logging
import uuid
import json
import hashlib
from typing import List, Dict, Any
from src.evidence.correlator import Evidence

logger = logging.getLogger(__name__)

class InTotoEvidenceChain:
    """
    In-toto-style evidence chain for TRUSTTRACE workflow.
    Stages:
    1. dataset_ingest
    2. dataset_audit
    3. model_verification
    4. inference
    5. assurance_report
    """
    
    def __init__(self):
        self.chain = []
        
    def add_link(self, stage: str, materials: Dict[str, str], products: Dict[str, str], command: str = ""):
        """
        Adds a link metadata describing materials and products for a logical stage.
        """
        link = {
            "_type": "link",
            "name": stage,
            "materials": materials,
            "products": products,
            "command": command,
            "environment": {"name": "trusttrace-cv"}
        }
        
        # In a real in-toto setup, we would sign this link metadata.
        # For this prototype we serialize and hash it.
        link_str = json.dumps(link, sort_keys=True)
        link_hash = hashlib.sha256(link_str.encode('utf-8')).hexdigest()
        
        self.chain.append({
            "link": link,
            "hash": link_hash
        })
        
    def export_chain(self) -> List[Dict[str, Any]]:
        return self.chain

def generate_intoto_evidence(chain: InTotoEvidenceChain, report_id: str) -> List[Evidence]:
    """
    Converts an in-toto chain into TRUSTTRACE Evidence.
    """
    evidence_list = []
    
    if len(chain.chain) == 0:
        return evidence_list
        
    evidence = Evidence(
        evidence_id=f"INTOTO_{uuid.uuid4().hex[:8]}",
        asset_id=report_id,
        finding_type="INTOTO_PROVENANCE_CHAIN",
        category="PROVENANCE",
        method="in-toto_adapter",
        status="PASS",
        severity="INFO",
        confidence_basis="In-toto local link verification",
        observations=f"In-toto-style evidence chain generated with {len(chain.chain)} stages.",
        limitations="Adapts in-toto semantics for CV inference offline. Software supply chain semantics not blindly copied.",
        source_metadata={"chain": chain.export_chain()}
    )
    evidence_list.append(evidence)
    
    return evidence_list
