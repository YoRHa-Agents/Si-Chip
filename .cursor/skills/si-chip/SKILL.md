---
name: si-chip
description: BasicAbility optimization factory. Covers profile, evaluate, diagnose, improve, router-test, half-retire plus core_goal, token-tier, real-data per Si-Chip v0.5.0.
when_to_use: When a Skill needs eval evidence, router_floor, half-retire, C0, token-tier, provenance, or health-smoke.
version: 0.5.0
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

### v0.4.0 Add-ons (§18 / §19 / §20 / §21 / §22 / §23)

- **§18 Token-Tier**: `token_tier {C7,C8,C9}` (eager / oncall / lazy) + EAGER-weighted iteration_delta + R3 split + `.lazy-manifest` + `tier_transitions`. Ref: `references/token-tier-invariant-r12-summary.md`.
- **§19 Real-Data Verification**: 3-layer §8.1 step 2 sub-step (msw / install / recovery). Hard rule 12 / BLOCKER 13: grep `// real-data sample provenance: <captured_at> / <observer>`. Ref: `references/real-data-verification-r12-summary.md`.
- **§20 Stage Transitions & Promotion History**: `stage_transition_table` + `lifecycle.promotion_history` + `promotion_state`; `ship_prep` → 7th evidence `ship_decision.yaml`. Ref: `references/lifecycle-state-machine-r12-summary.md`.
- **§21 Health Smoke Check**: `packaging.health_smoke_check` REQUIRED when `live_backend: true` (hard rule 13 / BLOCKER 14); 4-axis. Ref: `references/health-smoke-check-r12-summary.md`.
- **§22 Eval-Pack Curation**: v1 20 / v2 **40** / v3 60+ prompts; G1 `provenance` REQUIRED; cache `raw/real_llm_runner_cache/`. Ref: `references/eval-pack-curation-r12-summary.md`.
- **§23 Method-Tagged Metrics**: `<metric>_method` + `_ci_low/_ci_high`; `U1_language_breakdown` + `U4_*_state`. Ref: `references/method-tagged-metrics-r12-summary.md`.

### Skill Hygiene Discipline — §24 v0.4.x Add-ons

§24.1 Normative (v0.4.2): description ≤ 1024 chars; `min(chars,bytes)` (CJK fair); "what+when". Hard rule 14 / BLOCKER 15. Ref: `references/description-discipline-r13-summary.md`.

§24.2 Informative (v0.4.3): Rationalizations / Red Flags / Verification end-of-body sections (applied below). Ref: `references/standardized-sections-r13-summary.md`.

§24.3 Normative (v0.4.4): `body_tokens > 5000` → MUST cite ≥1 `references/<file>.md`. Hard rule 15 / BLOCKER 16; `lazy_manifest.template.yaml` Normative-conditional. Ref: `references/progressive-disclosure-r13-summary.md`.

§24.4 Informative (v0.4.5): OPTIONAL `lifecycle.category ∈ {define, plan, build, verify, review, ship, meta, null}` (default null). Si-Chip = `meta`. Ref: `references/lifecycle-category-r13-summary.md`.

§24.5 Informative (v0.4.6): meta-routing description-driven; **NO router-model training** (§5.2). Si-Chip canonical impl. Ref: `references/meta-routing-pattern-r13-summary.md`.

§24.6 Informative (v0.4.7): External Research Reference Registration; r13 first long-term pin `.local/research/r13_agent_skills_comparison.md` (research-only per §11.1; v0.5.0 arc complete). §24 absorbed from addyosmani/agent-skills v1.0.0.

## When To Trigger

- "evaluate this skill" / "is this skill worth keeping" → profile + evaluate + diagnose.
- "what router floor does this ability need" → router-test (§5.3 8-cell MVP / 96-cell Full at v2+).
- "should we retire skill X" → half-retire-review (§6) → emit `half_retire_decision.yaml`.
- "compare this round to last round" → iterate → emit `iteration_delta_report.yaml`.
- "package this skill for Cursor / Claude Code" → package-register (§7 priority order).
- "generate a `BasicAbilityProfile` for ..." → step 1 (`scripts/profile_static.py`).
- "diagnose why this skill is slow / costly / off-trigger" → diagnose against R6's 7 dim / 37 sub-metrics.
- "draft next round's plan" → step 4 → emit `next_action_plan.yaml`.
- "verify core_goal hasn't regressed" → eval with C0 check (§14.3); `tools/eval_skill.py --core-goal-test-pack`.
- "this round only added measurement" → set `round_kind: measurement_only` (§15.1; iteration_delta RELAXED to monotonicity).
- "audit token tier EAGER/ON-CALL/LAZY" → §18 decomposition; emit `token_tier {C7,C8,C9}` + EAGER-weighted `iteration_delta` (§18.2).
- "verify real-data fixtures" → §19 provenance audit; grep `// real-data sample provenance: ...`.
- "run health smoke probes before ship" → §21 packaging-gate; iterate `packaging.health_smoke_check`.
- "audit description length" → §24.1 cap; run `spec_validator.py` and inspect `DESCRIPTION_CAP_1024` entries.
- "SKILL body grew past 5000 tokens" → §24.3.1 graduated trigger; split long sections to `references/<topic>.md` and cite verbatim from body; BLOCKER 16 verifies cite + file existence.

## When NOT To Trigger

