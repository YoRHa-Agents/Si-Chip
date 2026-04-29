---
title: "Si-Chip Spec"
version: "v0.2.0-rc1"
status: "release_candidate"
effective_date: "2026-04-28"
compiled_into_rules: true
supersedes: "v0.1.0"
language: zh-CN
authoritative_inputs:
  - .local/research/si_chip_research_report_zh.md
  - .local/research/decision_checklist_zh.md
  - .local/research/README.md
  - .local/research/r6_metric_taxonomy.md
  - .local/research/r7_devolaflow_nines_integration.md
  - .local/research/r8_router_test_protocol.md
  - .local/research/r9_half_retirement_framework.md
  - .local/research/r10_self_registering_skill_roadmap.md
  - .local/feedbacks/feedbacks_for_research/feedback_for_research_v0.0.5.md
  - .local/research/spec_v0.1.0.md
normative_sections: [3, 4, 5, 6, 7, 8, 11]
reconciliation_only: true   # v0.2.0-rc1 scope: §13.4 prose counts aligned with §3.1 / §4.1 tables; Normative semantics (§3/§4/§5/§6/§7/§8/§11) byte-identical to v0.1.0.
---

# Si-Chip Spec v0.2.0-rc1（Release Candidate — 仅 §13.4 prose-count reconciliation）

> 本文是 Si-Chip 的冻结规范的 release candidate。相对 v0.1.0，仅做 **§13.4 prose 对 §3.1 / §4.1 table 的计数对齐**：
> (a) §3 summary + §3.2 冻结约束 #2 + §8.1 step 3 + §8.2 evidence #2 + §13.3 + §13.4 里 "28 子指标" 更新为 "37 子指标"；
> (b) §13.4 里 "21 个数" 更新为 "30 个数"。
> §3 / §4 / §5 / §6 / §7 / §8 / §11 Normative 段的语义（sub-metric 集合、阈值数值、步骤顺序、平台优先级、value-vector 轴、forever-out 项、reactivation triggers）与 v0.1.0 **逐字节等价**。
> v0.2.0 final 仍未 ship；本 RC 等待 Round 12 v2_tightened readiness 验证后晋升至 v0.2.0 final。
> 一经生效即作为本仓库 Rules，通过 `.rules/si-chip-spec.mdc` 编译进 `AGENTS.md`。
> 内容遵循 R1-R10 证据库与 canonical docs，不复述其完整内容，必要时按 path 引用。
> 第 3、4、5、6、7、8、11 节为 **Normative**，其它为信息性 (Informative)。

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

---

## 12. Rules Integration

### 12.1 编译路径

本规范的 Normative 部分压缩进 `.rules/si-chip-spec.mdc`，通过 DevolaFlow rule compiler (`src/devolaflow/local/compiler.py::RuleCompiler`) 与 `.rules/compile-config.yaml` 现有 `agents_md` target 合并生成 `AGENTS.md`。`compile-config.yaml` 需新增 `si-chip-spec` layer (priority 10, always_include: true)，并加入 `targets.agents_md.include_layers`。该编译配置变更不属于本规范写入范围，由后续设计任务执行。

### 12.2 修订流程

- **Normative 段**（§3 / §4 / §5 / §6 / §7 / §8 / §11）任何修改：bump spec version → 更新 `effective_date` / `supersedes` → 同步 `.rules/si-chip-spec.mdc` 与 `compile-config.yaml` → 重跑 §13 验收。
- **Informative 段** 允许小修而不 bump，但必须在 PR 中说明。

### 12.3 Drift Detection

依赖 `.rules/.compile-hashes.json` + `check-rules-drift`；漂移即 CI 失败。平台 Skill 目录与 source of truth 的漂移由 §10 / §7 联合守护。

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

| 本规范节 | 主要 R 引用 |
|---|---|
| §1 / §11 | `si_chip_research_report_zh.md` §0/§11；`feedback_for_research_v0.0.5.md` |
| §2 | `decision_checklist_zh.md` §1；`r10_*` §3 |
| §3 / §4 | `r6_metric_taxonomy.md` §1/§2/§5/§6 |
| §5 | `r8_router_test_protocol.md` §1–§9；`r7_*` §1.4/§1.6 |
| §6 | `r9_half_retirement_framework.md` §1–§5 |
| §7 / §8 | `r10_self_registering_skill_roadmap.md` §1/§3/§4/§6 |
| §9 / §10 | `r7_devolaflow_nines_integration.md` §1.2/§1.5/§1.7 |
| §12 | `.rules/compile-config.yaml`；DevolaFlow `local/compiler.py` |

