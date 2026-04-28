# R9 Half-Retirement — Reader Reference

`half_retire` is a first-class lifecycle state for abilities whose functional
uplift has shrunk but whose efficiency, context, path, or routing value still
holds. Retirement is never "base model already covers it" alone — the decision
must be backed by R9's 7-axis value vector. This page distills Si-Chip v0.1.0
§6 plus R9; full tables, simplification playbooks, and schemas live in
`.local/research/r9_half_retirement_framework.md`.

## 7-Axis Value Vector (spec §6.1)

Each axis is computed against a no-ability baseline for the same scenario and
model. Positive numbers mean "ability helps"; negative numbers mean "ability
hurts". All seven are required for every `half_retire` or `retire` decision.

| Axis | Formula | Data source |
|---|---|---|
| `task_delta` | `pass_with − pass_without` | R6 T3 |
| `token_delta` | `(tokens_without − tokens_with) / tokens_without` | R6 C4 + OTel `gen_ai.client.token.usage` |
| `latency_delta` | `(p95_without − p95_with) / p95_without` | R6 L1 / L2 |
| `context_delta` | `(footprint_without − footprint_with) / footprint_without` | R6 C1–C5 |
| `path_efficiency_delta` | `(detour_without − detour_with) / detour_without` | R6 L5 |
| `routing_delta` | `trigger_F1_with − trigger_F1_without` | R6 D6 |
| `governance_risk_delta` | `risk_without − risk_with` | R6 D7 |

The five middle axes (token / latency / context / path_efficiency / routing)
are bucketed against the bound gate profile's `iteration_delta` threshold:
`v1_baseline ≥ +0.05`, `v2_tightened ≥ +0.10`, `v3_strict ≥ +0.15`.

## 4 Decision Rules (spec §6.2 verbatim)

| 决策 | 触发条件 |
|---|---|
| `keep` | `task_delta >= +0.10` 或当前档 (§4) 下全部硬门槛通过 |
| `half_retire` | `task_delta` 近零 (`-0.02 ≤ task_delta ≤ +0.10`) **且** `token_delta` / `latency_delta` / `context_delta` / `path_efficiency_delta` / `routing_delta` 中至少一项达到当前 gate profile 的对应阈值桶 (`v1 ≥ +0.05`, `v2 ≥ +0.10`, `v3 ≥ +0.15`) |
| `retire` | value_vector 全部维度 ≤ 0 **或** `governance_risk_delta < 0` 且超出 §11 风险策略 **或** v3_strict 下连续两轮失败且无任一性能轴改善 |
| `disable_auto_trigger` | `governance_risk_delta` 显著为负，无论其它维度 |

`half_retire` forces an immediate simplification pass drawn from R9 §3 —
shorter description, cold-storing references, dropping oversized scripts,
switching from auto-trigger to manual-only, lowering routing priority, or
merging into a broader ability. A `next_review_at` is mandatory, typically
30 / 60 / 90 days out depending on the simplification depth.

## Decision Artifact Minimum Fields (spec §6.3)

Every `half_retire` or `retire` decision must persist a
`half_retire_decision.yaml` instance with at least these keys:

- `ability_id`
- `version`
- `decided_at` (ISO date)
- `decision` (`keep` | `half_retire` | `retire` | `disable_auto_trigger`)
- `value_vector` (all seven axes, no nulls)
- `simplification.applied` (list of applied R9 §3 strategies)
- `retained_core` (list describing the scripts, prompts, or metadata that
  justify keeping the ability around despite near-zero task delta)
- `review.next_review_at` (ISO date)
- `review.triggers` (list drawn from the six reactivation signals below)
- `provenance` (paths to the baseline report, with-ability report, and any
  NineS compare artefact used to compute the vector)

Missing any of the above keys invalidates the decision record. Reviewers
must be able to reconstruct the vector from `provenance` alone.

## 6 Reactivation Triggers (spec §6.4)

A `half_retired` ability returns to `evaluated` the moment any one of
these signals fires:

1. On a new no-ability baseline, `task_delta` returns to `≥ +0.10`
   (for example, the underlying base model regressed on this task).
2. A new scenario or domain emerges that the ability's
   `references` / `scripts` happen to cover.
3. Router-test shows that a cheaper model now needs this ability to pass,
   dropping the ability's `router_floor` by one step.
4. `context_delta`, `token_delta`, or `latency_delta` becomes significant
   (for example, any one crosses `≥ +0.25`).
5. A dependency API or CLI changes in a way that makes the ability's
   wrapper more stable than the base model's freeform output.
6. Manual-invocation frequency rises back to `≥ 5` calls in 30 days.

Each reactivation instance must be recorded through
`devolaflow.feedback.*` and must cite the triggering signal in
`review.triggers` on the subsequent decision artifact.

## Cycle Detection

Repeated flipping between `active` and `half_retired` is a smell, not a
feature. Two consecutive `half_retire ↔ active` cycles must be flagged by
`devolaflow.gate.cycle_detector.py` (per the R7 import map), which raises
a human review requirement. Automatic promotion past a cycled boundary is
blocked until a reviewer signs off, so "ratcheting" back and forth to game
the gate is rejected by tooling rather than by policy alone.

Source spec section: Si-Chip v0.1.0 §6.1 (value vector), §6.2 (decision rules), §6.3 (artifact fields), §6.4 (reactivation); distilled from `.local/research/r9_half_retirement_framework.md`.
