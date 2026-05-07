# Si-Chip Bridge Instructions (Codex)

> Si-Chip v0.5.1 — bridge handoff for OpenAI Codex.
> Per spec §7.2 + §11.2, Codex consumes Si-Chip via this bridge and
> `AGENTS.md` only — there is **no native SKILL.md runtime** in v0.x.
> Cursor and Claude Code remain priority 1 + 2 (frozen).

## Read These First
1. `AGENTS.md` (repo root) — full Normative corpus (auto-generated from
   `.rules/si-chip-spec.mdc` via DevolaFlow `RuleCompiler`).
2. `.codex/profiles/si-chip.md` — sibling profile metadata.
3. `.agents/skills/si-chip/SKILL.md` — reference only (NOT loaded as a
   Codex runtime skill in v0.x; Cursor / Claude Code load it natively).

## Hard-Rule Preamble (verbatim from AGENTS.md §13; 15 rules at v0.5.1)
1. Treat §3 / §4 / §5 / §6 / §7 / §8 / §11 as Normative; ignoring = violation.
2. Reject marketplace / router-model training / Markdown-to-CLI / generic IDE compat.
3. Speak in `BasicAbility` first-class terms.
4. Bind every metric judgment to `v1_baseline / v2_tightened / v3_strict`.
5. Honor packaging priority `Cursor > Claude Code > Codex`; Codex is **bridge only**.
6. Half-retire decisions need eval-metric evidence, not subjective rationale.
7. Failure in any self-dogfood step must be reported, never silently skipped.
8. Every round must drop the §8.2 6-evidence-file minimum.
9. Attach `core_goal_test_pack` and verify `C0 = 1.0` every round.
10. Declare `round_kind` in every `next_action_plan.yaml`.
11. Declare `token_tier {C7,C8,C9}` when any tier sub-axis is reported.
12. Cite real-data sample provenance when fixtures are declared.
13. Declare `packaging.health_smoke_check` when `live_backend: true`.
14. Cap every `description` at ≤ 1024 chars (`min(chars,bytes)`).
15. When `body_tokens > 5000`, cite ≥ 1 `references/<file>.md` that exists.

## What NOT To Do (Codex-Specific)

- DO NOT propose loading `.agents/skills/si-chip/SKILL.md` as a native
  Codex skill — that is §11.2 deferred and gated on v3_strict 2-round pass
  (current state: only v2_tightened achieved 9 consecutive times).
- DO NOT propose installing Si-Chip into Copilot / OpenCode / Gemini CLI
  — that is §11.1 forever-out (generic IDE compat layer) and §11.2 deferred.
- DO NOT propose marketplace publication — §11.1 forever-out item 1.
- DO NOT propose router-model training — §11.1 forever-out item 2.

## Quickstart (mirrors `.agents/skills/si-chip/SKILL.md` Dogfood Quickstart)

The 8 frozen steps in spec §8.1, written so Codex can dispatch them
without loading the SKILL body:

1. `profile`         → `basic_ability_profile.yaml`
2. `evaluate`        → `metrics_report.yaml` (MVP-8 + 37-key null placeholders)
3. `diagnose`        → bottleneck scan across R6's 7 dim / 37 sub-metrics
4. `improve`         → `next_action_plan.yaml` (+ `round_kind` declared)
5. `router-test`     → `router_floor_report.yaml` (8-cell MVP / 96-cell at v2+)
6. `half-retire-review` → `half_retire_decision.yaml`
7. `iterate`         → `iteration_delta_report.yaml` (≥ 1 efficiency axis at gate bucket)
8. `package-register` → sync `.agents/skills/si-chip/` to platforms in §7.2 priority order

Evidence path: `.local/dogfood/<DATE>/round_<N>/`.

## Provenance
- Bridge profile: `.codex/profiles/si-chip.md`
- Bridge instructions: this file
- Source-of-truth: `.agents/skills/si-chip/`
- Spec: `.rules/si-chip-spec.mdc` (frozen v0.5.0; v0.5.1 patch operationalizes Codex bridge install)
- Compiled rules: `AGENTS.md`
