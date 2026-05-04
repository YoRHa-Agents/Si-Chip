---
title: "Si-Chip Spec"
version: "v0.4.2-rc1"
status: "rc"
effective_date: "2026-05-05"
promoted_from: null
compiled_into_rules: false
supersedes: "v0.4.0"
language: zh-CN
authoritative_inputs:
  - .local/research/r12_v0_4_0_industry_practice.md
  - .local/research/r12.5_real_llm_runner_feasibility.md
  - .local/research/spec_v0.4.0.md
  - .local/research/r11_core_goal_invariant.md
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/SUMMARY.md
absorbed_external_sources:
  - { repo: "addyosmani/agent-skills", version: "v1.0.0", upstream_doc: "docs/skill-anatomy.md", absorbed_into: "§24.1 Description Discipline", absorbed_at: "2026-05-05" }
normative_sections: [3, 4, 5, 6, 7, 8, 11, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24]
informative_sections: [16]
additive_only: true
preserves_byte_identical_v0_4_0: ["§1", "§2", "§3", "§4", "§5", "§6", "§7", "§8", "§9", "§10", "§11", "§12", "§13", "§14", "§15", "§16", "§17.1-§17.6", "§18", "§19", "§20", "§21", "§22", "§23"]
new_normative_sections_v0_4_2: ["§17.7", "§24"]
forever_out_unchanged: true
new_hard_rules: [14]
new_blockers: ["DESCRIPTION_CAP_1024"]
ship_gate_target: v2_tightened
real_llm_runner_in_scope: true
---

# Si-Chip Spec v0.4.2-rc1（rc — additive 1 Normative section + 1 hard rule + 1 BLOCKER absorbed from addyosmani/agent-skills v1.0.0）

