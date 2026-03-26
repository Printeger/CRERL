# Module Migration Checklist

## 1. Scope

This checklist maps the **current project-owned files** into the new CRE architecture.

It is meant to answer:

1. which files remain on the mainline,
2. which files must be refactored to fit the new architecture,
3. which files should be retired from the main execution path,
4. which modules still need to be written.

This checklist excludes:
- `third_party/`
- `__pycache__/`
- generated runtime artifacts under `training/logs/` and historical one-off outputs

The canonical architecture reference is:
- `doc/system_architecture_and _control_flow.md`
- `doc/roadmap.md`

---

## 2. Legend

Exactly one of the four action columns should be marked for each row:

- `保留`: keep as part of the mainline with only minor hygiene changes
- `重构`: keep the file, but change its role/interface to match the new architecture
- `废弃`: remove from the mainline path; keep only as historical or reference material
- `新写`: module does not exist yet and should be created

---

## 3. Architecture Mapping

### 3.1 Specification Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `doc/roadmap/phase0.md` | Specification Layer | ✅ |  |  |  | 保留为 `SPEC-v0` 冻结文档，继续补齐 `C/R/E` 正式定义。 |
| `doc/specs/Env_Primitive_Spec_v0.md` | Specification Layer | ✅ |  |  |  | 保留为 primitive schema 的正式来源。 |
| `doc/specs/env_gen_rules.md` | Specification Layer | ✅ |  |  |  | 保留为 scene-family generation rules 的正式来源。 |
| `doc/system_architecture_and _control_flow.md` | Specification Layer | ✅ |  |  |  | 保留为系统总架构文档。 |
| `doc/roadmap.md` | Specification Layer | ✅ |  |  |  | 保留为主路线图，不再让零散 phase note 充当主路线。 |
| `doc/module_migration_checklist.md` | Specification Layer |  |  |  | ✅ | 本文件，作为后续迁移与任务拆分基准。 |

### 3.2 Environment Family Config Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/cfg/env_cfg/scene_cfg_base.yaml` | Specification Layer / Environment Config | ✅ |  |  |  | 保留为 family config 公共基底。 |
| `isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml` | Specification Layer / Environment Config | ✅ |  |  |  | 保留为 `nominal` family 的基准配置。 |
| `isaac-training/training/cfg/env_cfg/scene_cfg_boundary_critical.yaml` | Specification Layer / Environment Config | ✅ |  |  |  | 已补齐 `boundary_critical` family，作为主线 family config 保留。 |
| `isaac-training/training/cfg/env_cfg/scene_cfg_shifted.yaml` | Specification Layer / Environment Config | ✅ |  |  |  | 已补齐 `shifted` family，作为主线 family config 保留。 |

### 3.3 Scenario and Runtime Substrate Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/envs/env_gen.py` | Scenario and Runtime Substrate |  | ✅ |  |  | 作为主线 scene backend 保留，但继续收敛到 family-based generation、统一 IR、统一 validation/report 接口。 |
| `isaac-training/training/envs/universal_generator.py` | Legacy Prototype |  |  | ✅ |  | 退出主线，只保留为历史原型与几何模式参考。 |
| `isaac-training/training/scripts/universal_generator.py` | Legacy Compatibility Shim |  |  | ✅ |  | 作为兼容 shim 逐步退场，避免主线继续依赖旧路径。 |
| `isaac-training/training/envs/livox_mid360.py` | Sensor Utility | ✅ |  |  |  | 保留为传感器模式库。 |
| `isaac-training/training/envs/lidar_processor.py` | Sensor Utility | ✅ |  |  |  | 保留为点云/深度处理工具。 |
| `isaac-training/training/scripts/livox_mid360_integration.py` | Legacy Integration Helper |  |  | ✅ |  | 内容应并回主线环境集成文档或 `env.py`/新观察构建器，不再作为独立主线模块。 |

### 3.4 Execution and Logging Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/envs/cre_logging.py` | Execution and Logging |  | ✅ |  |  | 继续作为统一日志 schema，但要扩展到训练主循环和分析器输入。 |
| `isaac-training/training/logs/` | Runtime Artifact Store | ✅ |  |  |  | 保留为主线日志目录。 |
| `isaac-training/training/unit_test/logs/` | Historical Artifact Store |  |  | ✅ |  | 不再作为主线日志位置，保留历史记录即可。 |
| `isaac-training/training/runtime_logging/training_log_adapter.py` | Execution and Logging |  |  |  | ✅ | 新写，把 `env.py/train.py/eval.py` 产出的统计统一接入 `cre_logging` schema；使用 `runtime_logging/` 避免与 Python 标准库 `logging` 冲突。 |

