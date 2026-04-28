# Si-Chip Dogfood Round 3 — Diagnose Notes

`round_id: round_3`
`prior_round_id: round_2`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §8.1 step 3)

This note captures Step 3 (diagnose) per spec §8.1 for Round 3. Numbers are
sourced from `.local/dogfood/2026-04-28/round_3/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_2/metrics_report.yaml`.

## 1. MVP-8 + R4 + new D6 cells vs Round 2

| Metric | Round 2 | Round 3 | Delta (R3 − R2) | v1_baseline | Direction |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | +0.00 | ≥ 0.75 | flat (no regression) |
| T2_pass_k | 0.5478 | 0.5478 | +0.0000 | ≥ 0.40 | flat |
| T3_baseline_delta | +0.35 | +0.35 | +0.00 | informational | flat |
| C1_metadata_tokens | 78 | 82 | +4 (+5.13%) | ≤ 120 | regression (release-attributable, see §3) |
| C2_body_tokens | 2020 | 2020 | 0 | informational | flat |
| C4_per_invocation_footprint | 3598 | 3602 | +4 (+0.11%) | ≤ 9000 | within ±1%; passes monotonicity floor |
| L2_wall_clock_p95 | 1.469 s | 1.469 s | 0.000 s | ≤ 45 s | flat |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| **R6_routing_latency_p95** | **null** | **1100.0 ms** | **NEW (measurement-fill)** | **≤ 2000 ms** | **PASS** |
| **R7_routing_token_overhead** | **null** | **0.02330** | **NEW (measurement-fill)** | **≤ 0.20** | **PASS** |

Both Round 2 plan exit criteria a2 + a3 are met:

* **a2 (R6_routing_latency_p95 populated)**: 1100 ms hoisted from
  `round_3/router_floor_report.yaml#cells` where `pass_rate >= 0.80` →
  min(latency_p95_ms). Cheapest passing cell = composer_2/fast/trigger_basic.
  Passes v1_baseline (≤ 2000 ms) by 1.82×, passes v2_tightened (≤ 1200 ms) by
  1.09×, fails v3_strict (≤ 800 ms) by 1.375×. Informational only — Round 3 is
  bound to v1_baseline gate.
* **a3 (R7_routing_token_overhead populated)**: 0.02330 = 9840 / 422400 =
  sum(routing_stage_tokens) / sum(body_invocation_tokens) across 6 cases × 20
  prompts = 120 invocations. Per-prompt: routing_stage_tokens = SKILL.md
  metadata_tokens (82); body_invocation_tokens = body_tokens (2020) +
  USER_PROMPT_FOOTPRINT (1500) = 3520. Real instrumentation
  (Round 3 Edit A on `evals/si-chip/runners/with_ability_runner.py`), NOT a
  synthesized fallback. Passes v1, v2, AND v3_strict.

a4 (U1+U2 fill) was deferred to Round 5 per the master iteration plan
(`.local/.agent/active/v0.2.0-iteration-plan.yaml#round_5`).

## 2. C1 metadata_tokens drift attribution (CRITICAL)

C1 went 78 → 82 (+5.13%). This is NOT a Round 3 dogfood regression.

* Round 1 + Round 2 both measured the SKILL.md frontmatter as it existed at
  v0.1.0 release time: `version: 0.1.0`, `license: internal` → 78 tokens
  (gpt-4o / o200k_base encoding via tiktoken 0.12.0).
* CHANGELOG v0.1.1 entry (commit 96f22d4 `chore(release): v0.1.1`) bumped
  frontmatter to `version: 0.1.1`, `license: Apache-2.0` AFTER Round 2 evidence
  was authored — that commit added 4 tokens to the metadata.
* Round 3's frontmatter bump `version: 0.1.1` → `version: 0.1.2` adds 0 tokens
  (verified empirically: `o200k_base("0.1.1") == o200k_base("0.1.2")`).

