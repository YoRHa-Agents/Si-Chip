---
title: Si-Chip Basic Ability 决策清单
language: zh-CN
version: v0.0.5
last_updated: 2026-04-28
status: canonical
purpose: "用于判断一个 Skill/basic ability 当前状态、价值、优化路径、router floor、半退役决策与可安装 Skill/Plugin 产出状态。"
---

# Si-Chip Basic Ability 决策清单

## 0. 使用原则

不要先问“它是 Markdown first、code first 还是 CLI first”。先问：

1. 这个 **basic ability** 解决什么问题？
2. 它当前有什么可测收益？
3. 它的上下文、耗时、路径、路由成本是否合理？
4. 它应该继续迭代、产品化执行、做 router-test、半退役，还是完全退役？

输出统一为：

```yaml
ability_id: example
stage: evaluated
surface_type: markdown
shape_hint: markdown_first
decision: half_retire
next_action: "缩短 description，改 manual-only，保留核心 script；30 天后复审"
confidence: 0.82
```

---

## 1. BasicAbilityProfile 最小字段

```yaml
basic_ability:
  id: "example"
  intent: "这个能力解决什么问题"
  owner: "optional"
  current_surface:
    type: markdown|script|cli|mcp|sdk|memory|mixed
    path: "..."
    shape_hint: markdown_first|code_first|cli_first|registry_first|memory_first|mixed
  packaging:
    install_targets:
      claude_code: false
      cursor: false
      codex: false
    source_of_truth: ".agents/skills/<name>/"
    generated_targets: []
  lifecycle:
    stage: exploratory|evaluated|productized|routed|governed|half_retired|retired
    last_reviewed_at: "YYYY-MM-DD"
    next_review_at: "YYYY-MM-DD"
  eval_state:
    has_eval_set: false
    has_no_ability_baseline: false
    has_self_eval: false
    has_router_test: false
    has_iteration_delta: false
  metrics:
    task_quality: {}
    context_economy: {}
    latency_path: {}
    generalizability: {}
    usage_cost: {}
    routing_cost: {}
    governance_risk: {}
  value_vector: {}
  decision:
    action: null
    rationale: null
    risk_flags: []
```

---

## 2. Intake 检查

| 问题 | 目的 | 缺失时动作 |
|---|---|---|
| 能否一句话说明 intent？ | 防止能力边界模糊 | 回到探索访谈 |
| 是否有 ≥3 个代表任务？ | 防止过早模板化 | 收集案例 |
| 是否有 expected output？ | 支持 eval | 写验收标准 |
| 是否有 no-ability baseline？ | 判断净收益 | 跑 baseline |
| 是否能在目标工具本地安装或被读取？ | 验证产出形态 | 建 packaging bridge |
| 是否能对自身运行 self-eval？ | 验证 dogfood 能力 | 建 self-eval harness |
| 是否有触发正负例？ | 支持 router-test | 建 trigger eval |
| 是否有真实调用痕迹？ | 判断使用价值 | 标记低置信度 |
| 是否存在权限 / 凭据 / drift 风险？ | 防止 unsafe productization | 加 risk flag |

---

## 3. Stage 判断

| Stage | 判定条件 | 下一步 |
|---|---|---|
| `exploratory` | 有 intent 和案例，但无 eval / baseline | 建 eval set，补 expected outputs |
| `evaluated` | 有 eval、baseline、pass/token/time/trigger 指标 | 根据瓶颈进入 improve / productize / half-retire |
| `productized` | 稳定步骤已下沉到 script/CLI/MCP/SDK | 加 CI、schema、version、error reporting |
| `routed` | 有 router-test，能得出 router_floor | 优化 floor 或降级模型 |
| `governed` | 有 owner/version/telemetry/deprecation | 定期复审 |
| `half_retired` | 功能收益近零但性能/上下文/路径收益存在 | 简化表面积，周期复审 |
| `retired` | 功能与性能收益均低或风险高 | 归档、停止触发 |

---

## 4. Progressive 指标 Gate（v1 → v2 → v3 递进）

v0.0.5 起阈值按三档递进。连续 **2 轮 dogfood** 都通过 gate N 才能进入 gate N+1。

| 指标 | v1_baseline | v2_tightened | v3_strict |
|---|---:|---:|---:|
| `pass_rate` | ≥0.75 | ≥0.82 | ≥0.90 |
| `pass_k` (k=4) | ≥0.40 | ≥0.55 | ≥0.70 |
| `baseline_delta` | ≥0 | ≥+0.05 | ≥+0.10 |
| `metadata_tokens` | ≤120 | ≤100 | ≤80 |
| `per_invocation_footprint` | ≤9000 | ≤7000 | ≤5000 |
| `wall_clock_p95` | ≤45s | ≤30s | ≤20s |
| `trigger_F1` | ≥0.80 | ≥0.85 | ≥0.90 |
| `near_miss_FP_rate` | ≤0.15 | ≤0.10 | ≤0.05 |
| `router_floor` | Sonnet default 可过 | Composer/Haiku default 可过 | Composer fast 可过 |
| `iteration_delta` | ≥+0.05 一项 | ≥+0.10 一项 | ≥+0.15 一项 |

