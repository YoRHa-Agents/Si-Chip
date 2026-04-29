# Round 12 dogfood — Diagnose notes (Step 3 of 8)

## Round 12 deliverables (Step 4 + Step 8 outputs)

| File | Status |
|------|--------|
| `tools/reactivation_detector.py` | NEW; all 6 §6.4 triggers verbatim; CLI exit-0/2 contract |
| `tools/test_reactivation_detector.py` | NEW; 31 unit tests (pytest -v passing) |
| `tools/spec_validator.py` | EXTENDED; 9th BLOCKER `REACTIVATION_DETECTOR_EXISTS`; SCRIPT_VERSION 0.1.2 -> 0.1.3 |
| `tools/test_spec_validator.py` | EXTENDED; 4 new tests for the new check; existing test renamed `test_default_mode_9_of_9_pass` |
| `evals/si-chip/cases/reactivation_review.yaml` | NEW; 20 prompts; 7th case for the §6.4 detector workflow |
| `evals/si-chip/baselines/with_si_chip_round12/` | NEW; 7-case regenerated baselines under seed=42 |
| `evals/si-chip/baselines/no_ability_round12/` | NEW; 7-case no-ability baselines under seed=42 |
| `.local/dogfood/2026-04-28/round_12/` | 6 evidence files + raw/ subtree |
| `.local/dogfood/2026-04-28/v0.2.0_ship_decision.yaml` | NEW; verdict `SHIP_BLOCKED` at gate v2_tightened |
| `.local/dogfood/2026-04-28/v0.2.0_ship_report.md` | NEW; companion to ship_decision.yaml |

## R6 7-dimension diagnose against current Round 12 metrics

| Dimension | Sub-metrics covered (Round 12) | Movement vs Round 11 | Diagnose |
|-----------|------|--------|--------|
| D1 task_quality | T1, T2, T3 (T4 null OOS) | T1: 0.85 -> 0.8214; T2: 0.5478 -> 0.4950 (REGRESSION); T3: 0.35 -> 0.3214 | 7th case `reactivation_review` per Option A drags every D1 metric down. T2 is the v2_tightened blocker (-0.055). v1_baseline still cleared by margin. |
| D2 context_economy | C1, C2, C4, C5, C6 (C3 null by design) | C1/C2/C4: 0.0; C5: 0.2601 -> 0.260625 (live); C6: 0.0435 -> 0.0417 (live) | C1/C2/C4 unchanged (no SKILL.md edit). C5/C6 LIVE re-derivation produces tiny drift. v2_tightened ceilings (C1<=100, C4<=7000) PASS by margin. |
| D3 latency_path | L1, L2, L3, L4 (L5/L6/L7 real-LLM-required) | L1: 1.2153 -> 1.2021 (-0.013); L2: 1.4693 -> 1.4707 (+0.001) | Trivial movement from 7-case mean shift. v2_tightened L2 ceiling 30s PASS by ~20x. |
| D4 generalizability | G1 (G2/G3/G4 null OOS for v0.1.x) | G1: byte-identical (no router-test rerun) | Carries Round 10/11 partial-proxy. Real-LLM runner is the upgrade path. |
| D5 usage_cost | U1, U2, U3, U4 | U1: 19.58 -> 18.85 (live); U2: 0.75 -> 0.6857 (REGRESSION); U3: 1; U4: 0.0073 -> 0.0079 (live) | U2 drops -0.064 from 7th case. U1/U4 LIVE re-derivation. v1_baseline cleared. |
| D6 routing_cost | R3, R4, R5, R6, R7, R8 (R1/R2 null OOS) | R3: 0.8934 -> 0.8729; R4: 0.05 -> 0.0429 (improvement); R7: 0.0233 -> 0.0234; R8: 0.0435 -> 0.0417 (live); R5/R6: unchanged | R3 still PASSES v2_tightened by +0.023. R4 IMPROVED. R5/R6 carried (no router-test rerun). |
| D7 governance_risk | V1, V2, V3, V4 (FULL coverage) | All unchanged. Mirror sync to 0.1.11 will re-verify V3. | Clean baseline preserved. |

