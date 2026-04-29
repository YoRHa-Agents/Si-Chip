# Si-Chip Dogfood Round 7 — Diagnose Notes

`round_id: round_7`
`prior_round_id: round_6`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §8.1 step 3)

This note captures Step 3 (diagnose) per spec §8.1 for Round 7. Numbers are
sourced from `.local/dogfood/2026-04-28/round_7/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_6/metrics_report.yaml`.

## 1. MVP-8 + R4 + D3 + D5 + D2 cells vs Round 6

| Metric | Round 6 | Round 7 | Delta (R7 − R6) | v1_baseline | Direction |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | +0.00 | ≥ 0.75 | flat (no regression) |
| T2_pass_k | 0.5478 | 0.5478 | +0.0000 | ≥ 0.40 | flat |
| T3_baseline_delta | +0.35 | +0.35 | +0.00 | informational | flat |
| C1_metadata_tokens | 82 | 82 | +0 (+0.00%) | ≤ 120 | flat |
| C2_body_tokens | 2020 | 2020 | 0 | informational | flat |
| C3_resolved_tokens | null | null | — | by-design null | permanently null |
| C4_per_invocation_footprint | 3602 | 3602 | +0 (+0.00%) | ≤ 9000 | flat |
| **C5_context_rot_risk** | **null** | **0.2601** | **NEW (measurement-fill)** | **no §4.1 threshold; range [0, 1]** | **populated (PASS)** |
| **C6_scope_overlap_score** | **null** | **0.0435** | **NEW (measurement-fill)** | **no §4.1 threshold; range [0, 1]** | **populated (PASS)** |
| L1_wall_clock_p50 | 1.215 s | 1.215 s | 0.000 s | informational | flat |
| L2_wall_clock_p95 | 1.469 s | 1.469 s | 0.000 s | ≤ 45 s | flat |
| L3_step_count | 20 | 20 | 0 | informational | flat |
| L4_redundant_call_ratio | 0.0 | 0.0 | 0.0 | informational | flat |
| U1_description_readability | 19.58 | 19.58 | +0.00 | informational | flat |
| U2_first_time_success_rate | 0.75 | 0.75 | +0.00 | informational | flat |
| U3_setup_steps_count | 1 | 1 | 0 | ≤ 2 (master plan target) | flat |
| U4_time_to_first_success | 0.0073 s | 0.0073 s | 0.000 s | ≤ 60 s sanity ceiling | flat |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |

All Round 7 plan exit criteria (a1, a2, a3, a4, a5) are met:

* **a1 (C5_context_rot_risk populated)**: 0.2601 hoisted from
  `count_tokens.skill_md_context_rot_risk` via
  `aggregate_eval.hoist_c5_context_rot_risk` (Round 7 Edit B). Formula
  = `clip(body_tokens/typical_window + 0.05*fanout_depth, 0, 1)` =
  `clip(2020/200_000 + 0.05*5, 0, 1)` = `0.2601`. body_tokens=2020
  (C2, carried from Round 6), typical_window=200_000 (Sonnet 4.6
  baseline per `references/metrics-r6-summary.md`), fanout_depth=5
  (literal substring match: all 5 `.md` files under
  `.agents/skills/si-chip/references/` are named in SKILL.md body).

  Range sanity gate `[0.0, 1.0]` PASS. No §4.1 hard threshold on C5 —
  range sanity is the only gate per master plan Round 7 risk_flag
  (C5 is a v1_baseline-acceptable heuristic proxy; full ground-truth
  measurement is a Round 12 / real-LLM-runner upgrade candidate).

  **Plan vs actual note**: Master plan Round 7 rationale estimated
  `C5 ≈ 0.06` based on `fanout_depth = 1` (graph-depth
  interpretation). The L3 Task Spec §1 literal formula counts the
  number of referenced `.md` files = 5, yielding 0.25. The actual
  value 0.2601 satisfies the acceptance criterion (non-null AND in
  `[0.0, 1.0]`); the discrepancy is documented in
  `raw/c5_derivation.json#plan_vs_actual_note`.

