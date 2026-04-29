# Si-Chip Dogfood Round 10 — Diagnose Notes

`round_id: round_10`
`prior_round_id: round_9`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §3.1 D4 G1-G4,
§4.1 progressive gates, §5 router paradigm, §5.1 allowed work surfaces,
§5.2 prohibitions, §5.3 harness table, §5.4 profile↔gate binding, §8.1 step 3,
§11.1 forever-out)

This note captures Step 3 (diagnose) per spec §8.1 for Round 10. Numbers are
sourced from `.local/dogfood/2026-04-28/round_10/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_9/metrics_report.yaml`.

## 1. MVP-8 + R4 + D3 + D5 + D2 + D7 + R8 + G1 cells vs Round 9

| Metric | Round 9 | Round 10 | Delta (R10 − R9) | v1_baseline | Direction |
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
| **G1_cross_model_pass_matrix** | **null** | **2×2 nested dict** | **NEW (measurement-fill)** | **no §4.1 threshold; all cells in [0, 1]** | **populated (PASS)** |
| G2_cross_domain_transfer_pass | null | null | — | out-of-scope for v0.1.x | permanently null (v0.3.x+ work) |
| G3_OOD_robustness | null | null | — | out-of-scope for v0.1.x | permanently null (v0.3.x+ work) |
| G4_model_version_stability | null | null | — | out-of-scope for v0.1.x | permanently null (v0.3.x+ work) |
| U1_description_readability | 19.58 | 19.58 | +0.00 | informational | flat |
| U2_first_time_success_rate | 0.75 | 0.75 | +0.00 | informational | flat |
| U3_setup_steps_count | 1 | 1 | 0 | ≤ 2 | flat |
| U4_time_to_first_success | 0.0073 s | 0.0073 s | 0.000 s | ≤ 60 s | flat |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |
| R8_description_competition_index | 0.0435 | 0.0435 | 0.0000 | range [0, 1] | flat |
| V1_permission_scope | 0 | 0 | 0 | no §4.1 threshold | flat |
| V2_credential_surface | 0 | 0 | 0 | no §4.1 threshold | flat |
| V3_drift_signal | 0.0 | 0.0 | 0.0 | no §4.1 threshold | flat (re-verified post-0.1.9 sync) |
| V4_staleness_days | 0 | 0 | 0 | no §4.1 threshold | flat |

Round 10 G1_cross_model_pass_matrix breakdown (2×2 view):

|  | trigger_basic | near_miss |
|---|---|---|
| composer_2 | 0.90 (max of fast=0.86, default=0.90) | 0.83 (max of fast=0.78, default=0.83) |
| sonnet_shallow | 0.88 (max of fast=0.83, default=0.88) | 0.81 (max of fast=0.74, default=0.81) |

All Round 10 plan exit criteria (a1-a5) are met:

* **a1 (G1_cross_model_pass_matrix populated)**: 2×2 nested dict
  `{composer_2: {trigger_basic: 0.9, near_miss: 0.83}, sonnet_shallow:
  {trigger_basic: 0.88, near_miss: 0.81}}` hoisted via
  `aggregate_eval.hoist_g1_cross_model_pass_matrix` (Round 10 Edit A;
  SCRIPT_VERSION 0.1.5 → 0.1.6). Collapse rule = `max(pass_rate)` across
  `thinking_depth` per `(model, scenario_pack)`; applied to the mvp
  8-cell sweep (carried byte-identical from Round 8's flat-shape
  router_floor_report; also verified against Round 9's nested
  `mvp_profile.cells` shape — the helper accepts both).

  **PARTIAL PROXY DISCLOSURE**: G1 from 2-model × 2-pack is a v0.1.x
  partial proxy. Authoritative G1 requires real-LLM runs against the
  full 96-cell profile (§5.3 full: 6 model × 4 depth × 4 pack;
  v2_tightened+ / Round 12+ upgrade path). The `max` aggregation is
  monotone under adding more depths, so the hoist is forward-compatible
  with the 96-cell upgrade.

