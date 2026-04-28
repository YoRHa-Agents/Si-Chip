
This guide walks through the concepts, evidence files, and validators that make
Si-Chip a persistent BasicAbility optimization factory. It is intentionally
deeper than the [README](./README.md): every section cites the spec at
[`.local/research/spec_v0.1.0.md`](./.local/research/spec_v0.1.0.md) so you
can trace any claim back to the frozen normative text.

If you just want to install and run, see [INSTALL.md](./INSTALL.md).

## 1. Concepts

### 1.1 BasicAbility

`BasicAbility` is the first-class object Si-Chip optimizes (spec §2). It is
not a Markdown file or a CLI command — those are surfaces. Frozen top-level
fields (spec §2.1):

`id`, `intent`, `current_surface`, `packaging`, `lifecycle`, `eval_state`,
`metrics`, `value_vector`, `router_floor`, `decision`.

The schema is authoritative; see
[`templates/basic_ability_profile.schema.yaml`](./templates/basic_ability_profile.schema.yaml).
Stage enum (spec §2.2):
`exploratory -> evaluated -> productized -> routed -> governed`, with
`half_retired` as a side-loop and `retired` as terminus. `half_retired` can
be pulled back to `evaluated` by the §6.4 reactivation triggers.

### 1.2 R6 Metric Taxonomy (7 dimensions, 28 sub-metrics)

