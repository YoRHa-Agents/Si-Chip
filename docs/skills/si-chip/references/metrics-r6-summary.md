# R6 Metric Taxonomy — Reader Reference

Si-Chip v0.1.0 is full-scope: all 7 dimensions and 28 sub-metrics from R6 are
reserved. This page gives a compact reader's map; the authoritative definitions
(formulas, 2026 evidence, adjacency graph) live in
`.local/research/r6_metric_taxonomy.md`, and are consumed by
`metrics/bridge.py` and `scripts/aggregate_eval.py`.

## 7 Dimensions

**D1 Task Quality** captures the raw functional ceiling of an ability — does
it solve the task at all, does it solve it repeatably, and does it beat the
no-ability baseline. Four sub-metrics (T1–T4) track pass rate, k-repeat pass,
baseline delta, and self-recovery. D1 is the gate of "keep vs retire".

**D2 Context Economy** measures how much of the context window the ability
consumes — metadata, body, resolved references, total footprint, rot risk, and
overlap with siblings. Six sub-metrics (C1–C6) bind directly to the §4 gate
budgets and to the context-rot cliff documented in 2026 frontier-model
studies.

**D3 Latency & Path Efficiency** answers "is the trajectory straight?". Seven
sub-metrics (L1–L7) cover p50/p95 wall clock, step count, redundant-call
ratio, detour index, replanning rate, and think/act token split. L5
detour_index maps directly onto the user feedback of "does the path wander".

**D4 Generalizability** exposes cross-model, cross-domain, and cross-version
robustness. Four sub-metrics (G1–G4) feed the router floor and stability
tracking: a strong G1 matrix is the prerequisite for claiming a low
`router_floor`.

**D5 Learning & Usage Cost** reports how expensive first-time success is —
readability of the description, first-time success rate, setup steps, and
time to first success (U1–U4). D5 low values are frequently upstream causes
of D6 routing errors.

**D6 Routing Cost** measures the cost of reaching the ability at all:
trigger precision/recall/F1, near-miss false positives, router floor,
routing latency, routing token overhead, and the description-competition
index (R1–R8). R5 `router_floor` is the composite output of §5 router-test.

**D7 Governance / Risk** captures permission scope, credential surface,
drift signal, and staleness (V1–V4). Risk dominates: a negative
`governance_risk_delta` forces auto-trigger disable regardless of other
gains.

## Full 28 Sub-Metric Table

| D | sub-id | name | MVP-8? |
|---|---|---|:---:|
| D1 | T1 | pass_rate | yes |
| D1 | T2 | pass_k (k=4) | yes |
| D1 | T3 | baseline_delta | yes |
| D1 | T4 | error_recovery_rate | — |
| D2 | C1 | metadata_tokens | yes |
| D2 | C2 | body_tokens | — |
| D2 | C3 | resolved_tokens | — |
| D2 | C4 | per_invocation_footprint | yes |
| D2 | C5 | context_rot_risk | — |
| D2 | C6 | scope_overlap_score | — |
| D3 | L1 | wall_clock_p50 | — |
| D3 | L2 | wall_clock_p95 | yes |
| D3 | L3 | step_count | — |
| D3 | L4 | redundant_call_ratio | — |
| D3 | L5 | detour_index | — |
| D3 | L6 | replanning_rate | — |
| D3 | L7 | think_act_split | — |
| D4 | G1 | cross_model_pass_matrix | — |
| D4 | G2 | cross_domain_transfer_pass | — |
| D4 | G3 | OOD_robustness | — |
| D4 | G4 | model_version_stability | — |
| D5 | U1 | description_readability | — |
| D5 | U2 | first_time_success_rate | — |
| D5 | U3 | setup_steps_count | — |
| D5 | U4 | time_to_first_success | — |
| D6 | R1 | trigger_precision | — |
| D6 | R2 | trigger_recall | — |
| D6 | R3 | trigger_F1 | yes |
| D6 | R4 | near_miss_FP_rate | — |
| D6 | R5 | router_floor | yes |
| D6 | R6 | routing_latency_p95 | — |
| D6 | R7 | routing_token_overhead | — |
| D6 | R8 | description_competition_index | — |
| D7 | V1 | permission_scope | — |
| D7 | V2 | credential_surface | — |
| D7 | V3 | drift_signal | — |
| D7 | V4 | staleness_days | — |

(Row count is 7 D + 28 sub-metrics; MVP-8 marked.)

## MVP-8 List

Every dogfood round must emit these eight, regardless of gate level:

`T1 pass_rate`, `T2 pass_k`, `T3 baseline_delta`, `C1 metadata_tokens`,
`C4 per_invocation_footprint`, `L2 wall_clock_p95`, `R3 trigger_F1`,
`R5 router_floor`.

The other 20 sub-metric keys must still appear in `metrics_report` with
explicit `null` placeholders; dropping a key is a spec violation.

## Three Gate Profiles (spec §4.1 verbatim)

| 指标 | v1_baseline | v2_tightened | v3_strict |
|---|---:|---:|---:|
| `pass_rate` | ≥ 0.75 | ≥ 0.82 | ≥ 0.90 |
| `pass_k` (k=4) | ≥ 0.40 | ≥ 0.55 | ≥ 0.65 |
| `trigger_F1` | ≥ 0.80 | ≥ 0.85 | ≥ 0.90 |
| `near_miss_FP_rate` | ≤ 0.15 | ≤ 0.10 | ≤ 0.05 |
| `metadata_tokens` | ≤ 120 | ≤ 100 | ≤ 80 |
| `per_invocation_footprint` | ≤ 9000 | ≤ 7000 | ≤ 5000 |
| `wall_clock_p95` (s) | ≤ 45 | ≤ 30 | ≤ 20 |
| `routing_latency_p95` (ms) | ≤ 2000 | ≤ 1200 | ≤ 800 |
| `routing_token_overhead` | ≤ 0.20 | ≤ 0.12 | ≤ 0.08 |
| `iteration_delta` (one efficiency axis) | ≥ +0.05 | ≥ +0.10 | ≥ +0.15 |

Thresholds are strictly monotone left-to-right; any proposed change must
preserve monotonicity and bump the spec version.

## Promotion Rule

- New abilities default to `v1_baseline`.
- Advance one level only after two consecutive dogfood rounds fully pass
  every threshold at the current level.
- One failure at the current level: stay; two consecutive failures: demote
  one level and trigger §6 half-retire review.
- Any level change, threshold tweak, or monotonicity shift must be recorded
  in `iteration_delta_report.yaml` and the profile's `lifecycle` block.

## Data Source Preference

Use OpenTelemetry GenAI semantic conventions as the first-choice data
source: `gen_ai.client.operation.duration` (for L1/L2),
`gen_ai.client.token.usage` (for C-series and routing overhead),
`gen_ai.tool.name` and `mcp.method.name` (for L3/L4/R6).
`metrics/bridge.py` is the only place that maps OTel attributes and
NineS scorer output onto the 28 sub-metric keys; inventing private fields
is forbidden.

Source spec section: Si-Chip v0.1.0 §3 (taxonomy) + §4.1/§4.2 (gates and promotion); distilled from `.local/research/r6_metric_taxonomy.md`.
