# Si-Chip Dogfood Round 4 — Diagnose Notes

`round_id: round_4`
`prior_round_id: round_3`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §8.1 step 3)

This note captures Step 3 (diagnose) per spec §8.1 for Round 4. Numbers are
sourced from `.local/dogfood/2026-04-28/round_4/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_3/metrics_report.yaml`.

## 1. MVP-8 + R4 + new D3 cells vs Round 3

| Metric | Round 3 | Round 4 | Delta (R4 − R3) | v1_baseline | Direction |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | +0.00 | ≥ 0.75 | flat (no regression) |
| T2_pass_k | 0.5478 | 0.5478 | +0.0000 | ≥ 0.40 | flat |
| T3_baseline_delta | +0.35 | +0.35 | +0.00 | informational | flat |
| C1_metadata_tokens | 82 | 82 | +0 (+0.00%) | ≤ 120 | flat |
| C2_body_tokens | 2020 | 2020 | 0 | informational | flat |
| C4_per_invocation_footprint | 3602 | 3602 | +0 (+0.00%) | ≤ 9000 | flat |
| **L1_wall_clock_p50** | **null** | **1.215 s** | **NEW (measurement-fill)** | **informational** | **populated** |
| L2_wall_clock_p95 | 1.469 s | 1.469 s | 0.000 s | ≤ 45 s | flat (within ±1%) |
| **L3_step_count** | **null** | **20** | **NEW (measurement-fill)** | **informational** | **populated** |
| **L4_redundant_call_ratio** | **null** | **0.0** | **NEW (measurement-fill)** | **informational** | **populated** |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |

All Round 4 plan exit criteria (a1, a2, a3, a4) are met:

* **a1 (L1_wall_clock_p50 populated)**: 1.215 s hoisted from
  `with_si_chip_round4/<case>/result.json#latency_p50_s` via
  `aggregate_eval.hoist_l1_wall_clock_p50` (Round 4 Edit C). Per-case p50s
  computed by the new `percentile_p50` helper in
  `evals/si-chip/runners/with_ability_runner.py` (Round 4 Edit A). Sanity
  invariant **L1 ≤ L2** holds (1.215 ≤ 1.469). L1 has no §4.1 hard threshold
  row at v1_baseline; this is fill (not gate movement).
* **a2 (L3_step_count populated)**: 20 (= mean across 6 cases of
  `len(prompt_outcomes)` per case = 20). Hoisted via
  `aggregate_eval.hoist_l3_step_count` from per-case `step_count` emitted by
  `with_ability_runner.step_count_from_outcomes` (Round 4 Edit A). Integer
  sanity check passes (≥ 1).
* **a3 (L4_redundant_call_ratio populated)**: 0.0 (degenerate VALID value
  — every prompt_id within a case is unique by construction in the
  deterministic simulator). Hoisted via
  `aggregate_eval.hoist_l4_redundant_call_ratio` from per-case
  `redundant_call_ratio` emitted by
  `with_ability_runner.redundant_call_ratio_from_outcomes` (Round 4 Edit A).
  Range sanity check passes ([0.0, 1.0]). The aggregator distinguishes
  `None` (no field present) from `0.0` (field present, no redundancy
  observed) per workspace rule "No Silent Failures".
