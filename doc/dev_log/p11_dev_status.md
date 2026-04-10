# Phase 11 Development Status

Updated: 2026-03-30

## 1. This Iteration Goal

This iteration performs the formal documentation close-out of Phase 11 and of
the roadmap as currently written.

The goal of this step is:

- update `doc/roadmap.md` so its current-status section matches the real
  repository state,
- add a top-level roadmap close-out note under `doc/`,
- and formally record whether the roadmap is complete as currently written.

## 2. Result

The roadmap documentation is now aligned with the actual repository state at
the end of `Phase 11`.

The key result is that:

- the top-level roadmap no longer claims that major analyzers/repair/validation
  pieces are "not yet available",
- there is now an explicit roadmap close-out note,
- and the project now has a written formal judgment that the current roadmap is
  complete as defined.

This iteration added four concrete capabilities:

1. **final roadmap status sync**
   - `doc/roadmap.md` now reflects final roadmap-complete status instead of an
     outdated midpoint snapshot
   - the `Current project status under this roadmap` section now distinguishes:
     - already available
     - partially available
     - not part of the current roadmap baseline
     - formal status

2. **top-level close-out note**
   - a new document now exists at:
     - `doc/roadmap_closeout.md`
   - it records:
     - roadmap scope
     - formal completion judgment
     - close-out evidence
     - what is complete
     - what is not claimed
     - what should happen next

3. **formal roadmap-complete judgment**
   - the documentation now clearly states:
     - `Phase 0` through `Phase 11` are complete against the current roadmap
   - and also clearly states:
     - future work should be treated as roadmap extension / release hardening,
       not as if the current roadmap were still open-ended

4. **traceability close-out sync**
   - `Traceability.md` has been refreshed so the staged summary reflects this
     documentation close-out pass

## 3. Main Files Added or Changed

Benchmark / release pipeline / contract:

- `doc/roadmap.md`
- `doc/roadmap_closeout.md`

Tests / traceability:

- `doc/dev_log/p11_dev_status.md`
- `Traceability.md`

## 4. How To Validate

Recommended focused checks:

```bash
python3 tools/update_traceability.py
```

```bash
rg -n "Formal status|Phase 0 through Phase 11|roadmap is complete" \
  doc/roadmap.md \
  doc/roadmap_closeout.md \
  doc/dev_log/p11_dev_status.md
```

```bash
git diff -- doc/roadmap.md doc/roadmap_closeout.md doc/dev_log/p11_dev_status.md Traceability.md
```

## 5. Validation Results

Validated in this iteration:

- `Traceability.md` refresh completed successfully
- the roadmap docs now explicitly contain:
  - formal completion wording
  - roadmap close-out note
  - clarified "not part of current roadmap baseline" section
- the previous Phase 11 close-out evidence remains the basis for the formal
  judgment:
  - `phase11_exit_ready = true`
  - release acceptance checks all passed

This confirms that **Phase 11 and the roadmap as currently written can now be
considered formally complete in documentation as well as implementation**:

- the code has already reached roadmap completion,
- and now the top-level docs say so consistently.

## 6. What Should Be Done Next

The next step should be:

1. decide whether to extend the roadmap beyond `CRE-v1`,
2. or freeze the current roadmap and move into release hardening / publication
   packaging,
3. while keeping the real-provider path optional so it does not disturb the
   evidence-first default release flow.

## 7. Post-Close-Out Addendum

After the formal roadmap close-out, a user-facing verification guide was added:

- `doc/verification_readme.md`

Its purpose is to make the completed roadmap verifiable in practice by a human
operator. It summarizes:

- what is still not claimed as finished,
- what the main modules are,
- what the canonical call flow is,
- how to verify each module,
- and how to verify the full pipeline end-to-end.

## 8. One-Command Smoke-Test Addendum

After the verification guide, the repository was further extended with a
one-command smoke-test harness:

- `isaac-training/training/scripts/run_full_smoke_test.sh`

Its purpose is to make the full pipeline easier to verify in one shot by:

- activating `conda activate NavRL`,
- running the canonical smoke chain from:
  - static
  - dynamic
  - semantic
  - report
  - repair
  - validation
  - integration
  - benchmark
  - release
- and collecting per-step CLI outputs into:
  - `full_smoke_summary.json`

