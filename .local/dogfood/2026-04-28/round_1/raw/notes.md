# Si-Chip Dogfood Round 1 — Diagnose Notes

`round_id: round_1`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive gates)

This note captures Step 3 (diagnose) per spec §8.1. It is a working trace, not
an evidence file. Numbers are sourced from
`.local/dogfood/2026-04-28/round_1/metrics_report.yaml` and the no-ability
baseline summary at `evals/si-chip/baselines/no_ability/summary.json`.

## 1. Per-dimension R6 scan (MVP-8 vs v1_baseline)

`v1_baseline` thresholds (spec §4.1):
- pass_rate >= 0.75
- pass_k (k=4) >= 0.40
- trigger_F1 >= 0.80
- near_miss_FP_rate <= 0.15
- metadata_tokens <= 120
- per_invocation_footprint <= 9000
- wall_clock_p95 <= 45 s
- routing_latency_p95 <= 2000 ms
- routing_token_overhead <= 0.20
- iteration_delta (any axis) >= +0.05

| Dim | MVP key | Round 1 value | v1_baseline | v2_tightened | v3_strict | Verdict | Null sub-metrics |
|---|---|---|---|---|---|---|---|
| D1 task_quality | T1_pass_rate | 0.85 | >= 0.75 | >= 0.82 | >= 0.90 | **passes v1, v2; fails v3** | T4_error_recovery_rate |
| D1 task_quality | T2_pass_k | 0.5478 | >= 0.40 | >= 0.55 | >= 0.65 | **passes v1; fails v2 (margin -0.0023)** | — |
| D1 task_quality | T3_baseline_delta | +0.35 | informational (used by half-retire) | — | — | feeds value_vector.task_delta | — |
| D2 context_economy | C1_metadata_tokens | 78 | <= 120 | <= 100 | <= 80 | **passes v1, v2, v3** | C2, C3, C5, C6 |
| D2 context_economy | C4_per_invocation_footprint | 4071 | <= 9000 | <= 7000 | <= 5000 | **passes v1, v2, v3** | C2, C3, C5, C6 |
| D3 latency_path | L2_wall_clock_p95 | 1.469 s | <= 45 s | <= 30 s | <= 20 s | **passes v1, v2, v3** | L1, L3, L4, L5, L6, L7 |
| D4 generalizability | (none MVP-8) | — | — | — | — | not measured this round | G1, G2, G3, G4 |
| D5 usage_cost | (none MVP-8) | — | — | — | — | not measured this round | U1, U2, U3, U4 |
| D6 routing_cost | R3_trigger_F1 | 0.8934 | >= 0.80 | >= 0.85 | >= 0.90 | **passes v1, v2; fails v3 (margin -0.0066)** | R1, R2, R4, R6, R7, R8 |
| D6 routing_cost | R5_router_floor | composer_2/fast (will be revised to composer_2/default by Step 5 router test) | informational | — | — | feeds half-retire context | — |
| D7 governance_risk | (none MVP-8) | — | — | — | — | not measured | V1, V2, V3, V4 |

`near_miss_FP_rate`, `routing_latency_p95`, `routing_token_overhead`,
`wall_clock_p95` table-row metrics that are not in MVP-8 are **null** in
`metrics_report.yaml` for Round 1 — this is allowed per spec §3.2 frozen
constraint #2 (explicit null placeholder). Per task spec, the v1_baseline
hard-threshold check treats them as inapplicable for now (an axis-status
positive-axis is supplied by `routing_delta = +0.8934` from the iteration delta
clause).

## 2. Top-3 BLOCKERS to v2_tightened promotion

A blocker is an MVP-8 sub-metric whose Round 1 value passes v1 but FAILS v2.

1. **T2_pass_k = 0.5478 fails v2_tightened (>= 0.55)** by margin **-0.0022**.
   Almost-there; one extra correct case across the 6-case suite would tip it
   over. Mitigated by (a) tightening case acceptance criteria in
   `evals/si-chip/cases/profile_self.yaml` and `next_action_plan.yaml` (both
   currently 0.41 and 0.32 contributing the bottom of the distribution), and
   (b) refining SKILL.md guidance for those two cases. (Targets D1.)
