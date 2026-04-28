# Changelog

All notable changes to Si-Chip are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `install.sh` — one-line bash installer at `https://yorha-agents.github.io/Si-Chip/install.sh`. Supports `--target cursor|claude|both`, `--scope global|repo`, `--repo-root <path>`, `--version`, `--source-url`, `--yes`, `--dry-run`, `--force`, `--uninstall`, `--help`. Interactive when run in a TTY without `--yes`.
- `docs/skills/si-chip/` — fourth Skill payload mirror (alongside `.agents/`, `.cursor/`, `.claude/`) so the installer can fetch the 9-file payload from the public Pages URL. Drift contract documented in `CONTRIBUTING.md` §9.
- `docs/install.sh` — byte-identical copy of root `install.sh`, served by Pages.

### Changed
- `INSTALL.md` and `docs/_install_body.md` — promoted the new one-line install path to the top; the previous git-clone manual flow is now under `## Manual install`.
- `README.md` — `## Quick Start` split into `## Quick Install` (one-liner) and `## Quick Start (after install or clone)` (the original 3-command verification block).

### Notes
- The installer never targets Codex (spec §7.2: Codex is bridge-only and deferred). It also never offers a `--target marketplace` option (spec §11.1: forever-out).
- `DESIGN.md` is intentionally omitted from all three platform mirrors and the `docs/skills/si-chip/` Pages mirror.

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

[0.1.0]: https://github.com/YoRHa-Agents/Si-Chip/releases/tag/v0.1.0
