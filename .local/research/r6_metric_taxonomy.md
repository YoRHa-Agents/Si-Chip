---
task_id: R6
scope: Skill 指标多维 taxonomy（dimensions × sub-dimensions）
sources_count: 23
dimensions: 7
sub_metrics_count: 28
mvp_subset_count: 8
last_updated: 2026-04-27
provenance: "L0-direct fallback after subagent capacity exhausted"
related_artifacts:
  - r3_evaluation.md
  - r4_endgame_routing.md
  - .local/feedbacks/feedbacks_for_research/feedback_for_research_v0.0.1.md
---

# R6 · Skill 指标多维 taxonomy

> v0.0.2 · 不重复 R3 的 benchmark 全景，只做指标设计。
> 中文为主，英文保留专有名词、API 名、子指标 key。
> 时间窗：以 2026-01-01 起的论文 / 文档为主要论据。

---

## 0. TL;DR（给决策者的 5 条）

1. **指标确实需要"维度 × 子维度"分层**。R3 给出了 8 个 skill-level metrics（AP / TF1 / TpO / CSR / MRVD / Pk / RoF / SMRI），但它们其实分别落在不同维度上。R6 把它们重排进 7 维，并补 **20 个新增子指标**（共 28 个），其中 11 个是 R3 没覆盖的（绕弯指数、复用率、router floor、context rot risk 等）。
2. **首要新增维度是 "Path Efficiency"（路径效率）**。2026 公开的 `AgentProcessBench`（arXiv:2603.14465, 8,509 step annotations）和 `AgentEval` `code_tool_efficiency` / `DeepEval Step Efficiency` 都把"绕弯 / 冗余 / 自愈"做成可度量指标。这正对应用户 feedback 的"处理路径有没有绕弯路"。
3. **Routing Cost 的核心是 "router floor"**——满足全部阈值的最弱模型 × 最浅思考深度。LLMRouterBench (arXiv:2601.07206, ACL 2026 Findings) 已给出 "no single model dominates" + "many recent routing methods fail to reliably outperform simple baselines" 的硬证据。Si-Chip 不要 train router，要测 floor。
4. **Context Economy 必须含 "context rot risk"**。Chroma 18-frontier-models 研究 + Tianpan 2026-04 测试 13 frontier models 显示 11 个在 32K token 跌破 50% baseline。每个 Skill 的 metadata + body + scripts 是否会推到 cliff 区间，是一等公民指标。
5. **OpenTelemetry GenAI semconv (development status, 2026-04)** 已经把 `gen_ai.client.operation.duration`、`gen_ai.client.token.usage`、`gen_ai.tool.name`、`gen_ai.tool.call.arguments`、`mcp.method.name` 等做成事实标准。Si-Chip 的"数据源"列直接对接 OTel attribute，避免发明字段。

---

## 1. 7 顶级维度 × 28 子指标 主矩阵

> 每个 cell 是一条子指标。下文 §2 对每条给出 6 字段。Cell key 同时是 R6 内部 ID。

| 维度 | 子指标 | 已在 R3？ | MVP？ |
|---|---|---|---|
| **D1 Task Quality 能力底线** | T1 pass_rate（基础通过率） | ✅ | ✅ |
| | T2 pass_k（k 次重复一致通过率） | ✅ | ✅ |
| | T3 baseline_delta（vs no-skill baseline 净增益） | ✅ | ✅ |
| | T4 error_recovery_rate（首次失败后自愈成功率） | ➖ | — |
| **D2 Context Economy 上下文经济性** | C1 metadata_tokens（frontmatter + name + description token） | ➖ | ✅ |
| | C2 body_tokens（SKILL.md body token） | ➖ | — |
| | C3 resolved_tokens（references + scripts 出口注入的 token） | ➖ | — |
| | C4 per_invocation_footprint（一次调用净注入 token） | ➖ | ✅ |
| | C5 context_rot_risk（落在 32K-64K cliff 风险评分 0-1） | ➖ | — |
| | C6 scope_overlap_score（与同 namespace 其他 skill description 的余弦相似度最大值） | 部分 (SMRI) | — |
| **D3 Latency & Path Efficiency 响应与路径效率** | L1 wall_clock_p50 / L2 wall_clock_p95 | ✅ (TpO 包含一部分) | ✅ |
| | L3 step_count（tool call 步数） | ➖ | — |
| | L4 redundant_call_ratio（重复调用比） | ➖ | — |
| | L5 detour_index（实际步数 / 最优步数） | ➖ | — |
| | L6 replanning_rate（agent 自发重规划的次数 / task） | ➖ | — |
| | L7 think_act_split（think token : act token） | ➖ | — |
| **D4 Generalizability 泛用性 / 跨模型跨域** | G1 cross_model_pass_matrix（Opus/Sonnet/Haiku/Composer/小模型矩阵） | ➖ | ✅ |
| | G2 cross_domain_transfer_pass | ➖ | — |
| | G3 OOD_robustness（adversarial / format perturb 下 pass） | 部分 (BFCL format_sensitivity) | — |
| | G4 model_version_stability（同 family 跨版本 pass 抖动） | ➖ | — |
| **D5 Learning & Usage Cost 使用与学习成本** | U1 description_readability（Flesch / 中文可读性） | ➖ | — |
| | U2 first_time_success_rate（首次使用成功率） | ➖ | ✅ |
| | U3 setup_steps_count（前置步骤数） | ➖ | — |
| | U4 time_to_first_success（中位数秒数） | ➖ | — |
| **D6 Routing Cost 面向 agent 的路由成本** | R1 trigger_precision / R2 trigger_recall / R3 trigger_F1 | ✅ (TF1) | ✅ |
| | R4 near_miss_FP_rate（"近义但不该触发"的误触发率） | ✅ (一部分 RoF) | — |
| | R5 router_floor（满足全部阈值的最弱模型 × 最浅思考深度） | ➖ | ✅ |
| | R6 routing_latency_p95 / R7 routing_token_overhead | ➖ | — |
| | R8 description_competition_index（多 skill 同时存在时正确选中率） | ➖ | — |
| **D7 Governance / Risk** | V1 permission_scope（allowed_tools 数 + sandbox） | ➖ | — |
| | V2 credential_surface（需要凭据的 tool 数） | ➖ | — |
| | V3 drift_signal（依赖 API/CLI schema 变更次数） | ➖ | — |
| | V4 staleness_days（last_used + last_modified） | ➖ | — |

