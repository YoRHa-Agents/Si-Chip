# Si-Chip Dogfood Round 5 — Diagnose Notes

`round_id: round_5`
`prior_round_id: round_4`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §8.1 step 3)

This note captures Step 3 (diagnose) per spec §8.1 for Round 5. Numbers are
sourced from `.local/dogfood/2026-04-28/round_5/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_4/metrics_report.yaml`.

## 1. MVP-8 + R4 + D3 + D5 cells vs Round 4

| Metric | Round 4 | Round 5 | Delta (R5 − R4) | v1_baseline | Direction |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | +0.00 | ≥ 0.75 | flat (no regression) |
| T2_pass_k | 0.5478 | 0.5478 | +0.0000 | ≥ 0.40 | flat |
| T3_baseline_delta | +0.35 | +0.35 | +0.00 | informational | flat |
| C1_metadata_tokens | 82 | 82 | +0 (+0.00%) | ≤ 120 | flat |
| C2_body_tokens | 2020 | 2020 | 0 | informational | flat |
| C4_per_invocation_footprint | 3602 | 3602 | +0 (+0.00%) | ≤ 9000 | flat |
| L1_wall_clock_p50 | 1.215 s | 1.215 s | 0.000 s | informational | flat |
| L2_wall_clock_p95 | 1.469 s | 1.469 s | 0.000 s | ≤ 45 s | flat |
| L3_step_count | 20 | 20 | 0 | informational | flat |
| L4_redundant_call_ratio | 0.0 | 0.0 | 0.0 | informational | flat |
| **U1_description_readability** | **null** | **19.58** | **NEW (measurement-fill)** | **informational** | **populated** |
| **U2_first_time_success_rate** | **null** | **0.75** | **NEW (measurement-fill)** | **informational** | **populated** |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |

All Round 5 plan exit criteria (a1, a2, a3, a4, a5) are met:

* **a1 (U1_description_readability populated)**: 19.58 hoisted from
  SKILL.md frontmatter description via `aggregate_eval.hoist_u1_description_readability`
  (Round 5 Edit B). The helper reads the frontmatter `description:` field
  (via PyYAML), tokenizes with `_FK_WORD_RE`, counts sentences with
  `_FK_SENT_RE` (digit-period stripping applied), counts syllables via
  the vowel-group heuristic with silent-e adjustment, and computes
  `0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59`.
  Counts: 20 words / 2 sentences / 53 syllables. Raw grade 19.58;
  clamped to `[0.0, 24.0]` — no clamp adjustment applied. Range sanity
  check PASS. U1 has no §4.1 hard threshold row at v1_baseline; this is
  fill (not gate movement).

* **a2 (U2_first_time_success_rate populated)**: 0.75 hoisted from
  per-prompt outcomes via `aggregate_eval.hoist_u2_first_time_success_rate`
  (Round 5 Edit B). Numerator (first-time successes on should_trigger
  prompts) = 45; denominator (total should_trigger prompts) = 60; rate =
  0.75. Per case: docs_boundary 9/10, half_retire_review 7/10, metrics_gap
  9/10, next_action_plan 7/10, profile_self 7/10, router_matrix 6/10.
  The deterministic simulator does not retry prompts, so `correct == True`
  on an `expected == "trigger"` prompt IS the first-time success signal.
  Range sanity check PASS ([0.0, 1.0]). U2 has no §4.1 hard threshold row
  at v1_baseline; this is fill.

* **a3 (L1/L3/L4 not regressed)**: carried unchanged from Round 4 to
  4 decimal places (deterministic runner; same seed; baselines byte-
  identical). L1 = 1.2153 s (invariant L1 ≤ L2 still holds: 1.215 ≤
  1.469). L3 = 20. L4 = 0.0 (degenerate VALID).

* **a4 (T2_pass_k carry-forward)**: No Round 5 action; tracked for
  Round 12 v2_tightened readiness check.

* **a5 (Nines signals D14 / D15 cross-referenced)**: U1 derivation
  provenance (`raw/u1_fk_derivation.json`) explicitly cites the Round 3
  Nines self-eval signals D14 (index_recall = 0.20) and D15
  (structure_recognition = 0.75) as upstream motivation. The U1 fill
  addresses the "description quality is the limiting factor" signal
  by making it measurable for the first time.

