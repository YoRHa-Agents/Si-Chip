# Si-Chip Research Index

> Last updated: 2026-04-28  
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
