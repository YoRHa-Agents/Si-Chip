<!--
template_version: 0.4.3-rc1
informative: true
purpose: standardized recommended sections for any Si-Chip SKILL.md (advisory; absorbed from addyosmani/agent-skills v1.0.0 — Common Rationalizations + Red Flags + Verification three-section convention)
spec_section: §24.2
status: Informative (NOT Normative; spec_validator does NOT introduce a new BLOCKER for this template)
sibling_template: templates/eval_pack_qa_checklist.md (same Informative-Markdown class)
-->

# Standardized SKILL.md Sections (Si-Chip §24.2 Informative)

> Recommended skeleton for the three end-of-SKILL sections any Si-Chip-instrumented `SKILL.md` SHOULD adopt: `## Common Rationalizations`, `## Red Flags`, `## Verification`. Place after `## When NOT To Trigger`. All three are **Informative** — author MAY skip any or all; spec_validator continues to PASS without them.

## Why these three sections

Three recurring failure modes the upstream `addyosmani/agent-skills` v1.0.0 SKILL files solve with this end-of-body trio:

1. **Rationalization debt** — without a public list, reviewers cannot grep for "is someone about to take this shortcut?".
2. **Anti-pattern detection latency** — without Red Flags, anti-patterns surface only in hindsight.
3. **Audit-trail handoff** — without Verification + per-item Evidence path, "ability is done" is verbal-only.

## Section 1 — Common Rationalizations

Markdown table mapping rejected shortcuts → spec / BLOCKER anchors. ≥3 rows recommended.

```markdown
## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll skip dogfood this round" | §8.1 step 8 mandates package-register; missing round = ship-blocker per §8.3. |
| "core_goal regression is just noise" | §14.3.2 strict no-regression: any C0 < prior = round FAILURE; trigger §14.4 REVERT-only. |
| "spec_validator BLOCKER too strict" | BLOCKERs map 1:1 to AGENTS.md hard rules 9-14; bypass = workspace policy violation. |
```

## Section 2 — Red Flags

Bullet list of observable anti-patterns. Each SHOULD cite a machine signal (grep / BLOCKER / round artefact field). ≥5 items recommended.

```markdown
## Red Flags

- `C0_core_goal_pass_rate < 1.0` silently overlooked (grep `iteration_delta_report.yaml.core_goal_check.c0_pass_rate_this_round`).
- `round_kind` not declared in `next_action_plan.yaml` (spec_validator catches in v0.4.0+ mode; hard rule 10).
- `description_length > 1024` bypassed (BLOCKER 15 catches at v0.4.2-rc1+; hard rule 14).
- `iteration_delta_report.verdict.pass = true` set without an axis at the gate bucket (§15.2 strict clause for code_change).
- `T2_pass_k _method=real_llm` claimed while cache dir absent (§22.6 + §23.1; fabricated provenance is integrity hazard).
```

## Section 3 — Verification

Checkbox list with per-item `- Evidence path:` sub-bullet. ≥5 items recommended.

```markdown
## Verification

- [ ] All 6 (or 7 for `round_kind = ship_prep`) evidence files written under the round directory.
  - Evidence path: `.local/dogfood/<DATE>/round_<N>/{basic_ability_profile,metrics_report,router_floor_report,half_retire_decision,next_action_plan,iteration_delta_report}.yaml`
- [ ] `python tools/spec_validator.py --json` exits 0 with verdict PASS.
  - Evidence path: `.local/dogfood/<DATE>/round_<N>/raw/spec_validator.json`
- [ ] `pytest tools/test_spec_validator.py -q` all green; new-BLOCKER tests pass when round adds a BLOCKER.
  - Evidence path: `.local/dogfood/<DATE>/round_<N>/raw/pytest_full.txt`
- [ ] `count_tokens.py` reports `metadata ≤ 100` and `body ≤ 5000`.
  - Evidence path: `.local/dogfood/<DATE>/round_<N>/raw/count_tokens.json`
- [ ] `C0 = 1.0` and `c0_no_regression: true` in this round's `iteration_delta_report.yaml.core_goal_check`.
  - Evidence path: `.local/dogfood/<DATE>/round_<N>/iteration_delta_report.yaml`
```

## How to adopt

1. Open ability's source-of-truth `.agents/skills/<id>/SKILL.md`.
2. After `## When NOT To Trigger`, copy the three skeletons above.
3. Replace example rows / items with ability-specific ones (3-15 rows / items per section).
4. Sync mirrors at `.cursor/skills/<id>/SKILL.md` + `.claude/skills/<id>/SKILL.md` (§7.2 + §10).
5. Re-run `count_tokens.py` + `spec_validator.py --json`; both must continue to PASS.

## Cross-references

- spec §24.2 — full Informative section text
- spec §24.1 — Normative description-cap rule (BLOCKER 15) — same §24 chapter
- spec §22.3 — sibling Informative template `templates/eval_pack_qa_checklist.md`
- spec §14 / §15 / §17 — C0 / round_kind / hard-rule anchors §24.2 SHOULD cite
- spec §11.1 — forever-out re-affirmation; §24.2 introduces NO marketplace, NO router-model training, NO Markdown-to-CLI converter, NO generic IDE compat
- `.agents/skills/si-chip/references/standardized-sections-r13-summary.md` — reader-friendly summary

## Provenance

- Authored: 2026-05-05 (Si-Chip v0.4.3-rc1 Patch 2)
- Spec version: v0.4.3-rc1
- Source: addyosmani/agent-skills v1.0.0 (push @ 2026-05-03) `skills/test-driven-development/SKILL.md` + `skills/code-review-and-quality/SKILL.md` end-of-body three-section convention

---

> **Reminder**: Informative — spec_validator does NOT FAIL when sections are omitted. Underlying integrity guarantees come from §14 core_goal + §15 round_kind + §17 hard rules + BLOCKERs 1-15.