## §6.4 reactivation-detector audit-gap closure (Round 12 marquee)

* The 6 §6.4 reactivation triggers existed only as Normative spec
  prose since v0.1.0. v0.1.0 ship report flagged the absence of a
  programmatic detector as a known limitation; master plan Round 12
  pre-specified the closure.
* Round 12 ships the COMPLETE detector
  (`tools/reactivation_detector.py`) with all 6 triggers verbatim +
  31 unit tests + spec_validator BLOCKER asserting the contract
  cannot regress.
* The §6.4 contract is now MACHINE-CHECKABLE end-to-end. This is the
  governance_risk axis full-coverage flavour bonus (claimed at
  +0.10 v2_tightened bucket per spec §4.1 iteration_delta column;
  see `iteration_delta_report.yaml#axis_status.governance_risk`).

## v2_tightened readiness check (Step 4 — verify primitive)

| Round | T1 | T2 | R3 | R4 | C1 | C4 | L2 | R6 | R7 | iter_delta | Verdict |
|-----:|---:|---:|---:|---:|---:|---:|---:|---:|---:|-----------:|---------|
| 11 | 0.85 ✅ | **0.5478 ❌** | 0.8934 ✅ | 0.05 ✅ | 85 ✅ | 3710 ✅ | 1.4693 ✅ | 1100 ✅ | 0.0233 ✅ | **+0.05 ❌** | FAIL (2 blockers) |
| 12 | 0.8214 ✅ | **0.4950 ❌** | 0.8729 ✅ | 0.0429 ✅ | 85 ✅ | 3710 ✅ | 1.4707 ✅ | 1100 ✅ | 0.0234 ✅ | +0.10 ✅ | FAIL (1 blocker) |

`consecutive_v2_passes = 0`. v0.2.0 ship at v2_tightened is BLOCKED.
See `.local/dogfood/2026-04-28/round_12/raw/v2_readiness_verdict.md`
and `.local/dogfood/2026-04-28/v0.2.0_ship_decision.yaml` for the
full per-row trace + ship verdict.

## Honest Option A execution log

* Created `evals/si-chip/cases/reactivation_review.yaml` per L3 task
  brief Option A (preferred path).
* Regenerated baselines: `with_si_chip_round12/` + `no_ability_round12/`
  with `seed=42`.
* Per-case pass_rate for the new case = 0.65 under deterministic
  SHA-256 simulator. This LOWERS the cross-case T2_pass_k from 0.5478
  to 0.4950 — a regression of -0.0528.
* We did NOT cherry-pick the seed.
* We did NOT cherry-pick the case_id (a dry-run showed
  `case_id="reactivation_detector"` would yield per-case pass_rate=0.95
  but we kept the user's suggested filename `reactivation_review`
  with case_id matching the filename per repository convention).
* We did NOT edit `prompt_outcomes`.
* We did NOT manually bump per-case pass_rate.
* Per the L3 task brief's explicit "I want HONESTY here, not
  number-chasing" instruction, we documented the regression rather
  than working around it.

See `raw/v2_tightened_approach.md` for the full Option A analysis.

## §11 forever-out compliance (verbatim)

* No marketplace touched.
* No router model training (the new detector is pure-Python
  deterministic; consumes YAML/JSON inputs and emits a JSON verdict;
  no learned weights, no inference model).
* No Markdown-to-CLI converter introduced.
* No generic IDE compatibility layer introduced (Cursor + Claude Code
  mirrors at §7.2 priority 1+2; Codex still bridge-only at §11.2
  deferred).

All 4 §11.1 items remain forever-out. Round 12 compliant.

## Recommended Round 13 path

PATH A (recommended): real-LLM runner upgrade in Round 13; v2_tightened
verification in Round 14. Naturally closes T2_pass_k blocker (real
sampling at k=4 is typically higher than the pass_rate^4 PROXY) and
many secondary blockers (G1 partial proxy, L5/L6/L7, R1/R2,
G2/G3/G4).

PATH B (alternative): ship at v1_baseline as v0.2.0 with documentation;
v2_tightened upgrade documented as known limitation.

L0 orchestrator chooses; both paths preserve §11 forever-out.