> 总计 **7 维 / 28 子指标**；其中 R3 已有 5 条（重排进新维度），新增 23 条。MVP 子集见 §6。

---

## 2. 每条子指标的 6 字段定义

> 字段：① 中英文名 ② 公式 ③ 数据源 ④ 阈值（green / yellow / red）⑤ 2026 佐证 ⑥ 重叠依赖

### D1 Task Quality 能力底线

#### T1 pass_rate / 基础通过率
- 公式：`pass_rate = passed_evals / total_evals`
- 数据源：Anthropic Skill Creator `grading.json` `summary.pass_rate`，或 NineS `nines eval` 输出 [^anth-skill-creator] [^nines-eval]
- 阈值：green ≥ 0.85；yellow 0.70-0.85；red < 0.70
- 佐证：R3 §0 第 2 条；Anthropic Skill Creator 2026-03 [^anth-skill-creator]
- 重叠依赖：被 T2、T3 直接消费；不能孤立判断

#### T2 pass_k / k 次重复一致通过率
- 公式：`Pass^k = (c/n)^k`，c=单次成功数，n=重复次数；推荐 k ∈ {1,2,4}
- 数据源：tau-bench / τ²-bench / τ³-bench 多次重复 + `auto_error_identification.py` [^tau-bench-readme]
- 阈值：green Pass¹ ≥ 0.85 ∧ Pass⁴ ≥ 0.55；yellow Pass¹ ≥ 0.75 ∧ Pass⁴ ≥ 0.40；red 任一更低
- 佐证：R3 §1.2；τ-bench README airline `Pass¹=0.46 → Pass⁴=0.225` [^tau-bench-readme]
- 重叠依赖：T1 是 k=1 的特例

#### T3 baseline_delta / 相对 no-skill baseline 净增益
- 公式：`Δ = pass_rate_with_skill − pass_rate_without_skill`
- 数据源：Anthropic Skill Creator `benchmark.md` 中 with_skill vs baseline 两列 [^anth-skill-creator]
- 阈值：green Δ ≥ +0.10；yellow 0 ≤ Δ < 0.10；red Δ ≤ 0（半退役候选）
- 佐证：R3 §0 第 6 条 "Stage-0 retired" 概念；R6 §5 半退役判定输入
- 重叠依赖：D1 + Stage 0 半退役决策的核心信号

#### T4 error_recovery_rate / 自愈成功率
- 公式：`recoveries / first_failures`
- 数据源：`gen_ai.client.operation.duration` + retry trace + tool error attribution [^otel-genai-metrics] [^otel-genai-attrs]
- 阈值：green ≥ 0.50；yellow 0.20-0.50；red < 0.20
- 佐证：AgentEval `code_tool_success` 重试模式 [^agenteval-metrics]
- 重叠依赖：与 L6 replanning_rate 强相关

### D2 Context Economy 上下文经济性

#### C1 metadata_tokens
- 公式：`tokens(SKILL.md frontmatter + name + description)`，用 tiktoken 或 model 自带 tokenizer
- 数据源：static analysis；DevolaFlow `local/compiler.py::_estimate_tokens` 同等思路
- 阈值：green ≤ 100；yellow 100-200；red > 200（违反 Anthropic skill-creator 推荐 [^anth-skill-creator] L95）
- 佐证：Anthropic skill-creator §"Progressive Disclosure" L93-L97；Calmops "Skills 50 个 metadata 总 ~5000 token" [^calmops]
- 重叠依赖：C1 + C2 + C4 决定 router 时的最低 context cost

#### C2 body_tokens
- 公式：`tokens(SKILL.md body)`
- 数据源：static；DevolaFlow `compression_pipeline.py::CompressionPipeline.run` 可作压缩前 baseline [^df-compression]
- 阈值：green ≤ 5000；yellow 5000-10000；red > 10000（远超 Anthropic 推荐"<500 lines"）
- 佐证：Anthropic skill-creator §"Progressive Disclosure" L96
- 重叠依赖：与 C5 context_rot_risk 强相关

