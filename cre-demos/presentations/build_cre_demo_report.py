#!/usr/bin/env python3
"""Generate the detailed Chinese HTML deck for the three CRE demos."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESENTATION_DIR = Path(__file__).resolve().parent


SNAPSHOT = {
    "demo1": {
        "title": "Demo 1 · C-R 边界诱导",
        "subtitle": "同一几何中，仅改变 reward 偏置，就会把策略推向危险近路。",
        "claim_type": "C-R",
        "claim_sentence": "环境固定、seed 固定、训练预算固定，只有 reward 平衡被动了手脚。",
        "root_cause": "Reward-boundary coupling is elevated.",
        "repair_operator": "strengthen_safety_reward",
        "validation": "accepted",
        "scene_label": "双通道场景：内侧通道更短但危险，外侧通道更长但更安全。",
        "takeaway": "Injected 版本拿到了更高回报，但它并不是学到了更好的策略，而是学到了更冒险的捷径偏好。",
        "metrics": {
            "clean": {
                "W_CR": 0.010271858923982921,
                "W_EC": 0.0777777777777778,
                "W_ER": 0.0,
                "average_return": 17.65626103410395,
                "success_rate": 1.0,
                "collision_rate": 0.0,
                "min_distance": 0.3684707313442594,
                "near_violation_ratio": 0.05555555555555555,
                "risky_route_rate": 0.0,
                "safe_route_rate": 1.0,
            },
            "injected": {
                "W_CR": 0.7180302016989564,
                "W_EC": 0.0777777777777778,
                "W_ER": 0.0,
                "average_return": 20.33273671259478,
                "success_rate": 0.6666666666666666,
                "collision_rate": 0.3333333333333333,
                "min_distance": 0.0672684745200607,
                "near_violation_ratio": 0.5787037037037037,
                "risky_route_rate": 1.0,
                "safe_route_rate": 0.0,
            },
            "repaired": {
                "W_CR": 0.011751475952220041,
                "W_EC": 0.0777777777777778,
                "W_ER": 0.0,
                "average_return": 21.238089886563397,
                "success_rate": 1.0,
                "collision_rate": 0.0,
                "min_distance": 0.36444209453100185,
                "near_violation_ratio": 0.05555555555555555,
                "risky_route_rate": 0.0,
                "safe_route_rate": 1.0,
            },
        },
        "assets": {
            "scene": "cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_scene_topdown.svg",
            "overlay": "cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_trajectory_overlay.svg",
            "metrics": "cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_metric_board.svg",
            "replay": "cre-demos/demo1_cr_boundary_lure/assets/videos/demo1_replay.html",
        },
        "artifacts": {
            "verification": "cre-demos/demo1_cr_boundary_lure/reports/latest/verification/verification_summary.json",
            "report": "cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/report.json",
            "repair": "cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_plan.json",
            "validation": "cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_decision.json",
            "readme": "cre-demos/demo1_cr_boundary_lure/README.md",
        },
    },
    "demo2": {
        "title": "Demo 2 · E-C 隐藏楔形",
        "subtitle": "reward 完全冻结，但训练集漏掉关键危险几何后，policy 在 critical family 明显掉穿。",
        "claim_type": "E-C",
        "claim_sentence": "只改变训练场景覆盖率，不改变 reward、policy 和预算。",
        "root_cause": "Critical-state coverage appears weak.",
        "repair_operator": "increase_critical_route_bias",
        "validation": "accepted",
        "scene_label": "训练集以宽通道和开阔样本为主，评估时再引入盲拐角与隐藏危险楔形。",
        "takeaway": "Injected 版本在 nominal 回放里看起来还过得去，但一旦切到 boundary-critical family，成功率和安全性同步塌缩。",
        "metrics": {
            "clean": {
                "W_CR": 0.010482751081490473,
                "W_EC": 0.08725490196078434,
                "W_ER": 0.0,
                "critical_success_rate": 0.75,
                "boundary_critical_vs_nominal_success_gap": 0.25,
                "nominal_success_rate": 1.0,
                "critical_collision_rate": 0.0,
                "critical_region_failure_rate": 0.0,
            },
            "injected": {
                "W_CR": 0.0,
                "W_EC": 0.5,
                "W_ER": 0.0,
                "critical_success_rate": 0.16666666666666666,
                "boundary_critical_vs_nominal_success_gap": 0.75,
                "nominal_success_rate": 0.9166666666666666,
                "critical_collision_rate": 0.4166666666666667,
                "critical_region_failure_rate": 0.7142857142857143,
            },
            "repaired": {
                "W_CR": 0.013215679805010509,
                "W_EC": 0.08725490196078434,
                "W_ER": 0.0,
                "critical_success_rate": 0.6666666666666666,
                "boundary_critical_vs_nominal_success_gap": 0.33333333333333337,
                "nominal_success_rate": 1.0,
                "critical_collision_rate": 0.0,
                "critical_region_failure_rate": 0.0,
            },
        },
        "assets": {
            "scene": "cre-demos/demo2_ec_hidden_wedge/assets/screenshots/demo2_scene_compare.svg",
            "coverage": "cre-demos/demo2_ec_hidden_wedge/assets/screenshots/demo2_training_coverage_map.svg",
            "overlay": "cre-demos/demo2_ec_hidden_wedge/assets/screenshots/demo2_critical_overlay.svg",
            "nominal_overlay": "cre-demos/demo2_ec_hidden_wedge/assets/screenshots/demo2_nominal_overlay.svg",
            "metrics": "cre-demos/demo2_ec_hidden_wedge/assets/screenshots/demo2_gap_metric_board.svg",
            "summary": "cre-demos/demo2_ec_hidden_wedge/assets/screenshots/demo2_summary_card.svg",
            "nominal_replay": "cre-demos/demo2_ec_hidden_wedge/assets/videos/demo2_nominal_replay.html",
            "critical_replay": "cre-demos/demo2_ec_hidden_wedge/assets/videos/demo2_critical_replay.html",
        },
        "artifacts": {
            "verification": "cre-demos/demo2_ec_hidden_wedge/reports/latest/verification/verification_summary.json",
            "report": "cre-demos/demo2_ec_hidden_wedge/reports/latest/injected/analysis/report/demo2_injected_report/report.json",
            "repair": "cre-demos/demo2_ec_hidden_wedge/reports/latest/injected/analysis/repair/demo2_injected_repair/repair_plan.json",
            "validation": "cre-demos/demo2_ec_hidden_wedge/reports/latest/analysis/validation/demo2_validation/validation_decision.json",
            "readme": "cre-demos/demo2_ec_hidden_wedge/README.md",
        },
    },
    "demo3": {
        "title": "Demo 3 · E-R 位移门洞",
        "subtitle": "环境 shift 后，reward 仍然看起来像回事，但真实任务效用已经明显掉穿。",
        "claim_type": "E-R",
        "claim_sentence": "nominal 训练与 reward 定义完全冻结，只让评估环境发生轻中度 shift。",
        "root_cause": "Reward stays deceptively decent under shift while task utility collapses.",
        "repair_operator": "increase_shifted_boundary_bias",
        "validation": "accepted",
        "scene_label": "居中门洞在 nominal 中很顺手，shifted 版本把门洞侧移并收窄 squeeze zone。",
        "takeaway": "Injected 版本保住了 93.2% 的 reward retention，却只保住了 24.4% 的 utility retention，这是 E-R 问题的最强证据。",
        "metrics": {
            "clean": {
                "W_CR": 0.0,
                "W_EC": 0.4333333333333334,
                "W_ER": 0.4347044888743997,
                "reward_retention_under_shift": 0.6910171811439413,
                "utility_retention_under_shift": 0.7550374701765069,
                "reward_utility_decoupling_gap": -0.06402028903256562,
                "shifted_success_rate": 0.8333333333333334,
                "nominal_success_rate": 1.0,
            },
            "injected": {
                "W_CR": 0.0,
                "W_EC": 0.4333333333333334,
                "W_ER": 0.5741221531175901,
                "reward_retention_under_shift": 0.9316550729762786,
                "utility_retention_under_shift": 0.24372122402271734,
                "reward_utility_decoupling_gap": 0.6879338489535612,
                "shifted_success_rate": 0.3333333333333333,
                "nominal_success_rate": 1.0,
            },
            "repaired": {
                "W_CR": 0.0,
                "W_EC": 0.4333333333333334,
                "W_ER": 0.3678858055843942,
                "reward_retention_under_shift": 0.9673757206114503,
                "utility_retention_under_shift": 0.7854580280553534,
                "reward_utility_decoupling_gap": 0.1819176925560969,
                "shifted_success_rate": 0.8333333333333334,
                "nominal_success_rate": 1.0,
            },
        },
        "assets": {
            "scene": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_scene_compare.svg",
            "inset": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_gate_offset_inset.svg",
            "same_seed": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_same_seed_overlay.svg",
            "scatter": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_reward_utility_scatter.svg",
            "bars": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_reward_utility_bars.svg",
            "quality": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_quality_metrics.svg",
            "recovery": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_repair_recovery_board.svg",
            "summary": "cre-demos/demo3_er_shifted_gate/assets/screenshots/demo3_summary_card.svg",
            "nominal_replay": "cre-demos/demo3_er_shifted_gate/assets/videos/demo3_nominal_success.html",
            "shifted_replay": "cre-demos/demo3_er_shifted_gate/assets/videos/demo3_injected_shifted_failure.html",
            "repaired_replay": "cre-demos/demo3_er_shifted_gate/assets/videos/demo3_repaired_shifted_recovery.html",
            "triplet_replay": "cre-demos/demo3_er_shifted_gate/assets/videos/demo3_triplet_split_screen.html",
        },
        "artifacts": {
            "verification": "cre-demos/demo3_er_shifted_gate/reports/latest/verification/verification_summary.json",
            "report": "cre-demos/demo3_er_shifted_gate/reports/latest/injected/analysis/report/demo3_injected_report/report.json",
            "repair": "cre-demos/demo3_er_shifted_gate/reports/latest/injected/analysis/repair/demo3_injected_repair/repair_plan.json",
            "validation": "cre-demos/demo3_er_shifted_gate/reports/latest/analysis/validation/demo3_validation/validation_decision.json",
            "readme": "cre-demos/demo3_er_shifted_gate/README.md",
        },
    },
}


SLIDE_NOTES = [
    {
        "title": "总览：为什么要用三个 Demo 讲同一套 CRE 方法",
        "duration": "1 分钟",
        "script": [
            "这一页先给汇报结论。我们不是拿三个彼此孤立的小例子来凑数，而是用三个受控实验把 CRE 的三类典型根因分别钉住：C-R 讲 reward 设计如何诱导危险行为，E-C 讲环境覆盖不足如何造成 critical family 失守，E-R 讲环境 shift 下 reward 与真实任务效用如何脱钩。三组实验都遵守同一套 Clean、Injected、Repaired 三联结构，所以可以横向比较，也可以顺着同一条证据链往下讲。",
            "第二个要点是，这三个 Demo 的角色分工非常明确。Demo 1 说明不能把高回报直接当成好策略；Demo 2 说明 nominal 看着能飞，不代表训练覆盖到真正关键的约束场景；Demo 3 说明 deployment shift 下，reward proxy 和任务 utility 不是一回事。三者合起来，正好把 CRE 的诊断、修复和验证闭环补齐。",
        ],
        "transition": "接下来先把三组实验为什么可比讲清楚，再分别展开每个 Demo 的设计与结果。",
    },
    {
        "title": "方法：三组实验共享的控制变量和证据链",
        "duration": "1 分钟",
        "script": [
            "为了让结论具有说服力，我们给三组 Demo 统一了实验语法。每一组都只有一个主导因子可以变化，并且都输出同一套 machine-readable evidence：verification summary、root-cause report、repair plan 和 validation decision。这样汇报时不是靠口头解释说服别人，而是每一步都有结构化证据可回查。",
            "另外，三组 witness 其实分别回答不同问题。W_CR 问的是 reward 有没有把策略往危险边界拉；W_EC 问的是训练环境有没有把关键危险区域覆盖进去；W_ER 问的是 reward proxy 在环境 shift 下还能不能代表真实任务效用。把这三个问题拆开，才能避免误诊断。",
        ],
        "transition": "有了共同实验语法之后，我们就可以先横向给结论，再回到每个 Demo 的局部细节。",
    },
    {
        "title": "横向矩阵：三类 failure 现象相似，但根因与修法完全不同",
        "duration": "1 分钟",
        "script": [
            "这一页建议当作听众的导航页。表格里最重要的是三列：被隔离的单一变量、主导 witness、以及 repair 怎么做。Demo 1 只改 reward，所以修法也应该回到 reward 侧；Demo 2 是训练覆盖问题，所以修法必须补 critical family；Demo 3 是 utility 解耦问题，所以修法要把 shifted robustness 拉回来，而不是一味继续堆 reward。",
            "横向看数字也能发现规律。Injected 版本的 witness 都明显升高，但它们恶化的方式不同：Demo 1 是 risky route rate 直接拉满，Demo 2 是 nominal 还能飞但 critical gap 撕开，Demo 3 则是 reward retention 还高、utility retention 却掉穿。正是这种模式差异，让 CRE 的分类诊断有意义。",
        ],
        "transition": "下面先看 Demo 1，它回答的是 reward 本身会不会把策略诱导到危险边界上。",
    },
    {
        "title": "Demo 1 设计：只改 reward，不改场景",
        "duration": "1 分钟",
        "script": [
            "Demo 1 的设计重点是把环境完全固定住。图里可以看到同一个起点、终点和双通道布局，其中内侧通道更短但净空更小，外侧通道更长但更安全。我们要求三组版本的几何、seed 和训练预算都不变，只允许 reward 平衡改变，这样一旦轨迹选择发生系统性转移，就可以把根因指向 reward 设计，而不是别的因素。",
            "另一张轨迹图是这个实验最直观的证据。健康策略会更多选择外侧安全通道；Injected 版本则开始贴着内侧边界飞，说明它被 progress-style reward 推向了短而险的捷径。这里真正想说明的是偏好发生了结构性变化，而不是单次偶然失误。",
        ],
        "transition": "设计讲清楚之后，我们就看结果页，重点看 injected 为什么不是简单地变差，而是变得更危险。",
    },
    {
        "title": "Demo 1 结果：回报更高，但安全裕度和路线选择同时恶化",
        "duration": "1 分 30 秒",
        "script": [
            "这里要特别强调一个反直觉现象：Injected 版本的 average return 从 17.66 上升到 20.33，看上去像是学得更好了，但 success rate 从 100% 掉到 66.7%，collision rate 从 0 提升到 33.3%，min distance 从 0.368 缩到 0.067。也就是说，回报提高并没有代表真实行为变好，反而是在奖励函数牵引下更频繁地压着危险边界走。",
            "再看结构性指标，risky route rate 从 0 直接拉到 1，near violation ratio 从 5.6% 提高到 57.9%，W_CR 飙到 0.718。Repair 后这些值基本回到 clean 水平，而且 success rate 恢复到 100%。所以这不是策略能力不够，而是 reward 目标和安全意图发生了冲突，修 reward 才是对症下药。",
        ],
        "transition": "第二组 Demo 会把 reward 固定住，说明另一类问题其实来自训练环境覆盖不足。",
    },
    {
        "title": "Demo 2 设计：reward 固定，只让训练覆盖率出问题",
        "duration": "1 分钟",
        "script": [
            "Demo 2 的关键是把 reward 彻底冻结，然后人为制造训练分布偏置。左侧的场景对比图展示了 nominal family 和 boundary-critical family 的几何差异，右侧覆盖热图展示了 injected 训练样本主要堆在宽通道和开阔区域，真正危险的楔形区几乎没被充分访问。",
            "这个实验要证明的不是策略全面变差，而是策略在它熟悉的 nominal family 里还能维持表面可接受的表现，但一旦到了真正考验约束的 critical geometry，问题就暴露出来。所以这里的核心不是 reward 调错了，而是训练集没有把该见的关键场景见全。",
        ],
        "transition": "接下来我们看结果页，重点关注 nominal 和 critical 之间的性能裂口。",
    },
    {
        "title": "Demo 2 结果：nominal 还能飞，但 critical family 明显掉穿",
        "duration": "1 分 30 秒",
        "script": [
            "这一页最关键的证据是 success gap。Injected 版本 nominal success 还有 91.7%，如果只看常规演示回放，很容易误判为模型还算稳定；但 critical success rate 只剩 16.7%，boundary-critical versus nominal success gap 扩大到 0.75，critical collision rate 上升到 41.7%，critical region failure rate 也达到 71.4%。",
            "这组结果非常适合说明 E-C 与 C-R 的区别。这里 reward 没有变化，却依然出现明显失败，说明根因不在 reward。Repair 的方式也因此不同，我们不是去改奖励，而是把 critical route bias 和关键几何重新注回训练流程。修复后 critical success 回到 66.7%，collision 和 region failure 都降回 0，验证结果也被接受。",
        ],
        "transition": "第三组 Demo 会再往前走一步，讨论 deployment shift 下 reward 为什么会和真实任务 utility 脱钩。",
    },
    {
        "title": "Demo 3 设计：只改评估环境，并把 utility 单独冻结出来",
        "duration": "1 分钟",
        "script": [
            "Demo 3 的设计思想是：先把 nominal 训练和 reward 定义全部冻结，然后只在评估侧引入轻中度环境 shift。图里可以看到门洞发生了横向位移，通行区也变窄，但任务并没有被设计成不可能完成。这样做的目的是制造一种最容易误判的情况，也就是 reward 还在给正反馈，可真正的任务效用已经下降。",
            "因此这个 Demo 不是直接拿 reward 当结果，而是额外冻结了一个独立的 utility 聚合指标 U_task_v1，把 success、collision、timeout、clearance 和效率组合进来。只有把 utility 从 reward 里分离出来，我们才能严格证明 E-R 的解耦，而不是把问题重新说成 reward 写错了。",
        ],
        "transition": "有了这个设计前提，下一页的散点图和恢复图就会特别有解释力。",
    },
    {
        "title": "Demo 3 结果：reward 仍然像回事，但 utility 已经掉穿",
        "duration": "1 分 30 秒",
        "script": [
            "这一页建议先讲最打人的数字。Injected 版本的 reward retention under shift 还有 93.2%，如果只看 return，很多人会觉得策略并没有显著退化；但 utility retention under shift 只剩 24.4%，reward-utility decoupling gap 扩大到 0.688，shifted success 也从 83.3% 掉到 33.3%。这说明 reward proxy 已经失去了代表真实任务效果的能力。",
            "Repair 后我们看到的是另一种恢复模式：reward retention 继续保持在 96.7%，utility retention 回升到 78.5%，decoupling gap 收窄到 0.182，shifted success 恢复到 83.3%。这组结果特别适合作为 E-R 的展示，因为它不是简单地让所有指标一起好转，而是准确地缩小了 reward 和 utility 之间的裂口。",
        ],
        "transition": "看完三组局部细节之后，我们回到横向层面总结怎么区分这三类问题。",
    },
    {
        "title": "交叉对比：不要把三类问题混成同一种“飞得不好”",
        "duration": "1 分钟",
        "script": [
            "这一页的目的，是帮助听众把表面相似的失败现象重新拆开。三组 Demo 都可能出现碰撞、贴边、成功率下降，但诊断逻辑不一样。若危险捷径偏好在固定几何下被稳定放大，就是 C-R；若 nominal 还能过、critical 明显掉穿，就是 E-C；若 reward 看着还行但 utility 掉穿，就是 E-R。",
            "更重要的是修法映射。C-R 应该从 reward 或 safety penalty 下手，E-C 要补训练覆盖，E-R 则要增强 shifted robustness 和 utility 对齐。只有把现象、witness 和 repair 对上，CRE 的修复流程才不会流于经验主义。",
        ],
        "transition": "最后两页我会把这份汇报依赖的支撑材料和推荐收束结论一起给出来。",
    },
    {
        "title": "支撑材料：汇报时每一页都能回到具体证据文件",
        "duration": "1 分钟",
        "script": [
            "这一页主要用来回答一个常见问题：这些图是不是只适合演示，不适合复核？答案是否定的。每个 Demo 我们都保留了截图、回放、verification summary、root-cause report、repair plan 和 validation decision，所以汇报里的每一个判断都能落回机器可读文件。",
            "汇报时可以根据对象灵活切换证据粒度。面对管理或评审，可以停留在图和关键指标层；面对研发同学，可以直接跳到对应 README、JSON 或 replay 页面，验证 witness、repair operator 和 validation status 是否真的闭环一致。",
        ],
        "transition": "最后一页我会把三组 Demo 串成一句完整的汇报结论，并给出下一步建议。",
    },
    {
        "title": "结论：三组 Demo 已经把 CRE 的诊断、修复、验证故事讲闭环",
        "duration": "1 分钟",
        "script": [
            "如果只用一句话总结这份汇报，那就是：我们已经用三组受控实验把 CRE 的三类核心 failure mechanism 分别钉住，并且每一组都完成了 Injected、Repair、Validation 的闭环。它们共同说明，RL 系统失效不能只看 reward 或单次回放，而必须回到 witness、根因和修复证据链去判断。",
            "接下来的工作也很自然。对外汇报时，可以用这套 deck 做统一叙事；对内工程推进时，可以把这三组 Demo 当作回归基线，持续检查 reward 侧、coverage 侧和 shift robustness 侧是否再次出现已知问题。这样这份材料就不仅是一次展示，也是一套可复用的审计模板。",
        ],
        "transition": "汇报结束后，可以根据提问深度回跳到任意 Demo 页，或者直接打开对应 artifact 做现场追溯。",
    },
]


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def fmt_float(value: float) -> str:
    return f"{value:.3f}"


def load_svg(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        return (
            '<div class="figure-missing">'
            f"<strong>素材缺失</strong><span>{html.escape(relative_path)}</span>"
            "</div>"
        )
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<\?xml[^>]*>\s*", "", text, count=1)
    text = re.sub(r"<!DOCTYPE[^>]*>\s*", "", text, count=1, flags=re.IGNORECASE)
    return text.strip()


def rel_link(relative_path: str) -> str:
    return ("../" + Path(relative_path).relative_to("cre-demos").as_posix())


def figure_card(title: str, relative_path: str, caption: str) -> str:
    return dedent(
        f"""
        <figure class="figure-card">
          <figcaption>
            <span class="figure-title">{html.escape(title)}</span>
            <span class="figure-caption">{html.escape(caption)}</span>
          </figcaption>
          <div class="figure-art">
            {load_svg(relative_path)}
          </div>
        </figure>
        """
    ).strip()


def stat_chip(label: str, value: str, tone: str = "neutral") -> str:
    return (
        f'<div class="stat-chip tone-{tone}">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        "</div>"
    )


def witness_card(title: str, witness: str, statement: str, operator_type: str) -> str:
    return dedent(
        f"""
        <article class="demo-card">
          <div class="demo-card-head">
            <span class="claim-pill">{html.escape(witness)}</span>
            <span class="validation-pill">validation: accepted</span>
          </div>
          <h3>{html.escape(title)}</h3>
          <p>{html.escape(statement)}</p>
          <div class="demo-card-foot">
            <span>root cause: {html.escape(witness)}</span>
            <span>repair: {html.escape(operator_type)}</span>
          </div>
        </article>
        """
    ).strip()


def table_row(cells: list[str], header: bool = False) -> str:
    tag = "th" if header else "td"
    return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"


def evidence_links(items: list[tuple[str, str]]) -> str:
    links = []
    for label, relative_path in items:
        href = html.escape(rel_link(relative_path))
        links.append(f'<a href="{href}" target="_blank" rel="noreferrer">{html.escape(label)}</a>')
    return '<div class="evidence-links">' + "".join(links) + "</div>"


def build_slide_1() -> str:
    d1 = SNAPSHOT["demo1"]
    d2 = SNAPSHOT["demo2"]
    d3 = SNAPSHOT["demo3"]
    return dedent(
        f"""
        <section class="slide" data-title="总览">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">overview</span>
              <h2>CRE 三个核心 Demo 的实验结果汇报</h2>
              <p class="slide-lead">用三组受控实验，把 <strong>C-R</strong>、<strong>E-C</strong>、<strong>E-R</strong> 三类根因与对应修法拆开说明。</p>
            </div>
            <div class="headline-chip">结构化证据驱动汇报</div>
          </div>
          <div class="hero-grid">
            <div class="hero-main">
              <div class="story-band">
                <div class="story-step"><span>01</span><strong>Clean</strong><p>健康对照组，冻结共同基线。</p></div>
                <div class="story-step"><span>02</span><strong>Injected</strong><p>只放大一个因子，让 witness 有明确指向。</p></div>
                <div class="story-step"><span>03</span><strong>Repaired</strong><p>按根因修复，再看 validation 是否接受。</p></div>
              </div>
              <div class="hero-claim">
                <h3>汇报主线</h3>
                <p>这三组 Demo 不是分别讲“模型出错”，而是分别讲三种完全不同的<strong>错法</strong>：reward 把策略往危险边界拉、训练覆盖遗漏关键风险几何、以及部署 shift 下 reward 与真实 utility 脱钩。它们共同构成 CRE-v1 最核心的审计故事。</p>
              </div>
              <div class="key-metrics">
                {stat_chip("Demo 1 · Injected W_CR", fmt_float(d1["metrics"]["injected"]["W_CR"]), "red")}
                {stat_chip("Demo 2 · Critical Gap", fmt_float(d2["metrics"]["injected"]["boundary_critical_vs_nominal_success_gap"]), "amber")}
                {stat_chip("Demo 3 · Reward / Utility Gap", fmt_float(d3["metrics"]["injected"]["reward_utility_decoupling_gap"]), "blue")}
              </div>
            </div>
            <div class="hero-side">
              {witness_card(d1["title"], "C-R", "环境不变，只改 reward，就能把策略推向危险近路。", d1["repair_operator"])}
              {witness_card(d2["title"], "E-C", "reward 固定，但 critical geometry 覆盖不足会撕开 nominal / critical 裂口。", d2["repair_operator"])}
              {witness_card(d3["title"], "E-R", "环境 shift 下 reward 仍然像回事，但 utility 已经明显掉穿。", d3["repair_operator"])}
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_2() -> str:
    return dedent(
        """
        <section class="slide" data-title="共享方法">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">method</span>
              <h2>三组实验共享同一套因果隔离与证据链</h2>
              <p class="slide-lead">只有把控制变量、witness 和验证出口统一，三个 Demo 的结果才能拿来横向比较。</p>
            </div>
          </div>
          <div class="two-col method-grid">
            <div class="panel">
              <h3>共同实验契约</h3>
              <div class="timeline">
                <div class="timeline-item"><strong>一因子规则</strong><p>每个 Demo 只允许一个主导因子变化，其余条件冻结。</p></div>
                <div class="timeline-item"><strong>同一三联结构</strong><p>统一采用 Clean、Injected、Repaired 三个版本来讲清变化方向。</p></div>
                <div class="timeline-item"><strong>同一证据面</strong><p>都输出图像、回放、metrics summary、report、repair plan、validation decision。</p></div>
                <div class="timeline-item"><strong>同一判断方式</strong><p>不是凭主观感受下结论，而是让 witness 主导诊断、让 validation 主导收尾。</p></div>
              </div>
            </div>
            <div class="panel">
              <h3>CRE 证据链</h3>
              <div class="pipeline">
                <div class="pipe-box tone-red"><strong>动态证据</strong><span>轨迹、成功率、间隙、安全事件</span></div>
                <div class="pipe-arrow">→</div>
                <div class="pipe-box tone-amber"><strong>语义归纳</strong><span>把现象聚合成 C-R / E-C / E-R 候选 claim</span></div>
                <div class="pipe-arrow">→</div>
                <div class="pipe-box tone-blue"><strong>报告与修复</strong><span>选择主导 witness，生成 repair operator</span></div>
                <div class="pipe-arrow">→</div>
                <div class="pipe-box tone-green"><strong>验证</strong><span>检查修后 witness 是否回落、关键指标是否恢复</span></div>
              </div>
              <div class="witness-strip">
                <div><strong>W_CR</strong><span>reward 是否诱导危险边界行为</span></div>
                <div><strong>W_EC</strong><span>训练覆盖是否漏掉关键风险几何</span></div>
                <div><strong>W_ER</strong><span>环境 shift 下 reward 是否仍能代表 utility</span></div>
              </div>
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_3() -> str:
    d1 = SNAPSHOT["demo1"]
    d2 = SNAPSHOT["demo2"]
    d3 = SNAPSHOT["demo3"]
    rows = [
        ["Demo", "隔离变量", "Injected 最强症状", "主导 witness", "修法", "validation"],
        [
            "Demo 1",
            "reward 平衡",
            f"risky route rate = {fmt_pct(d1['metrics']['injected']['risky_route_rate'])}, min distance = {fmt_float(d1['metrics']['injected']['min_distance'])}",
            f"W_CR = {fmt_float(d1['metrics']['injected']['W_CR'])}",
            d1["repair_operator"],
            d1["validation"],
        ],
        [
            "Demo 2",
            "critical geometry 覆盖率",
            f"critical success = {fmt_pct(d2['metrics']['injected']['critical_success_rate'])}, gap = {fmt_float(d2['metrics']['injected']['boundary_critical_vs_nominal_success_gap'])}",
            f"W_EC = {fmt_float(d2['metrics']['injected']['W_EC'])}",
            d2["repair_operator"],
            d2["validation"],
        ],
        [
            "Demo 3",
            "eval 环境 shift",
            f"reward retention = {fmt_pct(d3['metrics']['injected']['reward_retention_under_shift'])}, utility retention = {fmt_pct(d3['metrics']['injected']['utility_retention_under_shift'])}",
            f"W_ER = {fmt_float(d3['metrics']['injected']['W_ER'])}",
            d3["repair_operator"],
            d3["validation"],
        ],
    ]
    table_html = "<table class='matrix-table'>" + "".join(
        table_row(row, header=index == 0) for index, row in enumerate(rows)
    ) + "</table>"
    return dedent(
        f"""
        <section class="slide" data-title="横向矩阵">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">matrix</span>
              <h2>三个 Demo 的横向结果先给结论，再展开细节</h2>
              <p class="slide-lead">表面上都是“飞得不好”，但三组实验的根因、witness 和 repair operator 其实完全不同。</p>
            </div>
          </div>
          <div class="panel table-panel">
            {table_html}
          </div>
          <div class="three-notes">
            <div class="note-box"><strong>Demo 1</strong><p>Injected 回报更高，但 risky route 直接拉满，所以它不是“性能提升”，而是 reward 诱导。</p></div>
            <div class="note-box"><strong>Demo 2</strong><p>Injected nominal 还能飞，但 critical family 崩掉，所以它不是 reward 设计问题，而是 coverage 问题。</p></div>
            <div class="note-box"><strong>Demo 3</strong><p>Injected reward retention 很高但 utility retention 掉穿，所以它不是简单的“奖励低”，而是 proxy 失真。</p></div>
          </div>
        </section>
        """
    ).strip()


def build_slide_4() -> str:
    demo = SNAPSHOT["demo1"]
    return dedent(
        f"""
        <section class="slide" data-title="Demo 1 设计">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">demo 1 design</span>
              <h2>Demo 1：同一几何里，reward 偏置把策略推向危险近路</h2>
              <p class="slide-lead">{html.escape(demo['scene_label'])}</p>
            </div>
            <div class="headline-chip">claim type: {html.escape(demo['claim_type'])}</div>
          </div>
          <div class="two-col demo-grid">
            <div class="figure-stack">
              {figure_card("俯视场景图", demo["assets"]["scene"], "危险内侧通道与安全外侧通道被刻意摆在同一场景中。")}
              {figure_card("轨迹叠加图", demo["assets"]["overlay"], "看路径偏好是否从安全外侧系统性迁移到危险内侧。")}
            </div>
            <div class="panel">
              <h3>设计意图</h3>
              <ul class="bullet-list">
                <li>固定几何、固定 seed、固定训练预算，只允许 reward 权重变化。</li>
                <li>Injected 目标不是让策略全面崩掉，而是让它更愿意走短而险的近路。</li>
                <li>只要路径偏好发生系统性转移，就能把根因指向 reward-boundary coupling。</li>
              </ul>
              <div class="mini-metrics">
                {stat_chip("Clean safe route", fmt_pct(demo["metrics"]["clean"]["safe_route_rate"]), "green")}
                {stat_chip("Injected risky route", fmt_pct(demo["metrics"]["injected"]["risky_route_rate"]), "red")}
                {stat_chip("Repair target", "回到安全通道", "blue")}
              </div>
              <div class="callout">
                <strong>因果链</strong>
                <p>progress 偏置增强 → 策略更偏向内侧窄通道 → min distance 降低、near violation 升高 → W_CR 成为主 witness。</p>
              </div>
              {evidence_links([
                  ("Demo 1 README", demo["artifacts"]["readme"]),
                  ("Replay", demo["assets"]["replay"]),
                  ("Verification", demo["artifacts"]["verification"]),
              ])}
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_5() -> str:
    demo = SNAPSHOT["demo1"]
    rows = [
        ["版本", "Avg Return", "Success", "Collision", "Min Distance", "Near Violation", "W_CR"],
        [
            "Clean",
            fmt_float(demo["metrics"]["clean"]["average_return"]),
            fmt_pct(demo["metrics"]["clean"]["success_rate"]),
            fmt_pct(demo["metrics"]["clean"]["collision_rate"]),
            fmt_float(demo["metrics"]["clean"]["min_distance"]),
            fmt_pct(demo["metrics"]["clean"]["near_violation_ratio"]),
            fmt_float(demo["metrics"]["clean"]["W_CR"]),
        ],
        [
            "Injected",
            fmt_float(demo["metrics"]["injected"]["average_return"]),
            fmt_pct(demo["metrics"]["injected"]["success_rate"]),
            fmt_pct(demo["metrics"]["injected"]["collision_rate"]),
            fmt_float(demo["metrics"]["injected"]["min_distance"]),
            fmt_pct(demo["metrics"]["injected"]["near_violation_ratio"]),
            fmt_float(demo["metrics"]["injected"]["W_CR"]),
        ],
        [
            "Repaired",
            fmt_float(demo["metrics"]["repaired"]["average_return"]),
            fmt_pct(demo["metrics"]["repaired"]["success_rate"]),
            fmt_pct(demo["metrics"]["repaired"]["collision_rate"]),
            fmt_float(demo["metrics"]["repaired"]["min_distance"]),
            fmt_pct(demo["metrics"]["repaired"]["near_violation_ratio"]),
            fmt_float(demo["metrics"]["repaired"]["W_CR"]),
        ],
    ]
    table_html = "<table class='metric-table'>" + "".join(
        table_row(row, header=index == 0) for index, row in enumerate(rows)
    ) + "</table>"
    return dedent(
        f"""
        <section class="slide" data-title="Demo 1 结果">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">demo 1 results</span>
              <h2>Injected 回报更高，但安全裕度和路线选择同时恶化</h2>
              <p class="slide-lead">{html.escape(demo['takeaway'])}</p>
            </div>
          </div>
          <div class="two-col result-grid">
            <div class="figure-stack">
              {figure_card("Demo 1 指标板", demo["assets"]["metrics"], "同一组种子下，Injected 的回报更高，但安全相关指标整体恶化。")}
            </div>
            <div class="panel">
              {table_html}
              <div class="result-claim">
                <div class="claim-card tone-red">
                  <strong>为什么这不是“模型变强”</strong>
                  <p>Injected 的 average return 提升到了 {fmt_float(demo["metrics"]["injected"]["average_return"])}，但 success 降到 {fmt_pct(demo["metrics"]["injected"]["success_rate"])}，collision 升到 {fmt_pct(demo["metrics"]["injected"]["collision_rate"])}。</p>
                </div>
                <div class="claim-card tone-green">
                  <strong>为什么修复有效</strong>
                  <p>Repaired 把 success 拉回 {fmt_pct(demo["metrics"]["repaired"]["success_rate"])}，同时把 W_CR 压回 {fmt_float(demo["metrics"]["repaired"]["W_CR"])}，说明修复方向对准了 reward 侧根因。</p>
                </div>
              </div>
              {evidence_links([
                  ("Injected report", demo["artifacts"]["report"]),
                  ("Repair plan", demo["artifacts"]["repair"]),
                  ("Validation", demo["artifacts"]["validation"]),
              ])}
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_6() -> str:
    demo = SNAPSHOT["demo2"]
    return dedent(
        f"""
        <section class="slide" data-title="Demo 2 设计">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">demo 2 design</span>
              <h2>Demo 2：训练集没有把真正危险的几何见全</h2>
              <p class="slide-lead">{html.escape(demo['scene_label'])}</p>
            </div>
            <div class="headline-chip">claim type: {html.escape(demo['claim_type'])}</div>
          </div>
          <div class="two-col demo-grid">
            <div class="figure-stack">
              {figure_card("场景对比图", demo["assets"]["scene"], "nominal family 更开阔，critical family 明确引入盲拐角与楔形危险区。")}
              {figure_card("训练覆盖热图", demo["assets"]["coverage"], "Injected 训练样本主要覆盖宽通道区域，关键风险几何覆盖偏弱。")}
            </div>
            <div class="panel">
              <h3>设计意图</h3>
              <ul class="bullet-list">
                <li>reward、policy 和训练预算全部冻结，只改变训练场景采样分布。</li>
                <li>Injected 的目标是让 nominal family 看起来仍然“还能飞”，但 critical family 大幅掉点。</li>
                <li>如果 nominal 与 critical 一起全面崩掉，这个 Demo 就失去 E-C 的解释力。</li>
              </ul>
              <div class="mini-metrics">
                {stat_chip("Clean nominal success", fmt_pct(demo["metrics"]["clean"]["nominal_success_rate"]), "green")}
                {stat_chip("Injected critical success", fmt_pct(demo["metrics"]["injected"]["critical_success_rate"]), "amber")}
                {stat_chip("Injected W_EC", fmt_float(demo["metrics"]["injected"]["W_EC"]), "red")}
              </div>
              <div class="callout">
                <strong>因果链</strong>
                <p>critical template 覆盖率下降 → 训练中很少进入真正危险的边界关键区 → nominal 表面仍可接受，但 boundary-critical family 失守 → W_EC 主导诊断。</p>
              </div>
              {evidence_links([
                  ("Demo 2 README", demo["artifacts"]["readme"]),
                  ("Nominal replay", demo["assets"]["nominal_replay"]),
                  ("Critical replay", demo["assets"]["critical_replay"]),
              ])}
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_7() -> str:
    demo = SNAPSHOT["demo2"]
    rows = [
        ["版本", "Nominal Success", "Critical Success", "Gap", "Critical Collision", "Critical Region Failure", "W_EC"],
        [
            "Clean",
            fmt_pct(demo["metrics"]["clean"]["nominal_success_rate"]),
            fmt_pct(demo["metrics"]["clean"]["critical_success_rate"]),
            fmt_float(demo["metrics"]["clean"]["boundary_critical_vs_nominal_success_gap"]),
            fmt_pct(demo["metrics"]["clean"]["critical_collision_rate"]),
            fmt_pct(demo["metrics"]["clean"]["critical_region_failure_rate"]),
            fmt_float(demo["metrics"]["clean"]["W_EC"]),
        ],
        [
            "Injected",
            fmt_pct(demo["metrics"]["injected"]["nominal_success_rate"]),
            fmt_pct(demo["metrics"]["injected"]["critical_success_rate"]),
            fmt_float(demo["metrics"]["injected"]["boundary_critical_vs_nominal_success_gap"]),
            fmt_pct(demo["metrics"]["injected"]["critical_collision_rate"]),
            fmt_pct(demo["metrics"]["injected"]["critical_region_failure_rate"]),
            fmt_float(demo["metrics"]["injected"]["W_EC"]),
        ],
        [
            "Repaired",
            fmt_pct(demo["metrics"]["repaired"]["nominal_success_rate"]),
            fmt_pct(demo["metrics"]["repaired"]["critical_success_rate"]),
            fmt_float(demo["metrics"]["repaired"]["boundary_critical_vs_nominal_success_gap"]),
            fmt_pct(demo["metrics"]["repaired"]["critical_collision_rate"]),
            fmt_pct(demo["metrics"]["repaired"]["critical_region_failure_rate"]),
            fmt_float(demo["metrics"]["repaired"]["W_EC"]),
        ],
    ]
    table_html = "<table class='metric-table'>" + "".join(
        table_row(row, header=index == 0) for index, row in enumerate(rows)
    ) + "</table>"
    return dedent(
        f"""
        <section class="slide" data-title="Demo 2 结果">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">demo 2 results</span>
              <h2>Nominal 还能飞，但 boundary-critical family 明显掉穿</h2>
              <p class="slide-lead">{html.escape(demo['takeaway'])}</p>
            </div>
          </div>
          <div class="three-col demo2-results-grid">
            <div class="figure-stack compact">
              {figure_card("Critical 轨迹叠加", demo["assets"]["overlay"], "关键危险区附近的轨迹偏差与失败模式更容易被看出来。")}
            </div>
            <div class="figure-stack compact">
              {figure_card("Gap 指标板", demo["assets"]["metrics"], "Injected 版本的 nominal / critical 裂口明显扩大。")}
            </div>
            <div class="figure-stack compact">
              {figure_card("Summary Card", demo["assets"]["summary"], "把 witness、gap 和修后恢复状态收拢到同一张卡片。")}
            </div>
          </div>
          <div class="two-col lower-grid">
            <div class="panel">
              {table_html}
            </div>
            <div class="panel">
              <div class="claim-card tone-amber">
                <strong>为什么这不是 reward 问题</strong>
                <p>Injected nominal success 还有 {fmt_pct(demo["metrics"]["injected"]["nominal_success_rate"])}，但 critical success 只剩 {fmt_pct(demo["metrics"]["injected"]["critical_success_rate"])}，说明失败不是 reward 全局失效，而是 critical 几何覆盖不足。</p>
              </div>
              <div class="claim-card tone-green">
                <strong>为什么修复是环境侧修复</strong>
                <p>Repair 后 critical collision 和 region failure 都回到 0，gap 从 {fmt_float(demo["metrics"]["injected"]["boundary_critical_vs_nominal_success_gap"])} 收窄到 {fmt_float(demo["metrics"]["repaired"]["boundary_critical_vs_nominal_success_gap"])}，这和补 coverage 的修法完全对齐。</p>
              </div>
              {evidence_links([
                  ("Verification", demo["artifacts"]["verification"]),
                  ("Injected report", demo["artifacts"]["report"]),
                  ("Repair plan", demo["artifacts"]["repair"]),
                  ("Validation", demo["artifacts"]["validation"]),
              ])}
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_8() -> str:
    demo = SNAPSHOT["demo3"]
    return dedent(
        f"""
        <section class="slide" data-title="Demo 3 设计">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">demo 3 design</span>
              <h2>Demo 3：reward 与真实任务效用在环境 shift 下开始脱钩</h2>
              <p class="slide-lead">{html.escape(demo['scene_label'])}</p>
            </div>
            <div class="headline-chip">claim type: {html.escape(demo['claim_type'])}</div>
          </div>
          <div class="two-col demo-grid">
            <div class="figure-stack">
              {figure_card("Nominal / Shifted 场景对比", demo["assets"]["scene"], "几何差异足够明显，但还没有强到让任务必然失败。")}
              <div class="figure-pair">
                {figure_card("门洞位移细节", demo["assets"]["inset"], "把 shift 的变化点可视化出来，避免把 OOD 说得太抽象。")}
                {figure_card("同 seed 轨迹对比", demo["assets"]["same_seed"], "在同一个 seed 上观察 nominal 与 shifted 的偏航与犹豫。")}
              </div>
            </div>
            <div class="panel">
              <h3>设计意图</h3>
              <ul class="bullet-list">
                <li>训练策略和 reward 完全冻结，只在评估侧加入门洞位移与 squeeze-zone 收窄。</li>
                <li>单独冻结 <code>U_task_v1</code>，确保 utility 不是从 reward 派生出来的。</li>
                <li>目标是制造“reward 看起来还行，但真实任务效用已明显下滑”的可解释案例。</li>
              </ul>
              <div class="formula-card">
                <strong>U_task_v1</strong>
                <pre>0.40 * success
- 0.25 * collision
- 0.15 * timeout
+ 0.10 * clearance
+ 0.10 * time efficiency
+ 0.10 * path efficiency</pre>
              </div>
              <div class="callout">
                <strong>因果链</strong>
                <p>轻中度环境 shift → reward 仍能奖励“看起来在推进”的行为 → success / clearance / efficiency 明显恶化 → reward 与 utility 裂口扩大 → W_ER 成为主 witness。</p>
              </div>
              {evidence_links([
                  ("Demo 3 README", demo["artifacts"]["readme"]),
                  ("Nominal replay", demo["assets"]["nominal_replay"]),
                  ("Injected shifted replay", demo["assets"]["shifted_replay"]),
                  ("Triplet replay", demo["assets"]["triplet_replay"]),
              ])}
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_9() -> str:
    demo = SNAPSHOT["demo3"]
    rows = [
        ["版本", "Reward Retention", "Utility Retention", "Decoupling Gap", "Shifted Success", "W_ER"],
        [
            "Clean",
            fmt_pct(demo["metrics"]["clean"]["reward_retention_under_shift"]),
            fmt_pct(demo["metrics"]["clean"]["utility_retention_under_shift"]),
            fmt_float(demo["metrics"]["clean"]["reward_utility_decoupling_gap"]),
            fmt_pct(demo["metrics"]["clean"]["shifted_success_rate"]),
            fmt_float(demo["metrics"]["clean"]["W_ER"]),
        ],
        [
            "Injected",
            fmt_pct(demo["metrics"]["injected"]["reward_retention_under_shift"]),
            fmt_pct(demo["metrics"]["injected"]["utility_retention_under_shift"]),
            fmt_float(demo["metrics"]["injected"]["reward_utility_decoupling_gap"]),
            fmt_pct(demo["metrics"]["injected"]["shifted_success_rate"]),
            fmt_float(demo["metrics"]["injected"]["W_ER"]),
        ],
        [
            "Repaired",
            fmt_pct(demo["metrics"]["repaired"]["reward_retention_under_shift"]),
            fmt_pct(demo["metrics"]["repaired"]["utility_retention_under_shift"]),
            fmt_float(demo["metrics"]["repaired"]["reward_utility_decoupling_gap"]),
            fmt_pct(demo["metrics"]["repaired"]["shifted_success_rate"]),
            fmt_float(demo["metrics"]["repaired"]["W_ER"]),
        ],
    ]
    table_html = "<table class='metric-table'>" + "".join(
        table_row(row, header=index == 0) for index, row in enumerate(rows)
    ) + "</table>"
    return dedent(
        f"""
        <section class="slide" data-title="Demo 3 结果">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">demo 3 results</span>
              <h2>reward 仍然“像回事”，但 utility 已经掉穿</h2>
              <p class="slide-lead">{html.escape(demo['takeaway'])}</p>
            </div>
          </div>
          <div class="three-col demo3-visual-grid">
            <div class="figure-stack compact">
              {figure_card("Reward / Utility 散点图", demo["assets"]["scatter"], "Injected 样本明显滑向高 reward、低 utility 区域。")}
            </div>
            <div class="figure-stack compact">
              {figure_card("Retention 与 Gap 指标", demo["assets"]["bars"], "把 reward retention、utility retention 和 decoupling gap 并列展示。")}
            </div>
            <div class="figure-stack compact">
              {figure_card("修后恢复板", demo["assets"]["recovery"], "修复后最重要的不是继续堆 reward，而是缩小 reward / utility 裂口。")}
            </div>
          </div>
          <div class="two-col lower-grid">
            <div class="panel">
              {table_html}
            </div>
            <div class="panel">
              <div class="claim-card tone-blue">
                <strong>为什么这是 E-R，不是一般泛化失败</strong>
                <p>Injected 仍保住了 {fmt_pct(demo["metrics"]["injected"]["reward_retention_under_shift"])} 的 reward retention，却只保住了 {fmt_pct(demo["metrics"]["injected"]["utility_retention_under_shift"])} 的 utility retention，这正是 proxy 失真而不是 reward 变低。</p>
              </div>
              <div class="claim-card tone-green">
                <strong>为什么修复被接受</strong>
                <p>Repaired 把 decoupling gap 从 {fmt_float(demo["metrics"]["injected"]["reward_utility_decoupling_gap"])} 压到 {fmt_float(demo["metrics"]["repaired"]["reward_utility_decoupling_gap"])}，并把 shifted success 恢复到 {fmt_pct(demo["metrics"]["repaired"]["shifted_success_rate"])}。</p>
              </div>
              {evidence_links([
                  ("Verification", demo["artifacts"]["verification"]),
                  ("Injected report", demo["artifacts"]["report"]),
                  ("Repair plan", demo["artifacts"]["repair"]),
                  ("Validation", demo["artifacts"]["validation"]),
              ])}
            </div>
          </div>
        </section>
        """
    ).strip()


def build_slide_10() -> str:
    d1 = SNAPSHOT["demo1"]
    d2 = SNAPSHOT["demo2"]
    d3 = SNAPSHOT["demo3"]
    return dedent(
        f"""
        <section class="slide" data-title="交叉对比">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">cross compare</span>
              <h2>同样像“飞得不好”，三类问题的根因和修法完全不同</h2>
              <p class="slide-lead">不要把现象相似当成根因一致，CRE 的价值就在于把错法拆开。</p>
            </div>
          </div>
          <div class="three-col compare-grid">
            <div class="panel visual-panel">
              <h3>Demo 1</h3>
              <div class="mini-figure">{load_svg(d1["assets"]["overlay"])}</div>
              <p><strong>识别信号：</strong>固定几何下，危险捷径偏好被系统性放大。</p>
              <p><strong>修法：</strong>{html.escape(d1["repair_operator"])}</p>
            </div>
            <div class="panel visual-panel">
              <h3>Demo 2</h3>
              <div class="mini-figure">{load_svg(d2["assets"]["summary"])}</div>
              <p><strong>识别信号：</strong>nominal 还能飞，critical family 的 success gap 却被撕开。</p>
              <p><strong>修法：</strong>{html.escape(d2["repair_operator"])}</p>
            </div>
            <div class="panel visual-panel">
              <h3>Demo 3</h3>
              <div class="mini-figure">{load_svg(d3["assets"]["summary"])}</div>
              <p><strong>识别信号：</strong>reward 仍高，但 utility retention 掉穿。</p>
              <p><strong>修法：</strong>{html.escape(d3["repair_operator"])}</p>
            </div>
          </div>
          <div class="compare-banner">
            <div><strong>如果你看到：</strong><span>高回报伴随危险捷径偏好</span><em>优先怀疑 C-R</em></div>
            <div><strong>如果你看到：</strong><span>nominal 可接受但 critical 崩塌</span><em>优先怀疑 E-C</em></div>
            <div><strong>如果你看到：</strong><span>reward 还行但 utility 掉穿</span><em>优先怀疑 E-R</em></div>
          </div>
        </section>
        """
    ).strip()


def build_slide_11() -> str:
    d1 = SNAPSHOT["demo1"]
    d2 = SNAPSHOT["demo2"]
    d3 = SNAPSHOT["demo3"]
    demo_entries = []
    for title, demo, visual_path in [
        ("Demo 1", d1, d1["assets"]["metrics"]),
        ("Demo 2", d2, d2["assets"]["summary"]),
        ("Demo 3", d3, d3["assets"]["summary"]),
    ]:
        demo_entries.append(
            dedent(
                f"""
                <article class="artifact-card">
                  <div class="artifact-visual">{load_svg(visual_path)}</div>
                  <div class="artifact-copy">
                    <h3>{html.escape(title)}</h3>
                    <p>README、verification、report、repair、validation 和 replay 都已落在固定路径下，可作为现场追溯入口。</p>
                    <ul class="artifact-list">
                      <li><code>{html.escape(rel_link(demo["artifacts"]["readme"]))}</code></li>
                      <li><code>{html.escape(rel_link(demo["artifacts"]["verification"]))}</code></li>
                      <li><code>{html.escape(rel_link(demo["artifacts"]["report"]))}</code></li>
                      <li><code>{html.escape(rel_link(demo["artifacts"]["repair"]))}</code></li>
                      <li><code>{html.escape(rel_link(demo["artifacts"]["validation"]))}</code></li>
                    </ul>
                  </div>
                </article>
                """
            ).strip()
        )
    return dedent(
        f"""
        <section class="slide" data-title="支撑材料">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">artifacts</span>
              <h2>汇报支撑材料如何组织：每一页都能回到具体实验文件</h2>
              <p class="slide-lead">这份 deck 不是独立的“展示层”，而是通往三组 machine-readable artifact 的导航页。</p>
            </div>
          </div>
          <div class="artifact-grid">
            {''.join(demo_entries)}
          </div>
          <div class="support-bar">
            <div><strong>推荐用法</strong><span>先用本 deck 给结构，再在问答环节按需打开 replay 或 JSON 证据。</span></div>
            <div><strong>本页新增材料</strong><span><code>cre-demos/presentations/cre_three_demo_report.html</code> 与逐页讲稿配套使用。</span></div>
          </div>
        </section>
        """
    ).strip()


def build_slide_12() -> str:
    return dedent(
        """
        <section class="slide" data-title="结论">
          <div class="slide-head">
            <div>
              <span class="slide-kicker">conclusion</span>
              <h2>三组 Demo 已经把 CRE 的“诊断 → 修复 → 验证”故事讲闭环</h2>
              <p class="slide-lead">这套材料既能作为对外汇报 deck，也能作为对内回归审计模板。</p>
            </div>
          </div>
          <div class="two-col conclusion-grid">
            <div class="panel">
              <h3>本次汇报的完整结论</h3>
              <p>Demo 1 说明 reward 设计可以直接诱导危险边界行为；Demo 2 说明 nominal 回放看起来正常并不代表训练覆盖到关键风险几何；Demo 3 说明部署 shift 下 reward proxy 与真实 utility 可能明显脱钩。三组实验都给出了 repair operator，并且 validation 都接受了修后结果。</p>
              <div class="three-notes">
                <div class="note-box"><strong>对外价值</strong><p>把 CRE 的核心能力从抽象方法论变成可视化、可追溯的实验故事。</p></div>
                <div class="note-box"><strong>对内价值</strong><p>把 reward、coverage、shift robustness 三类风险分开做回归基线。</p></div>
                <div class="note-box"><strong>下一步</strong><p>可继续扩成 live demo、PDF 导出包和更细粒度的 operator 手册。</p></div>
              </div>
            </div>
            <div class="panel">
              <h3>汇报建议顺序</h3>
              <ol class="number-list">
                <li>先用第 1 至 3 页把三类问题和统一实验语法讲清楚。</li>
                <li>再按 Demo 1、Demo 2、Demo 3 的顺序讲局部设计与结果。</li>
                <li>最后回到交叉对比页，强调“同样失败，不同根因，不同修法”。</li>
                <li>问答环节直接打开 artifact 路径，展示这份汇报背后的结构化证据。</li>
              </ol>
              <div class="callout">
                <strong>建议收束句</strong>
                <p>CRE 的价值不只是指出“模型会失败”，而是能把失败归因为 reward、coverage 或 shift-proxy 解耦，并给出可验证的修复方向。</p>
              </div>
            </div>
          </div>
        </section>
        """
    ).strip()


def render_html() -> str:
    slides = [
        build_slide_1(),
        build_slide_2(),
        build_slide_3(),
        build_slide_4(),
        build_slide_5(),
        build_slide_6(),
        build_slide_7(),
        build_slide_8(),
        build_slide_9(),
        build_slide_10(),
        build_slide_11(),
        build_slide_12(),
    ]
    notes_payload = [
        {
            "title": item["title"],
            "duration": item["duration"],
            "bodyHtml": "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in item["script"])
            + f"<p class='note-transition'><strong>过渡：</strong>{html.escape(item['transition'])}</p>",
        }
        for item in SLIDE_NOTES
    ]

    template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CRE 三个 Demo 汇报 Deck</title>
  <style>
    :root {
      --paper: #fffdfa;
      --canvas: #f4efe8;
      --ink: #1f2530;
      --muted: #66707f;
      --line: #d9d0c4;
      --navy: #15324f;
      --red: #aa4938;
      --amber: #c27c22;
      --teal: #1f7a72;
      --green: #2c7d53;
      --blue: #2d68b2;
      --soft-red: #fbede8;
      --soft-amber: #fff4e4;
      --soft-teal: #e8f6f4;
      --soft-green: #edf8f1;
      --soft-blue: #eaf2ff;
      --shadow: 0 28px 70px rgba(26, 37, 48, 0.12);
      --radius: 28px;
    }

    * { box-sizing: border-box; }

    html, body {
      margin: 0;
      min-height: 100%;
      background:
        radial-gradient(circle at top left, rgba(27, 104, 178, 0.10), transparent 32%),
        radial-gradient(circle at bottom right, rgba(170, 73, 56, 0.08), transparent 28%),
        linear-gradient(180deg, #f7f2eb 0%, #efe7dc 100%);
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
    }

    body { padding: 22px; }

    .shell {
      max-width: 1560px;
      margin: 0 auto;
      display: grid;
      gap: 16px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      background: rgba(255, 253, 250, 0.88);
      border: 1px solid rgba(217, 208, 196, 0.9);
      border-radius: 22px;
      padding: 16px 20px;
      box-shadow: 0 10px 24px rgba(20, 34, 50, 0.06);
      backdrop-filter: blur(8px);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-mark {
      width: 56px;
      height: 56px;
      border-radius: 18px;
      background:
        radial-gradient(circle at 30% 30%, #fffdf7 0%, #fffdf7 15%, transparent 16%),
        linear-gradient(135deg, #15324f 0%, #2d68b2 50%, #1f7a72 100%);
      box-shadow: 0 12px 22px rgba(33, 72, 124, 0.25);
    }

    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 12px;
      font-weight: 700;
      color: var(--muted);
      margin-bottom: 4px;
    }

    h1, h2, h3, p, ol, ul { margin: 0; }

    .brand h1 {
      font-size: 28px;
      line-height: 1.02;
      letter-spacing: -0.03em;
    }

    .brand p {
      font-family: "Source Serif 4", "Georgia", serif;
      color: var(--muted);
      max-width: 860px;
      line-height: 1.45;
      margin-top: 4px;
      font-size: 15px;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .toolbar button {
      border: 0;
      min-width: 42px;
      height: 42px;
      padding: 0 14px;
      border-radius: 999px;
      cursor: pointer;
      background: #fffaf3;
      color: var(--navy);
      font-weight: 700;
      font-size: 14px;
      border: 1px solid rgba(217, 208, 196, 0.9);
      box-shadow: 0 8px 16px rgba(21, 50, 79, 0.08);
    }

    .toolbar button:hover { background: #fff2de; }
    .toolbar button:disabled { opacity: 0.35; cursor: not-allowed; }

    .page-pill {
      min-width: 110px;
      height: 42px;
      padding: 0 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      background: #fffdfa;
      border: 1px solid rgba(217, 208, 196, 0.9);
      font-size: 13px;
      color: var(--muted);
      font-weight: 700;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 18px;
      align-items: start;
    }

    .layout.notes-hidden {
      grid-template-columns: minmax(0, 1fr);
    }

    .deck {
      position: relative;
    }

    .slide {
      display: none;
      aspect-ratio: 16 / 9;
      width: 100%;
      background:
        linear-gradient(135deg, rgba(246, 239, 231, 0.72), transparent 34%),
        linear-gradient(180deg, #fffdfa 0%, #fffaf4 100%);
      border-radius: 34px;
      border: 1px solid rgba(217, 208, 196, 0.95);
      box-shadow: var(--shadow);
      padding: 34px 38px 28px;
      overflow: hidden;
      position: relative;
    }

    .slide::before,
    .slide::after {
      content: "";
      position: absolute;
      border-radius: 999px;
      pointer-events: none;
    }

    .slide::before {
      width: 320px;
      height: 320px;
      top: -160px;
      right: -120px;
      background: radial-gradient(circle, rgba(45, 104, 178, 0.11) 0%, rgba(45, 104, 178, 0) 70%);
    }

    .slide::after {
      width: 260px;
      height: 260px;
      left: -120px;
      bottom: -130px;
      background: radial-gradient(circle, rgba(170, 73, 56, 0.08) 0%, rgba(170, 73, 56, 0) 72%);
    }

    .slide.is-active { display: grid; }

    .slide-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
      z-index: 1;
      position: relative;
    }

    .slide-kicker {
      display: inline-flex;
      align-items: center;
      padding: 7px 12px;
      border-radius: 999px;
      background: #eef4ff;
      color: var(--navy);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 11px;
      font-weight: 700;
      margin-bottom: 10px;
    }

    .slide h2 {
      font-size: 32px;
      line-height: 1.04;
      letter-spacing: -0.03em;
      max-width: 960px;
    }

    .slide-lead {
      font-family: "Source Serif 4", "Georgia", serif;
      margin-top: 8px;
      max-width: 960px;
      line-height: 1.45;
      font-size: 17px;
      color: var(--muted);
    }

    .headline-chip {
      background: rgba(255, 250, 243, 0.95);
      color: var(--navy);
      border: 1px solid rgba(217, 208, 196, 0.95);
      border-radius: 999px;
      padding: 10px 14px;
      font-weight: 700;
      font-size: 13px;
      white-space: nowrap;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.18fr) minmax(320px, 0.82fr);
      gap: 20px;
      z-index: 1;
      position: relative;
    }

    .hero-main,
    .hero-side,
    .panel,
    .demo-card,
    .note-box,
    .artifact-card {
      background: rgba(255, 253, 250, 0.94);
      border: 1px solid rgba(217, 208, 196, 0.9);
      border-radius: 24px;
      box-shadow: 0 14px 30px rgba(26, 37, 48, 0.06);
    }

    .hero-main { padding: 22px; display: grid; gap: 18px; }
    .hero-side { padding: 18px; display: grid; gap: 14px; }

    .story-band {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }

    .story-step {
      background: linear-gradient(180deg, #fffaf3 0%, #fffdfa 100%);
      border: 1px solid rgba(224, 213, 198, 0.9);
      border-radius: 20px;
      padding: 14px;
      display: grid;
      gap: 8px;
    }

    .story-step span,
    .claim-pill,
    .validation-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: fit-content;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }

    .story-step span {
      background: var(--soft-blue);
      color: var(--navy);
    }

    .story-step strong { font-size: 18px; }
    .story-step p { line-height: 1.45; color: var(--muted); font-size: 14px; }

    .hero-claim h3,
    .panel h3,
    .artifact-copy h3 { font-size: 22px; margin-bottom: 10px; }

    .hero-claim p,
    .panel p,
    .artifact-copy p {
      font-family: "Source Serif 4", "Georgia", serif;
      line-height: 1.55;
      color: var(--ink);
      font-size: 16px;
    }

    .key-metrics,
    .mini-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .stat-chip {
      border-radius: 18px;
      padding: 14px 16px;
      display: grid;
      gap: 6px;
      border: 1px solid rgba(217, 208, 196, 0.9);
      background: #fffaf4;
    }

    .stat-chip span {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }

    .stat-chip strong {
      font-size: 22px;
      line-height: 1;
      letter-spacing: -0.03em;
    }

    .tone-red { background: var(--soft-red); }
    .tone-amber { background: var(--soft-amber); }
    .tone-blue { background: var(--soft-blue); }
    .tone-green { background: var(--soft-green); }
    .tone-teal { background: var(--soft-teal); }

    .demo-card {
      padding: 16px;
      display: grid;
      gap: 12px;
    }

    .demo-card-head,
    .demo-card-foot {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }

    .claim-pill { background: var(--soft-blue); color: var(--navy); }
    .validation-pill { background: var(--soft-green); color: var(--green); }
    .demo-card h3 { font-size: 22px; }
    .demo-card p { font-family: "Source Serif 4", "Georgia", serif; color: var(--ink); line-height: 1.5; }
    .demo-card-foot span { color: var(--muted); font-size: 12px; }

    .two-col,
    .three-col,
    .artifact-grid,
    .three-notes,
    .pipeline,
    .witness-strip,
    .compare-banner,
    .conclusion-grid {
      position: relative;
      z-index: 1;
    }

    .two-col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(340px, 0.92fr); gap: 18px; }
    .three-col { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
    .figure-stack { display: grid; gap: 14px; }
    .figure-stack.compact .figure-card { height: 100%; }
    .figure-pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .panel { padding: 18px; display: grid; gap: 14px; }
    .callout {
      border-radius: 18px;
      padding: 14px 16px;
      background: linear-gradient(180deg, #fff6ea 0%, #fffdf7 100%);
      border: 1px solid rgba(224, 213, 198, 0.9);
      display: grid;
      gap: 8px;
    }

    .bullet-list,
    .artifact-list {
      padding-left: 18px;
      display: grid;
      gap: 8px;
      color: var(--ink);
      line-height: 1.45;
      font-size: 15px;
    }

    .figure-card {
      background: rgba(255, 253, 250, 0.95);
      border: 1px solid rgba(217, 208, 196, 0.92);
      border-radius: 22px;
      padding: 14px;
      display: grid;
      gap: 12px;
      min-height: 0;
    }

    .figure-card figcaption {
      display: grid;
      gap: 4px;
    }

    .figure-title {
      font-weight: 700;
      font-size: 15px;
      color: var(--navy);
    }

    .figure-caption {
      font-family: "Source Serif 4", "Georgia", serif;
      font-size: 14px;
      color: var(--muted);
      line-height: 1.45;
    }

    .figure-art,
    .artifact-visual,
    .mini-figure {
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(180deg, #fffefc 0%, #f9f3eb 100%);
      border-radius: 18px;
      min-height: 220px;
      padding: 10px;
      overflow: hidden;
      border: 1px solid rgba(228, 219, 205, 0.8);
    }

    .figure-art svg,
    .artifact-visual svg,
    .mini-figure svg {
      width: 100%;
      height: auto;
      max-height: 100%;
    }

    .figure-missing {
      min-height: 220px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      gap: 8px;
      font-size: 14px;
    }

    .timeline,
    .pipeline { display: grid; gap: 12px; }

    .timeline-item {
      border-radius: 18px;
      padding: 14px 16px;
      background: #fffaf3;
      border: 1px solid rgba(224, 213, 198, 0.9);
    }

    .timeline-item strong { display: block; margin-bottom: 6px; font-size: 17px; }
    .timeline-item p { color: var(--muted); font-size: 15px; }

    .pipe-box {
      border-radius: 18px;
      padding: 14px 16px;
      display: grid;
      gap: 5px;
      border: 1px solid rgba(217, 208, 196, 0.9);
    }

    .pipe-box strong { font-size: 18px; }
    .pipe-box span { color: var(--muted); line-height: 1.4; font-size: 14px; }
    .pipe-arrow { text-align: center; font-size: 24px; color: var(--muted); font-weight: 700; }

    .witness-strip,
    .three-notes,
    .compare-banner {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .witness-strip div,
    .note-box,
    .support-bar div {
      border-radius: 18px;
      padding: 14px 16px;
      background: #fffaf3;
      border: 1px solid rgba(224, 213, 198, 0.9);
      display: grid;
      gap: 6px;
    }

    .witness-strip strong,
    .note-box strong { font-size: 18px; color: var(--navy); }
    .witness-strip span,
    .note-box p,
    .compare-banner span,
    .support-bar span {
      color: var(--muted);
      line-height: 1.45;
      font-size: 14px;
    }

    .table-panel { padding: 14px; }

    .matrix-table,
    .metric-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      overflow: hidden;
      border-radius: 18px;
    }

    .matrix-table th,
    .matrix-table td,
    .metric-table th,
    .metric-table td {
      padding: 12px 10px;
      border-bottom: 1px solid rgba(224, 213, 198, 0.8);
      text-align: left;
      vertical-align: top;
      line-height: 1.35;
    }

    .matrix-table th,
    .metric-table th {
      background: #f7efe3;
      color: var(--navy);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .result-grid,
    .lower-grid,
    .conclusion-grid { align-items: start; }

    .result-claim { display: grid; gap: 12px; }

    .claim-card {
      border-radius: 18px;
      padding: 14px 16px;
      border: 1px solid rgba(217, 208, 196, 0.9);
      display: grid;
      gap: 6px;
    }

    .claim-card strong { font-size: 17px; }
    .claim-card p { font-family: "Source Serif 4", "Georgia", serif; font-size: 15px; line-height: 1.5; }

    .formula-card {
      border-radius: 18px;
      padding: 14px 16px;
      background: #fffaf3;
      border: 1px solid rgba(224, 213, 198, 0.9);
      display: grid;
      gap: 10px;
    }

    .formula-card pre {
      margin: 0;
      white-space: pre-wrap;
      font-family: "SFMono-Regular", "Consolas", monospace;
      font-size: 14px;
      line-height: 1.5;
      color: var(--navy);
    }

    .demo2-results-grid,
    .demo3-visual-grid,
    .compare-grid { margin-bottom: 16px; }

    .mini-figure { min-height: 180px; }

    .artifact-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }

    .artifact-card {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      gap: 14px;
      padding: 14px;
    }

    .artifact-copy { display: grid; gap: 10px; }

    .artifact-list {
      margin: 0;
      font-size: 13px;
    }

    .artifact-list code,
    code {
      background: rgba(21, 50, 79, 0.06);
      border-radius: 8px;
      padding: 2px 6px;
      font-family: "SFMono-Regular", "Consolas", monospace;
      font-size: 13px;
    }

    .evidence-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: auto;
    }

    .evidence-links a {
      color: var(--blue);
      text-decoration: none;
      font-weight: 700;
      font-size: 13px;
      background: rgba(45, 104, 178, 0.08);
      border-radius: 999px;
      padding: 8px 12px;
    }

    .compare-banner div,
    .support-bar {
      display: grid;
      gap: 12px;
    }

    .compare-banner div {
      padding: 14px 16px;
      border-radius: 18px;
      background: #fffaf3;
      border: 1px solid rgba(224, 213, 198, 0.9);
    }

    .compare-banner strong,
    .support-bar strong { color: var(--navy); font-size: 16px; }
    .compare-banner em { color: var(--red); font-style: normal; font-weight: 700; }

    .support-bar {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .number-list {
      padding-left: 22px;
      display: grid;
      gap: 10px;
      line-height: 1.5;
      font-size: 15px;
    }

    .notes {
      background: rgba(255, 253, 250, 0.94);
      border: 1px solid rgba(217, 208, 196, 0.92);
      border-radius: 28px;
      box-shadow: 0 18px 34px rgba(26, 37, 48, 0.08);
      padding: 18px 18px 20px;
      position: sticky;
      top: 22px;
      display: grid;
      gap: 14px;
      max-height: calc(100vh - 44px);
      overflow: auto;
    }

    .notes h3 { font-size: 22px; }
    .notes-meta {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      border-bottom: 1px solid rgba(224, 213, 198, 0.8);
      padding-bottom: 10px;
    }

    .notes-body {
      display: grid;
      gap: 12px;
      font-family: "Source Serif 4", "Georgia", serif;
      line-height: 1.6;
      font-size: 16px;
    }

    .note-transition {
      padding: 12px 14px;
      border-radius: 16px;
      background: #fff4e6;
      border: 1px solid rgba(230, 210, 181, 0.9);
      font-family: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
      font-size: 14px;
    }

    .footer-tip {
      text-align: right;
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
    }

    @media (max-width: 1280px) {
      .layout { grid-template-columns: 1fr; }
      .notes { position: static; max-height: none; }
      .slide { aspect-ratio: auto; min-height: 900px; }
    }

    @media (max-width: 980px) {
      .two-col,
      .hero-grid,
      .three-col,
      .figure-pair,
      .story-band,
      .witness-strip,
      .three-notes,
      .compare-banner,
      .support-bar,
      .key-metrics,
      .mini-metrics {
        grid-template-columns: 1fr;
      }

      .artifact-card { grid-template-columns: 1fr; }
      .topbar { flex-direction: column; align-items: flex-start; }
      .toolbar { width: 100%; }
      .slide { padding: 24px; min-height: 1020px; }
      .slide h2 { font-size: 28px; }
    }

    @media print {
      body {
        background: #ffffff;
        padding: 0;
      }

      .topbar,
      .notes { display: none; }

      .layout,
      .layout.notes-hidden { grid-template-columns: 1fr; }

      .slide {
        display: grid !important;
        page-break-after: always;
        box-shadow: none;
        border-radius: 0;
        border: 0;
        min-height: auto;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true"></div>
        <div>
          <div class="eyebrow">CRE Demo Presentation</div>
          <h1>CRE 三个 Demo 的实验结果汇报</h1>
          <p>详细中文 HTML deck，覆盖三组 Demo 的设计、结果、根因、修复、验证与逐页讲稿。支持方向键翻页、`N` 键切换讲稿、浏览器打印为 PDF。</p>
        </div>
      </div>
      <div class="toolbar">
        <button type="button" id="prev-btn" aria-label="上一页">←</button>
        <div class="page-pill" id="page-pill">1 / 12</div>
        <button type="button" id="next-btn" aria-label="下一页">→</button>
        <button type="button" id="notes-btn" aria-label="切换讲稿">讲稿</button>
      </div>
    </header>

    <div class="layout" id="layout">
      <main class="deck">
        __SLIDES__
      </main>

      <aside class="notes" id="notes-panel">
        <h3 id="notes-title">讲稿</h3>
        <div class="notes-meta">
          <span id="notes-page">第 1 页</span>
          <span id="notes-duration">建议时长</span>
        </div>
        <div class="notes-body" id="notes-body"></div>
        <div class="footer-tip">提示：方向键翻页，`N` 切换讲稿面板。</div>
      </aside>
    </div>
  </div>

  <script id="notes-data" type="application/json">__NOTES_JSON__</script>
  <script>
    const slides = Array.from(document.querySelectorAll('.slide'));
    const notes = JSON.parse(document.getElementById('notes-data').textContent);
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const notesBtn = document.getElementById('notes-btn');
    const pagePill = document.getElementById('page-pill');
    const layout = document.getElementById('layout');
    const notesTitle = document.getElementById('notes-title');
    const notesPage = document.getElementById('notes-page');
    const notesDuration = document.getElementById('notes-duration');
    const notesBody = document.getElementById('notes-body');
    let currentIndex = 0;

    function syncHash(index) {
      history.replaceState(null, '', '#slide-' + (index + 1));
    }

    function renderNotes(index) {
      const entry = notes[index];
      notesTitle.textContent = entry.title;
      notesPage.textContent = '第 ' + (index + 1) + ' 页';
      notesDuration.textContent = '建议时长：' + entry.duration;
      notesBody.innerHTML = entry.bodyHtml;
    }

    function showSlide(index) {
      currentIndex = Math.max(0, Math.min(index, slides.length - 1));
      slides.forEach((slide, slideIndex) => {
        slide.classList.toggle('is-active', slideIndex === currentIndex);
      });
      prevBtn.disabled = currentIndex === 0;
      nextBtn.disabled = currentIndex === slides.length - 1;
      pagePill.textContent = (currentIndex + 1) + ' / ' + slides.length;
      renderNotes(currentIndex);
      syncHash(currentIndex);
    }

    function jumpFromHash() {
      const match = window.location.hash.match(/slide-(\\d+)/);
      if (!match) return;
      const index = Number(match[1]) - 1;
      if (!Number.isNaN(index)) {
        showSlide(index);
      }
    }

    function toggleNotes() {
      layout.classList.toggle('notes-hidden');
      const hidden = layout.classList.contains('notes-hidden');
      document.getElementById('notes-panel').style.display = hidden ? 'none' : 'grid';
    }

    prevBtn.addEventListener('click', () => showSlide(currentIndex - 1));
    nextBtn.addEventListener('click', () => showSlide(currentIndex + 1));
    notesBtn.addEventListener('click', toggleNotes);

    window.addEventListener('hashchange', jumpFromHash);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') {
        event.preventDefault();
        showSlide(currentIndex + 1);
      } else if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
        event.preventDefault();
        showSlide(currentIndex - 1);
      } else if (event.key.toLowerCase() === 'n') {
        event.preventDefault();
        toggleNotes();
      }
    });

    showSlide(0);
    jumpFromHash();
  </script>
</body>
</html>
"""

    return template.replace("__SLIDES__", "\n".join(slides)).replace(
        "__NOTES_JSON__", json.dumps(notes_payload, ensure_ascii=False)
    )


def render_notes_markdown() -> str:
    lines = [
        "# CRE 三个 Demo 汇报讲稿",
        "",
        "这份讲稿与 `cre_three_demo_report.html` 一一对应，共 12 页。",
        "建议用法：浏览器打开 HTML deck，讲稿面板可以同步查看；如果需要打印讲稿或发给讲解人，直接使用本文件。",
        "",
    ]
    for index, item in enumerate(SLIDE_NOTES, start=1):
        lines.extend(
            [
                f"## Slide {index:02d} · {item['title']}",
                "",
                f"- 建议时长：{item['duration']}",
                "- 讲稿：",
            ]
        )
        for paragraph in item["script"]:
            lines.append(f"  {paragraph}")
        lines.extend(["- 过渡：", f"  {item['transition']}", ""])
    return "\n".join(lines).strip() + "\n"


def render_readme() -> str:
    return dedent(
        """
        # CRE Demo 汇报材料

        本目录提供一套更适合中文汇报的 HTML 格式 PPT，以及逐页讲稿。

        ## 文件说明

        - `cre_three_demo_report.html`
          - 详细版 HTML deck
          - 浏览器直接打开即可翻页
          - 支持方向键翻页、`N` 键切换讲稿面板、浏览器打印为 PDF
        - `cre_three_demo_report_notes.md`
          - 与 deck 一一对应的逐页讲稿
          - 适合打印、演讲排练或发给讲解同学
        - `build_cre_demo_report.py`
          - deck 与讲稿的生成脚本
          - 方便后续根据 demo 数据继续刷新内容

        ## 重新生成

        在仓库根目录执行：

        ```bash
        python3 cre-demos/presentations/build_cre_demo_report.py
        ```

        ## 汇报建议

        1. 先讲第 1 至 3 页，把三类问题和共同实验语法讲清楚。
        2. 再按 Demo 1、Demo 2、Demo 3 的顺序讲设计与结果。
        3. 最后用交叉对比页和支撑材料页收束，进入问答。

        ## 与旧版 deck 的关系

        - `doc/cre_v1_three_demo_deck.html`
          - 英文、轻量、适合快速总览
        - `cre-demos/presentations/cre_three_demo_report.html`
          - 中文、细节更完整、适合正式汇报与答辩支撑
        """
    ).strip() + "\n"


def main() -> None:
    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)
    (PRESENTATION_DIR / "cre_three_demo_report.html").write_text(
        render_html(), encoding="utf-8"
    )
    (PRESENTATION_DIR / "cre_three_demo_report_notes.md").write_text(
        render_notes_markdown(), encoding="utf-8"
    )
    (PRESENTATION_DIR / "README.md").write_text(render_readme(), encoding="utf-8")
    print(
        json.dumps(
            {
                "html": str(PRESENTATION_DIR / "cre_three_demo_report.html"),
                "notes": str(PRESENTATION_DIR / "cre_three_demo_report_notes.md"),
                "readme": str(PRESENTATION_DIR / "README.md"),
                "slide_count": len(SLIDE_NOTES),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
