# Lifecycle Category Taxonomy — R13 Summary (Spec §24.4 Informative)

> Reader-friendly summary of the §24.4 Lifecycle Category Taxonomy
> Informative sub-section (v0.4.5-rc1; promotion target v0.4.5).
> Authoritative sources: `.local/research/spec_v0.4.5-rc1.md` §24.4,
> the `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
> `using-agent-skills/SKILL.md` lifecycle-stage organisation of 21
> upstream skills, and the existing Si-Chip §16 multi-ability layout
> (Informative @ v0.3.0) plus `templates/basic_ability_profile.schema.yaml`
> `lifecycle` block.

## Why this section exists

`addyosmani/agent-skills` v1.0.0 organises its 21 published skills
into a 6-stage lifecycle taxonomy (`define / plan / build / verify /
review / ship`) plus a 7th `meta` category for self-referential
abilities — those that are *about other abilities* rather than
directly delivering user value. The upstream `using-agent-skills`
SKILL itself is `meta` (it teaches how to use other skills).

Si-Chip already has §16 Multi-Ability Dogfood Layout (Informative
@ v0.3.0) which defines `.local/dogfood/<DATE>/abilities/<ability-id>/`
as the directory shape for hosting multiple abilities side-by-side.
v0.4.5 absorbs the agent-skills lifecycle taxonomy as a normalized
**naming vocabulary** for that layout — without changing §16's
structural rules. Authors can either (a) declare `lifecycle.category`
in BAP and keep the existing flat `abilities/<id>/` layout, or (b)
adopt an additional category-prefix sub-directory
`abilities/<category>/<id>/`. Both are OPTIONAL; pre-v0.4.5 profiles
need no modification.

## Rule statement (§24.4.1 — schema field)

`templates/basic_ability_profile.schema.yaml` `lifecycle` block adds
one OPTIONAL field (sibling of `stage`, `last_reviewed_at`,
`next_review_at`):

```yaml
lifecycle:
  category:
    type: ["string", "null"]
    enum: [define, plan, build, verify, review, ship, meta, null]
    default: null
