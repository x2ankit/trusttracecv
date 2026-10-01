"""
src/models/integrity.py

Model identity and integrity checks for PyTorch (.pt/.pth),
TorchScript (.pt), and ONNX (.onnx) artifacts.

Supported checks:
  - SHA-256 hash computation and comparison against a reference manifest
  - Model metadata extraction (architecture, input shape, opset)
  - Model substitution detection (hash mismatch vs known-good)
  - Basic structural validation (loadability, required keys)

Limitations:
  - Hash matching confirms file identity, NOT model correctness or safety.
  - ONNX opset and shape validation is structural only; semantics are not verified.
  - TorchScript and PyTorch state_dict loading does not execute inference.
  - Universal backdoor detection via static analysis is NOT performed.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hash & Manifest utilities
# ---------------------------------------------------------------------------
import hmac

_ENV_MANIFEST_SECRET = os.environ.get("TRUSTTRACE_CV_MANIFEST_SECRET")
if _ENV_MANIFEST_SECRET:
    _MANIFEST_SECRET = _ENV_MANIFEST_SECRET.encode("utf-8")
else:
    logger.warning("INSECURE DEVELOPMENT FALLBACK: Using hardcoded Manifest HMAC secret.")
    _MANIFEST_SECRET = b"TRUSTTRACE_CV_DEFAULT_MANIFEST_SECRET"

def sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file, reading in 64 KiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def sign_manifest(manifest: Dict[str, str], secret: bytes = _MANIFEST_SECRET) -> Dict[str, str]:
    clean_manifest = {k: v for k, v in manifest.items() if k not in ("hmac_sig", "rsa_sig")}
    payload_bytes = json.dumps(clean_manifest, sort_keys=True).encode()
    hmac_sig = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    clean_manifest["hmac_sig"] = hmac_sig
    return clean_manifest

def verify_manifest(manifest: Dict[str, str], secret: bytes = _MANIFEST_SECRET, public_key_path: Optional[Path] = None) -> Tuple[bool, str]:
    """Verifies manifest using RSA asymmetric signature if available, fallback to HMAC."""
    clean_manifest = {k: v for k, v in manifest.items() if k not in ("hmac_sig", "rsa_sig")}
    payload_bytes = json.dumps(clean_manifest, sort_keys=True).encode()
    
    if "rsa_sig" in manifest and public_key_path and public_key_path.exists():
        try:
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives import serialization
            import base64
            
            with open(public_key_path, "rb") as key_file:
                public_key = serialization.load_pem_public_key(key_file.read())
            
            signature = base64.b64decode(manifest["rsa_sig"])
            public_key.verify(
                signature,
                payload_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True, "ASYMMETRIC"
        except Exception as e:
            logger.error(f"RSA signature verification failed: {e}")
            return False, "ASYMMETRIC"
            
    if "hmac_sig" in manifest:
        expected_sig = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
        is_valid = hmac.compare_digest(manifest["hmac_sig"], expected_sig)
        return is_valid, "HMAC"
        
    return False, "NONE"

def build_manifest(model_paths: List[Path]) -> Dict[str, str]:
    """Build a {filename: sha256} manifest for the given model files."""
    return {p.name: sha256_file(p) for p in model_paths if p.is_file()}

def save_manifest(manifest: Dict[str, str], manifest_path: Path) -> None:
    signed_manifest = sign_manifest(manifest)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(signed_manifest, fh, indent=2)
    logger.info("Manifest saved to %s", manifest_path)

def load_manifest(manifest_path: Path) -> Dict[str, str]:
    with open(manifest_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# PyTorch / TorchScript loader
# ---------------------------------------------------------------------------

def _try_load_pytorch(path: Path) -> Dict[str, Any]:
    """
    Attempt to load a .pt or .pth file as:
    1. TorchScript (torch.jit.load)
    2. State dict / full model (torch.load)

    Returns metadata dict without executing inference.
    """
    import os
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    import torch

    meta: Dict[str, Any] = {
        "load_type": "UNKNOWN",
        "keys": [],
        "torchscript": False,
        "error": None,
    }

    # Try TorchScript first
    try:
        model = torch.jit.load(str(path), map_location="cpu")
        meta["load_type"] = "TorchScript"
        meta["torchscript"] = True
        try:
            meta["graph_summary"] = str(model.graph)[:500]
        except Exception:
            meta["graph_summary"] = "NOT ASSESSED"
        return meta
    except Exception:
        pass

    # Try generic torch.load
    try:
        obj = torch.load(str(path), map_location="cpu", weights_only=True)
        if isinstance(obj, dict):
            meta["load_type"] = "state_dict"
            meta["keys"] = list(obj.keys())[:20]
            meta["total_keys"] = len(obj)
        else:
            meta["load_type"] = type(obj).__name__
        return meta
    except Exception as exc:
        try:
            # Fallback without weights_only (older format)
            obj = torch.load(str(path), map_location="cpu")
            if isinstance(obj, dict):
                meta["load_type"] = "state_dict (legacy)"
                meta["keys"] = list(obj.keys())[:20]
                meta["total_keys"] = len(obj)
            else:
                meta["load_type"] = type(obj).__name__
            return meta
        except Exception as exc2:
            meta["error"] = str(exc2)
            return meta


# ---------------------------------------------------------------------------
# ONNX loader
# ---------------------------------------------------------------------------

def _try_load_onnx(path: Path) -> Dict[str, Any]:
    """
    Load an ONNX model and extract metadata.
    Does NOT execute inference.
    """
    meta: Dict[str, Any] = {
        "load_type": "ONNX",
        "opset_version": "NOT ASSESSED",
        "inputs": [],
        "outputs": [],
        "model_version": "NOT ASSESSED",
        "ir_version": "NOT ASSESSED",
        "error": None,
    }
    try:
        import onnx
        model = onnx.load(str(path))
        onnx.checker.check_model(model)
        meta["ir_version"] = model.ir_version
        meta["model_version"] = model.model_version
        if model.opset_import:
            meta["opset_version"] = model.opset_import[0].version

        for inp in model.graph.input:
            shape = [
                d.dim_value if d.HasField("dim_value") else "?"
                for d in inp.type.tensor_type.shape.dim
            ] if inp.type.tensor_type.HasField("shape") else ["?"]
            meta["inputs"].append({"name": inp.name, "shape": shape})

        for out in model.graph.output:
            shape = [
                d.dim_value if d.HasField("dim_value") else "?"
                for d in out.type.tensor_type.shape.dim
            ] if out.type.tensor_type.HasField("shape") else ["?"]
            meta["outputs"].append({"name": out.name, "shape": shape})

    except ImportError:
        meta["error"] = "onnx package not installed"
    except Exception as exc:
        meta["error"] = str(exc)

    return meta


# ---------------------------------------------------------------------------
# Main integrity check
# ---------------------------------------------------------------------------

def inspect_model(
    model_path: Path,
    reference_manifest: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Perform full integrity inspection of a model artifact.

    Args:
        model_path: Path to the model file.
        reference_manifest: dict mapping filename → expected SHA-256.
                           If None, integrity comparison is NOT ASSESSED.

    Returns:
        Structured finding dict with result, severity, evidence.
    """
    model_path = Path(model_path)

    record: Dict[str, Any] = {
        "filename": model_path.name,
        "path": str(model_path),
        "format": "UNKNOWN",
        "size_bytes": None,
        "sha256": "NOT ASSESSED",
        "metadata": {},
        "checks": {},
    }

    # --- File existence ---
    if not model_path.exists():
        record["checks"]["file_exists"] = {
            "result": "FAIL", "detail": "File not found"
        }
        return record
    record["checks"]["file_exists"] = {"result": "PASS"}

    # --- Size ---
    record["size_bytes"] = model_path.stat().st_size

    # --- Hash ---
    record["sha256"] = sha256_file(model_path)

    # --- Format detection ---
    suffix = model_path.suffix.lower()
    if suffix in (".pt", ".pth"):
        record["format"] = "PyTorch"
        record["metadata"] = _try_load_pytorch(model_path)
        if record["metadata"].get("error"):
            record["checks"]["loadable"] = {
                "result": "FAIL",
                "detail": record["metadata"]["error"],
            }
        else:
            record["checks"]["loadable"] = {"result": "PASS"}

    elif suffix == ".onnx":
        record["format"] = "ONNX"
        record["metadata"] = _try_load_onnx(model_path)
        if record["metadata"].get("error"):
            record["checks"]["loadable"] = {
                "result": "FAIL",
                "detail": record["metadata"]["error"],
            }
        else:
            record["checks"]["loadable"] = {"result": "PASS"}

    else:
        record["format"] = suffix.upper().strip(".")
        record["checks"]["loadable"] = {
            "result": "NOT ASSESSED",
            "detail": f"Unsupported format: {suffix}",
        }

    # --- Integrity comparison vs manifest ---
    if reference_manifest is not None:
        if "hmac_sig" in reference_manifest or "rsa_sig" in reference_manifest:
            # Check if there is a public key available for this project
            pub_key_path = Path(os.environ.get("TRUSTTRACE_PUBLIC_KEY", "public_key.pem"))
            sig_valid, sig_type = verify_manifest(reference_manifest, public_key_path=pub_key_path)
            
            if not sig_valid:
                record["checks"]["manifest_integrity"] = {
                    "result": "FAIL",
                    "severity": "CRITICAL",
                    "detail": f"Manifest {sig_type} signature is invalid. The manifest may have been tampered with."
                }
            else:
                record["checks"]["manifest_integrity"] = {
                    "result": "PASS",
                    "detail": f"Manifest {sig_type} signature verified."
                }
                
            record["checks"]["manifest_integrity"]["trace"] = {
                "operation_id": "MANIFEST_SIG_VERIFY",
                "operation_type": "Cryptographic Signature Verification",
                "formula": f"verify({sig_type}, manifest_payload, key)",
                "inputs": {
                    "signature_scheme": sig_type,
                    "payload_keys": [k for k in reference_manifest.keys() if k not in ("hmac_sig", "rsa_sig")],
                    "public_key_identifier": str(pub_key_path.name) if sig_type == "ASYMMETRIC" else "HMAC_SECRET"
                },
                "intermediate_values": {
                    "provided_signature": reference_manifest.get("rsa_sig") if sig_type == "ASYMMETRIC" else reference_manifest.get("hmac_sig")
                },
                "result": "VALID" if sig_valid else "INVALID",
                "threshold": "Cryptographic Match",
                "comparison": "verify() == True",
                "decision": record["checks"]["manifest_integrity"]["result"],
                "explanation": f"Verifies the {sig_type} signature of the canonicalized manifest dictionary. This ensures the reference hashes have not been maliciously modified since they were signed."
            }
        else:
            record["checks"]["manifest_integrity"] = {
                "result": "NOT ASSESSED",
                "detail": "Manifest is unsigned."
            }

        expected_sha = reference_manifest.get(model_path.name)
        if expected_sha is None:
            record["checks"]["hash_match"] = {
                "result": "NOT ASSESSED",
                "detail": "Model not present in reference manifest",
            }
        elif expected_sha == record["sha256"]:
            record["checks"]["hash_match"] = {
                "result": "PASS",
                "detail": "SHA-256 matches reference manifest",
                "expected": expected_sha,
                "actual": record["sha256"],
            }
        else:
            record["checks"]["hash_match"] = {
                "result": "FAIL",
                "severity": "CRITICAL",
                "detail": "SHA-256 MISMATCH — possible model substitution",
                "expected": expected_sha,
                "actual": record["sha256"],
            }
    else:
        record["checks"]["manifest_integrity"] = {
            "result": "NOT ASSESSED",
            "detail": "No reference manifest provided."
        }
        record["checks"]["hash_match"] = {
            "result": "NOT ASSESSED",
            "detail": "No reference manifest provided. Cannot verify integrity.",
        }

    return record


