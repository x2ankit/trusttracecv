# Trustworthy CV Integrity Assurance — Research & Solution Report

**Problem statement:** Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines **Organisation:** Ministry of Defence / Indian Army (DGIS) **Report status:** Pre-validation design. Nothing here has been executed or benchmarked yet. **Tag legend:** \[Certain\] = established or directly sourced · \[Inference\] = high-probability conclusion · \[Hypothesis\] = needs validation

---

## 0. Bottom line

1. \[Certain\] Every required capability has partial prior art. No single public project covers data + model + inference provenance + shift + governance together. The integration and the honesty about limits are the contribution, not any single detector.
2. \[Certain\] At least two public repos already target this exact PS (CVIF-SIH2026, VisionTrustAI). Both use a near-identical headline architecture. A generic "four pillars + Ed25519 + hash chain + Neural Cleanse" design will not stand out.
3. \[Certain\] Model-level backdoor detection on object detectors is unsolved at high reliability. Published results on the NIST TrojAI object-detection round are far from perfect. Any claim of dependable backdoor detection is a credibility risk.
4. \[Inference\] The primary constraint is **engineering bandwidth against breadth**, not algorithm novelty. Build order must be certainty-first: deterministic crypto and audit, then data and source aggregation, then shift, then model integrity.
5. \[Inference\] The strongest differentiators, in order: (a) access-tiered model assessment with explicit "unavailable" reporting, (b) source-level Bayesian aggregation with false-discovery control, (c) verify-by-recompute on inference records, (d) a drift-vs-manipulation discriminator with stated evidence, (e) a rigorous coverage statement.

### Correction of Premise

**The Flaw:** The assumption that there is a public "Indian Army DGIS approach" to copy or benchmark against. No public DGIS technical implementation for CV integrity assurance was found. **The Correction:** The closest public doctrine is the DRDO/MoD **ETAI (Evaluating Trustworthy AI) Framework and Guidelines**, launched 17 Oct 2024 by the CDS and DRDO Chairman. It is a risk-based assessment framework, built by DRDO's Scientific Analysis Group. \[Certain\] Align report fields and vocabulary to it after reading the primary document (not yet read by me). **The Downside:** Asserting unverified claims about how the Army "currently does it" in front of a jury from that organisation is checkable and fatal to credibility.

---

## 1. Threat model

| Asset | Threat (from PS) | Attacker capability assumed |
| --- | --- | --- |
| Training data | Trigger injection, label flipping, systematic mislabelling, near-duplicate flooding, OOD insertion | One or more malicious/careless contributors; cannot alter the auditor |
| Model | Substitution, modification, hidden backdoor | Supplier controls weights; auditor may have file-only, black-box or white-box access |
| Inference records | Replay, replacement, post-hoc alteration | Attacker can write to record storage; may or may not hold the signing key |
| Operational data | Shift from terrain/season/sensor/illumination, or deliberate manipulation | Natural drift or adversary |
| Auditor itself | Log tampering | Out of scope beyond tamper-**evidence** (see §8) |

---

## 2. Prior-art survey (sourced)

### 2.1 Backdoor / trojan detection (model level)

- **Neural Cleanse** (trigger inversion, outlier on trigger size), **ABS** (neuron stimulation), **Trojan Signatures**, **MNTD**, **ULP**, **TABOR**, **K-Arm**. All are classification-era. \[Certain, per surveys\]
- **Known weaknesses:** Neural Cleanse assumes small triggers; ABS makes strong assumptions on neuron interaction and is weaker for class-specific triggers. A forensics paper (BEAGLE) found NC works well mainly for universal patch triggers and that NC/ABS variants fail on complex triggers such as WaNet. \[Certain\]
- **Object detection** is harder: BadDet defines four attacks (Object Generation, Regional Misclassification, Global Misclassification, Object Disappearance) on Faster-RCNN/YOLOv3 and showed fine-tuning on benign data does not remove the backdoor. \[Certain\] Detection-specific scanners: **ODSCAN** (SP'24), **DJANGO** (NeurIPS'23), a 2026 pre-NMS distribution-shift method, and MIA (two-stage models). \[Certain that they exist; I did not verify their released code\]
- **Reality check:** On TrojAI Round 13 (object detection), one linear-weight-classification paper reports only one technique exceeded AUC 0.8 and its own method failed; ODSCAN's paper states other methods reached at most 0.763. \[Certain, self-reported by papers\]

