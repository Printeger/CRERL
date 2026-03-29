#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_full_smoke_test.sh [--reports-root DIR] [--bundle-prefix PREFIX] [--rerun-mode MODE] [--skip-conda-activate]

Description:
  Runs the full CRE smoke-test chain end to end:
    static -> dynamic -> semantic -> report -> repair -> validation -> integration -> benchmark -> release

Options:
  --reports-root DIR       Root directory for generated smoke-test reports.
                           Default: /tmp/crerl_full_smoke_<timestamp>
  --bundle-prefix PREFIX   Prefix used for bundle names.
                           Default: smoke
  --rerun-mode MODE        Validation rerun mode: preview | auto | subprocess
                           Default: auto
  --skip-conda-activate    Skip "conda activate NavRL" if already inside the right env.
  -h, --help               Show this help text.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${TRAINING_DIR}/../.." && pwd)"

REPORTS_ROOT=""
BUNDLE_PREFIX="smoke"
RERUN_MODE="auto"
SKIP_CONDA_ACTIVATE="0"

while (($#)); do
  case "$1" in
    --reports-root)
      REPORTS_ROOT="$2"
      shift 2
      ;;
    --bundle-prefix)
      BUNDLE_PREFIX="$2"
      shift 2
      ;;
    --rerun-mode)
      RERUN_MODE="$2"
      shift 2
      ;;
    --skip-conda-activate)
      SKIP_CONDA_ACTIVATE="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${REPORTS_ROOT}" ]]; then
  REPORTS_ROOT="/tmp/crerl_full_smoke_$(date +%Y%m%d_%H%M%S)"
fi

STATIC_BUNDLE="${BUNDLE_PREFIX}_static"
DYNAMIC_BUNDLE="${BUNDLE_PREFIX}_dynamic"
SEMANTIC_BUNDLE="${BUNDLE_PREFIX}_semantic"
REPORT_BUNDLE="${BUNDLE_PREFIX}_report"
REPAIR_BUNDLE="${BUNDLE_PREFIX}_repair"
VALIDATION_BUNDLE="${BUNDLE_PREFIX}_validation"
INTEGRATION_BUNDLE="${BUNDLE_PREFIX}_integration"
BENCHMARK_BUNDLE="${BUNDLE_PREFIX}_benchmark"
RELEASE_BUNDLE="${BUNDLE_PREFIX}_release"

DYNAMIC_PRIMARY_RUN="${DYNAMIC_PRIMARY_RUN:-${TRAINING_DIR}/logs/baseline_greedy_rollout_20260326_190209}"
DYNAMIC_COMPARE_RUN="${DYNAMIC_COMPARE_RUN:-${TRAINING_DIR}/logs/baseline_greedy_rollout_20260326_223636}"
REPAIRED_LOGS_ROOT="${REPAIRED_LOGS_ROOT:-${REPORTS_ROOT}/repaired_logs}"

activate_navrl() {
  if [[ "${SKIP_CONDA_ACTIVATE}" == "1" ]]; then
    return 0
  fi

  if [[ "$(type -t conda || true)" != "function" ]]; then
    if command -v conda >/dev/null 2>&1; then
      # shellcheck disable=SC1091
      source "$(conda info --base)/etc/profile.d/conda.sh"
    elif [[ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]]; then
      # shellcheck disable=SC1091
      source "${HOME}/miniconda3/etc/profile.d/conda.sh"
    elif [[ -f "${HOME}/anaconda3/etc/profile.d/conda.sh" ]]; then
      # shellcheck disable=SC1091
      source "${HOME}/anaconda3/etc/profile.d/conda.sh"
    else
      echo "Unable to locate conda initialization script." >&2
      exit 1
    fi
  fi

  conda activate NavRL
}

run_step() {
  local step_name="$1"
  shift
  local output_path="${REPORTS_ROOT}/${step_name}_cli_output.json"
  echo
  echo "==> Running ${step_name}"
  "$@" | tee "${output_path}"
}

require_dir() {
  local path="$1"
  if [[ ! -d "${path}" ]]; then
    echo "Required directory not found: ${path}" >&2
    exit 1
  fi
}

mkdir -p "${REPORTS_ROOT}" "${REPAIRED_LOGS_ROOT}"
require_dir "${DYNAMIC_PRIMARY_RUN}"
require_dir "${DYNAMIC_COMPARE_RUN}"

cd "${REPO_ROOT}"
activate_navrl

echo "Repository root: ${REPO_ROOT}"
echo "Reports root: ${REPORTS_ROOT}"
echo "Python: $(command -v python)"
echo "Conda env: ${CONDA_DEFAULT_ENV:-unknown}"