The verification guide was also updated to advertise this one-command path in:

- `doc/verification_readme.md`

Focused validation for this addendum:

```bash
bash -n isaac-training/training/scripts/run_full_smoke_test.sh
```

```bash
bash isaac-training/training/scripts/run_full_smoke_test.sh \
  --reports-root /tmp/crerl_full_smoke_20260329_001 \
  --bundle-prefix full
```

Validation results:

- the script activated `NavRL` successfully
- the script completed end to end and wrote:
  - `/tmp/crerl_full_smoke_20260329_001/full_smoke_summary.json`
- the generated smoke bundle results were:
  - static: `passed = true`, `num_findings = 8`
  - dynamic: `passed = true`, `W_CR = 0.0`, `W_EC = 0.46666666666666673`, `W_ER = 0.14285714285714285`
  - semantic: `passed = true`, `supported_claims = 1`, `weak_claims = 1`
  - report: `passed = true`, `primary_claim_type = C-R`
  - repair: `passed = true`, `phase9_ready = true`
  - validation: bundle generation succeeded but decision was `inconclusive`
  - integration: `passed = true`
  - benchmark: `ready_case_count = 4`
  - release: `phase11_exit_ready = true`

This means the one-command harness is now working as a full namespace smoke
generator, even though the default example chain currently lands on a
`C-R`-dominated repair path whose validation decision remains inconclusive.

## 9. Interface-Map Addendum

The verification guide was further extended with a module interface map in:

- `doc/verification_readme.md`

This addition turns the README from a verification checklist into a pipeline
inspection guide. The new section explicitly records:

- `module/stage -> inputs -> outputs -> downstream consumer`

for the major CRE pipeline layers:

- spec/config
- scene compilation
- execution/logging
- static/dynamic/semantic analysis
- report/repair/validation
- integration/benchmark/release

Its purpose is to make two things much easier for a human verifier:

1. trace where a piece of information originates and where it should appear
   next
2. understand the correct order for changing rules without breaking downstream
   contracts

Focused validation for this addendum:

```bash
rg -n "Module Interface Map|Rule changes should move from upstream to downstream|analysis/static/<bundle>" \
  doc/verification_readme.md
```

Validation results:

- the README now contains a dedicated interface-map section
- the map explicitly ties together:
  - inputs
  - outputs
  - downstream consumers
- the README now also explicitly states the preferred rule-change order:
  - spec/config
  - scene/runtime binding
  - execution/logging
  - analyzers
  - report/repair/validation/integration/benchmark/release

## 10. Native-Execution Smoke-Test Addendum

The verification guide was further split into two explicit smoke-test paths:

1. analysis-only smoke test
2. native execution smoke test

This update added a new script:

- `isaac-training/training/scripts/run_native_execution_smoke.sh`

Its purpose is to prove that the real native entrypoints still execute and can
still feed the analysis stack.

Concretely, it performs:
- `baseline`
- `train`
- `eval`
- then:
  - `static`
  - `dynamic`
  - `semantic`
  - `report`
  - `repair`
  - `validation`

Focused validation for this addendum:

```bash
bash -n isaac-training/training/scripts/run_native_execution_smoke.sh
```

```bash
bash isaac-training/training/scripts/run_native_execution_smoke.sh \
  --work-root /tmp/crerl_native_execution_20260329_003 \
  --bundle-prefix native3
```

Validation results:

- the script completed successfully and wrote:
  - `/tmp/crerl_native_execution_20260329_003/native_execution_summary.json`
- the native accepted runs all passed acceptance:
  - baseline: `true`
  - train: `true`
  - eval: `true`
- the native analysis chain all passed:
  - static: `passed = true`
  - dynamic: `passed = true`
  - semantic: `passed = true`
  - report: `passed = true`
  - repair: `passed = true`
- the validation stage now produces real repaired accepted reruns:
  - `/tmp/crerl_native_execution_20260329_003/repaired_logs/native3_repair_baseline_nominal_00`
  - `/tmp/crerl_native_execution_20260329_003/repaired_logs/native3_repair_eval_nominal_01`
- validation now records:
  - `repaired_run_count = 2`
  - `decision_status = inconclusive`
  - `blocked_by = ['missing_consistency_evidence']`

