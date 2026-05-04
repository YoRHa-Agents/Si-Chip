---
name: si-chip
description: BasicAbility optimization factory. Covers profile, evaluate, diagnose, improve, router-test, half-retire plus core_goal, token-tier, real-data per Si-Chip v0.4.2.
when_to_use: When a Skill needs eval evidence, router_floor, half-retire, C0, token-tier, provenance, or health-smoke.
version: 0.4.2
license: Apache-2.0
---

## What Si-Chip Does

Si-Chip is a persistent `BasicAbility` optimization factory. It runs a frozen
8-step loop — `profile → evaluate → diagnose → improve → router-test →
half-retire-review → iterate → package-register` — to keep one ability sharp
on functionality, context, latency, path, routing, and governance. Each
`BasicAbility` is the unit of measurement; every round must drop machine-
readable evidence so the next round can compute deltas. Si-Chip dogfoods
itself before guiding any other skill, and refuses to ship without two
consecutive passing rounds (spec v0.2.0 §1.1, §8.3; §11 forever-out and
Normative semantics byte-identical to v0.1.0).

## Core Object: BasicAbility

A `BasicAbility` is the first-class object Si-Chip optimizes. Frozen
top-level fields (spec §2.1):

`id`, `intent`, `current_surface`, `packaging`, `lifecycle`, `eval_state`,
`metrics`, `value_vector`, `router_floor`, `decision`.

Stage enum (spec §2.2): `exploratory → evaluated → productized → routed →
governed`, with `half_retired` as a side-loop and `retired` as terminus.
`half_retired` can be pulled back to `evaluated` by §6.4 reactivation
triggers.

The schema is authoritative — never invent ad-hoc keys. For full field
semantics, validators, and stage flow, read:

- `templates/basic_ability_profile.schema.yaml` — machine-validated schema
  (this file is the source of truth for every field).
- `references/basic-ability-profile.md` — reader-friendly walkthrough of
  every field plus the stage diagram.

MVP-8 sub-metrics (`T1`, `T2`, `T3`, `C1`, `C4`, `L2`, `R3`, `R5`) must be
filled every round; the remaining 29 sub-metric keys must be present with
explicit `null` placeholders (spec §3.2 frozen constraint #2; 37 total in
§3.1 TABLE, reconciled with §13.4 prose at v0.2.0). The 7-axis
`value_vector` drives §6 half-retire decisions.

### Core Goal — v0.3.0 Add-on (§14)

Every `BasicAbility` must also carry a `core_goal` block — the persistent,
never-regress functional outcome the ability delivers. `core_goal` is
orthogonal to `intent` (narrative) and to `description` (router metadata):
it is a testable contract.

```yaml
core_goal:
  statement: "<one-sentence testable functional contract>"
  test_pack_path: "<repo-relative path to core_goal_test_pack.yaml>"
  minimum_pass_rate: 1.0           # spec-locked; any < 1.0 = violation
```

The pack referenced by `test_pack_path` must enumerate ≥3 prompt +
`expected_shape` cases (Pact-style loose assertions, not exact equality;
spec §14.2). Every round computes the top-level invariant
`C0_core_goal_pass_rate = cases_passed / cases_total`. Per §14.3:

- `C0` MUST be exactly `1.0` every round (universal across all
  `round_kind` values — §15.3).
- If `C0 < prior_round.C0`, the round is a FAILURE regardless of the
  other R6 axes (§14.3.2 strict no-regression).
- Failing rounds trigger a REVERT-only response (§14.4); the offending
  source change is reverted before the next round begins.

`C0` is a **top-level** invariant — it is NOT the 38th R6 sub-metric
(§14.5). R6 stays frozen at 7 × 37 keys.

Details: `references/core-goal-invariant-r11-summary.md`.

### Token-Tier Invariant — v0.4.0 Add-on (§18)

