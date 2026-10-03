# TRUSTTRACE CV

## A Unified Integrity-Assurance System for Multi-Contributor Computer-Vision Pipelines

**SIH Problem Statement:** SIH26228 --- *Trustworthy Computer Vision
Integrity Assurance for Data, Models and Inference Outputs in
Multi-Contributor Pipelines*\
**Organisation listed in the problem statement:** Ministry of Defence /
Indian Army (DGIS)\
**Document type:** Consolidated solution design, technical architecture,
mathematical specification, and validation plan\
**Version:** 1.0 --- pre-implementation design\
**Status:** Proposed architecture; benchmark claims and detector
performance remain to be validated.

------------------------------------------------------------------------

## Executive summary

TRUSTTRACE CV is an offline-first assurance workbench that evaluates the
integrity of computer-vision datasets, model artifacts, inference
records, and deployment data distributions. It converts multiple
heterogeneous checks into a common evidence format and produces an
auditable disposition---**ACCEPT, REVIEW, or QUARANTINE**---with
reasons, evidence references, confidence basis, coverage limitations,
and a tamper-evident audit trail.

The problem is not solved by one detector or by adding a blockchain.
Training-data poisoning, model backdoors, inference-record tampering,
and natural distribution shift are different failure classes and require
different evidence. TRUSTTRACE CV therefore combines:

1.  **Data integrity analysis:** near-duplicate flooding, suspected
    trigger recurrence, label errors, systematic mislabelling,
    out-of-distribution (OOD) samples, and contributor/batch-level risk.
2.  **Model integrity assessment:** artifact and digest checks,
    reference-based behavioural fingerprinting, controlled
    trigger-hypothesis tests, and optional grey-/white-box methods where
    access permits.
3.  **Inference provenance:** cryptographically bind input, model
    digest, preprocessing, inference configuration, runtime identity,
    output, sequence and nonce; independently verify records and
    optionally recompute predictions.
4.  **Distribution-shift assessment:** quantify deviation from a
    declared reference distribution and assess whether available
    evidence is more consistent with broad operational drift, a
    localised suspicious pattern, or an indeterminate case.
5.  **Analyst governance:** standardised findings, evidence retention,
    explicit policy thresholds, reproducible reports, coverage
    statements, and a standalone offline verifier.

The core differentiator is **evidence integration with honest limits**.
Deterministic integrity failures (for example, an invalid signature or
digest mismatch) are treated differently from probabilistic ML signals.
A missing capability is reported as *unavailable* or *not assessed*,
never silently interpreted as a clean result.

No public implementation can establish that all possible model backdoors
or adaptive attacks will be detected. TRUSTTRACE CV will state which
tests ran, under which access assumptions, with what measured
performance, and which attack classes remain unsupported.

### What this proposal does not claim

-   It does not claim that the system has already been implemented,
    benchmarked, or accepted by the organiser.
-   It does not claim access to classified, internal, or non-public
    DGIS/Indian Army systems.
-   It does not claim that public competitor repository descriptions
    have been independently audited.
-   It does not claim universal detection of stealthy or adaptive
    backdoors.
-   It does not require a blockchain consensus network. For an offline,
    single-authority workflow, signed manifests, hash chains, and signed
    checkpoints are simpler to operate and can provide tamper evidence
    under stated key-custody assumptions.

------------------------------------------------------------------------

## 1. Problem statement and requirements mapping

The system is designed around the problem statement's requirements,
rather than around a preferred algorithm.

  -------------------------------------------------------------------------------
  PS requirement                TRUSTTRACE CV component Main output
  ----------------------------- ----------------------- -------------------------
  Detect trigger injection,     Data Integrity Engine   Sample-level findings,
  label flipping/systematic                             clusters, batch/source
  mislabelling, near-duplicate                          summaries
  flooding and OOD insertion                            

  Aggregate evidence by         Source Risk Engine      Calibrated risk estimate,
  contributor, batch and source                         uncertainty interval,
                                                        FDR-adjusted
                                                        investigation list

  Assess model substitution and Model Integrity Engine  Artifact verification and
  backdoor-like behaviour                               access-tiered
                                                        behavioural/structural
                                                        evidence

  State model access            Capability/coverage     T0/T1/T2 access
  assumptions, confidence and   registry                declaration and
  limits                                                skipped-check report

  Bind input, model,            Inference Provenance    Signed canonical
  preprocessing/configuration   Engine                  inference record
  and output                                            

  Detect post-hoc modification, Provenance Verifier     Deterministic
  substitution and replay                               verification failures and
                                                        chain-integrity report

  Detect distribution shift in  Shift Assessor          Drift statistics,
  terrain, season, sensor,                              reference comparison,
  illumination or acquisition                           evidence-based
                                                        interpretation

  Provide analyst-readable      Decision and Reporting  ACCEPT / REVIEW /
  reasons, severity, confidence Engine                  QUARANTINE plus
  and action                                            explanations

  Maintain tamper-evident audit Evidence Store and      Content-addressed
  trail                         Audit Log               evidence, hash chain and
                                                        signed checkpoints

  Operate offline/air-gapped    Offline Runtime Package Pinned dependencies,
                                                        local models/assets, no
                                                        network requirement

  Support COCO, YOLO, ONNX,     Adapters                Canonical
  PyTorch/TorchScript                                   dataset/model/inference
                                                        interfaces

  Baseline does not require     Audit-first pipeline    Detection and
  retraining                                            verification without
                                                        mandatory model
                                                        retraining
  -------------------------------------------------------------------------------

### Scope boundaries

**In scope:** software-level evidence about dataset integrity, model
artifacts and observable behaviour, inference records, distribution
shift, auditability, and analyst workflow.

**Out of scope for the baseline:** hardware-level trojans, proof of the
physical provenance of a sensor image, guaranteed detection of arbitrary
adaptive backdoors, secure hardware key custody provided solely by
software, and claims about the internal operational systems of the named
organisation.

------------------------------------------------------------------------

## 2. Threat model and trust assumptions

### 2.1 Assets and threats

  -----------------------------------------------------------------------
  Asset                   Example threat          Observable evidence
  ----------------------- ----------------------- -----------------------
  Dataset samples and     Trigger injection,      Repeated patterns,
  annotations             label flips, systematic annotation/prediction
                          annotation errors,      disagreement, unusual
                          duplicate flooding, OOD embedding distances,
                          insertion               duplicate clusters

  Contributor or batch    One source contributes  Concentration of
                          a disproportionate      calibrated sample-level
                          share of poisoned or    evidence
                          suspicious samples      

  Model artifact          Replacement, unintended Digest mismatch,
                          modification, malicious manifest mismatch,
                          checkpoint, backdoor    reference-behaviour
                                                  deviation,
                                                  trigger-hypothesis
                                                  response

  Inference record        Output changed after    Signature failure, hash
                          inference, record       mismatch, repeated
                          replayed, records       nonce, sequence gap,
                          deleted/reordered       chain break

  Runtime/configuration   Different preprocessing Configuration/runtime
                          or inference settings   digest mismatch;
                                                  recomputation
                                                  discrepancy

  Input stream            Natural drift or        Statistical shift,
                          adversarially           localised repeated
                          introduced patterns     patterns,
                                                  source/temporal
                                                  concentration

  Audit trail             Historical event        Hash-chain/checkpoint
                          changed or removed      verification failure
  -----------------------------------------------------------------------

### 2.2 Attacker capabilities

The design considers one or more contributors who may submit malicious
or low-quality data; a supplier who may provide a substituted or
backdoored model; and an actor who may alter inference-record storage.
Some attackers may know which detectors are used.

The baseline assumes the auditor's executable and policy configuration
are not already malicious. If an attacker controls the host, signing
key, model runtime, and all external checkpoints, software-only controls
cannot provide complete protection. This is an explicit limitation, not
something the system should conceal.

