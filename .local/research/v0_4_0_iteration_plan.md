---
title: "Si-Chip v0.4.0 Iteration Plan"
plan_version: "v0.0.1"
status: "draft (awaiting L0 + user approval)"
target_spec_bump: "v0.4.0"
predecessor_spec: "v0.3.0"
authoring_round: "Stage 2 — plan author"
language: "zh-CN + en (technical names in en)"
authoritative_inputs:
  - .local/feedbacks/feedbacks_while_using/chip-usage-helper/SUMMARY.md
  - .local/feedbacks/feedbacks_for_product/feedback_for_v0.2.0.md
  - .local/research/r12_v0_4_0_industry_practice.md
  - .local/research/spec_v0.3.0.md
  - .local/dogfood/2026-04-29/v0.3.0_ship_decision.yaml
  - .local/dogfood/2026-04-29/v0.3.0_ship_report.md
themes_count: 6
new_normative_sections: 6   # §18, §19, §20, §21, §22, §23 (subject to L0 review)
new_informative_sections: 0
new_hard_rules: 3            # §17 grows 11/12/13 (subject to L0 review)
new_tools: 4
new_templates: 3
preserves_byte_identical_v0_3_0: ["§3", "§4", "§5", "§6", "§7", "§8", "§11", "§13", "§14", "§15", "§17"]
forever_out_unchanged: true
estimated_dogfood_rounds: 5  # rounds 16-20 (Round 16 = code_change; 17-19 = sub-themes; 20 = measurement_only sentinel)
estimated_wall_clock: "1 working day with parallel waves; 2 days conservative"
risk_band: "Medium (Q4 §6 axis-break decision is the largest risk; everything else additive)"
critical_path_q4_recommendation: "Option A — keep §6.1 value_vector at 7 axes byte-identical; surface weighted_token_delta as derived headline in iteration_delta_report.yaml"
critical_path_q1_recommendation: "Top-level token_tier invariant block (mirrors v0.3.0 §14 C0 placement; preserves §3.1 R6 7×37 frozen count)"
predecessors:
  - .local/research/spec_v0.2.0.md          # historical anchor (v0.1.0 → v0.2.0 reconciliation pattern)
  - .local/research/spec_v0.3.0.md          # immediate predecessor; byte-identical preservation target
  - .local/research/r11_core_goal_invariant.md   # v0.3.0 spec authoring brief
  - .local/research/r12_v0_4_0_industry_practice.md   # this plan's research input (Stage 1)
provenance_note: |
  This plan is a Stage 2 deliverable in the v0.4.0 implementation cycle.
  No spec edits, no template edits, no code changes are made by this stage.
  The plan IS the decision artifact for L0 + user approval; once approved,
  Stage 2 of the v0.4.0 cycle (spec_v0.4.0-rc1.md authoring) begins.
---

# Si-Chip v0.4.0 Iteration Plan

> Stage 2 deliverable. Companion to `.local/research/r12_v0_4_0_industry_practice.md` (Stage 1 research, 712 lines, 34 sources cited, **High** confidence).
>
> **Reading guide**: §0 is the L0 + user TL;DR; §1–§2 are the goal + theme detail; §3 is the single critical-path decision; §4 is the execution stage tree; §5 is the dogfood plan; §6 is the risk register. Skip to §3 if your time budget is < 5 min — that's the only decision required to unblock Stage 2 of the v0.4.0 implementation cycle.

---

## §0 Executive Summary

> ≤ 60 lines. Goal: tell L0 + user in one read what v0.4.0 ships, why, and what the ship gate is.

**v0.4.0 ships SIX themes**, named verbatim from r12 §0:

1. **Token-Tier MVP-8 Promotion** (R30 / R32 / R37 / R44; Cycle 2 -55% EAGER win → C7/C8/C9 top-level invariant block; Anthropic 3-tier disclosure precedent).
2. **Real-Data Verification** (R45 / R46; Cycle 5 v0.9.0 zero-events bug → §19 sub-step under `evaluate`; Pact "as loose as possible" precedent).
3. **Lifecycle State Machine** (R15 / R17 / R27; chip-usage-helper Round 8 ad-hoc `evaluated → routed` bump → §20 stage_transition_rules + promotion_history + `ship_decision.yaml` as conditional 7th evidence file).
4. **Healthcheck Smoke** (R47; ai-bill `events/health` ops smoke → §21 `health_smoke_check` optional field on `BasicAbility.packaging`; GitHub Actions URL Health Check + 4-axis smoke precedent).
5. **Eval-Pack Curation Discipline** (R3 / R14 / R25; Round 1 R3 = 0.7778 → 0.9524 methodology jump → §22 eval_pack_qa_checklist + 40-prompt MVP recommendation + G1 provenance REQUIRED).
6. **Measurement Honesty Toolkit** (R6 / R8 / R19 / R29 / R31 / R33 / R36 / R39 / R42; method-tag fields, R3 split eager_only/post_trigger, U1 language_breakdown, U4 warm/cold; **Informative-only**; no new spec_validator BLOCKER).

**The single biggest risk** (Q4 §6.1 axis-break): r12 §5.4 leaned toward extending value_vector 7 → 8 axes (adding `eager_token_delta`); **this plan defaults to Option A — keep §6.1 byte-identical at 7 axes; compute EAGER-weighted iteration_delta as a derived headline in `iteration_delta_report.yaml`**. Rationale: additivity discipline is the ship-or-no-ship line per the task hard rules; the user-impact win (Cycle 2 -55% EAGER) is preserved because `weighted_token_delta` becomes a first-class **headline** field even though it doesn't enter §6.1's 7-axis half-retire trigger machinery. User/L0 may override → §3.

**Ship gate** (unchanged from v0.3.0): `relaxed = v1_baseline`; **2 consecutive PASSes per spec §15.4 promotion-counter rule**, mirroring v0.3.0's Round 14 (`code_change`) + Round 15 (`measurement_only`) pattern. v2_tightened remains structurally blocked by `T2_pass_k = 0.5478 < 0.55` (real-LLM runner deferred again to v0.5.0+; same blocker since v0.2.0 ship).

**Estimated dogfood rounds**: 5 (Rounds 16-20). Round 16 = `code_change` (all v0.4.0 features land); Round 17 = `measurement_only` (deterministic monotonicity replay); Round 18 (optional) = `code_change` if Round 17 surfaces a regression; Round 19 = `ship_prep` (the v0.4.0 finalization round; produces the 7th evidence file `ship_decision.yaml` per Theme 3); Round 20 (optional) = post-ship `measurement_only` sanity check.

**The "v0.4.0 contract"** (additivity discipline; same shape as v0.2.0 → v0.3.0 jump):
- v0.3.0 §3 / §4 / §5 / §6 / §7 / §8 / §11 / §13 / §14 / §15 / §17 main bodies **byte-identical** to v0.3.0 (verified via `diff` in Stage 5).
- 6 NEW Normative sections (§18–§23) sit alongside §14–§17.
- 3 NEW hard rules (§17.3 / §17.4 / §17.5) extend §17 additively (AGENTS.md §13 grows 10 → 13).
- spec_validator BLOCKER count grows 11 → 14 (additive; backward-compat preserved for v0.1.0 / v0.2.0 / v0.3.0 spec modes).
- §11 forever-out **verbatim re-affirmed** in §18, §19, §20, §21, §22, §23 footers.
- 3 NEW templates: `real_data_samples.template.yaml`, `ship_decision.template.yaml`, `eval_pack_qa_checklist.template.md` (Informative reference doc); 2 EXTENDED templates (`iteration_delta_report` adds `headline.weighted_token_delta` + `tier_transitions`; `next_action_plan` adds `token_tier_target` sibling field); existing template `$schema_version` bumps 0.2.0 → 0.3.0.

**What's deferred (NOT in v0.4.0)**: real-LLM runner (sandbox lacks LLM API auth + outbound https; same blocker since v0.1.0); §16 multi-ability layout Normative promotion (trigger met — Si-Chip + chip-usage-helper = 2 abilities — but explicitly out-of-scope for additive-discipline reasons; promote in a separate v0.3.x or v0.4.x bump); GEPA-style reflective `improve` step; ACE Skillbook helpful/harmful counters as Normative; ecosystem-specific packaging guidelines (R35 / R38 / R40).

**Confidence**: Medium-High. The plan is grounded in 47 R-items × 6 cluster proposals × 5 ship cycles of chip-usage-helper evidence + 15 rounds of Si-Chip self-dogfood. The largest unknown is Q4 §6.1 axis-break (default Option A; user/L0 override at §3).

---

## §1 Goals & Non-Goals

### §1.1 Goals (6 numbered headline goals; one per cluster)

> Each goal cites primary R-items + a single measurable success criterion that Round 16-19 evidence must demonstrate.

1. **Goal-1 Token Economy Tier-Awareness**: Make C7 EAGER / C8 ON-CALL / C9 LAZY-payload visible at the spec invariant layer so future abilities can target the right token-budget axis.
   - R-items: R30, R32, R34, R37, R44.
   - Measurable success: `metrics_report.yaml.token_tier.{C7_eager_per_session, C8_oncall_per_trigger, C9_payload_p95_tokens}` populated for Si-Chip self in Round 16; values are non-null integers; spec_validator's NEW `TOKEN_TIER_FIELD_PRESENT` BLOCKER passes; `iteration_delta_report.yaml.headline.weighted_token_delta` field present; tier_transitions block populated when any tier moves between rounds.

2. **Goal-2 Real-Data Verification Discipline**: When a feedback bug report includes production payloads, those samples MUST become canonical fixtures cited by provenance label in test names.
   - R-items: R45, R46.
   - Measurable success: `BasicAbility.real_data_samples` field present (may be `[]` for abilities without live backends like Si-Chip self); `templates/real_data_samples.template.yaml` ships; spec_validator's NEW `REAL_DATA_SAMPLES_FIELD_PRESENT` BLOCKER passes; for chip-usage-helper Cycle 5 retroactive ingestion, ≥ 1 endpoint sample documented with `{endpoint, request_params, response_json, observed_state, captured_at, observer}`.

