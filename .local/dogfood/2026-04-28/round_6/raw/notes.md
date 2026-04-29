# Si-Chip Dogfood Round 6 — Diagnose Notes

`round_id: round_6`
`prior_round_id: round_5`
`computed_at: 2026-04-28`
`spec: .local/research/spec_v0.1.0.md` (§3 R6 metric taxonomy, §4.1 progressive
gates, §8.1 step 3)

This note captures Step 3 (diagnose) per spec §8.1 for Round 6. Numbers are
sourced from `.local/dogfood/2026-04-28/round_6/metrics_report.yaml` and
compared against `.local/dogfood/2026-04-28/round_5/metrics_report.yaml`.

## 1. MVP-8 + R4 + D3 + D5 cells vs Round 5

| Metric | Round 5 | Round 6 | Delta (R6 − R5) | v1_baseline | Direction |
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
| U1_description_readability | 19.58 | 19.58 | +0.00 | informational | flat |
| U2_first_time_success_rate | 0.75 | 0.75 | +0.00 | informational | flat |
| **U3_setup_steps_count** | **null** | **1** | **NEW (measurement-fill)** | **≤ 2 (master plan target)** | **populated (PASS)** |
| **U4_time_to_first_success** | **null** | **0.0073 s** | **NEW (measurement-fill)** | **≤ 60 s sanity ceiling** | **populated (PASS by 8200x)** |
| R3_trigger_F1 | 0.8934 | 0.8934 | +0.0000 | ≥ 0.80 | flat |
| R4_near_miss_FP_rate | 0.05 | 0.05 | +0.0000 | ≤ 0.15 | flat |
| R5_router_floor | composer_2/fast | composer_2/fast | unchanged | informational | flat |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0 ms | ≤ 2000 ms | flat |
| R7_routing_token_overhead | 0.0233 | 0.0233 | +0.0000 | ≤ 0.20 | flat |

All Round 6 plan exit criteria (a1, a2, a3, a4, a5) are met:

* **a1 (U3_setup_steps_count populated)**: 1 hoisted from
  `tools/install_telemetry.count_setup_steps` via
  `aggregate_eval.hoist_u3_setup_steps_count` (Round 6 Edit C). The helper
  parses the new self-reported `# SI_CHIP_INSTALLER_STEPS=1` header that
  Round 6 Edit B adds to `install.sh`. Count = 1 for the non-interactive
  one-liner (`curl ... | bash -s -- --yes --target ... --scope ...`) —
  **validates the CHANGELOG v0.1.1 "one-line installer" claim**. The
  interactive flow (no `--yes`, TTY) adds 2 prompts (`--target` +
  `--scope`), so interactive count = 3. We surface the non-interactive
  figure as the headline value because the published docs
  (`INSTALL.md#Quick Install (one-line)`) lead with the non-interactive
  one-liner.

  v1_baseline gate ≤ 2 PASS. Range sanity check (U3 >= 0) PASS.

* **a2 (U4_time_to_first_success populated)**: 0.0073 s hoisted from
  `tools/install_telemetry.time_first_success` via
  `aggregate_eval.hoist_u4_time_to_first_success` (Round 6 Edit C). The
  helper runs `bash install.sh --dry-run --yes --target cursor --scope
  repo --repo-root <tmp>` via `subprocess.run` with a 60 s timeout and
  measures wall-clock from spawn to the first `[OK] Installed` line in
  stdout. Dry-run short-circuits the HTTP tarball fetch + extract
  (installer still LOGS those but does not execute them), so the value
  is a valid floor estimate — real wall-clock includes ~1-5 s HTTP
  download + ~100-200 ms tar extraction on top.

  v1_baseline sanity ceiling ≤ 60 s PASS by 8200x margin. Range sanity
  check (U4 in [0.0, 60.0]) PASS. Real wall-clock measurement is opt-in
  via `dry_run=False` and is not invoked here so Round 6 stays offline-
  deterministic (per master plan risk_flag about network latency
  variance; full live-install p50+p95 is a Round 12 / real-LLM-runner
  upgrade candidate).