#### C3 resolved_tokens
- 公式：sum(tokens) over actually-loaded references/scripts per invocation
- 数据源：runtime trace + OTel `gen_ai.tool.call.arguments` size
- 阈值：green ≤ 3000；yellow 3000-8000；red > 8000
- 佐证：Anthropic skill-creator §"Bundled Resources" L83-L88
- 重叠依赖：C4 = C1 + C2 + C3

#### C4 per_invocation_footprint
- 公式：C1 + C2 + C3
- 数据源：组合
- 阈值：green ≤ 7000；yellow 7000-15000；red > 15000
- 佐证：Cursor Composer 2 上下文压力公开数字 [^cursor-composer-2]
- 重叠依赖：直接喂入 C5

#### C5 context_rot_risk
- 公式：`risk = sigmoid((session_total_tokens − 32000) / 8000)`，落在 0-1
- 数据源：runtime；OTel `gen_ai.client.token.usage` 累计 [^otel-genai-metrics]
- 阈值：green < 0.20；yellow 0.20-0.60；red ≥ 0.60
- 佐证：Tianpan 2026-04 "11/13 frontier models drop below 50% baseline by 32K" [^context-cliff]；Chroma 18-model context rot study [^morph-rot]
- 重叠依赖：与 C4、L1 共同影响 stage 跃迁

#### C6 scope_overlap_score
- 公式：`max(cosine(emb(self.description), emb(other.description)) for other in siblings)`
- 数据源：embedding；DevolaFlow `gate/cycle_detector.py` Jaccard 思路可借用 [^df-gate-models]
- 阈值：green < 0.55；yellow 0.55-0.75；red ≥ 0.75
- 佐证：AgentPatterns "Skill Library Evolution" 论"redundant entries → nondeterministic selection" [^agentpatterns-skilllib]
- 重叠依赖：与 D6 R8 description_competition_index 强相关

### D3 Latency & Path Efficiency 响应与路径效率

#### L1/L2 wall_clock_p50/p95
- 公式：分位
- 数据源：OTel `gen_ai.client.operation.duration` histogram [^otel-genai-metrics]
- 阈值：MVP green P95 ≤ 30s；yellow 30-90s；red > 90s（按场景调）
- 佐证：HELM v0.5.14 efficiency 维度 [^helm-readme]
- 重叠依赖：与 R6 routing_latency_p95 加和

#### L3 step_count
- 公式：tool_call 数
- 数据源：OTel span; AgentEval `code_tool_efficiency.actual_calls` [^agenteval-metrics]
- 阈值：相对每个 task 的 optimal_calls；标 absolute red > 30
- 佐证：DeepEval `Step Efficiency`；AgentProcessBench step annotations [^agent-process-bench]
- 重叠依赖：L4 / L5 的分母

#### L4 redundant_call_ratio
- 公式：`redundant_calls / total_calls`，redundant = 同 tool 同参数重复
- 数据源：trace 后处理
- 阈值：green ≤ 0.10；yellow 0.10-0.25；red > 0.25
- 佐证：AgentEval `code_tool_efficiency.redundant_calls` [^agenteval-metrics]；Quaxel "Tool Thrashing" 2026-03 [^tool-thrashing]
- 重叠依赖：会推高 L5

#### L5 detour_index
- 公式：`detour = actual_step_count / optimal_step_count`，optimal 由 expert/oracle 标注或 LLM-as-judge 给出
- 数据源：AgentEval `code_tool_efficiency.efficiency_ratio` 反向 [^agenteval-metrics]；Self-Healing Routing Dijkstra reference path [^self-healing-routing]
- 阈值：green ≤ 1.20；yellow 1.20-1.80；red > 1.80
- 佐证：直接对应用户 feedback "处理路径有没有绕弯路"；AgentProcessBench step-level annotations [^agent-process-bench]
- 重叠依赖：L4 是 L5 的局部成因之一

#### L6 replanning_rate
- 公式：agent 自发产生新 plan 的次数 / task
- 数据源：trace 中的 "I will instead..." marker，或 OTel span 上下文树
- 阈值：green ≤ 0.5/task；yellow 0.5-1.5；red > 1.5
- 佐证：AgentProcessBench "weaker policy models exhibit inflated ratios of correct steps due to early termination" [^agent-process-bench]
- 重叠依赖：与 T4 error_recovery_rate 强相关

#### L7 think_act_split
- 公式：`reasoning_tokens / action_tokens`
- 数据源：OTel `gen_ai.usage.input_tokens` 拆分（thinking vs tool）[^otel-genai-metrics]
- 阈值：green 0.5-2.0；其它视场景
- 佐证：Anthropic extended thinking 与 fast-mode beta（`fast-mode-2026-02-01` header）[^anth-api-betas]
- 重叠依赖：与 R7 routing_token_overhead 互斥

### D4 Generalizability 泛用性 / 跨模型跨域

#### G1 cross_model_pass_matrix
- 公式：每模型 × 每 task pass_rate；输出矩阵 + min/median 行
- 数据源：手工运行多模型；Anthropic API + OpenAI API + Cursor Composer
- 阈值：green min ≥ 0.70；yellow 0.50-0.70；red < 0.50
- 佐证：SkillsBench (arXiv:2602.12670) 16/84 任务负向 delta [^skillsbench]
- 重叠依赖：直接决定 R5 router_floor

