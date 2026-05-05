# Meta-Routing Pattern — R13 Summary (Spec §24.5 Informative)

> Reader-friendly summary of the §24.5 Meta-Routing Pattern Informative
> sub-section (v0.4.6-rc1; promotion target v0.4.6).
> Authoritative sources: `.local/research/spec_v0.4.6-rc1.md` §24.5,
> the `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
> `using-agent-skills/SKILL.md` itself, and Si-Chip's own SKILL.md
> as the reference implementation across Round 1-23.

## Why this section exists

`addyosmani/agent-skills` v1.0.0 ships a special skill called
`using-agent-skills` that does NOT solve a particular task but
instead **routes agents to other skills**. Its body lists
"If the user wants X, suggest skill Y" mappings; the description
tells the host LLM when to load it. The skill is plain Markdown —
no learned model, no classifier, no online update — and it works
because routing decisions are made by the host LLM reading the
description plus the When-To-Trigger / When-NOT-To-Trigger
enumeration.

This is the same workmanship Si-Chip already practices: Si-Chip is
itself a "meta ability" (it routes agents to dogfood / half-retire
/ router-test workflows rather than doing one specific user task).
v0.4.6 makes the implicit pattern explicit so future ability
authors can grep `meta-routing-pattern` and find a documented
recipe.

## §11 forever-out: re-affirmation up front

§11.1 forbids router-model training in perpetuity (§5.2 lists the
prohibited surfaces verbatim). §24.5 documents an existing
description-driven pattern; it adds NO router-model training,
NO classifier, NO online learning, NO fine-tuning. The patch is
pattern documentation only.

| §11.1 forever-out | Touched by §24.5? |
|---|---|
| Marketplace | NO — pattern documentation only. |
| Router-model training | NO — §24.5.2 forbids learned models / classifiers / online weight updates / fine-tuning. Description-driven only. |
| Generic IDE compat | NO — meta abilities are plain Markdown SKILL.md across all 3 mirror trees. |
| Markdown-to-CLI | NO — author hand-edits description + When-To-Trigger lists. |

## Five atomic features of a meta ability (§24.5.1)

A `BasicAbility` qualifies as a meta ability when it satisfies all
five features in combination:

1. **Intent shape `route to ...`** — BAP `intent` describes which
   abilities or sub-workflows this ability points to, not a
   user-facing deliverable.
2. **Description "what + when"** — frontmatter `description` ≤ 1024
   chars (§24.1); "what" lobe describes the routing scope, "when"
   lobe describes trigger context for the meta ability itself.
3. **`When To Trigger` ≥ 5 mappings** — explicit Markdown section
   listing five or more `(user-text-pattern → target-ability-id)`
   pairs, hand-written and grep-friendly.
4. **`When NOT To Trigger` ≥ 3 negative examples** — explicit
   negative-space section so R3 trigger_F1 + R4 near_miss_FP_rate
   don't silently degrade.
5. **Description-only iteration** — when §5 router-test reports R3
   below the gate threshold, the *only* permitted fix is editing
   the description / When-To-Trigger / When-NOT-To-Trigger text
   and re-running router-test. No model training. Ever.

## Implementation constraint (§24.5.2 — STRICT)

Meta abilities **MUST** be implemented via plain `description` +
hand-written enumeration tables, iterated through text edits only.

The following implementations are forever-out per §5.2 + §11.1:

| Forbidden implementation | Spec anchor |
|---|---|
| Learned router models (classifier / ranker / retrieval model) | §5.2 #1; §11.1 item 2 |
| External classifiers (out-of-process service) | §5.2 #3; §11.1 item 2 |
| Online weight updates (runtime parameter adjustment) | §5.2 #2; §11.1 item 2 |
| Training or fine-tuning (any gradient update) | §5.2 #1; §11.1 item 2 |
| Embedding routers when *trained* or *weight-updated* | §5.2; deterministic baseline retrieval over descriptions remains allowed per §5.1 / §5.3 #2 |

The only allowed implementation surface is the pre-existing
description-optimization workflow already authorised under
§5.1 / §5.3:

1. Plain string `description` (≤ 1024 chars; "what + when").
2. `When To Trigger` enumeration (Markdown list / table).
3. `When NOT To Trigger` enumeration.
4. Description text-edit iteration (per Anthropic
   `skill-creator/improve_description.py` workflow; §5.3 #3).
5. Static / semantic retrieval over the description as a *baseline*
   that is *used*, never *trained* (§5.1 / §5.3 #2).

> **Author intuition pump**: any time you catch yourself writing
> "score = ...", "learn the routing weights", "train a small
> classifier", "fine-tune", "online-update the parameters", or
> "build an embedding index from descriptions and update it
> dynamically" — STOP. That implementation is §11.1 forbidden.
> Return to text edits + enumeration + §5 router-test + iterate.

## Step-by-step recipe

To author a new meta ability:

1. **Define the meta intent** — `intent: "route agents to
   <ability-X> when <context-Y>"`. Don't write `intent: "do
   <task-Z>"`; that's a regular ability.
2. **Write 5–10 `When To Trigger` examples** —
   `(user-text-pattern → ability-id)` mappings, covering typical
   user phrasings the host LLM should detect.