Token usage decomposes into three top-level tiers `C7_eager_per_session / C8_oncall_per_trigger / C9_lazy_avg_per_load` (beside `metrics` and `core_goal`; NOT inside R6 D2). Adds OPTIONAL EAGER-weighted `iteration_delta` formula, `R3` split into `R3_eager_only` / `R3_post_trigger`, Informative `prose_class` taxonomy, `.lazy-manifest` packaging gate, and `tier_transitions` block on `iteration_delta_report.yaml`. Details: `references/token-tier-invariant-r12-summary.md`.

### Real-Data Verification — v0.4.0 Add-on (§19)

Normative sub-step of §8.1 step 2 `evaluate` (main list count unchanged). Three layers: msw fixture provenance, user-install verification, post-recovery live verification. `feedback_real_data_samples.yaml` holds redacted production samples. Hard rule 12 / BLOCKER 13 `REAL_DATA_FIXTURE_PROVENANCE` requires grep-able `// real-data sample provenance: <captured_at> / <observer>` citations. Details: `references/real-data-verification-r12-summary.md`.

### Stage Transitions & Promotion History — v0.4.0 Add-on (§20)

§2.2 stages gain a formal `stage_transition_table` (reverse transitions forbidden). `lifecycle.promotion_history` is append-only. `metrics_report.yaml.promotion_state` is a first-class top-level block. When `round_kind == 'ship_prep'` the round emits a **7th evidence file** `ship_decision.yaml`. Backward-compat: legacy rounds keep `promotion_history: null`. Details: `references/lifecycle-state-machine-r12-summary.md`.

### Health Smoke Check — v0.4.0 Add-on (§21)

`packaging.health_smoke_check` is OPTIONAL at schema level, REQUIRED when `current_surface.dependencies.live_backend: true` (hard rule 13 / BLOCKER 14). Each entry declares axes from the 4-axis taxonomy `{read, write, auth, dependency}`. §8.1 step 8 `package-register` runs every declared probe and gates ship-eligibility. Probes emit OTel spans `gen_ai.tool.name=si-chip.health_smoke` (spec-internal observability; does NOT reinvent Kubernetes liveness/readiness). Details: `references/health-smoke-check-r12-summary.md`.

### Eval-Pack Curation Discipline — v0.4.0 Add-on (§22)

Minimum pack size by gate: v1 20 prompts, v2 **40 prompts** (curated near-miss bucket), v3 60+ recommended. G1 `provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` is first-class REQUIRED. Informative `templates/eval_pack_qa_checklist.md` + Normative `templates/recovery_harness.template.yaml` (T4). §3.2 frozen constraint #5: deterministic seed `hash(round_id + ability_id)`. Real-LLM cache at `.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/`. Details: `references/eval-pack-curation-r12-summary.md`.

### Method-Tagged Metrics — v0.4.0 Add-on (§23)

Every metric emits a `<metric>_method` companion — token metrics take `{tiktoken, char_heuristic, llm_actual}`; quality/routing take `{real_llm, deterministic_simulator, mixed}`; G1 takes `{real_llm_sweep, deterministic_simulation, mixed}`. `_method == char_heuristic` also requires `_ci_low` + `_ci_high` 95% CI bands. Adds `U1_language_breakdown` + `U4_time_to_first_success_state ∈ {warm, cold, semicold}`. `spec_validator::R6_KEYS` BLOCKER ignores companion suffixes. Details: `references/method-tagged-metrics-r12-summary.md`.

### Skill Hygiene Discipline — v0.4.2 Add-on (§24)

Description ≤ 1024 chars (binding `min(chars,bytes)`; CJK fair); "what + when", not workflow. Hard rule 14 / BLOCKER 15 `DESCRIPTION_CAP_1024`. Absorbed from addyosmani/agent-skills v1.0.0. Details: `references/description-discipline-r13-summary.md`.

## When To Trigger

Use Si-Chip whenever a Skill needs eval evidence, a `router_floor`, or a
half-retire decision.

- User says: "evaluate this skill" or "is this skill worth keeping" →
  Trigger Si-Chip to run profile + evaluate + diagnose.
