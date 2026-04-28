# Changelog

All notable changes to Si-Chip are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Round 4 (v0.1.3) dogfood: `L1_wall_clock_p50`, `L3_step_count`, and `L4_redundant_call_ratio` now hoisted from per-case runner instrumentation into `metrics_report.yaml`; D3 latency-path dimension reaches 4/7 sub-metric coverage at `v1_baseline` (was 1/7 in Round 3). L1 = 1.2153 s (L1 ≤ L2 sanity invariant PASS), L3 = 20 (integer ≥ 1), L4 = 0.0 (degenerate-but-valid per master plan risk_flag; unique prompt_ids per case in the simulated runner).
- `evals/si-chip/runners/with_ability_runner.py` adds `percentile_p50`, `step_count_from_outcomes`, and `redundant_call_ratio_from_outcomes` helpers (Round 4 Edit A). Per-case `latency_p50_s` / `step_count` / `redundant_call_ratio` surfaced to `result.json` alongside Round 3's R7 instrumentation. Sibling test extended (25 tests; 17 new in Round 4).
- `evals/si-chip/runners/no_ability_runner.py` mirrors the same L1/L3/L4 plumbing (Round 4 Edit B). New test file `evals/si-chip/runners/test_no_ability_runner.py` (21 tests) covers helpers, fields, determinism, and L1 ≤ L2 sanity invariant on the baseline arm.
- `.agents/skills/si-chip/scripts/aggregate_eval.py` adds `hoist_l1_wall_clock_p50` (mean latency_p50_s), `hoist_l3_step_count` (round(mean step_count)), and `hoist_l4_redundant_call_ratio` (mean redundant_call_ratio clamped to [0,1]) (Round 4 Edit C). Sibling test extended (27 tests; 12 new in Round 4) covering hoist correctness, degenerate paths, L1 ≤ L2 invariant, and 28-key contract.
- All 6 evidence files at `.local/dogfood/2026-04-28/round_4/` (`basic_ability_profile.yaml`, `metrics_report.yaml`, `router_floor_report.yaml`, `half_retire_decision.yaml`, `next_action_plan.yaml`, `iteration_delta_report.yaml`) plus `raw/` derivations (`l1_l3_l4_derivation.json`, re-derived `r4_near_miss_FP_rate_derivation.json` and `r7_derivation.json`, `notes.md`, `eval_run.log`, `aggregate_eval.log`, `aggregator_raw_output.yaml`, `spec_validator.json`).
- `docs/skills/si-chip-0.1.3.tar.gz` deterministic release tarball (SHA-256 `5ad6880874856ae85093416de8e127304cb87701ec60b547fcf042fa0ba3db68`; reproducible across rebuilds; same canonical layout as v0.1.0/v0.1.1/v0.1.2: 1 SKILL.md + 5 references + 3 scripts).
- Round 3 (v0.1.2) dogfood: `R6_routing_latency_p95` and `R7_routing_token_overhead` now hoisted from per-cell router-test data and per-prompt runner instrumentation into `metrics_report.yaml`; D6 routing-cost dimension reaches 8/8 sub-metric coverage at `v1_baseline` (was 6/8 in Round 2). R6 = 1100 ms (≤ 2000 ms ceiling, also passes v2_tightened ≤ 1200 ms); R7 = 0.0233 (≤ 0.20 ceiling, also passes v2_tightened 0.12 and v3_strict 0.08).
- `evals/si-chip/runners/with_ability_runner.py` records `routing_stage_tokens` + `body_invocation_tokens` per prompt (Round 3 Edit A); per-case totals also surfaced for the aggregator. Sibling test `evals/si-chip/runners/test_with_ability_runner.py` (8 unit tests covering instrumentation determinism + v1_baseline ceiling).
- `.agents/skills/si-chip/scripts/aggregate_eval.py` adds `hoist_r6_routing_latency_p95` (cells where `pass_rate >= 0.80` → min `latency_p95_ms`) and `hoist_r7_routing_token_overhead` (sum routing / sum body) plus a new `--router-floor-report` CLI flag (Round 3 Edit B). Sibling test `.agents/skills/si-chip/scripts/test_aggregate_eval.py` (12 unit tests + 4 doctests covering hoist logic, degenerate paths, and 28-key invariant).
- All 6 evidence files at `.local/dogfood/2026-04-28/round_3/` (`basic_ability_profile.yaml`, `metrics_report.yaml`, `router_floor_report.yaml`, `half_retire_decision.yaml`, `next_action_plan.yaml`, `iteration_delta_report.yaml`) plus `raw/` derivations (`r4_near_miss_FP_rate_derivation.json`, `r7_derivation.json`, `notes.md`, `eval_run.log`, `spec_validator.json`).
- `docs/skills/si-chip-0.1.2.tar.gz` deterministic release tarball (SHA-256 reproducible across rebuilds; same canonical layout as v0.1.0/v0.1.1: 1 SKILL.md + 5 references + 3 scripts).

