---
layout: default
title: Demo
---

# Live Demo: v0.1.0 ship walkthrough

This page walks through the actual evidence Si-Chip produced when it
self-shipped v0.1.0 on 2026-04-28.

## 1. Two consecutive `v1_baseline` passes

| Round | pass_rate | trigger_F1 | metadata_tokens | per_invocation_footprint | wall_clock_p95 (s) | half_retire | router_floor |
|---|---|---|---|---|---|---|---|
| 1 | 0.85 | 0.89 | 78 | 4071 | 1.47 | keep | composer_2/default |
| 2 | 0.85 | 0.89 | 78 | 3598 (-11.6%) | 1.47 | keep | composer_2/default |

Round 2 also populated `R4_near_miss_FP_rate = 0.05`, slimming SKILL.md body
tokens from 2493 to 2020 (-18.97 %).

## 2. The 7-axis value vector (Round 2)

| Axis | Value | Direction |
|---|---|---|
| `task_delta` | +0.35 | improvement vs no-ability baseline |
| `token_delta` | -1.40 | regression (expected for unoptimized v0.1) |
| `latency_delta` | -0.55 | regression (expected) |
| `context_delta` | -1.40 | regression (expected) |
| `path_efficiency_delta` | null | not yet measured |
| `routing_delta` | +0.8934 | improvement |
| `governance_risk_delta` | 0.0 | unchanged |

Decision rule (spec section 6.2): `task_delta = +0.35 >= +0.10` → **keep**.

## 3. The 8-cell MVP router-test sweep

| model | thinking_depth | scenario_pack | pass_rate |
|---|---|---|---|
| composer_2 | fast | trigger_basic | 0.86 |
| composer_2 | fast | near_miss | 0.78 |
| composer_2 | default | trigger_basic | 0.90 |
| composer_2 | default | near_miss | 0.83 |
| sonnet_shallow | fast | trigger_basic | 0.83 |
| sonnet_shallow | fast | near_miss | 0.74 |
| sonnet_shallow | default | trigger_basic | 0.88 |
| sonnet_shallow | default | near_miss | 0.81 |

`router_floor = composer_2/default` (cheapest tuple where both packs reach pass_rate >= 0.80).

> Si-Chip does **not** train router models (spec section 5.2). The sweep evaluates
> existing model x thinking-depth combinations to find the cheapest cell that
> meets the gate.

## 4. Cross-platform sync (drift = 0)

| Tree | Files | SHA-of-SKILL.md | Drift |
|---|---|---|---|
| Source `.agents/skills/si-chip/` | 10 (incl. DESIGN.md) | identical | n/a |
| Mirror `.cursor/skills/si-chip/` | 9 | identical | DRIFT_ZERO |
| Mirror `.claude/skills/si-chip/` | 9 | identical | DRIFT_ZERO |

Three-tree summary verdict: **ALL_TREES_DRIFT_ZERO**.

## 5. The 8 spec invariants

The default `python tools/spec_validator.py --json` run reports verdict **PASS**:

```text
[BLOCKER] BAP_SCHEMA: PASS
[BLOCKER] R6_KEYS: PASS (37 keys per section 3.1 table; INFO note on section 13.4 prose discrepancy)
[BLOCKER] THRESHOLD_TABLE: PASS (30 cells per section 4.1 table; INFO note on section 13.4 prose)
[BLOCKER] ROUTER_MATRIX_CELLS: PASS (mvp=8, full=96)
[BLOCKER] VALUE_VECTOR_AXES: PASS (7 axes)
[BLOCKER] PLATFORM_PRIORITY: PASS (Cursor -> Claude Code -> Codex)
[BLOCKER] DOGFOOD_PROTOCOL: PASS (8 steps + 6 evidence files)
[BLOCKER] FOREVER_OUT_LIST: PASS (4 items)
verdict: PASS
```

The `--strict-prose-count` mode intentionally fails on `R6_KEYS` and
`THRESHOLD_TABLE` to flag the section 13.4 prose-vs-table discrepancy that a future
spec bump should reconcile.

## 6. Reproduce the numbers locally

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip

# 1. Spec validator (8 invariants — verdict PASS)
python tools/spec_validator.py --json

# 2. Re-aggregate the included simulated baseline runs
python .agents/skills/si-chip/scripts/aggregate_eval.py \
  --runs-dir evals/si-chip/baselines/with_si_chip \
  --baseline-dir evals/si-chip/baselines/no_ability \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --templates-dir templates \
  --out /tmp/metrics_report.yaml

# 3. Confirm packaging gate (metadata=78, body=2020, pass=true)
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .agents/skills/si-chip/SKILL.md --both \
  --budget-meta 100 --budget-body 5000 --json
```

## 7. What ships next (deferred from v0.1.0)

- v2_tightened promotion (2 fresh rounds at v2 thresholds)
- Codex `.codex/` bridge
- Round 3+ continuation, populating R6_routing_latency_p95, R7_routing_token_overhead, L1, U1-U4
- LLM-backed eval runner swap (the `result.json` schema and runner CLI are stable)

See [`CHANGELOG.md`](https://github.com/YoRHa-Agents/Si-Chip/blob/main/CHANGELOG.md)
for the full v0.1.0 release notes.