约束：

- 7 维 / 28 子指标 **全量实现**，不做 MVP 子集。
- 每次升级 gate 前必须出具连续 2 轮通过证据。
- `iteration_delta` 改善不得伴随 `pass_rate` 下降。

---

## 5. 下一步动作决策

| 观察 | 决策 |
|---|---|
| 无 eval / baseline | `create_eval_set` |
| pass 低，trigger 正常 | `improve_ability_body` |
| pass 高，trigger 差 | `improve_description` |
| pass 高，但 token / latency 高 | `optimize_context_or_productize_surface` |
| 重复步骤稳定、参数清晰 | `productize_execution_surface` |
| 当前 ability 就是 Si-Chip 自身，且 docs/spec 已冻结 | `create_self_registering_skill_package` |
| 三目标无法本地安装或读取 | `build_packaging_bridge` |
| 缺少 self-eval / iteration delta | `run_self_dogfood_loop` |
| 多 ability 竞争或误触发 | `run_router_test` |
| base model 功能追平，但性能收益明显 | `half_retire` |
| base model 功能追平，性能收益也低 | `retire` |
| drift / credential 风险高 | `disable_auto_trigger` |

---

## 6. Router 范式研究（不训练 router）

v0.0.5 明确：Si-Chip 不训练任何 router 模型；Router 工作是研究让既有模型完成 routing 的更有效范式。Router-Test 是衡量范式是否有效的唯一工具。

### 6.1 何时跑 Router-Test

满足任一条件即跑：

- ability 数量 > 10。
- 出现 near-miss 误触发。
- 希望把 `router_floor` 从 Opus/extended 下移到 Sonnet/default 甚至 Composer/default。
- 想确认浅思考是否够用。
- 多 ability 描述相似。
- 测试新的 routing 范式（metadata retrieval / heuristic / kNN / description 优化 / thinking-depth 升级 / fallback 策略）。

### 6.2 MVP Matrix（8 cells）

| 轴 | 取值 |
|---|---|
| model_id | `composer_2`, `sonnet_shallow` |
| thinking_depth | `fast`, `default` |
| scenario_pack | `trigger_basic`, `near_miss` |

### 6.3 Full Matrix（96 cells）

| 轴 | 取值 |
|---|---|
| model_id | `composer_2`, `haiku_4_5`, `sonnet_4_6`, `opus_4_7`, `gpt_5_mini`, `deterministic_memory_router` |
| thinking_depth | `fast`, `default`, `extended`, `round_escalated` |
| scenario_pack | `trigger_basic`, `near_miss`, `multi_skill_competition`, `execution_handoff` |

### 6.4 Router Floor 阈值（绑定 v1/v2/v3 gate）

| Gate | `trigger_F1` | `near_miss_FP` | `pass_rate` | `latency_p95` | `token_overhead` |
|---|---:|---:|---:|---:|---:|
| v1_baseline | ≥0.80 | ≤0.15 | ≥0.75 | ≤2000ms | ≤0.18 |
| v2_tightened | ≥0.85 | ≤0.10 | ≥0.82 | ≤1200ms | ≤0.12 |
| v3_strict | ≥0.92 | ≤0.05 | ≥0.90 | ≤800ms | ≤0.08 |

### 6.5 Router Floor 决策

| floor | 判断 |
|---|---|
| deterministic / Composer fast | 极适合轻量路由，可简化描述并稳定产品化 |
| Composer default / Haiku | 可进入 routed capability |
| Sonnet default | 保留中档模型路由 |
| Opus / extended | 不适合声明轻量路由，需继续优化范式或降级目标 |

**严禁**：训练任何 router 模型；发明私有黑盒 router 替代 `router_floor` 判定。

---

## 7. 半退役决策

### 7.1 Value Vector

| 维度 | 公式 | 半退役触发 |
|---|---|---|
| `task_delta` | `pass_with - pass_without` | 近零 |
| `token_delta` | `(tokens_without - tokens_with) / tokens_without` | ≥0.10 |
| `latency_delta` | `(p95_without - p95_with) / p95_without` | ≥0.10 |
| `context_delta` | `(footprint_without - footprint_with) / footprint_without` | ≥0.10 |
| `path_efficiency_delta` | `(detour_without - detour_with) / detour_without` | ≥0.10 |
| `routing_delta` | `trigger_F1_with - trigger_F1_without` | ≥0 |
| `governance_risk_delta` | `risk_without - risk_with` | 非负 |

### 7.2 三态判定

| 条件 | 决策 |
|---|---|
| `task_delta >= +0.10` | keep |
| `task_delta ≈ 0` 且任一性能/上下文/路径收益 ≥0.10 | half_retire |
| `task_delta ≈ 0` 且无明显收益 | retire |
| `task_delta < 0` | disable / retire |
| 风险高 | 先 disable auto trigger |

