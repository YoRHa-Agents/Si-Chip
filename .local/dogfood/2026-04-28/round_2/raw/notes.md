# Si-Chip Dogfood Round 2 — Diagnose Notes

`round_id: round_2`
`prior_round_id: round_1`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §8.1 step 3)

This note captures Step 3 (diagnose) per spec §8.1 for Round 2. Numbers are
sourced from `.local/dogfood/2026-04-28/round_2/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_1/metrics_report.yaml`.

## 1. MVP-8 + R4 vs Round 1

| Metric | Round 1 | Round 2 | Delta (R2 − R1) | v1_baseline | Direction |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | +0.00 | ≥ 0.75 | flat (no regression) |
| T2_pass_k | 0.5478 | 0.5478 | +0.0000 | ≥ 0.40 | flat |
| T3_baseline_delta | +0.35 | +0.35 | +0.00 | informational | flat |
| C1_metadata_tokens | 78 | 78 | 0 | ≤ 120 | flat (frontmatter untouched) |
| C2_body_tokens | null | 2020 | newly populated (-473 vs Round 1's 2493 prior count) | informational | improved (Improvement #1) |
| C4_per_invocation_footprint | 4071 | 3598 | -473 | ≤ 9000 | improved (-11.62%) |
| L2_wall_clock_p95 | 1.469 s | 1.469 s | 0.000 s | ≤ 45 s | flat (no Improvement #2 latency change applied this round) |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | null | 0.05 | newly populated | ≤ 0.15 | PASS (also passes v3_strict ≤ 0.05) |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |

Two of the three Round 1 plan exit criteria are met:

* **a1 (C2_body_tokens reduction)**: reduced 2493 → 2020 = **-18.97%**, far
  exceeding the 5% target.
* **a3 (R4_near_miss_FP_rate populated)**: now 0.05, meets v1 (≤ 0.15) and
  v3_strict (≤ 0.05).
* **a2 (L2 latency reduction)**: NOT executed this round (Round 1's plan
  required moving the optional `_safe_devolaflow_version()` call behind a
  flag in `aggregate_eval.py`, which would have required editing scripts/
  — outside S5's allowed-edit set). Carried forward into Round 3 plan
  with explicit deferral note.

## 2. Computed `context_delta` (NEW iteration_delta axis claim)

Per S5 task §3, the diagnose-stage definition of `context_delta` (round-to-round
flavour) is:

```
context_delta_iteration = (footprint_round_1 − footprint_round_2) / footprint_round_1
                       = (4071 − 3598) / 4071
                       = 473 / 4071
                       = 0.11620
```

This is the round-to-round efficiency improvement and feeds the `axis_status`
clause of `iteration_delta_report.yaml`. v1_baseline gate bucket is
`≥ +0.05`; observed `+0.1162` clears it by **2.32×**.

Note that the §6.1 value-vector flavour of `context_delta` (used in
`half_retire_decision.yaml`) measures against the no-ability baseline footprint
(1500 tokens), not against Round 1:

```
context_delta_value_vector = (1500 − 3598) / 1500 = -1.3987
```

Round 1's value-vector context_delta was -1.71. The axis-level (round-to-round
delta of the value-vector axis) improvement is:

```
axis_delta_context = -1.3987 − (-1.71) = +0.3113
```

Either flavour clears `≥ +0.05`. Both are surfaced in
`iteration_delta_report.yaml` so the verdict cannot be ambiguous.

## 3. v1_baseline hard-threshold check (Round 2)

| Threshold (v1_baseline) | Round 2 value | Pass? |
|---|---|---|
| pass_rate ≥ 0.75 | 0.85 | yes |
| pass_k ≥ 0.40 | 0.5478 | yes |
| trigger_F1 ≥ 0.80 | 0.8934 | yes |
| near_miss_FP_rate ≤ 0.15 | 0.05 | yes (NEW: was inapplicable Round 1) |
| metadata_tokens ≤ 120 | 78 | yes |
| per_invocation_footprint ≤ 9000 | 3598 | yes |
| wall_clock_p95 ≤ 45 s | 1.469 s | yes |
| routing_latency_p95 ≤ 2000 ms | null | inapplicable (still not measured; carried into Round 3 plan) |
| routing_token_overhead ≤ 0.20 | null | inapplicable (still not measured; carried into Round 3 plan) |
| iteration_delta (any axis) ≥ +0.05 | context_delta = +0.1162 (or axis_delta_context = +0.3113) | yes |

**No v1_baseline hard threshold for an MVP-8 metric (or R4) is FAILED in Round 2.**
R6 and R7 are still inapplicable (null), tracked for Round 3.

## 4. Monotonicity check vs Round 1

* `T1_pass_rate`: 0.85 == 0.85 — equal, NO regression.
* `T2_pass_k`: 0.5478 == 0.5478 — equal.
* `R3_trigger_F1`: 0.8934 == 0.8934 — equal.
* `C1_metadata_tokens`: 78 == 78 — equal.
* `C4_per_invocation_footprint`: 3598 < 4071 — IMPROVED (lower-is-better).
* `L2_wall_clock_p95`: 1.469 == 1.469 — equal.

No metric regressed by more than 1%; `pass_rate` is exactly equal (per spec
§8.3 hard rule — no regression allowed). Monotonicity check PASSES.

## 5. Top-3 BLOCKERS to v2_tightened promotion (carried forward to Round 3)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Round 1; cases unchanged this round so this is unchanged.
   Targeted in Round-3 plan.
2. **R6_routing_latency_p95 still null** — measurement gap; Round-3 plan
   instruments routing-latency telemetry.
3. **R7_routing_token_overhead still null** — measurement gap; same Round-3
   instrumentation pass should fill this.

## 6. Step 8 deferral note (explicit per §13 hard rule #7 / S5 task spec)

Step 8 (package-register) is again deferred to S6 (Cursor sync) and S7 (Claude
Code sync). Round 2 does NOT touch `.cursor/skills/si-chip/` or
`.claude/skills/si-chip/`. Source of truth remains `.agents/skills/si-chip/`.

## 7. R4 derivation method (transparency)

R4 is computed by reading every per-case `result.json` in
`evals/si-chip/baselines/with_si_chip_round2/` and counting prompts where
`expected == "no_trigger"` and `triggered == True` (these are the per-prompt
near-miss false positives). Per case: `fp_rate = n_fp / n_should_not_trigger`,
mean across the 6 cases:

* docs_boundary: 0/10
* half_retire_review: 0/10
* metrics_gap: 0/10
* next_action_plan: 2/10
* profile_self: 1/10
* router_matrix: 0/10

Mean = (0 + 0 + 0 + 0.2 + 0.1 + 0)/6 = **0.05**. Weighted (3/60) also = 0.05.
Full trace in `raw/r4_near_miss_FP_rate_derivation.json`.

The fallback proxy formula `max(0, (1 - trigger_F1) * 0.5)` would have given
`max(0, (1 - 0.8934) * 0.5) = 0.0533`. Direct measurement is authoritative
because the runner emits per-prompt outcomes; the proxy was NOT used. Result
is consistent with the proxy to within 0.003.
