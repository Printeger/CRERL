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

## 17. RL-Mainline CRE-Intervention Addendum

The comparison note was then extended with a training-centered explanation so
the structural difference can be read from the perspective of reinforcement
learning workflow, not only from the perspective of module topology.

This update added one new chapter to:

- `doc/cre_v4_structure_gap_analysis.md`

The new chapter answers:

- if RL training is treated as the project mainline, how does CRE intervene in
  the current repository?
- if RL training is treated as the project mainline, how does CRE intervene in
  `doc/CRE_v4.pdf`?

What this addendum now makes explicit:

1. **current project intervention path**
   - pre-training:
     - YAML spec/env config
     - `spec_ir`
     - static audit
   - in-training:
     - scene-family binding
     - runtime metadata binding
     - unified CRE log capture for train/eval/baseline
   - post-training:
     - static/dynamic/semantic/report bundles interpret rollout evidence
   - repair loop:
     - repair bundle
     - validation rerun
     - evidence-based return to execution

2. **`CRE_v4` intervention path**
   - pre-training starts even earlier from:
     - `NLInput`
     - `M1`
     - `SpecS`
   - pre-training diagnosis is more centralized through:
     - `M2`
     - `M3`
     - discrepancy protocol
     - `M5 / PsiCRE`
   - semantic diagnosis, repair generation, and acceptance are modelled as one
     continuous typed pipeline around repaired `SpecS`

3. **a clearer architectural interpretation**
   - current repo:
     - CRE acts as an evidence-oriented outer loop around RL training
   - `CRE_v4`:
     - CRE acts more like a unified supervisory kernel over the RL loop

Focused validation for this addendum:

```bash
rg -n "以强化学习训练为主线看 CRE 的介入方式|训练前介入|训练中介入|证据型外环系统|统一内核型中枢系统" \
  doc/cre_v4_structure_gap_analysis.md
```

```bash
git diff -- \
  doc/cre_v4_structure_gap_analysis.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the note now contains a dedicated RL-mainline chapter
- the chapter distinguishes:
  - pre-training intervention
  - in-training intervention
  - post-training interpretation
  - repair-loop return path
- the chapter now makes the difference between current-project CRE and
  `CRE_v4` CRE readable from the RL workflow perspective instead of only from
  the static architecture perspective

## 18. Pure-RL Mainline Addendum

The comparison note was then extended once more to isolate the reinforcement
learning training stack itself before discussing CRE intervention.

This update added one new chapter to:

- `doc/cre_v4_structure_gap_analysis.md`

The new chapter answers:

- if CRE is temporarily removed from consideration, what is the actual RL
  training startup mainline in the current repository?
- which files are on that mainline?

What this addendum now makes explicit:

1. **startup flow without CRE**
   - config composition via Hydra
   - Isaac Sim startup
   - WandB run initialization
   - `NavigationEnv` construction
   - controller wrapping via `LeePositionController + VelController`
   - PPO policy construction
   - rollout collection through `SyncDataCollector`
   - `policy.train(data)` updates
   - periodic `evaluate(...)`
   - checkpoint saving and shutdown

2. **file-level mainline ownership**
   - startup/config:
     - `scripts/train.py`
     - `cfg/train.yaml`
     - `cfg/ppo.yaml`
     - `cfg/sim.yaml`
     - `cfg/drone.yaml`
   - env/runtime:
     - `scripts/env.py`
     - `envs/env_gen.py`
   - learning core:
     - `scripts/ppo.py`
     - `scripts/utils.py`

3. **a clarified architectural baseline**
   - before CRE is layered on top, the repo is still fundamentally an
     Isaac-Sim-based PPO navigation training stack
   - CRE should therefore be understood as an added evidence/diagnosis/repair
     system around this training backbone, not as the original base training
     loop itself

Focused validation for this addendum:

```bash
rg -n "没有 CRE 介入时的 RL 训练启动主流程|NavigationEnv|SyncDataCollector|policy.train\\(data\\)|checkpoint_final.pt|标准的 Isaac Sim \\+ PPO 导航训练栈" \
  doc/cre_v4_structure_gap_analysis.md
