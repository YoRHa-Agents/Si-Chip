# Si-Chip Dogfood Round 8 — Diagnose Notes

`round_id: round_8`
`prior_round_id: round_7`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §6 half-retirement / governance_risk_delta, §8.1 step 3)

This note captures Step 3 (diagnose) per spec §8.1 for Round 8. Numbers are
sourced from `.local/dogfood/2026-04-28/round_8/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_7/metrics_report.yaml`.

## 1. MVP-8 + R4 + D3 + D5 + D2 + D7 cells vs Round 7

| Metric | Round 7 | Round 8 | Delta (R8 − R7) | v1_baseline | Direction |
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
| U3_setup_steps_count | 1 | 1 | 0 | ≤ 2 (master plan target) | flat |
| U4_time_to_first_success | 0.0073 s | 0.0073 s | 0.000 s | ≤ 60 s sanity ceiling | flat |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |
| **V1_permission_scope** | **null** | **0** | **NEW (measurement-fill)** | **no §4.1 threshold; range >= 0** | **populated (PASS)** |
| **V2_credential_surface** | **null** | **0** | **NEW (measurement-fill)** | **no §4.1 threshold; range >= 0; values-never-logged invariant** | **populated (PASS)** |
| **V3_drift_signal** | **null** | **0.0** | **NEW (measurement-fill)** | **no §4.1 threshold; range [0, 1]** | **populated (PASS)** |
| **V4_staleness_days** | **null** | **0** | **NEW (measurement-fill)** | **no §4.1 threshold; range >= 0** | **populated (PASS)** |

All Round 8 plan exit criteria (a1, a2, a3, a4, a5) are met:

* **a1 (V1_permission_scope populated)**: 0 hoisted from
  `governance_scan.scan_permission_scope` via
  `aggregate_eval.hoist_v1_permission_scope` (Round 8 Edit B). Walks the
  skill's Python + shell source (`.agents/skills/si-chip/scripts/*.py` +
  `.agents/skills/si-chip/SKILL.md` metadata) for hardcoded absolute
  write paths via regex pattern-matching:
    - Python: `open(path, 'w'...)`, `Path(path).write_text/write_bytes/mkdir`,
      `os.makedirs/os.mkdir(path)`
    - Shell: `> /abs/path` / `>> /abs/path` redirections
  Allowed prefixes (in-scope, do NOT contribute to V1):
    - `.local/dogfood/` (dogfood evidence root)
    - `.agents/skills/si-chip/` (canonical source tree)
    - `.cursor/skills/si-chip/` (§7.2 mirror)
    - `.claude/skills/si-chip/` (§7.2 mirror)
  Relative paths (not `/...`) treated as in-scope by convention
  (caller-parameterised). Si-Chip scripts route writes through
  caller-provided `--out` arguments; no hardcoded external absolute
  write paths → **V1 = 0 (clean)**.

* **a2 (V2_credential_surface populated)**: 0 hoisted from
  `governance_scan.scan_credential_surface`. Scans every skill artifact
  body for 4 canonical credential patterns:
    - `aws_access_key` (`AKIA[0-9A-Z]{16}`)
    - `generic_high_entropy_40` (`[A-F0-9]{40}\b` — SHA-1-like hex)
    - `pem_private_key` (`-----BEGIN [A-Z ]*PRIVATE KEY-----`)
    - `credential_assignment` (`(api[_-]?key|token|password|secret|bearer)\s*[:=]\s*"..."{8+}`)

  **CRITICAL**: the scanner NEVER logs the matched value verbatim — only
  the pattern name + file path + per-file count. Unit-test verified in
  `tools/test_governance_scan.py::test_must_not_log_secret_value`, which
  writes a known AWS-key fixture, runs the scanner, captures log output,
  and asserts the scanner logs `"aws_access_key"` + `"1 time"` but NOT
  the actual key body (nor even a 10-char prefix of it).

  Si-Chip artifacts contain no credential bodies → **V2 = 0 (clean)**.

