# Lifecycle State-Machine — R12 Summary (Spec §20)

> Reader-friendly summary of the §20 stage-transitions-and-promotion-history
> Normative chapter (v0.4.0-rc1). Authoritative sources:
> `.local/research/spec_v0.4.0-rc1.md` §20 and
> `.local/research/r12_v0_4_0_industry_practice.md` §2.4 + §4.3.

## Why this section exists

§2.2 v0.3.0 declared 7 stages (`exploratory → evaluated →
productized → routed → governed`, side-loop `half_retired`, terminus
`retired`) but left **when to advance** unspecified. chip-usage-helper
Round 8 promoted to `routed` on the author's judgement that
"router_floor bound + v3_strict all-green". That's probably correct,
but without spec rules the promotion is unreproducible. §20 codifies
each `from → to` edge with required-conditions so promotions are
spec-replayable.

## `stage_transition_table` (Normative DAG)

| `from_stage` | `to_stage` | Required conditions |
|---|---|---|
| `exploratory` | `evaluated` | (a) `has_eval_set: true` + `has_no_ability_baseline: true`; (b) D1-D7 emitted (null placeholders OK); (c) T1/T3/C1/C4 non-null. |
| `evaluated` | `productized` | (a) `current_surface.shape_hint ∈ {code_first, cli_first, mcp_first, mixed-with-code}`; (b) v1_baseline ≥ 2 consecutive PASS (§4.2 + §15.4). |
| `evaluated` | `routed` | (a) `router_floor` non-null; (b) v3_strict ≥ 3 consecutive PASS (1 code_change + 1 measurement_only minimum); (c) R3_trigger_F1 ≥ 0.90. |
| `productized` | `routed` | (a) `router_floor` non-null; (b) router_test ≥ 1 complete (MVP 8-cell or 96-cell); (c) v2_tightened ≥ 2 consecutive PASS. |
| `routed` | `governed` | (a) `lifecycle.owner` declared; (b) `lifecycle.version` synced with ability semver; (c) OTel `gen_ai.tool.name=<id>` for ≥ 30 days; (d) `lifecycle.deprecation_policy` declared. |
| `*` | `half_retired` | §6.2 value_vector trigger + `half_retire_decision.yaml` per §6.3. |
| `half_retired` | `evaluated` | (a) §6.4 reactivation trigger fires; (b) `core_goal_test_pack.yaml` hash unchanged (§14.7 #1); (c) C0 = 1.0 against current run. |
| `*` | `retired` | §6.2 retire trigger + `retire_decision.yaml` (extension of `half_retire_decision.template.yaml`). |

### Forbidden transitions (§20.1.1)

- `productized → evaluated` — re-exploring a code-sunk ability requires
  first `retire` then new `exploratory`.
- `routed → productized` — router-bound abilities may only
  `half_retired` (retains router_floor for reactivation) or `retired`.
- `governed → routed` — governed is a terminal branch; only
  `half_retired` / `retired` permitted.

## `BasicAbility.lifecycle.promotion_history` (append-only)

Every stage transition appends one entry:

```yaml
lifecycle:
  stage: routed
  last_reviewed_at: "2026-04-29"
  next_review_at: "2026-05-29"
  promotion_history:
    - from: exploratory
      to: evaluated
      triggered_by_round_id: round_1
      triggered_by_metric_value: { T1_pass_rate: 0.90, T3_baseline_delta: 0.85 }
      observer: "chip-usage-helper-cycle1-author"
      archived_artifact_path: ".local/dogfood/2026-04-29/abilities/chip-usage-helper/round_1/iteration_delta_report.yaml"
      decision_rationale: "Initial profile; T1/T3 above MVP thresholds."
    - from: evaluated
      to: routed
      triggered_by_round_id: round_8
      triggered_by_metric_value: { R3_trigger_F1: 1.0, R5_router_floor: "composer_2/fast" }
      observer: "chip-usage-helper-cycle1-author"
      archived_artifact_path: "..."
      decision_rationale: "router_floor bound; 5 consecutive v3_strict passes."
```

### Append-only invariant (§20.2.1)

- Modifications and deletions are forbidden — entries are audit
  history, not working fields.
- Corrections happen by appending a **sentinel entry** with `to: <same
  as prior>` and `decision_rationale: "Correcting observer field on
  round_X entry"`.

The `archived_artifact_path` must 1-click replay the full transition
evidence; this mirrors OpenSpec's
`changes/archive/<date>-<change-name>/` semantics (per r12 §2.4.a).

## `metrics_report.yaml.promotion_state` (first-class)

Round `N`'s counter state is **not** buried in `lifecycle` — it's a
top-level block beside `metrics`, `core_goal`, `token_tier`:

```yaml
promotion_state:
  current_gate: v1_baseline
  consecutive_passes: 2
  promotable_to: v2_tightened
  last_promotion_round_id: round_<M>
  ineligible_reason: null
```

### `ineligible_reason` enum (§20.3.1)

Non-null when `promotable_to: null` or `consecutive_passes < 2`:

- `"already_at_v3_strict"` — ceiling reached.
- `"insufficient_consecutive_passes"` — counter hasn't hit 2.
- `"hard_gate_regression_in_prior_round"` — prior round failed a hard
  threshold, counter reset.
- `"c0_regression_in_prior_round"` — §14.3.2 strict no-regression.
- `"round_kind_not_eligible"` — prior round was `ship_prep` /
  `maintenance` (§15.4 eligibility).

## `ship_decision.yaml` — the 7th evidence file

When `next_action_plan.yaml.round_kind == 'ship_prep'`, the round
emits **seven** evidence files instead of six. The extra file is
`ship_decision.yaml` (abridged; full template in Wave 1b):

```yaml
$schema_version: "0.1.0"
$spec_section: "v0.4.0 §20.4"
ability_id: "<id>"
round_id: "<round_id>"
decided_at: "YYYY-MM-DDTHH:MM:SSZ"
decided_by: "<observer>"
ship_target: { version: "<semver>", promoted_from: "...", spec_version_used: "v0.4.0" }
verdict: shipped|rolled-back|deferred
verdict_rationale: "<one paragraph>"
evidence_pointers:
  basic_ability_profile: ".local/dogfood/<DATE>/<round_id>/basic_ability_profile.yaml"
  metrics_report: ".../metrics_report.yaml"
  router_floor_report: ".../router_floor_report.yaml"
  half_retire_decision: ".../half_retire_decision.yaml"
  next_action_plan: ".../next_action_plan.yaml"
  iteration_delta_report: ".../iteration_delta_report.yaml"
target_repo_commits: [{ sha: "<sha>", message: "<msg>" }]
verified_with_live_data:
  - { backend_id: "<id>", endpoint: "<url>", verified_at: "...", sentinel: "...", sentinel_observed: <val>, observer: "...", note: "..." }
post_ship_review: { next_maintenance_at: "YYYY-MM-DD", triggers_to_watch: [...] }
```

### Conditional evidence-file count (§20.4.1)

spec_validator's `EVIDENCE_FILES` BLOCKER becomes conditional:

- `round_kind == 'ship_prep'` → expected count **7** (adds
  `ship_decision.yaml`).
- `round_kind ∈ {code_change, measurement_only, maintenance}` →
  expected count **6** (v0.3.0 semantics unchanged).

## Backward compatibility (§20.5)

- Round 1–15 Si-Chip and Round 1–10 chip-usage-helper profiles keep
  `promotion_history: null`; spec_validator does not backfill.
- Only Round 16+ Si-Chip / Round 26+ chip-usage-helper start
  appending entries.
- `archived_artifact_path` must use the multi-ability layout
  `.local/dogfood/<DATE>/abilities/<id>/round_<N>/...` (new) OR the
  legacy `.local/dogfood/<DATE>/round_<N>/...` (Si-Chip self only per
  §16.2).

## Interaction with §14 / §15 / §16

- **§14 Reactivation**: `half_retired → evaluated` transition row
  explicitly references §14.7 `(pack hash unchanged + C0 = 1.0)`
  prerequisites; `promotion_history` gains one entry per
  reactivation.
- **§15 round_kind**: `ship_prep` fires the 7th evidence file only;
  `promotion_state.consecutive_passes` increments only on
  `code_change` + `measurement_only` rounds (§15.4).
- **§16 multi-ability layout**: `archived_artifact_path` must be
  schema-compliant; spec_validator distinguishes ability per
  §16.2 rules.

## Forever-out re-check (§20.6)

| §11.1 forever-out | Touched by §20? |
|---|---|
| Marketplace | NO — `promotion_history` is a BasicAbilityProfile field; `ship_decision.yaml` is a local dogfood artifact. |
| Router model training | NO — all §20 fields are lifecycle metadata; no weights involved. |
| Generic IDE compat | NO — lifecycle stages are spec-internal; platform priority §7.2 unchanged. |
| Markdown-to-CLI | NO — entries are hand-witnessed by an observer; ship verdicts are hand-authored. |

## Cross-References

| §20 subsection | Spec section | R12 section |
|---|---|---|
| 20.1 stage_transition_table | spec §20.1 | r12 §4.3 + §2.4.a |
| 20.2 promotion_history | spec §20.2 | r12 §2.4.a OpenSpec archive |
| 20.3 promotion_state | spec §20.3 | r12 §4.3 |
| 20.4 ship_decision.yaml | spec §20.4 | r12 §4.3 + §2.3.c (ACE Skillbook) |
| 20.5 backward-compat | spec §20.5 | r12 §5 |
| 20.6 forever-out re-affirm | spec §20.6 | r12 §7 |

Cross-ref: `references/round-kind-r11-summary.md` (§15.4
eligibility; `ship_prep` fires the 7th file),
`references/real-data-verification-r12-summary.md` (§19.1.3
`verified_with_live_data` block fills `ship_decision.yaml`),
`references/half-retirement-r9-summary.md` (§6.2 triggers half_retired
transitions).

Source spec section: Si-Chip v0.4.0-rc1 §20 (Normative); distilled
from `.local/research/r12_v0_4_0_industry_practice.md` §2.4 + §4.3.
This reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
