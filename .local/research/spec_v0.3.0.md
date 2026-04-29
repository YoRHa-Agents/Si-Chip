---
title: "Si-Chip Spec"
version: "v0.3.0"
status: "frozen"
effective_date: "2026-04-29"
promoted_from: "v0.3.0-rc1"
compiled_into_rules: true
supersedes: "v0.2.0"
language: zh-CN
authoritative_inputs:
  - .local/research/r11_core_goal_invariant.md
  - .local/research/spec_v0.2.0.md
  - .local/research/r6_metric_taxonomy.md
  - .local/research/r9_half_retirement_framework.md
  - .local/feedbacks/feedbacks_for_product/feedback_for_v0.2.0.md
  - .local/dogfood/2026-04-28/v0.2.0_ship_report.md
  - .local/dogfood/2026-04-29/abilities/chip-usage-helper/round_10/iteration_delta_report.yaml
normative_sections: [3, 4, 5, 6, 7, 8, 11, 14, 15, 17]
informative_sections: [16]
additive_only: true
preserves_byte_identical_v0_2_0: ["§3", "§4", "§5", "§6", "§7", "§8", "§11", "§13"]
new_normative_sections: ["§14 core_goal", "§15 round_kind", "§17 agent_behavior_contract_addons"]
new_informative_sections: ["§16 multi-ability layout"]
new_additive_subsections: ["§2.1.1 core_goal addendum (forward pointer to §14)", "§13.5 acceptance criteria for v0.3.0-rc1"]
forever_out_unchanged: true
---

# Si-Chip Spec v0.3.0（Frozen — promoted from v0.3.0-rc1; body byte-identical）

> 本文是 Si-Chip 的冻结规范 v0.3.0（promoted from v0.3.0-rc1）。相对 v0.2.0，**仅做加法**：
> (a) 新增 §14 core_goal Normative 章；
> (b) 新增 §15 round_kind Normative 章；
> (c) 新增 §16 multi-ability dogfood 目录布局 Informative 章。
> §3 / §4 / §5 / §6 / §7 / §8 / §11 Normative 段的语义、阈值、表格、forever-out 项与 v0.2.0 **逐字节等价**。
> 内容遵循 R1-R11 证据库与 canonical docs，必要时按 path 引用。
> v0.3.0 Round 14 (code_change) + Round 15 (measurement_only) consecutive PASSes at v1_baseline ⇒ v0.3.0 ship at gate relaxed (= v1_baseline; same as v0.2.0 ship gate).
> Frozen: 本文已进入 `.rules/` 编译（compiled_into_rules: true）。
> Pinned historical record: `.local/research/spec_v0.3.0-rc1.md`（保留作为 v0.3.0 的 rc 上游，不删除）；`.local/research/spec_v0.2.0.md`（保留作为 v0.3.0 的 v0.2.0 baseline，不删除）。

---

## 1. Purpose & Non-Goals

### 1.1 Si-Chip 是什么

Si-Chip 是一个 **持久化的 Skill / Basic Ability 优化工厂 (persistent optimization factory)**：

- 它的核心对象是 `BasicAbility`，不是某种文件形态的 Skill。
- 它通过 **测试 + 指标驱动** 的多轮循环 (capture → profile → evaluate → diagnose → improve → router-test → half-retire-review → iterate → package/register) 持续优化能力的功能、上下文、耗时、路径、路由与治理表面积。
- 它必须 **先把自身交付为可安装的 Skill**，并在本仓库做多轮 dogfood，证明自己能优化自己，然后才允许向外提供能力。
- 它的成功定义不是“支持多少工具”，而是 **每轮 dogfood 都能输出可机器读取的迭代证据**。

### 1.2 Non-Goals（明确不做）

| 非目标 | 状态 | 理由 |
|---|---|---|
| Skill / Plugin marketplace | **forever-out in v0.x** | 本规范不允许引入分发表面积 |
| Router 模型训练 | **forever-out in v0.x** | 详见 §5；Router 工作只研究范式，不训练模型 |
| 全 IDE 通用兼容层 | out-of-scope | 平台优先级见 §7，仅 Cursor / Claude Code / Codex 三档 |
| Markdown-to-CLI 自动转换器 | out-of-scope | 详见 `si_chip_research_report_zh.md` §11 |
| 一次性研究产物 | out-of-scope | Si-Chip 是持久化工厂，单轮交付不构成 ship |
| 通用 Plugin 分发与 commands/hooks | deferred to post-v0.1 | self-eval 稳定通过后另行设计 |
| Codex 原生 SKILL.md runtime 假设 | out-of-scope | Codex 仅经 `AGENTS.md` + `.codex/` bridge |

> 凡涉及 marketplace 或 Router 训练的需求，必须直接拒绝；不允许通过命名转写绕过。

---

## 2. Core Object: BasicAbility

`BasicAbility` 是 Si-Chip 的第一层对象。所有评估、改进、路由、半退役决策都以它为单位。其完整 schema 在 `decision_checklist_zh.md` §1 与 `templates/basic_ability_profile.schema.yaml` 中维护，本节给出冻结字段清单。

### 2.1 字段（Frozen）

```yaml
basic_ability:
  id: "<ability-name>"
  intent: "<this ability solves what>"
  current_surface:
    type: markdown|script|cli|mcp|sdk|memory|mixed
    path: "<repo-relative path>"
    shape_hint: markdown_first|code_first|cli_first|registry_first|memory_first|mixed
  packaging:
    install_targets:
      cursor: bool
      claude_code: bool
      codex: bool
    source_of_truth: ".agents/skills/<name>/"
    generated_targets: ["<...>"]
  lifecycle:
    stage: exploratory|evaluated|productized|routed|governed|half_retired|retired
    last_reviewed_at: "YYYY-MM-DD"
    next_review_at: "YYYY-MM-DD"
  eval_state:
    has_eval_set: bool
    has_no_ability_baseline: bool
    has_self_eval: bool
    has_router_test: bool
    has_iteration_delta: bool
  metrics:
    task_quality: {}
    context_economy: {}
    latency_path: {}
    generalizability: {}
    usage_cost: {}
    routing_cost: {}
    governance_risk: {}
  value_vector:
    task_delta: float
    token_delta: float
    latency_delta: float
    context_delta: float
    path_efficiency_delta: float
    routing_delta: float
    governance_risk_delta: float
  router_floor: "<model_id>/<thinking_depth>" | null
  decision:
    action: keep|half_retire|retire|disable|optimize|productize|create_eval_set|...
    rationale: "<why>"
    risk_flags: ["<...>"]
```

#### 2.1.1 core_goal addendum (NEW v0.3.0; cross-refs §14)

v0.3.0 在 `BasicAbility` 顶层新增一个 **REQUIRED** 字段 `core_goal`，承载 ability 的 "持久的、不可回退的、可被一组测例验证的功能输出"。该字段 **不修改** §2.1 上方的 yaml 主块（main yaml block remains byte-identical to v0.2.0）；其完整 schema、worked examples、test pack 结构、C0_core_goal_pass_rate 度量、严格无回退规则、回滚规则、与 R6 7×37 子指标关系、§11 forever-out 复核以及与 §6 半退役周期的交互均集中在 §14。Reader 应把本小节当作一个 forward pointer：实际的字段细节、yaml 片段、acceptance behavior 都在 §14；本小节只声明 "字段位置在 BasicAbility 根，与 `intent` / `current_surface` 同级"。

> 与 §2.1 主块的关系：`core_goal` 是 v0.3.0 的 **加法**，不替换或修改 §2.1 现存任何字段。`templates/basic_ability_profile.schema.yaml` 在 v0.3.0 通过 additive extension 增加 `core_goal` 块（schema_version 从 0.1.0 → 0.2.0），其它字段定义与 v0.2.0 byte-identical。Round 1-13 Si-Chip 自身证据 + Round 1-10 chip-usage-helper 证据在 schema_version 0.2.0 下继续校验通过（向下兼容契约保留）。

### 2.2 Stage 枚举（Frozen）

```text
exploratory → evaluated → productized → routed → governed
                                       ↘ half_retired ↺
                                          ↘ retired
```

| Stage | 含义 |
|---|---|
| `exploratory` | 有 intent / 案例，无 eval / baseline |
| `evaluated` | 有 eval set + no-ability baseline + 7 维基础指标 |
| `productized` | 稳定步骤已下沉到 script / CLI / MCP / SDK |
| `routed` | 跑过 router-test 并得出 `router_floor` |
| `governed` | 有 owner / version / telemetry / deprecation policy |
| `half_retired` | 功能收益近零但性能 / 上下文 / 路径价值仍存在；周期复审 |
| `retired` | 功能与性能收益均低，或风险高于阈值；归档停触发 |

> Stage 之间可双向迁移；`half_retired` 不是终点，可被 §6.4 的重新激活触发器拉回 `evaluated`。

---

## 3. Metric Taxonomy（Normative）

**Normative.** Si-Chip 必须实现 R6 全部 7 维 / 37 子指标（full scope，非 MVP-only；v0.1.0 prose 写为 "28 子指标" 与 §3.1 table 计数不一致，v0.2.0-rc1 将 prose 对齐到 table 实际枚举数 37），并以 OpenTelemetry GenAI semconv 为首选数据源。完整定义、公式、阈值与 2026 佐证见 `r6_metric_taxonomy.md`，本节只列名与冻结约束。

### 3.1 7 维 37 子指标清单

| 维度 | 子指标 | MVP 8 |
|---|---|:---:|
| **D1 Task Quality** | T1 pass_rate / T2 pass_k / T3 baseline_delta / T4 error_recovery_rate | T1, T2, T3 |
| **D2 Context Economy** | C1 metadata_tokens / C2 body_tokens / C3 resolved_tokens / C4 per_invocation_footprint / C5 context_rot_risk / C6 scope_overlap_score | C1, C4 |
| **D3 Latency & Path Efficiency** | L1 wall_clock_p50 / L2 wall_clock_p95 / L3 step_count / L4 redundant_call_ratio / L5 detour_index / L6 replanning_rate / L7 think_act_split | L1/L2 |
| **D4 Generalizability** | G1 cross_model_pass_matrix / G2 cross_domain_transfer_pass / G3 OOD_robustness / G4 model_version_stability | — |
| **D5 Learning & Usage Cost** | U1 description_readability / U2 first_time_success_rate / U3 setup_steps_count / U4 time_to_first_success | — |
| **D6 Routing Cost** | R1 trigger_precision / R2 trigger_recall / R3 trigger_F1 / R4 near_miss_FP_rate / R5 router_floor / R6 routing_latency_p95 / R7 routing_token_overhead / R8 description_competition_index | R3, R5 |
| **D7 Governance / Risk** | V1 permission_scope / V2 credential_surface / V3 drift_signal / V4 staleness_days | — |

### 3.2 冻结约束

1. **MVP 8 子指标** (`T1 pass_rate`, `T2 pass_k`, `T3 baseline_delta`, `C1 metadata_tokens`, `C4 per_invocation_footprint`, `L2 wall_clock_p95`, `R3 trigger_F1`, `R5 router_floor`) 必须在每轮 dogfood 中产出。
2. **完整 37 子指标**（§3.1 table 实际枚举数；v0.1.0 prose 写作 "28" — v0.2.0-rc1 对齐到 table 计数）的字段在 `BasicAbilityProfile.metrics` 中必须预留，未实现项以 `null` 显式占位，不得省略 key。
3. 数据源优先 OTel attribute (`gen_ai.client.operation.duration` / `gen_ai.client.token.usage` / `gen_ai.tool.name` / `mcp.method.name`)，详见 `r6_metric_taxonomy.md` §5。
4. 任何指标的阈值或公式变更，必须 bump spec version 并经 §13 验收。

**v0.3.0 add-on**: a new top-level invariant `C0_core_goal_pass_rate` is defined in §14; it is *not* a member of the 7×37 R6 set and does not affect the §3.2 frozen counts.

---

## 4. Progressive Gate Profiles（Normative）

**Normative.** Si-Chip 的指标阈值采用 **三档渐进式 gate**，不是单一 MVP 快照。一个能力必须在低档连续通过两轮 dogfood，才允许被高档度量。

### 4.1 三档阈值（每行 = 一个硬门槛；从左到右严格单调）

| 指标 | v1_baseline | v2_tightened | v3_strict |
|---|---:|---:|---:|
| `pass_rate` | ≥ 0.75 | ≥ 0.82 | ≥ 0.90 |
| `pass_k` (k=4) | ≥ 0.40 | ≥ 0.55 | ≥ 0.65 |
| `trigger_F1` | ≥ 0.80 | ≥ 0.85 | ≥ 0.90 |
| `near_miss_FP_rate` | ≤ 0.15 | ≤ 0.10 | ≤ 0.05 |
| `metadata_tokens` | ≤ 120 | ≤ 100 | ≤ 80 |
| `per_invocation_footprint` | ≤ 9000 | ≤ 7000 | ≤ 5000 |
| `wall_clock_p95` (s) | ≤ 45 | ≤ 30 | ≤ 20 |
| `routing_latency_p95` (ms) | ≤ 2000 | ≤ 1200 | ≤ 800 |
| `routing_token_overhead` | ≤ 0.20 | ≤ 0.12 | ≤ 0.08 |
| `iteration_delta` (一项效率轴) | ≥ +0.05 | ≥ +0.10 | ≥ +0.15 |

