# Si-Chip Self-Skill Package — DESIGN.md

> Stage S1 (design only). Authoritative spec: `.local/research/spec_v0.1.0.md`.
> This document is the package-level design contract; no implementation lives here.
> Owner stages refer to the implementation plan: S2 = Skill Body & Scripts, S3 = Self-Eval Harness,
> S4 = Cross-Platform Sync, S5 = Dogfood Round 1+, S6 = Promotion / Cross-Platform Sync (Codex deferred).

---

## 1. Purpose

This package is the source-of-truth artifact through which Si-Chip ships itself as a Skill.
Per spec §7.1, the only canonical location is `.agents/skills/si-chip/`; every platform target
(`.cursor/skills/si-chip/`, `.claude/skills/si-chip/`, future `.codex/`) is a synchronized
derivative of this directory. The package exists so Si-Chip can (a) install and trigger as a
first-class `BasicAbility` on Cursor and Claude Code, and (b) run the full self-dogfood loop
defined in spec §8 against its own files. Per spec §13.4 the package is also the unit that the
v0.1.0 ship gate evaluates: it must be loadable, produce a `BasicAbilityProfile`, and emit the
six minimum evidence files in spec §8.2 for at least two consecutive dogfood rounds. Anything
outside this directory tree (marketplace manifests, IDE shims, router weights) is rejected by
spec §11.1.

---

## 2. File Inventory

The Skill package owns exactly the following files. Token budgets are upper bounds enforced by
`scripts/count_tokens.py` (planned in S2); "owner stage" indicates the wave that authors the file;
"source spec section" is the normative source of truth.

| path | size budget | owner stage | source spec section |
|---|---|---|---|
| `.agents/skills/si-chip/SKILL.md` | metadata (frontmatter + description) ≤ 100 tokens; body ≤ 5000 tokens | S2 | §7.1, §7.3, §13.1 |
| `.agents/skills/si-chip/references/basic-ability-profile.md` | body ≤ 1500 tokens | S2 | §2.1, §2.2 |
| `.agents/skills/si-chip/references/self-dogfood-protocol.md` | body ≤ 1500 tokens | S2 | §8.1, §8.2, §8.3 |
| `.agents/skills/si-chip/references/metrics-r6-summary.md` | body ≤ 1500 tokens | S2 | §3.1, §3.2, §4.1 |
| `.agents/skills/si-chip/references/router-test-r8-summary.md` | body ≤ 1500 tokens | S2 | §5.1, §5.2, §5.3, §5.4 |
| `.agents/skills/si-chip/references/half-retirement-r9-summary.md` | body ≤ 1500 tokens | S2 | §6.1, §6.2, §6.3, §6.4 |
| `.agents/skills/si-chip/scripts/profile_static.py` | ≤ 250 LOC | S2 | §2.1, §8.1 step 1 |
| `.agents/skills/si-chip/scripts/count_tokens.py` | ≤ 150 LOC | S2 | §3.2 (C1), §7.3 |
| `.agents/skills/si-chip/scripts/aggregate_eval.py` | ≤ 300 LOC | S3 | §3.2, §8.2 (evidence files 2,3,6) |
| `.agents/skills/si-chip/DESIGN.md` (this file) | n/a (design artifact, not loaded by Skill runtime) | S1 | §7, §13 |

> The five `references/` files are loaded on-demand and are explicitly excluded from the SKILL.md
> token budget per spec §7.3 and §13.1; their job is to keep `SKILL.md` body small while preserving
> traceability back to spec sections.

---

## 3. Module Boundaries (six thin self-built layers)

Per R7 §6, Si-Chip self-implements only six thin layers; everything else is a `devolaflow.*`
import (see §4). Each layer maps to a stable file path inside the package. Where a layer is
implementation-bearing it lives outside the Skill body to keep metadata small.

