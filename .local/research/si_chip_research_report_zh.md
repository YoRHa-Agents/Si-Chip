---
title: Si-Chip Skill 能力迭代优化体系统一调研报告
language: zh-CN
version: v0.0.5
last_updated: 2026-04-28
status: canonical
canonical_role: "主报告；规范 `spec_v0.1.0.md` 为 frozen 规范，R1-R10 为证据库"
frozen_spec: .local/research/spec_v0.1.0.md
compiled_rules: .rules/si-chip-spec.mdc
rules_output: AGENTS.md
source_artifacts:
  - r1_tool_paradigms.md
  - r2_lifecycle_literature.md
  - r3_evaluation.md
  - r4_endgame_routing.md
  - r6_metric_taxonomy.md
  - r7_devolaflow_nines_integration.md
  - r8_router_test_protocol.md
  - r9_half_retirement_framework.md
  - r10_self_registering_skill_roadmap.md
verdict: "Si-Chip 是持久化的 Skill/basic ability 优化工厂；v0.1.0 规范已冻结并作为仓库 Rules 生效；下一步进入 design 阶段。Marketplace 与 router 模型训练永远不做。"
---

# Si-Chip Skill 能力迭代优化体系统一调研报告

## 0. 执行结论

Si-Chip 的核心对象不应是某种文件形态的 `Skill`，而应是更抽象的 **Basic Ability**：一个可被 Agent 发现、调用、评估、优化、简化或退役的能力单元。

统一后的判断是：

> **Si-Chip 要做的是“测试 + 指标驱动的 Skill/basic ability 持久优化工厂模板体系”。**
>
> 它通过多轮次 eval、benchmark、router-test、half-retirement review 和工厂模板，让一个能力不断适配更多模型、更多场景、更低成本路径，而不是把 Markdown 自动转换成 CLI，也不是一开始就完成所有工具生态兼容。
>
> v0.0.4 后进一步明确：Si-Chip 的产出本身也应成为一个可本地注册 / 安装的 Skill 或 Plugin，先在自身仓库上 dogfood，证明它能优化和迭代自己，再用于优化其他 Skill。

因此，v0.1.0 规范冻结时：

1. 抽象 `BasicAbility` 为第一类对象。
2. 建立 7 维 / 28 子指标体系（**全量实现，不做 MVP 子集**）。
3. 建立阶段判定与下一步建议（状态机：exploratory | evaluated | productized | routed | governed | half_retired | retired）。
4. 建立 router-test 协议，研究让模型完成 routing 的更有效范式；**严禁训练 router 模型**。
5. 建立半退役机制，`half_retire` 必须基于评测指标（R9 value vector）。
6. 复用 DevolaFlow / NineS 作为工厂运行底座。
7. 打包为 `si-chip` Skill，优先级顺序：**Cursor → Claude Code → Codex（后续）**。Codex 仅经 `AGENTS.md` + `.codex/` bridge，不假设原生 SKILL.md runtime。
8. 阈值按 `v1_baseline → v2_tightened → v3_strict` 分档递进，连续 2 轮通过 gate N 才进入 gate N+1。
9. 规范作为仓库 Rules 生效，通过 `.rules/si-chip-spec.mdc` 编译进 `AGENTS.md`。
10. **Marketplace 与 router 模型训练永远不做**。

---

## 1. 文档分层

`.local/research/` 下文档现在分为三层：

| 层级 | 文件 | 角色 |
|---|---|---|
| Spec (Frozen) | `spec_v0.1.0.md` | v0.1.0 冻结规范；§3/§4/§5/§6/§7/§8/§11 为 Normative |
| Rules | `.rules/si-chip-spec.mdc` | 由 spec 压缩成的规则层，编译进 `AGENTS.md` |
| Rules Output | `AGENTS.md` | 由 `.rules/si-chip-spec.mdc` 编译而成，是 Agent 读取的强约束入口 |
| Canonical | `si_chip_research_report_zh.md` | 主报告，解释 spec 由来与上下文 |
| Canonical | `decision_checklist_zh.md` | 操作手册，供逐个 BasicAbility 决策使用 |
| Index | `README.md` | 文档地图、阅读顺序、版本说明 |
| Evidence | `r1-r10_*.md` | 证据库，支持 spec 的研究论证 |

读取优先级：Spec = Rules > Canonical > Evidence。当 canonical 文档与 spec 冲突时，spec 优先。

---