> 任何后续修订必须保持单调性 (v1 ≤ v2 ≤ v3 / 反向≥)。详细公式 / 数据源见 `r6_metric_taxonomy.md`；Router profile (relaxed / standard / strict) 与 v1/v2/v3 的对应关系见 §5.4。

### 4.2 State Promotion Rule

1. 新能力默认绑定 `v1_baseline`。
2. `v1_baseline` 下 **连续两轮 dogfood 全部通过**，才允许提升至 `v2_tightened`；`v2_tightened` 同理才能升至 `v3_strict`。
3. 任一指标在当前档失败一次：保持当前档；连续两轮失败：下调一档并触发 §6 的 half-retire review。
4. profile 切换、单调性破坏、阈值微调必须记录在 `iteration_delta_report.template.yaml` 与 `BasicAbilityProfile.lifecycle` 中。

**v0.3.0 add-on**: §15 round_kind defines per-kind interpretation of row 10 (`iteration_delta any axis ≥ +0.05`); for `measurement_only` rounds the clause is RELAXED to monotonicity-only per §15.2.

---

## 5. Router Paradigm（Normative）

**Normative.** Si-Chip **不训练 Router 模型**。Router 工作的目标是 **寻找一种更有效的、让模型完成 Router 的范式**。本节冻结允许的工作面与 Router-test 协议骨架；完整协议详见 `r8_router_test_protocol.md`。

### 5.1 允许的 Router 工作面

1. **Metadata 检索**：对 `BasicAbility.description` / 标签 / 触发样例的静态/语义检索。
2. **启发式 / kNN baseline**：复用 DevolaFlow `memory_router/router.py::MemoryRouter` 与 `cache.py::MemoryCase` 作 deterministic baseline。
3. **Description 优化**：参考 Anthropic skill-creator `improve_description.py` 与 R6 `R3 trigger_F1` / `R4 near_miss_FP_rate`。
4. **思考深度升档 (thinking-depth escalation)**：直接调用 DevolaFlow `task_adaptive_selector.select_context(task_type, round_num=N)` 与 `apply_round_escalation`，不自实现档位。
5. **Fallback policy**：失败按 `deterministic_memory_router → composer_2/fast → sonnet/default → opus/extended` 顺序升档；接入 `gate/convergence.py` 防止无限重试。

### 5.2 严格禁止

- 训练任意规模的 Router 分类 / 排序模型。
- 维护私有路由权重或在线学习参数。
- 把 Router 工作转包成 marketplace、模型微调或外部服务。
- 任何使 “Si-Chip 对外提供路由模型” 的语言或字段。

### 5.3 Router-Test Harness 规范

| 项 | MVP（v1_baseline 起步） | Full（v2_tightened+ 必备） |
|---|---|---|
| Cells | 8 (`2 model × 2 thinking_depth × 2 scenario_pack`) | 96 (`6 × 4 × 4`) |
| Models | `composer_2`, `sonnet_shallow` | `composer_2`, `haiku_4_5`, `sonnet_4_6`, `opus_4_7`, `gpt_5_mini`, `deterministic_memory_router` |
| Thinking depths | `fast`, `default` | `fast`, `default`, `extended`, `round_escalated` |
| Scenario packs | `trigger_basic`, `near_miss` | + `multi_skill_competition`, `execution_handoff` |
| Dataset | 每 pack 20 prompts (10 should-trigger + 10 should-not-trigger) | 每 pack 20–50 prompts |
| 必测指标 | `T1`, `T2`, `T3`, `L1/L2`, `R1/R2/R3`, `R4`, `R5`, `R6/R7` | + `C4`, `C5`, `L3`, `L4`, `L5`, `R8`, `G1` |

输出：每个能力一个 `router_floor` (= `model_id × thinking_depth`)，与 §4 当前档对齐。

### 5.4 Router Profile ↔ Gate Profile 绑定

| Router profile (R8) | 绑定 Gate (本规范 §4) |
|---|---|
| relaxed | v1_baseline |
| standard | v2_tightened |
| strict | v3_strict |

> 同一能力同一时刻只允许绑定一个组合；变更必须经 §4.3 promotion rule。

---

## 6. Half-Retirement（Normative）

**Normative.** 生命周期包含三态：`keep` / `half_retire` / `retire`。`half_retire` 必须由 R9 value vector 触发，禁止仅凭主观判断或 “base model 覆盖” 即 retire。

### 6.1 Value Vector（7 维，Frozen）

| 维度 | 公式 | 数据源 |
|---|---|---|
| `task_delta` | `pass_with - pass_without` | R6 T3 |
| `token_delta` | `(tokens_without − tokens_with) / tokens_without` | R6 C4 + OTel |
| `latency_delta` | `(p95_without − p95_with) / p95_without` | R6 L1/L2 |
| `context_delta` | `(footprint_without − footprint_with) / footprint_without` | R6 C1–C5 |
| `path_efficiency_delta` | `(detour_without − detour_with) / detour_without` | R6 L5 |
| `routing_delta` | `trigger_F1_with − trigger_F1_without` | R6 D6 |
| `governance_risk_delta` | `risk_without − risk_with` | R6 D7 |

### 6.2 三态触发规则

| 决策 | 触发条件 |
|---|---|
| `keep` | `task_delta >= +0.10` 或当前档 (§4) 下全部硬门槛通过 |
| `half_retire` | `task_delta` 近零 (`-0.02 ≤ task_delta ≤ +0.10`) **且** `token_delta` / `latency_delta` / `context_delta` / `path_efficiency_delta` / `routing_delta` 中至少一项达到当前 gate profile 的对应阈值桶 (`v1 ≥ +0.05`, `v2 ≥ +0.10`, `v3 ≥ +0.15`) |
| `retire` | value_vector 全部维度 ≤ 0 **或** `governance_risk_delta < 0` 且超出 §11 风险策略 **或** v3_strict 下连续两轮失败且无任一性能轴改善 |
| `disable_auto_trigger` | `governance_risk_delta` 显著为负，无论其它维度 |

> `half_retire` 触发后必须执行 R9 §3 的简化策略（缩短 description、reference 冷存储、manual-only、降低 routing priority 等），并设置 `next_review_at`（建议 30/60/90 天周期，依简化强度）。

### 6.3 Decision Artifact

每次 `half_retire` 或 `retire` 必须落盘 `half_retire_decision.template.yaml` 实例，最少字段：`ability_id`, `version`, `decided_at`, `decision`, `value_vector`, `simplification.applied`, `retained_core`, `review.next_review_at`, `review.triggers`, `provenance`。

### 6.4 Reactivation Triggers（≥ 5）

来自 R9 §5：

1. 新模型 no-ability baseline 上 `task_delta` 重新 ≥ +0.10。
2. 新场景 / 新 domain 的流程恰好被该能力覆盖。
3. router-test 显示便宜模型需要该能力才能通过；`router_floor` 下降一档。
4. `context_delta` / `token_delta` / `latency_delta` 任一变得显著（≥ 0.25）。
5. 依赖 API 变更后，能力的 wrapper 比 base model 更稳。
6. 用户手动调用频率回升（30 天 ≥ 5 次）。

> 满足任一即重新进入 `evaluated` 复审；连续两次 half_retire ↔ active 循环必须经 `gate/cycle_detector.py` 标记并人工 review。

---

## 7. Packaging & Platform Priority（Normative）

**Normative.** Si-Chip 自身必须以可安装 Skill 形式交付。Source of truth、平台优先级与生成产物均冻结如下。

### 7.1 Source of Truth

```text
.agents/skills/si-chip/
  SKILL.md
  references/{basic-ability-profile,self-dogfood-protocol,metrics-r6-summary,router-test-r8-summary,half-retirement-r9-summary}.md
  scripts/{profile_static,count_tokens,aggregate_eval}.py
```

任何平台目录均为 **同步产物**，禁止与 source 漂移。漂移检测见 §10。

### 7.2 优先级（Frozen）

| 优先级 | 平台 | 路径 | 状态 |
|---|---|---|---|
| **1** | **Cursor** | `.agents/skills/si-chip/` + `.cursor/skills/si-chip/` (+ 可选 `.cursor/rules/si-chip-bridge.mdc`) | v0.1.0 必须支持 |
| **2** | **Claude Code** | `.claude/skills/si-chip/` (SKILL.md + references + scripts) | v0.1.0 必须支持 |
| **3** | **Codex** | `AGENTS.md` + `.codex/profiles/si-chip.md` + `.codex/instructions/si-chip-bridge.md` | v0.1.0 仅 bridge；后续接入；不假设 native SKILL.md runtime |

> 用户反馈 v0.0.5 明确：先 Cursor，再 Claude Code，Codex 放后续。本节顺序冻结，不允许颠倒。

### 7.3 Packaging Gate

每个平台必须满足：
- `metadata_tokens ≤ 100`
- `body_tokens ≤ 5000`
- 本地安装步骤 ≤ 2
- 可在该平台生成 Si-Chip 自身的 `BasicAbilityProfile`
- 可执行 §8 self-dogfood 协议至少 1 轮

### 7.4 Marketplace 与分发

明确 **out of v0.x scope**。本规范不提供任何 marketplace 字段、manifest 或注册接口；任何引入分发表面积的 PR 必须被拒绝。

---

## 8. Self-Dogfood Protocol（Normative）

**Normative.** Si-Chip 在向外提供任何指导前，必须先在本仓库完成多轮自我评估、改进、路由测试、半退役复审和迭代。单轮不构成 ship。

### 8.1 必须执行的 8 个步骤（Frozen Order）

```text
1. profile             生成自身 BasicAbilityProfile
2. evaluate            no-ability baseline vs with-ability，输出 metrics_report
3. diagnose            按 R6 7 维 / 37 子指标定位瓶颈
4. improve             生成并执行下一轮 next_action_plan
5. router-test         按 §5.3 跑 8-cell MVP（或 96-cell Full），输出 router_floor_report
6. half-retire-review  按 §6 跑 value vector，产出 half_retire_decision
7. iterate             基于上一轮，比对 iteration_delta_report
8. package-register    同步 source of truth → 平台目录（按 §7 优先级）
```

> 任一步骤失败必须显式报告，禁止静默跳过 (依据 workspace rule “No Silent Failures”)。

### 8.2 每轮最小证据集

每轮 dogfood 必须落盘以下 6 件：

1. `BasicAbilityProfile` (yaml)
2. `metrics_report` (json/yaml，覆盖 MVP 8 项 + 37 项 key 占位；v0.1.0 prose "28 项" 对齐到 §3.1 table 枚举数 37)
3. `router_floor_report` (yaml)
4. `half_retire_decision` (yaml)
5. `next_action_plan` (yaml)
6. `iteration_delta_report` (yaml，与上一轮比对，至少含一项效率轴正向 delta)

**v0.3.0 add-on**: §15 introduces a 7th evidence sentinel `round_kind` field on `next_action_plan.yaml`; this is a field-level addition, not a 7th file.

### 8.3 多轮迭代要求

- v0.1.0 ship 前必须完成 **至少 2 轮** dogfood，且第 2 轮在 `v1_baseline` 全部硬门槛通过。
- 若任一轮 `pass_rate` 显著下降，禁止 ship；必须回滚或重新 improve。
- 多轮历史必须保留并可回放，参见 §10。

---

## 9. Factory Template Contract

工厂模板为机器可读 yaml，用 DevolaFlow `template_engine` 解析与运行 (R7 §1.7)。以下模板必须全部存在于 `templates/` 根目录：

| 模板文件 | 用途 |
|---|---|
| `basic_ability_profile.schema.yaml` | §2 schema 的可验证版本（JSON Schema 风格） |
| `self_eval_suite.template.yaml` | §8.1 的 evaluate / diagnose 套件骨架 |
| `router_test_matrix.template.yaml` | §5.3 的 8-cell / 96-cell 矩阵骨架 |
| `half_retire_decision.template.yaml` | §6.3 决策落盘骨架 |
| `next_action_plan.template.yaml` | §8.1 step 4 的下一轮行动骨架 |
| `iteration_delta_report.template.yaml` | §8.2 第 6 项的对比骨架 |

> 模板内容、字段顺序、必填项的演进必须经 `template_engine/validator.py::validate_template` 通过；任何 schema 变更必须 bump spec 版本。

**v0.3.0 add-on**: `templates/basic_ability_profile.schema.yaml`, `templates/iteration_delta_report.template.yaml`, and `templates/next_action_plan.template.yaml` are extended additively per §14, §15; their `$schema_version` bumps from 0.1.0 → 0.2.0.

---

## 10. Persistence Contract

### 10.1 落盘位置

```text
.local/dogfood/<YYYY-MM-DD>/<round_id>/
  basic_ability_profile.yaml
  metrics_report.yaml
  router_floor_report.yaml
  half_retire_decision.yaml
  next_action_plan.yaml
  iteration_delta_report.yaml
  raw/                       # OTel traces, NineS reports, logs
```

> 等价路径（如 `.local/dogfood/<date>/`）由实现自由命名，但必须保证 round 之间可追溯排序。

