# TRACEABILITY.md — CRE PDF 条款 → 代码 追溯表

> 权威来源：`doc/CRE_v4.pdf` v1.0  
> 规则：实现前填写状态为 ❌；实现完成且合约测试全部通过后改为 ✅。  
> **未在本表登记 = 未完成，STATUS.md 不得勾选对应 DoD 条目。**

---

## Part A：核心数据结构（Phase 0）

| PDF 依据 | 数据结构 | 实现文件 | 状态 |
|---------|---------|---------|------|
| Part II §1.2 p.22 | `SpecS` (@dataclass frozen=True) | `analyzers/diag_report.py` | ✅ |
| Part II §1.2 p.21 | `NLInput` | `analyzers/diag_report.py` | ✅ |
| Part II §1.2 p.22 | `Constraint` | `analyzers/diag_report.py` | ✅ |
| Part II §1.2 p.22 | `RewardDAG` (nodes + edges) | `analyzers/diag_report.py` | ✅ |
| Part II §1.2 p.22 | `AmbiguityFlag` (flag_type, location, impact_score) | `analyzers/diag_report.py` | ✅ |
| Part II §1.2 p.22–23 | `DiagReport` (all fields incl. phi_cr2, phi_ec_bar, phi_er3, ci_95, flags, discrepancy, failure_hypothesis, repair_targets) | `analyzers/diag_report.py` | ✅ |
| Part II §1.2 p.23 | `RepairProposal` (proposal_id, spec_prime, operator_class, declared_side_effects, semantic_justification, predicted_delta_psi, rough_delta_psi) | `analyzers/diag_report.py` | ✅ |
| Part II §1.2 p.23 | `AcceptanceVerdict` (accepted, c1–c4 pass, s_sem, intent_preserved, rejection_feedback) | `analyzers/diag_report.py` | ✅ |
| Part II §1.3 Table 4 p.23–24 | `CFG` singleton (全部字段含默认值) | `analyzers/cfg.py` | ✅ |
| Part II §11 p.49–51 | `CREError` + 全部错误码子类 | `analyzers/errors.py` | ✅ |

---

## Part B：M1 Specification Parsing（Phase 1）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §2.1.1 p.25 | `M1.parse_nl_input` → (SpecS, list[AmbiguityFlag]) | `analyzers/m1.py` | `parse_nl_input()` | `test_m1_contract.py::test_parse_nl_input_*` | ❌ |
| Part II §2.1.2 p.26 | `M1.detect_and_escalate_ambiguities` | `analyzers/m1.py` | `detect_and_escalate_ambiguities()` | `test_m1_contract.py::test_escalate_*` | ❌ |
| Part II §2.1.3 p.26–27 | `M1.run_symbolic_precheck` → list[str] (warning codes) | `analyzers/m1.py` | `run_symbolic_precheck()` | `test_m1_contract.py::test_precheck_*` | ❌ |

---

## Part C：M2 Primary Estimators（Phase 2）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §3.2.1, Eq.(10) p.27–28 | `M2.compute_phi_cr1` (supplementary, Reward-Risk Corr.) | `analyzers/m2.py` | `compute_phi_cr1()` | `test_m2_contract.py::test_phi_cr1_*` | ❌ |
| Part II §3.2.2, Eq.(11) p.28 | `M2.compute_phi_cr2` (**canonical**, Boundary-Seeking) | `analyzers/m2.py` | `compute_phi_cr2()` | `test_m2_contract.py::test_phi_cr2_*` | ❌ |
| Part II §3.3.1, Eq.(12) p.29 | `M2.compute_phi_ec_j` (per-constraint KD-tree coverage) | `analyzers/m2.py` | `compute_phi_ec_j()` | `test_m2_contract.py::test_phi_ec_j_*` | ❌ |
| Part II §3.3.2, Eq.(13) p.30 | `M2.compute_phi_ec_bar` (**canonical**, mean/min aggregation) | `analyzers/m2.py` | `compute_phi_ec_bar()` | `test_m2_contract.py::test_phi_ec_bar_*` | ❌ |
| Part II §3.3.3, Eq.(14) p.30 | `M2.compute_phi_ec2` (supplementary, activation freq.) | `analyzers/m2.py` | `compute_phi_ec2()` | `test_m2_contract.py::test_phi_ec2_*` | ❌ |
| Part II §3.3.4, Eq.(15) p.31 | `M2.compute_phi_ec3` (supplementary, constraint diversity) | `analyzers/m2.py` | `compute_phi_ec3()` | `test_m2_contract.py::test_phi_ec3_*` | ❌ |
| Part II §3.4.1, Eq.(16) p.31 | `M2.compute_phi_er1` (supplementary, deployment utility gap) | `analyzers/m2.py` | `compute_phi_er1()` | `test_m2_contract.py::test_phi_er1_*` | ❌ |
| Part II §3.4.2, Eq.(17) p.32 | `M2.compute_phi_er2` (supplementary, deployment reward gap) | `analyzers/m2.py` | `compute_phi_er2()` | `test_m2_contract.py::test_phi_er2_*` | ❌ |
| Part II §3.4.3, Eq.(18) p.32–33 | `M2.compute_phi_er3` (**canonical**, reward-utility decoupling) | `analyzers/m2.py` | `compute_phi_er3()` | `test_m2_contract.py::test_phi_er3_*` | ❌ |

