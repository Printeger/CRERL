# Phase 7: Unified Report Generator and Repair-Ready Inconsistency Reporting

## 1. Purpose

Phase 7 is the stage where the project moves from:

- "we have separate static, dynamic, and semantic evidence bundles"

to:

- "we can produce one ranked inconsistency report per spec/run pair that is
  ready for downstream repair."

The direct goal of this phase is to implement the first **unified report
generator** for the CRE stack.

This report layer should consume the artifacts stabilized in Phases 4-6:

- machine-readable `SpecIR`,
- static audit bundles,
- dynamic analysis bundles,
- semantic analysis bundles,
- semantic merge inputs and claim-consumer payloads,

and turn them into one evidence-ranked output that explains:

- what is wrong,
- why the issue is classified as `C-R`, `E-C`, or `E-R`,
- what evidence supports that conclusion,
- what the minimal next repair direction should be.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 7. Build the report generator`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md)
  `Layer F. Report, Repair, and Validation Layer`
- the post-semantic handoff described by the current Phase 6 outputs

---

## 2. Why Phase 7 Starts Here

Phases 4-6 already established:

- a deterministic static audit contract under `analysis/static`,
- stable runtime logs and accepted run directories,
- dynamic witness reports under `analysis/dynamic`,
- evidence-grounded semantic claims under `analysis/semantic`,
- repair-facing semantic artifacts:
  - `semantic_merge_input.json`
  - `claim_consumer.json`

What is still missing is the decision layer:

`given the available static, dynamic, and semantic evidence, what should the system tell the engineer to fix next?`

This is exactly the role of the Phase 7 report generator.

The first report generator should not try to synthesize code patches or mutate
specs directly. Its first job is narrower and more useful:

1. ingest the current multi-analyzer bundles deterministically;
2. normalize findings, witnesses, and semantic claims into one ranking space;
3. emit one machine-readable report bundle and one human-readable summary;
4. identify a small set of repair-ready claims for Phase 8.

That gives Phase 8 a clean handoff substrate instead of forcing repair logic to
scrape three analyzer namespaces independently.

---

## 3. Scope of Phase 7

Phase 7 should implement **report generation only**.

In scope:

- merging static, dynamic, and semantic analyzer outputs
- severity ranking across heterogeneous evidence types
- root-cause ordering and claim selection
- repair-ready claim handoff
- machine-readable and human-readable report bundle generation

Out of scope:

- generating actual repair patches
- mutating specs or configs
- retraining policies
- automatic acceptance/rejection of repaired specs

Those belong to Phases 8-9.

---

## 4. Inputs the Report Generator Must Read

The report generator should treat the following as the authoritative Phase 7
inputs for `v0`.

### 4.1 Static Audit Bundle

Under:

`analysis/static/<bundle_name>/`

Minimum required artifacts:

- `static_report.json`
- `summary.json`
- `manifest.json`

Optional but expected:

- `namespace_manifest.json`

### 4.2 Dynamic Analysis Bundle

Under:

`analysis/dynamic/<bundle_name>/`

Minimum required artifacts:

- `dynamic_report.json`
- `dynamic_evidence.json`
- `semantic_inputs.json`
- `summary.json`
- `manifest.json`

### 4.3 Semantic Analysis Bundle

Under:

`analysis/semantic/<bundle_name>/`

Minimum required artifacts:

- `semantic_report.json`
- `semantic_claims.json`
- `semantic_input.json`
- `semantic_merge_input.json`
- `claim_consumer.json`
- `summary.json`
- `manifest.json`

### 4.4 Report Namespace Contract

The report generator must also consume the namespaced analysis contract:

- `analysis/report_namespace_contract.json`

This is the canonical source of:

- expected analyzer namespaces
- required artifacts per namespace
- bundle compatibility rules

---

## 5. Required Report Outputs

Phase 7 should introduce a new namespace:

`analysis/report/<bundle_name>/`

The first machine-readable bundle should contain at least:

- `report.json`
- `ranked_findings.json`
- `repair_handoff.json`
- `summary.json`
- `manifest.json`

The first human-readable bundle should contain at least:

- `report_summary.md`

### 5.1 `report.json`

This should be the canonical unified report and contain:

- report metadata
- input bundle references
- normalized finding set
- ranked inconsistency records
- witness summary
- semantic-claim summary
- root-cause ordering
- minimal next repair directions

### 5.2 `ranked_findings.json`

This should contain the ranking substrate used by downstream consumers:

- `finding_id`
- `source_namespace`
- `claim_type`
- `severity`
- `confidence`
- `support_status`
- `evidence_refs`
- `rank_score`

### 5.3 `repair_handoff.json`

This should not yet synthesize a repair.

It should provide Phase 8 with:

- selected repair-ready claims
- impacted spec components:
  - `C`
  - `R`
  - `E`
- suggested repair direction:
  - `reward`
  - `environment`
  - `constraint`
  - `mixed`
- required evidence references

### 5.4 `report_summary.md`

This should be a concise engineer-facing summary that answers:

- what is wrong
- why the system thinks so
- what evidence is strongest
- what should be checked or repaired first

---

## 6. First Ranking and Merge Rules

Phase 7 does not need the final ranking theory.

It needs stable engineering rules that are:

- deterministic,
- auditable,
- easy to trace back to machine evidence.

### 6.1 Source Priority

Phase 7 should preserve analyzer provenance.

Recommended initial priority:

1. static blockers / hard conflicts
2. dynamic witness-backed failures
3. semantic supported claims
4. semantic weak claims

Rejected semantic claims should be retained for traceability but should not
drive top-level report conclusions.

### 6.2 Severity Normalization

The merge layer should normalize severities into one ordered space:

- `critical`
- `high`
- `medium`
- `warning`
- `info`

### 6.3 Confidence and Support

Each unified record should expose:

- a normalized confidence score
- whether it is:
  - `machine_direct`
  - `machine_derived`
  - `semantic_supported`
  - `semantic_weak`

### 6.4 Repair-Ready Claim Selection

A claim should only become repair-ready when:

- it has stable evidence references,
- it has a supported or machine-backed status,
- it identifies at least one impacted spec component,
- it carries a minimal next-repair direction.

---

## 7. File-Level Implementation Plan

Phase 7 should start with these concrete files.

### 7.1 New Analyzer Files

Create:

- `isaac-training/training/analyzers/report_generator.py`
- `isaac-training/training/analyzers/report_merge.py`

Responsibilities:

- load static/dynamic/semantic bundles
- normalize findings into one shared report substrate
- compute ranking and repair-handoff records
- emit the report namespace bundle

### 7.2 Report Contract Updates

Extend:

- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

Responsibilities:

- define the `analysis/report` namespace
- define required artifacts
- define compatibility with static/dynamic/semantic bundles

### 7.3 CLI Entry Point

Create:

- `isaac-training/training/scripts/run_report_audit.py`

Responsibilities:

- accept bundle paths or report roots
- assemble a Phase 7 report bundle
- write outputs under `analysis/report/<bundle_name>/`

### 7.4 Tests

Create:

- `isaac-training/training/unit_test/test_env/test_report_generator.py`

The first tests should cover:

- synthetic merge of one static + one dynamic + one semantic bundle
- ranking order sanity
- repair-handoff generation
- report namespace bundle writing

---

## 8. Recommended Implementation Order

1. Freeze the `analysis/report` namespace contract.
2. Implement a minimal bundle loader over static/dynamic/semantic outputs.
3. Implement normalized finding records and ranking.
4. Emit `report.json` and `ranked_findings.json`.
5. Add `repair_handoff.json`.
6. Add `report_summary.md`.
7. Add CLI and tests.

---

## 9. Validation Plan

Phase 7 should be validated in two layers.

### 9.1 Synthetic Validation

Use small synthetic bundle fixtures to ensure:

- merge logic is deterministic
- ranking is stable
- repair-handoff records are generated only for supported evidence

### 9.2 Real Artifact Smoke Test

Run the report generator over the current real bundles produced by:

- Phase 4 static audit
- Phase 5 dynamic analysis
- Phase 6 semantic analysis

and ensure:

- the report bundle is written successfully
- all input bundle refs are preserved
- the top-ranked findings are traceable back to machine evidence

---

## 10. Exit Criteria

Phase 7 is complete when:

- the system can produce one unified report per spec/run bundle set
- the report explains:
  - what is wrong
  - why it is classified as `C-R`, `E-C`, or `E-R`
  - what evidence supports that classification
  - what the minimal next repair direction is
- the result is available in both:
  - machine-readable form
  - human-readable form
- Phase 8 can consume the repair handoff without scraping analyzer-specific
  internals