---

## Reconciliation Log (v0.1.0 → v0.2.0-rc1; 2026-04-28, Round 11)

> 本段为 **Informative 溯源记录**，不属于 Normative 语义；但每一条都可由 `tools/spec_validator.py` 自动验证。

### (a) Prose-count 变更明细

| 位置 | v0.1.0 旧值 | v0.2.0-rc1 新值 | 性质 |
|---|---|---|---|
| §3 intro | `7 维 / 28 子指标` | `7 维 / 37 子指标` | 对齐 §3.1 table (4+6+7+4+4+8+4) |
| §3.1 title | `### 3.1 7 维 28 子指标清单` | `### 3.1 7 维 37 子指标清单` | 对齐 §3.1 table 枚举数 |
| §3.2 item 2 | `完整 28 子指标` | `完整 37 子指标` | 对齐 §3.1 table 枚举数 |
| §8.1 step 3 | `R6 7 维 / 28 子指标` | `R6 7 维 / 37 子指标` | 对齐 §3.1 table |
| §8.2 item 2 | `MVP 8 项 + 28 项 key 占位` | `MVP 8 项 + 37 项 key 占位` | 对齐 §3.1 table |
| §13.3 | `R6 全部 7 维 / 28 子指标` | `R6 全部 7 维 / 37 子指标` | 对齐 §3.1 table |
| §13.4 sub-metric | `§3 metric key 28 项` | `§3 metric key 37 项` | 对齐 §3.1 table |
| §13.4 threshold | `§4 阈值表 21 个数` | `§4 阈值表 30 个数（= 10 metrics × 3 profiles）` | 对齐 §4.1 table |

### (b) 目标计数（Frozen 起点）

| 项 | 值 | 证据来源 |
|---|---:|---|
| §3.1 7 维 sub-metrics 总数 | **37** | D1(4)+D2(6)+D3(7)+D4(4)+D5(4)+D6(8)+D7(4) |
| §4.1 阈值单元总数 | **30** | 10 metric 行 × 3 profile 列 |
| §3 MVP-8 子集 | **8** | T1, T2, T3, C1, C4, L2, R3, R5（未变） |
| §5.3 router-test matrix | **8 / 16 / 96** | mvp（2×2×2）/ intermediate (2×2×4，Round 9 additive) / full（6×4×4） |
| §6.1 value_vector 轴数 | **7** | task / token / latency / context / path_efficiency / routing / governance_risk（未变） |
| §11.1 forever-out 项 | **4** | marketplace / router_training / md_to_cli / ide_compat（未变） |

### (c) Round 11 证据文件

所有 prose-count 对齐的证据落盘在 `.local/dogfood/2026-04-28/round_11/`：

- `basic_ability_profile.yaml`（spec_version: v0.2.0-rc1；metrics 承自 Round 10 字节级不变）
- `metrics_report.yaml`（37 sub-metric keys 全部在位；spec_version: v0.2.0-rc1）
- `router_floor_report.yaml`（承自 Round 10 字节级不变；mvp 8 + intermediate 16 cells 不变）
- `half_retire_decision.yaml`（decision=keep；value_vector 7 轴不变；rationale 重写记录 Round 11 spec reconciliation）
- `next_action_plan.yaml`（预置 Round 12：§6.4 reactivation detector + v2_tightened readiness）
- `iteration_delta_report.yaml`（governance_risk 轴 positive_axis: true，记录 drift-removal 成就；其余 axes delta=0.0）
- `raw/spec_reconciliation.md`（本次 reconciliation 的叙事纪要）
- `raw/spec_drift_report.json`（spec_validator 在所有模式 + 10 轮 artefact 上的验证结果）
- `raw/rules_compile_hashes_before.json` + `raw/rules_compile_hashes_after.json`（`.rules/.compile-hashes.json` 前后快照）

### (d) Normative 语义字节级不变性声明

以下 Normative 内容相对 v0.1.0 **逐字节一致**（`diff` 命令可机器验证）：