> 本文是 Si-Chip 的 rc spec v0.4.2-rc1（candidate for promotion to v0.4.2 frozen）。Authored 2026-05-05; Patch 1 of the v0.5.0 absorption plan.
> Relative to v0.4.0, ADD §24.1 + 1 hard rule (#14) + 1 BLOCKER (#15); §1–§23 byte-identical to v0.4.0; §17.1–§17.6 byte-identical, §17.7 NEW.
> 相对 v0.4.0，仅做加法：新增 §24 Skill Hygiene Discipline (Normative) + §17.7 hard rule 14 (Description cap 1024 chars) + 1 个 spec_validator BLOCKER 15 `DESCRIPTION_CAP_1024`；§1–§23 与 v0.4.0 byte-identical；§17.1–§17.6 byte-identical；forever-out (§11.1) 字节级保留。
> 吸收外源：addyosmani/agent-skills v1.0.0 (push @ 2026-05-03) `docs/skill-anatomy.md` 的 1024-character description cap convention，作为 §24.1 Description Discipline 落地（不引入 marketplace、router-model training、Markdown-to-CLI converter、generic IDE compat 任何边界突破；详见 §24.1 closing prose）。
> §3 / §4-main-table / §5 / §7 / §8-main-list / §11 / §13 / §14 / §15 / §16 / §17.1-§17.6 / §18 / §19 / §20 / §21 / §22 / §23 字节级保留 v0.4.0 内容。
> 内容遵循 R1–R12 证据库 + r12.5 real-LLM 可行性证据 + chip-usage-helper SUMMARY.md R1–R47 实证 + addyosmani/agent-skills v1.0.0 description-discipline 工艺借鉴。
> rc 阶段：本文不进入 `.rules/` 编译，待 v0.4.2 final ship 后晋升（编译期间仍以 spec v0.4.0 frozen 为 active 规则集；v0.4.2-rc1 BLOCKER 15 在 spec_validator 中以 SKIP-pass 模式向 legacy spec backward-compatible 兼容）。
> Pinned historical record: `.local/research/spec_v0.4.0.md`（保留作为 v0.4.2-rc1 的 frozen 上游 baseline，不删除）；`.local/research/spec_v0.4.0-rc1.md` + `.local/research/spec_v0.3.0.md`（保留作为更上游 baseline，不删除）。

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

#### 2.1.2 v0.4.0 add-on field map (forward pointers to §20 / §21 / §23)

v0.4.0 在 `BasicAbility` 顶层 / 子块上 additively 增加 4 组字段，**不修改** §2.1 主 yaml block 的任何已有字段定义；新增字段位置与完整 schema 集中在 §20 / §21 / §23：

| 新字段 / 子块 | 父对象 | 完整 schema 位置 | 性质 |
|---|---|---|---|
| `lifecycle.promotion_history: [{from, to, triggered_by_round_id, triggered_by_metric_value, observer, archived_artifact_path, decision_rationale}]` | `lifecycle` | §20.2 | append-only；每次 stage transition 追加 1 行 |
| `current_surface.dependencies.live_backend: bool` | `current_surface` | §21.2 | OPTIONAL；缺省 false；为 true 时 §21.1 `packaging.health_smoke_check` 变 REQUIRED |
| `packaging.health_smoke_check: [{endpoint, expected_status, max_attempts, retry_delay_ms, sentinel_field, sentinel_value_predicate, axis ∈ {read, write, auth, dependency}, description}]` | `packaging` | §21.1 | OPTIONAL @ schema；REQUIRED-when-live-backend per §21.2 |
| `metrics.<dim>.<metric>_method` / `_ci_low` / `_ci_high` / `metrics.usage_cost.U1_language_breakdown` / `metrics.usage_cost.U4_state` | `metrics` | §23.1–§23.4 | companion fields；不计入 §3.1 R6 7×37 sub-metric count（per §23.6 spec_validator 规则） |

> 与 §2.1 主块的关系：以上 4 组字段同 §2.1.1 `core_goal` 的处理方式一致，**通过 additive extension 进入 `templates/basic_ability_profile.schema.yaml`**（schema_version 0.2.0 → 0.3.0），不破坏 §2.1 主 yaml block byte-identicality。Round 1-15 Si-Chip + Round 1-10 chip-usage-helper 既有证据在 schema_version 0.3.0 下继续校验通过（新增字段在历史 artefact 中 default null + 仅对 Round 16+ 强制 require）。详见 §20.1 stage_transition_table、§21 health_smoke_check 4-axis 工艺、§23 method-tag controlled vocabulary。

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

**v0.4.0 add-on**: token-tier invariant `C7/C8/C9` lives in NEW §18 (top-level, NOT R6 D2.7-9; per Q1 design rationale; 7×37 frozen count unchanged); method-tag companion fields (`<metric>_method`, `_ci_low`, `_ci_high`, U1.language_breakdown, U4.state) live in NEW §23 (not new sub-metrics; companion fields ignored by spec_validator R6_KEYS BLOCKER per Q1).

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

**v0.4.0 add-on**: row 10 `iteration_delta` clause adds an OPTIONAL EAGER-weighted formula `weighted_token_delta = 10×eager_delta + 1×oncall_delta + 0.1×lazy_delta` per §18.2; `eager_token_delta` becomes the 8th §6.1 value_vector axis per Q4 user decision (BREAKS v0.3.0 byte-identicality of §6.1 value_vector axes count); see Reconciliation Log.

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

### 6.1 Value Vector（8 维，v0.4.0；v0.3.0 之前为 7 维）

| 维度 | 公式 | 数据源 |
|---|---|---|
| `task_delta` | `pass_with - pass_without` | R6 T3 |
| `token_delta` | `(tokens_without − tokens_with) / tokens_without` | R6 C4 + OTel |
| `latency_delta` | `(p95_without − p95_with) / p95_without` | R6 L1/L2 |
| `context_delta` | `(footprint_without − footprint_with) / footprint_without` | R6 C1–C5 |
| `path_efficiency_delta` | `(detour_without − detour_with) / detour_without` | R6 L5 |
| `routing_delta` | `trigger_F1_with − trigger_F1_without` | R6 D6 |
| `governance_risk_delta` | `risk_without − risk_with` | R6 D7 |
| `eager_token_delta` | `(eager_tokens_without − eager_tokens_with) / eager_tokens_without` | C7 + OTel via tier decomposition (§18.1) |

**v0.4.0 add-on**: §6.1 value_vector axes count moves from 7 (v0.3.0) to 8 (v0.4.0). The new `eager_token_delta` axis enables §6.2 half-retire decisions to differentiate EAGER vs ON-CALL token wins (per Cycle 2 -55% EAGER win evidence). spec_validator's `VALUE_VECTOR_AXES` BLOCKER expectation is bumped accordingly. Reconciliation Log records this as the FIRST byte-identicality break since v0.1.0 → v0.2.0 prose-count alignment.

### 6.2 三态触发规则

| 决策 | 触发条件 |
|---|---|
| `keep` | `task_delta >= +0.10` 或当前档 (§4) 下全部硬门槛通过 |
| `half_retire` | `task_delta` 近零 (`-0.02 ≤ task_delta ≤ +0.10`) **且** `token_delta` / `latency_delta` / `context_delta` / `path_efficiency_delta` / `routing_delta` 中至少一项达到当前 gate profile 的对应阈值桶 (`v1 ≥ +0.05`, `v2 ≥ +0.10`, `v3 ≥ +0.15`) |
| `retire` | value_vector 全部维度 ≤ 0 **或** `governance_risk_delta < 0` 且超出 §11 风险策略 **或** v3_strict 下连续两轮失败且无任一性能轴改善 |
| `disable_auto_trigger` | `governance_risk_delta` 显著为负，无论其它维度 |

> `half_retire` 触发后必须执行 R9 §3 的简化策略（缩短 description、reference 冷存储、manual-only、降低 routing priority 等），并设置 `next_review_at`（建议 30/60/90 天周期，依简化强度）。

**v0.4.0 add-on**: §6.2 `half_retire` trigger now also fires on `task_delta` near zero AND `eager_token_delta ≥ +0.10` (v2_tightened bucket) for surface-area-shrinking abilities; this is the dedicated EAGER-axis trigger that v0.3.0's pooled `token_delta` could not isolate.

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

**v0.4.0 add-on**: packaging-gate adds health-smoke-check enforcement per §21.4 (REQUIRED when ability declares `current_surface.dependencies.live_backend: true`); ship-eligible declaration requires `health_smoke_check` either (a) absent (no live backend deps) or (b) all declared axes PASS at packaging time.

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

**v0.4.0 add-on**: step 2 `evaluate` gains a Normative sub-step `evaluate-real-data` (defined in §19); the 8-step main list count is unchanged; sub-step is enumerated in §8.1 expansion table (see §19.1 for the 3-layer pattern: msw fixture provenance / user-install / post-recovery live).

### 8.2 每轮最小证据集

每轮 dogfood 必须落盘以下 6 件：

1. `BasicAbilityProfile` (yaml)
2. `metrics_report` (json/yaml，覆盖 MVP 8 项 + 37 项 key 占位；v0.1.0 prose "28 项" 对齐到 §3.1 table 枚举数 37)
3. `router_floor_report` (yaml)
4. `half_retire_decision` (yaml)
5. `next_action_plan` (yaml)
6. `iteration_delta_report` (yaml，与上一轮比对，至少含一项效率轴正向 delta)

**v0.3.0 add-on**: §15 introduces a 7th evidence sentinel `round_kind` field on `next_action_plan.yaml`; this is a field-level addition, not a 7th file.

**v0.4.0 add-on**: when `next_action_plan.round_kind == 'ship_prep'`, evidence file count is 7 (the 7th file is `ship_decision.yaml` per §20.4); when `round_kind ∈ {code_change, measurement_only, maintenance}`, evidence count remains 6.

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

**v0.4.0 add-on**: 5 NEW templates (`lazy_manifest.template.yaml`, `feedback_real_data_samples.template.yaml`, `ship_decision.template.yaml`, `recovery_harness.template.yaml`, `method_taxonomy.template.yaml`) + 1 NEW Informative reference (`eval_pack_qa_checklist.md`) extend the factory contract additively; existing 6 templates' `$schema_version` bumps 0.2.0 → 0.3.0 (BAP schema gains §20.2 `lifecycle.promotion_history` / §21.1 `packaging.health_smoke_check` / §23 method-tag companions; iteration_delta_report gains §18.6 `tier_transitions` block + 8-axis value_vector; next_action_plan gains §15-sibling `token_tier_target` field).

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

**v0.4.0 add-on**: `.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/` is the canonical CI-replayable cache directory for real-LLM eval runs (per §22.6); cache key shape `sha256(model + prompt + system + sample_idx)[:16]` per r12.5 spike validation (Stage 1 PROCEED_MAJOR verdict).

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

**v0.4.0 add-on (re-affirmation)**: §18 token-tier invariant, §19 real-data verification, §20 lifecycle state-machine, §21 health smoke check, §22 eval-pack curation, §23 method-tagged metrics, real-LLM runner under `evals/si-chip/runners/`, all introduce NO new distribution surface, NO router-model training, NO generic IDE compat, NO Markdown-to-CLI converter. See §18.7 / §19.6 / §20.6 / §21.6 / §22.7 / §23.7 forever-out re-checks.

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

**v0.4.0 add-on**: this v0.4.0-rc1 is NOT yet compiled into `.rules/`; ship-time L0 step (Stage 8 of v0.4.0 plan) flips `compiled_into_rules: true` and re-runs `.rules/compile-config.yaml`. §17 hard rules grow 10 → 13 (rules 11/12/13 land; spec_validator BLOCKER count grows 11 → 14; SCRIPT_VERSION bumps 0.2.0 → 0.3.0).

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

**v0.4.0 add-on**: when spec_validator is invoked against v0.4.0+ specs, §13.4 prose "§6.1 value_vector 7 项" is overridden by §13.6.4 which expects 8 axes (`EXPECTED_VALUE_VECTOR_AXES_BY_SPEC["v0.4.0"] = 8`). The v0.3.0 prose preserves byte-identicality for backward-compat spec_validator invocations against v0.3.0 spec (which still expects 7).

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

### 13.6 Acceptance Criteria for v0.4.0-rc1（NEW additive subsection；v0.4.0）

> 本子节是 v0.4.0-rc1 ship gate add-on，与 §13.1–§13.5 并列。覆盖 v0.4.0 新增的 §18 / §19 / §20 / §21 / §22 / §23 + §17 rules 11/12/13 + §6.1 axes 7→8 break。§13.1–§13.5 主体内容字节级保留 v0.3.0；本小节仅做加法。

#### 13.6.1 结构与表达

- v0.4.0-rc1 在 v0.3.0 之上新增 §18（Token-Tier Invariant，Normative）、§19（Real-Data Verification，Normative）、§20（Stage Transitions & Promotion History，Normative）、§21（Health Smoke Check，Normative）、§22（Eval-Pack Curation Discipline，Normative）、§23（Method-Tagged Metrics，Normative）；spec 章节总数从 17 → 23（同 v0.2.0 → v0.3.0 的 13 → 17 跳步）。
- §3 / §4-main-table / §5 / §7 / §8-main-list / §11 / §13 / §14 / §15 / §16 / §17 主体内容字节级保留 v0.3.0；每章最多追加 **1 句** "v0.4.0 add-on" 注记，无其它修改（§6 / §8 例外详见 §13.6.3）。
- §13.1–§13.5 主体内容字节级保留 v0.3.0；本 §13.6 为 v0.4.0 新增 additive 子节，与 §13.1–§13.5 并列。
- 中文为主；英文仅用于专有名词、API、文件路径、字段 key（与 §13.1 / §13.5.1 一致）。
- §6.1 value_vector axes 7 → 8 是 v0.1.0 → v0.2.0 prose-count alignment 之后的 **第一次** byte-identicality 破坏；reconciliation log 显式记录 (per §13.6.3 Reconciliation Log entry (c) below)。

#### 13.6.2 Normative 内容守护

- **§18** 显式锁定 `token_tier: {C7/C8/C9}` 顶层 invariant（NOT R6 D2.7-9；R6 7×37 frozen count 不破 per §18.7 / §23.6）；EAGER-weighted `iteration_delta` formula OPTIONAL (§18.2)；R3 split (§18.3 + §23.5) 是 method-quality primitives；prose_class taxonomy Informative @ v0.4.0 (§18.4)；`lazy_manifest` packaging gate Normative (§18.5)；`tier_transitions` block additive extension (§18.6)。
- **§19** 显式锁定 real-data verification 作为 §8.1 step 2 `evaluate` 的 Normative sub-step（NOT 9th step；§8.1 8-step main list count 不变 per §19.1）；`feedback_real_data_samples.yaml` schema 字段集合 `{endpoint, request_params, response_json, observed_state, captured_at, observer}` (§19.2)；fixture-citation rule 用 `// real-data sample provenance: <captured_at> / <observer>` 注释格式 grep-able (§19.3)；user-install + post-recovery live verification 工作流 (§19.4 + §19.5)。
- **§20** 显式锁定 `stage_transition_table` Normative，每行 `from_stage → to_stage` 含 required-conditions (§20.1)；`lifecycle.promotion_history` append-only block 字段 `{from, to, triggered_by_round_id, triggered_by_metric_value, observer, archived_artifact_path, decision_rationale}` (§20.2)；`metrics_report.yaml.promotion_state: {current_gate, consecutive_passes, promotable_to, last_promotion_round_id}` first-class top-level key (§20.3)；`ship_decision.yaml` 是 §8.2 第 7 个 evidence file when `round_kind == 'ship_prep'` (§20.4)。
- **§21** 显式锁定 `BasicAbility.packaging.health_smoke_check` 字段 schema (§21.1)；`current_surface.dependencies.live_backend: true` MAKES `packaging.health_smoke_check` 非空 REQUIRED (§21.2)；4-axis taxonomy `{read, write, auth, dependency}` 完备 (§21.3)；packaging-gate enforcement at §8.1 step 8 (§21.4)；OTel semconv extension `gen_ai.tool.name=si-chip.health_smoke` (§21.5)。
- **§22** 显式锁定 40-prompt minimum gate for v2_tightened promotion (§22.1；v1_baseline 仍为 20-prompt MVP)；G1 `provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` REQUIRED first-class (§22.2)；`templates/eval_pack_qa_checklist.md` Informative reference (§22.3)；`templates/recovery_harness.template.yaml` for T4 (§22.4)；deterministic seeding rule `hash(round_id + ability_id)` (§22.5；§3.2 frozen constraint 4 → 5)；real-LLM cache directory (§22.6)。
- **§23** 显式锁定 `<metric>_method` companion fields enumerated per metric (§23.1；`templates/method_taxonomy.template.yaml` 控制 controlled vocabulary)；`_ci_low / _ci_high` confidence band fields for char-heuristic-derived token metrics (§23.2)；U1 `language_breakdown` (§23.3)；U4 `state ∈ {warm, cold, semicold}` (§23.4)；R3 split cross-listed from §18.3 (§23.5)；spec_validator's `R6_KEYS` BLOCKER ignores companion suffixes (§23.6)。
- **§17** 仅承载 v0.4.0 新增的 **3 条** hard rules (rule 11/12/13)；v0.2.0 的 8 条 + v0.3.0 的 2 条 + v0.4.0 的 3 条 = 13 hard rules 在 ship 时合并 (10 → 13 rules)。

#### 13.6.3 横向一致性

- **§18 ↔ §6.1**: 8th axis `eager_token_delta` 公式引用 §18.1 C7 数据源；§4.1 row 10 v0.4.0 add-on 的 EAGER-weighted formula 引用 §18.2；`token_tier` 与 §14 C0 顶层 invariant 类型同构 (§18.7 / §23.6 保证 R6 7×37 不破)。
- **§19 ↔ §8.1 step 2 `evaluate`**: §8.1 8-step main list count 不变；§19 是 step 2 的 Normative sub-step；`tools/eval_skill.py` `--real-data-only / --synthetic-only / --both` flag 是 §19 实现 surface (Stage 4 Wave 1c)。
- **§20 ↔ §15 round_kind**: §20.4 `ship_decision.yaml` 仅在 `round_kind == 'ship_prep'` 时作 evidence file #7；§8.2 v0.4.0 add-on 6/7 conditional 子句指向本节；`promotion_state` 与 §4.2 promotion rule 互引。
- **§21 ↔ §7 packaging gate**: §7.3 v0.4.0 add-on 子句指向 §21.4；§8.1 step 8 `package-register` health-smoke pre-ship gate 同源；`health_smoke_check` 与 §21.2 `live_backend` 形成 conditional REQUIRED (BLOCKER `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`)。
- **§22 ↔ §3.2 frozen constraints**: §3.2 count 4 → 5（新增 #5 deterministic seeding，§22.5 完整定义）；§22.4 `recovery_harness.template.yaml` 是 T4 canonical generator；§22.2 G1 `provenance` REQUIRED 与 §23.1 method-tag 同源工艺。
- **§23 ↔ §3.1 R6**: method-tag companion fields 与 §3.1 R6 7×37 sub-metrics 是 1-to-1 平行附属，但 `R6_KEYS` BLOCKER 不计入 (§23.6)；`R6_KEYS_BY_SCHEMA` 在 spec_validator 中扩展支持 method-tag 后缀。
- **§17 rules 11/12/13 ↔ spec_validator BLOCKERs**: rule 11 ↔ `TOKEN_TIER_DECLARED_WHEN_REPORTED`；rule 12 ↔ `REAL_DATA_FIXTURE_PROVENANCE`；rule 13 ↔ `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND` (一一对应)。

#### 13.6.4 机器可校验项

下一阶段（Stage 4 Wave 1b）`tools/spec_validator.py` 必须能加载 `--spec .local/research/spec_v0.4.0-rc1.md` 并通过 11 + 3 = **14 个 BLOCKER**（v0.3.0 的 11 个 BLOCKER 不变 + v0.4.0 新增 3 个）：

- 既有 11 个 BLOCKER（来自 v0.3.0 ship 状态）：BAP_SCHEMA_KEYS / R6_KEYS / THRESHOLD_TABLE / VALUE_VECTOR / PLATFORM_PRIORITY / DOGFOOD_STEPS / EVIDENCE_FILES / FOREVER_OUT / REACTIVATION_DETECTOR_EXISTS / CORE_GOAL_FIELD_PRESENT / ROUND_KIND_FIELD_PRESENT_AND_VALID — 在 v0.4.0-rc1 spec 上必须继续 11/11 PASS（其中 VALUE_VECTOR 与 EVIDENCE_FILES 的 expected 值为 v0.4.0 修订版，详见下文）。
- 新增 BLOCKER 12：**`TOKEN_TIER_DECLARED_WHEN_REPORTED`** —— 当 `metrics_report.yaml.metrics` 中存在任一 `C7_eager_per_session / C8_oncall_per_trigger / C9_lazy_avg_per_load` 子键时，`metrics_report.yaml.token_tier` 顶层 block 必须三键全在（C7/C8/C9 placeholder 允许 null，但 key 必须 in 位）；缺失 = FAIL。
- 新增 BLOCKER 13：**`REAL_DATA_FIXTURE_PROVENANCE`** —— 每当 ability 在 `feedback_real_data_samples.yaml` 中声明 `real_data_samples` 时，对应 ability 的 test fixture 文件（grep `tests/**/*.test.* tests/**/*.spec.*`）必须含注释 `// real-data sample provenance: <captured_at> / <observer>`（grep-able audit trail）；缺失 = FAIL。
- 新增 BLOCKER 14：**`HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`** —— 当 `BasicAbilityProfile.basic_ability.current_surface.dependencies.live_backend: true` 时，`BasicAbilityProfile.basic_ability.packaging.health_smoke_check` 必须非空 array；缺失或空数组 = FAIL。
- **修订** BLOCKER `VALUE_VECTOR_AXES`：v0.4.0+ expected = 8 axes（v0.3.0 之前 = 7 axes；spec_validator 按 spec frontmatter `version` 字段切换 expected count）。`EXPECTED_VALUE_VECTOR_AXES_BY_SPEC["v0.4.0-rc1"] = {task_delta, token_delta, latency_delta, context_delta, path_efficiency_delta, routing_delta, governance_risk_delta, eager_token_delta}`。
- **修订** BLOCKER `EVIDENCE_FILES`：v0.4.0+ conditional based on `next_action_plan.round_kind`：当 `round_kind == 'ship_prep'` 时 expected count = 7（含 `ship_decision.yaml`）；其它 round_kind expected count = 6（与 v0.3.0 相同）。
- **修订** BLOCKER `R6_KEYS`：v0.4.0+ ignore companion suffixes `_method` / `_ci_low` / `_ci_high` / `_language_breakdown` / `_state` 等 method-tag companion keys（不计入 7×37 = 37 sub-metric count）；`R6_KEYS_BY_SCHEMA` 扩展以承载 §23 method-tag taxonomy。
- `--strict-prose-count` 模式：`SUPPORTED_SPEC_VERSIONS` 加入 `v0.4.0-rc1` 与 `v0.4.0`；`EXPECTED_R6_PROSE_BY_SPEC["v0.4.0-rc1"] = 37` 与 `EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.4.0-rc1"] = 30`（继承 v0.3.0 的 reconciled 计数；v0.4.0-rc1 §13.4 byte-identical 保留 v0.3.0 §13.4 整段，因此 anchor `§3 metric key 37 项` 与 `§4 阈值表 30 个数` 自动满足）。
- Round 1-15 Si-Chip + Round 1-10 chip-usage-helper 既有证据在 v0.4.0-rc1 spec 下继续 PASS（向下兼容契约延续；新增字段在历史 artefact 中 default null + 仅对 Round 16+ 的 Si-Chip / Round 26+ 的 chip-usage-helper 强制 require；schema_version 0.1.0 / 0.2.0 / 0.3.0 同时被 templates 接受）。
- spec_validator 的 `SCRIPT_VERSION` 由 0.2.0 bump 至 0.3.0（标记 v0.4.0-rc1 BLOCKER 集合扩展）；6 个既有 templates 的 `$schema_version` 由 0.2.0 bump 至 0.3.0；5 个 NEW templates 的 `$schema_version` 起始 0.1.0。

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

**v0.4.0 add-on**: §6.1 value_vector has moved to 8 axes in v0.4.0 (adds `eager_token_delta`); the §14.5.2 "value_vector orthogonal to C0" principle still applies to all 8 axes. See Reconciliation Log entry (c).

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

**v0.4.0 add-on**: chip-usage-helper Round 26 under v0.4.0 spec (Stage 7 of v0.4.0 plan) is the second-ability witness that promotes §16 from Informative to **Normative target v0.4.x** once the round lands cleanly (combined with Si-Chip Round 16-17 self-dogfood, this gives the "2 abilities × 2 consecutive ships" evidence required by §16.3 promotion trigger).

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

### 17.4 Rule 11 — `token_tier` block 声明 (NEW v0.4.0)

**MUST** declare `token_tier: {C7_eager_per_session, C8_oncall_per_trigger, C9_lazy_avg_per_load}` block in `metrics_report.yaml` when ANY token-tier sub-axis is reported (C7/C8/C9 placeholders required if tier-axis is observed).

具体绑定：

- 每个 `metrics_report.yaml` 在 `metrics` 同级（顶层）必须含 `token_tier` block，键集合 `{C7_eager_per_session, C8_oncall_per_trigger, C9_lazy_avg_per_load}` 三个子键全在；未观测的子键以 `null` 显式占位（per §3.2 frozen constraint #2 同源工艺）。
- `token_tier` 是 **顶层 invariant**，**不计入** R6 7×37 子指标（per §18.1 placement rationale；与 §14.5 C0 placement 类型同构）；spec_validator 把 `TOKEN_TIER_DECLARED_WHEN_REPORTED` 作为 BLOCKER 12（per §13.6.4 与 Stage 4 Wave 1b spec_validator 扩展）。
- `token_tier` 数据源：C7 来自 EAGER 路径 OTel attribute（每 session 始终加载的 metadata + always-apply rules），C8 来自 ON-CALL 路径 OTel attribute（trigger 后加载的 SKILL body + references），C9 来自 LAZY 路径 OTel attribute（按需加载的 resources / `.lazy-manifest` 项）。详见 §18.1 worked examples。
- 当 ability 跑过任何含 token-tier 维度的 measurement（即 `metrics.token_tier.C7 / C8 / C9` 三键中至少一个非 null），完整 3 键 block 必须在场。
- EAGER-weighted `iteration_delta` formula `weighted_token_delta = 10×eager_delta + 1×oncall_delta + 0.1×lazy_delta` 是 OPTIONAL，按需在 `iteration_delta_report.yaml` 里 emit（per §18.2）。

### 17.5 Rule 12 — Real-data sample provenance (NEW v0.4.0)

**MUST** cite real-data sample provenance in test fixture filenames or in-file comments when ability has `real_data_samples` declared in `feedback_real_data_samples.yaml`.

具体绑定：

- 当 ability 在 `feedback_real_data_samples.yaml` 中 declare `real_data_samples: [{endpoint, request_params, response_json, observed_state, captured_at, observer}]` 数组（per §19.2 schema），对应 ability 的 test fixture 文件（grep `tests/**/*.test.* tests/**/*.spec.*` 或 ability 实现树等价 test 路径）必须含至少一行注释 `// real-data sample provenance: <captured_at> / <observer>` （或语言适用的同义注释格式：Python `# real-data sample provenance: ...`，Markdown `<!-- real-data sample provenance: ... -->`）。
- spec_validator 把 `REAL_DATA_FIXTURE_PROVENANCE` 作为 BLOCKER 13（per §13.6.4 与 Stage 4 Wave 1b spec_validator 扩展）：grep ability 的 test 文件树，缺失任一 `real-data sample provenance` 注释 = FAIL。
- `<captured_at>` 必须是 ISO 8601 timestamp（e.g. `2026-04-29T14:32:00Z`）；`<observer>` 必须是可识别的人名或 agent id（e.g. `yorha@anthropic.local` 或 `chip-usage-helper-cycle5-author`）。
- fixture-citation 的目的是 **grep-able audit trail**：post-ship reviewer 可以 `grep -r "real-data sample provenance" tests/` 一键溯源所有 production-payload-derived fixtures，按 captured_at 时序排序。这是 §19.3 fixture-citation rule 的 hard binding。
- 如果 ability **没有** declare `real_data_samples`（即 `feedback_real_data_samples.yaml` 不存在或 `real_data_samples` 数组为空），则 BLOCKER 跳过（PASS by absence）；这适用于纯 synthetic-fixture ability（如 Si-Chip self-dogfood，无 live backend）。

### 17.6 Rule 13 — `health_smoke_check` declaration (NEW v0.4.0)

**MUST** declare non-empty `packaging.health_smoke_check` array when `current_surface.dependencies.live_backend: true`.

具体绑定：

- 每个 `BasicAbilityProfile` 在 `current_surface.dependencies.live_backend: true` 时（即 ability 依赖 live backend，例如 chip-usage-helper 依赖 ai-bill `events/health` 端点），`packaging.health_smoke_check` 必须是非空数组，每个元素满足 §21.1 schema：`{endpoint, expected_status, max_attempts, retry_delay_ms, sentinel_field, sentinel_value_predicate, axis ∈ {read, write, auth, dependency}, description}`。
- spec_validator 把 `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND` 作为 BLOCKER 14（per §13.6.4 与 Stage 4 Wave 1b spec_validator 扩展）：`live_backend: true` AND `health_smoke_check` 缺失或空数组 = FAIL。
- §8.1 step 8 `package-register` 在 v0.4.0 后期（per §21.4 packaging-gate enforcement）必须 (a) 跑所有 declared axes 的 health smoke probe；(b) 记录 pass/fail 结果到 `.local/dogfood/<DATE>/<round_id>/raw/health_smoke_results.yaml`；(c) ship-eligible declaration 要求所有 axes PASS。
- 4-axis taxonomy `{read, write, auth, dependency}` 完备覆盖 production smoke 工业模式（per §21.3 引用的 fitgap post-deploy verification 4-axis pattern）；至少一个 `axis: dependency` 是 chip-usage-helper Cycle 5 v0.9.0 zero-events bug 的直接修复（ai-bill `events/health` `latestTsMs > 0` sentinel）。
- 如果 ability **没有** live backend dependency（即 `live_backend: false` 或 `live_backend` 字段缺失），则 BLOCKER 跳过（PASS by absence）；这适用于纯本地 ability（如 Si-Chip self-dogfood，无外部依赖）。

### 17.7 Rule 14 — Description cap 1024 chars (NEW v0.4.2)

**MUST** cap each `BasicAbility.description` (and any `SKILL.md` frontmatter `description`) at ≤ 1024 characters per spec §24.1; spec_validator BLOCKER 15 `DESCRIPTION_CAP_1024` enforces.

具体绑定：

- 每个 `SKILL.md` (源 `.agents/skills/<name>/SKILL.md` 与镜像 `.cursor/skills/<name>/SKILL.md` + `.claude/skills/<name>/SKILL.md`) 的 YAML frontmatter `description` 字段必须 ≤ 1024（per §24.1 binding cap convention `min(len(s), len(s.encode('utf-8')))`；CJK 与混合语言 ability 走字符数那一支，避免被 UTF-8 byte expansion 误伤）。
- 每个 `BasicAbilityProfile.basic_ability.description` 字段（OPTIONAL；schema 不要求 required）若 present 必须遵守同一 cap；absent 时 spec_validator 回退检查 `basic_ability.intent`（intent 在 §2.1 schema 是 REQUIRED，作为 description 缺位时的语义代理；intent 通常远短于 1024，spec_validator 给出超长警示但仍按 BLOCKER 处理 hard FAIL）。
- description 必须满足 "what + when" 双语义（"what" = 这个 ability 解决什么；"when" = 什么时候触发它）；**禁止** 把 SKILL body / step-by-step workflow / How To 段落塞进 description（这是 description discipline 的核心；详见 §24.1 prose）。
- spec_validator 把 `DESCRIPTION_CAP_1024` 作为 BLOCKER 15（per §13.6.4 与 Stage 4 Wave 1d spec_validator 扩展）：grep `.agents/skills/*/SKILL.md` + `.cursor/skills/*/SKILL.md` + `.claude/skills/*/SKILL.md` 与 `.local/dogfood/**/round_*/basic_ability_profile.yaml`，提取 description / intent，超过 cap = FAIL。
- BLOCKER 15 在以下情况 SKIP-as-PASS：(a) 仓库内没有 SKILL.md 与 BasicAbilityProfile（pre-bootstrap repo）；(b) 当前 `--spec` 目标不含 §24 marker（即 spec 不是 v0.4.2-rc1+，pre-v0.4.2 artefact 兼容；按 §13.6.4 grace period 同源工艺执行）。

> 与 §17.1–§17.6 v0.3.0/v0.4.0 的 5 条 hard rules 的关系：本 §17.7 (rule 14) 是 **additive**，不替换、不修改 v0.4.0 rules 11/12/13 中任何一条，也不替换 v0.3.0 rules 9/10 / v0.2.0 8 条中任何一条。四套规则（v0.2.0 8 + v0.3.0 2 + v0.4.0 3 + v0.4.2 1 = 14 rules）在 ship 时统一编译进 AGENTS.md §13；冲突解读时仍以 workspace rules（如 "No Silent Failures"、"Mandatory Verification"、"Protected Branch Workflow"）为更高优先级，但不得借此绕过 §17 的 Normative 段。

---

## 18. Token-Tier Invariant（Normative，NEW v0.4.0）

**Normative.** 每个 `BasicAbility` 当报告 token usage 时必须按 EAGER / ON-CALL / LAZY 三层 decompose。该三层 (`C7/C8/C9`) 是 **顶层 invariant**，**不进入** R6 D2 sub-metric set（per §3.1 R6 7×37 frozen count；与 §14.5 C0 placement 类型同构）。本章节由 r12 §2.1 + §4.1 设计推论而来；动机：chip-usage-helper Cycle 2-3（Round 14 -55% EAGER win + Cycle 3 first-run total -33%）暴露 R6 现有的 `C1 metadata + C4 footprint` 框架把 EAGER（每 session 始终付费）与 ON-CALL（trigger 后一次性付费）混在一起，无法区分 user-impact 量级。Anthropic 官方 Skill 文档明确的三档 progressive disclosure (Metadata ~100 tokens / Instructions <500 lines / Resources unlimited) 是同构概念（详见 r12 §2.1.b）。

### 18.1 `token_tier` 字段 schema 与 worked examples

`token_tier` 是 `metrics_report.yaml` 顶层 **REQUIRED-when-reported** block，与 `metrics` (R6 7-dim) 同级 / 与 `core_goal` (§14) 同级。

#### 18.1.1 Schema sketch (additive on `metrics_report.yaml`)

```yaml
# metrics_report.yaml
spec_version: "v0.4.0-rc1"
round_id: "round_<N>"
ability_id: "<id>"

metrics:
  ...                                          # existing 7 R6 dimensions per §3.1
  core_goal:                                   # NEW v0.3.0 top-level dim per §14.3
    C0_core_goal_pass_rate: 1.0
    ...

token_tier:                                    # NEW v0.4.0 top-level invariant per §18.1
  C7_eager_per_session: <int|null>             # tokens always paid per agent session (metadata + always-apply rules + AGENTS.md fragments)
  C7_eager_per_session_method: tiktoken|char_heuristic|llm_actual   # method tag per §23.1
  C8_oncall_per_trigger: <int|null>            # tokens paid once per skill trigger (SKILL.md body + references loaded on activation)
  C8_oncall_per_trigger_method: tiktoken|char_heuristic|llm_actual
  C9_lazy_avg_per_load: <int|null>             # avg tokens per LAZY load (resources/ files; only when explicitly read)
  C9_lazy_avg_per_load_method: tiktoken|char_heuristic|llm_actual
  measured_with_sessions: <int>                # number of agent sessions sampled to compute C7
  measured_with_triggers: <int>                # number of trigger events sampled to compute C8
  measured_with_lazy_loads: <int>              # number of LAZY-tier reads sampled to compute C9
```

#### 18.1.2 Worked examples — Si-Chip self vs chip-usage-helper (post-Cycle 2/3)

| Tier | Si-Chip self (Round 14 sampled) | chip-usage-helper (post-Cycle 2/3) | rationale |
|---|---:|---:|---|
| `C7_eager_per_session` (tiktoken) | 2843 | 365 | Si-Chip = AGENTS.md + always-apply bridge .mdc; chip-usage-helper = post-Cycle 2 -447 vs v0.7.0 (-55% EAGER win) |
| `C8_oncall_per_trigger` (tiktoken) | 4612 | 7338 | Si-Chip = SKILL.md + 5 references/*.md; chip-usage-helper = SKILL.md body + rules/usage-helper.mdc post-Cycle 3 slim |
| `C9_lazy_avg_per_load` (tiktoken) | 1850 | 3281 | Si-Chip = avg of 3 scripts/*.py + occasional templates; chip-usage-helper = max compact `get_dashboard_data` payload (top-10) |
| `measured_with_{sessions, triggers, lazy_loads}` | {14, 9, 4} | {25, 18, 12} | sampling depth; trigger-rate 64% (Si-Chip) vs 72% (chip-usage-helper) |

> 注意：C7 / C8 / C9 reportable 表示 ability 已经测过 token-tier 维度。如果 ability 暂未做 tier decomposition（例如 v0.4.0 ship 前的 Si-Chip Round 14 之前），三键以 `null` 占位、measurement_with_* 字段为 0；spec_validator BLOCKER 12 (`TOKEN_TIER_DECLARED_WHEN_REPORTED`) 跳过（PASS by absence of any reported axis）。

### 18.2 EAGER-weighted `iteration_delta` formula (extends §4.1 row 10)

§4.1 row 10 现有的子句 "iteration_delta (一项效率轴) ≥ +0.05 (v1) / +0.10 (v2) / +0.15 (v3)" 在 v0.4.0 加上 OPTIONAL 的 EAGER-weighted formula：

```text
weighted_token_delta = 10 × eager_delta + 1 × oncall_delta + 0.1 × lazy_delta
```

其中:

- `eager_delta = (C7_without − C7_with) / C7_without` （正值 = EAGER token reduction）
- `oncall_delta = (C8_without − C8_with) / C8_without`
- `lazy_delta = (C9_without − C9_with) / C9_without`

#### 18.2.1 Why 10 / 1 / 0.1 weights

EAGER tokens 每个 agent session 都付一次（Cursor 默认每个 conversation 都 load AGENTS.md + always-apply rules）；ON-CALL tokens 每次 skill trigger 付一次（典型 ratio: 1 trigger : ~10 sessions）；LAZY tokens 仅在 explicit read 时付（典型 ratio: 1 LAZY load : ~10 triggers : ~100 sessions）。10 / 1 / 0.1 weights 把单 token 的 cumulative-payment 频率乘进去，让 weighted_token_delta 反映实际 user-impact 量级。chip-usage-helper Cycle 2 Round 14 的 `EAGER -447 / ON-CALL +407` 净改变在 weighted formula 下 = `10×(447/812) + 1×(-407/8017) + 0` ≈ `5.50 - 0.05 = +5.45`（remarkable EAGER win）；如果按 v0.3.0 spec 的 pooled `token_delta`（C4-only），同一改动反而看起来近似零。

#### 18.2.2 Existing axis-bucket clause unchanged

§4.1 row 10 的现有子句 "≥1 axis at gate bucket" **仍然适用**：legacy 7 axes（task/token/latency/context/path_efficiency/routing/governance_risk）+ 新加的 `eager_token_delta`（per §6.1 v0.4.0 modification）任一达到 v1/v2/v3 的对应阈值桶 = 满足 row 10。EAGER-weighted formula 是 **headline metric** 用于 PR review / on-call dashboard，不替代任何 axis-bucket 判定。

### 18.3 R3 split: `R3_eager_only` + `R3_post_trigger` (extends §3.1 D6 R3)

§3.1 D6 R3 现行 `trigger_F1` 把 "ability 是否被选中" 和 "ability 被选中后是否完成 trigger" 混在一起。v0.4.0 拆分为 2 个 sibling sub-metrics：

- **`R3_eager_only`**: 只看 EAGER-tier prose 触发。eval pack 的 `should_trigger` prompt 在仅看 ability description (C7-EAGER 部分) 的 routing 模型下命中率。
- **`R3_post_trigger`**: 看完整 EAGER + ON-CALL prose 触发。eval pack 的 `should_trigger` prompt 在 ability 已经被 attempt-trigger 后（ON-CALL prose 已 load）的执行率。

两者 union ⇒ legacy `R3_trigger_F1` 兼容（`R3 = harmonic_mean(R3_eager_only, R3_post_trigger)`）。

#### 18.3.1 Why this split (chip-usage-helper Cycle 2 evidence)

chip-usage-helper Round 14 EAGER -447 / ON-CALL +407 的对调表面看像 zero-net token 变化，实则是 **prose 从 EAGER 移到 ON-CALL**：description 变短（routing 更依赖 trigger 词命中而非 description hint），SKILL.md 主体变长（trigger 后能给出更准确的 step-by-step）。如果只看 `R3_trigger_F1`，看不到这个 trade-off 是 net 改善还是 net 倒退；split 之后可以分别看 R3_eager_only（应该几乎不动，因为 trigger 词没改）与 R3_post_trigger（应该上升，因为 SKILL.md 更长更准）。

#### 18.3.2 spec §3.1 D6 R3 row 增 2 行 prose（不修改 R3 sub-metric count）

§3.1 D6 R3 sub-metric 仍然算 1 个（保持 R6 7×37 frozen count），prose 增 2 行说明：

```text
| **D6 Routing Cost** | R1 trigger_precision / R2 trigger_recall / R3 trigger_F1 / R4 near_miss_FP_rate / R5 router_floor / R6 routing_latency_p95 / R7 routing_token_overhead / R8 description_competition_index | R3, R5 |
                                                              ^^^^^^^^^^^^^^^^^^
                                                              v0.4.0 §18.3 split:
                                                              R3 = harmonic_mean(R3_eager_only, R3_post_trigger)
                                                              method-tag companion: R3_eager_only_method ∈ {real_llm_sweep, deterministic_simulation}
```

### 18.4 `prose_class` taxonomy (Informative @ v0.4.0)

`prose_class ∈ {trigger, contract, recipe, narrative}` 是 `SKILL.md` section annotation 工艺：

- **`trigger`**: 让 routing 模型决定 "是不是该 trigger 这个 skill" 的 prose（description 关键词、example 用户 prompts）。**只有 trigger 类 prose 影响 R3 / R4。** 这部分进 EAGER tier（C7）。
- **`contract`**: ability 的 functional contract / Pact-style assertions / I/O schema。这部分通常进 ON-CALL tier（C8）。
- **`recipe`**: step-by-step instructions for the ability to follow once triggered。这部分进 ON-CALL tier（C8）。
- **`narrative`**: 长篇背景解释、history、design rationale。**应该进 LAZY tier（C9）**，但实际中常错放到 ON-CALL，导致 C8 偏高。

#### 18.4.1 Adoption rule

`prose_class` 在 v0.4.0 是 **Informative**：ability 作者可以在 SKILL.md section heading 旁标注 `<!-- prose_class: trigger -->`，但不强制。`tools/eval_skill.py`（v0.4.0+）会 grep 这些 annotations 并报告 prose-class breakdown。

#### 18.4.2 Promotion to Normative trigger

满足下面 **任一** 触发 §16.3 同源工艺的 promotion-to-Normative 决策：

1. ≥2 abilities 在 v0.4.x ship 中 adopt `prose_class` annotations on ≥80% of SKILL.md sections。
2. 1 个 ability 在两个 consecutive ships（v0.4.x → v0.4.y）中 demonstrate `prose_class`-driven re-tiering 带来 ≥+0.10 weighted_token_delta（per §18.2 formula）。

满足 → bump v0.4.x，把 §18.4 从 Informative 升 Normative，并在 spec_validator 加 `PROSE_CLASS_ANNOTATED` BLOCKER（要求每个 ability SKILL.md 至少 50% sections 含 prose_class annotation）。

### 18.5 `lazy_manifest` packaging gate (Normative)

`templates/lazy_manifest.template.yaml` 是 v0.4.0 NEW template。每个 ability 的 source-of-truth 目录（`.agents/skills/<id>/`）下可以放一个 `.lazy-manifest` 文件，声明哪些 sibling 文件属于 LAZY tier (C9)。

#### 18.5.1 `.lazy-manifest` 文件 schema

```yaml
# .agents/skills/<id>/.lazy-manifest
$schema_version: "0.1.0"
$spec_section: "v0.4.0 §18.5"

ability_id: "<id>"
declared_at: "YYYY-MM-DD"

lazy_files:
  - path: "references/long-history.md"
    avg_tokens: 1200
    rationale: "Historical context; only loaded when user explicitly asks for design background."
  - path: "scripts/recover.py"
    avg_tokens: 850
    rationale: "Recovery harness; only loaded by error-recovery flow (per §22.4)."
  - path: "templates/large-canvas-template.yaml"
    avg_tokens: 2400
    rationale: "Heavy canvas template; only loaded when user requests rendered output."
```

#### 18.5.2 packaging-gate enforcement

§8.1 step 8 `package-register` 在 v0.4.0 后扩展：

1. 读取 ability source 目录下的 `.lazy-manifest`（如存在）。
2. 验证 `lazy_files[*].path` 指向的文件 **不在** 当前平台的 EAGER/ON-CALL load path（即不被 SKILL.md 在 trigger 时直接 load、不被 always-apply 规则 reference）。
3. 如果 verify 失败（即声明为 LAZY 的文件实际在 ON-CALL load path 上），spec_validator 发 WARNING（v0.4.0）/ BLOCKER（v0.4.x，promotion 触发后）。
4. 在 `metrics_report.yaml.token_tier.C9_lazy_avg_per_load` 计算时，仅 average `.lazy-manifest` 中 declared 的文件 token 数（避免把 ON-CALL 当 LAZY 算导致 C9 虚低）。

> chip-usage-helper Round 17 R44 evidence 显示，没有 `.lazy-manifest` 时容易把 700-token reference 错放到 ON-CALL load path；`.lazy-manifest` 是 LAZY tier 的 **source-of-truth declaration**，避免 silent tier creep。

### 18.6 `tier_transitions` block (additive on `iteration_delta_report.template.yaml`)

`iteration_delta_report.template.yaml` 在 v0.4.0 additively 增加 `tier_transitions` block，记录本轮 token 跨 tier 的移动：

```yaml
# iteration_delta_report.yaml
spec_version: "v0.4.0-rc1"
round_id: "round_<N>"
prior_round_id: "round_<N-1>"

tier_transitions:
  - from: EAGER
    to: ON-CALL
    tokens: 447
    reason: "Moved description verbose example sentences from SKILL.md frontmatter (EAGER) to references/examples.md (ON-CALL)."
    net_benefit: positive                       # positive | neutral | negative
  - from: ON-CALL
    to: LAZY
    tokens: 1200
    reason: "Moved long-history.md from references/ explicit-load to .lazy-manifest declaration."
    net_benefit: positive
  - from: LAZY
    to: ON-CALL
    tokens: 60
    reason: "Promoted compact contract.md from LAZY back to ON-CALL because trigger-time clarity outweighed token cost."
    net_benefit: neutral

verdict:
  ...                                           # existing v0.3.0 fields (e.g. core_goal_pass) unchanged
  weighted_token_delta_v0_4_0: +5.45            # OPTIONAL §18.2 headline metric
```

#### 18.6.1 `net_benefit` enum 语义

- **`positive`**: 该 transition 在 §18.2 weighted formula 下贡献 ≥+0.05 / +0.10 / +0.15 (v1/v2/v3) 的 weighted_token_delta。
- **`neutral`**: |delta| < 0.05；通常用于 trigger-clarity 与 token-cost 的 trade-off。
- **`negative`**: 该 transition 在 weighted formula 下贡献 ≤-0.05；只允许在 ship_prep / maintenance round 中（per §15 round_kind 工艺，非 code_change round 不要求 axis improvement），否则触发 §6.2 retire decision review。

#### 18.6.2 OpenSpec 同源工艺

`tier_transitions` 的 `{from, to, tokens, reason, net_benefit}` 结构 mirror OpenSpec 的 ADDED/MODIFIED/REMOVED delta semantics（详见 r12 §2.3.d 引用）。spec 不应该只看 final state（C7/C8/C9 当前数值），而应该看 transitions —— 因为相同的 final state 可能由 "all in ON-CALL" 或 "good split with transitions" 产生，前者难维护、后者表明 tier discipline 已建立。

### 18.7 §11 forever-out re-affirmation

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. `token_tier` block 是 ability 自身 metrics_report 的顶层字段，不引入 distribution surface；`.lazy-manifest` 是 ability source-of-truth 树内文件，不是注册中心；`tier_transitions` 是 iteration_delta_report 内的 audit trail，不是 marketplace listing。 |
| Router 模型训练 | NO. C7/C8/C9 是 token observation，不喂任何模型；`R3_eager_only` / `R3_post_trigger` 是 evaluator metric split，依旧落在 §5.1 允许的 "metadata 检索 / kNN baseline / description 优化 / thinking-depth escalation / fallback policy" 范畴内。 |
| 通用 IDE / Agent runtime 兼容层 | NO. `prose_class` 是 SKILL.md section annotation 工艺，与 IDE 无关；§7.2 平台优先级（Cursor → Claude Code → Codex）保持。`token_tier` 不引入新的 IDE adapter abstraction，仅 Cursor / Claude Code / Codex 三档下统一的 OTel attribute 命名。 |
| Markdown-to-CLI 自动转换器 | NO. `prose_class` annotation 是手写 HTML 注释 (`<!-- prose_class: trigger -->`)，不做 Markdown → CLI 自动生成；`.lazy-manifest` 是手写 YAML 文件，不从 SKILL.md 自动 derive。 |

**结论**: §18 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。token-tier 是 observability not distribution；prose_class / lazy_manifest / tier_transitions 都是 ability-local artifacts。

---

## 19. Real-Data Verification（Normative，NEW v0.4.0）

**Normative.** 当 ability 在 production payload 与 mock fixture 之间存在 shape divergence 风险时（即 ability 依赖外部 backend 或 user-supplied 数据），必须执行 **real-data verification** 作为 §8.1 step 2 `evaluate` 的 Normative sub-step。本章节由 r12 §2.2 + §4.2 设计推论而来；动机：chip-usage-helper Round 24 v0.9.0 zero-events bug 是 production payload 与 mock fixture 形态分歧的直接产物 —— ai-bill 后端空数据时 dashboard 静默崩。msw + user-install + post-recovery-live 三层验证是 Cycle 5 的实证修复（详见 r12 §2.2 引用 Pact "as loose as possible" + tau-bench real-dialogue + Inspect AI Sample.metadata + msw fixture pattern）。

### 19.1 Sub-step of §8.1 step 2 `evaluate` (3-layer pattern)

`evaluate-real-data` 是 §8.1 step 2 `evaluate` 的 Normative sub-step；**§8.1 8-step main list count 不变**（per §8 add-on 句的 frozen 8 步）。该 sub-step 由 3 layer 构成：

#### 19.1.1 Layer A — msw fixture provenance

每个 test fixture（typically under `tests/fixtures/` 或 vitest `tests/__mocks__/`）使用的 mock JSON shape 必须直接来自 production-observed payload sample（per §19.2 schema），并在 fixture 文件名或 in-file comment 中 cite provenance。

#### 19.1.2 Layer B — user-install verification

ability 的 release branch 在 push 后，必须由 user 实际安装（tarball + install.sh）并在 production state 下 manual 验证 user-observable behavior。这是 chip-usage-helper Cycle 5 codified pattern：

1. push branch；
2. 用户 `npm install <tarball>` 或 `cursor install <plugin>`；
3. 用户在 production Cursor / Claude Code 实例下 manually trigger ability；
4. 观察实际 user-visible output 是否符合 §14 core_goal `statement`；
5. 如不符合，记录 negative result 到 `.local/dogfood/<DATE>/<round_id>/raw/user_install_verification.md`，触发 §14.4 REVERT-only rollback。

#### 19.1.3 Layer C — post-recovery live verification

当依赖的 live backend 经历 incident（e.g. ai-bill `events/health` 返回 0 events）后恢复时，必须在 ability 的 ship_decision.yaml 中 append 一条 "verified-with-live-data" note：

```yaml
# .local/dogfood/<DATE>/<round_id>/ship_decision.yaml
# (per §20.4 7th evidence file when round_kind == 'ship_prep')
verified_with_live_data:
  - backend_id: ai-bill
    endpoint: "/api/v1/cursor/events/health"
    verified_at: "2026-04-30T08:14:00Z"
    sentinel: "latestTsMs > 0"
    sentinel_observed: 1714464840000
    observer: "yorha@anthropic.local"
    note: "Backend recovered after Cycle 5 incident; events stream nominal; 1714464840000 ms = 2024-04-30 08:14:00 UTC."
```

### 19.2 `feedback_real_data_samples.yaml` schema

`templates/feedback_real_data_samples.template.yaml` (NEW v0.4.0；abridged schema below；full template lands Stage 4 Wave 1b)：

```yaml
# templates/feedback_real_data_samples.template.yaml (abridged)
$schema_version: "0.1.0"
$spec_section: "v0.4.0 §19.2"

ability_id: "<id>"
last_revised: "YYYY-MM-DD"
revision_log:
  - { round: round_N, change: "added v1.1.0 ai-bill endpoint sample after live recovery" }

real_data_samples:
  - { id: "sample_1_dashboard_top10", endpoint: "/api/v1/cursor/dashboard/top10", request_params: { window: "30d", org_id: "<redacted>" }, response_json: '{"ok":true,"data":{"leaderboard":[...],"spendBreakdown":{...},"latestTsMs":1714464840000}}', observed_state: "live, post-recovery, top-10 leaderboard populated", captured_at: "2026-04-30T08:14:00Z", observer: "yorha@anthropic.local", rationale: "Drives msw fixture for tests/get_dashboard_top10.test.ts" }
  - { id: "sample_2_zero_events_failure_mode", endpoint: "/api/v1/cursor/events/health", request_params: {}, response_json: '{"ok":true,"data":{"latestTsMs":0,"eventCount":0}}', observed_state: "Cycle 5 v0.9.0 incident: backend healthy but no events ingested for 4h", captured_at: "2026-04-29T22:31:00Z", observer: "chip-usage-helper-cycle5-author", rationale: "Drives msw fixture for tests/zero_events_recovery.test.ts; the bug we fixed in v0.9.1" }
```

字段语义：`id` (sample 唯一 id；fixture cross-ref) / `endpoint` (被采样的 backend endpoint) / `request_params` (object，PII redacted) / `response_json` (string，actual production response shape verbatim，PII redacted) / `observed_state` (string，sample 的语境描述：live / staging / incident / post-recovery) / `captured_at` (ISO 8601 timestamp) / `observer` (string，采集人或 agent id) / `rationale` (string，该 sample 驱动哪些 fixture / why this sample matters)。

### 19.3 Fixture-citation rule (spec_validator BLOCKER 13: `REAL_DATA_FIXTURE_PROVENANCE`)

每个 ability 的 test fixture 文件（grep `tests/**/*.test.* tests/**/*.spec.*` 或 ability 实现树等价 test 路径）必须含至少一行注释 `// real-data sample provenance: <captured_at> / <observer>`（或语言适用的同义注释格式：`# real-data sample provenance: ...` for Python，`<!-- real-data sample provenance: ... -->` for HTML/Markdown）。

#### 19.3.1 grep-able audit trail

post-ship reviewer 可以一键溯源所有 production-payload-derived fixtures：

```bash
grep -rn "real-data sample provenance" tests/ | sort -t: -k1
```

输出按文件路径排序，每行格式：`tests/path/to/file.ts:LINE_NUMBER:// real-data sample provenance: 2026-04-30T08:14:00Z / yorha@anthropic.local`

#### 19.3.2 spec_validator BLOCKER 实现

`tools/spec_validator.py` (Stage 4 Wave 1b 后) 增新 BLOCKER 13 `REAL_DATA_FIXTURE_PROVENANCE`：

1. 加载 `feedback_real_data_samples.yaml`，得到 ability 的 declared `real_data_samples` ids 集合。
2. 如果集合非空，grep ability 的 test 文件树（按 ability 类型选 glob：TS abilities `tests/**/*.test.ts`，Python abilities `tests/**/*.test.py`，etc.）。
3. 每个 declared sample id 必须有至少 1 个 fixture 文件 cite 其 `<captured_at> / <observer>`。
4. 缺失 = FAIL；fail message 含 missing sample ids。
5. 如果 `feedback_real_data_samples.yaml` 不存在或 `real_data_samples` 数组为空 → BLOCKER 跳过（PASS by absence）。

### 19.4 User-install verification (Layer B detail)

chip-usage-helper Cycle 5 codified pattern（per r12 §4.2）：

1. **push branch**: `git push origin feature/<release-branch>`。
2. **build tarball**: 在 release branch 上 `npm pack`（TS abilities）/ `python -m build` （Python abilities），产出 versioned tarball。
3. **user install**: 用户在 production 环境（Cursor IDE / Claude Code CLI）执行 `npm install <tarball-path>` 或 `cursor install <plugin-zip>`。
4. **manual verification**: 用户根据 §14 `core_goal.statement` 触发 ability 至少 3 个 cases（典型：1 EN + 1 CJK + 1 slash command），观察 user-visible output。
5. **artifact**: `.local/dogfood/<DATE>/<round_id>/raw/user_install_verification.md` 记录每个 case 的 prompt + observed output + verdict (PASS / FAIL)。
6. **failure path**: 任一 case FAIL → 触发 §14.4 REVERT-only rollback，把 release branch reset 到 prior 已通过 round。

### 19.5 Post-recovery live verification (Layer C detail)

当 ability 依赖的 live backend（e.g. chip-usage-helper 依赖 ai-bill）经历 incident 并恢复后：

1. **trigger condition**: backend 的 `health_smoke_check`（per §21）从 FAIL → PASS。
2. **action**: 在最近的 ship_prep round 中重新跑 ability 的 core_goal_test_pack + real_data_samples → fixture parity check。
3. **artifact**: 在 `ship_decision.yaml` (per §20.4 7th evidence file) 中 append `verified_with_live_data` block（per §19.1.3 schema）。
4. **rationale**: live backend 恢复后的 payload shape 可能与 incident 前不同（schema 漂移、字段名改、new error code）；post-recovery verification 是 spec 对 "incident 不仅要修复也要确认 contract 仍 alignment" 的硬要求。

### 19.6 §11 forever-out re-affirmation

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. `feedback_real_data_samples.yaml` 是 ability 自身 source-of-truth 文件，不引入 distribution surface；msw fixture 是 ability test 树内文件，不是注册中心；user-install verification 用现有 `npm install` / `cursor install` 工业工艺，不引入新 marketplace。 |
| Router 模型训练 | NO. real-data verification 是 testing 工艺，不喂任何模型；fixture 是 mock data，不是 training data；post-recovery live verification 是 ability behavior re-check，不涉及任何 router weight 学习。 |
| 通用 IDE / Agent runtime 兼容层 | NO. user-install verification 用每个 IDE 现有的 install 通道（Cursor / Claude Code / Codex）；spec 不引入新的 cross-IDE adapter；§7.2 平台优先级保持。 |
| Markdown-to-CLI 自动转换器 | NO. `feedback_real_data_samples.yaml` 是手写 YAML，不从 SKILL.md 自动 derive；fixture 是 hand-curated production samples，不做 Markdown → fixture 自动转换。 |

**结论**: §19 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。real-data verification 是 testing not distribution；msw fixture / user-install / post-recovery 都是 ability-local 工艺。

---

## 20. Stage Transitions & Promotion History（Normative，NEW v0.4.0）

**Normative.** §2.2 stage 枚举（`exploratory → evaluated → productized → routed → governed ↘ half_retired ↺ ↘ retired`）列了 7 个状态但 v0.3.0 spec 没说什么时候 advance。chip-usage-helper Round 8 把 stage 从 `evaluated` bumps 到 `routed` 是基于 "router_floor 已绑 + v3_strict 全部通过" 的 ad-hoc 决策，不是 spec 规则。本章节由 r12 §2.4 + §4.3 设计推论而来；OpenSpec proposal/apply/archive + delta semantics + `verify` 3-dim check 是 industry precedent；ACE Skillbook helpful/harmful/neutral 计数 + SimilarityDecision (KEEP) 显示 lifecycle metadata 应该 first-class（详见 r12 §2.4.a / §2.3.c 引用）。

### 20.1 `stage_transition_table` (Normative)

每行 `from_stage → to_stage` 含 **required-conditions**：

| `from_stage` | `to_stage` | 必须满足的条件 |
|---|---|---|
| `exploratory` | `evaluated` | (a) `eval_state.has_eval_set: true` + `has_no_ability_baseline: true`；(b) `metrics_report.metrics` 中 7 维基础指标 (D1-D7) 全部 emitted（即使大多数 null placeholder）；(c) 至少 MVP-8 中的 T1/T3/C1/C4 非 null。 |
| `evaluated` | `productized` | (a) ability 的稳定步骤已下沉到 script / CLI / MCP / SDK（即 `current_surface.shape_hint ∈ {code_first, cli_first, mcp_first} 或 mixed-with-code`）；(b) v1_baseline 全部硬门槛连续 ≥ 2 轮 PASS（per §4.2 promotion rule + §15.4 round_kind eligibility）。 |
| `evaluated` | `routed` | (a) `router_floor` 已 bound (非 null)；(b) v3_strict 全部硬门槛 ≥ 3 轮 PASS（含至少 1 轮 `code_change` + 至少 1 轮 `measurement_only`）；(c) `R3_trigger_F1 ≥ 0.90` （v3_strict）。 |
| `productized` | `routed` | (a) `router_floor` 已 bound (非 null)；(b) router_test 在 §5.3 MVP 8-cell（或 96-cell）跑过并出 `router_floor_report.yaml`；(c) v2_tightened 全部硬门槛 ≥ 2 轮 PASS。 |
| `routed` | `governed` | (a) `BasicAbility` 含 `lifecycle.owner` field (Informative @ v0.4.0)；(b) `BasicAbility` 含 `lifecycle.version` field（typically synced with ability source `package.json` 或等价 semver）；(c) telemetry pipeline emits OTel `gen_ai.tool.name=<ability_id>` for ≥ 30 days；(d) `lifecycle.deprecation_policy` field declared (e.g. "30 day notice + migration guide")。 |
| `*` (any) | `half_retired` | (a) §6.2 value_vector trigger 命中 (`task_delta` 近零 + 至少 1 个性能轴 ≥ +0.05/+0.10/+0.15 according to current gate)；(b) spec-compliant `half_retire_decision.yaml` written per §6.3。 |
| `half_retired` | `evaluated` (reactivation) | (a) §6.4 reactivation triggers 任一命中；(b) `core_goal_test_pack.yaml` hash 与 half_retire 时刻一致（per §14.7 #1）；(c) C0 = 1.0 against current run（per §14.7 #2）。 |
| `*` (any) | `retired` | (a) §6.2 retire trigger 命中 (value_vector 全部 ≤ 0 OR `governance_risk_delta < 0` 且超出 §11 风险策略 OR v3_strict 下连续 ≥ 2 轮失败且无任一性能轴改善)；(b) `retire_decision.yaml` written (extension of `half_retire_decision.template.yaml`)。 |

#### 20.1.1 Forbidden transitions

以下 transitions 是 **明确禁止**：

- `productized → evaluated` 反向：不允许把已下沉到 code 的 ability 退回到 markdown-only 状态；如果需要 rewrite，必须先 `retire` 再 重新 `exploratory`。
- `routed → productized` 反向：同上，路由已 bound 的 ability 不允许退回到无 router 状态；只能 `half_retired`（保留 router_floor for reactivation）或 `retired`（完全归档）。
- `governed → routed` 反向：governed 是终态分支；只能 `half_retired` 或 `retired`。

### 20.2 `BasicAbility.lifecycle.promotion_history` (append-only block)

每次 stage 变化必须 append 一条记录到 `BasicAbility.lifecycle.promotion_history`（abridged worked example：chip-usage-helper transitions through Cycle 1）：

```yaml
# basic_ability_profile.yaml
basic_ability:
  ...
  lifecycle:
    stage: routed                                # current stage
    last_reviewed_at: "2026-04-29"
    next_review_at: "2026-05-29"
    promotion_history:                           # NEW v0.4.0 §20.2; append-only
      - { from: exploratory, to: evaluated, triggered_by_round_id: round_1, triggered_by_metric_value: { T1_pass_rate: 0.90, T3_baseline_delta: 0.85 }, observer: "chip-usage-helper-cycle1-author", archived_artifact_path: ".local/dogfood/2026-04-29/abilities/chip-usage-helper/round_1/iteration_delta_report.yaml", decision_rationale: "Initial profile; 7-dim metrics emitted; T1/T3 above MVP threshold." }
      - { from: evaluated, to: routed, triggered_by_round_id: round_8, triggered_by_metric_value: { R3_trigger_F1: 1.0, R5_router_floor: "composer_2/fast" }, observer: "chip-usage-helper-cycle1-author", archived_artifact_path: ".local/dogfood/2026-04-29/abilities/chip-usage-helper/round_8/iteration_delta_report.yaml", decision_rationale: "router_floor bound; 5 consecutive v3_strict-row-complete passes; R3=1.0 perfect routing." }
```

#### 20.2.1 Append-only invariant

`promotion_history` 是 **append-only**：

- 不允许 modify 已有 entry（每条 entry 是历史记录，篡改 = falsifying audit trail）。
- 不允许 delete 已有 entry（同上）。
- 仅允许 append 新 entry。
- 如果发现历史 entry 错误（e.g. observer 写错），必须 append 一条 `to: <same as last entry>, decision_rationale: "Correcting observer field on round_X entry"` 的 sentinel entry，而不是改原 entry。

#### 20.2.2 OpenSpec archive 同源工艺

`promotion_history` 字段 mirror OpenSpec 的 `changes/archive/<date>-<change-name>/` semantics（详见 r12 §2.4.a 引用）：每次 transition 的 `archived_artifact_path` 必须指向 `.local/dogfood/<DATE>/<round_id>/iteration_delta_report.yaml` 或等价 round artifact，让 readers 可以 1-click 重放该次 transition 的完整 evidence。

### 20.3 `metrics_report.yaml.promotion_state` first-class top-level key

`metrics_report.yaml` 在 v0.4.0 additively 增加 `promotion_state` 顶层 block（与 `metrics` / `core_goal` / `token_tier` 同级）：

```yaml
# metrics_report.yaml
spec_version: "v0.4.0-rc1"
round_id: "round_<N>"
ability_id: "<id>"

metrics: { ... }
core_goal: { ... }
token_tier: { ... }                              # NEW v0.4.0 §18

promotion_state:                                 # NEW v0.4.0 §20.3
  current_gate: v1_baseline                      # current §4 gate (v1_baseline | v2_tightened | v3_strict)
  consecutive_passes: 2                          # consecutive rounds passing per §4.2 + §15.4 (resets to 0 on failure)
  promotable_to: v2_tightened                    # next gate after consecutive_passes >= 2 (or null if at v3_strict ceiling)
  last_promotion_round_id: round_<M>             # round_id where last gate promotion happened (or null if no promotion yet)
  ineligible_reason: null                        # if not promotable, why; null when promotable
```

#### 20.3.1 `ineligible_reason` enum

当 `promotable_to: null` 或 `consecutive_passes < 2` 时 `ineligible_reason` 必须非 null，取值 enum：

- `"already_at_v3_strict"`: 当前已经是 v3_strict，无更高档；
- `"insufficient_consecutive_passes"`: consecutive_passes < 2；
- `"hard_gate_regression_in_prior_round"`: 上一轮某 hard gate FAIL，counter 归零；
- `"c0_regression_in_prior_round"`: C0 < 1.0 in prior round (per §14.3.2 strict no-regression)；
- `"round_kind_not_eligible"`: 上一轮 round_kind 是 ship_prep 或 maintenance（不计入 counter，per §15.4）。

### 20.4 `ship_decision.yaml` 7th evidence file (when `round_kind == 'ship_prep'`)

`templates/ship_decision.template.yaml` (NEW v0.4.0；abridged schema below；full template lands Stage 4 Wave 1b)：

```yaml
# templates/ship_decision.template.yaml (abridged)
$schema_version: "0.1.0"
$spec_section: "v0.4.0 §20.4"

ability_id: "<id>"
round_id: "<round_id>"
decided_at: "YYYY-MM-DDTHH:MM:SSZ"
decided_by: "<observer>"

ship_target: { version: "<semver>", promoted_from: "<prior_version>", spec_version_used: "v0.4.0" }

verdict: shipped|rolled-back|deferred
verdict_rationale: "<one paragraph>"

evidence_pointers:                               # cross-refs to the 6 standard evidence files of this round
  basic_ability_profile: ".local/dogfood/<DATE>/<round_id>/basic_ability_profile.yaml"
  metrics_report: ".local/dogfood/<DATE>/<round_id>/metrics_report.yaml"
  router_floor_report: ".local/dogfood/<DATE>/<round_id>/router_floor_report.yaml"
  half_retire_decision: ".local/dogfood/<DATE>/<round_id>/half_retire_decision.yaml"
  next_action_plan: ".local/dogfood/<DATE>/<round_id>/next_action_plan.yaml"
  iteration_delta_report: ".local/dogfood/<DATE>/<round_id>/iteration_delta_report.yaml"

target_repo_commits: [{ sha: "<git sha>", message: "<commit message>" }]

verified_with_live_data:                         # NEW v0.4.0 §19.1.3 (post-recovery live verification)
  - { backend_id: "<id>", endpoint: "<url>", verified_at: "YYYY-MM-DDTHH:MM:SSZ", sentinel: "<predicate>", sentinel_observed: <value>, observer: "<observer>", note: "<one sentence>" }

post_ship_review: { next_maintenance_at: "YYYY-MM-DD", triggers_to_watch: ["30d cadence per §6.4", "post-model-upgrade re-verify"] }
```

#### 20.4.1 Conditional 7th evidence file

`ship_decision.yaml` 仅在 `round_kind == 'ship_prep'` 时才作为 §8.2 第 7 个 evidence file（per §8.2 v0.4.0 add-on 子句）；其它 round_kind 仍然 6 件。spec_validator 的 `EVIDENCE_FILES` BLOCKER 在 v0.4.0 后是 conditional：

- `next_action_plan.round_kind == 'ship_prep'` → expected count = 7（含 ship_decision.yaml）；
- `next_action_plan.round_kind ∈ {code_change, measurement_only, maintenance}` → expected count = 6（与 v0.3.0 相同）。

### 20.5 Backward compatibility + cross-references (§14 / §15 / §16)

v0.4.0 §20 lifecycle machinery 与 v0.3.0 既有 Normative 章节协同如下；向下兼容契约保持：

- **§20 ↔ §14 Reactivation**: `stage_transition_table` 的 `half_retired → evaluated` 行显式引用 §14.7 的 2 个 prerequisite（pack hash unchanged + C0 = 1.0 against current run）；两者合并为 reactivation gate；`promotion_history` 为每次 reactivation append 一条 entry（`from: half_retired, to: evaluated, triggered_by_metric_value.C0_core_goal_pass_rate: 1.0`）。
- **§20 ↔ §15 round_kind**: §20.4 `ship_decision.yaml` 只在 `round_kind == 'ship_prep'` 时作为第 7 个 evidence file；§20.3 `promotion_state.consecutive_passes` 按 §15.4 eligibility table 计数（`code_change` + `measurement_only` 计入；`ship_prep` + `maintenance` 不计入）；`ineligible_reason: round_kind_not_eligible` 明确标记 ship_prep / maintenance 轮次不推进 counter。
- **§20 ↔ §16 Multi-Ability Layout**: `archived_artifact_path` 字段必须 `.local/dogfood/<DATE>/abilities/<id>/round_<N>/iteration_delta_report.yaml`（新布局）或 `.local/dogfood/<DATE>/round_<N>/iteration_delta_report.yaml`（legacy, Si-Chip self only，per §16.2）；spec_validator 按 §16.2 rules 区分 ability。
- **Backward-compat契约**: Round 1-15 Si-Chip + Round 1-10 chip-usage-helper 的既有 `BasicAbilityProfile.lifecycle` 在 schema_version 0.3.0 下 `promotion_history` 字段 default null（历史未记录的 transitions 不追溯写）；仅 Round 16+ 的 Si-Chip / Round 26+ 的 chip-usage-helper 开始 append 新 entries；spec_validator `BAP_SCHEMA_KEYS` BLOCKER 对 Round 1-15 不要求 `promotion_history` 非空。

### 20.6 §11 forever-out re-affirmation

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. `promotion_history` 是 ability 自身 BasicAbilityProfile 的字段，不引入 distribution surface；`ship_decision.yaml` 是 ability 自身 dogfood evidence file，不是 marketplace 列表；`stage_transition_table` 是 spec-internal Normative table，与外部分发无关。 |
| Router 模型训练 | NO. stage transitions / promotion_history / ship_decision 都是 lifecycle metadata，不喂任何模型；`promotion_state` 是 evaluator-side 状态字段，不涉及任何 router weight 学习。 |
| 通用 IDE / Agent runtime 兼容层 | NO. lifecycle stages 是 spec-internal，与 IDE 无关；§7.2 平台优先级保持。`ship_decision.yaml` 用每个 ability 现有的 dogfood evidence path，不引入新的 IDE adapter。 |
| Markdown-to-CLI 自动转换器 | NO. `promotion_history` entry 是 hand-witnessed transitions（observer 字段必须是人或 agent id）；`ship_decision.yaml` 是 hand-authored ship verdict，不做 Markdown → ship_decision 自动生成。 |

**结论**: §20 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。lifecycle state-machine 是 ability-local audit trail，不是 marketplace；transitions 是 hand-witnessed，不是 model-driven。

---

## 21. Health Smoke Check（Normative，NEW v0.4.0）

**Normative.** 当 ability 依赖 live backend 时（即 `current_surface.dependencies.live_backend: true`），必须声明非空 `packaging.health_smoke_check` 数组，覆盖至少 1 个 axis。该 health smoke check 在 §8.1 step 8 `package-register` ship-eligibility 决策时强制执行。本章节由 r12 §2.6 + §4.4 设计推论而来；动机：chip-usage-helper Cycle 5 v0.9.0 zero-events bug 暴露 spec §8 的 8-step protocol 没有 production smoke check —— ability 可以 ship-eligible 但 backend 已经空的情况下 dashboard 静默崩。GitHub Actions URL Health Check + post-deploy verification 4-axis pattern (read/write/auth/dependency) 是 industry precedent（详见 r12 §2.6.a / §2.6.b 引用）。

### 21.1 `health_smoke_check` 字段 schema

`BasicAbility.packaging.health_smoke_check` (NEW v0.4.0; OPTIONAL @ schema, REQUIRED-when-live-backend per §21.2)。Worked example for chip-usage-helper：

```yaml
basic_ability:
  ...
  current_surface:
    type: mcp
    path: "ChipPlugins/chips/chip_usage_helper/mcp/"
    shape_hint: code_first
    dependencies:                                # NEW v0.4.0 §21.2 (additive on current_surface)
      live_backend: true                         # if true, packaging.health_smoke_check is REQUIRED

  packaging:
    install_targets: { cursor: true, claude_code: false, codex: false }
    source_of_truth: ".agents/skills/chip-usage-helper/"
    generated_targets: ["ChipPlugins/chips/chip_usage_helper/"]
    health_smoke_check:                          # NEW v0.4.0 §21.1; REQUIRED non-empty when live_backend: true
      - { endpoint: "https://ai-bill.example.com/api/v1/cursor/events/health", expected_status: 200, max_attempts: 3, retry_delay_ms: 2000, sentinel_field: "data.latestTsMs", sentinel_value_predicate: ">0", axis: dependency, description: "ai-bill backend health: events stream non-empty (latestTsMs > 0)" }
      - { endpoint: "https://ai-bill.example.com/api/v1/cursor/dashboard/top10", expected_status: 200, max_attempts: 2, retry_delay_ms: 1000, sentinel_field: "data.leaderboard", sentinel_value_predicate: "non_empty_array", axis: read, description: "Dashboard top-10 endpoint returns non-empty leaderboard" }
```

字段语义：

| 字段 | 类型 | 说明 |
|---|---|---|
| `endpoint` | string (URL) | 被探测的 backend endpoint |
| `expected_status` | integer | 期望的 HTTP status (typically 200; some healthchecks use 204) |
| `max_attempts` | integer | retry 次数上限（默认 3） |
| `retry_delay_ms` | integer | 每次 retry 的间隔毫秒（默认 1000） |
| `sentinel_field` | string (dot path) | 在 response JSON 中提取的字段路径，e.g. `"data.latestTsMs"` |
| `sentinel_value_predicate` | string | 对 sentinel field 值的断言：`">0"`, `"<100"`, `"non_empty_array"`, `"non_empty_string"`, `"!= null"`, `"== <value>"`, etc. |
| `axis` | enum | `read | write | auth | dependency` (per §21.3 4-axis taxonomy) |
| `description` | string | 一句话 human-readable 描述本 check 的目的 |

### 21.2 Optional REQUIRED-when-live-backend (spec_validator BLOCKER 14: `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`)

`current_surface.dependencies.live_backend: true` MAKES `packaging.health_smoke_check` 非空 REQUIRED。

#### 21.2.1 `live_backend` 字段定义

`current_surface.dependencies.live_backend: bool` (NEW v0.4.0)：当 ability 在执行时需要 read/write 到外部 live backend（HTTP API、message queue、database），即 ability 的 functional output 依赖该 backend 的 alive state，则该字段为 true。例如：

- chip-usage-helper 依赖 ai-bill `/api/v1/cursor/events/health` → `live_backend: true`；
- Si-Chip self-dogfood 不依赖任何外部 backend（所有 evidence 在本仓库 .local/dogfood/） → `live_backend: false`；
- 一个生成 boilerplate 的 ability，纯本地 file system 操作 → `live_backend: false`。

#### 21.2.2 spec_validator BLOCKER 14 实现

`tools/spec_validator.py` (Stage 4 Wave 1b 后) 增新 BLOCKER 14 `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`：

1. 加载 `BasicAbilityProfile.basic_ability.current_surface.dependencies.live_backend`。
2. 如果为 true：检查 `BasicAbilityProfile.basic_ability.packaging.health_smoke_check` 是否非空 array；为空或缺失 = FAIL。
3. 如果为 false 或字段缺失：BLOCKER 跳过（PASS by absence）。
4. fail message 含 ability id + missing live_backend declaration suggestion。

### 21.3 4-axis taxonomy (read / write / auth / dependency)

post-deploy verification 工业模式（详见 r12 §2.6.b 引用 fitgap pattern）的 4-axis 完备覆盖：

| `axis` | 语义 | 典型 health probe 例子 |
|---|---|---|
| `read` | GET critical resource | `GET /api/v1/users/me` returns user profile (200 + non-empty) |
| `write` | POST create + GET verify | `POST /api/v1/test-resource` then `GET /api/v1/test-resource/<id>` (round-trip OK) |
| `auth` | auth-protected flow | `POST /api/v1/login` with test creds returns 200 + valid token |
| `dependency` | dependency touch (queue / cache / downstream service) | `GET /api/v1/health/redis` or downstream service health endpoint |

#### 21.3.1 Per-ability axis selection

每个 ability 不需要覆盖全部 4 axes；只需覆盖其 `live_backend` 实际依赖的 axes。例如：

- chip-usage-helper 主要是 read（dashboard data）+ dependency（events stream），不做 write；
- 一个 issue-creator ability 主要是 write（创建 GitHub Issue）+ auth（GitHub PAT），不做 dependency；
- 一个 cache-warmup ability 主要是 dependency（Redis / Memcached），不做 read/write/auth。

#### 21.3.2 ≥ 1 axis required

每个非空 `health_smoke_check` 数组必须至少包含 1 个 axis；spec_validator WARNING（v0.4.0）/ BLOCKER（v0.4.x，promotion 触发后）当 ability declare `live_backend: true` 但 `health_smoke_check` 全是 `axis: read` 而 backend 实际有 dependency 风险（typically chip-usage-helper-shape ability：ai-bill 是 dependency 不是 read）。

### 21.4 Packaging-gate enforcement (extension to §8.1 step 8 `package-register`)

§8.1 step 8 `package-register` 在 v0.4.0 后扩展：

1. 读取 `BasicAbilityProfile.basic_ability.packaging.health_smoke_check`（如非空）。
2. 对每个 declared check：执行 HTTP probe，按 `max_attempts` retry，验证 `expected_status` + `sentinel_field` + `sentinel_value_predicate`。
3. 把每个 probe 结果（`{check_id, axis, attempts_used, response_status, sentinel_observed, predicate_passed, elapsed_ms}`）写入 `.local/dogfood/<DATE>/<round_id>/raw/health_smoke_results.yaml`。
4. **ship-eligible declaration 要求**：`health_smoke_check` 数组的每个 check 必须 `predicate_passed: true`，否则 ship 阻塞。
5. 当 `current_surface.dependencies.live_backend: false` 或字段缺失：health_smoke probe 跳过（不阻塞 ship）。

#### 21.4.1 `tools/eval_skill.py health_smoke` runner

Stage 4 Wave 1b 在 `tools/eval_skill.py` 增 `health_smoke` runner subcommand：

```bash
python tools/eval_skill.py health_smoke \
    --skill chip-usage-helper \
    --basic-ability-profile .local/dogfood/2026-04-30/abilities/chip-usage-helper/round_26/basic_ability_profile.yaml \
    --out .local/dogfood/2026-04-30/abilities/chip-usage-helper/round_26/raw/health_smoke_results.yaml
```

退出码 0 = 全部 axes PASS；非零 = 至少 1 个 axis FAIL；详细结果在 `--out` 指向的 yaml。

### 21.5 OTel semconv extension (`gen_ai.tool.name=si-chip.health_smoke`)

每个 health smoke probe 必须 emit 一个 OTel span：

| OTel attribute | 值 |
|---|---|
| `gen_ai.tool.name` | `si-chip.health_smoke` |
| `mcp.method.name` | `health_check` |
| `gen_ai.system` | `<ability_id>` |
| `gen_ai.operation.name` | `health_smoke_check` |
| `gen_ai.client.operation.duration` | `<elapsed_ms>` |
| `http.status_code` | `<response_status>` |
| `si_chip.health_smoke.axis` | `<axis>` |
| `si_chip.health_smoke.predicate_passed` | `<bool>` |

> 这让 health smoke 与 ability 的其它 telemetry **流入同一 trace pipeline**（OTel GenAI semconv 兼容），readers 可以通过 trace ID 一键溯源 ship-prep round 的所有 probe 决策。详见 r12 §2.6.c 引用 OpenTelemetry GenAI semconv 与 §3.2 frozen constraint #3 OTel-first datasource alignment。

### 21.6 §11 forever-out re-affirmation

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. `health_smoke_check` 是 ability 自身 BasicAbilityProfile 的字段，不引入 distribution surface；smoke probe 是 per-ability local 配置，不是注册中心；4-axis taxonomy 是 spec-internal Normative，与外部 marketplace 无关。 |
| Router 模型训练 | NO. health smoke 是 backend probe，不喂任何模型；OTel span emit 是 observability，不涉及任何 router weight 学习。 |
| 通用 IDE / Agent runtime 兼容层 | NO. health probe schema 是 ability-local，**不绑定** 到具体 orchestrator API（不引入 Kubernetes liveness/readiness、不引入 systemd watchdog、不引入 IDE-specific health adapter）；§7.2 平台优先级保持。Per r12 §2.6.c 显式 boundary：OpenTelemetry 没有专门的 healthcheck semconv，Si-Chip 不应 reinvent Kubernetes-side health-probe patterns；如果 ability 需要 orchestrator-side probe，那是 ability 部署 pipeline 的事，不是 spec 的事。 |
| Markdown-to-CLI 自动转换器 | NO. `health_smoke_check` 是手写 YAML，不从 SKILL.md 自动 derive；OTel span 是 runtime emit，不是从 Markdown 自动转换。 |

**结论**: §21 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。health probe schema 是 observability not distribution，**不绑定具体 orchestrator API**（这是 §11 forever-out 的精神延伸 —— Si-Chip 不应 reinvent Kubernetes 工艺）。

---

## 22. Eval-Pack Curation Discipline（Normative，NEW v0.4.0）

**Normative.** 每个 ability 的 `eval_pack.yaml` (R3 trigger F1) + `core_goal_test_pack.yaml` (C0 core goal) 必须遵守 minimum-size + provenance + reproducibility-floor 三类约束。本章节由 r12 §2.5 + §4.5 设计推论而来；动机：chip-usage-helper Round 1 的 R3 = 0.7778 → 0.9524 跳变全部来自 evaluator 方法学修正（CJK substring + 40-prompt curated pack），不是 ability 改善（详见 SUMMARY.md R3 / R14 / R25）。如果不把 eval pack curation 工艺写进 spec，下一个 ability 的作者会重蹈 30 分钟方法学陷阱。OpenAI Evals registry + MLPerf submission rules + DSPy `metric_threshold` 是 industry precedent（详见 r12 §2.5 引用）。

### 22.1 40-prompt minimum gate for v2_tightened promotion

| Gate | Eval pack minimum size | Rationale |
|---|---|---|
| `v1_baseline` | 20 prompts (10 should + 10 should-not) | §5.3 router-test harness MVP；启动 ability 评估的最小可信样本量 |
| `v2_tightened` | **40 prompts** (20 should + 20 should-not, with curated near-miss bucket) | 1 FP at 20 prompts ⇒ -0.05 F1 噪声窗 (chip-usage-helper Round 1 实证)；40 prompts 把单 FP 的 F1 影响减到 -0.025，让 v2 阈值 (`R3 ≥ 0.85`) 决策可信 |
| `v3_strict` | 40 prompts MINIMUM；建议 60+ | v3 阈值 (`R3 ≥ 0.90`) 在 40 prompts 下仍有 ~0.025 噪声窗；60 prompts 让 v3 决策稳定 |

#### 22.1.1 §5.3 router-test harness Normative table 增 1 句

§5.3 现行 Normative table "Dataset" 行写 "每 pack 20 prompts (10 should-trigger + 10 should-not-trigger)"。v0.4.0 add-on 句：

> **v0.4.0 add-on**: MVP=20 prompts is the v1_baseline floor; v2_tightened promotion decisions require 40+ prompts (20 should + 20 should-not, with curated near-miss bucket per §22.3 eval_pack_qa_checklist.md) (per r12 §4.5 R3 + MLPerf reproducibility precedent §2.5.c).

> 注意：本 add-on 句 **不修改** §5.3 现行 table 字节级内容（保持 v0.3.0 byte-identicality），仅在 table 之后追加 1 行 prose；技术上 §5.3 仍是 byte-identical with one v0.4.0 add-on sentence pattern（per §13.6.1 add-on rule）。

### 22.2 G1 `provenance` REQUIRED first-class field

§3.1 D4 G1 `cross_model_pass_matrix` 现行 schema 把 `provenance` 当作 sub-key（"deterministic_simulation" 容易被 readers 误读为 real cross-model robustness）。v0.4.0 把 `provenance` 升 first-class REQUIRED 字段：

```yaml
# metrics_report.yaml
metrics:
  generalizability:
    G1_cross_model_pass_matrix:
      provenance: real_llm_sweep|deterministic_simulation|mixed   # NEW v0.4.0 §22.2 REQUIRED first-class
      matrix:                                                      # the actual cross-model pass results
        composer_2/fast: 0.92
        claude-haiku-4-5: 1.00
        claude-sonnet-4-6: 0.97
        deterministic_memory_router: 0.85
      sampled_at: "2026-04-30T08:14:00Z"                          # NEW v0.4.0 §22.2 (when matrix was computed)
      sample_size_per_cell: 20                                     # NEW v0.4.0 §22.2 (prompt count per model cell)
```

#### 22.2.1 `provenance` enum 语义

- `real_llm_sweep`: matrix 是 real LLM 调用产物（per §22.6 real-LLM cache + r12.5 spike PROCEED_MAJOR verdict）；
- `deterministic_simulation`: matrix 是 deterministic simulator 产物（如 SHA-256 simulator 的 algebraic 算式 `pass_k = pass_rate^k`）；这种 provenance 不能作为 v2_tightened/v3_strict promotion 的 cross-model 证据；
- `mixed`: 部分 cells real_llm，部分 deterministic（典型：composer_2 internal model 不可达 → 用 deterministic substitute；claude family 跑 real_llm）；这种 provenance 必须 in-yaml 注明哪些 cells 是哪种。

#### 22.2.2 §3.1 D4 G1 row 修订

§3.1 D4 G1 row 仍然是 1 个 sub-metric（保持 R6 7×37 frozen count），但 prose 增 1 行说明：

```text
| **D4 Generalizability** | G1 cross_model_pass_matrix / G2 cross_domain_transfer_pass / G3 OOD_robustness / G4 model_version_stability | — |
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                            v0.4.0 §22.2 REQUIRED first-class field:
                            G1.provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}
                            G1.sampled_at + G1.sample_size_per_cell
```

> 这是 §3.1 D4 G1 row 的 prose 注释 add-on；**不修改** §3.1 main table 字节级内容（10 rows × 3 cols 不变）。

### 22.3 `templates/eval_pack_qa_checklist.md` (Informative reference doc)

NEW v0.4.0 Informative template（mirror v0.3.0 §16 Informative-then-Normative pattern）。Checklist 包含 6 个 sections（每节 2-4 个 bullet items；完整内容由 Stage 4 Wave 1b 落地为 `templates/eval_pack_qa_checklist.md`）：

1. **Bilingual coverage** — CJK abilities 用 50/50 EN/CJK 比例（per chip-usage-helper R29 evidence）；EN-only abilities 必须文档化为何 omit CJK。
2. **Near-miss curation** — 每个 positive trigger 配 2-5 negatives；包含 "spend time" 类 discriminator（chip-usage-helper Round 1 实证）+ cross-skill ambiguity。
3. **Anti-patterns to avoid** — 不用 naive `\w+` tokenization for CJK（会产生 R3 = 0.7778 artifact）；不用 single-language packs（chip-usage-helper R29 evidence）；不用 over-trivial prompts；不用 benchmark detection（per §14.2.1 freeze constraint #5 + MLPerf "benchmark detection is not allowed"）。
4. **Reproducibility floor** (per §22.5) — deterministic simulators MUST seed with `hash(round_id + ability_id)`；cache key shape `sha256(model + prompt + system + sample_idx)[:16]`（per r12.5 spike）；cache directory per §22.6。
5. **Pack size gates** (per §22.1) — v1_baseline ≥ 20 prompts；v2_tightened decisions ≥ 40 prompts (20 + 20 + curated near-miss)；v3_strict decisions ≥ 60 prompts recommended。
6. **Provenance documentation** (per §22.2 + §23) — G1.provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}；每个 metric value 有 `_method` companion field per §23.1。

