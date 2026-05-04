# Description Discipline — R13 Summary (Spec §24)

> Reader-friendly summary of the §24 Skill Hygiene Discipline
> Normative chapter (v0.4.2-rc1; promotion target v0.4.2). Authoritative
> sources: `.local/research/spec_v0.4.2-rc1.md` §24, the
> `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
> `docs/skill-anatomy.md` "description: a string up to 1024 characters"
> upstream convention, and the existing R6 routing-cost taxonomy
> (`references/metrics-r6-summary.md` §3.1 D6 R1/R2/R3/R4/R8).

## Why this section exists

`description` is the routing-time metadata surface that determines
whether the model selects this ability — it lives in EAGER tier
(C7 per §18.1 token-tier invariant), so every agent session pays
its token cost once at startup, regardless of whether the ability is
ultimately triggered. When ability authors stuff long workflow prose
into `description` (instead of letting the SKILL body / references
carry it), three failure modes compound:

1. **EAGER token bloat** — every `Cursor` / `Claude Code` / `Codex`
   session re-loads the bloated description; users pay tokens they
   never asked for. Empirically (chip-usage-helper Cycle 2 R14)
   description-shape changes alone moved C7 by hundreds of tokens.
2. **R4 near-miss FP rate climbs** — routing models latch onto
   narrative noise (sentences from the SKILL body that look like
   trigger keywords) and mis-fire on near-miss prompts.
3. **R8 description_competition_index pegs** — long descriptions
   keyword-collide with each other across the skill registry; routing
   becomes ambiguous; users have to disambiguate with explicit
   "use skill X" phrases that defeat the purpose of routing.

`addyosmani/agent-skills` v1.0.0 lifted a clean upstream convention
("description: a string up to 1024 characters") into the public
skill anatomy spec; Si-Chip's §24.1 absorbs the cap as a hard
machine-checkable invariant, wraps it with a CJK fairness
measurement, and pins the "what + when" semantic shape so the rule
is not just length-aware but also direction-aware.

## Rule statement (§24.1)

`SKILL.md` frontmatter `description` and `BasicAbility.description`
(OPTIONAL; falls back to `intent` when absent) must satisfy three
atomic invariants:

1. **Length cap** — `min(len(s), len(s.encode('utf-8'))) <= 1024`.
   Both character count and UTF-8 byte count are measured; the
   binding cap walks the *smaller* of the two (CJK fairness — see
   below). 1024 is a hard ceiling; the recommended sweet-spot
   (≤ 500 chars, mirroring Anthropic Claude Skills convention) is
   not enforced by spec_validator but is encouraged by §22 eval-pack
   curation guidance.
2. **Semantic shape** — must be "what + when": one or two sentences
   describing what the ability solves, followed by a phrase or
   keyword cluster describing when routing should trigger it. The
   step-by-step workflow / How-To / Dogfood Quickstart belongs in
   the SKILL body (ON-CALL tier C8) and references (LAZY tier C9),
   not in the description.
3. **Cross-tree mirror byte-identicality** — the source-of-truth
   `.agents/skills/<name>/SKILL.md` and the platform mirrors at
   `.cursor/skills/<name>/SKILL.md` + `.claude/skills/<name>/SKILL.md`
   must carry byte-identical `description` fields. Drift is caught
   by `tools/spec_validator.py` BLOCKER 15 (each file measured
   independently; max length checked against cap) and the existing
   §10 V3_drift_signal SHA-256 mirror invariant.

## Measurement convention (CJK fairness)

| Description | chars | bytes | binding |
|---|---:|---:|---:|
| `"x" * 1024` (ASCII) | 1024 | 1024 | 1024 PASS |
| `"x" * 1025` (ASCII) | 1025 | 1025 | 1025 FAIL |
| `"汉" * 600` (CJK)  |  600 | 1800 |  600 PASS |
| `"汉" * 1025` (CJK) | 1025 | 3075 | 1025 FAIL |
| `"汉" * 800` + `"x" * 200` (mixed) | 1000 | 2600 | 1000 PASS |

The smaller-of-the-two binding rule is the load-bearing fairness
guarantee. Without it, naive `len(s.encode('utf-8'))` measurement
would systematically penalize CJK / Arabic / Cyrillic abilities by
~3× compared to ASCII abilities (1 汉字 ≈ 3 UTF-8 bytes), even
though the routing model sees them as equivalent semantic units.
The rule is direct upstream-pin to addyosmani/agent-skills's `len(s)`
character convention but adds the byte-side floor so abilities that
genuinely abuse encoding (e.g. zero-width joiners, emoji modifier
sequences, RTL marks bloating bytes) still get caught.

## BLOCKER 15 mechanics (§24.1.1)

`tools/spec_validator.py::check_description_cap_1024(repo_root, *, spec_text)`:

1. **Discovery** — walks `.agents/skills/`, `.cursor/skills/`,
   `.claude/skills/` for `SKILL.md` files, plus
   `.local/dogfood/**/round_*/basic_ability_profile.yaml` (sharing
   `_iter_basic_ability_profiles` with BLOCKER 14).
2. **Extraction** — SKILL.md frontmatter `description:` line via the
   regex declared next to BLOCKER 15; BAP `basic_ability.description`
   if present; falls back to `basic_ability.intent` (the only
   currently REQUIRED narrative field on BAP).
3. **Measurement** — `min(len(s), len(s.encode('utf-8')))`.
4. **Verdict** — `binding_length > 1024 = FAIL`; findings include
   the file path, the chars / bytes / binding triplet, and which
   axis (chars or bytes) was the binding ceiling.
5. **SKIP-as-PASS path 1** (spec backward compat) — when the
   validated `--spec` lacks the §24 marker
   (`## 24.` / `### 24.1` / `DESCRIPTION_CAP_1024` / `§24.1` strings
   not found), the BLOCKER skips. This keeps `python tools/spec_validator.py`
   against `spec_v0.4.0.md` / `spec_v0.3.0.md` / `spec_v0.2.0.md`
   passing 15/15 BLOCKERs (14 historical PASS + 1 SKIP-PASS).
