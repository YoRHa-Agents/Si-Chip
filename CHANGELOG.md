# Changelog

All notable changes to Si-Chip are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pages site supports zh/en language toggle and day/night theme toggle. Hero top-right `[ LANG / EN ]` and `[ THEME / DAY ]` buttons; persisted to `localStorage` (`si-chip-lang`, `si-chip-theme`); first-visit defaults from `navigator.language` and `prefers-color-scheme`. Body markdown bilingualized via `<div lang="en" markdown="1">` / `<div lang="zh" markdown="1">` pattern; chrome translations live in a JSON island inside `_layouts/default.html`.
- `docs/assets/css/nier.css` extended (~+90 lines) with three new sections: i18n display rules + responsive table overflow, dark-mode palette overrides under `body[data-theme="night"]`, and toggle control styles.
- `docs/assets/js/nier.js` extended (~12 → ~100 lines) with theme + language state machines (localStorage + system-preference detection + DOM event handlers); cursor blink behavior preserved.
- `CONTRIBUTING.md` §10 documents the bilingualization contract, the JSON island convention, and the loosened sync contracts for `_install_body.md` / `_userguide_body.md`.

### Fixed
- The 8-column table in `docs/demo.md` (and any wide table site-wide) no longer overflows the NieR page chrome on the right edge. `.page-body table` is now `display: block; max-width: 100%; overflow-x: auto; white-space: nowrap;` at all viewport widths, so wide tables scroll horizontally inside the chrome rather than bursting out.

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
