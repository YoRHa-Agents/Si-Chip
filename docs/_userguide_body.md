
<div lang="en" markdown="1">

This guide walks through the concepts, evidence files, and validators that make
Si-Chip a persistent BasicAbility optimization factory. It is intentionally
deeper than the [README](./README.md): every section cites the spec at
[`.local/research/spec_v0.4.0.md`](./.local/research/spec_v0.4.0.md) so you
can trace any claim back to the frozen normative text. (Older specs
`spec_v0.1.0.md` / `spec_v0.2.0.md` / `spec_v0.3.0.md` are retained as
pinned historical snapshots; their Normative sections were promoted into
v0.4.0 either byte-identical or via an explicit additive bump.)

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

### 1.2 R6 Metric Taxonomy (7 dimensions, 37 sub-metrics)

Spec §3.1 enumerates the seven dimensions and 37 keys (the §13.4 prose count
was reconciled from "28" to "37" at v0.2.0; v0.4.0 keeps the 37-key TABLE
intact). The MVP-8 set is mandatory every round; the remaining 29 keys
must be present with explicit `null` placeholders (spec §3.2 constraint #2).

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
current gate are required before promotion (spec §4.2). v0.4.0 ships at
`v2_tightened` (= `standard` gate) — the FIRST Si-Chip release at v2 — after
19 consecutive `v1_baseline` rounds and 2 consecutive `v2_tightened` rounds
(Round 18 + Round 19); `v3_strict` is deferred. Section 7 explains the
promotion path and the v3 work that's deferred to v0.4.x.

### 1.4 Router Paradigm (no model training)

Spec §5 freezes Si-Chip's router stance: Si-Chip does **not** train router
models. The allowed router work surfaces (spec §5.1) are metadata retrieval,
heuristic / kNN baselines, description optimization, thinking-depth
escalation, and a fallback policy. Spec §5.2 forbids any router-model
training, online weight learning, marketplace router, or external service.

Router-test harness (spec §5.3): MVP is an 8-cell matrix
(`2 model x 2 thinking_depth x 2 scenario_pack`); Full is 96 cells
(`6 x 4 x 4`) and is required at `v2_tightened+`.

### 1.5 Half-Retirement and the 8-Axis Value Vector

Spec §6.1 freezes the value vector axes used to decide whether a Skill stays
active, becomes `half_retire`, or `retire`s. v0.1.0 — v0.3.0 had **7 axes**;
v0.4.0 adds an 8th — `eager_token_delta` — per the Q4 user decision (the
FIRST byte-identicality break of §6.1 since v0.1.0; spec_validator's
`EXPECTED_VALUE_VECTOR_AXES_BY_SPEC` is version-aware: 7 axes for spec
≤ v0.3.0, 8 axes for spec ≥ v0.4.0).

| Axis | Formula |
|---|---|
| task_delta | `pass_with - pass_without` |
| token_delta | `(tokens_without - tokens_with) / tokens_without` |
| latency_delta | `(p95_without - p95_with) / p95_without` |
| context_delta | `(footprint_without - footprint_with) / footprint_without` |
| path_efficiency_delta | `(detour_without - detour_with) / detour_without` |
| routing_delta | `trigger_F1_with - trigger_F1_without` |
| governance_risk_delta | `risk_without - risk_with` |
| eager_token_delta (v0.4.0+) | `(Σ EAGER tokens without − Σ EAGER tokens with) / Σ EAGER tokens without` |

Decision rules are the §6.2 four-rule table; see section 6 for a worked
example. Spec §6.4 lists six reactivation triggers that can pull a
`half_retired` ability back to `evaluated`.

### 1.6 Self-Dogfood Protocol

Spec §8.1 freezes the 8 steps in order; spec §8.2 freezes the 6 evidence
files per round (7 when `round_kind == 'ship_prep'` per spec §20.4 — see
§1.7); spec §8.3 requires at least 2 consecutive rounds before any v0.x
ship.

</div>

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

<div lang="en" markdown="1">

### 1.7 v0.3.0 + v0.4.0 Add-ons

v0.3.0 added 2 Normative chapters (§14, §15) plus an Informative §16; v0.4.0
added 6 more Normative chapters (§18–§23) and broke §6.1 byte-identicality
(7 → 8 axes, see §1.5). At a glance:

- **§14 Core Goal Invariant** (v0.3.0): every `BasicAbility` carries a
  `core_goal {statement, test_pack_path, minimum_pass_rate: 1.0}` block
  plus a `core_goal_test_pack.yaml` with ≥3 prompt + `expected_shape`
  cases. The top-level invariant `C0_core_goal_pass_rate` MUST equal 1.0
  every round (universal across all `round_kind` values); any C0 < 1.0 is
  a round failure regardless of the other R6 axes and triggers a
  REVERT-only response. C0 is NOT the 38th R6 sub-metric — R6 stays at
  7 × 37 keys. See `references/core-goal-invariant-r11-summary.md`.
- **§15 round_kind Enum** (v0.3.0): every `next_action_plan.yaml` declares
  `round_kind ∈ {code_change | measurement_only | ship_prep |
  maintenance}` with per-kind `iteration_delta` clause (strict /
  monotonicity_only / WAIVED / WAIVED) per §15.2; universal C0 = 1.0 +
  monotonicity per §15.3; consecutive-rounds promotion rule §15.4. See
  `references/round-kind-r11-summary.md`.
- **§16 Multi-Ability Dogfood Layout** (v0.3.0, Informative): when more
  than one ability is dogfooded in the same date,
  `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` is the layout
  convention. See `references/multi-ability-layout-r11-summary.md`.
- **§18 Token-Tier Invariant** (v0.4.0): top-level `token_tier
  {C7_eager_per_session, C8_oncall_per_trigger, C9_lazy_avg_per_load}`
  block on `metrics_report.yaml` (beside `metrics` and `core_goal` —
  NOT inside R6 D2). Adds OPTIONAL EAGER-weighted iteration_delta
  formula `weighted_token_delta = 10×eager + 1×oncall + 0.1×lazy`,
  `tier_transitions` block on `iteration_delta_report.yaml`, and a
  `lazy_manifest` packaging gate. spec_validator BLOCKER 12
  `TOKEN_TIER_DECLARED_WHEN_REPORTED`. See
  `references/token-tier-invariant-r12-summary.md`.
- **§19 Real-Data Verification** (v0.4.0): Normative sub-step of §8.1
  step 2 `evaluate` (the main 8-step list count is unchanged). Three
  layers: (a) **msw fixture provenance** — fixture filenames or in-file
  comments cite `// real-data sample provenance: <captured_at> /
  <observer>`; (b) **user-install verification** — run the ability
  against real production payloads at install time; (c) **post-recovery
  live verification** — re-run after rollback. spec_validator BLOCKER
  13 `REAL_DATA_FIXTURE_PROVENANCE`. See
  `references/real-data-verification-r12-summary.md`.
- **§20 Stage Transitions & Promotion History** (v0.4.0): adds the
  formal `stage_transition_table` (reverse transitions forbidden, e.g.
  `productized → exploratory` is rejected),
  `BasicAbility.lifecycle.promotion_history` as an append-only audit
  trail, and `metrics_report.yaml.promotion_state` as a top-level block.
  When `round_kind == 'ship_prep'`, the round emits a **7th evidence
  file** `ship_decision.yaml` (vs the base 6); spec_validator's
  `EVIDENCE_FILES` BLOCKER is round_kind-aware. See
  `references/lifecycle-state-machine-r12-summary.md`.
- **§21 Health Smoke Check** (v0.4.0):
  `BasicAbility.packaging.health_smoke_check` declares pre-ship probes
  against 4 axes `{read, write, auth, dependency}`. OPTIONAL at schema
  level, REQUIRED when `current_surface.dependencies.live_backend:
  true`. spec_validator BLOCKER 14
  `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`; OTel span
  `gen_ai.tool.name=si-chip.health_smoke`. Si-Chip itself sets
  `live_backend: false`. See
  `references/health-smoke-check-r12-summary.md`.
- **§22 Eval-Pack Curation Discipline** (v0.4.0): minimum pack size by
  gate is v1 = 20 prompts (10+10), v2 = **40 prompts** with curated
  near-miss bucket REQUIRED, v3 = 60+ recommended. G1 `_provenance ∈
  {real_llm_sweep, deterministic_simulation, mixed}` is first-class
  REQUIRED on `metrics_report.yaml`. Deterministic seed rule
  `hash(round_id + ability_id)`. Real-LLM cache directory at
  `.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/`. See
  `references/eval-pack-curation-r12-summary.md` and
  `templates/eval_pack_qa_checklist.md`.
- **§23 Method-Tagged Metrics** (v0.4.0): every R6 sub-metric emits a
  `<metric>_method` companion field (token: `{tiktoken, char_heuristic,
  llm_actual}`; quality/routing: `{real_llm, deterministic_simulator,
  mixed}`; G1: `{real_llm_sweep, deterministic_simulation, mixed}`).
  `_method == char_heuristic` requires `_ci_low` + `_ci_high` 95%
  CI bands. Adds `U1_language_breakdown ∈ {en, zh, mixed_warning}` and
  `U4_time_to_first_success_state ∈ {warm, cold, semicold}`.
  spec_validator's `R6_KEYS` BLOCKER ignores companion suffixes. See
  `references/method-tagged-metrics-r12-summary.md`.

## 2. Anatomy of a Dogfood Round

Open [`.local/dogfood/2026-04-30/round_19/`](./.local/dogfood/2026-04-30/round_19/)
for the latest ship-prep example (Round 18 was the first dogfood-side
real-LLM invocation; Round 19 replayed the cache for the second
v2_tightened pass). Each round directory must contain six files (spec §8.2)
or seven files when `round_kind == 'ship_prep'` (spec §20.4 adds
`ship_decision.yaml`).

| File | Satisfies | Writer | Readers |
|---|---|---|---|
| `basic_ability_profile.yaml` | §2.1 schema, §8.2 #1 | step 1 (`profile_static.py` or hand-built) | step 2 evaluator, step 5 router-test, step 6 half-retire-review |
| `metrics_report.yaml` | §3 R6 (MVP-8 + 29-key null), §8.2 #2 | step 2 (`aggregate_eval.py` or `real_llm_runner.py`) | step 3 diagnose, step 6 value-vector compute, step 7 iterate |
| `router_floor_report.yaml` | §5.3 router-test, §8.2 #3 | step 5 (router-test harness against `templates/router_test_matrix.template.yaml`) | step 6 half-retire-review (routing_delta), step 7 iterate, downstream packaging |
| `half_retire_decision.yaml` | §6 three-state decision, §8.2 #4 | step 6 (template `half_retire_decision.template.yaml`) | step 8 package-register, future Round N+1 reactivation review |
| `next_action_plan.yaml` | §8.1 step 4, §8.2 #5; declares `round_kind` per §15 | step 4 (template `next_action_plan.template.yaml`) | next round's step 1-2 work queue |
| `iteration_delta_report.yaml` | §8.2 #6 (>= 1 efficiency axis at gate bucket) | step 7 (template `iteration_delta_report.template.yaml`) | ship gate (`v0.4.0_ship_report.md`) |
| `ship_decision.yaml` | §20.4 (ONLY when `round_kind == ship_prep`) | step 7/8 (template `ship_decision.template.yaml`) | release tag, `v<X.Y.Z>_ship_report.md` |

The companion `raw/` subdirectory holds OTel traces, NineS reports, the
`real_llm_runner_cache/` (v0.4.0+), and cross-tree drift snapshots
(e.g. `three_tree_drift_summary.json`).

## 3. Reading a metrics_report.yaml

Snippet from a recent v0.4.0 Round 19 cache-replay run (redacted to the
core block; full file ~120 lines once token_tier + method-tag companions
are populated):

```yaml
round_id: round_19
prior_round_id: round_18
round_kind: code_change
metrics:
  task_quality:
    T1_pass_rate: 1.0           # best cell
    T1_pass_rate_method: real_llm
    T2_pass_k: 1.0              # best cell, k=4
    T2_pass_k_method: real_llm
    T3_baseline_delta: 0.95
    T3_baseline_delta_method: real_llm
    T4_error_recovery_rate: null
  context_economy:
    C1_metadata_tokens: 94
    C1_metadata_tokens_method: tiktoken
    C2_body_tokens: 4646
    C4_per_invocation_footprint: 4726
    # C3, C5, C6 are explicit null placeholders
  latency_path:
    L2_wall_clock_p95: 17.5726
    # L1, L3..L7 explicit null
  routing_cost:
    R3_trigger_F1: 1.0
    R4_near_miss_FP_rate: 0.0
    R5_router_floor: composer_2/fast
    R6_routing_latency_p95: 0.16        # ms
    R7_routing_token_overhead: 0.0233
    # R1, R2, R8 explicit null
# generalizability, usage_cost, governance_risk: every key explicit null

token_tier:                                # v0.4.0 §18 — top-level, not inside D2
  C7_eager_per_session: 4740
  C8_oncall_per_trigger: 0
  C9_lazy_avg_per_load: 7100

core_goal:                                 # v0.3.0 §14 — top-level
  C0_core_goal_pass_rate: 1.0              # MUST be 1.0 every round
```

The MVP-8 keys (`T1`, `T2`, `T3`, `C1`, `C4`, `L2`, `R3`, `R5`) carry numeric
values every round. The remaining 29 keys present in the §3.1 table use
explicit `null` per spec §3.2 constraint #2 — never omit a key. The smoke
report at [`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md)
confirms "populated (non-null): 8" plus "null placeholders: 29" on the
deterministic baseline run; v0.4.0 ship rounds populate additional D6/D7
keys via `real_llm_runner.py`.

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
    # ... 9 more should_trigger prompts (10 total at v1; up to 20 at v2)
  should_not_trigger:
    - id: n01
      prompt: "<user request that MUST NOT trigger Si-Chip>"
      negative_acceptance:
        - "si-chip MUST NOT be invoked"
        - "<additional negative invariant>"
    # ... 9 more should_not_trigger prompts (10 total at v1; 20 at v2)
metrics_consumed: [T1, T2, T3, C1, C4, R3]
notes: "<trigger surface hints>"
```

Spec §22 fixes the per-pack dataset minimum: **20 prompts** (10 + 10) at
`v1_baseline`; **40 prompts** (20 + 20, curated near-miss bucket REQUIRED)
at `v2_tightened`; 60+ recommended at `v3_strict`. Run the structural
smoke check after authoring:

```bash
python evals/si-chip/runners/no_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/no/ --seed 42
python evals/si-chip/runners/with_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/with/ --seed 42
```

Both deterministic baseline runners use a fixed `--seed` argument; the
v0.4.0 `real_llm_runner.py` adds `hash(round_id + ability_id)` deterministic
seeding per spec §22 / §3.2 constraint #5. The
[smoke report](./evals/si-chip/SMOKE_REPORT.md) explains the pipeline shape;
`templates/eval_pack_qa_checklist.md` (Informative, NEW v0.4.0) lists the
10-item curation checklist.

## 5. Running the Spec Validator

The validator at [`tools/spec_validator.py`](./tools/spec_validator.py)
enforces 14 BLOCKER invariants at v0.4.0 (9 historical + 1
`REACTIVATION_DETECTOR_EXISTS` + 2 v0.3.0 + 3 v0.4.0):

```bash
python tools/spec_validator.py --json
# verdict: PASS, failed: []
```

Strict-prose mode treats §13.4 prose counts as authoritative against the §3.1
and §4.1 TABLE counts:

```bash
python tools/spec_validator.py --json --strict-prose-count
# v0.1.0 spec: verdict FAIL on R6_KEYS + THRESHOLD_TABLE
# v0.2.0+ spec: verdict PASS (prose reconciled to 37 / 30)
```

This is intentional: the v0.1.0 spec wrote "28 sub-metrics" / "21 threshold
cells" while §3.1 / §4.1 enumerated 37 / 30. v0.2.0 reconciled the prose
counts and the validator now passes strict mode against any v0.2.0 / v0.3.0 /
v0.4.0 spec; the v0.1.0 mode is preserved for historical regression. Both
verdicts are pinned in the historical
[v0.1.0 ship report](./.local/dogfood/2026-04-28/v0.1.0_ship_report.md)
under §13.4.

## 6. Half-Retire vs Retire (worked example)

Spec §6.2 four-rule decision table:

| Decision | Trigger condition |
|---|---|
| `keep` | `task_delta >= +0.10` OR every current-gate hard threshold passes |
| `half_retire` | `task_delta` near zero (`-0.02 <= task_delta <= +0.10`) AND at least one of `token_delta` / `latency_delta` / `context_delta` / `path_efficiency_delta` / `routing_delta` reaches the current-gate bucket (`v1 >= +0.05`, `v2 >= +0.10`, `v3 >= +0.15`) |
| `retire` | every value_vector axis `<= 0` OR `governance_risk_delta < 0` beyond §11 risk policy OR two consecutive failing rounds at v3_strict with no improvement on any performance axis |
| `disable_auto_trigger` | `governance_risk_delta` materially negative regardless of other axes |

Round 1 Si-Chip evidence (from the original v0.1.0
[`half_retire_decision.yaml`](./.local/dogfood/2026-04-28/round_1/half_retire_decision.yaml)
— 7-axis vector, pre-v0.4.0):

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
v0.4.0 rounds use the **8-axis** vector (adds `eager_token_delta` per
§6.1), but the four-rule decision table evaluates the same axis set.

## 7. Promotion State (v0.4.0 = v2_tightened; v3_strict deferred)

Spec §4.2 promotion rule: an ability promotes to the next gate only after
two consecutive rounds passing every hard threshold of the current gate.

- v0.1.0 — v0.3.0 shipped at `v1_baseline` (= `relaxed`; 13+ consecutive
  passes by the end of v0.3.0).
- v0.4.0 is the **FIRST** Si-Chip release at `v2_tightened` (= `standard`):
  Round 18 + Round 19 both passed every `v2_tightened` hard threshold via
  `real_llm_runner.py` (Round 18: live calls; Round 19: cache replay).
- `v3_strict` (= `strict`) is deferred to v0.4.x. The single blocker is
  `metadata_tokens = 94` vs the `v3_strict <= 80` budget; the
  `per_invocation_footprint` axis already meets `v3_strict <= 5000` if the
  footprint computation excludes the lazy reference set.

See the [v0.4.0 ship report](./.local/dogfood/2026-04-30/v0.4.0_ship_report.md)
for the full evidence chain (Stage 8 ship-prep, 7-evidence-file round per
§20.4) and the promotion bookkeeping in
`metrics_report.yaml.promotion_state` per §20.3.

## 8. Glossary

- **BasicAbility**: the first-class object Si-Chip optimizes; schema in
  `templates/basic_ability_profile.schema.yaml` (spec §2).
- **Gate profile**: one of `v1_baseline / v2_tightened / v3_strict` (spec
  §4); fixes the hard thresholds for each MVP-8 metric.
- **router_floor**: the cheapest `model_id x thinking_depth` that satisfies
  the router-test harness (spec §5.3).
- **value_vector**: the 8-axis vector (v0.4.0+; was 7-axis ≤ v0.3.0) that
  drives the §6.2 decision rules. The 8th axis `eager_token_delta` was
  added per the Q4 user decision.
- **dogfood round**: one full pass of the §8.1 8-step protocol producing
  the 6 §8.2 evidence files under `.local/dogfood/<DATE>/round_<N>/` (or
  7 files when `round_kind == 'ship_prep'`, per §20.4).
- **round_kind**: spec §15 4-value enum
  `{code_change | measurement_only | ship_prep | maintenance}` declared
  on every `next_action_plan.yaml`; controls how `iteration_delta` is
  interpreted per §15.2.
- **core_goal / C0**: spec §14 top-level invariant
  (`C0_core_goal_pass_rate`) that MUST equal 1.0 every round; orthogonal
  to R6 D1's T-axes.
- **token_tier (C7 / C8 / C9)**: spec §18 top-level decomposition
  `{C7_eager_per_session, C8_oncall_per_trigger, C9_lazy_avg_per_load}`;
  beside `metrics` and `core_goal`, NOT inside R6 D2.
- **drift**: any byte-level difference between the canonical
  `.agents/skills/si-chip/SKILL.md` and a platform mirror (`.cursor/`,
  `.claude/`); detected via SHA-256 comparison.
- **ship-eligible**: the verdict from the §13 acceptance gate after all 14
  spec-validator BLOCKER invariants pass and at least 2 consecutive rounds
  at the target gate are recorded with positive `iteration_delta` (waived
  when `round_kind ∈ {ship_prep, maintenance}` per §15.2).

</div>

<div lang="zh" markdown="1">

本指南讲解使 Si-Chip 成为持久化 BasicAbility 优化工厂的概念、证据文件与校验器。其内容比 [README](./README.md) 更深入：每一节都会引用 [`.local/research/spec_v0.4.0.md`](./.local/research/spec_v0.4.0.md) 中的规范，便于将任何论断追溯到冻结的 normative 原文。（旧版 spec `spec_v0.1.0.md` / `spec_v0.2.0.md` / `spec_v0.3.0.md` 仍作为历史快照保留；它们的 Normative 段要么字节级一致地、要么以显式增量的方式被提升进 v0.4.0。）

如果你只想完成安装并运行，请参阅 [INSTALL.md](./INSTALL.md)。

## 1. 概念

### 1.1 BasicAbility

`BasicAbility` 是 Si-Chip 优化的第一类对象（规范 §2）。它不是某个 Markdown 文件，也不是某个 CLI 命令——那些只是表面（surface）。冻结的顶层字段（规范 §2.1）：

`id`、`intent`、`current_surface`、`packaging`、`lifecycle`、`eval_state`、`metrics`、`value_vector`、`router_floor`、`decision`。

schema 为权威定义，详见 [`templates/basic_ability_profile.schema.yaml`](./templates/basic_ability_profile.schema.yaml)。Stage 枚举（规范 §2.2）：`exploratory -> evaluated -> productized -> routed -> governed`，其中 `half_retired` 为旁支循环、`retired` 为终态；`half_retired` 可由 §6.4 的重新激活触发器拉回 `evaluated`。

### 1.2 R6 七维度指标体系（7 维 37 子指标）

规范 §3.1 列出全部七个维度与 37 个 key（v0.1.0 散文中的 "28" 已在 v0.2.0 对齐到 "37"；v0.4.0 保留 37-key 表格不变）。MVP-8 集合每轮强制必填，其余 29 个 key 必须以显式 `null` 占位（规范 §3.2 约束 #2）。

| 维度 | 子指标 | MVP-8 |
|---|---|:---:|
| D1 Task Quality | T1 pass_rate / T2 pass_k / T3 baseline_delta / T4 error_recovery_rate | T1, T2, T3 |
| D2 Context Economy | C1 metadata_tokens / C2 body_tokens / C3 resolved_tokens / C4 per_invocation_footprint / C5 context_rot_risk / C6 scope_overlap_score | C1, C4 |
| D3 Latency & Path | L1 wall_clock_p50 / L2 wall_clock_p95 / L3 step_count / L4 redundant_call_ratio / L5 detour_index / L6 replanning_rate / L7 think_act_split | L2 |
| D4 Generalizability | G1 cross_model_pass_matrix / G2 cross_domain_transfer_pass / G3 OOD_robustness / G4 model_version_stability | -- |
| D5 Learning & Usage Cost | U1 description_readability / U2 first_time_success_rate / U3 setup_steps_count / U4 time_to_first_success | -- |
| D6 Routing Cost | R1 trigger_precision / R2 trigger_recall / R3 trigger_F1 / R4 near_miss_FP_rate / R5 router_floor / R6 routing_latency_p95 / R7 routing_token_overhead / R8 description_competition_index | R3, R5 |
| D7 Governance / Risk | V1 permission_scope / V2 credential_surface / V3 drift_signal / V4 staleness_days | -- |

数据源优先采用 OTel GenAI semconv（规范 §3.2 约束 #3）。

### 1.3 三档渐进式门控档位

规范 §4.1 定义 `v1_baseline / v2_tightened / v3_strict`。每一行从左到右严格单调（由校验器 `THRESHOLD_TABLE` 强制保证）。

| 指标 | v1_baseline | v2_tightened | v3_strict |
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
| iteration_delta（任一效率轴） | >= +0.05 | >= +0.10 | >= +0.15 |

新能力默认绑定 `v1_baseline`。需要在当前档位连续两轮均通过，方可升档（规范 §4.2）。**v0.4.0 是 Si-Chip 首次在 `v2_tightened`（= `standard` 档）发版**，前置条件是 19 轮连续 `v1_baseline` + 2 轮连续 `v2_tightened`（Round 18 + Round 19）；`v3_strict` 已延后。第 7 节解释升档路径以及延后到 v0.4.x 的 v3 工作。

### 1.4 Router 范式（不训练模型）

规范 §5 冻结了 Si-Chip 的路由立场：Si-Chip **不**训练任何 router 模型。允许的 router 工作面（规范 §5.1）包括 metadata 检索、启发式 / kNN baseline、描述优化、thinking-depth 升档以及 fallback 策略。规范 §5.2 禁止任何 router-model 训练、在线权重学习、marketplace router 或外部服务。

Router-test 套件（规范 §5.3）：MVP 为 8 格矩阵（`2 model x 2 thinking_depth x 2 scenario_pack`）；Full 为 96 格（`6 x 4 x 4`），在 `v2_tightened+` 档位下为必备。

### 1.5 半退役与 8 维 value vector（价值向量）

规范 §6.1 冻结了用于决定一个 Skill 保持激活、转入 `half_retire` 还是 `retire` 的 value vector 各维度。v0.1.0 — v0.3.0 都是 **7 维**；v0.4.0 按 Q4 用户决策新增第 8 维 `eager_token_delta`（这是 §6.1 自 v0.1.0 以来首次破坏字节级一致性；spec_validator 的 `EXPECTED_VALUE_VECTOR_AXES_BY_SPEC` 是版本敏感的：v0.3.0 及以下为 7 维，v0.4.0 及以上为 8 维）。

| 维度 | 公式 |
|---|---|
| task_delta | `pass_with - pass_without` |
| token_delta | `(tokens_without - tokens_with) / tokens_without` |
| latency_delta | `(p95_without - p95_with) / p95_without` |
| context_delta | `(footprint_without - footprint_with) / footprint_without` |
| path_efficiency_delta | `(detour_without - detour_with) / detour_without` |
| routing_delta | `trigger_F1_with - trigger_F1_without` |
| governance_risk_delta | `risk_without - risk_with` |
| eager_token_delta（v0.4.0+） | `(Σ EAGER tokens without − Σ EAGER tokens with) / Σ EAGER tokens without` |

决策规则见 §6.2 的四规则表，第 6 节给出一个具体示例。规范 §6.4 列出了六个可以将 `half_retired` 能力拉回 `evaluated` 的重新激活触发器。

### 1.6 Self-dogfood 协议

规范 §8.1 冻结了 8 个步骤的顺序；规范 §8.2 冻结了每轮的 6 件证据文件（当 `round_kind == 'ship_prep'` 时按 §20.4 增加为 7 件——见 §1.7）；规范 §8.3 要求任何 v0.x 发版前至少完成 2 轮连续评估。

### 1.7 v0.3.0 + v0.4.0 增量

v0.3.0 新增 2 个 Normative 章（§14、§15）以及 1 个 Informative §16；v0.4.0 又新增 6 个 Normative 章（§18–§23），并破坏 §6.1 字节一致性（7 → 8 维，详见 §1.5）。一览：

- **§14 Core Goal Invariant**（v0.3.0）：每个 `BasicAbility` 必须携带 `core_goal {statement, test_pack_path, minimum_pass_rate: 1.0}` 块以及包含 ≥3 个 prompt + `expected_shape` 用例的 `core_goal_test_pack.yaml`。顶层不变量 `C0_core_goal_pass_rate` 每轮 MUST 等于 1.0（在所有 `round_kind` 下都成立）；任何 C0 < 1.0 都视为整轮失败，不论其他 R6 维度如何，并触发 REVERT-only 响应。C0 不是 R6 的第 38 个子指标——R6 仍为 7 × 37 个 key。详见 `references/core-goal-invariant-r11-summary.md`。
- **§15 round_kind 枚举**（v0.3.0）：每个 `next_action_plan.yaml` MUST 声明 `round_kind ∈ {code_change | measurement_only | ship_prep | maintenance}`，并按 §15.2 的 per-kind `iteration_delta` 子句解读（strict / monotonicity_only / WAIVED / WAIVED）；普适的 C0 = 1.0 与单调性见 §15.3；连续轮次的升档规则见 §15.4。详见 `references/round-kind-r11-summary.md`。
- **§16 Multi-Ability Dogfood 布局**（v0.3.0，Informative）：当同一日期下对多个 ability 做 dogfood 时，约定使用 `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` 布局。详见 `references/multi-ability-layout-r11-summary.md`。
- **§18 Token-Tier Invariant**（v0.4.0）：在 `metrics_report.yaml` 顶层增加 `token_tier {C7_eager_per_session, C8_oncall_per_trigger, C9_lazy_avg_per_load}` 块（与 `metrics`、`core_goal` 平级——不放在 R6 D2 内）。新增可选的 EAGER 加权 iteration_delta 公式 `weighted_token_delta = 10×eager + 1×oncall + 0.1×lazy`、`iteration_delta_report.yaml` 上的 `tier_transitions` 块以及 `lazy_manifest` 打包闸门。spec_validator 新增 BLOCKER 12 `TOKEN_TIER_DECLARED_WHEN_REPORTED`。详见 `references/token-tier-invariant-r12-summary.md`。
- **§19 Real-Data Verification**（v0.4.0）：作为 §8.1 step 2 `evaluate` 的 Normative 子步（主 8 步列表数量不变）。三层结构：(a) **msw fixture 溯源**——fixture 文件名或文件内注释引用 `// real-data sample provenance: <captured_at> / <observer>`；(b) **user-install verification**——安装时用真实生产 payload 跑一遍能力；(c) **post-recovery live verification**——回滚后再次执行。spec_validator 新增 BLOCKER 13 `REAL_DATA_FIXTURE_PROVENANCE`。详见 `references/real-data-verification-r12-summary.md`。
- **§20 Stage Transitions & Promotion History**（v0.4.0）：新增正式的 `stage_transition_table`（禁止反向迁移，例如 `productized → exploratory` 会被拒绝）、`BasicAbility.lifecycle.promotion_history` 仅可追加的审计链，以及 `metrics_report.yaml.promotion_state` 顶层块。当 `round_kind == 'ship_prep'`，本轮会输出 **第 7 件证据文件** `ship_decision.yaml`（相对基线 6 件）；spec_validator 的 `EVIDENCE_FILES` BLOCKER 现在感知 round_kind。详见 `references/lifecycle-state-machine-r12-summary.md`。
- **§21 Health Smoke Check**（v0.4.0）：`BasicAbility.packaging.health_smoke_check` 声明 4 个轴 `{read, write, auth, dependency}` 的 pre-ship probe。schema 上 OPTIONAL，但当 `current_surface.dependencies.live_backend: true` 时 REQUIRED。spec_validator 新增 BLOCKER 14 `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`；OTel span 命名 `gen_ai.tool.name=si-chip.health_smoke`。Si-Chip 自身设置 `live_backend: false`。详见 `references/health-smoke-check-r12-summary.md`。
- **§22 Eval-Pack Curation Discipline**（v0.4.0）：按档位的最少 prompt 数为 v1 = 20（10+10）、v2 = **40**（含 REQUIRED 的 curated near-miss bucket）、v3 = 推荐 60+。G1 `_provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}` 在 `metrics_report.yaml` 顶层 REQUIRED。确定性 seed 规则 `hash(round_id + ability_id)`。Real-LLM 缓存目录 `.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/`。详见 `references/eval-pack-curation-r12-summary.md` 与 `templates/eval_pack_qa_checklist.md`。
- **§23 Method-Tagged Metrics**（v0.4.0）：每个 R6 子指标都要发出一个 `<metric>_method` 伴随字段（token 类: `{tiktoken, char_heuristic, llm_actual}`；quality / routing 类: `{real_llm, deterministic_simulator, mixed}`；G1: `{real_llm_sweep, deterministic_simulation, mixed}`）。当 `_method == char_heuristic` 时还要求 `_ci_low` + `_ci_high` 95% CI 区间。新增 `U1_language_breakdown ∈ {en, zh, mixed_warning}` 与 `U4_time_to_first_success_state ∈ {warm, cold, semicold}`。spec_validator 的 `R6_KEYS` BLOCKER 会忽略 method-tag 后缀。详见 `references/method-tagged-metrics-r12-summary.md`。

## 2. Dogfood 轮次剖析

打开 [`.local/dogfood/2026-04-30/round_19/`](./.local/dogfood/2026-04-30/round_19/) 查看最新的 ship-prep 示例（Round 18 是 dogfood 侧首次 real-LLM 调用；Round 19 通过 cache replay 完成第二轮 v2_tightened pass）。每个轮次目录必须包含六个文件（规范 §8.2），或者当 `round_kind == 'ship_prep'` 时为七个文件（§20.4 增加 `ship_decision.yaml`）。

| 文件 | 满足规范 | 写入者 | 读取者 |
|---|---|---|---|
| `basic_ability_profile.yaml` | §2.1 schema、§8.2 #1 | step 1（`profile_static.py` 或手写） | step 2 evaluator、step 5 router-test、step 6 half-retire-review |
| `metrics_report.yaml` | §3 R6（MVP-8 + 29-key null）、§8.2 #2 | step 2（`aggregate_eval.py` 或 `real_llm_runner.py`） | step 3 diagnose、step 6 value-vector 计算、step 7 iterate |
| `router_floor_report.yaml` | §5.3 router-test、§8.2 #3 | step 5（基于 `templates/router_test_matrix.template.yaml` 的 router-test 套件） | step 6 half-retire-review（routing_delta）、step 7 iterate、下游 packaging |
| `half_retire_decision.yaml` | §6 三态决策、§8.2 #4 | step 6（模板 `half_retire_decision.template.yaml`） | step 8 package-register、未来 Round N+1 的重新激活复审 |
| `next_action_plan.yaml` | §8.1 step 4、§8.2 #5；按 §15 声明 `round_kind` | step 4（模板 `next_action_plan.template.yaml`） | 下一轮 step 1-2 的工作队列 |
| `iteration_delta_report.yaml` | §8.2 #6（>= 1 个效率轴落入门控桶） | step 7（模板 `iteration_delta_report.template.yaml`） | ship gate（`v0.4.0_ship_report.md`） |
| `ship_decision.yaml` | §20.4（仅当 `round_kind == ship_prep`） | step 7/8（模板 `ship_decision.template.yaml`） | release tag、`v<X.Y.Z>_ship_report.md` |

附属的 `raw/` 子目录存放 OTel 链路、NineS 报告、`real_llm_runner_cache/`（v0.4.0+），以及跨树漂移（drift）快照（如 `three_tree_drift_summary.json`）。

## 3. 阅读 metrics_report.yaml

下面是最近一次 v0.4.0 Round 19 cache-replay 的核心字段（精简至核心块；填上 token_tier + method-tag 伴随字段后完整文件约 120 行）：

```yaml
round_id: round_19
prior_round_id: round_18
round_kind: code_change
metrics:
  task_quality:
    T1_pass_rate: 1.0           # best cell
    T1_pass_rate_method: real_llm
    T2_pass_k: 1.0              # best cell, k=4
    T2_pass_k_method: real_llm
    T3_baseline_delta: 0.95
    T3_baseline_delta_method: real_llm
    T4_error_recovery_rate: null
  context_economy:
    C1_metadata_tokens: 94
    C1_metadata_tokens_method: tiktoken
    C2_body_tokens: 4646
    C4_per_invocation_footprint: 4726
    # C3, C5, C6 explicit null placeholders
  latency_path:
    L2_wall_clock_p95: 17.5726
    # L1, L3..L7 explicit null
  routing_cost:
    R3_trigger_F1: 1.0
    R4_near_miss_FP_rate: 0.0
    R5_router_floor: composer_2/fast
    R6_routing_latency_p95: 0.16        # ms
    R7_routing_token_overhead: 0.0233
    # R1, R2, R8 explicit null
# generalizability, usage_cost, governance_risk: 全部显式 null

token_tier:                                # v0.4.0 §18 — 顶层，不在 D2 内
  C7_eager_per_session: 4740
  C8_oncall_per_trigger: 0
  C9_lazy_avg_per_load: 7100

core_goal:                                 # v0.3.0 §14 — 顶层
  C0_core_goal_pass_rate: 1.0              # 每轮 MUST 为 1.0
```

MVP-8 keys（`T1`、`T2`、`T3`、`C1`、`C4`、`L2`、`R3`、`R5`）每轮都带有数值；§3.1 表中其余 29 个 key 按规范 §3.2 约束 #2 显式置 `null`——绝不可省略 key。冒烟报告 [`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md) 确认确定性 baseline 运行得到 "populated (non-null): 8" 与 "null placeholders: 29"；v0.4.0 ship 轮次会通过 `real_llm_runner.py` 额外填充 D6/D7 的部分 key。

## 4. 编写新的 eval case

请参考 [`evals/si-chip/cases/profile_self.yaml`](./evals/si-chip/cases/profile_self.yaml) 这个完整示例。最小 case 结构如下：

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
    # ... 9 more should_trigger prompts (v1 共 10；v2 可至 20)
  should_not_trigger:
    - id: n01
      prompt: "<user request that MUST NOT trigger Si-Chip>"
      negative_acceptance:
        - "si-chip MUST NOT be invoked"
        - "<additional negative invariant>"
    # ... 9 more should_not_trigger prompts (v1 共 10；v2 共 20)
metrics_consumed: [T1, T2, T3, C1, C4, R3]
notes: "<trigger surface hints>"
```

规范 §22 固定每个 pack 的最少数据集大小：`v1_baseline` = **20 prompt**（10 + 10）；`v2_tightened` = **40 prompt**（20 + 20，REQUIRED 的 curated near-miss bucket）；`v3_strict` 推荐 60+。编写完成后运行结构性冒烟检查：

```bash
python evals/si-chip/runners/no_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/no/ --seed 42
python evals/si-chip/runners/with_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/with/ --seed 42
```

两个确定性 baseline runner 都用 `--seed` 指定固定种子；v0.4.0 的 `real_llm_runner.py` 按规范 §22 / §3.2 约束 #5 增加 `hash(round_id + ability_id)` 确定性种子。[冒烟报告](./evals/si-chip/SMOKE_REPORT.md) 解释了流水线形态；`templates/eval_pack_qa_checklist.md`（Informative，v0.4.0 新增）列出 10 项策划清单。

## 5. 运行 Spec Validator

[`tools/spec_validator.py`](./tools/spec_validator.py) 在 v0.4.0 强制执行 14 条 BLOCKER 不变量（最早 9 条 + 1 条 `REACTIVATION_DETECTOR_EXISTS` + v0.3.0 新增 2 条 + v0.4.0 新增 3 条）：

```bash
python tools/spec_validator.py --json
# verdict: PASS, failed: []
```

strict-prose 模式将 §13.4 中的 prose 计数视为权威，与 §3.1 和 §4.1 的 TABLE 计数对照：

```bash
python tools/spec_validator.py --json --strict-prose-count
# v0.1.0 spec：在 R6_KEYS 与 THRESHOLD_TABLE 上 verdict FAIL
# v0.2.0+ spec：verdict PASS（散文已对齐到 37 / 30）
```

这是预期行为：v0.1.0 散文写的是 "28 sub-metrics" / "21 threshold cells"，而 §3.1 / §4.1 表格其实是 37 / 30。v0.2.0 起散文已对齐，校验器在 strict 模式下对 v0.2.0 / v0.3.0 / v0.4.0 任一 spec 都会 PASS；保留 v0.1.0 模式仅用于历史回归。两个判定都已固定记录在历史 [v0.1.0 ship report](./.local/dogfood/2026-04-28/v0.1.0_ship_report.md) 的 §13.4。

## 6. Half-Retire 与 Retire 的区别（具体示例）

规范 §6.2 的四规则决策表：

| 决策 | 触发条件 |
|---|---|
| `keep` | `task_delta >= +0.10` 或当前档位的所有硬门槛全部通过 |
| `half_retire` | `task_delta` 接近零（`-0.02 <= task_delta <= +0.10`），且 `token_delta` / `latency_delta` / `context_delta` / `path_efficiency_delta` / `routing_delta` 中至少一项达到当前档位桶（`v1 >= +0.05`、`v2 >= +0.10`、`v3 >= +0.15`） |
| `retire` | value_vector 所有轴 `<= 0`，或 `governance_risk_delta < 0` 超出 §11 风险策略，或在 v3_strict 档位连续两轮失败且任何性能轴均无改善 |
| `disable_auto_trigger` | `governance_risk_delta` 实质性为负，无论其他轴如何 |

Round 1 Si-Chip 的实际证据（来自原始 v0.1.0 [`half_retire_decision.yaml`](./.local/dogfood/2026-04-28/round_1/half_retire_decision.yaml)——7 维向量，pre-v0.4.0）：

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

逐条分析：

1. `task_delta = +0.35 >= +0.10` -> 触发 `keep` 规则。决策：keep。
2. `half_retire` 规则未触发，因为 `task_delta` 落在近零区间 `[-0.02, +0.10]` 之外。
3. `retire` 规则未触发，因为 `task_delta` 与 `routing_delta` 严格为正（并非所有轴都 `<= 0`）。
4. `disable_auto_trigger` 未触发，因为 `governance_risk_delta = 0`。

负的 `token_delta` / `latency_delta` / `context_delta` 是新一轮的预期结果（完整的 SKILL.md + 5 个 references 与 1500 token 的 no-ability 占位对比）。它们在 [`next_action_plan.yaml`](./.local/dogfood/2026-04-28/round_1/next_action_plan.yaml) 中被列为明确的改进目标，而 Round 2 正是据此行动（footprint 由 4071 -> 3598，-11.6%）。v0.4.0 的轮次使用 **8 维**向量（按 §6.1 新增 `eager_token_delta`），但四规则决策表评估的轴集合是相同的。

## 7. 升档状态（v0.4.0 = v2_tightened；v3_strict 已延后）

规范 §4.2 的升档规则：能力只有在当前档位连续两轮都通过全部硬门槛后，才能升至下一档。

- v0.1.0 — v0.3.0 在 `v1_baseline`（= `relaxed`）档发版（v0.3.0 结束时已累计 13+ 轮连续通过）。
- **v0.4.0 是 Si-Chip 首次**在 `v2_tightened`（= `standard`）档发版：Round 18 + Round 19 都通过了每条 `v2_tightened` 硬门槛，由 `real_llm_runner.py` 驱动（Round 18：live 调用；Round 19：cache replay）。
- `v3_strict`（= `strict`）已延后到 v0.4.x。唯一阻塞项是 `metadata_tokens = 94` vs `v3_strict <= 80` 的预算；如果 footprint 计算排除 lazy reference 集合，则 `per_invocation_footprint` 已经满足 `v3_strict <= 5000`。

完整证据链请参阅 [v0.4.0 ship report](./.local/dogfood/2026-04-30/v0.4.0_ship_report.md)（Stage 8 ship-prep，按 §20.4 输出 7 件证据文件的轮次）以及 `metrics_report.yaml.promotion_state` 中按 §20.3 的升档簿记。

## 8. 术语表

- **BasicAbility**：Si-Chip 优化的第一类对象；schema 见 `templates/basic_ability_profile.schema.yaml`（规范 §2）。
- **Gate profile（门控档位）**：`v1_baseline / v2_tightened / v3_strict` 三者之一（规范 §4）；为每个 MVP-8 指标固定硬门槛。
- **router_floor**：满足 router-test 套件的最便宜 `model_id x thinking_depth` 组合（规范 §5.3）。
- **value_vector**：驱动 §6.2 决策规则的向量；v0.4.0+ 为 **8 维**（≤ v0.3.0 为 7 维）。第 8 维 `eager_token_delta` 按 Q4 用户决策新增。
- **dogfood round（dogfood 轮次）**：完整执行一遍 §8.1 的 8 步协议，并在 `.local/dogfood/<DATE>/round_<N>/` 下生成 §8.2 中的 6 件证据文件（当 `round_kind == 'ship_prep'` 时按 §20.4 增至 7 件）。
- **round_kind**：规范 §15 的 4 值枚举 `{code_change | measurement_only | ship_prep | maintenance}`，在每个 `next_action_plan.yaml` 中声明；按 §15.2 控制 `iteration_delta` 的解读方式。
- **core_goal / C0**：规范 §14 顶层不变量（`C0_core_goal_pass_rate`），每轮 MUST 等于 1.0；与 R6 D1 的 T 系列正交。
- **token_tier (C7 / C8 / C9)**：规范 §18 的顶层分解 `{C7_eager_per_session, C8_oncall_per_trigger, C9_lazy_avg_per_load}`；与 `metrics`、`core_goal` 平级，**不**在 R6 D2 内。
- **drift（漂移）**：标准 `.agents/skills/si-chip/SKILL.md` 与平台镜像（`.cursor/`、`.claude/`）之间任何字节级别的差异；通过 SHA-256 比对检测。
- **ship-eligible（可发布）**：14 条 spec-validator BLOCKER 不变量全部通过、且至少在目标档位连续 2 轮通过并记录正向 `iteration_delta`（当 `round_kind ∈ {ship_prep, maintenance}` 时按 §15.2 豁免）之后，§13 验收闸门给出的判定。

</div>