#### G2 cross_domain_transfer_pass
- 公式：在 N 个相邻域上的 pass_rate 几何平均
- 数据源：SkillCraft compositional benchmark [^skillcraft]；自建 domain pack
- 阈值：green ≥ 0.65；yellow 0.45-0.65；red < 0.45
- 佐证：SkillsBench 域间方差大（+4.5pp ~ +51.9pp）[^skillsbench]
- 重叠依赖：与 G1 互补

#### G3 OOD_robustness
- 公式：format perturb / paraphrase / adversarial trigger 下 pass_rate
- 数据源：BFCL V4 `format_sensitivity`；K2VV `trigger_similarity` [^bfcl-v4]
- 阈值：green ≥ 0.80；yellow 0.65-0.80；red < 0.65
- 佐证：HuggingFace "OOD generalization is the most important open challenge" 2026 [^hf-ood]
- 重叠依赖：和 R4 near_miss_FP_rate 共享样本

#### G4 model_version_stability
- 公式：`stddev(pass_rate)` 跨同 family 多个版本（如 claude-haiku-4.5 / 4.6 / 5）
- 数据源：内部 ratchet history；DevolaFlow `gate/ratchet.py` 可借用 [^df-gate-models]
- 阈值：green stddev ≤ 0.05；yellow 0.05-0.10；red > 0.10
- 佐证：Trace2Skill (arXiv:2603.25158) "evolved skills transfer across LLM scales" 反方向证据 [^trace2skill]
- 重叠依赖：决定半退役周期长短

### D5 Learning & Usage Cost 使用与学习成本

#### U1 description_readability
- 公式：中文用 `字数 / 句数 + 复杂词比例`；英文用 Flesch Reading Ease
- 数据源：static
- 阈值：green Flesch ≥ 50；yellow 30-50；red < 30
- 佐证：Anthropic skill-creator §"description... primary triggering mechanism, include both what and when" L73 [^anth-skill-creator]
- 重叠依赖：直接影响 R3 trigger_F1

#### U2 first_time_success_rate
- 公式：`first_run_passes / total_first_runs`
- 数据源：dogfood log
- 阈值：green ≥ 0.70；yellow 0.50-0.70；red < 0.50
- 佐证：Fungies 2026 "with skills 47% → 83%" [^fungies-skill]
- 重叠依赖：低 U2 高概率指向 U1 / R1 不足

#### U3 setup_steps_count
- 公式：完成首次成功调用所需手工步骤
- 数据源：static + 手工标注
- 阈值：green ≤ 2；yellow 3-5；red > 5
- 佐证：Anthropic skill-creator §"compatibility frontmatter, rarely needed" L74
- 重叠依赖：与 V1/V2 凭据相关

#### U4 time_to_first_success
- 公式：从首次接触到首次成功的中位秒数
- 数据源：dogfood log
- 阈值：green ≤ 240s；yellow 240-720s；red > 720s
- 佐证：Fungies 2026 "12 min → 4 min" [^fungies-skill]
- 重叠依赖：U2 + U3 + U1 联合作用

### D6 Routing Cost 面向 agent 的路由成本

#### R1 trigger_precision / R2 trigger_recall / R3 trigger_F1
- 公式：标准
- 数据源：Anthropic skill-creator description optimizer 20-query 协议 [^anth-skill-creator] L343-L364；BFCL V4 `irrelevance` 子集 [^bfcl-v4]
- 阈值：green F1 ≥ 0.85；yellow 0.70-0.85；red < 0.70
- 佐证：见数据源
- 重叠依赖：与 C6 scope_overlap_score 直接相关

#### R4 near_miss_FP_rate
- 公式：在"近义但不该触发"集合上的 FP / total
- 数据源：自建 near-miss eval set；K2VV `trigger_similarity` 启发 [^k2vv]
- 阈值：green ≤ 0.10；yellow 0.10-0.25；red > 0.25
- 佐证：Anthropic skill-creator 指 "should-not-trigger 8-10 个 near-miss" L361 [^anth-skill-creator]
- 重叠依赖：与 R1 反方向取舍

#### R5 router_floor
- 公式：满足 (R3 ≥ X ∧ R6 ≤ Y ∧ R4 ≤ Z) 的 (model_id × thinking_depth) 中**最弱**组合
- 数据源：R8 router-test 协议
- 阈值：green floor ≤ Composer 2 / Sonnet shallow；yellow 需要 Sonnet deep；red 需要 Opus
- 佐证：LLMRouterBench (arXiv:2601.07206) [^llm-router-bench]；Cursor Composer 2 (2026-03-19) CursorBench 61.3 [^cursor-composer-2]；Claude Haiku 4.5 tau2-bench 92.5% [^haiku-45]
- 重叠依赖：是 D6 的合成指标，必须最后算

#### R6 routing_latency_p95 / R7 routing_token_overhead
- 公式：路由层独立测；overhead = `routing_tokens / total_tokens`
- 数据源：OTel；自建 router harness
- 阈值：green latency ≤ 800ms ∧ overhead ≤ 0.10；yellow 800-2000ms / 0.10-0.20；red > 2000ms / > 0.20
- 佐证：OpenAI Agents SDK 2026 production guide "router GPT-5-nano" [^openai-agents]
- 重叠依赖：直接决定 R5

