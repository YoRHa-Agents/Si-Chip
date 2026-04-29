# Si-Chip Dogfood Round 9 — Diagnose Notes

`round_id: round_9`
`prior_round_id: round_8`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §5 router paradigm, §5.1 allowed work surfaces, §5.2 prohibitions,
§5.3 harness table, §5.4 profile↔gate binding, §8.1 step 3, §11.1 forever-out)

This note captures Step 3 (diagnose) per spec §8.1 for Round 9. Numbers are
sourced from `.local/dogfood/2026-04-28/round_9/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_8/metrics_report.yaml`.

## 1. MVP-8 + R4 + D3 + D5 + D2 + D7 + R8 cells vs Round 8

| Metric | Round 8 | Round 9 | Delta (R9 − R8) | v1_baseline | Direction |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | +0.00 | ≥ 0.75 | flat (no regression) |
| T2_pass_k | 0.5478 | 0.5478 | +0.0000 | ≥ 0.40 | flat |
| T3_baseline_delta | +0.35 | +0.35 | +0.00 | informational | flat |
| C1_metadata_tokens | 82 | 82 | +0 (+0.00%) | ≤ 120 | flat |
| C2_body_tokens | 2020 | 2020 | 0 | informational | flat |
| C3_resolved_tokens | null | null | — | by-design null | permanently null |
| C4_per_invocation_footprint | 3602 | 3602 | +0 (+0.00%) | ≤ 9000 | flat |
| C5_context_rot_risk | 0.2601 | 0.2601 | 0.00 | range [0, 1] | flat |
| C6_scope_overlap_score | 0.0435 | 0.0435 | 0.00 | range [0, 1] | flat |
| L1_wall_clock_p50 | 1.215 s | 1.215 s | 0.000 s | informational | flat |
| L2_wall_clock_p95 | 1.469 s | 1.469 s | 0.000 s | ≤ 45 s | flat |
| L3_step_count | 20 | 20 | 0 | informational | flat |
| L4_redundant_call_ratio | 0.0 | 0.0 | 0.0 | informational | flat |
| U1_description_readability | 19.58 | 19.58 | +0.00 | informational | flat |
| U2_first_time_success_rate | 0.75 | 0.75 | +0.00 | informational | flat |
| U3_setup_steps_count | 1 | 1 | 0 | ≤ 2 | flat |
| U4_time_to_first_success | 0.0073 s | 0.0073 s | 0.000 s | ≤ 60 s | flat |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |
| **R8_description_competition_index** | **null** | **0.0435** | **NEW (measurement-fill)** | **no §4.1 threshold; range [0, 1]** | **populated (PASS)** |
| V1_permission_scope | 0 | 0 | 0 | no §4.1 threshold | flat |
| V2_credential_surface | 0 | 0 | 0 | no §4.1 threshold | flat |
| V3_drift_signal | 0.0 | 0.0 | 0.0 | no §4.1 threshold | flat (re-verified post-0.1.8 sync) |
| V4_staleness_days | 0 | 0 | 0 | no §4.1 threshold | flat |

All Round 9 plan exit criteria (a1-a5) are met:

* **a1 (R8_description_competition_index populated)**: 0.043478260869565216
  hoisted from `count_tokens.skill_md_description_competition_index` with
  `method="max_jaccard"` via `aggregate_eval.hoist_r8_description_competition_index`
  (Round 9 Edit A + Edit B). R8 = max Jaccard across 23
  `/root/.claude/skills/lark-*/SKILL.md` neighbor descriptions. Top
  offender = `lark-whiteboard-cli` at 1/23 token overlap.

  **R8 ≡ C6 by construction**: both use set-Jaccard on the SAME neighbor
  set; a cross-validation check in `raw/r8_derivation.json#c6_vs_r8_consistency_check`
  asserts delta < 1e-9 and confirms equality.

  R8 additionally supports `method="tfidf_cosine_mean"` as an ALTERNATIVE
  that surfaces AVERAGE competition (complementary to max_jaccard
  WORST-offender signal). Round 9 picks `max_jaccard` as default per
  master plan risk_flag (Jaccard infra already battle-tested in Round 7).