3. **Write 5–10 `When NOT To Trigger` examples** — negative
   examples that look superficially like triggers but should not
   activate. Most important step for precision.
4. **Run §5 router-test 8-cell MVP** — emit
   `router_floor_report.yaml` with R3 + R4 readings.
5. **Iterate description text only** — if R3 < gate (v1 0.80 / v2
   0.85 / v3 0.90) or R4 > gate (v1 0.15 / v2 0.10 / v3 0.05),
   edit description / trigger lists and re-run. Never train.

## Categorization cross-reference (§24.5.3)

A meta ability *typically* declares `lifecycle.category: meta`
(per §24.4 7-value enum) but doing so is OPTIONAL. §24.5 is a
workmanship pattern; §24.4 is a BAP schema field. Author may
adopt one without the other; spec_validator passes 16/16 either
way.

## Quality gates: same R6 / §4 thresholds (§24.5.4)

Meta abilities are NOT exempt from §3 R6 7-dim / 37 sub-metric or
§4.1 three-gate thresholds. **R3 trigger_F1 is especially
important** — a mis-routing meta ability is *worse* than no meta
ability because it sends agents down wrong paths and pollutes
near-miss curation. Gate values byte-identical: v1 ≥ 0.80, v2 ≥
0.85, v3 ≥ 0.90. §5 router-test 8-cell / 96-cell unchanged.
§14 core_goal C0 = 1.0 unchanged. No special treatment.

## Si-Chip itself as canonical reference impl (§24.5.5)

Si-Chip's own SKILL.md satisfies all five §24.5.1 features:

| §24.5.1 feature | Si-Chip self-impl |
|---|---|
| 1. Intent `route to ...` | BAP `intent` routes agents to the 8-step dogfood workflow, not a user-end deliverable. |
| 2. Description "what + when" | frontmatter `description` ≤ 1024 chars; `when_to_use` describes routing context. |
| 3. `When To Trigger` ≥ 5 | SKILL.md ## When To Trigger lists 14+ mappings. |
| 4. `When NOT To Trigger` ≥ 3 | SKILL.md ## When NOT To Trigger lists 6 negative examples. |
| 5. Description-only iteration | Round 1 → 23 evolved exclusively through SKILL.md / description / trigger-list text edits. ZERO router-model / classifier / online learning ever introduced. |

This makes Si-Chip the canonical first-use case for the §24.5
pattern. Future meta-ability authors can use Si-Chip's SKILL.md
as a reference template.

## What §24.5 does NOT trigger

- No new spec_validator BLOCKER (count remains 16/16).
- No new AGENTS.md hard rule (count remains 15).
- No new BAP schema field — pattern documentation, not a schema
  increment (contrast with §24.4 which added `lifecycle.category`).
- No `$schema_version` bump.
- No backward-compat work needed — every pre-v0.4.6 BAP profile
  still PASSes 16/16 BLOCKERs without modification.
- No router-test format / cell-count change (8 / 96 unchanged).
- No special meta-ability threshold relaxation in §3 / §4 / §5.

## §11 forever-out re-affirmation (§24.5.6)

Repeated for emphasis: §24.5 documents *how to write* a meta
ability; it does **NOT** introduce any router-model training,
classifier, online learning, or fine-tuning pathway. §5.2
byte-identical preserved. §11.1 four forever-out items
byte-identical preserved.

If a future PR proposes "but what if we trained a tiny router
classifier on the descriptions?" — reject on sight. Same for
"embed all descriptions and serve a kNN service that re-trains
on usage" — reject on sight. The pattern is description-driven
only, forever.

## Cross-References

| §24.5 sub-section | Spec section | Sibling evidence |
|---|---|---|
| 24.5.1 five atomic features | spec §24.5.1 | Si-Chip SKILL.md ## When To Trigger / ## When NOT To Trigger |
| 24.5.2 implementation constraint | spec §24.5.2 | §5.2 prohibition list byte-identical |
| 24.5.3 categorization cross-ref | spec §24.5.3 | §24.4 lifecycle.category; OPTIONAL `meta` value |
| 24.5.4 quality gates | spec §24.5.4 | §3 R6 / §4 three-gate table byte-identical |
| 24.5.5 Si-Chip canonical impl | spec §24.5.5 | `.agents/skills/si-chip/SKILL.md` Round 1-23 |
| 24.5.6 forever-out re-affirm | spec §24.5.6 | spec §11.1 / §5.2 verbatim |

Cross-ref:
`references/router-test-r8-summary.md` (§5 router paradigm — meta
abilities run the same 8-cell / 96-cell harness);
`references/description-discipline-r13-summary.md` (§24.1 — cap ≤
1024 chars under `min(chars, bytes)`);
`references/standardized-sections-r13-summary.md` (§24.2 — meta
abilities benefit especially from Common Rationalizations / Red
Flags / Verification mnemonics);
`references/lifecycle-category-r13-summary.md` (§24.4 — meta
abilities typically declare `lifecycle.category: meta`).

Source spec section: Si-Chip v0.4.6-rc1 §24.5 (Informative);
upstream absorption from `addyosmani/agent-skills` v1.0.0
(push @ 2026-05-03) `using-agent-skills/SKILL.md` itself. This
reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