* **a2 (C6_scope_overlap_score populated)**: 0.0435 hoisted from
  `count_tokens.skill_md_scope_overlap_score` via
  `aggregate_eval.hoist_c6_scope_overlap_score` (Round 7 Edit B).
  Formula = max Jaccard similarity across 23 neighbor SKILL.md
  descriptions under `/root/.claude/skills/lark-*/SKILL.md`. Si-Chip
  description has 21 tokens post-stopword filtering; no neighbor
  exceeds 1/23 token overlap — `lark-whiteboard-cli` tops the pack
  at `1/23 = 0.0435`.

  Range sanity gate `[0.0, 1.0]` PASS. No §4.1 hard threshold on C6 —
  range sanity is the only gate. The full per-pair enumeration is
  recorded in `raw/c6_overlap_pairs.json`; reproducibility is
  deterministic given a fixed neighbor set.

  **Neighbor set note**: The lark-* family was chosen because it is
  the only neighbor skill family present in the workspace at round_7
  time. R8 (Round 9 target) will replace this conservative-max with
  the formal across-matrix description-competition index.

* **a3 (≥ 12 new unit tests covering C5/C6 helpers + build_report
  integration)**: 33 new tests in
  `.agents/skills/si-chip/scripts/test_count_tokens.py` (32 → 65)
  cover:
    - `context_rot_risk` slim body (< 0.10), saturation (== 1.0 at
      body == typical_window), degenerate body=0 returns fanout term
      only, range clamp to `[0.0, 1.0]`, negative fanout/body raise
      ValueError, zero typical_window raises ValueError,
      typical_window override reduces value
    - `skill_md_context_rot_risk` real-SKILL.md integration (returns
      value in `[0.0, 1.0]` with `fanout_depth >= 1` for the
      canonical source tree), no-refs-dir zero-fanout, missing
      refs-dir logged-and-degrades, references-present-but-not-cited
      yields zero fanout, cited refs increment fanout, missing
      SKILL.md raises
    - `jaccard_similarity` identical=1, disjoint=0, partial overlap
      deterministic, both-empty=0 by convention, one-empty=0,
      range invariant
    - `tokenize_description` basic, stopword filter, custom empty
      stopwords disables filter, hyphen separator, empty=empty,
      non-ASCII stripped
    - `skill_md_scope_overlap_score` max-reduction across neighbors,
      all-disjoint=0, missing-neighbor logged+skipped,
      missing-base raises, empty-neighbors=0, real Si-Chip vs lark-*
      integration (< 0.30)
  Plus 15 new tests in `.agents/skills/si-chip/scripts/test_aggregate_eval.py`
  (65 → 80) covering `hoist_c5_context_rot_risk` happy path and
  degenerate paths, `hoist_c6_scope_overlap_score` happy path and
  degenerate paths, `build_report` C5+C6 integration, missing
  skill_md keeps C5+C6 null, empty neighbor list keeps C6 = 0.0,
  range invariant, 28-key invariant preserved, CLI flag round-trip
  via subprocess.

  All 164 tests (test_count_tokens + test_aggregate_eval +
  test_install_telemetry) PASS under `python -m pytest`.

* **a4 (U3 + U4 have not regressed)**: Both numbers carry forward
  byte-identically from Round 6 because:
    - U3 depends only on the `# SI_CHIP_INSTALLER_STEPS=1` header in
      `install.sh` (header unchanged this round).
    - U4 depends only on the install_telemetry.json from Round 6
      (re-used directly; install.sh argument parsing and control
      flow are unchanged).
  U3 stable at 1 (exactly equal); U4 stable at 0.00729… s (exactly
  equal because we re-use the Round 6 payload). Master plan
  acceptance criterion #4 satisfied trivially.

* **a5 (top-3 blockers for Round 12 v2_tightened readiness)**:
  See §5 below. Three blockers identified; all three carry forward
  from Round 5/6 diagnose notes and align with the master plan
  Rounds 8/9/12 scope.

## 2. v1_baseline hard-threshold check (Round 7)