#### 22.3.1 Adoption tracking

`templates/eval_pack_qa_checklist.md` 在 v0.4.0 是 Informative；promote-to-Normative trigger（§16.3 同源工艺）：

1. ≥ 2 abilities 在 v0.4.x ship 中 fill out this checklist 在 `eval_pack.yaml` adjacent file（e.g. `eval_pack_qa.md`）；
2. 1 个 ability 在两个 consecutive ships 中 demonstrate checklist-driven 改善（e.g. R3 噪声从 0.05 降到 0.025）。

满足 → bump v0.4.x，把 `eval_pack_qa_checklist.md` 从 Informative 升 Normative，并在 spec_validator 加 `EVAL_PACK_QA_CHECKLIST_FILLED` BLOCKER。

### 22.4 `templates/recovery_harness.template.yaml` for T4

NEW v0.4.0 template，标准化 T4 `error_recovery_rate` 的 **4-scenario branch test pattern**（chip-usage-helper R8 evidence；per type 4 scenarios，每场景 weight 0.25 sum to 1.0）：

```yaml
# templates/recovery_harness.template.yaml (abridged schema; full template lands Stage 4 Wave 1b)
$schema_version: "0.1.0"
$spec_section: "v0.4.0 §22.4"

ability_id: "<id>"
metric: T4_error_recovery_rate
last_revised: "YYYY-MM-DD"

scenarios:
  # ── identity-resolution type (e.g. user lookup, entity match) ─────────────
  - { id: identity_match, type: identity, setup: "exact match", expected: "1 candidate, HIGH confidence", weight: 0.25 }
  - { id: identity_one_candidate, type: identity, setup: "partial match → 1 record", expected: "1 candidate, MEDIUM confidence", weight: 0.25 }
  - { id: identity_no_candidate, type: identity, setup: "match 0 records", expected: "graceful 'not found' + disambiguation; no crash", weight: 0.25 }
  - { id: identity_multi_candidate, type: identity, setup: "match 2+ records", expected: "all candidates + ask user to disambiguate; no silent default", weight: 0.25 }
  # ── tool-call type (e.g. invoke API, run script) ──────────────────────────
  - { id: tool_success, type: tool_call, setup: "2xx valid payload", expected: "forward to user; no error block", weight: 0.25 }
  - { id: tool_expected_failure, type: tool_call, setup: "4xx (e.g. 404)", expected: "surface expected error; no retry", weight: 0.25 }
  - { id: tool_recoverable_failure, type: tool_call, setup: "5xx / transient timeout", expected: "retry per max_attempts; surface after exhaustion", weight: 0.25 }
  - { id: tool_unrecoverable_failure, type: tool_call, setup: "persistent 5xx OR 401 auth", expected: "clear error + suggest user action; no infinite retry", weight: 0.25 }

t4_computation: "weighted_avg(scenario passes; weights sum to 1.0 per type)"
```