## 2. v1_baseline hard-threshold check (Round 5)

| Threshold (v1_baseline) | Round 5 value | Pass? |
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
| iteration_delta (any axis) ≥ +0.05 | usage_cost measurement-fill axis bonus | yes (per acceptance criterion #5 alternative) |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 metric PASSES in
Round 5.** D5 usage_cost dimension reaches **2/4** sub-metric coverage at
v1_baseline (was 0/4 at Round 4 — U1, U2 newly populated). U3, U4
(setup_steps_count, time_to_first_success) stay null pending Round 6
install.sh instrumentation and are not §4.1 hard-gated.

## 3. Monotonicity check vs Round 4 (spec §8.3)

| Metric | Round 4 | Round 5 | pct_change | direction | pass? |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | 0.00% | flat | yes |
| T2_pass_k | 0.5478 | 0.5478 | 0.00% | flat | yes |
| T3_baseline_delta | 0.35 | 0.35 | 0.00% | flat | yes |
| C1_metadata_tokens | 82 | 82 | 0.00% | flat | yes |
| C4_per_invocation_footprint | 3602 | 3602 | 0.00% | flat | yes |
| L1_wall_clock_p50 | 1.2153 | 1.2153 | 0.00% | flat | yes |
| L2_wall_clock_p95 | 1.4693 | 1.4693 | 0.00% | flat | yes |
| L3_step_count | 20 | 20 | 0.00% | flat | yes |
| L4_redundant_call_ratio | 0.0 | 0.0 | 0.00% | flat | yes |
| R3_trigger_F1 | 0.8934 | 0.8934 | 0.00% | flat | yes |
| R4_near_miss_FP_rate | 0.05 | 0.05 | 0.00% | flat | yes |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0.00% | flat | yes |
| R7_routing_token_overhead | 0.0233 | 0.0233 | 0.00% | flat | yes |

**T1_pass_rate MUST NOT regress** (spec §8.3 hard rule); Round 5 holds at 0.85,
exactly equal to Round 4 — PASS. No metric regressed by more than 1%; no
release-attribution exceptions need to be invoked this round.

## 4. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05" at
v1_baseline. Round 5 axis movements (round_5 - round_4):

* task_quality: 0 (flat)
* context_economy: 0 (flat; C1 / C4 unchanged this round)
* latency_path: 0 (flat; L1/L2/L3/L4 unchanged; D3 stays at 4/7 coverage)
* generalizability: 0 (flat; G1 still null — Round 10 work)
* **usage_cost: +0.05 measurement-fill bonus** (U1 + U2 newly populated;
  D5 coverage 0/4 → 2/4). The usage_cost axis was 0.0 through Rounds 1-4
  because D5 was fully null; Round 5 is the first round where the
  usage_cost axis carries ANY measurement content. The master-plan-allowed
  "axis is now non-zero (was 0.0 in Round 2-4)" clause is invoked.
* routing_cost: 0 (flat; R8 still null — Round 9 work)
* governance_risk: 0 (flat; V1-V4 still null — Round 8 work)

Per master plan acceptance criterion #5: "iteration_delta_report.yaml
usage_cost axis is now non-zero (was 0.0 in Round 2-4)". Round 5
satisfies this with the measurement-fill axis bonus on usage_cost. This
is the single axis improvement satisfying the §4.1 v1_baseline
iteration_delta clause.

## 5. Top-3 BLOCKERS to v2_tightened promotion (carried forward to Round 6+)

1. **U3_setup_steps_count + U4_time_to_first_success still null** —
   D5 usage_cost coverage is 2/4 after Round 5; U3 + U4 fill requires
   install.sh telemetry instrumentation. **Round 6 master plan action
   set targets U3+U4 fill (via tools/install_telemetry.py + aggregator
   hoist).** Hint: install.sh already has a `--dry-run` path that
   short-circuits I/O; U3 counting (step count to first
   `[OK] Installed` line) can reuse that. U4 is wall-clock from
   `curl | bash` entry to count_tokens.py --file SKILL.md exiting 0.

2. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Rounds 1/2/3/4; cases unchanged this round. Carried forward
   to Round 12 v2_tightened readiness check.

3. **C5_context_rot_risk + C6_scope_overlap_score still null** — D2
   context_economy is at 4/6 (C1, C2, C4 measured; C3 explicit-null
   per resolved-on-demand semantics). Round 7 master plan target.

## 6. Round 6 hint (per master plan)

Round 6 fills D5 usage_cost (U3 + U4) to complete the dimension. The
diagnose findings here flag:

* **U3 derivation strategy**: instrument install.sh with timestamp
  markers at main() entry and at the first post-install verify_install
  success; emit a machine-readable JSON log to
  `.local/dogfood/<date>/round_6/raw/install_telemetry.json`. Count
  steps = # of user-visible prompts fired (0 in --yes mode, 2 in
  interactive mode, 1 in partially-interactive mode). Expected U3 ≤ 2.

