---
task_id: R2
scope: Skill 生命周期 / 成熟度模型文献综述
sources_count: 18
frameworks_compared: 7
blind_spots_count: 9
hypothesis_assessment: "partially_supported_non_linear"
last_updated: 2026-04-27
---

# R2 · Skill 生命周期 / 成熟度模型文献综述

> Wave 1 · Task R2 (research-only)。中文为主，专有名词保留英文。
> 时间窗：以 2026-01-01 起的论文、官方文档、工程报告作为主要论据；2024-2025 只作背景类比。

---

## 0. TL;DR（给决策者的 6 条）

1. **用户的 3 阶段假设方向是对的，但它不是完整生命周期，而只是其中一条"prompt-first skill"成长路径。** 2026 的证据显示，真实系统至少有 3 条并行分支：`Markdown-first`、`code-first`、`registry/toolkit-first`。R1 已证明 LangGraph / ADK / Pydantic-AI / CrewAI 这类 code-first 框架不会先进入 Markdown 阶段；R4 也证明 CLI-first / RTK / Composio 这类路径可直接从可执行层起步。
2. **2026 文献更接近"非线性成熟度模型"，不是单向升级链。** Agentic Academy 的 agent lifecycle 明确包含 Design / Development / Testing / Deployment / Monitoring / Updating / Decommission 七段；Skill Library Evolution 把 skill 从 ad-hoc code 走到 agent capability，但同时强调 pruning / deprecation；Anthropic Skill Creator 把 eval / A-B / description optimizer 放进迭代闭环。也就是说，Skill 可能升级、拆分、冻结、回滚、退役，而不是永远向 CLI 前进。
3. **最大的补充阶段是 Stage 0：退役 / 回收候选。** R3 已指出：当 base model 不加载 Skill 也能通过 eval，该 Skill 应回收，而不是被"升级"。Agentic Academy 的 Decommission 阶段也要求停止路由、撤销凭据、处理日志留存、通知依赖系统。Si-Chip 的判定器必须允许 `active -> deprecated -> retired` 的非单调转移。
4. **2026 的关键转折不是"Markdown 变成 CLI"，而是"Skill 变成可治理资产"。** Skilldex (arXiv:2604.16911, 2026-04-18) 把 skill package 做成包管理器 + registry + conformance scoring + skillset；Anthropic Skills API 支持 version create/list/retrieve/delete；Skill Creator 的 workspace 记录 `evals.json`、`grading.json`、`benchmark.json`、trigger eval、iteration history。治理资产的必要字段包括 owner、version、scope、eval set、trigger policy、observability、deprecation policy。
5. **"轻量模型 + CLI 路由"更适合作为 Stage 4/5 的运行形态，而不是 Stage 3 的必然终局。** R4 的结论更稳健：单层小模型直接驱动复杂 agent 失败案例明确存在；可行路径是分层路由 + CLI 渐进披露 + schema/version governance + retrieval + fallback。
6. **Si-Chip 应输出两个东西：一个阶段判定器 + 一个分支化路线图。** 阶段判定器给出 `stage`、`dominant_shape`、`graduation_gate`、`risk_flags`；路线图允许 Markdown-first、code-first、registry-first 多路径收敛，而不是把所有 Skill 塞进同一个三段流水线。

---

## 1. 2026 来源与各自的生命周期模型

| 来源 | 日期 | 主要模型 | 对 Si-Chip 的启示 |
|---|---:|---|---|
| Agentic Academy · Agent Lifecycle Management | 2026-02-17 | Design → Development → Testing → Deployment → Monitoring → Updating → Decommission | 生命周期必须包含监控、更新、退役；不是"写好 skill 就结束" |
| Anthropic `skill-creator` | 2026 当前 | Capture intent → write SKILL.md → create evals → run with/without skill → grade → benchmark → rewrite → expand test set → optimize trigger description | Skill 成熟的核心是 eval loop，不是文件格式本身 |
| Anthropic Skills API Versions | 2026 当前文档 | create/list/retrieve/delete skill versions，版本从 SKILL.md 提取 name/description/directory | Skill 已进入 API 级版本管理，不再只是本地 Markdown |
| Skilldex | 2026-04-18, arXiv:2604.16911 | skill package manager + conformance scoring + skillset + hierarchical scope registry | skill 的下一层可能是 registry / package，不一定是 CLI |
| SkillX | 2026-04-06 / 2026-04-19, arXiv:2604.04804 | Multi-Level Skills Design → Iterative Skills Refinement → Exploratory Skills Expansion | 自动化 skill library 可从轨迹蒸馏出战略 / 功能 / 原子三层，不依赖人工 Markdown 阶段 |
| Skill Library Evolution | 2026 语境 | Ad-hoc code → Saved solution → Reusable function → Documented skill → Agent capability；另含 pruning / deprecation | 支持用户"探索到收敛"方向，但明确补充质量闸门与回收 |
| Claude Context Engineering Guide | 2026-04-02 | prompt engineering → context engineering；system / history / tools / RAG 多层 context | Skill 成熟还包含 context budget、tool description、retrieval 策略 |
| LangGraph production pattern | 2026 Q1 语境 | graph nodes / edges / state / checkpoint / human approval / streaming / observability | code-first agent 框架绕过 Markdown 阶段，直接从 runtime primitives 成熟 |
| ACE / Agentic Context Engine | 2026 本地参考 | Skillbook 从执行反馈中自我演化；成功提取模式，失败提取反模式 | 提供"自演化 skill memory"分支，可能替代人工阶段迁移 |
| ContextOS | 2026 本地参考 | Context-as-OS：retrieval router、index lifecycle、schema quarantine、cognition layer | 成熟阶段必须治理 context 与索引生命周期 |