### 2.3 Model-access tiers

  -------------------------------------------------------------------------------
  Tier              Available access       What can be assessed What cannot be
                                                                assumed
  ----------------- ---------------------- -------------------- -----------------
  **T0 ---          File, declared         File hashes,         No behavioural
  Artifact-only**   metadata and optional  manifest checks,     conclusion
                    trusted digest         format checks,       without executing
                                           tensor/graph         or querying the
                                           metadata,            model
                                           safe-loading         
                                           preflight            

  **T1 ---          Inputs and outputs     Reference-probe      No access to
  Black-box**       through a declared     fingerprint,         gradients or
                    runtime                controlled           internal
                                           trigger-hypothesis   activations
                                           sweep, output        
                                           consistency          

  **T2a ---         Intermediate graph     Activation           Gradient-based
  Grey-box**        tensors/activations,   statistics,          trigger inversion
                    no gradients           clustering and       is unavailable
                                           selected             
                                           neuron-response      
                                           analysis             

  **T2b ---         Model structure,       Additional           Access does not
  White-box**       weights and gradients  activation/weight    guarantee
                                           analysis and         detection of
                                           research             arbitrary
                                           trigger-inversion    backdoors
                                           methods              
  -------------------------------------------------------------------------------

Every report states the highest tier actually used, checks skipped, and
the reason each check was unavailable. The system must not convert
"cannot test" into "passed".

------------------------------------------------------------------------

## 3. Design principles and differentiators

### 3.1 A common evidence contract

Each detector is a plugin that returns structured findings instead of
making a final decision in isolation. This permits different methods to
be added, replaced, calibrated, or disabled without rewriting the entire
application.

### 3.2 Separate deterministic integrity from statistical suspicion

Cryptographic verification can determine whether bytes match a known
digest or whether a signature verifies under a supplied public key. It
cannot determine whether a model is semantically safe.

ML detectors produce statistical evidence, not proof. A high anomaly
score is not by itself proof of malicious intent. TRUSTTRACE CV keeps
these evidence classes separate in both scoring and user-facing
explanations.

### 3.3 Verify-by-recompute

Where a model and runtime are available, the verifier can recompute an
inference from the stored input and declared model/configuration and
compare the result with the recorded output. This offers a second path
to detect output substitution. It is not infallible: nondeterministic
GPU kernels, runtime changes, missing dependencies, or a compromised
recomputation environment can complicate the comparison.

### 3.4 Source-level analysis

An isolated suspicious sample may be a benign outlier. A
contributor-level cluster of similar anomalies can be more actionable.
The system aggregates sample evidence by contributor/batch/source when
metadata exists, while clearly marking inferred grouping when it does
not.

### 3.5 Coverage is a first-class output

Every report lists attack classes as **tested with measured
performance**, **partially tested**, **not tested**, or **unsupported**.
The label "supported" is not used as a substitute for measured evidence.

------------------------------------------------------------------------

## 4. System architecture

``` text
                      OFFLINE / AIR-GAPPED WORKSPACE
 ┌─────────────────────────────────────────────────────────────────────┐
 │ Inputs                                                              │
 │  COCO / YOLO datasets     ONNX / PyTorch / TorchScript models        │
 │  inference logs           declared references, policies, keys        │
 └──────────────────┬─────────────────────────────┬────────────────────┘
                    │                             │
           ┌────────▼────────┐           ┌────────▼─────────┐
           │ Dataset adapter │           │ Model / log      │
           │ + canonical     │           │ adapters         │
           │ manifest        │           │ + safe preflight │
           └────────┬────────┘           └────────┬─────────┘
                    │                             │
       ┌────────────▼────────────┐     ┌──────────▼─────────────┐
       │ Data Integrity Engine   │     │ Model Integrity Engine │
       │ duplicates, labels, OOD │     │ T0 → T1 → T2a → T2b    │
       │ triggers, source risk   │     │ reference comparisons  │
       └────────────┬────────────┘     └──────────┬─────────────┘
                    │                             │
             ┌──────▼─────────────────────────────▼──────┐
             │ Uniform Finding / Evidence Interface      │
             └──────┬─────────────────────────────┬──────┘
                    │                             │
       ┌────────────▼──────────┐      ┌───────────▼───────────┐
       │ Inference Provenance   │      │ Distribution Shift   │
       │ signatures, chain,     │      │ reference statistics,│
       │ replay, recomputation  │      │ drift characterization│
       └────────────┬──────────┘      └───────────┬───────────┘
                    └──────────────┬───────────────┘
                                   ▼
                  ┌────────────────────────────────┐
                  │ Policy + calibrated evidence   │
                  │ hard vetoes / uncertainty      │
                  └────────────────┬───────────────┘
                                   ▼
                ACCEPT / REVIEW / QUARANTINE + coverage
                                   ▼
           Content-addressed evidence + hash-chained audit log
                                   ▼
             CLI + static HTML/JSON report + offline verifier
```

### 4.1 Core interfaces

Recommended plugin contract:

``` python
run(
    asset,
    access_level,
    config,
    reference=None
) -> list[Finding]
```

Each plugin declares its identifier, version, required inputs, access
tier, deterministic/probabilistic nature, dependencies, output schema,
and known limitations. The runtime records the exact plugin version and
configuration used.

### 4.2 Suggested implementation stack

  -----------------------------------------------------------------------
  Layer                   Initial choice          Rationale / caveat
  ----------------------- ----------------------- -----------------------
  Language                Python 3.11             Mature ML/security
                                                  ecosystem; pin exact
                                                  version

  CLI                     Typer or argparse       Reproducible offline
                                                  command interface

  Schemas                 JSON Schema 2020-12     Validate findings,
                                                  manifests and reports

  Numerical/statistical   NumPy, SciPy,           Distances, tests,
  layer                   scikit-learn            calibration, statistics

  Vision/model runtime    ONNX Runtime; PyTorch   Separate ONNX and
                          where required          PyTorch adapters

  Cryptography            `cryptography` or       Ed25519 signatures and
                          PyNaCl                  SHA-256 digests

  Metadata/evidence index SQLite +                Simple offline storage;
                          content-addressed files evidence files are
                                                  immutable by digest

  Reports                 JSON + static HTML;     Machine-readable and
                          optional PDF            analyst-readable
                                                  outputs

  Tests                   pytest + deterministic  Reproducible regression
                          scenario generator      and attack-injection
                                                  tests
  -----------------------------------------------------------------------

Dependencies, model weights, licenses and hashes must be audited before
bundling. Core provenance verification should have a minimal dependency
path and must not require network access.

------------------------------------------------------------------------

## 5. Data integrity engine

### 5.1 Canonical dataset manifest

Each sample should have a stable sample ID, byte-level digest,
annotation digest, source/contributor/batch fields if supplied, format
metadata, and a pointer to the original file. Do not silently normalise
or rewrite source data. Store canonicalised derived metadata separately
from original bytes.

For sample bytes (x_i), define:

\[ h_i = `\operatorname{SHA256}`{=tex}(x_i) \]

A digest detects changes relative to a trusted recorded digest; it does
not establish that the original sample was benign or authentic.

### 5.2 D1 --- Exact and near-duplicate flooding

Use multiple complementary signals:

-   SHA-256 for exact byte-identical files.
-   Perceptual hash (pHash/dHash) for near-identical images under
    limited transformations.
-   Embedding-space nearest-neighbour search for visually or
    semantically similar images.
-   Cluster size and contributor/batch concentration for flooding
    analysis.

For binary perceptual hashes (a,b `\in `{=tex}{0,1}\^m), Hamming
distance is:

\[
d_H(a,b)=`\sum`{=tex}\_{j=1}\^{m}`\mathbf{1}`{=tex}\[a_j`\ne `{=tex}b_j\]
\]

Flag a candidate pair when (d_H(a,b)`\le `{=tex}`\tau`{=tex}\_h), where
(`\tau`{=tex}\_h) is selected using a clean validation set and known
transformed duplicates. Do not use a universal threshold without
measuring false matches. For embeddings (z_i,z_j), cosine distance may
be used:

