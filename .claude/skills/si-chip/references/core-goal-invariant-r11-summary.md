# Core-Goal Invariant — R11 Summary (Spec §14)

> Reader-friendly summary of the §14 core_goal Normative chapter
> (v0.3.0-rc1). Authoritative sources:
> `.local/research/spec_v0.3.0-rc1.md` §14 and
> `.local/research/r11_core_goal_invariant.md` §3.

## What is core_goal?

`core_goal` is the **persistent, never-regress functional outcome** a
`BasicAbility` delivers — the one-sentence contract between the ability
and the user: if this behavior disappears, the user notices immediately.

Distinct from two adjacent fields already defined in v0.2.0:

| Field | Purpose | Consumer |
|---|---|---|
| `intent` | Narrative — "what this ability solves" | Humans / Stage 1 capture |
| `description` (SKILL.md frontmatter) | Router metadata | Router / R3_trigger_F1 |
| `core_goal.statement` (NEW v0.3.0) | Testable functional contract | Evaluator / C0_core_goal_pass_rate |

All three coexist; they optimize different signals.

## Schema (REQUIRED in v0.3.0+ profiles)

`core_goal` is a top-level REQUIRED field on `BasicAbility` (additive
to §2.1; existing fields unchanged). Canonical JSON-Schema definition:
`templates/basic_ability_profile.schema.yaml` (`$schema_version: 0.2.0`).

```yaml
basic_ability:
  id: "<ability-name>"
  intent: "<this ability solves what>"
  core_goal:                                  # NEW v0.3.0, REQUIRED
    statement: "<one-sentence functional contract; testable, not narrative>"
    user_observable_failure_mode: "<what user sees if core_goal regresses>"
    test_pack_path: "<repo-relative path to core_goal_test_pack.yaml>"
    minimum_pass_rate: 1.0                    # spec-locked; cannot be lowered
    last_passing_round: "<round_id>"
    core_goal_version: "0.1.0"
```

Field semantics:

- `statement` (≥16 chars): testable functional contract. Narrative
  prose is NOT acceptable — the line must be checkable against a
  prompt + `expected_shape`.
- `user_observable_failure_mode`: what the user sees if `core_goal`
  regresses. Written for PR review / on-call diagnosis.
- `test_pack_path` (`*.yaml`): repo-relative path to the pack
  enumerating ≥3 cases (§14.2).
- `minimum_pass_rate`: spec-locked at exactly `1.0`.
- `last_passing_round` / `core_goal_version`: bookkeeping; pack
  version bumps on case deletion or `expected_shape` revision.

## Worked Examples

### Example (a) — Si-Chip itself

```yaml
basic_ability:
  id: "si-chip"
  core_goal:
    statement: "Given any BasicAbility, Si-Chip MUST execute the 8-step dogfood protocol and emit 6 schema-valid evidence files into .local/dogfood/<DATE>/[abilities/<id>/]round_<N>/."
    test_pack_path: ".agents/skills/si-chip/core_goal_test_pack.yaml"
    minimum_pass_rate: 1.0
    last_passing_round: "round_13"
    core_goal_version: "0.1.0"
```

Cases (≥3): (1) profile a synthetic `dummy-ability`; (2) run Si-Chip on
`chip-usage-helper` Round 1 from scratch; (3) re-run Si-Chip on itself
Round N+1 from Round N artifacts.

### Example (b) — chip-usage-helper

```yaml
basic_ability:
  id: "chip-usage-helper"
  core_goal:
    statement: "Given a user prompt about their own Cursor usage / spend / model mix / team rank, the helper MUST return a response containing (i) a numeric value with currency/percentage unit, (ii) an explicit time window, and (iii) rendered through the chip-usage-helper MCP."
    test_pack_path: "ChipPlugins/chips/chip_usage_helper/.dogfood/core_goal_test_pack.yaml"
    minimum_pass_rate: 1.0
    last_passing_round: "round_10"
    core_goal_version: "0.1.0"
```

Cases (≥3): (1) EN `"show me my cursor usage dashboard"` → `$<num>` +
window + MCP; (2) CJK `"我本月花了多少？"` → `¥<num>` + "本月" + MCP;
(3) slash `"/usage-report --window=30d"` → numeric + "30d" + MCP.

> These cases differ from the 40-prompt `eval_pack.yaml` trigger pack:
> the trigger pack measures `R3_trigger_F1` (did the router load this
> ability?); the core_goal pack measures `C0_core_goal_pass_rate`
> (once loaded, did the ability fulfill its contract?). Both are needed.

## C0_core_goal_pass_rate

`C0 = (cases passed) / (cases total)`, always in `[0.0, 1.0]`.
Spec-locked at exactly `1.0` per §14.3.

C0 is a **top-level invariant**, NOT the 38th R6 sub-metric. R6 stays
frozen at 7 × 37. `metrics_report.yaml` places C0 outside `metrics`:

```yaml
metrics:
  task_quality: { ... }
  ...
core_goal:                                 # top-level, outside metrics
  C0_core_goal_pass_rate: 1.0              # MUST be exactly 1.0
  cases_passed: 3
  cases_total: 3
  failed_case_ids: []                      # MUST be []
  pack_version: "0.1.0"
```

## No-Regression Rule (§14.3)

Two paired rules govern C0 every round:

1. **Strict `MUST = 1.0`** (§14.3.1): every round emits `C0 == 1.0`
   with `failed_case_ids == []`. Any `C0 < 1.0` = round FAILURE,
   regardless of other R6 axes or `round_kind`.
2. **Strict no-regression** (§14.3.2): if
   `metrics_report[round_N+1].C0 < metrics_report[round_N].C0`, round
   N+1 is a FAILURE. The round's `iteration_delta_report.yaml` MUST
   have `verdict.pass = false` and
   `core_goal_check.verdict.core_goal_pass = false`.

There is no "C0 = 0.95 but other axes are great so let it pass" legal
path. C0 is binary; R6 axes are continuous; they do not trade off.

## REVERT-Only Rule on Regression (§14.4)

Failing rounds (C0 regressed) MUST:

1. **Verdict**: no `verdict.pass = true` regardless of other axes.
2. **Source revert**: the source change that caused the regression
   MUST be reverted before the next round starts. Do NOT "patch
   forward" past a C0 regression.
3. **Next plan**: failing round's `next_action_plan.yaml.actions` MUST
   include a `primitive: refine` action targeting
   `C0_core_goal_pass_rate` with
   `exit_criterion: "C0 >= prior_round.C0"`.
4. **No silent skip**: failing round's evidence stays on disk at
   `.local/dogfood/<DATE>/...` as a negative-result trace (workspace
   rule "No Silent Failures").

### Round 12 → Round 13 precedent

Si-Chip Round 12 added a 7th eval case to push `T2_pass_k` past
v2_tightened's 0.55 threshold. Under the SHA-256 deterministic
simulator the new case's per-case `pass_rate = 0.65` pulled the 7-case
average from Round 11's `0.5478` to Round 12's `0.4950` — a regression
of `-0.0528`. L0 decided `PATH = REVERT-ONLY`; Round 13 `git rm`'d the
7th case + Round 12 baselines, restoring T2_pass_k byte-identically to
`0.5477708333333333`. v0.3.0 turns this manual intervention into spec
machinery: future Round-12-shape regressions are auto-flagged as round
failure by `tools/spec_validator.py`.

## Why NOT R6 D8 — design rationale (§14.5, R11 §3.4)

Adding C0 as the 38th R6 sub-metric (option A) was considered and
rejected. Decisive reasons:

- **Preserves frozen 7×37 count.** v0.2.0 reconciled prose to 37;
  adding D8 would force 7×38, breaking the additivity discipline
  v0.3.0 promises (§3-§11 byte-identical).
- **C0 is binary, not continuous.** R6 sub-metrics are "more / less /
  faster / slower" quality scales; C0 is a boolean go/no-go. Feeding
  a boolean into a progressive-gate table (§4.1 v1/v2/v3) is a
  semantic type error — there is no meaningful "v2_tightened C0
  threshold" distinct from v1's; both are `1.0`.
- **"Failure regardless of other axes" doesn't fit value_vector.**
  R9 value_vector weighs axes against each other; C0 short-circuits,
  it is not an axis.

Consumers iterating "all metric keys" should synthesize the list as
`R6_KEYS + ["C0"]`.

## Reactivation Interaction (§14.7)

Half-retired abilities (§6) preserve their `core_goal_test_pack`
snapshot — cold-archived in place, not deleted. Reactivation (§6.4
trigger fires) requires:

1. **Pack unchanged**: verify hash matches pre-half-retire snapshot;
   a drifted pack means "effectively a new ability" → §14.1 fresh flow.
2. **C0 = 1.0 against current run**: re-run pack under current model /
   dependency / scenario. `C0 < 1.0` → reactivation REJECTED.
3. **Pack may grow, not shrink**: reactivation may add new cases for
   the triggering scenario. Deletion still forbidden without
   `core_goal_version` bump.
4. **`core_goal_version` carry-forward**: reactivation alone does not
   bump pack version.

## Forever-Out Re-Affirmation (§14.6)

Spec §14.6 re-quotes the four §11.1 forever-out items verbatim and
confirms §14 touches none of them:

- Skill / Plugin **marketplace** 与任何分发表面积。
- **Router 模型训练** 或在线权重学习。
- 通用 IDE / Agent runtime **兼容层**。
- Markdown-to-CLI 自动转换器。

`core_goal_test_pack` is an in-tree ability artifact; `C0` is an
evaluator metric. Neither introduces a registry, model-training
pipeline, IDE compatibility layer, or markdown-to-CLI transformation.
The spec invariant holds.

## Cross-References

| §14 subsection | Spec section | R11 section |
|---|---|---|
| 14.1 schema + worked examples | spec §14.1 | r11 §3.1 |
| 14.2 test pack + freeze constraints | spec §14.2 | r11 §3.2 |
| 14.3 C0 + no-regression | spec §14.3 | r11 §3.3 |
| 14.4 rollback + Round 12 precedent | spec §14.4 | r11 §3.3.2 + §1.2 |
| 14.5 top-level invariant placement | spec §14.5 | r11 §3.4 |
| 14.6 forever-out re-affirm | spec §14.6 | r11 §3.5 |
| 14.7 reactivation interaction | spec §14.7 | r11 §10.5 + §3.3 + spec §6.4 |

Source spec section: Si-Chip v0.3.0-rc1 §14 (Normative); distilled
from `.local/research/r11_core_goal_invariant.md` §3. This reference
is loaded on demand and is excluded from the §7.3 SKILL.md body budget.