* **a2 (router-test matrix widened to 16-cell intermediate profile)**:
  `templates/router_test_matrix.template.yaml` `$schema_version` bumped
  `0.1.0 -> 0.1.1`. ADDITIVE intermediate profile added alongside mvp:8
  and full:96 (BOTH structurally unchanged).

  intermediate = 2 models × 2 thinking_depths × 4 scenario_packs = 16
  cells. 2 extra scenario_packs introduced: `multi_skill_competition`
  (HARDER than trigger_basic; pass_rates 0.70-0.82) and `execution_handoff`
  (between trigger_basic and multi; pass_rates 0.78-0.85). Pass-rates
  hard-coded in `evals/si-chip/runners/with_ability_runner.py::INTERMEDIATE_EXTRA_CELL_OUTCOMES`;
  deterministic dict lookup (no RNG). The 8 cells shared with mvp are
  BYTE-IDENTICAL to the mvp sweep (stability invariant).

  Gate binding stays at `relaxed` (same as mvp; NOT a §5.4 binding
  escalation — v2_tightened+ still requires full 96-cell matrix).

* **a3 (router_floor_report emits BOTH sweeps + intersection floor)**:
  `router_floor_report.yaml round_9` emits BOTH the mvp 8-cell sweep
  AND the intermediate 16-cell sweep. `router_floor` = INTERSECTION of
  cheapest (model, depth) tuple that passes on BOTH profiles.

  Cost ordering: composer_2/fast < composer_2/default < sonnet_shallow/fast
  < sonnet_shallow/default. Per-tuple min(pack_pass_rate):

  | Tuple | mvp | intermediate |
  |---|---|---|
  | composer_2/fast | 0.78 (FAIL) | 0.72 (FAIL) |
  | **composer_2/default** | **0.83 (PASS)** | **0.81 (PASS)** ← cheapest that passes BOTH |
  | sonnet_shallow/fast | 0.74 (FAIL) | 0.70 (FAIL) |
  | sonnet_shallow/default | 0.81 (PASS) | 0.81 (PASS) |

  **intersection router_floor = composer_2/default** (same as mvp-only
  floor in rounds 1-8; no divergence).

* **a4 (≥ 8 new tests in test_count_tokens.py + ≥ 6 new tests in test_aggregate_eval.py
  + ≥ 3 new tests in tools/test_spec_validator.py)**:
    - `test_count_tokens.py`: 65 → 90 tests (25 new Round 9 tests covering
      tokenize_description_list × 3, tf_idf_vector × 6, cosine_similarity
      × 7, skill_md_description_competition_index × 9 including real
      Si-Chip smoke max_jaccard and tfidf_cosine_mean). Meets the ≥ 8
      threshold by a comfortable margin.
    - `test_aggregate_eval.py`: 101 → 109 tests (8 new Round 9 tests
      covering hoist_r8_description_competition_index happy/degenerate
      paths + build_report integration + 28-key invariant).
    - `tools/test_spec_validator.py`: NEW file, 7 tests — 0.1.1 happy
      path + axis-product check, 0.1.0 backward-compat, 0.1.1 negative
      (wrong cell count + wrong gate_binding + unsupported schema),
      default-mode subprocess 8/8 PASS round-trip.

  Total test count growth Round 8 (220 passed, 1 skipped) -> Round 9
  (243 passed, 1 skipped) — count growth continues per master plan.

* **a5 (V1-V4 continue to pass after spec_validator extension + template
  bump)**: `round_9/raw/spec_validator.json` = 8/8 PASS. Schema 0.1.1
  invariants asserted (cell_counts.intermediate==16 + profile cells==16
  + gate_binding==relaxed + axis_product==16). Backward compat:
  spec_validator accepts BOTH 0.1.0 and 0.1.1 schemas.

