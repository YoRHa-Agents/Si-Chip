---
task_id: R9
scope: Skill Half-Retirement / Value Preservation Framework
sources_count: 17
value_vector_dims: 7
simplification_strategies: 9
reactivation_triggers: 6
last_updated: 2026-04-28
related_artifacts:
  - r6_metric_taxonomy.md
  - r7_devolaflow_nines_integration.md
  - r8_router_test_protocol.md
  - .local/feedbacks/feedbacks_for_research/feedback_for_research_v0.0.1.md
---

# R9 · Skill 半退役 / 价值保留框架

> 核心修正：**被强模型功能覆盖 ≠ 立即退役**。如果 Skill 仍在 token、latency、context footprint、路径效率、触发稳定性上有净收益，应进入 `half_retire`：保留核心优化点，压缩表面积，降低触发优先级，并周期复审。

---

## 0. TL;DR

1. **Stage 0 不应只有 retire**。应拆成 `retire / half_retire / keep` 三态；`half_retire` 对应"功能价值降低，但性能价值仍存在"。
2. **判定依据是 Value Vector，而不是单个 pass_rate_delta**。至少包括 task quality、token、latency、context、path efficiency、routing、governance 七维。
3. **半退役的动作不是删除，而是简化**：短 description、manual-only、pure metadata、合并 references、移除大 scripts、降优先级、保留 benchmark-winning core。
4. **encoded preference 与 capability uplift 要分开**。Capability uplift 更容易过期；encoded preference 即使 base model 会做，也可能因流程、上下文、成本优势长期保留。
5. **DevolaFlow 已提供半退役基础设施**：`entropy_manager` 做 drift/staleness，`learnings.decay_confidence` 做长期价值衰减，`feedback.py` 落盘决策，NineS `self-eval --baseline --compare` 做复审。

---

## 1. Value Vector

定义：

```yaml
value_vector:
  task_delta:              # 功能收益
  token_delta:             # token 净节省
  latency_delta:           # 响应时间净节省
  context_delta:           # 上下文污染净减少
  path_efficiency_delta:   # 路径绕弯净减少
  routing_delta:           # 触发 / 路由质量净收益
  governance_risk_delta:   # 风险变化
```

正值代表 Skill 相对 no-skill baseline 更好；负值代表更差。

| 维度 | 公式 | 数据源 | keep | half_retire | retire |
|---|---|---|---:|---:|---:|
| task_delta | `pass_rate_with - pass_rate_without` | R6 T3 | ≥ +0.10 | -0.02 ~ +0.10 | < -0.02 |
| token_delta | `(tokens_without - tokens_with) / tokens_without` | R6 C4 + OTel | ≥ +0.20 | ≥ +0.10 | < +0.10 |
| latency_delta | `(p95_without - p95_with) / p95_without` | R6 L1/L2 | ≥ +0.20 | ≥ +0.10 | < +0.10 |
| context_delta | `(footprint_without - footprint_with) / footprint_without` | R6 C1-C5 | ≥ +0.25 | ≥ +0.10 | < +0.10 |
| path_efficiency_delta | `(detour_without - detour_with) / detour_without` | R6 L5 | ≥ +0.20 | ≥ +0.10 | < +0.10 |
| routing_delta | `trigger_F1_with - trigger_F1_without` 或 route success delta | R6 D6 | ≥ +0.10 | ≥ 0 | < 0 |
| governance_risk_delta | risk_without - risk_with | R6 D7 | ≥ 0 | mixed | < 0 |

半退役典型形态：

```text
task_delta ≈ 0
AND (token_delta OR latency_delta OR context_delta OR path_efficiency_delta) >= threshold
AND governance_risk_delta is not strongly negative
```

---

## 2. 三态决策矩阵

| 功能收益 | 性能 / 上下文收益 | 风险 | 决策 | 解释 |
|---|---|---|---|---|
| 高 | 高/中 | 可控 | keep | Skill 仍有功能和性能价值 |
| 高 | 低 | 可控 | keep + optimize | 功能仍强，先优化性能 |
| 近零 | 高 | 可控 | half_retire | 功能被覆盖，但核心优化点仍值得保留 |
| 近零 | 中 | 可控 | half_retire + review | 保留 30-90 天复审 |
| 近零 | 低 | 可控 | retire | 没有显著价值 |
| 负 | 任意 | 任意 | retire / disable | Skill 伤害结果 |
| 任意 | 任意 | 高 | disable auto trigger | 权限 / drift / credential 风险优先 |

ASCII 流程：

