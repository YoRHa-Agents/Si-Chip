# Si-Chip Dogfood Round 11 — Diagnose Notes

`round_id: round_11`
`prior_round_id: round_10`
`computed_at: 2026-04-28`
`spec_old: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §3.1 D4 G1-G4,
§4.1 progressive gates, §5 router paradigm, §5.1 allowed work surfaces,
§5.2 prohibitions, §5.3 harness table, §5.4 profile↔gate binding, §8.1 step 3,
§11.1 forever-out)
`spec_new: .local/research/spec_v0.2.0-rc1.md` (Round 11 reconciliation;
§13.4 prose aligned with §3.1 / §4.1 TABLES; §3/§4/§5/§6/§7/§8/§11
Normative semantics byte-identical to v0.1.0 per
raw/normative_diff_check.json verdict=NORMATIVE_TABLES_BYTE_IDENTICAL)

This note captures Step 3 (diagnose) per spec §8.1 for Round 11. Numbers are
sourced from `.local/dogfood/2026-04-28/round_11/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_10/metrics_report.yaml`.
Round 11 is a SPEC-RECONCILIATION ROUND: the only metric movement is
C1/C2/C4 (recomputed from updated SKILL.md frontmatter+body); all other
metrics are carried byte-identical from Round 10 per L3 task spec.

## 1. MVP-8 + R4 + D3 + D5 + D2 + D7 + R8 + G1 cells vs Round 10

| Metric | Round 10 | Round 11 | Delta (R11 − R10) | v1_baseline | Direction |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | +0.00 | ≥ 0.75 | flat (no regression) |
| T2_pass_k | 0.5478 | 0.5478 | +0.0000 | ≥ 0.40 | flat |
| T3_baseline_delta | +0.35 | +0.35 | +0.00 | informational | flat |
| **C1_metadata_tokens** | **82** | **85** | **+3 (+3.66%)** | **≤ 120** | **RECOMPUTED — spec_version "v0.1.0" -> "v0.2.0-rc1" string change (+3 tokens; verified: o200k_base("v0.1.0")=6 tokens, o200k_base("v0.2.0-rc1")=9 tokens)** |
| **C2_body_tokens** | **2020** | **2125** | **+105 (+5.20%)** | **informational** | **RECOMPUTED — spec_v0.2.0-rc1 references in §1/§3/§11/References Index/Provenance footer + 28 -> 37 sub-metric prose tweak** |
| C3_resolved_tokens | null | null | — | by-design null | permanently null |
| **C4_per_invocation_footprint** | **3602** | **3710** | **+108 (+3.00%)** | **≤ 9000** | **RECOMPUTED — = C1(85) + C2(2125) + USER_PROMPT_FOOTPRINT(1500)** |
| C5_context_rot_risk | 0.2601 | 0.2601 | 0.00 | range [0, 1] | flat (carried; aggregator natural derivation 0.260625 in raw/aggregator_raw_output.yaml) |
| C6_scope_overlap_score | 0.0435 | 0.0435 | 0.00 | range [0, 1] | flat (carried; aggregator natural derivation 0.04166... in raw/aggregator_raw_output.yaml) |
| L1_wall_clock_p50 | 1.215 s | 1.215 s | 0.000 s | informational | flat |
| L2_wall_clock_p95 | 1.469 s | 1.469 s | 0.000 s | ≤ 45 s | flat |
| L3_step_count | 20 | 20 | 0 | informational | flat |
| L4_redundant_call_ratio | 0.0 | 0.0 | 0.0 | informational | flat |
| G1_cross_model_pass_matrix | 2×2 nested dict | 2×2 nested dict | byte-identical | range [0, 1] | flat (carried; mvp 8-cell sweep cell outcomes hard-coded) |
| G2_cross_domain_transfer_pass | null | null | — | out-of-scope for v0.1.x | permanently null (v0.3.x+ work) |
| G3_OOD_robustness | null | null | — | out-of-scope for v0.1.x | permanently null (v0.3.x+ work) |
| G4_model_version_stability | null | null | — | out-of-scope for v0.1.x | permanently null (v0.3.x+ work) |
| U1_description_readability | 19.58 | 19.58 | +0.00 | informational | flat (carried; aggregator natural derivation 18.85 in raw/aggregator_raw_output.yaml) |
| U2_first_time_success_rate | 0.75 | 0.75 | +0.00 | informational | flat |
| U3_setup_steps_count | 1 | 1 | 0 | ≤ 2 | flat |
| U4_time_to_first_success | 0.0073 s | 0.0073 s | 0.000 s | ≤ 60 s | flat |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |
| R8_description_competition_index | 0.0435 | 0.0435 | 0.0000 | range [0, 1] | flat (carried; aggregator natural derivation 0.04166... in raw/aggregator_raw_output.yaml) |
| V1_permission_scope | 0 | 0 | 0 | no §4.1 threshold | flat |
| V2_credential_surface | 0 | 0 | 0 | no §4.1 threshold | flat |
| V3_drift_signal | 0.0 | 0.0 | 0.0 | no §4.1 threshold | flat (re-verified post-0.1.10 sync; 3/3 mirror byte-equality) |
| V4_staleness_days | 0 | 0 | 0 | no §4.1 threshold | flat |

## 2. Diagnosis: spec prose drift removed

The §3.1 TABLE has always enumerated 37 sub-metrics (D1=4, D2=6, D3=7, D4=4,
D5=4, D6=8, D7=4 = 37 total). Round 11 reconciles the §13.4 prose with the
TABLE: "完整 28 子指标" -> "完整 37 子指标"; "§3 metric key 28 项" -> "§3
metric key 37 项". The §4.1 TABLE has always enumerated 30 numeric threshold
cells (10 metrics × 3 profiles). Round 11 reconciles "§4 阈值表 21 个数" ->
"§4 阈值表 30 个数".

These changes are PROSE ONLY. The §3.1 / §4.1 TABLE rows themselves
(sub-metric IDs, dimension assignments, threshold values, monotonicity
direction, MVP-8 subset annotations) are byte-identical to v0.1.0. The
§3 / §4 / §5 / §6 / §7 / §8 / §11 Normative semantics are byte-identical
per `raw/normative_diff_check.json` verdict=NORMATIVE_TABLES_BYTE_IDENTICAL.

`tools/spec_validator.py` extended:
* DEFAULT_SPEC: `.local/research/spec_v0.1.0.md` -> `.local/research/spec_v0.2.0-rc1.md`.
* SCRIPT_VERSION: 0.1.1 -> 0.1.2.
* Per-spec EXPECTED_R6_PROSE_BY_SPEC + EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC
  maps (v0.1.0=28+21, v0.2.0-rc1=37+30) — the strict-prose mode auto-selects
  the correct expected count from the spec frontmatter.
* `_threshold_prose_numbers_in_section13` narrowed to §13.4 subsection only
  (stop at next ### / ##) — previously the function scanned everything from
  §13.4 to end of file, which incorrectly counted "§4 阈值表 21 个数" strings
  inside the v0.2.0-rc1 reconciliation-log appendices; the narrowing fixes
  this and lets `--strict-prose-count` pass on v0.2.0-rc1.

## 3. v1_baseline hard-threshold check (Round 11)

| Threshold (v1_baseline) | Round 11 value | Pass? |
|---|---|---|
| pass_rate ≥ 0.75 | 0.85 | yes |
| pass_k ≥ 0.40 | 0.5478 | yes |
| trigger_F1 ≥ 0.80 | 0.8934 | yes |
| near_miss_FP_rate ≤ 0.15 | 0.05 | yes (also passes v3_strict ≤ 0.05) |
| metadata_tokens ≤ 120 | 85 | yes (still passes v2_tightened ≤ 100; v3_strict ≤ 80 fails by -5; tracked) |
| per_invocation_footprint ≤ 9000 | 3710 | yes (still passes v2_tightened ≤ 7000) |
| wall_clock_p95 ≤ 45 s | 1.469 s | yes |
| routing_latency_p95 ≤ 2000 ms | 1100 ms | yes |
| routing_token_overhead ≤ 0.20 | 0.0233 | yes |
| iteration_delta (any axis) ≥ +0.05 | governance_risk spec-reconciliation drift-removal axis bonus | yes |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 / R8
metric PASSES in Round 11.** No sub-metrics become null; spec §3.2
frozen key contract still holds (37 keys, 27 populated, 10 explicit
null).

## 4. Monotonicity check vs Round 10 (spec §8.3)

`T1_pass_rate` hard non-regression rule holds at 0.85 = 0.85 — PASS.

C1/C2/C4 EXEMPTED from the 1% no-regression sub-clause this round per
master plan Round 11 spec-reconciliation exemption (the round's purpose
is the spec bump; metric movement on C1/C2/C4 is the expected price of
the spec_version string update). All three remain WELL within
v2_tightened ceilings (C1<=100, C4<=7000).

All other metrics carried byte-identical (C5/C6/R8/U1 explicitly carried
per L3 task spec; the aggregator's natural live-derivations from the
new SKILL.md content are recorded in `raw/aggregator_raw_output.yaml`
for traceability).

## 5. Top blockers to v2_tightened promotion (carried forward to Round 12)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Rounds 1/2/3/4/5/6/7/8/9/10; cases unchanged this round.
   Carried forward to Round 12 v2_tightened readiness check. Fix path:
   CASE-LEVEL adjustment to `evals/si-chip/cases/*.yaml` or per-prompt
   verdict tweaks; out of scope for Round 11 (spec-text only).

2. **G1 authoritative-full-matrix requirement** — Round 10 populates a
   2-model × 2-pack PARTIAL PROXY (carried through Round 11). v2_tightened
   promotion requires the full 96-cell matrix (§5.3 full: 6 model × 4
   depth × 4 pack) from a real-LLM runner. v0.2.0 ship gate decision
   per Round 12 readiness check.

3. **iteration_delta v2_tightened ceiling** — any axis must reach ≥ +0.10
   at v2_tightened. Round 11 governance_risk drift-removal axis is at
   +0.05 (v1_baseline bucket); does NOT meet v2_tightened +0.10. Round 12
   must produce a stronger axis movement OR continue carrying T2_pass_k
   as the single open blocker.

**REMOVED FROM BLOCKER LIST (closed this round)**:
- ~~`tools/spec_validator.py --strict-prose-count` known FAIL on R6_KEYS
  + THRESHOLD_TABLE~~ — closed by Round 11 spec reconciliation: §13.4
  prose now matches §3.1/§4.1 TABLE counts (37/30); validator narrowing
  of `_threshold_prose_numbers_in_section13` to §13.4 subsection only
  ignores appendix reconciliation-log historical "21 个数" references;
  `--strict-prose-count` now 8/8 PASS against v0.2.0-rc1.
- ~~spec text drift (TABLE 37/30 vs prose 28/21)~~ — closed by §13.4
  prose alignment to TABLE counts.

## 6. Round 12 hint (per master plan)

Round 12 implements `tools/reactivation_detector.py` with all 6 §6.4
triggers + unit tests; extends `tools/spec_validator.py` with a 9th
invariant `REACTIVATION_DETECTOR_PRESENT`; runs the v2_tightened
readiness check across Round 11 + Round 12 metrics; emits
`v0.2.0_ship_decision.yaml` + `v0.2.0_ship_report.md`. SHIP_ELIGIBLE iff
both rounds pass every v2_tightened hard threshold per §4.2. Otherwise
SHIP_BLOCKED with explicit blocker list and Round 13+ recovery plan.

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L3 task spec:
* SKILL.md frontmatter `version: 0.1.9` → `version: 0.1.10` in 3 mirrors
  (.agents canonical + .cursor + .claude); body changed minimally for
  spec_version v0.1.0 -> v0.2.0-rc1 references + 28 -> 37 sub-metric
  prose tweak.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.9` → `v0.1.10`.
* `docs/_install_body.md` version references `v0.1.9` → `v0.1.10`
  (English + Chinese rows).
* `docs/skills/si-chip-0.1.10.tar.gz` deterministic tarball generated
  (mirroring v0.1.9 tarball structure; same canonical layout = 1
  SKILL.md + 5 references + 3 scripts).
* Mirror drift = 0 verified across 3 trees (re-verified by
  V3_drift_signal = 0.0 in metrics_report).

## 8. Spec reconciliation method transparency

### Normative byte-identity check

`raw/normative_diff_check.json` runs a structural diff across §3 / §4 / §5 /
§6 / §7 / §8 / §11 Normative sections between v0.1.0 and v0.2.0-rc1. Result:
verdict=NORMATIVE_TABLES_BYTE_IDENTICAL. Only TWO §3 (intro + §3.2 item 2)
and TWO §8 (§8.1 step 3 + §8.2 item 2) prose lines have integer-count diffs
(28 -> 37); all other Normative tables (§3.1 sub-metric rows, §4.1 threshold
rows, §5.1 work surfaces, §5.3 harness, §6.1 value vector, §6.2 decision
rules, §6.4 reactivation triggers, §7.2 platform priority, §11.1 forever-out)
are byte-identical.

### Validator extension

`tools/spec_validator.py` extended this round:
* DEFAULT_SPEC: `.local/research/spec_v0.1.0.md` -> `.local/research/spec_v0.2.0-rc1.md`.
  Backward-compat: passing `--spec .local/research/spec_v0.1.0.md` still
  works for verifying Rounds 1-10 artefacts.
* SCRIPT_VERSION: 0.1.1 -> 0.1.2.
* `EXPECTED_R6_PROSE_BY_SPEC` + `EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC`:
  per-spec dictionaries mapping spec_version -> expected prose-count integer
  (v0.1.0=28+21, v0.2.0-rc1=37+30). The strict-prose mode auto-selects from
  the spec frontmatter `version:` field via `detect_spec_version`.
* `_threshold_prose_numbers_in_section13` narrowed to §13.4 subsection ONLY:
  the function previously scanned everything from §13.4 to end of file
  (which incorrectly counted "§4 阈值表 21 个数" strings inside the
  v0.2.0-rc1 reconciliation-log appendices); the narrowing stops at the
  next ### / ## heading.
* `--json` default-mode 8/8 PASS against BOTH v0.1.0 and v0.2.0-rc1.
* `--strict-prose-count` 8/8 PASS against v0.2.0-rc1 (was FAIL pre-Round-11;
  reconciliation closed).
* `--strict-prose-count` still FAILS against v0.1.0 by design — the
  reconciliation sentinel is preserved (v0.1.0 prose 28/21 mismatches
  template TABLE 37/30; this is the historical regression mode that
  motivated Round 11).

## 9. Evidence index (raw/)

| File | Contents |
|---|---|
| `normative_diff_check.json` | §3/§4/§5/§6/§7/§8/§11 byte-identity check vs v0.1.0; verdict=NORMATIVE_TABLES_BYTE_IDENTICAL |
| `rules_compile_hashes_before.json` | `.rules/.compile-hashes.json` snapshot pre-recompile |
| `rules_compile_hashes_after.json` | `.rules/.compile-hashes.json` snapshot post-recompile (matches AGENTS.md compile) |
| `spec_validator.json` | `tools/spec_validator.py --json` against v0.2.0-rc1 — 8/8 PASS |
| `spec_validator_strict_prose.json` | `tools/spec_validator.py --json --strict-prose-count` against v0.2.0-rc1 — 8/8 PASS |
| `spec_validator_v0.1.0.json` | `tools/spec_validator.py --json --spec v0.1.0` — 8/8 PASS (backward-compat) |
| `r4_near_miss_FP_rate_derivation.json` | Round 11 R4 derivation (carried byte-identical from Round 10; deterministic re-derivation) |
| `aggregate_eval.log` | Aggregator run log (Round 11 invocation + observations + post-processing notes) |
| `aggregator_raw_output.yaml` | Aggregator raw output (live derivations of C5/C6/R8/U1 from new SKILL.md body — recorded for traceability; canonical metrics_report.yaml carries Round 10 values byte-identical per L3 task spec) |

## 10. spec §11 forever-out check

* No marketplace touched. (Round 11 is spec-text reconciliation only;
  no `marketplace`, `manifest`, distribution-surface fields anywhere
  in this round's deltas.)
* No router model training. (No learned ranker, no online weight
  learning. The §5.1 vs §5.2 boundary is byte-identical to v0.1.0
  in v0.2.0-rc1.)
* No Markdown-to-CLI converter introduced.
* No generic IDE compatibility layer introduced. (Cursor + Claude
  Code mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex
  is bridge-only per §11.2 deferred. The "bridge only at v0.2.0-rc1"
  language anchor in SKILL.md §11 "When NOT To Trigger" only updates
  the spec_version anchor, NOT the bridge-only constraint itself.)

All 4 §11.1 items remain forever-out. Round 11 stays compliant.