6. **SKIP-as-PASS path 2** (pre-bootstrap repo) — when no SKILL.md
   exists under any of the 3 skill trees AND no BAP exists under
   `.local/dogfood/`, the BLOCKER skips.

The check runs in `run_all`'s deterministic order as the 15th
BLOCKER, after `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`. Spec
version detection is plumbed through from the existing
`detect_spec_version` helper.

## What does NOT trigger BLOCKER 15 (§24.1.2)

To avoid false positives, the BLOCKER deliberately excludes these
informational surfaces:

- `BasicAbility.intent` when `BasicAbility.description` is **present**
  — `intent` is allowed to be a longer narrative paragraph (it's the
  "what does this solve in narrative form" field; `description` is
  the routing-time tagline). The `intent` fallback only kicks in when
  `description` is absent OR an empty string.
- `BasicAbility.core_goal.statement` (§14.1) — the core_goal contract
  is a different observability surface (functional invariant, not
  routing metadata) and has its own §14 cap (`minLength: 16`); §24
  does not double-cap it.
- `references/*.md` LAZY-tier reference docs, README files, and
  Markdown documentation under `docs/` — these are LAZY tier C9
  surfaces governed by §22.5 deterministic seeding and §10 persistence
  contract, not by the routing-time discipline of §24.
- `metrics_report.yaml.runner_provenance`,
  `iteration_delta_report.yaml.notes`, and other free-form narrative
  fields on round evidence — these are evidence body governed by §23
  method-tagged metrics, not routing surfaces.

## §11 forever-out re-affirmation (§24.1.3)

Description-discipline absorption from `addyosmani/agent-skills`
v1.0.0 takes ONLY the 1024-char cap and the "what + when" semantic
shape. It explicitly does NOT absorb that project's marketplace
direction, plugin distribution surface, or any Markdown-to-CLI
tooling. Si-Chip §11.1 four forever-out items remain byte-identical:

| §11.1 forever-out | Touched by §24? |
|---|---|
| Marketplace | NO — BLOCKER 15 is a length validator over local files; no distribution surface introduced. |
| Router model training | NO — cap is a string-length measurement; no weights touched. |
| Generic IDE compat | NO — schema is ability-local YAML frontmatter + BAP field; §7.2 platform priority unchanged. |
| Markdown-to-CLI | NO — BLOCKER 15 is a grep / length check, not a code generator. |

## Cross-References

| §24 subsection | Spec section | Upstream evidence |
|---|---|---|
| 24.1 length cap + "what+when" | spec §24.1 | `addyosmani/agent-skills` v1.0.0 `docs/skill-anatomy.md` |
| 24.1.1 BLOCKER 15 mechanics | spec §24.1.1 | spec §13.6.4 grace-period pattern + `tools/spec_validator.py` |
| 24.1.2 what doesn't trigger | spec §24.1.2 | §14.1 core_goal placement + §10 persistence contract |
| 24.1.3 forever-out re-affirm | spec §24.1.3 | spec §11.1 verbatim |

Cross-ref:
`references/metrics-r6-summary.md` (§3.1 D6 R1/R2/R3/R4/R8 routing
costs that bloated descriptions degrade);
`references/token-tier-invariant-r12-summary.md` (§18.1 EAGER tier
C7 — where `description` lives token-economically);
`references/eval-pack-curation-r12-summary.md` (§22 near-miss
curation discipline that interlocks with description-shape).

Source spec section: Si-Chip v0.4.2-rc1 §24 (Normative); upstream
absorption from `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
`docs/skill-anatomy.md` 1024-char description cap convention. This
reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
