# Standardized SKILL.md Sections — R13 Summary (Spec §24.2 Informative)

> Reader-friendly summary of the §24.2 Standardized SKILL.md Sections
> Informative sub-section (v0.4.3-rc1; promotion target v0.4.3).
> Sources: `.local/research/spec_v0.4.3-rc1.md` §24.2 and the
> `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
> `skills/test-driven-development/SKILL.md` +
> `skills/code-review-and-quality/SKILL.md` end-of-body three-section
> convention.

## Why this section exists (and why it is **Informative not Normative**)

`addyosmani/agent-skills` v1.0.0's upstream SKILL files share a fixed
end-of-body trio (`## Common Rationalizations`, `## Red Flags`,
`## Verification`) that hardens the human-readable surface of SKILL.md
against three failure modes Si-Chip's existing Normative machinery
does NOT directly address:

1. **Rationalization debt** — without a public list of past-rejected
   shortcuts, agents cannot grep for "is someone about to take this
   shortcut?".
2. **Anti-pattern detection latency** — without Red Flags, anti-
   patterns surface only in hindsight.
3. **Audit-trail handoff** — without Verification + per-item Evidence
   path, "ability is done" is verbal-only.

**§24.2 is deliberately Informative, not Normative.** The three
failure modes can ALSO be addressed by Si-Chip's existing Normative
machinery (BLOCKERs 1-15 + C0 invariant + round_kind discipline +
spec_validator). The three sections do not introduce a NEW invariant;
they amplify the audit surface area of EXISTING invariants in human-
readable form. Authors who already write strong `next_action_plan.yaml`
+ `iteration_delta_report.yaml` get full §14 / §15 / §17 coverage
without adopting §24.2.

## Cross-tree positioning vs §24.1

§24.2 sits inside the §24 Skill Hygiene Discipline chapter alongside
§24.1 (Description Discipline). They are at OPPOSITE ends of the
Normative-Informative spectrum:

| Aspect | §24.1 Description Discipline | §24.2 Standardized Sections |
|---|---|---|
| Status | **Normative** | **Informative** |
| spec_validator BLOCKER | BLOCKER 15 `DESCRIPTION_CAP_1024` | none introduced (count stays 15) |
| AGENTS.md hard rule | hard rule 14 (added at v0.4.2) | none introduced (count stays 14 at v0.4.3) |
| If author ignores | spec_validator FAILs | spec_validator continues to PASS |
| Source | addyosmani/agent-skills v1.0.0 `docs/skill-anatomy.md` 1024-char cap | addyosmani/agent-skills v1.0.0 SKILL files end-of-body trio |
| r13 cycle | description-discipline-r13-summary.md (Patch 1) | standardized-sections-r13-summary.md (Patch 2; this file) |

## The three recommended sections (§24.2.1)

| Section | Structure | Min items | Recommended cross-refs |
|---|---|---:|---|
| `## Common Rationalizations` | Markdown table `\| Rationalization \| Reality \|` | 3 | §8.1 step 8, §14.3, §15.2, §17.1-§17.7 (each Reality lobe SHOULD cite a spec clause / BLOCKER anchor) |
| `## Red Flags` | bullet list of observable anti-patterns | 5 | C0 (§14.3), round_kind (§15), BLOCKERs 9-15 (each flag SHOULD be greppable / verifiable against a machine signal) |
| `## Verification` | checkbox list `- [ ]` + per-item `- Evidence path:` sub-bullet | 5 | §8.2 6 evidence files, §20.4 7th evidence, `tools/spec_validator.py`, `count_tokens.py` |

Place after `## When NOT To Trigger`. The fixed order (Rationalizations
→ Red Flags → Verification) is recommended for grep-friendly audit,
not required.

## Interlock with existing Si-Chip Normative invariants (§24.2.2)

§24.2 works **with** (not against / not over) the existing Si-Chip
Normative machinery:

1. **C0 + round_kind + Verification** — when adopted, `## Verification`
   SHOULD cite C0 = 1.0 (§14.3) and round_kind declaration (§15.1).
   This makes the author-side checklist a mirror of what
   spec_validator already enforces. If §24.2 is omitted, the
   Normative invariants apply unchanged.
2. **BLOCKER cross-references** — Red Flag items SHOULD cite a
   spec_validator BLOCKER number (1-15) so reviewers can grep the
   BLOCKER for the machine-side enforcement contract.