run_step "static" \
  python "${TRAINING_DIR}/scripts/run_static_audit.py" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${STATIC_BUNDLE}" \
  --output "${REPORTS_ROOT}/static_report_copy.json"

run_step "dynamic" \
  python "${TRAINING_DIR}/scripts/run_dynamic_audit.py" \
  --run-dir "${DYNAMIC_PRIMARY_RUN}" \
  --compare-run-dir "${DYNAMIC_COMPARE_RUN}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${DYNAMIC_BUNDLE}" \
  --output "${REPORTS_ROOT}/dynamic_report_copy.json"

run_step "semantic" \
  python "${TRAINING_DIR}/scripts/run_semantic_audit.py" \
  --static-bundle-dir "${REPORTS_ROOT}/analysis/static/${STATIC_BUNDLE}" \
  --dynamic-bundle-dir "${REPORTS_ROOT}/analysis/dynamic/${DYNAMIC_BUNDLE}" \
  --provider-mode mock \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${SEMANTIC_BUNDLE}" \
  --output "${REPORTS_ROOT}/semantic_report_copy.json"

run_step "report" \
  python "${TRAINING_DIR}/scripts/run_report_audit.py" \
  --static-bundle-dir "${REPORTS_ROOT}/analysis/static/${STATIC_BUNDLE}" \
  --dynamic-bundle-dir "${REPORTS_ROOT}/analysis/dynamic/${DYNAMIC_BUNDLE}" \
  --semantic-bundle-dir "${REPORTS_ROOT}/analysis/semantic/${SEMANTIC_BUNDLE}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${REPORT_BUNDLE}" \
  --output "${REPORTS_ROOT}/report_copy.json"

run_step "repair" \
  python "${TRAINING_DIR}/scripts/run_repair_audit.py" \
  --report-bundle-dir "${REPORTS_ROOT}/analysis/report/${REPORT_BUNDLE}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${REPAIR_BUNDLE}" \
  --output "${REPORTS_ROOT}/repair_plan_copy.json"

run_step "validation" \
  python "${TRAINING_DIR}/scripts/run_validation_audit.py" \
  --repair-bundle-dir "${REPORTS_ROOT}/analysis/repair/${REPAIR_BUNDLE}" \
  --logs-root "${TRAINING_DIR}/logs" \
  --repaired-logs-root "${REPAIRED_LOGS_ROOT}" \
  --trigger-rerun \
  --rerun-mode "${RERUN_MODE}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${VALIDATION_BUNDLE}" \
  --output "${REPORTS_ROOT}/validation_decision_copy.json"

run_step "integration" \
  python "${TRAINING_DIR}/scripts/run_integration_audit.py" \
  --scene-family nominal \
  --repair-preview-path "${REPORTS_ROOT}/analysis/repair/${REPAIR_BUNDLE}/validation_context_preview.json" \
  --comparison-bundle-dir "${REPORTS_ROOT}/analysis/dynamic/${DYNAMIC_BUNDLE}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${INTEGRATION_BUNDLE}" \
  --output "${REPORTS_ROOT}/integration_summary_copy.json"

run_step "benchmark" \
  python "${TRAINING_DIR}/scripts/run_benchmark_suite.py" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${BENCHMARK_BUNDLE}" \
  --output "${REPORTS_ROOT}/benchmark_summary_copy.json"

run_step "release" \
  python "${TRAINING_DIR}/scripts/run_release_packaging.py" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${RELEASE_BUNDLE}" \
  --integration-bundle-dir "${REPORTS_ROOT}/analysis/integration/${INTEGRATION_BUNDLE}" \
  --benchmark-bundle-dir "${REPORTS_ROOT}/analysis/benchmark/${BENCHMARK_BUNDLE}" \
  --output "${REPORTS_ROOT}/release_summary_copy.json"

python - "${REPORTS_ROOT}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

reports_root = Path(sys.argv[1])
steps = [
    "static",
    "dynamic",
    "semantic",
    "report",
    "repair",
    "validation",
    "integration",
    "benchmark",
    "release",
]
summary = {
    "summary_type": "cre_full_smoke_summary.v1",
    "reports_root": str(reports_root),
    "steps": {},
}
for step in steps:
    output_path = reports_root / f"{step}_cli_output.json"
    summary["steps"][step] = json.loads(output_path.read_text(encoding="utf-8"))

summary_path = reports_root / "full_smoke_summary.json"
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
print()
print(f"Full smoke summary written to: {summary_path}")
PY

echo
echo "Full smoke test completed successfully."
echo "Summary: ${REPORTS_ROOT}/full_smoke_summary.json"