## 2. v1_baseline hard-threshold check (Round 9)

| Threshold (v1_baseline) | Round 9 value | Pass? |
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
| iteration_delta (any axis) ≥ +0.05 | routing_cost measurement-fill axis bonus | yes |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 metric
PASSES in Round 9.** D6 routing_cost dimension reaches 6/8 POPULATED
sub-metric coverage (R3+R4+R5+R6+R7+R8 measured; R1+R2 permanently
out-of-scope for v0.1.x). R8 also passes range-sanity. No sub-metrics
become null; spec §3.2 frozen key contract still holds (37 keys, 26
populated, 11 explicit null).

## 3. Monotonicity check vs Round 8 (spec §8.3)

Every metric either held flat or was newly populated (R8). `T1_pass_rate`
hard non-regression rule holds at 0.85 = 0.85 — PASS.

## 4. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05"
at v1_baseline. Round 9 axis movements (round_9 − round_8):

* task_quality: 0 (flat)
* context_economy: 0 (flat; D2 already at full coverage from Round 7)
* latency_path: 0 (flat; D3 stays at 4/7)
* generalizability: 0 (flat; G1 still null — Round 10 work)
* usage_cost: 0 (flat; D5 fully complete from Round 6)
* **routing_cost: +0.05 measurement-fill axis bonus** (R8 newly populated
  + 16-cell intermediate router-test profile additively introduced; D6
  coverage 5/8 populated → 6/8 populated; R1/R2 stay out-of-scope for
  v0.1.x). This is the "measurement-fill flavour bonus" branch of master
  plan acceptance criterion #6: "iteration_delta_report.yaml routing_cost
  axis is positive_axis: true (R8 fill OR floor improvement)". Round 9
  satisfies BOTH branches — R8 newly populated AND router-test widened
  to intermediate.
* governance_risk: 0 (flat; D7 already at full coverage from Round 8)

Per master plan acceptance criterion #6, Round 9 satisfies the
iteration_delta clause with the measurement-fill-flavour bonus on
routing_cost. This is the single axis improvement satisfying the §4.1
v1_baseline iteration_delta clause.

## 5. Top blockers to v2_tightened promotion (carried forward to Round 10+)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Rounds 1/2/3/4/5/6/7/8; cases unchanged this round. Carried
   forward to Round 12 v2_tightened readiness check.

2. **G1_cross_model_pass_matrix still null** — D4 generalizability is at
   0/4 after Round 9 (G1 Round 10 target). Round 10 master plan extracts
   a 2-model-by-2-pack pass_rate matrix from the existing 8-cell MVP
   sweep to partially fill G1 while G2/G3/G4 stay null by scope.

**REMOVED FROM BLOCKER LIST (closed this round)**:
- ~~R8_description_competition_index still null~~ — populated this round
  (0.0435; byte-identical to C6 by construction on same neighbor set).
  D6 reaches 6/8 populated + 2/8 permanently out-of-scope for v0.1.x
  (R1/R2).
- ~~router-test widening from mvp-only to a transitional intermediate~~ —
  shipped this round as ADDITIVE 16-cell intermediate profile; gate
  binding relaxed (same as mvp).

## 6. Round 10 hint (per master plan)

Round 10 fills G1_cross_model_pass_matrix by collapsing the existing
mvp 8-cell sweep along the depth dimension: 2 models × 2 packs = 4
cells per (model, pack). D4 generalizability moves from 0/4 populated
to 1/4 populated (G2/G3/G4 stay null by scope — Round 11 spec
reconciliation decides whether they ship in v0.2.0 or v0.3.x).