Spec §3.1 enumerates the seven dimensions. The MVP-8 set is mandatory every
round; the rest must be present with explicit `null` placeholders (spec §3.2
constraint #2).

| Dimension | Sub-metrics | MVP-8 |
|---|---|:---:|
| D1 Task Quality | T1 pass_rate / T2 pass_k / T3 baseline_delta / T4 error_recovery_rate | T1, T2, T3 |
| D2 Context Economy | C1 metadata_tokens / C2 body_tokens / C3 resolved_tokens / C4 per_invocation_footprint / C5 context_rot_risk / C6 scope_overlap_score | C1, C4 |
| D3 Latency & Path | L1 wall_clock_p50 / L2 wall_clock_p95 / L3 step_count / L4 redundant_call_ratio / L5 detour_index / L6 replanning_rate / L7 think_act_split | L2 |
| D4 Generalizability | G1 cross_model_pass_matrix / G2 cross_domain_transfer_pass / G3 OOD_robustness / G4 model_version_stability | -- |
| D5 Learning & Usage Cost | U1 description_readability / U2 first_time_success_rate / U3 setup_steps_count / U4 time_to_first_success | -- |
| D6 Routing Cost | R1 trigger_precision / R2 trigger_recall / R3 trigger_F1 / R4 near_miss_FP_rate / R5 router_floor / R6 routing_latency_p95 / R7 routing_token_overhead / R8 description_competition_index | R3, R5 |
| D7 Governance / Risk | V1 permission_scope / V2 credential_surface / V3 drift_signal / V4 staleness_days | -- |

OTel GenAI semconv is the preferred data source (spec §3.2 constraint #3).

### 1.3 Three Progressive Gate Profiles

Spec §4.1 defines `v1_baseline / v2_tightened / v3_strict`. Each row is
strictly monotone left-to-right (validator `THRESHOLD_TABLE` enforces this).

| Metric | v1_baseline | v2_tightened | v3_strict |
|---|---:|---:|---:|
| pass_rate | >= 0.75 | >= 0.82 | >= 0.90 |
| pass_k (k=4) | >= 0.40 | >= 0.55 | >= 0.65 |
| trigger_F1 | >= 0.80 | >= 0.85 | >= 0.90 |
| near_miss_FP_rate | <= 0.15 | <= 0.10 | <= 0.05 |
| metadata_tokens | <= 120 | <= 100 | <= 80 |
| per_invocation_footprint | <= 9000 | <= 7000 | <= 5000 |
| wall_clock_p95 (s) | <= 45 | <= 30 | <= 20 |
| routing_latency_p95 (ms) | <= 2000 | <= 1200 | <= 800 |
| routing_token_overhead | <= 0.20 | <= 0.12 | <= 0.08 |
| iteration_delta (one efficiency axis) | >= +0.05 | >= +0.10 | >= +0.15 |

A new ability binds to `v1_baseline`. Two consecutive passing rounds at the
current gate are required before promotion (spec §4.2). v0.1.0 holds at
`v1_baseline`; section 7 explains why.

### 1.4 Router Paradigm (no model training)

Spec §5 freezes Si-Chip's router stance: Si-Chip does **not** train router
models. The allowed router work surfaces (spec §5.1) are metadata retrieval,
heuristic / kNN baselines, description optimization, thinking-depth
escalation, and a fallback policy. Spec §5.2 forbids any router-model
training, online weight learning, marketplace router, or external service.

Router-test harness (spec §5.3): MVP is an 8-cell matrix
(`2 model x 2 thinking_depth x 2 scenario_pack`); Full is 96 cells
(`6 x 4 x 4`) and is required at `v2_tightened+`.

### 1.5 Half-Retirement and the 7-Axis Value Vector

Spec §6.1 freezes the value vector axes used to decide whether a Skill stays
active, becomes `half_retire`, or `retire`s.

| Axis | Formula |
|---|---|
| task_delta | `pass_with - pass_without` |
| token_delta | `(tokens_without - tokens_with) / tokens_without` |
| latency_delta | `(p95_without - p95_with) / p95_without` |
| context_delta | `(footprint_without - footprint_with) / footprint_without` |
| path_efficiency_delta | `(detour_without - detour_with) / detour_without` |
| routing_delta | `trigger_F1_with - trigger_F1_without` |
| governance_risk_delta | `risk_without - risk_with` |

Decision rules are the §6.2 four-rule table; see section 6 for a worked
example. Spec §6.4 lists six reactivation triggers that can pull a
`half_retired` ability back to `evaluated`.

### 1.6 Self-Dogfood Protocol

Spec §8.1 freezes the 8 steps in order; spec §8.2 freezes the 6 evidence
files per round; spec §8.3 requires at least 2 consecutive rounds before any
v0.x ship.

```mermaid
flowchart LR
    s1[1 profile] --> s2[2 evaluate]
    s2 --> s3[3 diagnose]
    s3 --> s4[4 improve]
    s4 --> s5[5 router-test]
    s5 --> s6[6 half-retire-review]
    s6 --> s7[7 iterate]
    s7 --> s8[8 package-register]
    s8 -.next round.-> s1
```

## 2. Anatomy of a Dogfood Round

Open [`.local/dogfood/2026-04-28/round_2/`](./.local/dogfood/2026-04-28/round_2/)
for the canonical example. Each round directory must contain six files
(spec §8.2). For each: which spec section it satisfies, who writes it, what
reads it.

| File | Satisfies | Writer | Readers |
|---|---|---|---|
| `basic_ability_profile.yaml` | §2.1 schema, §8.2 #1 | step 1 (`profile_static.py` or hand-built) | step 2 evaluator, step 5 router-test, step 6 half-retire-review |
| `metrics_report.yaml` | §3 R6 (MVP-8 + 28-key null), §8.2 #2 | step 2 (`aggregate_eval.py`) | step 3 diagnose, step 6 value-vector compute, step 7 iterate |
| `router_floor_report.yaml` | §5.3 router-test, §8.2 #3 | step 5 (router-test harness against `templates/router_test_matrix.template.yaml`) | step 6 half-retire-review (routing_delta), step 7 iterate, downstream packaging |
| `half_retire_decision.yaml` | §6 three-state decision, §8.2 #4 | step 6 (template `half_retire_decision.template.yaml`) | step 8 package-register, future Round N+1 reactivation review |
| `next_action_plan.yaml` | §8.1 step 4, §8.2 #5 | step 4 (template `next_action_plan.template.yaml`) | next round's step 1-2 work queue |
| `iteration_delta_report.yaml` | §8.2 #6 (>= 1 efficiency axis at gate bucket) | step 7 (template `iteration_delta_report.template.yaml`) | ship gate (`v0.1.0_ship_report.md`) |

The companion `raw/` subdirectory holds OTel traces, NineS reports, and
cross-tree drift snapshots (e.g. `three_tree_drift_summary.json`).

## 3. Reading a metrics_report.yaml

Snippet from [`.local/dogfood/2026-04-28/round_2/metrics_report.yaml`](./.local/dogfood/2026-04-28/round_2/metrics_report.yaml)
(redacted to the core block; full file ~75 lines):

```yaml
round_id: round_2
prior_round_id: round_1
metrics:
  task_quality:
    T1_pass_rate: 0.85
    T2_pass_k: 0.5478
    T3_baseline_delta: 0.35
    T4_error_recovery_rate: null
  context_economy:
    C1_metadata_tokens: 78
    C2_body_tokens: 2020
    C3_resolved_tokens: null
    C4_per_invocation_footprint: 3598.0
    C5_context_rot_risk: null
    C6_scope_overlap_score: null
  latency_path:
    L1_wall_clock_p50: null
    L2_wall_clock_p95: 1.4693
    # L3 .. L7 all null
  routing_cost:
    R3_trigger_F1: 0.8934
    R4_near_miss_FP_rate: 0.05
    R5_router_floor: composer_2/fast
    # R1, R2, R6, R7, R8 null
  # generalizability, usage_cost, governance_risk: every key is explicit null
```

The MVP-8 keys (`T1`, `T2`, `T3`, `C1`, `C4`, `L2`, `R3`, `R5`) carry numeric
values every round. The remaining 29 keys present in the table use explicit
`null` per spec §3.2 constraint #2 — never omit a key. The smoke report at
[`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md) confirms
"populated (non-null): 8" plus "null placeholders: 29" on the baseline run.

## 4. Authoring a New Eval Case

Use [`evals/si-chip/cases/profile_self.yaml`](./evals/si-chip/cases/profile_self.yaml)
as a worked example. The minimal case structure:

```yaml
case_id: <unique slug>
case_title: "<one-line summary>"
spec_section: "§<n> step <m>"
ability_under_test: "si-chip"
goal: "<what success looks like>"
prompts:
  should_trigger:
    - id: t01
      prompt: "<user request that MUST trigger Si-Chip>"
      acceptance_criteria:
        - id: ac1
          description: "<observable success criterion>"
          how_verified: file_exists | json_field | regex
          target: "<glob | jsonpath | regex>"
    # ... 9 more should_trigger prompts (10 total)
  should_not_trigger:
    - id: n01
      prompt: "<user request that MUST NOT trigger Si-Chip>"
      negative_acceptance:
        - "si-chip MUST NOT be invoked"
        - "<additional negative invariant>"
    # ... 9 more should_not_trigger prompts (10 total)
metrics_consumed: [T1, T2, T3, C1, C4, R3]
notes: "<trigger surface hints>"
```

Spec §5.3 fixes the per-pack dataset at 20 prompts (10 + 10). Run the
structural smoke check after authoring:

```bash
python evals/si-chip/runners/no_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/no/ --seed 42
python evals/si-chip/runners/with_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/with/ --seed 42
```

Both runners are deterministic simulations (seed=42) per W3.B docstrings; the
[smoke report](./evals/si-chip/SMOKE_REPORT.md) explains the pipeline shape
and the upgrade path to live LLM runs.

## 5. Running the Spec Validator

The validator at [`tools/spec_validator.py`](./tools/spec_validator.py)
enforces 8 BLOCKER invariants:

```bash
python tools/spec_validator.py --json
# verdict: PASS, failed: []
```

Strict-prose mode treats §13.4 prose counts as authoritative against the §3.1
and §4.1 TABLE counts:

```bash
python tools/spec_validator.py --json --strict-prose-count
# verdict: FAIL
# failed: [R6_KEYS, THRESHOLD_TABLE]
```

This is intentional: §3.1 enumerates 37 sub-metric keys but §13.4 prose says
28; §4.1 has 30 numeric cells but §13.4 prose says 21. Default mode honours
the TABLE counts (the runtime contract); strict mode proves the validator
catches the discrepancy. Both verdicts are pinned in the
[ship report](./.local/dogfood/2026-04-28/v0.1.0_ship_report.md) under §13.4.

## 6. Half-Retire vs Retire (worked example)

Spec §6.2 four-rule decision table:

| Decision | Trigger condition |
|---|---|
| `keep` | `task_delta >= +0.10` OR every current-gate hard threshold passes |
| `half_retire` | `task_delta` near zero (`-0.02 <= task_delta <= +0.10`) AND at least one of `token_delta` / `latency_delta` / `context_delta` / `path_efficiency_delta` / `routing_delta` reaches the current-gate bucket (`v1 >= +0.05`, `v2 >= +0.10`, `v3 >= +0.15`) |
| `retire` | every value_vector axis `<= 0` OR `governance_risk_delta < 0` beyond §11 risk policy OR two consecutive failing rounds at v3_strict with no improvement on any performance axis |
| `disable_auto_trigger` | `governance_risk_delta` materially negative regardless of other axes |

Round 1 Si-Chip evidence (from
[`half_retire_decision.yaml`](./.local/dogfood/2026-04-28/round_1/half_retire_decision.yaml)):

```yaml
value_vector:
  task_delta: 0.35
  token_delta: -1.71
  latency_delta: -0.55
  context_delta: -1.71
  path_efficiency_delta: null
  routing_delta: 0.8934
  governance_risk_delta: 0.0
```

Walk-through:

1. `task_delta = +0.35 >= +0.10` -> the `keep` rule fires. Decision: keep.
2. The `half_retire` rule does not fire because `task_delta` is outside the
   near-zero band `[-0.02, +0.10]`.
3. The `retire` rule does not fire because `task_delta` and `routing_delta`
   are strictly positive (not all axes `<= 0`).
4. `disable_auto_trigger` does not fire because `governance_risk_delta = 0`.

The negative `token_delta` / `latency_delta` / `context_delta` are expected
for a fresh round (full SKILL.md + 5 references vs the 1500-token no-ability
stand-in). They are explicit improvement targets in
[`next_action_plan.yaml`](./.local/dogfood/2026-04-28/round_1/next_action_plan.yaml),
which is exactly what Round 2 acted on (footprint 4071 -> 3598, -11.6%).

## 7. Promotion to v2_tightened (Future Work)

Spec §4.2 promotion rule: an ability promotes to the next gate only after
two consecutive rounds passing every hard threshold of the current gate.
Si-Chip Round 1 + Round 2 both passed `v1_baseline`, so v0.2 work is
**eligible** for `v2_tightened` promotion.

v0.1.0 holds at `v1_baseline` (router profile `relaxed`) by S5 task spec:
the v0.1.0 ship gate is "two consecutive `v1_baseline` passes plus at least
one positive iteration_delta efficiency axis", which Round 2's
`context_delta +0.31` axis satisfies. v2_tightened promotion is a follow-up
plan rather than part of the v0.1.0 ship; see the ship report's
"Promotion State" section.

## 8. Glossary

- **BasicAbility**: the first-class object Si-Chip optimizes; schema in
  `templates/basic_ability_profile.schema.yaml` (spec §2).
- **Gate profile**: one of `v1_baseline / v2_tightened / v3_strict` (spec
  §4); fixes the hard thresholds for each MVP-8 metric.
- **router_floor**: the cheapest `model_id x thinking_depth` that satisfies
  the router-test harness (spec §5.3).
- **value_vector**: the 7-axis vector that drives the §6.2 decision rules.
- **dogfood round**: one full pass of the §8.1 8-step protocol producing the
  6 §8.2 evidence files under `.local/dogfood/<DATE>/round_<N>/`.
- **drift**: any byte-level difference between the canonical
  `.agents/skills/si-chip/SKILL.md` and a platform mirror (`.cursor/`,
  `.claude/`); detected via SHA-256 comparison.
- **ship-eligible**: the verdict from the §13 acceptance gate after all 8
  spec-validator invariants pass and at least 2 consecutive `v1_baseline`
  rounds are recorded with positive `iteration_delta`.
