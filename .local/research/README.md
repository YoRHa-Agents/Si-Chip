# Si-Chip Research Index

> Last updated: 2026-05-05  
> 本目录保存 Si-Chip 关于 Skill/basic ability 迭代优化体系的调研、证据库与 canonical 文档。

## Canonical Reading Path

优先级：**Spec / Rules 高于 Canonical 高于 Evidence**。

1. `spec_v0.1.0.md` — **Frozen 规范**，Normative 条款定义 Si-Chip 的所有强约束。
2. `../../.rules/si-chip-spec.mdc` + `../../AGENTS.md` — 由 spec 编译的规则层，所有 Agent 会读到的强约束入口。
3. `si_chip_research_report_zh.md` — 主报告，解释 spec 的由来和上下文。
4. `decision_checklist_zh.md` — 操作手册，逐个 BasicAbility 做评估与决策。
5. `README.md` — 文档地图、版本历史、维护规则。

当 canonical 文档与 spec 冲突时，以 spec 为准。

## Evidence Library

R1-R10 是证据库，保留详细调研和来源，不作为主线文档。

| 文件 | 主题 | 被 spec / canonical 吸收的位置 |
|---|---|---|
| `r1_tool_paradigms.md` | 工具范式、Claude/Cursor/Codex/Copilot、code-first 反例 | spec §2/§7；主报告 §2/§7 |
| `r2_lifecycle_literature.md` | 生命周期、阶段模型、退役与治理 | spec §2/§6；主报告 §3 |
| `r3_evaluation.md` | benchmark、Skill-level metric | spec §3/§4；主报告 §4 |
| `r4_endgame_routing.md` | 轻量路由、CLI-first、失败模式 | spec §5；主报告 §5 |
| `r6_metric_taxonomy.md` | 7 维 / 28 子指标 taxonomy | spec §3；主报告 §4；清单 §4 |
| `r7_devolaflow_nines_integration.md` | DevolaFlow + NineS 可复用能力 | spec §10；主报告 §7 |
| `r8_router_test_protocol.md` | Router-test 协议、router_floor | spec §5；主报告 §5；清单 §6 |
| `r9_half_retirement_framework.md` | 半退役 / value vector / 简化策略 | spec §6；主报告 §6；清单 §7 |
| `r10_self_registering_skill_roadmap.md` | 自注册 Skill/Plugin 与 self-dogfood 行动路线 | spec §7/§8；主报告 §9；清单 §8.1 |
| `r11_core_goal_invariant.md` | Core-Goal Invariant + round_kind enum + multi-ability layout | spec v0.3.0 §14/§15/§16；主报告 §3 |
| `r12_v0_4_0_industry_practice.md` | v0.4.0 industry practice survey + chip-usage-helper R1-R47 实证 | spec v0.4.0 §18/§19/§20/§21/§22/§23 |
| `r12.5_real_llm_runner_feasibility.md` | Real-LLM runner feasibility spike (Veil proxy + Anthropic Messages) | spec v0.4.0 §3 D1 + §22.6 cache + r12.5 PROCEED_MAJOR |
| `r13_agent_skills_comparison.md` (NEW v0.4.7) | **FIRST registered long-term external research reference**: addyosmani/agent-skills v1.0.0 comparative study + anti-pattern doc + provenance pin | spec v0.4.7-rc1 §24.6 (canonical exemplar) |

> 注：没有 `r5`。R5 是前一轮 synthesis 任务，产物已经被 canonical 文档取代。

## Current Unified Model（Spec v0.1.0 冻结）

```text
Basic Ability
  -> Profile
  -> Evaluate
  -> Diagnose (7 dimensions / 28 sub-metrics, full scope)
  -> Improve
  -> Router-Test (paradigm research, no training)
  -> Half-Retirement Review (value-vector driven)
  -> Iterate (Progressive v1 -> v2 -> v3)
  -> Package/Register (Cursor -> Claude Code -> Codex)
```

核心约束（由 `spec_v0.1.0.md` 与 `.rules/si-chip-spec.mdc` 强制）：

- Marketplace **永远不做**。
- Router 模型训练 **永远不做**；Router 工作只研究范式。
- 不做 Markdown-to-CLI 自动转换器，不做通用 IDE 兼容层。
- `half_retire` 必须基于 R9 value vector 数字。
- 平台优先级：**Cursor → Claude Code → Codex（后续）**。
- 指标阈值按 `v1_baseline → v2_tightened → v3_strict` 分档递进，连续 2 轮通过才升档。
- Si-Chip 自身必须先成为可安装 Skill 并在本仓库 dogfood。

## Canonical Concepts