### Changed
- `.agents/skills/si-chip/SKILL.md` frontmatter `version: 0.1.2` → `version: 0.1.3` (canonical; Round 4), with mirrored bumps in `.cursor/skills/si-chip/SKILL.md` and `.claude/skills/si-chip/SKILL.md`. Body unchanged. Mirror drift verified = 0 across all 3 trees.
- `install.sh` and `docs/install.sh` default `SI_CHIP_VERSION_DEFAULT` constant: `v0.1.2` → `v0.1.3` (Round 4). Override with `--version v0.1.2` (or earlier) to install a prior payload.
- `docs/_install_body.md` `--version` table cell: `v0.1.2` → `v0.1.3` (Round 4; English + Chinese rows).
- Round 4 promotion-state trace: `consecutive_v1_passes: 4` (Round 1 + 2 + 3 + 4); promotion to v2_tightened still held to Round 12 per master plan.
- `.agents/skills/si-chip/SKILL.md` frontmatter `version: 0.1.1` → `version: 0.1.2` (Round 3), with mirrored bumps in the 3 platform trees.
- `install.sh` and `docs/install.sh` default `SI_CHIP_VERSION_DEFAULT` constant: `v0.1.1` → `v0.1.2` (Round 3).
- `docs/_install_body.md` `--version` table cell: `v0.1.1` → `v0.1.2` (Round 3; English + Chinese rows).
- Pages site supports zh/en language toggle and day/night theme toggle. Hero top-right `[ LANG / EN ]` and `[ THEME / DAY ]` buttons; persisted to `localStorage` (`si-chip-lang`, `si-chip-theme`); first-visit defaults from `navigator.language` and `prefers-color-scheme`. Body markdown bilingualized via `<div lang="en" markdown="1">` / `<div lang="zh" markdown="1">` pattern; chrome translations live in a JSON island inside `_layouts/default.html`.
- `docs/assets/css/nier.css` extended (~+90 lines) with three new sections: i18n display rules + responsive table overflow, dark-mode palette overrides under `body[data-theme="night"]`, and toggle control styles.
- `docs/assets/js/nier.js` extended (~12 → ~100 lines) with theme + language state machines (localStorage + system-preference detection + DOM event handlers); cursor blink behavior preserved.
- `CONTRIBUTING.md` §10 documents the bilingualization contract, the JSON island convention, and the loosened sync contracts for `_install_body.md` / `_userguide_body.md`.

### Fixed
- The 8-column table in `docs/demo.md` (and any wide table site-wide) no longer overflows the NieR page chrome on the right edge. `.page-body table` is now `display: block; max-width: 100%; overflow-x: auto; white-space: nowrap;` at all viewport widths, so wide tables scroll horizontally inside the chrome rather than bursting out.