#### R8 description_competition_index
- 公式：在 N 个候选 skill 同时存在时，正确选中目标 skill 的比例
- 数据源：自建 multi-skill harness
- 阈值：green ≥ 0.85；yellow 0.65-0.85；red < 0.65
- 佐证：AgentPatterns "softmax over near-equal scores" [^agentpatterns-skilllib]
- 重叠依赖：C6 scope_overlap_score 越高，R8 越低

### D7 Governance / Risk

#### V1 permission_scope
- 公式：count(allowed_tools) + sandbox_level（none/basic/strict）
- 数据源：SKILL.md frontmatter / plugin manifest
- 阈值：green ≤ 5 tools ∧ sandbox ≥ basic；yellow / red 视域
- 佐证：Claude Code plugin manifest [^cc-plugin-structure]
- 重叠依赖：影响 V2

#### V2 credential_surface
- 公式：count(tools requiring credentials)
- 数据源：static + plugin manifest
- 阈值：green = 0；yellow 1-2；red > 2
- 佐证：Agentic Academy lifecycle Decommission stage credential cleanup [^agentic-academy]
- 重叠依赖：与 V1 同源

#### V3 drift_signal
- 公式：依赖的 API/CLI schema 30 天内变更次数
- 数据源：DevolaFlow `entropy_manager.DeviationScanner` + `check_drift` [^df-entropy]
- 阈值：green = 0；yellow 1-2；red ≥ 3
- 佐证：MCP 2025-Apr "Tool Schema Drift / 静默失败" R4 §F5
- 重叠依赖：与 G4 互补

#### V4 staleness_days
- 公式：`max(today - last_used_at, today - last_modified_at)`
- 数据源：DevolaFlow `entropy_manager.DocFreshness` + `learnings.last_accessed` [^df-entropy] [^df-learnings]
- 阈值：green ≤ 30；yellow 30-90；red > 90 → 进入 Stage 0 评审
- 佐证：DevolaFlow `DEFAULT_STALENESS_THRESHOLD_DAYS = 30` [^df-entropy]
- 重叠依赖：与 T3 baseline_delta 同为 Stage 0 输入

---

## 3. 依赖 / 重叠图（adjacency list）

```yaml
# key: source ; value: 直接受影响的 sub-metrics
T1 -> [T2, T3]
T2 -> [G4]
T3 -> [Stage0_decision]
T4 -> [L6]
C1 -> [C4]
C2 -> [C4, C5]
C3 -> [C4]
C4 -> [C5, R6, R7]
C5 -> [Stage_gate, T1_degradation]
C6 -> [R1, R3, R8]
L1 -> [L2]
L3 -> [L4, L5]
L4 -> [L5]
L5 -> [Stage3_signal]
L6 -> [T4, L5]
L7 -> [R7]
G1 -> [R5]
G2 -> [G1]
G3 -> [R4]
G4 -> [Stage0_decision]
U1 -> [R1, R3]
U2 -> [Stage1_to_2]
U3 -> [U2, U4]
U4 -> [U2]
R1, R2 -> [R3]
R3 -> [R5]
R4 -> [R3, R8]
R5 -> [Stage4_decision]
R6 -> [R5]
R7 -> [R5]
R8 -> [Stage4_decision]
V1 -> [V2]
V2 -> [Stage5_gate]
V3 -> [G4, Stage0_decision]
V4 -> [Stage0_decision]
```

> 重叠区: (T1, T2, T3) 都消费 eval pass 信号；(C5, L1, T2) 都受 long-context 影响；(R3, R4, R8, C6) 共享 description / scope；(T3, V4, V3, G4) 共同决定半退役 / 退役。

---

## 4. 与 R3 的差异清单（≥ 11 个新增）

| ID | 子指标 | R3 状态 | R6 新增点 |
|---|---|---|---|
| C1 | metadata_tokens | 隐含 | 显式 token cap，对接 OTel `gen_ai.usage.input_tokens` |
| C2 | body_tokens | 隐含 | 同上，独立维度便于压缩追溯 |
| C3 | resolved_tokens | 无 | runtime 实际拉取量，对接 `gen_ai.tool.call.arguments` |
| C4 | per_invocation_footprint | 无 | Stage gate 一等公民 |
| C5 | context_rot_risk | 无 | 引入 32K-64K cliff sigmoid |
| L3 | step_count | 隐含 | 独立维度，对接 AgentEval |
| L4 | redundant_call_ratio | 无 | 路径绕弯主因之一 |
| L5 | detour_index | 无 | 路径绕弯核心指标，用户 feedback 直接对应 |
| L6 | replanning_rate | 无 | 由 AgentProcessBench 启发 |
| L7 | think_act_split | 无 | 与 routing token overhead 互斥 |
| G1 | cross_model_pass_matrix | 无 | 是 R5 router_floor 的输入 |
| G4 | model_version_stability | 无 | 半退役周期决策 |
| U1 | description_readability | 无 | trigger_F1 的上游 |
| U4 | time_to_first_success | 无 | 用户 feedback "学习成本" 对应 |
| R5 | router_floor | 无 | 不 train router 的核心结论指标 |
| R6 | routing_latency_p95 | 无 | 与 R5 联动 |
| R7 | routing_token_overhead | 无 | 与 R5 联动 |
| R8 | description_competition_index | 无 | 多 skill 共存的真实路由质量 |
| V3 | drift_signal | 无 | DevolaFlow entropy_manager 直接对接 |
| V4 | staleness_days | 无 | DevolaFlow `learnings.last_accessed` 直接对接 |