```

```bash
git diff -- \
  doc/cre_v4_structure_gap_analysis.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the comparison note now contains a dedicated pure-RL startup chapter
- the chapter explicitly separates:
  - startup/config
  - environment definition
  - PPO learning core
  - collector/evaluation/checkpoint flow
- the file ownership of the non-CRE RL mainline is now documented directly in
  the comparison note

## 19. Three-Demo HTML Deck Addendum

The repository was then extended with a lightweight English HTML presentation
deck for the three core CRE demonstration cases:

- Class I (`C-R`)
- Class II (`E-C`)
- Class III (`E-R`)

This update added one new presentation artifact at:

- `doc/cre_v1_three_demo_deck.html`

Its purpose is to make the benchmarked demo story presentation-ready without
requiring a new frontend app or an external slide tool.

What this addendum now makes explicit:

1. **one white-background HTML slide deck**
   - the new file is a standalone browser-viewable presentation
   - it keeps a white slide background for export-friendly review and PDF print
   - it supports:
     - keyboard navigation
     - clickable next/previous controls
     - print-to-PDF output

2. **a consistent five-slide story for all three demo classes**
   - slide 1:
     - overall benchmark/release framing
   - slide 2:
     - Class I (`C-R`) reward-vs-safety conflict
   - slide 3:
     - Class II (`E-C`) critical-scene undercoverage
   - slide 4:
     - Class III (`E-R`) nominal-vs-shifted fragility
   - slide 5:
     - live-demo guide and operator commands

3. **tight alignment with the existing CRE artifact contracts**
   - the deck points presenters back to:
     - benchmark configs
     - dynamic/semantic/report/validation artifacts
     - release packaging outputs
   - the deck therefore stays aligned with the Phase 11 benchmark/release path
     instead of becoming a disconnected marketing-only asset

Focused validation for this addendum:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

class SlideCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.slide_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section" and attrs.get("class", "").startswith("slide"):
            self.slide_count += 1

path = Path("doc/cre_v1_three_demo_deck.html")
parser = SlideCounter()
parser.feed(path.read_text(encoding="utf-8"))
print({"exists": path.exists(), "slide_count": parser.slide_count})
PY
```

```bash
rg -n "Three benchmarked demos|Class I \\(C-R\\)|Class II \\(E-C\\)|Class III \\(E-R\\)|How to show the three demos live" \
  doc/cre_v1_three_demo_deck.html
```

```bash
git diff -- \
  doc/cre_v1_three_demo_deck.html \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the new HTML deck exists and parses successfully as a local HTML document
- the deck contains:
  - 5 slides
  - 3 class-specific demo pages
  - one final live-demo operator page
- the deck remains white-background and self-contained:
  - no external runtime dependency is required to open it in a browser
  - no separate slide framework is required for local presentation

## 20. Isolated Three-Demo Experiment-Plan Addendum

The repository was then extended with an isolated markdown planning workspace
for the three core CRE demonstrations so the demo implementation does not drift
into uncontrolled edits across the main benchmark path.

This update added one new isolated planning artifact at:

- `cre-demos/README.md`

Its purpose is to freeze the intended causal structure of the three demos
before implementing any demo-only configs or scripts.

What this addendum now makes explicit:

1. **an isolated demo-only planning folder**
   - the new planning note lives under:
     - `cre-demos/`
   - this keeps demo work logically separated from:
     - main benchmark configs
     - main training scripts
     - the default Phase 11 release path

2. **strict causal boundaries for the three demos**
   - Demo 1 (`C-R`):
     - reward may change
     - environment must stay fixed
   - Demo 2 (`E-C`):
     - environment coverage may change
     - reward must stay fixed
   - Demo 3 (`E-R`):
     - evaluation environment may shift
     - reward and utility definitions must stay separate

