---
task_id: R10
scope: Si-Chip self-registering Skill/Plugin roadmap for feedback v0.0.3
last_updated: 2026-04-28
supported_targets:
  - Claude Code
  - Cursor
  - Codex
---

# R10 · Si-Chip 自注册 Skill/Plugin 路线图

## 0. TL;DR
Si-Chip 应交付为一个可本地注册、安装、运行的 **self-registering Skill/Plugin**，而不只是研究文档或模板库。
第一步不是 marketplace，也不是支持所有 IDE；第一步是让 Si-Chip 自己成为第一个被 Si-Chip 评估、优化、router-test 和 half-retire review 的 `BasicAbility`。
推荐路线：
```text
doc/spec freeze -> self Skill MVP -> self-eval harness -> dogfood iteration -> cross-IDE packaging -> plugin distribution
```
成功定义：在 **Claude Code / Cursor / Codex** 三个目标上可用，并能证明一轮自迭代后 token、latency、context footprint 或 path efficiency 至少一项改善，同时不牺牲任务质量。

## 1. Packaging Targets（v0.0.5 冻结优先级：Cursor → Claude Code → Codex）

### 1.1 Cursor（第一优先）
兼容产物：
```text
.agents/skills/si-chip/SKILL.md
.cursor/skills/si-chip/SKILL.md
```
策略：
- 以 `.agents/skills/si-chip/` 作为中立源。
- `.cursor/skills/si-chip/` 作为同步或编译产物。
- Rules 通过 `AGENTS.md`（由 `.rules/si-chip-spec.mdc` 编译）生效。
- 不把 Cursor-only 配置写死进核心 Skill body。

### 1.2 Claude Code（第二优先）
优先产物：
```text
.claude/skills/si-chip/SKILL.md
```
策略：
- 同步自 `.agents/skills/si-chip/`。
- 先做 `SKILL.md`，不先做 Plugin；commands/hooks 等 self-eval 稳定通过后再做。
- `description` 聚焦 profile / eval / router-test / half-retire 触发。
- R6/R8/R9/R10 长内容放 `references/`，不塞进触发 metadata。

### 1.3 Codex CLI（后续，最低优先级）
兼容产物：
```text
AGENTS.md
.codex/
```
策略：
- 不假设 Codex CLI 有真实 `SKILL.md` runtime。
- `AGENTS.md` 说明 Si-Chip 的触发场景、工作流和输出格式。
- `.codex/` profile / instruction bridge 绑定 Si-Chip 工作流。
- 仅在 Cursor / Claude Code 均通过 v1_baseline 后才推进。

### 1.4 Marketplace
永远不做。不允许通过命名转写引入。

## 2. Recommended Action Route（v0.0.5）

| Phase | 名称 | Gate |
|---|---|---|
| P0 | Spec Freeze（已完成） | `spec_v0.1.0.md` 冻结并编译进 `AGENTS.md`；不回到 Markdown-to-CLI 定位 |
| P1 | Design（当前） | schema / 架构 / 接口 / factory templates 设计；不做实现 |
| P2 | Self Skill Package（full scope） | 全量 7 维 / 28 子指标可输出；安装步骤 ≤2；metadata 在 v1_baseline 范围内 |
| P3 | Self Evaluation Harness | ≥6 个 dogfood case；有 no-ability baseline；报告机器可读 |
| P4 | Dogfood Iteration Loop | 连续 2 轮 v1_baseline 通过 → 升 v2_tightened → 再升 v3_strict |
| P5 | Cross-Platform Sync | **顺序：Cursor → Claude Code → Codex**；每次 spec 变更重新 compile `AGENTS.md` |
| P6 | Local Distribution（非 marketplace） | 仅限本地安装 / 分发；**marketplace 永远不做** |

### P2 · Self Skill Package（全量）
最小文件：
```text
.agents/skills/si-chip/SKILL.md
.agents/skills/si-chip/references/basic-ability-profile.md
.agents/skills/si-chip/references/self-dogfood-protocol.md
.agents/skills/si-chip/references/metrics-r6-summary.md
.agents/skills/si-chip/references/router-test-r8-summary.md
.agents/skills/si-chip/references/half-retirement-r9-summary.md
```
Gate：`metadata_tokens <= 120`（v1 起步），`body_tokens <= 5000`，本地安装步骤 `<= 2`，能为 Si-Chip 自身输出全量 7 维 / 28 子指标的 `BasicAbilityProfile`。