2. **R4_near_miss_FP_rate is null** — unknown vs the v1 ceiling 0.15 / v2 0.10.
   This is a **measurement gap**, not a known regression, but until measured we
   cannot promote past v1. Targets D6. Round 2 must instrument the runners to
   emit per-case near-miss labels.
3. **R3_trigger_F1 = 0.8934 fails v3_strict (>= 0.90)** by margin -0.0066. Not
   blocking v2 promotion, but it is the next ceiling after we collect 2
   consecutive v1 passes. Listed here so Round 2's plan keeps it on the radar.

NON-blockers explicitly checked:
- C1_metadata_tokens = 78 already passes v3 (<= 80).
- C4_per_invocation_footprint = 4071 already passes v3 (<= 5000).
- L2_wall_clock_p95 = 1.469 s already passes v3 (<= 20 s).
- T1_pass_rate = 0.85 passes v2 (>= 0.82) but fails v3 (>= 0.90); since it
  passes v2 it is NOT a v2 blocker.

## 3. Top-3 EFFICIENCY WINS expected for Round 2

These map to `expected_iteration_delta_axes` in `next_action_plan.yaml`.

1. **C2_body_tokens reduction (target context_economy axis).** SKILL.md body is
   currently 2493 tokens (re-checked via `count_tokens.py`). Tightening the
   "Plain-language plan" / "Common pitfalls" sections by ~5% should move
   `context_delta` upward without losing trigger fidelity. Exit: body_tokens
   reduced by >= 5%.
2. **L2_wall_clock_p95 reduction (target latency_path axis).** Round 1 latency
   is 1.469 s end-to-end across the 6-case suite. This is dominated by
   `aggregate_eval.py` startup + statistics; removing the optional
   `_safe_devolaflow_version()` call from the hot path saves ~0.3-0.5 s in
   profiling runs. Exit: L2 reduced by >= 5%.
3. **R4_near_miss_FP_rate measurement (target routing_cost axis).** Round 2
   needs concrete near_miss_FP_rate so we can verify R3 stays >= 0.80 while
   FP-rate stays <= 0.15 (v1) / <= 0.10 (v2). Exit: R4 instrumented and
   non-null AND R3 not regressed.

## 4. Step 8 deferral note (explicit per S4 acceptance)

Step 8 deferred per S4 plan; package-register handled by S6 (Cursor sync) and
S7 (Claude Code sync). Round 1 does NOT touch `.cursor/skills/si-chip/` or
`.claude/skills/si-chip/`. Source of truth remains `.agents/skills/si-chip/`.
Per spec §13 hard rule #7 (No Silent Failures), this deferral is recorded
explicitly here and does not pretend the step ran.

## 5. Round 1 hard-threshold matrix vs v1_baseline (sanity)

| Threshold (v1_baseline) | Round 1 value | Pass? |
|---|---|---|
| pass_rate >= 0.75 | 0.85 | yes |
| pass_k >= 0.40 | 0.5478 | yes |
| trigger_F1 >= 0.80 | 0.8934 | yes |
| near_miss_FP_rate <= 0.15 | null (not measured Round 1) | inapplicable |
| metadata_tokens <= 120 | 78 | yes |
| per_invocation_footprint <= 9000 | 4071 | yes |
| wall_clock_p95 <= 45 s | 1.469 s | yes |
| routing_latency_p95 <= 2000 ms | null (not measured Round 1) | inapplicable |
| routing_token_overhead <= 0.20 | null (not measured Round 1) | inapplicable |
| iteration_delta (any axis) >= +0.05 | routing_delta = +0.8934 | yes |

**No v1_baseline hard threshold for an MVP-8 metric is FAILED in Round 1.**
Three thresholds are inapplicable because their R6 sub-metric is still null
(not in MVP-8 for v1_baseline; tracked in §3 above as Round 2 work).
