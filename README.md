# CRERL

CRERL 在 Isaac Sim + TorchRL 的无人机避障训练框架中实现 CRE（Constraint-Reward-Environment）预训练诊断流程，用于在训练前或训练后检测三类 specification 不一致：C-R（constraint-reward）、E-C（environment-constraint）、E-R（environment-reward），并输出语义报告、修复建议与验证结果。

## 目录结构

`isaac-training/training/` 下与 CRE 相关的关键目录如下：

- `analyzers/`：`spec_validator.py`、`static_analyzer.py`、`dynamic_analyzer.py`、`semantic_analyzer.py`、`report_generator.py`
- `repair/`：`repair_generator.py`、`validator.py`
- `cfg/spec_cfg/`：四份正式 v1 spec，作为静态分析与训练集成输入
- `cfg/benchmark_cfg/`：Phase 9 的 benchmark suite，含 `clean_nominal`、`injected_cr`、`injected_ec`、`injected_er`
- `scripts/`：训练与 benchmark 入口，包括 `train.py`、`run_benchmark.py`
- `unit_test/test_env/`：CRE 各阶段单元测试与集成测试

## 快速开始

激活环境：

```bash
conda activate NavRL
```

运行静态分析：

```bash
cd isaac-training/training
python -c "from analyzers.static_analyzer import run_static_analysis; import json; report = run_static_analysis('cfg/spec_cfg/reward_spec_v1.yaml', 'cfg/spec_cfg/constraint_spec_v1.yaml', 'cfg/spec_cfg/policy_spec_v1.yaml', 'cfg/spec_cfg/env_spec_v1.yaml'); print(json.dumps(report.summary, ensure_ascii=False, indent=2))"
```

运行 benchmark：

```bash
cd isaac-training/training
python scripts/run_benchmark.py --benchmark_dir cfg/benchmark_cfg/
```

运行全部测试：

```bash
cd isaac-training/training
python -m pytest unit_test/test_env/ -v
```

## 六阶段流水线

| Phase | 输入 | 输出 |
|---|---|---|
| Phase 2 Static Analysis | `reward/constraint/policy/env` 四份 spec | `StaticReport` |
| Phase 3 Dynamic Analysis | `StaticReport` + 运行日志目录 + `reward/constraint` spec | `DynamicReport` |
| Phase 4 Semantic Analysis | `StaticReport` + `DynamicReport` + `reward/constraint` spec | `SemanticReport` |
| Phase 5 Report Generation | `StaticReport` + `DynamicReport` + `SemanticReport` | `CREReport` |
| Phase 6 Repair | `CREReport` | `RepairResult` |
| Phase 7 Validation | `RepairResult` + `StaticReport` + 四份 spec | `PatchValidationResult` |

## 已知限制

- `D-BM1`：`phi_er=None`，E-R 维度当前不参与 `Psi_CRE` 与 `alarm` 计算。
- 因此 `injected_er` benchmark case 当前只保证 `total_issues > 0`，不保证 `alarm=True`。
- E-R 维度要进入 alarm，需要真实多环境部署数据支持 `phi_er` 的跨环境相关性计算。

## 决策记录

架构决策与偏差记录见 [DECISIONS.md](/home/mint/rl_dev/CRERL/DECISIONS.md)。