**v0.3.0 add-on**: §16 introduces an alternative multi-ability layout `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` for second-and-later abilities; legacy layout REMAINS valid for the Si-Chip self-dogfood (Round 1-13 evidence is canonical).

### 10.2 Persistent Learnings

- 每轮 dogfood 的关键发现（决策原因、阈值漂移、reactivation 触发）必须通过 DevolaFlow `learnings.py::capture_learning` 写入 `.local/memory/skill_profiles/si-chip/learnings.jsonl`。
- 长期价值衰减依赖 `learnings.decay_confidence` (默认 30 天半衰期)。
- 与 DevolaFlow `feedback.py` 联动，所有 half_retire / retire 决策必须有 feedback 记录。

### 10.3 Archive Rule

- 至少保留 **6 个月** 的 dogfood 历史。
- 超过 6 个月的可压缩归档（保留 metrics_report + iteration_delta_report 概要），但不得整体删除。
- 模型升级、依赖 schema 漂移事件必须保留，作为 §6.4 reactivation 的证据。

---

## 11. Scope Boundaries（Normative）

**Normative.** 本节为强制边界；与之冲突的需求一律拒绝。

### 11.1 Out of Scope（永久）

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

### 11.2 Deferred（后续版本可重新评估）

- Codex 原生 SKILL.md runtime 支持（v0.x 仅 bridge）。
- Plugin distribution（commands/hooks/marketplace 升级）。
- 更广义 IDE（OpenCode / Copilot CLI / Gemini CLI 等）支持。
- 多租户 hosted API 表面。

### 11.3 边界守护

- 任何 PR / spec 修订引入上述 Out-of-Scope 项 → 直接拒绝。
- Deferred 项的开闸条件：本规范 bump 至 v0.2.x 及以上，且经 §4 v3_strict 连续两轮通过。

**v0.3.0 add-on (re-affirmation)**: §14 `core_goal` invariant, §15 `round_kind`, §16 multi-ability layout introduce NO new distribution surface, NO router-model training, NO generic IDE compat, NO Markdown-to-CLI converter. See §14.6 forever-out check.

---

## 12. Rules Integration

### 12.1 编译路径

本规范的 Normative 部分压缩进 `.rules/si-chip-spec.mdc`，通过 DevolaFlow rule compiler (`src/devolaflow/local/compiler.py::RuleCompiler`) 与 `.rules/compile-config.yaml` 现有 `agents_md` target 合并生成 `AGENTS.md`。`compile-config.yaml` 需新增 `si-chip-spec` layer (priority 10, always_include: true)，并加入 `targets.agents_md.include_layers`。该编译配置变更不属于本规范写入范围，由后续设计任务执行。

### 12.2 修订流程

- **Normative 段**（§3 / §4 / §5 / §6 / §7 / §8 / §11）任何修改：bump spec version → 更新 `effective_date` / `supersedes` → 同步 `.rules/si-chip-spec.mdc` 与 `compile-config.yaml` → 重跑 §13 验收。
- **Informative 段** 允许小修而不 bump，但必须在 PR 中说明。

### 12.3 Drift Detection

依赖 `.rules/.compile-hashes.json` + `check-rules-drift`；漂移即 CI 失败。平台 Skill 目录与 source of truth 的漂移由 §10 / §7 联合守护。

**v0.3.0 add-on**: this rc is NOT yet compiled into `.rules/`; ship-time L0 step is to flip `compiled_into_rules: true` in frontmatter and rerun `.rules/compile-config.yaml`.

---

## 13. Acceptance Criteria for v0.1.0

本节为 v0.1.0 ship gate；任意一条不通过即视为 spec 未冻结成功。

### 13.1 结构与表达

- 13 个章节全部存在并已填写；`§3 / §4 / §5 / §6 / §7 / §8 / §11` 均以 `**Normative.**` 显式起首。
- 中文为主；英文仅用于专有名词、API、文件路径、字段 key。
- 不复述 R1–R10 全文，所有详细公式 / 数据源 / 论据通过 path 引用。

### 13.2 Normative 内容守护

- §4 三档 `v1_baseline` / `v2_tightened` / `v3_strict` 均存在；每行阈值从左到右严格单调。
- §4 含 state promotion rule（连续 2 轮通过才能升档）。
- §5 明确 “不训练 Router 模型”，并列出允许的工作面与 fallback 顺序；含 8-cell MVP 与 96-cell Full router-test matrix。
- §6 三态 `keep / half_retire / retire` 由 R9 value vector 触发；含 ≥ 5 reactivation triggers。
- §7 平台优先级 Cursor → Claude Code → Codex 显式且不可颠倒；Codex 仅 bridge。
- §8 dogfood 协议覆盖 `profile / evaluate / diagnose / improve / router-test / half-retire-review / iterate / package-register` 八步。
- §11 显式禁止 marketplace 与 Router 模型训练；全文无任何允许性措辞（仅出现在禁止上下文中）。

### 13.3 横向一致性

- §3 引用 R6 全部 7 维 / 37 子指标（§3.1 table 实际枚举数），并冻结 MVP 8 项必产。
- §9 列出的 6 个模板与 §5.3 / §6.3 / §8.2 等 Normative 章节产物一一对应。
- §10 落盘路径与 `r10_self_registering_skill_roadmap.md` §4 仓库布局兼容。
- §12 编译路径与 `.rules/compile-config.yaml` 现状兼容（仅新增 layer，未破坏 schema）。

### 13.4 机器可校验项

下一阶段必须能用脚本读取本规范并自动校验：§2 schema 字段集合、§3 metric key 37 项（对齐 §3.1 table 实际枚举数；v0.1.0 prose "28 项" 为错记）、§4 阈值表 30 个数（= 10 metrics × 3 profiles；v0.1.0 prose "21 个数" 为错记）、§5.3 matrix (8 / 16 intermediate@0.1.1 / 96 cells)、§6.1 value_vector 7 项、§7.2 平台优先级与必产路径、§8.1 / §8.2 步骤与产物清单、§9 模板文件名清单、§11.1 / §11.2 黑/灰名单。

### 13.5 Acceptance Criteria for v0.3.0-rc1（NEW additive subsection；v0.3.0）

> 本子节是 v0.3.0-rc1 ship gate add-on，与 §13.1–§13.4 并列。覆盖 v0.3.0 新增的 §14 / §15 / §16 / §17。§13.1–§13.4 主体内容字节级保留 v0.2.0；本小节仅做加法。

#### 13.5.1 结构与表达

- v0.3.0-rc1 在 v0.2.0 之上新增 §14（Core-Goal Invariant，Normative）、§15（round_kind Enum，Normative）、§16（Multi-Ability Dogfood Layout，Informative @ v0.3.0；target Normative @ v0.3.x）、§17（Agent Behavior Contract Add-ons for v0.3.0，Normative）。
- §3 / §4 / §5 / §6 / §7 / §8 / §11 主体内容字节级保留 v0.2.0；每章最多追加 **1 句** "v0.3.0 add-on" 注记，无其它修改。
- §13.1–§13.4 主体内容字节级保留 v0.2.0；本 §13.5 为 v0.3.0 新增 additive 子节，与 §13.1–§13.4 并列。
- 中文为主；英文仅用于专有名词、API、文件路径、字段 key（与 §13.1 一致）。

#### 13.5.2 Normative 内容守护

- §14 显式锁定 `core_goal` REQUIRED 字段、`core_goal_test_pack.yaml` ≥3 cases + Pact-style "expected_shape, not exact equality"、`C0_core_goal_pass_rate` 每轮 **MUST = 1.0**、严格无回退、REVERT-only rollback rule（与 Round 12 → Round 13 precedent 对齐）。
- §14.5 明确 C0 是 **顶层 invariant**，**NOT** R6 D8 / 第 38 个子指标；R6 7×37 frozen count 不破。
- §14.6 §11 forever-out 4 项 **verbatim 重申**（marketplace / router-model-training / 通用 IDE 兼容层 / Markdown-to-CLI 转换器），无任何新增 forever-out 项。
- §14.7 reactivation 协议要求 half-retired ability 的 `core_goal_test_pack` 必须保留；reactivation prerequisite 包含 C0 = 1.0 against current run。
- §15 4 值枚举 `round_kind ∈ {code_change | measurement_only | ship_prep | maintenance}` 完备；每值都有 §15.2 iteration_delta 子句 + §15.3 C0 子句 + §15.4 promotion-counter 资格说明。
- §17 仅承载 v0.3.0 新增的 **2 条** hard rules（rule 9 + rule 10）；v0.2.0 的 8 条 hard rules 仍由 `.rules/si-chip-spec.mdc` 编译进 AGENTS.md §13；两套规则在编译时合并。

#### 13.5.3 横向一致性

- §14 与 §2.1.1 addendum 互引：§2.1.1 是 forward pointer（"see §14 for full schema"），§14.1.1 schema 与 §2.1.1 narrative 兼容；§2.1 主 yaml block 字节级保留 v0.2.0。
- §15 与 §4.2 promotion rule 互引：§15.4 显式声明 `code_change` + `measurement_only` 计入 consecutive-rounds counter（前提 C0 = 1.0 + 无 v1_baseline 回退），`ship_prep` + `maintenance` 不计入；§4.2 add-on 句指向 §15.2。
- §16 与 §10 落盘段互引：§10 add-on 引用 §16 的新布局；§16.2 migration table 区分 Si-Chip self（legacy retained）/ chip-usage-helper（new layout adopted）/ future new abilities（MUST use new layout）。
- §17 与 §13（compiled AGENTS.md §13）互补：v0.2.0 8 rules + v0.3.0 2 rules 在编译时合并；本 spec markdown §13 主体仍是 v0.1.0 acceptance criteria（保留 v0.2.0 的形态），不重复 AGENTS.md §13 的 8 rules（避免 source-of-truth 漂移）。

#### 13.5.4 机器可校验项

下一阶段（Stage 4）`tools/spec_validator.py` 必须能加载 `--spec .local/research/spec_v0.3.0-rc1.md` 并通过 9 + 2 = **11 个 BLOCKER**（v0.2.0 的 9 个 BLOCKER 不变 + v0.3.0 新增 2 个）：

- 既有 9 个 BLOCKER（来自 v0.2.0 ship 状态）：BAP_SCHEMA_KEYS / R6_KEYS / THRESHOLD_TABLE / VALUE_VECTOR / PLATFORM_PRIORITY / DOGFOOD_STEPS / EVIDENCE_FILES / FOREVER_OUT / REACTIVATION_DETECTOR_EXISTS — 在 v0.3.0-rc1 spec 上必须继续 8/8 PASS（+ 第 9 个 detector existence）。
- 新增 BLOCKER 1：**`CORE_GOAL_FIELD_PRESENT`** —— 每个 `BasicAbilityProfile` YAML 在 `.local/dogfood/.../basic_ability_profile.yaml` 中必须含 `basic_ability.core_goal.{statement, test_pack_path, minimum_pass_rate}`，且 `minimum_pass_rate >= 1.0`（spec-locked at exactly 1.0；任何 < 1.0 = FAIL）。
- 新增 BLOCKER 2：**`ROUND_KIND_FIELD_PRESENT_AND_VALID`** —— 每个 `next_action_plan.yaml` 必须含根字段 `round_kind`，且 `round_kind ∈ {code_change, measurement_only, ship_prep, maintenance}`；缺失或非法值 = FAIL。
- `--strict-prose-count` 模式：`SUPPORTED_SPEC_VERSIONS` 加入 `v0.3.0-rc1`；`EXPECTED_R6_PROSE_BY_SPEC["v0.3.0-rc1"] = 37`、`EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.3.0-rc1"] = 30`（继承 v0.2.0 的 reconciled 计数；v0.3.0-rc1 §13.4 byte-identical 保留 v0.2.0 §13.4 整段，因此 anchor `§3 metric key 37 项` 与 `§4 阈值表 30 个数` 自动满足）。
- Round 1-13 Si-Chip + Round 1-10 chip-usage-helper 既有证据在 v0.3.0-rc1 spec 下继续 PASS（向下兼容契约延续；schema_version 0.1.0 与 0.2.0 同时被 templates 接受）。
- spec_validator 必须区分 Round 14+ 的 ability 走 `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` 新布局（per §16.2）vs Si-Chip self 仍可走 legacy `.local/dogfood/<DATE>/round_<N>/`；前者强制（new ability 落 legacy → BLOCKER），后者保留（Si-Chip self 落 legacy → PASS）。

---

## 14. Core-Goal Invariant（Normative，NEW v0.3.0）

**Normative.** 每个 `BasicAbility` 必须显式锁定一个 **核心目标 (core goal)** —— 即它对 user 承诺的、不可让渡、不可静默回退的功能输出。任何一轮 dogfood 在 `core_goal_test_pack` 上的通过率 **必须 = 1.0**；任何回退即 round failure，无论其它指标多漂亮。本章节由 R11 §3 设计推论而来；v0.2.0 的 13 轮 Si-Chip + 10 轮 chip-usage-helper 联合证据（详见 `.local/dogfood/2026-04-28/v0.2.0_ship_report.md` 与 `.local/dogfood/2026-04-29/abilities/chip-usage-helper/round_10/iteration_delta_report.yaml`）展示了在缺乏 core_goal 锚定时迭代轮自然漂向 measurement-fill 的失效模式；本章是修正。