> 共 20 条新增；其余 8 条是对 R3 既有指标的重排 / 严格化。

---

## 5. 可对接的 DevolaFlow / NineS API（≥ 5 条）

| 上游 | 入口 | 对接子指标 | 路径:行 |
|---|---|---|---|
| DevolaFlow `gate/scorer.py` | `score_dimension(findings)` / `composite_score(dims, weights)` | T1/T2/T3 聚合 + Stage gate 判断 | `src/devolaflow/gate/scorer.py:117-178` [^df-gate-scorer] |
| DevolaFlow `gate/models.py` | `Severity` / `composite_threshold` / `coverage_threshold` / `max_blocker` | 阈值结构、`blocker / critical / major / minor / info` 分级直接复用 | `src/devolaflow/gate/models.py:12,105,158,175-187` [^df-gate-models] |
| DevolaFlow `legibility/scorer.py` | `LegibilityScorer.score(path)` → `LegibilityReport.dimensions{naming/comment/cyclomatic}` | U1 description_readability + 间接给 V3 drift 评分提供方法学 | `src/devolaflow/legibility/scorer.py:1-90` [^df-legibility] |
| DevolaFlow `entropy_manager.py` | `DocFreshness.scan()` / `DeviationScanner.scan()` / `cleanup(...)` | V3 drift_signal + V4 staleness_days；Stage 0 半退役评审 | `src/devolaflow/entropy_manager.py:1-90` [^df-entropy] |
| DevolaFlow `compression_pipeline.py` | `CompressionPipeline.run(payload, context)` + `CompressionStage` | C2 body_tokens 压缩前/后比较；C4 footprint baseline | `src/devolaflow/compression_pipeline.py:108-490` [^df-compression] |
| DevolaFlow `memory_router/router.py` | `MemoryRouter.lookup_case(...)` + `MemoryCase` + TTL/version 检查 | R5 router_floor 测试床（先用 deterministic router 拉 baseline）；C6 / R8 的 cache 端实测 | `src/devolaflow/memory_router/router.py:95-335` [^df-router] |
| DevolaFlow `learnings.py` | `decay_confidence(...)` / `consolidate_session(...)` / `pin_learning_for_session(...)` | V4 staleness_days；半退役状态跟踪；T3 退役决策日志 | `src/devolaflow/learnings.py:74,189,610,762,836` [^df-learnings] |
| DevolaFlow `nines/scorer.py` | `nines_dimension_scores(NinesScorerConfig, artifact_path)` | T1/T3/G3 接 NineS eval；与 gate 4 维 (test_quality / code_review / architecture / benchmark) 桥接 | `src/devolaflow/nines/scorer.py:34-141` [^df-nines-scorer] |
| DevolaFlow `nines/researcher.py` | `collect_research(...)` / `analyze_target(...)` | 自动 collect 同类 skill 描述做 C6 scope_overlap 输入 | `src/devolaflow/nines/researcher.py:1-90` [^df-nines-researcher] |
| DevolaFlow `pre_decision/{recommend,checklist,validate,freeze}` | `recommend_workflow(text)` / `auto_detect(repo_path)` / `validate_consistency(checklist)` / `freeze_config(...)` | Stage 1 → Stage 2 跃迁前自检 | `src/devolaflow/pre_decision/recommend.py:258-330` 等 [^df-pre-decision] |
| DevolaFlow `task_adaptive_selector.py` | `select_context(task_type, round_num)` / `apply_round_escalation` | R5/R6/R7 路由测试时的"多档思考深度"配置即用 | `src/devolaflow/task_adaptive_selector.py:844,1011,1066,1088` [^df-tas] |
| DevolaFlow `template_engine` | `parse_template` / `validate_template` / `select_stages_for_runtime` | Si-Chip 工厂模板的 IR 直接复用 | `src/devolaflow/template_engine/{parser,validator,runtime}.py` [^df-template] |
| NineS CLI | `nines self-eval --dimensions DIM,... --baseline VERSION --compare --report` | 一键比对当前版本 vs baseline；G4 model_version_stability 数据源 | `/root/.codex/skills/nines/commands/self-eval.md` [^nines-self-eval] |
| NineS CLI | `nines iterate --max-rounds N --convergence-threshold F --dry-run` | 阶段间收敛轮次的硬上限；R6/R7 measurement 自动化 | `/root/.codex/skills/nines/commands/iterate.md` [^nines-iterate] |
| NineS CLI | `nines collect --source --query --max-results` + `analyze --target-path --depth` | C6 描述池构造；R7 上游 reference 抓取 | `/root/.codex/skills/nines/commands/{collect,analyze}.md` [^nines-collect] [^nines-analyze] |
| OTel GenAI semconv | `gen_ai.client.operation.duration` / `gen_ai.client.token.usage` / `gen_ai.tool.name` / `mcp.method.name` | C1-C5 / L1-L7 / R6-R7 全链路数据源标准 | OpenTelemetry GenAI semconv [^otel-genai-metrics] [^otel-genai-attrs] |