```

**Backward-compat**: default `null` = "uncategorised". All v0.4.0–v0.4.4
profiles (Round 1-22 Si-Chip + Round 1-27 chip-usage-helper) remain
valid with no edit needed.

## Category enum (§24.4.1)

The 7 enum values mirror the upstream agent-skills lifecycle stages
plus `meta` for self-referential abilities. One-line examples
relevant to Si-Chip context:

| Category | Si-Chip example |
|---|---|
| `define` | turning a fuzzy user request into a testable contract (kin to §14 core_goal authoring) |
| `plan` | drafting an architecture decision record or trade-off analysis before implementation |
| `build` | writing new module / SKILL.md / spec section / test fixture (implementation phase) |
| `verify` | running pytest / spec_validator / count_tokens — single-point verification |
| `review` | PR review, lint sweep, security audit, accessibility audit (whole-artifact pass) |
| `ship` | drafting CHANGELOG, triggering release pipeline, publishing announcement |
| `meta` | abilities *about other abilities* (orchestration / self-referential); Si-Chip itself fits here |

## Integration with §16 multi-ability layout (§24.4.2)

§24.4 supplements §16 — it does not replace any §16 rule.

| §16 sub-section | §24.4 increment | Notes |
|---|---|---|
| §16.1 layout `.local/dogfood/<DATE>/abilities/<ability-id>/` | OPTIONAL category sub-directory `.local/dogfood/<DATE>/abilities/<category>/<ability-id>/` | category sub-directory is OPTIONAL; existing flat layout still PASSes BLOCKER 1. |
| §16.2 migration (chip-usage-helper / 3rd ability) | category does not affect migration path | category is OPTIONAL field, decoupled from layout-shape BLOCKER decisions. |
| §16.3 promotion-to-Normative trigger | category is not counted toward §16.3 trigger | §16.3 byte-identical preserved; promotion criteria unchanged. |

> **Core insight**: §24.4 is a *vocabulary supplement* to §16; not a
> schema modification of §16. §16 decides "how to arrange directories";
> §24.4 decides "how to name them / how to classify abilities".

## Structural metadata, NOT a workflow gate (§24.4.4)

§24.4 is a **naming convention** (structural metadata), not a
workflow gate. This contrasts §24.4 cleanly with §24.3 / §14 / §15 /
§17 etc., which are workflow gates with binding enforcement.

| Aspect | §24.4 lifecycle.category | §24.3 / §14 / §15 / §17 (Normative gates) |
|---|---|---|
| Nature | Naming convention / structural metadata | Workflow contract / invariant |
| Affects §8 dogfood steps | NO — 8-step order + 6 evidence files byte-identical | YES — workflow behaviour depends (e.g. §14 C0 monitoring, §15 round_kind decides iteration_delta clause, §24.3 BLOCKER 16 forces cite) |
| spec_validator behaviour | Schema validator checks enum legality; no BLOCKER | BLOCKER 1 / 9-16 enforce |
| AGENTS.md hard rule | None | rules 9 / 10 / 11 / 12 / 13 / 14 / 15 each binding |
| Backward-compat path | Default null = uncategorised = PASS | SKIP-as-PASS path per §13.6.4 grace period |
| Author freedom | Total — author may opt out, spec_validator still PASS | Bound by spec MUST |

Specifically, §24.4 does NOT change:

- §8.1 8-step order (`profile → evaluate → diagnose → improve →
  router-test → half-retire-review → iterate → package-register`).
- §8.2 6-evidence-file set (`basic_ability_profile.yaml` /
  `metrics_report.yaml` / `router_floor_report.yaml` /
  `half_retire_decision.yaml` / `next_action_plan.yaml` /
  `iteration_delta_report.yaml`; `ship_prep` adds 7th
  `ship_decision.yaml` per §20.4 — also unchanged).
- §3 R6 7-dim / 37 sub-metric count (frozen; category is not an R6 metric).
- §6.1 8-axis value_vector (v0.4.0 break preserved).
- §14 C0 monitoring / §15 round_kind iteration_delta clause / §17
  hard rules / §24.3 BLOCKER 16 — all unchanged.

## Si-Chip's own lifecycle.category = meta

Si-Chip self-classifies as `meta` because Si-Chip is an ability that
*optimises other abilities*. It is not directly delivering a user-end
deliverable (it does not ship code to a customer-facing UI, does not
write a particular feature, does not run a release pipeline);
instead, every Si-Chip dogfood round examines and improves the
*workflow* by which other abilities are profiled, evaluated, routed,
and half-retired. This makes Si-Chip the canonical first-use case for
the `meta` enum value.

The categorisation is round-stable: Si-Chip's `lifecycle.category`
will remain `meta` across all future rounds unless its scope changes
fundamentally (e.g. if Si-Chip starts authoring a particular external
feature directly, then the category may shift to `build` for that
specific scope). Since §11 forever-out forbids Si-Chip from
becoming a marketplace / router-trainer / Markdown-to-CLI converter
/ generic IDE compat layer — none of which would change the `meta`
classification anyway — this slot is deliberately stable.

## Stage vs category (orthogonal)

`lifecycle.stage` (§2.2 enum: `exploratory → evaluated → productized
→ routed → governed`, plus `half_retired ↺` and `retired`) and
`lifecycle.category` (§24.4 enum: `define / plan / build / verify /
review / ship / meta`) are **orthogonal observability axes**:

- `stage` is the Si-Chip-internal maturity progression of a particular
  ability (how mature is it as a Si-Chip-evaluated artefact).
- `category` is the SDLC-external phase classification of an ability
  (which lifecycle phase does this ability serve in a typical
  software-delivery pipeline).

A `meta` ability (e.g. Si-Chip) can be in any §2.2 stage — Si-Chip
itself is currently `routed` (post-promotion since Round 19's v2
gate-eligibility). A `build` ability could be at `exploratory` stage
(brand-new) or at `governed` stage (mature-and-stable). The two axes
do not constrain each other; the spec does not require any specific
correlation.

## What does NOT trigger spec_validator FAIL (§24.4.5)

§24.4 deliberately introduces NO new spec_validator behaviour:

- No new BLOCKER (count remains 16/16; v0.4.4-rc1 already added the
  most recent BLOCKER 16).
- No new hard rule in AGENTS.md §13 (count remains 15; v0.4.4-rc1
  added the most recent rule 15).
- BAP doesn't have to declare `lifecycle.category` (default null).
- Multi-ability directory layout doesn't have to add category
  sub-folders (§16.1 byte-identical).
- `category` doesn't have to track `stage` evolution synchronously
  (orthogonal axes).
- `category` doesn't have to evolve in linear `define→plan→build→
  verify→review→ship` order; an ability can jump from `build`
  directly to `meta` if its scope is reclassified.
- chip-usage-helper Round 1-27 profiles need no migration; they
  continue to PASS BLOCKER 1 with `category: null` implied.

## §11 forever-out re-affirmation (§24.4.6)

Lifecycle-taxonomy absorption from agent-skills v1.0.0 takes
ONLY the 6-stage + meta naming taxonomy. NOT absorbed: marketplace
direction, plugin distribution surface, per-skill installer
architecture, Markdown-to-CLI tooling, generic IDE compat surface.

| §11.1 forever-out | Touched by §24.4? |
|---|---|
| Marketplace | NO — `category` is a single OPTIONAL enum field on the BAP schema; no distribution surface, no SKILL package index, no cross-ability discovery API. |
| Router model training | NO — category is a deterministic enum value; router-test (§5) behaviour byte-identical preserved (does not branch on `build` vs `meta`); §5.2 unchanged. |
| Generic IDE compat | NO — `category` is BAP schema-internal; §7.2 priority (Cursor > Claude Code > Codex bridge-only) unchanged; schema validator behaves identically across all 3 mirrors. |
| Markdown-to-CLI | NO — §24.4 is a schema increment + Informative naming convention; not a code generator; author hand-edits the BAP `lifecycle.category` field. |

## Cross-References

| §24.4 sub-section | Spec section | Upstream / sibling evidence |
|---|---|---|
| 24.4.1 enum + schema field | spec §24.4.1 | agent-skills v1.0.0 6-stage + meta taxonomy; OPTIONAL field default null |
| 24.4.2 cross-ref to §16 multi-ability layout | spec §24.4.2 | §16.1 / §16.2 / §16.3 byte-identical preserved |
| 24.4.3 schema sketch + backward-compat | spec §24.4.3 | `templates/basic_ability_profile.schema.yaml` `lifecycle` block additive |
| 24.4.4 structural metadata, NOT a workflow gate | spec §24.4.4 | contrast with §24.3 / §14 / §15 / §17 Normative gates |
| 24.4.5 what does NOT trigger | spec §24.4.5 | no BLOCKER, no hard rule, no §16 layout shape change |
| 24.4.6 forever-out re-affirm | spec §24.4.6 | spec §11.1 verbatim |

Cross-ref:
`references/multi-ability-layout-r11-summary.md` (§16 sibling
Informative; §24.4 is the naming-vocabulary supplement to §16's
directory-layout structural rule);
`references/description-discipline-r13-summary.md` (§24.1 sibling
Normative; description is metadata-side of §24, lifecycle.category
is BAP-schema-side; together they outline the §24 chapter's full
metadata + sections + body + classification surface);
`references/standardized-sections-r13-summary.md` (§24.2 sibling
Informative; both §24.2 and §24.4 are Informative naming /
sections conventions that don't trigger BLOCKERs);
`references/progressive-disclosure-r13-summary.md` (§24.3 sibling
Normative; body-shape rule; complementary to §24.4 BAP-shape rule);
`references/basic-ability-profile.md` (BAP schema reader walkthrough
— `lifecycle` block now hosts the new OPTIONAL `category` field).

Source spec section: Si-Chip v0.4.5-rc1 §24.4 (Informative); upstream
absorption from `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
`using-agent-skills/SKILL.md` lifecycle taxonomy. This reference is
loaded on demand and is excluded from the §7.3 SKILL.md body budget.