### 3.5 Policy Execution Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/scripts/env.py` | RL Execution |  | ✅ |  |  | 保留当前 NavigationEnv，但要接入 family-based scene backend 与统一 CRE logs。 |
| `isaac-training/training/scripts/train.py` | RL Execution |  | ✅ |  |  | 保留训练入口，但重构成使用 scene-family config 和 CRE logging。 |
| `isaac-training/training/scripts/eval.py` | RL Execution |  | ✅ |  |  | 保留评估入口，但重构成与训练共用同一 spec/log/report pipeline。 |
| `isaac-training/training/scripts/ppo.py` | RL Execution | ✅ |  |  |  | 当前作为 baseline 算法保留；仅在接口需要时做轻量改动。 |
| `isaac-training/training/scripts/utils.py` | RL Execution Support |  | ✅ |  |  | 当前职责过杂，逐步拆成 `evaluation`, `math`, `policy_utils` 等更清晰模块。 |
| `isaac-training/training/scripts/command_generator.py` | Baseline / Stress Tool |  | ✅ |  |  | 改挂到 baseline execution / adversarial stress toolkit，下游服务于动态分析。 |
| `isaac-training/training/execution/baseline_policies.py` | Policy Execution |  |  |  | ✅ | 新写，提供 random / greedy / conservative 三类非 RL 基线。 |
| `isaac-training/training/execution/batch_rollout.py` | Policy Execution |  |  |  | ✅ | 新写，统一跑 scene families、policy sources、日志导出。 |

### 3.6 Manual Validation Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/unit_test/test_flight.py` | Manual Validation Harness |  | ✅ |  |  | 作为主线人工验证入口保留，但继续收敛成 family-scene inspection + CRE logging harness。 |
| `isaac-training/training/unit_test/test_hover.py` | Manual Validation Harness | ✅ |  |  |  | 保留为空场悬停/GPU/控制器 smoke test。 |
| `isaac-training/training/unit_test/test_livox_mid360.py` | Manual Validation Harness | ✅ |  |  |  | 保留为传感器专项验证。 |
| `isaac-training/training/unit_test/test_adversarial_gen.py` | Manual Validation / Stress Tool |  | ✅ |  |  | 保留但改归类为“stress/baseline inspection”，不作为主线 scene backend 入口。 |
| `isaac-training/training/unit_test/test_arena_viz.py` | Legacy Visualization |  |  | ✅ |  | 与旧 `universal_generator` 强绑定，退出主线。 |
| `isaac-training/training/unit_test/test_universal_viz.py` | Legacy Visualization |  |  | ✅ |  | 与旧 `universal_generator` 强绑定，退出主线。 |

### 3.7 Analysis Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/analyzers/spec_ir.py` | Analysis Layer |  |  |  | ✅ | 新写，统一 `C/R/E` 中间表示。 |
| `isaac-training/training/analyzers/static_analyzer.py` | Analysis Layer |  |  |  | ✅ | 新写，做 reward-constraint、coverage、proxy 等训练前静态检查。 |
| `isaac-training/training/analyzers/dynamic_analyzer.py` | Analysis Layer |  |  |  | ✅ | 新写，从统一 logs 计算 `W_CR / W_EC / W_ER` 等动态指标。 |
| `isaac-training/training/analyzers/llm_analyzer.py` | Analysis Layer |  |  |  | ✅ | 新写，负责语义诊断、缺失场景识别、修复建议。 |
| `isaac-training/training/analyzers/report_aggregator.py` | Analysis Layer |  |  |  | ✅ | 新写，融合 static/dynamic/LLM 输出，形成统一 inconsistency report。 |

### 3.8 Repair and Validation Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/repair/proposal_schema.py` | Repair Layer |  |  |  | ✅ | 新写，定义 repair patch 的机器可读 schema。 |
| `isaac-training/training/repair/repair_engine.py` | Repair Layer |  |  |  | ✅ | 新写，生成 reward / environment / threshold 级 repair 候选。 |
| `isaac-training/training/repair/patch_executor.py` | Repair Layer |  |  |  | ✅ | 新写，对配置/规约层应用结构化 patch。 |
| `isaac-training/training/repair/repair_validator.py` | Repair Layer |  |  |  | ✅ | 新写，对 repaired spec 重新执行分析与评估。 |
| `isaac-training/training/repair/acceptance.py` | Repair Layer |  |  |  | ✅ | 新写，编码 accept/reject rule。 |

### 3.9 Orchestration Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/pipeline/run_cre_audit.py` | Orchestration Layer |  |  |  | ✅ | 新写，主入口：`spec -> rollout -> analysis -> report`。 |
| `isaac-training/training/pipeline/run_repair_cycle.py` | Orchestration Layer |  |  |  | ✅ | 新写，主入口：`report -> repair -> validation -> accept/reject`。 |
| `isaac-training/training/pipeline/version_manager.py` | Orchestration Layer |  |  |  | ✅ | 新写，管理 spec/config/report/repair 版本关系。 |