---

## 6. MVP 子指标集（第一版必须支持的 8 条）

> 选择标准：(1) 直接可由 OTel + Skill Creator + DevolaFlow API 算出；(2) 覆盖用户 feedback 7 条要点中至少一项；(3) 无需自建数据集即可起步。

| MVP # | 子指标 | 优先级 | 直接支撑的 Stage gate | 立即可用的数据源 |
|---|---|---|---|---|
| 1 | T1 pass_rate | P0 | Stage 2 → 3 | Skill Creator `grading.json` |
| 2 | T2 pass_k (k=4) | P0 | Stage 2 → 3 | tau-bench harness 模式 |
| 3 | T3 baseline_delta | P0 | Stage 0 半退役决策 | Skill Creator with/without baseline |
| 4 | C1 metadata_tokens | P1 | Stage 1 → 2 | static analyse |
| 5 | C4 per_invocation_footprint | P1 | Stage 3 → 4 | OTel token usage |
| 6 | L1/L2 wall_clock_p95 | P1 | Stage 3 → 4 | OTel duration |
| 7 | R3 trigger_F1 | P0 | Stage 1 → 2 + Stage 4 | Skill Creator description optimizer |
| 8 | R5 router_floor | P2 | Stage 4 → 5 | R8 router-test 输出 |

> 8 条全部覆盖用户 feedback 中"性能/上下文/响应/路径/触发 F1/半退役/路由 floor"七大要点；其余 20 条留待 v0.0.3 延伸。

---

## 7. 关键发现 (Top-5)

1. **指标按"维度 × 子维度"重排后，R3 已有的 8 条只覆盖 D1/D6 的部分**。R6 在 D2/D3/D5/D7 上**至少要加 11 条新指标**才能满足用户 feedback 中"性能 / 上下文 / 路径绕弯 / 学习成本 / 路由成本"七维要求。
2. **detour_index (L5) 是用户 feedback 最直接的新指标**，AgentEval `code_tool_efficiency.efficiency_ratio` + AgentProcessBench step annotations + Self-Healing Routing Dijkstra 三者共同形成可工程化定义。
3. **router_floor (R5) 不是单一数字，而是 (model_id × thinking_depth) 二元组**。直接呼应用户 "测试 Sonnet/Composer/浅思考是否够用" 的诉求；对应 R8 路由测试协议是 R5 的唯一数据源。
4. **DevolaFlow 已经覆盖 ≥ 11 条本研究指标的上游 API**：gate scorer + scorer.composite + entropy_manager + learnings + memory_router + compression_pipeline + nines/scorer + nines/researcher + pre_decision + task_adaptive_selector + template_engine。Si-Chip 真正需要自研的薄层是 (a) Skill 级 schema、(b) 28 个子指标的字段桥接、(c) Stage classifier。R7 详述。
5. **OpenTelemetry GenAI semconv (development, 2026-04)** 是 D2/D3/D6 的事实数据源标准。Si-Chip 从第一行代码就应直接生成 OTel attribute，不要发明私有字段——会自动获得 LangSmith / Phoenix / Honeycomb 等观测面板支持。

---

## 8. 来源清单

### 8.1 2026 外部来源（按字母序）