### 14.1 `core_goal` 字段 schema 与 worked examples

`core_goal` 是 `BasicAbility` 顶层 **REQUIRED** 字段，与 `intent` / `current_surface` 同级。`intent` 描述 "this ability solves what"（高层叙述、router-friendly），`core_goal` 描述 "the persistent, never-regress functional outcome that, if removed, would be immediately user-visible"（可测试的功能契约）。两者正交。

#### 14.1.1 Schema sketch（additive to §2.1；existing fields unchanged）

```yaml
basic_ability:
  id: "<ability-name>"
  intent: "<this ability solves what>"        # unchanged from v0.2.0 §2.1
  core_goal:                                  # NEW in v0.3.0 §14, REQUIRED
    statement: "<one-sentence functional contract; testable, not narrative>"
    user_observable_failure_mode: "<what user sees if core_goal regresses>"
    test_pack_path: "<repo-relative path to core_goal_test_pack.yaml>"
    minimum_pass_rate: 1.0                    # spec-locked at 1.0; cannot be lowered
    last_passing_round: "<round_id>"          # updated each successful round
    core_goal_version: "0.1.0"                # bumps on case deletion or expected_shape revision
  current_surface: { ... }                    # unchanged
  ... (rest of §2.1 unchanged)
```

字段语义：

| 字段 | 类型 | 说明 |
|---|---|---|
| `statement` | string (one sentence) | 可测试的功能契约。禁止抽象叙述，必须可被一组 prompts 验证。 |
| `user_observable_failure_mode` | string | 当 core_goal 回退时 user 立即观察到什么。用于 PR review / on-call diagnose。 |
| `test_pack_path` | string (repo-relative) | 指向 §14.2 的 `core_goal_test_pack.yaml`。pack 必须落地为真实磁盘 artifact。 |
| `minimum_pass_rate` | float | spec-locked = 1.0；任何降低 = §14 违规。 |
| `last_passing_round` | string (`round_<N>` or repo round id) | 上一次 C0 = 1.0 的 round id；每个成功 round 更新。 |
| `core_goal_version` | string (semver) | pack 大版本号；删除 case 或修订 expected_shape 必须 bump。详见 §14.2 冻结约束。 |

#### 14.1.2 Worked example (a) — Si-Chip itself

```yaml
basic_ability:
  id: "si-chip"
  intent: "Persistent BasicAbility optimization factory; profile/evaluate/improve/router-test/half-retire-review/iterate/package any BasicAbility through the 8-step dogfood protocol and emit 6 evidence artifacts per round."
  core_goal:
    statement: "Given any BasicAbility (target ability source path + intent), Si-Chip MUST execute the 8-step dogfood protocol end-to-end and emit 6 evidence files (basic_ability_profile / metrics_report / router_floor_report / half_retire_decision / next_action_plan / iteration_delta_report) into .local/dogfood/<DATE>/[abilities/<id>/]round_<N>/, with all 6 schema-valid against templates/."
    user_observable_failure_mode: "User runs 'profile this new ability through Si-Chip' and gets either a crash, a partial evidence set (≤5 of 6 files), or schema-invalid YAML in any of the 6 files. Either case means Si-Chip cannot deliver its primary value."
    test_pack_path: ".agents/skills/si-chip/core_goal_test_pack.yaml"
    minimum_pass_rate: 1.0
    last_passing_round: "round_13"
    core_goal_version: "0.1.0"
```

至少 ≥3 cases 示例：

1. Profile a synthetic new ability `dummy-ability` (markdown + 1 script). Verify all 6 evidence files land + are template-validated.
2. Run Si-Chip on `chip-usage-helper` (real second ability) Round 1 from scratch. Verify 6 evidence files + iteration_delta accepts `null` as prior_round.
3. Re-run Si-Chip on Si-Chip itself (the meta-case) Round N+1 from Round N artifacts. Verify deltas computed correctly.

#### 14.1.3 Worked example (b) — chip-usage-helper

```yaml
basic_ability:
  id: "chip-usage-helper"
  intent: "Surface a per-user Cursor usage / billing / model-mix / leaderboard dashboard inside the Cursor agent."
  core_goal:
    statement: "Given a user prompt that asks about their own Cursor usage / spend / model mix / team rank in the current or recent billing period, the helper MUST return a response containing (i) a numeric value with currency or percentage unit, (ii) an explicit time window (week / month / period), and (iii) the response is rendered through the chip-usage-helper MCP (not deferred to base model or another skill)."
    user_observable_failure_mode: "User asks '我本月花了多少？' and gets back either an empty string, a generic 'I cannot help with that', a number without time window, or the response is silently routed to a different skill that cannot answer."
    test_pack_path: "ChipPlugins/chips/chip_usage_helper/.dogfood/core_goal_test_pack.yaml"
    minimum_pass_rate: 1.0
    last_passing_round: "round_10"
    core_goal_version: "0.1.0"
```

至少 ≥3 cases 示例：

1. **EN**: "show me my cursor usage dashboard" → response contains `$<num>`, time window, MCP-rendered.
2. **CJK**: "我本月花了多少？" → response contains `¥<num>` 或 `$<num>`, "本月" 时间窗, MCP-rendered.
3. **Slash command**: "/usage-report --window=30d" → response contains numeric, "30 days" / "30d", MCP-rendered.

> 注意：这 3 cases 与 ability 的 40-prompt **trigger eval pack** (`eval_pack.yaml`) 不同。后者测 R3_trigger_F1（routing 决策对不对，即模型是否选中本 ability），前者测 C0_core_goal_pass_rate（routing 后产物对不对，即本 ability 是否真的把功能交付了）。两者互不替代。

### 14.2 `core_goal_test_pack.yaml` schema 与 "expected_shape, not exact equality"

`core_goal_test_pack` 是 `core_goal.test_pack_path` 指向的 YAML 文件，是真实磁盘上的可重放 artifact（不是 inline schema）。其骨架：

```yaml
# .agents/skills/<id>/core_goal_test_pack.yaml （或 ability 实现树等价位置）
$schema_version: "0.1.0"
$spec_section: "v0.3.0 §14.2"

ability_id: "<id>"
last_revised: "YYYY-MM-DD"
revision_log:
  - { round: round_N, change: "added EN case for slash command" }
  - { round: round_M, change: "tightened expected_shape.contains_unit on case_2" }

cases:
  - id: "core_goal_case_1"
    prompt: "<user prompt verbatim>"
    expected_shape:                            # NOT exact equality — Pact-style "loose"
      contains_numeric: true                   # response must contain a number
      contains_unit: ["currency", "percent", "time"]   # at least one of these unit types
      contains_time_window: true               # explicit week/month/period reference
      rendered_by: "<expected_renderer>"       # e.g. "chip-usage-helper-mcp"
      not_empty: true
      not_redirected_to: ["other_skill_id_a", "other_skill_id_b"]
    rationale: "If this case fails, user observes <user_observable_failure_mode>."
    weight: 1.0
  - id: "core_goal_case_2"
    ...
  - id: "core_goal_case_3"
    ...
```

#### 14.2.1 冻结约束（Pack-level）

1. **Case count**: 至少 ≥3 cases。建议 5-10 cases。 ≤20 cases（防止 metadata 预算被吃光；按 Anthropic skill best-practices 每 case ~50 tokens × 20 = 1000 tokens 上限）。
2. **Loose assertion**: `expected_shape` 必须是 **结构断言**（contains, shape, type, renderer），**不是值断言**（exact equality）。这是 Pact "as loose as possible while still ensuring the provider can't break compatibility" 原则的直接应用。
3. **No deletion without major bump**: `cases` 一旦写入，从 round_N 起 **不允许删除任何 case**；只允许 (a) 新增 case；(b) 修订 `expected_shape` 时必须同时把 `revision_log` 加一条说明，并且修订当轮的 `core_goal_pass_rate` 必须仍 = 1.0（否则 = 把已有用户契约改了 → behavioral breaking change）。
4. **Case deletion bumps `core_goal_version`**: 删除 case 必须 bump pack frontmatter `core_goal_version` 一次（v0.3.0 引入此字段时初始为 `0.1.0`），并在 `revision_log` 留 deprecation reason。
5. **No benchmark-detection**: pack 中的 prompts 必须从真实 user prompt 中抽样，不允许 ability 实现侧识别 "这是 core_goal_test 在跑" 而采取与生产 prompt 不同的策略（参考 MLPerf "Benchmark detection is not allowed" 原则）。

#### 14.2.2 与 §6 半退役、§14.7 reactivation 的关系

`core_goal_test_pack.yaml` 是 ability 在生命周期中的 **change detector** —— 它不是 "测这个 ability 多好"，而是 "这个 ability 对用户承诺的核心行为还存在不存在"。当 ability 进入 `half_retired` (§6) 时，pack 不删除而是 cold-archive；reactivation 时（§14.7）必须重跑 pack 并验证 C0 = 1.0。

### 14.3 `C0 core_goal_pass_rate` 度量定义 + 严格 "MUST = 1.0" + 无回退规则

`C0_core_goal_pass_rate` = (number of cases passing in current round) / (total cases). 永远在 [0, 1]。

```yaml
# in metrics_report.yaml
metrics:
  ...                                          # existing 7 R6 dimensions per §3.1
  core_goal:                                   # NEW top-level dimension (NOT inside R6)
    C0_core_goal_pass_rate: 1.0                # MUST be exactly 1.0
    cases_passed: 3
    cases_total: 3
    failed_case_ids: []                        # MUST be []
    pack_version: "0.1.0"                      # mirrors core_goal.core_goal_version
    pack_revision_at_round: "round_N"          # echoes core_goal_test_pack.last_revised
```

#### 14.3.1 The strict "MUST = 1.0" rule

```text
For every dogfood round (regardless of round_kind ∈ §15):
   metrics_report[round].metrics.core_goal.C0_core_goal_pass_rate MUST == 1.0
   metrics_report[round].metrics.core_goal.failed_case_ids MUST == []
```

任何违反 = round failure。不存在 "C0 = 0.95 but other axes are great so let it pass" 的合法路径。

#### 14.3.2 The strict no-regression rule

```text
if metrics_report[round_N+1].metrics.core_goal.C0_core_goal_pass_rate
   < metrics_report[round_N].metrics.core_goal.C0_core_goal_pass_rate
THEN
   round_N+1 IS A FAILURE
   regardless of any other axis
   verdict.core_goal_pass MUST == false
   iteration_delta_report.yaml.verdict.pass MUST == false
```

具体到 round_N+1 的 `iteration_delta_report.yaml` 必须包含 `verdict.core_goal_pass: true`，否则 spec_validator 在 BLOCKER 模式抛错（参见 §13.4 / Stage 4 即将扩展的 spec_validator BLOCKER 集）。

### 14.4 Rollback rule on C0 < 1.0（REVERT-only）+ Round 12 → Round 13 precedent

#### 14.4.1 The rollback rule

failing rounds（`core_goal_pass_rate` regressed）MUST:

1. **Verdict**: 不写 `iteration_delta_report.yaml.verdict.pass = true`（无论其它轴 delta 如何）。
2. **Source revert**: 引发回退的 source 修改必须在下一 round 开始前 reverted（per Round 12 → Round 13 REVERT-ONLY precedent，详见 §14.4.2）。
3. **Next plan**: failing 当轮的 `next_action_plan.yaml.actions` MUST 包含至少一个 `primitive: refine` action with `applies_to_metric: C0_core_goal_pass_rate` 与 `exit_criterion: "C0_core_goal_pass_rate >= prior_round.C0_core_goal_pass_rate"`.
4. **No silent skip**: failing round 仍然 keep 在 `.local/dogfood/<DATE>/...` 下（不删除证据），保留作为 honest negative-result trace（per workspace rule "No Silent Failures"）。这是 §10 archive rule 的延伸：失败的 round 也是历史的一部分。

#### 14.4.2 Round 12 → Round 13 precedent

Si-Chip Round 12 主动添加了一个第 7 个 eval case `evals/si-chip/cases/reactivation_review.yaml`，目的是把 `T2_pass_k` 推过 v2_tightened 的 0.55 阈值。结果该 case 在 SHA-256 deterministic simulator 下 per-case `pass_rate = 0.65`，把 7-case 平均从 Round 11 的 0.5478 拉低到 Round 12 的 0.4950 —— **regression -0.0528**。L0 决定 `PATH = REVERT-ONLY`，Round 13 把第 7 个 case 与 Round 12 baselines 全部 `git rm`，T2_pass_k 字节级恢复到 Round 11 的 0.5477708333333333。

这是一个 **near-miss precedent**：

- 如果 spec 当时已经有 `core_goal_pass_rate` 严格无回退条款，Round 12 在产生 -0.0528 的同时就会被 spec 自动判定为 round failure，REVERT 决策不需要 L0 介入；
- 如果 spec 当时已经有 §15 `round_kind = code_change` vs `measurement_only` 区分，Round 12 添加 case 是 "measurement coverage 扩张" 与 "task quality 实测变化" 同时发生，那种张力会在 spec 层面就显形（"你既改了 measurement surface 又改了 ability 输出，这两件事必须分两轮做"）。