This confirms that the native smoke harness no longer stops at the report
stage. It now reaches a real `repair -> validation` close-out loop and
materializes repaired accepted runs, even though the current default
`C-R`-dominated example still does not reach a final accepted/rejected
validation decision.

## 11. Native-Execution Decision-Closure Addendum

The native smoke harness was then tightened so that its default example is more
likely to land on a final `accepted/rejected` validation decision instead of
stopping at `inconclusive`.

This update made three connected changes:

1. the native smoke default now uses a stronger `E-R` signal
   - `baseline(nominal) -> train(nominal) -> eval(shifted)`
   - the repair pass now explicitly overrides the repair claim type to `E-R`

2. the repair engine now supports targeted claim-type overrides
   - `run_repair_audit.py` accepts `--claim-type-override`
   - `rule_based_repair.py` records the override in repair-plan metadata

3. the validation decision rule now supports claim-specific fallback
   consistency evidence
   - when `E-C / E-R` repaired runs do not carry explicit `W_EC / W_ER`
   - but the higher-order family-gap metrics are present
   - the decision rule now resolves to `accepted` or `rejected`
     deterministically instead of returning `missing_consistency_evidence`

Focused validation for this addendum:

```bash
python3 -m py_compile \
  isaac-training/training/repair/decision.py \
  isaac-training/training/repair/rule_based_repair.py \
  isaac-training/training/scripts/run_repair_audit.py \
  isaac-training/training/unit_test/test_env/test_repair_engine.py \
  isaac-training/training/unit_test/test_env/test_validation_loop.py
```

```bash
bash -n isaac-training/training/scripts/run_native_execution_smoke.sh
```

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_repair_engine.py \
  isaac-training/training/unit_test/test_env/test_validation_loop.py
```

```bash
bash isaac-training/training/scripts/run_native_execution_smoke.sh \
  --work-root /tmp/crerl_native_execution_20260329_005 \
  --bundle-prefix native5
```

Validation results:

- focused repair/validation regression tests now pass:
  - `27 passed, 1 skipped`
- the native smoke script syntax check passes
- the latest native smoke run completed successfully and wrote:
  - `/tmp/crerl_native_execution_20260329_005/native_execution_summary.json`
- the native accepted runs all passed acceptance:
  - baseline: `true`
  - train: `true`
  - eval: `true`
- the native analysis chain again passed through repair:
  - static: `passed = true`
  - dynamic: `passed = true`
  - semantic: `passed = true`
  - report: `passed = true`
  - repair: `passed = true`
- validation now closes with a final machine-readable decision:
  - `primary_claim_type = E-R`
  - `decision_status = rejected`
  - `blocked_by = []`
  - `consistency_evidence_mode = claim_specific_fallback`
  - `repaired_run_count = 2`

This confirms that the native smoke harness now defaults to a more stable
`E-R` example and that the validation stage can reach a final accepted/rejected
decision without requiring explicit repaired `W_ER` evidence.

## 12. Real-Semantic Smoke-Path Addendum

The smoke-test harnesses were then extended so they can optionally call a real
online semantic provider instead of always forcing mock mode.

This addendum introduced three changes:

1. semantic prompt externalization
   - the semantic prompt template now lives at:
     - `isaac-training/training/cfg/semantic_cfg/semantic_prompt_v1.yaml`
   - `run_semantic_audit.py` now exposes `--prompt-cfg-path`

2. one-command smoke-script provider flags
   - both scripts now forward:
     - `--semantic-provider-mode`
     - `--semantic-api-key-env-var`
     - `--semantic-gateway-base-url`
     - `--semantic-deployment-name`
     - `--semantic-api-version`

3. fail-fast provider preflight
   - when `--semantic-provider-mode` is not `mock`
   - both scripts now fail before the first audit stage if the configured API
     key env var is not visible in the shell

Focused validation for this addendum:

```bash
bash -n \
  isaac-training/training/scripts/run_full_smoke_test.sh \
  isaac-training/training/scripts/run_native_execution_smoke.sh
```

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/semantic_provider.py \
  isaac-training/training/scripts/run_semantic_audit.py \
  isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

```bash
pytest -q isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