| # | Layer | Package path | Responsibility (spec source) |
|---|---|---|---|
| 1 | `schema/skill_profile.py` | `.agents/skills/si-chip/scripts/profile_static.py` materializes / validates the dataclass; the dataclass module itself lives at repo `src/si_chip/schema/skill_profile.py` (created in S2) and is imported by the script | Hold the `BasicAbilityProfile` dataclass exactly mirroring spec §2.1 fields and §2.2 stage enum; reject extra/missing keys |
| 2 | `metrics/bridge.py` | repo `src/si_chip/metrics/bridge.py`; consumed by `scripts/aggregate_eval.py` | Map OTel GenAI attributes + NineS scorer output + `count_tokens.py` results onto R6 7 dim / 28 sub-metrics (spec §3.1); fill MVP-8 unconditionally and `null`-pad the rest per §3.2 |
| 3 | `stage/classifier.py` | repo `src/si_chip/stage/classifier.py` | Move a profile across the §2.2 stage graph using §4 promotion rule (consecutive-2-rounds at current gate) and the §6 half-retire trigger table |
| 4 | `stage/half_retire_review.py` | repo `src/si_chip/stage/half_retire_review.py` | Compute the §6.1 7-axis value vector, evaluate §6.2 keep/half_retire/retire rules against the bound v1/v2/v3 bucket, and emit a `half_retire_decision.yaml` per §6.3 |
| 5 | `router_test/harness.py` | repo `src/si_chip/router_test/harness.py` | Run the §5.3 8-cell MVP matrix (or 96-cell Full); compute per-cell `R1..R7` + emit a single `router_floor` per §5.3 / §5.4 |
| 6 | `templates/*.yaml` | repo `templates/` (top-level, per spec §9) | Provide the six machine-readable yaml templates that the protocol consumes; all template structural validation goes through `devolaflow.template_engine.validator.validate_template` |

> The Skill package itself ships only the three `scripts/` (`profile_static.py`, `count_tokens.py`,
> `aggregate_eval.py`). They import the dataclasses / harnesses listed above from the wider repo.
> This split keeps the Skill body and metadata small while letting heavyweight logic evolve outside
> the §7.3 packaging gate.

---

## 4. R7 Import Map

The following table is copied / condensed from `r7_devolaflow_nines_integration.md` §1. Each row
records a Si-Chip duty, the upstream `devolaflow.*` API symbol Si-Chip will import, and which of
the six self-built layers (§3) calls it. NineS CLI and `nines/*` modules are routed through
`metrics/bridge.py` for scoring and through `router_test/harness.py` for dataset / overlap pulls.

