---
task_id: R8
scope: Skill Router-Test Protocol（不训练 router，只测试 model × thinking-depth floor）
sources_count: 18
cells_mvp: 8
cells_full: 96
anchor_numbers_count: 10
last_updated: 2026-04-28
related_artifacts:
  - r4_endgame_routing.md
  - r6_metric_taxonomy.md
  - r7_devolaflow_nines_integration.md
  - .local/feedbacks/feedbacks_for_research/feedback_for_research_v0.0.1.md
---

# R8 · Skill Router-Test Protocol

> 目标：验证某个 Skill / basic ability 在更弱模型、更浅思考深度、更低成本路径下是否仍能可靠路由和执行。**不训练 router，不自研私有 router，只做测试协议与判定。**

---

## 0. TL;DR

1. **Router-test 的核心输出不是模型排名，而是 `router_floor`**：满足质量 / 触发 / 性能阈值的最弱模型 × 最浅思考深度组合。R6 已把它定义为 D6.R5；R8 给出协议。
2. **不要 train router**。LLMRouterBench (arXiv:2601.07206, 2026) 显示 400K+ instances、21 datasets、33 models、10 routing baselines 下，许多复杂 routing 方法不能稳定超过简单 baseline；OpenRouter 比 Best Single 低 24.7pp，而 Avengers-Pro 只是在 Pareto 上做到 +4% accuracy / -31.7% cost。
3. **MVP 只测 8 个 cells**：2 models × 2 thinking depths × 2 scenario packs；Full 扩展到 6 models × 4 depths × 4 scenario packs = 96 cells。
4. **thinking depth 不等于模型大小**。Composer 2 技术报告明确用 length penalty 让 easy task 快速完成、hard task 更深思；DevolaFlow `task_adaptive_selector.select_context(round_num=N)` 与 `apply_round_escalation` 可以把这一点直接变成测试档位。
5. **Si-Chip 第一版只需要回答一个问题**：这个 ability 是否能从 Opus/deep 降到 Sonnet/Composer/shallow，而不损失触发、通过率、路径效率和成本收益。

---

## 1. 2026 Anchor 数字

| Anchor | 数字 | 用途 |
|---|---:|---|
| LLMRouterBench | 400K+ instances / 21 datasets / 33 models / 10 baselines | 说明 router-test 应标准化，而非凭感觉 |
| LLMRouterBench / OpenRouter | 比 Best Single 低 24.7pp | 反证：商业/复杂 router 不必然更好 |
| LLMRouterBench / Avengers-Pro | +4% accuracy / -31.7% cost | router 的目标是 Pareto，不是单点精度 |
| Composer 2 | CursorBench 61.3 | 专用 coding model 可作为中档 router/executor |
| Composer 2 | Terminal-Bench 2.0 61.7 | 终端 / 工具型场景 anchor |
| Composer 2 | SWE-bench Multilingual 73.7 | 多语言软件工程 anchor |
| Composer 2 | 约 250 tokens/s，较 Composer 1.5 约 4× 快 | latency / path efficiency anchor |
| Claude Haiku 4.5 | $1/M input, $5/M output | 便宜档模型 anchor |
| Claude Sonnet 4.6 | $3/M input, $15/M output | 中档模型 anchor |
| Claude Opus 4.7 | $5/M input, $25/M output | 强模型 / fallback anchor |

> 这些数字只用于设定测试梯度，不用于证明某个模型一定适合 Si-Chip。真正结论必须来自 repo 内 router-test 结果。

---

## 2. Test Matrix

### 2.1 MVP Matrix：8 cells

| 轴 | 取值 |
|---|---|
| model_id | `composer_2`、`sonnet_shallow` |
| thinking_depth | `fast`、`default` |
| scenario_pack | `trigger_basic`、`near_miss` |
| dataset | 每 pack 20 prompts：10 should-trigger + 10 should-not-trigger |

Cells:

| # | model | depth | scenario |
|---:|---|---|---|
| 1 | composer_2 | fast | trigger_basic |
| 2 | composer_2 | fast | near_miss |
| 3 | composer_2 | default | trigger_basic |
| 4 | composer_2 | default | near_miss |
| 5 | sonnet_shallow | fast | trigger_basic |
| 6 | sonnet_shallow | fast | near_miss |
| 7 | sonnet_shallow | default | trigger_basic |
| 8 | sonnet_shallow | default | near_miss |

### 2.2 Full Matrix：96 cells