#### 22.4.1 spec §3.1 D1 T4 row 不变

§3.1 D1 T4 sub-metric 仍然算 1 个（保持 R6 7×37 frozen count），prose 不修改；`recovery_harness.template.yaml` 仅是 T4 metric 的 canonical generator，避免每个 ability 重复发明 4-scenario harness。

### 22.5 Deterministic seeding rule (§3.2 frozen constraint #5)

§3.2 现行 frozen constraints 4 项。v0.4.0 add 第 5 项：

5. **Deterministic seeding**: deterministic eval simulators MUST seed with `hash(round_id + ability_id)` (where `hash` is SHA-256 truncated to first 16 hex chars used as `random.seed()`); 这保证 round-on-round / ability-cross 比较时 deterministic simulator 产出 byte-equivalent 结果，避免 spurious axis movement 来自 RNG drift。

#### 22.5.1 MLPerf 同源工艺

MLPerf submission rules 要求 "All random numbers must use fixed random seeds with the Mersenne Twister 19937 generator, with random seeds announced four weeks before the submission deadline" (详见 r12 §2.5.c 引用)。Si-Chip §22.5 用 `hash(round_id + ability_id)` 替代 Mersenne 全局 seed，理由：

- ability-cross：不同 ability 有不同 seed，避免 simulator artifact 在多个 ability 间 spurious correlate；
- round-on-round：同 ability 不同 round 有不同 seed，避免 simulator artifact 在 round-on-round delta 中假装稳定；
- reproducibility：seed 是 `hash` 的 deterministic function，CI 可以 byte-replay。