---

## Part D：M3 Enhanced Estimators（Phase 8，依赖 Isaac Sim）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §4.1.1, Eq.(19) p.33–34 | `M3.compute_kappa_cr` (gradient conflict score) | `analyzers/m3.py` | `compute_kappa_cr()` | `test_m3_contract.py::test_kappa_cr_*` | ❌ |
| Part II §4.1.2, Eq.(20) p.34 | `M3.compute_gamma_ec` (bisimulation soft coverage) | `analyzers/m3.py` | `compute_gamma_ec()` | `test_m3_contract.py::test_gamma_ec_*` | ❌ |
| Part II §4.1.3, Eq.(21) p.34–35 | `M3.compute_delta_er` (gradient drift score) | `analyzers/m3.py` | `compute_delta_er()` | `test_m3_contract.py::test_delta_er_*` | ❌ |

---

## Part E：Stage III Discrepancy Protocol（Phase 8）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §5.1.1, Eq.(22) p.35 | `DP.compute_discrepancy` | `analyzers/discrepancy_protocol.py` | `compute_discrepancy()` | `test_dp_contract.py::test_discrepancy_*` | ❌ |
| Part II §5.1.2 p.36 | `DP.case_a_handler` (LATENT_INCONSISTENCY) | `analyzers/discrepancy_protocol.py` | `case_a_handler()` | `test_dp_contract.py::test_case_a_*` | ❌ |
| Part II §5.1.3 p.36 | `DP.case_b_handler` (CRITIC_QUALITY_WARN) | `analyzers/discrepancy_protocol.py` | `case_b_handler()` | `test_dp_contract.py::test_case_b_*` | ❌ |
| Part II §5.1.4 p.37 | `DP.run_protocol` (main entry) | `analyzers/discrepancy_protocol.py` | `run_protocol()` | `test_dp_contract.py::test_run_*` | ❌ |

---

## Part F：M5 Composite Scoring（Phase 3）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §6.1.1, Eq.(27) p.38 | `M5.monotone_transform f(·)` | `analyzers/m5.py` | `monotone_transform()` | `test_m5_contract.py::test_f_*` | ❌ |
| Part II §6.1.2, Eq.(26) p.38 | `M5.compute_psi_cre` (3-dim, w_cr+w_ec+w_er=1) | `analyzers/m5.py` | `compute_psi_cre()` | `test_m5_contract.py::test_psi_cre_*` | ❌ |
| Part II §6.1.3, Eq.(28) p.39 | `M5.compute_bootstrap_ci` (BCa, B=1000) | `analyzers/m5.py` | `compute_bootstrap_ci()` | `test_m5_contract.py::test_bootstrap_*` | ❌ |
| Part II §6.1.4 p.40 | `M5.calibrate_thresholds` (τ_detect, τ_alarm) | `analyzers/m5.py` | `calibrate_thresholds()` | `test_m5_contract.py::test_thresholds_*` | ❌ |

---