\[
d\_{`\cos`{=tex}}(z_i,z_j)=1-`\frac{z_i^\top z_j}{\|z_i\|_2\|z_j\|_2}`{=tex}
\]

Embedding similarity is a review signal, not proof that two samples are
duplicates. A cluster becomes more suspicious when it is unusually
large, concentrated in a contributor/batch, and associated with repeated
annotations or trigger-like patterns.

### 5.3 D2 --- Label errors and systematic mislabelling

For classification data, use out-of-fold proxy predictions where
feasible. Avoid evaluating a sample with a proxy model that was trained
on that same sample without controls, since memorisation can distort
confidence.

Let (`\tilde `{=tex}y_i) be the observed label and (p_i(k)) the
out-of-fold estimated probability of class (k). One simple disagreement
signal is:

\[ s_i\^{`\text{disagree}`{=tex}} = 1 - p_i(`\tilde `{=tex}y_i) \]

This is not a calibrated probability that the label is wrong. It must be
calibrated and evaluated on labelled synthetic corruption scenarios.

For object detection, compare annotation boxes with model proposals and
consistency checks: missed objects, spurious boxes, class swaps, unusual
box shifts, invalid coordinates, class-map mismatch, and impossible
dimensions. Proxy-model disagreement can help prioritise review but
cannot replace expert annotation.

For a source (c), build a directed confusion profile:

\[ C\^{(c)}\_{a,b} =
#{i:`\operatorname{source}`{=tex}(i)=c, `\tilde `{=tex}y_i=a, `\hat `{=tex}y_i=b}
\]

Compare the source-specific confusion profile with the pooled reference
profile. A consistent class-pair pattern concentrated in one source is
more actionable than a global confusion pattern. Use uncertainty
intervals and clean controls before calling it systematic mislabelling.

### 5.4 D3 --- Trigger-injection indicators in training data

No single generic detector reliably identifies every poisoning strategy.
Use several weakly complementary signals:

-   repeated local patches at similar position/scale;
-   similar high-frequency or colour residual patterns;
-   clustering in a proxy embedding or activation space;
-   correlation between a recurring visual pattern and a target label;
-   source/batch concentration of the pattern.

For a candidate patch descriptor (q), define recurrence:

\[ r(q)=`\frac{1}{N}`{=tex}`\sum`{=tex}\_{i=1}\^{N}
`\mathbf{1}`{=tex}\[`\text{candidate }`{=tex}q`\text{ occurs in sample }`{=tex}i\]
\]

Also calculate label association and source concentration. A high
recurrence alone may represent a legitimate object, watermark, sensor
artefact, or common scene feature. Trigger evidence must therefore be
contextual and accompanied by example images and uncertainty.

**Coverage limit:** sophisticated clean-label, semantic, input-aware,
warping, or adaptive poisoning may not produce a stable repeated patch.
These cases remain partial or unsupported unless demonstrated by the
evaluation suite.

### 5.5 D4 --- Out-of-distribution insertion

Extract embeddings (z_i) with a documented, locally available feature
extractor. Compare each sample against a declared reference
distribution, preferably by class or operational stratum when reliable
labels exist.

A k-nearest-neighbour score can be:

\[
s_i\^{`\text{kNN}`{=tex}}=`\frac{1}{k}`{=tex}`\sum`{=tex}\_{j`\in `{=tex}`\mathcal `{=tex}N_k(i)}
d(z_i,z_j) \]

A Mahalanobis score for a class/stratum with mean (`\mu`{=tex}) and
covariance (`\Sigma`{=tex}) is:

\[
s_i^{`\text{Mah}`{=tex}}=(z_i-`\mu`{=tex})^`\top`{=tex}`\Sigma`{=tex}\^{-1}(z_i-`\mu`{=tex})
\]

Covariance estimation can be unstable in high dimensions or with small
samples; use regularisation and document it. Calibrate thresholds on
held-out in-distribution examples and known OOD scenarios. An OOD flag
means "different from the declared reference," not "malicious."

### 5.6 D5 --- Contributor/source aggregation

Contributor metadata may be missing, false, or too coarse. Preserve the
distinction between provided metadata and inferred groupings. When
metadata exists, aggregate sample evidence by contributor, batch and
source.

A simple transparent baseline is a Beta-Binomial model. Let (k_c) of
(n_c) samples from contributor (c) exceed a pre-calibrated flag
threshold. Assume:

\[ k_c`\mid `{=tex}`\theta`{=tex}\_c
`\sim `{=tex}`\operatorname{Binomial}`{=tex}(n_c,`\theta`{=tex}\_c) \]

\[ `\theta`{=tex}\_c
`\sim `{=tex}`\operatorname{Beta}`{=tex}(`\alpha`{=tex},`\beta`{=tex})
\]

Then the posterior is:

\[ `\theta`{=tex}\_c`\mid `{=tex}k_c,n_c `\sim`{=tex}
`\operatorname{Beta}`{=tex}(`\alpha`{=tex}+k_c,`\beta`{=tex}+n_c-k_c) \]

The report can provide:

\[ P(`\theta`{=tex}*c\>`\epsilon`{=tex}`\mid `{=tex}k_c,n_c)
=1-I*{`\epsilon`{=tex}}(`\alpha`{=tex}+k_c,`\beta`{=tex}+n_c-k_c) \]

where (I_x(a,b)) is the regularised incomplete beta function and
(`\epsilon`{=tex}) is a declared contamination-rate threshold. This
model is a baseline, not a complete causal model: sample flags may be
correlated, and a detector's false-positive rate must be accounted for.
Fit or choose (`\alpha`{=tex},`\beta`{=tex}) from clean/control data and
disclose the choice.

For ranking many contributors, use Benjamini--Hochberg (BH)
false-discovery-rate adjustment on valid p-values. If (m) hypotheses
have sorted p-values
(p\_{(1)}`\le`{=tex}`\cdots`{=tex}`\le `{=tex}p\_{(m)}), find the
largest (k) such that:

\[ p\_{(k)} `\le `{=tex}`\frac{k}{m}`{=tex}q \]

and flag hypotheses up to (k), at target FDR level (q), subject to the
method's assumptions. Do not apply BH directly to arbitrary anomaly
scores; valid p-values or a defensible null calibration are required.

**Correlation warning:** do not multiply probabilities from highly
correlated detectors as if they were independent. For example, pHash and
embedding similarity may respond to the same duplicate phenomenon. Use
calibrated models, grouped evidence, or conservative rules, and test
calibration under correlated signals.

------------------------------------------------------------------------

## 6. Model integrity engine

### 6.1 T0 --- Artifact integrity and safe preflight

T0 checks should include:

-   SHA-256 of each model artifact and an optional manifest root.
-   Digest comparison against a trusted local registry or signed
    manifest.
-   File-format and metadata validation.
-   Architecture/tensor-shape metadata comparison where available.
-   Optional layer-wise tensor statistics or comparison with a trusted
    reference model.
-   Safe loading procedures and explicit isolation.

PyTorch checkpoint files may involve Python object deserialisation.
Prefer safe, weights-only loading when compatible; inspect untrusted
files in a restricted subprocess with no network and minimal privileges.
Static scanning is only a preflight signal, not a proof that a file is
safe. Do not execute arbitrary untrusted pickle payloads as part of
routine auditing.

A matching digest proves equality to the referenced bytes, not benign
training history or absence of a backdoor. Without a trusted reference
digest or registry, a model's origin cannot be established from the
digest alone.

### 6.2 T1 --- Black-box behavioural fingerprint

Create a versioned probe battery containing representative clean images
and controlled transformations. Record a fingerprint such as:

-   output class distributions;
-   detection count and class frequencies;
-   confidence distributions;
-   box-size/position distributions;
-   output consistency under benign transformations;
-   runtime and preprocessing identity.