* **a4 (L2_wall_clock_p95 not regressed)**: 1.469 s, identical to Round 3
  to 4 decimal places — well within the ±1% tolerance (master plan
  acceptance criterion #4).

a5 was a Plan-only carry-forward (T2_pass_k v2_tightened tracking for
Round 12); no Round 4 action required.

## 2. v1_baseline hard-threshold check (Round 4)

| Threshold (v1_baseline) | Round 4 value | Pass? |
|---|---|---|
| pass_rate ≥ 0.75 | 0.85 | yes |
| pass_k ≥ 0.40 | 0.5478 | yes |
| trigger_F1 ≥ 0.80 | 0.8934 | yes |
| near_miss_FP_rate ≤ 0.15 | 0.05 | yes (also passes v3_strict ≤ 0.05) |
| metadata_tokens ≤ 120 | 82 | yes |
| per_invocation_footprint ≤ 9000 | 3602 | yes |
| wall_clock_p95 ≤ 45 s | 1.469 s | yes |
| routing_latency_p95 ≤ 2000 ms | 1100 ms | yes |
| routing_token_overhead ≤ 0.20 | 0.0233 | yes |
| iteration_delta (any axis) ≥ +0.05 | latency_path measurement-fill axis bonus | yes (per acceptance criterion #5 alternative) |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 metric PASSES in
Round 4.** D3 latency_path dimension reaches **4/7** sub-metric coverage at
v1_baseline (was 1/7 at Round 3 — L1, L3, L4 newly populated). L5/L6/L7
(detour_index, replanning_rate, think_act_split) stay null pending a real-LLM
upgrade and are not §4.1 hard-gated.

## 3. Monotonicity check vs Round 3 (spec §8.3)

| Metric | Round 3 | Round 4 | pct_change | direction | pass? |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | 0.00% | flat | yes |
| T2_pass_k | 0.5478 | 0.5478 | 0.00% | flat | yes |
| T3_baseline_delta | 0.35 | 0.35 | 0.00% | flat | yes |
| C1_metadata_tokens | 82 | 82 | 0.00% | flat | yes |
| C4_per_invocation_footprint | 3602 | 3602 | 0.00% | flat | yes |
| L2_wall_clock_p95 | 1.4693 | 1.4693 | 0.00% | flat | yes |
| R3_trigger_F1 | 0.8934 | 0.8934 | 0.00% | flat | yes |
| R4_near_miss_FP_rate | 0.05 | 0.05 | 0.00% | flat | yes |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0.00% | flat | yes |
| R7_routing_token_overhead | 0.0233 | 0.0233 | 0.00% | flat | yes |

**T1_pass_rate MUST NOT regress** (spec §8.3 hard rule); Round 4 holds at 0.85,
exactly equal to Round 3 — PASS. No metric regressed by more than 1%; no
release-attribution exceptions need to be invoked this round.

## 4. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05" at
v1_baseline. Round 4 axis movements (round_4 - round_3):

* task_quality: 0 (flat)
* context_economy: 0 (flat; C1 / C4 unchanged this round)
* latency_path: **+0.05 measurement-fill bonus** (L1, L3, L4 newly
  populated; D3 coverage 1/7 → 4/7). The latency_delta value-vector axis
  movement is +0.0092 (improvement from -0.5467 → -0.5375; due to using the
  live no_ability L2 mean 0.9557 instead of the hardcoded 0.95). The
  master-plan-allowed alternative ("measurement-fill or actual reduction")
  is invoked here.
* generalizability: 0 (flat; G1 still null — Round 10 work)
* usage_cost: 0 (flat; U1-U4 still null — Round 5 + 6 work)
* routing_cost: 0 (flat; R8 still null — Round 9 work)
* governance_risk: 0 (flat; V1-V4 still null — Round 8 work)

Per master plan acceptance criterion #5: "iteration_delta_report.yaml
latency_path axis flagged with delta_iteration_flavour >= +0.05
(measurement-fill or actual reduction)". Round 4 satisfies this with the
measurement-fill axis bonus on latency_path. This is the single axis
improvement satisfying the §4.1 v1_baseline iteration_delta clause.

## 5. Top-3 BLOCKERS to v2_tightened promotion (carried forward to Round 5+)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Round 1 + 2 + 3; cases unchanged this round. Carried forward to
   Round 12 v2_tightened readiness check.
2. **U1_description_readability + U2_first_time_success_rate still null**
   — D5 usage_cost coverage is 0/4. **Round 5 master plan action set
   targets U1+U2 fill (via Flesch-Kincaid grade level on SKILL.md
   `description` frontmatter and first-trigger success rate from
   prompt_outcomes).** Hint: U1 derivation can reuse `count_tokens.py` as
   a sibling helper (description string is already in scope); U2 derivation
   can be lifted from `evals/si-chip/baselines/with_si_chip_round4/<case>/result.json#prompt_outcomes`
   without a new runner (master plan rationale).
3. **C5_context_rot_risk + C6_scope_overlap_score still null** — D2
   context_economy is at 4/6 (C1, C2, C4 measured; C3 explicit-null
   per resolved-on-demand semantics). Round 7 master plan target.

## 6. Round 5 hint (per master plan)

Round 5 fills D5 usage_cost (U1+U2). The diagnose findings here flag:

* **U1 derivation strategy**: SKILL.md `description` field is bilingual-ish
  ("Persistent BasicAbility optimization factory. Use when profiling,
  evaluating, diagnosing, ..."), short, and dense. Flesch-Kincaid grade level
  may be unflattering — that's OK; surfacing it is the value (master plan
  Round 5 risk_flag).
* **U2 derivation strategy**: First-trigger success per prompt = was the
  trigger emitted on the FIRST eval iteration (vs. requiring a
  retry/escalation). The simulator's `triggered` field is the first-pass
  outcome by construction; mean across should_trigger prompts gives U2
  directly. No new runner required.

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L1 task spec:
* SKILL.md frontmatter `version: 0.1.2` → `version: 0.1.3` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.2` → `v0.1.3`.
* `docs/_install_body.md` version reference `v0.1.2` → `v0.1.3`.
* `docs/skills/si-chip-0.1.3.tar.gz` deterministic tarball generated
  (mirroring v0.1.2 tarball structure, same `tar --sort=name --owner=0
  --group=0 --numeric-owner -cf - ... | gzip -n > ...` flags).
* Mirror drift = 0 verified across 3 trees.

## 8. L1/L3/L4 hoist methods (transparency)

### L1_wall_clock_p50 hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_l1_wall_clock_p50`
(Round 4 Edit C; unit-tested in `test_aggregate_eval.py::HoistL1Tests` —
4 tests + 1 doctest covering basic hoist, no-instrumentation, sanity
invariant L1 ≤ L2, partial instrumentation).

Formula: `L1 = mean(latency_p50_s across with-ability rows)`. Per-row
p50 from runner `percentile_p50` over per-prompt latencies.

Sanity: L1 (1.215 s) ≤ L2 (1.469 s). Aggregator raises `ValueError` if
the inequality is violated (workspace rule "No Silent Failures").

### L3_step_count hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_l3_step_count`
(Round 4 Edit C; unit-tested in `test_aggregate_eval.py::HoistL3Tests`).

Formula: `L3 = round(mean(step_count across with-ability rows))`. Each
case's `step_count` is the count of `prompt_outcomes` (= 20 by
construction in the deterministic runner).

### L4_redundant_call_ratio hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_l4_redundant_call_ratio`
(Round 4 Edit C; unit-tested in `test_aggregate_eval.py::HoistL4Tests`).

Formula: `L4 = mean(redundant_call_ratio across with-ability rows)`.
Per-case ratio = `(total_calls - unique_call_names) / total_calls` with
tool-name = `prompt_id`.

Degenerate VALID 0.0: every `prompt_id` in a case is unique by
construction (master plan risk_flag acknowledged). The aggregator
distinguishes `None` (no instrumentation) from `0.0` (instrumentation
present, no redundancy observed).

## 9. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-surface
  fields anywhere in this round's deltas.)
* No router model training. (L1, L3, L4 are MEASUREMENT improvements; no
  online weight learning, no classifier training, no kNN model fit. The
  router_floor_report is re-emitted verbatim from Round 3.)
* No Markdown-to-CLI converter introduced.
* No generic IDE compatibility layer introduced. (Cursor + Claude Code
  mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex is bridge-only
  per spec §11.2 deferred.)

All 4 §11.1 items remain forever-out. Round 4 stays compliant.