### 22.6 Real-LLM cache directory (`.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/`)

per r12.5 Stage 1 spike PROCEED_MAJOR verdict（详见 `.local/research/r12.5_real_llm_runner_feasibility.md` §3.3 Caching strategy + §5.2 Caching for CI determinism）：

- **Cache directory shape**：`real_llm_runner_cache/{meta.json, cache_<model>.json}`；`meta.json` 含 `cache_seed`, `eval_pack_path`, `eval_pack_hash`, `system_prompt_hash`；`cache_<model>.json` 含 per-sample entries (per-model: claude-haiku-4-5 / claude-sonnet-4-6 / claude-opus-4-6).
- **Cache key shape**：`sha256(model + prompt + system + sample_idx)[:16]`，每个 entry 存 `text`, `usage` (tokens_input + tokens_output), `stop_reason`, `elapsed_s`, `fetched_at`.
- **CI determinism with `--seal-cache`**：production `real_llm_runner.py` (Stage 4 Wave 1c) 接受 `--seal-cache` flag：cache miss 时 refuse to call LLM，仅做 pure replay。CI 跑 spec_validator 时 default 用 `--seal-cache`，避免 CI 跑出真实 API 费用；developer 本地 dogfood 时不带 flag，allow cache build-up。
- **Cache provenance into metrics_report**：real_llm_runner 每次跑出 metric 必须在 `metrics_report.yaml.runner_provenance` emit `{runner: real_llm_runner.py, runner_version, endpoint, models_used: [...], cache_dir, cache_hits, cache_misses, total_calls, total_tokens_input, total_tokens_output, wall_clock_s}` block.