* **a3 (V3_drift_signal populated)**: 0.0 hoisted from
  `governance_scan.scan_drift_signal`. Computes SHA-256 byte-equality
  ratio across the 3 SKILL.md mirrors:
    - `.agents/skills/si-chip/SKILL.md` (canonical; md5 `53184fa...`)
    - `.cursor/skills/si-chip/SKILL.md`
    - `.claude/skills/si-chip/SKILL.md`
  Total unordered pairs = C(3, 2) = 3. Equal pairs = 3 (all three
  byte-equal post-0.1.7 sync). drift_zero_ratio = 3/3 = 1.0. V3 =
  1.0 - 1.0 = **0.0 (clean; matches ALL_TREES_DRIFT_ZERO verdict)**.

* **a4 (V4_staleness_days populated)**: 0 hoisted from
  `governance_scan.scan_staleness_days`. Parses
  `basic_ability_profile.lifecycle.last_reviewed_at` from the Round 8
  profile = `2026-04-28`. Today (master plan shared date) = `2026-04-28`.
  `(2026-04-28 - 2026-04-28).days = 0` → **V4 = 0 (same-day review)**.

* **a5 (tools/governance_scan.py has ≥ 15 unit tests)**: 35 tests in
  `tools/test_governance_scan.py` cover:
    - ScanPermissionScopeTests (7): empty input → 0, real si-chip tree →
      0, positive-count fixture with `/etc/` write, missing-path raises,
      in-scope `.local/dogfood/` write not counted, relative path
      in-scope, mirror target (`/.cursor/skills/si-chip/`) in-scope.
    - ScanCredentialSurfaceTests (8): empty input → 0, real si-chip tree
      → 0, positive-count AWS key, positive-count PEM, positive-count
      assignment, **MUST-NOT-log-secret-value CRITICAL test**,
      missing-path raises, extra_artifacts deduped.
    - ScanDriftSignalTests (7): 2 identical mirrors → 0, 3 identical →
      0, one divergent → 2/3, real si-chip mirrors → 0, <2 mirrors
      raises, missing mirror raises, range invariant.
    - ScanStalenessDaysTests (7): same-day → 0, 30-day → 30, missing
      file raises, malformed YAML raises, missing last_reviewed_at
      raises, bad ISO date raises, future date raises.
    - BuildGovernanceReportTests (2): real si-chip all-zero + provenance
      keys, CLI JSON round-trip.
    - ComputeGovernanceRiskDeltaTests (4): all-zero → 0, V1=1 → -0.25,
      worst-case clamped to -1.0, v4_staleness_cap validation.

  Plus aggregate_eval.py extended with 18 new tests (HoistV1Tests ×5,
  HoistV2Tests ×4, HoistV3Tests ×4, HoistV4Tests ×4,
  BuildReportV1V4Integration ×4 including test_round_8_keeps_28_key_invariant
  and test_governance_risk_delta_derived_live_not_hardcoded). Total test
  count growth Round 7 (164) → Round 8 (217 + carried).

* **a5 extra: governance_risk_delta audit-gap closure**: The
  `half_retire_decision.yaml` `value_vector.governance_risk_delta` field
  is now DERIVED LIVE via `governance_scan.compute_governance_risk_delta(
  V1=0, V2=0, V3=0.0, V4=0)` rather than the hard-coded `0.0` literal
  Rounds 1-7 used. Formula:

  ```
  risk_with = min(V1, 1)*0.25 + min(V2, 1)*0.25 + V3*0.25
            + min(V4/30, 1)*0.25
           = 0.0 + 0.0 + 0.0 + 0.0 = 0.0
  risk_without = 0.0  # no-ability baseline has no filesystem/credential/mirror interaction
  governance_risk_delta = risk_without - risk_with = 0.0 - 0.0 = 0.0
  ```

  Numerically the axis still reads 0.0 (clean Si-Chip baseline), BUT it
  now traces to a computable function. Any future V1/V2/V3/V4 regression
  will move the axis negative automatically (e.g. V1 rising to 1 moves
  the axis to -0.25; V1 + V2 rising to 1 each moves it to -0.50 which
  approaches the `disable_auto_trigger` trigger threshold).