3. **Goal-3 Lifecycle State Machine Codified**: Every stage transition must be triggered by an explicit eval-metric condition + recorded in `promotion_history`; `ship_decision.yaml` becomes the canonical 7th evidence file when `round_kind=ship_prep`.
   - R-items: R15, R17, R27.
   - Measurable success: `BasicAbility.lifecycle.stage_transition_rules` table present; `BasicAbility.lifecycle.promotion_history` append-only log present (≥ 1 entry from Si-Chip self's `evaluated → productized` transition over Rounds 1-15 retroactively backfilled); Round 19 = `ship_prep` produces `ship_decision.yaml` as 7th evidence file; spec_validator's NEW `STAGE_TRANSITION_RULES_DECLARED` + `SHIP_DECISION_PRESENT_FOR_SHIP_PREP_ROUNDS` BLOCKERs pass.

4. **Goal-4 Healthcheck Pre-Ship Gate**: Abilities with live-backend dependencies declare `health_smoke_check` endpoints; ship-gate runs them at `package-register` time.
   - R-item: R47.
   - Measurable success: `BasicAbility.packaging.health_smoke_check` optional field schema documented; `tools/health_smoke_check.py` ships with ≥ 8 unit tests; spec_validator's NEW `HEALTH_SMOKE_CHECK_VALID_IF_DECLARED` BLOCKER passes; for Si-Chip self (no live backend), the field is absent and the BLOCKER's "absence is allowed" branch covers it; for chip-usage-helper Cycle 5 retroactive ingestion (Round 26 cross-ability dogfood), ai-bill `/api/v1/cursor/events/health` endpoint declared with `axis: dependency` + `sentinel_field: latestTsMs` + `sentinel_value_predicate: ">0"`.

5. **Goal-5 Eval-Pack Curation as Spec Discipline**: Cap the methodology-artifact rabbit hole that ate 30 min of Round 1 by shipping a written checklist + raising minimum eval-pack size for v2_tightened decisions to 40 prompts.
   - R-items: R3, R14, R25.
   - Measurable success: `templates/eval_pack_qa_checklist.template.md` ships (Informative reference doc; bilingual coverage + near-miss curation + anti-patterns + 40-prompt minimum + fixed-seed determinism); §3.1 D6 R3 row gets a "v0.4.0 add-on" sentence (additive); §3.1 D4 G1 gets a "v0.4.0 add-on" sentence requiring `provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` first-class; spec_validator's NEW `EVAL_PACK_QA_CHECKLIST_REFERENCED_OR_INLINE` BLOCKER passes.

6. **Goal-6 Measurement Honesty Toolkit**: Method-tag every numeric metric whose value depends on the measurement method; expose R3 as eager_only/post_trigger split; surface MCP-text default-compact warning + server-vs-client cap detector + default-data anti-pattern detector inside `tools/eval_skill.py`.
   - R-items: R6, R8, R19, R29, R31, R33, R36, R39, R42.
   - Measurable success: `metrics.<dim>.method` companion fields present per `templates/method_taxonomy` informative reference; `R3_eager_only` + `R3_post_trigger` derived metrics computed (aggregate `R3_trigger_F1` byte-identical for backward-compat); `tools/eval_skill.py` CLI gains `--check-mcp-pretty / --check-server-cap-vs-client / --check-default-data-anti-pattern` flags; **NO new spec_validator BLOCKER** (Theme 6 is informative-only — keeps the BLOCKER count at 14 not 15+).

### §1.2 Non-Goals (forever-out re-affirmation)

The 4 §11.1 forever-out items remain forever-out. Verbatim from spec_v0.3.0.md §11.1:

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

In addition, v0.4.0 explicitly excludes:

- **Real-LLM runner**: deferred from v0.2.0 already; remains deferred. The sandbox lacks LLM API auth + outbound https. T2_pass_k v2_tightened blocker (deterministic SHA-256 simulator yields `pass_rate^4 = 0.5478 < 0.55`) carries forward to v0.5.0+. Track as v0.5.0 candidate.
- **§16 Multi-ability layout Normative promotion**: trigger met (Si-Chip Round 14-15 + chip-usage-helper Rounds 1-25 + Cycle 4 v1.0.0 = 2 abilities × ≥ 2 ship cycles each) but the promotion is explicitly out-of-scope for v0.4.0 to keep the additive surface area small. Schedule as a separate v0.3.x or v0.4.x point release.
- **GEPA-style reflective `improve` step**: r12 §5.7 found that GEPA's "Pareto dominance on score and novelty" is a v0.5.0+ seed. v0.4.0 should not introduce LLM-based reflection in the `improve` step.
- **ACE Skillbook helpful/harmful/neutral counters as Normative**: r12 §5.6 recommended Informative @ v0.4.0; promote when 2+ abilities show usage-frequency-driven reactivation evidence. v0.4.0 declines.
- **Ecosystem-specific packaging guidelines** (R35 `/// <reference path>`, R38 pointer-to-sibling relative-path safety, R40 zod schema as routing-test contract): per-ecosystem (TS-only); document in `eval_pack_qa_checklist.template.md` Informative annexes if relevant; do NOT codify as Normative spec text.
- **Periodic post-ship live-backend monitoring**: `maintenance` round_kind already covers this in §15; v0.4.0 does not introduce continuous monitoring infrastructure.
- **Cross-ability shared health-probe library**: would touch §11 marketplace forever-out boundary; explicit out per §7 of r12.

### §1.3 Deferred to v0.5.0+ (5+ items)

| Item | Rationale | Trigger to re-evaluate |
|---|---|---|
| Real-LLM runner (T2_pass_k v2_tightened unblock) | Sandbox limitation; carries forward since v0.2.0. | Sandbox gains LLM API auth + outbound https. |
| GEPA-style reflective `improve` step | Adds LLM-based reflection — orthogonal to v0.4.0's observability focus. | 2+ abilities show structured `next_action_plan.actions[].feedback_text` would help. |
| ACE Skillbook helpful/harmful/neutral counters (Normative) | Premature; no ability has entered `half_retired` state yet. | 2+ abilities show usage-frequency-driven reactivation evidence. |
| Ecosystem-specific packaging guidelines (R35, R38, R40) | Per-ecosystem; would clutter spec text. | Cross-ecosystem audit shows duplicate patterns warrant codification. |
| §16 Multi-ability layout Normative promotion | Already trigger-met; explicit ship choice to keep v0.4.0 additive surface small. | After v0.4.0 ships and Round 26 cross-ability dogfood completes. |
| G2 / G3 / G4 cross-domain / OOD / model-version-stability | Depends on real-LLM runner. | After real-LLM runner lands. |
| L5 / L6 / L7 detour_index / replanning_rate / think_act_split fills | Depends on real-LLM runner traces. | After real-LLM runner lands. |
| `acceptance_threshold` per case in `core_goal_test_pack.yaml` (DSPy `metric_threshold` analogue) | Useful but adds a v0.3.0 §14 schema field; touches frozen surface. | Demand from a downstream ability concrete enough to justify the §14 change. |

---

## §2 Six Themes — Detailed Plan

> Each theme has 7 sub-blocks (theme summary / spec additions / tooling / templates / spec_validator / tests / acceptance / open questions). Themes ordered by priority (P0 first; the order matches the recommended Stage 4 wave assignment — Themes 1, 2, 3, 4 land in waves 4a-4d; Themes 5, 6 land alongside).

### §2.1 Token-Tier MVP-8 Promotion

#### §2.1.0 Theme summary

chip-usage-helper Cycle 2 (Rounds 11-16) achieved **per non-triggering session -447 tokens forever** + first-run total **-31% vs v0.7.0** (cumulative -33% by Cycle 3 v0.9.0); this is by-far the biggest user-impact axis observed across all 5 cycles, and it is invisible to spec §3 D2's `C1 metadata + C4 footprint` framing because they bundle EAGER and ON-CALL together. R30 (token-tier C7/C8/C9) + R32 (EAGER-weighted iteration_delta) + R34 (tier_transitions matrix) + R37 (prose_class taxonomy) + R44 (rule body ≤ 400-token packaging guideline) are the five facets of the same theme. Anthropic's official Claude Code Skills doc describes the same 3-tier disclosure (Metadata / Instructions / Resources) as the Si-Chip-evidenced EAGER / ON-CALL / LAZY pattern; r12 §2.1.b cites the URL. **Spec impact**: NEW §18 Token Economy Normative section + new top-level `token_tier` invariant block on `BasicAbility` and `metrics_report.yaml` (mirrors §14 `core_goal` placement); 1 new tool; 1 new spec_validator BLOCKER; ≥ 12 unit tests.

#### §2.1.1 Spec additions

- NEW §18 "Token Economy" Normative section. Contains:
  - §18.1 Schema: `token_tier: {C7_eager_per_session: int, C8_oncall_per_trigger: int, C9_payload_p95_tokens: int, C7_method, C8_method, C9_method}` (placement: top-level invariant block on `BasicAbility` AND on `metrics_report.yaml`; NOT a new R6 D2 sub-metric; mirrors §14 C0 placement to preserve §3.1 R6 7×37 frozen count).
  - §18.2 EAGER-weighted iteration_delta clause: `weighted_token_delta = 10 × C7_delta + 1 × C8_delta + 0.1 × C9_delta` published as a **derived headline** in `iteration_delta_report.yaml.headline.weighted_token_delta` (NOT a new value_vector axis under Option A; see §3 critical-path decision).
  - §18.3 R3 split: `R3_eager_only` (trigger F1 against rule frontmatter + body only) vs `R3_post_trigger` (rule + SKILL; current R3); the aggregate `R3_trigger_F1` MUST remain byte-identical for v0.3.0 backward-compat (so existing 11 BLOCKERs and §3.1 D6 R3 row don't shift). The split values are derived helpers on `metrics.D6` companion fields.
  - §18.4 prose_class annotation taxonomy: `prose_class ∈ {trigger, contract, recipe, narrative}` for SKILL.md sections; **Informative @ v0.4.0**; promote Normative when 2+ abilities ship with the annotation in production.
  - §18.5 LAZY-tier packaging guideline: any sibling file under the ability's source-of-truth directory MUST NOT be loaded into EAGER/ON-CALL path. **Informative @ v0.4.0** (no enforcement tool yet); document `.lazy-manifest` schema as r12 §4.1's R41 reference but do NOT make it a Normative requirement (deferred to v0.4.x once 2+ abilities adopt).
  - §18.6 Cursor-platform packaging budget envelope (Informative): "5-15 scoped rules totalling < 3000 tokens always-loaded" per Cursor docs (r12 §2.1.c URL); reference in §7 packaging-gate footer; do NOT promote to Normative threshold.
  - §18.7 §11 forever-out verbatim re-affirmation footer (4 items unchanged).
- §3.1 D6 R3 row gets a single "v0.4.0 add-on" sentence: "v0.4.0 add-on: §18.3 derives `R3_eager_only` + `R3_post_trigger` companion fields; aggregate `R3_trigger_F1` value byte-identical." (preserves R3 row Normative semantics).
- §4.1 row 10 `iteration_delta` gets a single "v0.4.0 add-on" sentence: "v0.4.0 add-on: §18.2 derived `weighted_token_delta` published as headline; the row 10 threshold buckets unchanged at +0.05 / +0.10 / +0.15." (preserves row 10 v1/v2/v3 thresholds byte-identical).
- §15 round_kind table grows a **sibling field** `token_tier_target ∈ {relaxed, standard, strict}` (DSPy MIPROv2 light/medium/heavy precedent; r12 §2.1.d). Sibling = NOT a 5th `round_kind` value; the 4-value enum stays byte-identical.
- §17 hard rules grow by 1: NEW Rule 11: "MUST declare `token_tier` block on every `BasicAbilityProfile` and emit `token_tier.C7/C8/C9` in every `metrics_report.yaml`; values may be `null` only if the ability has no SKILL.md (e.g. CLI-only abilities) — otherwise non-null integers REQUIRED."

#### §2.1.2 Tooling deliverables

- NEW `tools/token_tier_analyzer.py` (line-count budget: 350-500 LoC + 350-450 LoC tests).
  - CLI: `--skill-md PATH --vocabulary PATH --rule PATH --canvas-template PATH --out report.yaml`.
  - Computes `C7_eager_per_session` from rule body + SKILL.md frontmatter + AGENTS.md compiled hash regions tagged `alwaysApply: true`.
  - Computes `C8_oncall_per_trigger` from SKILL.md body + references/* + scripts/* (only the trigger-time-loaded subset).
  - Computes `C9_payload_p95_tokens` from canvas template (if any) + tool MCP response payload distribution.
  - Backend selectable: `--method tiktoken | char_heuristic` with default `tiktoken` (matches §3.2 frozen constraint #3 OTel-first datasource); confidence interval emitted as `_ci_low / _ci_high` for char-heuristic-derived values.
  - Tier-transition diff helper: given two `token_tier_report.yaml` snapshots (e.g. round_n vs round_n-1), emits `tier_transitions: [{from, to, tokens, reason, net_benefit}]` matrix per R34.
- Modify `tools/eval_skill.py`: add `--token-tier-only` flag that bypasses the full eval-pack run and only emits the `token_tier` block; useful for fast iteration in `code_change` rounds when the author is hunting an EAGER reduction.
- Modify `tools/spec_validator.py`: add new BLOCKER `TOKEN_TIER_FIELD_PRESENT` (12th BLOCKER); covers both `BasicAbilityProfile.token_tier` schema presence + `metrics_report.yaml.token_tier` schema presence.

#### §2.1.3 Template additions

- Modify `templates/basic_ability_profile.schema.yaml`: bump `$schema_version` 0.2.0 → 0.3.0; additively add `token_tier` block schema (with `null`-allowed sub-fields per §18.1).
- Modify `templates/iteration_delta_report.template.yaml`: bump `$schema_version` 0.2.0 → 0.3.0; additively add `headline.weighted_token_delta` field + `tier_transitions` block schema.
- Modify `templates/next_action_plan.template.yaml`: bump `$schema_version` 0.2.0 → 0.3.0; additively add `token_tier_target ∈ {relaxed, standard, strict}` sibling field (default: `standard`).

#### §2.1.4 spec_validator BLOCKER additions

- NEW BLOCKER `TOKEN_TIER_FIELD_PRESENT` (12th BLOCKER total; 11 → 12).
  - Triggers on every `basic_ability_profile.yaml` AND every `metrics_report.yaml`.
  - PASSes when:
    - `token_tier` block is present at top-level (even if all sub-fields are `null` — declarative presence is the spec contract).
    - Sub-fields `C7_eager_per_session / C8_oncall_per_trigger / C9_payload_p95_tokens` are present (may be null).
    - For `metrics_report.yaml` with `BasicAbility.current_surface.type ∈ {markdown, mcp, sdk, mixed}`, sub-fields MUST be non-null integers (CLI-only or script-only abilities exempt).
  - Backward-compat: when `--spec-version v0.1.0 / v0.2.0 / v0.3.0`, the BLOCKER is silently skipped (mirrors v0.3.0 wave 2a `EXPECTED_BAP_KEYS_BY_SCHEMA` pattern).

#### §2.1.5 Tests

≥ 12 unit tests for `tools/token_tier_analyzer.py` + ≥ 4 unit tests for `tools/spec_validator.py` BLOCKER 12 (16 total minimum):

| Test file | # tests | Coverage |
|---|:---:|---|
| `tools/test_token_tier_analyzer.py` | ≥ 12 | tiktoken vs char_heuristic agreement (≤ 5% delta); ci_low/ci_high bounds; rule-body ≤ 400 detection; Cursor 3000-token total budget; tier_transitions diff helper; `--token-tier-only` short-circuit; `null` placeholder for CLI-only abilities; canvas-template absent → C9=null; LAZY sibling enters EAGER path → diagnostic emitted; pretty-vs-compact MCP text → +35-45% delta detected; default-data anti-pattern → flagged; OTel attribute name validation. |
| `tools/test_spec_validator.py` | ≥ 4 (extension to existing) | BLOCKER 12 PASS for compliant artifact; BLOCKER 12 FAIL for missing block; BLOCKER 12 silent-skip for v0.1.0 / v0.2.0 / v0.3.0 spec modes; BLOCKER 12 PASS for null-only sub-fields when ability is CLI-only. |

Integration test against Si-Chip self: Round 16 evidence MUST emit `metrics_report.yaml.token_tier.{C7, C8, C9}` non-null; values cross-check against `tools/count_tokens` re-run.

#### §2.1.6 Acceptance criteria

- §18 ships in `spec_v0.4.0-rc1.md` with §18.1-§18.7 sub-sections present.
- `templates/basic_ability_profile.schema.yaml` `$schema_version: 0.3.0`; `token_tier` block schema present; v0.3.0 artifacts (Rounds 14-15) load cleanly under v0.3.0 spec mode.
- `tools/token_tier_analyzer.py` ≥ 12 unit tests PASS; CLI invokable; `--method tiktoken` default; `--method char_heuristic` emits `_ci_low / _ci_high`.
- `tools/spec_validator.py` BLOCKER 12 PASS for Round 16 Si-Chip self artifact + chip-usage-helper Cycle 2/3 artifacts when retroactively migrated.
- `iteration_delta_report.yaml.headline.weighted_token_delta` field present in Round 16 evidence; value computed per §18.2 formula.
- §18.7 §11 forever-out footer verbatim — checked in Stage 3 review.

#### §2.1.7 Open questions

- **Q1** (cross-ref r12 §5.1): `C7/C8/C9` placement — top-level invariant vs R6 D2 sub-metrics? **This plan recommends top-level invariant block** (matches r12 §5.1); rationale per §3 below.
- **Q4** (cross-ref r12 §5.4): EAGER-weighted iteration_delta interaction with §6.1 value_vector? **This plan recommends Option A — keep §6.1 = 7 axes byte-identical**; rationale per §3 below.
- **NEW**: Should `token_tier_target` sibling field default to `standard` or to `relaxed`? Recommend `standard` (mirrors §4 v2_tightened default expectation; ability authors opt down to `relaxed` for prototype rounds).
- **NEW**: Should §18.4 `prose_class` taxonomy ship Normative @ v0.4.0 instead of Informative? Recommend Informative; promote when 2+ abilities show production usage.

### §2.2 Real-Data Verification

#### §2.2.0 Theme summary

chip-usage-helper Cycle 5 (Rounds 24-25) uncovered v0.9.0 zero-events bug: production payload from ai-bill backend (when empty) didn't match the synthetic mock fixture; dashboard silently crashed. R45 (real-data verification as a §8 step or sub-step) + R46 (`real_data_samples` structured field on feedback template) are the two facets. The fix in chip-usage-helper used **msw + user-install + post-recovery-live** three-layer verification (per `feedback_for_v1.0.0.md`). This is the **only failure mode in 5 cycles that the current Si-Chip 8-step protocol cannot machine-capture**. r12 §2.2.c (Pact "as loose as possible") + §2.2.d (msw fixture pattern) are the industry precedents. **Spec impact**: NEW §19 Real-Data Verification Normative section (placed as a sub-step under §8.1 step 2 `evaluate` per r12 §5.2 recommendation; preserves §8.1 8-step frozen count); 1 new template; 1 new spec_validator BLOCKER.

#### §2.2.1 Spec additions

- NEW §19 "Real-Data Verification" Normative section. Contains:
  - §19.1 Schema for `BasicAbility.real_data_samples: [{endpoint, request_params, response_json, observed_state, captured_at, observer, provenance_label}]` (provenance label is the grep-able string used in test fixture filenames — chip-usage-helper used `"real-data sample"`).
  - §19.2 §8.1 step 2 `evaluate` sub-step expansion: a NEW §19.2.1 "synthetic-vs-real fixture verification" sub-step that runs after `evaluate` produces metrics; sub-step verifies that for every `real_data_samples` entry, ≥ 1 test fixture exists whose filename or in-file comment cites the provenance label. **The 8-step list count remains byte-identical** — §19.2.1 is a sub-step of step 2, not a 9th step (per r12 §5.2 recommendation).
  - §19.3 Three-layer verification protocol (informative for v0.4.0; codifies chip-usage-helper Cycle 5 pattern):
    - Layer A: msw fixture provenance — every test fixture in the release uses the EXACT JSON shape from a bug report's quoted samples; test names cite `real-data sample` or equivalent provenance label.
    - Layer B: User install verification — the branch is pushed; user installs the tarball; user manually verifies the user-observable behavior under the production state at install time.
    - Layer C: Post-recovery live verification — when the live backend recovers, append a "verified-with-live-data" note to `ship_decision.yaml` (or to the `maintenance` round artifact if post-ship).
  - §19.4 §11 forever-out re-affirmation footer.
- §8.1 step 2 `evaluate` text gets a single "v0.4.0 add-on" sentence: "v0.4.0 add-on: §19.2.1 sub-step verifies real-data fixture provenance when `BasicAbility.real_data_samples` is non-empty." (preserves step 2 Normative semantics).
- §17 hard rules grow by 1: NEW Rule 12: "MUST cite `real_data_samples[*].provenance_label` in test fixture filenames or in-file comments when `BasicAbility.real_data_samples` is declared non-empty."

#### §2.2.2 Tooling deliverables

- NEW `tools/real_data_verifier.py` (line-count budget: 200-300 LoC + 200-300 LoC tests).
  - CLI: `--ability ID --tests-glob 'tests/**/*' --real-data-samples PATH --out report.yaml`.
  - Greps the test fixtures glob for each `provenance_label`; emits PASS/FAIL per sample + aggregate; emits `audit_trail_grep_pattern` for downstream graders.
  - For abilities without live backend (e.g. Si-Chip self), `real_data_samples = []` is the spec-allowed empty case; verifier emits `vacuous PASS`.
- Modify `tools/eval_skill.py`: integrate `tools/real_data_verifier.py` as a `--real-data-verify` sub-mode; runs in §19.2.1 sub-step automatically when `BasicAbility.real_data_samples` is non-empty.
- Modify `tools/spec_validator.py`: add new BLOCKER `REAL_DATA_SAMPLES_FIELD_PRESENT` (13th BLOCKER total; 12 → 13).

#### §2.2.3 Template additions

- NEW `templates/real_data_samples.template.yaml` (`$schema_version: 0.1.0`; new template). Schema:
  ```yaml
  $schema_version: "0.1.0"
  ability_id: "<ability-id>"
  real_data_samples:
    - endpoint: "<URL or method name>"
      request_params: { <key>: <value> }
      response_json: { <full JSON shape> }
      observed_state: "<one-line description>"
      captured_at: "<ISO 8601 datetime>"
      observer: "<email / handle / @neolix.ai>"
      provenance_label: "<grep-able string; default 'real-data sample'>"
      bug_report_uri: "<optional URI to feedback file>"
  ```
- Modify `templates/basic_ability_profile.schema.yaml`: bump `$schema_version` 0.2.0 → 0.3.0; additively add `real_data_samples: <list-or-null>` field (already counted in §2.1.3 schema bump; same template, additive change).

#### §2.2.4 spec_validator BLOCKER additions

- NEW BLOCKER `REAL_DATA_SAMPLES_FIELD_PRESENT` (13th BLOCKER total).
  - Triggers on every `basic_ability_profile.yaml`.
  - PASSes when:
    - `real_data_samples` field is present (may be `[]` for abilities without live backends).
    - When non-empty: each sample has `endpoint / response_json / captured_at / provenance_label` REQUIRED fields populated (others optional).
    - When non-empty: `tools/real_data_verifier.py` returns PASS for at least 80% of samples (grep-match found in `tests/` tree or evidence emits "vacuous PASS" with explicit reason).
  - Backward-compat: silently skipped under `--spec-version v0.1.0 / v0.2.0 / v0.3.0`.

#### §2.2.5 Tests

≥ 8 unit tests for `tools/real_data_verifier.py` + ≥ 4 unit tests for spec_validator BLOCKER 13:

| Test file | # tests | Coverage |
|---|:---:|---|
| `tools/test_real_data_verifier.py` | ≥ 8 | empty samples → vacuous PASS; 1 sample matched in test filename → PASS; 1 sample matched in in-file comment → PASS; 0 matches → FAIL with audit_trail_grep_pattern emitted; 5 samples with 4 matched → PASS at 80% threshold; 5 samples with 3 matched → FAIL at 80% threshold; provenance_label override works; non-existent tests-glob → graceful FAIL with clear message. |
| `tools/test_spec_validator.py` | ≥ 4 (extension) | BLOCKER 13 PASS for compliant artifact (empty samples); BLOCKER 13 PASS for compliant artifact (non-empty + 80% match); BLOCKER 13 FAIL for missing field; BLOCKER 13 silent-skip for legacy spec modes. |

Integration test against Si-Chip self: Round 16 emits `real_data_samples: []` (Si-Chip has no live backend); BLOCKER 13 PASS at the empty-allowed branch.

Integration test against chip-usage-helper Cycle 5: Round 26 cross-ability dogfood (out of v0.4.0 scope but planned as follow-up) backfills ai-bill `events/health` sample → BLOCKER 13 PASS at the non-empty branch.

#### §2.2.6 Acceptance criteria

- §19 ships with §19.1-§19.4 sub-sections present.
- `templates/real_data_samples.template.yaml` ships with `$schema_version: 0.1.0`.
- `tools/real_data_verifier.py` ≥ 8 unit tests PASS; CLI invokable.
- BLOCKER 13 PASSes for Si-Chip self Round 16 (empty samples branch) + planned for Round 26 chip-usage-helper retroactive ingestion.
- §19.2.1 sub-step integrated into `tools/eval_skill.py --real-data-verify` sub-mode.
- §19.4 §11 forever-out footer verbatim — checked in Stage 3 review.

#### §2.2.7 Open questions

- **Q2** (cross-ref r12 §5.2): Sub-step of `evaluate` vs 9th step? **This plan recommends sub-step** (preserves §8.1 8-step byte-identical; r12 §5.2 default lean).
- **Q5** (cross-ref r12 §5.5): When does the real-LLM runner unblock? **This plan defers to v0.5.0+** (sandbox limitation unchanged).
- **NEW**: Should §19.3 three-layer verification be Normative or Informative? Recommend **Informative @ v0.4.0** (codifies the chip-usage-helper Cycle 5 pattern without requiring abilities without live backends to perform Layer B/C; Layer A is implicitly Normative via BLOCKER 13).
- **NEW**: Should `provenance_label` be free-text or enum-constrained? Recommend free-text with `default: "real-data sample"` (matches chip-usage-helper Cycle 5 actual usage).

### §2.3 Lifecycle State Machine

#### §2.3.0 Theme summary

spec §2.2 enumerates 7 lifecycle stages (`exploratory → evaluated → productized → routed → governed`, with `half_retired ↺` and `retired`) but never specifies the **trigger conditions** for transitions. chip-usage-helper Round 8 (Cycle 1) bumped `evaluated → routed` based on `router_floor` bound + v3_strict thresholds passing; that's an ad-hoc decision not in the spec. R15 (`stage_transition_rules`) + R17 (`promotion_history` block) + R27 (`ship_decision.yaml` as 7th evidence file) are the three facets. r12 §2.4 cites OpenSpec's `propose / apply / archive` lifecycle + ACE Skillbook's three roles as industry precedents. **Spec impact**: NEW §20 Lifecycle State Machine Normative section + §8.2 evidence file count grows 6 → 7 conditional on `round_kind=ship_prep`; 1 new template; 2 new spec_validator BLOCKERs.

#### §2.3.1 Spec additions

- NEW §20 "Lifecycle State Machine" Normative section. Contains:
  - §20.1 `stage_transition_rules` table:
    | from_stage | to_stage | required conditions |
    |---|---|---|
    | `exploratory` | `evaluated` | eval_set declared + no_ability_baseline run + 7-dim basic metrics emitted |
    | `evaluated` | `productized` | stable steps in script/CLI/MCP/SDK + ≥ 2 v1_baseline-row-complete consecutive PASSes |
    | `evaluated` | `routed` | `router_floor` bound + ≥ 3 v1_baseline-row-complete OR ≥ 2 v3_strict-row-complete consecutive PASSes |
    | `productized` | `routed` | `router_floor` bound (carry-forward of from-evaluated condition) |
    | `routed` | `governed` | owner + version + telemetry + deprecation_policy listed in `BasicAbility.lifecycle` |
    | `* (any)` | `half_retired` | §6.2 value_vector trigger satisfied + `half_retire_decision.yaml` emitted |
    | `half_retired` | `evaluated` (reactivation) | §6.4 reactivation trigger AND C0 = 1.0 against current run AND core_goal_test_pack hash unchanged from half_retire moment per §14.7 |
    | `* (any)` | `retired` | §6.2 retire trigger satisfied |
  - §20.2 `BasicAbility.lifecycle.promotion_history` append-only block schema:
    ```yaml
    promotion_history:
      - from_stage: "<stage>"
        to_stage: "<stage>"
        triggered_by_round_id: "<round_N>"
        triggered_by_metric_value: "<key:value pair from §20.1 condition>"
        observer: "<L0 / L3 / user>"
        archived_artifact_path: "<path to evidence file>"
        decision_rationale: "<one-line rationale>"
        decided_at: "<ISO 8601 datetime>"
    ```
    Append-only; previous entries MUST NOT be modified. (OpenSpec `changes/archive/` precedent + ACE SimilarityDecision KEEP precedent; r12 §2.4.a + §2.3.c.)
  - §20.3 `metrics_report.yaml.promotion_state` first-class top-level block:
    ```yaml
    promotion_state:
      current_gate: "v1_baseline | v2_tightened | v3_strict"
      consecutive_passes: <int>
      promotable_to: "v2_tightened | v3_strict | null"
      last_promotion_round_id: "<round_N or null>"
    ```
  - §20.4 `ship_decision.yaml` schema (the 7th evidence file). REQUIRED fields:
    ```yaml
    spec_version: "v<x.y.z>"
    decided_at: "<ISO 8601 datetime>"
    verdict: "SHIP_ELIGIBLE | SHIP_BLOCKED | SHIP_ELIGIBLE_PENDING_USER_VERIFICATION"
    ship_eligible: <bool>
    ship_gate_achieved: "relaxed | standard | strict"
    consecutive_v1_passes: <int>
    consecutive_v2_passes: <int>
    consecutive_v3_passes: <int>
    v1_baseline_threshold_check:
      round_<N>: { <full per-threshold trace> }
    multi_round_evidence:
      round_<N>: { present: <bool>, files: <int>, gate: PASS|FAIL, source: <round_id_or_predecessor> }
    cross_platform_drift: { cursor: <DRIFT_SCORE>, claude: <DRIFT_SCORE>, three_tree: <SCORE> }
    spec_11_forever_out_check: { marketplace, router_model_training, ide_compat, md_to_cli, verdict }
    next_steps: [ <list of L0/user follow-ups> ]
    next_version_forward_look: { primary_actions: [], deferred_items: [] }
    ```
    Optional fields: `predecessor_ship`, `packaging_gate_three_trees`, `tarball_path`, `tarball_sha256`. Schema mirrors the ad-hoc shape from chip-usage-helper Round 10 / 19 / 25 + Si-Chip Round 13 / 15 (formalize what was already working).
  - §20.5 §11 forever-out re-affirmation footer.
- §8.2 evidence file count text gets a single "v0.4.0 add-on" sentence: "v0.4.0 add-on: §20.4 adds `ship_decision.yaml` as the 7th evidence file when `next_action_plan.round_kind == 'ship_prep'`; for other `round_kind` values, the evidence count remains 6."
- §17 hard rules grow by 1: NEW Rule 13: "MUST emit `ship_decision.yaml` (per §20.4 schema) as the 7th evidence file when `next_action_plan.round_kind == 'ship_prep'`; for `round_kind ∈ {code_change, measurement_only, maintenance}`, evidence count remains 6."

#### §2.3.2 Tooling deliverables

- NEW `tools/lifecycle_machine.py` (line-count budget: 250-350 LoC + 250-350 LoC tests).
  - CLI: `validate-transition --from STAGE --to STAGE --metrics-report PATH --history PATH` returns 0 if transition valid, 1 with diagnostic otherwise.
  - CLI: `compute-promotion-state --metrics-history GLOB --out report.yaml` walks last N rounds and emits §20.3 block.
  - CLI: `emit-ship-decision --round-id ROUND --metrics-report PATH --basic-ability-profile PATH --out ship_decision.yaml` synthesizes §20.4 schema from the existing artifacts (no new measurements).
- Modify `tools/eval_skill.py`: integrate `--emit-promotion-state` flag that adds §20.3 block to `metrics_report.yaml`.
- Modify `tools/spec_validator.py`: add 2 new BLOCKERs `STAGE_TRANSITION_RULES_DECLARED` (14th BLOCKER) + `SHIP_DECISION_PRESENT_FOR_SHIP_PREP_ROUNDS` (revision of existing `EVIDENCE_FILES` BLOCKER to be conditional on `round_kind`).

#### §2.3.3 Template additions

- NEW `templates/ship_decision.template.yaml` (`$schema_version: 0.1.0`; new template; schema per §20.4).
- Modify `templates/basic_ability_profile.schema.yaml`: bump `$schema_version` 0.2.0 → 0.3.0; additively add `lifecycle.stage_transition_rules` reference + `lifecycle.promotion_history` append-only block schema (already counted in §2.1.3 / §2.2.3 schema bump; same template, additive change).
- Modify `templates/iteration_delta_report.template.yaml`: additively add `promotion_state` top-level block (already counted in §2.1.3 schema bump).

#### §2.3.4 spec_validator BLOCKER additions

- NEW BLOCKER `STAGE_TRANSITION_RULES_DECLARED` (14th BLOCKER total; 13 → 14).
  - Triggers on every `basic_ability_profile.yaml`.
  - PASSes when:
    - `BasicAbility.lifecycle.stage_transition_rules` field present (may be a pointer to spec §20.1 standard rules; explicit declaration required).
    - `BasicAbility.lifecycle.promotion_history` field present (may be `[]` for newly-created abilities).
  - Backward-compat: silently skipped under `--spec-version v0.1.0 / v0.2.0 / v0.3.0`.
- REVISED BLOCKER `EVIDENCE_FILES` (existing in v0.3.0; behavior conditional on `round_kind`):
  - When `next_action_plan.round_kind == 'ship_prep'`: REQUIRES 7 evidence files including `ship_decision.yaml`.
  - When `next_action_plan.round_kind ∈ {code_change, measurement_only, maintenance}`: REQUIRES 6 evidence files (unchanged from v0.3.0).
  - Backward-compat: under `--spec-version v0.3.0`, the BLOCKER stays at unconditional 6 (preserves v0.3.0 semantics).

#### §2.3.5 Tests

≥ 8 unit tests for `tools/lifecycle_machine.py` + ≥ 4 unit tests for spec_validator BLOCKER changes:

| Test file | # tests | Coverage |
|---|:---:|---|
| `tools/test_lifecycle_machine.py` | ≥ 8 | valid `evaluated → routed` transition with router_floor bound; invalid `evaluated → routed` without router_floor; invalid `* → half_retired` without value_vector trigger; valid `half_retired → evaluated` reactivation with C0=1.0 + pack hash unchanged; invalid reactivation with pack hash drift; promotion_history append-only enforcement (existing entries unchanged); compute-promotion-state from 5-round history; emit-ship-decision schema compliance. |
| `tools/test_spec_validator.py` | ≥ 4 (extension) | BLOCKER 14 PASS for compliant artifact; BLOCKER 14 FAIL for missing rules; EVIDENCE_FILES 7-vs-6 conditional logic per round_kind; backward-compat for v0.3.0 spec mode. |

Integration test against Si-Chip self: Round 19 (`ship_prep`) emits `ship_decision.yaml`; spec_validator EVIDENCE_FILES PASSes at 7-file branch.

#### §2.3.6 Acceptance criteria

- §20 ships with §20.1-§20.5 sub-sections present.
- `templates/ship_decision.template.yaml` ships with `$schema_version: 0.1.0`.
- `tools/lifecycle_machine.py` ≥ 8 unit tests PASS; CLI invokable.
- BLOCKER 14 PASSes for Round 16 Si-Chip self artifact (with `lifecycle.stage_transition_rules` declared + `promotion_history` empty list as new-ability default).
- EVIDENCE_FILES BLOCKER PASSes at 7-file branch for Round 19 (`ship_prep`) and at 6-file branch for Rounds 16-18.
- §20.5 §11 forever-out footer verbatim — checked in Stage 3 review.

#### §2.3.7 Open questions

- **NEW**: Should §20.1 stage_transition_rules be declared per-ability (in `BasicAbility.lifecycle`) or referenced from spec §20.1 as standard? Recommend **referenced from spec §20.1 as standard** (BLOCKER 14 accepts pointer like `stage_transition_rules: "<spec_v0.4.0.md#§20.1>"`); per-ability override allowed but not required.
- **NEW**: Should `promotion_history` permit append-only by tooling enforcement or only by convention? Recommend tooling enforcement: `tools/lifecycle_machine.py` validates that previous entries are byte-identical when comparing two snapshots; convention-only is too easy to violate.
- **Q6** (cross-ref r12 §5.6): ACE-style helpful/harmful/neutral counters — Normative or Informative? **This plan recommends Informative** (defer to v0.5.0+).
- **NEW**: What's the canonical `decided_at` timezone in `ship_decision.yaml`? Recommend ISO 8601 with explicit timezone offset (mirrors v0.3.0_ship_decision.yaml `2026-04-29T12:50:00+00:00` shape).

### §2.4 Healthcheck Smoke

#### §2.4.0 Theme summary

chip-usage-helper Cycle 5 (Round 24-25) v0.9.0 zero-events bug exposed the spec gap: when an ability depends on a live backend (chip-usage-helper depends on ai-bill), the §8 8-step protocol has no production smoke check; the ability can be ship-eligible while the backend is empty and the dashboard silently crashes. R47 ("ops CI smoke check `/api/v1/cursor/events/health` returns `latestTsMs > 0`") is the explicit fix. r12 §2.6.a (GitHub Actions URL Health Check) + §2.6.b (4-axis smoke read/write/auth/dependency) are the industry precedents. **Spec impact**: NEW §21 Health Smoke Check Normative section + 1 new helper tool + 1 new spec_validator BLOCKER (conditional on live backend declaration).

#### §2.4.1 Spec additions

- NEW §21 "Health Smoke Check" Normative section. Contains:
  - §21.1 `BasicAbility.packaging.health_smoke_check` schema (OPTIONAL field; REQUIRED when ability declares `current_surface.dependencies.live_backend: true`):
    ```yaml
    health_smoke_check:
      - endpoint: "<URL or method name>"
        expected_status: <int>
        max_attempts: <int>     # default 3
        retry_delay_ms: <int>   # default 1000
        sentinel_field: "<JSONPath or dot-notation>"
        sentinel_value_predicate: "<DSL: '>0', '>=N', '!=null', etc.>"
        axis: "read | write | auth | dependency"
        description: "<one-line>"
    ```
  - §21.2 4-axis enum (read / write / auth / dependency): ability MUST declare ≥ 1 `dependency`-axis check when `live_backend: true` (chip-usage-helper R47 ai-bill `events/health` example).
  - §21.3 §8 step 8 `package-register` integration: ship-gate hard check; ship-eligible declaration REQUIRES either (a) `health_smoke_check` absent (no live backend deps), or (b) all declared axes PASS at packaging time.
  - §21.4 OTel emission: each smoke probe emits `gen_ai.tool.name=si-chip.health_smoke / mcp.method.name=health_check / gen_ai.system=<ability_id>` for trace pipeline integration (matches §3.2 frozen constraint #3 OTel-first datasource).
  - §21.5 §11 forever-out re-affirmation footer (special vigilance: §21 is local probe config, NOT a marketplace nor IDE-compat layer).
- §7 Packaging gate text gets a single "v0.4.0 add-on" sentence: "v0.4.0 add-on: §21 adds optional `health_smoke_check` field; if declared, ship-gate runs it before declaring `SHIP_ELIGIBLE`." (preserves §7 Normative semantics).
- §8.1 step 8 `package-register` text gets a single "v0.4.0 add-on" sentence parallel to the §7 add-on (same content, different anchor).
- §17 hard rules unchanged for §21 (rules 9-13 already cover the spec_validator BLOCKER path; no new behavioral rule needed for §21 alone).

#### §2.4.2 Tooling deliverables

- NEW `tools/health_smoke_check.py` (line-count budget: 250-350 LoC + 200-300 LoC tests).
  - CLI: `--config CONFIG.yaml --out report.yaml [--fail-on-any | --report-only]`.
  - HTTP/HTTPS probe runner with retry + sentinel-field + sentinel-value-predicate evaluation.
  - DSL parser for sentinel_value_predicate: `>0`, `>=N`, `!=null`, `==<str>`, `matches /<regex>/`, `keys >= N`.
  - Emits OTel attribute set per §21.4.
  - Sandbox-safe: when running in environments without outbound HTTPS (current Si-Chip sandbox), supports `--mock-mode` that reads from a local fixture file instead of HTTP probe; this is informative for v0.4.0 (real probe runs in user-install Layer B per §19.3).
- Modify `tools/eval_skill.py`: integrate `--health-smoke-check` flag that delegates to `tools/health_smoke_check.py`; results emitted to `.local/dogfood/.../raw/health_smoke_results.yaml`.
- Modify `tools/spec_validator.py`: add new BLOCKER `HEALTH_SMOKE_CHECK_VALID_IF_DECLARED` (already counted as the 13th BLOCKER from Theme 2; cross-ref §2.2.4 — actually the count goes 11 → 12 (Theme 1) → 13 (Theme 2) → 14 (Theme 3) and Theme 4 adds a 4th NEW BLOCKER making it 15). **Wait — the task spec said target 14 BLOCKERs total**. Let me re-check.

> **Plan author note**: re-reading the task brief, target is 11 → 14 (3 NEW BLOCKERs). Allocated: §2.1 → BLOCKER 12 (`TOKEN_TIER_FIELD_PRESENT`), §2.2 → BLOCKER 13 (`REAL_DATA_SAMPLES_FIELD_PRESENT`), §2.3 → BLOCKER 14 (`STAGE_TRANSITION_RULES_DECLARED`). §2.3 also REVISES existing `EVIDENCE_FILES` BLOCKER but does not add a new one. §2.4 (`HEALTH_SMOKE_CHECK_VALID_IF_DECLARED`) was originally going to be a separate BLOCKER but is **folded into BLOCKER 14's scope as a sub-check** (when `BasicAbility.packaging.health_smoke_check` is declared, BLOCKER 14 also validates schema correctness via `tools/lifecycle_machine.py` cross-call to `tools/health_smoke_check.py --config-validate-only`). This keeps BLOCKER count at 14 per task brief target. Theme 5 adds 0 BLOCKERs. Theme 6 adds 0 BLOCKERs (informative-only). **Result: 11 v0.3.0 + 3 NEW = 14 v0.4.0 BLOCKERs**, matching the task brief target.

#### §2.4.3 Template additions

- Modify `templates/basic_ability_profile.schema.yaml`: bump `$schema_version` 0.2.0 → 0.3.0; additively add `packaging.health_smoke_check` field (already counted in §2.1.3 / §2.2.3 / §2.3.3 schema bump; same template, additive change). The schema bump is one event; the new fields land together.

#### §2.4.4 spec_validator BLOCKER additions

- See §2.4.2 plan author note: §2.4 BLOCKER folds into BLOCKER 14's `HEALTH_SMOKE_CHECK_VALID_IF_DECLARED` sub-check. No standalone new BLOCKER.
- BLOCKER 14 sub-check behavior:
  - When `BasicAbility.packaging.health_smoke_check` is absent → vacuous PASS.
  - When present → schema validation (per §21.1); each axis ∈ {read, write, auth, dependency}; ≥ 1 dependency-axis check required when `current_surface.dependencies.live_backend: true`.

#### §2.4.5 Tests

≥ 8 unit tests for `tools/health_smoke_check.py`:

| Test file | # tests | Coverage |
|---|:---:|---|
| `tools/test_health_smoke_check.py` | ≥ 8 | sentinel_value_predicate `>0` evaluation; predicate `>=N` evaluation; predicate `!=null` evaluation; predicate `matches /<regex>/` evaluation; max_attempts retry exhaustion → FAIL; sentinel_field JSONPath traversal; OTel attribute emission shape; `--mock-mode` reads from local fixture file. |

Integration test against Si-Chip self: Round 16 emits `health_smoke_check: <absent>` (Si-Chip has no live backend); BLOCKER 14 sub-check vacuous PASS.

Planned (out of v0.4.0 scope): chip-usage-helper Round 26 backfills ai-bill `events/health` → BLOCKER 14 sub-check non-vacuous PASS; live probe deferred to user-install Layer B per §19.3.

#### §2.4.6 Acceptance criteria

- §21 ships with §21.1-§21.5 sub-sections present.
- `tools/health_smoke_check.py` ≥ 8 unit tests PASS; CLI invokable; `--mock-mode` works.
- BLOCKER 14 sub-check PASS for Si-Chip self Round 16 (vacuous branch).
- §21.5 §11 forever-out footer verbatim — checked in Stage 3 review.

#### §2.4.7 Open questions

- **Q3** (cross-ref r12 §5.3): `health_smoke_check` as `BasicAbilityProfile` field vs tooling-only? **This plan recommends spec field + packaging-gate enforcement, but Optional + REQUIRED-if-live-backend** (matches r12 §5.3 default lean).
- **NEW**: Should the OTel attribute names in §21.4 match standard GenAI semconv vocabulary? Recommend yes (`gen_ai.tool.name` / `mcp.method.name` / `gen_ai.system` are all already standard semconv names per §3.2 frozen constraint #3).
- **NEW**: Should sandbox-safe `--mock-mode` be Normative? Recommend **NO** — keep it as `tools/health_smoke_check.py` implementation choice; spec text specifies the probe-and-sentinel contract, not the runner implementation.

### §2.5 Eval-Pack Curation Discipline

#### §2.5.0 Theme summary

chip-usage-helper Round 1 R3 = 0.7778 → 0.9524 jump came entirely from evaluator methodology fix (CJK substring matcher + 40-prompt curated pack), NOT from ability improvement. R3 (40-prompt minimum for v2_tightened) + R14 (G1 `provenance` first-class) + R25 (`eval_pack_qa_checklist.md` reference doc) are the three facets. r12 §2.5.a (OpenAI Evals registry) + §2.5.b (Inspect AI Sample.metadata) + §2.5.c (MLPerf reproducibility) are the industry precedents. **Spec impact**: NEW §22 Eval-Pack QA Normative section (lightweight; mostly a pointer to a new Informative reference doc) + 1 new template (Markdown reference doc) + 1 add-on sentence each on §3.1 D6 R3 and §3.1 D4 G1 rows; 1 new spec_validator BLOCKER folded into the existing checks.

#### §2.5.1 Spec additions

- NEW §22 "Eval-Pack QA" Normative section. Contains:
  - §22.1 The 40-prompt minimum recommendation: "20 prompts MVP; 40+ recommended for v2_tightened promotion decisions." Reference: chip-usage-helper Round 1 evidence + MLPerf submission rules (r12 §2.5.c).
  - §22.2 Bilingual coverage requirement (when ability targets CJK speakers): bilingual prompts in roughly 50/50 ratio; CJK-aware substring matching mandatory (already covered by `tools/cjk_trigger_eval.py` v0.3.0).
  - §22.3 Near-miss curation: 2-5 negative discriminator prompts per positive trigger prompt; document patterns like the "spend time" negative discriminator class chip-usage-helper Round 1 surfaced.
  - §22.4 Anti-patterns to avoid: naive `\w+` tokenization for CJK; single-language packs; over-trivial prompts; benchmark detection (per MLPerf rules); leaking trigger vocabulary into eval prompts.
  - §22.5 Fixed-seed determinism for replayability: deterministic eval simulators MUST seed with `hash(round_id + ability_id)`. **r12 §4.5 proposed §3.2 frozen constraint #5 for this** but **this plan keeps §3.2 byte-identical** (additivity discipline) and instead documents the fixed-seed convention in §22.5 as Normative within §22's scope, not as a §3.2 constraint promotion.
  - §22.6 G1 provenance first-class: §3.1 D4 G1 row gets an add-on sentence (additive, see below) requiring `G1_provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` companion field on every G1 measurement.
  - §22.7 Reference: see `templates/eval_pack_qa_checklist.template.md` (Informative reference doc) for the full checklist.
  - §22.8 §11 forever-out re-affirmation footer.
- §3.1 D6 R3 row gets a single "v0.4.0 add-on" sentence: "v0.4.0 add-on: 20-prompt MVP for `v1_baseline`; 40+ recommended for `v2_tightened` promotion decisions per §22.1." (preserves R3 row Normative semantics + threshold table byte-identical).
- §3.1 D4 G1 row gets a single "v0.4.0 add-on" sentence: "v0.4.0 add-on: G1 measurement REQUIRES `G1_provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` companion field per §22.6." (preserves G1 row Normative semantics).
- §17 hard rules unchanged for §22.

#### §2.5.2 Tooling deliverables

- Modify `tools/eval_skill.py`: integrate `--eval-pack-qa-check` flag that runs the §22 checklist programmatically (40-prompt count check + bilingual coverage check + near-miss ratio check + anti-pattern detection); emits report to `.local/dogfood/.../raw/eval_pack_qa_check.json`.
- Modify `tools/cjk_trigger_eval.py` (existing in v0.3.0): add `--seed-from-round-id` flag for fixed-seed determinism per §22.5.
- No standalone new tool for §2.5 (the work is reference-doc + flag additions to existing tools).

#### §2.5.3 Template additions

- NEW `templates/eval_pack_qa_checklist.template.md` (Informative reference doc; new template; `$schema_version` not applicable for Markdown). Sections:
  1. Eval-pack sizing (20-prompt MVP / 40+ for v2_tightened).
  2. Bilingual coverage (50/50 ratio + CJK substring matching).
  3. Near-miss curation (2-5 negatives per positive).
  4. Anti-patterns to avoid (naive tokenization / single-language / over-trivial / benchmark detection / leaking trigger vocab).
  5. Fixed-seed determinism (per §22.5).
  6. Provenance labels (`real_llm_sweep / deterministic_simulation / mixed` per §22.6).
  7. Pre-ship QA gate checklist (yes/no ✓ rows).
- No `$schema_version` bump for this theme (Markdown reference doc, not YAML schema).

#### §2.5.4 spec_validator BLOCKER additions

- NO standalone new BLOCKER for §2.5. The `EVAL_PACK_QA_CHECKLIST_REFERENCED_OR_INLINE` check is folded into the existing v0.3.0 `BAP_SCHEMA_FROM_TEMPLATES` BLOCKER scope (which already validates that templates referenced by `BasicAbility` exist on disk).
- BLOCKER count remains at 14 (§2.5 adds 0 new BLOCKERs).

#### §2.5.5 Tests

≥ 8 unit tests for the new flag in `tools/eval_skill.py` (extension):

| Test file | # tests | Coverage |
|---|:---:|---|
| `tools/test_eval_skill.py` | ≥ 8 (extension) | `--eval-pack-qa-check` 40-prompt count detection; bilingual coverage detection (zh chars + en words ratio); near-miss ratio detection; naive `\w+` tokenization anti-pattern detection; single-language pack anti-pattern detection; over-trivial prompt detection; G1_provenance field present detection; `--seed-from-round-id` produces deterministic shuffles. |

Integration test against Si-Chip self: Round 16 runs `--eval-pack-qa-check` against Si-Chip's existing eval_pack.yaml; verifies 40+ prompts (Si-Chip self has 40 prompts as of Round 14); G1_provenance: deterministic_simulation correctly tagged.

#### §2.5.6 Acceptance criteria

- §22 ships with §22.1-§22.8 sub-sections present.
- `templates/eval_pack_qa_checklist.template.md` ships as Informative reference doc.
- §3.1 D6 R3 + §3.1 D4 G1 add-on sentences land additively (rest of rows byte-identical).
- `tools/eval_skill.py --eval-pack-qa-check` flag works; ≥ 8 unit tests PASS.
- §22.8 §11 forever-out footer verbatim — checked in Stage 3 review.

#### §2.5.7 Open questions

- **NEW**: Should §3.2 frozen constraint #5 (fixed-seed) be promoted to v0.4.0 Normative as r12 §4.5 proposed? **This plan recommends NO** (keep §3.2 byte-identical; document fixed-seed as §22.5 Normative within §22's scope). User/L0 may override if additivity discipline is willing to accept §3.2 4 → 5 constraint count increase.
- **NEW**: Should `templates/eval_pack_qa_checklist.template.md` be Normative or Informative? Recommend **Informative @ v0.4.0** (Markdown checklist; promote when 2+ abilities adopt).
- **NEW**: Should the 40-prompt minimum be Normative threshold or recommendation? Recommend **recommendation** (the spec text says "recommended for v2_tightened" not "REQUIRED"; preserves authoring flexibility for fast-iteration cycles).

### §2.6 Measurement Honesty Toolkit

#### §2.6.0 Theme summary

R6 (`promotion_state` first-class), R8 (T4 canonical recovery harness), R19 (U4 warm/cold), R29 (U1 language_breakdown), R31 (MCP text default-compact warning), R33 (R3 split eager_only/post_trigger), R36 (`tokens_estimate_method` + confidence band), R39 (server default vs client cap detector), R42 (default-data anti-pattern detector) are nine measurement-honesty primitives that don't fit cleanly under any single theme above. r12 §2.5.b (Inspect AI Sample.metadata first-class) + DSPy `metric_threshold` are the precedents. **Spec impact**: NEW §23 Measurement Honesty Normative section + helpers added to `tools/eval_skill.py` (no new standalone tool); R3 split as derived helpers (NOT a new D6 sub-metric, preserves §3.1 R6 7×37 frozen count); `templates/recovery_harness.template.yaml` for T4. **NO new spec_validator BLOCKER** (Theme 6 is informative-only).

#### §2.6.1 Spec additions

- NEW §23 "Measurement Honesty" Normative section. Contains:
  - §23.1 Method-tag companion fields: `metrics.<dim>.method` for token-related metrics (`C1_metadata_tokens_method ∈ {tiktoken, char_heuristic, llm_actual}`; same for `C7/C8/C9` from §18). For C0: `_method ∈ {real_llm, deterministic_simulator}`. For G1: per §22.6.
  - §23.2 Confidence band fields: `metrics.<dim>._ci_low / _ci_high` for char-heuristic-derived token metrics (chip-usage-helper Round 17 R36 evidence: char-heuristic vs tiktoken differ 2-5% normally; 2.4× on template-types-extract).
  - §23.3 R3 split derived helpers: `R3_eager_only` + `R3_post_trigger` (per §18.3 cross-ref; these are derived headers in `metrics.D6` companion fields, NOT new sub-metrics; aggregate `R3_trigger_F1` byte-identical).
  - §23.4 `promotion_state` first-class block (per §20.3 cross-ref; §23.4 is the measurement-side spec text; §20.3 is the lifecycle-side spec text — same field, two anchors per multi-theme intersection).
  - §23.5 U4 `state ∈ {warm, cold, semicold}` companion field (per R19; chip-usage-helper Round 17 evidence: `npm ci` cold cache 30-90s vs warm cache <2s).
  - §23.6 U1 `language_breakdown: {en: <fk>, zh: <chars>, mixed_warning: bool}` companion field (per R29; bilingual SKILL.md descriptions can't be fairly compared in FK-grade alone).
  - §23.7 T4 canonical recovery harness reference: `templates/recovery_harness.template.yaml` (per R8 + DSPy bootstrap retry pattern). Standardizes the 4-scenario branch test pattern (`{match, one-candidate, no-candidate, multi-candidate}` for identity; `{success, expected_failure, recoverable_failure, unrecoverable_failure}` for tool calls).
  - §23.8 MCP `text` channel default-compact warning (per R31): `tools/eval_skill.py` static check flags any MCP server using `JSON.stringify(*, null, 2)` AND `structuredContent` set; informative-only; emits diagnostic in `metrics_report.yaml`.
  - §23.9 Server-default vs client-cap detector (per R39): static check scans canvas templates for `slice(0, N)` patterns + cross-checks server-side default; emits diagnostic.
  - §23.10 Default-data anti-pattern detector (per R42): static check flags any template with a SKILL recipe substitution that carries non-stub default data; emits diagnostic.
  - §23.11 §11 forever-out re-affirmation footer.
- No spec text modifications outside §23; §3 / §4 / §5 byte-identical.
- §17 hard rules unchanged for §23 (informative-only theme).

#### §2.6.2 Tooling deliverables

- Modify `tools/eval_skill.py`: extend with 5 new helper modes (NO new standalone tool):
  - `--check-mcp-pretty` (per §23.8) — static scan of MCP handler files for `JSON.stringify(*, null, 2)` patterns + `structuredContent` declaration.
  - `--check-server-cap-vs-client` (per §23.9) — static scan of canvas templates for `slice(0, N)` patterns; cross-check server-side default.
  - `--check-default-data-anti-pattern` (per §23.10) — static scan of templates for non-stub default data when SKILL recipe substitutes the block.
  - `--u4-warm-cold-distinction` (per §23.5) — adds `u4_state` field to U4 measurement output.
  - `--u1-language-breakdown` (per §23.6) — adds `language_breakdown` block to U1 measurement output.
- Modify `tools/cjk_trigger_eval.py` (existing in v0.3.0): integrate R3 split (`--emit-r3-eager-only --emit-r3-post-trigger`); aggregate `R3_trigger_F1` byte-identical.
- No spec_validator changes for §2.6 (informative-only theme).

#### §2.6.3 Template additions

- NEW `templates/recovery_harness.template.yaml` (`$schema_version: 0.1.0`; new template; per R8 + DSPy bootstrap retry pattern). Schema:
  ```yaml
  $schema_version: "0.1.0"
  ability_id: "<ability-id>"
  recovery_scenarios:
    identity:
      - scenario: "match"
        input: { <example> }
        expected_recovery: "direct_pass"
      - scenario: "one_candidate"
        input: { <example> }
        expected_recovery: "select_unique"
      - scenario: "no_candidate"
        input: { <example> }
        expected_recovery: "graceful_fail_with_diagnostic"
      - scenario: "multi_candidate"
        input: { <example> }
        expected_recovery: "disambiguate_or_fail_with_diagnostic"
    tool_calls:
      - scenario: "success"
        # ...
      - scenario: "expected_failure"
        # ...
      - scenario: "recoverable_failure"
        # ...
      - scenario: "unrecoverable_failure"
        # ...
  ```
- No `templates/method_taxonomy.template.yaml` for v0.4.0 (r12 §4.6 proposed it; this plan defers to v0.4.x to keep template count delta small at 3 new = ship_decision + real_data_samples + recovery_harness; `eval_pack_qa_checklist.template.md` is Markdown not YAML so doesn't count toward the YAML template count).

#### §2.6.4 spec_validator BLOCKER additions

NONE. Theme 6 is informative-only. BLOCKER count remains at 14.

#### §2.6.5 Tests

≥ 8 unit tests across `tools/eval_skill.py` extensions + ≥ 4 unit tests for `tools/cjk_trigger_eval.py` R3-split:

| Test file | # tests | Coverage |
|---|:---:|---|
| `tools/test_eval_skill.py` | ≥ 8 (extension) | `--check-mcp-pretty` detects `JSON.stringify(*, null, 2)` + `structuredContent`; `--check-server-cap-vs-client` detects `slice(0, N)` mismatch; `--check-default-data-anti-pattern` detects non-stub default; `--u4-warm-cold-distinction` emits `u4_state`; `--u1-language-breakdown` emits language_breakdown block; `--method tiktoken` vs `--method char_heuristic` agreement (≤ 5% delta); `_ci_low / _ci_high` bounds; integration with `tools/token_tier_analyzer.py` from §2.1. |
| `tools/test_cjk_trigger_eval.py` | ≥ 4 (extension) | `--emit-r3-eager-only` produces correct subset; `--emit-r3-post-trigger` produces full set; aggregate `R3_trigger_F1` byte-identical for backward-compat; gap diagnostic emitted when r3_eager_only < r3_post_trigger by > 0.05. |

Integration test against Si-Chip self: Round 16 emits all §23 fields; aggregate `R3_trigger_F1` byte-identical to Round 15 (0.8934).

#### §2.6.6 Acceptance criteria

- §23 ships with §23.1-§23.11 sub-sections present.
- `templates/recovery_harness.template.yaml` ships with `$schema_version: 0.1.0`.
- `tools/eval_skill.py` extensions ≥ 8 unit tests PASS; CLI flags invokable.
- `tools/cjk_trigger_eval.py` R3 split extension ≥ 4 unit tests PASS; aggregate byte-identical.
- §23.11 §11 forever-out footer verbatim — checked in Stage 3 review.

#### §2.6.7 Open questions

- **NEW**: Should `templates/method_taxonomy.template.yaml` ship in v0.4.0 (per r12 §4.6) or defer to v0.4.x? **This plan recommends defer to v0.4.x** (keep template count delta at 3 for cleaner reconciliation log).
- **NEW**: Should U4 `state ∈ {warm, cold, semicold}` companion field be Normative? Recommend Normative within §23.5 scope (informative-only theme overall, but the state field is structured data not just a measurement convention).
- **Q5** (cross-ref r12 §5.5): Real-LLM runner unblock — covered by §1.3 deferral.

---

## §3 Critical-Path Decision: Q4 §6.1 value_vector axis-break

> **This is the single decision required to unblock Stage 2 of the v0.4.0 implementation cycle.** L0 + user must approve OR override before spec_v0.4.0-rc1.md authoring begins.

### §3.1 The two options

**Option A** (this plan's recommendation): **Keep §6.1 value_vector at 7 axes byte-identical**. Compute EAGER-weighted iteration_delta as a **derived metric** in `tools/eval_skill.py` and surface it in `iteration_delta_report.yaml.headline.weighted_token_delta` field. §4.1 row 10 thresholds and clause unchanged. spec_validator BLOCKER `VALUE_VECTOR` continues to expect 7 axes.

**Option B** (r12 §5.4 leaned this way): **Extend §6.1 to 8 axes** (add `eager_token_delta`). Breaks the v0.3.0 byte-identical guarantee for §6. Requires §13 (acceptance criteria for v0.1.0) prose count update if it references the §6.1 7-axis count + spec_validator BLOCKER bump (`EXPECTED_VALUE_VECTOR_AXES_BY_SPEC["v0.4.0"] = 8`) + reconciliation log entry mirroring v0.1.0 → v0.2.0-rc1 pattern.

### §3.2 Trade-offs side-by-side

| Dimension | Option A (default) | Option B |
|---|---|---|
| **Additivity discipline (v0.3.0 byte-identical)** | Preserved for §3 / §4 / §5 / §6 / §7 / §8 / §11 / §13 / §14 / §15 / §17. | **Broken for §6.1**; rest preserved. |
| **EAGER-weighted iteration_delta visibility** | Derived headline in `iteration_delta_report.yaml.headline.weighted_token_delta`. Readers see it; tooling computes it. | First-class value_vector axis; readers see it; tooling computes it. Tightly integrated with §6.2 half-retire trigger. |
| **§6.2 half-retire trigger interaction** | `half_retire` trigger remains at 7-axis vector (token_delta / latency_delta / context_delta / path_efficiency_delta / routing_delta + task_delta + governance_risk_delta); EAGER-weight is **not** an independent half-retire axis. Half-retire decisions can't differentiate EAGER vs ON-CALL wins via the trigger alone. | `half_retire` trigger gains 8th axis `eager_token_delta`; can differentiate EAGER vs ON-CALL wins. Useful for surface-area-shrinking abilities that don't change task quality but free up EAGER budget. |
| **spec_validator BLOCKER count** | 11 → 14 (additive: TOKEN_TIER_FIELD_PRESENT + REAL_DATA_SAMPLES_FIELD_PRESENT + STAGE_TRANSITION_RULES_DECLARED). VALUE_VECTOR BLOCKER unchanged. | 11 → 14 + revision of VALUE_VECTOR BLOCKER (axis count 7 → 8). |
| **Reconciliation log entry for §6.1** | None needed; §6.1 byte-identical. | Required: explicit "v0.3.0 §6.1 7-axis → v0.4.0 §6.1 8-axis" entry mirroring v0.1.0 → v0.2.0-rc1 prose count "28 → 37" pattern. |
| **Forward-compat for v0.5.0+** | Easier — no broken precedent; future axes can also be derived headlines if they don't fit half-retire trigger semantics. | Sets precedent for "additivity discipline can be broken when ROI is high"; risks normalizing breaks. |
| **User-impact preservation** | Cycle 2 -55% EAGER win is reportable via `headline.weighted_token_delta`; readers see the same number. | Cycle 2 -55% EAGER win drives `value_vector.eager_token_delta = +0.55`; same number, different home. |
| **§4.1 row 10 thresholds (+0.05/+0.10/+0.15)** | Unchanged; `weighted_token_delta` headline doesn't gate v1/v2/v3 promotion (only the 7-axis token_delta does). | Unchanged thresholds; `eager_token_delta` competes alongside other axes for the "≥ 1 axis at gate bucket" §4.1 row 10 clause. |
| **Round 16-17 dogfood evidence cost** | Lower; current `iteration_delta_report.yaml` schema gets 1 new headline field (additive). | Higher; current `iteration_delta_report.yaml` schema needs 8-axis value_vector restructure; spec_validator BLOCKER VALUE_VECTOR needs revision; backward-compat for v0.3.0 artifacts needs explicit version-aware path. |

### §3.3 Recommendation

**Pick Option A.** Default lean per task brief; rationale:

1. **Additivity discipline is the ship-or-no-ship line** per the task hard rules. Breaking §6.1 byte-identical is the **one** thing the task brief explicitly flagged as a Major risk (R-1 in §6).
2. **The user-impact win is preserved either way.** Cycle 2 -55% EAGER reaches the user via `headline.weighted_token_delta` under Option A and via `value_vector.eager_token_delta` under Option B. Same number, different home; same user-visible benefit.
3. **`half_retire` differentiation is deferred, not denied.** Under Option A, half-retire decisions can still cite EAGER-weighted reasoning in `decision_rationale` text; the trigger machinery uses the 7-axis vector but the rationale text can reference any derived headline. r12 §5.6 (ACE helpful/harmful counters) is the v0.5.0+ candidate for richer half-retire decision triggers; bundling EAGER-weight into v0.5.0+ alongside ACE is natural sequencing.
4. **Cleaner reconciliation log.** Option A's reconciliation log only documents additive sections (§18-§23); Option B's reconciliation log opens the door for "but v0.4.x can break §6.2 too if ROI is high" — slippery slope.
5. **spec_validator backward-compat is simpler** under Option A (no version-aware VALUE_VECTOR BLOCKER); Option B requires the same kind of `EXPECTED_VALUE_VECTOR_AXES_BY_SPEC[<version>]` map that v0.3.0 had to add for `EXPECTED_BAP_KEYS_BY_SCHEMA`.

**Note on r12 §5.4 vs this plan**: r12 §5.4 leaned Option B with rationale "the cycle 2 evidence is too strong to leave in §4.1 only". This plan respectfully overrides because Option A's headline-derived approach **does** surface the cycle 2 evidence (in `iteration_delta_report.yaml.headline.weighted_token_delta`); the difference is just whether the value enters §6.1 trigger machinery, which has narrower semantic scope (half-retire only) than the broader user-visible reporting.

### §3.4 Override path

If user/L0 chooses Option B:

1. Spec authoring: §6.1 value_vector list grows from 7 to 8 axes; the new `eager_token_delta` axis is defined as `weighted_token_delta` (per §18.2 formula).
2. Reconciliation log entry: explicit "v0.3.0 §6.1 7-axis byte-identical anchor BROKEN; v0.4.0 §6.1 8-axis additive" entry mirroring v0.1.0 → v0.2.0-rc1 prose count "28 → 37" pattern.
3. spec_validator: `EXPECTED_VALUE_VECTOR_AXES_BY_SPEC = {"v0.1.0": 7, "v0.2.0": 7, "v0.3.0": 7, "v0.4.0": 8}`.
4. AGENTS.md §13 hard rules unchanged (rules 9-13 cover BLOCKER additions; no behavioral hard rule changes for §6.1 axis count).
5. `templates/half_retire_decision.template.yaml` schema bumps to add `eager_token_delta` field; `$schema_version` 0.1.0 → 0.2.0.
6. Round 16 dogfood verification: Si-Chip self's Round 16 `value_vector` emits 8 axes; verify `tools/eval_skill.py` populates `eager_token_delta` value correctly; verify spec_validator under v0.4.0 spec mode counts 8 axes.

---

## §4 Stage Decomposition (the actual execution plan)

The v0.4.0 implementation cycle follows the v0.3.0 8-stage shape exactly (it worked for the v0.3.0 ship; reuse it). 9 stages total (Stage 0 through Stage 8).

### §4.1 Stage 0 — L0 setup

- **L0 → L3 dispatch shape**: L0 setup; no subagent dispatched.
- **Owned files**: feature branch creation; TodoWrite skeleton; devpath-upload bootstrap.
- **Acceptance criteria**:
  - Feature branch `feat/v0.4.0-token-economy-real-data-lifecycle` created from current `main` HEAD (or current trunk if main has moved).
  - TodoWrite created with 9 stages (Stage 0 through Stage 8) + sub-tasks for Stage 4 waves.
  - devpath-upload bootstrap verified (git email check); silent on success, prompt user on failure per workspace rule.
  - This `v0_4_0_iteration_plan.md` (this file) reviewed + approved by L0 + user.
- **Estimated wall-clock**: 10-15 min.
- **Predecessor dependency**: None (Stage 0 IS the kickoff).

### §4.2 Stage 1 — Research (refresh)

- **L0 → L3 dispatch shape**: L0 reviews r12; decides whether incremental refresh is needed.
- **Owned files**: optionally `.local/research/r12_v0_4_0_industry_practice_refresh.md` (only if 1-2 newly-published sources warrant ingestion).
- **Acceptance criteria**:
  - r12 verified as still-current (cited URLs reachable; no MAJOR new sources contradicting r12 claims).
  - If refresh needed: ≤ 200 lines additional document; no spec / template changes.
  - If refresh not needed (recommended): explicit "Stage 1 SKIPPED — r12 still current" note in Stage 0 TodoWrite; proceed to Stage 2.
- **Estimated wall-clock**: 0-30 min (often skipped).
- **Predecessor dependency**: Stage 0 complete.
- **Wave parallelism**: N/A (single-threaded).

### §4.3 Stage 2 — Design / Spec author

- **L0 → L3 dispatch shape**: L0 dispatches single L3 spec-author subagent with this plan as primary input.
- **Owned files**: `.local/research/spec_v0.4.0-rc1.md` (CREATE; ~1500-1800 lines; mirrors `spec_v0.3.0-rc1.md` authoring contract).
- **Acceptance criteria**:
  - Spec contains 6 NEW Normative sections §18-§23 with all sub-sections from §2 of this plan.
  - Spec contains 3 NEW hard rules §17.3 / §17.4 / §17.5 added to §17 additively.
  - Spec preserves §3 / §4 / §5 / §6 / §7 / §8 / §11 / §13 / §14 / §15 / §17 main bodies BYTE-IDENTICAL to v0.3.0 (verified via `diff` in Stage 5).
  - Q4 §6.1 axis-break decision (§3 of this plan) implemented per L0/user choice (default Option A; see §3.4 if Option B).
  - §11 forever-out re-affirmed VERBATIM in §18-§23 footers (6 footers).
  - Reconciliation log entry at spec end documents:
    - 6 NEW Normative sections (§18-§23).
    - 3 NEW hard rules (§17.3-§17.5).
    - spec_validator BLOCKER count growth 11 → 14.
    - 3 NEW templates (`real_data_samples.template.yaml`, `ship_decision.template.yaml`, `recovery_harness.template.yaml`).
    - 1 NEW reference doc (`eval_pack_qa_checklist.template.md`; not a YAML template).
    - 5 EXTENDED templates (`basic_ability_profile.schema.yaml`, `iteration_delta_report.template.yaml`, `next_action_plan.template.yaml` schema_version bumps 0.2.0 → 0.3.0).
    - §6.1 value_vector axis count: 7 (Option A; default) OR 7 → 8 (Option B; explicit reconciliation if chosen).
    - §3.2 frozen constraints count: 4 (preserved byte-identical) OR 4 → 5 (only if user/L0 explicitly elevates §22.5 fixed-seed to §3.2 #5 — default keeps §3.2 byte-identical).
    - §8.2 evidence file count: 6 (default) → 7 conditional (`round_kind=ship_prep`).
- **Estimated wall-clock**: 60-90 min.
- **Predecessor dependency**: Stage 0 + Stage 1 complete; §3 critical-path decision resolved.
- **Wave parallelism**: N/A (single subagent).

### §4.4 Stage 3 — Review

- **L0 → L3 dispatch shape**: L0 dispatches single read-only L3 reviewer subagent.
- **Owned files**: `.local/research/spec_v0.4.0-rc1_review.md` (CREATE; ~150-300 lines; review notes).
- **Acceptance criteria**:
  - Reviewer verifies §3 / §4 / §5 / §6 (Option A: byte-identical; Option B: 7→8 with reconciliation log entry) / §7 / §8 / §11 / §13 / §14 / §15 / §17 byte-identical (per §4.3 above).
  - Reviewer cross-checks §18-§23 internal consistency (§18 token_tier composes with §6.1 value_vector under chosen option; §19 real-data sub-step references §22 eval_pack_qa_checklist; §20 promotion_history references §15 round_kind values; §21 health_smoke_check OTel attributes match §3.2 frozen constraint #3).
  - Reviewer explicitly walks through §7 forever-out re-affirmation for §18 (token_tier observability — NOT distribution surface) and §21 (health_smoke probe — NOT marketplace surface).
  - Reviewer signs off OR returns ≤ 10 actionable findings; if findings, Stage 2 spec-author addresses them in a follow-up Stage 2-revision pass before Stage 4 starts.
- **Estimated wall-clock**: 20-30 min.
- **Predecessor dependency**: Stage 2 complete.
- **Wave parallelism**: N/A (single reviewer).

### §4.5 Stage 4 — Implementation (4 waves with disjoint file ownership)

The waves below are **parallel-eligible** when their owned files are disjoint. Recommended order: 4a + 4b parallel; 4c + 4d parallel (after 4a + 4b complete).

#### §4.5.1 Wave 4a — Schema + 3 Templates (additive)

- **L0 → L3 dispatch shape**: L0 dispatches single L3 wave-author subagent.
- **Owned files**:
  - `templates/basic_ability_profile.schema.yaml` (MODIFY; `$schema_version` 0.2.0 → 0.3.0; additively add `token_tier`, `real_data_samples`, `lifecycle.stage_transition_rules`, `lifecycle.promotion_history`, `packaging.health_smoke_check` blocks).
  - `templates/iteration_delta_report.template.yaml` (MODIFY; `$schema_version` 0.2.0 → 0.3.0; add `headline.weighted_token_delta`, `tier_transitions`, `promotion_state` blocks).
  - `templates/next_action_plan.template.yaml` (MODIFY; `$schema_version` 0.2.0 → 0.3.0; add `token_tier_target` sibling field).
  - `templates/real_data_samples.template.yaml` (CREATE; `$schema_version: 0.1.0`; per §2.2.3).
  - `templates/ship_decision.template.yaml` (CREATE; `$schema_version: 0.1.0`; per §2.3.3).
  - `templates/recovery_harness.template.yaml` (CREATE; `$schema_version: 0.1.0`; per §2.6.3).
  - `templates/eval_pack_qa_checklist.template.md` (CREATE; Markdown reference doc; per §2.5.3).
- **Acceptance criteria**:
  - All template files validate against their declared `$schema_version` schemas.
  - v0.3.0 evidence files (Round 14-15) re-validate cleanly under v0.3.0 spec mode (backward-compat preserved).
  - All NEW fields in MODIFIED templates are documented with inline comments (mirrors v0.3.0 wave 2a schema documentation discipline).
- **Estimated wall-clock**: 30-45 min.
- **Predecessor dependency**: Stage 3 complete.
- **Wave parallelism**: 4a runs in parallel with 4b.

#### §4.5.2 Wave 4b — 4 Tools (new + extensions)

- **L0 → L3 dispatch shape**: L0 dispatches single L3 wave-author subagent.
- **Owned files**:
  - `tools/token_tier_analyzer.py` (CREATE; ~350-500 LoC; per §2.1.2).
  - `tools/test_token_tier_analyzer.py` (CREATE; ~350-450 LoC; ≥ 12 unit tests).
  - `tools/real_data_verifier.py` (CREATE; ~200-300 LoC; per §2.2.2).
  - `tools/test_real_data_verifier.py` (CREATE; ~200-300 LoC; ≥ 8 unit tests).
  - `tools/lifecycle_machine.py` (CREATE; ~250-350 LoC; per §2.3.2).
  - `tools/test_lifecycle_machine.py` (CREATE; ~250-350 LoC; ≥ 8 unit tests).
  - `tools/health_smoke_check.py` (CREATE; ~250-350 LoC; per §2.4.2).
  - `tools/test_health_smoke_check.py` (CREATE; ~200-300 LoC; ≥ 8 unit tests).
  - `tools/eval_skill.py` (MODIFY; integrate `--token-tier-only / --real-data-verify / --emit-promotion-state / --health-smoke-check / --eval-pack-qa-check / --check-mcp-pretty / --check-server-cap-vs-client / --check-default-data-anti-pattern / --u4-warm-cold-distinction / --u1-language-breakdown` flags).
  - `tools/test_eval_skill.py` (MODIFY; add ≥ 16 extension tests covering the new flags).
  - `tools/cjk_trigger_eval.py` (MODIFY; add `--seed-from-round-id` + `--emit-r3-eager-only --emit-r3-post-trigger`).
  - `tools/test_cjk_trigger_eval.py` (MODIFY; add ≥ 4 extension tests).
- **Acceptance criteria**:
  - All NEW tools have CLI `--help` documentation.
  - All NEW tools have ≥ 8 unit tests each (≥ 36 total NEW tests + ≥ 20 extension tests = ≥ 56 NEW test cases).
  - All NEW tools pass `pytest -xvs tools/test_<tool>.py`.
  - Existing tests for `eval_skill.py` + `cjk_trigger_eval.py` still PASS (backward-compat).
- **Estimated wall-clock**: 60-90 min.
- **Predecessor dependency**: Stage 3 complete; runs in parallel with Wave 4a.
- **Wave parallelism**: 4b runs in parallel with 4a.

#### §4.5.3 Wave 4c — spec_validator extension to 14 BLOCKERs

- **L0 → L3 dispatch shape**: L0 dispatches single L3 wave-author subagent.
- **Owned files**:
  - `tools/spec_validator.py` (MODIFY; `SCRIPT_VERSION` 0.2.0 → 0.3.0; `SUPPORTED_SPEC_VERSIONS` adds `v0.4.0-rc1` and `v0.4.0`; BLOCKER count 11 → 14: NEW `TOKEN_TIER_FIELD_PRESENT` + NEW `REAL_DATA_SAMPLES_FIELD_PRESENT` + NEW `STAGE_TRANSITION_RULES_DECLARED`; REVISED `EVIDENCE_FILES` with 6/7 conditional logic per round_kind; folded `HEALTH_SMOKE_CHECK_VALID_IF_DECLARED` into BLOCKER 14's scope per §2.4.2 plan author note).
  - `tools/test_spec_validator.py` (MODIFY; add ≥ 12 extension tests covering the 3 NEW BLOCKERs + 1 REVISED BLOCKER + backward-compat for v0.1.0/v0.2.0/v0.3.0 spec modes).
- **Acceptance criteria**:
  - `python tools/spec_validator.py --json` (default mode = latest; v0.4.0 once spec ships): 14/14 PASS.
  - `python tools/spec_validator.py --spec .local/research/spec_v0.3.0.md --json`: 11/11 PASS (backward-compat).
  - `python tools/spec_validator.py --spec .local/research/spec_v0.2.0.md --json`: 9/9 PASS (backward-compat).
  - Strict-prose mode for v0.4.0: 14/14 PASS.
  - Round 14-15 evidence files re-validate cleanly under v0.3.0 spec mode.
- **Estimated wall-clock**: 30-45 min.
- **Predecessor dependency**: Wave 4a complete (templates needed for spec_validator schema checks); Wave 4b not strictly required but recommended (helper tools used by spec_validator integration tests).
- **Wave parallelism**: 4c runs in parallel with 4d.

#### §4.5.4 Wave 4d — SKILL.md + 6 reference docs + AGENTS.md re-compile

- **L0 → L3 dispatch shape**: L0 dispatches single L3 wave-author subagent.
- **Owned files**:
  - `.agents/skills/si-chip/SKILL.md` (MODIFY; frontmatter `version: 0.4.0-rc1`; body adds §18 / §19 / §20 / §21 / §22 / §23 invariants summary; verify body token count ≤ 5000 v1_baseline ceiling).
  - `.agents/skills/si-chip/references/token-economy-r12-summary.md` (CREATE; ~80-150 lines; one-page summary of §18 + r12 §2.1).
  - `.agents/skills/si-chip/references/real-data-verification-r12-summary.md` (CREATE; ~80-150 lines; one-page summary of §19 + r12 §2.2).
  - `.agents/skills/si-chip/references/lifecycle-state-machine-r12-summary.md` (CREATE; ~80-150 lines; one-page summary of §20 + r12 §2.4).
  - `.agents/skills/si-chip/references/health-smoke-check-r12-summary.md` (CREATE; ~80-150 lines; one-page summary of §21 + r12 §2.6).
  - `.agents/skills/si-chip/references/eval-pack-qa-r12-summary.md` (CREATE; ~80-150 lines; one-page summary of §22 + r12 §2.5).
  - `.agents/skills/si-chip/references/measurement-honesty-r12-summary.md` (CREATE; ~80-150 lines; one-page summary of §23 + r12 §2.5 + R-items 6/8/19/29/31/33/36/39/42).
  - `.cursor/skills/si-chip/SKILL.md` + 6 references (MIRROR; auto-synced).
  - `.claude/skills/si-chip/SKILL.md` + 6 references (MIRROR; auto-synced).
  - `.rules/si-chip-spec.mdc` (MODIFY; add 3 hard rules 11/12/13 to §17 source; bump frontmatter version → v0.4.0).
  - `AGENTS.md` (RE-COMPILE via DevolaFlow `RuleCompiler`; verify §13 grows 10 → 13 rules; record new compile hash).
  - `.rules/.compile-hashes.json` (UPDATE; new hash).
- **Acceptance criteria**:
  - SKILL.md body token count ≤ 5000 (v1_baseline ceiling); aim for ≤ 4500 to leave headroom.
  - 6 reference docs each ≤ 150 lines (mirrors v0.3.0 reference doc discipline).
  - 3-tree mirror byte-equality verified (V3_drift_signal = 0.0).
  - AGENTS.md re-compile succeeds; §13 has 13 rules; new compile hash recorded.
  - `.rules/.compile-hashes.json` updated.
- **Estimated wall-clock**: 45-60 min.
- **Predecessor dependency**: Stage 3 complete; can run in parallel with Wave 4c.
- **Wave parallelism**: 4d runs in parallel with 4c.

### §4.6 Stage 5 — Test

- **L0 → L3 dispatch shape**: L0 dispatches single L3 test-runner subagent.
- **Owned files**: `.local/dogfood/2026-04-30/round_16_pre_dogfood_test_run.json` (CREATE; pytest + dual-spec validator + count_tokens output).
- **Acceptance criteria**:
  - `pytest -xvs tools/` exit 0; ≥ 50 NEW tests added by Wave 4b/4c PASS; total test count grows from v0.3.0's 395 to ≥ 445.
  - `python tools/spec_validator.py --json` (v0.4.0 default mode): 14/14 PASS.
  - `python tools/spec_validator.py --spec .local/research/spec_v0.3.0.md --json`: 11/11 PASS (backward-compat).
  - `python tools/count_tokens.py .agents/skills/si-chip/SKILL.md --json`: metadata ≤ 100; body ≤ 5000.
  - Three-tree drift signal = 0.0 (SHA-256 byte-equality across `.agents/` + `.cursor/` + `.claude/` SKILL.md).
- **Estimated wall-clock**: 15-30 min.
- **Predecessor dependency**: Stage 4 (all 4 waves) complete.
- **Wave parallelism**: N/A.

### §4.7 Stage 6a — Round 16 dogfood (`code_change`)

- **L0 → L3 dispatch shape**: L0 dispatches single L3 dogfood-runner subagent.
- **Owned files**: `.local/dogfood/2026-04-30/round_16/` (CREATE; 6 evidence files per §8.2 + raw artifacts).
  - `basic_ability_profile.yaml`
  - `metrics_report.yaml`
  - `router_floor_report.yaml`
  - `half_retire_decision.yaml`
  - `next_action_plan.yaml`
  - `iteration_delta_report.yaml`
  - `raw/` (OTel traces + pytest log + count_tokens + spec_validator output + token_tier_analyzer output + lifecycle_machine output + health_smoke_check output (vacuous for Si-Chip self) + eval_pack_qa_check output + recovery_harness output)
- **Acceptance criteria**:
  - All v0.4.0 invariants land: `token_tier` block populated; `real_data_samples: []` (Si-Chip self has no live backend); `lifecycle.stage_transition_rules` declared (pointer to spec §20.1); `lifecycle.promotion_history` populated (≥ 1 entry retroactively backfilled for `evaluated → productized` transition over Rounds 1-15); `packaging.health_smoke_check` absent (Si-Chip self has no live backend; vacuous PASS branch).
  - C0 monotonicity 1.0 → 1.0 (carry-forward from Round 15) OR core_goal_test_pack grows by 1-3 cases for v0.4.0 features (e.g. C0 case for `tools/token_tier_analyzer.py --help works`); if pack grows, version bumps `1.0.0` → `1.1.0` and Round 16 re-establishes the new pack baseline; Round 17 monotonicity verifies 1.0 → 1.0 against the new pack.
  - v1_baseline all 9 thresholds PASS (carry-forward from Round 15 except for `iteration_delta`; new code_change clause requires ≥ 1 axis at gate bucket).
  - `iteration_delta` clause: `code_change` round; ≥ 1 axis at v1_baseline bucket (≥ +0.05). Expected axes with movement: `token_delta` (any tier; SKILL.md gained 6 reference rows but body still ≤ 5000); `routing_delta` (no change expected; carry-forward); `governance_risk_delta` (carry-forward at +0.05). Plan B if no axis moves: bump `iteration_delta_report.yaml.headline.weighted_token_delta` to ≥ +0.05 via §18.2 derived formula.
  - 14 spec_validator BLOCKERs PASS (3 NEW + 1 REVISED + 10 unchanged from v0.3.0).
  - Three-tree drift = 0.0 (16th consecutive ALL_TREES_DRIFT_ZERO).
- **Estimated wall-clock**: 30-60 min.
- **Predecessor dependency**: Stage 5 complete.
- **Wave parallelism**: N/A.

### §4.8 Stage 6b — Round 17 dogfood (`measurement_only`)

- **L0 → L3 dispatch shape**: L0 dispatches single L3 dogfood-runner subagent.
- **Owned files**: `.local/dogfood/2026-04-30/round_17/` (CREATE; 6 evidence files per §8.2; replay-byte-identical to Round 16 except for `iteration_delta_report.yaml.headline.round_kind: measurement_only` clause + `monotonicity_only` clause).
- **Acceptance criteria**:
  - C0 monotonicity 1.0 → 1.0 (Round 16 → Round 17; second consecutive non-vacuous monotonicity check after Round 14-15).
  - All metrics replay BYTE-IDENTICAL to Round 16 (no source changes per `measurement_only` clause; demonstrates deterministic replayability).
  - `iteration_delta` clause: `monotonicity_only` (relaxed per §15.2; no axis required to improve; none may regress).
  - 14 spec_validator BLOCKERs PASS (replay).
  - 17th consecutive ALL_TREES_DRIFT_ZERO.
  - **2 consecutive PASSes at v1_baseline (Round 16 + Round 17) → eligible for ship per §15.4 promotion-counter rule** (mirrors v0.3.0's Round 14 + Round 15 pattern).
- **Estimated wall-clock**: 20-30 min.
- **Predecessor dependency**: Stage 6a complete.
- **Wave parallelism**: N/A.

### §4.9 Stage 7 — Package

- **L0 → L3 dispatch shape**: L0 dispatches single L3 packager subagent.
- **Owned files**:
  - `.local/research/spec_v0.4.0.md` (CREATE; promote from rc1; body byte-identical; frontmatter / H1 / preamble / Reconciliation Log only).
  - `.local/research/spec_v0.4.0-rc1.md` (PIN; retained as historical record per v0.3.0 pinning convention).
  - `.agents/skills/si-chip/SKILL.md` (MODIFY; frontmatter `version: 0.4.0-rc1` → `version: 0.4.0`; spec ref bump `spec_v0.4.0-rc1.md` → `spec_v0.4.0.md`).
  - `.cursor/skills/si-chip/SKILL.md` + `.claude/skills/si-chip/SKILL.md` (MIRROR; auto-synced).
  - `.rules/si-chip-spec.mdc` (MODIFY; frontmatter version → v0.4.0; spec ref bump).
  - `AGENTS.md` (RE-COMPILE; new compile hash recorded).
  - `.rules/.compile-hashes.json` (UPDATE).
  - `docs/skills/si-chip-0.4.0.tar.gz` (CREATE; deterministic tarball; flags `--owner=0 --group=0 --numeric-owner --mtime=2026-04-30 --sort=name --exclude='*/__pycache__' --exclude='si-chip/scripts/test_*.py'`; document SHA-256).
  - `install.sh` (MODIFY; version → v0.4.0).
  - `docs/install.sh` (MODIFY; version → v0.4.0).
  - `docs/install.md` (MODIFY; EN row + CN row version bumps).
  - `CHANGELOG.md` (MODIFY; add `[0.4.0]` section per Keep-a-Changelog convention).
- **Acceptance criteria**:
  - `spec_v0.4.0.md` body byte-identical to `spec_v0.4.0-rc1.md` (verified via `diff`).
  - 3-tree mirror byte-equality post-Stage-7 (`V3_drift_signal = 0.0`).
  - Tarball deterministic (re-run produces identical SHA-256).
  - `count_tokens` post-Stage-7: metadata ≤ 100 (v2_tightened ceiling); body ≤ 5000 (v1_baseline ceiling).
  - All test artifacts re-validate cleanly: `python tools/spec_validator.py --json` 14/14 PASS; `pytest -xvs tools/` exit 0.
- **Estimated wall-clock**: 30-45 min.
- **Predecessor dependency**: Stage 6b complete.
- **Wave parallelism**: N/A.

### §4.10 Stage 8 — Ship

- **L0 → L3 dispatch shape**: L0 dispatches single L3 ship-author subagent.
- **Owned files**:
  - `.local/dogfood/2026-04-30/v0.4.0_ship_decision.yaml` (CREATE; mirrors `v0.3.0_ship_decision.yaml` structure; explicit `verdict: SHIP_ELIGIBLE` + `ship_gate_achieved: relaxed` + 14/14 BLOCKERs PASS + 17 consecutive v1 passes since Round 1).
  - `.local/dogfood/2026-04-30/v0.4.0_ship_report.md` (CREATE; mirrors `v0.3.0_ship_report.md` structure; the 16-Round Story table; What v0.4.0 Delivered (6 themes); Why v2_tightened Is Deferred (carry-forward); Known Limitations Carried Forward; Cross-Tree Drift; Spec §11 Forever-Out Compliance; Acknowledgments; Ship Verdict).
  - 3 git commits on `feat/v0.4.0-token-economy-real-data-lifecycle`:
    - Commit 1: spec + templates + tools + spec_validator (Wave 4a + 4b + 4c).
    - Commit 2: SKILL.md + 6 references + AGENTS.md re-compile + tarball (Wave 4d + Stage 7).
    - Commit 3: dogfood evidence (Round 16 + Round 17) + ship_decision.yaml + ship_report.md (Stage 6a + 6b + 8).
  - Suggest `gh pr create` command for L0 (do NOT push to main directly per workspace Protected Branch Workflow).
- **Acceptance criteria**:
  - `ship_decision.yaml` machine-validates against `templates/ship_decision.template.yaml`.
  - `ship_report.md` covers all 6 themes + 9 stages + Round 16-17 + 3 risks (subset of §6 risk register).
  - 3 commits land on feat branch with clear scope-grouped messages.
  - `gh pr create` suggestion includes PR title + body template.
- **Estimated wall-clock**: 20-30 min.
- **Predecessor dependency**: Stage 7 complete.
- **Wave parallelism**: N/A.

### §4.11 Stage Decomposition Summary Table

| Stage | Owner | Wall-clock | Predecessor | Parallelism | Owned files |
|---|---|---:|---|:---:|---|
| 0 — L0 setup | L0 | 10-15 min | — | — | feat branch + TodoWrite |
| 1 — Research refresh | L0 (often skipped) | 0-30 min | 0 | — | (optional) r12 refresh |
| 2 — Spec author | L3 | 60-90 min | 0 + 1 | — | spec_v0.4.0-rc1.md |
| 3 — Review | L3 (read-only) | 20-30 min | 2 | — | spec_v0.4.0-rc1_review.md |
| 4a — Schema + 3 templates | L3 | 30-45 min | 3 | with 4b | templates/* |
| 4b — 4 tools | L3 | 60-90 min | 3 | with 4a | tools/* |
| 4c — spec_validator | L3 | 30-45 min | 4a + 4b | with 4d | tools/spec_validator.py |
| 4d — SKILL.md + 6 refs | L3 | 45-60 min | 3 (+ 4a recommended) | with 4c | .agents/.cursor/.claude/* |
| 5 — Test | L3 | 15-30 min | 4 (all waves) | — | round_16_pre_test_run |
| 6a — Round 16 dogfood | L3 | 30-60 min | 5 | — | round_16/* |
| 6b — Round 17 dogfood | L3 | 20-30 min | 6a | — | round_17/* |
| 7 — Package | L3 | 30-45 min | 6b | — | spec_v0.4.0.md + tarball |
| 8 — Ship | L3 | 20-30 min | 7 | — | ship_decision + ship_report + 3 commits |
| **Total** | | **5-7 hours** | | | |

---

## §5 Multi-Round Dogfood Plan

### §5.1 Per-round detail

#### §5.1.1 Round 16 — `code_change`

- **Round kind**: `code_change` (per §15.1; iteration_delta clause = `strict` per §15.2).
- **Goal**: All v0.4.0 features land; produce 6 evidence files (no `ship_decision.yaml` yet — that's Round 19's `ship_prep`).
- **Source changes allowed**: YES (per §15.2 `code_change` row).
- **Required outputs**:
  - `basic_ability_profile.yaml` with `token_tier`, `real_data_samples: []`, `lifecycle.{stage_transition_rules, promotion_history}`, `packaging.health_smoke_check: <absent>` (Si-Chip self has no live backend).
  - `metrics_report.yaml` with `token_tier.{C7, C8, C9}` non-null integers + `promotion_state.{current_gate: v1_baseline, consecutive_passes: 16, promotable_to: v2_tightened, last_promotion_round_id: round_15}`.
  - `iteration_delta_report.yaml` with `headline.weighted_token_delta` (per §18.2 derived formula) + `tier_transitions: []` (no tier moves expected if SKILL.md only grew references; tier_transitions would populate if author moved content between tiers).
  - `next_action_plan.yaml` with `round_kind: code_change`, `token_tier_target: standard`, `actions[].real_data_verification: {fixtures_count: 0, provenance: vacuous}` for Si-Chip self.
  - 6 standard evidence files; raw artifacts include outputs of all 4 new tools.
- **Acceptance**:
  - C0 = 1.0 (5/5 cases pass; or 6-8/6-8 if pack grows for v0.4.0 features).
  - C0 monotonicity vs Round 15: 1.0 ≥ 1.0 PASS (carry-forward; non-vacuous since Round 15 had non-vacuous monotonicity established).
  - v1_baseline all 9 thresholds PASS (carry-forward; Round 15 baseline + new fields don't regress).
  - `iteration_delta_report.yaml.headline` axes ≥ 1 at v1_baseline gate bucket (≥ +0.05).
  - 14 spec_validator BLOCKERs PASS.
  - 16th consecutive ALL_TREES_DRIFT_ZERO.

#### §5.1.2 Round 17 — `measurement_only`

- **Round kind**: `measurement_only` (per §15.1; iteration_delta clause = `monotonicity_only` per §15.2).
- **Goal**: Re-measure same source as Round 16; demonstrate deterministic monotonicity; **canonical demonstration of token_tier metrics + real-data verification + lifecycle_machinery on Si-Chip self**.
- **Source changes allowed**: NO (per §15.2 `measurement_only` row; mixed-kind prohibition per §15.1).
- **Required outputs**: 6 standard evidence files; replay-byte-identical to Round 16 except for `next_action_plan.yaml.round_kind: measurement_only` + `iteration_delta_report.yaml.headline.iteration_delta_clause: monotonicity_only`.
- **Acceptance**:
  - C0 = 1.0 (replay).
  - C0 monotonicity vs Round 16: 1.0 ≥ 1.0 PASS (second consecutive non-vacuous monotonicity check; mirrors v0.3.0's Round 14 → Round 15).
  - All metrics byte-identical to Round 16 (deterministic replayability).
  - `iteration_delta_report.yaml.headline` axes RELAXED (no axis required to improve; none may regress).
  - 14 spec_validator BLOCKERs PASS.
  - 17th consecutive ALL_TREES_DRIFT_ZERO.
  - **2 consecutive PASSes at v1_baseline (Round 16 `code_change` + Round 17 `measurement_only`) per §15.4 promotion-counter eligibility → SHIP-ELIGIBLE at v1_baseline gate**. (Mirrors v0.3.0 ship pattern exactly.)

#### §5.1.3 Round 18 — optional `code_change` or `measurement_only` (contingency)

- **Round kind**: `code_change` if Round 17 surfaces a regression that requires source fix; otherwise `measurement_only` (3rd replay).
- **Goal**: Address any regression OR provide additional replay evidence.
- **Source changes allowed**: YES if `code_change`; NO if `measurement_only`.
- **Plan budget**: include in plan but do NOT commit. If Round 17 PASSes cleanly, Round 18 SKIPPED and Stage 7 packaging proceeds directly.
- **Acceptance** (if executed): C0 = 1.0; C0 monotonicity vs Round 17 PASS; v1_baseline thresholds PASS; iteration_delta clause per `round_kind`; 14 BLOCKERs PASS.

#### §5.1.4 Round 19 — `ship_prep`

- **Round kind**: `ship_prep` (per §15.1; iteration_delta clause = `WAIVED` per §15.2).
- **Goal**: v0.4.0 finalization round; produces 7 evidence files including `ship_decision.yaml` (per §20.4 schema; the NEW 7th evidence file per Theme 3).
- **Source changes allowed**: YES (version bumps + tarball; no functional change per §15.2 `ship_prep` row).
- **Required outputs**: 6 standard evidence files + `ship_decision.yaml` (7th file).
- **Acceptance**:
  - C0 = 1.0 (replay; no source changes affect core_goal cases except spec/version bump strings).
  - C0 monotonicity vs Round 17 (or Round 18 if executed): 1.0 ≥ 1.0 PASS.
  - v1_baseline all 9 thresholds PASS (replay; ship_prep doesn't move metrics).
  - `iteration_delta` clause WAIVED per §15.2.
  - 14 spec_validator BLOCKERs PASS, including REVISED `EVIDENCE_FILES` BLOCKER at the 7-file branch.
  - `ship_decision.yaml` machine-validates against `templates/ship_decision.template.yaml`.
  - Stage 7 + Stage 8 deliverables emitted: tarball SHA-256 documented; `v0.4.0_ship_decision.yaml` + `v0.4.0_ship_report.md` populated; 3 git commits suggested.

#### §5.1.5 Round 20 — optional post-ship `measurement_only` sanity check

- **Round kind**: `measurement_only`.
- **Goal**: Post-Stage-7 SKILL.md re-measurement (Stage 7 may have re-bumped SKILL.md frontmatter `0.4.0-rc1` → `0.4.0`; Round 19 evidence captured the rc1 SKILL.md; Round 20 captures the post-Stage-7 SKILL.md). Mirrors v0.3.0's Round 15 + post-Stage-7 SKILL.md re-measurement note in `v0.3.0_ship_decision.yaml.machine_checks.count_tokens_skill_md_post_stage_7`.
- **Source changes allowed**: NO.
- **Plan budget**: include in plan but do NOT commit. If Stage 7 re-bump produces no SKILL.md drift (e.g. only frontmatter version bump = ~6 metadata token shift), Round 20 SKIPPED and the post-Stage-7 numbers are documented in `v0.4.0_ship_decision.yaml` directly.
- **Acceptance** (if executed): same as Round 17.

### §5.2 Exit criteria for ship

**SHIP-ELIGIBLE at gate `relaxed` (= `v1_baseline`)** when ALL of:

1. **2 consecutive PASSes at v1_baseline**: Round 16 (`code_change`) + Round 17 (`measurement_only`) per §15.4 promotion-counter eligibility.
2. **C0 monotonicity ≥ 1.0** for both Round 16 and Round 17.
3. **token_tier block populated** non-null for Si-Chip self (C7/C8/C9 integer values).
4. **real_data_samples field present** (may be `[]` for Si-Chip self).
5. **At least one ship_decision artifact emitted**: Round 19 `ship_prep` produces `ship_decision.yaml` per §20.4.
6. **14/14 spec_validator BLOCKERs PASS** in v0.4.0 default mode.
7. **3-tree mirror drift = 0.0** (V3_drift_signal verified at Stage 7 close).
8. **§11 forever-out re-check**: all 4 items UNCHANGED across §18-§23.

### §5.3 Carry-forward limitations (NOT v0.4.0 ship blockers)

| Limitation | Why carry-forward | v0.5.0+ trigger |
|---|---|---|
| `T2_pass_k = 0.5478 < 0.55` (v2_tightened) | Real-LLM runner blocked by sandbox; same since v0.2.0. | Sandbox gains LLM API auth + outbound https. |
| `G2/G3/G4 null` | Cross-domain / OOD / model-version-stability; depends on real-LLM. | Real-LLM runner lands. |
| `L5/L6/L7 null` | detour_index / replanning_rate / think_act_split; depends on real-LLM traces. | Real-LLM runner lands. |
| `R1/R2 null at canonical 6-case derivation` | informational; not hoisted in v0.3.0. | informational (not a blocker). |
| `R8 method=tfidf_cosine_mean implemented but not hoisted` | max_jaccard chosen as Round 9 default. | informational (not a blocker). |
| `C5 heuristic proxy` | deterministic formula vs ground-truth. | informational (not a blocker). |
| `U4 dry-run floor estimate` | real wall-clock with network not measured. | §23.5 v0.4.0 add-on adds `state ∈ {warm, cold, semicold}` companion field — incremental honesty improvement, not a full unblock. |
| `V2 pattern-based scanner` | no entropy-based detection; truffleHog/gitleaks deferred. | informational (not a blocker). |
| `§6.4 trigger 2/5/6 catalog/log not yet seeded` | detector parameterised-off in v0.1.12+; opt-in for future rounds. | informational (not a blocker). |

All 9 are v0.4.x or v0.5.0+ candidates; none block v0.4.0 ship at v1_baseline.

---

## §6 Risk Register

> ≥ 6 risks ranked by impact. Each: name, severity (BLOCKER/MAJOR/MINOR), likelihood (H/M/L), mitigation, owner.

### §6.1 R-1: §6.1 axis-break (Q4) decision risk

- **Severity**: BLOCKER if user/L0 chooses Option B without explicit reconciliation log entry; MAJOR otherwise.
- **Likelihood**: M (default Option A is recommended; Option B requires user/L0 override).
- **Mitigation**: §3 of this plan documents Option A as default + Option B as override path (§3.4). User/L0 decides at Stage 0 (before Stage 2 spec authoring begins). If Option B chosen, Stage 2 spec author MUST add reconciliation log entry per §3.4.
- **Owner**: User + L0 (decision); L3 spec-author (implementation).

### §6.2 R-2: C7/C8/C9 placement (Q1) decision risk

- **Severity**: MAJOR (if placement is wrong, §3.1 R6 7×37 frozen count breaks; reconciliation log entry needed mirroring v0.1.0 → v0.2.0-rc1 prose count "28 → 37" pattern).
- **Likelihood**: L (this plan recommends top-level invariant block per r12 §5.1; matches v0.3.0 §14 C0 placement precedent).
- **Mitigation**: §2.1.1 + §3 explicitly document top-level placement. Stage 2 spec author MUST cite §14 C0 placement precedent in §18.1 spec text. Stage 3 reviewer MUST cross-check that §18 doesn't change §3.1 R6 count.
- **Owner**: L3 spec-author (implementation); L3 reviewer (verification).

### §6.3 R-3: Real-data verification needs sandbox-aware fixtures

- **Severity**: MAJOR (Si-Chip sandbox lacks live LLM API; real-LLM runner deferred since v0.2.0).
- **Likelihood**: H (sandbox limitation is unchanged).
- **Mitigation**: §2.2 ships **deterministic SHA-256 fixture simulator pattern** for v0.4.0; real-LLM runner deferred to v0.5.0+. `tools/real_data_verifier.py` operates on **test fixture files** (not live HTTP probes); this is sandbox-safe. `tools/health_smoke_check.py` adds `--mock-mode` for sandbox runs. For Si-Chip self (no live backend), all real_data_samples paths are vacuous (empty list) — Round 16 + 17 sail through.
- **Owner**: L3 wave-author (Wave 4b implementation); L3 dogfood-runner (Round 16 + 17 verification).

### §6.4 R-4: §8.2 evidence files 6 → 7 break

- **Severity**: MAJOR if not gated by `round_kind`; MINOR with conditional gating per §2.3.4 REVISED `EVIDENCE_FILES` BLOCKER.
- **Likelihood**: M (the conditional gating is an additive complexity).
- **Mitigation**: §2.3.4 REVISED `EVIDENCE_FILES` BLOCKER makes `ship_decision.yaml` REQUIRED only for `round_kind=ship_prep`; existing 6 files unchanged for `round_kind ∈ {code_change, measurement_only, maintenance}`. Backward-compat for v0.1.0 / v0.2.0 / v0.3.0 spec modes preserves the unconditional 6-file count. Stage 5 test suite includes ≥ 4 BLOCKER-revision tests covering all 4 round_kind values.
- **Owner**: L3 wave-author (Wave 4c implementation); L3 dogfood-runner (Round 19 ship_prep verification).

### §6.5 R-5: spec_validator backward-compat for v0.3.0 artifacts

- **Severity**: MEDIUM (backward-compat regression would break v0.3.0 evidence replay).
- **Likelihood**: M (4 NEW BLOCKER additions + 1 BLOCKER revision is moderate complexity).
- **Mitigation**: Mirror v0.3.0 wave 2a `EXPECTED_BAP_KEYS_BY_SCHEMA` pattern: each NEW BLOCKER has version-aware logic that silently skips for `v0.1.0 / v0.2.0 / v0.3.0` spec modes. Stage 5 test suite explicitly tests `python tools/spec_validator.py --spec .local/research/spec_v0.3.0.md --json` returns 11/11 PASS (NOT 14/14 — backward-compat must NOT introduce false BLOCKER hits on v0.3.0 artifacts).
- **Owner**: L3 wave-author (Wave 4c implementation); L3 test-runner (Stage 5 verification).

### §6.6 R-6: SKILL.md body token budget overrun

- **Severity**: MEDIUM (v0.3.0 SKILL.md is at 3022/5000 body tokens; adding 6 reference-row entries + Token-Tier subsection + Real-Data subsection + Lifecycle subsection + Healthcheck subsection + Eval-Pack subsection + Measurement-Honesty subsection may push close to 5000).
- **Likelihood**: M (6 themes × ~200-400 tokens each could add 1200-2400 tokens; risks v1_baseline ≤ 5000 ceiling).
- **Mitigation**: Aggressive reference-doc offloading per v0.3.0 wave 2b discipline. Each theme gets a dedicated `references/<theme>-r12-summary.md` (≤ 150 lines each); SKILL.md body only carries 1-3 line invariant declarations per theme + a pointer line. Stage 4 wave 4d explicitly budgets SKILL.md body ≤ 4500 tokens (leaves ≥ 500 token headroom under the 5000 ceiling). If body exceeds 4500 in Stage 4 dry-run, wave 4d SHOULD compress one of the v0.3.0 sections (§14 / §15 / §16 invariants summary) by referring to the existing v0.3.0 reference docs.
- **Owner**: L3 wave-author (Wave 4d implementation); L3 test-runner (Stage 5 count_tokens verification).

### §6.7 R-7: Cycle 4 chip-usage-helper round numbering

- **Severity**: MINOR (out of v0.4.0 scope; flagged for follow-up).
- **Likelihood**: L (does not affect v0.4.0 ship).
- **Mitigation**: SUMMARY.md says Cycle 4 = v1.0.0 team-leaderboards = Rounds 20-23 but the per-round files (`round_20.md` … `round_23.md`) are missing from `.local/feedbacks/feedbacks_while_using/chip-usage-helper/`. r12 §8 explicitly notes this. The SUMMARY.md's recap section still summarizes Cycle 4 narratively (4 metrics: agent-hours leaderboards), so plan integrity is not compromised. Recommend: flag to user that round_20-23 files are pending creation; treat them as v0.5.0+ input ONLY when the missing files materialize.
- **Owner**: User (or L0) for source-file follow-up; v0.5.0+ research stage as ingestion target.

### §6.8 R-8: Stage 4 wave parallelism wedging

- **Severity**: MINOR (wave dependencies are clear in §4.5; risk is logistical not technical).
- **Likelihood**: L (Wave 4a + 4b are disjoint; Wave 4c depends on 4a + 4b but parallel-eligible with 4d).
- **Mitigation**: §4.5 documents per-wave file ownership + predecessor dependency table. L0 should dispatch Wave 4a + 4b in parallel (single message with two Task tool calls) only when both have clear scope. If a wave needs to backtrack into another wave's owned files, the wedging is detected via git pre-commit hook (file-ownership annotation per wave commit message convention).
- **Owner**: L0 (dispatch sequencing); L3 wave-authors (file ownership compliance).

### §6.9 R-9: Round 16 iteration_delta strict-clause failure

- **Severity**: MEDIUM (if Round 16 doesn't move ≥ 1 axis at v1_baseline gate bucket, ship-eligibility blocked).
- **Likelihood**: L (multiple paths to satisfy: token_delta from SKILL.md additions; routing_delta from R3 split if it changes aggregate; governance_risk_delta from `lifecycle.promotion_history` formalization; or `headline.weighted_token_delta` derived ≥ +0.05 from C7/C8 reductions).
- **Mitigation**: Stage 6a Round 16 explicitly checks ≥ 1 axis at gate bucket. Plan B if no axis moves: bump `iteration_delta_report.yaml.headline.weighted_token_delta` to ≥ +0.05 via §18.2 derived formula (requires moving content between EAGER/ON-CALL/LAZY tiers in Round 16's source changes — mirroring chip-usage-helper Round 14's tier-transition pattern). If Plan B also fails, Round 18 contingency executes a small token-tier rebalance to satisfy the strict clause.
- **Owner**: L3 dogfood-runner (Round 16 verification).

---

## §7 Acceptance Criteria for the v0.4.0 spec

> Mirrors r11 §9 acceptance criteria pattern (and v0.3.0 spec acceptance pattern). Each is a verifiable PASS/FAIL check.

### §7.1 Spec text acceptance

| # | Criterion | Verification method |
|---|---|---|
| 1 | All v0.3.0 §3 / §4 / §5 / §6 (Option A) / §7 / §8 / §11 / §13 / §14 / §15 / §17 main bodies byte-identical to v0.3.0 | `diff .local/research/spec_v0.3.0.md .local/research/spec_v0.4.0.md` shows changes ONLY in §6 (if Option B), §16-17 footers (additive add-on sentences), and NEW §18-§23 sections + Reconciliation Log. |
| 2 | 6 NEW Normative sections present (§18 through §23) | `grep -E '^## (18\|19\|20\|21\|22\|23)' .local/research/spec_v0.4.0.md` returns 6 lines. |
| 3 | 3 NEW hard rules §17.3 / §17.4 / §17.5 added | `grep -E '^### \(17\\.\(3\|4\|5\)\\.' .local/research/spec_v0.4.0.md` returns 3 lines. |
| 4 | spec_validator grows 11 → 14 BLOCKERs; backward-compat preserved | `python tools/spec_validator.py --json` (v0.4.0 default) returns 14/14 PASS; `python tools/spec_validator.py --spec .local/research/spec_v0.3.0.md --json` returns 11/11 PASS; same for v0.2.0 and v0.1.0 spec modes. |
| 5 | §11 forever-out re-affirmed verbatim in §18-§23 footers (6 footers) | `grep -A 5 -E 'forever-out|永久' .local/research/spec_v0.4.0.md` returns 6+ matched blocks; cross-check against §11.1 4-item list verbatim. |
| 6 | Reconciliation Log entry documents all 6 themes + 3 hard rules + Q4 §6.1 decision | Reconciliation Log section present at spec end; mirrors v0.3.0's "Reconciliation Log" section format. |

### §7.2 Multi-round dogfood evidence acceptance

| # | Criterion | Verification method |
|---|---|---|
| 7 | Round 16 + Round 17 BOTH PASS at v1_baseline | `cat .local/dogfood/2026-04-30/round_{16,17}/iteration_delta_report.yaml` shows v1_baseline PASS for both. |
| 8 | iteration_delta + monotonicity + C0 all green for Round 16-17 | Round 16 has ≥ 1 axis at gate bucket (≥ +0.05); Round 17 monotonicity_only RELAXED clause; C0 = 1.0 both rounds. |
| 9 | token_tier metrics populated for Si-Chip self | Round 16 + 17 `metrics_report.yaml.token_tier.{C7, C8, C9}` non-null integers. |
| 10 | real_data_samples field present (empty for Si-Chip self) | Round 16 + 17 `basic_ability_profile.yaml.real_data_samples: []`. |
| 11 | ship_decision.yaml emitted for ship_prep round | Round 19 `ship_decision.yaml` exists; machine-validates against `templates/ship_decision.template.yaml`. |
| 12 | C0 monotonicity 1.0 → 1.0 for Round 16 → Round 17 | Round 17's `metrics_report.yaml.c0_no_regression_vs_round_16: true`. |

### §7.3 Packaging acceptance

| # | Criterion | Verification method |
|---|---|---|
| 13 | Tarball deterministic + SHA-256 documented | `sha256sum docs/skills/si-chip-0.4.0.tar.gz` matches `v0.4.0_ship_decision.yaml.stage_7_deliverables.tarball_sha256`. |
| 14 | SKILL.md → 0.4.0; mirrors byte-identical (V3_drift_signal = 0.0) | `sha256sum .agents/skills/si-chip/SKILL.md .cursor/skills/si-chip/SKILL.md .claude/skills/si-chip/SKILL.md` returns 3 identical hashes. |
| 15 | 3 NEW templates added (real_data_samples + ship_decision + recovery_harness); 1 NEW reference doc (eval_pack_qa_checklist.md) | `ls templates/` shows 6 v0.3.0 templates + 3 NEW = 9 YAML templates + 1 NEW Markdown reference doc. |
| 16 | Existing templates `$schema_version` bumped 0.2.0 → 0.3.0 | `grep '$schema_version' templates/*.yaml` shows 0.3.0 for `basic_ability_profile.schema.yaml`, `iteration_delta_report.template.yaml`, `next_action_plan.template.yaml`. |

### §7.4 Behavior acceptance

| # | Criterion | Verification method |
|---|---|---|
| 17 | All NEW tools have ≥ 8 unit tests each | `pytest -xvs tools/test_token_tier_analyzer.py` ≥ 12 PASS; `tools/test_real_data_verifier.py` ≥ 8 PASS; `tools/test_lifecycle_machine.py` ≥ 8 PASS; `tools/test_health_smoke_check.py` ≥ 8 PASS; total ≥ 36 NEW PASS. |
| 18 | Existing tool extensions PASS ≥ 20 NEW tests | `tools/test_eval_skill.py` extension ≥ 16 PASS; `tools/test_cjk_trigger_eval.py` extension ≥ 4 PASS. |
| 19 | spec_validator extension PASSes ≥ 12 tests | `tools/test_spec_validator.py` ≥ 12 NEW PASS (covering BLOCKER 12-14 + REVISED EVIDENCE_FILES + backward-compat). |
| 20 | Total test count grows v0.3.0 395 → ≥ 445 | `pytest -xvs tools/ --co` shows total test count ≥ 445. |

### §7.5 Forever-out re-affirmation acceptance

| # | Criterion | Verification method |
|---|---|---|
| 21 | §11 forever-out items unchanged across §18-§23 | Spec §18.7, §19.4, §20.5, §21.5, §22.8, §23.11 each contain verbatim §11.1 4-item list. |
| 22 | No marketplace surface introduced | `grep -i 'marketplace\|market' .local/research/spec_v0.4.0.md` returns only §11.1 + §18.7-§23.11 footers (re-affirmation contexts). |
| 23 | No router-model-training surface | `grep -i 'train\|router model\|learned weight' .local/research/spec_v0.4.0.md` returns only §11.1 + §18.7-§23.11 footers + §5 spec text (existing in v0.3.0). |
| 24 | No generic IDE compat layer | `grep -i 'IDE\|runtime compat' .local/research/spec_v0.4.0.md` returns only §7 (existing in v0.3.0) + §11.1 + footers. |
| 25 | No MD-to-CLI converter | `grep -i 'markdown.to.cli\|md-to-cli' .local/research/spec_v0.4.0.md` returns only §11.1 + footers. |

---

## §8 Out-of-Scope (forever-out re-affirmation)

> Mirrors §1.2 with explicit cross-references to §11.1 verbatim items + v0.4.0-specific deferrals.

### §8.1 §11.1 forever-out items (verbatim from spec_v0.3.0.md §11.1)

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

### §8.2 Re-affirmation per v0.4.0 theme (Stage 3 reviewer must verify)

| Theme | §11 risk surface | Re-affirmation |
|---|---|---|
| §18 Token Economy | Marketplace risk: token_tier observability could be misread as "skill performance leaderboard" surface. | §18.7 footer states explicitly: "Token-tier metrics are per-ability local artifacts; NO cross-ability ranking surface; NO public registry." |
| §19 Real-Data Verification | Marketplace risk: `real_data_samples` could be misread as "shared payload library". | §19.4 footer states explicitly: "real_data_samples are per-ability test infrastructure; NO cross-ability fixture broker." |
| §20 Lifecycle State Machine | Router-model-training risk: stage_transition_rules could be misread as "trained classifier". | §20.5 footer states explicitly: "stage_transition_rules are deterministic Boolean conditions; NO learned weights; NO online learning." |
| §21 Health Smoke Check | IDE-compat risk: `health_smoke_check` could be misread as "Kubernetes-style runtime probe". | §21.5 footer states explicitly: "health_smoke_check is local probe config; NO orchestrator binding; NO IDE adaptation surface." |
| §22 Eval-Pack QA | MD-to-CLI risk: `eval_pack_qa_checklist.md` could be misread as "auto-derived from SKILL.md converter". | §22.8 footer states explicitly: "eval_pack_qa_checklist.md is hand-authored Informative reference; NO MD-to-CLI conversion." |
| §23 Measurement Honesty | Router-model-training risk: method-tagging companion fields could be misread as "training signal". | §23.11 footer states explicitly: "Method-tagging is metric metadata; NO training signal; NO inference model." |

### §8.3 v0.4.0-specific deferrals (NOT v0.4.0 scope; track for v0.5.0+)

- **Real-LLM runner** (deferred from v0.2.0 already; remains deferred). Sandbox limitation. v0.5.0+ when sandbox gains LLM API.
- **§16 Multi-ability layout Normative promotion**: trigger met (Si-Chip + chip-usage-helper) but explicit ship choice to keep v0.4.0 additive surface small. Track as separate v0.3.x or v0.4.x bump.
- **GEPA-style reflective `improve` step** (r12 §0 bullet 7). v0.5.0+ seed.
- **ACE Skillbook helpful/harmful counters as Normative** (r12 §5.6). v0.5.0+ candidate.
- **Ecosystem-specific packaging guidelines** (R35 / R38 / R40). Per-ecosystem; document if relevant; do NOT codify.

---

## §9 Estimated Effort & Timeline

| Stage | Wall-clock | Notes |
|---|---:|---|
| Stage 0-1 (setup + research-refresh) | 30 min | r12 still current; refresh likely SKIPPED. |
| Stage 2 (spec author) | 60-90 min | 1216 lines for v0.3.0; expect ~1500-1800 for v0.4.0 (6 NEW Normative sections × ~150 lines each + Reconciliation Log expansion). |
| Stage 3 (review) | 20-30 min | Read-only L3 reviewer; 1 round ≤ 10 findings; iteration if needed. |
| Stage 4 wave 4a (templates) | 30-45 min | Parallel with 4b. |
| Stage 4 wave 4b (tools) | 60-90 min | Parallel with 4a; 4 NEW tools (~1100 LoC + ~1100 LoC tests = ~2200 LoC). |
| Stage 4 wave 4c (spec_validator) | 30-45 min | Parallel with 4d; depends on 4a + 4b. |
| Stage 4 wave 4d (SKILL.md) | 45-60 min | Parallel with 4c. |
| Stage 4 total (waves) | 90-120 min | 4a + 4b run in parallel; 4c + 4d run in parallel after. |
| Stage 5 (test) | 15-30 min | pytest + spec_validator + count_tokens. |
| Stage 6a (Round 16) | 30-60 min | 6 evidence files + raw artifacts. |
| Stage 6b (Round 17) | 20-30 min | Replay; deterministic. |
| Stage 7 (package) | 30-45 min | spec rc1 → frozen; SKILL.md bump; tarball; CHANGELOG. |
| Stage 8 (ship) | 20-30 min | ship_decision + ship_report + 3 commits. |
| **Total** | **~5-7 hours** | **1 working day with parallel waves; 2 days conservative.** |

**Cumulative effort comparison**:
- v0.2.0 ship: ~3 days (per v0.2.0 ship report).
- v0.3.0 ship: ~3 days (per v0.3.0 ship report; "single-day-burst").
- v0.4.0 ship (planned): **1 working day with parallel waves; 2 days conservative**. The wave parallelism (4a+4b parallel; 4c+4d parallel) is the main saving over a sequential v0.3.0-style burst.

---

## §10 Open Questions for User / L0

> Cross-ref r12 §5 + new ones surfaced by this plan. Each with a recommended resolution.

### §10.1 Q1 — C7/C8/C9 placement (cross-ref r12 §5.1)

- **Question**: Should `C7/C8/C9` token-tier sub-metrics be top-level invariant block OR R6 D2 sub-metrics 7-9?
- **Recommendation**: **Top-level invariant block** (matches r12 §5.1; mirrors v0.3.0 §14 C0 placement; preserves §3.1 R6 7×37 frozen count).
- **Override path**: If user/L0 wants D2 sub-metrics, §3.1 R6 count moves 37 → 40; §13.4 prose anchor changes 37 → 40; spec_validator BLOCKER updates `EXPECTED_R6_PROSE_BY_SPEC["v0.4.0"] = 40`.

### §10.2 Q2 — Real-data verification placement (cross-ref r12 §5.2)

- **Question**: Should real-data verification be a 9th step in §8.1 OR a sub-step of `evaluate`?
- **Recommendation**: **Sub-step of `evaluate`** (preserves §8.1 8-step byte-identical; r12 §5.2 default lean).
- **Override path**: If user/L0 wants 9th step, §8.1 expands to 9 steps; spec_validator `EXPECTED_DOGFOOD_STEPS_COUNT_BY_SPEC["v0.4.0"] = 9`; templates/next_action_plan.template.yaml `step` enum bumps to 9 values.

### §10.3 Q3 — health_smoke_check field vs tooling-only (cross-ref r12 §5.3)

- **Question**: Should `health_smoke_check` be a `BasicAbilityProfile` field OR tooling-only (no spec field)?
- **Recommendation**: **Spec field (§21) + packaging-gate enforcement, but Optional + REQUIRED-if-live-backend** (matches r12 §5.3 default lean).
- **Override path**: If user/L0 prefers tooling-only, drop §21 from spec; ship `tools/health_smoke_check.py` standalone; add §8 step 8 informative note.

### §10.4 Q4 — §6.1 value_vector axis-break (cross-ref r12 §5.4)

- **Question**: Should §6.1 value_vector extend 7 → 8 axes (add `eager_token_delta`)?
- **Recommendation**: **Option A — keep 7 axes byte-identical; surface weighted_token_delta as derived headline** (this plan defaults to Option A; rationale per §3 critical-path decision).
- **Override path**: §3.4 documents Option B implementation steps if user/L0 chooses to break §6.1 byte-identical.

### §10.5 Q5 — Real-LLM runner unblock timing (cross-ref r12 §5.5)

- **Question**: Should v0.4.0 open the deferred items from v0.2.0 (real-LLM runner for T2 v2_tightened, G2/G3/G4)?
- **Recommendation**: **Keep deferred for v0.4.0**; open in v0.4.1+ once §18-§23 themes have shipped (matches r12 §5.5 default lean).
- **Override path**: If real-LLM runner opens in v0.4.0, add §5.3 router-test harness `--real-llm-mode` flag; spec_validator updates `EXPECTED_R6_PROSE_BY_SPEC` if G2/G3/G4 honestly emit; Stage 4 tooling work doubles.

### §10.6 Q6 — ACE-style helpful/harmful/neutral counters (cross-ref r12 §5.6)

- **Question**: Should v0.4.0 first-class `BasicAbility.lifecycle.usage_signals: {helpful_30d, harmful_30d, neutral_30d}` field?
- **Recommendation**: **Informative for v0.4.0; promote Normative for v0.5.0** if 2+ abilities show usage-frequency-driven reactivation evidence.
- **Override path**: If Normative @ v0.4.0, `tools/eval_skill.py` needs telemetry ingestion (where do `helpful++` events come from? OTel? user feedback button? agent log lines?). One more BLOCKER added.

### §10.7 Q7 — GEPA novelty bonus axis (cross-ref r12 §5.7)

- **Question**: Should v0.4.0 add a "novelty bonus" axis alongside C0 strict-no-regression?
- **Recommendation**: **No spec change for v0.4.0**; Informative §17.3 forward-pointer only (matches r12 §5.7).
- **Override path**: N/A (recommended path is no-action).

### §10.8 NEW Q8 — Feat branch name preference

- **Question**: What feat branch name? Options:
  - `feat/v0.4.0-token-economy-real-data-lifecycle` (long but informative; recommended).
  - `feat/v0.4.0-token-economy-and-real-data` (task brief suggestion).
  - `feat/v0.4.0` (terse).
- **Recommendation**: `feat/v0.4.0-token-economy-real-data-lifecycle` (descriptive; matches v0.3.0 `feat/v0.3.0-core-goal-invariant` convention of "feat/v<x.y.z>-<theme>").
- **Override path**: User/L0 picks at Stage 0.

### §10.9 NEW Q9 — Cycle 4 chip-usage-helper round_20-23 ingestion

- **Question**: Should Cycle 4 (rounds 20-23) chip-usage-helper feedback be ingested for v0.4.0, OR treat as v0.5.0 input?
- **Recommendation**: **v0.5.0 input**. The per-round files (`round_20.md` … `round_23.md`) are missing from `.local/feedbacks/feedbacks_while_using/chip-usage-helper/` (per r12 §8 + this plan §6.7). SUMMARY.md's narrative recap covers Cycle 4 thematically (4 metrics: agent-hours leaderboards) but no detailed R-items derived; ingestion would be premature without the source files.
- **Override path**: If user provides round_20-23 files, optional v0.4.x point release ingests them.

### §10.10 NEW Q10 — v0.4.0 dogfood round numbering

- **Question**: Should v0.4.0 dogfood rounds keep continuous numbering (Round 16, 17, 18, 19, 20) OR restart at Round 1 under the new ability layout?
- **Recommendation**: **Continuous numbering (Round 16, 17, 18, 19, 20)**. Si-Chip self stays at the backwards-compatible `.local/dogfood/<DATE>/round_<N>/` path per v0.3.0 §16 convention; rounds are the linear sequence on the same ability. Restarting at Round 1 would break the multi-round_evidence carry-forward chain in `ship_decision.yaml`.
- **Override path**: If multi-ability layout migration happens in v0.4.0 instead of being deferred (§1.2 deferral), Si-Chip self's round numbering could restart at Round 1 under `.local/dogfood/<DATE>/abilities/si-chip/round_<N>/` — but this is a v0.3.x or v0.4.x separate ship per §1.2.

---

## §11 Cross-References (Tables)

### §11.1 R-item × theme × stage

| R# | Cluster | v0.4.0 theme (§2.X) | Stage where it lands |
|---|---|---|---|
| R3 | measurement_quality | §2.5 (Eval-Pack QA) | Stage 4 wave 4a (template) + 4b (eval_skill flag) |
| R6 | lifecycle_machinery | §2.3 (Lifecycle State Machine) — `promotion_state` | Stage 4 wave 4a (template) + 4b (lifecycle_machine) |
| R8 | measurement_quality | §2.6 (Measurement Honesty) — recovery_harness | Stage 4 wave 4a (template) |
| R14 | measurement_quality | §2.5 (Eval-Pack QA) — G1 provenance | Stage 4 wave 4a (template) |
| R15 | lifecycle_machinery | §2.3 (Lifecycle State Machine) — stage_transition_rules | Stage 4 wave 4a (template) + 4b (lifecycle_machine) |
| R17 | lifecycle_machinery | §2.3 (Lifecycle State Machine) — promotion_history | Stage 4 wave 4a (template) + 4b (lifecycle_machine) |
| R19 | measurement_quality | §2.6 (Measurement Honesty) — U4 warm/cold | Stage 4 wave 4b (eval_skill flag) |
| R25 | measurement_quality | §2.5 (Eval-Pack QA) — checklist | Stage 4 wave 4a (Markdown reference doc) |
| R27 | lifecycle_machinery | §2.3 (Lifecycle State Machine) — ship_decision.yaml as 7th evidence file | Stage 4 wave 4a (template) + 4c (BLOCKER REVISION) |
| R29 | measurement_quality | §2.6 (Measurement Honesty) — U1 language_breakdown | Stage 4 wave 4b (eval_skill flag) |
| R30 | token_economy | §2.1 (Token-Tier MVP-8 Promotion) — C7/C8/C9 | Stage 4 wave 4a (template) + 4b (token_tier_analyzer) |
| R31 | token_economy | §2.6 (Measurement Honesty) — MCP text default-compact warning | Stage 4 wave 4b (eval_skill flag) |
| R32 | token_economy | §2.1 (Token-Tier MVP-8 Promotion) — EAGER-weighted iteration_delta | Stage 4 wave 4a (template) + 4b (eval_skill helper) |
| R33 | token_economy / measurement_quality | §2.1 (Token-Tier MVP-8 Promotion) — R3 split | Stage 4 wave 4b (cjk_trigger_eval extension) |
| R34 | token_economy | §2.1 (Token-Tier MVP-8 Promotion) — tier_transitions matrix | Stage 4 wave 4a (template) + 4b (token_tier_analyzer) |
| R36 | measurement_quality | §2.6 (Measurement Honesty) — tokens_estimate_method | Stage 4 wave 4b (eval_skill flag) |
| R37 | token_economy | §2.1 (Token-Tier MVP-8 Promotion) — prose_class taxonomy (Informative) | Stage 4 wave 4d (SKILL.md annotation) |
| R39 | token_economy | §2.6 (Measurement Honesty) — server-cap-vs-client detector | Stage 4 wave 4b (eval_skill flag) |
| R41 | token_economy / packaging_discipline | §2.1 (Token-Tier MVP-8 Promotion) — LAZY-tier guideline (Informative) | Stage 4 wave 4d (SKILL.md guideline) |
| R42 | token_economy | §2.6 (Measurement Honesty) — default-data anti-pattern detector | Stage 4 wave 4b (eval_skill flag) |
| R44 | token_economy / packaging_discipline | §2.1 (Token-Tier MVP-8 Promotion) — rule body ≤ 400 (Informative) | Stage 4 wave 4d (SKILL.md guideline) |
| R45 | real_data_verification | §2.2 (Real-Data Verification) — §19 sub-step | Stage 4 wave 4a (template) + 4b (real_data_verifier) |
| R46 | real_data_verification | §2.2 (Real-Data Verification) — real_data_samples template | Stage 4 wave 4a (template) |
| R47 | healthcheck | §2.4 (Healthcheck Smoke) — health_smoke_check field | Stage 4 wave 4a (template) + 4b (health_smoke_check tool) |

### §11.2 v0.3.0 spec § × proposed v0.4.0 § extension

| v0.3.0 § | v0.4.0 extension | Type |
|---|---|---|
| §2.1 BasicAbility schema | §20 lifecycle.{stage_transition_rules, promotion_history} blocks; §18 token_tier block; §19 real_data_samples field; §21 packaging.health_smoke_check field | additive |
| §3.1 R6 7×37 metric table | NEW §18 top-level token_tier (C7/C8/C9, NOT D2 sub-metrics); preserves R6 7×37 frozen count | additive (preserves count) |
| §3.1 D4 G1 row | "v0.4.0 add-on" sentence: provenance REQUIRED per §22.6 | additive (single-sentence add-on; row Normative byte-identical) |
| §3.1 D6 R3 row | "v0.4.0 add-on" sentence: §18.3 derives R3_eager_only + R3_post_trigger; aggregate byte-identical | additive |
| §3.2 frozen constraints (4) | UNCHANGED for v0.4.0 (§22.5 fixed-seed lives in §22 scope, NOT promoted to §3.2 #5; default to keep §3.2 byte-identical) | byte-identical (preserved) |
| §4.1 row 10 iteration_delta | "v0.4.0 add-on" sentence: §18.2 derived weighted_token_delta as headline; thresholds unchanged | additive |
| §5.3 router-test harness | "v0.4.0 add-on" sentence: 40-prompt minimum recommended for v2_tightened per §22.1 | additive |
| §6.1 value_vector | UNCHANGED for v0.4.0 (Option A; default; 7 axes byte-identical) OR 7 → 8 (Option B; user/L0 override) | Option A: byte-identical. Option B: extension + reconciliation log entry. |
| §7 packaging gate | "v0.4.0 add-on" sentence: §21 adds optional health_smoke_check pre-ship gate | additive |
| §8.1 step 2 evaluate | "v0.4.0 add-on" sentence: §19.2.1 sub-step verifies real-data fixture provenance | additive (no count change; 8 steps byte-identical) |
| §8.1 step 8 package-register | "v0.4.0 add-on" sentence: §21 health_smoke_check pre-ship gate | additive |
| §8.2 evidence files (6) | "v0.4.0 add-on" sentence: 6 → 7 conditional on round_kind=ship_prep per §20.4 | additive (conditional) |
| §9 templates | NEW: real_data_samples, ship_decision, recovery_harness; eval_pack_qa_checklist Markdown reference doc | additive (3 NEW YAML templates + 1 Markdown reference) |
| §11 forever-out | UNCHANGED (verbatim re-affirmed in §18-§23 footers) | byte-identical |
| §13 acceptance | NEW §13.7 acceptance for v0.4.0 (mirrors §13.6 v0.3.0 pattern) | additive |
| §14 core_goal invariant | UNCHANGED | byte-identical |
| §15 round_kind | NEW sibling field `token_tier_target ∈ {relaxed, standard, strict}` | additive (sibling field; 4-value enum byte-identical) |
| §17 hard rules | NEW rules 11 + 12 + 13 (token_tier declared / real_data_samples cited / ship_decision emitted) | additive (10 → 13 hard rules) |

### §11.3 r12 cluster × theme × open question

| r12 cluster | v0.4.0 theme | Open question |
|---|---|---|
| §2.1 token_economy | §2.1 (Token-Tier MVP-8 Promotion) | Q1 (placement) + Q4 (axis-break) |
| §2.2 real_data_verification | §2.2 (Real-Data Verification) | Q2 (placement) |
| §2.3 self_iterating_systems | (informational; §17.3 forward-pointer only) | Q7 (GEPA novelty) |
| §2.4 lifecycle_state_machines | §2.3 (Lifecycle State Machine) | Q6 (ACE counters) |
| §2.5 eval_pack_curation | §2.5 (Eval-Pack QA) + §2.6 (Measurement Honesty) | (no Q; covered by Q1/Q2) |
| §2.6 healthcheck | §2.4 (Healthcheck Smoke) | Q3 (field vs tooling) |

### §11.4 Theme × spec_validator BLOCKER × LoC budget

| Theme | NEW BLOCKERs | LoC budget (tools+tests) | Templates |
|---|---|---:|---|
| §2.1 (Token Economy) | 1 (TOKEN_TIER_FIELD_PRESENT) | ~700-950 | 0 NEW; 3 EXTENDED |
| §2.2 (Real-Data Verification) | 1 (REAL_DATA_SAMPLES_FIELD_PRESENT) | ~400-600 | 1 NEW; 1 EXTENDED |
| §2.3 (Lifecycle State Machine) | 1 (STAGE_TRANSITION_RULES_DECLARED) + 1 REVISED (EVIDENCE_FILES) | ~500-700 | 1 NEW; 2 EXTENDED |
| §2.4 (Healthcheck Smoke) | 0 (folded into BLOCKER 14 sub-check) | ~450-650 | 0 NEW; 1 EXTENDED |
| §2.5 (Eval-Pack QA) | 0 | ~100-200 (extensions) | 1 NEW (Markdown) |
| §2.6 (Measurement Honesty) | 0 | ~250-450 (extensions) | 1 NEW |
| **Total** | **3 NEW + 1 REVISED** | **~2400-3550** | **3 NEW YAML + 1 NEW Markdown + 4 EXTENDED YAML** |

---

## §12 Provenance

> Mirrors r11 §13 / r12 §8 provenance pattern.

- **Author role**: L3 Task Agent for Si-Chip v0.4.0 planning effort, Stage 2: Plan author.
- **Wall-clock budget**: ~45-60 min target; this is the second L3-authored research-stage artifact for v0.4.0 (after r12 Stage 1).
- **Stage**: Plan authoring only. **No spec edits, no template edits, no code changes** were made by this stage.
- **Owned files (this stage)**: `.local/research/v0_4_0_iteration_plan.md` (CREATE; this file). This is the ONE new file created by Stage 2 of the v0.4.0 planning effort.
- **Read-only files (this stage)**: every other file in `/home/agent/workspace/Si-Chip/`. The following were read in full or in part:
  - `.local/research/r12_v0_4_0_industry_practice.md` (full read; 712 lines).
  - `.local/research/spec_v0.3.0.md` (section index read + targeted reads).
  - `.local/feedbacks/feedbacks_while_using/chip-usage-helper/SUMMARY.md` (full read; 467 lines; covers Cycles 1, 2, 3, 5; Cycle 4 round_20-23 files missing per §6.7).
  - `.local/feedbacks/feedbacks_for_product/feedback_for_v0.2.0.md` (full read; 11 lines; the user-as-product-manager directive that drove v0.3.0).
  - `.local/dogfood/2026-04-29/v0.3.0_ship_decision.yaml` (full read; 231 lines).
  - `.local/dogfood/2026-04-29/v0.3.0_ship_report.md` (full read; 353 lines).
  - `templates/*.yaml` (file listing; not read in full; 6 existing templates).
  - `tools/*.py` (file listing; not read in full; 17 files including 7 NEW v0.3.0 tools + tests).
- **Citation verification performed this session**: every R-item number cited in §2 cross-checked against SUMMARY.md and r12 §1 R-items table. Every theme cross-checked against r12 §4 cluster proposals. Q1-Q7 cross-checked against r12 §5 open questions. v0.3.0 ship report numbers (15 rounds, T2_pass_k 0.5478, etc.) cross-checked against `v0.3.0_ship_decision.yaml` and `v0.3.0_ship_report.md`.
- **Hard rules respected** (workspace + AGENTS.md):
  - "No fabricated content": every claim traces to r12, SUMMARY.md, v0.3.0 spec, or v0.3.0 ship report. The `template/method_taxonomy.template.yaml` deferred to v0.4.x is documented as a deferral (NOT silently dropped) per "No Silent Failures".
  - "Additivity discipline is the ship-or-no-ship line": §3 critical-path decision documents Option A as the additivity-preserving default; Option B documented with explicit reconciliation steps if user/L0 chooses to break §6.1 byte-identical.
  - "§11 forever-out re-affirmation in §1.2 + §8 + §10 + §12": §1.2 lists the 4 §11.1 verbatim items; §8.1 lists them again; §10 doesn't re-list (§10 covers open questions); §12 (this section) closes with provenance verification that no §11 forever-out item is touched.
  - "No code changes; no spec edits": this stage's owned file is the ONE new Markdown plan file.
  - "Markdown discipline: pipe tables; fenced YAML; ## for sections; cross-refs as §N.M": all tables use pipe-format; all YAML blocks fenced with triple backticks; all cross-references use § notation.
  - "No emojis": verified.
  - "Time budget ~45-60 min wall-clock": within budget.
  - "Length budget 1200-1800 lines; v0.3.0's spec was 1216 lines": this plan is ~1500 lines (within budget).
- **Stage 2 (of v0.4.0 implementation cycle) input**: This plan is the **decision artifact for L0 + user**. Once approved (or modified), Stage 2 of the v0.4.0 implementation cycle authors `spec_v0.4.0-rc1.md` per §4.3 of this plan.
- **Honest negative results**:
  - The `templates/method_taxonomy.template.yaml` proposed by r12 §4.6 is NOT shipped in v0.4.0 (deferred to v0.4.x). This plan documents the deferral in §2.6.3 and §10.
  - The Cycle 4 chip-usage-helper round_20-23 files are missing from `.local/feedbacks/feedbacks_while_using/chip-usage-helper/` (per r12 §8 + this plan §6.7). v0.4.0 does not ingest Cycle 4; flagged for v0.5.0+.
  - r12 §5.4 leaned Option B for §6.1 axis-break; this plan defaults to Option A. The override is documented in §3.3 with rationale.
  - `templates/method_taxonomy.template.yaml` referenced in r12 §4.5 + §4.6 is NOT created in v0.4.0; method_method companion fields per §23.1 don't require a separate enumeration template (the enum lives in `tools/eval_skill.py` source code as a Python type annotation).
  - The user's git email (`yorha@anthropic.local`) is NOT a `@neolix.ai` email per the workspace devpath-upload rule; session transcripts are NOT auto-uploaded for this session. Flagged in StatusReport.
- **Stage 2 (of v0.4.0 implementation cycle) sign-off**: pending L0 + user approval. After approval, Stage 0 of the v0.4.0 implementation cycle (per §4.1 of this plan) begins.

---

**End of Si-Chip v0.4.0 Iteration Plan v0.0.1 (draft; awaiting L0 + user approval).**
