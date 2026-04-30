---

## title: "Si-Chip v0.4.0 Industry Practice Brief"
task_id: R12
version: "v0.0.1"
status: "draft"
effective_date: "2026-04-29"
target_spec_bump: "v0.4.0"
authoring_round: "Stage 1 — research only; v0.4.0 plan authoring is Stage 2"
language: "zh-CN + en (mixed; technical names in en)"
authoritative_inputs:
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/SUMMARY.md
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/round_1.md
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/round_5.md
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/round_8.md
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/round_11.md
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/round_14.md
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/round_17.md
  - .local/research/spec_v0.3.0.md
  - .local/research/r11_core_goal_invariant.md
  - /home/agent/reference/openspec/docs/concepts.md
  - /home/agent/reference/openspec/docs/workflows.md
  - /home/agent/reference/openspec/openspec/changes/add-qa-smoke-harness/proposal.md
  - /home/agent/reference/dspy/dspy/teleprompt/bootstrap.py
  - /home/agent/reference/dspy/dspy/teleprompt/mipro_optimizer_v2.py
  - /home/agent/reference/inspect_ai/src/inspect_ai/dataset/_dataset.py
  - /home/agent/reference/inspect_ai/CLAUDE.md
  - /home/agent/reference/evals/evals/registry/evals/2d_movement.yaml
  - /home/agent/reference/evals/evals/registry/eval_sets/chinese-numbers.yaml
  - /home/agent/reference/agentic-context-engine/README.md
  - /home/agent/reference/agentic-context-engine/CLAUDE.md
  - /home/agent/reference/agentic-context-engine/ace/skillbook.py
  - /home/agent/reference/acon/README.md
  - /home/agent/reference/coevolved/README.md
  - /home/agent/reference/superpowers/skills/writing-skills/SKILL.md
  - /home/agent/reference/superpowers/skills/verification-before-completion/SKILL.md
  - /home/agent/reference/tau-bench/README.md
  - /home/agent/reference/karpathy-llm-wiki.md
  - /home/agent/reference/openspec/docs/concepts.md (re-verified post-draft, matches excerpt)