| 轴 | 取值 |
|---|---|
| model_id | `composer_2`, `haiku_4_5`, `sonnet_4_6`, `opus_4_7`, `gpt_5_mini`, `deterministic_memory_router` |
| thinking_depth | `fast`, `default`, `extended`, `round_escalated` |
| scenario_pack | `trigger_basic`, `near_miss`, `multi_skill_competition`, `execution_handoff` |
| dataset | 每 pack 20-50 prompts |

`6 × 4 × 4 = 96 cells`。

---

## 3. 每 Cell 的 6 字段定义

| 字段 | 定义 |
|---|---|
| input | scenario prompt + available ability list + allowed tools + optional repo state |
| tools | read/search/execute/mock tool set；必须固定，不随模型漂移 |
| output | route decision (`use_skill`, `no_skill`, `ask_clarification`, `fallback`) + optional execution result |
| pass condition | trigger label 正确、必要时 task eval pass、无 forbidden tool、within token/latency budget |
| data source | Skill Creator trigger eval、NineS `eval/self-eval`、OTel traces、DevolaFlow memory_router baseline |
| failure handling | retry same depth once；失败升级 depth；再失败升级 model；最终人工/strong model fallback |

---

## 4. 必测指标

MVP 必测：

| R6 ID | 名称 | 公式 |
|---|---|---|
| T1 | pass_rate | `passed / total` |
| T2 | pass_k | `Pass^k = (c/n)^k`，k=4 |
| T3 | baseline_delta | `with_ability - no_ability` |
| L1/L2 | wall_clock_p50/p95 | OTel duration histogram |
| R1/R2/R3 | trigger precision/recall/F1 | standard |
| R4 | near_miss_FP_rate | FP on near-miss negatives |
| R5 | router_floor | 最弱可通过组合 |
| R6/R7 | routing latency/token overhead | route-only overhead |

Full 增补：

- C4 per_invocation_footprint
- C5 context_rot_risk
- L3 step_count
- L4 redundant_call_ratio
- L5 detour_index
- R8 description_competition_index
- G1 cross_model_pass_matrix

---

## 5. Router Floor 三档阈值

公式：

```text
router_floor = min_by(cost, latency, model_strength)(
  model_id × thinking_depth
  where trigger_F1 >= X
    and near_miss_FP_rate <= Y
    and pass_rate >= Z
    and routing_latency_p95 <= L
    and routing_token_overhead <= O
)
```

| Profile | trigger_F1 | near_miss_FP | pass_rate | latency_p95 | token_overhead | 用途 |
|---|---:|---:|---:|---:|---:|---|
| relaxed | ≥0.75 | ≤0.20 | ≥0.70 | ≤2000ms | ≤0.20 | 探索 / Stage 1-2 |
| standard | ≥0.85 | ≤0.10 | ≥0.80 | ≤1200ms | ≤0.12 | MVP 默认 |
| strict | ≥0.92 | ≤0.05 | ≥0.88 | ≤800ms | ≤0.08 | 生产 / Stage 4+ |

比较顺序建议：

```yaml
model_strength_order:
  - deterministic_memory_router
  - composer_2
  - haiku_4_5
  - gpt_5_mini
  - sonnet_4_6
  - opus_4_7
thinking_depth_order:
  - fast
  - default
  - extended
  - round_escalated
```

---

## 6. Fallback / Escalation 流程

```text
1. deterministic_memory_router 尝试精确或近似匹配
2. composer_2 / fast 做低成本 route
3. 若 trigger_confidence 低或 near_miss，高一档 thinking_depth
4. 若仍失败，升级到 Sonnet/default 或 Sonnet/extended
5. 若 execution_handoff 失败，升级到 Opus 或人工澄清；记录 reinforcement finding
```

与 DevolaFlow 对接：

- `task_adaptive_selector.select_context(task_type, round_num=N)`：生成不同 thinking / model_hint 档位。
- `task_adaptive_selector.apply_round_escalation`：失败后升档。
- `gate/convergence.py`：避免无限 retry。
- `memory_router.lookup_case`：确定性 baseline。
- NineS `self-eval --baseline --compare`：对比当前 floor 与上一版本 floor。

---

## 7. Schema 草案