### P3 · Self Evaluation Harness
最小 cases：
- 为 Si-Chip docs 生成 `BasicAbilityProfile`。
- 区分 canonical / spec / rules / evidence。
- 根据 R6 输出指标缺口（全量 28 子指标，不做 MVP 子集）。
- 根据 R8 设计 router-test matrix 与 router 范式研究任务。
- 根据 R9 判断过重 instruction 是否 `half_retire`（必须附 value vector 数字）。
- 根据 eval 结果生成下一轮 `next_action_plan`。
必测指标：7 维 / 28 子指标全量；顶层强制 `pass_rate`、`pass_k`、`baseline_delta`、`metadata_tokens`、`per_invocation_footprint`、`wall_clock_p95`、`trigger_F1`、`router_floor`、`iteration_delta`。

### P4 · Dogfood Iteration Loop
循环：
```text
profile -> evaluate -> diagnose -> improve -> router-test -> half-retire review -> iterate -> package/register
```
每轮产物：`BasicAbilityProfile`、`metrics_report`、`router_floor_report`、`half_retire_decision`、`next_action_plan`、`iteration_delta`。
Gate：连续 ≥2 轮通过当前 gate（v1 → v2 → v3）；不允许通过牺牲 `pass_rate` 换取效率；所有 `half_retire` 必须基于 R9 value vector 数字。

### P5 · Cross-Platform Sync（Cursor 优先）
- `.agents/skills/si-chip/` 是 source of truth。
- 先把 `.cursor/skills/si-chip/` 同步上。
- 再同步 `.claude/skills/si-chip/`。
- 最后做 `AGENTS.md` + `.codex/` bridge。
- 每次 spec 或规则变更强制重新 compile `AGENTS.md`。

### P6 · Local Distribution（非 marketplace）
仅限 local install / mirror / git 分发。**Marketplace 永远不做**；不允许绕名义引入。

## 3. Self-Dogfood Protocol
Dogfood 对象是当前仓库：
```text
/home/agent/workspace/Si-Chip
```
输入文档：
- `.local/research/si_chip_research_report_zh.md`
- `.local/research/decision_checklist_zh.md`
- `.local/research/README.md`
- `.local/research/r6_metric_taxonomy.md`
- `.local/research/r8_router_test_protocol.md`
- `.local/research/r9_half_retirement_framework.md`
- `.agents/skills/si-chip/` 或等价 Skill package
协议：
1. `profile`: 为 Si-Chip 生成 `BasicAbilityProfile`。
2. `evaluate`: 跑 no-ability baseline 与 with-ability。
3. `diagnose`: 用 R6 7 维 / 28 子指标定位瓶颈（**全量实现，不做 MVP 子集**）。
4. `router-test`: 用 R8 8-cell MVP 测 `router_floor`；研究 routing 范式，不训练 router 模型。
5. `half-retire review`: 用 R9 value vector 判断压缩、冷存储、manual-only 或 retire；必须附带数字。
6. `iterate`: 生成并执行下一轮 action plan，连续 2 轮通过 v1_baseline 才升 v2_tightened。
7. `compare`: 输出 iteration delta。
8. `package/register`: 按 Cursor → Claude Code → Codex 顺序同步。
R6 绑定：D1-D7 全量子指标，`v1_baseline / v2_tightened / v3_strict` 三档递进。
R8 绑定：测 `composer_2`、`sonnet_shallow` × `fast/default` × `trigger_basic/near_miss`；**严禁**训练 router。
R9 绑定：half_retire 必须由 value vector 数字触发，不允许凭感觉。

## 4. Concrete Repo Layout Proposal
```text
.agents/skills/si-chip/
  SKILL.md
  references/{basic-ability-profile,self-dogfood-protocol,metrics-r6-summary,router-test-r8-summary,half-retirement-r9-summary}.md
  scripts/{profile_static,count_tokens,aggregate_eval}.py
.claude/skills/si-chip/
  SKILL.md
  references/
  scripts/
.cursor/skills/si-chip/
  SKILL.md
  references/
  scripts/
.cursor/rules/si-chip-bridge.mdc
.codex/profiles/si-chip.md
.codex/instructions/si-chip-bridge.md
AGENTS.md
templates/
  basic_ability_profile.schema.yaml
  self_eval_suite.template.yaml
  router_test_matrix.template.yaml
  half_retire_decision.template.yaml
  next_action_plan.template.yaml
evals/si-chip/
  cases/{profile_self,docs_boundary,metrics_gap,router_matrix,half_retire_review,next_action_plan}.yaml
  baselines/{no_ability,with_si_chip}/
  reports/{basic_ability_profile,metrics_report,router_floor_report,half_retire_decision,iteration_delta}
```
Source rule：`.agents/skills/si-chip/` 是源；平台目录是产物；`templates/` 存结构；`evals/` 存证据，不进入 Skill trigger body。

