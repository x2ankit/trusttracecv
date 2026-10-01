import logging
import subprocess
import uuid
import os
from typing import List
from src.evidence.correlator import Evidence

logger = logging.getLogger(__name__)

def verify_cosign_signature(manifest_path: str, public_key_path: str, signature_path: str, model_id: str) -> List[Evidence]:
    """
    Offline-compatible key-pair workflow using Cosign CLI.
    """
    evidence_list = []
    
    import shutil
    if not shutil.which("cosign"):
        logger.info("Cosign CLI not installed.")
        evidence = Evidence(
            evidence_id=f"COS_NA_{uuid.uuid4().hex[:8]}",
            asset_id=model_id,
            finding_type="COSIGN_VERIFICATION",
            category="MODEL_ARTIFACT_INTEGRITY",
            method="cosign",
            status="NOT_ASSESSED",
            severity="INFO",
            confidence_basis="N/A",
            observations="Cosign signature verification cannot be assessed because the cosign CLI is unavailable.",
            limitations="Cosign binary is not in PATH.",
            recommended_action="Install cosign (https://docs.sigstore.dev/cosign/installation) to enable offline signature verification."
        )
        evidence_list.append(evidence)
        return evidence_list

    if not os.path.exists(public_key_path) or not os.path.exists(signature_path) or not os.path.exists(manifest_path):
        evidence = Evidence(
            evidence_id=f"COS_NA_{uuid.uuid4().hex[:8]}",
            asset_id=model_id,
            finding_type="COSIGN_VERIFICATION",
            category="MODEL_ARTIFACT_INTEGRITY",
            method="cosign",
            status="NOT_ASSESSED",
            severity="INFO",
            confidence_basis="N/A",
            observations="Verification material (key, signature, or manifest) is locally unavailable.",
            limitations="Requires public key, signature file, and manifest to be present.",
        )
        evidence_list.append(evidence)
        return evidence_list

    try:
        # cosign verify-blob --key <public_key> --signature <signature> <blob>
        result = subprocess.run(
            ["cosign", "verify-blob", "--key", public_key_path, "--signature", signature_path, manifest_path],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            evidence = Evidence(
                evidence_id=f"COS_{uuid.uuid4().hex[:8]}",
                asset_id=model_id,
                finding_type="COSIGN_VERIFICATION",
                category="MODEL_ARTIFACT_INTEGRITY",
                method="cosign",
                status="PASS",
                severity="INFO",
                confidence_basis="Cosign CLI offline key-pair verification",
                observations="Signed manifest verified successfully via Cosign.",
                limitations="Does not prove online transparency log inclusion (offline mode)."
            )
        else:
            evidence = Evidence(
                evidence_id=f"COS_{uuid.uuid4().hex[:8]}",
                asset_id=model_id,
                finding_type="COSIGN_VERIFICATION",
                category="MODEL_ARTIFACT_INTEGRITY",
                method="cosign",
                status="FAIL",
                severity="CRITICAL",
                confidence_basis="Cosign CLI offline key-pair verification",
                observations=f"Cosign signature invalid: {result.stderr.strip()}",
                limitations="Does not prove online transparency log inclusion (offline mode).",
                recommended_action="QUARANTINE - Model signature verification failed."
            )
            
        evidence_list.append(evidence)
        
    except Exception as e:
        logger.error(f"Cosign verification error: {e}")
        evidence = Evidence(
            evidence_id=f"COS_ERR_{uuid.uuid4().hex[:8]}",
            asset_id=model_id,
            finding_type="COSIGN_VERIFICATION",
            category="MODEL_ARTIFACT_INTEGRITY",
            method="cosign",
            status="NOT_ASSESSED",
            severity="INFO",
            confidence_basis="N/A",
            observations=f"Error running cosign: {str(e)}"
        )
        evidence_list.append(evidence)

    return evidence_list
