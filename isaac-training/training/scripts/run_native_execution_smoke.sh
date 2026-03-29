#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_native_execution_smoke.sh [--work-root DIR] [--bundle-prefix PREFIX] [--skip-conda-activate]

Description:
  Runs a true native-execution smoke path:
    baseline(nominal) -> short train(nominal) -> short eval(shifted)
      -> static -> dynamic -> semantic -> report -> repair(E-R) -> validation

  The script:
    - activates conda env NavRL
    - sources setup_conda_env.sh when available
    - launches real baseline/train/eval entrypoints
    - stores deterministic accepted runs under a dedicated logs root
    - runs a short analysis/repair/validation chain over the generated native runs

Options:
  --work-root DIR         Root working directory for logs, reports, and wandb artifacts.
                          Default: /tmp/crerl_native_execution_<timestamp>
  --bundle-prefix PREFIX  Prefix used for bundle names.
                          Default: native
  --skip-conda-activate   Skip conda activation if already in NavRL.
  -h, --help              Show this help text.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${TRAINING_DIR}/../.." && pwd)"
ISAAC_ROOT="$(cd -- "${REPO_ROOT}/.." && pwd)"
SETUP_CONDA_ENV_SCRIPT="${ISAAC_ROOT}/setup_conda_env.sh"

WORK_ROOT=""
BUNDLE_PREFIX="native"
SKIP_CONDA_ACTIVATE="0"

while (($#)); do
  case "$1" in
    --work-root)
      WORK_ROOT="$2"
      shift 2
      ;;
    --bundle-prefix)
      BUNDLE_PREFIX="$2"
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

if [[ -z "${WORK_ROOT}" ]]; then
  WORK_ROOT="/tmp/crerl_native_execution_$(date +%Y%m%d_%H%M%S)"
fi

LOGS_ROOT="${WORK_ROOT}/logs"
REPORTS_ROOT="${WORK_ROOT}/reports"
WANDB_ROOT="${WORK_ROOT}/wandb"
REPAIRED_LOGS_ROOT="${WORK_ROOT}/repaired_logs"
SUMMARY_PATH="${WORK_ROOT}/native_execution_summary.json"

BASELINE_RUN_NAME="${BUNDLE_PREFIX}_baseline"
TRAIN_RUN_NAME="${BUNDLE_PREFIX}_train"
EVAL_RUN_NAME="${BUNDLE_PREFIX}_eval"
REPAIR_CLAIM_TYPE_OVERRIDE="E-R"

BASELINE_RUN_DIR="${LOGS_ROOT}/${BASELINE_RUN_NAME}"
TRAIN_RUN_DIR="${LOGS_ROOT}/${TRAIN_RUN_NAME}"
EVAL_RUN_DIR="${LOGS_ROOT}/${EVAL_RUN_NAME}"

STATIC_BUNDLE="${BUNDLE_PREFIX}_static"
DYNAMIC_BUNDLE="${BUNDLE_PREFIX}_dynamic"
SEMANTIC_BUNDLE="${BUNDLE_PREFIX}_semantic"
REPORT_BUNDLE="${BUNDLE_PREFIX}_report"
REPAIR_BUNDLE="${BUNDLE_PREFIX}_repair"
VALIDATION_BUNDLE="${BUNDLE_PREFIX}_validation"

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
    else
      echo "Unable to locate conda initialization script." >&2
      exit 1
    fi
  fi

  conda activate NavRL
  if [[ -f "${SETUP_CONDA_ENV_SCRIPT}" ]]; then
    # shellcheck disable=SC1090
    source "${SETUP_CONDA_ENV_SCRIPT}"
  fi
}

run_hydra_step() {
  local run_name="$1"
  local wandb_dir="$2"
  local script_path="$3"
  shift 3

  rm -rf "${LOGS_ROOT:?}/${run_name}" "${wandb_dir}"
  mkdir -p "${LOGS_ROOT}" "${REPORTS_ROOT}" "${wandb_dir}"

  (
    export CRE_RUN_LOG_BASE_DIR="${LOGS_ROOT}"
    export CRE_RUN_USE_TIMESTAMP=0
    export CRE_RUN_NAME_OVERRIDE="${run_name}"
    export WANDB_DIR="${wandb_dir}"
    export HYDRA_FULL_ERROR=1
    cd "${REPO_ROOT}"
    python "${script_path}" "$@"
  )
}

collect_latest_checkpoint() {
  local wandb_dir="$1"
  find "${wandb_dir}" -path '*checkpoint_final.pt' | sort | tail -n 1
}

mkdir -p "${WORK_ROOT}" "${LOGS_ROOT}" "${REPORTS_ROOT}" "${WANDB_ROOT}" "${REPAIRED_LOGS_ROOT}"
cd "${REPO_ROOT}"
activate_navrl