- User says: "what router floor does this ability need" → Trigger Si-Chip's
  router-test step (§5.3 8-cell MVP, or 96-cell Full at v2_tightened+).
- User says: "should we retire skill X" → Trigger Si-Chip's
  half-retire-review (§6) and emit a `half_retire_decision.yaml`.
- User says: "compare this round to last round" → Trigger Si-Chip's iterate
  step and emit an `iteration_delta_report.yaml`.
- User says: "package this skill for Cursor / Claude Code" → Trigger
  Si-Chip's package-register step (§7 priority order).
- User says: "generate a `BasicAbilityProfile` for ..." → Trigger Si-Chip
  step 1 (`scripts/profile_static.py`).
- User says: "diagnose why this skill is slow / costly / off-trigger" →
  Trigger Si-Chip's diagnose step against R6's 7 dim / 37 sub-metrics.
- User says: "draft next round's plan" → Trigger Si-Chip step 4 and emit a
  `next_action_plan.yaml`.
- User says: "verify core_goal hasn't regressed" → Trigger Si-Chip's eval
  step with the C0 check (§14.3); run `tools/eval_skill.py` with
  `--core-goal-test-pack`.
- User says: "this round only added measurement" → Set
  `round_kind: measurement_only` per §15.1 (iteration_delta clause
  RELAXED to monotonicity-only).
- User says: "audit my token tier EAGER/ON-CALL/LAZY breakdown" → spec
  §18 decomposition helpers; emit `token_tier {C7, C8, C9}` block and
  EAGER-weighted `iteration_delta` per §18.2.
- User says: "verify real-data fixtures trace to production payloads" →
  spec §19 provenance audit; grep `// real-data sample provenance: ...`
  citations and cross-check `feedback_real_data_samples.yaml`.
- User says: "run health smoke probes before ship" → spec §21
  packaging-gate; iterate `packaging.health_smoke_check` axes and write
  `raw/health_smoke_results.yaml`.
- User says: "audit my skill description length" → §24.1 cap; run
  `tools/spec_validator.py` and inspect the `DESCRIPTION_CAP_1024`
  BLOCKER's `per_artifact` chars / bytes / binding length entries.

## When NOT To Trigger

- User says: "publish this skill on a marketplace" → reject (spec §11.1
  forever-out: marketplace).
- User says: "train a router model on these traces" → reject (spec §11.1
  forever-out: Router model training).
- User says: "auto-convert this Markdown into a CLI" → reject (spec §11.1
  forever-out: Markdown-to-CLI converter).
- User says: "make Si-Chip support OpenCode / Copilot CLI / Gemini CLI" →
  reject (spec §11.1 forever-out: generic IDE compatibility layer; native
  Codex SKILL.md runtime is §11.2 deferred — bridge only at v0.2.0).
- User says: "just write this Python file" → not Si-Chip; no BasicAbility
  loop is needed. Use a direct edit instead.
- User says: "explain what BPE tokens are" → not Si-Chip; informational
  query only.

## How To Use

Run the 8 frozen steps in spec §8.1 order; each writes one artifact
under `.local/dogfood/<DATE>/round_<N>/`. Failures must be reported, not
skipped (workspace rule: No Silent Failures). Full step semantics,
scripts, templates, and references are in
`references/self-dogfood-protocol.md`.

1. **profile** → `basic_ability_profile.yaml` (schema §2.1).
2. **evaluate** → `metrics_report.yaml` (MVP-8 + 37-key null placeholders).
3. **diagnose** → bottleneck scan across R6's 7 dim / 37 sub-metrics.
4. **improve** → `next_action_plan.yaml` (each action targets one R6 key). **v0.3.0**: every `next_action_plan.yaml` MUST declare `round_kind ∈ {code_change | measurement_only | ship_prep | maintenance}` per §15.1; iteration_delta clause interpretation per §15.2.
5. **router-test** → `router_floor_report.yaml` (8-cell MVP, 96-cell at v2+); no router-model training (§5.2).
6. **half-retire-review** → `half_retire_decision.yaml` (7-axis value vector, §6.1).
7. **iterate** → `iteration_delta_report.yaml` (≥ 1 efficiency axis at gate bucket: v1 ≥ +0.05, v2 ≥ +0.10, v3 ≥ +0.15).
8. **package-register** → sync `.agents/skills/si-chip/` to platforms in §7.2 priority order: Cursor → Claude Code → Codex (bridge only).

