# Si-Chip Profile (Codex Bridge)

> Si-Chip v0.5.1 — Codex bridge profile.
> Binding contract lives in `AGENTS.md` (repo root, compiled from
> `.rules/si-chip-spec.mdc`). This file is metadata for Codex's profile
> loader; do **not** treat it as a SKILL.md replacement.

## Identity
- Name: `si-chip`
- Role: Persistent BasicAbility optimization factory.
- Source-of-truth: `.agents/skills/si-chip/`.
- Spec: `.rules/si-chip-spec.mdc` (frozen at v0.5.0; v0.5.1 patch operationalizes Codex bridge install).

## Binding Contract

Codex MUST consume this skill via the **bridge** mechanism per spec §7.2:
- `AGENTS.md` is the canonical hard-rule corpus (15 rules at v0.5.1).
- `.codex/instructions/si-chip-bridge.md` is the per-session bridge handoff.
- Codex does **NOT** load `SKILL.md` directly (§11.2 deferred — v0.x bridge-only).

## Capabilities Surfaced
- Profile / evaluate / diagnose / improve / router-test / half-retire / iterate / package-register (the §8.1 frozen 8-step loop).
- C0 core_goal invariant verification (§14.3).
- Round-kind + ship-prep evidence (§15 / §20).
- Token-tier decomposition + lazy-manifest (§18).
- Real-data provenance + health-smoke (§19 / §21).

## Forever-Out Re-Affirmation (§11.1)
Even when invoked from Codex, Si-Chip rejects:
1. Skill / Plugin marketplace surfaces.
2. Router model training (any size; any type).
3. Generic IDE / Agent runtime compat layers.
4. Markdown-to-CLI auto converters.

## Loading Hint
Codex profile loader: load `.codex/instructions/si-chip-bridge.md` after
this profile to receive the per-session handoff (rule preamble + the
8-step loop quickstart). All Normative content remains in `AGENTS.md`.