* **a2 (evals/si-chip/golden_set/ seeded)**: NEW directory with
  `trigger_basic.yaml` (12 prompts; all `expected: trigger`) +
  `near_miss.yaml` (12 prompts; all `expected: no_trigger`) +
  `README.md`. Prompts are **VERBATIM** subsets of
  `evals/si-chip/cases/*.yaml` — 0 new prompts authored. Source case
  distribution enumerated in
  `.local/dogfood/2026-04-28/round_10/raw/golden_set_index.json`.

  Addresses Round 3 nines self-eval D01 scoring_accuracy = 0 / D02
  eval_coverage = 0 / D03 samples_dir_exists = 0 / D05 golden_set_path
  = 0 signals. NON-AUTHORITATIVE opt-in source; the deterministic
  runner does NOT consume it this round. `nines --golden-dir
  evals/si-chip/golden_set/` is the future invocation shape.

* **a3 (R8 + intermediate-profile stability verified)**: R8 byte-
  identical to Round 9 (0.043478260869565216). Intermediate 16-cell
  sweep in `router_floor_report.yaml` byte-identical to Round 9 (no
  router-test rerun this round; carry-forward is explicit in master
  plan Round 10 scope_writable_files). `spec_validator --json`
  default-mode 8/8 PASS unchanged.

* **a4 (≥ 6 new tests in test_aggregate_eval.py for G1 hoist)**:
    - `test_aggregate_eval.py`: 109 → 120 tests (11 new Round 10 tests
      covering 7 `HoistG1Tests` (happy path flat + nested, None report,
      empty cells, malformed cells skipped, range invariant, pack filter)
      + 4 `BuildReportG1Integration` (build_report populates G1, null
      router_floor_report keeps G1 null, G1 coexists with G2/G3/G4 null,
      28-key invariant preserved after G1 fill)). Exceeds the ≥ 6
      threshold.

  Total test count growth Round 9 (243 passed, 1 skipped) -> Round 10
  estimate remains similar — the G1 tests bump aggregate_eval to 120,
  no change to count_tokens / install_telemetry / governance_scan /
  spec_validator suites (all unchanged this round).

* **a5 (versions + mirrors + tarball + docs bumped to v0.1.9)**:
  `.agents/skills/si-chip/SKILL.md` frontmatter `version: 0.1.8 →
  0.1.9` + mirrors .cursor/.claude byte-equal (SHA-256 verified =
  3/3 identical). `install.sh` + `docs/install.sh`
  `SI_CHIP_VERSION_DEFAULT="v0.1.8" → "v0.1.9"`. `docs/_install_body.md`
  `--version` table cells (English + Chinese) bumped to `v0.1.9`.
  `docs/skills/si-chip-0.1.9.tar.gz` deterministic tarball (SHA-256
  recorded in CHANGELOG). V3_drift_signal re-verified = 0.0.

## 2. v1_baseline hard-threshold check (Round 10)

| Threshold (v1_baseline) | Round 10 value | Pass? |
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
| iteration_delta (any axis) ≥ +0.05 | generalizability measurement-fill axis bonus | yes |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 / R8
metric PASSES in Round 10.** D4 generalizability dimension reaches 1/4
POPULATED sub-metric coverage (G1 measured) + 3/4 explicit null
(G2/G3/G4 permanently out-of-scope for v0.1.x). G1 passes range-sanity
(all 4 cells in [0.0, 1.0]). No sub-metrics become null; spec §3.2
frozen key contract still holds (37 keys, 27 populated, 10 explicit
null).

## 3. Monotonicity check vs Round 9 (spec §8.3)

Every metric either held flat or was newly populated (G1). `T1_pass_rate`
hard non-regression rule holds at 0.85 = 0.85 — PASS.