## 2. v1_baseline hard-threshold check (Round 8)

| Threshold (v1_baseline) | Round 8 value | Pass? |
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
| iteration_delta (any axis) ≥ +0.05 | governance_risk measurement-fill axis bonus | yes (per master plan acceptance criterion #7 alternative) |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 metric PASSES in
Round 8.** D7 governance_risk dimension reaches **4/4 measured** sub-metric
coverage at v1_baseline (was 0/4 at Round 7 — V1/V2/V3/V4 all newly
populated). **D7 is now COMPLETE — all 4 sub-metrics have deterministic
static derivations with NO by-design-null cells.** V1/V2/V3/V4 also pass
range-sanity gates. No new sub-metrics become null; spec §3.2 frozen key
contract still holds.

## 3. Monotonicity check vs Round 7 (spec §8.3)

| Metric | Round 7 | Round 8 | pct_change | direction | pass? |
|---|---|---|---|---|---|
| T1_pass_rate | 0.85 | 0.85 | 0.00% | flat | yes |
| T2_pass_k | 0.5478 | 0.5478 | 0.00% | flat | yes |
| T3_baseline_delta | 0.35 | 0.35 | 0.00% | flat | yes |
| C1_metadata_tokens | 82 | 82 | 0.00% | flat | yes |
| C2_body_tokens | 2020 | 2020 | 0.00% | flat | yes |
| C4_per_invocation_footprint | 3602 | 3602 | 0.00% | flat | yes |
| C5_context_rot_risk | 0.2601 | 0.2601 | 0.00% | flat | yes |
| C6_scope_overlap_score | 0.0435 | 0.0435 | 0.00% | flat | yes |
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
| V1_permission_scope | null | 0 | newly applicable | flat (new) | yes |
| V2_credential_surface | null | 0 | newly applicable | flat (new) | yes |
| V3_drift_signal | null | 0.0 | newly applicable | flat (new) | yes |
| V4_staleness_days | null | 0 | newly applicable | flat (new) | yes |

**T1_pass_rate MUST NOT regress** (spec §8.3 hard rule); Round 8 holds at 0.85,
exactly equal to Round 7 — PASS. No metric regressed by more than 1%; no
release-attribution exceptions need to be invoked this round. Newly-populated
V1-V4 are flagged as "NEWLY APPLICABLE — was null at Round 7; not a
regression" per the iteration_delta_report monotonicity_check.

## 4. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05" at
v1_baseline. Round 8 axis movements (round_8 − round_7):

* task_quality: 0 (flat)
* context_economy: 0 (flat; D2 already at full coverage from Round 7)
* latency_path: 0 (flat; L1/L2/L3/L4 unchanged; D3 stays at 4/7)
* generalizability: 0 (flat; G1 still null — Round 10 work)
* usage_cost: 0 (flat; D5 fully complete from Round 6)
* routing_cost: 0 (flat; R8 still null — Round 9 work)
* **governance_risk: +0.05 measurement-fill axis bonus** (V1 + V2 + V3 + V4
  newly populated; D7 coverage 0/4 measured → 4/4 measured = full D7
  measurement-attempt completion; NO by-design-null cells). This is the
  "measurement-fill flavour bonus" branch of master plan acceptance
  criterion #7: "iteration_delta_report.yaml governance_risk axis can
  now be positive_axis: true with delta >= 0.0 (still neutral; not a
  regression)". Round 8 satisfies the measurement-fill alternative:
  4/4 populated AND delta >= 0 (=0.0 numerically) AND derivation now
  live (not hard-coded).

Per master plan acceptance criterion #7, Round 8 satisfies this with the
measurement-fill-flavour bonus on governance_risk. This is the single axis
improvement satisfying the §4.1 v1_baseline iteration_delta clause.

## 5. Top-2 BLOCKERS to v2_tightened promotion (carried forward to Round 9+)

1. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Rounds 1/2/3/4/5/6/7; cases unchanged this round. Carried forward
   to Round 12 v2_tightened readiness check.

2. **R8_description_competition_index still null** — D6 routing_cost is
   at 7/8 after Round 8 (R1, R2 permanently null; R8 Round 9 target).
   Round 9 master plan widens this into a formal across-matrix index
   (distinct from Round 7's C6 conservative-max) AND introduces the
   16-cell intermediate router-test profile.

**REMOVED FROM BLOCKER LIST (closed this round)**:
- ~~V1-V4 governance_risk sub-metrics still null~~ — ALL 4 populated this
  round (V1=0, V2=0, V3=0.0, V4=0). D7 is the THIRD R6-dimension to
  reach full coverage (after D5 in Round 6 and D2 in Round 7).
- ~~half_retire_decision.yaml governance_risk_delta hard-coded 0.0~~ —
  Now DERIVED LIVE from V1-V4 via
  `governance_scan.compute_governance_risk_delta`. The audit-gap flagged
  in Round 7 diagnose notes is CLOSED.

## 6. Round 9 hint (per master plan)

Round 9 fills R8_description_competition_index (D6 routing_cost final) and
widens the router-test matrix from 8-cell MVP to 16-cell intermediate. The
diagnose findings here flag:

* **R8 derivation strategy**: R8 = TF-IDF cosine or token-Jaccard across
  the FULL neighbor skill matrix. Distinct from Round 7's C6 conservative-
  max (which picked the single highest-overlap neighbor). R8 measures the
  §3 description-competition surface area that the router has to
  discriminate on.

* **Intermediate profile strategy**: 16 cells = 2 model × 2 thinking_depth
  × 4 scenario (OR 3 × 2 × 2). ADDITIVE only — mvp:8 and full:96 stay
  frozen. Template $schema_version bumps 0.1.0 → 0.1.1; spec_validator
  must accept both schemas.

* **Router-test widening is §5.1 allowed**: "metadata retrieval /
  heuristic kNN baseline" surface expansion is explicitly permitted
  under the Router Paradigm. Router model training (§5.2 forbidden)
  remains out of scope.

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L3 task spec:
* SKILL.md frontmatter `version: 0.1.6` → `version: 0.1.7` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.6` → `v0.1.7`. No other install.sh edits this round.
* `docs/_install_body.md` version references `v0.1.6` → `v0.1.7`
  (English + Chinese rows).
* `docs/skills/si-chip-0.1.7.tar.gz` deterministic tarball generated
  (mirroring v0.1.6 tarball structure).
* Mirror drift = 0 verified across 3 trees (AND verified by new
  governance_scan.scan_drift_signal → V3 = 0.0).

## 8. V1-V4 hoist methods (transparency)

### V1_permission_scope hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_v1_permission_scope`
(Round 8 Edit B; unit-tested in `test_aggregate_eval.py::HoistV1Tests` —
5 tests covering happy paths + degenerate paths). Inner helper:
`tools/governance_scan.py::scan_permission_scope` (Round 8 Edit A;
unit-tested in `test_governance_scan.py::ScanPermissionScopeTests` —
7 tests including the REAL si-chip tree smoke).

Formula: count of distinct absolute write-paths outside the allowed
prefix set. Allowed prefixes: `.local/dogfood/`, `.agents/skills/si-chip/`,
`.cursor/skills/si-chip/`, `.claude/skills/si-chip/`. Relative paths +
`/tmp/` paths are treated as in-scope.

Determinism: regex match; no RNG. Output byte-identical on rebuild.

### V2_credential_surface hoist
Code path:
`aggregate_eval.py::hoist_v2_credential_surface` (Round 8 Edit B; unit-
tested in `HoistV2Tests` — 4 tests). Inner helper:
`governance_scan.py::scan_credential_surface` (Round 8 Edit A; unit-tested
in `ScanCredentialSurfaceTests` — 8 tests including the CRITICAL
`test_must_not_log_secret_value`).

Formula: count of pattern matches across 4 canonical patterns. Scanner
logs pattern name + file path + per-file count BUT NEVER the matched
value verbatim.

Determinism: regex match; no RNG.

### V3_drift_signal hoist
Code path:
`aggregate_eval.py::hoist_v3_drift_signal` (Round 8 Edit B; unit-tested in
`HoistV3Tests` — 4 tests). Inner helper:
`governance_scan.py::scan_drift_signal` (Round 8 Edit A; unit-tested in
`ScanDriftSignalTests` — 7 tests including the REAL si-chip mirrors
smoke).

Formula: `1.0 - (byte_equal_pairs / total_pairs)` across the N mirrors.
For N=3 there are C(3, 2) = 3 unordered pairs. All 3 byte-equal →
drift_zero_ratio = 1.0 → V3 = 0.0.

Determinism: SHA-256 hash; no RNG.

### V4_staleness_days hoist
Code path:
`aggregate_eval.py::hoist_v4_staleness_days` (Round 8 Edit B; unit-tested
in `HoistV4Tests` — 4 tests). Inner helper:
`governance_scan.py::scan_staleness_days` (Round 8 Edit A; unit-tested in
`ScanStalenessDaysTests` — 7 tests including same-day, positive-days,
malformed-YAML, missing-field, future-date, and bad-ISO-date cases).

Formula: `(today - basic_ability_profile.lifecycle.last_reviewed_at).days`.
Guards: malformed YAML → ValueError; missing last_reviewed_at → ValueError;
future-dated last_reviewed_at → ValueError (workflow bug); same-day
review → 0; non-negative otherwise.

Determinism: date arithmetic; no RNG.

## 9. governance_risk_delta live-derivation trace (audit-gap closure)

Rounds 1-7 hard-coded `value_vector.governance_risk_delta = 0.0` in
`half_retire_decision.yaml` because no D7 sub-metric was measured. The
comment typically read something like "# No risk regression introduced;
D7 — unchanged from Round 6" — i.e. stipulated, not computed.

Round 8 closes this audit gap. The
`half_retire_decision.yaml#value_vector.governance_risk_delta` is now:

```yaml
  governance_risk_delta: 0.0    # NEW IN ROUND 8: DERIVED LIVE via governance_scan.compute_governance_risk_delta(V1=0, V2=0, V3=0.0, V4=0). Formula: risk_with = min(V1,1)*0.25 + min(V2,1)*0.25 + V3*0.25 + min(V4/30,1)*0.25 = 0.0; risk_without = 0.0 (no-ability baseline has no filesystem/credential/mirror interaction); governance_risk_delta = risk_without - risk_with = 0.0.
```

The full derivation trace lives in
`half_retire_decision.yaml#governance_risk_delta_derivation`:

```yaml
  inputs: {V1: 0, V2: 0, V3: 0.0, V4: 0}
  computation:
    v1_term: 0.0    # min(V1, 1) * 0.25 = min(0, 1) * 0.25 = 0.0
    v2_term: 0.0    # min(V2, 1) * 0.25 = min(0, 1) * 0.25 = 0.0
    v3_term: 0.0    # V3 * 0.25 = 0.0 * 0.25 = 0.0
    v4_term: 0.0    # min(V4 / 30, 1) * 0.25 = min(0 / 30, 1) * 0.25 = 0.0
    risk_with: 0.0
    risk_without: 0.0
    governance_risk_delta: 0.0
```

Going forward, any V1/V2/V3/V4 regression propagates automatically. Per
spec §6.2, `disable_auto_trigger` fires when governance_risk_delta is
"materially negative" — the V1-V4 weighting (0.25 each) means two
rising sub-metrics drop the axis to -0.50 which approaches that
threshold.

## 10. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-surface
  fields anywhere in this round's deltas.)
* No router model training. (V1-V4 are STATIC scans of source / artifacts /
  mirrors / profile YAML; no online weight learning, no classifier
  training, no kNN model fit. The router_floor_report is re-emitted
  verbatim from Round 7.)
* No Markdown-to-CLI converter introduced. (The governance_scan helpers
  MEASURE static skill structure but do not convert markdown to a CLI.)
* No generic IDE compatibility layer introduced. (Cursor + Claude Code
  mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex is bridge-only
  per spec §11.2 deferred.)

All 4 §11.1 items remain forever-out. Round 8 stays compliant.