```text
          ┌──────────────┐
          │ run baseline │
          └──────┬───────┘
                 │
          task_delta > 0.10?
          ├─ yes ──> KEEP or OPTIMIZE
          │
          no / near-zero
                 │
   perf/context/path benefit >= threshold?
          ├─ yes ──> HALF_RETIRE
          │             ├─ simplify surface
          │             ├─ lower trigger priority
          │             └─ schedule re-test
          │
          no
                 │
       risk high or stale?
          ├─ yes ──> RETIRE / DISABLE
          └─ no  ──> HALF_RETIRE with short review window
```

---

## 3. 半退役简化策略

| # | 策略 | Trigger 条件 | 风险 | 复审周期 |
|---:|---|---|---|---|
| 1 | 缩短 description | C1 metadata_tokens red/yellow；R3 仍达标 | 触发召回下降 | 30 天 |
| 2 | body 摘要化 | C2 body_tokens > 5k；task_delta 近零 | 丢失边界条件 | 30 天 |
| 3 | reference 冷存储 | C3 resolved_tokens 高但引用少 | 需要时找不到上下文 | 60 天 |
| 4 | scripts 精简为核心函数 | scripts 大但只用少数入口 | 功能碎片化 | 60 天 |
| 5 | auto → manual-only | R4 near_miss_FP 高；误触发伤害大 | 用户忘记手动调用 | 30 天 |
| 6 | 降低 routing priority | scope_overlap_score 高 | 正确触发下降 | 30 天 |
| 7 | 合并到更广 Skill | 与 sibling 重叠，且独立价值低 | 大 Skill context 变重 | 60 天 |
| 8 | 保留 pure-metadata trigger | 功能由 base model 完成，但需要流程提醒 | 过度提示 | 90 天 |
| 9 | 保留 benchmark-winning core | task_delta 近零但 token/latency/path 明显优 | 维护成本隐藏 | 60 天 |

半退役不是"放着不管"。每个 half-retired skill 必须有：

- `review_by`
- `next_review_at`
- `retained_value`
- `simplification_applied`
- `reactivation_triggers`

---

## 4. 保留窗口 / 复审周期

| 事件 | 动作 |
|---|---|
| 模型升级 | 立即重跑 no-skill baseline + with-skill baseline |
| Skill 30 天无调用 | 进入 half-retire review |
| 90 天无调用且无性能收益 | retire |
| 依赖 API/CLI schema drift | disable auto trigger，跑 drift eval |
| routing floor 下降一档 | 可进一步简化 |
| routing floor 上升一档 | 考虑重新激活或回滚 |

DevolaFlow 对接：

- `learnings.decay_confidence` 默认 30 天半衰期，可作为 value confidence 衰减。
- `entropy_manager.DocFreshness` 提供 staleness。
- `DeviationScanner` 提供 drift。
- `gate/cycle_detector.py` 可检测反复 half-retire / reactivate 的循环；若循环 ≥2 次，应人工 review。

---

## 5. 重新激活触发器

半退役 Skill 遇到以下任一信号，应升级回 active review：

1. no-skill baseline 在新模型版本上回退，`task_delta` 重新 > +0.10。
2. 新场景 / 新 domain 出现，半退役 Skill 的 references/scripts 正好覆盖。
3. router-test 显示便宜模型需要该 Skill 才能通过，`router_floor` 下降。
4. context_delta / token_delta / latency_delta 变得显著（例如 token_delta ≥ 0.25）。
5. 依赖 API 变更后，Skill 的 wrapper 比 base model 更稳。
6. 用户手动调用频率回升（例如 30 天 ≥ 5 次）。

---

## 6. Schema 草案

```yaml
half_retire_decision:
  ability_id: "example-skill"
  version: "0.2.0"
  decided_at: "2026-04-28"
  decision: "half_retire"   # keep | half_retire | retire
  reason: "base model matches pass rate, but skill saves 34% tokens and 28% p95 latency"
  value_vector:
    task_delta: 0.01
    token_delta: 0.34
    latency_delta: 0.28
    context_delta: 0.22
    path_efficiency_delta: 0.18
    routing_delta: 0.03
    governance_risk_delta: 0.00
  simplification:
    applied:
      - shrink_description
      - reference_cold_storage
      - manual_only_trigger
    retained_core:
      - "deterministic script for CSV normalization"
      - "3-step checklist encoded as pure metadata"
  review:
    next_review_at: "2026-05-28"
    triggers:
      - model_upgrade
      - router_floor_regression
      - token_delta_below_0_10
  provenance:
    baseline_report: ".local/research/evals/example/no_skill.json"
    with_skill_report: ".local/research/evals/example/with_skill.json"
    nines_compare: ".local/research/evals/example/nines_compare.json"
```

---

## 7. 2026 实证支撑

