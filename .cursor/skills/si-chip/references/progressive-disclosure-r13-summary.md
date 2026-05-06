# Progressive Disclosure Discipline — R13 Summary (Spec §24.3 Normative)

> Reader-friendly summary of the §24.3 Progressive Disclosure
> Discipline Normative sub-section (v0.4.4-rc1; promotion target
> v0.4.4). Authoritative sources: `.local/research/spec_v0.4.4-rc1.md`
> §24.3, the `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
> `docs/skill-anatomy.md` "progressive disclosure" upstream
> convention, and the existing Si-Chip `.agents/skills/si-chip/`
> 14-reference-doc layout + `scripts/count_tokens.py` packaging-gate
> infrastructure.

## Why this section exists

`addyosmani/agent-skills` v1.0.0 standardises a SKILL anatomy where
the SKILL.md body itself stays small (≤ ~5 KB) and long material
(worked examples, deep references, history, design rationale) lives
in `references/<topic>.md` files loaded *only when explicitly cited*.
Router-time decision pays only the EAGER (description) + a small
slice of ON-CALL (SKILL body) tokens; long reference content is
deferred to LAZY tier and only loaded when the agent actually needs
it.

Si-Chip has practised this *informally* since v0.1.0:

- 14 reference docs under `.agents/skills/si-chip/references/*.md`.
- `scripts/count_tokens.py` enforces `metadata_tokens ≤ 100` +
  `body_tokens ≤ 5000` as the §7.3 packaging gate. Both are flat
  across v1/v2/v3 (the spec deliberately does not tighten body past
  v3_strict — it expects authors to *change body shape* by splitting
  to references/, not to keep cramming).
- Si-Chip's own SKILL.md sits at ~4929 body tokens precisely because
  long material lives in references/* cited from the body.

What v0.4.4 changes is making the *informal practice* a *Normative
contract*: when a SKILL.md crosses the v3_strict body budget (5000
tokens), spec_validator BLOCKER 16 enforces that the body verbatim
cite at least one `references/<file>.md` AND that the cited file
exist on disk. Single-purpose: stop authors from inflating the
SKILL.md body past v3_strict without showing evidence that the long
material has been split out.

## Rule statement (§24.3.1)

When `body_tokens > 5000` (i.e. crosses §7.3 v3_strict body budget):

1. SKILL.md body MUST cite at least one `references/<file>.md` path
   verbatim (regex: `references/[\w\-]+\.md`).
2. Cited file MUST exist at `<skill_dir>/references/<file>.md` on
   disk (i.e. SKILL.md's own sibling `references/`, NOT a repo-root
   references/).

Both conditions checked by `tools/spec_validator.py::
check_body_budget_requires_references_split`. Either failing →
BLOCKER FAIL.

## Graduated nature: encouraged at v1, MUST at v3_strict

This rule is **graduated**: spec_validator only fails when body
crosses the *v3_strict* threshold (5000), but spec strongly
*encourages* the references-split pattern at lower gates as best
practice:

| Gate | body_tokens | spec_validator behaviour | Recommended author practice |
|---|---:|---|---|
| v1_baseline | ≤ 5000 | PASS | If body > 4000, *consider* splitting long sections to references/ |
| v2_tightened | ≤ 5000 | PASS | If body > 4500, *prefer* splitting; refactor before next round |
| v3_strict | ≤ 5000 + cite when over | FAIL when body > 5000 AND no references/ cite | Body should be < 4500; long material in references/ as a matter of routine |

The graduated nature is intentional: BLOCKER 16 is not "more strict
body budget"; it is "the body budget is the same number across all
three gates, but at v3_strict you also have to *prove* your long
material is split". Authors targeting v3_strict promotion should
practise references-split from v1 onward so v3_strict transition is
a no-behaviour-change formality.

## Reference doc anatomy (§24.3.2)

Each `references/<topic>.md` SHOULD (not MUST — BLOCKER 16 only
checks cite + existence) satisfy:

1. **First-paragraph 1-line summary** — first non-empty paragraph
   after H1 carries a 1-sentence summary. Used by reverse-lookup.
2. **Section with `<topic>` name** — at least one H2/H3 sub-section
   semantically aligned with filename. Makes cross-references
   deterministic.
3. **"Cross-references" tail block** — closing `## Cross-References`
   or `Cross-ref:` segment listing related sibling references.

The 14 existing Si-Chip references already follow this pattern
(canonical examples: `description-discipline-r13-summary.md`,
`standardized-sections-r13-summary.md`).

## Lazy manifest integration (§24.3.3)

The existing `templates/lazy_manifest.template.yaml` (v0.4.0 §18.5
Informative) is *promoted* in v0.4.4-rc1 to **Normative-conditional**:

- v1_baseline / v2_tightened: `.lazy-manifest` remains OPTIONAL.
- v3_strict + body crosses threshold: `.lazy-manifest` becomes
  Normative REQUIRED. Each split file SHOULD declare
  `lazy_load_class ∈ {eager, oncall, lazy}` consistent with §18:
  - `lazy` (default) — C9 LAZY tier; only loaded on explicit read.
  - `oncall` — C8; loaded at trigger-time (sparingly used; e.g.
    `recovery_harness.template.yaml` in §22.4).
  - `eager` — C7; almost never used for references/.

> **No new BLOCKER for lazy_manifest at v0.4.4**: schema promotion
> is documentation-only. Future spec versions may add a BLOCKER if
> §16.3 promotion-trigger conditions are met.

## BLOCKER 16 mechanics (§24.3.4)

`tools/spec_validator.py::check_body_budget_requires_references_split(repo_root, *, spec_text)`:

1. **Discovery** — walks `.agents/skills/`, `.cursor/skills/`,
   `.claude/skills/` for `SKILL.md` (sharing `_iter_skill_md_files`
   with BLOCKER 15).
2. **Body extraction** — reads file, splits frontmatter via
   `scripts/count_tokens.py::split_frontmatter` (importing live
   module to guarantee measurement-method consistency with §7.3
   gate; falls back to inline regex per "No Silent Failures" if
   import fails).
3. **Token counting** — `count_tokens.py::count_tokens(body)`
   (tiktoken-with-fallback; same module the gate uses, so BLOCKER 16
   and gate report identical numbers — binding consistency
   constraint of §24.3.4).
4. **Cite detection** — scans body for `references/<filename>.md`
   regex.
5. **File existence** — verifies `<skill_dir>/references/<filename>.md`
   on disk for each cited filename.
6. **Verdict per file**:
   - body ≤ 5000 → PASS;
   - body > 5000 + no cite → FAIL;
   - body > 5000 + cite + at least one cited file exists → PASS
     (missing cited refs reported informationally as
     `info_missing_cited_refs`, not FAIL — author may legitimately
     mention a future-planned references/* doc);
   - body > 5000 + cite + all cited files missing → FAIL.
7. **SKIP-as-PASS path 1** (spec backward compat) — `--spec` lacks
   §24.3 marker (`### 24.3` / `BODY_BUDGET_REQUIRES_REFERENCES_SPLIT`
   / `§24.3` not found). Keeps spec_v0.4.3-rc1.md / spec_v0.4.2-rc1.md
   / spec_v0.4.0.md / etc. passing 16/16 BLOCKERs (15 historical
   PASS + 1 SKIP-PASS).
8. **SKIP-as-PASS path 2** (pre-bootstrap repo) — no SKILL.md.
9. **SKIP-as-PASS path 3** (no body crosses) — every SKILL.md ≤ 5000.

Runs as the 16th BLOCKER, after `DESCRIPTION_CAP_1024`. Spec version
detection is plumbed via `detect_spec_version`.

## Measurement-consistency constraint

The §24.3.4 binding constraint that BLOCKER 16's body-token
measurement matches `scripts/count_tokens.py::count_tokens(body)` is
**not optional**: drift > 5% is a BLOCKER 16 implementation bug to
fix. Implementation imports the live `count_tokens` module instead
of reimplementing the heuristic. At self-test (Si-Chip's own
SKILL.md, body = 4929 tokens), BLOCKER 16 and `count_tokens.py
--body` report identical numbers.

## What does NOT trigger BLOCKER 16 (§24.3.5)

- §7.3 packaging gate enforcement continues via existing mechanisms
  (count_tokens.py + iteration_delta_report verification). BLOCKER 16
  only adds the references-split overlay when body crosses threshold.
- §4.1 three-gate progressive thresholds byte-identical to
  v0.1.0–v0.4.3-rc1.
- R6 sub-metric count remains 7 × 37 (frozen). Progressive disclosure
  is a packaging-discipline invariant, not a metric.
- `.lazy-manifest` BLOCKER-ization deferred — schema promotion is
  documentation-only at v0.4.4.
- Reference doc anatomy (§24.3.2) is SHOULD, not MUST. BLOCKER 16
  only checks cite + file-existence.

## §11 forever-out re-affirmation (§24.3.6)

Progressive-disclosure absorption from agent-skills v1.0.0 takes
ONLY the SKILL body / references/ split workmanship convention.
NOT absorbed: marketplace direction, plugin distribution surface,
per-skill installer architecture, Markdown-to-CLI tooling.

| §11.1 forever-out | Touched by §24.3? |
|---|---|
| Marketplace | NO — file-organization rule over local SKILL trees; no distribution surface. |
| Router model training | NO — body-token count + grep + filesystem check; no weights. |
| Generic IDE compat | NO — schema is ability-local Markdown body + sibling references/; §7.2 priority unchanged; BLOCKER 16 behaves identically across 3 mirrors. |
| Markdown-to-CLI | NO — BLOCKER 16 is deterministic length + grep + existence check, not a code generator. |

## Cross-References

| §24.3 subsection | Spec section | Upstream / sibling evidence |
|---|---|---|
| 24.3.1 body-budget trigger (graduated) | spec §24.3.1 | §7.3 packaging gate (frozen v0.1.0); agent-skills v1.0.0 ~5KB body convention |
| 24.3.2 reference doc anatomy | spec §24.3.2 | 14 existing Si-Chip references; agent-skills `references/<name>.md` pattern |
| 24.3.3 lazy manifest integration | spec §24.3.3 | `templates/lazy_manifest.template.yaml` (v0.4.0 §18.5); §18 token-tier |
| 24.3.4 BLOCKER 16 mechanics | spec §24.3.4 | `tools/spec_validator.py` + `scripts/count_tokens.py` binding consistency |
| 24.3.5 what does NOT trigger | spec §24.3.5 | §4.1 thresholds frozen; §7.3 budget unchanged |
| 24.3.6 forever-out re-affirm | spec §24.3.6 | spec §11.1 verbatim |

Cross-ref:
`references/description-discipline-r13-summary.md` (§24.1 sibling
Normative; same r13 cycle; description-cap is metadata-side
discipline, body-budget is body-side discipline);
`references/standardized-sections-r13-summary.md` (§24.2 sibling
Informative; same r13 cycle; layout-side discipline; together
§24.1 + §24.2 + §24.3 complete the §24 chapter: metadata-cap +
sections-convention + body-shape);
`references/token-tier-invariant-r12-summary.md` (§18 EAGER/ON-CALL/
LAZY tiers — references/* is the canonical LAZY tier surface);
`references/metrics-r6-summary.md` (§3.1 D2 C2 body_tokens — the
metric BLOCKER 16 over-reads at v3_strict).

Source spec section: Si-Chip v0.4.4-rc1 §24.3 (Normative); upstream
absorption from `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03)
`docs/skill-anatomy.md` progressive-disclosure convention. This
reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