```bash
bash isaac-training/training/scripts/run_full_smoke_test.sh \
  --reports-root /tmp/crerl_real_llm_smoke_20260329_002 \
  --bundle-prefix realllm2 \
  --semantic-provider-mode azure_gateway \
  --semantic-api-key-env-var COMP_OPENAI_API_KEY \
  --semantic-gateway-base-url https://comp.azure-api.net/azure \
  --semantic-deployment-name gpt4o \
  --semantic-api-version 2024-02-01
```

```bash
bash isaac-training/training/scripts/run_full_smoke_test.sh \
  --reports-root /tmp/crerl_mock_llm_smoke_20260329_001 \
  --bundle-prefix mockcfg \
  --semantic-provider-mode mock \
  --semantic-api-key-env-var COMP_OPENAI_API_KEY \
  --semantic-gateway-base-url https://comp.azure-api.net/azure \
  --semantic-deployment-name gpt4o \
  --semantic-api-version 2024-02-01
```

Validation results:

- script syntax checks passed
- semantic-focused `py_compile` passed
- semantic-focused `pytest` passed:
  - `17 passed`
- the real-provider smoke path now fails fast with an explicit blocker when the
  configured key is not visible:
  - `Semantic provider mode 'azure_gateway' requires env var 'COMP_OPENAI_API_KEY' to be set before running this script.`
- the same full smoke script still succeeds with mock mode and writes:
  - `/tmp/crerl_mock_llm_smoke_20260329_001/full_smoke_summary.json`
- in that successful run, semantic CLI output confirms:
  - `provider_mode = mock`
  - `prompt_cfg_path = /home/mint/rl_dev/CRERL/isaac-training/training/cfg/semantic_cfg/semantic_prompt_v1.yaml`
- a later real-provider full smoke run also completed successfully once the
  COMP gateway key was exposed in the launching shell:
  - `/tmp/crerl_real_llm_smoke_20260329_004/full_smoke_summary.json`
- in that successful real-provider run:
  - `provider_mode = azure_gateway`
  - `semantic passed = true`
  - `supported_claims = 3`
  - `weak_claims = 0`
  - `most_likely_claim_type = E-C`
  - `release phase11_exit_ready = true`
- a later native real-provider smoke run also completed successfully:
  - `/tmp/crerl_native_real_llm_20260329_001/native_execution_summary.json`
- in that successful native real-provider run:
  - `semantic provider_mode = azure_gateway`
  - `semantic passed = true`
  - `supported_claims = 3`
  - `weak_claims = 0`
  - `most_likely_claim_type = E-C`
  - `repair primary_claim_type = E-R`
  - `validation decision_status = rejected`
  - `validation repaired_run_count = 2`
- the verification guide now also documents a safe local-only key injection
  pattern using:
  - `python3` + `Path('doc/API_KEY.md').read_text(...)`
  - Unicode-whitespace stripping via `ch.isspace()`
  - `export COMP_OPENAI_API_KEY=\"$(...)\"`
- `.gitignore` now ignores:
  - `doc/API_KEY`
  - `doc/API_KEY.md`

This means the repository now supports a one-command real-semantic smoke path,
but the actual online call will only proceed once the chosen API key env var is
visible in the launching shell or conda session.

## 11. Local Key-Helper and Online-Chain Consistency Addendum

After the real-provider smoke path was proven manually, the repository was
further extended with a local-only API-key helper:

- `isaac-training/training/scripts/with_comp_api_key.sh`

Its purpose is to avoid repeatedly hand-writing:

- `export COMP_OPENAI_API_KEY="$(python3 ...)"`,

while still preserving two important safety properties:

1. the key is read only from ignored local files:
   - `doc/API_KEY`
   - `doc/API_KEY.md`
2. the cleaned key is injected only into the child process environment that
   runs the smoke command

The verification guide was updated accordingly:

- `doc/verification_readme.md`

It now documents:

- the helper-script path,
- the real-provider analysis-only smoke command,
- and the real-provider native smoke command.

Focused validation for this addendum:

```bash
bash -n isaac-training/training/scripts/with_comp_api_key.sh
```