```yaml
router_test:
  ability_id: "example-skill"
  version: "0.1.0"
  profile: "standard"
  dataset:
    scenario_packs:
      - trigger_basic
      - near_miss
      - multi_skill_competition
      - execution_handoff
    prompts_per_pack: 20
  matrix:
    models:
      - composer_2
      - haiku_4_5
      - sonnet_4_6
      - opus_4_7
    thinking_depths:
      - fast
      - default
      - extended
      - round_escalated
  metrics:
    required:
      - trigger_F1
      - near_miss_FP_rate
      - pass_rate
      - pass_k
      - routing_latency_p95
      - routing_token_overhead
    optional:
      - detour_index
      - per_invocation_footprint
  floor_policy:
    optimize_for:
      - model_strength
      - thinking_depth
      - token_cost
      - latency
    fallback_order:
      - deterministic_memory_router
      - composer_2_fast
      - sonnet_default
      - opus_extended
```

---

## 8. 输出示例

| ability | profile | router_floor | F1 | pass | p95 | token_overhead | decision |
|---|---|---|---:|---:|---:|---:|---|
| `skill-review` | standard | `composer_2/default` | 0.88 | 0.82 | 940ms | 0.09 | keep floor |
| `skill-release` | standard | `sonnet_4_6/default` | 0.86 | 0.84 | 1180ms | 0.11 | no Opus needed |
| `skill-debug` | strict | `opus_4_7/extended` | 0.93 | 0.89 | 4200ms | 0.28 | not routeable cheaply |

---

## 9. 为什么不训练 Router

1. **样本量不足**：LLMRouterBench 花了 400K+ instances 和显著 GPU/API 成本，Si-Chip MVP 没必要复制。
2. **复杂方法未必超过简单 baseline**：2026 证据显示许多 routing 方法不能稳定 outperform simple baselines。
3. **Skill 的路由目标动态变化**：description、eval、模型能力、context budget 都会变；训练出的 router 容易过期。
4. **可解释性更重要**：Si-Chip 需要输出"为什么这个 ability 需要 Sonnet/default"，而不是黑盒概率。
5. **DevolaFlow / NineS 已能测 floor**：当前阶段应先测，再决定是否需要 router。

---

## 10. 关键发现

1. Router-test 应是 **model × thinking-depth × scenario × dataset** 的矩阵测试，不是单次 prompt 判断。
2. `router_floor` 是 Si-Chip 的核心指标之一：它回答"能不能用更便宜、更快、更浅的模型满足路由需求"。
3. Composer 2 / Haiku / Sonnet / Opus 的公开数字足以构成第一版梯度，不需要训练专用模型。
4. DevolaFlow 的 `task_adaptive_selector` 已提供升档机制，NineS 提供 baseline compare；Si-Chip 只需写 harness。
5. MVP 8 cells 足够验证方向；Full 96 cells 用于 Stage 4+。

---

## 11. 来源清单

### 11.1 外部 2026 来源

1. LLMRouterBench, arXiv:2601.07206, 2026 — 400K+ instances / 21 datasets / 33 models / 10 baselines.
2. Cursor, **Composer 2 Technical Report**, arXiv:2603.24477v2, 2026 — CursorBench 61.3 / Terminal-Bench 61.7 / SWE-bench Multilingual 73.7 / 250 tokens/s.
3. Cursor blog, **Introducing Composer 2**, 2026-03.
4. BenchLM.ai, **Claude API Pricing: Haiku 4.5, Sonnet 4.6, and Opus 4.7**, 2026-04-13 — Haiku $1/$5, Sonnet $3/$15, Opus $5/$25 per M tokens.
5. Anthropic Claude Opus 4.7 launch, 2026-04-16 — premium fallback anchor.
6. OpenAI Agents SDK production patterns, 2026 — cheap routing/supervisor layer pattern.
7. BFCL V4 / Gorilla 2026 leaderboard refresh — function-calling / irrelevance / format sensitivity anchor.
8. Anthropic Skill Creator 2.0 eval / benchmark / trigger tuning, 2026-03.

### 11.2 本地路径

1. `/home/agent/workspace/Si-Chip/.local/research/r6_metric_taxonomy.md` — R5 router_floor, R6/R7 routing latency/token overhead.
2. `/home/agent/workspace/Si-Chip/.local/research/r7_devolaflow_nines_integration.md` — `task_adaptive_selector`, NineS, memory_router 对接。
3. `/home/agent/workspace/Si-Chip/.local/research/r4_endgame_routing.md` — F1-F8 failure modes.
4. `/home/agent/workspace/DevolaFlow/src/devolaflow/task_adaptive_selector.py` — `select_context`, `apply_round_escalation`.
5. `/home/agent/workspace/DevolaFlow/src/devolaflow/memory_router/router.py` — deterministic routing baseline.
6. `/root/.codex/skills/nines/commands/self-eval.md` — baseline compare command.
