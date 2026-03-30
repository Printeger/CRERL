#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  with_comp_api_key.sh [--key-file PATH] [--env-var NAME] [--print-source] -- <command...>
  with_comp_api_key.sh [--key-file PATH] [--env-var NAME] [--print-source] <command...>

Description:
  Reads a local COMP API key file, strips all Unicode whitespace, exports the
  key into the requested env var, and then execs the given command.

Defaults:
  key-file candidates:
    1. doc/API_KEY
    2. doc/API_KEY.md
  env-var:
    COMP_OPENAI_API_KEY

Examples:
  bash isaac-training/training/scripts/with_comp_api_key.sh -- \
    bash isaac-training/training/scripts/run_full_smoke_test.sh \
      --reports-root /tmp/crerl_real_llm_smoke \
      --bundle-prefix realllm \
      --semantic-provider-mode azure_gateway

  bash isaac-training/training/scripts/with_comp_api_key.sh \
    bash isaac-training/training/scripts/run_native_execution_smoke.sh \
      --work-root /tmp/crerl_native_real_llm \
      --bundle-prefix native_llm \
      --semantic-provider-mode azure_gateway
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${TRAINING_DIR}/../.." && pwd)"

ENV_VAR_NAME="COMP_OPENAI_API_KEY"
KEY_FILE=""
PRINT_SOURCE="0"

while (($#)); do
  case "$1" in
    --key-file)
      KEY_FILE="$2"
      shift 2
      ;;
    --env-var)
      ENV_VAR_NAME="$2"
      shift 2
      ;;
    --print-source)
      PRINT_SOURCE="1"
      shift
      ;;
    --)
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

if [[ -z "${KEY_FILE}" ]]; then
  if [[ -f "${REPO_ROOT}/doc/API_KEY" ]]; then
    KEY_FILE="${REPO_ROOT}/doc/API_KEY"
  elif [[ -f "${REPO_ROOT}/doc/API_KEY.md" ]]; then
    KEY_FILE="${REPO_ROOT}/doc/API_KEY.md"
  else
    echo "No local COMP API key file found. Checked: ${REPO_ROOT}/doc/API_KEY and ${REPO_ROOT}/doc/API_KEY.md" >&2
    exit 1
  fi
fi

if [[ ! -f "${KEY_FILE}" ]]; then
  echo "API key file not found: ${KEY_FILE}" >&2
  exit 1
fi

KEY_VALUE="$(
  python3 - "${KEY_FILE}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
cleaned = "".join(ch for ch in text if not ch.isspace())
if not cleaned:
    raise SystemExit("API key file is empty after whitespace stripping")
print(cleaned, end="")
PY
)"

export "${ENV_VAR_NAME}=${KEY_VALUE}"

if [[ "${PRINT_SOURCE}" == "1" ]]; then
  echo "Loaded ${ENV_VAR_NAME} from ${KEY_FILE}" >&2
fi

if (($# == 0)); then
  echo "Loaded ${ENV_VAR_NAME} from ${KEY_FILE}. Pass a command after -- to execute with this key." >&2
  exit 0
fi

exec "$@"
