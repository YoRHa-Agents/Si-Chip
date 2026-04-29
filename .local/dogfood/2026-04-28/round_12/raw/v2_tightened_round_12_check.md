# Round 12 v2_tightened readiness check

Source: `.local/dogfood/2026-04-28/round_12/metrics_report.yaml` +
`.local/dogfood/2026-04-28/round_12/iteration_delta_report.yaml`

Baselines regenerated this round at
`evals/si-chip/baselines/with_si_chip_round12/` and
`evals/si-chip/baselines/no_ability_round12/` with the new 7th case
`reactivation_review.yaml` added (Option A; see
`raw/v2_tightened_approach.md` for the honest analysis).

| Metric | v2 threshold | Round 12 observed | Pass? |
|--------|--------------|-------------------|-------|
| `pass_rate` (T1) | ≥ 0.82 | 0.821429 | ✅ PASS by +0.001 (razor-thin) |
| `pass_k` (T2) | ≥ 0.55 | 0.495019 | ❌ **FAIL by -0.055** (regression vs Round 11) |
| `trigger_F1` (R3) | ≥ 0.85 | 0.8729 | ✅ PASS by +0.023 |
| `near_miss_FP_rate` (R4) | ≤ 0.10 | 0.042857 | ✅ PASS by margin (-0.057) |
| `metadata_tokens` (C1) | ≤ 100 | 85 | ✅ PASS by margin (-15) |
| `per_invocation_footprint` (C4) | ≤ 7000 | 3710 | ✅ PASS by margin (-3290) |
| `wall_clock_p95` (L2) | ≤ 30 s | 1.4707 s | ✅ PASS by margin (~20x) |
| `routing_latency_p95` (R6) | ≤ 1200 ms | 1100 ms (carried mvp 8-cell) | ✅ PASS by margin (-100 ms) |
| `routing_token_overhead` (R7) | ≤ 0.12 | 0.023448 | ✅ PASS by margin (-0.097) |
| `iteration_delta` any axis | ≥ +0.10 | +0.10 (governance_risk axis — §6.4 detector full-coverage flavour) | ✅ PASS at the bucket boundary |

## Summary

| Bucket | Count | Detail |
|--------|------:|--------|
| PASS | 9 | T1, R3, R4, C1, C4, L2, R6, R7, iteration_delta |
| FAIL | 1 | **T2_pass_k (-0.055 vs 0.55) — REGRESSED vs Round 11** |

## Verdict for Round 12 vs v2_tightened

**FAIL** — Round 12 does NOT pass every v2_tightened hard threshold.

* `pass_k=0.4950` is the SOLE blocker, but it represents a **regression
  vs Round 11** (Round 11 was 0.5478). The regression is the honest
  consequence of adding the 7th case `reactivation_review` (per-case
  pass_rate=0.65 under the deterministic SHA-256 simulator with
  seed=42).
* All 9 other v2_tightened thresholds PASS, several by wide margins.
* T1 is now razor-thin at 0.821 vs 0.820 (margin +0.001). Adding more
  marginal-pass-rate cases would push T1 below v2 too.

## Cross-references

* `raw/v2_tightened_approach.md` — full Option A execution log + per-case
  pass_rate table.
* `raw/v2_readiness_verdict.md` — final verdict combining Round 11 +
  Round 12 status.
* `next_action_plan.yaml` — Round 13 plan with the real-LLM-runner
  upgrade path or v1_baseline ship recommendation.
