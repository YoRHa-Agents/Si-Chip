
<div lang="en" markdown="1">

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

</div>

<div lang="zh" markdown="1">

本指南讲解使 Si-Chip 成为持久化 BasicAbility 优化工厂的概念、证据文件与校验器。其内容比 [README](./README.md) 更深入：每一节都会引用 [`.local/research/spec_v0.1.0.md`](./.local/research/spec_v0.1.0.md) 中的规范，便于将任何论断追溯到冻结的 normative 原文。

如果你只想完成安装并运行，请参阅 [INSTALL.md](./INSTALL.md)。

## 1. 概念

### 1.1 BasicAbility

`BasicAbility` 是 Si-Chip 优化的第一类对象（规范 §2）。它不是某个 Markdown 文件，也不是某个 CLI 命令——那些只是表面（surface）。冻结的顶层字段（规范 §2.1）：

`id`、`intent`、`current_surface`、`packaging`、`lifecycle`、`eval_state`、`metrics`、`value_vector`、`router_floor`、`decision`。

schema 为权威定义，详见 [`templates/basic_ability_profile.schema.yaml`](./templates/basic_ability_profile.schema.yaml)。Stage 枚举（规范 §2.2）：`exploratory -> evaluated -> productized -> routed -> governed`，其中 `half_retired` 为旁支循环、`retired` 为终态；`half_retired` 可由 §6.4 的重新激活触发器拉回 `evaluated`。

### 1.2 R6 七维度指标体系（7 维 28 子指标）

规范 §3.1 列出全部七个维度。MVP-8 集合每轮强制必填，其余指标必须以显式 `null` 占位（规范 §3.2 约束 #2）。

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

新能力默认绑定 `v1_baseline`。需要在当前档位连续两轮均通过，方可升档（规范 §4.2）。v0.1.0 维持在 `v1_baseline`，原因详见第 7 节。

### 1.4 Router 范式（不训练模型）

规范 §5 冻结了 Si-Chip 的路由立场：Si-Chip **不**训练任何 router 模型。允许的 router 工作面（规范 §5.1）包括 metadata 检索、启发式 / kNN baseline、描述优化、thinking-depth 升档以及 fallback 策略。规范 §5.2 禁止任何 router-model 训练、在线权重学习、marketplace router 或外部服务。

Router-test 套件（规范 §5.3）：MVP 为 8 格矩阵（`2 model x 2 thinking_depth x 2 scenario_pack`）；Full 为 96 格（`6 x 4 x 4`），在 `v2_tightened+` 档位下为必备。

### 1.5 半退役与 7 维 value vector（价值向量）

规范 §6.1 冻结了用于决定一个 Skill 保持激活、转入 `half_retire` 还是 `retire` 的 value vector 各维度。

| 维度 | 公式 |
|---|---|
| task_delta | `pass_with - pass_without` |
| token_delta | `(tokens_without - tokens_with) / tokens_without` |
| latency_delta | `(p95_without - p95_with) / p95_without` |
| context_delta | `(footprint_without - footprint_with) / footprint_without` |
| path_efficiency_delta | `(detour_without - detour_with) / detour_without` |
| routing_delta | `trigger_F1_with - trigger_F1_without` |
| governance_risk_delta | `risk_without - risk_with` |

决策规则见 §6.2 的四规则表，第 6 节给出一个具体示例。规范 §6.4 列出了六个可以将 `half_retired` 能力拉回 `evaluated` 的重新激活触发器。

### 1.6 Self-dogfood 协议

规范 §8.1 冻结了 8 个步骤的顺序；规范 §8.2 冻结了每轮的 6 件证据文件；规范 §8.3 要求任何 v0.x 发版前至少完成 2 轮连续评估。

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

</div>

<div lang="zh" markdown="1">

## 2. Dogfood 轮次剖析

打开 [`.local/dogfood/2026-04-28/round_2/`](./.local/dogfood/2026-04-28/round_2/) 查看标准示例。每个轮次目录必须包含六个文件（规范 §8.2）。下面给出每个文件满足哪条规范、由谁写入、被谁读取。

| 文件 | 满足规范 | 写入者 | 读取者 |
|---|---|---|---|
| `basic_ability_profile.yaml` | §2.1 schema, §8.2 #1 | step 1（`profile_static.py` 或手写） | step 2 evaluator、step 5 router-test、step 6 half-retire-review |
| `metrics_report.yaml` | §3 R6（MVP-8 + 28-key null）、§8.2 #2 | step 2（`aggregate_eval.py`） | step 3 diagnose、step 6 value-vector 计算、step 7 iterate |
| `router_floor_report.yaml` | §5.3 router-test、§8.2 #3 | step 5（基于 `templates/router_test_matrix.template.yaml` 的 router-test 套件） | step 6 half-retire-review（routing_delta）、step 7 iterate、下游 packaging |
| `half_retire_decision.yaml` | §6 三态决策、§8.2 #4 | step 6（模板 `half_retire_decision.template.yaml`） | step 8 package-register、未来 Round N+1 的重新激活复审 |
| `next_action_plan.yaml` | §8.1 step 4、§8.2 #5 | step 4（模板 `next_action_plan.template.yaml`） | 下一轮 step 1-2 的工作队列 |
| `iteration_delta_report.yaml` | §8.2 #6（>= 1 个效率轴落入门控桶） | step 7（模板 `iteration_delta_report.template.yaml`） | ship gate（`v0.1.0_ship_report.md`） |

附属的 `raw/` 子目录存放 OTel 链路、NineS 报告，以及跨树漂移（drift）快照（如 `three_tree_drift_summary.json`）。

