# Phase 6 Development Status

Updated: 2026-03-29

## 1. This Iteration Goal

This iteration continues Phase 6 beyond the first semantic bundle writer.

The goal of this step is to add three things while keeping the current
evidence-first contract unchanged:

- a higher-level semantic report merge interface
- a stable claim-consumer interface for Phase 7 reporting and Phase 8 repair
- a real-provider-ready semantic adapter path, using
  `doc/COMP OpenAI Access Guide v3.11.pdf` as the local integration reference,
  but keeping API-key access optional and externalized

## 2. Implemented Results

### 2.1 Phase-7 Claim Consumer Interface Added

A new file was added:

- `isaac-training/training/analyzers/semantic_merge.py`

It now defines a downstream-consumable semantic substrate:

- `Phase7ClaimRecord`
- `Phase7ClaimConsumerBundle`
- `SemanticReportMergeInput`
- `build_phase7_claim_consumer(...)`
- `build_semantic_report_merge_input(...)`

This means Phase 7 and Phase 8 no longer need to scrape ad hoc fields directly
from `semantic_report.json`. They can instead consume:

- `claim_consumer.json`
- `semantic_merge_input.json`

with a stable contract.

### 2.2 Semantic Bundle Now Exports Merge and Consumer Artifacts

`isaac-training/training/analyzers/semantic_analyzer.py` was extended so that a
semantic bundle now writes:

- `semantic_report.json`
- `semantic_claims.json`
- `semantic_input.json`
- `semantic_summary.md`
- `semantic_merge_input.json`
- `claim_consumer.json`
- `summary.json`
- `manifest.json`

This keeps the Phase 6 semantic output aligned with the later Phase 7 report
generator and Phase 8 repair engine.

### 2.3 Real Provider Interface Is Now Reserved Without Breaking Determinism

`isaac-training/training/analyzers/semantic_provider.py` was extended with:

- `SemanticProviderConfig`
- `AzureGatewayProviderConfig`
- `AzureGatewaySemanticProvider`
- `build_provider_messages(...)`
- `build_semantic_provider(...)`

The integration shape follows the local guide in:

- `doc/COMP OpenAI Access Guide v3.11.pdf`

Specifically, the reserved real-provider path uses the same Azure-style gateway
pattern described there:

- `AzureOpenAI`
- gateway base URL
- deployment name
- API version
- API key passed externally

The current implementation is intentionally conservative:

- `mock` remains the default provider mode
- the real provider path is optional
- API key must come from config or env var
- evidence-first input construction remains mandatory
- the provider still only generates claims
- cross-check still decides whether claims become supported / weak / rejected

### 2.4 LLM Analyzer Placeholder Was Upgraded

`isaac-training/training/analyzers/llm_analyzer.py` is no longer a dead
placeholder.

It is now a compatibility entrypoint that delegates to the Phase 6 semantic
analyzer with a named provider mode.

This keeps the naming bridge for later LLM integration while still preserving
the current semantic pipeline architecture.

### 2.5 Report Contract and Policy Runtime Expectations Were Extended

The semantic report contract was updated again so the semantic namespace now
expects the two new downstream artifacts:

- `semantic_merge_input.json`
- `claim_consumer.json`

This was updated in:

- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

That makes the Phase 7 consumer contract machine-readable instead of implicit.

## 3. Main Files Added or Changed

Code files:

- `isaac-training/training/analyzers/semantic_merge.py`
- `isaac-training/training/analyzers/semantic_provider.py`
- `isaac-training/training/analyzers/semantic_analyzer.py`
- `isaac-training/training/analyzers/llm_analyzer.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/scripts/run_semantic_audit.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`
- `isaac-training/training/unit_test/test_env/test_semantic_analyzer.py`

Documentation/state files:

- `doc/dev_log/p6_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/analyzers/semantic_claims.py \
  isaac-training/training/analyzers/semantic_inputs.py \
  isaac-training/training/analyzers/semantic_crosscheck.py \
  isaac-training/training/analyzers/semantic_provider.py \
  isaac-training/training/analyzers/semantic_merge.py \
  isaac-training/training/analyzers/semantic_analyzer.py \
  isaac-training/training/analyzers/llm_analyzer.py \
  isaac-training/training/analyzers/__init__.py \
  isaac-training/training/scripts/run_semantic_audit.py \
  isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

Expected result:

- no syntax error

### 4.2 Pure Python Unit Test

Run:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

Expected result:

- existing semantic tests still pass
- merge/consumer tests pass
- provider-selection tests pass
- no Isaac Sim dependency is required

### 4.3 Real Bundle Semantic CLI Smoke Test

Run:

```bash
python3 isaac-training/training/scripts/run_semantic_audit.py \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --dynamic-bundle-dir /tmp/crerl_phase5_round4_reports/analysis/dynamic/dynamic_eval_nominal_vs_shifted \
  --reports-root /tmp/crerl_phase6_reports_round2 \
  --bundle-name semantic_eval_nominal_vs_shifted_round2 \
  --provider-mode mock \
  --output /tmp/crerl_phase6_reports_round2/semantic_report_copy.json