3. **visual-first scene concepts and acceptance criteria**
   - each demo now has:
     - a dedicated scene concept
     - an allowed-change list
     - a frozen-variable list
     - required metrics
     - required visualizations
     - success criteria
     - anti-drift rejection conditions

Focused validation for this addendum:

```bash
test -f cre-demos/README.md
```

```bash
rg -n "^## 5\\.|^## 6\\.|^## 7\\.|One-factor rule|One-Page Anti-Drift Summary" \
  cre-demos/README.md
```

```bash
git diff -- \
  cre-demos/README.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the isolated demo-planning markdown now exists under `cre-demos/`
- the plan now contains dedicated sections for:
  - Demo 1 / `C-R`
  - Demo 2 / `E-C`
  - Demo 3 / `E-R`
- the plan also now contains:
  - shared visualization rules
  - anti-drift rules
  - a future isolated folder layout for demo-specific configs/scripts/assets

## 21. Demo-1 Chinese Development-Plan Addendum

The isolated demo-planning workspace was then extended with a dedicated
Chinese development plan for Demo 1 so implementation can start from a more
concrete execution checklist instead of only a high-level causal design note.

This update added one new demo-specific planning artifact at:

- `cre-demos/demo1_cr_boundary_lure/README.md`

It also refreshed the root demo plan so it links to that new subplan:

- `cre-demos/README.md`

What this addendum now makes explicit:

1. **a dedicated Demo 1 execution plan**
   - the new markdown expands Demo 1 from:
     - a high-level causal sketch
   - into:
     - a staged implementation plan
     - a directory plan
     - a data-retention plan
     - a video-retention plan
     - final acceptance gates

2. **what must be saved during Demo 1 execution**
   - config snapshots
   - seed manifests
   - train/eval outputs
   - step/episode trajectory logs
   - metric summaries
   - screenshots
   - raw and captioned videos

3. **what makes Demo 1 presentation-ready**
   - mandatory scene figure
   - mandatory trajectory overlay
   - mandatory grouped metric chart
   - mandatory corridor-choice figure
   - mandatory clean/injected/repaired video set

Focused validation for this addendum:

```bash
test -f cre-demos/demo1_cr_boundary_lure/README.md
```

```bash
rg -n "^## 6\\.|^## 8\\.|^## 9\\.|^## 10\\.|^## 12\\." \
  cre-demos/demo1_cr_boundary_lure/README.md
```

```bash
rg -n "Current dedicated subplans|demo1_cr_boundary_lure/README.md" \
  cre-demos/README.md
```

```bash
git diff -- \
  cre-demos/README.md \
  cre-demos/demo1_cr_boundary_lure/README.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the dedicated Demo 1 markdown now exists under its own isolated subfolder
- the new plan now explicitly records:
  - staged development steps
  - required experiment data
  - required videos
  - final acceptance rules
- the root isolated demo plan now links directly to the Demo 1 subplan

## 22. Demo-1 Isolated Implementation Addendum

The first isolated demo is now implemented end-to-end under:

- `cre-demos/demo1_cr_boundary_lure/`

This addendum introduced:

1. **demo-local config copies and scene geometry**
   - fixed dual-corridor scene definition in:
     - `cfg/scene_layout.yaml`
   - demo-local environment config in:
     - `cfg/env_cfg/scene_cfg_base.yaml`
     - `cfg/env_cfg/scene_cfg_nominal.yaml`
   - demo-local detector config in:
     - `cfg/detector_cfg/*.yaml`
   - demo-local clean / injected / repaired spec variants in:
     - `cfg/spec_clean/`
     - `cfg/spec_injected/`
     - `cfg/spec_repaired/`