### 22.7 §11 forever-out re-affirmation

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. `eval_pack_qa_checklist.md` 是手写 Markdown reference doc，不引入 distribution surface；`recovery_harness.template.yaml` 是 spec-internal template，不是 marketplace listing；real-LLM cache 是 ability-local artifact，不是 cross-ability fixture broker。 |
| Router 模型训练 | NO. eval-pack curation 是 testing 工艺，不喂任何模型；`acceptance_threshold` 是 case-level filter accept/reject，**不是** training a router model（per r12 §7 explicit boundary check）；deterministic seeding rule 是 reproducibility floor，与训练无关。 |
| 通用 IDE / Agent runtime 兼容层 | NO. eval pack 是 ability-local artifact；real-LLM cache 用 sandbox-internal Veil egress，不引入 cross-IDE adapter；§7.2 平台优先级保持。 |
| Markdown-to-CLI 自动转换器 | NO. `eval_pack_qa_checklist.md` 是手写 Markdown，不做 Markdown → CLI 自动生成；`recovery_harness.template.yaml` 是手写 YAML template；deterministic seed 是 hash function，不是 conversion tool。 |

**结论**: §22 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。eval-pack curation 是 ability-local testing discipline，不是 marketplace；real-LLM cache 是 reproducibility floor，不是 cross-ability fixture broker。

---

## 23. Method-Tagged Metrics（Normative，NEW v0.4.0）

**Normative.** 所有 token-related metrics 与若干 method-ambiguous metrics 必须附带 `_method` 后缀 companion fields；char-heuristic-derived token metrics 必须附带 `_ci_low / _ci_high` confidence band fields。本章节由 r12 §2.5 + §4.6 设计推论而来；动机：chip-usage-helper Round 17 R36 实证 char-based heuristic vs tiktoken differ 2-5% on individual surfaces and **2.4× on template-types-extract prediction** (1.9K predicted vs 786 actual)；如果不把 method 显式 tag，round-on-round 比较容易把 method swap 误读为 ability change。Inspect AI Sample.metadata first-class + DSPy MIPROv2 budget metadata 是 industry precedent（详见 r12 §2.5.b / §2.1.d 引用）。

### 23.1 `<metric>_method` companion fields enumerated per metric

`templates/method_taxonomy.template.yaml` (NEW v0.4.0) 控制每个 metric 允许的 `_method` 值集合（abridged schema below；full taxonomy lands Stage 4 Wave 1b）：

```yaml
# templates/method_taxonomy.template.yaml (abridged; full version covers all 37 R6 sub-metrics + §18 C7/C8/C9 + §14 C0)
$schema_version: "0.1.0"
$spec_section: "v0.4.0 §23.1"

method_taxonomy:
  # ── Token-related metrics (D2 + §18 C7/C8/C9) ─────────────────────────────
  # All take {tiktoken, char_heuristic, llm_actual}; default tiktoken; char_heuristic requires _ci_low/_ci_high.
  C1_metadata_tokens: { allowed_methods: [tiktoken, char_heuristic, llm_actual], default_method: tiktoken, char_heuristic_requires_ci: true }
  C2_body_tokens:    { allowed_methods: [tiktoken, char_heuristic, llm_actual], default_method: tiktoken, char_heuristic_requires_ci: true }
  C3_resolved_tokens: { allowed_methods: [tiktoken, llm_actual], default_method: llm_actual }   # runtime trace required
  C4_per_invocation_footprint: { allowed_methods: [tiktoken, char_heuristic, llm_actual], default_method: tiktoken, char_heuristic_requires_ci: true }
  C7_eager_per_session: { allowed_methods: [tiktoken, char_heuristic, llm_actual], default_method: tiktoken, char_heuristic_requires_ci: true }
  C8_oncall_per_trigger: { allowed_methods: [tiktoken, char_heuristic, llm_actual], default_method: tiktoken, char_heuristic_requires_ci: true }
  C9_lazy_avg_per_load: { allowed_methods: [tiktoken, char_heuristic, llm_actual], default_method: tiktoken, char_heuristic_requires_ci: true }

  # ── Quality metrics (D1 + §14 C0) ─────────────────────────────────────────
  # All take {real_llm, deterministic_simulator, mixed} (C0: only first two); default real_llm.
  T1_pass_rate:           { allowed_methods: [real_llm, deterministic_simulator, mixed], default_method: real_llm }
  T2_pass_k:              { allowed_methods: [real_llm, deterministic_simulator, mixed], default_method: real_llm }
  T3_baseline_delta:      { allowed_methods: [real_llm, deterministic_simulator, mixed], default_method: real_llm }
  C0_core_goal_pass_rate: { allowed_methods: [real_llm, deterministic_simulator], default_method: real_llm }

  # ── Routing metrics (D6, including §18.3 R3 split) ────────────────────────
  R3_trigger_F1:    { allowed_methods: [real_llm, deterministic_simulator], default_method: real_llm }
  R3_eager_only:    { allowed_methods: [real_llm, deterministic_simulator], default_method: real_llm }   # §18.3 / §23.5
  R3_post_trigger:  { allowed_methods: [real_llm, deterministic_simulator], default_method: real_llm }   # §18.3 / §23.5

  # ── Generalizability (D4 G1) — §22.2 promotes provenance to first-class ───
  G1_cross_model_pass_matrix:
    allowed_methods: [real_llm_sweep, deterministic_simulation, mixed]
    default_method: real_llm_sweep
```

#### 23.1.1 metrics_report.yaml emit pattern

每个 metric value 旁边必须 emit `_method`：

```yaml
metrics:
  task_quality:
    T1_pass_rate: 0.97
    T1_pass_rate_method: real_llm                # NEW v0.4.0 §23.1
    T2_pass_k: 0.78
    T2_pass_k_method: real_llm
    T3_baseline_delta: 0.85
    T3_baseline_delta_method: real_llm
    T4_error_recovery_rate: 0.85
    T4_error_recovery_rate_method: deterministic_simulator
  context_economy:
    C1_metadata_tokens: 86
    C1_metadata_tokens_method: tiktoken
    C4_per_invocation_footprint: 4612
    C4_per_invocation_footprint_method: tiktoken
    ...
token_tier:                                       # per §18
  C7_eager_per_session: 365
  C7_eager_per_session_method: tiktoken
  ...
```

### 23.2 Confidence band `_ci_low / _ci_high` for char-heuristic-derived tokens

当 `_method == char_heuristic` 时，必须同时 emit `_ci_low` + `_ci_high`：

```yaml
metrics:
  context_economy:
    C1_metadata_tokens: 1900                      # char-based heuristic guess
    C1_metadata_tokens_method: char_heuristic
    C1_metadata_tokens_ci_low: 1500               # NEW v0.4.0 §23.2 (95% CI lower)
    C1_metadata_tokens_ci_high: 2300              # NEW v0.4.0 §23.2 (95% CI upper)
```

#### 23.2.1 Confidence band 来源

chip-usage-helper Round 17 R36 实测：char-heuristic vs tiktoken differ:
- ASCII-heavy text: ±5% (char count / 4 ≈ tokens)
- CJK-heavy text: ±20% (char count ≈ tokens, but emoji and punctuation skew)
- code blocks: 2-5× off (char count >> tokens because compact tokens)
- template extraction: **2.4× off** (1.9K char-heuristic vs 786 actual — biggest miss)

所以 `_ci_low / _ci_high` 应该按内容类型选择 confidence band 半宽（建议工业默认：±20% for general text, ±50% for code-heavy, ±100% for template extraction）；当 char_heuristic 用于内容类型不确定时，`_ci_low / _ci_high` 应该用最大半宽（±100%）。

#### 23.2.2 Round-on-round comparison rule

任何 metric 跨 round 比较时（例如 §6.1 value_vector 计算 `token_delta`），如果两端都是 `char_heuristic` 且 confidence interval 重叠，spec_validator 发 WARNING："metric delta within confidence band; consider switching to tiktoken before claiming axis improvement"。这避免 measurement-noise 被误读为 ability-improvement。

### 23.3 U1 `language_breakdown` field

§3.1 D5 U1 `description_readability` 现行 schema 仅返回 FK-grade 数字。chip-usage-helper R29 实证：bilingual SKILL.md descriptions 的 FK-grade 被 CJK 单字符算 1 syllable 的工艺 biased upward，cross-ability 比较不可信。v0.4.0 加 `U1_language_breakdown`：

```yaml
metrics:
  usage_cost:
    U1_description_readability: 9.2               # FK grade (legacy field)
    U1_description_readability_method: flesch_kincaid_chinese_character_lossy
    U1_language_breakdown:                        # NEW v0.4.0 §23.3
      en:
        char_count: 1024
        flesch_kincaid: 8.4                       # FK on EN portion only
      zh:
        char_count: 320
        chinese_readability_grade: "中等"          # if a CJK readability metric is computed; else string "n/a"
      mixed_warning: true                         # true if both en and zh non-trivial; readers should NOT cross-ability compare on FK alone
```

### 23.4 U4 `state` field

§3.1 D5 U4 `time_to_first_success` 现行 schema 仅返回 seconds 数字。chip-usage-helper R19 实证：`npm ci` from cold cache is 30-90s vs warm cache <2s — same metric value 在两个 state 下含义完全不同。v0.4.0 加 `U4_state`：

```yaml
metrics:
  usage_cost:
    U4_time_to_first_success: 12.4                # seconds
    U4_time_to_first_success_state: warm          # NEW v0.4.0 §23.4
```

`U4_state ∈ {warm, cold, semicold}`：

- `warm`: dependency cache 已 populated（`node_modules/` 存在 + `package-lock.json` 哈希匹配）；
- `cold`: dependency cache 完全空（fresh checkout，需要 `npm ci` from scratch）；
- `semicold`: 部分 cache 命中（`node_modules/` 存在但 lockfile 漂移，需要 partial reinstall）。

### 23.5 R3 split (cross-listed from §18.3)

R3 split 是 method-quality primitives:

- `R3_eager_only_method ∈ {real_llm, deterministic_simulator}`
- `R3_post_trigger_method ∈ {real_llm, deterministic_simulator}`

详见 §18.3 split rationale。本节 cross-list 是为了让 §23 method taxonomy 的 controlled vocabulary 完备覆盖到 R3 的 2 个 sub-axes。

### 23.6 spec_validator's `R6_KEYS` BLOCKER ignores companion suffixes

`tools/spec_validator.py` 的 `R6_KEYS` BLOCKER 在 v0.4.0 后 **ignore** 以下 companion suffixes：

- `_method`
- `_ci_low`
- `_ci_high`
- `_language_breakdown`
- `_state`
- `_provenance` (G1 specific)
- `_sampled_at`
- `_sample_size_per_cell`

`R6_KEYS_BY_SCHEMA` extension：BLOCKER count 仍然按 7×37 = 37 sub-metric （基本字段名，不含 companion 后缀）；spec_validator 在 metrics_report parsing 时 strip 后缀 match 主名后再 count。