## 2. 从“三阶段 Skill”到“Basic Ability 工厂”

### 2.1 原三阶段模型的保留与修正

原模型：

```text
复杂 Markdown 探索 -> 有验收标准的 Markdown 收敛 -> CLI 包装 -> Skill-as-Agent
```

保留点：

- 初期确实常以对话、Markdown、规则、流程清单等形式沉淀。
- 一旦有验收标准，就可以通过 eval/benchmark 进入收敛。
- 稳定、重复、参数化的部分应下沉到确定性执行层。
- 长期目标是让更弱、更快、更便宜的模型也能正确选择和调用能力。

修正点：

- **Markdown 不是必经起点**：LangGraph、ADK、Pydantic-AI、CrewAI 等是 code-first。
- **CLI 不是唯一终点**：scripts、MCP、SDK、hosted API、registry toolkit 都可能是执行表面。
- **退役不是删除**：强模型覆盖功能后，仍可能保留 token、latency、context、path 优势。
- **小模型 router 不需要训练**：先测试 `router_floor`，再决定是否值得做更复杂路由。
- **核心不是 shape，而是 ability 的可测、可改、可复审。**

### 2.2 统一抽象：Basic Ability

`BasicAbility` 是 Si-Chip 的第一层对象。字段见 `spec_v0.1.0.md §2` 与 `decision_checklist_zh.md §1`，本节只强调几个冻结点：

- 字段范围已由 spec §2.1 冻结；任何新增字段需先改 spec 再改其他文档。
- `shape_hint` 只是属性，不作为第一版分流主线。
- `packaging.install_targets` 三个字段严格按 **Cursor → Claude Code → Codex** 顺序评估和推进。
- `value_vector` 七个分量都要求能落到数字，不允许凭感觉打分。

---

## 3. 统一生命周期

统一后的生命周期不是线性升级链，而是可回退、可半退役、可复审的状态机：

| Stage | 名称 | 核心问题 | 典型动作 |
|---|---|---|---|
| S0 | Retired / Deprecated / Half-retired | 是否仍值得存在？若功能被覆盖，是否仍有性能价值？ | retire、half-retire、manual-only、保留核心优化点 |
| S1 | Exploratory Capture | 这个能力是否值得沉淀？ | 收集案例、描述 intent、列输入输出 |
| S2 | Evaluated Ability | 是否有可验证收益？ | 建 eval、跑 baseline、算 pass/token/time/trigger |
| S3 | Productized Execution Surface | 是否应下沉到确定性执行？ | scripts、CLI、MCP、SDK、API |
| S4 | Routed Capability | 是否能被更弱模型和路由层稳定选择？ | router-test、near-miss、multi-skill competition |
| S5 | Governed Skill System | 是否能组织级持续复用？ | owner、version、telemetry、A/B、deprecation policy |

关键变化：S0 不是终点垃圾桶，而是价值复审入口。`half_retired` 是一等状态。

---

## 4. 统一指标体系

R6 将指标统一成 7 个维度、28 个子指标。第一版不需要全部实现，但数据结构要预留。

| 维度 | 目的 | 代表指标 |
|---|---|---|
| D1 Task Quality | 能力底线 | `pass_rate`, `pass_k`, `baseline_delta`, `error_recovery_rate` |
| D2 Context Economy | 上下文污染 / footprint | `metadata_tokens`, `body_tokens`, `per_invocation_footprint`, `context_rot_risk` |
| D3 Latency & Path Efficiency | 响应速度与路径绕弯 | `wall_clock_p95`, `step_count`, `redundant_call_ratio`, `detour_index` |
| D4 Generalizability | 跨模型 / 跨域 / 版本稳定 | `cross_model_pass_matrix`, `OOD_robustness`, `model_version_stability` |
| D5 Learning & Usage Cost | 使用和学习成本 | `first_time_success_rate`, `setup_steps_count`, `time_to_first_success` |
| D6 Routing Cost | 面向 Agent 的触发与路由成本 | `trigger_F1`, `near_miss_FP_rate`, `router_floor`, `routing_token_overhead` |
| D7 Governance / Risk | 权限、凭据、漂移、陈旧度 | `permission_scope`, `credential_surface`, `drift_signal`, `staleness_days` |

MVP 必须实现 8 个指标：

1. `pass_rate`
2. `pass_k`
3. `baseline_delta`
4. `metadata_tokens`
5. `per_invocation_footprint`
6. `wall_clock_p95`
7. `trigger_F1`
8. `router_floor`

