# CRERL

CRERL 在 Isaac Sim + TorchRL 的无人机避障训练框架中推进 CRE（Constraint-Reward-Environment）PDF 对齐重构。当前 canonical 主线处于 strict PDF refactor 阶段，旧版 `static/dynamic/semantic/report/repair/validator` 流水线已降级为 `legacy/` 历史参考，不再代表当前实现目标。

## 目录结构

`isaac-training/training/` 下与 CRE 相关的关键目录如下：

- `analyzers/`：当前 canonical 基础设施位于 `diag_report.py`、`cfg.py`、`errors.py`、`llm_gateway.py`、`m1.py`；旧分析链路位于 `analyzers/legacy/`
- `repair/`：当前 canonical 目标是未来的 `m7.py` / `m8.py`；旧修复/验收链路位于 `repair/legacy/`
- `cfg/spec_cfg/`：四份正式 v1 spec，作为静态分析与训练集成输入
- `cfg/benchmark_cfg/`：Phase 9 的 benchmark suite，含 `clean_nominal`、`injected_cr`、`injected_ec`、`injected_er`
- `scripts/`：训练与 benchmark 入口，包括 `train.py`、`run_benchmark.py`
- `unit_test/test_env/`：CRE 各阶段单元测试与集成测试

## 快速开始

激活环境：

```bash
conda activate NavRL
```

运行旧版静态分析（historical / legacy only）：

```bash
cd isaac-training/training
python -c "from analyzers.legacy.static_analyzer import run_static_analysis; import json; report = run_static_analysis('cfg/spec_cfg/reward_spec_v1.yaml', 'cfg/spec_cfg/constraint_spec_v1.yaml', 'cfg/spec_cfg/policy_spec_v1.yaml', 'cfg/spec_cfg/env_spec_v1.yaml'); print(json.dumps(report.summary, ensure_ascii=False, indent=2))"
```

运行旧版 benchmark（historical / legacy only）：

```bash
cd isaac-training/training
python scripts/run_benchmark.py --benchmark_dir cfg/benchmark_cfg/
```

运行全部测试：

```bash
cd isaac-training/training
python -m pytest unit_test/test_env/ -v
```

## Historical Legacy Pipeline

| Phase | 输入 | 输出 |
|---|---|---|
| Legacy Static Analysis | `reward/constraint/policy/env` 四份 spec | `StaticReport` |
| Legacy Dynamic Analysis | `StaticReport` + 运行日志目录 + `reward/constraint` spec | `DynamicReport` |
| Legacy Semantic Analysis | `StaticReport` + `DynamicReport` + `reward/constraint` spec | `SemanticReport` |
| Legacy Report Generation | `StaticReport` + `DynamicReport` + `SemanticReport` | `CREReport` |
| Legacy Repair | `CREReport` | `RepairResult` |
| Legacy Validation | `RepairResult` + `StaticReport` + 四份 spec | `PatchValidationResult` |

## 已知限制

- 以下限制针对 `analyzers/legacy/` 与 `repair/legacy/` 历史链路，而非 strict PDF canonical 目标。
- `D-BM1`：legacy `phi_er=None`，E-R 维度当前不参与 `Psi_CRE` 与 `alarm` 计算。
- 因此 legacy `injected_er` benchmark case 当前只保证 `total_issues > 0`，不保证 `alarm=True`。
- E-R 维度要进入 alarm，需要 canonical M2/M5 落地并接入真实多环境部署数据。

## 决策记录

架构决策与偏差记录见 [DECISIONS.md](/home/mint/rl_dev/CRERL/DECISIONS.md)。