#### 23.6.1 spec_validator 实现细节

```python
COMPANION_SUFFIXES = (
    "_method", "_ci_low", "_ci_high",
    "_language_breakdown", "_state",
    "_provenance", "_sampled_at", "_sample_size_per_cell",
)

def is_companion_key(key: str) -> bool:
    return any(key.endswith(suffix) for suffix in COMPANION_SUFFIXES)

# in R6_KEYS check:
def count_r6_keys(metrics_dim: dict) -> int:
    return sum(1 for k in metrics_dim if not is_companion_key(k))
```

### 23.7 §11 forever-out re-affirmation

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. method-tag companion fields 是 metrics_report.yaml 的字段后缀，不引入 distribution surface；`method_taxonomy.template.yaml` 是 spec-internal controlled vocabulary，不是 marketplace listing。 |
| Router 模型训练 | NO. method tags 是 metric metadata，不喂任何模型；`_method ∈ {tiktoken, char_heuristic, llm_actual}` 是 measurement provenance，不涉及任何 router weight 学习。 |
| 通用 IDE / Agent runtime 兼容层 | NO. method-tag schema 是 spec-internal，与 IDE 无关；§7.2 平台优先级保持。tiktoken 库是 BPE encoder，不是 IDE adapter。 |
| Markdown-to-CLI 自动转换器 | NO. method-tag emit 是 evaluator runtime 行为，不涉及 Markdown → CLI 转换；`method_taxonomy.template.yaml` 是手写 YAML controlled vocabulary。 |

**结论**: §23 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。method-tag 是 metric metadata not distribution；companion fields 是 evaluator-side 工艺，不是 marketplace。

---

## 24. Skill Hygiene Discipline（Normative，NEW v0.4.2）

**Normative.** 每个被 Si-Chip 评估或 packaging 的 ability，其 routing-time metadata（首要为 `SKILL.md` frontmatter `description` + `BasicAbility.description`）必须遵守 **description discipline**：长度受控 + 语义聚焦 ("what + when")。本章节由 r12 §2.5 + addyosmani/agent-skills v1.0.0 (push @ 2026-05-03) `docs/skill-anatomy.md` 的 1024-character description cap convention 设计推论而来；动机：description 是 routing 模型在 R3 trigger F1 决策瞬间唯一可见的语义表面（per §3.1 D6 R1/R2/R3 / §5.1.1 metadata 检索通道），如果 description 被作者塞成完整 SKILL body 段落，(a) routing 模型在 EAGER tier (C7) 必须为每个 session 反复加载长 description（per §18.1 token-tier 工艺）；(b) routing 决策被 narrative noise 稀释，R4 near_miss_FP_rate 上升、R8 description_competition_index 拉爆；(c) skill body 与 metadata 出现重复信息，违反 §22 eval-pack curation 中 "near-miss curation" 期望的 metadata-vs-body 信号清晰度。Anthropic Claude Skills `description` 实务（≤500 chars 推荐 + 关键词触发）、OpenAI function-calling `description` 字段约定、addyosmani/agent-skills `docs/skill-anatomy.md` 显式 1024-char cap 是同源工艺。

### 24.1 Description Discipline（Absorbed from addyosmani/agent-skills v1.0.0）

`SKILL.md` frontmatter `description` 与 `BasicAbility.description`（OPTIONAL；缺位时由 `intent` 充当语义代理）必须满足 **三条 atomic invariants**：

