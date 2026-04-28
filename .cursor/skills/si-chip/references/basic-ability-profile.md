# BasicAbility Profile — Reader Reference

## Purpose

`BasicAbility` is the first-class object of Si-Chip. Every capture, evaluation,
diagnosis, improvement, router-test, half-retirement, iteration, and packaging
decision is keyed by a single `BasicAbility` record. This reference summarises
the frozen field layout and stage enum so that readers can produce or validate a
`BasicAbilityProfile` without re-opening the full spec. It is intentionally
read-only: the canonical, machine-validated schema lives in
`templates/basic_ability_profile.schema.yaml`, and any field change must bump
the Si-Chip spec version. Use this page to understand the object; use the
schema file to instantiate or verify one.

## Field Reference (top-level keys, spec §2.1)

- `id`: stable ability slug, matches `.agents/skills/<name>/` path segment.
- `intent`: one-sentence "what problem this ability solves".
- `current_surface`: where the ability lives today.
  - `type`: one of `markdown`, `script`, `cli`, `mcp`, `sdk`, `memory`, `mixed`.
  - `path`: repo-relative path to the source artefact.
  - `shape_hint`: declared preferred shape (`markdown_first`, `code_first`,
    `cli_first`, `registry_first`, `memory_first`, `mixed`).
- `packaging`: how the ability is shipped to platforms.
  - `install_targets`: booleans for `cursor`, `claude_code`, `codex`.
  - `source_of_truth`: canonical directory, always `.agents/skills/<name>/`.
  - `generated_targets`: list of synced platform paths (derivative only).
- `lifecycle`: stage bookkeeping.
  - `stage`: one of the seven values in the Stage Enum below.
  - `last_reviewed_at` / `next_review_at`: ISO `YYYY-MM-DD` dates; the
    `next_review_at` is mandatory whenever `stage == half_retired`.
- `eval_state`: booleans that gate stage transitions.
  - `has_eval_set`, `has_no_ability_baseline`, `has_self_eval`,
    `has_router_test`, `has_iteration_delta`.
- `metrics`: 7-dimension container for R6's 28 sub-metrics.
  - `task_quality`, `context_economy`, `latency_path`, `generalizability`,
    `usage_cost`, `routing_cost`, `governance_risk`.
  - MVP-8 keys (T1, T2, T3, C1, C4, L2, R3, R5) must be filled every round.
  - All remaining sub-metric keys must be present with explicit `null`
    placeholders; silently dropping a key is a spec violation.
- `value_vector`: seven floats feeding §6 half-retirement decisions.
  - `task_delta`, `token_delta`, `latency_delta`, `context_delta`,
    `path_efficiency_delta`, `routing_delta`, `governance_risk_delta`.
- `router_floor`: `"<model_id>/<thinking_depth>"` or `null` until §5
  router-test runs at least once.
- `decision`: the action chosen this round.
  - `action`: typically `keep`, `half_retire`, `retire`, `disable`,
    `optimize`, `productize`, `create_eval_set`, etc.
  - `rationale`: human-readable reason tied to metrics or value_vector.
  - `risk_flags`: list of strings surfacing governance or drift concerns.

## Stage Enum (spec §2.2)

Stages are bidirectionally reachable. `half_retired` is a side-loop, not a
terminal; `retired` is the only true terminus.

| Stage | Meaning |
|---|---|
| `exploratory` | Has intent and examples; no eval or baseline yet. |
| `evaluated` | Owns an eval set, a no-ability baseline, and 7-dim base metrics. |
| `productized` | Stable steps have moved into script / CLI / MCP / SDK. |
| `routed` | Router-test ran and produced a `router_floor`. |
| `governed` | Has owner, version, telemetry, deprecation policy. |
| `half_retired` | Task delta near zero but efficiency value remains; periodic review. |
| `retired` | Value exhausted or risk beyond threshold; auto-trigger disabled. |

Flow diagram: `exploratory → evaluated → productized → routed → governed`,
with `half_retired` branching from `governed` (and reachable from `evaluated`
or `productized` on demand), and `retired` reachable from `half_retired`.
Reactivation triggers listed in §6.4 (see `half-retirement-r9-summary.md`)
pull `half_retired` abilities back to `evaluated` for re-evaluation.

## Source-of-Truth Pointer

The authoritative, JSON-Schema-style definition of every field above lives at
`templates/basic_ability_profile.schema.yaml`. Validation flows through
`devolaflow.template_engine.validator.validate_template`; any schema change
requires a spec version bump and refreshed compile hashes per the rule
integration contract. Do not hand-edit a `BasicAbilityProfile` without
running it through the schema first, and never mint ad-hoc keys — if a field
you need is missing, open a spec revision instead of extending the profile
locally.

Source spec section: Si-Chip v0.1.0 §2.1 (fields) + §2.2 (stage enum).