echo "Repository root: ${REPO_ROOT}"
echo "Work root: ${WORK_ROOT}"
echo "Logs root: ${LOGS_ROOT}"
echo "Reports root: ${REPORTS_ROOT}"
echo "WandB root: ${WANDB_ROOT}"
echo "Repaired logs root: ${REPAIRED_LOGS_ROOT}"
echo "Python: $(command -v python)"
echo "Conda env: ${CONDA_DEFAULT_ENV:-unknown}"

echo
echo "==> Running native baseline"
run_hydra_step \
  "${BASELINE_RUN_NAME}" \
  "${WANDB_ROOT}/baseline" \
  "${TRAINING_DIR}/scripts/run_baseline.py" \
  "headless=True" \
  "baseline.name=greedy" \
  "baseline.num_episodes=1" \
  "baseline.seeds=[0]" \
  "scene_family_backend.family=nominal" \
  "env.num_envs=1" \
  "env.max_episode_length=64"

echo
echo "==> Running short native train"
run_hydra_step \
  "${TRAIN_RUN_NAME}" \
  "${WANDB_ROOT}/train" \
  "${TRAINING_DIR}/scripts/train.py" \
  "headless=True" \
  "wandb.mode=offline" \
  "scene_family_backend.family=nominal" \
  "env.num_envs=1" \
  "env.max_episode_length=64" \
  "max_frame_num=128" \
  "save_interval=999999" \
  "eval_interval=999999" \
  "+skip_periodic_eval=True"

TRAIN_CHECKPOINT="$(collect_latest_checkpoint "${WANDB_ROOT}/train")"
if [[ -z "${TRAIN_CHECKPOINT}" || ! -f "${TRAIN_CHECKPOINT}" ]]; then
  echo "Failed to locate checkpoint_final.pt under ${WANDB_ROOT}/train" >&2
  exit 1
fi
echo "Train checkpoint: ${TRAIN_CHECKPOINT}"

echo
echo "==> Running short native eval"
run_hydra_step \
  "${EVAL_RUN_NAME}" \
  "${WANDB_ROOT}/eval" \
  "${TRAINING_DIR}/scripts/eval.py" \
  "headless=True" \
  "wandb.mode=offline" \
  "scene_family_backend.family=shifted" \
  "scene_logging.scenario_type=shifted" \
  "scene_logging.scene_cfg_name=scene_cfg_shifted.yaml" \
  "scene_logging.scene_id_prefix=shifted_native_smoke" \
  "env.num_envs=1" \
  "env.max_episode_length=64" \
  "max_frame_num=128" \
  "+checkpoint_path=${TRAIN_CHECKPOINT}"

echo
echo "==> Running static audit"
python "${TRAINING_DIR}/scripts/run_static_audit.py" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${STATIC_BUNDLE}" \
  --output "${WORK_ROOT}/static_report_copy.json"

echo
echo "==> Running dynamic audit on native shifted eval vs nominal baseline"
python "${TRAINING_DIR}/scripts/run_dynamic_audit.py" \
  --run-dir "${EVAL_RUN_DIR}" \
  --compare-run-dir "${BASELINE_RUN_DIR}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${DYNAMIC_BUNDLE}" \
  --output "${WORK_ROOT}/dynamic_report_copy.json"

echo
echo "==> Running semantic audit"
python "${TRAINING_DIR}/scripts/run_semantic_audit.py" \
  --static-bundle-dir "${REPORTS_ROOT}/analysis/static/${STATIC_BUNDLE}" \
  --dynamic-bundle-dir "${REPORTS_ROOT}/analysis/dynamic/${DYNAMIC_BUNDLE}" \
  --provider-mode mock \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${SEMANTIC_BUNDLE}" \
  --output "${WORK_ROOT}/semantic_report_copy.json"

echo
echo "==> Running report audit"
python "${TRAINING_DIR}/scripts/run_report_audit.py" \
  --static-bundle-dir "${REPORTS_ROOT}/analysis/static/${STATIC_BUNDLE}" \
  --dynamic-bundle-dir "${REPORTS_ROOT}/analysis/dynamic/${DYNAMIC_BUNDLE}" \
  --semantic-bundle-dir "${REPORTS_ROOT}/analysis/semantic/${SEMANTIC_BUNDLE}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${REPORT_BUNDLE}" \
  --output "${WORK_ROOT}/report_copy.json"

echo
echo "==> Running repair audit"
python "${TRAINING_DIR}/scripts/run_repair_audit.py" \
  --report-bundle-dir "${REPORTS_ROOT}/analysis/report/${REPORT_BUNDLE}" \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${REPAIR_BUNDLE}" \
  --claim-type-override "${REPAIR_CLAIM_TYPE_OVERRIDE}" \
  --output "${WORK_ROOT}/repair_plan_copy.json"