### 2.2 Benchmarks and tooling (GitHub)

| Repo | Gives us | Caveat |
| --- | --- | --- |
| `usnistgov/trojai-example`, `trojai-round-generation`, NIST trojan embedding tools (JHU/APL) | Detector I/O pattern; reproducible trojaned-model generation; Round 10 & 13 object-detection model sets (Round 13 uses DOTA_v2 aerial imagery + SSD/Faster R-CNN/DETR) | Large downloads; fetch before going air-gapped. Round 13 relevance to aerial terrain is high. |
| `SCLBD/BackdoorBench` | 16–20 attacks, 28–32 defences (STRIP, SentiNet, TeCo, SS, AC, SPECTRE, NC, ABL…); CIFAR-10/100, GTSRB, Tiny-ImageNet | Classification-centric; licence unverified; Python 3.8-era env |
| `Trusted-AI/adversarial-robustness-toolbox` (ART) | MIT-licensed badge shown; ActivationDefence, SpectralSignatures, provenance-based poison detection; YOLOv8+ support from v1.20 | Research library, not an assurance system |
| `cleanlab/cleanlab` | ObjectLab label-error detection for object detection; duplicates, outliers | **Verify licence** (I believe copyleft; unconfirmed) |
| `SeldonIO/alibi-detect` | MMD / learned-kernel MMD drift | Described as **source-available**, not OSS — licence risk. Implement MMD ourselves. |
| `sigstore/model-transparency` (OMS) | Model hashing manifest, in-toto statements, signing with bare keys / certs / Sigstore | Sigstore keyless needs network; use **bare-key mode** offline |
| `modelsign` (PyPI) | Offline Ed25519 model signing | Small project; evaluate before relying on it |
| `usnistgov/trojai-literature` | Curated paper list | Reading list only |

### 2.3 Directly competing public repos for this PS (same PS title)

