import requests
import json
import time
import shutil
import os
from pathlib import Path

API_BASE = "http://127.0.0.1:8001/api"
FIXTURE_A_ZIP = "data/fixtureA.zip"

print("="*60)
print("TRUSTTRACE CV - LIVE DEMONSTRATION")
print("="*60)

# Wait for server
for _ in range(5):
    try:
        if requests.get(f"{API_BASE}/health").status_code == 200:
            break
    except:
        pass
    time.sleep(1)

print("\n[1] Uploading Clean Dataset...")
with open(FIXTURE_A_ZIP, "rb") as f:
    res = requests.post(f"{API_BASE}/upload/dataset", files={"file": ("fixtureA.zip", f)}, data={"format": "yolo"}).json()
clean_ds_path = res["dataset_path"]
print(f"    -> Uploaded to {clean_ds_path}")

print("\n[2] Running Full Audit (Clean State)...")
req = {
    "dataset_path": clean_ds_path,
    "model_path": "models/fixtures/dummy_detector.pt",
    "manifest_path": "models/fixtures/manifest.json",
    "inference_log": "data/fixtures/inference_logs/inference_log.jsonl"
}
res = requests.post(f"{API_BASE}/audit/full", json=req).json()
print(f"    -> Verdict: {res['verdict']}")
print("    -> Findings:")
for f in res['findings']:
    print(f"       [{f['result']}] {f['name']} (Severity: {f['severity']})")

print("\n[3] Tampering with the Model Manifest Signature...")
tampered_manifest = Path("models/fixtures/manifest_tampered.json")
with open("models/fixtures/manifest.json", "r") as f:
    m = json.load(f)
m["hmac_sig"] = "badc0ffee" + "0" * 55 # tampered
with open(tampered_manifest, "w") as f:
    json.dump(m, f)

req["manifest_path"] = str(tampered_manifest)
res = requests.post(f"{API_BASE}/audit/full", json=req).json()
print(f"    -> Verdict after Tampering: {res['verdict']}")
print("    -> Findings:")
for f in res['findings']:
    if f["result"] != "PASS" and f["result"] != "NOT_ASSESSED":
        print(f"       [{f['result']}] {f['name']} (Severity: {f['severity']})")

print("\n[4] Tampering with Dataset Labels (Label Flipping)...")
tampered_ds_path = f"{clean_ds_path}_tampered"
if os.path.exists(tampered_ds_path):
    shutil.rmtree(tampered_ds_path)
shutil.copytree(clean_ds_path, tampered_ds_path)

# Flip a label in the dataset
label_file = list(Path(tampered_ds_path).glob("labels/*.txt"))[0]
content = label_file.read_text()
# YOLO format: <class> <x> <y> <w> <h>
# Just change the first digit (class id) to something completely out of bounds or different
new_content = "99" + content[content.find(" "):]
label_file.write_text(new_content)

req["manifest_path"] = "models/fixtures/manifest.json" # reset manifest
req["dataset_path"] = tampered_ds_path
res = requests.post(f"{API_BASE}/audit/full", json=req).json()
print(f"    -> Verdict after Dataset Tampering: {res['verdict']}")
print("    -> Findings:")
for f in res['findings']:
    if f["result"] != "PASS" and f["result"] != "NOT_ASSESSED":
        print(f"       [{f['result']}] {f['name']} - {f['description']}")


print("\n[5] Replaying an Inference Record...")
res = requests.post(f"{API_BASE}/audit/full", json=req).json()
# Replay check will hit because inference_log has same records!
print(f"    -> Verdict on Replay: {res['verdict']}")
for f in res['findings']:
    if f["check_id"] == "SEC-INF-002" and f["result"] == "ANOMALY_DETECTED":
         print(f"       [{f['result']}] {f['name']} - {f['description']}")

print("\n="*60)
print("DEMONSTRATION COMPLETE")
print("="*60)