---

## 2. 阶段对比表：用户 3 阶段 vs 外部模型

| 模型 | 阶段划分 | 与用户假设的对应 | 缺口 / 反例 |
|---|---|---|---|
| 用户假设 | 1 Markdown 探索 → 2 Markdown 收敛 → 3 CLI 包装 → Skill-as-Agent | 适合手工 prompt-first skill | 缺退役、版本、观测、A/B、registry、code-first 分支 |
| Agentic Academy 生命周期 | Design → Dev → Testing → Deploy → Monitoring → Updating → Decommission | 用户阶段 1-3 只覆盖 Dev 的一部分 | 生产阶段 4-7 完全缺失 |
| Anthropic Skill Creator | intent → SKILL.md → eval prompts → with/baseline runs → grading → benchmark → rewrite → scale → trigger optimizer | 强支持"Markdown 收敛" | 其终点不是 CLI，而是 measurable skill + trigger accuracy |
| Skill Library Evolution | Ad-hoc code → Saved solution → Reusable function → Documented skill → Agent capability | 支持"探索 → 可复用 → 文档化" | 起点是 code，不是 Markdown；终点是 tested capability，不一定 CLI |
| SkillX | raw trajectories → strategic plans / functional skills / atomic skills → iterative refinement → exploratory expansion | 支持"从经验中沉淀 skill" | 自动从轨迹生成多层 skill，不需要人工 Markdown 先行 |
| Skilldex | single skill package → skillset → hierarchical scope registry → MCP server | 支持"模板化 / 包化" | 下一阶段是 package/registry，不是 CLI wrapper |
| LangGraph / production graph | state → node → edge → checkpoint → HITL → tracing → deployment | 与用户路径弱相关 | code-first，直接 runtime 级成熟；Markdown 不是必经 |
| ContextOS / ACE | retrieval lifecycle / skillbook feedback → self-improving context layer | 对应 Skill-as-Agent 的上层治理 | 指向 context/learning OS，而不是单一 CLI |

---

## 3. 支持用户假设的证据

### 3.1 从探索到收敛：Anthropic Skill Creator 已经把它工程化

Anthropic `skill-creator` 的流程明确从意图访谈、写 `SKILL.md`、创建 eval prompts、运行 with-skill baseline、量化 benchmark、再重写 skill 开始，并要求"Repeat until you're satisfied"。它还把 trigger description optimization 单独作为后置步骤，生成 should-trigger / should-not-trigger 查询，迭代最多 5 次，按 held-out test score 选最佳描述。这强力支持用户的第二阶段：一旦有验收标准，Markdown Skill 就有明确的收敛方向。

关键证据：

- `skill-creator` 说明其用途是 create / modify / improve skills、run evals、benchmark performance、optimize description triggering。
- 它要求 `benchmark.json` / `benchmark.md` 输出 pass_rate、time、tokens，并做 mean ± stddev 与 delta。
- 它把 description 视为 primary triggering mechanism，并专门做 20 个正负例 trigger eval。

### 3.2 从反复 prompt 到可执行资源：scripts/ 是事实上的确定性出口

Anthropic Skill anatomy 把 `scripts/` 定义为可选 bundled resource：可执行代码用于 deterministic / repetitive tasks。R1 已证明 Claude Code / Cursor / Devin / OpenSpec 都采纳了 `SKILL.md + scripts/references/assets` 的形态。用户认为"固定化工作不应再让模型生成代码，而应转成 CLI"是正确方向，但更准确说法是：**确定性子任务应下沉到 executable resource**，这个 resource 可以是 script、CLI、MCP tool、hosted API 或 registry toolkit。