## 3. 阅读 metrics_report.yaml

来自 [`.local/dogfood/2026-04-28/round_2/metrics_report.yaml`](./.local/dogfood/2026-04-28/round_2/metrics_report.yaml) 的片段（仅保留核心块；完整文件约 75 行）：

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

MVP-8 keys（`T1`、`T2`、`T3`、`C1`、`C4`、`L2`、`R3`、`R5`）每轮都带有数值；表中其余 29 个 key 按规范 §3.2 约束 #2 显式置 `null`——绝不可省略 key。冒烟报告 [`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md) 确认基线运行得到 "populated (non-null): 8" 与 "null placeholders: 29"。

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

规范 §5.3 将每个 pack 的数据集固定为 20 个 prompt（10 + 10）。编写完成后运行结构性冒烟检查：

```bash
python evals/si-chip/runners/no_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/no/ --seed 42
python evals/si-chip/runners/with_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/with/ --seed 42
```

按 W3.B 的文档说明，两个 runner 都是确定性模拟（seed=42）；[冒烟报告](./evals/si-chip/SMOKE_REPORT.md) 解释了流水线形态以及切换到真实 LLM 运行的升级路径。

## 5. 运行 Spec Validator

[`tools/spec_validator.py`](./tools/spec_validator.py) 强制 8 条 BLOCKER 不变量：

```bash
python tools/spec_validator.py --json
# verdict: PASS, failed: []
```

strict-prose 模式将 §13.4 中的 prose 计数视为权威，与 §3.1 和 §4.1 的 TABLE 计数对照：

```bash
python tools/spec_validator.py --json --strict-prose-count
# verdict: FAIL
# failed: [R6_KEYS, THRESHOLD_TABLE]
```

这是预期行为：§3.1 列出 37 个子指标 key，§13.4 prose 写的是 28；§4.1 有 30 个数值单元格，§13.4 prose 写的是 21。默认模式遵循 TABLE 计数（即运行期契约）；strict 模式则用于证明校验器能捕获两者间的差异。两个判定都已在 [ship report](./.local/dogfood/2026-04-28/v0.1.0_ship_report.md) 的 §13.4 中固定记录。

## 6. Half-Retire 与 Retire 的区别（具体示例）

规范 §6.2 的四规则决策表：

| 决策 | 触发条件 |
|---|---|
| `keep` | `task_delta >= +0.10` 或当前档位的所有硬门槛全部通过 |
| `half_retire` | `task_delta` 接近零（`-0.02 <= task_delta <= +0.10`），且 `token_delta` / `latency_delta` / `context_delta` / `path_efficiency_delta` / `routing_delta` 中至少一项达到当前档位桶（`v1 >= +0.05`、`v2 >= +0.10`、`v3 >= +0.15`） |
| `retire` | value_vector 所有轴 `<= 0`，或 `governance_risk_delta < 0` 超出 §11 风险策略，或在 v3_strict 档位连续两轮失败且任何性能轴均无改善 |
| `disable_auto_trigger` | `governance_risk_delta` 实质性为负，无论其他轴如何 |

Round 1 Si-Chip 的实际证据（来自 [`half_retire_decision.yaml`](./.local/dogfood/2026-04-28/round_1/half_retire_decision.yaml)）：

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

负的 `token_delta` / `latency_delta` / `context_delta` 是新一轮的预期结果（完整的 SKILL.md + 5 个 references 与 1500 token 的 no-ability 占位对比）。它们在 [`next_action_plan.yaml`](./.local/dogfood/2026-04-28/round_1/next_action_plan.yaml) 中被列为明确的改进目标，而 Round 2 正是据此行动（footprint 由 4071 -> 3598，-11.6%）。

## 7. 升级到 v2_tightened（后续工作）

规范 §4.2 的升档规则：能力只有在当前档位连续两轮都通过全部硬门槛后，才能升至下一档。Si-Chip 的 Round 1 与 Round 2 均通过 `v1_baseline`，因此 v0.2 工作**有资格**升档至 `v2_tightened`。

v0.1.0 按 S5 任务规范保持在 `v1_baseline`（router profile 为 `relaxed`）：v0.1.0 的 ship gate 是 "连续两轮通过 `v1_baseline` 且至少一个 iteration_delta 效率轴为正"，而 Round 2 的 `context_delta +0.31` 轴满足该条件。v2_tightened 升档属于后续计划，并非 v0.1.0 发版的一部分；详见 ship report 的 "Promotion State" 章节。

## 8. 术语表

- **BasicAbility**：Si-Chip 优化的第一类对象；schema 见 `templates/basic_ability_profile.schema.yaml`（规范 §2）。
- **Gate profile（门控档位）**：`v1_baseline / v2_tightened / v3_strict` 三者之一（规范 §4）；为每个 MVP-8 指标固定硬门槛。
- **router_floor**：满足 router-test 套件的最便宜 `model_id x thinking_depth` 组合（规范 §5.3）。
- **value_vector**：驱动 §6.2 决策规则的 7 维向量。
- **dogfood round（dogfood 轮次）**：完整执行一遍 §8.1 的 8 步协议，并在 `.local/dogfood/<DATE>/round_<N>/` 下生成 §8.2 中的 6 件证据文件。
- **drift（漂移）**：标准 `.agents/skills/si-chip/SKILL.md` 与平台镜像（`.cursor/`、`.claude/`）之间任何字节级别的差异；通过 SHA-256 比对检测。
- **ship-eligible（可发布）**：8 条 spec-validator 不变量全部通过、且至少连续 2 轮 `v1_baseline` 通过并记录正向 `iteration_delta` 之后，§13 验收闸门给出的判定。

</div>