| 案例 | 数字 / 事实 | 半退役启发 |
|---|---|---|
| Anthropic Skill Creator 2.0 | Benchmark 比较 pass rate / time / tokens；用于 outgrowth detection | 功能覆盖后仍需看 time/tokens |
| Capability Uplift vs Encoded Preference | uplift 会过期；encoded preference 更耐久 | 不能只看能力覆盖 |
| ACE | browser automation token 成本减少 49%，并提升稳定性 | 性能收益可独立于功能收益存在 |
| RTK | CLI 拦截节省 60-90% tokens | 被模型覆盖的 shell 操作仍值得保留压缩器 |
| Cursor Composer 2 | 约 250 tokens/s，且 CursorBench 61.3 | 专用/轻量路径可保留速度优势 |
| Claude pricing 2026 | Haiku $1/$5 vs Sonnet $3/$15 vs Opus $5/$25 | 价值要折算成本，不只看 pass |
| Aider Architect mode | R4 记录 4.2× token reduction | 分层保留优化点 |
| LLMRouterBench | Avengers-Pro +4% accuracy / -31.7% cost | Pareto 优化比单点强模型更重要 |

---

## 8. 半退役失败模式

| 失败模式 | 说明 | 缓解 |
|---|---|---|
| 简化过度 | description 缩短后 trigger recall 崩 | 重跑 trigger eval |
| manual-only 遗忘 | 用户不知道要手动调用 | 在 parent index 保留提示 |
| scope overlap 低估 | 合并后误触发上升 | 运行 R8 multi_skill_competition |
| API drift 静默失败 | 保留 script 但依赖变更 | DeviationScanner + smoke eval |
| value vector 翻转未检测 | 模型升级后性能优势消失 | 模型升级强制复审 |
| 只看 token 不看路径 | token 少但绕路多 | 同时看 detour_index |
| 半退役循环 | half_retire ↔ active 反复 | cycle_detector + 人工判定 |

---

## 9. 与 R6/R7 的严格对接

R6 子指标：

- D1：T1/T2/T3 判定功能收益。
- D2：C1-C5 判定上下文经济性。
- D3：L1-L7 判定 latency 和路径效率。
- D6：R1-R8 判定触发和路由成本。
- D7：V1-V4 判定治理风险。

R7 上游能力：

- `entropy_manager`：V3/V4 drift + staleness。
- `learnings.decay_confidence`：value confidence 随时间衰减。
- `feedback.py`：half-retirement decision 落盘。
- `nines self-eval --baseline --compare`：复审对比。
- `gate/cycle_detector.py`：检测反复半退役循环。

---

## 10. 关键发现

1. 半退役是 Si-Chip 的关键差异点：它避免"功能被覆盖就删除"的粗糙判断。
2. Skill 的价值必须拆成 function value 与 efficiency value；后者经常在强模型时代仍然成立。
3. `encoded preference` 类型 Skill 更应该半退役/简化，而不是退役。
4. 半退役动作本质是 active forgetting：保留核心优化点，删除上下文噪声。
5. 半退役必须周期复审，否则会变成更隐蔽的上下文垃圾。

---

## 11. 来源清单

### 11.1 外部 2026 来源

1. Claude Code Skills 2.0, 2026-03-07 — evals / benchmarks / A-B / trigger tuning / capacity uplift vs encoded preferences.
2. Anthropic Skill Creator, 2026 — benchmark pass rate / time / tokens / description optimizer.
3. BenchLM.ai Claude pricing 2026 — Haiku/Sonnet/Opus cost tiers.
4. Cursor Composer 2 Technical Report, arXiv:2603.24477v2 — CursorBench / speed / thinking penalties.
5. LLMRouterBench, arXiv:2601.07206 — routing Pareto / cost tradeoff.
6. ACE / Agentic Context Engine, 2026 — token reduction and Skillbook learning.
7. Agentic Academy lifecycle, 2026-02-17 — Decommission / update lifecycle.
8. OpenTelemetry GenAI semconv, 2026-04 — metrics source for token/duration/tool traces.

### 11.2 本地路径

1. `/home/agent/workspace/Si-Chip/.local/research/r6_metric_taxonomy.md` — R6 7 维 28 子指标。
2. `/home/agent/workspace/Si-Chip/.local/research/r7_devolaflow_nines_integration.md` — DevolaFlow/NineS 对接。
3. `/home/agent/workspace/Si-Chip/.local/research/r8_router_test_protocol.md` — router_floor 复审输入。
4. `/home/agent/reference/agentic-context-engine/README.md:17-112` — Skillbook / token reduction。
5. `/home/agent/reference/ContextOS/README.md:39-75` — Active Forgetting / Index Lifecycle Manager。
6. `/home/agent/workspace/DevolaFlow/src/devolaflow/entropy_manager.py` — staleness/drift。
7. `/home/agent/workspace/DevolaFlow/src/devolaflow/learnings.py` — decay_confidence / last_accessed。
8. `/root/.codex/skills/nines/commands/self-eval.md` — baseline compare。