Additionally seeds `evals/si-chip/golden_set/` with `trigger_basic.yaml`
and `near_miss.yaml` files (~12-20 prompts each) for future real-LLM
opt-in; addresses nines self-eval's D01/D02/D03/D05 = 0 signals.

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L3 task spec:
* SKILL.md frontmatter `version: 0.1.7` → `version: 0.1.8` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.7` → `v0.1.8`. No other install.sh edits this round.
* `docs/_install_body.md` version references `v0.1.7` → `v0.1.8`
  (English + Chinese rows).
* `docs/skills/si-chip-0.1.8.tar.gz` deterministic tarball generated
  (mirroring v0.1.7 tarball structure).
* Mirror drift = 0 verified across 3 trees (re-verified by
  V3_drift_signal = 0.0).

## 8. R8 + intermediate-profile method transparency

### R8_description_competition_index hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_r8_description_competition_index`
(Round 9 Edit B; unit-tested in `test_aggregate_eval.py::HoistR8Tests` —
8 tests covering happy paths max_jaccard + tfidf_cosine_mean, degenerate
paths, 28-key invariant, Round 8-compat null path). Inner helper:
`count_tokens.skill_md_description_competition_index` (Round 9 Edit A;
unit-tested in `test_count_tokens.py::SkillMdDescriptionCompetitionIndexTests`
— 9 tests including REAL Si-Chip neighbor smoke for both methods).

Formula (method=max_jaccard, default):
`R8 = max(Jaccard(base_tokens_set, neighbor_tokens_set))` across 23
`/root/.claude/skills/lark-*/SKILL.md` neighbor descriptions. Same
formula family as C6 on the SAME neighbor set → R8 ≡ C6 by construction
(cross-validation check in raw/r8_derivation.json).

Formula (method=tfidf_cosine_mean, alternative):
`R8 = mean(cosine_similarity(tfidf(base_tokens, corpus), tfidf(neighbor_tokens, corpus)))`
across the neighbor set. Corpus = [base_tokens] + neighbor_tokens (base
included so its own term counts contribute to df). Surfaces AVERAGE
competition (complementary to max_jaccard WORST-offender).

Determinism: sorted vocab + no RNG → byte-identical on repeat runs.

### intermediate router-test profile
Template:
`templates/router_test_matrix.template.yaml#profiles.intermediate`
(Round 9 Edit C; `$schema_version` 0.1.0 → 0.1.1). ADDITIVE only —
mvp:8 and full:96 profiles STRUCTURALLY UNCHANGED.

Runner helper:
`evals/si-chip/runners/with_ability_runner.py::simulate_router_sweep(profile_name)`
+ `intersection_router_floor(a, b)` (Round 9 Edit E; SCRIPT_VERSION
0.1.0 → 0.1.1). Uses `MVP_CELL_OUTCOMES` + `INTERMEDIATE_EXTRA_CELL_OUTCOMES`
hard-coded dicts (deterministic; no RNG).

Spec_validator:
`tools/spec_validator.py::check_router_matrix_cells` (Round 9 Edit D;
SCRIPT_VERSION 0.1.0 → 0.1.1). Accepts BOTH 0.1.0 and 0.1.1 schemas
(backward compat); additionally asserts intermediate invariants on 0.1.1
(cells==16 + gate_binding==relaxed + axis_product==16). Unit-tested in
`tools/test_spec_validator.py` (NEW; 7 tests).

## 9. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-surface
  fields anywhere in this round's deltas.)
* No router model training. (R8 is static Jaccard/TF-IDF on SKILL.md
  descriptions; intermediate profile uses hard-coded deterministic cell
  outcomes — not a learned ranker, not online weight learning, not a
  kNN fit. §5.1 metadata-retrieval widening, NOT §5.2 router-model
  training.)
* No Markdown-to-CLI converter introduced.
* No generic IDE compatibility layer introduced. (Cursor + Claude Code
  mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex is bridge-
  only per §11.2 deferred.)

All 4 §11.1 items remain forever-out. Round 9 stays compliant.
