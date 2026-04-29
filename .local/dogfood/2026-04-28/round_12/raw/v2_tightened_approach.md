# Round 12 v2_tightened approach — Option A (HONEST 7th-case attempt)

## Pre-flight findings

Per `raw/v2_tightened_round_11_check.md`, Round 11 already FAILS the
v2_tightened gate on TWO threshold rows:

1. `T2_pass_k = 0.5478 < 0.55` (the long-standing carry-forward blocker)
2. `iteration_delta any axis = +0.05 < +0.10` (Round 11's
   spec-reconciliation drift-removal bonus claimed at the v1_baseline
   bucket only)

Because Round 11 metrics are immutable history, **even a perfect
Round 12 cannot satisfy `consecutive_v2_passes ≥ 2`** (the spec §4.2
promotion rule requires BOTH Round 11 AND Round 12 to clear every v2
hard threshold).

## L3 task brief — explicit instructions

The L3 task brief explicitly states:

> "Proceed with **Option A** and document the addition clearly in
> `raw/v2_tightened_approach.md`."

> "If the 7th case DOESN'T happen to yield ≥ 0.55, this is evidence
> that ship at v2_tightened isn't achievable at Round 12."

> "**I want HONESTY here, not number-chasing.** If pass_k stays below
> 0.55, say so clearly."

## Option A execution

We executed Option A as instructed:

1. Created `evals/si-chip/cases/reactivation_review.yaml` (case_id =
   `reactivation_review`) with 20 prompts (10 should_trigger covering
   the §6.4 detector workflow + 10 should_not_trigger near-miss
   prompts). Filename matches the user's task brief verbatim.
2. Regenerated `evals/si-chip/baselines/with_si_chip_round12/` and
   `evals/si-chip/baselines/no_ability_round12/` with `seed=42`.
3. Re-ran the aggregator against the new 7-case baselines.

## Honest Round 12 result with the 7th case

**Per-case `pass_rate` (deterministic SHA-256 simulator under seed=42)**:

| case_id | Round 4-11 carried | Round 12 (7-case) | Δ |
|---------|------:|------:|------:|
| docs_boundary | 0.95 | 0.95 | 0.00 |
| half_retire_review | 0.85 | 0.85 | 0.00 |
| metrics_gap | 0.95 | 0.95 | 0.00 |
| next_action_plan | 0.75 | 0.75 | 0.00 |
| profile_self | 0.80 | 0.80 | 0.00 |
| router_matrix | 0.80 | 0.80 | 0.00 |
| **reactivation_review (NEW)** | — | **0.65** | NEW |
| **mean pass_rate (T1)** | **0.8500** | **0.8214** | **-0.0286** |
| **mean pass_k (T2 = pass_rate^4)** | **0.5478** | **0.4950** | **-0.0528** |

Adding the 7th case **LOWERS** pass_k from 0.5478 to 0.4950 — a
regression of -0.0528. Per-case `pass_k_4 = 0.65^4 = 0.1785` for the
new case is well below the per-case mean of 0.5478, so the cross-case
mean drops.

This is NOT a number-chasing failure — it is the honest, deterministic
output of the SHA-256-driven simulator under `seed=42` for the
case_id `reactivation_review` with the prompt set the L3 task brief
suggested.

## Why we proceeded with Option A despite the regression

1. **Real test coverage**: the new case genuinely tests the
   `tools/reactivation_detector.py` workflow added in Round 12. It is
   not synthetic filler.
2. **Spec §3.2 frozen-constraint #2**: the case file is the canonical
   way to expand evaluation coverage; it lives in
   `evals/si-chip/cases/` alongside the 6 prior cases and follows the
   same YAML schema.
3. **HONESTY mandate**: the L3 brief explicitly instructed "If pass_k
   stays below 0.55, say so clearly". Reporting the regression
   honestly is more valuable than not running Option A at all.
4. **Forbidden alternative was "cherry-pick seeds" and forbidden
   semantic alternative would be selecting a different `case_id`
   solely because its SHA-256 produces higher `pass_rate`** — both of
   those are number-chasing, not honesty. We did neither.

## What we DID NOT do

* We did NOT cherry-pick `seed`.
* We did NOT edit `prompt_outcomes` in any existing `result.json`.
* We did NOT manually bump per-case `pass_rate`.
* We did NOT pick a `case_id` based on which one happens to produce a
  high deterministic pass_rate (a dry-run showed `case_id =
  "reactivation_detector"` would yield pass_rate=0.95 vs
  `reactivation_review`'s 0.65 — the difference is purely SHA-256
  noise. We used the user's suggested filename `reactivation_review`
  with a matching `case_id` per repository convention).

## Verdict for Round 12 v2_tightened

| Metric | v2 threshold | Round 12 observed | Pass? |
|--------|--------------|-------------------|-------|
| `pass_rate` (T1) | ≥ 0.82 | 0.8214 | ✅ PASS by +0.0014 (razor-thin) |
| `pass_k` (T2) | ≥ 0.55 | 0.4950 | ❌ **FAIL by -0.0550** (regression vs Round 11) |
| `trigger_F1` (R3) | ≥ 0.85 | 0.8729 | ✅ PASS by +0.0229 |
| `near_miss_FP_rate` (R4) | ≤ 0.10 | 0.0429 | ✅ PASS |
| `metadata_tokens` (C1) | ≤ 100 | 85 | ✅ PASS |
| `per_invocation_footprint` (C4) | ≤ 7000 | 3710 | ✅ PASS |
| `wall_clock_p95` (L2) | ≤ 30 s | 1.4707 s | ✅ PASS |
| `routing_latency_p95` (R6) | ≤ 1200 ms | 1100 ms (carried mvp 8-cell) | ✅ PASS |
| `routing_token_overhead` (R7) | ≤ 0.12 | 0.0234 | ✅ PASS |
| `iteration_delta` any axis | ≥ +0.10 | governance_risk +0.10 (reactivation detector NEW = full-coverage flavour) | ✅ PASS by exactly the bucket boundary |

## Final v2_readiness verdict

**BLOCKED** — see `raw/v2_readiness_verdict.md` for the full reasoning.

* Round 11 fails on T2_pass_k AND iteration_delta.
* Round 12 fails on T2_pass_k (with adverse regression vs Round 11).
* `consecutive_v2_passes = 0` (no consecutive round pair clears v2).

## Recommended Round 13 path

The only honest paths to clear v2_tightened on T2_pass_k are:

1. **Real-LLM runner upgrade** — replace the deterministic SHA-256
   simulator with a real-LLM runner that produces real `pass_k_4`
   (currently `pass_k_4 = pass_rate^4` is a documented PROXY, not
   sampled k=4). This is the v0.3.x roadmap item already deferred in
   `round_11/next_action_plan.yaml`.
2. **Ship at v1_baseline as v0.2.0 with documentation** — accept that
   the deterministic simulator cannot honestly clear v2_tightened on
   T2_pass_k; ship v0.2.0 at the relaxed/v1_baseline gate; document
   the v2_tightened upgrade path in the ship report.

Both paths leave Si-Chip's BasicAbility shape intact and §11
forever-out compliant.