**v0.3.0 add-on**: at the start of every round, run `python tools/eval_skill.py --core-goal-test-pack <path> ...` to verify `C0_core_goal_pass_rate = 1.0` per §14.3. If C0 < 1.0, the round is REVERT-only per §14.4 — no `iteration_delta_report.verdict.pass = true`, no promotion counter tick, revert the offending source change before starting the next round.

Each round must produce six evidence files (§8.2):
`basic_ability_profile.yaml`, `metrics_report.yaml`,
`router_floor_report.yaml`, `half_retire_decision.yaml`,
`next_action_plan.yaml`, `iteration_delta_report.yaml`. v0.1.0 ship
requires ≥ 2 consecutive rounds; round 2 must pass every `v1_baseline`
hard threshold (§8.3).

**v0.4.0**: `round_kind=ship_prep` rounds emit 7 evidence files (adds
`ship_decision.yaml` per §20.4); token-tier C7/C8/C9 decomposition is
OPTIONAL but REQUIRED-when-reported per hard rule 11 (BLOCKER 12);
real-data fixture provenance citations REQUIRED when
`feedback_real_data_samples.yaml` declares samples (BLOCKER 13);
`health_smoke_check` REQUIRED when
`current_surface.dependencies.live_backend: true` (BLOCKER 14).

**v0.4.2**: see §24 add-on (description ≤ 1024; BLOCKER 15).

## References Index

| Path | One-line summary |
|---|---|
| `references/basic-ability-profile.md` | Reader walkthrough of §2.1 fields and §2.2 stage enum. |
| `references/self-dogfood-protocol.md` | The 8-step protocol, 6 evidence files, and multi-round rule. |
| `references/metrics-r6-summary.md` | R6 7 dim / 37 sub-metrics + the §4.1 three-gate threshold table. |
| `references/router-test-r8-summary.md` | §5 router paradigm, MVP 8-cell vs Full 96-cell harness, profile↔gate binding. |
| `references/half-retirement-r9-summary.md` | §6 7-axis value vector, 4 decision rules, 6 reactivation triggers. |
| `references/core-goal-invariant-r11-summary.md` | §14 core_goal field, C0 metric, strict no-regression rule, REVERT-only rollback. |
| `references/round-kind-r11-summary.md` | §15 round_kind 4-value enum, per-kind iteration_delta clause, promotion-rule interaction. |
| `references/multi-ability-layout-r11-summary.md` | §16 `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` layout (Informative @ v0.3.0). |
| `references/token-tier-invariant-r12-summary.md` | §18 C7/C8/C9 + EAGER-weighted iteration_delta + lazy_manifest + prose_class + tier_transitions. |
| `references/real-data-verification-r12-summary.md` | §19 msw fixture provenance + user-install + post-recovery; BLOCKER 13. |
| `references/lifecycle-state-machine-r12-summary.md` | §20 stage_transition_table + promotion_history + promotion_state + ship_decision.yaml (7th evidence). |
| `references/health-smoke-check-r12-summary.md` | §21 4-axis (read/write/auth/dependency) + Optional-REQUIRED-when-live-backend; BLOCKER 14. |
| `references/eval-pack-curation-r12-summary.md` | §22 40-prompt minimum for v2_tightened + G1 provenance + eval_pack_qa_checklist + deterministic seeding. |
| `references/method-tagged-metrics-r12-summary.md` | §23 `<metric>_method` companions + `_ci_low`/`_ci_high` + U1/U4 language/state extensions. |
| `references/description-discipline-r13-summary.md` | §24.1 description cap 1024 + "what+when" + CJK fairness; BLOCKER 15. |

