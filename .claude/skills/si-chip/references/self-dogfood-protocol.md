# Self-Dogfood Protocol — Reader Reference

Si-Chip must prove itself by optimising itself before it guides anything else.
This reference distills the frozen dogfood protocol in Si-Chip v0.1.0 §8 plus
the persistence requirements from R10. A single execution is not a ship event;
multi-round evidence is mandatory.

## 8 Steps (frozen order)

The following order is normative. Steps run strictly sequentially within a
round; parallelising or reordering is a spec violation.

1. `profile` — generate Si-Chip's own `BasicAbilityProfile` (see
   `basic-ability-profile.md`), populating MVP-8 metrics and leaving the rest
   of the 28 sub-metric keys explicitly `null`.
2. `evaluate` — run the no-ability baseline and the with-ability suite, then
   emit `metrics_report` covering MVP-8 plus 28-key placeholders.
3. `diagnose` — locate bottlenecks across R6's 7 dimensions / 28 sub-metrics
   (see `metrics-r6-summary.md`). Record which sub-metric pushed which gate.
4. `improve` — author and execute the next round's `next_action_plan`, with
   concrete edits that target the diagnosed bottlenecks.
5. `router-test` — run the §5.3 router harness, 8-cell MVP minimum or 96-cell
   Full (see `router-test-r8-summary.md`), and emit `router_floor_report`.
6. `half-retire-review` — compute the 7-axis value vector per
   `half-retirement-r9-summary.md` and commit `half_retire_decision`.
7. `iterate` — compare with the previous round and emit
   `iteration_delta_report`. At least one efficiency axis must show a
   positive delta meeting the current gate bucket.
8. `package-register` — sync the source of truth
   (`.agents/skills/si-chip/`) to platform targets in the Cursor → Claude
   Code → Codex order; never write a platform target by hand.

Any step that fails must surface the failure explicitly in the round's
evidence files (see below); silent skipping violates both this protocol and
the workspace "No Silent Failures" rule.

## 6 Evidence Files per Round

Every round must drop the following six artefacts. Missing one file makes the
round unship-able regardless of metric quality.

| # | File | Format | Produced by step |
|---|---|---|---|
| 1 | `basic_ability_profile.yaml` | YAML, schema-validated | 1 |
| 2 | `metrics_report.yaml` (or `.json`) | MVP-8 + 28-key placeholders | 2, 3 |
| 3 | `router_floor_report.yaml` | Per-cell metrics + chosen `router_floor` | 5 |
| 4 | `half_retire_decision.yaml` | Value vector + decision + review triggers | 6 |
| 5 | `next_action_plan.yaml` | Ordered plan for the next round | 4 |
| 6 | `iteration_delta_report.yaml` | Deltas vs the previous round | 7 |

All six are machine-readable. Validators live in
`devolaflow.template_engine.validator`; their structural schemas live under
`templates/` per spec §9.

## Multi-Round Requirement

v0.1.0 ship requires at least two consecutive dogfood rounds. The second
round must pass every `v1_baseline` hard threshold (see
`metrics-r6-summary.md`). `pass_rate` must never regress from one round to
the next; a regression forces a rollback or a re-improve pass before ship.
Promotion to `v2_tightened` or `v3_strict` follows the rule that a gate
level is cleared only after two consecutive rounds pass every threshold at
that level.

## Persistence Path

All evidence lands under:

```
.local/dogfood/<YYYY-MM-DD>/<round_id>/
  basic_ability_profile.yaml
  metrics_report.yaml
  router_floor_report.yaml
  half_retire_decision.yaml
  next_action_plan.yaml
  iteration_delta_report.yaml
  raw/    # OTel traces, NineS reports, tool-call logs
```

`<round_id>` must preserve chronological order across rounds of the same
day. The `raw/` directory carries OTel GenAI traces, NineS reports, and tool
logs that back the aggregated metrics. History is retained for at least six
months; archiving earlier rounds is allowed only if `metrics_report` and
`iteration_delta_report` summaries are preserved.

Learnings captured during the round flow into
`.local/memory/skill_profiles/si-chip/learnings.jsonl` via
`devolaflow.learnings.capture_learning`, and all half-retire / retire
decisions must leave a `feedback.py` trail for later reactivation review.

## No Silent Failures

If any of the eight steps fails — a missing eval set, a router-test cell
that timed out, a value-vector dimension that cannot be computed — the
failure must be written into the corresponding evidence file with a clear
error reason and surfaced in the round log. Suppressing errors without
logging, re-raising, or returning an explicit failure state is forbidden
and invalidates the round.

Source spec section: Si-Chip v0.1.0 §8.1 (steps), §8.2 (evidence files), §8.3 (multi-round), §10.1–§10.2 (persistence); aligned with `.local/research/r10_self_registering_skill_roadmap.md` §3.