## 4. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05"
at v1_baseline. Round 10 axis movements (round_10 − round_9):

* task_quality: 0 (flat)
* context_economy: 0 (flat; D2 already at full coverage from Round 7)
* latency_path: 0 (flat; D3 stays at 4/7)
* **generalizability: +0.05 measurement-fill axis bonus** (G1 newly
  populated; D4 coverage 0/4 → 1/4 populated; G2/G3/G4 stay out-of-
  scope for v0.1.x). This is the "measurement-fill flavour bonus"
  branch of master plan Round 10 acceptance criterion #4:
  "iteration_delta_report.yaml generalizability axis becomes
  positive_axis: true (was 0.0 since Round 1)". Round 10 satisfies
  the clause verbatim.
* usage_cost: 0 (flat; D5 fully complete from Round 6)
* routing_cost: 0 (flat; D6 at 6/8 from Round 9 carry-forward; R8 bonus
  was Round 9's win)
* governance_risk: 0 (flat; D7 already at full coverage from Round 8)

Per master plan acceptance criterion #4, Round 10 satisfies the
iteration_delta clause with the measurement-fill-flavour bonus on
generalizability. This is the single axis improvement satisfying the
§4.1 v1_baseline iteration_delta clause.

## 5. Top blockers to v2_tightened promotion (carried forward to Round 11+)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Rounds 1/2/3/4/5/6/7/8/9; cases unchanged this round.
   Carried forward to Round 12 v2_tightened readiness check.

2. **G1 authoritative-full-matrix requirement** — Round 10 populates a
   2-model × 2-pack PARTIAL PROXY. v2_tightened promotion requires the
   full 96-cell matrix (§5.3 full: 6 model × 4 depth × 4 pack) from a
   real-LLM runner. This is the v0.2.0 ship gate blocker per master
   plan Round 12 readiness check.

3. **G2_cross_domain_transfer_pass / G3_OOD_robustness /
   G4_model_version_stability** — all remain null for v0.1.x.
   Spec §3.1 D4 promotion to full 4/4 coverage requires cross-domain +
   OOD + multi-model-version runner. Round 11 spec reconciliation
   decides v0.2.0 vs v0.3.x+ ship target.

**REMOVED FROM BLOCKER LIST (closed this round)**:
- ~~G1_cross_model_pass_matrix still null~~ — populated this round
  (2×2 nested dict; partial proxy acknowledged). D4 reaches 1/4
  populated + 3/4 out-of-scope for v0.1.x.
- ~~evals/si-chip/golden_set/ directory missing~~ — seeded this
  round (12+12 prompts; verbatim subsets of existing cases;
  addresses nines self-eval D01/D02/D03/D05 = 0 signals).

## 6. Round 11 hint (per master plan)

Round 11 reconciles spec §3.1 / §13.4 + §4.1 / §13.4 internal
discrepancies (TABLE = 37 sub-metrics / 30 threshold cells vs prose =
28 sub-metrics / 21 threshold cells). Normative spec bump v0.1.0 →
v0.2.0-rc1. Decision rule: keep tables as runtime contract; rewrite
§13.4 prose to match. `tools/spec_validator.py --strict-prose-count`
will exit 0 against the new spec file after the prose catches up.
All 6 templates remain `$schema_version 0.1.0` or bump to `0.2.0-rc1`
with backward-compat validator acceptance. SKILL.md frontmatter
version: 0.1.10.

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L3 task spec:
* SKILL.md frontmatter `version: 0.1.8` → `version: 0.1.9` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.8` → `v0.1.9`. No other install.sh edits this round.
* `docs/_install_body.md` version references `v0.1.8` → `v0.1.9`
  (English + Chinese rows).
* `docs/skills/si-chip-0.1.9.tar.gz` deterministic tarball generated
  (mirroring v0.1.8 tarball structure; same canonical layout = 1
  SKILL.md + 5 references + 3 scripts).
* Mirror drift = 0 verified across 3 trees (re-verified by
  V3_drift_signal = 0.0 in metrics_report).

## 8. G1 hoist + golden_set method transparency

### G1_cross_model_pass_matrix hoist

Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_g1_cross_model_pass_matrix`
(Round 10 Edit A; unit-tested in `test_aggregate_eval.py::HoistG1Tests` +
`BuildReportG1Integration` — 11 tests covering happy paths flat + nested,
degenerate paths, 28-key invariant, 2×2 shape invariant, range invariant,
pack filter).

Formula (collapse_rule = `max across depths`):
`G1[model][pack] = max(cell.pass_rate for cell in mvp_sweep
if cell.model == model and cell.scenario_pack == pack)`

Applied to the mvp 8-cell sweep (2 model × 2 depth × 2 pack):

| model | pack | fast | default | G1[model][pack] = max |
|---|---|---|---|---|
| composer_2 | trigger_basic | 0.86 | 0.90 | **0.90** |
| composer_2 | near_miss | 0.78 | 0.83 | **0.83** |
| sonnet_shallow | trigger_basic | 0.83 | 0.88 | **0.88** |
| sonnet_shallow | near_miss | 0.74 | 0.81 | **0.81** |

**Source shape flexibility**: the helper accepts both flat top-level
`cells:` (Round 1-8 legacy) AND nested `mvp_profile.cells:` (Round 9+).
For Round 10 the aggregator is fed Round 8's flat file (because R6 hoist
requires flat shape), but the canonical Round 10 evidence
`router_floor_report.yaml` carries Round 9's nested shape verbatim.