### 3.3 从单个 skill 到体系：Skilldex / Skill Library Evolution 支持"模板 + 包管理"

Skilldex (arXiv:2604.16911) 明确指出 2026 的缺口是：缺少 public tool 对 Anthropic skill spec 做 conformance scoring，缺少把相关 skills 与共享 context 绑定的机制。它提出 `skillset`、三层 hierarchical scope、metadata-only community registry、MCP server。这与 Si-Chip 目标高度一致：仓库不应只做单个 Skill，而应做**阶段模板 + 判定器 + 迭代工具**。

---

## 4. 反证 / 不支持用户假设的证据

### 4.1 Code-first 框架永不进入 Markdown 阶段

R1 的工具范式调研已经给出最大反证：LangGraph、ADK、Pydantic-AI、CrewAI Flows、OpenAI Agents SDK 这类框架直接以 code / graph / typed tool / state checkpoint 为核心。LangGraph 的生产设计强调 parallelization、streaming、task queue、checkpointing、human-in-the-loop、tracing；这些是 runtime primitives，不是 Markdown 的自然演化结果。

结论：Si-Chip 如果只定义 Markdown-first 成熟度，会错判一整类 code-first Skill / Agent。

### 4.2 Registry-first 可能替代 CLI-first

Skilldex 的下一阶段是 package manager / registry / skillset / MCP server；Composio 这类生态把 capability 放入 hosted toolkit registry；GitHub Copilot Extensions / MCP 也把工具化边界放在 registry。它们并不要求每个 Skill 变成本地 CLI。

结论：用户的 Stage 3 "CLI 包装"应扩展为 **Productized Execution Surface**，可取 CLI / MCP / hosted tool / package / SDK 多种形态。

### 4.3 Markdown 可能是终态，不是过渡态

Anthropic Skills 的 official pattern 并不把 `SKILL.md` 视为临时脚手架。其 progressive disclosure 本身就是 production mechanism：metadata 总在 context，body 触发后加载，references/scripts 按需读取或执行。对偏知识型、风格型、流程型 Skill，Markdown + references 可能就是最低成本终态。

结论：不能把"没有 CLI"判为不成熟；要看它是否通过 eval、触发准确、token budget 和用户价值门槛。

### 4.4 Skill 可能应该退役，而不是升级

R3 已指出，Anthropic 区分 capability uplift 与 encoded preference：如果 base model 不加载 Skill 也能 pass，Skill 应进入 retirement/deprecation，而不是继续升级。Agentic Academy 的 Decommission 阶段也说明 agent/skill 退役需要停止新请求路由、允许 in-flight 完成、撤销凭据、处理日志保留、通知依赖系统。

结论：Si-Chip 的状态机必须允许 `Stage 2 -> Stage 0 retired`，不能单调向上。

---

## 5. 用户假设的盲点（至少 9 个）

| 盲点 | 为什么重要 | 推荐纳入 Si-Chip 的字段 / 指标 |
|---|---|---|
| Evaluation gate | 没有 eval，"收敛"只是感觉 | `eval_set_path`、`pass_rate`、`pass^k`、baseline delta |
| Trigger accuracy | Skill 是否被正确调用是第一生产风险 | `trigger_precision`、`trigger_recall`、near-miss false positive |
| Telemetry / observability | 上线后才知道真实调用分布与失败模式 | `invocation_count`、tool-call trace、latency、cost、error taxonomy |
| Versioning | Skill 是可变资产，必须比较版本 | semver / epoch version、changelog、rollback target |
| Deprecation / retirement | 不该保留过期 Skill | `last_used_at`、`superseded_by`、`retirement_reason` |
| Composability | 多 Skill 组合会冲突或重复触发 | `scope_overlap_score`、dependency graph、shared context |
| Isolation / permissions | Skill 可能含脚本、凭据、MCP 访问 | `allowed_tools`、sandbox policy、credential scope |
| Context budget | Markdown / tools / schemas 会挤爆上下文 | `metadata_tokens`、`body_tokens`、`schema_tokens`、RAG policy |
| A/B / shadow testing | 版本替换不能靠单次 demo | baseline-vs-candidate、shadow traffic、canary gate |

---

## 6. 精炼后的成长路径建议

我建议 Si-Chip 把用户 3 阶段改成 **"分支化 6 态状态机"**，其中 `dominant_shape` 与 `stage` 分开记录：