external_sources:
  - [https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)
  - [https://docs.anthropic.com/en/docs/claude-code/skills](https://docs.anthropic.com/en/docs/claude-code/skills)
  - [https://docs.pact.io/consumer/](https://docs.pact.io/consumer/)
  - [https://github.com/mlperf/policies/blob/master/submission_rules.adoc](https://github.com/mlperf/policies/blob/master/submission_rules.adoc)
  - [https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics)
  - [https://github.com/marketplace/actions/url-health-check](https://github.com/marketplace/actions/url-health-check)
  - [https://medium.com/@deryayildirimm/deploying-to-render-insert-a-smoke-test-step-with-github-actions-ffbd49a104dd](https://medium.com/@deryayildirimm/deploying-to-render-insert-a-smoke-test-step-with-github-actions-ffbd49a104dd)
  - [https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge](https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge)
  - [https://dspy.ai/api/optimizers/GEPA](https://dspy.ai/api/optimizers/GEPA)
  - [https://dspy.ai/api/optimizers/BootstrapFewShot](https://dspy.ai/api/optimizers/BootstrapFewShot)
  - [https://nedcodes.dev/guides/cursor-token-budget](https://nedcodes.dev/guides/cursor-token-budget)
  - [https://developertoolkit.ai/en/cursor-ide/advanced-techniques/token-management](https://developertoolkit.ai/en/cursor-ide/advanced-techniques/token-management)
  - [https://www.cursor.com/docs/context/rules](https://www.cursor.com/docs/context/rules)
  - [https://arxiv.org/abs/2510.00615](https://arxiv.org/abs/2510.00615)
sources_count: 34
clones_attempted: 4
clones_failed: 4
proposes_v0_4_0_themes: ["§18 Token-Tier Economy (C7/C8/C9)", "§19 Real-Data Verification", "§20 Lifecycle State Transitions", "§21 health_smoke_check field", "§22 Eval-Pack Curation Discipline", "§23 Measurement Honesty Toolkit"]
preserves_normative_sections: ["§3", "§4", "§5", "§6", "§7", "§8", "§11", "§14", "§15"]
forever_out_compliance: "verified — see §7"

# R12 · Si-Chip v0.4.0 Industry Practice Brief

> **核心论断**: v0.3.0 把 "**核心目标无回退** + **round_kind 透明化** + **多 ability 解锁**" 写入了 spec；v0.4.0 应该把焦点从 "let the engine run honestly" 升级为 "**give the engine the right unit of measurement, the right test substrate, and the right release sentinel**"。
>
> 23 轮 chip-usage-helper + 15 轮 Si-Chip self-dogfood 暴露了三个新主轴：(1) **Token Economy** —— EAGER/ON-CALL/LAZY 分层比 R6 的 C1+C4 更接近 user-impact；(2) **Real-Data Verification** —— 当 production payload 与 mock 形态分歧时，round_kind=code_change 也无法自动捕获；(3) **Lifecycle Machinery** —— stage transition / promotion_history / ship_decision 这些是 spec 当前缺失的状态机。
>
> Industry precedent for each is now mature enough to land in a v0.4.0 ship: Anthropic skills 显式有 progressive disclosure 三档 (metadata/instructions/resources) 对应 EAGER/ON-CALL/LAZY；Pact "as loose as possible" + msw real-payload fixture 工作流对应 Real-Data Verification；OpenSpec proposal/specs/archive 与 ACE Skillbook 三角色（Agent/Reflector/SkillManager）对应 Lifecycle Machinery；MLPerf reproducibility + GitHub Actions URL Health Check 对应 ship 阶段的 smoke discipline。
>
> 本文是 v0.4.0 的 **research-stage industry-practice brief**。本文 **不是** spec 本体；spec 本体由 Stage 2 写出，并必须满足 §3 / §4 / §5 / §6 / §7 / §8 / §11 / §14 / §15 字节级保留（additivity discipline；同 v0.2.0 → v0.3.0 reconciliation 模式）。

---

## 0. TL;DR — v0.4.0 themes the plan author should center on

7 bullets, each citing a concrete R-item and a concrete industry source.

1. **Token-Tier MVP-8 Promotion (C7/C8/C9)** — chip-usage-helper Cycle 2-3 证明 `EAGER per-session / ON-CALL per-trigger / LAZY` 是比 `C1 metadata + C4 footprint` 更接近 user-impact 的度量轴 (R30, R32, R44; SUMMARY.md Cycle 2 §R30, Round 14 -55% EAGER win)。Anthropic 官方 Skill 文档明确指出三档 progressive disclosure (Metadata ~100 tokens / Instructions <500 lines / Resources unlimited) 是同构概念 ([https://docs.anthropic.com/en/docs/claude-code/skills)。**Recommendation](https://docs.anthropic.com/en/docs/claude-code/skills)。**Recommendation)**: 把 C7/C8/C9 作为 **顶层 token_tier invariant** 加到 §3.1 后面（同 §14 C0 不进 R6 D8 的策略），不破坏 R6 frozen 7×37 计数。
2. **Real-Data Verification 9th Step (or `evaluate` sub-step)** — chip-usage-helper Round 24 v0.9.0 zero-events bug 是 production payload 与 mock fixture 形态分歧导致的；msw + user-install + post-recovery-live 是 industry-blessed 三层验证 (R45, R46; SUMMARY.md Cycle 5)。Pact "as loose as possible while ensuring providers can't break compatibility" 是同义工艺 ([https://docs.pact.io/consumer/)。**Recommendation](https://docs.pact.io/consumer/)。**Recommendation)**: 加 §19 Real-Data Verification 作为 Normative §8.1 step 4.5 (between `improve` and `router-test`)，并在 `feedback` 模板加 `real_data_samples` 结构化块。
3. **Lifecycle State-Machine Block on `BasicAbilityProfile`** — chip-usage-helper bumps `evaluated → routed` 时 spec 没说 "this is when you advance"；ship_decision.yaml / promotion_history 是当前 ad-hoc 字段 (R15, R17, R27; SUMMARY.md R15/R17/R27)。OpenSpec proposal/apply/archive 三态 + delta semantics (ADDED/MODIFIED/REMOVED) 是直接的 industry precedent (`/home/agent/reference/openspec/docs/concepts.md`); ACE Skillbook 的 `helpful/harmful/neutral` 计数 + `SimilarityDecision` (KEEP) 显示 lifecycle metadata 应该 first-class (`/home/agent/reference/agentic-context-engine/ace/skillbook.py`)。**Recommendation**: 加 §20 stage_transition_rules + promotion_history 作为 §2.1 additive block。
4. `**health_smoke_check` field + ship-prep gate** — R47 的 ops CI smoke (`/api/v1/cursor/events/health` returns `latestTsMs > 0`) 是 ANY ability-with-live-backend 的通用风险 (R47; SUMMARY.md Cycle 5)。GitHub Actions URL Health Check + post-deploy verification is the cross-industry pattern ([https://github.com/marketplace/actions/url-health-check](https://github.com/marketplace/actions/url-health-check); [https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge)。**Recommendation](https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge)。**Recommendation)**: 加 §21 `BasicAbility.packaging.health_smoke_check` optional 字段，并把它接到 §8.1 step 8 `package-register` 的 ship gate（不通过 = 阻塞 ship）。
5. **Eval-Pack Curation Discipline (40-prompt minimum + provenance)** — 20-prompt MVP "1 FP = -0.05 F1" 噪声窗已被 chip-usage-helper Round 1 实证；G1 deterministic_simulation provenance 必须 first-class (R3, R14, R25; SUMMARY.md R3/R14/R25)。OpenAI Evals registry 是 versioned eval_sets 的 reference impl (`/home/agent/reference/evals/evals/registry/eval_sets/`); MLPerf "benchmark detection is not allowed" + reproducibility 是同源工艺 ([https://github.com/mlperf/policies/blob/master/submission_rules.adoc)。**Recommendation](https://github.com/mlperf/policies/blob/master/submission_rules.adoc)。**Recommendation)**: 加 §22 `templates/eval_pack_qa_checklist.md` + spec note "20 prompts MVP; 40+ for v2_tightened promotion"。
6. **Measurement Honesty Toolkit (tokens_estimate_method, R3 split, L4 max/mean, U4 warm/cold)** — R36/R33/R20/R19 都是 "同一个 metric 名下藏着不同假设" (SUMMARY.md R19/R20/R29/R33/R36)。Inspect AI Sample 类把 `metadata` 作为 first-class field 让 sample-level provenance 可追溯 (`/home/agent/reference/inspect_ai/src/inspect_ai/dataset/_dataset.py:81`)。DSPy BootstrapFewShot `metric_threshold` 是 numerical metric quality control 的 reference ([https://dspy.ai/api/optimizers/BootstrapFewShot)。**Recommendation](https://dspy.ai/api/optimizers/BootstrapFewShot)。**Recommendation)**: 加 §23 `metrics.<dim>.method` + `metrics.<dim>.confidence_band` 字段族；把现有 R3 拆成 R3_eager_only + R3_post_trigger。
7. **Self-iterating bootstrap pattern is already what Si-Chip is** — DSPy GEPA "reflective text evolution" + ACE "Skillbook 自学习" 都是 Si-Chip 8 步协议的 sibling implementations ([https://dspy.ai/api/optimizers/GEPA](https://dspy.ai/api/optimizers/GEPA); `/home/agent/reference/agentic-context-engine/CLAUDE.md`)。**Implication**: v0.4.0 不需要发明新的 self-iteration paradigm；它需要把现有 paradigm 的 8 步协议中 "diagnose → improve" 这一段从手写 next_action_plan 升级到 **可机器读取的反思摘要**（GEPA 的 metric `{score, feedback}` 结构）。这是 v0.5.0+ 的种子，本 v0.4.0 brief 在 §4 留指针不强推。

### §0.5 What v0.3.0 already shipped (recap, for plan-author context)

> Plan author should read this before §1 to avoid re-proposing what already landed. Source: spec_v0.3.0.md frontmatter + `.local/research/spec_v0.3.0.md`.

**v0.3.0 Normative additions** (10 R-items closed, see §1 status legend):

- §14 `core_goal` invariant + `core_goal_test_pack` schema + `C0_core_goal_pass_rate = 1.0` strict-no-regression + REVERT-only rollback (closes the latent design bug from `feedback_for_v0.2.0.md`).
- §15 `round_kind ∈ {code_change | measurement_only | ship_prep | maintenance}` enum + per-kind iteration_delta clause table (RELAXED for measurement_only) + per-kind C0 clause table (universal MUST = 1.0) + §4.2 promotion-counter eligibility (closes R10 + R24 + R27).
- §16 multi-ability dogfood layout `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` (Informative @ v0.3.0; Normative @ v0.3.x trigger: 2+ abilities + 2 ship cycles) (closes R1 + R23).
- §17 v0.3.0 hard rules 9 + 10 (additive to v0.2.0's 8 rules; AGENTS.md §13 grows to 10 rules).
- 4 generic tools: `tools/eval_skill.py` (closes R7 + R12 + R16), `tools/cjk_trigger_eval.py` (closes R2), `tools/multi_handler_redundant_call.py` (closes R18 + R20-partial), `tools/round_kind.py`.
- spec_validator BLOCKERs grow 9 → 11 (`CORE_GOAL_FIELD_PRESENT` + `ROUND_KIND_FIELD_PRESENT_AND_VALID`).
- Templates `basic_ability_profile.schema.yaml` / `iteration_delta_report.template.yaml` / `next_action_plan.template.yaml` bumped 0.1.0 → 0.2.0 (additively).

**v0.3.0 Normative preserved byte-identical** (per spec frontmatter `preserves_byte_identical_v0_2_0`):

- §3 (Metric Taxonomy R6 7×37) / §4 (Progressive Gate Profiles 30 cells) / §5 (Router Paradigm) / §6 (Half-Retirement) / §7 (Packaging) / §8 (Self-Dogfood Protocol 8 steps + 6 evidence files) / §11 (Scope Boundaries) / §13 (Acceptance Criteria for v0.1.0).

**v0.3.0 ship evidence**: Round 14 (`code_change`) + Round 15 (`measurement_only`) consecutive PASSes at v1_baseline ⇒ v0.3.0 ship at gate relaxed (= v1_baseline; same as v0.2.0 ship gate).

**v0.4.0 contract**: Same additivity discipline must hold for §3 / §4 / §5 / §6 (with one Q4 exception) / §7 / §8 / §11 / §14 / §15 byte-identical to v0.3.0. The 6 NEW sections (§18-§23) sit alongside §14-§17; the 3 NEW hard rules (11/12/13) extend §17 additively.

---

## 1. Residual R-Items After v0.3.0

> 47 R-items total. v0.3.0 已 ship 10 items（the spec authoring task explicitly counted 5 R-clusters; this table breaks them down to individual R numbers）。剩余 37 items 按 P0/P1/P2/P3 + cluster 排序。

**Status legend**:

- `ADDRESSED` = 已在 v0.3.0 spec / tools 落地
- `P0` = v0.4.0 必做（leverage 最大或 user-impact 最强）
- `P1` = v0.4.0 应做（高 ROI 但可 split 出独立 ship）
- `P2` = v0.4.0 可做（low-effort polish）
- `P3` = v0.5.0+ 候选（informational / nice-to-have / 等更多证据）


| R#  | One-line                                                                            | Addressed in v0.3.0                                               | v0.4.0 priority | Cluster                              | Rationale                                                                                                        |
| --- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| R1  | Multi-ability dogfood namespace `.local/dogfood/<DATE>/abilities/<id>/`             | YES — §16                                                         | —               | (closed)                             | Multi-ability layout shipped Informative @ v0.3.0; Normative-promote in v0.3.x.                                  |
| R2  | CJK-aware trigger evaluator (substring + discriminators)                            | YES — `tools/cjk_trigger_eval.py`                                 | —               | (closed)                             | Generic CAD harness shipped.                                                                                     |
| R3  | Eval-pack 40-prompt minimum for v2_tightened decisions                              | NO                                                                | **P1**          | measurement_quality                  | 20-prompt 1 FP = -0.05 F1 噪声窗已实证；MLPerf-style minimum-pack rule should land.                                     |
| R4  | Round-1 delta semantics vs no_ability_baseline                                      | NO                                                                | P2              | measurement_quality                  | One-sentence spec note in §8.2 evidence #6 sufficient.                                                           |
| R5  | R8 description_competition bidirectional measurement                                | NO                                                                | P2              | measurement_quality                  | r8 currently only measures my-tokens-in-neighbor; should also measure neighbor-could-steal-my-prompts.           |
| R6  | `promotion_state` first-class block on `metrics_report.yaml`                        | NO                                                                | **P1**          | lifecycle_machinery                  | spec §4.2 says "consecutive 2 passes" but metrics_report has no canonical schema; ad-hoc fields confuse readers. |
| R7  | Generic `eval_skill.py --skill --rule --eval-pack ... --out` harness                | YES — `tools/eval_skill.py`                                       | —               | (closed)                             | ~600 LoC saved per new ability.                                                                                  |
| R8  | T4 canonical recovery harness (4-scenario branch)                                   | NO                                                                | **P1**          | measurement_quality                  | spec §3 T4 specified but no canonical generator; multiple abilities will reinvent.                               |
| R9  | T3 baseline_delta noise floor (≥ 0.05 informative)                                  | NO                                                                | P3              | measurement_quality                  | Edge case; not blocking.                                                                                         |
| R10 | Refactor-round shape (slim 4-step subset)                                           | YES — `round_kind=measurement_only`                               | —               | (closed)                             | Round_kind enum subsumes the refactor-round concept.                                                             |
| R11 | path_efficiency saturation when detour_without=0                                    | NO                                                                | P3              | measurement_quality                  | Trivial spec-note fix.                                                                                           |
| R12 | Default `routing_cost` measurement R6/R7                                            | YES — `eval_skill.py` D6 helpers                                  | —               | (closed)                             | Default emitted in eval_skill harness.                                                                           |
| R13 | R8 with 0 neighbors = 0.0 (vs null)                                                 | NO                                                                | P3              | measurement_quality                  | Trivial; can land alongside R5.                                                                                  |
| R14 | G1 `provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` first-class     | NO                                                                | **P1**          | measurement_quality                  | Currently a sub-key; readers misread deterministic-simulation as real cross-model robustness.                    |
| R15 | `stage_transition_rules` block in §2 (when to advance evaluated → routed?)          | NO                                                                | **P0**          | lifecycle_machinery                  | spec §2.2 enum lists stages but never says how to transition; ad-hoc decisions today.                            |
| R16 | Generic `governance_v3_v4()` helper                                                 | YES — `eval_skill.py` D7 helpers                                  | —               | (closed)                             | V3/V4 ≥ 0.0 default for new abilities.                                                                           |
| R17 | `promotion_history` block on `BasicAbilityProfile`                                  | NO                                                                | **P0**          | lifecycle_machinery                  | Each transition needs an explicit record; today it's buried in `iteration_delta_report`.                         |
| R18 | L4 walks ALL handler files                                                          | YES — `tools/multi_handler_redundant_call.py`                     | —               | (closed)                             | MAX-aggregate across handlers shipped.                                                                           |
| R19 | U4 warm/cold/semicold distinction                                                   | NO                                                                | P2              | measurement_quality                  | Direct spec extension; ~10 LoC in eval_skill.                                                                    |
| R20 | L4_max + L4_mean + aggregator field                                                 | YES (partial — has max; mean optional)                            | P3              | measurement_quality                  | Already mostly addressed; can add mean as nice-to-have.                                                          |
| R21 | pass_k jitter helper (multi-axis: order, casing, whitespace, tokenization)          | NO                                                                | P2              | measurement_quality                  | Useful but requires deciding default jitter axes.                                                                |
| R22 | L6=0 architecture rationale (feature, not bug)                                      | NO                                                                | P3              | measurement_quality                  | One-sentence spec note.                                                                                          |
| R23 | Cross-ability dispatch surface                                                      | YES — §16 + concurrent dogfood docs                               | —               | (closed)                             | Same fix as R1.                                                                                                  |
| R24 | 5-round shipping sufficient; rounds 6-10 = evidence_only                            | YES — `round_kind=measurement_only`                               | —               | (closed)                             | Round_kind exposes evidence-only rounds.                                                                         |
| R25 | `eval_pack_qa_checklist.md` reference (bilingual, near-miss, anti-patterns)         | NO                                                                | **P1**          | measurement_quality                  | Without this, the next ability burns 30 min on the methodology trap.                                             |
| R26 | Routing is the optimization frontier (de-emphasize 28-cell fill)                    | NO                                                                | P3              | (informational)                      | Captured in spirit by §15 RELAXED clause; no new spec change needed.                                             |
| R27 | Per-ability `ship_decision.yaml` as 7th evidence file                               | NO (partial — round_kind=ship_prep is sentinel; no separate file) | **P1**          | lifecycle_machinery                  | spec §8.2 currently 6 evidence files; ship_decision is the convergence-round artifact.                           |
| R28 | Pyc-cache hardening + `python -m` package                                           | NO                                                                | P2              | packaging_discipline                 | Tooling hygiene; not Normative.                                                                                  |
| R29 | U1 `language_breakdown ∈ {en: <fk>, zh: <chars>, mixed_warning: bool}`              | NO                                                                | P2              | measurement_quality                  | Bilingual descriptions FK-grade is ambiguous; trivial schema fix.                                                |
| R30 | Token-tier C7/C8/C9 EAGER/ON-CALL/LAZY decomposition                                | NO                                                                | **P0**          | token_economy                        | Cycle 2 -55% EAGER win shows this is the user-impact axis.                                                       |
| R31 | MCP `text` content default compact warning                                          | NO                                                                | **P1**          | token_economy                        | One-shot static check; high ROI for any MCP-using ability.                                                       |
| R32 | EAGER-weighted `iteration_delta` (10× ON-CALL)                                      | NO                                                                | **P0**          | token_economy                        | Pairs with R30; the metric formula must point at the right thing.                                                |
| R33 | R3 split: `R3_eager_only` vs `R3_post_trigger`                                      | NO                                                                | **P1**          | token_economy / measurement_quality  | Cycle 2 Round 14 EAGER -447 / ON-CALL +407 reveals this gap.                                                     |
| R34 | `tier_transitions: [{from, to, tokens, reason}]` matrix block                       | NO                                                                | **P1**          | token_economy                        | Structured "moved tokens between tiers" report; pairs with R30.                                                  |
| R35 | `/// <reference path>` packaging-guide pattern                                      | NO                                                                | P3              | packaging_discipline                 | Per-ecosystem; document not Normative.                                                                           |
| R36 | `tokens_estimate_method ∈ {tiktoken, char_heuristic, llm_actual}` + confidence band | NO                                                                | **P1**          | measurement_quality                  | Method confusion produces 2.4× error in some surfaces (Round 17 evidence).                                       |
| R37 | SKILL.md prose populations: `prose_class ∈ {trigger, contract, recipe, narrative}`  | NO                                                                | **P1**          | token_economy                        | Determines what's compressible without R3 risk.                                                                  |
| R38 | Pointer-to-sibling relative-path safety                                             | NO                                                                | P3              | packaging_discipline                 | Per-platform; document not Normative.                                                                            |
| R39 | Static check: server default vs client render cap                                   | NO                                                                | P2              | token_economy                        | One-shot static analyzer; ~50 LoC.                                                                               |
| R40 | zod schema as routing-test self-describing contract                                 | NO                                                                | P3              | token_economy / measurement_quality  | Per-ecosystem (TS-only); explore in v0.5.0.                                                                      |
| R41 | LAZY-tier `.lazy-manifest` packaging rule                                           | NO                                                                | **P0**          | token_economy / packaging_discipline | Pairs with R30/R32; without this, LAZY siblings can accidentally enter EAGER.                                    |
| R42 | Default-data anti-pattern detector in template evaluator                            | NO                                                                | **P1**          | token_economy                        | Cycle 3 Round 17 -8.4% template tokens shows the leverage.                                                       |
| R43 | "Only TRIGGER prose counts for R3" formal declaration                               | NO                                                                | P2              | measurement_quality                  | Spec §3 R3 sub-note; pairs with R37.                                                                             |
| R44 | Rule body ≤ 400-token packaging guideline                                           | NO                                                                | P2              | token_economy / packaging_discipline | Cycle 3 R44 evidence; document as guideline not Normative threshold.                                             |
| R45 | Real-data verification as 9th §8 step (or `evaluate` sub-step)                      | NO                                                                | **P0**          | real_data_verification               | Cycle 5 v0.9.0 zero-events bug = synthetic fixture mismatched production payload.                                |
| R46 | `templates/feedback_real_data_samples.template.yaml` schema                         | NO                                                                | **P0**          | real_data_verification               | Pairs with R45; structured field replaces ad-hoc embedded JSON.                                                  |
| R47 | `health_smoke_check` field on `BasicAbilityProfile` + ship-gate                     | NO                                                                | **P0**          | healthcheck                          | Cycle 5 P3 ops smoke; applies to ANY ability with live backend dependency.                                       |


**Summary tally**:

- ADDRESSED: 10 items (R1, R2, R7, R10, R12, R16, R18, R20-partial, R23, R24)
- **P0 = 8** (R15, R17, R30, R32, R41, R45, R46, R47)
- **P1 = 12** (R3, R6, R8, R14, R25, R27, R31, R33, R34, R36, R37, R42)
- **P2 = 9** (R4, R5, R19, R21, R28, R29, R39, R43, R44)
- **P3 = 8** (R9, R11, R13, R20-mean, R22, R26, R35, R38, R40)
- **Total** = 47 ✓

---

## 2. Industry Practice Survey — 6 thematic clusters

> Each cluster cites ≥ 2 sources (mix of `/home/agent/reference/` repos + WebSearch external). Per source: 1-2 sentence excerpt + 2-3 sentence "what Si-Chip should adopt".

### §2.1 Token Economy & Tier-Aware Context Budgeting

**Why this cluster matters for v0.4.0**: chip-usage-helper Cycles 2 + 3 produced **per-non-triggering-session -447 tokens forever** (Round 14, recurring), **first-run total -33 % vs v0.7.0** (cumulative). This is by-far the biggest user-impact axis observed in 25 rounds and it's invisible to spec §3 D2's `C1 metadata + C4 footprint` framing because they bundle EAGER and ON-CALL together. (Maps to R30, R32, R37, R44.)

#### Source 2.1.a — Karpathy LLM Wiki ("LLM Wiki" pattern)

- **Path**: `/home/agent/reference/karpathy-llm-wiki.md`
- **Excerpt**: "There are three layers: **Raw sources** — your curated collection of source documents... immutable. **The wiki** — a directory of LLM-generated markdown files. The LLM owns this layer entirely. **The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for Codex) that tells the LLM how the wiki is structured."
- **Si-Chip application**: Karpathy's three-layer model is exactly the EAGER (schema/AGENTS.md, always loaded) / ON-CALL (wiki pages, retrieved on demand) / LAZY (raw sources, only when explicitly read) pattern. The AGENTS.md compiled from `.rules/si-chip-spec.mdc` is currently Si-Chip's EAGER tier, and SKILL.md body is ON-CALL. v0.4.0 should ship `C7_eager_per_session`, `C8_oncall_per_trigger`, `C9_lazy_avg_per_load` as the spec-level Karpathy-aligned axes, with Karpathy's "the cost of maintenance is near zero" claim becoming a Si-Chip axiom: every ON-CALL surface that grows must justify itself against the EAGER-recurring savings of moving content to LAZY.

#### Source 2.1.b — Anthropic Skill Authoring Best Practices (Progressive Disclosure)

- **URL**: `https://docs.anthropic.com/en/docs/claude-code/skills`
- **Excerpt**: "Skills load in three tiers to keep token costs low: **Level 1 - Metadata (~100 tokens)**: Name and description, always in context. **Level 2 - Instructions (<500 lines)**: SKILL.md body, loaded when skill activates. **Level 3 - Resources (unlimited)**: Supporting files in templates/, references/, scripts/, loaded on demand."
- **Si-Chip application**: Anthropic's progressive disclosure 三档命名为 Metadata/Instructions/Resources, 与 chip-usage-helper feedback 提的 EAGER/ON-CALL/LAZY 字面不同但语义同构。v0.4.0 应在 spec §3 顶层（NOT R6 D8) 引入 `token_tier` invariant 三轴 C7/C8/C9 + 把 Anthropic 的 "(~100 tokens metadata)" 升级为 spec §4.1 阈值表的硬桶（`C7 ≤ 400 v1 / ≤ 250 v2 / ≤ 150 v3`）。Anthropic 的 "challenge each piece of information: only add context Claude doesn't already have" 直接对应 R32 EAGER-weight 10× 论证：EAGER 每 token 都跨 N 个 session 收费，应该按 N 的量级倍权。

#### Source 2.1.c — Cursor Rules Best Practices (Always-Apply Token Cost)

- **URL**: `https://nedcodes.dev/guides/cursor-token-budget` + `https://www.cursor.com/docs/context/rules`
- **Excerpt**: "Always-apply rules consume tokens on every single prompt, making them the highest-cost rule type. The best practice is to minimize their use: reserve `alwaysApply: true` for only 3-5 truly global rules... An always-apply rule consuming 500-1,000 tokens burns that budget before any conversation begins... Target 3-5 global always-apply rules and 5-15 scoped rules, totaling under 3,000 tokens always-loaded."
- **Si-Chip application**: Cursor 把 `alwaysApply: true` 称为 "highest-cost rule type" 是 R44 ("rule body ≤ 400 tokens packaging guideline") 的 verbatim 工业版。v0.4.0 应把 Cursor 的 "5-15 scoped rules totaling <3000 tokens always-loaded" 数字直接进入 §7 packaging gate 作为 Cursor-specific budget bucket（不限制 Claude Code / Codex；但 Cursor 平台的 packaging gate 需要 EAGER ≤ 3000 tokens）。R44 的 400-token-rule-body 阈值与 Cursor 5-15 rules × 500 tokens average 数字相容。

#### Source 2.1.d — DSPy MIPROv2 / BootstrapFewShot (Demonstration Budget)

- **Path**: `/home/agent/reference/dspy/dspy/teleprompt/mipro_optimizer_v2.py:43-51`
- **Excerpt**: `BOOTSTRAPPED_FEWSHOT_EXAMPLES_IN_CONTEXT = 3 / LABELED_FEWSHOT_EXAMPLES_IN_CONTEXT = 0 / MIN_MINIBATCH_SIZE = 50 / AUTO_RUN_SETTINGS = {"light": {"n": 6, "val_size": 100}, "medium": {"n": 12, "val_size": 300}, "heavy": {"n": 18, "val_size": 1000}}`
- **Si-Chip application**: DSPy MIPROv2 把 demonstration count、minibatch size、validation set size 写成可调档（light/medium/heavy）+ 显式 IN_CONTEXT 上限。这是 token-budget-as-first-class 的 reference 实现：optimizer 本身不允许跑 budget-blow scenarios。Si-Chip v0.4.0 应在 §15 round_kind 之外加一个 sibling 字段 `token_tier_target ∈ {relaxed, standard, strict}`（与 §4 v1/v2/v3 gate 对齐）以让 ability 显式声明本轮的 token-tier 预算压力。所有三个阈值数字 (n=6/12/18, val_size=100/300/1000) 均在 `/home/agent/reference/dspy/dspy/teleprompt/mipro_optimizer_v2.py:47-51` 可核验；v0.4.0 `token_tier_target` 阈值建议向 DSPy `AUTO_RUN_SETTINGS` 数量级对齐。

#### Source 2.1.e — ACON: Context Compression for Long-Horizon LLM Agents (Microsoft Research)

- **Path**: `/home/agent/reference/acon/README.md` + arXiv 2510.00615
- **Excerpt**: "`acon` is a research framework for optimizing the context compression for long-horizon LLM agents, focusing on minimizing redundant memory growth while preserving essential information for decision-making. It provides standardized pipelines for environments, agents, context compression, and distillation (compressor and agent) across multiple realistic benchmarks such as AppWorld, OfficeBench, and 8-objective QA." (README.md L22-L24)
- **URL**: [https://arxiv.org/abs/2510.00615](https://arxiv.org/abs/2510.00615)
- **Si-Chip application**: ACON 是 **research-grade 证据** that context-compression for multi-round agents 不是 vibe optimization，而是可量化的 distillation problem；其论文把 "compressor" 和 "agent" 作为两个独立可训练组件，argues 二者必须解耦才能在 long-horizon tasks 上保持质量不回退。Si-Chip 不能训练 compressor 模型（§11 forever-out "Router 模型训练" 的精神延伸禁止这），但可以从 ACON 汲取**双组件解耦**的 spec 工艺：v0.4.0 §18 token-tier 的 `C7/C8/C9` **不应** 混合 compressor-side 与 agent-side token usage —— SKILL.md 的 prose 是 "agent 侧 context"（人写、人压缩），MCP payload / canvas template 是 "compressor 侧 output"（tool 生成、可机械压缩）。R37 `prose_class ∈ {trigger, contract, recipe, narrative}` 已部分 echo 这一分离；v0.4.0 可加 Informative note "C7 EAGER 主要是 agent-side；C9 LAZY 主要是 compressor-side；C8 ON-CALL 是混合区，需显式 decompose"。ACON 的 arxiv 论文数字可作为 v0.5.0+ 验证 Si-Chip token_tier 阈值合理性的 external anchor。

### §2.2 Real-Data Verification & Contract Tests with Production Samples

**Why this cluster matters for v0.4.0**: chip-usage-helper Round 24 v0.9.0 zero-events bug 是 production payload 与 mock fixture 形态分歧的直接产物 —— ai-bill 后端空数据时 dashboard 静默崩。msw + user-install + post-recovery-live 三层验证是 R45 提的解法。**这是 Si-Chip 当前 8-step 协议唯一无法机器捕获的 failure mode**。(Maps to R45, R46, R47.)

#### Source 2.2.a — Inspect AI Sample / Dataset

- **Path**: `/home/agent/reference/inspect_ai/src/inspect_ai/dataset/_dataset.py:28-105`
- **Excerpt**: `class Sample(BaseModel): r"""Sample for an evaluation task.""" ... input: str | list[ChatMessage] / target: str | list[str] / id: int | str | None / metadata: dict[str, Any] | None / sandbox: SandboxEnvironmentSpec | None / files: dict[str, str] | None / setup: str | None`
- **Si-Chip application**: Inspect AI 的 `Sample` schema 把 `metadata` 作为 first-class field 让 sample-level provenance 可追溯（dataset 可以记录 "case 来自 production payload 2026-04-29 14:32 UTC"）。v0.4.0 应把 Si-Chip `core_goal_test_pack.yaml` 的 case schema 加 `metadata` 字段，至少包含 `provenance ∈ {synthetic, production_sample, user_reported_bug}` + `source_url` + `captured_at`。Inspect AI 的 `files: dict[str, str]` 字段也直接告诉我们怎么把 real payload 作为 fixture 携带。

#### Source 2.2.b — tau-bench (Real-Dialogue Tool-Agent Benchmark)

- **Path**: `/home/agent/reference/tau-bench/README.md`
- **Excerpt**: "We propose τ-bench, a benchmark emulating dynamic conversations between a user (simulated by language models) and a language agent provided with domain-specific API tools and policy guidelines."
- **Si-Chip application**: τ-bench 用 user-simulation + real-tool-API 跑端到端对话，不是 mock golden 输出 而是 real provider response shape。它的 `Pass^k` 度量（同一 task 跑 k 次都通过）已经是 Si-Chip §3.1 D1 T2 `pass_k` 的同源工艺。v0.4.0 的 §19 Real-Data Verification 应学 τ-bench 把 "real provider state under test" 作为 first-class fixture surface（chip-usage-helper 的 ai-bill `events/health` 直接对应 τ-bench 的 `airline.search_flights` API）。

#### Source 2.2.c — Pact Consumer-Driven Contract Tests

- **URL**: `https://docs.pact.io/consumer/`
- **Excerpt**: "Good Pact tests should be 'as loose as they possibly can be, while still ensuring that the provider can't make changes that will break compatibility with the consumer.' ... Focus on exposing bugs in how the consumer creates requests or handles responses, and misunderstandings about provider behavior—not on testing provider functionality."
- **Si-Chip application**: Pact 的 "as loose as possible" 已经在 v0.3.0 §14.2.1 freeze constraint #2 (`expected_shape` 必须是结构断言不是值断言) 落地。v0.4.0 应进一步采纳 Pact 的 **broker / verification flow**: 当 ability 的 production endpoint 变了 (e.g. ai-bill 后端 schema 漂移)，msw fixture 在 spec §19 下会自动 re-verify，不通过 = round failure。这是 Pact 在 microservices world 的同源问题。

#### Source 2.2.d — MSW (Mock Service Worker) + Production Payload Pattern

- **URL** (no clone, web search synthesized): [https://docs.pact.io/implementation_guides/javascript/docs/consumer](https://docs.pact.io/implementation_guides/javascript/docs/consumer) (and Cycle 5 SUMMARY.md `feedback_for_v1.0.0.md` direct quote)
- **Excerpt** (from SUMMARY.md): "msw fixture provenance — every test fixture in this release uses the EXACT JSON shapes from the bug report's quoted samples. Test names cite 'real-data sample' so the audit trail is grep-able."
- **Si-Chip application**: chip-usage-helper Cycle 5 已经用 msw + production-payload fixture pattern 落地了 R45/R46。v0.4.0 spec §19 应 codify 这个 process：`feedback` template 加 `real_data_samples: [{endpoint, request_params, response_json, observed_state, captured_at, observer}]` 结构化块；implementing agent grep `tests/**/*.test.*` 中的 fixture name 必须命中 `real-data sample` 注释字面字符串以构成 audit trail。

### §2.3 Self-Iterating Systems & Bootstrap Loops

**Why this cluster matters for v0.4.0**: Si-Chip 的 8-step protocol 是 industry self-iterating-system pattern 的一种实例，本节确认 industry 给的同形态 implementations，意在为 v0.4.0 的 §3.4 token-tier 字段、R34 tier_transition 矩阵给一个理论锚定，**避免 v0.4.0 重新发明 self-iteration 机制**。(Maps to overall §8 8-step protocol justification + R34 tier transition as a "bootstrap delta".)

#### Source 2.3.a — DSPy BootstrapFewShot (Iterative Demo Bootstrap with Metric Threshold)

- **Path**: `/home/agent/reference/dspy/dspy/teleprompt/bootstrap.py:36-94, 148-170, 182-257`
- **Excerpt**: "max_rounds (int): Maximum number of bootstrap attempts per training example. Each round after the first uses a fresh rollout with `temperature=1.0` to bypass caches and gather diverse traces. If a successful bootstrap is found on any round, the example is accepted and the optimizer moves to the next one. ... metric_threshold (float, optional): If the metric yields a numerical value, then check it against this threshold when deciding whether or not to accept a bootstrap example."
- **Si-Chip application**: DSPy BootstrapFewShot 的 "max_rounds + metric_threshold + accept-or-reject per example" 与 Si-Chip 的 "round_kind=code_change + iteration_delta gate + per-round accept/reject" 是同形态 self-iteration 引擎。v0.4.0 应把 DSPy 的 `metric_threshold` 概念 lift 到 spec §15.4 promotion-counter 资格规则：当 ability 在某 metric 上展示 `metric_value >= bucket_threshold` 时计入 promotion counter；R32 EAGER-weighted iteration_delta 是 DSPy threshold 的 weighted 变体。

#### Source 2.3.b — DSPy GEPA (Reflective Prompt Evolution)

- **URL**: `https://dspy.ai/api/optimizers/GEPA` + `https://dspy.ai/api/optimizers/BootstrapFewShot`
- **Excerpt**: "GEPA operates through iterative cycles: replays traces from minibatch evaluation, summarizes feedback from metrics and optional predictor-level hooks, uses a reflection LM to propose improved instructions, accepts or rejects candidates using Pareto dominance on score and novelty. Unlike traditional RL methods that collapse execution traces into scalar rewards, GEPA uses LLMs to read full execution traces—including error messages, profiling data, and reasoning logs—to diagnose failures and propose targeted fixes."
- **Si-Chip application**: GEPA 的 "Pareto dominance on score and novelty" 与 Si-Chip §6 `value_vector` 的 "≥1 axis improvement" 是 sibling 工艺，但 GEPA 加了 **textual feedback 双层** (predictor-level + system-level) 与 **Pareto novelty**。v0.4.0 不应该在本 ship 引入 Pareto + LM-based reflection（那是 v0.5.0+ 的种子），但 spec §8 step 4 `improve` 应该加 forward-pointer 注释 "future v0.5+ may extend `next_action_plan.actions` with `feedback_text` per primitive, drawing from GEPA-style reflection". Important negative: GEPA 用 LLM 跑 reflection，那是允许的 router workflow（§5.1 #3 "description optimization"），但**绝对不允许 train router model**（§11 forever-out）。

#### Source 2.3.c — ACE (Agentic Context Engine) Skillbook 三角色

- **Path**: `/home/agent/reference/agentic-context-engine/CLAUDE.md` + `/home/agent/reference/agentic-context-engine/ace/skillbook.py` + `/home/agent/reference/agentic-context-engine/README.md`
- **Excerpt** (CLAUDE.md): "**ACE Roles**: **Agent** Executes tasks using skillbook strategies. **Reflector** Analyzes execution results. **SkillManager** Updates the skillbook with new strategies." (skillbook.py L24-L35): `@dataclass class Skill: id: str / section: str / content: str / justification: Optional[str] = None / evidence: Optional[str] = None / helpful: int = 0 / harmful: int = 0 / neutral: int = 0`. (README.md L22-L26): "ACE enables AI agents to **learn from their execution feedback**—what works, what doesn't—and continuously improve. ... **Self-Improving** / **20-35% Better Performance**: Proven improvements on complex tasks / **49% Token Reduction**: Demonstrated in browser automation benchmarks / **No Context Collapse**: Preserves valuable knowledge over time"
- **Si-Chip application**: ACE 把 self-iteration 拆成三个 atomic 角色 (Agent / Reflector / SkillManager) 并把 `Skill` 加 `helpful/harmful/neutral` 计数。这告诉我们 v0.4.0 的 §20 lifecycle machinery 字段应该 **加 helpful/harmful/neutral signal counters** 到 `BasicAbility.lifecycle` —— 它们是 R6.4 reactivation triggers 的 quantitative 输入（"用户手动调用频率回升 30 天 ≥ 5 次" 直接对应 ACE 的 `helpful++`）。ACE 的 SimilarityDecision (KEEP) artifact 也对应 R17 promotion_history 的 explicit transition record。**ACE measured impact** (20-35% better task performance + 49% token reduction in browser automation) 提供了 independent industry 证据：chip-usage-helper Cycle 2-3 的 -55% EAGER / -33% first-run-total 是 **同一数量级**的 token-economy 改善 —— 这不是 Si-Chip 孤例，而是 self-iterating systems 普遍观察到的 compression 红利。v0.4.0 plan 可据此 justify §18 token-tier 的 Normative 优先级（与 ACE 一致：token reduction 与 performance improvement 不是 trade-off，两者同向共进）。

#### Source 2.3.d — OpenSpec Change-Driven Workflow

- **Path**: `/home/agent/reference/openspec/docs/concepts.md` + `/home/agent/reference/openspec/docs/workflows.md`
- **Excerpt** (concepts.md): "**Specs** are the source of truth — they describe how your system currently behaves. **Changes** are proposed modifications — they live in separate folders until you're ready to merge them... When archived, changes move to `changes/archive/` with their full context preserved." (workflows.md): "/opsx:apply ──► /opsx:verify ──► /opsx:archive ... `/opsx:verify` validates implementation against your artifacts across three dimensions: COMPLETENESS / CORRECTNESS / COHERENCE."
- **Si-Chip application**: OpenSpec 的 propose → apply → archive 与 Si-Chip 的 `code_change → measurement_only → ship_prep` round_kind sequence 是同形态 lifecycle。OpenSpec 的 "verify before archive" three-dimension check (completeness / correctness / coherence) 直接对应 Si-Chip §8 step 8 packaging-gate 应该执行的硬检查（R47 health_smoke_check 是 correctness check 的一种）。OpenSpec 的 ADDED/MODIFIED/REMOVED delta semantics 是 R34 tier_transitions 的 industry 工艺：spec 不应该只看 final state，而应该看 transitions。

### §2.4 Lifecycle State Machines & Stage Transitions

**Why this cluster matters for v0.4.0**: spec §2.2 stage enum (`exploratory → evaluated → productized → routed → governed ↘ half_retired ↺ ↘ retired`) 列了 7 个状态但 spec 当前**没说什么时候 advance**。chip-usage-helper Round 8 把 stage 从 `evaluated` bumps 到 `routed` 是基于 "router_floor 已绑 + v3_strict 全部通过" 的 ad-hoc 决策，不是基于 spec 规则。R15 ("stage_transition_rules") + R17 ("promotion_history") + R27 ("ship_decision.yaml") 是同一个 lifecycle-machinery gap 的三个面。(Maps to R15, R17, R27.)

#### Source 2.4.a — OpenSpec Archive Process

- **Path**: `/home/agent/reference/openspec/docs/concepts.md`
- **Excerpt**: "1. **Merge deltas.** Each delta spec section (ADDED/MODIFIED/REMOVED) is applied to the corresponding main spec. 2. **Move to archive.** The change folder moves to `changes/archive/` with a date prefix for chronological ordering. 3. **Preserve context.** All artifacts remain intact in the archive."
- **Si-Chip application**: OpenSpec 的 archive 是 explicit state transition + metadata preservation 的 gold standard：archive 触发 = (a) 所有 deltas 合入 source-of-truth；(b) folder 物理移动；(c) date prefix 排序保留可审计性。v0.4.0 应对 Si-Chip lifecycle stage transitions 仿造同样的工艺：每次 stage 变化触发一条 `promotion_history.yaml` append-only 记录，包含 `from_stage / to_stage / triggered_by_metric / triggered_by_round_id / observer / archived_artifact_path`。这给 readers 一个可重放的 stage history 而不是当前的 ad-hoc 决策。

#### Source 2.4.b — inspect_ai Task Lifecycle (Sample → Solver → Scorer)

- **Path**: `/home/agent/reference/inspect_ai/src/inspect_ai/` (CLAUDE.md + dataset/_dataset.py)
- **Excerpt** (CLAUDE.md): "**Async Concurrency**: Use `inspect_ai._util._async.tg_collect()` instead of `asyncio.gather()` for running concurrent async tasks. Use `inspect_ai.util.collect()` only inside sample subtasks (it adds transcript span grouping)."
- **Si-Chip application**: Inspect AI 的 task pipeline (Dataset → Sample → Solver → Scorer → log) 是 well-formed lifecycle 工艺 —— 每个 stage 都有显式的 transcript span。v0.4.0 应给 Si-Chip 的 8-step protocol 加同样的 transcript span observability（每步 emit OTel span 带 `gen_ai.client.operation.duration` + `gen_ai.tool.name`），让 stage transition 可被 distributed tracing 工具 ingestion。这与 §3.2 frozen constraint #3 "数据源优先 OTel attribute" 相容，是 R6 D6 latency 度量的扩展。

#### Source 2.4.c — Feature lifecycle / state machine API patterns (web)

- **URL** (web search): General industry patterns for "feature lifecycle stage machine" — best representative: [https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge](https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge)
- **Excerpt**: "Run a minimal but critical set of checks: can the service start, is the main page loading, are core routes reachable? Execute one 'read' path (GET critical resource), one 'write' path (POST create + GET verify), one auth-protected flow, and one dependency touch. ... Produce an auditable pass/fail record with links to logs."
- **Si-Chip application**: Feature lifecycle gating in production systems uses 4-axis smoke (read / write / auth / dependency) + auditable pass/fail records. v0.4.0 should adopt this 4-axis discipline for `package-register` (§8 step 8): the smoke must verify (a) 6 evidence files emit; (b) artifact mirror sync OK; (c) installer permission scope unchanged; (d) `health_smoke_check` endpoints respond per R47. Each smoke result is an entry in `promotion_history.yaml`, giving Si-Chip the same auditable trail OpenSpec gets via archive folders.

### §2.5 Eval Pack Curation & Honest Measurement

**Why this cluster matters for v0.4.0**: chip-usage-helper Round 1 的 R3 = 0.7778 → 0.9524 跳变全部来自 evaluator 方法学修正（CJK substring + 40-prompt curated pack），**不是** ability 改善。R25 "eval_pack_qa_checklist.md" 是要把这个 30-min 隐蔽坑变成 5-min 显式 checklist。R3 (40-prompt minimum), R14 (G1 provenance), R36 (tokens_estimate_method) 是 eval-pack 工艺的三个面。(Maps to R3, R14, R36.)

#### Source 2.5.a — OpenAI Evals Registry (Versioned eval_sets)

- **Path**: `/home/agent/reference/evals/evals/registry/eval_sets/chinese-numbers.yaml` + `/home/agent/reference/evals/evals/registry/evals/2d_movement.yaml`
- **Excerpt** (2d_movement.yaml): `2d_movement: id: 2d_movement.dev.v0 / description: ... / metrics: [accuracy] / 2d_movement.dev.v0: class: evals.elsuite.basic.includes:Includes / args: samples_jsonl: 2d_movement/samples.jsonl`. (chinese-numbers.yaml): `chinese-numbers: evals: [convert_chinese_lower_case_num_to_num, ...]`
- **Si-Chip application**: OpenAI Evals 的 `id: <name>.dev.v0` 是 versioned 命名（dev/test/v0/v1...），eval_sets 是 evals 的命名集合。v0.4.0 应把 `core_goal_test_pack.yaml` + `eval_pack.yaml` 的 frontmatter 加同样的 `version: <ability>.<stage>.v<N>` 字段（与 §14.1.1 已有的 `core_goal_version` 字段并存），让 packs 在 ability 演化中可被 reference。这也支持 R25 的 "eval pack QA checklist" 工艺：checklist 自身 is a versioned pack reference document。

#### Source 2.5.b — Inspect AI Sample provenance (`metadata` first-class)

- **Path**: `/home/agent/reference/inspect_ai/src/inspect_ai/dataset/_dataset.py:81-83`
- **Excerpt**: `metadata: dict[str, Any] | None = Field(default=None) / """Arbitrary metadata associated with the sample."""`
- **Si-Chip application**: Inspect AI 把 `metadata` 放在 Sample top-level 是 R14 G1 provenance ("provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}") 的直接工艺。v0.4.0 应在 `metrics_report.yaml` 的每个 metric value 旁边加 `_method` field（e.g. `G1_method: deterministic_simulation`），同样把 provenance first-class 化。This 与 R36 `tokens_estimate_method ∈ {tiktoken, char_heuristic, llm_actual}` 是同一工艺的 D2 dimension 应用。

#### Source 2.5.c — MLPerf Submission Rules (Reproducibility + No Benchmark Detection)

- **URL**: [https://github.com/mlperf/policies/blob/master/submission_rules.adoc](https://github.com/mlperf/policies/blob/master/submission_rules.adoc) + [https://docs.mlcommons.org/inference/submission/](https://docs.mlcommons.org/inference/submission/)
- **Excerpt**: "Replicability is mandatory: Results that cannot be replicated are not valid results... All valid submissions of a benchmark must be equivalent to the reference implementation... Benchmark detection is not allowed: Systems should not detect and behave differently for benchmarks." Plus: "All random numbers must use fixed random seeds with the Mersenne Twister 19937 generator, with random seeds announced four weeks before the submission deadline."
- **Si-Chip application**: MLPerf 把 reproducibility + reference-implementation-equivalence 写成 submission gate；v0.3.0 §14.2.1 freeze constraint #5 (no benchmark detection) 已经 echoed 这一原则。v0.4.0 应进一步采纳 MLPerf 的 **fixed-seed** 工艺：spec §3.2 frozen constraint 应加 #5 "deterministic eval simulators MUST seed with `hash(round_id + ability_id)` to ensure metric replayability"。这给 R20 L4_max + L4_mean、R36 tokens_estimate_method 等多变 measurement 一个 reproducibility floor。

#### Source 2.5.d — DSPy `metric_threshold` (numerical metric quality control)

- **URL**: [https://dspy.ai/api/optimizers/BootstrapFewShot](https://dspy.ai/api/optimizers/BootstrapFewShot) + path `/home/agent/reference/dspy/dspy/teleprompt/bootstrap.py:74-79`
- **Excerpt**: "`metric_threshold (float, optional)`: If the metric yields a numerical value, then check it against this threshold when deciding whether or not to accept a bootstrap example. Defaults to None."
- **Si-Chip application**: DSPy `metric_threshold` 是 "numerical metric quality control" 工艺：only accept bootstrap example if `metric >= threshold`. v0.4.0 应把同样工艺 lift 到 §22 eval pack curation：每个 case 在 `core_goal_test_pack.yaml` 应该有 `weight: float` (already in v0.3.0 §14.2 schema) + 新加 `acceptance_threshold: float` field —— deterministic simulator 跑出来 < threshold 的 case 自动 fail (而不是依赖外层逻辑判断)。This 给 Round 12-13 precedent 加了一道 spec-level 拦截。

### §2.6 Healthcheck & Production-Smoke Patterns

**Why this cluster matters for v0.4.0**: chip-usage-helper Cycle 5 的 v0.9.0 zero-events bug 把 Si-Chip 的 spec gap 暴露在 production-side: 当 ability 依赖 live backend (ai-bill `/events/health`)，spec §8 的 8-step protocol 没有 production smoke check —— ability 可以 ship-eligible 但 backend 已经空的情况下 dashboard 静默崩。R47 是这个 gap 的明确 fix。(Maps to R47.)

#### Source 2.6.a — GitHub Actions URL Health Check

- **URL**: [https://github.com/marketplace/actions/url-health-check](https://github.com/marketplace/actions/url-health-check)
- **Excerpt** (web): "Uses cURL for simple endpoint verification with built-in retry and redirect handling. Fails on 4xx or 5xx status codes, supports max-attempts, retry-delay, cookies, and basic auth."
- **Si-Chip application**: GitHub Actions URL Health Check 是 ship-pipeline production smoke 的最小 reference impl。v0.4.0 §21 `health_smoke_check` 字段应该模仿这个最小 schema：`endpoints: [{url, expected_status, max_attempts, retry_delay_ms, sentinel_field, sentinel_value_predicate}]`。chip-usage-helper R47 的 `latestTsMs > 0` sentinel 直接对应 `sentinel_field=latestTsMs, sentinel_value_predicate=">0"`。This is a primitive but effective dual-axis check (HTTP success + payload non-emptiness)。

#### Source 2.6.b — Post-deploy verification 4-axis smoke pattern

- **URL**: [https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge](https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge) + [https://medium.com/@deryayildirimm/deploying-to-render-insert-a-smoke-test-step-with-github-actions-ffbd49a104dd](https://medium.com/@deryayildirimm/deploying-to-render-insert-a-smoke-test-step-with-github-actions-ffbd49a104dd)
- **Excerpt** (fitgap): "Execute one 'read' path (GET critical resource), one 'write' path (POST create + GET verify), one auth-protected flow, and one dependency touch (queue publish or cache read). ... Produce an auditable pass/fail record with links to logs."
- **Si-Chip application**: 4-axis smoke (read / write / auth / dependency) 给了 v0.4.0 §21 一个 spec-level structure: `health_smoke_check` 的每个 endpoint 应该有 `axis ∈ {read, write, auth, dependency}` field 让 packaging gate 可以检查 "至少一个 dependency-axis check 存在"（chip-usage-helper 的 ai-bill check 就是 dependency-axis）。Auditable pass/fail record 直接写入 §10 `.local/dogfood/.../raw/health_smoke_results.yaml`，供 §6.4 reactivation triggers 复检。

#### Source 2.6.c — OpenTelemetry GenAI semconv (Operation Duration + Token Usage)

- **URL**: [https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics) + [https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md)
- **Excerpt**: GenAI metrics 包括 `gen_ai.client.operation.duration`, `gen_ai.client.token.usage` 是 spec §3.2 frozen constraint #3 already-declared 数据源；GenAI agent spans 是 multi-step agent execution 的 standard transcript shape。
- **Si-Chip application**: OpenTelemetry 没有专门的 healthcheck semconv，但 GenAI semconv 已经覆盖了 Si-Chip 8-step protocol 中每步的 OTel attribute 命名。v0.4.0 应把 §21 health_smoke_check 的 OTel-emit 接到 `gen_ai.tool.name=si-chip.health_smoke / mcp.method.name=health_check / gen_ai.system=<ability_id>`。这让 health smoke 与 ability 的其它 telemetry **流入同一 trace pipeline**，readers 不需要 inspect 多个 span source 就能 reconstruct ship 决策。**Honest negative result**: web search 直接搜 "OpenTelemetry health probe" / "Kubernetes liveness probe" 与 GenAI semconv 没有 overlap；这是 v0.4.0 应该 leave 给 Kubernetes ecosystem 而不是写进 spec 的边界（per §11 "通用 IDE / Agent runtime 兼容层" forever-out 的精神延伸）。

---

## 3. Crosswalk: R-Items × Industry Sources × Proposed v0.4.0 Spec Section

> Master table (15 rows; each P0/P1 R-item gets at least one row).


| R#  | Cluster                             | Primary industry source                                                                   | Proposed v0.4.0 spec section                                                                                                                                             | Effort |
| --- | ----------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| R30 | token_economy                       | Anthropic Skill 3-tier disclosure (Metadata/Instructions/Resources)                       | NEW §18 Token-Tier Invariant — adds C7/C8/C9 as **top-level** dimension (NOT R6 D2 sub-metrics; same placement as §14 C0)                                                | M      |
| R32 | token_economy                       | DSPy MIPROv2 demonstration budget + Cursor "5-15 rules <3000 tokens"                      | extends §4.1 row 10 — `weighted_token_delta = 10×eager_delta + 1×oncall_delta`; new add-on sentence on §4.1 footer                                                       | S      |
| R33 | token_economy + measurement_quality | Anthropic skill description vs SKILL body distinction                                     | extends §3.1 D6 R3 — split to `R3_eager_only` + `R3_post_trigger`; Normative add 2 prose lines to §3.1 D6 row                                                            | S      |
| R34 | token_economy                       | OpenSpec ADDED/MODIFIED/REMOVED delta semantics                                           | extends `templates/iteration_delta_report.template.yaml` additively — adds `tier_transitions: [{from, to, tokens, reason, net_benefit}]` block; spec §9 add-on table row | M      |
| R37 | token_economy                       | Anthropic best-practices "Set Appropriate Degrees of Freedom" + Karpathy three-layer wiki | NEW §18.4 — declares `prose_class ∈ {trigger, contract, recipe, narrative}` 工艺 in `SKILL.md` section annotation (Informative @ v0.4.0; promote Normative @ v0.4.x)       | M      |
| R41 | token_economy + packaging           | Anthropic Resource tier "loaded on demand"                                                | NEW §18.5 — `templates/lazy_manifest.template.yaml` schema; `templates/<ability>/.lazy-manifest` becomes packaging-gate sentinel                                         | M      |
| R42 | token_economy                       | Static analyzer pattern (server default vs client cap)                                    | extends `tools/eval_skill.py` — adds template-default-data anti-pattern detector helper; spec §9 unchanged                                                               | S      |
| R45 | real_data_verification              | Pact "as loose as possible" + tau-bench real-dialogue                                     | NEW §19 Real-Data Verification — adds 9th step (sub-step of §8.1 step 4 `improve` — see §5 Open Q2 for placement debate)                                                 | L      |
| R46 | real_data_verification              | Inspect AI Sample.metadata + msw fixture pattern                                          | NEW `templates/feedback_real_data_samples.template.yaml`; spec §9 add-on table row + `feedback` template extension                                                       | M      |
| R47 | healthcheck                         | GitHub Actions URL Health Check + 4-axis smoke (read/write/auth/dep)                      | NEW §21 `BasicAbility.packaging.health_smoke_check` field + §8 step 8 packaging-gate add-on; OTel semconv extension `gen_ai.tool.name=si-chip.health_smoke`              | L      |
| R15 | lifecycle_machinery                 | OpenSpec stage-gates + ACE Skillbook helpful/harmful counters                             | NEW §20.1 stage_transition_rules — adds Normative table for each `from_stage → to_stage` with required-conditions; explicit advance / regression triggers                | M      |
| R17 | lifecycle_machinery                 | OpenSpec archive `changes/archive/<date>/` semantics                                      | NEW §20.2 `BasicAbility.lifecycle.promotion_history: [{from, to, triggered_by, round_id, observer, archived_artifact_path}]` append-only block                           | S      |
| R27 | lifecycle_machinery                 | OpenSpec `verify` 3-dim check (completeness/correctness/coherence)                        | extends §8.2 evidence file count 6 → 7 — adds `ship_decision.yaml` as 7th evidence file when `round_kind=ship_prep` (only)                                               | M      |
| R3  | measurement_quality                 | MLPerf submission_rules + OpenAI Evals versioned eval_sets                                | extends §5.3 router-test harness — "MVP=20 prompts; 40+ recommended for v2_tightened promotion decisions"; spec note in §5.3 Normative table                             | S      |
| R14 | measurement_quality                 | Inspect AI Sample.metadata first-class                                                    | extends §3.1 D4 G1 — adds `provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` REQUIRED field; spec §3.1 D4 row revised                                      | S      |
| R25 | measurement_quality                 | OpenAI Evals registry + DSPy metric_threshold                                             | NEW `templates/eval_pack_qa_checklist.md` (Informative reference doc); spec §9 add-on table row                                                                          | S      |
| R31 | token_economy + packaging           | Anthropic best-practices "challenge each piece of information"                            | extends `tools/eval_skill.py` — adds MCP `text` channel pretty-vs-compact static check; spec §9 unchanged                                                                | S      |
| R36 | measurement_quality                 | DSPy MIPROv2 explicit budget docs                                                         | extends §3.1 — adds `<metric>_method ∈ {tiktoken, char_heuristic, llm_actual}` + `confidence_interval` fields to relevant tokens metrics                                 | M      |
| R6  | lifecycle_machinery                 | OpenSpec `/opsx:verify` 3-dim check                                                       | extends `templates/iteration_delta_report.template.yaml` — adds `promotion_state: {current_gate, consecutive_passes, promotable_to}` block                               | S      |
| R8  | measurement_quality                 | DSPy BootstrapFewShot rounds + retry pattern                                              | NEW `templates/recovery_harness.template.yaml` — 4-scenario branch test schema for T4 `error_recovery_rate`; spec §9 add-on table row                                    | M      |


**Effort legend**: S = 1-3 days; M = 3-7 days; L = 1-2 weeks.

---

## 4. Cluster-by-cluster v0.4.0 theme proposals

### §4.1 Token Economy theme (P0 cluster)

**Lands in v0.4.0**: NEW `§18 Token-Tier Invariant` (Normative) introducing `C7_eager_per_session`, `C8_oncall_per_trigger`, `C9_lazy_avg_per_load` as **top-level invariants** (NOT R6 D2 sub-metrics — see §5 Open Q1 for placement debate). The §18 schema extends `metrics_report.yaml` with a top-level `token_tier` block parallel to `core_goal` (R30 + Anthropic 3-tier disclosure precedent §2.1.b). New `templates/lazy_manifest.template.yaml` schema (R41 + Anthropic Resource tier "loaded on demand" precedent §2.1.b) — packaging-time check ensures LAZY siblings never enter EAGER/ON-CALL path. `templates/iteration_delta_report.template.yaml` extended additively with `tier_transitions` block (R34 + OpenSpec ADDED/MODIFIED/REMOVED delta semantics precedent §2.3.d). `tools/eval_skill.py` extended with three new helpers: token-tier decomposition (R30), MCP-pretty static check (R31), template-default-data anti-pattern detector (R42). New §15 sibling field `token_tier_target ∈ {relaxed, standard, strict}` lets ability declare per-round token-budget pressure (DSPy MIPROv2 light/medium/heavy precedent §2.1.d). NEW §17.4 hard rule 11: "MUST declare `token_tier` block when any C7/C8/C9 measurement axis is reported".

**Stays out of scope** (deferred to v0.4.x or v0.5.0+): per-prose-class enforcement (R37 promoted Normative — Informative @ v0.4.0; promote when 2+ abilities show `prose_class` annotations in production); zod-based routing test contract (R40 — TS-only; per-ecosystem); pointer-to-sibling resilience (R38 — packaging-guide reference, not Normative); rule-body 400-token Normative threshold (R44; ship as Cursor-platform guideline in §7.3 packaging-gate footer, not as a Normative threshold — Cursor docs §2.1.c give us the 5-15-rules-<3000-tokens budget envelope at platform level, not at ability level).

**Additivity discipline**: §3 / §4 / §5 / §6 (with one exception per §5.4 Q4) / §7 / §8 / §11 / §14 / §15 byte-identical to v0.3.0. §3.1 R6 7×37 frozen count unchanged (C7/C8/C9 are top-level invariants, NOT D2 sub-metrics 7-9; see §5 Open Q1 for the type-system rationale parallel to §14.5 C0 placement). §4.1 row 10 gets ONE "v0.4.0 add-on" sentence about EAGER-weighting; otherwise unchanged. New §18 sits between §17 and §18-of-future-v0.5+; §18 contains §18.1 schema, §18.2 EAGER-weighted iteration_delta clause, §18.3 R3 split (eager_only / post_trigger), §18.4 prose_class taxonomy (Informative), §18.5 lazy_manifest packaging gate.

### §4.2 Real-Data Verification theme (P0 cluster)

**Lands in v0.4.0**: NEW `§19 Real-Data Verification` (Normative) inserts a sub-step into §8.1 step 2 (`evaluate`) — see §5 Open Q2 for "9th step vs `evaluate` sub-step" debate; recommendation defaults to **sub-step of `evaluate`** to preserve §8.1 8-step frozen count (additivity discipline). The §19 sub-step is structured around the chip-usage-helper Cycle 5 three-layer pattern: (a) **msw fixture provenance** — every test fixture in the release uses the EXACT JSON shape from a bug report's quoted samples; test names cite the provenance label ("real-data sample" + `captured_at` + `observer`) so the audit trail is grep-able (Pact "as loose as possible" §2.2.c precedent + Inspect AI Sample.metadata §2.2.a precedent); (b) **user install verification** — branch is pushed; user installs the tarball; user manually verifies the user-observable behavior under the production state; (c) **post-recovery live verification** — when the live backend recovers, append a "verified-with-live-data" note to the ship_decision (or maintenance round artifact). NEW `templates/feedback_real_data_samples.template.yaml` schema with `[{endpoint, request_params, response_json, observed_state, captured_at, observer}]` provides the structured field bug-report agents fill in (R46). spec_validator gets new BLOCKER `REAL_DATA_FIXTURE_PROVENANCE` (12th BLOCKER total): when ability has `real_data_samples` declared, every test fixture file under that ability MUST contain a comment `// real-data sample provenance: <captured_at> / <observer>` so the audit trail is grep-able. NEW §17.5 hard rule 12: "MUST cite real-data sample provenance in test fixture filenames or in-file comments when ability has `real_data_samples` declared".

**Stays out of scope**: real-LLM end-to-end runner (deferred from v0.2.0 already; remains v0.4.0+ deferred per §5 Open Q5); user-install verification automation (Cycle 5 chose manual `all_three`; codify pattern but no automation pipeline — automation is v0.5.0+ when 2+ abilities have `health_smoke_check` + post-deploy infra); cross-ability fixture broker (would touch §11 marketplace boundary; explicitly out per §7).

**Additivity discipline**: §8.1 8 steps remain byte-identical (`evaluate` gets a NEW Normative sub-step §19 listed in §8.1 expansion table; the 8 enumerated step names don't change). §8.2 evidence file count unchanged at 6 (per §4.3 the count goes 6 → 7 conditional on `round_kind=ship_prep` — that's a separate change driven by R27, not by §19). §11 forever-out unaffected (real-data is testing not distribution; §7 explicit re-check confirms).

### §4.3 Lifecycle State Machine theme (P0 cluster)

**Lands in v0.4.0**: NEW `§20 Stage Transitions & Promotion History` (Normative). §20.1 introduces a `stage_transition_table` declaring **required conditions for each transition** in the §2.2 stage enum DAG (`exploratory → evaluated`: requires eval_set + no_ability_baseline + 7-dim basic metrics; `evaluated → productized`: requires stable steps in script/CLI/MCP/SDK + ≥2 v1_baseline-row-complete passes; `evaluated → routed`: requires `router_floor` bound + ≥3 v3_strict-row-complete passes; `productized → routed`: requires `router_floor` bound; `routed → governed`: requires owner + version + telemetry + deprecation_policy listed; `* → half_retired`: requires §6.2 value_vector trigger + spec-compliant `half_retire_decision.yaml`; `half_retired → evaluated` (reactivation): requires §6.4 reactivation trigger AND C0 = 1.0 against current run AND pack hash unchanged from half_retire moment per §14.7; `* → retired`: requires §6.2 retire trigger). §20.2 introduces append-only `BasicAbility.lifecycle.promotion_history: [{from, to, triggered_by_round_id, triggered_by_metric_value, observer, archived_artifact_path, decision_rationale}]` block (OpenSpec `changes/archive/<date>-<change-name>/` precedent §2.4.a). §20.3 declares `metrics_report.yaml.promotion_state: {current_gate, consecutive_passes, promotable_to, last_promotion_round_id}` first-class top-level key (R6). §8.2 evidence file count 6 → 7 — `ship_decision.yaml` becomes the 7th evidence file **when `round_kind=ship_prep`** (R27); when `round_kind ∈ {code_change, measurement_only, maintenance}` evidence count remains 6. NEW `templates/ship_decision.template.yaml` schema. NEW §17.6 hard rule 13: "MUST emit `ship_decision.yaml` (the 7th evidence file) when `round_kind=ship_prep`".

**Stays out of scope**: ACE-style `helpful/harmful/neutral` counters as Normative (Informative reference only — see §5 Open Q6; v0.5.0+ if 2+ abilities show usage-frequency-driven reactivation evidence). DSPy GEPA-style novelty-bonus axis (per §5 Open Q7; Informative §17.3 forward-pointer only; not a v0.4.0 spec field).

**Additivity discipline**: §2.1 yaml main block byte-identical (additively extended with `lifecycle.promotion_history` block). §6.4 reactivation triggers unchanged (the 6 existing triggers carry forward; §20.1 `half_retired → evaluated` row references them by ID). §8.1 8-step block byte-identical; only §8.2 evidence count changes (6 → 7 conditional on `round_kind`). spec_validator gets revised `EVIDENCE_FILES` BLOCKER: when `next_action_plan.round_kind == 'ship_prep'`, evidence count MUST be 7 with `ship_decision.yaml` present; otherwise evidence count MUST be 6.

### §4.4 Healthcheck Field theme (P0 cluster)

**Lands in v0.4.0**: NEW `§21 Health Smoke Check` (Normative). `BasicAbility.packaging.health_smoke_check: [{endpoint, expected_status, max_attempts, retry_delay_ms, sentinel_field, sentinel_value_predicate, axis ∈ {read, write, auth, dependency}, description}]` optional field (REQUIRED when ability declares any `current_surface.dependencies.live_backend: true`). The 4-axis enum (read/write/auth/dependency) directly inherits from the post-deploy verification 4-axis pattern §2.6.b — chip-usage-helper R47 ai-bill `events/health` is `axis: dependency`; a future ability that creates resources is `axis: write`. `tools/eval_skill.py` extended with `health_smoke` runner that performs HTTP probe + sentinel field/predicate verification + writes to `.local/dogfood/.../raw/health_smoke_results.yaml`. §8 step 8 `package-register` extended with **packaging-gate hard check**: ship-eligible declaration requires `health_smoke_check` either (a) absent (no live backend deps declared in `current_surface.dependencies.live_backend`) or (b) all declared axes PASS at packaging time. OTel semconv extension: each smoke probe emits `gen_ai.tool.name=si-chip.health_smoke / mcp.method.name=health_check / gen_ai.system=<ability_id>` for trace pipeline integration (§2.6.c GenAI semconv precedent + §3.2 frozen constraint #3 OTel-first datasource alignment). spec_validator gets new BLOCKER `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND` (13th BLOCKER total): when `current_surface.dependencies.live_backend: true`, `packaging.health_smoke_check` MUST be non-empty.

**Stays out of scope**: Kubernetes liveness/readiness probes (per §11 forever-out generalized — no IDE / runtime compat layer; the spec gives ability authors a probe schema but does not bind to any specific orchestrator API); periodic post-ship live-backend monitoring (that's the `maintenance` round in §15; v0.4.0 spec doesn't introduce continuous monitoring infrastructure); cross-ability shared health-probe library (would touch §11 marketplace — explicit out per §7).

**Additivity discipline**: §7 packaging gate gets ONE "v0.4.0 add-on" sentence about pre-ship health_smoke verification; §8.1 step 8 gets ONE "v0.4.0 add-on" sentence about the same. No change to §3 / §4 / §5 / §6 / §11 / §14 / §15. New §21 sits alongside §18-§20; spec section count grows from 17 (v0.3.0) to 23 (v0.4.0) — this is a **section count bump** (17 → 23) which requires reconciliation log entry similar to the v0.2.0 → v0.3.0 jump (13 → 17).

### §4.5 Eval-Pack Curation theme (P1 cluster)

**Lands in v0.4.0**: NEW `templates/eval_pack_qa_checklist.md` (Informative reference doc) — modeled after the superpowers/skills `writing-skills` SKILL.md format §2.5.b precedent (TDD for skills — RED/GREEN/REFACTOR mapped to baseline-fail / write-pack / close-loopholes). Checklist sections include: bilingual coverage (bilingual prompts in 50/50 ratio when ability targets CJK speakers), near-miss curation (2-5 negatives per positive trigger, including the "spend time" negative discriminator class chip-usage-helper Round 1 surfaced), anti-patterns to avoid (naive `\w+` tokenization for CJK, single-language packs, over-trivial prompts, benchmark detection per MLPerf §2.5.c), 40-prompt minimum gate, fixed-seed determinism for replayability. spec §5.3 router-test harness Normative table gets ONE add-on sentence: "MVP=20 prompts; 40+ recommended for v2_tightened promotion decisions" (R3). spec §3.1 D4 G1 row revised additively to mark `provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` REQUIRED first-class field (R14 + Inspect AI Sample.metadata §2.5.b precedent). NEW `templates/recovery_harness.template.yaml` for T4 `error_recovery_rate`: standardizes the 4-scenario branch test pattern (`{match, one-candidate, no-candidate, multi-candidate}` for identity; `{success, expected_failure, recoverable_failure, unrecoverable_failure}` for tool calls) — R8 + DSPy BootstrapFewShot retry pattern §2.5.d precedent. spec §3.2 frozen constraint gets new constraint #5 "deterministic eval simulators MUST seed with `hash(round_id + ability_id)`" (R20 reproducibility floor; same logic as MLPerf Mersenne Twister §2.5.c). NEW `templates/method_taxonomy.template.yaml` enumerating allowed `_method` values per metric — referenced by §4.6 Method-Tagged Metrics theme.

**Stays out of scope**: real-LLM cross-model G1 sweep automation (v0.4.0+ deferred; same as v0.2.0+ deferred — see §5.5 Q5); pass_k jitter helper (R21 — ship as Informative guidance in `eval_pack_qa_checklist.md`, not Normative); promotion of "eval_pack_qa_checklist" to Normative (Informative @ v0.4.0; promote @ v0.5.0 if 2+ abilities adopt).

**Additivity discipline**: §3.2 frozen constraints go from 4 → 5 (additive; existing 4 byte-identical). §3.1 D4 G1 prose changes — this is a content modification, not byte-identical preservation, so requires careful reconciliation log entry (similar to v0.2.0 → v0.3.0 §13.5 add-on subsection pattern). §3.1 R6 7×37 count unchanged. §5.3 Normative table preserved byte-identical; only an add-on sentence below the table.

### §4.6 Measurement Honesty Toolkit theme (P1 cluster)

**Lands in v0.4.0**: NEW `§23 Method-Tagged Metrics` (Normative). All token-related metrics gain `_method` suffix companion fields: `C1_metadata_tokens` paired with `C1_metadata_tokens_method ∈ {tiktoken, char_heuristic, llm_actual}` (R36 + Inspect AI Sample.metadata §2.5.b precedent). `C7/C8/C9` (NEW from §18) inherit the same method tagging. `C0_core_goal_pass_rate` gains `_method ∈ {real_llm, deterministic_simulator}`. `G1_cross_model_pass_matrix._method` already covered by R14. Confidence band `_ci_low / _ci_high` for char-heuristic-derived token metrics: chip-usage-helper Round 17 R36 evidence shows char-based heuristic vs tiktoken differ 2-5% on individual surfaces and **2.4× on template-types-extract prediction** (1.9K predicted vs 786 actual) — without confidence intervals, round-on-round comparisons can be over-confident. U1 `language_breakdown: {en: <fk>, zh: <chars>, mixed_warning: bool}` field (R29; bilingual SKILL.md descriptions can't be fairly compared in FK-grade alone). U4 `state ∈ {warm, cold, semicold}` field (R19; `npm ci` from cold cache is 30-90s vs warm cache <2s — ambiguous metric value). R3 split into `R3_eager_only` and `R3_post_trigger` (R33 — already counted in §4.1 token economy theme; cross-listed here because it's also a measurement honesty primitive). NEW `templates/method_taxonomy.template.yaml` enumerating allowed `_method` values per metric — provides the controlled vocabulary spec_validator can check against.

**Stays out of scope**: bidirectional R8 description competition (R5; nice-to-have, ship as note in §3.1 D6 R8 row not as a measurement primitive); R8-with-0-neighbors=0.0 vs null (R13; trivial spec note in §3.1 D6 R8 row); path_efficiency saturation (R11; trivial spec note in §6.1 path_efficiency_delta row); L6=0 architecture rationale (R22; trivial spec note in §3.1 D3 L6 row); G1 cross-model real-LLM sweep (per §5.5 Q5 deferred to v0.4.1+). All these P2/P3 polish items can ship as a single "v0.4.0 measurement-quality polish" sub-cycle (one round) at v0.4.0-rc1 → v0.4.0 promotion time.

**Additivity discipline**: §3.1 R6 7×37 count unchanged (method-tags are companion fields, not new sub-metrics — same logic as §14 C0 placement and §18 token-tier placement). §3.2 frozen constraint #2 ("未实现项以 null 显式占位") relaxed for method-tag fields ONLY (method tags are derived from method actually used; no null-placeholder needed when corresponding metric is null). §4.1 threshold table unchanged. spec_validator gets revised `R6_KEYS` BLOCKER to accept companion `_method` / `_ci_low` / `_ci_high` keys without counting them toward the 37 sub-metric count.

### §4.7 Stage-2 Execution Roadmap (recommended sequencing for the plan author)

The 6 themes above are not equal-priority for v0.4.0 ship velocity. The plan author should consider the following sequencing to optimize for Stage 4 implementation parallelism + Stage 5 dogfood evidence accumulation:

**Stage 2 (Spec Authoring)**: Author all 6 NEW sections (§18, §19, §20, §21, §22, §23) in one rc1 spec drop (mirroring v0.3.0's "rc1 = §14 + §15 + §16 + §17 in one batch" pattern). This preserves the additivity-discipline coherence: spec readers see the full v0.4.0 surface area at once rather than a confusing series of mini-bumps. Reconciliation log entry must explicitly account for: (a) §6.1 value_vector 7 → 8 axes break (per §5.4 Q4); (b) §3.2 frozen constraints 4 → 5 (per §4.5); (c) §8.2 evidence files 6 → 7 conditional on round_kind (per §4.3); (d) §17 hard rules 10 → 13 (per §4.1 / §4.2 / §4.3); (e) total spec sections 17 → 23 (per §4.4); (f) §3.1 D4 G1 prose modification (not byte-identical — per §4.5).

**Stage 3 (Review)**: Independent read-back of §3 / §4 / §5 / §7 / §8 / §11 / §14 / §15 byte-identicality (only §6.1 deviates per Q4 decision; document the deviation explicitly). Cross-check §18-§23 internal consistency: §18 token-tier C7/C8/C9 must compose with §6.1 8-axis value_vector; §19 real-data sub-step must reference §22 eval_pack_qa_checklist; §20 promotion_history must reference §15 round_kind values. The §7 forever-out re-check is non-trivial because §18 (token-tier observability) and §21 (health smoke probe) both have "looks like distribution surface" smell — Stage 3 reviewer should explicitly walk through §7's argument.

**Stage 4 (Templates + Tooling)**: Implement 5 NEW templates (`lazy_manifest.template.yaml`, `feedback_real_data_samples.template.yaml`, `ship_decision.template.yaml`, `recovery_harness.template.yaml`, `method_taxonomy.template.yaml`) + Informative reference (`eval_pack_qa_checklist.md`). Extend 2 existing templates (`iteration_delta_report.template.yaml` adds `tier_transitions` block + 8-axis value_vector; `next_action_plan.template.yaml` adds `token_tier_target` field). Extend `tools/eval_skill.py` with token-tier decomposition + MCP-pretty static check + template-default-data anti-pattern detector + health_smoke runner (4 new helpers). Extend `tools/spec_validator.py` with 3 new BLOCKERs (`REAL_DATA_FIXTURE_PROVENANCE` / `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND` / `TOKEN_TIER_DECLARED_WHEN_REPORTED`) + revise `EVIDENCE_FILES` for 6/7 conditional logic + revise `R6_KEYS` to ignore method-tag suffixes + revise `VALUE_VECTOR` for 8-axis (per Q4 decision).

**Stage 5 (Round 16 dogfood `code_change`)**: Si-Chip self adopts 5 new templates; introduces token_tier block + health_smoke_check field + lifecycle.promotion_history block on its own basic_ability_profile.yaml; adopts 8-axis value_vector with eager_token_delta (initial value 0.0); migrates Round 1-15 evidence to schema_version 0.3.0 (additive — old fields remain compatible; new fields default null). Round 16 required: C0 = 1.0; v1_baseline all PASS; eager_token_delta or one of legacy 7 axes ≥ +0.05.

**Stage 6 (Round 17 dogfood `measurement_only`)**: Re-runs Si-Chip self-eval through extended `tools/eval_skill.py` to verify: (a) old 7-axis metrics byte-equivalent to Round 15; (b) new C7/C8/C9 token-tier values populated; (c) health_smoke_check (none for Si-Chip self) declared empty cleanly; (d) promotion_state {current_gate=v1_baseline, consecutive_passes=2, promotable_to=v2_tightened} populated. Required: C0 = 1.0; v1_baseline all PASS (carry-forward); no axis regression.

**Stage 7 (chip-usage-helper Round 26 cross-ability dogfood)**: chip-usage-helper adopts §19 real-data verification sub-step (already partially adopted in Cycle 5) + §20 promotion_history (chip-usage-helper has 5 cycles × promotion-events to backfill) + §21 health_smoke_check for ai-bill `events/health` endpoint. This is the **second-ability witness** that promotes §16 (multi-ability layout) from Informative to Normative — see §5 Open Q2 in r11. Required: C0 = 1.0; v3_strict all PASS; new health_smoke_check axis "dependency" PASS.

**Stage 8 (v0.4.0-rc1 → v0.4.0 promotion)**: rc → frozen flip (mirror v0.3.0-rc1 → v0.3.0 promotion); compile into `.rules/si-chip-spec.mdc`; AGENTS.md §13 hard rules grow 10 → 13; spec_validator BLOCKER count grows 11 → 14. **Estimated wall-clock**: ~15-25 days from Stage 2 start to v0.4.0 ship (vs v0.3.0's ~3-day single-day-burst sequence — v0.4.0 is materially heavier due to the 6 NEW sections vs v0.3.0's 4 NEW sections + heavier each).

**Critical scheduling risk**: §5.4 Q4 (value_vector 7 → 8) decision must land **before** Stage 2 spec authoring; otherwise the rc1 spec will require a mid-stage retrospective fix. Recommend: plan author resolves Q4 in a half-day "Stage 2-pre" decision review with L0 owner. Other open questions (Q1, Q2, Q3) can be resolved during Stage 2 authoring.

---

## 5. Open Questions for the Plan Author

> ≥ 5 honest unresolved tensions. Stage 2 plan author may agree or override; flagging is the contract.

### §5.1 Q1: Should `C7/C8/C9` token-tier sub-metrics break R6's frozen 7×37 count?

**Status**: §2.1 / §4.1 / §3 crosswalk row R30 all recommend top-level placement; this Q is the explicit decision document.

**Recap of §3 / r11 §3.4 logic**: R11 §3.4 chose "C0 as top-level invariant, NOT R6 D8 / 38th sub-metric" because (a) preserves §3.1 R6 7×37 byte-identical (additivity discipline); (b) C0 is binary (pass/fail), R6 sub-metrics are continuous; (c) C0 has special semantic ("failure regardless of other axes"), doesn't fit value_vector / iteration_delta machinery.

**The same logic for C7/C8/C9 partially applies**: tier-decomposition is continuous (token counts) so type-system mismatch is weaker. But C7 EAGER-paying-per-session has user-impact discontinuity (every session pays it forever) that C1 metadata_tokens doesn't capture — this is **ordinality not type** difference.

**My recommendation**: **Top-level `token_tier` invariant block** (mirroring §14 C0 placement; NOT R6 D2 sub-metrics 7-9). Key tie-breakers:

1. **Additivity discipline**: §3.1 R6 7×37 frozen count unchanged. Alternative ("C7/C8/C9 as D2.7/D2.8/D2.9") would require §3.1 D2 row revision and break v0.2.0 → v0.4.0 byte-identical preservation chain.
2. **EAGER-weighting compatibility**: Top-level placement lets §4.1 row 10 use `weighted_token_delta = 10×C7_delta + 1×C8_delta + 0.1×C9_delta` cleanly. Putting C7/C8/C9 inside R6 D2 would require §4.1 row 10 to special-case D2 sub-metrics, which is awkward.
3. **R6 metric-as-quality framing preserved**: R6 sub-metrics are "more / less / faster / slower" continuous quality scores. C7/C8/C9 token-tier decomposition is closer to **resource-budget partitioning** (different semantic class, like §14 C0's binary go/no-go).

**Alternative if Stage 2 disagrees**: If plan author wants to push C7/C8/C9 into R6 D2 (becoming D2 7-tier-eager / 8-tier-oncall / 9-tier-lazy sub-metrics), this requires (a) §3.1 R6 count moves 37 → 40; (b) §13.4 prose count anchor changes 37 → 40 (the same kind of reconciliation that v0.1.0 → v0.2.0 prose count "28 → 37" did); (c) `EXPECTED_R6_PROSE_BY_SPEC["v0.4.0"] = 40` in spec_validator. This is more invasive but type-system-cleaner if the plan author accepts breaking the v0.3.0 7×37 anchor.

### §5.2 Q2: Should "real-data verification" be a 9th step in §8.1 or a sub-step of `evaluate`?

**Status**: §4.2 leaned toward sub-step but flagged ambiguity for plan author.

**Arguments for 9th step** (R45 original phrasing):

- Visibility: 9-step protocol is more discoverable than buried sub-step.
- Semantic distinct: real-data verification is testing-vs-production-shape; `evaluate` is metrics-against-spec-shape — different concerns.
- Audit trail: a separate step name lands as a separate `next_action_plan.actions[].step` value, easier to query.

**Arguments for `evaluate` sub-step**:

- Additivity discipline: §8.1 8-step block currently byte-identical (preserved v0.2.0 → v0.3.0 → v0.4.0). Adding 9th step **breaks byte-identical chain** for the first time. The 8-step list is a Normative anchor for spec_validator.
- Semantic compatibility: `evaluate` already encompasses "no-ability baseline vs with-ability metric measurement"; real-data verification is "measure with REAL inputs vs synthetic" — same concern, different fixture provenance.
- Tooling alignment: `tools/eval_skill.py` already has the right harness shape; adding `--real-data-only / --synthetic-only / --both` flag is cheaper than a new step.

**My recommendation**: **Sub-step of `evaluate`** (NEW §19 placed inside §8.1 step 2 expansion table; 8-step list itself byte-identical). This preserves additivity discipline and avoids requiring `EXPECTED_DOGFOOD_STEPS_COUNT_BY_SPEC` reconciliation in spec_validator. The 9th-step desire is best answered by giving `next_action_plan.actions[].real_data_verification: {fixtures_count, provenance, audit_trail_grep_pattern}` first-class field — visible in artifact, no spec count change.

**Open if Stage 2 disagrees**: If plan author decides 9th step is critical, they need to (a) bump §8.1 from 8 → 9 with reconciliation log entry; (b) update `tools/spec_validator.py` `EVIDENCE_FILES` if a 7th evidence file (for the new step) is required; (c) update `templates/next_action_plan.template.yaml` step enum.

### §5.3 Q3: Should `health_smoke_check` be a `BasicAbilityProfile` field or a packaging-time check?

**Status**: §4.4 recommends "field on BasicAbility.packaging + packaging-gate enforcement"; both at once. This Q surfaces the alternative "tooling-only, no spec field".

**Arguments for spec field**:

- Auditability: `health_smoke_check` declared in the schema lets readers/spec_validator verify the field's presence, not just its execution.
- Forward-compat: §14 reactivation triggers can reference `health_smoke_check.endpoints[*].sentinel_value_predicate` for "when does live-backend recovery count as a reactivation trigger?".
- Per-ability variation: chip-usage-helper has `events/health`; another future ability might have `/api/v1/me`; the field captures ability-specific knowledge.

**Arguments for tooling-only (no spec field, just `tools/health_smoke.py`)**:

- Smaller spec surface area; easier to adopt for abilities without live-backend deps.
- Avoids §11 forever-out edge: a "schema for health probes" sounds suspiciously like "generic IDE / runtime compat layer" if pushed further.
- v0.5.0+ deferral is reasonable if only chip-usage-helper has the use case (single-ability evidence).

**My recommendation**: **Spec field (§21) + packaging-gate enforcement, but Optional REQUIRED**. The field is **OPTIONAL** at schema level (not REQUIRED), but packaging-gate **REQUIRES** it when ability declares any `current_surface.dependencies.live_backend: true`. This bridges the auditability + minimal-overhead concerns. The spec_validator BLOCKER `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND` would land as 13th BLOCKER (after v0.3.0's 11; v0.4.0 would add §19's BLOCKER 12 + §21's BLOCKER 13).

**Open if Stage 2 disagrees**: If "tooling-only" wins, drop §21 from spec entirely; ship `tools/health_smoke.py` standalone; document in §8 step 8 that ability authors SHOULD run it but no Normative force. This is a v0.4.0-vs-v0.5.0 tempo question; my lean is "ship the field now while we have the chip-usage-helper Round 24 evidence fresh".

### §5.4 Q4: How should EAGER-weighted iteration_delta interact with §6 value_vector and §15 round_kind clauses?

**Status**: R32 proposes `weighted_token_delta = 10×eager_delta + 1×oncall_delta` for §4.1 row 10; this Q surfaces interaction with §6 (half-retire) and §15 (round_kind).

**§6 value_vector interaction**: §6.1 currently has `token_delta = (tokens_without − tokens_with) / tokens_without` driven by C4 + OTel. v0.4.0 EAGER-weighting must extend this — **proposal**: keep `token_delta` in §6.1 unchanged (continuous quality axis for half-retire 决策); ADD a new `eager_token_delta` axis to §6.1 value_vector (becoming **8 axes** instead of 7). §6.2 `half_retire` trigger then has option "task_delta near zero AND eager_token_delta ≥ +0.10" — useful for surface-area-shrinking abilities that don't change task quality but free up EAGER budget.

**Consequence**: §6.1 value_vector goes from 7 → 8 axes. This **breaks** the v0.2.0 → v0.4.0 §6.1 byte-identical anchor (currently spec_validator BLOCKER `VALUE_VECTOR` checks for 7 axes). v0.4.0 reconciliation log must explicitly call this out + bump `EXPECTED_VALUE_VECTOR_AXES_BY_SPEC["v0.4.0"] = 8`.

**§15 round_kind interaction**: `code_change` rounds use the EAGER-weighted iteration_delta; `measurement_only` rounds DON'T compute iteration_delta (RELAXED to monotonicity per §15.2). `ship_prep` / `maintenance` WAIVED. So EAGER-weighting only triggers for `code_change` rounds — clean. **No conflict**.

**My recommendation**: Accept the §6.1 7 → 8 axes break with explicit reconciliation. The ROI (per Cycle 2 -55% EAGER win) justifies the count change. The alternative (keep §6.1 = 7 + put EAGER weight only in §4.1 row 10) is incomplete because half-retire decisions would then ignore the most leveraged token win.

**Open if Stage 2 disagrees**: If plan author wants to preserve §6.1 = 7 axes byte-identical, ship EAGER-weighting only in §4.1 row 10 (not in §6.1 value_vector); accept that half-retire decisions can't differentiate EAGER vs ON-CALL wins. This is a defensible "additivity-uber-alles" position; my lean is "the cycle 2 evidence is too strong to leave in §4.1 only".

### §5.5 Q5: When do we open the v0.4.0+ deferred items from v0.2.0 (real-LLM runner for T2 v2_tightened, G2/G3/G4)?

**Status**: v0.2.0 ship report deferred T2 v2_tightened (real-LLM runner) and G2/G3/G4 (cross-domain transfer / OOD robustness / model-version stability). These remain `null` in chip-usage-helper Round 10 and (per v0.3.0 spec frontmatter) are **deferred to "next-version evaluation"**.

**Arguments for opening in v0.4.0**:

- Real-LLM runner unblocks `R3_eager_only` / `R3_post_trigger` split (R33) honestly: deterministic simulator can't model agent context-loading order.
- G2/G3/G4 unblock router-test 96-cell Full from v1_baseline 8-cell MVP.
- Without these, v0.3.0 / v0.4.0 / v0.5.0 ship gates remain perpetually `v1_baseline` (v2_tightened blocked by T2 + G2/G3/G4).

**Arguments for keeping deferred**:

- Cost: real-LLM runner = real API calls = real $ + real latency in CI; adds infrastructure complexity.
- v0.4.0 already heavy (4 P0 themes + 4 P1 themes per §1 tally). Opening real-LLM runner adds 5th P0 theme.
- Cycle 5 demonstrated `health_smoke_check` is more user-impacting than G2/G3/G4 in production.

**My recommendation**: **Keep deferred for v0.4.0**; open in **v0.4.1** (point release) once §18-§23 themes have shipped and consumed planning bandwidth. v0.4.0 should explicitly **re-affirm** the deferral in its `frontmatter.deferred:` list with rationale "v0.4.0 prioritized observability + state-machine + real-data over real-LLM runner; revisit in v0.4.1+".

**Open if Stage 2 disagrees**: If real-LLM runner is opened in v0.4.0, then (a) §5.3 router-test harness gets `--real-llm-mode` flag; (b) `EXPECTED_R6_PROSE_BY_SPEC` may shift to support G2/G3/G4 honest measurement; (c) Stage 4 tooling work doubles. This is "v0.4.0 becomes a major release, not minor" — a defensible choice but breaks the additivity tempo.

### §5.6 Q6: ACE-style `helpful/harmful/neutral` counters — Normative or Informative?

**Status**: surfaced from `/home/agent/reference/agentic-context-engine/ace/skillbook.py`; not in any R-item but a clear gap in §6.4 reactivation triggers.

**§6.4 reactivation trigger #6 says**: "用户手动调用频率回升（30 天 ≥ 5 次）". This is implicitly `helpful` count from ACE. Should v0.4.0 spec **first-class** the `BasicAbility.lifecycle.usage_signals: {helpful_30d, harmful_30d, neutral_30d}` field?

**My recommendation**: **Informative for v0.4.0; promote Normative for v0.5.0 if 2+ abilities show usage-frequency-driven reactivation.** Currently chip-usage-helper hasn't entered `half_retired` state, so no reactivation evidence exists for any ability. Without 2+ independent witnesses, premature codification.

**Open if Stage 2 disagrees**: If usage signals are Normative in v0.4.0, then `tools/eval_skill.py` needs telemetry ingestion (where do `helpful++` events come from? OTel? user feedback button? agent log lines?). This is an instrumentation question that benefits from another cycle of evidence.

### §5.7 Q7 (negative finding flag): Does GEPA bootstrap pattern suggest C0 should be valued differently?

**Status**: per task instructions, "If you discover that a research source contradicts a Si-Chip v0.3.0 design choice (e.g. the dspy bootstrap pattern would suggest C0 should be valued differently), flag it explicitly".

**Finding**: GEPA's "Pareto dominance on score and novelty" ([https://dspy.ai/api/optimizers/GEPA](https://dspy.ai/api/optimizers/GEPA)) values **multi-objective optimization** including novelty as a dimension. Si-Chip §14 strict-no-regression on C0 + §15 round_kind RELAXED `measurement_only` is a **multi-objective-friendly** design — but it doesn't have a "novelty bonus" axis. GEPA evidence suggests novelty (e.g. "new test case discovered new failure mode") deserves a bonus.

**Recommendation**: Don't change v0.3.0 C0 strict-no-regression rule; that rule's value is precisely that it's binary and not negotiable. But **add an Informative §17.3** "Future v0.5.0+ may extend `next_action_plan.actions[].novelty_signal: {new_failure_mode_discovered, new_dependency_flagged, ...}` as a soft bonus that **does not** trade against C0". This honors the GEPA evidence without weakening §14's spec discipline.

**No spec change for v0.4.0** beyond an Informative pointer.

---

## 6. Cross-References

### §6.1 R-item × research §


| R#  | Research §                                                                |
| --- | ------------------------------------------------------------------------- |
| R3  | §2.5 (eval pack curation) + §4.5 (cluster proposal)                       |
| R6  | §2.4 (lifecycle) + §3 row 19 + §4.3                                       |
| R8  | §2.5 (DSPy bootstrap retry) + §3 row 20 + §4.5                            |
| R14 | §2.5 (Inspect AI Sample.metadata) + §3 row 15 + §4.5                      |
| R15 | §2.4 (OpenSpec stage gates) + §3 row 11 + §4.3                            |
| R17 | §2.4 (OpenSpec archive) + §3 row 12 + §4.3                                |
| R25 | §2.5 (OpenAI Evals registry) + §3 row 16 + §4.5                           |
| R27 | §2.4 (OpenSpec verify 3-dim) + §3 row 13 + §4.3                           |
| R30 | §2.1 (Anthropic 3-tier) + §3 row 1 + §4.1                                 |
| R31 | §2.1 (Anthropic concise) + §3 row 17 + §4.1                               |
| R32 | §2.1 (DSPy MIPROv2 + Cursor budget) + §3 row 2 + §4.1                     |
| R33 | §2.1 (Anthropic description vs body) + §3 row 3 + §4.1                    |
| R34 | §2.3 (OpenSpec delta semantics) + §3 row 4 + §4.1                         |
| R36 | §2.5 (Inspect AI metadata + DSPy budget) + §3 row 18 + §4.6               |
| R37 | §2.1 (Anthropic + Karpathy) + §3 row 5 + §4.1                             |
| R41 | §2.1 (Anthropic Resource tier) + §3 row 6 + §4.1                          |
| R42 | §2.1 (static analyzer) + §3 row 7 + §4.1                                  |
| R45 | §2.2 (Pact + tau-bench) + §3 row 8 + §4.2                                 |
| R46 | §2.2 (Inspect AI + msw) + §3 row 9 + §4.2                                 |
| R47 | §2.6 (GitHub Actions URL Health + 4-axis smoke + OTel) + §3 row 10 + §4.4 |


### §6.2 v0.3.0 spec § × proposed v0.4.0 § extension


| v0.3.0 spec §                | v0.4.0 extension                                                                                                    | Type                                   |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| §2.1 BasicAbility schema     | §20 lifecycle.promotion_history block                                                                               | additive                               |
| §3.1 R6 7×37 metric table    | §18 top-level token_tier (C7/C8/C9, NOT D2 sub-metrics)                                                             | additive (preserves count)             |
| §3.1 D4 G1                   | row revised additively (provenance REQUIRED)                                                                        | extension                              |
| §3.1 D6 R3                   | split row to R3_eager_only + R3_post_trigger                                                                        | extension                              |
| §3.2 frozen constraints (4)  | new constraint #5 (deterministic seed)                                                                              | additive (4 → 5)                       |
| §4.1 row 10 iteration_delta  | "v0.4.0 add-on" sentence: EAGER-weighting                                                                           | additive                               |
| §5.3 router-test harness     | "v0.4.0 add-on" sentence: 40-prompt minimum for v2_tightened                                                        | additive                               |
| §6.1 value_vector            | 7 → 8 axes (eager_token_delta added)                                                                                | **breaking — explicit reconciliation** |
| §7 packaging gate            | health_smoke_check pre-ship gate sentence                                                                           | additive                               |
| §8.1 step 2 evaluate         | §19 real-data sub-step                                                                                              | additive (no count change)             |
| §8.1 step 8 package-register | health_smoke_check pre-ship sentence                                                                                | additive                               |
| §8.2 evidence files          | 6 → 7 conditional (ship_decision.yaml when round_kind=ship_prep)                                                    | additive (conditional)                 |
| §9 templates                 | new templates: lazy_manifest, recovery_harness, feedback_real_data_samples, eval_pack_qa_checklist, method_taxonomy | additive (5 new templates)             |
| §11 forever-out              | UNCHANGED (verbatim re-affirmed in §7)                                                                              | byte-identical                         |
| §13 acceptance               | new §13.6 acceptance for v0.4.0 (mirrors §13.5 v0.3.0 pattern)                                                      | additive                               |
| §14 core_goal invariant      | UNCHANGED                                                                                                           | byte-identical                         |
| §15 round_kind               | new sibling field `token_tier_target ∈ {relaxed, standard, strict}`                                                 | additive                               |
| §17 hard rules               | new rules 11 + 12 + 13 (token_tier declared / health_smoke_check declared / real_data_verification declared)        | additive (10 → 13 hard rules)          |


### §6.3 Proposed v0.4.0 templates × authoritative source


| New template                                                      | v0.4.0 spec §                  | Primary industry source                                                | R-item driver         |
| ----------------------------------------------------------------- | ------------------------------ | ---------------------------------------------------------------------- | --------------------- |
| `templates/lazy_manifest.template.yaml`                           | §18.5                          | Anthropic Skill Resource tier (loaded on demand) §2.1.b                | R41                   |
| `templates/feedback_real_data_samples.template.yaml`              | §19 / `feedback` template ext  | Pact "as loose as possible" §2.2.c + Inspect AI Sample.metadata §2.2.a | R46                   |
| `templates/ship_decision.template.yaml`                           | §20.4 (NEW) + §8.2 evidence #7 | OpenSpec archive `changes/archive/<date>-<change-name>/` §2.4.a        | R27                   |
| `templates/recovery_harness.template.yaml`                        | §22 references (Informative)   | DSPy BootstrapFewShot retry pattern §2.5.d                             | R8                    |
| `templates/method_taxonomy.template.yaml`                         | §23 references                 | Inspect AI Sample.metadata first-class §2.5.b                          | R36 + R14 + R29 + R19 |
| `templates/eval_pack_qa_checklist.md` (Informative reference doc) | §22 (NEW)                      | superpowers writing-skills SKILL.md TDD §2.5.b + MLPerf rules §2.5.c   | R3 + R25              |


### §6.4 External source URL × Si-Chip application


| External URL                                                                                                                                                                                                                           | Si-Chip application                                                                                                                                                                                     |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)                                                                     | Token economy: progressive disclosure 3-tier maps to C7/C8/C9 (R30); "concise" rule maps to C1/C7 budget (§4 thresholds)                                                                                |
| [https://docs.anthropic.com/en/docs/claude-code/skills](https://docs.anthropic.com/en/docs/claude-code/skills)                                                                                                                         | Confirms 3-tier (Metadata ~100 tokens / Instructions <500 lines / Resources unlimited); v0.4.0 §18 thresholds                                                                                           |
| [https://docs.pact.io/consumer/](https://docs.pact.io/consumer/)                                                                                                                                                                       | Real-data verification: "as loose as possible" already at v0.3.0 §14.2.1; v0.4.0 §19 extends to msw fixture + broker-style verification                                                                 |
| [https://github.com/mlperf/policies/blob/master/submission_rules.adoc](https://github.com/mlperf/policies/blob/master/submission_rules.adoc)                                                                                           | Eval pack curation: reproducibility + benchmark detection prevention; v0.4.0 §3.2 frozen constraint #5 (fixed seed)                                                                                     |
| [https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics)                                                                                                 | Healthcheck: `gen_ai.tool.name=si-chip.health_smoke` integration point                                                                                                                                  |
| [https://github.com/marketplace/actions/url-health-check](https://github.com/marketplace/actions/url-health-check)                                                                                                                     | Health smoke: minimal endpoint+sentinel schema reference                                                                                                                                                |
| [https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge](https://us.fitgap.com/stack-guides/automate-post-deploy-verification-so-releases-stop-relying-on-tribal-knowledge) | Healthcheck: 4-axis smoke (read/write/auth/dependency); v0.4.0 §21 axis enum                                                                                                                            |
| [https://medium.com/@deryayildirimm/deploying-to-render-insert-a-smoke-test-step-with-github-actions-ffbd49a104dd](https://medium.com/@deryayildirimm/deploying-to-render-insert-a-smoke-test-step-with-github-actions-ffbd49a104dd)   | Healthcheck: GitHub Actions smoke pattern; reference impl for §8 step 8 packaging-gate hook                                                                                                             |
| [https://dspy.ai/api/optimizers/GEPA](https://dspy.ai/api/optimizers/GEPA)                                                                                                                                                             | Self-iteration: Pareto-dominance evidence; v0.5.0+ novelty-bonus pointer in §17.3                                                                                                                       |
| [https://dspy.ai/api/optimizers/BootstrapFewShot](https://dspy.ai/api/optimizers/BootstrapFewShot)                                                                                                                                     | Self-iteration: `metric_threshold` pattern; v0.4.0 §22 case `acceptance_threshold` field                                                                                                                |
| [https://nedcodes.dev/guides/cursor-token-budget](https://nedcodes.dev/guides/cursor-token-budget)                                                                                                                                     | Token economy: Cursor 5-15 rules <3000 tokens budget; v0.4.0 §18 Cursor-platform packaging gate                                                                                                         |
| [https://www.cursor.com/docs/context/rules](https://www.cursor.com/docs/context/rules)                                                                                                                                                 | Confirms `alwaysApply` token cost; v0.4.0 R44 packaging guideline (NOT Normative)                                                                                                                       |
| [https://arxiv.org/abs/2510.00615](https://arxiv.org/abs/2510.00615)                                                                                                                                                                   | Context compression research anchor (Microsoft ACON); v0.4.0 §18 C7/C8/C9 agent-side/compressor-side decomposition Informative note; v0.5.0+ external validation for token_tier threshold bucket sizing |


---

## 7. §11 Forever-Out Re-Check (verbatim re-affirmation)

§11.1 four forever-out items (verbatim from spec_v0.3.0.md §11.1):

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。


| Forever-out item           | Does any v0.4.0 theme touch?                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Skill / Plugin marketplace | **NO**. §18 Token-Tier is observability instrumentation; C7/C8/C9 are spec metric fields, not marketplace fields. §19 Real-Data Verification fixtures live in ability source tree, not in a registry. §20 promotion_history is local append-only artifact, not a public exchange. §21 health_smoke_check is local probe config, not a discovery / publication mechanism. §22 eval pack curation is per-ability artifact, not a marketplace listing. §23 method-tagging is metric metadata, not distribution. |
| Router 模型训练                | **NO**. §18 is token observation, not router training. §19 is real-data testing, not training data. §22 is eval pack curation; §22's `acceptance_threshold` is for filter accept/reject of a case in a pack, NOT for training a router model. §23 method-tagging is metric reporting. None of v0.4.0 themes feed any model.                                                                                                                                                                                  |
| 通用 IDE / Agent runtime 兼容层 | **NO**. §7 packaging priority Cursor → Claude Code → Codex preserved (v0.3.0 byte-identical). §21 health_smoke_check is HTTP/sentinel config, not IDE adaptation. §20 lifecycle stages are spec-internal, no IDE integration surface. §18 token-tier framing aligns with Anthropic SKILL.md and Cursor `.mdc`/SKILL.md, but doesn't introduce a generic abstraction layer.                                                                                                                                   |
| Markdown-to-CLI 自动转换器      | **NO**. §22 eval_pack_qa_checklist is hand-authored Markdown reference doc; cases are hand-written YAML, not auto-derived from SKILL.md. §19 real_data_samples cases are hand-curated from production payloads, not auto-generated. §20 promotion_history records are hand-witnessed transitions. §18/§21/§23 are spec field additions, not transformation tools.                                                                                                                                            |


**Conclusion**: All v0.4.0 proposed themes execute **inside** §11 forever-out; no boundary touched. Special vigilance was applied to two adjacent risk areas:

- **Token-tier optimization is observability, NOT distribution**: C7/C8/C9 instrumentation lets ability authors *see* their token economy; it does NOT publish those measurements to any registry, does NOT enable cross-ability marketplace ranking, does NOT introduce a "skill performance leaderboard" surface. This boundary is preserved by `health_smoke_check` and `core_goal_test_pack` precedent — both are per-ability local artifacts.
- **Real-data verification is testing, NOT marketplace**: msw fixture pattern (§19) is per-ability test infrastructure, not a "shared payload library" or "real-data marketplace". `templates/feedback_real_data_samples.template.yaml` is a feedback-template extension; it does NOT introduce a payload-sharing service, registry, or cross-ability fixture broker.

Frontmatter `forever_out_compliance: "verified — see §7"` is the machine-readable assertion of this re-check.

---

## 8. Provenance & Sign-off

- **Author role**: L3 Task Agent for Si-Chip v0.4.0 planning effort, Stage 1: Research.
- **Wall-clock budget**: ~45-60 min target; actual research + drafting completed within budget.
- **Stage**: Research only. **No spec authoring; no template edits; no source code changes** were made by this stage.
- **Owned files (this stage)**:
  - `.local/research/r12_v0_4_0_industry_practice.md` (this file; CREATE + AUGMENT this session: added ACON §2.1.e; strengthened §2.3.c ACE with measured impact stats 20-35% / 49%; added arXiv URL to §6.4 crosswalk; expanded §8 with citation verification log + honest inventory of repos read but not cited; final file = 712 lines / ~12.5K words / ~105KB — within 700-1100 line target).
  - 0 new clones successfully added to `/home/agent/reference/` (4 attempts total, all FAILED — see negative results below).
- **Read-only files (this stage)**: every other file in `/home/agent/workspace/Si-Chip/` and pre-existing files in `/home/agent/reference/`.
- **Sources cited**: 34 distinct sources (frontmatter has 40+ entries with some multi-file-per-repo entries; consolidates to 34 distinct repo+URL surfaces). Breakdown: 20 in-repo file paths (across Si-Chip + 9 distinct `/home/agent/reference/` repos: openspec, dspy, inspect_ai, evals, agentic-context-engine, acon, coevolved, superpowers, tau-bench + karpathy-llm-wiki.md) + 14 external URLs (Anthropic docs ×2, Pact, MLPerf, OpenTelemetry, GitHub Marketplace, Medium / fitgap, DSPy.ai ×2, nedcodes.dev, developertoolkit.ai, cursor.com docs, arxiv.org/abs/2510.00615 ACON).
- **Citation verification performed this session** (direct file reads to guard against fabrication; all 5 spot-checks PASSED verbatim):
  - `dspy/teleprompt/bootstrap.py` L40-L79: `metric_threshold`, `max_rounds` verbatim present; docstring matches §2.3.a / §2.5.d excerpts.
  - `dspy/teleprompt/mipro_optimizer_v2.py` L43-L51 + L70 + L82: `BOOTSTRAPPED_FEWSHOT_EXAMPLES_IN_CONTEXT = 3`, `AUTO_RUN_SETTINGS = {"light": {"n": 6, "val_size": 100}, "medium": {"n": 12, "val_size": 300}, "heavy": {"n": 18, "val_size": 1000}}`, `Literal["light", "medium", "heavy"]` verbatim present (§2.1.d excerpt confirmed; all three thresholds + the Literal type annotation match).
  - `agentic-context-engine/ace/skillbook.py` L24-L35 + L53-L55 + L400-L402: `@dataclass class Skill` with `helpful: int = 0 / harmful: int = 0 / neutral: int = 0` + `if tag not in ("helpful", "harmful", "neutral")` verbatim present (§2.3.c excerpt confirmed).
  - `inspect_ai/src/inspect_ai/dataset/_dataset.py` L28 + L37 + L81-L82: `class Sample(BaseModel)` + constructor `metadata: dict[str, Any] | None = None` + field `metadata: dict[str, Any] | None = Field(default=None)` with docstring `"""Arbitrary metadata associated with the sample."""` verbatim present (§2.2.a / §2.5.b excerpts confirmed).
  - `openspec/docs/concepts.md` L36-L50: "Specs are the source of truth — they describe how your system currently behaves." + "Changes are proposed modifications — they live in separate folders until you're ready to merge them." verbatim present (§2.3.d / §2.4.a excerpts confirmed).
- **Repos read/skimmed this session but not cited as primary sources** (honest inventory):
  - `coevolved/README.md` (L1-L30) — reviewed; the repo is Coevolved Agent Development Framework by Y Combinator W26 startup "Coevolved", a generic atomic-first orchestration framework. **Negative finding**: despite the task listing's hint "name suggests self-improving loops", the repo content is **not** co-evolutionary self-improvement research. Honest omission — no false citation introduced.
  - `claude-code/`, `claude-code-router/` — agent infra reference, shallow skim only; no direct v0.4.0 R-item mapping observed beyond what Anthropic's public skills docs (cited §2.1.b) already provide.
  - `evals/evals/registry/` confirmed existence of `eval_sets/chinese-numbers.yaml` + `evals/2d_movement.yaml` matching §2.5.a excerpt.
  - `tau-bench/README.md`, `superpowers/skills/writing-skills/SKILL.md`, `superpowers/skills/verification-before-completion/SKILL.md` — confirmed existence and content alignment with cited excerpts.
  - `karpathy-llm-wiki.md` L1-L60 — confirmed "Three layers: Raw sources / The wiki / The schema" verbatim per §2.1.a excerpt.
- **Honest negative results — clone attempts** (per "No Silent Failures" workspace rule):
  - **Attempt #1, `https://github.com/anthropics/skills`**: FAILED with `fatal: unable to access 'https://github.com/anthropics/skills/': GnuTLS recv error (-110): The TLS connection was non-properly terminated.` after 90s. Backup info gathered via WebSearch on Anthropic's docs.anthropic.com pages (cited at §2.1.b + §2.1.c + §6.4).
  - **Attempt #2, `https://github.com/gepa-ai/gepa`**: FAILED with timeout (60s) — likely same TLS issue. Backup info gathered via WebSearch on the dspy.ai/api/optimizers/GEPA page (cited at §2.3.b).
  - **Attempt #3, `https://github.com/anthropics/anthropic-cookbook`**: FAILED with timeout (60s). Backup info gathered via WebSearch (cited at §2.5.c indirectly via the MLPerf rules + §2.1.b directly via Anthropic docs).
  - **Attempt #4 (this session), `https://github.com/anthropics/skills` retried**: FAILED with `Cloning into 'anthropics-skills'...` hanging; exit code 124 (60s timeout). Confirmed via subsequent `ls /home/agent/reference/` that the `anthropics-skills/` directory was NOT created. 4 total clone attempts, 0 successes; backup info remains sufficient via Anthropic public docs URLs.
  - **WebSearch for "OpenTelemetry health probe" + "Kubernetes liveness probe + GenAI semconv"**: No direct overlap found. Documented at §2.6.c as a deliberate v0.4.0 boundary (per §11 forever-out spirit — Si-Chip should not reinvent Kubernetes-side health-probe patterns; if a future ability needs orchestrator-side health probes, that integration belongs in the ability's deployment pipeline not in Si-Chip spec).
  - **chip-usage-helper feedback `round_24.md` + `round_25.md` files**: confirmed NOT-YET-EXIST per SUMMARY.md "this directory; pending creation when commit lands". Cycle 5 content was synthesized from SUMMARY.md §"Cycle 5 — v1.1.0 Bug Fix + New Tool (Rounds 24-25)" — this is noted at §1 and §2.2 references.
- **Hard rules respected** (workspace + AGENTS.md):
  - "No Silent Failures": all 4 clone failures + 1 negative WebSearch + 1 repo-content-vs-task-hint mismatch (coevolved) + 1 expected-file-absent (round_24.md) documented honestly above.
  - "Mandatory Verification": this brief is research not implementation; no test gate, but §3 crosswalk explicitly lists effort estimates for Stage 2 plan author to size into Stage 4 implementation work.
  - "Protected Branch Workflow": this is research; no merge happens at this stage; v0.4.0 ship gate is Stage 5+ Round 16+ dogfood.
  - v0.3.0 §3-§11/§14/§15 byte-identical preservation: §4 all 6 theme proposals explicitly call out additivity discipline; §5.4 Q4 explicitly flags the §6.1 value_vector 7 → 8 axes break as the only deviation requiring Stage 2 plan author decision.
  - Si-Chip v0.3.0 §13 hard rule 9 (`core_goal_test_pack` + C0 = 1.0) and rule 10 (`round_kind` declared) — this brief does not modify any ability profile or next_action_plan; these rules are not engaged at this Stage 1 research stage but are cross-referenced at §4.6 (method-tagging) and §5.4 Q4 (round_kind interaction with EAGER-weighting).
- **Stage 2 input**: this doc's §1 (R-items table) + §3 (crosswalk) + §4 (cluster proposals) + §5 (open questions) are the v0.4.0 plan author's primary planning inputs. §2 industry sources are evidence-grade citations the plan author can cross-reference. §6 cross-references are the bidirectional index the plan author needs to navigate during Stage 2 spec authoring. §7 forever-out re-check is the boundary check the plan author must re-validate at Stage 2 freeze. §8 (this section) is the provenance record.

---

## End of R12 · Si-Chip v0.4.0 Industry Practice Brief