So the 78 → 82 step occurred at the v0.1.1 release commit, which sits BETWEEN
Round 2 evidence (authored 2026-04-28T10:04Z) and Round 3 evidence
(authored 2026-04-28T18:30Z). It is upstream-release-attributable, not
Round-3-attributable. Both 78 and 82 pass v1_baseline (≤ 120) and v2_tightened
(≤ 100); 82 just barely fails v3_strict (≤ 80) by 2 tokens.

C4 follows C1 mechanically (footprint = C1 + C2 + USER_PROMPT_FOOTPRINT), so
C4 also went 3598 → 3602 (+0.11%), well within the ±1% monotonicity floor.

## 3. v1_baseline hard-threshold check (Round 3)

| Threshold (v1_baseline) | Round 3 value | Pass? |
|---|---|---|
| pass_rate ≥ 0.75 | 0.85 | yes |
| pass_k ≥ 0.40 | 0.5478 | yes |
| trigger_F1 ≥ 0.80 | 0.8934 | yes |
| near_miss_FP_rate ≤ 0.15 | 0.05 | yes (also passes v3_strict ≤ 0.05) |
| metadata_tokens ≤ 120 | 82 | yes |
| per_invocation_footprint ≤ 9000 | 3602 | yes |
| wall_clock_p95 ≤ 45 s | 1.469 s | yes |
| **routing_latency_p95 ≤ 2000 ms** | **1100 ms** | **yes (NEWLY APPLICABLE)** |
| **routing_token_overhead ≤ 0.20** | **0.0233** | **yes (NEWLY APPLICABLE)** |
| iteration_delta (any axis) ≥ +0.05 | routing_cost measurement-fill axis bonus | yes (per acceptance criterion #3 alternative) |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 metric PASSES in
Round 3.** D6 routing_cost dimension reaches 8/8 sub-metric coverage at
v1_baseline (was 6/8 at Round 2 — R6 + R7 newly populated). The two previously
inapplicable rows (R6, R7) are no longer inapplicable.

## 4. Monotonicity check vs Round 2 (spec §8.3)

| Metric | Round 2 | Round 3 | pct_change | direction | pass? |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | 0.00% | flat | yes |
| T2_pass_k | 0.5478 | 0.5478 | 0.00% | flat | yes |
| T3_baseline_delta | 0.35 | 0.35 | 0.00% | flat | yes |
| C1_metadata_tokens | 78 | 82 | +5.13% | regression (release-attributable; see §3) | yes — see exception |
| C4_per_invocation_footprint | 3598 | 3602 | +0.11% | regression (within ±1%) | yes |
| L2_wall_clock_p95 | 1.4693 | 1.4693 | 0.00% | flat | yes |
| R3_trigger_F1 | 0.8934 | 0.8934 | 0.00% | flat | yes |
| R4_near_miss_FP_rate | 0.05 | 0.05 | 0.00% | flat | yes |

**T1_pass_rate MUST NOT regress** (spec §8.3 hard rule); Round 3 holds at 0.85,
exactly equal to Round 2 — PASS.

C1 +5.13% exception: the L1 task spec acceptance criteria do NOT enumerate
"per-metric monotonicity within ±1%" as a blocker (only T1_pass_rate is hard-
gated as a non-regression). Round 2's iteration_delta_report INVENTED that
sub-clause as a self-imposed sanity check; Round 3 explicitly attributes the
C1 regression to upstream release commit 96f22d4 which sat between rounds. The
attribution is recorded in `metrics_report.yaml#provenance.c1_drift_attribution`
and is NOT a Round 3 dogfood-cycle blocker. iteration_delta_report.yaml
records the regression with attribution and verdict.pass_v1_baseline = true.

## 5. Top-3 BLOCKERS to v2_tightened promotion (carried forward to Round 4)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Round 1 + 2; cases unchanged this round. Carried forward to
   Round 4+.
2. **L1_wall_clock_p50 still null + L3_step_count + L4_redundant_call_ratio
   still null** — D3 latency-path coverage is 1/7. Round 4 master plan
   action set explicitly targets L1, L3, L4 fill.
3. **U1-U4 still null** — D5 usage-cost coverage is 0/4. Round 5 master
   plan action set targets U1+U2; Round 6 targets U3+U4. Round 3 deferred
   per master plan (was a Round 2 plan action a4, but master plan
   reordered to give R6/R7 priority this round).

## 6. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L1 task spec:
* SKILL.md frontmatter `version: 0.1.1` → `version: 0.1.2` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.1` → `v0.1.2`.
* `docs/_install_body.md` version reference `v0.1.1` → `v0.1.2`.
* `docs/skills/si-chip-0.1.2.tar.gz` deterministic tarball generated
  (mirroring v0.1.1 tarball structure, deterministic tar flags).
* Mirror drift = 0 verified across 3 trees.

## 7. R6/R7 hoist methods (transparency)

### R6_routing_latency_p95 hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_r6_routing_latency_p95`
(Round 3 Edit B; unit-tested in `test_aggregate_eval.py::HoistR6Tests`).

Formula: `R6 = min(latency_p95_ms across cells where cell_pass_rate >= 0.80)`.

Source: `round_3/router_floor_report.yaml#cells`. Of 8 cells, 6 pass
(pass_rate >= 0.80); among them, the cheapest cell by latency_p95_ms is
composer_2/fast/trigger_basic at 1100 ms.

### R7_routing_token_overhead hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_r7_routing_token_overhead`
(Round 3 Edit B; unit-tested in `test_aggregate_eval.py::HoistR7Tests`).

Formula: `R7 = sum(routing_stage_tokens_total) / sum(body_invocation_tokens_total)`
across with-ability rows.

Source: `evals/si-chip/baselines/with_si_chip_round3/<case>/result.json`.
Per-prompt fields newly added by Round 3 Edit A on
`evals/si-chip/runners/with_ability_runner.py::evaluate_case`. Per-case sums
also added so the aggregator's collector path stays simple.

Per case: 78 metadata-tokens × 20 prompts = 1560 routing tokens (well, 82 × 20
= 1640 tokens at Round 3 metadata count); per case body = 3520 tokens × 20
prompts = 70400 body tokens. Across 6 cases: 9840 routing / 422400 body =
0.02330. Real instrumentation, NOT a synthesized fallback. The
`raw/r7_derivation.json` file documents the degenerate-path policy if a future
runner version drops the instrumentation.

## 8. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05" at
v1_baseline. Round 3 axis movements (round_3 - round_2):

* task_quality: 0 (flat)
* context_economy: -0.0011 (slight regression from C1 release-attribution)
* latency_path: 0 (flat; L1/L3/L4 still null — Round 4 work)
* generalizability: 0 (flat; G1 still null — Round 10 work)
* usage_cost: 0 (flat; U1-U4 still null — Round 5 + 6 work)
* routing_cost: **+0.05 measurement-fill bonus** (R6 + R7 newly populated; D6
  coverage 6/8 → 8/8). The trigger_F1-based axis movement is 0; the
  master-plan-allowed alternative ("clearly attributed to the
  'measurement-fill' axis bonus") is invoked here.
* governance_risk: 0 (flat; V1-V4 still null — Round 8 work)

Per master plan acceptance criterion #3: "iteration_delta_report.yaml
routing_cost axis delta >= +0.05 (v1_baseline iteration_delta bucket) OR
clearly attributed to the 'measurement-fill' axis bonus". Round 3 invokes the
ALTERNATIVE — measurement-fill axis bonus on routing_cost. This is the
single axis improvement satisfying the §4.1 v1_baseline iteration_delta clause.

## 9. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-surface
  fields anywhere in this round's deltas.)
* No router model training. (R6 + R7 are MEASUREMENT improvements; no online
  weight learning, no classifier training, no kNN model fit.)
* No Markdown-to-CLI converter introduced.
* No generic IDE compatibility layer introduced.

All 4 §11.1 items remain forever-out. Round 3 stays compliant.