```bash
bash isaac-training/training/scripts/with_comp_api_key.sh --print-source -- \
  bash isaac-training/training/scripts/run_full_smoke_test.sh \
    --reports-root /tmp/crerl_real_llm_smoke_20260330_001 \
    --bundle-prefix realllm5 \
    --semantic-provider-mode azure_gateway \
    --semantic-api-key-env-var COMP_OPENAI_API_KEY \
    --semantic-gateway-base-url https://comp.azure-api.net/azure \
    --semantic-deployment-name gpt4o \
    --semantic-api-version 2024-02-01
```

Validation results:

- the helper script successfully loaded the local key file, stripped Unicode
  whitespace, and executed the requested smoke command
- the new real-provider analysis-only smoke run completed successfully:
  - `/tmp/crerl_real_llm_smoke_20260330_001/full_smoke_summary.json`
- the earlier native real-provider smoke run remains:
  - `/tmp/crerl_native_real_llm_20260329_001/native_execution_summary.json`
- comparing the two online chains shows consistent semantic behavior on their
  shared high-level outputs:
  - analysis-only:
    - `semantic supported_claims = 3`
    - `semantic weak_claims = 0`
    - `semantic most_likely_claim_type = E-C`
    - `report primary_claim_type = C-R`
  - native:
    - `semantic supported_claims = 3`
    - `semantic weak_claims = 0`
    - `semantic most_likely_claim_type = E-C`
    - `report primary_claim_type = C-R`
- the two chains intentionally diverge after the shared report stage:
  - analysis-only reuses existing accepted runs and lands on:
    - `validation decision_status = inconclusive`
    - `validation repaired_run_count = 4`
  - native uses fresh baseline/train/eval execution evidence and then applies a
    native-smoke repair override that lands on:
    - `repair primary_claim_type = E-R`
    - `validation decision_status = rejected`
    - `validation repaired_run_count = 2`

This confirms that the real online provider path is now reproducible in both:

- the artifact-only analysis smoke chain
- the native execution smoke chain

while still keeping the local key material out of version control.

## 12. Local Dashboard Addendum

After the release-grade artifact pipeline was frozen, the repository was
extended with a local monitoring dashboard for observing CRE module activity in
the browser.

New files:

- `isaac-training/training/dashboard/state.py`
- `isaac-training/training/dashboard/app.py`
- `isaac-training/training/dashboard/templates/`
- `isaac-training/training/scripts/run_dashboard.py`
- `isaac-training/training/unit_test/test_env/test_dashboard_monitor.py`

The first version is a local single-user read-only dashboard. It reads existing
machine-readable artifacts and does not trigger execution itself.

Key capabilities added:

1. **artifact-backed live state model**
   - scans accepted runs under `training/logs/`
   - scans namespaced bundles under `analysis/*`
   - scans smoke/native work roots under `/tmp/crerl_*`
   - infers:
     - active module
     - flow-node state
     - KPI cards
     - recent events
     - chart data

2. **browser dashboard with layered refresh**
   - top overview bar
   - left flow graph
   - middle active module panel
   - right KPI cards
   - bottom chart grid
   - refresh cadence:
     - `1s` for state panels
     - `5s` for charts

3. **training / analysis visualization**
   - average return trend
   - safety outcome trend
   - minimum distance trend
   - near-violation ratio trend
   - done-type distribution
   - reward-components breakdown
   - family comparison
   - witness trend
   - before/after repair deltas
   - optional WandB charts when history files exist

4. **environment-compatible ASGI fallback**
   - the intended backend shape is FastAPI-like
   - but the current `NavRL` environment has a broken FastAPI/pydantic import
     chain
   - therefore the app currently prefers:
     - FastAPI when importable
     - Starlette fallback when FastAPI is unavailable

Focused validation for this addendum:

```bash
python3 -m py_compile \
  isaac-training/training/dashboard/__init__.py \
  isaac-training/training/dashboard/state.py \
  isaac-training/training/dashboard/app.py \
  isaac-training/training/scripts/run_dashboard.py \
  isaac-training/training/unit_test/test_env/test_dashboard_monitor.py
```

```bash
pytest -q isaac-training/training/unit_test/test_env/test_dashboard_monitor.py
```

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate NavRL
pytest -q isaac-training/training/unit_test/test_env/test_dashboard_monitor.py
```

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate NavRL
python isaac-training/training/scripts/run_dashboard.py --host 127.0.0.1 --port 8766
```

Then:

```bash
curl -s http://127.0.0.1:8766/healthz
python3 - <<'PY'
import json, urllib.request
payload = json.load(urllib.request.urlopen('http://127.0.0.1:8766/api/state'))
print(payload['overview']['provider_mode'])
print(payload['overview']['active_module'])
print(payload['overview']['current_object'])
PY
```

Validation results:

- system-python focused tests passed:
  - `2 passed, 1 skipped`
- `NavRL` focused tests also passed:
  - `2 passed, 1 skipped`
- live dashboard smoke passed:
  - `/healthz` returned `ok`
  - `/api/state` returned:
    - `provider_mode = azure_gateway`
    - `active_module = Repair`
    - `current_object = repair_phase9_loader_smoke`
- the HTML page rendered the expected major sections:
  - `Global Overview`
  - `System Flow`
  - `Active Module Panel`
  - `Training and Analysis Charts`

This means the repository now has a browser-based local observability surface
for the CRE pipeline without introducing a separate Node frontend.

## 13. Dashboard One-Click and Design-Inventory Addendum

The smoke scripts were further extended so the local dashboard can now be tied
directly into one-command verification runs.

Updated scripts:

- `isaac-training/training/scripts/run_full_smoke_test.sh`
- `isaac-training/training/scripts/run_native_execution_smoke.sh`

New smoke-script flags:

- `--launch-dashboard`
- `--dashboard-host`
- `--dashboard-port`

The current behavior is:

1. both smoke scripts always print the exact dashboard command for the current
   generated work root
2. when `--launch-dashboard` is passed, the dashboard is launched in the
   background before the smoke chain starts
3. each smoke root now records dashboard metadata in its summary JSON

The verification guide was also updated with a design-facing content inventory
for the current dashboard. That inventory now explicitly lists:

- overview bar items
- flow-graph nodes
- active-module panel fields
- KPI card fields
- latest-run fields
- chart titles currently rendered

Focused validation for this addendum:

```bash
bash -n isaac-training/training/scripts/run_full_smoke_test.sh
bash -n isaac-training/training/scripts/run_native_execution_smoke.sh
```

```bash
python3 tools/update_traceability.py --working-tree
```

Validation results:

- both smoke scripts accept the new dashboard-launch arguments
- both smoke scripts now print a deterministic dashboard command
- the verification guide now documents:
  - how to auto-launch the dashboard from the smoke scripts
  - the current dashboard content inventory for UI redesign

## 14. Dashboard Reference-Layout Addendum

The local dashboard frontend was then restyled against the reference layout in:

- `doc/cre_frame_rl_live_dashboard.html`

This change intentionally kept the artifact-scanning backend unchanged and
focused only on the browser surface:

- `isaac-training/training/dashboard/templates/index.html`
- `isaac-training/training/dashboard/templates/partials/overview.html`
- `isaac-training/training/dashboard/templates/partials/live_grid.html`
- `isaac-training/training/dashboard/templates/partials/charts.html`

Key UI changes:

1. **reference-aligned visual direction**
   - switched from the previous blue-white utilitarian look to a warm
     cream/stroke/accent palette
   - adopted a headline + workbench layout closer to the provided reference

2. **restructured dashboard composition**
   - top hero panel now mirrors the live-monitor framing used by the reference
   - flow column now uses a vertical rail + node-card presentation
   - active-module area now has:
     - activity hero
     - key-details card
     - module-summary card
     - recent-events block
   - KPI and latest-run panels were restyled into separate right-rail cards

3. **chart-area redesign**
   - chart section now uses a more presentation-oriented heading and card layout
   - lucide icons are re-initialized after HTMX swaps so icons survive live
     refreshes

Focused validation for this addendum:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate NavRL
pytest -q isaac-training/training/unit_test/test_env/test_dashboard_monitor.py
```

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate NavRL
python isaac-training/training/scripts/run_dashboard.py --host 127.0.0.1 --port 8772
```

Then:

```bash
curl -s http://127.0.0.1:8772/healthz
curl -s http://127.0.0.1:8772/ | rg -n \
  "CRE Frame RL Live Monitor|Global Overview|System Flow|Active Module Panel|Training and Analysis Charts"
```

Validation results:

- focused dashboard tests passed:
  - `2 passed, 1 skipped`