echo
echo "==> Running validation audit"
python "${TRAINING_DIR}/scripts/run_validation_audit.py" \
  --repair-bundle-dir "${REPORTS_ROOT}/analysis/repair/${REPAIR_BUNDLE}" \
  --logs-root "${LOGS_ROOT}" \
  --repaired-logs-root "${REPAIRED_LOGS_ROOT}" \
  --trigger-rerun \
  --rerun-mode auto \
  --reports-root "${REPORTS_ROOT}" \
  --bundle-name "${VALIDATION_BUNDLE}" \
  --output "${WORK_ROOT}/validation_decision_copy.json"

python - "${WORK_ROOT}" "${BASELINE_RUN_DIR}" "${TRAIN_RUN_DIR}" "${EVAL_RUN_DIR}" "${REPORTS_ROOT}" "${STATIC_BUNDLE}" "${DYNAMIC_BUNDLE}" "${SEMANTIC_BUNDLE}" "${REPORT_BUNDLE}" "${REPAIR_BUNDLE}" "${VALIDATION_BUNDLE}" "${TRAIN_CHECKPOINT}" "${REPAIR_CLAIM_TYPE_OVERRIDE}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

work_root = Path(sys.argv[1])
baseline_run_dir = Path(sys.argv[2])
train_run_dir = Path(sys.argv[3])
eval_run_dir = Path(sys.argv[4])
reports_root = Path(sys.argv[5])
static_bundle = sys.argv[6]
dynamic_bundle = sys.argv[7]
semantic_bundle = sys.argv[8]
report_bundle = sys.argv[9]
repair_bundle = sys.argv[10]
validation_bundle = sys.argv[11]
train_checkpoint = sys.argv[12]
repair_claim_type_override = sys.argv[13]

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

summary = {
    "summary_type": "cre_native_execution_smoke_summary.v1",
    "work_root": str(work_root),
    "baseline_run_dir": str(baseline_run_dir),
    "train_run_dir": str(train_run_dir),
    "eval_run_dir": str(eval_run_dir),
    "train_checkpoint": train_checkpoint,
    "runs": {
        "baseline": {
            "manifest": load_json(baseline_run_dir / "manifest.json"),
            "summary": load_json(baseline_run_dir / "summary.json"),
            "acceptance": load_json(baseline_run_dir / "acceptance.json"),
        },
        "train": {
            "manifest": load_json(train_run_dir / "manifest.json"),
            "summary": load_json(train_run_dir / "summary.json"),
            "acceptance": load_json(train_run_dir / "acceptance.json"),
        },
        "eval": {
            "manifest": load_json(eval_run_dir / "manifest.json"),
            "summary": load_json(eval_run_dir / "summary.json"),
            "acceptance": load_json(eval_run_dir / "acceptance.json"),
        },
    },
    "analysis": {
        "static": load_json(reports_root / "analysis" / "static" / static_bundle / "summary.json"),
        "dynamic": load_json(reports_root / "analysis" / "dynamic" / dynamic_bundle / "summary.json"),
        "semantic": load_json(reports_root / "analysis" / "semantic" / semantic_bundle / "summary.json"),
        "report": load_json(reports_root / "analysis" / "report" / report_bundle / "summary.json"),
        "repair": load_json(reports_root / "analysis" / "repair" / repair_bundle / "repair_summary.json"),
        "validation": load_json(reports_root / "analysis" / "validation" / validation_bundle / "validation_summary.json"),
    },
    "repair": {
        "claim_type_override": repair_claim_type_override,
        "acceptance": load_json(reports_root / "analysis" / "repair" / repair_bundle / "acceptance.json"),
        "repair_validation": load_json(reports_root / "analysis" / "repair" / repair_bundle / "repair_validation.json"),
        "validation_request": load_json(reports_root / "analysis" / "repair" / repair_bundle / "validation_request.json"),
    },
    "validation": {
        "decision": load_json(reports_root / "analysis" / "validation" / validation_bundle / "validation_decision.json"),
        "comparison": load_json(reports_root / "analysis" / "validation" / validation_bundle / "comparison.json"),
        "validation_runs": load_json(reports_root / "analysis" / "validation" / validation_bundle / "validation_runs.json"),
        "post_repair_evidence": load_json(reports_root / "analysis" / "validation" / validation_bundle / "post_repair_evidence.json"),
    },
}

summary_path = work_root / "native_execution_summary.json"
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
print()
print(f"Native execution summary written to: {summary_path}")
PY

echo
echo "Native execution smoke test completed successfully."
echo "Summary: ${SUMMARY_PATH}"