这些指标覆盖用户反馈里的主要关注点：任务完成、性能、上下文、耗时、路径、泛用性、使用成本、路由成本。

---

## 5. Router 范式研究：寻找更有效的路由方式，不训练 router

v0.0.5 明确：**Si-Chip 不训练任何 router 模型**。Router 工作是研究"让既有模型完成 routing 的更有效范式"，输入输出都是已有模型与既有 thinking-depth 档位。

### 5.1 Router-Test 矩阵

```text
router-test = model_id × thinking_depth × scenario_pack × dataset
```

| 规模 | 轴 | 取值 |
|---|---|---|
| MVP 8 cells | model_id | `composer_2`, `sonnet_shallow` |
| | thinking_depth | `fast`, `default` |
| | scenario_pack | `trigger_basic`, `near_miss` |
| Full 96 cells | model_id | `composer_2`, `haiku_4_5`, `sonnet_4_6`, `opus_4_7`, `gpt_5_mini`, `deterministic_memory_router` |
| | thinking_depth | `fast`, `default`, `extended`, `round_escalated` |
| | scenario_pack | `trigger_basic`, `near_miss`, `multi_skill_competition`, `execution_handoff` |

核心输出：

```text
router_floor = 满足阈值的最弱模型 × 最浅 thinking_depth
```

### 5.2 Progressive Gate Profiles

阈值不是一次定死，而是按 `v1_baseline → v2_tightened → v3_strict` 分档递进。每次升级 gate 需要连续 2 轮 dogfood 通过上一档。

| 指标 | v1_baseline | v2_tightened | v3_strict |
|---|---:|---:|---:|
| `pass_rate` | ≥ 0.75 | ≥ 0.82 | ≥ 0.90 |
| `trigger_F1` | ≥ 0.80 | ≥ 0.85 | ≥ 0.90 |
| `near_miss_FP_rate` | ≤ 0.15 | ≤ 0.10 | ≤ 0.05 |
| `metadata_tokens` | ≤ 120 | ≤ 100 | ≤ 80 |
| `per_invocation_footprint` | ≤ 9000 | ≤ 7000 | ≤ 5000 |
| `wall_clock_p95` | ≤ 45s | ≤ 30s | ≤ 20s |
| `iteration_delta` (一项效率轴改善) | ≥ +0.05 | ≥ +0.10 | ≥ +0.15 |

### 5.3 Router 范式研究任务（不训练）

- 研究 metadata retrieval、heuristic / kNN、description 优化、thinking-depth 升级、fallback 策略。
- 对每种范式跑 router-test 矩阵。
- 目标是推动 `router_floor` 下移、`routing_token_overhead` 下降，而非训练任何 router 模型。
- 如果 `composer_2/default` 可过，说明该能力具备轻量路由潜力；如果只有 `opus_4_7/extended` 可过，则不应宣称可轻量路由。

---

## 6. 半退役：价值保留而非简单删除

R9 修正了原本“base model 覆盖就 retire”的粗糙判断。

### 6.1 Value Vector

半退役判断使用 7 维 value vector：

| 维度 | 公式 | 含义 |
|---|---|---|
| `task_delta` | `pass_with - pass_without` | 功能收益 |
| `token_delta` | `(tokens_without - tokens_with) / tokens_without` | token 节省 |
| `latency_delta` | `(p95_without - p95_with) / p95_without` | 响应收益 |
| `context_delta` | `(footprint_without - footprint_with) / footprint_without` | 上下文收益 |
| `path_efficiency_delta` | `(detour_without - detour_with) / detour_without` | 路径收益 |
| `routing_delta` | `trigger_F1_with - trigger_F1_without` | 路由收益 |
| `governance_risk_delta` | `risk_without - risk_with` | 风险变化 |

### 6.2 三态判断

| 条件 | 决策 |
|---|---|
| `task_delta` 高 | keep |
| `task_delta` 近零，但 token/latency/context/path 有显著收益 | half-retire |
| `task_delta` 近零，性能收益也低 | retire |
| `task_delta` 为负 | disable / retire |
| 风险高 | 先 disable auto trigger |

### 6.3 半退役动作

- 缩短 description。
- body 摘要化。
- reference 冷存储。
- scripts 只保留核心函数。
- auto trigger 改 manual-only。
- 降低 routing priority。
- 合并到更广 ability。
- 保留 pure-metadata workflow reminder。
- 保留 benchmark-winning core。

