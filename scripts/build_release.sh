#!/usr/bin/env bash
# CRE 分析套件发布打包脚本
set -euo pipefail

VERSION=${1:-"v1.0.0"}
OUT_DIR="release"
PACKAGE_NAME="cre_suite_${VERSION}"

mkdir -p "${OUT_DIR}"

tar -czf "${OUT_DIR}/${PACKAGE_NAME}.tar.gz" \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='*.egg-info' \
    --exclude='.pytest_cache' \
    --exclude='logs/' \
    -C isaac-training/training \
    analyzers/ \
    repair/ \
    cfg/spec_cfg/ \
    cfg/benchmark_cfg/ \
    scripts/run_benchmark.py \
    -C ../../ \
    TRACEABILITY.md \
    README.md \
    DECISIONS.md

echo "打包完成：${OUT_DIR}/${PACKAGE_NAME}.tar.gz"