- §3.1 table 10 行 × 3 列原子枚举（每行维度 / sub-metric / MVP 8 标注）
- §4.1 table 10 行 × 3 列阈值数值与比较符
- §4.2 State Promotion Rule 四条规则
- §5.1 允许的 5 条 Router 工作面
- §5.2 严格禁止的 4 条
- §5.3 Router-Test Harness 表（MVP / Full 列）
- §5.4 Router profile ↔ Gate binding 3 行
- §6.1 value_vector 7 行（公式 + 数据源）
- §6.2 决策触发规则 4 行
- §6.3 Decision Artifact 最少字段集
- §6.4 Reactivation Triggers 6 条
- §7.1 Source of Truth 路径
- §7.2 平台优先级 3 行（Cursor → Claude Code → Codex 顺序）
- §7.3 Packaging Gate 5 条
- §7.4 Marketplace 边界
- §8.1 8 步骤顺序
- §8.2 6 证据文件清单
- §8.3 多轮迭代要求
- §11.1 Out of Scope 4 项
- §11.2 Deferred 4 项
- §11.3 边界守护 2 条

**变更仅限于 Informative prose 的计数数字**（28→37；21→30）——table 本身（每个 sub-metric 名字、维度分类、每个阈值数字、单调方向、profile 列顺序、MVP-8 子集标注、reactivation trigger ID、forever-out 4 项）无一改动。

`tools/spec_validator.py` 在 `--json` 默认模式下（TABLE 权威）继续 8/8 PASS；在 `--strict-prose-count --spec .local/research/spec_v0.2.0-rc1.md` 模式下，新的 `EXPECTED_R6_PROSE_TOTAL = 37` 与 `EXPECTED_THRESHOLD_CELLS_PROSE = 30` 让 R6_KEYS + THRESHOLD_TABLE 也 PASS —— v0.1.0 下这两条在 strict-prose 模式下刻意 FAIL 作为 reconciliation sentinel 的行为已完成其历史使命。

### (e) 向下兼容契约

Round 1 – Round 10 产生的 `metrics_report.yaml` / `router_floor_report.yaml` / `half_retire_decision.yaml` / `iteration_delta_report.yaml` / `basic_ability_profile.yaml` artefact 在 v0.2.0-rc1 下继续验证：

- `templates/*.template.yaml` 的 `$schema_version` 全部保持原值（`0.1.0` / `router_test_matrix.template.yaml: 0.1.1`）——无字段语义变更。
- 6 个模板文件顶部统一新增 sentinel comment `# Compatible with spec versions: v0.1.0, v0.2.0-rc1`。
- `tools/spec_validator.py` 默认模式对历史 artefact 的读取行为逐字节未变（spec 路径参数 `--spec` 可同时指向 v0.1.0 或 v0.2.0-rc1）。

### (f) Post-RC 路径

v0.2.0-rc1 → v0.2.0 final 的 ship gate：
1. Round 12 执行 v2_tightened readiness verify + §6.4 reactivation detector 实现 + 连续两轮 v2 pass。
2. 若 Round 12 全部通过 → spec bump v0.2.0-rc1 → v0.2.0；否则追加 Round 13/14 直至 §4.2 promotion rule 满足。
3. v0.2.0 final ship 前不得再修订 §3/§4/§5/§6/§7/§8/§11 Normative table（semantic freeze 延续）。

---

## 附录：Reconciliation Log — v0.1.0 → v0.2.0-rc1（Round 11 dogfood, 2026-04-28）

### A. 变更范围（summary）

| 原 prose | 新 prose | 位置 |
|---|---|---|
| "R6 全部 7 维 / 28 子指标" | "R6 全部 7 维 / 37 子指标" | §3 title intro |
| "### 3.1 7 维 28 子指标清单" | "### 3.1 7 维 37 子指标清单" | §3.1 heading |
| "完整 28 子指标" | "完整 37 子指标"（+ 对齐注记） | §3.2 冻结约束 #2 |
| "按 R6 7 维 / 28 子指标定位瓶颈" | "按 R6 7 维 / 37 子指标定位瓶颈" | §8.1 step 3 |
| "覆盖 MVP 8 项 + 28 项 key 占位" | "覆盖 MVP 8 项 + 37 项 key 占位"（+ 对齐注记） | §8.2 evidence #2 |
| "§3 引用 R6 全部 7 维 / 28 子指标" | "§3 引用 R6 全部 7 维 / 37 子指标"（+ table 注记） | §13.3 bullet 1 |
| "§3 metric key 28 项、§4 阈值表 21 个数" | "§3 metric key 37 项、§4 阈值表 30 个数"（+ 纠正注记） | §13.4 bullet 1 |