- "publish on marketplace" → reject (§11.1 forever-out).
- "train a router model on these traces" → reject (§11.1 forever-out).
- "auto-convert Markdown into CLI" → reject (§11.1 forever-out).
- "make Si-Chip support OpenCode / Copilot CLI / Gemini CLI" → reject (§11.1; Codex bridge-only per §11.2 deferred).
- "just write this Python file" → not Si-Chip; use direct edit (no BasicAbility loop needed).
- "explain what BPE tokens are" → not Si-Chip; informational only.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Skip dogfood this round" | §8.1 step 8 + §8.3 multi-round rule = ship-blocker. |
| "C0 regression is just measurement noise" | §14.3.2: any C0 < prior = round FAIL → §14.4 REVERT-only. |
| "spec_validator BLOCKER too strict" | BLOCKERs ↔ AGENTS.md hard rules 9-15; bypass = workspace policy violation. |
| "Ship without iteration_delta proof" | §15.2 strict for code_change requires ≥1 axis at gate bucket. |
| "Just stuff the long material into SKILL.md body" | §24.3.1 + BLOCKER 16: body > 5000 MUST cite existing `references/<file>.md`; split first, don't cram. |

## Red Flags

- `C0_core_goal_pass_rate < 1.0` silently overlooked.
- `round_kind` not declared in `next_action_plan.yaml` (hard rule 10 / spec_validator v0.4.0+ catches).
- `description_length > 1024` bypassed (BLOCKER 15 / hard rule 14).
- `iteration_delta_report.verdict.pass = true` set without an axis at the gate bucket (§15.2).
- `T2_pass_k _method=real_llm` claimed while `raw/real_llm_runner_cache/` is missing (§22.6 + §23.1).
- `body_tokens > 5000` without a `references/<file>.md` cite + existing file (BLOCKER 16 / hard rule 15; §24.3.1 graduated v3_strict trigger).

## Verification

- [ ] All 6 (or 7 ship_prep) evidence files written under round dir.
  - Evidence path: `.local/dogfood/<DATE>/round_<N>/`
- [ ] `python tools/spec_validator.py --json` exits 0; verdict PASS.
  - Evidence path: `raw/spec_validator.json`
- [ ] `pytest tools/test_spec_validator.py -q` all green.
  - Evidence path: `raw/pytest_full.txt`
- [ ] `count_tokens.py` reports metadata ≤ 100, body ≤ 5000.
  - Evidence path: `raw/count_tokens.json`
- [ ] `C0 = 1.0` and `c0_no_regression: true` in `iteration_delta_report.yaml.core_goal_check`.
  - Evidence path: `iteration_delta_report.yaml`

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

**v0.3.0**: every round MUST verify `C0_core_goal_pass_rate = 1.0` (§14.3); C0 < 1.0 → REVERT-only round (§14.4) — no `verdict.pass`, no promotion tick, revert source before next round.

Each round produces 6 evidence files (§8.2): `basic_ability_profile.yaml` / `metrics_report.yaml` / `router_floor_report.yaml` / `half_retire_decision.yaml` / `next_action_plan.yaml` / `iteration_delta_report.yaml`. Ship requires ≥ 2 consecutive rounds; round 2 must pass every `v1_baseline` threshold (§8.3).

**v0.4.0**: `round_kind=ship_prep` emits 7 files (+`ship_decision.yaml` §20.4); token-tier C7/C8/C9 OPTIONAL-but-REQUIRED-when-reported (BLOCKER 12); real-data provenance REQUIRED when declared (BLOCKER 13); `health_smoke_check` REQUIRED when `live_backend: true` (BLOCKER 14).

**v0.4.x §24**: §24.1 description cap BLOCKER 15; §24.2 sections (above); §24.3 progressive-disclosure BLOCKER 16; §24.4 OPTIONAL `lifecycle.category`; §24.5 meta-routing (NO router-training); §24.6 r13 registration.

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
| `references/standardized-sections-r13-summary.md` | §24.2 Informative Common Rationalizations + Red Flags + Verification template (no BLOCKER); reference impl in own SKILL.md above. |
| `references/progressive-disclosure-r13-summary.md` | §24.3 Normative body-budget triggers references/ split (graduated v1 best-practice → v3 MUST); hard rule 15 / BLOCKER 16. |
| `references/lifecycle-category-r13-summary.md` | §24.4 Informative OPTIONAL `lifecycle.category` 7-value enum + meta (no BLOCKER). |
| `references/meta-routing-pattern-r13-summary.md` | §24.5 Informative description-driven meta-ability pattern; NO router-model training. Si-Chip = canonical impl. |
| `templates/lazy_manifest.template.yaml` | §18.5 v0.4.0 + §24.3.3 v0.4.4 (Normative-conditional when SKILL body crosses v3_strict threshold). |

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

Forever-out per §11.1: marketplace / router-model training / generic IDE compat / Markdown-to-CLI. Reject any such request. Codex native SKILL.md runtime is §11.2 deferred (bridge-only at v0.2.0).

**v0.3.0 / v0.4.x reaffirm forever-out**: core_goal, token-tier, real-data, health-smoke, §24.1-§24.6 introduce NONE of §11.1 items (verbatim in §14.6 / §18.7 / §19.6 / §20.6 / §21.6 / §22.7 / §23.7 / §24.1.3 / §24.2.6 / §24.3.6 / §24.4.6 / §24.5.6 / §24.6.5).

## Provenance

Source-of-truth: `.agents/skills/si-chip/` ; Spec: `.local/research/spec_v0.5.0.md` (FROZEN; v0.5.0 arc complete) ; Compiled into `AGENTS.md` via `.rules/si-chip-spec.mdc`.