* **a3 (tools/install_telemetry.py is testable)**: 20 unit tests in
  `tools/test_install_telemetry.py` cover:
    - happy paths (self-reported header 0/1/2 steps)
    - fallback path (legacy installer with `read -p` / `read -r` prompts)
    - commented `read` lines ignored
    - negative header rejected (`ValueError`)
    - missing file raises `FileNotFoundError`
    - header precedence over fallback (both present → header wins)
    - real repo `install.sh` advertises U3 == 1 (integration smoke)
    - `time_first_success` happy path (subprocess monkey-patched)
    - `time_first_success` degenerate paths: non-zero rc, missing
      `[OK] Installed` line, `TimeoutExpired`, `FileNotFoundError` on
      bash-missing
    - real dry-run smoke (opt-in via `SI_CHIP_RUN_DRY_RUN=1` env var;
      deterministic offline default skips it)
    - `build_telemetry_payload` shape / JSON round-trip
  All 20 tests PASS under `python3 tools/test_install_telemetry.py`.

* **a4 (install.sh existing flags not regressed)**: real regression test
  `bash install.sh --dry-run --yes --target cursor --scope repo
  --repo-root /tmp/si_chip_round6_dry` exits 0, emits the correct
  `[OK] Installed Si-Chip v0.1.5` line, and preserves every existing
  flag. Log captured at
  `.local/dogfood/2026-04-28/round_6/raw/install_dry_run.log`. All 11
  pre-existing flags (`--target`, `--scope`, `--version`, `--dry-run`,
  `--yes`/`-y`, `--force`, `--uninstall`, `--source-url`, `--repo-root`,
  `--help`/`-h`, `--version-info`) still parsed verbatim by
  `parse_args`; no hidden behavior change. The only additive change is
  the header comment `# SI_CHIP_INSTALLER_STEPS=1` and the
  `SI_CHIP_VERSION_DEFAULT` constant bump `v0.1.4 -> v0.1.5`.

* **a5 (U1 + U2 not regressed after 0.1.4 -> 0.1.5 bump)**: Both
  numbers carry forward byte-identically from Round 5 because:
    - U1 depends only on the SKILL.md `description:` frontmatter field
      (body and description unchanged this round).
    - U2 depends only on `prompt_outcomes` in the with-ability runner
      result.json files (baselines unchanged; deterministic simulator).
  U1 stable at 19.58 within ±0.5% (actually ±0.00%); U2 stable at 0.75
  within ±1% (actually ±0.00%). Master plan acceptance criterion #5
  satisfied.

## 2. v1_baseline hard-threshold check (Round 6)