v0.3.0 把这个工艺自动化：未来任何同形态的 Round 12 错误都会被 spec_validator 在 BLOCKER 模式自动拦截（详见 §13.4 / Stage 4 spec_validator BLOCKER 扩展），不需要等 L0 review。

### 14.5 Top-level invariant placement (NOT R6 D8)

`C0_core_goal_pass_rate` 是 **顶层 invariant**，**不是** R6 第 38 个子指标，**不**新增 D8 维度。这是 R11 brief §3.4 的明确推论，本节做 Normative 落地。

#### 14.5.1 Rationale

| 选项 | Pros | Cons |
|---|---|---|
| **A. Add as R6 D8 / 38th sub-metric** | 统一在 7×N 矩阵下；spec_validator 改动小；OTel attribute mapping 可重用 | 破坏 §3.1 R6 frozen 7×37 count → 与 v0.2.0-rc1 prose-count reconciliation 的成果直接冲突；C0 与其它 R6 子指标的 **语义类型不同**（C0 是 binary go/no-go，其它是 continuous quality scores）；R6 子指标允许 v1/v2/v3 阈值递进，C0 只有 = 1.0 一种合法值 → 不应进 progressive gate table |
| **B. Top-level `core_goal_pass_rate` field; separate from R6 metrics dict** | 保持 R6 7×37 frozen；C0 的 binary 性质对应 binary verdict（go/no-go），不混入 progressive scoring；spec §4.2 promotion rule 不需要为 C0 新设阈值桶；C0 失败的 spec 行为（"failure regardless of other axes"）直接写在 §14，不与 §4.1 阈值表纠缠 | spec_validator 多一个 BLOCKER；agents 需要学一个新的字段位置；OTel attribute 需新增 (但反正 D8 也要新增) |

**v0.3.0 选 B**。关键 tie-breaker：**C0 不是 "评估这个 ability 多好" 的指标，而是 "这个 ability 还存在不存在" 的开关**。R6 的 7 维 37 子指标本质上都是 "更多 / 更少 / 更快 / 更慢" 的连续轴；C0 是 "通过 / 不通过" 的 boolean。强行塞进 R6 会造成 spec semantic 上的类型错误。另外，§9 acceptance criteria 要求 v0.2.0 §3-§11 byte-identical；如果选 A，§3.1 table 必须 +1 行（D8 task-quality-invariant），等于自己破自己 additivity。

#### 14.5.2 与 R9 7-axis value vector 的关系

| 概念 | 度量内容 | 触发时机 | 类型 |
|---|---|---|---|
| §6.1 value_vector (7 axes) | 本轮带来的 *改善* 量级 | half-retire-review 阶段 | continuous deltas |
| §14 C0_core_goal_pass_rate | 本轮没破之前的 *核心承诺* | 每个 round 的 evaluate 阶段 | binary go/no-go |

两者是 **正交的 "硬前提 vs 改善信号"**，不是同一类东西。spec §6 在 v0.3.0 中 **不变**：value_vector 仍然 7 轴；C0 是 §14 引入的独立机制。`half_retire_decision.yaml` 仍然只看 value_vector，不看 C0；但任何 round 级 verdict 都先看 C0（C0 fail → round fail → half_retire / iterate / improve 全部停摆，先 REVERT）。

### 14.6 §11 forever-out 复核（verbatim re-affirmation）

Hard check：本节提议的 `core_goal` / `core_goal_test_pack` / `C0_core_goal_pass_rate` / strict no-regression / rollback rule 是否触碰 §11.1？

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. `core_goal_test_pack` 落在每个 ability 自己的源码树或 `.agents/skills/<id>/`，不引入注册中心、distribution surface 或 manifest exchange。 |
| Router 模型训练 | NO. `core_goal_pass_rate` 是 evaluator metric，不喂任何模型；spec §5.1 允许的 "metadata 检索" / "kNN baseline" / "description 优化" / "thinking-depth escalation" / "fallback policy" 完全无需改动。 |
| 通用 IDE / Agent runtime 兼容层 | NO. `core_goal` 是 ability-level 的 yaml 字段，与 IDE 无关；§7.2 平台优先级（Cursor → Claude Code → Codex）保持。 |
| Markdown-to-CLI 自动转换器 | NO. test_pack 是手写 YAML cases，不做 Markdown → CLI 自动生成；core_goal 的 `statement` 是人写的句子，不是从 SKILL.md 自动 derive 的。 |

**结论**: §14 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。

### 14.7 Reactivation interaction（与 §6 / §6.4 的协同）

当一个 ability 进入 `half_retired` (§6) 时，其 `core_goal_test_pack.yaml` **必须保留**（cold-archive 在原路径或 archive 目录），不删除、不重写。reactivation（§6.4 任一触发器命中）的 prerequisite 包含：

1. **Pack 仍然存在且未被改动**：reactivation review 第一步是 verify pack hash 与 half_retire 时刻一致；pack 漂移 = 当作新 ability 走 §14.1 流程，不计入 reactivation。
2. **C0 = 1.0 against current run**：在新模型 / 新场景 / 新依赖下，重跑 pack。如果 C0 < 1.0 → reactivation 拒绝，ability 留在 `half_retired`（或进一步降到 `retired`，由 §6.2 决策）。
3. **Pack 可以扩展但不能收缩**：reactivation 后允许 add cases（涵盖触发 reactivation 的新场景），不允许 delete cases（per §14.2 冻结约束 #3）。
4. **`core_goal_version` carry-forward**：reactivation 不自动 bump pack version；只有 §14.2 #4 触发的 deletion / shape revision 才 bump。

> 与 §6.4 reactivation triggers 的协作：6 个 reactivation triggers 中任一命中是 *necessary*；C0 = 1.0 是 *sufficient* 验证 —— 缺一不可。这把 §6.4 的 "ability 重新有用" 与 §14 的 "ability 仍然 work" 串成一个完整的 reactivation gate。

---

## 15. round_kind Enum（Normative，NEW v0.3.0）

**Normative.** 每轮 dogfood 必须显式声明 `round_kind ∈ {code_change | measurement_only | ship_prep | maintenance}`。该字段进入 `next_action_plan.yaml` 的根字段（template additive extension；详见 §9 add-on 与 templates `$schema_version` 0.1.0 → 0.2.0 升级）。`round_kind` 决定本轮如何解读 §4.1 row 10 的 iteration_delta 子句以及 §4.2 promotion rule 的 "consecutive rounds" 计数。本章节由 R11 §4 设计推论而来；动机：v0.2.0 13 轮 Si-Chip 中 9 轮（Round 4-12）满足 iteration_delta 是通过 measurement-fill（"本轮新增对一个之前没测的 sub-metric 的覆盖"），而不是通过真实的能力改善；`round_kind` 让 spec 显式承认这种工作类别，避免持续诱导 measurement-fill 失真。

### 15.1 The 4-value enum + decision tree

#### 15.1.1 The 4 values

| `round_kind` | 定义 | 历史例子 |
|---|---|---|
| `code_change` | 本轮 modifies ability source files (≥1 file under `.agents/skills/<id>/` 或对应 ability 实现树) | Si-Chip Round 1 (initial profile)，Round 2 (install.sh)，Round 3 (R6+R7 instrumentation)；chip-usage-helper Round 1 (initial)，Round 2 (CJK tokenizer fix) |
| `measurement_only` | 本轮 adds new metric coverage / new eval cases / new instrumentation 但 **does NOT touch ability source files** | Si-Chip Rounds 4-12（在 v0.3.0 下应回标为 `measurement_only`；当时按 v0.2.0 规则虚构了 axis improvement） |
| `ship_prep` | 本轮 finalizes for release: mirror sync between `.agents/skills/<id>/` 与 `.cursor/skills/<id>/` / `.claude/skills/<id>/`；version bumps in SKILL.md frontmatter / install.sh / CHANGELOG / docs；tarball build | Si-Chip Round 13 (SHIP-PREP REVERT-ONLY)；chip-usage-helper Round 10 (5th consecutive v3-row-complete pass — official convergence) |
| `maintenance` | 本轮 是 post-ship review (e.g. 30/60/90 day cadence per §6.4 reactivation triggers；或 post-model-upgrade re-verify；或 post-dependency-bump smoke) | (尚未在 Si-Chip 13 轮中出现；chip-usage-helper `lifecycle.next_review_at = round_10 + 30d` 隐含一个未来的 maintenance round) |

#### 15.1.2 Decision tree（pick exactly one per round）

```text
START
  │
  ├── (Q1) Does this round modify any file under
  │         .agents/skills/<id>/  OR  the ability's implementation tree?
  │         (e.g. ChipPlugins/chips/chip_usage_helper/mcp/)
  │
  ├── YES ──→ Q2: Is this also a release-finalization round
  │                (mirror sync + version bump + tarball)?
  │           │
  │           ├── YES ──→ round_kind = ship_prep
  │           │
  │           └── NO  ──→ round_kind = code_change
  │
  └── NO ───→ Q3: Is this a post-ship periodic review
              (≥30d after last ship, or post-model-upgrade
               re-verify, or post-dependency-bump smoke)?
              │
              ├── YES ──→ round_kind = maintenance
              │
              └── NO  ──→ round_kind = measurement_only
                          (this round adds metric coverage,
                           new eval cases, or new instrumentation,
                           but does not change ability behavior)
```

边界判定：

- **Mixed `code_change` + `measurement_only`**: 不允许在同一轮内同时改 source 与扩 measurement coverage。如果两者都需要做，必须拆成 2 轮（先 `code_change` 然后 `measurement_only`，或反向，依优先级）。这是 R11 §1.2 在 Round 12 precedent 中的明确教训：同时改两件事会让 regression 归因变得不可能。
- **`ship_prep` 必含 source touch**: ship_prep 必然涉及 mirror sync（修改 `.cursor/skills/<id>/` 或 `.claude/skills/<id>/`），但 source-of-truth `.agents/skills/<id>/` 在 ship_prep 阶段 **不应** 改 ability 行为，只 bump 版本号 / docs。如果 ship_prep 中临时引入一个 fix，必须 (a) 改 round_kind 为 `code_change`，(b) 重跑 evaluate / router-test，(c) 把 ship 推迟到下一轮。
- **`maintenance` 边界**: 如果 maintenance 中 C0 跌或 v1_baseline 任一 hard gate 跌 → 立即触发 §6 半退役复审 / §6.4 reactivation 决策（可能反向把 ability 拉回 `evaluated`），并将下一 round 标为 `code_change` 进行修复。

### 15.2 Per-kind iteration_delta clause table

```text
                     | iteration_delta clause             | C0 clause
---------------------|------------------------------------|----------------------------------
code_change          | ≥1 axis at gate bucket             | == 1.0 AND >= prior
                     |   (v1 ≥ +0.05 / v2 ≥ +0.10
                     |   / v3 ≥ +0.15)
measurement_only     | monotonicity only                  | == 1.0 AND == prior
                     |   (no axis regression below
                     |   v1_baseline; not required to
                     |   show improvement)
ship_prep            | WAIVED                             | == 1.0 AND == prior
                     |   (carry-forward from prior round)
maintenance          | WAIVED                             | == 1.0
                     |   (re-verify only; no metric
                     |   change required)
```

详细说明：