* **U4 derivation strategy**: wall-clock from `curl | bash` entry to
  `count_tokens.py --file SKILL.md` exit code 0. Master plan risk_flag:
  U4 is subject to network latency; record p50 + p95 separately when
  variance is high. Expected U4 ≤ 60 s (sanity ceiling).

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L1 task spec:
* SKILL.md frontmatter `version: 0.1.3` → `version: 0.1.4` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.3` → `v0.1.4`.
* `docs/_install_body.md` version references `v0.1.3` → `v0.1.4`
  (English + Chinese rows).
* `docs/skills/si-chip-0.1.4.tar.gz` deterministic tarball generated
  (mirroring v0.1.3 tarball structure, same `tar --sort=name --owner=0
  --group=0 --numeric-owner -cf - ... | gzip -n > ...` flags).
* Mirror drift = 0 verified across 3 trees.

## 8. U1 / U2 hoist methods (transparency)

### U1_description_readability hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_u1_description_readability`
(Round 5 Edit B; unit-tested in `test_aggregate_eval.py::HoistU1Tests` — 5
tests covering happy path, degenerate paths, determinism, and missing-file
raise). Inner helper:
`.agents/skills/si-chip/scripts/count_tokens.py::skill_md_description_fk_grade`
(Round 5 Edit A; unit-tested in `test_count_tokens.py::SkillMdDescriptionFkTests`
and the 3 sibling helper test classes).

Formula: `U1 = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59`.
Word count = maximal runs of `[A-Za-z][A-Za-z'-]*`. Syllable count =
vowel-group heuristic with silent-e adjustment. Sentence count = `[.!?]+`
runs after stripping periods between digits. Grade clamped to `[0.0, 24.0]`.

Determinism: No RNG; no external wordlist; no tokenizer dependency for
the FK path. PyYAML is the only runtime dependency (stdlib-adjacent).
Repeat runs yield byte-identical output.

### U2_first_time_success_rate hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_u2_first_time_success_rate`
(Round 5 Edit B; unit-tested in `test_aggregate_eval.py::HoistU2Tests` — 6 tests
covering default-ninety-percent, all-correct, all-wrong, no-outcomes,
no-should-trigger, and range invariant).

Formula:
```
U2 = sum(correct for o in prompt_outcomes if o.expected == 'trigger')
      / sum(1 for o in prompt_outcomes if o.expected == 'trigger')
     across with-ability rows
```

Deterministic simulator note: single-pass runner means `correct == True`
on a `expected == "trigger"` prompt IS first-time success by construction.
Real-LLM upgrade path: replace the per-prompt `correct` flag with the
first-attempt outcome from an OTel correlation-ID-tracked retry log.

## 9. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-surface
  fields anywhere in this round's deltas.)
* No router model training. (U1 + U2 are MEASUREMENT improvements; no
  online weight learning, no classifier training, no kNN model fit. The
  router_floor_report is re-emitted verbatim from Round 4.)
* No Markdown-to-CLI converter introduced.
* No generic IDE compatibility layer introduced. (Cursor + Claude Code
  mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex is bridge-only
  per spec §11.2 deferred.)

All 4 §11.1 items remain forever-out. Round 5 stays compliant.