1. **Length cap (binding measurement = `min(len(s), len(s.encode('utf-8')))`)**：description ≤ 1024。同时按字符数与 UTF-8 字节数测量，取二者较小值作为 binding cap。这条规则的目的是 **CJK fairness**：纯 ASCII description 字符数 == 字节数（cap 等价于 1024）；CJK / 混合语言 description 字符数 < 字节数（cap 走字符数那一支，1 个汉字 ≈ 3 字节但仍记 1 char），避免 UTF-8 byte expansion 把多语种 ability 的 metadata 预算系统性砍掉 1/3。1024-char convention 直接吸收自 addyosmani/agent-skills v1.0.0 `docs/skill-anatomy.md` ("description: a string up to 1024 characters")；是 industry-de-facto 上界（与 Anthropic / OpenAI / DSPy / Claude Skills 在 ≤500-char 的 sweet-spot 一致 ─ 1024 仅作为硬刚性上界，不取代 §22 eval-pack curation 工艺对 ≤500-char "good practice" 的鼓励）。
2. **Semantic shape = "what + when"**：description 必须由两个语义 lobe 组成 ─ "what" (这个 ability 解决什么/输出什么；用 1-2 句话) + "when" (什么时候 routing 模型应该 trigger 它；典型 user-prompt 关键词 / 场景特征)。**禁止** 把 SKILL body 的 step-by-step workflow / How To Use / Dogfood Quickstart / Reference Index 段落塞进 description ─ 这些段落由 SKILL body (ON-CALL tier C8) 与 references/* (LAZY tier C9) 承担，不属于 routing-time EAGER metadata。违反此条意味着 (a) C7 EAGER token 被无谓抬高（每 session 都付费）；(b) R4 near_miss_FP_rate 上升（routing 模型把 narrative 误读为关键词命中）；(c) R8 description_competition_index 拉爆（多个 ability 的长 description 互相 keyword-collide）。
3. **Cross-tree mirror invariant**：source-of-truth (`.agents/skills/<name>/SKILL.md`) 与平台镜像 (`.cursor/skills/<name>/SKILL.md` + `.claude/skills/<name>/SKILL.md`) 的 `description` 必须 **byte-identical**。任何 mirror 之间出现 description drift 会被 `tools/spec_validator.py` BLOCKER 15 grep-pattern 同时命中（每个文件单独 measure 后 max 取上限不超 cap），并由 §10 持久化合约的 V3_drift_signal 守护跟踪。

#### 24.1.1 spec_validator BLOCKER 15 实现

`tools/spec_validator.py::check_description_cap_1024(repo_root)` (Stage 4 Wave 1d 落地；与 §17.7 hard rule 14 一一映射) 实现 grep pattern：

- **发现源**：`rglob('SKILL.md')` 限定在 `.agents/skills/`、`.cursor/skills/`、`.claude/skills/` 三棵树；并 `rglob('basic_ability_profile.yaml')` 限定在 `.local/dogfood/**/round_*/`（沿用 BLOCKER 14 的 `_iter_basic_ability_profiles` discovery）。
- **抽取**：SKILL.md 走 YAML frontmatter `description` 字段（`---\n...\n---` block 内）；BAP 走 `basic_ability.description` 字段；BAP 缺 description 时回退到 `basic_ability.intent`。
- **测量**：`min(len(s), len(s.encode('utf-8')))`（§24.1 binding cap convention）。
- **判定**：测量值 > 1024 = FAIL；≤ 1024 = PASS。Findings 携带文件路径 + ability_id + 实际长度 + 字符 / 字节哪个先触顶。
- **SKIP-as-PASS 路径**（per §17.7 binding 与 §13.6.4 grace period 同源工艺）：(a) 仓库内 0 个 SKILL.md 且 0 个 BAP（pre-bootstrap repo）；(b) 当前 `--spec` 目标不含 §24 marker（即 spec 不是 v0.4.2-rc1+，pre-v0.4.2 artefact 走 SKIP 路径，确保 v0.4.0 / v0.3.0 / v0.2.0 spec 仍通过 14/14 BLOCKERs）。

#### 24.1.2 What this rule does NOT trigger

为了避免误伤 informational 字段，BLOCKER 15 **明确排除** 以下场景：

- `BasicAbility.intent` 当 `BasicAbility.description` **存在** 时不再二次检查（intent 仅作为 description 缺位的 fallback；description 已 present 时 intent 可以是 narrative paragraph，不受 1024 cap 约束）。
- `BasicAbility.core_goal.statement`（§14.1 schema sketch）─ statement 是 user-observable functional contract 的一句话陈述，与 routing-time metadata 是不同的 observability surface，不受 §24.1 cap 约束（spec_validator BLOCKER 15 不抓 core_goal 子字段）。
- 仓库内的 README / docs / Markdown reference files (e.g. `references/*.md`) ─ 这些是 LAZY tier C9 reference docs，用 §22.5 deterministic seeding 与 §10 persistence contract 守护即可，不进 BLOCKER 15 grep set。
- `metrics_report.yaml.runner_provenance` / `iteration_delta_report.yaml.notes` 等 narrative free-form 字段 ─ 这些是 evidence body，按 §23 method-tagged metrics 工艺守护，与 routing-time metadata 无关。

#### 24.1.3 §11 forever-out re-affirmation

§11.1 four forever-out items（verbatim from §11.1 above）：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. description discipline 是 ability-local hygiene rule，不引入 distribution surface；1024 cap 借鉴自 addyosmani/agent-skills 但 **明确不吸收** 其 marketplace 部分（agent-skills 的 marketplace direction 在 §11.1 forever-out 内部禁止）。 |
| Router 模型训练 | NO. description cap 是 routing-time metadata 长度治理，不喂任何模型；BLOCKER 15 是字符数 cap 检查，不涉及任何 router weight 学习；§5.2 "禁止训练任意规模的 Router 分类 / 排序模型" 字节级保留。 |
| 通用 IDE / Agent runtime 兼容层 | NO. description discipline 守护的是 SKILL.md frontmatter（hand-written YAML） + BAP description（spec-internal field），与 IDE 无关；§7.2 平台优先级（Cursor > Claude Code > Codex bridge-only）字节级保留。 |
| Markdown-to-CLI 自动转换器 | NO. BLOCKER 15 是 grep / length validator，不做 Markdown → CLI 自动生成；description discipline 是手工编辑约束（"what + when" semantic shape 由 ability author 把控），不涉及任何转换工具。 |

**结论**: §24 全部新增内容在 §11 forever-out 内部执行，不踩任何边界。description-discipline absorption 从 addyosmani/agent-skills v1.0.0 仅抄写 1024-char cap 与 "what+when" 语义工艺，**不抄写** marketplace direction / plugin distribution / Markdown-to-CLI conversion 任何相关 surface。

---

## Reconciliation Log (v0.3.0 → v0.4.0-rc1; 2026-04-30)

> 本段为 **Informative 溯源记录**，不属于 Normative 语义；mirror v0.2.0 → v0.3.0-rc1 reconciliation log 的 (a)-(f) 风格，扩展为 (a)-(h) 以容纳 v0.4.0 新增的 §6.1 byte-identicality break + real-LLM runner in-scope 决策。每条都可被 `tools/spec_validator.py`（Stage 4 Wave 1b 扩展后）或 `diff` 自动验证。

### (a) Sections added

| 章节 | 性质 | 简述 | 子节数 |
|---|---|---|---|
| **§18 Token-Tier Invariant** | Normative (NEW) | `token_tier` 顶层 invariant block (`C7/C8/C9`) + EAGER-weighted iteration_delta + R3 split + prose_class taxonomy (Informative) + lazy_manifest packaging gate + tier_transitions block + forever-out | 7 (§18.1–§18.7) |
| **§19 Real-Data Verification** | Normative (NEW) | sub-step of §8.1 step 2 `evaluate` (3-layer: msw fixture / user-install / post-recovery) + `feedback_real_data_samples.yaml` schema + fixture-citation rule + forever-out | 6 (§19.1–§19.6) |
| **§20 Stage Transitions & Promotion History** | Normative (NEW) | `stage_transition_table` + `lifecycle.promotion_history` append-only + `promotion_state` top-level key + `ship_decision.yaml` 7th evidence (when ship_prep) + backward-compat cross-refs + forever-out | 6 (§20.1–§20.6) |
| **§21 Health Smoke Check** | Normative (NEW) | `packaging.health_smoke_check` schema + REQUIRED-when-live-backend BLOCKER + 4-axis taxonomy + packaging-gate enforcement + OTel semconv + forever-out | 6 (§21.1–§21.6) |
| **§22 Eval-Pack Curation Discipline** | Normative (NEW) | 40-prompt minimum (v2_tightened) + G1 `provenance` REQUIRED + `eval_pack_qa_checklist.md` (Informative) + `recovery_harness.template.yaml` (T4) + deterministic seeding (§3.2 #5) + real-LLM cache dir + forever-out | 7 (§22.1–§22.7) |
| **§23 Method-Tagged Metrics** | Normative (NEW) | `<metric>_method` companion fields (`method_taxonomy.template.yaml`) + `_ci_low/_ci_high` confidence band + U1 `language_breakdown` + U4 `state` + R3 split cross-listed + R6_KEYS BLOCKER ignores companions + forever-out | 7 (§23.1–§23.7) |

### (b) Sections preserved byte-identical

`§3` / `§4-main-table` / `§5` / `§7` / `§8-main-list` / `§11` / `§13 (§13.1-§13.5)` / `§14` / `§15` / `§16` / `§17 (§17.1-§17.2)` 主体内容相对 `spec_v0.3.0.md` **字节级一致**，由 `diff` 命令机器验证：

| Section | v0.3.0 source line range | v0.4.0-rc1 status | 验证方法 |
|---|---|---|---|
| §3 (Metric Taxonomy) | lines 151-176 of `spec_v0.3.0.md` | byte-identical (10-row table + 4-item frozen constraints; +1 v0.4.0 add-on sentence) | `diff <(sed -n '151,174p' spec_v0.3.0.md) <(sed -n '<v0.4.0-rc1 §3 lines>p' spec_v0.4.0-rc1.md)` → diff only on add-on sentence |
| §4 main table (§4.1) | lines 178-198 of `spec_v0.3.0.md` | byte-identical (10-metric × 3-profile threshold table); +1 v0.4.0 add-on after §4.2 | `diff` zero output on table proper |
| §5 (Router Paradigm) | lines 210-251 | byte-identical | `diff` zero output |
| §7 (Packaging) | lines 300-337 | byte-identical (+1 v0.4.0 add-on after §7.3 packaging gate) | `diff` zero output on table proper |
| §8.1 8-step list | lines 344-356 | byte-identical | `diff` zero output |
| §11 (Scope Boundaries) | lines 432-455 | byte-identical (+1 v0.4.0 add-on re-affirmation) | `diff` zero output |
| §13 (§13.1-§13.5) | lines 478-545 | byte-identical (whole §13.1-§13.5 verbatim; new §13.6 appended) | `diff` zero output on §13.1-§13.5 |
| §14 (Core-Goal Invariant) | lines 549-790 | byte-identical | `diff` zero output |
| §15 (round_kind Enum) | lines 792-921 | byte-identical | `diff` zero output |
| §16 (Multi-Ability Layout) | lines 923-998 | byte-identical (+1 v0.4.0 add-on after §16.3) | `diff` zero output on §16.1-§16.3.2 |
| §17 (§17.1-§17.2) | lines 1000-1033 | byte-identical (whole §17.1-§17.2 verbatim; new §17.4-§17.6 appended) | `diff` zero output on §17.1-§17.2 |

> Each byte-identical section above carries at most ONE "v0.4.0 add-on" sentence appended after the byte-identical body. Total v0.4.0 add-on sentences across byte-identical sections: §3 (1) + §4.2 (1) + §6.1 (1) + §6.2 (1) + §7.3 (1) + §8.1 step 2 (1) + §8.2 (1) + §9 (1) + §10.1 (1) + §11 (1) + §12 (1) + §16 (1) = 12 add-on sentences total.

### (c) Sections modified — §6.1 value_vector axes count 7 → 8 (FIRST byte-identicality break since v0.1.0 → v0.2.0)

§6.1 value_vector table 在 v0.4.0 加 1 行（第 8 行）`eager_token_delta`：

| 维度 | v0.3.0 | v0.4.0-rc1 | Diff |
|---|---|---|---|
| §6.1 value_vector axes | 7 (`task_delta / token_delta / latency_delta / context_delta / path_efficiency_delta / routing_delta / governance_risk_delta`) | **8** (+ `eager_token_delta`) | **+1 row (NEW `eager_token_delta`)** |

#### (c.1) The 8th row literal text

```
| `eager_token_delta` | `(eager_tokens_without − eager_tokens_with) / eager_tokens_without` | C7 + OTel via tier decomposition (§18.1) |
```

#### (c.2) §6.2 trigger rules table NOT modified, but gets v0.4.0 add-on sentence

§6.2 trigger rules table (4 rows: keep / half_retire / retire / disable_auto_trigger) **byte-identical preserved** from v0.3.0；仅在 table 之后加 1 句 v0.4.0 add-on：

> **v0.4.0 add-on**: §6.2 `half_retire` trigger now also fires on `task_delta` near zero AND `eager_token_delta ≥ +0.10` (v2_tightened bucket) for surface-area-shrinking abilities; this is the dedicated EAGER-axis trigger that v0.3.0's pooled `token_delta` could not isolate.

#### (c.3) §6.3 / §6.4 byte-identical from v0.3.0

§6.3 Decision Artifact (字段集合 unchanged) 与 §6.4 Reactivation Triggers (6 个 triggers unchanged) 字节级保留 v0.3.0。

#### (c.4) Reconciliation pattern — mirror v0.1.0 → v0.2.0 prose-count alignment

v0.1.0 → v0.2.0 ("28→37 子指标" prose-count alignment) = **no semantic change**；v0.3.0 → v0.4.0-rc1 §6.1 7→8 axes = **semantic addition** with byte-identicality break（v0.x 系列第一次真 break）。spec_validator `EXPECTED_VALUE_VECTOR_AXES_BY_SPEC` 按 spec version 切换 (`v0.1.0/v0.2.0/v0.3.0` → 7 axes; `v0.4.0-rc1/v0.4.0` → 8 axes)。

### (d) New §13.6 acceptance criteria subsection added (additive; §13.1-§13.5 unchanged)

§13 (`## 13. Acceptance Criteria for v0.1.0`) §13.1-§13.5 主体内容字节级保留 v0.3.0；新增 additive subsection **§13.6 Acceptance Criteria for v0.4.0-rc1**（mirror v0.3.0-rc1 §13.5 pattern）。§13.6 覆盖 v0.4.0 新增的 §18-§23 + §17.4-§17.6 + §6.1 7→8 break 验收 criteria；含 §13.6.1 (结构与表达)、§13.6.2 (Normative 内容守护)、§13.6.3 (横向一致性)、§13.6.4 (机器可校验项含 14 个 BLOCKER 列表)。

### (e) Templates affected (FORWARD-LOOKING; not yet edited at this Stage 2 spec authoring)

下述 templates 在 Stage 4 Wave 1b 必须 additively 扩展 + 5 个 NEW templates 创建；本 Stage 2 (spec authoring) 不修改任何 template 文件：

| Template | Stage 4 修改 | `$schema_version` bump |
|---|---|---|
| `templates/basic_ability_profile.schema.yaml` | additively 增加 `lifecycle.promotion_history` block (per §20.2) + `current_surface.dependencies.live_backend` field (per §21.2) + `packaging.health_smoke_check` array (per §21.1) + `metrics.<dim>.<metric>_method/_ci_low/_ci_high` companion fields (per §23) | 0.2.0 → 0.3.0 |
| `templates/iteration_delta_report.template.yaml` | additively 增加 `tier_transitions` block (per §18.6) + 8-axis value_vector with `eager_token_delta` (per §6.1 v0.4.0 modification) + OPTIONAL `verdict.weighted_token_delta_v0_4_0` field (per §18.2) | 0.2.0 → 0.3.0 |
| `templates/next_action_plan.template.yaml` | additively 增加 sibling field `token_tier_target ∈ {relaxed, standard, strict}` (per §15 round_kind 工艺扩展，与 §4 v1/v2/v3 gate 对齐) | 0.2.0 → 0.3.0 |
| `templates/router_test_matrix.template.yaml` | UNCHANGED | 0.1.1 (unchanged) |
| `templates/half_retire_decision.template.yaml` | UNCHANGED | 0.1.0 (unchanged) |
| `templates/self_eval_suite.template.yaml` | UNCHANGED | 0.1.0 (unchanged) |
| **NEW** `templates/lazy_manifest.template.yaml` | per §18.5 schema | 0.1.0 (NEW) |
| **NEW** `templates/feedback_real_data_samples.template.yaml` | per §19.2 schema | 0.1.0 (NEW) |
| **NEW** `templates/ship_decision.template.yaml` | per §20.4 schema | 0.1.0 (NEW) |
| **NEW** `templates/recovery_harness.template.yaml` | per §22.4 schema | 0.1.0 (NEW) |
| **NEW** `templates/method_taxonomy.template.yaml` | per §23.1 schema | 0.1.0 (NEW) |
| **NEW** `templates/eval_pack_qa_checklist.md` | Informative reference doc per §22.3 | n/a (Markdown) |

向下兼容契约：Round 1-15 Si-Chip + Round 1-10 chip-usage-helper 的既有 yaml artefact 在 schema_version 0.3.0 下继续校验通过（新增字段在历史 artefact 中 default null + 仅对 Round 16+ 的 Si-Chip / Round 26+ 的 chip-usage-helper 强制 require）。

### (f) `tools/spec_validator.py` upcoming additions (Stage 4 Wave 1b)

| 改动 | 说明 |
|---|---|
| `SCRIPT_VERSION` bump | 0.2.0 → 0.3.0（标记 v0.4.0-rc1 BLOCKER 集合扩展） |
| `SUPPORTED_SPEC_VERSIONS` 加入 | 现有集合 `{"v0.1.0", "v0.2.0-rc1", "v0.2.0", "v0.3.0-rc1", "v0.3.0"}` → `{"v0.1.0", "v0.2.0-rc1", "v0.2.0", "v0.3.0-rc1", "v0.3.0", "v0.4.0-rc1", "v0.4.0"}` |
| `EXPECTED_R6_PROSE_BY_SPEC["v0.4.0-rc1"] = EXPECTED_R6_PROSE_BY_SPEC["v0.4.0"] = 37` | 继承 v0.3.0 reconciled prose count（v0.4.0-rc1 §13.4 byte-identical 保留 v0.3.0 §13.4 整段，因此 anchor `§3 metric key 37 项` 自动满足） |
| `EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.4.0-rc1"] = 30` | 同上；anchor `§4 阈值表 30 个数` 自动满足 |
| **修订** `EXPECTED_VALUE_VECTOR_AXES_BY_SPEC` | `{"v0.1.0": 7, "v0.2.0-rc1": 7, "v0.2.0": 7, "v0.3.0-rc1": 7, "v0.3.0": 7, "v0.4.0-rc1": 8, "v0.4.0": 8}`（per §6.1 7→8 break） |
| **修订** `EXPECTED_EVIDENCE_FILES` | conditional based on `next_action_plan.round_kind`：`ship_prep` → 7（含 ship_decision.yaml）；其它 → 6（与 v0.3.0 相同） |
| **修订** `R6_KEYS` BLOCKER | ignore companion suffixes (`_method`, `_ci_low`, `_ci_high`, `_language_breakdown`, `_state`, `_provenance`, `_sampled_at`, `_sample_size_per_cell`) per §23.6 |
| **新增** BLOCKER 12: `TOKEN_TIER_DECLARED_WHEN_REPORTED` | 当 `metrics_report.yaml.metrics` 中存在任一 `C7/C8/C9` 子键时，`metrics_report.yaml.token_tier` 顶层 block 必须三键全在；缺失 = FAIL |
| **新增** BLOCKER 13: `REAL_DATA_FIXTURE_PROVENANCE` | 当 ability declare `real_data_samples` 时，对应 ability 的 test fixture 文件必须含 `// real-data sample provenance: <captured_at> / <observer>` 注释（grep-able audit trail）；缺失 = FAIL |
| **新增** BLOCKER 14: `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND` | 当 `current_surface.dependencies.live_backend: true` 时，`packaging.health_smoke_check` 必须非空 array；缺失或空 = FAIL |
| Total BLOCKER count | 11 (v0.3.0) + 3 (v0.4.0-rc1) = **14** BLOCKERS at v0.4.0-rc1 |
| Backward-compat sentinel | Round 1-15 Si-Chip + Round 1-10 chip-usage-helper artefact 在 v0.4.0-rc1 spec 下：既有 11 BLOCKER 全部 PASS（其中 VALUE_VECTOR 与 EVIDENCE_FILES 的 expected 值按 spec 版本切换）；新增 3 BLOCKER 在 Round 16+ Si-Chip / Round 26+ chip-usage-helper 才严格执行（per §16.2 / §13.6.4 grace period） |

### (g) §11 forever-out: UNCHANGED

§11.1 four forever-out items **byte-identical preserved**：

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

§18.7 / §19.6 / §20.6 / §21.6 / §22.7 / §23.7 explicit 复核 confirms 上述 4 项均不被 §18 / §19 / §20 / §21 / §22 / §23 触碰。所有 6 个 NEW Normative sections 各自包含一个 `§N.<last> §11 forever-out re-affirmation` 子节（§20 因额外包含 §20.5 backward-compat cross-refs 子节而采用 §20.6；其余 §18/§19/§21/§22/§23 使用 §N.6 或 §N.7），verbatim 重申 4 项 forever-out items 并对 4 项各自 emit "本节是否触碰: NO" 的 explicit table；§11 v0.4.0 add-on 句也在原 §11 内 verbatim 重申 4 项。

frontmatter `forever_out_unchanged: true` 即为本条的机器可读断言。

### (h) Real-LLM runner now in scope (per Q5 + r12.5 PROCEED_MAJOR verdict)

v0.3.0 spec 把 real-LLM runner deferred to "next-version evaluation" (per v0.2.0 ship report deferred items)；r12 §5.5 Q5 lean was "keep deferred for v0.4.0; open in v0.4.1"；user 在 v0.4.0 plan 决议中 OVERRIDE 选 Major (per Q5 user-confirmed)。Stage 1 r12.5 spike 在 sandbox 验证 Veil proxy at `http://127.0.0.1:8086` routes to claude-haiku-4-5/sonnet-4-6/opus-4-6 with PROCEED_MAJOR verdict (T2_pass_k=1.0 on 20-prompt subsample vs deterministic floor 0.5478)；v2_tightened gate `T2 ≥ 0.55` 是 reachable.

- **(h.1) Stage 4 Wave 1c production runner**：`evals/si-chip/runners/real_llm_runner.py` 含 `RouterFloorAdapter` (spec router_floor labels → physical endpoint/model pairs per r12.5 §5.1) + `AnthropicMessagesClient` (raw `requests.post` against Veil-egressed `/v1/messages`) + `RealLlmRunner.evaluate_pack/evaluate_router_matrix` + cache directory (per §22.6) + `--seal-cache` flag for CI determinism (per r12.5 §5.2).
- **(h.2) Veil proxy bootstrap**：Stage 4 Wave 1c 含 `tools/start_real_llm_runtime.sh` (background veil serve + health probe wait) + `tools/stop_real_llm_runtime.sh` (cleanup)；这些 scripts 在 Stage 4 owned-files list 内（不在本 Stage 2 spec authoring 范围）。
- **(h.3) Cost / time budget per round** (per r12.5 §5.3)：≈ 200 calls × 130 tok ≈ 26k tokens per ability per round；≈ $0.02–$0.10 per ability per round at Haiku pricing；two-ability round-pair ~$0.20；96-cell Full router matrix multiplies 8-cell cost by ~12, still under $1 per round.
- **(h.4) `composer_2/fast` substitution rule**：`composer_2` is Cursor-internal (unreachable from sandbox shell)；production runner remap `composer_2/fast` → `claude-haiku-4-5`；spec §5 `router_floor` 仍 nominal `composer_2/fast`；production runner emit substitution in `metrics_report.runner_provenance.models_used`.
- **(h.5) Real-LLM runner does NOT touch §11 forever-out** (per r12.5 §7.3)：runner adds NO marketplace, NO router-model-training (LLM is called as black box for measurement; no weights / demos / prompts / routing decisions persisted into trainable artifact), NO MD-to-CLI, NO generic IDE-compat. Pure `requests`-based measurement client of existing Veil egress；spec §11 boundary preserved.

### Promotion v0.4.0-rc1 → v0.4.0 (2026-04-30)

The Stage 8 ship event flips this spec from `rc` to `frozen` and from `compiled_into_rules: false` to `compiled_into_rules: true`. The promotion is metadata-only: the body of `spec_v0.4.0.md` is **byte-identical** to `spec_v0.4.0-rc1.md` except for 6-7 lines (frontmatter `version` / `status` / `promoted_from` / `compiled_into_rules`, the H1 title, and the preamble status sentence + Pinned-record sentence). Every Normative section (§3 / §4 / §5 / §6 / §7 / §8 / §11 / §13 / §14 / §15 / §17 / §18 / §19 / §20 / §21 / §22 / §23) and every Informative section retains its rc1 wording verbatim.

| Item | rc1 | v0.4.0 final |
|---|---|---|
| `frontmatter.version` | `"v0.4.0-rc1"` | `"v0.4.0"` |
| `frontmatter.status` | `"rc"` | `"frozen"` |
| `frontmatter.promoted_from` | `null` | `"v0.4.0-rc1"` |
| `frontmatter.compiled_into_rules` | `false` | `true` |
| `H1` | `# Si-Chip Spec v0.4.0-rc1（rc — …）` | `# Si-Chip Spec v0.4.0（Frozen — promoted from v0.4.0-rc1; body byte-identical except metadata）` |
| Preamble status line | `> rc 阶段：本文不进入 .rules/ 编译，待 v0.4.0 final ship 后晋升。` | `> Frozen: 本文已进入 .rules/ 编译（compiled_into_rules: true）。` |
| Preamble pinned-record line | `> Pinned historical record: 本文，作为 v0.4.0 final 的上游 baseline。` | `> Pinned historical record: .local/research/spec_v0.4.0-rc1.md（保留作为 v0.4.0 的 rc 上游 baseline，不删除）；.local/research/spec_v0.3.0.md（保留作为 v0.4.0 的 v0.3.0 baseline，不删除）。` |
| End-of-spec H2 | `## End of Si-Chip Spec v0.4.0-rc1（rc — …）` | `## End of Si-Chip Spec v0.4.0（Frozen — promoted from v0.4.0-rc1; body byte-identical except metadata）` |

**Ship event evidence pointers** (Stage 8 ship is gated on the Round 18 + Round 19 v2_tightened consecutive-pass evidence):

- `.local/dogfood/2026-04-30/round_18/metrics_report.yaml` — FIRST v2_tightened pass for Si-Chip (T2_pass_k 0.5478 → 1.0 via real_llm_runner.py first dogfood-side invocation; mvp 8-cell matrix; 640 calls; $0.20 spend).
- `.local/dogfood/2026-04-30/round_18/iteration_delta_report.yaml` — Round 17 → Round 18 axis_status (task_quality +0.4522 + generalizability +0.10 G1 provenance hoist).
- `.local/dogfood/2026-04-30/round_19/metrics_report.yaml` — SECOND v2_tightened pass for Si-Chip via real-LLM cache-replay byte-equivalence to Round 18 (consecutive_v2_passes=2 per §4.2 promotion rule).
- `.local/dogfood/2026-04-30/round_19/iteration_delta_report.yaml` — Round 18 → Round 19 cache-replay byte-equivalent axis values; THIRD WITHIN-v0.4.0-rc1 non-vacuous C0 monotonicity check (1.0 ≥ 1.0).
- `.local/dogfood/2026-04-30/v0.4.0_ship_decision.yaml` — machine-readable ship verdict (companion to this promotion).
- `.local/dogfood/2026-04-30/v0.4.0_ship_report.md` — human-readable ship report.

**Compiled-into-rules invariant**: post-promotion, `.rules/si-chip-spec.mdc` is bumped to spec v0.4.0 and re-compiled into `AGENTS.md` via the DevolaFlow `RuleCompiler`; AGENTS.md §13 grows from 10 hard rules (v0.3.0) to **13 hard rules** (v0.4.0; rules 11 / 12 / 13 per §17.4 / §17.5 / §17.6 add-ons).

**Forever-out re-affirmation**: this promotion does NOT touch §11.1's four forever-out items (marketplace / router-model training / generic IDE compat / Markdown-to-CLI). The `compiled_into_rules` flag flip is a packaging metadata change; the §11.1 Normative content is byte-identical to v0.3.0.

---

## 附录：术语速查与引用索引（Informative）

| 术语 | 引用 |
|---|---|
| Basic Ability / Router Floor / Value Vector (8 axes @ v0.4.0) / Self-Dogfood / Factory Template / Gate Profile / Source of Truth | §2 / §5 / §6 / §8 / §9 / §4 / §7.1（v0.3.0 appendix 保留；见 `r6`/`r8`/`r9`/`r10` 引用） |
| **Core Goal** / **core_goal_test_pack** / **C0_core_goal_pass_rate** (NEW v0.3.0) | §14 / §14.2 / §14.3；`r11_core_goal_invariant.md` §3 |
| **round_kind** / **measurement_only round** (NEW v0.3.0) | §15 / §15.1–§15.2；`r11_core_goal_invariant.md` §4 |
| **Multi-ability layout** (NEW v0.3.0 Informative; Normative target v0.4.x) | §16；`r11_core_goal_invariant.md` §5 |
| **§18 Token-Tier (C7/C8/C9)** (NEW v0.4.0) | §18；r12 §2.1 + §4.1；includes EAGER-weighted iteration_delta (§18.2 / R32), R3 split (§18.3 / R33), prose_class (§18.4 / R37), lazy_manifest (§18.5 / R41), tier_transitions (§18.6 / R34) |
| **§19 Real-Data Verification** (NEW v0.4.0) | §19；r12 §2.2 + §4.2；chip-usage-helper Cycle 5 R45/R46/R47；includes feedback_real_data_samples (§19.2), fixture-citation rule (§19.3 / BLOCKER 13) |
| **§20 Stage Transitions & Promotion History** (NEW v0.4.0) | §20；r12 §2.4 + §4.3；includes stage_transition_table (§20.1 / R15), promotion_history append-only (§20.2 / R17 / OpenSpec archive), promotion_state (§20.3 / R6), ship_decision.yaml 7th evidence (§20.4 / R27) |
| **§21 Health Smoke Check** (NEW v0.4.0) | §21；r12 §2.6 + §4.4；chip-usage-helper Cycle 5 R47；4-axis read/write/auth/dependency (§21.3 / fitgap) |
| **§22 Eval-Pack Curation** (NEW v0.4.0) | §22；r12 §2.5 + §4.5；40-prompt minimum (§22.1 / R3), G1 provenance REQUIRED (§22.2 / R14), recovery_harness (§22.4 / R8), deterministic seeding (§22.5 / MLPerf), real_llm_runner_cache (§22.6 / r12.5) |
| **§23 Method-Tagged Metrics** (NEW v0.4.0) | §23；r12 §2.5 + §4.6；chip-usage-helper R36 2.4× error evidence；method_taxonomy (§23.1), _ci_low/_ci_high (§23.2 / R36), U1 language_breakdown (§23.3 / R29), U4 warm/cold (§23.4 / R19), R3 split (§23.5 / R33) |

| 本规范节 | 主要引用 |
|---|---|
| §1 / §2 / §3 / §4 / §5 / §6 / §7 / §8 / §9 / §10 / §11 / §12 | v0.3.0 bibliographic references preserved byte-identical (see `r6_metric_taxonomy.md` / `r8_router_test_protocol.md` / `r9_half_retirement_framework.md` / `r10_self_registering_skill_roadmap.md` / `r7_devolaflow_nines_integration.md` / `si_chip_research_report_zh.md` § 引用集合) + `r12 §4.1` for §6.1 eager_token_delta 8th axis |
| §13 / §14 / §15 / §16 / §17 (v0.3.0 sections) | v0.3.0 references preserved; `r11_core_goal_invariant.md` §3/§4/§5 primary |
| §17 rules 11/12/13 (NEW v0.4.0) | r12 §4.1 / §4.2 / §4.4 + chip-usage-helper SUMMARY.md Cycle 2/3/5 |
| §18 / §19 / §20 / §21 / §22 / §23 (NEW v0.4.0) | r12 §2.1/§2.2/§2.4/§2.6/§2.5/§2.5 + r12.5 spike PROCEED_MAJOR + chip-usage-helper Cycle 1-5 evidence |
| §17.7 rule 14 + §24 (NEW v0.4.2-rc1) | addyosmani/agent-skills v1.0.0 (push @ 2026-05-03) `docs/skill-anatomy.md` 1024-char description cap convention; spec_validator BLOCKER 15 `DESCRIPTION_CAP_1024` |

---

## End of Si-Chip Spec v0.4.2-rc1（rc — additive 1 Normative section + 1 hard rule + 1 BLOCKER absorbed from addyosmani/agent-skills v1.0.0）