For a reference fingerprint vector (`\mu`{=tex}\_r) and observed
fingerprint (v), a simple distance is:

\[ D(v,`\mu`{=tex}\_r)=`\sqrt{(v-\mu_r)^\top W(v-\mu_r)}`{=tex} \]

where (W) is a regularised weighting matrix derived from a reference
set. Thresholds must be estimated from clean model/version variation. A
large distance indicates behavioural deviation, not necessarily
malicious substitution.

### 6.3 Controlled trigger-hypothesis sweep

Run a predefined library of synthetic patch, blend, size, position, and
frequency hypotheses through a controlled test set. For classifiers,
measure target-label concentration; for detectors, measure changes in
object count, class identity, confidence, and box location. Relevant
behaviours include:

-   object generation / ghost boxes;
-   object disappearance;
-   regional or global class misclassification;
-   unusual confidence or localisation shifts.

For a tested trigger hypothesis (t), one possible target-concentration
statistic is:

\[ A(t)=`\max`{=tex}*{y\^\*}`\frac{1}{N}`{=tex}`\sum`{=tex}*{i=1}\^{N}
`\mathbf{1}`{=tex}\[f(T_t(x_i))`\text{ contains target }`{=tex}y\^\*\]
\]

The precise definition must be task-specific. Compare it with clean
controls and benign transformations. A large response is a lead for
investigation, not definitive proof of a backdoor.

### 6.4 T2a/T2b --- Optional grey-/white-box checks

Where internal graph activations are available, examine activation
clustering, unusual layer statistics, or neuron-response concentration.
With gradients and suitable model support, run research methods for
trigger hypothesis generation. Methods originally designed for
classifiers may not transfer to object detectors without adaptation.

Do not build the core architecture around a single method such as Neural
Cleanse. Trigger inversion has assumptions and can fail on complex or
non-patch triggers. The detector's supported attack family must be
stated, and results must be benchmarked on both clean and trojaned
models.

### 6.5 Model decision policy

Keep deterministic artifact checks and probabilistic behavioural checks
separate.

-   **Deterministic hard failure:** digest mismatch against trusted
    expected artifact, invalid signature, malformed required manifest →
    QUARANTINE or a policy-defined hard stop.
-   **Strong calibrated behavioural evidence:** REVIEW or QUARANTINE
    depending on validated threshold and severity.
-   **No reference model / limited access:** report the limitation and
    narrow the conclusion.
-   **No anomaly found:** state "no tested indicator detected under the
    executed battery," not "model is safe."

------------------------------------------------------------------------

## 7. Inference provenance and output integrity

### 7.1 Canonical signed record

Each inference record binds the input, model, preprocessing, inference
configuration, runtime, output, ordering metadata and signer identity.
Use canonical JSON serialization (for example, RFC 8785 JSON
Canonicalization Scheme) before hashing/signing, and version the schema.

Illustrative record:

``` json
{
  "schema": "trusttrace.inference/1",
  "record_id": "uuid",
  "sequence": 10482,
  "nonce": "unique-random-value",
  "wall_time_utc": "2026-01-01T00:00:00Z",
  "input_sha256": "hex-digest",
  "model": {
    "weights_sha256": "hex-digest",
    "manifest_root": "hex-digest"
  },
  "preprocessing_sha256": "hex-digest",
  "inference_config_sha256": "hex-digest",
  "runtime_sha256": "hex-digest",
  "output_sha256": "hex-digest",
  "previous_record_hash": "hex-digest-or-genesis",
  "signer_key_id": "local-key-id",
  "signature": "base64-signature"
}
```

This is an illustrative schema, not yet a final JSON Schema. Actual
records should define encoding, nullability, canonicalisation and
signature payload precisely. Do not include the signature field in the
bytes that are themselves signed; define a canonical unsigned payload.

### 7.2 Cryptographic binding

Let (J_i) be the canonical unsigned record. Compute:

\[ d_i = `\operatorname{SHA256}`{=tex}(J_i) \]

Sign (d_i) or the canonical payload with Ed25519:

\[ `\sigma`{=tex}*i = `\operatorname{Sign}`{=tex}*{sk}(d_i) \]

Verify with the registered public key:

\[
`\operatorname{Verify}`{=tex}\_{pk}(d_i,`\sigma`{=tex}\_i)`\in`{=tex}{`\text{true}`{=tex},`\text{false}`{=tex}}
\]

The exact signing construction must follow the selected cryptographic
library's documented API. Store key identifiers and public-key trust
roots. Key generation, rotation, backup and revocation need an explicit
local operational procedure.

### 7.3 Hash-chained audit log

For each event (e_i), canonicalise the event and chain it to the
previous digest:

\[ H_0 = `\text{defined genesis value}`{=tex} \]

\[ H_i =
`\operatorname{SHA256}`{=tex}(H\_{i-1},\|,`\operatorname{Canon}`{=tex}(e_i))
\]

A modification or reordering changes downstream hashes. A hash chain
alone cannot detect an attacker who truncates the tail and presents only
the shortened log. Periodically sign and export a checkpoint (or anchor
it to a separately controlled medium) to detect rollback/truncation
relative to that checkpoint.

A signed Merkle checkpoint can commit to a batch of records. For leaves
(L_i=H(`\text{record}`{=tex}*i)), parent nodes are
(P=H(L*`\text{left}`{=tex}\|L\_`\text{right}`{=tex})), using a precisely
specified tree construction. Retain the root, tree parameters,
checkpoint signature, and inclusion proofs where needed.

A distributed blockchain is not required for this single-authority
offline baseline: a local chain and signed checkpoints are simpler. A
chain provides tamper evidence, not truth about the original sensor,
correctness of the model, or integrity of a compromised signer.

### 7.4 Replay, substitution and consistency checks

The verifier should check:

1.  Signature validity against an accepted key.
2.  Schema and canonical form.
3.  Input bytes match `input_sha256`.
4.  Model artifact matches the declared model digest.
5.  Preprocessing/config/runtime digests match available artifacts.
6.  Nonce uniqueness within the defined scope.
7.  Sequence monotonicity and missing records.
8.  Hash-chain continuity and checkpoint consistency.
9.  Wall-clock plausibility, treated as advisory if the local clock is
    not trusted.
10. Output bytes or canonical output object match `output_sha256`.

A nonce should be generated with a cryptographically secure random
generator and be sufficiently large (for example, 128 random bits). A
nonce helps detect duplicate/replayed identifiers but does not by itself
prevent replay; the verifier must maintain state or check
sequence/checkpoint history.

### 7.5 Verify-by-recompute