### 3.10 Test Layer

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/unit_test/test_env/test_primitives.py` | Test Layer | ✅ |  |  |  | 保留为 primitive schema/geometry 单测。 |
| `isaac-training/training/unit_test/test_env/test_perforated_slab.py` | Test Layer | ✅ |  |  |  | 保留为 perforation/traversability 单测。 |
| `isaac-training/training/unit_test/test_env/test_scene_generation.py` | Test Layer |  | ✅ |  |  | 跟随 family-based backend 继续扩展，逐步覆盖三类 scene families。 |
| `isaac-training/training/unit_test/test_env/test_serialization_and_motion.py` | Test Layer |  | ✅ |  |  | 保留并扩展到新的 family config 和 dynamic validation。 |
| `isaac-training/training/unit_test/test_env/test_cre_logging.py` | Test Layer | ✅ |  |  |  | 保留为 CRE logging schema 单测。 |
| `isaac-training/training/unit_test/test_env/test_static_analyzer.py` | Test Layer |  |  |  | ✅ | 新写，静态检测器单测。 |
| `isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py` | Test Layer |  |  |  | ✅ | 新写，动态 witness/metrics 单测。 |
| `isaac-training/training/unit_test/test_env/test_report_aggregation.py` | Test Layer |  |  |  | ✅ | 新写，报告聚合与 severity 排序单测。 |
| `isaac-training/training/unit_test/test_env/test_repair_validation.py` | Test Layer |  |  |  | ✅ | 新写，repair acceptance loop 单测。 |

### 3.11 Support and Hardware/Asset Utilities

| 文件 / 模块 | 新架构层 | 保留 | 重构 | 废弃 | 新写 | 迁移动作 |
|---|---|---:|---:|---:|---:|---|
| `isaac-training/training/unit_test/check_drone_params.py` | Support Utility | ✅ |  |  |  | 保留为资产参数检查工具。 |
| `isaac-training/training/unit_test/compare_multirotor_usd.py` | Support Utility | ✅ |  |  |  | 保留为 USD/参数一致性检查工具。 |
| `isaac-training/training/unit_test/test_rotor_index_mapping.py` | Support Utility | ✅ |  |  |  | 保留为旋翼映射诊断工具。 |
| `isaac-training/training/unit_test/open_taslab_uav.py` | Support Utility | ✅ |  |  |  | 保留为 UAV 资产打开/排障脚本。 |
| `isaac-training/training/unit_test/open_robot_urdf.py` | Support Utility | ✅ |  |  |  | 保留为 URDF 打开/排障脚本。 |
| `isaac-training/training/unit_test/fix_usd.py` | Support Utility | ✅ |  |  |  | 保留为手工资产修复辅助脚本。 |

---

## 4. Mainline Migration Order

The migration should happen in this order.

### Wave 1. Stabilize the mainline substrate
- keep:
  - `phase0.md`
  - primitive spec
  - env generation rules
  - `scene_cfg_base.yaml`
  - `scene_cfg_nominal.yaml`
- refactor:
  - `env_gen.py`
  - `cre_logging.py`
  - `test_flight.py`
- write:
  - `scene_cfg_boundary_critical.yaml`
  - `scene_cfg_shifted.yaml`

### Wave 2. Bring RL under the same spec/log path
- refactor:
  - `env.py`
  - `train.py`
  - `eval.py`
  - `utils.py`
- keep:
  - `ppo.py`
- write:
  - `training_log_adapter.py`

### Wave 3. Build the CRE analyzers
- write:
  - `spec_ir.py`
  - `static_analyzer.py`
  - `dynamic_analyzer.py`
  - `llm_analyzer.py`
  - `report_aggregator.py`

### Wave 4. Build repair and orchestration
- write:
  - `repair_engine.py`
  - `patch_executor.py`
  - `repair_validator.py`
  - `acceptance.py`
  - `run_cre_audit.py`
  - `run_repair_cycle.py`

### Wave 5. Retire the old branch points
- deprecate from mainline:
  - `universal_generator.py`
  - `scripts/universal_generator.py`
  - `test_arena_viz.py`
  - `test_universal_viz.py`
  - `scripts/livox_mid360_integration.py`

---

## 5. One-Sentence Decision Rule

If a file does not help complete:

`spec -> scene generation -> execution -> logs -> analysis -> report -> repair -> validation`

then it should either be:
- demoted to support status,
- retired from the mainline,
- or rewritten to serve that chain directly.