3. **Common Rationalizations as round_kind defense** — each row
   SHOULD reference a spec clause that the rationalization would
   violate, making past-rejected shortcuts a public artifact.

## What §24.2 does NOT trigger (§24.2.5)

- **No new BLOCKER**: count stays at 15 at v0.4.3-rc1.
- **No new hard rule**: count stays at 14.
- **No required header names**: while recommended headers are
  `## Common Rationalizations` / `## Red Flags` / `## Verification`,
  authors MAY use ability-specific alternatives.
- **No required content / row count**: ≥3 / ≥5 / ≥5 minimums in
  §24.2.1 are recommendations, not contracts.
- **No required ordering**: recommended order is for grep
  consistency; authors MAY reorder.
- **No mirror byte-identicality**: unlike §24.1 (BLOCKER 15), §24.2
  sections may diverge between source-of-truth and platform mirrors
  (in practice §7.2 + §10 sync workflow keeps them aligned).

## §11 forever-out re-affirmation (§24.2.6)

`addyosmani/agent-skills` v1.0.0 absorption takes ONLY the SKILL.md
end-of-body three-section convention. Si-Chip §11.1 four forever-out
items remain byte-identical:

| §11.1 forever-out | Touched by §24.2? |
|---|---|
| Marketplace | NO — Markdown editing convention; no distribution surface. |
| Router model training | NO — three sections are human-readable text; no weights touched. |
| Generic IDE compat | NO — plain Markdown body; §7.2 platform priority unchanged. |
| Markdown-to-CLI | NO — sections are hand-authored; no code generator. |

## Reference implementation in Si-Chip's own SKILL.md

`.agents/skills/si-chip/SKILL.md` adopts the three sections from
v0.4.3-rc1 onward as a self-dogfood demonstration. The sections appear
after `## When NOT To Trigger` with Si-Chip-specific content (not
generic best-practice prose):

- **Common Rationalizations** (4 rows): "Skip dogfood",
  "C0 regression is noise", "BLOCKER too strict",
  "Ship without iteration_delta proof". Reality lobes cite §8.1
  step 8, §14.3.2, §15.2 + hard rules 9-14.
- **Red Flags** (5 items): all greppable against round artefact
  fields or BLOCKER outputs (C0, round_kind, BLOCKER 15,
  iteration_delta verdict, real-LLM cache).
- **Verification** (5 checkboxes + per-item Evidence path): §8.2 6
  evidence files, spec_validator PASS, pytest PASS, count_tokens
  budget, C0 monotonicity.

The three sections are body content (not metadata) and contribute
to the §7.3 SKILL.md body budget. v0.4.3-rc1 absorbs them within
budget by keeping example content skeleton-minimal; detailed
examples live in `templates/skill_md_sections.template.md` and this
reference doc.

## Cross-References

| §24.2 subsection | Spec section | Notes |
|---|---|---|
| 24.2.1 Recommended section set | spec §24.2.1 | upstream addyosmani/agent-skills v1.0.0 SKILL trio |
| 24.2.2 Cross-refs to existing invariants | spec §24.2.2 | interlock with §14 + §15 + §17 |
| 24.2.3 Template reference | spec §24.2.3 | `templates/skill_md_sections.template.md` (sibling of `templates/eval_pack_qa_checklist.md`) |
| 24.2.4 Reference implementation | spec §24.2.4 | this Si-Chip self-dogfood |
| 24.2.5 What does NOT trigger | spec §24.2.5 | contrast with §24.1 Normative |
| 24.2.6 Forever-out re-affirm | spec §24.2.6 | spec §11.1 verbatim |

Cross-ref:
`references/description-discipline-r13-summary.md` (§24.1 sibling
Normative add-on; same r13 cycle);
`references/round-kind-r11-summary.md` (§15 round_kind);
`references/core-goal-invariant-r11-summary.md` (§14 C0 = 1.0);
`templates/eval_pack_qa_checklist.md` (sibling Informative-Markdown
template at §22.3).

Source spec section: Si-Chip v0.4.3-rc1 §24.2 (**Informative**);
upstream absorption from `addyosmani/agent-skills` v1.0.0 (push @
2026-05-03) `skills/test-driven-development/SKILL.md` and
`skills/code-review-and-quality/SKILL.md` end-of-body three-section
convention. This reference is loaded on demand and is excluded from
the §7.3 SKILL.md body budget.