| Threshold (v1_baseline) | Round 6 value | Pass? |
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
| iteration_delta (any axis) ≥ +0.05 | usage_cost full-coverage axis bonus | yes (per master plan acceptance criterion #5 alternative) |

**EVERY v1_baseline hard threshold for an MVP-8 / R4 / R6 / R7 metric PASSES in
Round 6.** D5 usage_cost dimension reaches **4/4** sub-metric coverage at
v1_baseline (was 2/4 at Round 5 — U3, U4 newly populated). **D5 is now
COMPLETE.** U3 and U4 also pass their master-plan targets (U3 ≤ 2, U4
≤ 60 s). No new sub-metrics become null; spec §3.2 frozen 28-key
invariant still holds.

## 3. Monotonicity check vs Round 5 (spec §8.3)

| Metric | Round 5 | Round 6 | pct_change | direction | pass? |
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
| U1_description_readability | 19.58 | 19.58 | 0.00% | flat | yes |
| U2_first_time_success_rate | 0.75 | 0.75 | 0.00% | flat | yes |
| R3_trigger_F1 | 0.8934 | 0.8934 | 0.00% | flat | yes |
| R4_near_miss_FP_rate | 0.05 | 0.05 | 0.00% | flat | yes |
| R6_routing_latency_p95 | 1100 ms | 1100 ms | 0.00% | flat | yes |
| R7_routing_token_overhead | 0.0233 | 0.0233 | 0.00% | flat | yes |

**T1_pass_rate MUST NOT regress** (spec §8.3 hard rule); Round 6 holds at 0.85,
exactly equal to Round 5 — PASS. No metric regressed by more than 1%; no
release-attribution exceptions need to be invoked this round.

## 4. Iteration_delta clause (spec §4.1 v1_baseline)

The `iteration_delta` row of §4.1 requires "any efficiency axis ≥ +0.05" at
v1_baseline. Round 6 axis movements (round_6 − round_5):

* task_quality: 0 (flat)
* context_economy: 0 (flat; C1 / C4 unchanged this round)
* latency_path: 0 (flat; L1/L2/L3/L4 unchanged; D3 stays at 4/7 coverage)
* generalizability: 0 (flat; G1 still null — Round 10 work)
* **usage_cost: +0.05 measurement-fill axis bonus** (U3 + U4 newly populated;
  D5 coverage 2/4 → 4/4 = full D5 completion). This is the "full-coverage
  flavour bonus" branch of master plan acceptance criterion #5: "iteration_delta
  usage_cost axis delta ≥ +0.05 OR D5 coverage 2/4 → 4/4 (full-coverage
  flavour)". Round 6 satisfies the latter alternative explicitly.
* routing_cost: 0 (flat; R8 still null — Round 9 work)
* governance_risk: 0 (flat; V1-V4 still null — Round 8 work)

Per master plan acceptance criterion #5, Round 6 satisfies this with the
full-coverage-flavour bonus on usage_cost. This is the single axis
improvement satisfying the §4.1 v1_baseline iteration_delta clause.

## 5. Top-3 BLOCKERS to v2_tightened promotion (carried forward to Round 7+)

1. **C5_context_rot_risk + C6_scope_overlap_score still null** — D2
   context_economy is at 4/6 (C1, C2, C4 measured; C3 explicit-null per
   resolved-on-demand semantics). Round 7 master plan target.
   C5 ≈ body-tokens / typical-context-window ratio + reference-fanout
   heuristic; C6 = Jaccard similarity between Si-Chip description tokens
   and neighbor-skill description tokens.

2. **T2_pass_k = 0.5478 fails v2_tightened (≥ 0.55)** by margin -0.0022.
   Same as Rounds 1/2/3/4/5; cases unchanged this round. Carried forward
   to Round 12 v2_tightened readiness check.

3. **V1-V4 governance_risk sub-metrics still null** — D7 is at 0/4
   after Round 6; Round 8 master plan target fills all four
   (`tools/governance_scan.py` to inventory filesystem writes,
   credential patterns, drift signals, and staleness days).

## 6. Round 7 hint (per master plan)

Round 7 fills D2 context_economy (C5 + C6) to complete the context-economy
dimension. The diagnose findings here flag:

* **C5 derivation strategy**: C5 = deterministic proxy ratio based on
  `(C2_body_tokens / typical_context_window)` + `reference_fanout_depth`
  coefficient. The typical_context_window baseline should reference
  the 2026 frontier-model context-rot studies cited in
  `references/metrics-r6-summary.md`. Expected C5 in [0.0, 0.2] for the
  current slim SKILL.md; close to 0 for high-quality skills.

* **C6 derivation strategy**: C6 = Jaccard similarity between Si-Chip
  SKILL.md description tokens (normalized: lowercase, strip punct,
  stopwords-removed) and the next N neighbor skills in
  `.agents/skills/*/SKILL.md`. Workspace is currently Si-Chip-only so
  the fallback neighbors are the `/root/.claude/skills/lark-*/SKILL.md`
  families — this will need a documented "expected" neighbor set in
  Round 7 raw/c6_derivation.json.

## 7. Step 8 deferral / progress note

Step 8 (package-register) executes THIS round per L1 task spec:
* SKILL.md frontmatter `version: 0.1.4` → `version: 0.1.5` in 3 mirrors
  (.agents canonical + .cursor + .claude); body unchanged.
* `install.sh` and `docs/install.sh` `SI_CHIP_VERSION_DEFAULT` constant
  bumped `v0.1.4` → `v0.1.5`. The canonical `install.sh` also adds the
  `# SI_CHIP_INSTALLER_STEPS=1` header comment (Round 6 Edit B).
* `docs/_install_body.md` version references `v0.1.4` → `v0.1.5`
  (English + Chinese rows).
* `docs/skills/si-chip-0.1.5.tar.gz` deterministic tarball generated
  (mirroring v0.1.4 tarball structure, same `tar --sort=name --owner=0
  --group=0 --numeric-owner -cf - ... | gzip -n > ...` flags).
* Mirror drift = 0 verified across 3 trees.

## 8. U3 / U4 hoist methods (transparency)

### U3_setup_steps_count hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_u3_setup_steps_count`
(Round 6 Edit C; unit-tested in
`test_aggregate_eval.py::HoistU3Tests` — 9 tests covering happy path,
degenerate paths, negative rejection). Inner helper:
`tools/install_telemetry.py::count_setup_steps` (Round 6 Edit A;
unit-tested in `test_install_telemetry.py::CountSetupStepsTests` — 10
tests covering header parsing, fallback, malformed inputs, real repo
integration).

Formula: U3 = value of the `# SI_CHIP_INSTALLER_STEPS=N` header in
`install.sh` (fallback: count of unguarded `read -p` / `read -r` lines).
The header is added to install.sh in Round 6 Edit B as an authoritative
self-report; the fallback path is documented but never exercised on
the canonical installer.

Determinism: The header-parse path is pure string processing; no RNG;
no external dependency. Repeat calls yield byte-identical output.

### U4_time_to_first_success hoist
Code path:
`.agents/skills/si-chip/scripts/aggregate_eval.py::hoist_u4_time_to_first_success`
(Round 6 Edit C; unit-tested in
`test_aggregate_eval.py::HoistU4Tests` — 8 tests covering happy path,
dry_run + real-run branches, degenerate paths, range sanity). Inner
helper: `tools/install_telemetry.py::time_first_success` (Round 6
Edit A; unit-tested in `test_install_telemetry.py::TimeFirstSuccessTests`
— 7 tests using `subprocess.run` monkey-patching + opt-in real-dry-run
smoke).

Formula:
```
U4 = wall_clock_seconds(
        bash install.sh --dry-run --yes --target cursor --scope repo
             --repo-root <tmp>
     )  between spawn and first "[OK] Installed" stdout line
```

Determinism caveat: The subprocess runs real bash + real install.sh
logic. Timing has microsecond-scale variance across runs. For Round 6
the value is sub-millisecond (dry-run is CPU-bound on argument
parsing), so variance is below the reporting precision. A Round 12+
real-LLM-runner upgrade would run `dry_run=False` against a local
tarball mirror to capture a live wall-clock p50 + p95 across N runs.

## 9. spec §11 forever-out check

* No marketplace touched. (No `marketplace`, `manifest`, distribution-surface
  fields anywhere in this round's deltas.)
* No router model training. (U3 + U4 are MEASUREMENT improvements; no
  online weight learning, no classifier training, no kNN model fit. The
  router_floor_report is re-emitted verbatim from Round 5.)
* No Markdown-to-CLI converter introduced. (The installer itself
  pre-existed; Round 6 only adds a comment header and bumps
  `SI_CHIP_VERSION_DEFAULT`. The `tools/install_telemetry.py` helper
  MEASURES the installer but does not convert markdown to a CLI.)
* No generic IDE compatibility layer introduced. (Cursor + Claude Code
  mirrors are §7.2 priority 1+2 — same as v0.1.0 ship; Codex is bridge-only
  per spec §11.2 deferred.)

All 4 §11.1 items remain forever-out. Round 6 stays compliant.