---

## 7. DevolaFlow / NineS 复用边界

R7 结论：Si-Chip 至少 80% 的基础设施可以复用现有上游。

| 领域 | 可复用能力 |
|---|---|
| Gate / 评分 | DevolaFlow `gate/scorer.py`, `gate/models.py`, `gate/profiles.py` |
| 收敛 | `gate/convergence.py`, `gate/ratchet.py`, `gate/reinforcement.py` |
| 半退役 | `entropy_manager.py`, `learnings.py`, `feedback.py` |
| Context | `compression_pipeline.py`, `compressor.py` |
| Routing baseline | `memory_router/router.py`, `memory_router/cache.py` |
| 多档思考深度 | `task_adaptive_selector.select_context`, `apply_round_escalation` |
| 评测 | NineS `eval`, `self-eval`, `iterate`, `analyze`, `collect` |
| 模板工厂 | DevolaFlow `template_engine/*` |

Si-Chip 必须自研的薄层只有：

1. `BasicAbilityProfile` schema。
2. Metrics bridge：Skill Creator / NineS / OTel / DevolaFlow traces -> R6 指标。
3. Stage + Value classifier。
4. Half-retirement reviewer。
5. Router-test harness。
6. Factory templates。

---

## 8. 工厂模板主流程

统一后的 Si-Chip factory loop：

```text
1. Capture
   收集能力意图、案例、输入输出、当前 surface。

2. Profile
   生成 BasicAbilityProfile，记录 shape 但不 shape-first 分流。

3. Evaluate
   建 eval set，跑 no-ability baseline 与 with-ability。

4. Diagnose
   计算 7 维指标，定位瓶颈：能力、上下文、路径、路由、泛用性、治理风险。

5. Improve
   选择优化任务：改 description、补 eval、压缩 context、拆 scripts、产品化执行等。

6. Router-Test
   测 model × thinking-depth floor，研究更有效的 routing 范式，**不训练 router 模型**。

7. Half-Retire Review
   若功能被覆盖但性能收益仍在，则简化保留；若无收益则 retire。

8. Iterate
   用 DevolaFlow / NineS 的 convergence 与 self-eval 进入下一轮。

9. Package / Register
   将通过 gate 的 Si-Chip 能力打包为可安装 Skill/Plugin，并同步到目标 IDE / Agent 工具。
```

---

## 9. 自注册 Skill/Plugin 行动路线

R10 将 Si-Chip 的产出形式明确为 **self-registering Skill/Plugin**。这不是分发优先，而是 dogfood 优先：Si-Chip 先把自己变成可安装能力，再用自己评估、优化、压缩和迭代自己。

### 9.1 目标平台（冻结优先级：Cursor → Claude Code → Codex）

| 顺序 | 平台 | 第一优先产物 | 策略 |
|---:|---|---|---|
| 1 | Cursor | `.agents/skills/si-chip/SKILL.md` + `.cursor/skills/si-chip/SKILL.md` | `.agents/skills/si-chip/` 作为中立源，Cursor 目录作为同步产物；rules 经 `AGENTS.md` 生效 |
| 2 | Claude Code | `.claude/skills/si-chip/SKILL.md` | 先 Skill，后 Plugin；长内容放 `references/`；commands/hooks 在 self-eval 稳定通过后再做 |
| 3 | Codex（后续） | `AGENTS.md` + `.codex/` bridge | 不假设 Codex 有真实 `SKILL.md` runtime；仅 instructions/profile bridge，必要时才做 |

Marketplace **永远不做**。

### 9.2 推荐阶段

| Phase | 名称 | Gate |
|---|---|---|
| P0 | Doc/Spec Freeze | **已完成**：`spec_v0.1.0.md` 冻结，编译进 `AGENTS.md` |
| P1 | Design（当前阶段） | 产出 schema、架构、接口；不做实现；完成后才可进入 P2 |
| P2 | Self Skill Package（full scope） | 可生成自身 `BasicAbilityProfile`；全量 7 维 / 28 子指标均可输出；安装步骤 ≤2 |
| P3 | Self Evaluation Harness | ≥6 eval cases；有 no-ability baseline；报告机器可读 |
| P4 | Dogfood Iteration Loop | 通过 v1_baseline gate；连续 2 轮后进入 v2 |
| P5 | Cross-IDE Packaging | Cursor → Claude Code → Codex 顺序推进 |
| P6 | Plugin Distribution | 仅限非 marketplace 的本地安装 / 分发；不做 marketplace |