| 概念 | 定义 |
|---|---|
| Basic Ability | Si-Chip 的第一类对象；可评估、可优化、可路由、可简化或退役的能力单元 |
| Surface | 当前承载形态：markdown / script / cli / mcp / sdk / memory / mixed |
| Shape Hint | 形态提示；仅记录，不作为分流主线 |
| Metric Taxonomy | 7 维 / 28 子指标，v0.1.0 起 **全量实现** |
| Progressive Gate | v1_baseline → v2_tightened → v3_strict，连续 2 轮通过才升档 |
| Router Floor | 满足 gate 阈值的最弱模型 × 最浅 thinking depth |
| Router Paradigm Research | 研究让模型完成 routing 的更有效范式；严禁训练 router 模型 |
| Half-Retirement | 功能收益近零但性能 / 上下文 / 路径价值仍在，基于 value vector 数字触发 |
| Factory Template | capture → profile → evaluate → diagnose → improve → router-test → half-retire review → iterate → package/register |
| Self-Registering Skill | Si-Chip 自身作为可安装 Skill/Plugin；优先级 Cursor → Claude Code → Codex |
| Self-Dogfood | 用 Si-Chip 评估、优化、router-test 和 half-retire review Si-Chip 自身，多轮迭代 |
| Rules Layer | `.rules/si-chip-spec.mdc`；由 spec 编译为 `AGENTS.md` 的强约束入口 |

## Maintenance Rules

1. `spec_v0.1.0.md` 是 **frozen**。修改它必须提升 spec 版本号并重新编译 `AGENTS.md`。
2. `.rules/si-chip-spec.mdc` 只能由 spec 派生；spec 变更后必须重新 compile。
3. `si_chip_research_report_zh.md` 与 `decision_checklist_zh.md` 是 canonical；当它们与 spec 冲突时，以 spec 为准。
4. R1-R10 作为证据库，原则上只追加新研究或更正来源。
5. 新反馈进入 `.local/feedbacks/feedbacks_for_research/`，处理后更新 `.local/feedbacks/TRACKER.md`。
6. 新增研究方向按 `r11_<topic>.md` 继续编号，并在本 README 的 Evidence Library 里登记。
7. 每次修改 canonical 文档，必须更新 `last_updated` 与版本号。
8. 规范在生效后必须作为仓库 Rules 存在（已通过 `.rules/si-chip-spec.mdc` → `AGENTS.md` 实现）。

## Version History

| Version | Date | Change |
|---|---|---|
| v0.0.1 | 2026-04-27 | 初始研究：R1-R4，形成三阶段假设修正 |
| v0.0.2 | 2026-04-28 | 吸收用户反馈：R6-R9，增加指标 taxonomy、DevolaFlow/NineS、router-test、half-retirement |
| v0.0.3 | 2026-04-28 | 文档统一：重写主报告与清单，新增 research index，确立 canonical / evidence 分层 |
| v0.0.4 | 2026-04-28 | 吸收 feedback v0.0.3：新增 R10，自注册 Skill/Plugin 路线，明确 Claude Code / Cursor / Codex 与 self-dogfood 成功标准 |
| v0.0.5 / spec v0.1.0 | 2026-04-28 | 吸收 feedback v0.0.5：冻结 `spec_v0.1.0.md` 与 `.rules/si-chip-spec.mdc`，翻转优先级为 Cursor → Claude Code → Codex，全量 7 维 28 子指标，阈值 v1/v2/v3 递进，router 严禁训练，half_retire 必须基于评测指标，marketplace 永远不做 |
| spec v0.2.0 | 2026-04-29 | 吸收 R5 reconciliation 与 28→37 子指标 prose 对齐；增加 metric coverage 表 |
| spec v0.3.0 | 2026-04-29 | 新增 §14 Core-Goal Invariant + §15 round_kind enum + §16 multi-ability layout (Informative); §17 hard rules 9 + 10 |
| spec v0.4.0 | 2026-04-30 | 新增 §18 token-tier + §19 real-data-verification + §20 lifecycle state machine + §21 health-smoke + §22 eval-pack-curation + §23 method-tagged-metrics; §17 hard rules 11/12/13; FIRST v2_tightened ship |
| spec v0.4.2-rc1 | 2026-05-05 | A1 description-cap absorption from `addyosmani/agent-skills` v1.0.0 docs/skill-anatomy.md; §24.1 Normative; +1 hard rule (14); +1 BLOCKER (15) |
| spec v0.4.3-rc1 | 2026-05-05 | A2 standardized SKILL.md sections from agent-skills TDD + code-review SKILL.mds; §24.2 Informative; ZERO new BLOCKER |
| spec v0.4.4-rc1 | 2026-05-05 | A3 progressive-disclosure from agent-skills docs/skill-anatomy.md; §24.3 Normative; +1 hard rule (15); +1 BLOCKER (16) |
| spec v0.4.5-rc1 | 2026-05-05 | A4 lifecycle category taxonomy from agent-skills using-agent-skills/SKILL.md; §24.4 Informative; +1 OPTIONAL schema field |
| spec v0.4.6-rc1 | 2026-05-05 | A5 meta-routing pattern from agent-skills using-agent-skills/SKILL.md; §24.5 Informative; ZERO new BLOCKER; STRICT §11 / §5.2 router-model-training forever-out compliance |
| spec v0.4.7-rc1 | 2026-05-05 | **A6 anti-pattern doc + r13 long-term registration**; §24.6 Informative metadocumentary registration mechanism; FIRST registered long-term external research reference (`r13_agent_skills_comparison.md` against agent-skills v1.0.0); ZERO new BLOCKER; STRICT §11 forever-out — research material only, NOT code dependency; **v0.5.0 absorption arc COMPLETE** |