2. **a runnable isolated pipeline**
   - the new runner:
     - `scripts/run_demo1.py`
   - now generates:
     - clean / injected / repaired CRE logs
     - static / dynamic bundles for all variants
     - semantic / report / repair bundle for injected
     - repair-validation bundle for injected vs repaired
     - verification summary JSON / markdown
     - top-down scene SVG
     - trajectory overlay SVG
     - metric-board SVG
     - lightweight replay HTML

3. **a focused regression test**
   - `test_demo1_pipeline.py`
   - runs the isolated pipeline in a temp directory
   - asserts that the demo-level goal is achieved

4. **frozen current demo outputs**
   - latest machine-readable artifacts now exist under:
     - `cre-demos/demo1_cr_boundary_lure/reports/latest/`
   - latest display assets now exist under:
     - `cre-demos/demo1_cr_boundary_lure/assets/`

Key observed result snapshot from the current successful run:

- Clean:
  - `risky_route_rate = 0.0`
  - `min_distance = 0.3685`
  - `near_violation_ratio = 0.0556`
  - `W_CR = 0.0103`
- Injected:
  - `risky_route_rate = 1.0`
  - `min_distance = 0.0673`
  - `near_violation_ratio = 0.5787`
  - `W_CR = 0.7180`
- Repaired:
  - `risky_route_rate = 0.0`
  - `min_distance = 0.3644`
  - `near_violation_ratio = 0.0556`
  - `W_CR = 0.0118`
- report primary claim:
  - `C-R`
- repair-validation decision:
  - `accepted`

Focused validation for this addendum:

```bash
python3 -m py_compile \
  cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py \
  cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py
```

```bash
pytest -q cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py
```

```bash
python3 cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py --clean-output
```

Validation results:

- the isolated Demo 1 runner now executes successfully inside the repo
- the focused pytest regression passes
- the latest verification summary reports:
  - `goal_achieved = true`
- the generated report path now attributes the injected case to:
  - `C-R`
- the generated validation path now resolves to:
  - `accepted`

## 13. Demo 1 Rerun Robustness Fix

Date:

- `2026-04-15`

What changed:

1. **made the isolated Demo 1 runner safe for repeated execution**
   - updated `cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py`
   - before creating each fixed-name run logger, the runner now removes the
     previous per-variant log directory:
     - `demo1_clean`
     - `demo1_injected`
     - `demo1_repaired`

2. **added a rerun regression test**
   - updated `cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py`
   - the new test executes the same pipeline twice against the same temp
     output root and asserts that the second run still succeeds

Why this was needed:

- the previous implementation reused the same fixed `run_name`
- `episodes.jsonl` and `steps.jsonl` were appended across reruns
- `summary.json` was regenerated for only the latest six episodes
- this caused `run_acceptance_check(...)` to fail with an
  `episode_count` mismatch on a plain rerun of:
  - `python3 cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py`

Focused validation:

```bash
python3 -m py_compile \
  cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py \
  cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py
```

```bash
pytest -q cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py
```

```bash
python3 cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py --clean-output
```

```bash
python3 cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py
```

Validation results:

- `py_compile` passed
- focused pytest passed:
  - `2 passed`
- the clean rerun path completed successfully
- the default rerun path completed successfully
- the verification result stayed stable:
  - `goal_achieved = true`
- the demo still supports the intended claim:
  - injected `risky_route_rate = 1.0`
  - injected `W_CR = 0.7180`
  - repaired validation decision = `accepted`

## 23. Demo-2 Chinese Development-Plan Addendum

Date:

- `2026-04-15`

What changed:

1. **added a dedicated Chinese development plan for Demo 2**
   - added:
     - `cre-demos/demo2_ec_hidden_wedge/README.md`
   - this new markdown expands Demo 2 from:
     - the high-level `E-C` causal sketch in `cre-demos/README.md`
   - into:
     - a staged implementation plan
     - a data-retention plan
     - a video-retention plan
     - acceptance and anti-drift rules