[^agent-process-bench]: AgentProcessBench, **arXiv:2603.14465 v1**, 2026, `https://arxiv.org/html/2603.14465v1`. — 1,000 trajectories / 8,509 step annotations / ternary correctness label.
[^agentic-academy]: Agentic Academy, **Agent Lifecycle Management: From Development to Decommission**, 2026-02-17.
[^agenteval-metrics]: AgentEval, **Agentic Metrics Guide**, 2026-01, `https://agenteval.dev/agentic-metrics.html`. — code_tool_selection / arguments / success / efficiency + llm_task_completion.
[^agentpatterns-skilllib]: AgentPatterns.ai, **Skill Library Evolution: Lifecycle Governance for Agents**, fetched 2026-04-27.
[^anth-api-betas]: Anthropic API Reference (Skills + Versions), 2026-04, `console.anthropic.com/docs/en/api/beta/skills/versions` — `fast-mode-2026-02-01` beta header.
[^anth-skill-creator]: Anthropic `skills/skill-creator/SKILL.md`, fetched 2026-04-27, `https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md`.
[^bfcl-v4]: BFCL V4 / Gorilla CHANGELOG, 2026-04-12 leaderboard refresh, `format_sensitivity` + `irrelevance` + `agentic memory` 子集.
[^calmops]: Calmops, **AI Agent Skills Complete Guide 2026**, 2026.
[^cc-plugin-structure]: Claude Code plugin manifest reference, 2026.
[^context-cliff]: Tianpan, **The Context Window Cliff**, 2026-04-14 / 2026-04-19.
[^cursor-composer-2]: Cursor blog, **Introducing Composer 2**, 2026-03-19; CursorBench 61.3 / Terminal-Bench 2.0 61.7 / SWE-bench Multi 73.7.
[^fungies-skill]: Fungies.io, **AI Agent Skills 2026 Complete Guide**, 2026.
[^haiku-45]: Anthropic Claude Haiku 4.5 release notes, 2025-10 ; tau2-bench 92.5%; tool error 1.55%.
[^helm-readme]: Stanford HELM v0.5.14, 2026-04-03.
[^hf-ood]: Hugging Face blog, **Evaluating Agentic AI Part 6: Generalizability**, 2026.
[^k2vv]: K2-Vendor-Verifier, 2026 commits — `trigger_similarity` 子集.
[^llm-router-bench]: LLMRouterBench, **arXiv:2601.07206 v1**, ACL 2026 Findings — 400K instances, 21 datasets, 33 models, 10 routing baselines.
[^morph-rot]: Morph LLM, **Context Rot Complete Guide**, 2026.
[^openai-agents]: OpenAI Agents SDK production patterns 2026 (ToolHalla / APIScout).
[^otel-genai-attrs]: OpenTelemetry, **GenAI Attributes**, 2026-04 development status.
[^otel-genai-metrics]: OpenTelemetry, **GenAI Metrics semconv**, 2026-04.
[^self-healing-routing]: AgentPatterns.ai, **Self-Healing Tool Routing** (Dijkstra), 2026.
[^skillsbench]: SkillsBench, **arXiv:2602.12670 v3**, 2026 — 86 tasks × 11 domains × 7 agent configs × 7,308 trajectories.
[^skillcraft]: SkillCraft, **arXiv:2603.00718**, 2026.
[^tau-bench-readme]: tau-bench README + τ²/τ³-bench leaderboards, 2026-03.
[^tool-thrashing]: Quaxel, **Agent Routing Rules That Stop Tool Thrashing**, Medium, 2026-03.
[^trace2skill]: Trace2Skill, **arXiv:2603.25158 v3**, 2026.

### 8.2 本地 reference（按 path:行号）

[^df-compression]: `/home/agent/workspace/DevolaFlow/src/devolaflow/compression_pipeline.py:108-490` — CompressionStageProtocol / CompressionPipeline.run.
[^df-entropy]: `/home/agent/workspace/DevolaFlow/src/devolaflow/entropy_manager.py:1-90` — DocFreshness / DeviationScanner / cleanup / DEFAULT_STALENESS_THRESHOLD_DAYS=30.
[^df-gate-models]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/models.py:12,87,105,158,175-187,425` — Severity / DimensionScore / ProfileConfig / CYCLE_DEFAULT_SEVERITY.
[^df-gate-scorer]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/scorer.py:110-180` — DEFAULT_DIMENSION_WEIGHTS / score_dimension / composite_score.
[^df-learnings]: `/home/agent/workspace/DevolaFlow/src/devolaflow/learnings.py:74,189,473,574,610,643,762,836` — capture_learning / load_relevant_learnings / consolidate_session / decay_confidence / pin_learning_for_session.
[^df-legibility]: `/home/agent/workspace/DevolaFlow/src/devolaflow/legibility/scorer.py:1-90` — LegibilityScorer / DEFAULT_DIMENSION_WEIGHTS naming/comment/cyclomatic.
[^df-nines-researcher]: `/home/agent/workspace/DevolaFlow/src/devolaflow/nines/researcher.py:1-90` — collect_research / analyze_target.
[^df-nines-scorer]: `/home/agent/workspace/DevolaFlow/src/devolaflow/nines/scorer.py:34-141` — run_nines_eval / run_nines_analyze / nines_dimension_scores / DIMENSION_KEYS.
[^df-pre-decision]: `/home/agent/workspace/DevolaFlow/src/devolaflow/pre_decision/{recommend,checklist,validate,freeze}.py` — recommend_workflow / auto_detect / validate_consistency / freeze_config.
[^df-router]: `/home/agent/workspace/DevolaFlow/src/devolaflow/memory_router/router.py:95-335` + `cache.py:81-260` — MemoryRouter.lookup_case + MemoryCase / is_ttl_expired / is_version_stale.
[^df-tas]: `/home/agent/workspace/DevolaFlow/src/devolaflow/task_adaptive_selector.py:844,1011,1066,1088` — select_context / select_round_result / escalate_round / apply_round_escalation.
[^df-template]: `/home/agent/workspace/DevolaFlow/src/devolaflow/template_engine/{parser,validator,runtime,composer,registry}.py` — parse_template / validate_template / select_stages_for_runtime / collect_stage_refs.
[^nines-analyze]: `/root/.codex/skills/nines/commands/analyze.md`.
[^nines-collect]: `/root/.codex/skills/nines/commands/collect.md`.
[^nines-eval]: `/root/.codex/skills/nines/commands/eval.md` — `nines eval <task-or-suite> [--scorer TYPE] [--format FORMAT] [--sandbox] [--seed N]`.
[^nines-iterate]: `/root/.codex/skills/nines/commands/iterate.md` — `nines iterate [--max-rounds N] [--convergence-threshold F] [--dry-run]`.
[^nines-self-eval]: `/root/.codex/skills/nines/commands/self-eval.md` — `nines self-eval [--dimensions DIM,...] [--baseline VERSION] [--compare] [--report]`.