def check_model_substitution(
    model_path: Path,
    reference_manifest: Dict[str, str],
) -> Dict[str, Any]:
    """
    Dedicated model substitution finding with severity grading.

    Returns a security finding dict.
    """
    actual_sha = sha256_file(model_path) if model_path.exists() else None
    expected_sha = reference_manifest.get(model_path.name)

    if not model_path.exists():
        result, severity = "FAIL", "CRITICAL"
        detail = "Model file is missing"
    elif expected_sha is None:
        result, severity = "NOT ASSESSED", "INFO"
        detail = "Model not listed in reference manifest"
    elif actual_sha == expected_sha:
        result, severity = "PASS", "INFO"
        detail = "Hash matches reference"
    else:
        result, severity = "ANOMALY_DETECTED", "CRITICAL"
        detail = "Hash mismatch — model may have been substituted or corrupted"

    return {
        "check_id": "SEC-MDL-001",
        "name": "Model Substitution / Integrity Check",
        "result": result,
        "severity": severity,
        "confidence": "HIGH",  # SHA-256 is deterministic
        "evidence": {
            "filename": model_path.name,
            "expected_sha256": expected_sha,
            "actual_sha256": actual_sha,
        },
        "description": detail,
        "recommended_action": (
            "If a hash mismatch is detected, do not use this model in production. "
            "Obtain the model from the original trusted source and verify again."
        ),
        "limitation": (
            "SHA-256 hash matching verifies file identity, NOT model correctness or safety. "
            "A matching hash does NOT guarantee the model is free of backdoors."
        ),
        "trace": {
            "operation_id": "SHA256_MODEL_VERIFY",
            "operation_type": "Cryptographic File Identity Verification",
            "formula": "actual_digest == expected_digest",
            "inputs": {
                "file_path": str(model_path.name),
                "file_size_bytes": model_path.stat().st_size if model_path.exists() else None,
            },
            "intermediate_values": {
                "hash_algorithm": "SHA-256",
                "actual_digest": actual_sha,
                "expected_digest": expected_sha
            },
            "result": "EQUAL" if actual_sha == expected_sha else "NOT EQUAL",
            "threshold": "Exact Match",
            "comparison": f"{actual_sha} == {expected_sha}",
            "decision": result,
            "explanation": "Calculates the SHA-256 cryptographic hash of the model artifact file and compares it deterministically against the manifest reference hash to ensure bit-level identity."
        }
    }
