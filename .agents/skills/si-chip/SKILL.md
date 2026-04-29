---
name: si-chip
description: Persistent BasicAbility optimization factory. Use when profiling, evaluating, diagnosing, improving, router-testing, half-retiring, OR validating core_goal no-regression per Si-Chip spec v0.3.0.
when_to_use: Whenever a Skill needs eval evidence, router_floor, half-retire decision, OR a core_goal regression check.
version: 0.3.0
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

Reference files are loaded on demand and are excluded from the §7.3
SKILL.md body budget.

## Dogfood Quickstart

```bash
python .agents/skills/si-chip/scripts/profile_static.py --ability si-chip --out .local/dogfood/$(date -u +%F)/round_1/basic_ability_profile.yaml
python .agents/skills/si-chip/scripts/count_tokens.py --file .agents/skills/si-chip/SKILL.md --both --budget-meta 100 --budget-body 5000 --json
python tools/eval_skill.py --ability si-chip --skill-md .agents/skills/si-chip/SKILL.md --vocabulary <pack>/vocabulary.yaml --eval-pack <pack>/eval_pack.yaml --core-goal-test-pack <pack>/core_goal_test_pack.yaml --test-runner-cmd "pytest -q" --test-runner-cwd . --runs 3 --round-kind code_change --out .local/dogfood/$(date -u +%F)/round_14/metrics_report.yaml
python tools/round_kind.py validate code_change
python .agents/skills/si-chip/scripts/aggregate_eval.py --runs-dir .local/dogfood/$(date -u +%F)/round_1/raw/with --baseline-dir .local/dogfood/$(date -u +%F)/round_1/raw/without --skill-md .agents/skills/si-chip/SKILL.md --out .local/dogfood/$(date -u +%F)/round_1/metrics_report.yaml
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

## Provenance

Source-of-truth: `.agents/skills/si-chip/` ; Spec: `.local/research/spec_v0.3.0.md` (frozen; promoted from v0.3.0-rc1; body byte-identical; additive — preserves v0.2.0 §3-§11 byte-identical; adds §14 core_goal + §15 round_kind + §16 multi-ability + §17 hard rules 9 & 10) ; Compiled into: `AGENTS.md` via `.rules/si-chip-spec.mdc`.
