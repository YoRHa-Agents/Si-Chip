# R8 Router-Test Protocol — Reader Reference

Si-Chip does NOT train router models. Router work exists only to find
paradigms that let the model route itself more effectively. This page
distills the router paradigm in Si-Chip v0.1.0 §5 plus the 8-cell and
96-cell harness from R8. Formal per-cell schemas and anchor numbers live
in `.local/research/r8_router_test_protocol.md`.

## Allowed Router Work Surfaces (spec §5.1)

Five — and only five — router paradigms are allowed. Everything else is a
§11 violation.

1. **Metadata retrieval** — static or semantic search over a
   `BasicAbility.description`, tags, and trigger example set.
2. **Heuristic / kNN baseline** — reuse
   `devolaflow.memory_router.router.MemoryRouter` with
   `memory_router.cache.MemoryCase` as a deterministic baseline; compute
   precision/recall/F1 on top.
3. **Description optimization** — iterate the `description` field against
   R6 `R3 trigger_F1` and `R4 near_miss_FP_rate`, drawing technique from
   the Anthropic `skill-creator/improve_description.py` loop.
4. **Thinking-depth escalation** — call
   `task_adaptive_selector.select_context(task_type, round_num=N)` and
   `apply_round_escalation`; do not re-implement depth steps.
5. **Fallback policy** — on failure, escalate in the fixed order
   `deterministic_memory_router → composer_2/fast → sonnet/default →
   opus/extended`, guarded by `gate/convergence.py` to prevent infinite
   retries.

## Strict Prohibitions (spec §5.2)

The following are forbidden in perpetuity; any PR introducing them must be
rejected on sight.

1. Training a router classifier or ranker of any size.
2. Maintaining private routing weights or online learning parameters.
3. Outsourcing router work to a marketplace, fine-tune pipeline, or
   third-party routing service.
4. Any wording or field that positions Si-Chip as a provider of routing
   models to outside consumers.

**Si-Chip does NOT train router models.** The only question routing work
answers is: which `(model_id × thinking_depth)` floor already lets the
model route itself well enough?

## MVP 8-Cell vs Full 96-Cell Matrix

Every ability must at least run the 8-cell MVP at `v1_baseline`. Full
96-cell coverage is required once the ability is at `v2_tightened` or
`v3_strict`.

| Axis | MVP (8 cells) | Full (96 cells) |
|---|---|---|
| Cells | 8 = 2 model × 2 depth × 2 scenario | 96 = 6 model × 4 depth × 4 scenario |
| Models | `composer_2`, `sonnet_shallow` | `composer_2`, `haiku_4_5`, `sonnet_4_6`, `opus_4_7`, `gpt_5_mini`, `deterministic_memory_router` |
| Thinking depths | `fast`, `default` | `fast`, `default`, `extended`, `round_escalated` |
| Scenario packs | `trigger_basic`, `near_miss` | `trigger_basic`, `near_miss`, `multi_skill_competition`, `execution_handoff` |
| Dataset | 20 prompts / pack (10 should-trigger + 10 should-not) | 20–50 prompts / pack |
| Required metrics | T1, T2, T3, L1/L2, R1/R2/R3, R4, R5, R6/R7 | MVP set + C4, C5, L3, L4, L5, R8, G1 |

The harness emits one `router_floor` per ability — the weakest
`(model_id × thinking_depth)` pair that clears the bound profile's
thresholds. Model strength order runs
`deterministic_memory_router < composer_2 < haiku_4_5 < gpt_5_mini <
sonnet_4_6 < opus_4_7`; depth order runs
`fast < default < extended < round_escalated`.

## Profile ↔ Gate Binding (spec §5.4)

At any moment, an ability is bound to exactly one profile / gate pair.
Switching pairs is a promotion event that follows the §4.2 rule.

| Router profile (R8) | Gate profile (spec §4) |
|---|---|
| `relaxed` | `v1_baseline` |
| `standard` | `v2_tightened` |
| `strict` | `v3_strict` |

Threshold examples per profile (full table in R8 §5): `relaxed` demands
`trigger_F1 ≥ 0.75`, `pass_rate ≥ 0.70`, `routing_latency_p95 ≤ 2000 ms`;
`standard` tightens to 0.85 / 0.80 / 1200 ms; `strict` enforces 0.92 /
0.88 / 800 ms. Because the gate and router profile advance together, a
router-test result at `standard` is only valid if the ability is already
bound to `v2_tightened`.

## Operational Reminders

- Every router-test run emits a `router_floor_report.yaml` stored in the
  round directory (see `self-dogfood-protocol.md`).
- Fallback escalations are recorded with reinforcement findings via
  `gate/reinforcement` so that later rounds can review the near-miss
  transitions.
- The deterministic memory router baseline is mandatory: if it alone
  passes, the ability's `router_floor` degrades to
  `deterministic_memory_router/fast`, which is the cheapest possible
  routing outcome.
- `gate/convergence.py` caps retry loops; a test that never converges is
  a failure, not an excuse to widen budgets.

Si-Chip does NOT train router models — this line is restated so it cannot
be missed.

Source spec section: Si-Chip v0.1.0 §5.1 (work surfaces), §5.2 (prohibitions), §5.3 (MVP/Full matrix), §5.4 (profile-gate binding); distilled from `.local/research/r8_router_test_protocol.md`.