Re-run the model on the recorded input using the declared preprocessing
and inference configuration. Compare the recomputed output (y') with
recorded output (y).

For deterministic, canonical structured outputs, require exact equality
after normalisation. For numerical tensors, a comparison may use:

\[
`\operatorname{MAE}`{=tex}(y,y')=`\frac{1}{n}`{=tex}`\sum`{=tex}\_{j=1}\^{n}\|y_j-y'\_j\|
\]

\[ `\operatorname{RMSE}`{=tex}(y,y')=
`\sqrt{\frac{1}{n}\sum_{j=1}^{n}(y_j-y'_j)^2}`{=tex} \]

and optionally a maximum absolute error:

\[ E\_{`\max`{=tex}}=`\max`{=tex}\_j\|y_j-y'\_j\| \]

Set tolerances from repeatability experiments on the declared
hardware/runtime, not by arbitrary convenience. For object detection,
first define deterministic ordering and matching of predicted
boxes/classes; otherwise equivalent detections can differ in order. Use
IoU-based matching only where exact byte comparison is inappropriate,
and document the matching algorithm and thresholds.

**Interpretation:** a mismatch indicates inconsistency requiring
investigation. Possible causes include output substitution, different
runtime/configuration, nondeterminism, numerical drift, or an incorrect
record. Recompute is strongest when model, preprocessing, configuration
and runtime are trusted and available.

------------------------------------------------------------------------

## 8. Distribution-shift assessment

### 8.1 Declared reference

Every shift result is relative to a declared reference dataset and its
metadata: sensor/acquisition family, terrain/scene type, season,
illumination, preprocessing, time window and known collection
limitations. If no appropriate reference exists, the system must say so
and avoid pretending to estimate operational risk accurately.

### 8.2 Shift features

Use multiple feature families rather than a single global score:

-   Photometric statistics: brightness, contrast, saturation and colour
    histograms.
-   Frequency/noise features: frequency spectrum and compression/noise
    residuals.
-   Embedding-space statistics from a versioned local feature extractor.
-   Model-output statistics: class proportions, confidence distribution,
    detection count and box geometry.
-   Metadata strata: sensor, acquisition mode, season/time and source
    where available.

These signals can indicate a change but generally cannot identify its
cause by themselves.

### 8.3 Maximum Mean Discrepancy (MMD)

For reference samples (X={x_i}*{i=1}\^{m}) and current samples
(Y={y_j}*{j=1}\^{n}), an empirical biased MMD-squared statistic with
kernel (k) is:

\[ `\widehat{\operatorname{MMD}}`{=tex}*b\^2(X,Y)=
`\frac{1}{m^2}`{=tex}`\sum`{=tex}*{i=1}\^{m}`\sum`{=tex}*{i'=1}\^{m}k(x_i,x*{i'})
+`\frac{1}{n^2}`{=tex}`\sum`{=tex}*{j=1}\^{n}`\sum`{=tex}*{j'=1}\^{n}k(y_j,y\_{j'})
-`\frac{2}{mn}`{=tex}`\sum`{=tex}*{i=1}\^{m}`\sum`{=tex}*{j=1}\^{n}k(x_i,y_j)
\]

A common kernel is the Gaussian RBF:

\[
k(u,v)=`\exp`{=tex}`\left`{=tex}(-`\frac{\|u-v\|_2^2}{2\sigma^2}`{=tex}`\right`{=tex})
\]

Choose bandwidth (`\sigma`{=tex}) using a documented procedure, such as
a median-distance heuristic fixed from the reference/calibration data.
Use a permutation test to estimate a p-value under exchangeability.
Large MMD means the feature distributions differ; it does not establish
malicious manipulation.

For scale, a two-sample Kolmogorov--Smirnov statistic can be used on
selected one-dimensional features:

\[ D\_{KS}=`\sup`{=tex}\_x \|F_m(x)-G_n(x)\| \]

Multiple features/tests require correction or an explicitly exploratory
interpretation.

### 8.4 Drift versus suspicious manipulation

This is a probabilistic interpretation, not a guaranteed classifier.

  ----------------------------------------------------------------------------
  Evidence pattern        More consistent with broad   More consistent with a
                          operational drift            localised suspicious
                                                       pattern
  ----------------------- ---------------------------- -----------------------
  Spatial distribution    Broad or smooth changes      Repeated local
                          across many images           patch/pattern or
                                                       concentrated region

  Contributor/sensor      Shared across multiple       Concentrated in a
  spread                  sources or sensors           source, batch or class

  Temporal pattern        Gradual or seasonal change   Abrupt burst or
                                                       unexplained step

  Photometric explanation Shift substantially          Residual anomaly
                          explained by                 remains after
                          illumination/colour/sensor   accounting for measured
                          features                     changes

  Label/output coupling   Weak or broad association    Strong association with
                                                       one target class or
                                                       model response
  ----------------------------------------------------------------------------

The output labels are `probable_drift`, `suspicious_pattern`, or
`indeterminate`. The last is the default when evidence is weak,
contradictory, or too sparse. A natural distribution shift can coexist
with malicious data; the categories are not necessarily mutually
exclusive.

### 8.5 Calibration and uncertainty

Bootstrap the reference/current samples to estimate uncertainty in shift
statistics. Report effect size, p-value (when valid), confidence
interval, sample counts, reference provenance and multiple-testing
method. A small p-value does not imply a large operationally meaningful
shift; report magnitude as well as statistical significance.

------------------------------------------------------------------------

## 9. Evidence fusion, calibration and disposition policy

### 9.1 Common finding schema

Each finding should include:

``` json
{
  "finding_id": "unique-id",
  "check_id": "D3",
  "asset": {
    "type": "dataset|sample|model|inference_record|stream",
    "id": "stable-id",
    "sha256": "digest"
  },
  "attack_class": "suspected_trigger_injection",
  "severity": "low|medium|high|critical",
  "confidence": {
    "value": 0.0,
    "meaning": "calibrated probability or explicitly labelled score",
    "calibration_method": "method-and-version"
  },
  "evidence": [
    {"type": "metric|image|plot|hash|record", "ref": "evidence-id", "sha256": "digest"}
  ],
  "reason": "Human-readable explanation of the observed evidence.",
  "access_level_used": "T1",
  "access_level_needed": "T2b",
  "status": "tested|partial|unavailable|unsupported",
  "disposition": "ACCEPT|REVIEW|QUARANTINE",
  "limitations": ["Known limitation."]
}
```

The production schema should use enumerations, required fields,
versioning and validation. Confidence must state whether it is a
calibrated probability, p-value, distance, or heuristic score; these are
not interchangeable.

### 9.2 Calibrating detector scores

A raw detector score (s) should not be called a probability. Where
labelled calibration data is available, fit a calibration mapping such
as isotonic regression:

\[ `\hat `{=tex}p = g(s), `\qquad `{=tex}g
`\text{ is non-decreasing}`{=tex} \]

Evaluate calibration on held-out data. Expected Calibration Error (ECE)
can be estimated by binning predictions:

\[
`\operatorname{ECE}`{=tex}=`\sum`{=tex}\_{b=1}\^{B}`\frac{|I_b|}{N}`{=tex}
`\left`{=tex}\|`\operatorname{acc}`{=tex}(I_b)-`\operatorname{conf}`{=tex}(I_b)`\right`{=tex}\|
\]

ECE depends on binning and sample size; report the binning scheme and
include reliability plots when possible. Calibration on synthetic
attacks may not transfer to real-world attacks. Report the evaluation
domain.

### 9.3 Avoid naive probability fusion

A tempting noisy-OR fusion is:

\[ P(`\text{any event}`{=tex})=1-`\prod`{=tex}\_{i=1}\^{r}(1-p_i) \]

This formula assumes conditional independence of the evidence sources
for its simple interpretation. That assumption is often false: duplicate
detectors, embedding anomaly detectors and activation detectors may
respond to the same underlying signal. Naive noisy-OR can overstate
risk.

**Initial policy:** do not use naive noisy-OR as the default calibrated
risk estimate. Instead: 1. group strongly correlated checks into
evidence families; 2. retain hard vetoes as independent deterministic
rules; 3. use a transparent rule-based evidence table for the first
prototype; 4. if sufficient labelled validation data exists,
train/calibrate a source-risk model using contributor-level features and
held-out splits; 5. compare calibration and false-positive rates against
simple baselines; 6. expose the contributing evidence in the report.

If a probabilistic fusion model is later adopted, it must be evaluated
on clean controls and multiple poisoning rates, and it must not let
benign signals cancel a critical deterministic integrity failure.

### 9.4 Disposition policy

Disposition is policy-driven, versioned and configurable.

-   **QUARANTINE:** deterministic hard failure (e.g. trusted
    digest/signature mismatch), or validated risk above a predeclared
    threshold for a high-impact finding.
-   **REVIEW:** suspicious but inconclusive evidence, missing reference,
    uncertain source attribution, or a calibrated score in a review
    band.
-   **ACCEPT:** no policy trigger under the checks actually executed and
    declared.
-   **NOT ASSESSED / UNAVAILABLE:** used at the capability/check level
    when the required input, reference, access tier or dependency is
    absent. This is not the same as ACCEPT.

For probabilistic score (R), a simple policy may use thresholds
(t_R\<t_Q):

\[ `\text{Disposition}`{=tex}(R)=
```{=tex}
\begin{cases}
\text{ACCEPT}, & R<t_R\\
\text{REVIEW}, & t_R\le R<t_Q\\
\text{QUARANTINE}, & R\ge t_Q
\end{cases}
```
\]

Thresholds must be selected on validation data according to the cost of
false accepts and false alarms, then frozen before held-out evaluation.
Never choose thresholds after looking at the final test results.

------------------------------------------------------------------------

## 10. Offline deployment and interoperability

### 10.1 Air-gapped operation

-   Package dependencies in a pinned, hash-verified offline wheelhouse.
-   Bundle only model weights and datasets whose licenses and provenance
    have been checked.
-   Disable network use in the runtime and test with socket/DNS access
    denied.
-   Record package versions, OS/runtime information, CPU/GPU details and
    configuration digest.
-   Keep a deterministic CPU path for reproducible provenance
    demonstrations.
-   Ensure reports and evidence can be exported without contacting
    external services.

A claim of offline operation requires a test that actually denies
network access; merely avoiding explicit web APIs in source code is not
sufficient.

### 10.2 COCO and YOLO adapters

Normalise dataset representations to a canonical internal format while
preserving the original file and source schema. Validate: - category IDs
and class-name mapping; - box format (`xyxy`, `xywh`), coordinate
normalisation and image dimensions; - missing/corrupt images and
annotations; - duplicate IDs, invalid boxes, negative coordinates and
out-of-bounds boxes; - segmentation/mask fields if included; -
annotation version and source metadata.

Adapters must emit validation findings rather than silently repairing
the dataset. Any optional repair should be a separate, explicitly logged
operation.

### 10.3 ONNX, PyTorch and TorchScript

Use isolated adapters with explicit runtime/configuration digests.
Verify ONNX graph input/output signatures and supported operators before
inference. Treat all untrusted model files as potentially unsafe inputs.
Do not auto-download model weights. Unsupported operators or unavailable
dependencies should produce a clear `unavailable` result, not a pass.

------------------------------------------------------------------------

## 11. Validation plan: how we prove the solution works

This section is mandatory. The proposal should only claim capabilities
demonstrated by reproducible tests.

### 11.1 Test data and attack scenarios

Use public or synthetic data only, with licenses checked before
bundling. A staged test suite should include:

**Dataset scenarios** - clean baseline; - exact and transformed
near-duplicate flooding; - random and class-targeted label flips at
declared rates; - systematic class-pair mislabelling; - synthetic
patch/blend triggers; - OOD insertions; - contributor/batch-specific
poisoning at multiple rates; - mixed attacks and clean hard negatives.

**Model scenarios** - clean model controls; - artifact substitution and
byte modification; - controlled patch/backdoor models where a
reproducible generation method is available; - behaviourally altered or
fine-tuned variants; - detection-task attacks including object
generation, disappearance, class misclassification and localisation
changes where benchmark tooling supports them.

**Inference-record scenarios** - valid record; - modified
input/output/model/config digest; - forged or invalid signature; -
repeated nonce; - deleted/reordered record; - sequence gap; - broken
hash chain; - truncated tail with and without a trusted checkpoint; -
valid signature but altered recomputation environment; -
nondeterministic runtime and tolerance stress tests.

**Shift scenarios** - illumination and contrast changes; - haze/fog or
seasonal colour changes; - sensor/compression/noise changes; - benign
source-wide shift; - localised trigger-like pattern; - abrupt and
gradual shifts; - mixtures of drift and suspicious patterns.

Seed all synthetic scenario generation and log the seed. Separate
attack-generation code from evaluation code to reduce accidental
leakage.

### 11.2 Baselines and candidate tooling

Candidate tools and repositories for evaluation---not automatic
dependencies---include:

-   **Adversarial Robustness Toolbox (ART):** useful for adversarial ML
    and some poisoning/defence workflows; check the exact version, task
    support and license.
-   **BackdoorBench:** useful as a research benchmark for backdoor
    attacks/defences, but much of its established evaluation is
    classification-oriented; detector-specific transfer needs testing.
-   **NIST TrojAI resources:** potentially useful for reproducible
    trojaned-model evaluation, including object-detection rounds;
    confirm downloads, formats and license/terms before use.
-   **cleanlab object-detection tooling:** candidate label-error
    baseline; verify license and exact task/version support before
    adoption.
-   **Custom MMD / hash / chain verifiers:** keep the core statistical
    and cryptographic logic transparent and independently tested.

No candidate library should be described as fully compatible,
permissively licensed, or production-ready until its current repository,
license, maintenance status and exact APIs have been checked.

### 11.3 Metrics

  --------------------------------------------------------------------------
  Goal                    Metric                     Definition / use
  ----------------------- -------------------------- -----------------------
  Detection ranking       AUROC                      Area under ROC; report
                                                     per attack family, not
                                                     only aggregate

  High-security operating TPR at fixed FPR           Detection rate at a
  point                                              predeclared
                                                     false-positive rate,
                                                     e.g. 1%, if sample size
                                                     supports it

  Alert usefulness        Precision / recall         Report by attack type
                                                     and contamination rate

  Contributor analysis    Source-level               Evaluate whether
                          precision/recall and FDR   suspicious contributors
                                                     are correctly
                                                     prioritised

  Probability reliability ECE + reliability diagram  Assess calibration on
                                                     held-out scenarios

  Provenance              Tamper-detection rate;     Deterministic tamper
                          false-accept count         cases should be caught
                                                     by the relevant checks

  Shift                   Effect size, permutation   Separate magnitude from
                          p-value, detection delay   statistical
                                                     significance

  Operational cost        Runtime, peak memory,      Report CPU and GPU
                          throughput                 configurations
                                                     separately

  Usability               Analyst                    Optional but valuable:
                          agreement/time-to-triage   evaluate whether
                                                     explanations aid review
  --------------------------------------------------------------------------

A target such as "100% tamper detection" should be phrased as an
acceptance criterion for a finite, enumerated test suite, not a
universal guarantee. For cryptographic checks, test both positive and
negative cases, key mismatch, corrupted payloads, and implementation
errors.

### 11.4 Experimental protocol

1.  Define the threat scenario and baseline before running the
    experiment.
2.  Split training/proxy/calibration/test data by source or acquisition
    session where possible to avoid leakage.
3.  Keep clean controls and attack cases separate.
4.  Fix detector configurations and thresholds before held-out
    evaluation.
5.  Run multiple random seeds for stochastic attack generation.
6.  Report per-attack and per-severity results, including failure cases.
7.  Report confidence intervals where sample sizes permit.
8.  Retain command, environment lockfile, input digests, seeds, raw
    outputs and report digest.
9.  If a detector does not beat a baseline or is poorly calibrated,
    label it experimental or omit it from the default disposition
    policy.
10. Do not report results until code has actually executed and the
    artefacts are available for review.

### 11.5 Proposed go/no-go gates

-   **Gate A --- Provenance:** valid records pass; modified fields,
    invalid signatures, replay, chain breaks and known truncation cases
    are caught under the stated checkpoint assumptions.
-   **Gate B --- Dataset integrity:** duplicate, label-flip and OOD
    scenarios show measurable separation from clean controls with an
    acceptable false-positive rate.
-   **Gate C --- Source aggregation:** source-level risk adds value over
    sample-level ranking and remains calibrated under class imbalance
    and correlated detector outputs.
-   **Gate D --- Model assessment:** clean models do not routinely
    trigger high-severity alerts; tested backdoor families and access
    limitations are documented.
-   **Gate E --- Shift assessment:** known benign shifts are detected as
    distribution changes, and the drift/manipulation label is used only
    when validated evidence supports it.
-   **Gate F --- Offline:** all required flows run with network access
    denied from a clean installation.
-   **Gate G --- Reproducibility:** another team member can regenerate
    the same deterministic audit artefacts from the documented command
    and seed.

------------------------------------------------------------------------

## 12. Coverage and limitations statement

The table below is a **planned coverage statement**, not a claim of
completed implementation. It must be updated after testing.

  --------------------------------------------------------------------------------------
  Attack / condition                     Initial intended        Limitation to disclose
                                         coverage                
  -------------------------------------- ----------------------- -----------------------
  Exact duplicate flooding               Strong deterministic    Depends on available
                                         coverage                bytes and manifest
                                                                 integrity

  Near-duplicate flooding                Partial-to-strong after Perceptual/embedding
                                         calibration             thresholds create false
                                                                 positives

  Label flips / systematic mislabelling  Partial                 Proxy-model bias and
                                                                 ambiguous labels

  Patch/blend trigger in dataset         Partial                 Can miss stealthy,
                                                                 semantic or adaptive
                                                                 triggers

  OOD insertion                          Partial                 Reference-dependent;
                                                                 OOD is not proof of
                                                                 malice

  Contributor/source contamination       Conditional             Requires reliable
                                                                 source metadata or
                                                                 explicitly inferred
                                                                 groups

  Model artifact substitution            Strong only with        Digest alone does not
                                         trusted expected        establish model safety
                                         digest/registry         

  Black-box patch-backdoor behaviour     Partial                 Trigger sweep covers
                                                                 only tested hypotheses

  Complex/warping/input-aware/semantic   Unsupported unless      No universal detector
  backdoors                              separately demonstrated 

  Inference record alteration            Strong under correct    Compromised signer/host
                                         cryptographic           can defeat trust
                                         implementation and key  assumptions
                                         assumptions             

  Replay/reordering/deletion             Strong for monitored    A chain without
                                         sequence/nonce/chain;   anchored checkpoint
                                         truncation needs        cannot prove its tail
                                         external checkpoint     was not removed

  Output substitution                    Strong for              Correctness depends on
                                         digest/signature        trusted
                                         mismatch; recomputation runtime/model/config
                                         adds independent        
                                         consistency evidence    

  Natural distribution shift             Statistical detection,  Cannot infer cause from
                                         reference-dependent     distance alone

  Drift versus manipulation              Experimental            Default to
                                         interpretation          indeterminate without
                                                                 sufficient evidence

  Adaptive attacker who knows all        Unsupported             Requires ongoing
  detectors                                                      red-team testing and
                                                                 method diversity

  Hardware-level trojan / sensor         Out of scope            Requires controls
  authenticity                                                   outside this software
                                                                 system
  --------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 13. Implementation roadmap

Prioritise deterministic, demonstrable functionality before
research-heavy detection.

### Phase 1 --- Contract and foundation

-   Finalise canonical schemas and JSON Schema validation.
-   Implement asset manifests, SHA-256 utilities, evidence store and
    plugin interface.
-   Implement hash-chained audit log and standalone verifier.
-   Build CLI commands and reproducible test fixtures.

**Exit criterion:** schema tests pass; evidence and audit chain can be
regenerated and verified offline.

### Phase 2 --- Inference provenance

-   Implement canonical unsigned records and Ed25519 signatures.
-   Add digest checks, sequence/nonce checks, chain verification and
    signed checkpoints.
-   Add tampering/replay/reorder test scenarios.
-   Add verify-by-recompute for one deterministic CPU model path.

**Exit criterion:** all enumerated negative tests fail safely; all valid
records verify; limitations are reported.

### Phase 3 --- Data adapters and scenario generator

-   Add COCO and YOLO adapters and validation.
-   Build reproducible synthetic poisoning, duplicate, label-flip and
    OOD scenarios.
-   Add per-sample evidence format and example visualisations.

**Exit criterion:** seeded scenarios regenerate consistently and input
data are never silently rewritten.

### Phase 4 --- Data and source risk

-   Implement exact/perceptual duplicate detection, label-disagreement
    signals and embedding-distance baseline.
-   Add contributor/batch aggregation, uncertainty and FDR adjustment
    where assumptions hold.
-   Measure clean false-positive rates.

**Exit criterion:** publish per-attack metrics and calibration; disable
any detector that is not reliable enough for default policy.

### Phase 5 --- Distribution shift

-   Implement photometric/output statistics and MMD/permutation testing.
-   Add controlled benign-shift scenarios.
-   Test the `probable_drift` / `suspicious_pattern` / `indeterminate`
    logic.

**Exit criterion:** statistical shift detection is demonstrated; causal
language is limited to validated cases.

### Phase 6 --- Model integrity

-   Complete T0 artifact checks.
-   Add T1 probe battery and trigger-hypothesis sweep.
-   Add optional T2 checks only where time and model access support
    them.
-   Evaluate on clean controls and supported trojan benchmarks.

**Exit criterion:** results are reported by attack family and access
tier; no universal backdoor claim is made.

### Phase 7 --- Report and packaging

-   Generate JSON and static HTML reports with reasons, evidence,
    severity, access level, policy version and coverage.
-   Package dependencies for offline operation and test with network
    disabled.
-   Freeze thresholds before final held-out evaluation.
-   Prepare a demo scenario that shows both a detected integrity failure
    and a benign shift without conflating them.

**Scope-control rule:** if time is limited, cut advanced white-box
backdoor research before sacrificing provenance correctness,
reproducibility, or honest reporting.

------------------------------------------------------------------------

## 14. Risks and mitigations

  ---------------------------------------------------------------------------
  Risk                    Consequence             Mitigation
  ----------------------- ----------------------- ---------------------------
  Too many features,      Demo failures and weak  Phase gates; complete
  shallow implementation  evidence                deterministic provenance
                                                  first

  ML detectors generate   Analysts lose trust     Calibrate on clean
  false alarms                                    controls; show evidence and
                                                  uncertainty

  Correlated signals      Overstated confidence   Group signals; avoid naive
  inflate source risk                             noisy-OR; test calibration

  Reference model/data    Unsupported conclusions Explicitly downgrade
  unavailable                                     coverage; never invent a
                                                  reference

  Model backdoor methods  Missed attacks          State task limitations;
  fail on detectors                               test
                                                  object-detection-specific
                                                  scenarios

  Compromised key or host Provenance claims fail  Offline key ceremony, key
                                                  separation, signed external
                                                  checkpoints; disclose
                                                  residual risk

  GPU nondeterminism      Recompute mismatches    CPU deterministic path;
                                                  measured tolerances and
                                                  canonical output matching

  Dataset/model license   Distribution or         License audit before
  problems                deployment risk         bundling or redistribution

  Air-gap claim is not    Deployment failure      Network-denied integration
  tested                                          test

  Competitor or           Credibility loss        Use only source-verified
  institutional claims                            claims; do not infer
  are wrong                                       private DGIS practice from
                                                  public doctrine

  Synthetic-only          Limited external        Disclose it and add
  evaluation              validity                held-out public benchmarks
                                                  where feasible
  ---------------------------------------------------------------------------

------------------------------------------------------------------------

## 15. Existing work and reuse strategy

The solution should reuse mature, auditable components where they reduce
risk, while avoiding the assumption that a library is a complete
integrity-assurance product.

### 15.1 Candidate repositories and resources

-   **ART --- Adversarial Robustness Toolbox:**
    https://github.com/Trusted-AI/adversarial-robustness-toolbox\
    Candidate source of adversarial-ML and poisoning-related methods.
    Check the exact release, API support for the selected detector
    architecture, and license before integrating.
-   **BackdoorBench:** https://github.com/SCLBD/BackdoorBench\
    Candidate research benchmark for backdoor attacks and defenses.
    Established workflows are substantially classification-oriented;
    evaluate object-detection transfer instead of assuming it works.
-   **NIST TrojAI resources:**
    https://github.com/usnistgov/trojai-literature and
    https://pages.nist.gov/trojai/\
    Candidate literature and reproducible benchmark resources. Confirm
    current availability, round/task fit, download requirements and use
    terms.
-   **OpenSSF model-signing specification:**
    https://github.com/ossf/model-signing-spec\
    Useful design reference for signed model metadata and attestations;
    adapt to the project's offline trust model and avoid claiming
    conformance without implementing the specification.
-   **cleanlab object-detection documentation:**
    https://docs.cleanlab.ai/stable/tutorials/object_detection.html\
    Candidate annotation-error baseline. Verify the current license and
    exact supported workflow before adopting it.
-   **ONNX Runtime:** https://github.com/microsoft/onnxruntime\
    Candidate local inference runtime; pin version and test required
    operators offline.

These are candidate building blocks, not endorsements or proof of
suitability. Repository maintenance, license, security posture, API
details and test results must be verified at the chosen commit/release.

### 15.2 Competing-repository claims

A prior research draft named repositories described as `CVIF-SIH2026`
and `VisionTrustAI` and attributed detailed capabilities to them. Their
exact repository contents and claims were **not independently verified
in the work available for this document**. Direct retrieval/search did
not provide sufficient evidence to validate the claimed features or
benchmark numbers. This does not prove the repositories do not exist; it
means their claims must not be presented as established facts until the
URLs, code, commit history, license, tests and actual execution have
been checked.

The appropriate competitive process is: 1. verify the exact repository
and owner; 2. inspect README and source files; 3. verify license and
dependency versions; 4. run the project using its documented setup if
feasible; 5. record tests that pass/fail and reproducible metrics; 6.
compare feature-by-feature using the same threat scenarios; 7.
distinguish a README claim from a measured result.

Do not copy another team's code. Use public work to identify baselines
and gaps, then build and document an independently testable
implementation.

### 15.3 Public institutional guidance

The Ministry of Defence/DRDO announced an **ETAI (Evaluating Trustworthy
AI) Framework and Guidelines** in October 2024 according to public
reporting. This is potentially relevant governance context, but this
document does not claim to have completed a clause-by-clause mapping
against the primary framework. Before submission, obtain and read the
primary document and map its applicable criteria to the finding schema,
risk policy, human review and coverage statement. Do not claim that the
Army/DGIS currently uses a particular private implementation unless an
authoritative public source explicitly establishes it.

------------------------------------------------------------------------

## 16. Why this integrated approach is defensible

The proposal's novelty should not be described as "we invented hashes",
"we use AI to detect every backdoor", or "we use blockchain". The
defensible contribution is a practical integration of distinct assurance
layers with a reproducible evidence contract:

1.  **One finding schema across heterogeneous detectors**, including
    skipped/unavailable checks.
2.  **Hard-veto handling for deterministic integrity failures**,
    separated from statistical risk scores.
3.  **Contributor-aware evidence aggregation** with uncertainty and
    false-discovery control rather than raw flag counts alone.
4.  **Access-tiered model assessment**, so file-only, black-box and
    white-box results are not conflated.
5.  **Inference record binding plus verify-by-recompute**, combining
    cryptographic consistency with model execution consistency.
6.  **Reference-based shift characterisation** with an indeterminate
    outcome when evidence cannot distinguish drift from manipulation.
7.  **Offline auditability**, signed checkpoints, reproducible
    scenarios, and a coverage statement generated from the checks that
    actually ran.
8.  **Benchmark-gated claims**: methods that fail validation are
    labelled experimental or removed from the default policy.

The proposal's credibility depends on showing a small number of
complete, reproducible paths rather than a long list of untested
detectors.

------------------------------------------------------------------------

## 17. Submission/demo plan

A concise demo should show an end-to-end audit of synthetic/public data
and a small model:

1.  Load a dataset manifest and show hashes, annotation validation and
    duplicate clusters.
2.  Inject a known synthetic label-flip or duplicate-flood scenario and
    show the resulting evidence and source-level summary.
3.  Run a clean model and a controlled modified/backdoored model through
    the same reference battery; show where the method detects the change
    and where it cannot.
4.  Produce signed inference records for a known
    input/model/configuration.
5.  Modify an output or replay a record; show the verifier failure.
6.  Run a benign illumination/noise shift and a localised
    suspicious-pattern scenario; demonstrate the system does not
    automatically call every shift an attack.
7.  Export a report with disposition, evidence, access tier, policy
    version, reproducibility metadata and coverage limitations.
8.  Disconnect/deny network access and repeat the core workflow.

The demo should clearly label synthetic attacks and must not use
classified, operational or service-generated data.

------------------------------------------------------------------------

## 18. Final technical decisions to freeze before implementation

  -----------------------------------------------------------------------
  Decision                Recommended initial     Must be validated
                          choice                  
  ----------------------- ----------------------- -----------------------
  System name             TRUSTTRACE CV           Team/project naming

  Baseline disposition    Hard veto + transparent Thresholds and severity
                          rule-based policy       

  Source aggregation      Beta-Binomial           Calibration, dependence
                          baseline + calibrated   and source sample sizes
                          sample evidence; BH     
                          only with valid         
                          p-values                

  Risk fusion             No naive noisy-OR by    Whether learned fusion
                          default                 improves held-out
                                                  calibration

  Provenance              Canonical records,      Exact signature payload
                          SHA-256, Ed25519, hash  and key lifecycle
                          chain, signed           
                          checkpoints             

  Recompute               Deterministic CPU path  Tolerances and output
                          first                   matching

  Shift                   MMD/permutation test +  False alarms under
                          interpretable features  benign shifts

  Model integrity         T0 then T1; T2 optional Actual architecture
                                                  support and benchmark
                                                  performance

  Offline assurance       Pinned wheelhouse,      Clean-install
                          local assets,           reproduction
                          network-denied tests    

  Public benchmark use    ART, BackdoorBench,     License, versions,
                          TrojAI and label-error  exact task
                          tooling as candidates   compatibility
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 19. References and verification notes

### Primary technical references / repositories

1.  ART --- https://github.com/Trusted-AI/adversarial-robustness-toolbox
2.  BackdoorBench --- https://github.com/SCLBD/BackdoorBench
3.  NIST TrojAI literature ---
    https://github.com/usnistgov/trojai-literature
4.  NIST TrojAI portal --- https://pages.nist.gov/trojai/
5.  BadDet paper --- https://arxiv.org/abs/2205.14497
6.  OpenSSF model-signing specification ---
    https://github.com/ossf/model-signing-spec
7.  ONNX Runtime --- https://github.com/microsoft/onnxruntime
8.  RFC 8785, JSON Canonicalization Scheme ---
    https://www.rfc-editor.org/rfc/rfc8785
9.  NIST FIPS 186-5, Digital Signature Standard ---
    https://csrc.nist.gov/pubs/fips/186-5/final
10. Benjamini--Hochberg, "Controlling the False Discovery Rate" (1995)
    --- https://doi.org/10.1111/j.2517-6161.1995.tb02031.x
11. Gretton et al., "A Kernel Two-Sample Test" ---
    https://www.jmlr.org/papers/v13/gretton12a.html
12. ETAI framework public announcement/context --- verify against the
    primary MoD/DRDO document before making detailed compliance claims.

### Evidence-status legend for future versions

-   **Verified:** checked against a primary source or reproducibly
    executed in the project.
-   **Reported by source:** a paper or repository claims the result, but
    the team has not reproduced it.
-   **Proposed:** part of this architecture, not yet implemented.
-   **Hypothesis:** expected to help but must be tested.
-   **Unsupported:** known limitation or no evidence that the method
    works for the relevant attack family.

### Final status

This is the consolidated design baseline for TRUSTTRACE CV. It combines
the detailed architecture ideas in the Claude-generated report with the
clearer proposal structure of the earlier GPT draft, while correcting
for unverified repository claims and avoiding unmeasured performance
promises. It is ready to guide implementation and controlled validation;
it should not be represented as a completed or independently validated
system until the validation plan has been executed and the results
recorded.