Reference files are loaded on demand and are excluded from the §7.3
SKILL.md body budget.

## Dogfood Quickstart

```bash
python .agents/skills/si-chip/scripts/profile_static.py --ability si-chip --out .local/dogfood/$(date -u +%F)/round_1/basic_ability_profile.yaml
python .agents/skills/si-chip/scripts/count_tokens.py --file .agents/skills/si-chip/SKILL.md --both --budget-meta 100 --budget-body 5000 --json
python tools/eval_skill.py --ability si-chip --skill-md .agents/skills/si-chip/SKILL.md --vocabulary <pack>/vocabulary.yaml --eval-pack <pack>/eval_pack.yaml --core-goal-test-pack <pack>/core_goal_test_pack.yaml --test-runner-cmd "pytest -q" --test-runner-cwd . --runs 3 --round-kind code_change --out .local/dogfood/$(date -u +%F)/round_14/metrics_report.yaml
python tools/round_kind.py validate code_change
python .agents/skills/si-chip/scripts/aggregate_eval.py --runs-dir .local/dogfood/$(date -u +%F)/round_1/raw/with --baseline-dir .local/dogfood/$(date -u +%F)/round_1/raw/without --skill-md .agents/skills/si-chip/SKILL.md --out .local/dogfood/$(date -u +%F)/round_1/metrics_report.yaml
python evals/si-chip/runners/real_llm_runner.py --ability si-chip --eval-pack <pack> --matrix-mode mvp --out .local/dogfood/$(date -u +%F)/round_18/raw/real_llm_run.json
python tools/health_smoke.py --profile .local/dogfood/$(date -u +%F)/round_16/basic_ability_profile.yaml --json
python tools/spec_validator.py --json
```

Steps 4–7 instantiate `templates/{next_action_plan,router_test_matrix,half_retire_decision,iteration_delta_report}.template.yaml` into the same round directory. Step 8 syncs `.agents/skills/si-chip/` → `.cursor/skills/si-chip/` → `.claude/skills/si-chip/` (Codex bridge only). Re-run `count_tokens.py` and `spec_validator.py --json` after every SKILL.md or template edit; both must exit 0.

## Out of Scope

Forever-out per spec §11.1:

- Skill / Plugin marketplace and any distribution surface.
- Router model training or online weight learning.
- Generic IDE / Agent-runtime compatibility layer.
- Markdown-to-CLI auto-converter.

Reject any request that pushes Si-Chip into these. Codex native SKILL.md
runtime is §11.2 deferred — bridge only at v0.2.0.

**v0.3.0 reaffirms forever-out**: `core_goal` is an observability invariant;
it does NOT introduce marketplace, router-model training, generic IDE
compat, or markdown-to-CLI conversion (spec §14.6).

**v0.4.0 reaffirms forever-out**: token-tier decomposition is
observability; real-data verification is testing; health-smoke check is
a pre-ship probe schema — NONE introduce marketplace, router-model
training, generic IDE compat, or Markdown-to-CLI conversion (spec §11.1
verbatim re-affirmed in §14.6 + §18.7 + §19.6 + §20.6 + §21.6 + §22.7
+ §23.7).

**v0.4.2 reaffirms forever-out**: §24 absorbs ONLY 1024-char cap +
"what+when" from agent-skills; NOT marketplace / plugin distribution
/ Markdown-to-CLI (spec §24.1.3 re-affirms §11.1).

## Provenance

Source-of-truth: `.agents/skills/si-chip/` ; Spec: `.local/research/spec_v0.4.2-rc1.md` (rc; +§24 + BLOCKER 15 absorbed from addyosmani/agent-skills v1.0.0; v0.4.0 baseline byte-identical) ; Compiled into `AGENTS.md` via `.rules/si-chip-spec.mdc`.