2. **refreshed the root isolated demo plan to index Demo 2**
   - updated:
     - `cre-demos/README.md`
   - the root plan now explicitly lists:
     - the new Demo 2 subplan
   - and links the Demo 2 section directly to:
     - `demo2_ec_hidden_wedge/README.md`

Why this was needed:

- the root three-demo plan already defined Demo 2 at the causal-design level
- but implementation could still drift because Demo 2 did not yet have:
  - a Chinese execution checklist
  - a frozen experimental retention contract
  - a frozen video / figure checklist
- this addendum closes that gap before environment configs or runners are
  implemented

What the new Demo 2 plan now makes explicit:

1. **the one-factor causal boundary**
   - reward must stay fixed
   - environment coverage is the only primary variable
   - repair must stay environment-side

2. **the concrete train/eval family story**
   - train family:
     - `demo2_ec_open_bias_train`
   - eval family:
     - `demo2_ec_hidden_wedge_eval`
   - the key presentation contrast is now frozen as:
     - open-bias training coverage vs hidden-wedge critical evaluation

3. **what must be saved for Demo 2**
   - family/spec snapshots
   - scene catalogs and template counts
   - coverage manifests
   - nominal / critical eval manifests
   - trajectory and failure artifacts
   - `W_EC`-oriented reports
   - raw and captioned demo videos

Focused validation:

```bash
test -f cre-demos/demo2_ec_hidden_wedge/README.md
```

```bash
rg -n "^## 6\\.|^## 8\\.|^## 9\\.|^## 10\\.|^## 12\\.|^## 15\\." \
  cre-demos/demo2_ec_hidden_wedge/README.md
```

```bash
rg -n "demo2_ec_hidden_wedge/README.md|Detailed Chinese subplan|Current dedicated subplans" \
  cre-demos/README.md
```

```bash
git diff -- \
  cre-demos/README.md \
  cre-demos/demo2_ec_hidden_wedge/README.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the dedicated Demo 2 markdown now exists under its own isolated subfolder
- the new plan now explicitly records:
  - staged development steps
  - required experiment data
  - required videos
  - final acceptance / anti-drift rules
- the root isolated demo plan now links directly to the Demo 2 subplan

## 24. Demo-3 Chinese Development-Plan Addendum

After Demo 2, the isolated `cre-demos` workspace was extended with a dedicated
Chinese planning document for the third demonstration:

- `cre-demos/demo3_er_shifted_gate/README.md`

This step is still documentation-only, but it is Phase 11-relevant because the
benchmark packaging layer depends on each demo having a frozen causal story,
artifact contract, and replay/visual proof surface before implementation.

This addendum also updates the root isolated demo index in:

- `cre-demos/README.md`

so the shared three-demo plan now links to all three dedicated subplans:

- Demo 1 / `C-R`
- Demo 2 / `E-C`
- Demo 3 / `E-R`

What the new Demo 3 plan now makes explicit:

1. **the one-factor causal boundary**
   - reward definition stays fixed
   - utility definition stays fixed
   - the shifted evaluation environment is the primary variable
   - repair must stay robustness-side

2. **the utility contract**
   - Demo 3 must define a non-reward utility metric before execution
   - the document freezes a proposed `U_task_v1` and its component fields
   - every proof artifact must present reward and utility together

3. **what must be saved for Demo 3**
   - config snapshots
   - scene/seed manifests
   - raw logs and trajectory records
   - utility/reward comparison tables
   - validation summaries
   - representative screenshots and replay/video exports

4. **what visual proof is required**
   - nominal-vs-shifted scene structure
   - same-seed trajectory comparison
   - reward-vs-utility scatter
   - repair recovery board
   - split-screen replay

Focused validation:

```bash
test -f cre-demos/demo3_er_shifted_gate/README.md
```

```bash
rg -n "Demo 3|demo3_er_shifted_gate|reward vs utility|必保存实验数据|必拍视频|图像出片规范" \
  cre-demos/README.md \
  cre-demos/demo3_er_shifted_gate/README.md \
  doc/dev_log/p11_dev_status.md