### 7.3 半退役动作

- 缩短 description。
- body 摘要化。
- reference 冷存储。
- scripts 只保留核心函数。
- auto trigger 改 manual-only。
- 降低 routing priority。
- 合并到更广 ability。
- 保留 pure-metadata workflow reminder。
- 保留 benchmark-winning core。

### 7.4 重新激活触发器

- 新模型 no-ability baseline 回退。
- 新场景出现，旧 ability 的流程仍有效。
- router_floor 因该 ability 显著下降。
- token/latency/context 收益重新变强。
- 用户手动调用频率回升。
- 依赖 API 变更后 wrapper 更稳定。

---

## 8. Productization 决策

不要把 productization 等同于 CLI。

| Surface | 适合 | 不适合 |
|---|---|---|
| `scripts/` | Skill 内部确定性步骤 | 跨项目复用 |
| CLI | 本地文件 / shell / 开发流 | 远程多租户 |
| MCP | 多工具统一暴露给 Agent | 工具很少 |
| SDK | code-first agent 框架 | 非工程用户 |
| hosted API | 企业权限 / 审计 / 多租户 | 本地离线场景 |
| pure metadata | 功能由模型完成，但流程提醒有价值 | 复杂执行 |

Productize 前必须满足：

- 输入输出结构稳定。
- 能写自动测试。
- 失败可显式暴露。
- token/latency/path 收益明确。
- 有维护者。

### 8.1 Self-Registering Skill Package 决策（平台优先级已冻结）

Si-Chip 自身优先走 self-registering Skill package。**顺序：Cursor → Claude Code → Codex（后续）**。**Marketplace 永远不做**。

| 顺序 | 目标 | 产物 | Gate |
|---:|---|---|---|
| 1 | Cursor | `.agents/skills/si-chip/SKILL.md` + `.cursor/skills/si-chip/SKILL.md` | `.agents/skills/si-chip/` 为源；Cursor 目录为同步产物；rules 经 `AGENTS.md` 生效 |
| 2 | Claude Code | `.claude/skills/si-chip/SKILL.md` | 同步自 `.agents/skills/si-chip/`；commands/hooks 留到 self-eval 稳定通过后 |
| 3 | Codex | `AGENTS.md` + `.codex/` bridge | 不假设原生 `SKILL.md` runtime；仅通过 instructions/profile；优先级最低 |

Packaging gate（按 v1_baseline 起步）：

- Cursor 先能本地安装 / 被读取；再推进 Claude Code；Codex 最后。
- `metadata_tokens <= 120`（v1），逐档收紧到 v2 ≤100、v3 ≤80。
- `body_tokens <= 5000`。
- 安装步骤 `<= 2`。
- 可为 Si-Chip 自身生成 `BasicAbilityProfile` 并输出 `iteration_delta`。
- 可运行 self-eval 并产出 `next_action_plan`。
- Spec / Rules 变更后必须重新 compile `AGENTS.md`，否则视为 drift。

---

## 9. 工厂模板循环

```text
capture -> profile -> evaluate -> diagnose -> improve -> router-test -> half-retire review -> iterate -> package/register
```

| 步骤 | 输出 |
|---|---|
| capture | intent、案例、expected output |
| profile | BasicAbilityProfile |
| evaluate | eval set、baseline、benchmark |
| diagnose | 7 维指标报告 |
| improve | 下一轮优化任务 |
| router-test | router_floor |
| half-retire review | keep / half_retire / retire |
| iterate | 新版本与历史对比 |
| package/register | 按 Cursor → Claude Code → Codex 顺序同步到可安装表面 |

---

## 10. 决策输出模板

```yaml
ability_id: example
current_surface:
  type: markdown
  shape_hint: markdown_first
stage: evaluated
metrics:
  pass_rate: 0.84
  pass_k_4: 0.52
  baseline_delta: 0.01
  metadata_tokens: 92
  per_invocation_footprint: 4300
  wall_clock_p95: 18.4
  trigger_F1: 0.88
router_test:
  profile: standard
  router_floor: composer_2/default
packaging:
  install_targets:
    claude_code: true
    cursor: true
    codex: true
  source_of_truth: ".agents/skills/si-chip/"
self_eval:
  cases_total: 6
  pass_rate: 0.84
  iteration_delta:
    token_delta: 0.18
    latency_delta: 0.11
value_vector:
  task_delta: 0.01
  token_delta: 0.34
  latency_delta: 0.28
  context_delta: 0.22
  path_efficiency_delta: 0.18
decision:
  action: half_retire
  simplification:
    - shrink_description
    - manual_only_trigger
    - retain_core_script
  rationale: "功能被 base model 覆盖，但仍节省 34% token、28% p95 latency，并能由 Composer/default 路由。"
review:
  next_review_at: "2026-05-28"
  triggers:
    - model_upgrade
    - router_floor_regression
    - token_delta_below_0_10
```
