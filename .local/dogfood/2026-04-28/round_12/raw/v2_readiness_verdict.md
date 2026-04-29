# v2_tightened Readiness Verdict (Round 11 + Round 12)

**Verdict: BLOCKED**

`consecutive_v2_passes = 0` — neither Round 11 nor Round 12 clears
every v2_tightened hard threshold individually, so the spec §4.2
promotion rule (two consecutive rounds passing) is not satisfied.

## Per-round summary

| Round | T1 ≥0.82 | T2 ≥0.55 | R3 ≥0.85 | R4 ≤0.10 | C1 ≤100 | C4 ≤7000 | L2 ≤30s | R6 ≤1200ms | R7 ≤0.12 | iter_delta ≥+0.10 | Verdict |
|------:|--------:|--------:|--------:|--------:|--------:|--------:|--------:|--------:|--------:|--------:|--------:|
| **11** | 0.85 ✅ | **0.5478 ❌** | 0.8934 ✅ | 0.05 ✅ | 85 ✅ | 3710 ✅ | 1.4693 ✅ | 1100 ✅ | 0.0233 ✅ | **+0.05 ❌** (governance_risk drift-removal at v1_baseline bucket) | **FAIL** (2 blockers) |
| **12** | 0.8214 ✅ | **0.4950 ❌** (regressed vs Round 11) | 0.8729 ✅ | 0.0429 ✅ | 85 ✅ | 3710 ✅ | 1.4707 ✅ | 1100 ✅ | 0.0234 ✅ | +0.10 ✅ (governance_risk axis — §6.4 detector full-coverage flavour) | **FAIL** (1 blocker) |

## Blockers (verbatim)

| Round | Blocker | Threshold | Observed | Delta |
|------:|--------|----------:|---------:|------:|
| 11 | T2_pass_k | ≥ 0.55 | 0.5478 | -0.0022 |
| 11 | iteration_delta any axis | ≥ +0.10 | +0.05 | -0.05 |
| 12 | T2_pass_k | ≥ 0.55 | 0.4950 | **-0.055** (regression vs Round 11) |

## Honest cause analysis

* The deterministic SHA-256 runner produces per-case pass_rate values
  that depend on `(seed, case_id, prompt_id)` triples. Across the
  6 carried cases, the per-case mean was 0.5478 — already below v2
  by -0.0022.
* Per the L3 task brief's Option A, we added a 7th case
  `reactivation_review.yaml` to test the new
  `tools/reactivation_detector.py` workflow. Under `seed=42` and
  `case_id="reactivation_review"`, the deterministic simulator
  returned per-case `pass_rate=0.65`, which yields
  `pass_k_4 = 0.65^4 = 0.1785` — well below the carried 0.5478 mean.
  Adding it dragged the mean to 0.4950, a regression of -0.0528 vs
  Round 11.
* The user brief explicitly said "**I want HONESTY here, not
  number-chasing**". We did not cherry-pick a `case_id`, did not
  cherry-pick a `seed`, did not edit `prompt_outcomes`, and did not
  manually bump `pass_rate`. The result is what the deterministic
  pipeline produced.
* `iteration_delta any axis` clears v2 at +0.10 for Round 12 because
  Round 12 ADDS a brand-new feature (the §6.4 reactivation detector),
  which qualifies as a `governance_risk` axis full-coverage flavour
  bonus (the §6.4 audit gap from v0.1.0 ship is closed). For Round 11
  the equivalent bonus was claimed at +0.05 (v1_baseline bucket only)
  per the master plan acceptance criterion — that does NOT meet v2.

## Implication for v0.2.0 ship

* `ship_eligible: false` at gate `standard` (v2_tightened).
* Round 13 (or later) needed to satisfy `consecutive_v2_passes ≥ 2`.
* See `next_action_plan.yaml` for the recommended Round 13 path.
* See `v0.2.0_ship_decision.yaml` and `v0.2.0_ship_report.md` for the
  formal ship decision artifact.

## Forbidden alternatives we did NOT pursue

* **Cherry-picking the seed** to find a `seed` that yields
  `pass_k ≥ 0.55` — explicitly forbidden by the L3 task brief
  ("Option C (forbidden)").
* **Cherry-picking the case_id** so the SHA-256 hash produces a
  high-pass case — equally cherry-picking, just at a different
  parameter (e.g., a dry-run shows `case_id="reactivation_detector"`
  yields per-case pass_rate=0.95, but we did NOT use that name; the
  case file is `reactivation_review.yaml` with case_id =
  `reactivation_review` per repository convention).
* **Editing existing `result.json` `prompt_outcomes`** — explicitly
  forbidden by the L3 task brief.
* **Manually bumping per-case pass_rate without a real change** —
  explicitly forbidden.

## Path forward

The two HONEST paths to v0.2.0 ship:

1. **Real-LLM runner upgrade** (recommended; see `next_action_plan.yaml`):
   replace the deterministic SHA-256 simulator with a real-LLM runner
   that produces a real `pass_k_4` (currently `pass_k_4 = pass_rate^4`
   is a documented PROXY). Real sampling at k=4 should produce a
   higher pass_k for the same skill (the proxy is a lower bound).
   Then run Round 13 + Round 14 to satisfy
   `consecutive_v2_passes ≥ 2` at v2_tightened.
2. **Ship at v1_baseline as v0.2.0 with documentation** (alternative):
   accept that the deterministic simulator cannot honestly clear
   v2_tightened on T2_pass_k; ship v0.2.0 at the relaxed/v1_baseline
   gate; document the v2_tightened upgrade path in the ship report.

The L0 orchestrator should choose between (1) and (2) and trigger the
appropriate Round 13 plan.

---

**Generated**: Round 12 (Si-Chip v0.1.11), 2026-04-28.