```

```bash
git diff --check -- \
  cre-demos/README.md \
  cre-demos/demo3_er_shifted_gate/README.md \
  doc/dev_log/p11_dev_status.md \
  Traceability.md
```

Validation results:

- the dedicated Demo 3 markdown now exists under its own isolated subfolder
- the new plan now explicitly records:
  - a staged implementation plan
  - a data-retention plan
  - a video-retention plan
  - a figure/styling plan
  - acceptance and anti-drift rules
- the root isolated demo plan now links directly to the Demo 3 subplan

## 25. Demo-3 Isolated Pipeline Implementation Addendum

The third isolated CRE demo is now fully implemented as a dedicated Phase 11
benchmark package under:

- `cre-demos/demo3_er_shifted_gate/`

This implementation keeps the Demo-3 causal story aligned with the frozen
documentation:

- reward stays fixed
- utility stays fixed as `U_task_v1`
- the injected failure is driven by shifted-family transfer mismatch
- the repair stays on the robustness / environment side

What was added:

1. **isolated demo configuration**
   - scene layout for a centered-gate nominal family and a shifted-gate family
   - clean / injected / repaired environment configs
   - shared reward / constraint / policy specs
   - detector thresholds and witness weights for the isolated run

2. **end-to-end demo pipeline**
   - `cre-demos/demo3_er_shifted_gate/scripts/run_demo3.py`
   - synthetic but contract-compliant runtime logs for:
     - `train`
     - `eval_nominal`
     - `eval_shifted`
   - static analysis, dynamic analysis, semantic analysis, report generation,
     rule-based repair, and post-repair validation

3. **machine-readable retained evidence**
   - full isolated report bundle under:
     - `cre-demos/demo3_er_shifted_gate/reports/latest/`
   - verification manifests, reward freeze note, utility freeze note, shift diff,
     metrics summaries, repair bundle, validation bundle, and visual manifest

4. **proof-oriented visuals**
   - multiple SVG boards under:
     - `cre-demos/demo3_er_shifted_gate/assets/screenshots/`
   - multiple replay pages under:
     - `cre-demos/demo3_er_shifted_gate/assets/videos/`
   - these include:
     - scene comparison
     - gate offset inset
     - same-seed shifted overlay
     - reward-vs-utility scatter
     - reward / utility retention bars
     - failure breakdown
     - shifted heatmap
     - repair recovery board
     - multiframe failure storyboard
     - summary card

5. **isolated regression test**
   - `cre-demos/demo3_er_shifted_gate/test_demo3_pipeline.py`
   - verifies:
     - goal achievement
     - injected reward remains deceptively decent under shift
     - injected utility drops sharply under shift
     - `W_ER` dominates the injected witness surface
     - repair validation is accepted

Observed headline result from the generated verification summary:

- injected `W_ER`: `0.574`
- injected reward retention under shift: `0.932`
- injected utility retention under shift: `0.244`
- injected nominal-vs-shifted success gap: `0.667`
- repaired decoupling gap: `0.182`
- repaired shifted success rate: `0.833`
- validation decision: `accepted`

Focused validation:

```bash
python3 cre-demos/demo3_er_shifted_gate/scripts/run_demo3.py --clean-output
```

```bash
pytest -q cre-demos/demo3_er_shifted_gate/test_demo3_pipeline.py
```

```bash
python3 -m py_compile \
  cre-demos/demo3_er_shifted_gate/scripts/run_demo3.py \
  cre-demos/demo3_er_shifted_gate/test_demo3_pipeline.py
```

Validation results:

- the isolated Demo-3 pipeline now runs end-to-end and reaches its goal
- the generated report promotes `E-R` as the primary claim type
- the selected repair operator is `increase_shifted_boundary_bias`
- post-repair validation is accepted
- the isolated pytest target passes: `2 passed`