## 5. What NOT To Do First
- 不要先建 marketplace。
- 不要先支持所有 IDE 或 Agent runtime。
- 不要训练 router。
- 不要在 Skill MVP 通过 eval 前先做通用 CLI。
- 不要把 R1-R9 全塞进 `SKILL.md`。
- 不要维护三套互相漂移的平台 Skill。
- 不要在没有 no-ability baseline 时宣称优化有效。

## 6. Acceptance Gates
MVP 必须满足：
1. 可在 Claude Code / Cursor / Codex 三个目标中本地安装或通过 bridge 使用。
2. 可运行 Si-Chip self-eval。
3. 可为 Si-Chip 自身产出 `BasicAbilityProfile`。
4. 可产出 `next_action_plan`。
5. 可输出 R6 MVP 8 指标中至少 6 项。
6. 可运行 R8 MVP router-test，并给出 `router_floor` 或明确阻塞原因。
7. 可运行 R9 value vector，区分 keep / half_retire / retire。
8. 一轮 dogfood 后，能展示 token、latency、context footprint 或 path efficiency 改善。
9. 改善不得伴随 `pass_rate` 明显下降。
10. 所有失败必须显式报告，不允许静默跳过 eval。
建议数值门槛：`pass_rate >= 0.80`；`trigger_F1 >= 0.85`；`near_miss_FP_rate <= 0.10`；`metadata_tokens <= 100`；`per_invocation_footprint <= 7000`；`wall_clock_p95 <= 30s`；单轮效率改善 `>= 10%`。

## 7. Risks and Mitigations
| 风险 | 影响 | 缓解 |
|---|---|---|
| 三平台 runtime 不一致 | 安装体验分裂 | `.agents/skills/si-chip/` 作源，平台目录作产物 |
| 过早做 Plugin | 分发复杂度吞掉 eval 目标 | P5 前禁止 Plugin-first |
| Skill body 过长 | context 成本上升 | 长证据放 references，metadata gate <= 100 |
| 没有 baseline | 无法证明收益 | P2 强制 no-ability vs with-ability |
| router-test 变训练 router | 偏离 R8 | 只测 floor，不训练模型 |
| dogfood 样本太少 | 指标不稳 | MVP >= 6 cases，后续扩到 20+ |
| half-retirement 被误解为删除 | 丢失性能价值 | R9 value vector 必跑 |
| Codex 无 SKILL.md runtime | 安装假设错误 | 只做 `AGENTS.md` + `.codex` bridge |
| 文档漂移 | canonical 失真 | 明确 docs 更新点和 source rule |

## 8. Integration With Existing Docs
后续需要更新以下 canonical / tracking docs：
1. `.local/research/si_chip_research_report_zh.md`: 执行结论加入 self-registering Skill/Plugin；MVP 路线图加入 self-dogfood package 阶段；最终推荐加入 Claude Code / Cursor / Codex 边界。
2. `.local/research/decision_checklist_zh.md`: Productization 决策加入 `self_registering_skill_package`；`BasicAbilityProfile` 加 `install_targets`、`packaging_surface`、`self_eval_state`；MVP gate 加 local install、self-eval、next-action plan、iteration delta。
3. `.local/research/README.md`: Evidence Library 登记 `r10_self_registering_skill_roadmap.md`；Current Unified Model 加 `package/register`；Version History 标记吸收 feedback v0.0.3。
4. `.local/feedbacks/TRACKER.md`: 标记 feedback v0.0.3 已处理；链接到 R10；记录 canonical-sync 待办。
本任务只写 R10，不修改上述文件；它们应由下一轮 canonical-sync 任务处理。

## 9. Immediate Next Actions
1. 新建 `.agents/skills/si-chip/SKILL.md` 作为 canonical Skill source。
2. 从 R6/R8/R9/R10 提炼 4 个短 reference 文件。
3. 建立 `templates/basic_ability_profile.schema.yaml`。
4. 建立 `evals/si-chip/cases/` 的 6 个 MVP cases。
5. 跑 no-ability baseline，再安装 Si-Chip Skill MVP 跑 with-ability eval。
6. 输出 `BasicAbilityProfile`、`metrics_report`、`router_floor_report`、`next_action_plan`。
7. 基于报告压缩或重写 Si-Chip Skill body，再跑 eval 并记录 `iteration_delta`。
8. Gate 通过后再进入 P4/P5。

## 10. Bottom Line
Si-Chip v0.0.3 后的关键转向是：把“研究如何优化 Skill”变成“Si-Chip 自己就是可安装 Skill，并用自己优化自己”。
第一版成功不以分发规模衡量，而以 self-dogfood 证据衡量：能安装、能评估、能产出 profile 与 next-action plan，并能在至少一个效率指标上显示真实改善。