### B. 语义不变性（invariant）— §3 / §4 / §5 / §6 / §7 / §8 / §11 Normative 段

| 类别 | v0.1.0 | v0.2.0-rc1 | Diff |
|---|---|---|---|
| §3.1 R6 table rows | T1–T4, C1–C6, L1–L7, G1–G4, U1–U4, R1–R8, V1–V4（计 37） | **同** | 0 bytes |
| §4.1 threshold table | 10 metrics × 3 profiles = 30 数值 cells | **同** | 0 bytes |
| §5.3 router-test matrix | mvp:8 / full:96（intermediate:16 由 template schema 0.1.1 提供） | **同** | 0 bytes |
| §6.1 value vector | 7 axes（task_delta / token_delta / latency_delta / context_delta / path_efficiency_delta / routing_delta / governance_risk_delta） | **同** | 0 bytes |
| §7.2 平台优先级 | Cursor → Claude Code → Codex | **同** | 0 bytes |
| §8.1 8 steps order | profile → evaluate → diagnose → improve → router-test → half-retire-review → iterate → package-register | **同** | 0 bytes |
| §11.1 forever-out | marketplace / router_training / generic IDE compat / Markdown-to-CLI（共 4 项） | **同** | 0 bytes |

> 工作区守则 "No Silent Failures" 要求：本 reconciliation 的所有变化已落盘在：
> (a) 本附录的变更表；
> (b) `.local/dogfood/2026-04-28/round_11/raw/spec_reconciliation.md`；
> (c) `.local/dogfood/2026-04-28/round_11/raw/spec_drift_report.json`。

### C. 证据集（§8.2 6 件 + diff）

- `.local/dogfood/2026-04-28/round_11/basic_ability_profile.yaml` — spec_version v0.2.0-rc1; metrics carried byte-identical from Round 10。
- `.local/dogfood/2026-04-28/round_11/metrics_report.yaml` — 37 keys present；T1=0.85 未回退；C1/C2 verify unchanged (frontmatter bump 0.1.9 → 0.1.10 tokenizer-verified)。
- `.local/dogfood/2026-04-28/round_11/router_floor_report.yaml` — 继承 Round 10 byte-identical (schema 0.1.1)。
- `.local/dogfood/2026-04-28/round_11/half_retire_decision.yaml` — decision=keep；value_vector 7 axis 全部未动。
- `.local/dogfood/2026-04-28/round_11/next_action_plan.yaml` — 指向 Round 12 (§6.4 reactivation detector + v2_tightened readiness)。
- `.local/dogfood/2026-04-28/round_11/iteration_delta_report.yaml` — round_11 vs round_10；governance_risk axis positive_axis=true for drift-removal（spec reconciliation 是 prose 对齐，也属于 governance/drift 治理改进）。

### D. Validator 行为

- `tools/spec_validator.py --json`（default mode）：8/8 PASS — 不变（TABLE counts 37 / 30 与此前一致）。
- `tools/spec_validator.py --strict-prose-count --spec .local/research/spec_v0.2.0-rc1.md`：8/8 PASS（原来 R6_KEYS + THRESHOLD_TABLE 失败因 prose 已对齐而解除）。
- 对 `.local/research/spec_v0.1.0.md` 指定 `--strict-prose-count` 仍会失败（prose 在旧文件中仍写 28/21），这是设计行为——strict-prose-count 的含义是 "prose == table"。

### E. 后续（v0.2.0 final gate）

- Round 12 必须跑 §6.4 reactivation detector 并验证 v2_tightened readiness；两轮 v2 硬门槛 PASS 后才能晋升至 v0.2.0 final。
- `.rules/si-chip-spec.mdc` 与 `AGENTS.md` 已同步至 v0.2.0-rc1；模板 `$schema_version` 未 bump（field semantics 未变 — 仅 prose-count 对齐，backward-compat 保证 Round 1-10 evidence 仍可校验）。

> 修订者注：本 RC 是 Round 11 "spec-reconciliation round" 的产出；v0.2.0 final 由 Round 12 ship gate 决定。