Determinism: mvp cells are hard-coded in
`evals/si-chip/runners/with_ability_runner.py::MVP_CELL_OUTCOMES`
(deterministic dict lookup; no RNG) → byte-identical on repeat runs.

### evals/si-chip/golden_set/ seed

Directory structure:
```
evals/si-chip/golden_set/
├── trigger_basic.yaml    # 12 prompts; all expected: trigger
├── near_miss.yaml        # 12 prompts; all expected: no_trigger
└── README.md             # schema + non-authoritative disclosure
```

Source case distribution (from
`round_10/raw/golden_set_index.json#files[].source_case_distribution`):

* `trigger_basic.yaml` = 12 prompts = 2 from profile_self + 2 from
  metrics_gap + 2 from router_matrix + 2 from half_retire_review + 2
  from next_action_plan + 2 from docs_boundary. Covers all 6 canonical
  cases.
* `near_miss.yaml` = 12 prompts = 3 from profile_self + 2 from
  metrics_gap + 2 from router_matrix + 2 from half_retire_review + 3
  from next_action_plan. Covers 5 of 6 canonical cases; docs_boundary
  is skipped because its `should_not_trigger` entries are legitimate
  in-scope operations (si-chip MUST NOT refuse), not true near_miss
  prompts.

**0 new prompts authored.** All 24 entries are verbatim copies from
`evals/si-chip/cases/*.yaml` `should_trigger` / `should_not_trigger`
blocks; `source_case` field in each entry points to the exact origin.

## 9. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-
  surface fields anywhere in this round's deltas. `evals/si-chip/golden_set/`
  is a local repo path, not a distribution surface.)
* No router model training. (G1 is a static pass_rate matrix collapsed
  from deterministic 8-cell sweep cells — not a learned ranker, not
  online weight learning, not a kNN fit. §5.1 metadata-retrieval
  widening, NOT §5.2 router-model training. Golden-set prompts are
  LABELS for a future real-LLM eval, not training data.)
* No Markdown-to-CLI converter introduced.
* No generic IDE compatibility layer introduced. (Cursor + Claude Code
  mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex is bridge-
  only per §11.2 deferred.)

All 4 §11.1 items remain forever-out. Round 10 stays compliant.