### 9.3 Self-Dogfood 成功定义（多轮迭代）

Si-Chip v0.1.0 成功不以"支持多少工具"衡量，而以自证能力与多轮迭代证据衡量：

1. 可本地安装为 `si-chip` Skill 或 bridge（优先 Cursor，再 Claude Code）。
2. 可为自身产出 `BasicAbilityProfile`。
3. 可跑 no-ability baseline 与 with-Si-Chip eval。
4. 可输出 `metrics_report`、`router_floor_report`、`half_retire_decision`、`next_action_plan`、`iteration_delta`。
5. 连续 ≥2 轮 dogfood 都通过 `v1_baseline` 的 `iteration_delta` 阈值。
6. 改善不得以 `pass_rate` 明显下降为代价。
7. 每一轮 `half_retire` 决策都必须附带 R9 value vector 数据，不能凭感觉。

---

## 10. 路线图（Full Scope，不做 MVP 子集）

v0.0.5 确认：Si-Chip 是自迭代工厂，必须 **全量实现** 下列模块，而不是挑子集做 MVP。

### M1：Spec Freeze（已完成）

- `spec_v0.1.0.md` 冻结。
- `.rules/si-chip-spec.mdc` 编译进 `AGENTS.md`。

### M2：Design（当前阶段）

- `BasicAbilityProfile` 最终 schema。
- 7 维 / 28 子指标接口定义。
- 6 个 factory template schema。
- 状态机 + Progressive gate 决策表。
- Router 范式研究的实验设计（不训练模型）。
- Dogfood persistence 目录结构。

### M3：Factory Engine（全量）

- BasicAbilityProfile loader + saver。
- 7 维 28 子指标 bridge（NineS / OTel / DevolaFlow traces 全通道）。
- Stage classifier。
- Half-retirement reviewer（基于 R9 value vector，强制评测指标）。
- Router-test harness（MVP 8 cells + Full 96 cells）。
- Factory templates loader + runner（复用 DevolaFlow template engine）。
- Iteration delta report + learnings persistence。

### M4：Self Skill Package

- `.agents/skills/si-chip/` 作为 source of truth。
- 同步到 `.cursor/skills/si-chip/`、`.claude/skills/si-chip/`、`AGENTS.md` + `.codex/` bridge。
- 按 Cursor → Claude Code → Codex 顺序启用。

### M5：Self Evaluation Harness

- ≥6 个 dogfood eval cases。
- 持续 no-ability baseline vs with-Si-Chip 对比。
- 机器可读 iteration delta 报告。

### M6：Dogfood Iteration Loop

- 连续 ≥2 轮通过 `v1_baseline`。
- 升入 `v2_tightened`。
- 再升入 `v3_strict`。
- 每轮产物全部持久化到 `.local/dogfood/<date>/`。

### M7：Cross-Platform Sync + Rules 同步

- 每次 spec/规则变更强制重新 compile `AGENTS.md`。
- `.cursor/skills/si-chip/` 与 `.claude/skills/si-chip/` 同步。
- `.codex/` bridge 最后完成。

---

## 11. 冻结决策（v0.0.5）

1. **项目性质**：持久化 Skill/basic ability 优化工厂。
2. **核心对象**：`BasicAbility`（非 shape-first）。
3. **评价体系**：7 维 / 28 子指标 **全量实现**，`v1 → v2 → v3` 阈值递进，连续 2 轮通过才升档。
4. **路由层面**：研究让模型完成 routing 的更有效范式；**永远不训练 router 模型**。
5. **退役层面**：`keep / half_retire / retire` 三态，`half_retire` 必须基于评测指标。
6. **工程层面**：复用 DevolaFlow / NineS，只自研薄层。
7. **产出层面**：Si-Chip 自身先做成可安装 Skill/Plugin，在本仓库 dogfood 通过后才可外用。
8. **平台优先级**：Cursor → Claude Code → Codex（后续）。**Marketplace 永远不做**。
9. **规范层级**：`spec_v0.1.0.md` 冻结 → `.rules/si-chip-spec.mdc` → `AGENTS.md` 生效；spec 与 canonical 冲突时 spec 优先。
10. **顺序**：spec freeze ✅ → design（当前）→ implement → dogfood → cross-platform。