### Stage 0 · Retired / Deprecated（退役或不值得固化）

- **进入条件**：base model 不加载 Skill 也能达到同等 pass rate；90 天无调用；被更大范围 Skill 覆盖；API / tool 已失效。
- **输出**：deprecation notice、migration target、credential cleanup、archive report。
- **允许转移**：可被重新激活到 Stage 1，但必须重新跑 eval。

### Stage 1 · Exploratory Capture（探索捕获）

- **形态**：conversation transcript、rough Markdown、prompt snippet、manual workflow。
- **进入条件**：重复出现的需求，但输入输出 / 验收仍不稳定。
- **出阶段 gate**：至少 3 个代表性案例、初步 trigger 描述、失败模式清单、用户确认价值。
- **风险**：过早模板化会冻结错误抽象。

### Stage 2 · Evaluated Skill（可评估 Skill）

- **形态**：`SKILL.md` + frontmatter + examples + evals。
- **进入条件**：有明确 expected output / acceptance criteria。
- **出阶段 gate**：`pass_rate >= 80%`、trigger F1 达标、与 baseline 有正收益、token/time 不劣化。
- **典型工具**：Anthropic Skill Creator、OpenSpec propose/apply/verify、Si-Chip 自研 evaluator。

### Stage 3 · Productized Execution Surface（产品化执行表面）

- **形态**：scripts/、CLI、MCP server、hosted API、Composio toolkit、typed SDK。
- **进入条件**：流程稳定、重复执行、可参数化；模型生成部分可替换为确定性代码。
- **出阶段 gate**：schema 稳定、版本化、错误可观测、CI / regression test 通过。
- **说明**：这替代用户原本的 "CLI 包装"，因为 CLI 只是多个执行表面之一。

### Stage 4 · Routed Capability（被路由能力）

- **形态**：Skill registry / package manager / routing metadata / retrieval index。
- **进入条件**：Skill 数量增长到需要自动选择，或多个工具有 scope overlap。
- **出阶段 gate**：routing precision/recall、near-miss false positive、context budget、fallback policy。
- **风险**：R4 证明单层小模型直接路由仍不可靠，需 kNN / retrieval / heuristic / model cascade 组合。

### Stage 5 · Governed Skill System（治理化 Skill 系统）

- **形态**：skillset / registry / telemetry / A-B / canary / deprecation / audit。
- **进入条件**：多个团队、多个 agent、共享 Skill 库、生产流量。
- **出阶段 gate**：owner、version、scope、eval history、usage telemetry、deprecation policy 均完整。
- **类比**：MLOps / DevOps maturity，不是单个 Skill 的技术成熟，而是组织运行成熟。

### `dominant_shape` 维度（与 stage 独立）

| shape | 说明 |
|---|---|
| markdown_first | Anthropic / Cursor / Devin / OpenSpec 风格 |
| code_first | LangGraph / ADK / Pydantic-AI / CrewAI 风格 |
| cli_first | RTK / claude-code-router / unix-style progressive disclosure |
| registry_first | Skilldex / Composio / MCP registry |
| memory_first | ACE Skillbook / ContextOS cognition layer |

这样，Si-Chip 可以表达：

- `stage=2, shape=markdown_first`：一个评估过的 `SKILL.md`。
- `stage=3, shape=cli_first`：一个稳定 CLI 能力。
- `stage=4, shape=registry_first`：一个被检索 / 路由的 skill package。
- `stage=0, shape=markdown_first`：一个因模型能力提升而退役的旧 skill。

---

## 7. 选型建议：Si-Chip 第一版应该做什么

1. **先做阶段判定器，不先做 CLI 生成器。** 证据显示 CLI 只是一个分支，过早押注会把 Markdown-final、code-first、registry-first 都错判。
2. **把 Anthropic Skill Creator 的 eval loop 作为 Stage 2 标准模板。** 它已经定义了 intent capture、evals、benchmark、description optimizer，是最接近 Si-Chip 目标的现成流程。
3. **把 Skilldex 的 conformance scoring / skillset 概念作为 Stage 4 参考。** Si-Chip 可以先实现 spec scoring 与 shape classification，再考虑 package manager。
4. **把 Agentic Academy 的 lifecycle 作为 Stage 5 参考。** 上线前必须有 monitoring / updating / decommission 字段，否则不是成熟系统。
5. **把 R4 的 RTK / claude-code-router 作为 Stage 3/4 的执行底座。** 但只有当指标显示 deterministic execution 有收益时才迁移，不做默认终点。
6. **保留退役机制。** 每次模型升级后重跑 no-skill baseline，发现 base model 能独立通过时，Skill 进入 deprecation review。