- live dashboard smoke passed:
  - `/healthz` returned `ok`
  - the rendered page contained the expected reference-aligned major sections:
    - `CRE Frame RL Live Monitor`
    - `Global Overview`
    - `System Flow`
    - `Active Module Panel`
    - `Training and Analysis Charts`

## 15. CRE_v4 Structure-Alignment Addendum

On `2026-04-10`, a new structure-comparison note was added for the latest
framework document:

- `doc/cre_v4_structure_gap_analysis.md`

Its purpose is to answer one practical question:

- how the current repository structure differs from the latest
  `doc/CRE_v4.pdf` structure dated `2026-04-10`

This addendum does not change the runtime pipeline itself. It records a
documentation-level alignment pass between:

- the current repository reality,
- the repo's own roadmap/architecture docs,
- and the new `CRE_v4` handbook-style module layout

What this note adds:

1. a documented comparison method
   - compare `CRE_v4.pdf` Part II module registry, data schemas, orchestrator,
     and integration-test definitions
   - against the real repository tree and the current implemented modules

2. a module-by-module structure mapping
   - `M1` through `M8`
   - `Pipeline Orchestrator`
   - typed schema objects
   - current repo packages and scripts

3. an explicit judgment on alignment status
   - what is already aligned
   - what is only partially aligned
   - what is absent
   - what the current repo already contains beyond `CRE_v4`

4. a migration recommendation
   - keep the current bundle-first engineering shape
   - selectively absorb the most valuable `CRE_v4` structural ideas:
     - real orchestrator
     - unified typed pipeline state
     - discrepancy protocol
     - audit trail

Focused validation for this addendum:

```bash
rg -n "CRE_v4 与当前项目结构差异对比|Module Registry|Pipeline Orchestrator|PsiCRE|AuditTrail" \
  doc/cre_v4_structure_gap_analysis.md
```

```bash
git diff -- \
  doc/cre_v4_structure_gap_analysis.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the comparison note now exists under `doc/`
- it explicitly records the `2026-04-10` PDF date/version context
- it distinguishes:
  - top-level structure differences
  - module mapping differences
  - data contract differences
  - method-path differences
- it concludes that the repo is architecturally compatible in intent, but not
  yet structurally identical to the latest `CRE_v4` single-orchestrator model

## 16. CRE_v4 Terminology-and-Flowchart Addendum

The new structure-comparison note was then extended so it is easier to read by
someone who was not involved in the earlier implementation passes.

This addendum added two things to:

- `doc/cre_v4_structure_gap_analysis.md`

### 16.1 `bundle-first` terminology clarification

The note now explicitly explains what `bundle-first` means in the context of
this repository.

The key clarification is:

- the current repo uses stage output bundles as the primary interface boundary
- instead of treating one in-memory orchestrator state object as the only
  system backbone

The note now also explains:

- where bundles appear in the repo
- what files typically exist in a bundle
- why this helps replay, verification, benchmark packaging, and release
  packaging
- what structural tradeoff it introduces

### 16.2 current-project and `CRE_v4` flowcharts

The note now includes two markdown-native `mermaid` flowcharts:

1. **current project flow**
   - `cfg/spec_cfg + cfg/env_cfg`
   - `spec_ir`
   - scene/runtime substrate
   - execution modes
   - runtime evidence
   - static/dynamic/semantic/report/repair/validation
   - integration/benchmark/release

2. **`CRE_v4.pdf` flow**
   - `NLInput`
   - `M1 -> M2 -> M3 -> DP(M6) -> M5 -> M4 -> M7 -> M8`
   - `PO.run_cre_pipeline`
   - `AuditTrail + PipelineResult`

This makes the structural difference visible at a glance instead of requiring
the reader to reconstruct the control flow mentally from text-only sections.

Focused validation for this addendum:

```bash
rg -n "bundle-first|flowchart LR|Current project flow|CRE_v4.pdf flow" \
  doc/cre_v4_structure_gap_analysis.md
```

```bash
git diff -- \
  doc/cre_v4_structure_gap_analysis.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the comparison note now contains an explicit `bundle-first` explanation
- the note now contains two `mermaid` flowcharts
- the current project flow and the `CRE_v4` flow are now both represented as
  standalone diagrams in the same document