## Part G：M4 Semantic Analysis（Phase 4）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §7.1.1 p.41 | `M4.generate_failure_hypothesis` → (str, list[str]) | `analyzers/m4.py` | `generate_failure_hypothesis()` | `test_m4_contract.py::test_hypothesis_*` | ❌ |

---

## Part H：M7 Repair Generation（Phase 5）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §8.1.1, Eq.(29) p.42 | `M7.compute_spec_edit_distance` (d_spec) | `repair/m7.py` | `compute_spec_edit_distance()` | `test_m7_contract.py::test_edit_dist_*` | ❌ |
| Part II §8.1.2 p.42–43 | `M7.generate_repair_proposals` (K'=2K candidates) | `repair/m7.py` | `generate_repair_proposals()` | `test_m7_contract.py::test_proposals_*` | ❌ |
| Part II §8.1.3 p.43 | `M7.filter_by_minimality` (d_spec ≤ η_edit) | `repair/m7.py` | `filter_by_minimality()` | `test_m7_contract.py::test_minimality_*` | ❌ |
| Part II §8.1.4 p.43–44 | `M7.rank_proposals` (Stage1: rollout, Stage2: predicted_delta_psi) | `repair/m7.py` | `rank_proposals()` | `test_m7_contract.py::test_rank_*` | ❌ |

---

## Part I：M8 Acceptance and Validation（Phase 6）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §9.1.1, Eq.(30) p.45 | `M8.evaluate_acceptance_criteria` (C1–C4) | `repair/m8.py` | `evaluate_acceptance_criteria()` | `test_m8_contract.py::test_criteria_*` | ❌ |
| Part II §9.1.2 p.46 | `M8.verify_semantic_consistency` (s_sem ≥ 0.80) | `repair/m8.py` | `verify_semantic_consistency()` | `test_m8_contract.py::test_semantic_*` | ❌ |
| Part II §9.1.3 p.46–47 | `M8.run_acceptance_loop` (N_max=5, HARD_REJECT) | `repair/m8.py` | `run_acceptance_loop()` | `test_m8_contract.py::test_loop_*` | ❌ |

---

## Part J：Pipeline Orchestrator（Phase 7）

| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
|---------|-----------|---------|---------|---------|------|
| Part II §10.1.1 p.48 | `PO.run_cre_pipeline` (M1→M2→M3→[DP]→M5→M4→[loop:M7→M8]) | `pipeline/orchestrator.py` | `run_cre_pipeline()` | `test_pipeline_e2e.py::test_full_*` | ❌ |
| Part II §10.1.2 p.49 | `PO.audit_trail_schema` | `pipeline/orchestrator.py` | `AuditTrail` class | `test_pipeline_e2e.py::test_audit_*` | ❌ |

---

## Part K：旧版实现追溯（历史，对齐 v1.0 之前）

> 以下为历史实现（现已移入 legacy/），记录其与 PDF 的对应关系和已知偏差，供参考。

| 旧版函数 | 旧版文件 | PDF 对应 | 已知偏差 |
|---------|---------|---------|---------|
| `run_static_analysis()` | `analyzers/legacy/static_analyzer.py` | M1 §2.3 symbolic precheck（部分） | 仅做 token 近似，未实现 M2 轨迹估计 |
| `run_dynamic_analysis()` | `analyzers/legacy/dynamic_analyzer.py` | M2 §3（部分行为估计） | 未实现 φ²_CR/φ̄¹_EC/φ³_ER 正确公式 |
| `run_semantic_analysis()` | `analyzers/legacy/semantic_analyzer.py` | M4+M5（严重偏差） | φ²_CR/φ̄¹_EC 用 issue 计数替代，Ψ_CRE 只有 2 维 |
| `generate_report()` | `analyzers/legacy/report_generator.py` | DiagReport（结构不符） | 无 spec_id、failure_hypothesis、ci_95 等字段 |
| `generate_repair()` | `repair/legacy/repair_generator.py` | M7（严重简化） | 无候选集、无 d_spec、无排名 |
| `validate_repair()` | `repair/legacy/validator.py` | M8（严重简化） | 只比较 issue 数，缺 C1–C4、N_max 循环 |