---

## 8. 对用户原始假设的判定

| 假设片段 | 判定 | 修正建议 |
|---|---|---|
| "最开始是复杂 Markdown / 引导式操作" | 部分支持 | 适用于 markdown-first；code-first / CLI-first 不适用 |
| "有验收标准后 Markdown 有收敛方向" | 强支持 | 需要明确 eval loop、trigger eval、baseline delta |
| "固定流程应转成 CLI" | 部分支持 | 改成 productized execution surface：CLI / script / MCP / API / SDK |
| "Skill 最终是轻量模型路由 CLI" | 条件成立 | 必须分层：retrieval / heuristic / kNN / small model / fallback；不能单层小模型硬路由 |
| "这是一整套体系和迭代工具" | 强支持 | 第一版应做 classifier + template + eval gate，而非单个 skill |

**总判定：** 用户方向值得推进，但必须从"三阶段单向升级链"改为"分支化、可退役、可治理的生命周期状态机"。

---

## 9. 来源清单

### 9.1 2026 外部来源

1. Agentic Academy, **Agent Lifecycle Management: From Development to Decommission**, 2026-02-17, `https://agentic-academy.ai/posts/agent-lifecycle-management/`.
2. Sampriti Saha, Pranav Hemanth, **Skilldex: A Package Manager and Registry for Agent Skill Packages with Hierarchical Scope-Based Distribution**, arXiv:2604.16911, submitted 2026-04-18.
3. Shumin Deng et al., **SkillX: Automatically Constructing Skill Knowledge Bases for Agents**, arXiv:2604.04804, submitted 2026-04-06, revised 2026-04-19.
4. Anthropic Skills API Reference, **Versions**, current 2026 docs, `https://console.anthropic.com/docs/en/api/beta/skills/versions`.
5. Anthropic `skills/skill-creator/SKILL.md`, fetched 2026-04-27, `https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md`.
6. AgentPatterns.ai, **Skill Library Evolution: Lifecycle Governance for Agents**, fetched 2026-04-27, `https://agentpatterns.ai/tool-engineering/skill-library-evolution/`.
7. Claude Lab, **The Complete Guide to Claude Context Engineering 2026**, 2026-04-02, `http://claudelab.net/en/articles/claude-ai/claude-context-engineering-production-guide-2026`.
8. Jahanzaib AI, **LangGraph Tutorial: Build Production AI Agents (2026)**, fetched 2026-04-27, `https://www.jahanzaib.ai/blog/langgraph-tutorial-build-production-ai-agents`.

### 9.2 本地参考

1. `/home/agent/reference/openspec/README.md:26-39,49-68` — OpenSpec propose/apply/archive 的 spec-driven lifecycle。
2. `/home/agent/reference/dspy/README.md:16-18,49-51` — "Programming, not prompting" 与 prompt/program 编译思想。
3. `/home/agent/reference/ContextOS/README.md:18-24,28-75` — Context-as-OS、retrieval router、index lifecycle manager。
4. `/home/agent/reference/agentic-context-engine/README.md:17-26,92-112` — Skillbook、execution feedback、自改进指标。
5. `/home/agent/reference/superpowers/README.md:1-15,27-63` — composable skills + marketplace / Cursor / Claude / Codex 跨工具分发。
6. `/home/agent/reference/research_notes/analysis_patterns.md:15-33` — ContextBench 式 process metrics / context precision-recall 对 Si-Chip 的评估启发。
7. `/home/agent/workspace/Si-Chip/.local/research/r1_tool_paradigms.md` — R1 工具范式调研（36 sources）。
8. `/home/agent/workspace/Si-Chip/.local/research/r3_evaluation.md` — R3 评估调研（33 sources）。
9. `/home/agent/workspace/Si-Chip/.local/research/r4_endgame_routing.md` — R4 轻量路由与 CLI 终局调研（24 sources）。

---

## 10. Machine-readable summary

```yaml
task_id: R2
state: completed
sources_count: 18
frameworks_compared: 7
blind_spots_count: 9
hypothesis_assessment: partially_supported_non_linear
recommended_model:
  stages:
    - retired_or_deprecated
    - exploratory_capture
    - evaluated_skill
    - productized_execution_surface
    - routed_capability
    - governed_skill_system
  shapes:
    - markdown_first
    - code_first
    - cli_first
    - registry_first
    - memory_first
key_decision:
  replace_user_three_stage_chain_with: "branching lifecycle state machine"
```