- **`code_change`**: SAME as v0.2.0 §4.1 row 10. MUST show ≥1 efficiency-axis improvement at the active gate's bucket. 这是 spec 对 "本轮真的改了 ability 应该带来真的改善" 的硬约束。
- **`measurement_only`**: **RELAXED**. 没改 source → 不应期望源码侧的改善。spec 只要求 (a) C0 没回退 (= prior round's C0), (b) v1_baseline 任一 hard gate 没从 PASS 变 FAIL。这一条直接修复 R11 §1.1 的 "9 轮 measurement-fill 失真" 问题：spec 不再误导团队去虚构 axis improvement。
- **`ship_prep`**: **WAIVED**. mirror sync 不应改变 ability 行为，metrics 是从前一轮 carry-forward。如果 sync 后任一指标变了，说明 mirror 与 source 漂移 → §10 archive rule + §7 packaging gate 联动报错（不归 §15 管，归 §7 / §12.3 drift detection 管）。
- **`maintenance`**: **WAIVED**. 30/60/90 day cadence 的目的是 re-verify，不是 improve。只要求 C0 = 1.0；不要求 == prior（因为可能距离 prior 已经数月，model / dependency 已变）；如果 C0 跌或 hard gate 跌，立即转 §6 / §6.4 决策路径。

### 15.3 Per-kind C0 clause（universal MUST = 1.0 + monotonicity for all 4 kinds）

| `round_kind` | C0 clause | 理由 |
|---|---|---|
| `code_change` | `C0 == 1.0` AND `C0 >= prior_round.C0` | 改 source 不应破坏核心契约；改善 OK，回退 = round failure。 |
| `measurement_only` | `C0 == 1.0` AND `C0 == prior_round.C0` | 没改 source → C0 严格相等（如果不等，说明 measurement pack 解读不一致 → 检查 simulator / runner 漂移）。 |
| `ship_prep` | `C0 == 1.0` AND `C0 == prior_round.C0` | mirror sync 不应改变 ability 行为；C0 必须等于 source 那一轮。 |
| `maintenance` | `C0 == 1.0` | maintenance 距离 prior 可能很久，prior 比对意义有限；只要求 ability 在当下仍 work。 |

> **C0 = 1.0 是 spec 对 4 种 round_kind 的 universal 硬要求**。spec_validator 在 BLOCKER 模式对每种 round_kind 都校验 C0 == 1.0；额外的 monotonicity / equality 子句按表执行。任何 C0 < 1.0 = round failure，触发 §14.4 rollback rule，无论 round_kind。

### 15.4 Interaction with §4.2 promotion rule（"consecutive rounds" 计数）

v0.2.0 §4.2 says: "连续两轮 dogfood 全部通过, 才允许提升至 v2_tightened". v0.3.0 §15.4 澄清：

#### 15.4.1 Per-kind eligibility for the consecutive-rounds counter

| `round_kind` | Counts toward "consecutive rounds" for promotion? | Conditions |
|---|---|---|
| `code_change` | **YES** | C0 = 1.0 AND `C0 >= prior_round.C0` AND no v1_baseline hard gate regressed AND iteration_delta ≥ +0.05 (v1) / +0.10 (v2) / +0.15 (v3) |
| `measurement_only` | **YES** | C0 = 1.0 AND `C0 == prior_round.C0` AND no v1_baseline hard gate regressed |
| `ship_prep` | **NO** | metrics are carry-forward (not fresh observations); cannot tick promotion counter |
| `maintenance` | **NO** | metrics are re-verify (not fresh ability iteration); cannot tick promotion counter |

#### 15.4.2 Why `measurement_only` counts but `ship_prep` / `maintenance` don't

`measurement_only` 轮虽然没改 source，但它仍然产生 *fresh observations*（新指标覆盖、新 eval case、新 instrumentation reading）。这些 observations 验证了 ability 在当前 source 状态下仍然在 v1_baseline 之上。让 `measurement_only` 计入 consecutive-rounds counter 既保留了 measurement coverage 扩张的激励（不会让团队为了升档而跳过覆盖工作），又通过 §15.2 的 RELAXED clause 切断了 measurement-fill 失真。

`ship_prep` 与 `maintenance` 的 metrics 是 carry-forward / re-verify，不是 fresh observations；让它们计入 consecutive-rounds 等于让团队靠 mirror-sync 工作偷拿 promotion 票，这违反 §4.2 的本意（"连续两轮通过 = 连续两轮在 evaluate 阶段证明了能力的硬门槛"）。

#### 15.4.3 Worked examples

**Example A**: ability on v1_baseline, want to promote to v2_tightened.

- Round N: `code_change`, C0 = 1.0, v1_baseline pass, iteration_delta = +0.07 → counter = 1
- Round N+1: `measurement_only`, C0 = 1.0 == prior, no v1_baseline regression → counter = 2 → **promotion eligible**
- Round N+2: `ship_prep`, C0 = 1.0 == prior, carry-forward → counter unchanged at 2 (still eligible from the N/N+1 streak)

**Example B**: ability on v1_baseline, ship_prep then real iteration.

- Round N: `code_change`, C0 = 1.0, v1_baseline pass, iteration_delta = +0.06 → counter = 1
- Round N+1: `ship_prep` (release v0.x.y) → counter unchanged at 1
- Round N+2: `code_change` (post-ship fix), C0 = 1.0, v1_baseline pass, iteration_delta = +0.05 → counter = 2 → **promotion eligible**
- Round N+3: `maintenance` (30d review), C0 = 1.0 → counter unchanged at 2

**Example C** (failure mode): ability on v1_baseline, attempts measurement_only push.

- Round N: `code_change`, C0 = 1.0, v1_baseline pass, iteration_delta = +0.07 → counter = 1
- Round N+1: `measurement_only`, C0 = 0.95 (one new case fails) → counter reset to 0 (C0 regression = round failure, §14.3.2) AND triggers §14.4 rollback for the source change that exposed the regression

#### 15.4.4 Interaction with §14.3 strict no-regression

`§14.3.2` 的 strict no-regression rule **优先于** §15.4 的 promotion eligibility。即：任何 round 中 C0 跌（无论 round_kind）→ round failure → counter 归零，并且本轮所有后续 verdicts (iteration_delta_report / half_retire_decision) 都不能写 `verdict.pass = true`。这把 §14 与 §15 串成一个一致的硬约束链。

---

## 16. Multi-Ability Dogfood Layout（Informative，NEW v0.3.0; Normative target v0.3.x）

> 本章 **Informative** at v0.3.0；promote to **Normative** 触发条件见 §16.3。本章节由 R11 §5 设计推论而来；当前已有 chip-usage-helper (Round 1-10) 在新布局下落地，加上 Si-Chip self（Round 1-13 在 legacy 布局）= 1 个 new + 1 个 legacy；§16.3 的 promotion 触发要求 "2+ abilities under new layout for 2 consecutive ships"，意味着至少需要再有一个 ability（或 Si-Chip 主动迁移）才能升 Normative。

### 16.1 Directory layout

新布局（multi-ability）:

```text
.local/dogfood/<YYYY-MM-DD>/abilities/<ability-id>/
    eval_pack.yaml                          # trigger eval pack (used by R3_trigger_F1)
    core_goal_test_pack.yaml                # NEW v0.3.0 §14.2 test pack (or symlink/path-ref to source-of-truth pack)
    tools/
        <ability-id>_specific.py            # OPTIONAL; only if generic harness can't handle
    round_<N>/
        basic_ability_profile.yaml
        metrics_report.yaml
        router_floor_report.yaml
        half_retire_decision.yaml
        next_action_plan.yaml               # MUST contain round_kind ∈ §15.1
        iteration_delta_report.yaml         # MUST contain core_goal verdict block per §14.3
        raw/                                # OTel traces, NineS reports, drift checks
```

旧布局（legacy single-ability，retained for Si-Chip self）:

```text
.local/dogfood/<YYYY-MM-DD>/round_<N>/
    basic_ability_profile.yaml
    metrics_report.yaml
    router_floor_report.yaml
    half_retire_decision.yaml
    next_action_plan.yaml
    iteration_delta_report.yaml
    raw/
```

#### 16.1.1 Path-style choices

- **Ability id 禁止包含 `/`**: 统一 kebab-case（例如 `lark-cli-im` 而不是 `lark-cli/im`）。理由：避免文件系统跨平台 quirks + 简化 spec_validator 的 path glob。
- **`tools/<ability-id>_specific.py`** 是 ability 的私有 evaluator 钩子；与未来 `tools/eval_skill.py` (generic harness) 的关系：generic harness 在 100 % cases 下应能跑；ability-specific 钩子只在 ability 有 unique step（如 chip-usage-helper 的 `npm test` 触发 vitest）时存在，且必须以 plugin/callback 形式接入 generic harness 而不是 fork harness。
- **`core_goal_test_pack.yaml`** 在新布局下既可以是 standalone 文件，也可以是指向 source-of-truth pack 的 path-ref（推荐：source-of-truth 落在 `.agents/skills/<id>/core_goal_test_pack.yaml` 或 ability 实现树等价位置；dogfood 子树持 path-ref 而不是拷贝，避免漂移）。

### 16.2 Migration path

| Surface | v0.3.0 status | Action |
|---|---|---|
| Si-Chip self-dogfood (Round 1-13 history) | **legacy layout retained** | No migration. Round 14+ MAY adopt new layout but not required (spec_validator accepts both). |
| chip-usage-helper (Round 1-10 already at new layout) | **new layout adopted** | No action (already correct at `.local/dogfood/2026-04-29/abilities/chip-usage-helper/round_<N>/`). |
| Any **new** ability introduced in v0.3.x | **MUST use new layout** | spec_validator BLOCKER if a new ability writes to `.local/dogfood/<date>/round_<N>/` (would collide with Si-Chip self). |

#### 16.2.1 Backward compatibility contract

- `tools/spec_validator.py` 在 v0.3.0 必须 accept **both** layouts（详见 §13.4 / Stage 4 spec_validator 扩展）。任何 path-shape BLOCKER 必须显式区分 "legacy is OK for Si-Chip" 与 "legacy is FAIL for second-or-later ability"。
- Round 1-13 Si-Chip 自身证据 + Round 1-10 chip-usage-helper 证据继续 PASS，无回退。
- 如果 Si-Chip 主动迁移（v0.3.x 某个 ship_prep 轮），必须把整段 Round 1-13 历史通过 migration script `mv .local/dogfood/<DATE>/round_<N>/ .local/dogfood/<DATE>/abilities/si-chip/round_<N>/`，并在 `next_action_plan.yaml` 记录 migration provenance。这是一次 ship_prep 轮的 housekeeping work（per §15.1 round_kind = ship_prep；§15.4 不计入 promotion counter）。

### 16.3 Promotion-to-Normative trigger

**Promote §16 from Informative to Normative when**:

1. **At least 2 abilities** are under the new `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` layout. （chip-usage-helper 算 1 个；需要再有 1 个新 ability 或 Si-Chip 主动迁移。）
2. **2 consecutive ship cycles** complete with both abilities under the new layout (i.e. each ability has shipped at least once after migration, and the layout has survived 2 ship-prep gates without regression).
3. **Migration script** for legacy → new is available in `tools/` (so further migrations are 1-command, not bespoke).
4. **§4.2 promotion rule** counterpart on layout: spec_validator's layout BLOCKER must have run successfully on both abilities for 2 consecutive rounds before §16 itself promotes.

满足上述 4 条 → 在 spec v0.3.x bump 时把 §16 从 `informative_sections` 移到 `normative_sections`，并把 §16.2 的 `MUST use new layout` 子句从 informative 文字提升为 spec_validator BLOCKER（"any ability profile under `.local/dogfood/<DATE>/round_<N>/` MUST be `id == si-chip`，否则 FAIL"）。

#### 16.3.1 Why "Informative @ v0.3.0, Normative @ v0.3.x"

spec promotion 需要 evidence（per §4.2 spirit）。当前我们只有 chip-usage-helper 一个 second ability 的实证（10 轮）；Si-Chip self 仍在 legacy layout 上。把 layout Normative 推到 v0.3.0 = forcing a rework of Si-Chip self-dogfood without two independent witnesses. Informative @ v0.3.0 给一轮 grace period（3rd ability 或 Si-Chip 主动迁移）后再升 Normative，符合 v0.1.0 → v0.2.0 reconciliation 用 RC（v0.2.0-rc1）渐进升 Normative 的同样模式。

#### 16.3.2 Soft-Normative behavior at v0.3.0

虽然 §16 在 v0.3.0 是 Informative，但 spec_validator 可以发出 **WARNING (not BLOCKER)** for any new ability that lands in legacy layout. 这给了 "soft Normative" 的弱约束：新 ability 作者会看到 warning 而倾向于走新布局，但不强制；老 ability + Si-Chip self 不被打扰。

---

## 17. Agent Behavior Contract Add-ons for v0.3.0 (Normative)

> **AGENTS.md §13** (compiled from `.rules/si-chip-spec.mdc`) carries the v0.2.0 8 hard rules verbatim; this §17 lists the **2 incremental hard rules added by v0.3.0**. Both sets compose at compile time into the rule layer (`.rules/si-chip-spec.mdc` 在 v0.3.0 ship 时增 2 条 rules，AGENTS.md §13 因此变为 8 + 2 = 10 rules)。
>
> 本章节单独存在的目的：保持 spec markdown 与 rule layer 的 source-of-truth 不重叠 —— v0.2.0 8 rules 仍由 `.rules/si-chip-spec.mdc` 单独维护、本 spec 文件只增量声明 v0.3.0 引入的新 rules，避免在两个 source 都 hard-code 同一组规则导致漂移（drift detection 由 `.rules/.compile-hashes.json` + `check-rules-drift` 守护）。

任何 Agent（Cursor / Codex / Claude Code / Copilot）在本仓库工作时，除 AGENTS.md §13 v0.2.0 的 8 条 hard rules 外，**还必须** 遵守 v0.3.0 新增的下列 2 条：

### 17.1 Rule 9 — `core_goal_test_pack` 与 C0 = 1.0

**MUST** attach `core_goal_test_pack` to every BasicAbility profile and verify `C0_core_goal_pass_rate = 1.0` every round; any C0 < 1.0 = round failure regardless of other axes (per §14.3).

具体绑定：

- 每个 `BasicAbilityProfile.basic_ability.core_goal` 必须含 `statement`、`user_observable_failure_mode`、`test_pack_path`、`minimum_pass_rate = 1.0`、`last_passing_round`、`core_goal_version`（per §14.1.1 schema sketch）。
- `core_goal.test_pack_path` 必须指向真实磁盘上的 `core_goal_test_pack.yaml` 文件（≥3 cases；per §14.2 冻结约束 #1）。
- 每轮 dogfood 的 `metrics_report.yaml.metrics.core_goal.C0_core_goal_pass_rate` 必须 == 1.0；任何 < 1.0 触发 §14.3.1 strict "MUST = 1.0" 与 §14.3.2 strict no-regression rule，进而触发 §14.4 REVERT-only rollback。
- C0 是 **顶层 invariant**，**不计入** R6 7×37 子指标（per §14.5）；spec_validator 把 `CORE_GOAL_FIELD_PRESENT` 作为独立 BLOCKER（per §13.5.4 与 Stage 4 forecast）。

### 17.2 Rule 10 — `round_kind` 4 值枚举声明

**MUST** declare `round_kind ∈ {code_change | measurement_only | ship_prep | maintenance}` in every `next_action_plan.yaml`; iteration_delta clause interpretation per §15.2.

具体绑定：

- 每个 `next_action_plan.yaml` 必须含根字段 `round_kind`，值必须是 `{code_change, measurement_only, ship_prep, maintenance}` 四值之一（per §15.1）；缺失或非法值 = §13.5.4 `ROUND_KIND_FIELD_PRESENT_AND_VALID` BLOCKER FAIL。
- `round_kind` 的选取按 §15.1.2 decision tree（先看是否改 ability source；再看是否 ship-finalize；再看是否 post-ship review；否则归 `measurement_only`）。
- iteration_delta 子句解读按 §15.2 per-kind table：`code_change` 严格（≥1 axis at gate bucket）；`measurement_only` RELAXED（monotonicity-only）；`ship_prep` WAIVED；`maintenance` WAIVED。
- C0 子句按 §15.3 per-kind table：四种 round_kind 都要求 `C0 == 1.0`；`code_change` 还要求 `C0 >= prior`；`measurement_only` / `ship_prep` 要求 `C0 == prior`；`maintenance` 仅要求 `C0 == 1.0`。
- promotion-counter 资格按 §15.4：`code_change` + `measurement_only` 计入 §4.2 consecutive-rounds 计数（前提 C0 = 1.0 + 无 v1_baseline 回退）；`ship_prep` + `maintenance` 不计入。

> 与 AGENTS.md §13 的 8 条 v0.2.0 hard rules 的关系：本 §17 的 rule 9 + rule 10 是 **additive**，不替换、不修改 8 条 v0.2.0 rules 中任何一条。冲突解读时仍以 workspace rules（如 "No Silent Failures"、"Mandatory Verification"、"Protected Branch Workflow"）为更高优先级，但不得借此绕过 §17 的 Normative 段。

---

## 附录：术语速查与引用索引（Informative）

| 术语 | 引用 |
|---|---|
| Basic Ability | §2；`decision_checklist_zh.md` §1 |
| Router Floor | §5；`r8_router_test_protocol.md` §5 |
| Value Vector | §6；`r9_half_retirement_framework.md` §1 |
| Self-Dogfood | §8；`r10_self_registering_skill_roadmap.md` §3 |
| Factory Template | §9；`r10_self_registering_skill_roadmap.md` §4 |
| Gate Profile | §4 (v1_baseline / v2_tightened / v3_strict) |
| Source of Truth | §7.1 (`.agents/skills/si-chip/`) |
| **Core Goal** (NEW v0.3.0) | §14；`r11_core_goal_invariant.md` §3 |
| **core_goal_test_pack** (NEW v0.3.0) | §14.2；`r11_core_goal_invariant.md` §3.2 |
| **C0_core_goal_pass_rate** (NEW v0.3.0) | §14.3；`r11_core_goal_invariant.md` §3.3 |
| **round_kind** (NEW v0.3.0) | §15；`r11_core_goal_invariant.md` §4 |
| **measurement_only round** (NEW v0.3.0) | §15.1 / §15.2；`r11_core_goal_invariant.md` §4.1.2 / §4.4 |
| **Multi-ability layout** (NEW v0.3.0; Informative @ v0.3.0) | §16；`r11_core_goal_invariant.md` §5 |

| 本规范节 | 主要引用 |
|---|---|
| §1 / §11 | `si_chip_research_report_zh.md` §0/§11；`feedback_for_research_v0.0.5.md` |
| §2 | `decision_checklist_zh.md` §1；`r10_*` §3 |
| §3 / §4 | `r6_metric_taxonomy.md` §1/§2/§5/§6 |
| §5 | `r8_router_test_protocol.md` §1–§9；`r7_*` §1.4/§1.6 |
| §6 | `r9_half_retirement_framework.md` §1–§5 |
| §7 / §8 | `r10_self_registering_skill_roadmap.md` §1/§3/§4/§6 |
| §9 / §10 | `r7_devolaflow_nines_integration.md` §1.2/§1.5/§1.7 |
| §12 | `.rules/compile-config.yaml`；DevolaFlow `local/compiler.py` |
| **§14 (NEW)** | `r11_core_goal_invariant.md` §3；`feedback_for_v0.2.0.md`；`v0.2.0_ship_report.md`（Round 12 → 13 precedent） |
| **§15 (NEW)** | `r11_core_goal_invariant.md` §4；`v0.2.0_ship_report.md`（Rounds 4-12 measurement-fill diagnosis） |
| **§16 (NEW Informative)** | `r11_core_goal_invariant.md` §5；`r10_self_registering_skill_roadmap.md` §3-§4 |

---

## v0.3.0-rc1 Provenance & Additivity Discipline (Informative)

### A. Additivity ledger（v0.2.0 → v0.3.0-rc1）

| 类别 | 数量 | 备注 |
|---|---:|---|
| Sections byte-identical to v0.2.0 (Normative) | 7 | §3, §4, §5, §6, §7, §8, §11 |
| Sections byte-identical to v0.2.0 (Informative) | 5 | §1, §2 (yaml block + §2.2), §9, §10, §12 |
| New "v0.3.0 add-on" sentences appended to existing sections | 7 | §3, §4, §8, §9, §10, §11, §12 |
| New §13 Agent Behavior Contract hard rules added (rules 9 + 10) | 2 | rule 9 (core_goal C0 = 1.0)，rule 10 (round_kind declared) |
| New Normative sections | 2 | §14 core_goal invariant，§15 round_kind enum |
| New Informative sections | 1 | §16 multi-ability layout |
| Forever-out items added | 0 | §11.1 unchanged; §14.6 re-affirms verbatim |

### B. Byte-identicality verification table

| Section | v0.2.0 source line range | v0.3.0-rc1 status |
|---|---|---|
| §3.1 7-dim 37-sub-metric table | lines 149-157 of `spec_v0.2.0.md` | byte-identical (10 rows × 3 cols) |
| §3.2 frozen constraints (4 items) | lines 161-164 | byte-identical (constraints 1-4) |
| §4.1 threshold table (10 metrics × 3 profiles) | lines 174-185 | byte-identical (30 cells) |
| §4.2 promotion rule (4 rules) | lines 191-194 | byte-identical |
| §5.1 / §5.2 / §5.3 / §5.4 router paradigm | lines 202-237 | byte-identical |
| §6.1 / §6.2 / §6.3 / §6.4 half-retirement | lines 244-282 | byte-identical |
| §7.1 / §7.2 / §7.3 / §7.4 packaging | lines 290-324 | byte-identical |
| §8.1 (8 steps) / §8.2 (6 evidence) / §8.3 (multi-round) | lines 332-362 | byte-identical |
| §11.1 (4 forever-out) / §11.2 / §11.3 | lines 416-435 | byte-identical |

> Verification method (Stage 3): for each row above, `diff -u <(sed -n '<v0.2.0 lines>p' spec_v0.2.0.md) <(sed -n '<v0.3.0-rc1 lines>p' spec_v0.3.0-rc1.md)` MUST emit zero output (mod the single "v0.3.0 add-on" sentence that the task spec allows).

### C. Forever-out re-affirmation (verbatim)

§14, §15, §16 are checked against §11.1 four forever-out items:

- Skill / Plugin **marketplace** 与任何分发表面积. → unchanged. §14 test packs are per-ability source artifacts, no registry. §15 round_kind is a yaml field. §16 is a directory layout.
- **Router 模型训练** 或在线权重学习. → unchanged. C0 is an evaluator metric; round_kind doesn't feed any model.
- 通用 IDE / Agent runtime **兼容层**. → unchanged. §7.2 priority Cursor → Claude Code → Codex preserved.
- Markdown-to-CLI 自动转换器. → unchanged. core_goal_test_pack cases are hand-authored; no auto-derivation from SKILL.md.

### D. Stage gating for v0.3.0 final ship

This v0.3.0-rc1 is a **research-stage spec authoring product**. The full v0.3.0 ship gate requires:

1. **Stage 3** (review): independent read-back of §3-§11 byte-identicality + §14/§15/§16 internal consistency.
2. **Stage 4** (templates + tooling): additive extension of `templates/basic_ability_profile.schema.yaml` + `templates/iteration_delta_report.template.yaml` + `templates/next_action_plan.template.yaml` (`$schema_version` 0.1.0 → 0.2.0); tooling deliverables `tools/cjk_trigger_eval.py` + `tools/eval_skill.py` + `tools/multi_handler_redundant_call.py` per R11 §6, §7, §8.
3. **Round 14** (`code_change`): introduces tooling + adds `core_goal` block to Si-Chip's own basic_ability_profile + adds `core_goal_test_pack.yaml` for Si-Chip; required: C0 = 1.0; v1_baseline all PASS; ≥1 axis improvement at +0.05.
4. **Round 15** (`measurement_only`): re-runs Si-Chip self-eval through new `tools/eval_skill.py` to verify metric byte-equivalence with Round 13; required: C0 = 1.0; v1_baseline all PASS (carry-forward); no axis regression.
5. **Promotion**: rc1 → final happens by flipping `compiled_into_rules: true` in frontmatter, filling `promoted_from: v0.3.0-rc1`, and rerunning `.rules/compile-config.yaml` (per §12 add-on).

### E. Cross-reference back to R11 design brief

| This spec § | r11_core_goal_invariant.md § | Relationship |
|---|---|---|
| §14.1 (core_goal field schema + worked examples) | §3.1 (3.1.1 / 3.1.2 / 3.1.3) | direct adoption with minor field-naming tightening (`core_goal_version` added to schema) |
| §14.2 (test pack schema + freeze constraints) | §3.2 | direct adoption; constraints 1-5 reordered for spec clarity |
| §14.3 (C0 metric definition + no-regression) | §3.3 | direct adoption; §14.3.1 / §14.3.2 split for clarity |
| §14.4 (rollback rule + Round 12 precedent) | §3.3.2 + §1.2 | merged into single subsection |
| §14.5 (top-level invariant placement) | §3.4 | direct adoption; the table reproduced verbatim |
| §14.6 (forever-out re-check) | §3.5 | direct adoption with §11.1 verbatim re-quote |
| §14.7 (reactivation interaction) | §10.5 (q5 escape hatch) + §3.3 + §6.4 | newly synthesized for spec; not in r11 as a single section |
| §15.1 (4 values + decision tree) | §4.1 (4.1.1 / 4.1.2 / 4.1.3 / 4.1.4) | direct adoption; decision tree §15.1.2 newly drawn here for spec clarity |
| §15.2 (per-kind iteration_delta table) | §4.2 | direct adoption |
| §15.3 (per-kind C0 clause) | §4.1 (per-kind C0 sub-bullet) | spec-level synthesis (r11 has it inline; spec splits it out) |
| §15.4 (interaction with §4.2 promotion) | §4.3 + §10.3 | direct adoption with §15.4.1-4 worked examples added |
| §16.1 / §16.2 / §16.3 | §5.1 / §5.2 / §5.3 / §5.4 / §5.5 | direct adoption; collapsed into 3 spec subsections |

---

## Reconciliation Log (v0.2.0 → v0.3.0-rc1; 2026-04-29)

> 本段为 **Informative 溯源记录**，不属于 Normative 语义；mirror v0.1.0 → v0.2.0-rc1 reconciliation log 的 (a)-(f) 风格。每条都可被 `tools/spec_validator.py`（Stage 4 扩展后）或 `diff` 自动验证。

### (a) Sections added

| 章节 | 性质 | 简述 |
|---|---|---|
| **§14 Core-Goal Invariant** | Normative (NEW) | `core_goal` REQUIRED 字段 + `core_goal_test_pack.yaml` schema (≥3 cases, Pact-style "expected_shape, not exact equality") + `C0_core_goal_pass_rate` 度量 (MUST = 1.0) + 严格无回退规则 + REVERT-only rollback + Round 12→13 precedent + 顶层 invariant 放置 (NOT R6 D8) + §11 forever-out 复核 + reactivation 协同。共 7 个子节 (§14.1–§14.7)。 |
| **§15 round_kind Enum** | Normative (NEW) | `round_kind ∈ {code_change | measurement_only | ship_prep | maintenance}` 4 值枚举 + 决策树 + per-kind iteration_delta 子句 (strict / monotonicity-only / WAIVED / WAIVED) + per-kind C0 子句 (universal MUST = 1.0) + 与 §4.2 promotion rule 的 consecutive-rounds counter 资格规则。共 4 个子节 (§15.1–§15.4)。 |
| **§16 Multi-Ability Dogfood Layout** | Informative (NEW) @ v0.3.0；Normative target @ v0.3.x | `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` 新布局 + 与 legacy `.local/dogfood/<DATE>/round_<N>/` 的 migration table + Normative-promotion trigger (≥2 abilities + 2 consecutive ships)。共 3 个子节 (§16.1–§16.3)。 |
| **§17 Agent Behavior Contract Add-ons for v0.3.0** | Normative (NEW) | 仅承载 v0.3.0 新增的 2 条 hard rules（rule 9: core_goal_test_pack + C0 = 1.0；rule 10: round_kind enum 声明）；不重复 AGENTS.md §13 的 v0.2.0 8 rules。共 2 个子节 (§17.1, §17.2)。 |

### (b) Sections preserved byte-identical

`§3` / `§4` / `§5` / `§6` / `§7` / `§8` / `§11` 主体内容相对 `spec_v0.2.0.md` **字节级一致**，由 `diff` 命令机器验证：

| Section | v0.2.0 source line range | v0.3.0-rc1 status | 验证方法 |
|---|---|---|---|
| §3 (Metric Taxonomy) | lines 143–164 of `spec_v0.2.0.md` | byte-identical | `diff <(sed -n '143,164p' spec_v0.2.0.md) <(sed -n '149,170p' spec_v0.3.0-rc1.md)` → zero output |
| §4 (Progressive Gate Profiles) | lines 168–194 | byte-identical | `diff <(sed -n '168,194p' spec_v0.2.0.md) <(sed -n '176,202p' spec_v0.3.0-rc1.md)` → zero output |
| §5 (Router Paradigm) | lines 198–238 | byte-identical | `diff` zero output |
| §6 (Half-Retirement) | lines 242–284 | byte-identical | `diff` zero output |
| §7 (Packaging & Platform Priority) | lines 288–324 | byte-identical | `diff` zero output |
| §8.1 (8-step block) | lines 328–346 | byte-identical | `diff` zero output |
| §11 (Scope Boundaries) | lines 414–435 | byte-identical | `diff` zero output |

> Stage 2 `StatusReport` (this author, prior turn) reported zero `diff` output for all 7 sections; Stage 3 review accepted this as PASS. The §3/§4/§8 sections also each carry **1** "v0.3.0 add-on" sentence appended after the byte-identical body (§3 line 172 / §4 line 204 / §8 line 368 of v0.3.0-rc1.md), as allowed by the additivity contract.

### (c) §13 unchanged from v0.2.0; §13.5 added as new subsection

**Stage 3 fix-1 result**: §13 (`## 13. Acceptance Criteria for v0.1.0`) restored byte-identical to v0.2.0 lines 456–485 (subsections §13.1, §13.2, §13.3, §13.4 verbatim). The `--strict-prose-count` validator anchors `§3 metric key 37 项` and `§4 阈值表 30 个数` are preserved literally inside §13.4.

A new additive subsection **§13.5 Acceptance Criteria for v0.3.0-rc1** is appended (with §13.5.1–§13.5.4 mirroring the §13.1–§13.4 pattern). §13.5 covers v0.3.0-specific acceptance: §14 / §15 / §16 / §17 内容守护、横向一致性互引、新增 BLOCKERs `CORE_GOAL_FIELD_PRESENT` + `ROUND_KIND_FIELD_PRESENT_AND_VALID`、向下兼容契约（Round 1-13 Si-Chip + Round 1-10 chip-usage-helper 既有证据继续 PASS）。

The Stage 2 mistake of replacing §13 with "Agent Behavior Contract" content is corrected: that content moved to a new §17 (above) and contains **only** v0.3.0's 2 new rules, not the 8 v0.2.0 rules (which remain in `.rules/si-chip-spec.mdc` only).

### (d) Templates affected (FORWARD-LOOKING; not yet edited at this stage)

下述 templates 在 Stage 4 (templates + tooling) 必须 additively 扩展；本 Stage 2 (spec authoring) 不修改任何 template 文件：

| Template | Stage 4 修改 | `$schema_version` bump |
|---|---|---|
| `templates/basic_ability_profile.schema.yaml` | additively 增加 `core_goal` block（含 `statement` / `user_observable_failure_mode` / `test_pack_path` / `minimum_pass_rate` / `last_passing_round` / `core_goal_version` 字段）；`required` list 加 `core_goal`；其它字段定义 byte-identical | 0.1.0 → 0.2.0 |
| `templates/iteration_delta_report.template.yaml` | additively 增加 `core_goal_check` block（含 `C0_pass_rate_current` / `C0_pass_rate_prior` / `regression_detected` / `verdict.core_goal_pass`）；其它字段 byte-identical | 0.1.0 → 0.2.0 |
| `templates/next_action_plan.template.yaml` | additively 增加根字段 `round_kind` (enum: 4 值；REQUIRED)；其它字段 byte-identical | 0.1.0 → 0.2.0 |
| `templates/router_test_matrix.template.yaml` | UNCHANGED | 0.1.1 (unchanged) |
| `templates/half_retire_decision.template.yaml` | UNCHANGED | 0.1.0 (unchanged) |
| `templates/self_eval_suite.template.yaml` | UNCHANGED | 0.1.0 (unchanged) |

向下兼容契约：Round 1-13 Si-Chip + Round 1-10 chip-usage-helper 的既有 yaml artefact 在 schema_version 0.2.0 下继续校验通过（新增字段在历史 artefact 中 default null + 仅对 Round 14+ 强制 require）。

### (e) `tools/spec_validator.py` upcoming additions (Stage 4)

| 改动 | 说明 |
|---|---|
| `SUPPORTED_SPEC_VERSIONS` 加入 `v0.3.0-rc1` | 现有集合 `{"v0.1.0", "v0.2.0-rc1", "v0.2.0"}` → `{"v0.1.0", "v0.2.0-rc1", "v0.2.0", "v0.3.0-rc1"}` |
| `EXPECTED_R6_PROSE_BY_SPEC["v0.3.0-rc1"] = 37` | 继承 v0.2.0 reconciled prose count（v0.3.0-rc1 §13.4 byte-identical 保留 v0.2.0 §13.4 整段，因此 anchor `§3 metric key 37 项` 自动满足） |
| `EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.3.0-rc1"] = 30` | 同上；anchor `§4 阈值表 30 个数` 自动满足 |
| **新增 BLOCKER 1: `CORE_GOAL_FIELD_PRESENT`** | 每个 `BasicAbilityProfile` YAML 必须含 `basic_ability.core_goal.{statement, test_pack_path, minimum_pass_rate}`；`minimum_pass_rate >= 1.0`（spec-locked at exactly 1.0；任何 < 1.0 = FAIL）。`test_pack_path` 必须指向真实磁盘路径（不是占位字符串）。 |
| **新增 BLOCKER 2: `ROUND_KIND_FIELD_PRESENT_AND_VALID`** | 每个 `next_action_plan.yaml` 必须含根字段 `round_kind`，且 `round_kind ∈ {code_change, measurement_only, ship_prep, maintenance}`；缺失或非法值 = FAIL。 |
| Total BLOCKER count | 9 (v0.2.0) + 2 (v0.3.0-rc1) = **11** BLOCKERS at v0.3.0-rc1 |
| Backward-compat sentinel | Round 1-13 Si-Chip + Round 1-10 chip-usage-helper artefact 在 v0.3.0-rc1 spec 下：既有 9 BLOCKER 全部 PASS；新增 2 BLOCKER 在 Round 14+ 才严格执行（per §16.2 / §13.5.4 grace period）。 |

### (f) §11 forever-out: UNCHANGED

§11.1 four forever-out items **byte-identical preserved**：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

§14.6 explicit 复核 confirms 上述 4 项均不被 §14 / §15 / §16 / §17 触碰：`core_goal_test_pack` 在 ability 源码树/`.agents/skills/<id>/`，非分发面；`C0_core_goal_pass_rate` 是 evaluator metric，非 router 模型训练；`round_kind` 是 yaml 字段，与 IDE / Markdown-to-CLI 无关；§16 是仓库目录布局，不引入 distribution surface。

frontmatter `forever_out_unchanged: true` 即为本条的机器可读断言。

---

### Promotion v0.3.0-rc1 → v0.3.0 (2026-04-29)

> 本段为 **Informative 溯源记录**，记录 rc → frozen 的晋升事件；body 与 `spec_v0.3.0-rc1.md` **逐字节等价**（除本段及 frontmatter / H1 / preamble 的 6-7 行 metadata 外）。

| 维度 | rc1 (2026-04-29 morning) | v0.3.0 (2026-04-29 evening) | 变化 |
|---|---|---|---|
| `frontmatter.version` | `"v0.3.0-rc1"` | `"v0.3.0"` | flip |
| `frontmatter.status` | `"rc"` | `"frozen"` | flip |
| `frontmatter.promoted_from` | `null` | `"v0.3.0-rc1"` | filled |
| `frontmatter.compiled_into_rules` | `false` | `true` | flip (entered `.rules/si-chip-spec.mdc` rule layer) |
| H1 标题 | `# Si-Chip Spec v0.3.0-rc1（rc — adds ...）` | `# Si-Chip Spec v0.3.0（Frozen — promoted from v0.3.0-rc1; body byte-identical）` | rc → frozen wording |
| preamble 第 1 行 | `本文是 Si-Chip 的候选规范 v0.3.0-rc1` | `本文是 Si-Chip 的冻结规范 v0.3.0（promoted from v0.3.0-rc1）` | rc → frozen wording |
| preamble 加句 | — | `> v0.3.0 Round 14 (code_change) + Round 15 (measurement_only) consecutive PASSes at v1_baseline ⇒ v0.3.0 ship at gate relaxed (= v1_baseline; same as v0.2.0 ship gate).` | added |
| Pinned historical record 行 | 指 `spec_v0.2.0.md` 一项 | 增加 `spec_v0.3.0-rc1.md` 一项 | additive |
| End-of-spec footer | `End of Si-Chip Spec v0.3.0-rc1（rc — ...）` | `End of Si-Chip Spec v0.3.0（Frozen — promoted from v0.3.0-rc1; body byte-identical）` | rc → frozen wording |
| Reconciliation Log（本节） | 含 (a)–(f) 6 个子段 | 含 (a)–(f) + 本 Promotion 子段 | additive |
| 其余 1208 行 body | — | — | byte-identical |

**(i) rc → frozen status flip**: frontmatter `status: rc → frozen`；H1 / preamble / footer 三处 wording 同步 rc → frozen。`promoted_from: null → "v0.3.0-rc1"` 填入晋升来源。

**(ii) compiled_into_rules: true**: frontmatter `compiled_into_rules: false → true`；本 spec 已通过 Stage 7 packaging 进入 `.rules/si-chip-spec.mdc` 编译流，并通过 `.rules/.compile-hashes.json` drift detection 守护。AGENTS.md §13 Agent Behavior Contract 同步增加 v0.3.0 §17.1 + §17.2 的 2 条 hard rules（rule 9 + rule 10），与 v0.2.0 8 rules 累加为 10 rules。

**(iii) Round 14 + 15 evidence pointers**:

| 轮次 | 类型 | 路径 | 关键证据 |
|---|---|---|---|
| Round 14 | `round_kind: code_change` | `.local/dogfood/2026-04-29/round_14/` | 6 evidence files + 4 abilities-tree files + 14 raw artifacts；C0 = 1.0 (5/5)；spec_validator dual-spec 11/11 + 11/11 PASS；14th consecutive v1_baseline pass；2 axes ≥ +0.05 (governance_risk + generalizability) |
| Round 15 | `round_kind: measurement_only` | `.local/dogfood/2026-04-29/round_15/` | 6 evidence files + 11 raw artifacts；C0 monotonicity 1.0 → 1.0 verified；spec_validator dual-spec 11/11 + 11/11 replay PASS；15th consecutive v1_baseline pass；canonical demonstration of §15 round_kind enum in production |

两轮均 `pytest 395 passed / 1 skipped`；mirrors byte-identical (V3_drift_signal = 0.0)；§4.2 + §15.4 ⇒ v0.3.0 ship at gate relaxed (= v1_baseline) eligible.

**(iv) "body byte-identical to rc1; no semantic change"**: 本 promotion **不修改任何 Normative 语义**：§3 / §4 / §5 / §6 / §7 / §8 / §11 / §13 / §14 / §15 / §16 / §17 全部 **逐字节** 沿用 rc1；阈值数值、子指标集合、value-vector 轴、forever-out 项、core_goal locked `minimum_pass_rate = 1.0`、round_kind 4 值枚举、§17 rule 9 / rule 10 wording 全部 **逐字节** 等价。

机器可校验：`diff -u <(sed -n '27,1135p' .local/research/spec_v0.3.0-rc1.md) <(sed -n '28,1136p' .local/research/spec_v0.3.0.md)` 应仅在 H1 行 (`v0.3.0-rc1` ↔ `v0.3.0`) 与 preamble 头部 (`候选规范 v0.3.0-rc1` ↔ `冻结规范 v0.3.0`) 报差异；body 其它 1208 行无差异。

> Stage 7 (Packaging) 完成本 promotion；Stage 8 (ship-commit) 由 L0 owner 在 Protected Branch Workflow 下提交。

---

## End of Si-Chip Spec v0.3.0（Frozen — promoted from v0.3.0-rc1; body byte-identical）