| Threshold (v1_baseline) | Round 7 value | Pass? |
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
| iteration_delta (any axis) ≥ +0.05 | context_economy measurement-fill axis bonus | yes (per master plan acceptance criterion #5 alternative) |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 metric PASSES in
Round 7.** D2 context_economy dimension reaches **5/6 measured + 1 by-design
null** sub-metric coverage at v1_baseline (was 3/6 at Round 6 — C5, C6 newly
populated). **D2 is now COMPLETE in the measurement-attempt sense — every
D2 cell has been either measured or explicitly documented as
permanently-null.** C5 and C6 also pass range-sanity gates. No new
sub-metrics become null; spec §3.2 frozen key contract still holds.

## 3. Monotonicity check vs Round 6 (spec §8.3)

| Metric | Round 6 | Round 7 | pct_change | direction | pass? |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | 0.00% | flat | yes |
| T2_pass_k | 0.5478 | 0.5478 | 0.00% | flat | yes |
| T3_baseline_delta | 0.35 | 0.35 | 0.00% | flat | yes |
| C1_metadata_tokens | 82 | 82 | 0.00% | flat | yes |
| C2_body_tokens | 2020 | 2020 | 0.00% | flat | yes |
| C4_per_invocation_footprint | 3602 | 3602 | 0.00% | flat | yes |
| L1_wall_clock_p50 | 1.2153 | 1.2153 | 0.00% | flat | yes |
| L2_wall_clock_p95 | 1.4693 | 1.4693 | 0.00% | flat | yes |
| L3_step_count | 20 | 20 | 0.00% | flat | yes |
| L4_redundant_call_ratio | 0.0 | 0.0 | 0.00% | flat | yes |
| U1_description_readability | 19.58 | 19.58 | 0.00% | flat | yes |
| U2_first_time_success_rate | 0.75 | 0.75 | 0.00% | flat | yes |
| U3_setup_steps_count | 1 | 1 | 0.00% | flat | yes |
| U4_time_to_first_success | 0.0073 | 0.0073 | 0.00% | flat | yes |
| R3_trigger_F1 | 0.8934 | 0.8934 | 0.00% | flat | yes |
| R4_near_miss_FP_rate | 0.05 | 0.05 | 0.00% | flat | yes |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0.00% | flat | yes |
| R7_routing_token_overhead | 0.0233 | 0.0233 | 0.00% | flat | yes |

**T1_pass_rate MUST NOT regress** (spec §8.3 hard rule); Round 7 holds at 0.85,
exactly equal to Round 6 — PASS. No metric regressed by more than 1%; no
release-attribution exceptions need to be invoked this round. Newly-populated
C5 and C6 are flagged as "NEWLY APPLICABLE — was null at Round 6; not a
regression" per the iteration_delta_report monotonicity_check.

## 4. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05" at
v1_baseline. Round 7 axis movements (round_7 − round_6):

* task_quality: 0 (flat)
* **context_economy: +0.05 measurement-fill axis bonus** (C5 + C6 newly
  populated; D2 coverage 3/6 measured → 5/6 measured + 1 by-design null =
  full D2 measurement-attempt completion). This is the "measurement-fill
  flavour bonus" branch of master plan acceptance criterion #5:
  "iteration_delta_report.yaml context_economy axis stays positive (no
  body regression vs Round 2's 2020 tokens)". Round 7 satisfies the
  measurement-fill alternative: C5 + C6 newly populated AND C2 stays at
  2020 (no body regression).
* latency_path: 0 (flat; L1/L2/L3/L4 unchanged; D3 stays at 4/7 coverage)
* generalizability: 0 (flat; G1 still null — Round 10 work)
* usage_cost: 0 (flat; D5 is already fully complete at 4/4 measured from
  Round 6 onwards)
* routing_cost: 0 (flat; R8 still null — Round 9 work)
* governance_risk: 0 (flat; V1-V4 still null — Round 8 work)

Per master plan acceptance criterion #5, Round 7 satisfies this with the
measurement-fill-flavour bonus on context_economy. This is the single axis
improvement satisfying the §4.1 v1_baseline iteration_delta clause.

## 5. Top-3 BLOCKERS to v2_tightened promotion (carried forward to Round 8+)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Rounds 1/2/3/4/5/6; cases unchanged this round. Carried forward
   to Round 12 v2_tightened readiness check.

2. **R8_description_competition_index still null** — D6 routing_cost is
   at 7/8 after Round 7 (R1, R2 permanently null; R8 Round 9 target).
   Round 9 master plan widens this into a formal across-matrix index
   (distinct from Round 7's C6 conservative-max).

3. **V1-V4 governance_risk sub-metrics still null** — D7 is at 0/4
   after Round 7; Round 8 master plan target fills all four
   (`tools/governance_scan.py` to inventory filesystem writes,
   credential patterns, drift signals, and staleness days). D7 full
   coverage is the last dimension before Round 9 + 10 + 11 + 12 ship
   prep.

## 6. Round 8 hint (per master plan)

Round 8 fills D7 governance_risk (V1+V2+V3+V4) to complete the governance
dimension. The diagnose findings here flag:

* **V1 derivation strategy**: V1 = filesystem-write inventory via
  `tools/governance_scan.py`. Walks the skill's script sources +
  templates + install.sh to enumerate write surfaces (mkdir,
  open-for-write, subprocess invocation of rm/mv, etc.). Currently
  expected = 0 (clean).

* **V2 derivation strategy**: V2 = secret-pattern scan via
  `tools/governance_scan.py`. Pattern list: `{API_KEY,
  AWS_ACCESS_KEY_ID, password, token, secret, private_key, bearer}`.
  **CRITICAL**: scanner MUST NOT log secret values — only pattern
  names + counts + file locations.

* **V3 derivation strategy**: V3 = `1 - cross_tree_drift_zero` ratio
  across the 3 mirrors. Reuse Round 6/7 drift-check pattern.

* **V4 derivation strategy**: V4 = days since
  `basic_ability_profile.lifecycle.last_reviewed_at`.

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L3 task spec:
* SKILL.md frontmatter `version: 0.1.5` → `version: 0.1.6` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.5` → `v0.1.6`. No other install.sh edits this round.
* `docs/_install_body.md` version references `v0.1.5` → `v0.1.6`
  (English + Chinese rows).
* `docs/skills/si-chip-0.1.6.tar.gz` deterministic tarball generated
  (mirroring v0.1.5 tarball structure).
* Mirror drift = 0 verified across 3 trees.

## 8. C5 / C6 hoist methods (transparency)

### C5_context_rot_risk hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_c5_context_rot_risk`
(Round 7 Edit B; unit-tested in
`test_aggregate_eval.py::HoistC5Tests` — 4 tests covering happy path,
none-path, missing-skill-md raises, no-refs-dir zero-fanout). Inner
helper:
`.agents/skills/si-chip/scripts/count_tokens.py::skill_md_context_rot_risk`
(Round 7 Edit A; unit-tested in
`test_count_tokens.py::SkillMdContextRotRiskTests` — 6 tests covering
real SKILL.md integration + 5 edge-case paths).

Formula: `C5 = clip(body_tokens/typical_window + 0.05*fanout_depth, 0, 1)`.
body_tokens from `count_tokens(SKILL.md body)` (tiktoken backend).
typical_window = 200_000 (default; Sonnet 4.6). fanout_depth = literal
substring-count of `*.md` files in references_dir whose filename appears
in SKILL.md body.

Determinism: No RNG, no external dependency beyond tiktoken's frozen
encoding. Repeat calls yield byte-identical output.

### C6_scope_overlap_score hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_c6_scope_overlap_score`
(Round 7 Edit B; unit-tested in
`test_aggregate_eval.py::HoistC6Tests` — 5 tests covering happy path,
none-skill-md, empty-neighbors, missing-base raises, missing-neighbor
recorded in pairs). Inner helper:
`.agents/skills/si-chip/scripts/count_tokens.py::skill_md_scope_overlap_score`
(Round 7 Edit A; unit-tested in
`test_count_tokens.py::SkillMdScopeOverlapScoreTests` — 6 tests).

Formula: `C6 = max(jaccard_similarity(tokenize(base_desc), tokenize(neighbor_desc)))`
across the neighbor set. Tokenisation pipeline: NFKD → lowercase →
strip ASCII-non-alphanumeric → split whitespace → filter minimal
stopwords.

Determinism: NFKD normalisation is the Unicode standard. No RNG, no
external wordlist. Set-based Jaccard is order-independent. Given the
same SKILL.md + same neighbor set, output is byte-identical every
rebuild.

## 9. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-surface
  fields anywhere in this round's deltas.)
* No router model training. (C5 + C6 are MEASUREMENT improvements via
  static string analysis; no online weight learning, no classifier
  training, no kNN model fit. The router_floor_report is re-emitted
  verbatim from Round 6.)
* No Markdown-to-CLI converter introduced. (The C5/C6 helpers
  MEASURE SKILL.md structure but do not convert markdown to a CLI.)
* No generic IDE compatibility layer introduced. (Cursor + Claude Code
  mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex is bridge-only
  per spec §11.2 deferred.)

All 4 §11.1 items remain forever-out. Round 7 stays compliant.