```

Expected result:

- semantic bundle is written successfully
- bundle includes:
  - `semantic_merge_input.json`
  - `claim_consumer.json`
- CLI prints `provider_mode = mock`

### 4.4 Real Provider Reservation Smoke Test

Run:

```bash
python3 - <<'PY'
import sys
from pathlib import Path
root = Path('/home/mint/rl_dev/CRERL/isaac-training/training')
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from analyzers.semantic_provider import build_semantic_provider

mock = build_semantic_provider('mock', config={'max_claims': 2, 'api_key_env_var': 'IGNORED'})
print({'mock_type': type(mock).__name__, 'mock_max_claims': getattr(mock, 'max_claims', None)})

gateway = build_semantic_provider(
    'azure_gateway',
    config={'deployment_name': 'gpt4o', 'api_key_env_var': 'THIS_ENV_SHOULD_NOT_EXIST_FOR_TEST'},
)
print({'gateway_type': type(gateway).__name__, 'deployment_name': gateway.config.deployment_name})

try:
    gateway._resolve_api_key()
except RuntimeError as exc:
    print({'gateway_key_resolution': 'failed_as_expected', 'message_contains_missing_key': 'Missing API key' in str(exc)})
PY
```

Expected result:

- `mock` provider still works
- `azure_gateway` provider can be instantiated
- missing API key produces an explicit failure instead of a silent fallback

## 5. Validation Results

Validation run on 2026-03-27:

### 5.1 `py_compile`

Result:

- passed

### 5.2 Unit Test

Command:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

Result:

- `16 passed`

### 5.3 Real Bundle Semantic CLI Smoke Test

Observed result:

- semantic bundle successfully written to:
  - `/tmp/crerl_phase6_reports_round2/analysis/semantic/semantic_eval_nominal_vs_shifted_round2/`
- CLI output confirmed:
  - `passed = true`
  - `provider_mode = mock`
  - `supported_claims = 1`
  - `weak_claims = 1`
  - `rejected_claims = 0`
  - `most_likely_claim_type = E-R`
- new downstream artifacts were present:
  - `semantic_merge_input.json`
  - `claim_consumer.json`

### 5.4 Real Provider Reservation Smoke Test

Observed result:

- `mock_type = MockSemanticProvider`
- `mock_max_claims = 2`
- `gateway_type = AzureGatewaySemanticProvider`
- `deployment_name = gpt4o`
- missing key failed explicitly as expected

Note:

- the host environment currently does not have the `openai` Python package
  installed, so an actual gateway call was not attempted
- this is acceptable for this iteration because the requirement was to reserve
  the API-key interface and keep the current evidence-first contract unchanged

## 6. Current Conclusion

Phase 6 now has:

- a deterministic semantic bundle pipeline
- a higher-level semantic merge input for Phase 7
- a stable claim-consumer contract for downstream report/repair logic
- a real-provider-ready semantic adapter path that still keeps evidence-first
  machine cross-checking in control

This is enough to start wiring Phase 7 report generation without coupling it to
provider details.

## 7. Next Step

The next step should be:

- build the Phase 7 unified report generator on top of:
  - `static_report.json`
  - `dynamic_report.json`
  - `semantic_report.json`
  - `semantic_merge_input.json`
  - `claim_consumer.json`
- define severity ranking and merged root-cause ordering
- keep the provider path optional until the merged report layer is stable

## 8. Semantic-Prompt Externalization Addendum

The semantic provider path was later tightened without changing the
evidence-first contract.

This addendum introduced:

- `isaac-training/training/cfg/semantic_cfg/semantic_prompt_v1.yaml`
- prompt-template loading inside:
  - `isaac-training/training/analyzers/semantic_provider.py`
- prompt-config passthrough inside:
  - `isaac-training/training/scripts/run_semantic_audit.py`

The main result is that the system prompt, task description, output schema, and
rule list are no longer hardcoded in Python. They now live in a machine-readable
runtime config file while the semantic analyzer keeps the same claim schema and
cross-check path as before.

Focused validation for this addendum:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/semantic_provider.py \
  isaac-training/training/scripts/run_semantic_audit.py \
  isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

```bash
pytest -q isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

Validation results:

- `py_compile` passed
- `pytest` passed:
  - `17 passed`
- the semantic provider now reports:
  - `prompt_cfg_path = isaac-training/training/cfg/semantic_cfg/semantic_prompt_v1.yaml`
- a temporary YAML prompt template can override:
  - `system_prompt`
  - `task`
  - `rules`
  - `required_output_schema`

Real-provider note:

- the `NavRL` environment now has the `openai` package available
- but a live gateway call still requires the configured API key env var to be
  visible in the shell that launches the semantic CLI or smoke scripts