- **CVIF-SIH2026** — Self-described as four pillars (dataset DT-1..6, model MT-1..4, provenance IT-1..5, shift DS-1..4). Features claimed: COCO/YOLO adapters, Neural Cleanse, pickle pre-flight scan, Ed25519 + nonce + sequence + stream hash chain, MMD/Wasserstein/KS, Veto + Noisy-OR + anti-dilution scoring, content-addressed evidence store, hash-chained audit, FastAPI + React UI, 346 tests. \[Certain these are the README's claims; unverified by execution\]
- **VisionTrustAI (ZTAAF)** — DataGuard, ModelShield (behavioural fingerprint + "Neural-Cleanse-Lite"), InferenceVault (Merkle tree), a trust graph that propagates distrust to dependent models, and an attack-injection suite. \[Certain as README claims\]
- \[Inference\] Their gaps: heavy reliance on Neural Cleanse-style inversion (weak on complex triggers and not built for detection boxes); shift detection that reports distance but not a drift-vs-manipulation judgement; README-level claims with no published benchmark numbers visible to me. **Use them to learn what judges will see; do not copy code.**

### 2.4 Provenance and standards

- OpenSSF Model Signing: detached Sigstore-bundle format containing an in-toto statement + signature; PKI-agnostic. \[Certain\]
- Sigstore transparency logs give inclusion proofs but need network; in an air-gap they are replaced by a local signed Merkle checkpoint (§6.3).

---

## 3. Gap analysis → where we can be better

| PS requirement | Existing state | Our improvement |
| --- | --- | --- |
| 2.2.1 Data integrity + **source-level** risk | Sample-level detectors only (cleanlab, AC, SS) | Calibrated per-sample evidence → **per-contributor posterior** with FDR control |
| 2.2.2 Model integrity with stated access | Mostly white-box research code | **Access tiers** T0/T1/T2 with explicit "unavailable" verdicts |
| 2.2.3 Provenance | Signing tools bind files, not inferences | Inference-record binding + **verify-by-recompute** |
| 2.2.4 Shift | Detectors output a distance | **Characterise + discriminate** drift vs manipulation |
| 2.2.5 Governance | Ad-hoc logs | Fixed finding schema, dispositions, hash-chained audit, standalone verifier, coverage statement |
| 2.2.6 Offline | Many tools pull weights/telemetry | Vendored wheels and bundled feature extractor; socket-deny test |

---

## 4. System architecture

```
                 ┌─────────────── Ingestion (offline) ───────────────┐
 COCO / YOLO ───►│ dataset adapter → canonical manifest + sample hashes │
 ONNX / .pt /    │ model adapter  → safe-load sandbox + weight manifest  │
 TorchScript ───►│ inference-log adapter → record parser                 │
                 └───────────────┬───────────────────────────────────────┘
                                 ▼
        ┌────────────┬────────────────┬──────────────┬──────────────┐
        │ Data       │ Model          │ Provenance   │ Shift        │
        │ integrity  │ integrity      │ verifier     │ assessor     │
        │ (D-checks) │ T0/T1/T2       │ (P-checks)   │ (S-checks)   │
        └─────┬──────┴───────┬────────┴──────┬───────┴──────┬───────┘
              └──────► Finding bus (uniform schema, §7) ◄─────┘
                                 ▼
                 Aggregation & calibration engine
          (source-level Bayes · noisy-OR per asset · hard vetoes)
                                 ▼
        Disposition: ACCEPT / REVIEW / QUARANTINE + coverage statement
                                 ▼
   Evidence store (content-addressed) + hash-chained audit + signed checkpoints
                                 ▼
          CLI · static HTML/PDF report · optional local web UI
```

**Design rules**

- \[Certain\] Checks are plugins behind one interface: `run(asset, access_level, config) → [Finding]`. This satisfies "extensible, not hard-coded to one architecture".
- \[Certain\] Model loading is sandboxed: subprocess, no network, allow-listed environment. PyTorch checkpoints are pickle-based; use `weights_only` loading where possible and scan opcodes before any load.
- \[Inference\] Hard vetoes (deterministic failures such as a bad signature or a digest mismatch) force QUARANTINE regardless of other scores. Probabilistic findings combine by noisy-OR but are never allowed to dilute a critical one.
- Stack: Python 3.11, onnxruntime, PyTorch (CPU/GPU), NumPy/SciPy/scikit-learn, PyNaCl or `cryptography` (Ed25519), SQLite, Typer CLI, Jinja2 → static HTML. JSON Schema 2020-12 for all artifacts.

---

## 5. Capability designs

### 5.1 Training-data integrity (D)

| ID | Target | Method | Confidence basis |
| --- | --- | --- | --- |
| D1 | Near-duplicate flooding | Perceptual hash (dHash/pHash) + embedding ANN clusters; cluster size and per-source concentration | \[Certain\] for exact/near-exact; \[Inference\] for semantic dupes |
| D2 | Label flipping / mislabelling | Out-of-fold predictions from a small proxy model on bundled features → confident-learning scores; for boxes use an ObjectLab-style check (missed, spurious, swapped, shifted boxes) | \[Inference\] |
| D3 | Trigger injection (patch/blend) | Spatial recurrence: same local patch at recurring position/scale across samples; frequency-domain anomaly; activation clustering / spectral signatures on proxy features | \[Inference\]; \[Hypothesis\] for stealthy triggers |
| D4 | OOD insertion | Mahalanobis / kNN distance in embedding space against per-class reference; conformal threshold | \[Inference\] |
| D5 | Systematic mislabelling | Class-confusion structure: a consistent directional confusion concentrated in one source | \[Inference\] |
| D6 | **Source-level aggregation** | See below | \[Inference\] |

**D6 method.** Convert each detector score to a calibrated probability `p_i` (isotonic on synthetic validation). For contributor *c* with *n_c* samples, model flagged count as Beta-Binomial with a prior fitted on the pooled batch. Report `P(contamination rate of c > ε)` plus a Benjamini–Hochberg-adjusted rank across contributors. Add concentration evidence: shared trigger signature, duplicate-cluster membership, label-flip direction. \[Hypothesis\] This beats flagging isolated samples; validate on multi-contributor synthetic splits with one to three bad sources at 1–20% poison rates.

**Without contributor metadata:** fall back to sample-level findings and to unsupervised grouping by file metadata/EXIF/annotation-tool fields, clearly marked as inferred grouping.

### 5.2 Model integrity (M) — access-tiered

| Tier | Access | Checks | Output when unavailable |
| --- | --- | --- | --- |
| **T0 File-only** | Weights file | Format validation, pickle opcode scan, SHA-256 weight manifest (OMS-style per-file hashing), digest vs declared registry, architecture/tensor-shape hash, layer-wise diff vs a reference model if supplied, weight statistic outliers | — (always runs) |
| **T1 Black-box** | Query outputs only (ONNX runtime is enough) | **Reference battery:** fixed probe set → behavioural fingerprint → distance to reference fingerprint (substitution/modification). **Trigger-hypothesis sweep:** stamp a library of patch/blend/frequency triggers at several sizes/positions and measure output collapse. For classifiers: label concentration. For detectors: ghost boxes (object generation), vanishing boxes (disappearance), class flips (regional/global misclassification). **Input-level:** STRIP, SCALE-UP, TeCo-style consistency on supplied images | Reports "T2 unavailable" |
| **T2a Grey-box (ONNX graph)** | Intermediate activations, no gradients | Expose internal tensors via graph edit → activation clustering, neuron-level stimulation (ABS-style), activation statistics vs reference | Reports "gradient-based inversion unavailable" |
| **T2b White-box (PyTorch/TorchScript)** | Gradients | Detection-adapted trigger inversion (simplified ODSCAN/DJANGO-style), weight-space statistics | — |

- \[Certain\] Each assessment block states: access assumed, methods run, methods skipped and why, detection coverage, and a confidence with its basis tag.
- \[Hypothesis\] Fusing T0+T1+T2 scores via noisy-OR improves recall over any single method; validate against the TrojAI object-detection sets and our own planted backdoors.
- **Do not claim** reliable detection of complex triggers (WaNet-class, input-aware, feature-space). Put them in the "partial/unsupported" column.
- Reference-free caution: without a reference model, substitution can only be detected via registry digests or consistency with declared behaviour, not proven. State it.

### 5.3 Inference provenance and output integrity (P)

**Record (canonicalised with RFC 8785 JCS, signed with Ed25519):**

```json
{
  "schema": "cvia.inference/1",
  "record_id": "uuid",
  "seq": 10482,
  "nonce": "128-bit random",
  "ts_wall": "…", "ts_monotonic_ns": 0,
  "input_sha256": "…",
  "model": {"weights_sha256": "…", "manifest_root": "…"},
  "preproc_sha256": "…", "infer_cfg_sha256": "…", "runtime_sha256": "…",
  "output_sha256": "…",
  "prev_record_hash": "…",
  "signer_key_id": "…",
  "signature": "…"
}
```

**Checks**

- P1 signature validity · P2 canonical-form and field completeness · P3 input hash matches the actual image bytes · P4 model digest matches the audited model · P5 nonce uniqueness (replay) · P6 sequence monotonic with no gaps · P7 hash-chain continuity (deletion/reordering) · P8 timestamp plausibility vs sequence.
- **P9 verify-by-recompute (differentiator):** re-run the declared model on the stored input with the declared config and compare to the recorded output within a tolerance. \[Certain\] This detects output substitution even if an attacker holds a valid signing key. \[Inference\] Exact match is realistic on deterministic CPU runs; GPU non-determinism needs a stated tolerance.
- \[Certain\] Limitation to declare: a fully compromised signing key plus a compromised recompute environment defeats this layer. Key custody (TPM/HSM or offline key ceremony) is a deployment assumption, not something software can prove.
- \[Certain\] Timestamps offline are only as trustworthy as the local clock; we bind ordering through sequence and chain, and treat wall-clock as advisory. Declare it.
- A real blockchain is not needed: for a single-authority, air-gapped deployment, a hash chain with signed Merkle checkpoints gives tamper-evidence without consensus overhead. \[Inference\]

### 5.4 Distribution shift and anomaly assessment (S)

**Characterise** against the declared reference set:

1. Photometric statistics (brightness, contrast, colour histogram, saturation) → illumination/season/sensor signature
2. Frequency spectrum and noise residuals → sensor/compression change
3. Embedding-space MMD with permutation p-value (own implementation; avoids the alibi-detect licence issue)
4. Output-space shift: class priors, confidence histograms, box-size and count distributions
5. Calibrated risk score by bootstrap over the reference set; report ECE on synthetic tests

**Discriminate drift vs manipulation** — \[Hypothesis\], needs validation:

| Evidence | Points to operational drift | Points to manipulation |
| --- | --- | --- |
| Spatial pattern | Global, smooth, affects all images | Localised, repeated patch/pattern |
| Explained by low-dimensional photometric change | Yes | Residual remains after compensating |
| Source spread | Shared across contributors/sensors | Concentrated in one source |
| Label coupling | Independent of label | Correlated with one label/class |
| Temporal shape | Gradual or seasonal | Abrupt step or burst |

Output: shift type, magnitude, which factors explain it, and a verdict of `probable drift` / `suspicious` / `indeterminate` with stated evidence. Default to `indeterminate` when evidence is thin. \[Inference\]

### 5.5 Analyst-facing assurance and governance (G)

**Finding schema** (every flag; JSON Schema published with the submission):

```json
{
  "finding_id": "…", "check_id": "D3",
  "asset": {"type": "dataset|model|record|stream", "id": "…", "sha256": "…"},
  "attack_class": "trigger_injection",
  "severity": "low|medium|high|critical",
  "confidence": {"value": 0.0, "basis": "Certain|Inference|Hypothesis", "calibration": "isotonic/ECE=…"},
  "reason": "human-readable sentence",
  "evidence": [{"type": "image|plot|metric|hash", "ref": "…", "sha256": "…"}],
  "access_level_used": "T1", "access_level_needed": "T2",
  "disposition": "accept|review|quarantine",
  "limitations": ["…"]
}
```

- **Disposition policy** is explicit and versioned: hard veto → quarantine; calibrated risk above a threshold → quarantine; mid band → review; otherwise accept. Thresholds are configurable and recorded in the report.
- **Audit trail:** JSON-lines, `H_n = SHA256(H_{n-1} ‖ canon(event_n))`, periodic Ed25519-signed Merkle checkpoint. A **standalone verifier** (single file, minimal dependencies) lets a third party verify offline.
- **Coverage statement:** auto-generated from the plugin registry, listing supported, partially supported and unsupported attack classes (§8).

---

## 6. Offline and constraint compliance

| Constraint | Approach |
| --- | --- |
| Air-gapped | Vendored wheels, pinned lockfile, bundled feature-extractor weights (licence check), CI test that denies all sockets and DNS |
| COCO + YOLO | Adapters to one canonical in-memory manifest; handle missing boxes, normalised vs absolute coordinates, class-map mismatches |
| ONNX + PyTorch/TorchScript | Runtime adapters; ONNX via onnxruntime; TorchScript/PyTorch via sandboxed subprocess |
| No retraining for baseline | All T0/T1/T2 and D/P/S checks are inference-only; optional remediation (filter-and-retrain) is a separate module |
| Graceful degradation | Every check declares `required_access`; missing access yields an explicit "unavailable" finding, never a silent pass |
| Reproducibility | Seeded scenario generator, locked dependencies, hash-pinned datasets, one command to regenerate the audit log |

---

## 7. Validation plan (before claiming anything)

**Scenario generator ("red team" module)**, fully seeded:

- Data: BadNets/blended patch, label flip at x%, systematic class-pair confusion, near-duplicate flood, OOD injection, per-contributor poison split
- Model: backdoored classifier and detector via BackdoorBench and NIST trojan tooling; substituted and fine-tuned/pruned variants; clean controls
- Records: modified output, replayed record, deleted record, reordered sequence, swapped model digest, forged signature
- Shift: synthetic haze/fog, illumination, sensor noise, seasonal colour shift vs planted triggers

**Datasets (public, verify each licence):** GTSRB and CIFAR-10 for fast iteration; COCO subset; an aerial set such as DOTA (Round 13 of TrojAI is built on DOTA_v2 backgrounds) for terrain realism. \[Hypothesis\] that licence terms permit our use; check before bundling.

**Metrics:** per-attack AUROC and TPR@1%FPR; source-level precision/recall and FDR; crypto tamper detection (target is 100% with zero false accepts); calibration ECE; runtime and memory per asset; false-positive rate on clean data.

**Baselines:** ART ActivationDefence and SpectralSignatures, BackdoorBench STRIP/SS/AC/NC, cleanlab ObjectLab, scipy MMD. Report honestly where we lose.

**Go/no-go gates:** a check that does not beat its baseline or has uncalibrated confidence ships as `experimental` with a declared limitation, or is cut.

---

## 8. Coverage statement (draft)

| Class | Status |
| --- | --- |
| Patch/blend triggers in training data | Supported (measured) |
| Label flipping, systematic mislabelling | Supported |
| Near-duplicate flooding, OOD insertion | Supported |
| Source-level contamination | Supported where metadata exists; degraded otherwise |
| Model substitution / weight modification | Supported with a reference; registry-digest only without |
| Patch-style backdoors (classifier/detector) | Partial; depends on trigger library coverage and access tier |
| Complex triggers (warping, input-aware, feature-space, semantic) | **Not supported** beyond opportunistic behavioural flags |
| Clean-label attacks with weak feature signal | **Partial / low confidence** |
| Adaptive attacker who knows our detectors | **Not supported** |
| Inference record tamper, replay, deletion, reorder | Supported (deterministic) |
| Compromised signing key and compromised recompute host | **Not supported** |
| Audit-log tail truncation | Detectable only against an externally anchored checkpoint |
| Encrypted or obfuscated models | **Not supported** (T0 only) |
| Hardware-level trojans, training-pipeline side channels | **Out of scope** |

---

## 9. Build order (certainty-first)

1. **Phase 1 — Foundation:** canonical schemas, finding bus, evidence store, hash-chained audit, standalone verifier, CLI skeleton.
2. **Phase 2 — Provenance (P1–P9):** fully deterministic and demo-able; built first to bank certainty.
3. **Phase 3 — Scenario generator + COCO/YOLO adapters.**
4. **Phase 4 — Data integrity (D1–D6)** with source-level aggregation.
5. **Phase 5 — Shift (S)** with the drift-vs-manipulation discriminator.
6. **Phase 6 — Model integrity T0 → T1 → T2a → T2b**, in that order.
7. **Phase 7 — Report generator, calibration, benchmark tables, coverage statement, submission packaging.**

---

## 10. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Scope too wide for the time available | Shallow everything | Phase gating; cut T2b first |
| Model-level detector underperforms | Judges' live backdoor fails | Lead with T1 behavioural sweep and honest confidence; show the tier table |
| Licence contamination (AGPL/BSL libraries) | Legal risk for a defence deliverable | Licence audit; own MMD/hash/dedup code; avoid AGPL dependencies in core |
| Near-identical competing submissions | No differentiation | §3 differentiators, published benchmark numbers, standalone verifier demo |
| Synthetic-only validation | Overstated real-world claims | State the limitation; add a TrojAI held-out evaluation |
| Bundled pretrained extractor licence | Offline claim breaks | Choose a permissively licensed backbone; document provenance |

---

## 11. Open items needed to move from \[Hypothesis\] to \[Inference\]

1. Read the ETAI framework primary document and map report fields to its criteria.
2. Confirm exact organiser-defined model formats/versions and any supplied reference model or dataset sizes.
3. Confirm the submission deadline, team size and GPU availability.
4. Run licence checks on: BackdoorBench, cleanlab, OMS/model-transparency, any bundled backbone, each dataset.
5. Execute baselines on one classification and one detection scenario to fix realistic targets.

---

## Sources consulted

- NIST TrojAI literature list — github.com/usnistgov/trojai-literature
- NIST TrojAI software/round docs — pages.nist.gov/trojai (object-detection-jul2022, object-detection-feb2023, software)
- usnistgov/trojai-example; usnistgov/trojai-round-generation
- BackdoorBench — github.com/SCLBD/BackdoorBench; backdoorbench.github.io; NeurIPS'22 paper; IJCV extension
- Adversarial Robustness Toolbox — github.com/Trusted-AI/adversarial-robustness-toolbox
- ODSCAN (SP'24) — answ.in/static/papers/SP24_Cheng.pdf; DJANGO (NeurIPS'23)
- BadDet — arxiv.org/abs/2205.14497; BadDet+ — arxiv.org/html/2601.21066
- BEAGLE — arxiv.org/pdf/2301.06241
- Linear weight classification for trojan detection — arxiv.org/html/2411.03445v1
- Trojan Detection Challenge — proceedings.mlr.press/v220/mazeika23a
- cleanlab object-detection docs — docs.cleanlab.ai/stable/tutorials/object_detection.html
- alibi-detect — github.com/SeldonIO/alibi-detect
- OpenSSF model-signing spec — github.com/ossf/model-signing-spec; sigstore/model-transparency; modelsign (PyPI)
- ETAI framework coverage — Ministry of Defence post (17 Oct 2024), MediaNama, ORF (Feb 2026)
- Competing public repos — github.com/adhavsri123-alt/CVIF-SIH2026; github.com/ameya2401/VisionTrustAI

*Limits of this research: no code was executed, no repo was audited line-by-line, licences were not verified, and competitor claims are README-level.*