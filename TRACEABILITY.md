# TRACEABILITY.md

本文件记录 CRE v2 规范字段、检测规则与实现代码之间的可追溯映射，用于发布验收、论文附录和后续维护。

| Spec 字段 | 所在文件 | 检测规则 | rule_id | 实现位置 | Phase |
|---|---|---|---|---|---|
| `reward_terms[*].weight` + `reward_terms[*].term_expr` | `cfg/spec_cfg/reward_spec_v1.yaml` | 正权 reward term 与 hard constraint 共享变量 token，近似检测 boundary-seeking 激励 | `type_compatibility` | `isaac-training/training/analyzers/static_analyzer.py::_rule_type_compatibility` (`115`) | Phase 2 |
| `reward_terms[*].clip_bounds` + `reward_terms[*].term_expr` | `cfg/spec_cfg/reward_spec_v1.yaml` | 非负 reward 支撑与 hard constraint 共享变量 token，近似检测边界支撑风险 | `domain_boundary` | `isaac-training/training/analyzers/static_analyzer.py::_rule_domain_boundary` (`170`) | Phase 2 |
| `shift_operators[*].description` + `E_tr.scene_families` | `cfg/spec_cfg/env_spec_v1.yaml` | 训练环境对 hard constraint critical region 的关键词级 coverage pre-bound 检查 | `coverage_prebound` | `isaac-training/training/analyzers/static_analyzer.py::_rule_coverage_prebound` (`234`) | Phase 2 |
| `E_tr.shift_operators` + `E_dep.deployment_envs[*].applied_shift_operators` | `cfg/spec_cfg/env_spec_v1.yaml` | 部署 shift 已声明但训练分布未显式覆盖 | `deployment_shift_coverage` | `isaac-training/training/analyzers/static_analyzer.py::_rule_deployment_shift_coverage` (`293`) | Phase 2 |
| `constraints[*].penalty_weight` + `constraints[*].indicator_predicate` + `reward_terms[*].weight` | `cfg/spec_cfg/constraint_spec_v1.yaml` + `cfg/spec_cfg/reward_spec_v1.yaml` | soft constraint 惩罚与正权 reward term 共享变量 token，提示潜在牵制关系 | `soft_constraint_penalty_alignment` | `isaac-training/training/analyzers/static_analyzer.py::_rule_soft_constraint_penalty_alignment` (`343`) | Phase 2 |
| `E_dep.deployment_envs[*].applied_shift_operators` | `cfg/spec_cfg/env_spec_v1.yaml` | 对已检出的 E-R 风险做语义层确认，形成独立 semantic issue | `SEM-ER-DETECTION` | `isaac-training/training/analyzers/semantic_analyzer.py::run_semantic_analysis` (`221`) | Phase 4 |
| `phi_cr`（由静态 + 动态 `C-R` issues 聚合，并按 reward terms 数量归一化） | `SemanticReport` 派生指标 | C-R 复合冲突信号，当 `phi_cr > 0.1` 且存在静态 `C-R` issues 时触发 | `SEM-CR-COMPOSITE` | `isaac-training/training/analyzers/semantic_analyzer.py::run_semantic_analysis` (`156`, `180`) | Phase 4 |
| `phi_ec`（由静态 + 动态 `E-C` issues 聚合，并按约束数量归一化） | `SemanticReport` 派生指标 | 训练环境对关键约束区域覆盖不足，当 `phi_ec < 0.5` 时触发 | `SEM-EC-COVERAGE` | `isaac-training/training/analyzers/semantic_analyzer.py::run_semantic_analysis` (`163`, `200`) | Phase 4 |
| `psi_cre` | `SemanticReport` 派生指标 | 全局 CRE 告警阈值检查，当 `psi_cre < 0.75` 时触发 | `SEM-ALARM` | `isaac-training/training/analyzers/semantic_analyzer.py::run_semantic_analysis` (`172`, `174`, `239`) | Phase 4 |

## 已知限制

- `D-BM1`：`phi_er` 当前固定为 `None`，E-R 维度不参与 `Psi_CRE` 与 `alarm` 计算。
- 这意味着 benchmark 中 `injected_er` 目前只能通过 `SEM-ER-DETECTION` 产生 `total_issues > 0`，不能像 `injected_cr` / `injected_ec` 一样触发 `alarm=True`。
- 若未来引入真实多环境部署数据并实现 `phi_er`，则 E-R 维度可进入 `Psi_CRE`，该偏差可自动消除。