| # | Si-Chip duty | devolaflow API symbol | Called from |
|---|---|---|---|
| 1 | Composite gate scoring per dimension (R6 D1) | `gate.scorer.score_dimension` / `gate.scorer.composite_score` | `metrics/bridge.py` |
| 2 | Severity / DimensionScore / ProfileConfig types | `gate.models.Severity`, `gate.models.ProfileConfig`, `gate.models.DimensionScore` | `metrics/bridge.py`, `stage/classifier.py` |
| 3 | Gate profile selection (relaxed/standard/strict) bound to v1/v2/v3 | `gate.profiles.Profile.relaxed` / `.standard` / `.strict` | `stage/classifier.py` |
| 4 | Convergence / ratchet / cycle detection for §4.2 promotion and §6.4 reactivation loop guard | `gate.convergence`, `gate.ratchet`, `gate.cycle_detector` | `router_test/harness.py`, `stage/half_retire_review.py` |
| 5 | Budget + over-complexity check at promotion boundaries (§3 D3) | `gate.budget`, `gate.complexity_detector` | `stage/classifier.py` |
| 6 | Reinforcement injection on gate failure | `gate.reinforcement` | `stage/classifier.py` |
| 7 | Drift signal (V3) + staleness (V4) + cleanup proposals | `entropy_manager.DocFreshness`, `entropy_manager.DeviationScanner`, `entropy_manager.cleanup` | `stage/half_retire_review.py` |
| 8 | Persistent learnings + confidence decay (§10.2) | `learnings.capture_learning`, `learnings.decay_confidence`, `learnings.consolidate_session`, `learnings.get_learnings_stats` | `stage/half_retire_review.py`, `metrics/bridge.py` |
| 9 | Feedback tracking for half_retire / retire decisions (§10.2) | `feedback.*` | `stage/half_retire_review.py` |
| 10 | Token / footprint baseline for D2 (C2/C3/C4) | `compression_pipeline.CompressionPipeline.run`, `compression_pipeline.make_stage` | `metrics/bridge.py` |
| 11 | Envelope wrap / unwrap for resolved-token accounting (C3) | `compressor.wrap_data_envelope`, `compressor.unwrap_data_envelope` | `metrics/bridge.py` |
| 12 | Deterministic memory-router baseline (R5 floor / R6 routing latency) | `memory_router.router.MemoryRouter.lookup_case` / `lookup_case_strict` | `router_test/harness.py` |
| 13 | Multi-skill description pool (R8 description_competition_index, C6 scope_overlap) | `memory_router.cache.MemoryCase`, `memory_router.cache.build_case_from_dict` | `router_test/harness.py`, `metrics/bridge.py` |
| 14 | NineS scorer bridge for T1/T3/G3 | `nines.scorer.nines_dimension_scores`, `nines.scorer.run_nines_eval`, `nines.scorer.run_nines_analyze` | `metrics/bridge.py` |
| 15 | Reference / overlap data collection | `nines.researcher.collect_research`, `nines.researcher.analyze_target` | `router_test/harness.py` |
| 16 | Research advice for next_action_plan | `nines.advisor.get_research_advice` | `stage/classifier.py` (next_action recommendation) |
| 17 | NineS availability detection (degrade gracefully) | `nines.detector.detect_nines`, `nines.detector.ensure_nines` | `metrics/bridge.py` |
| 18 | Workflow recommendation at evaluated → productized handoff | `pre_decision.recommend.recommend_workflow` | `stage/classifier.py` |
| 19 | Governance freeze for `governed` stage | `pre_decision.checklist.auto_detect`, `pre_decision.validate.validate_consistency`, `pre_decision.freeze.freeze_config` | `stage/classifier.py` |
| 20 | Acceptance-criteria draft for evaluate step | `ac_generator.*` | `stage/classifier.py` |
| 21 | R8 thinking-depth knob (Si-Chip MUST NOT reinvent) | `task_adaptive_selector.select_context(task_type, round_num=N)`, `task_adaptive_selector.apply_round_escalation`, `task_adaptive_selector.match_profile` | `router_test/harness.py` |
| 22 | Template IR parsing for §9 templates | `template_engine.parser.parse_template`, `template_engine.models.WorkflowTemplate` | `templates/*.yaml` (loaded via `aggregate_eval.py`) |
| 23 | Template structural validation (§9 contract) | `template_engine.validator.validate_template` | `templates/*.yaml` |
| 24 | Template runtime / stage composition (§8.1 8-step order) | `template_engine.runtime.select_stages_for_runtime`, `template_engine.composer.SequenceOp/ParallelOp/ChoiceOp/LoopOp/GateOp` | `templates/*.yaml` |
| 25 | Template registry + multi-version | `template_engine.registry.TemplateRegistry.discover` / `.load_template` / `.register` | `templates/*.yaml` |
| 26 | Template inheritance (baseline / domain / project) | `template_engine.inheritance.resolve_inheritance` | `templates/*.yaml` (S5+) |
| 27 | Compiled output to AGENTS.md / platform dirs (§7, §12) | `local.compiler.RuleCompiler`, `local.workspace`, `local.merge`, `local.drift` | Cross-platform sync (S4) — not Skill-runtime |

> Codex bridge (`AGENTS.md` + `.codex/`) is wired in S6 via row 27; v0.1.0 keeps it as bridge only
> per spec §7.2 row 3 and §11.2.

---

## 5. Packaging Gate Budget Plan (spec §7.3)

The §7.3 hard ceilings are `metadata_tokens ≤ 100`, `body_tokens ≤ 5000`, install steps ≤ 2, must
emit own `BasicAbilityProfile`, must execute one §8 round. Token budgets are sub-allocated as
follows; `scripts/count_tokens.py` (planned S2) verifies each row at packaging time.