### Notes
- `tools/spec_validator.py --json` default-mode 8/8 PASS unchanged after Round 4 (matches v0.1.0 ship report and Round 3). Strict-prose-count mode still flags the known §3.1/§4.1 vs §13.4 discrepancies (R6_KEYS + THRESHOLD_TABLE) — reconciliation deferred to Round 11 spec bump per master plan.
- Round 4 iteration_delta_report satisfies the §4.1 `iteration_delta ≥ +0.05` v1_baseline row via the master-plan-allowed measurement-fill axis bonus on `latency_path` (D3 sub-metric coverage 1/7 → 4/7). L2_wall_clock_p95 byte-identical to Round 3 at 1.4693 s (within ±1% as master plan round_4 acceptance criterion #4 requires).
- Round 3 metrics_report C1_metadata_tokens 78 → 82 is fully attributable to commit 96f22d4 (`chore(release): v0.1.1`) which bumped SKILL.md frontmatter `version + license` AFTER Round 2 evidence was authored; Round 3 frontmatter bump (0.1.1 → 0.1.2) added 0 tokens, and the Round 4 bump (0.1.2 → 0.1.3) also adds 0 tokens (verified: o200k_base tokenization is identical for 0.1.2 and 0.1.3). Both numbers pass v1_baseline (≤ 120) and v2_tightened (≤ 100).

## [0.1.1] — 2026-04-28

This release packages everything that has landed since v0.1.0 (PR #2 through PR #6) into a single named version. The frozen specification at `.local/research/spec_v0.1.0.md` is unchanged; this is a packaging / docs / installer release on top of the same v0.1.0 spec gate evidence.

### Added
- One-line bash installer (PR #5, refined in PR #6) at `https://yorha-agents.github.io/Si-Chip/install.sh`. Supports `--target cursor|claude|both`, `--scope global|repo`, `--repo-root <path>`, `--version`, `--source-url`, `--yes`, `--dry-run`, `--force`, `--uninstall`, `--help`. Interactive in a TTY without `--yes`.
- `docs/skills/si-chip-0.1.1.tar.gz` — deterministic release tarball for v0.1.1 (new in this release). The v0.1.0 tarball at `docs/skills/si-chip-0.1.0.tar.gz` is preserved for backward compatibility — `--version v0.1.0` still works.
- NieR: Automata-themed GitHub Pages design (PR #3, fixed in PR #4): warm khaki / olive-brown palette, B612 Mono + Saira Stencil One typography, bracketed `[SI-CHIP]` title, scan-line overlay, blinking cursor, `// CHAPTER 0N //` section markers, "GLORY TO MANKIND." motto, `[STATUS: ONLINE] [NODE: 0001] [VER: 0.1.1] [OPERATOR: 6O]` footer status grid. Cayman theme retired.
- `docs/_layouts/default.html`, `docs/_includes/{header,footer}.html`, `docs/assets/css/nier.css` (~476 lines), `docs/assets/js/nier.js` (12 lines, prefers-reduced-motion guarded).
- `CONTRIBUTING.md` §9 Mirror Drift Contract: 3-tree (`.agents/`, `.cursor/`, `.claude/`) + 1-derived-tarball (`docs/skills/si-chip-<version>.tar.gz`) contract with diff and rebuild commands.

### Changed
- `.agents/skills/si-chip/SKILL.md` frontmatter: `version: 0.1.0` → `version: 0.1.1`; `license: internal` → `license: Apache-2.0` (matches the repo's actual `LICENSE` file). Token budget still passes v3_strict (metadata ≤ 100, body ≤ 5000).
- `install.sh` and `docs/install.sh` default `SI_CHIP_VERSION` constant: `v0.1.0` → `v0.1.1`. Override with `--version v0.1.0` to install the prior payload.
- `INSTALL.md` and `docs/_install_body.md`: now lead with `## Quick Install (one-line)`; the previous git-clone flow is `## Manual install`; Codex deferral promoted to its own section.
- `README.md`: status badge bumped to `v0.1.1 ship-eligible`; `## Quick Start` split into `## Quick Install` (one-liner) and `## Quick Start (after install or clone)` (the original 3-command verification block).
- `install.sh` HTTP(S) path now downloads a single tarball at `${SOURCE_URL}/skills/si-chip-${VERSION}.tar.gz` and extracts it (PR #6). The previous per-file mirror at `docs/skills/si-chip/` was removed because Jekyll renders YAML-front-matter `.md` files (SKILL.md was served at `/skills/si-chip/SKILL/`, raw `.md` URL = 404). `file://` source URLs continue to use per-file `cp` for local testing.

### Fixed
- Pages build no longer hangs on `include_relative ../USERGUIDE.md` / `../INSTALL.md` traversal in `docs/userguide.md` and `docs/install.md` (PR #2). Userguide/install bodies now ship as sibling Jekyll partials `docs/_userguide_body.md` and `docs/_install_body.md`. Live URLs return HTTP 200.
- `docs/_config.yml` previously had `theme: ""` which Jekyll rejects (`MissingDependencyException: The  theme could not be found.`); the `theme:` key is now omitted entirely so Jekyll picks up the local `_layouts/default.html` via `defaults.layout: default` (PR #4).
- `install.sh` no longer 404s on SKILL.md when run against the live Pages URL (PR #6 tarball switch).

### Notes
- Codex (`--target codex`) remains out of scope (spec §7.2: bridge-only, deferred).
- Marketplace (`--target marketplace`) remains forever-out (spec §11.1).
- `DESIGN.md` is intentionally NOT in any platform mirror or in the tarball (internal artifact only).
- Spec text `.local/research/spec_v0.1.0.md` is unchanged — this release does NOT bump the spec version. The next spec bump (when there is one) would go to spec v0.2.0 alongside a project release ≥ v0.2.0.
- Dogfood evidence at `.local/dogfood/2026-04-28/round_{1,2}/` is unchanged; the v0.1.0 ship verdict (SHIP_ELIGIBLE at `relaxed` / `v1_baseline`, two consecutive v1 passes, ALL_TREES_DRIFT_ZERO, 8/8 spec invariants PASS) carries forward unchanged.

## [0.1.0] — 2026-04-28

Initial public release. Si-Chip is published as a persistent BasicAbility
optimization factory with a frozen specification, a self-installing Skill
package, an evaluation harness, and machine-checkable spec invariants.

### Added
- Frozen specification `spec_v0.1.0.md` with 7 normative sections (§3 metrics,
  §4 gate profiles, §5 router paradigm, §6 half-retirement, §7 packaging,
  §8 self-dogfood, §11 scope boundaries).
- Self-Skill package at `.agents/skills/si-chip/` (canonical source-of-truth):
  `SKILL.md` (metadata=78 tok, body=2020 tok — passes v3_strict packaging
  gate), 5 distilled references, 3 helper scripts.
- 6 frozen factory templates under `templates/` (BasicAbility schema, eval
  suite, router-test matrix, half-retire decision, next-action plan,
  iteration-delta report).
- Spec validator `tools/spec_validator.py` with 8 invariants (default mode
  honours the §3.1 / §4.1 tables; `--strict-prose-count` flags the known
  §13.4 prose discrepancies).
- Eval harness under `evals/si-chip/`: 6 cases × 20 prompts (10
  should_trigger + 10 should_not_trigger), no-ability and with-ability
  baseline runners, end-to-end metrics report.
- Two completed dogfood rounds at `.local/dogfood/2026-04-28/round_{1,2}/`
  with all 6 frozen evidence files each, plus the v0.1.0 ship report and
  ship decision YAML.
- Cross-platform mirrors: `.cursor/skills/si-chip/` and `.claude/skills/si-chip/`
  (drift = 0 verified across all three trees).
- Cursor bridge rule `.cursor/rules/si-chip-bridge.mdc`.
- Compiled rules layer `AGENTS.md` and `.rules/si-chip-spec.mdc`.
- Persistence: `.local/memory/skill_profiles/si-chip/learnings.jsonl` (3 entries:
  round_1, round_2, ship).

### Gate verdict (v0.1.0 ship)
- Default `spec_validator.py`: PASS (8/8 invariants).
- Two consecutive `v1_baseline` (relaxed) gate passes (R1: pass_rate 0.85,
  R2: pass_rate 0.85 with body slimmed 18.97 % and `R4_near_miss_FP_rate`
  populated at 0.05).
- Cross-tree drift: ALL_TREES_DRIFT_ZERO.
- Ship verdict: SHIP_ELIGIBLE at gate `relaxed` / `v1_baseline`.

### Known limitations
- Eval baselines are deterministic SHA-256 simulations (LLM-backed runner is
  the documented upgrade path; the result.json schema and runner CLI are
  stable so the swap requires no aggregator change).
- Spec internal discrepancies in §3.1 / §13.4 (28 vs 37 sub-metrics; 21 vs 30
  threshold cells) — the validator handles them in default mode and flags
  them in strict-prose mode. Reconciliation requires a future spec bump.
- Three R6 sub-metrics (R6_routing_latency_p95, R7_routing_token_overhead, plus
  the L1 / U1–U4 family) remain `null` — targeted in `next_action_plan.yaml`
  for round 3.

### Out of scope (per spec §11)
- No marketplace or distribution surface.
- No router model training.
- No Markdown-to-CLI converter.
- No generic IDE compatibility layer.
- Codex native SKILL.md runtime is bridge-only and deferred.

[Unreleased]: https://github.com/YoRHa-Agents/Si-Chip/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/YoRHa-Agents/Si-Chip/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/YoRHa-Agents/Si-Chip/releases/tag/v0.1.0