| Section in `SKILL.md` | Allocated tokens | Purpose |
|---|---:|---|
| Frontmatter (`name`, `version`, `description`, `triggers`) — counted as metadata | ≤ 100 | Trigger surface for Cursor / Claude Code metadata index |
| Body — trigger examples (10 should-trigger + 10 should-not, condensed) | 600 | Feeds R8 §5.3 trigger pack scenario `trigger_basic` directly |
| Body — when-to-use | 800 | Tells the calling agent the §1.1 identity and §11.1 boundary |
| Body — how-to (8-step protocol pointer + script invocations) | 1500 | Mirrors §8.1 ordered steps; references `scripts/` |
| Body — refs index (links to the 5 `references/*.md`) | 600 | Keeps detail pages lazy-loaded; protects body budget |
| Body — dogfood quickstart (1-page minimum to satisfy §7.3 install-≤2 + §8.2 evidence pointer) | 1500 | Lets a fresh user run round 1 in two commands |
| **Body total** | **5000** | matches §7.3 hard ceiling |

Notes:
- Token counting is performed by `scripts/count_tokens.py` (S2). It MUST use the same tokenizer as
  the consuming runtime (Cursor uses Anthropic tokenizer; Claude Code uses Anthropic tokenizer);
  a tokenizer mismatch is treated as a §7.3 violation.
- §4 §3.2 freeze: under `v2_tightened` metadata drops to ≤ 100 (already met) and under `v3_strict`
  to ≤ 80; the script must report headroom against all three gate columns even at v0.1.0.
- The `references/*.md` files are NOT counted toward `body_tokens`; each carries its own ≤ 1500
  per-file budget (see §2 above) so the on-demand load stays small.

---

## 6. Cross-platform Sync Plan (spec §7.2)

Sync direction is one-way: `.agents/skills/si-chip/` → platform target. `local.compiler.RuleCompiler`
+ `local.drift` enforce hash-based drift detection per spec §10 / §12.3.

### 6.1 Cursor (priority 1 — required at v0.1.0)
- Target: `.cursor/skills/si-chip/` (mirrors `SKILL.md` + `references/` + `scripts/`).
- Optional bridge: `.cursor/rules/si-chip-bridge.mdc` for repository-scoped rule injection.
- Trigger: handled by Cursor Skill metadata (`description` + frontmatter).
- §7.3 gate must hold on the synced copy; CI re-runs `scripts/count_tokens.py` against
  `.cursor/skills/si-chip/SKILL.md`.

### 6.2 Claude Code (priority 2 — required at v0.1.0)
- Target: `.claude/skills/si-chip/` (`SKILL.md` + `references/` + `scripts/`).
- Trigger: Claude Code Skill index uses the same `description`; no body changes.
- Bridge artifacts (commands / hooks / plugin manifest) are explicitly **deferred** per spec §11.2
  ("Plugin distribution") — not in v0.1.0.

### 6.3 Codex (priority 3 — DEFERRED to follow-up)
- Bridge-only at v0.1.0: `AGENTS.md` (already compiled) + `.codex/profiles/si-chip.md`
  + `.codex/instructions/si-chip-bridge.md`.
- No assumption that Codex CLI exposes a native `SKILL.md` runtime (spec §7.2 row 3 + §11.2).
- Native Codex Skill packaging is explicitly DEFERRED to v0.2.x and is out of scope for this
  design. A follow-up plan (S7+) will land after Cursor + Claude Code pass §4 v3_strict.

---

## 7. Out-of-Scope Assertions (spec §11.1)

- The package MUST NOT ship any marketplace manifest, registry record, hosted-distribution
  endpoint, or commerce surface; introducing one is a §11.3 hard reject.
- The package MUST NOT contain training data, fine-tuning configs, online learning weights, or any
  artifact whose purpose is to train a Router model; only the §5.1 paradigms are allowed.
- The package MUST NOT include a Markdown-to-CLI auto-converter or its templates; §11.1 forbids it
  permanently for v0.x.
- The package MUST NOT add a generic IDE / Agent-runtime compatibility layer beyond the three
  prioritized targets in §7.2 (Cursor, Claude Code, Codex-bridge); broader IDE support
  (OpenCode / Copilot CLI / Gemini CLI / etc.) is §11.2 deferred and out of scope here.
