---
layout: default
title: Demo
---

<div lang="en" markdown="1">

This page walks through the actual evidence Si-Chip produced when it
self-shipped v0.1.0 on 2026-04-28.

</div>

<div lang="zh" markdown="1">

本页面逐章呈现 Si-Chip 在 2026-04-28 自我交付 v0.1.0 时实际产出的证据。

</div>

// CHAPTER 01 //

<div lang="en" markdown="1">

## 1. Two consecutive `v1_baseline` passes

| Round | pass_rate | trigger_F1 | metadata_tokens | per_invocation_footprint | wall_clock_p95 (s) | half_retire | router_floor |
|---|---|---|---|---|---|---|---|
| 1 | 0.85 | 0.89 | 78 | 4071 | 1.47 | keep | composer_2/default |
| 2 | 0.85 | 0.89 | 78 | 3598 (-11.6%) | 1.47 | keep | composer_2/default |

Round 2 also populated `R4_near_miss_FP_rate = 0.05`, slimming SKILL.md body
tokens from 2493 to 2020 (-18.97 %).

</div>

<div lang="zh" markdown="1">

## 1. 连续两轮 `v1_baseline` 通过

| 轮次 | pass_rate | trigger_F1 | metadata_tokens | per_invocation_footprint | wall_clock_p95（秒） | half_retire | router_floor |
|---|---|---|---|---|---|---|---|
| 1 | 0.85 | 0.89 | 78 | 4071 | 1.47 | keep | composer_2/default |
| 2 | 0.85 | 0.89 | 78 | 3598 (-11.6%) | 1.47 | keep | composer_2/default |

Round 2 同时填充了 `R4_near_miss_FP_rate = 0.05`，并将 SKILL.md 正文 token
数从 2493 压缩到 2020（-18.97 %）。

</div>

// CHAPTER 02 //

<div lang="en" markdown="1">

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

</div>

<div lang="zh" markdown="1">

## 2. 7 维 value_vector（Round 2）

| 维度 | 数值 | 方向 |
|---|---|---|
| `task_delta` | +0.35 | 相对 no-ability baseline 改善 |
| `token_delta` | -1.40 | 退化（v0.1 尚未优化，符合预期） |
| `latency_delta` | -0.55 | 退化（符合预期） |
| `context_delta` | -1.40 | 退化（符合预期） |
| `path_efficiency_delta` | null | 尚未测量 |
| `routing_delta` | +0.8934 | 改善 |
| `governance_risk_delta` | 0.0 | 未变化 |

判定规则（规范 §6.2）：`task_delta = +0.35 >= +0.10` → **keep**。

</div>

// CHAPTER 03 //

<div lang="en" markdown="1">

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

</div>

<div lang="zh" markdown="1">

## 3. 8-cell MVP router-test 矩阵

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

`router_floor = composer_2/default`（两个 scenario_pack 均达到 pass_rate >= 0.80
的最低成本组合）。

> Si-Chip **不** 训练 router 模型（规范 §5.2）。该扫描评估的是既有
> model × thinking-depth 组合，目的是找到达到 gate 阈值的最便宜单元。

</div>

// CHAPTER 04 //

<div lang="en" markdown="1">

## 4. Cross-platform sync (drift = 0)

| Tree | Files | SHA-of-SKILL.md | Drift |
|---|---|---|---|
| Source `.agents/skills/si-chip/` | 10 (incl. DESIGN.md) | identical | n/a |
| Mirror `.cursor/skills/si-chip/` | 9 | identical | DRIFT_ZERO |
| Mirror `.claude/skills/si-chip/` | 9 | identical | DRIFT_ZERO |

Three-tree summary verdict: **ALL_TREES_DRIFT_ZERO**.

</div>

<div lang="zh" markdown="1">

## 4. 跨平台同步（drift = 0）

| 目录树 | 文件数 | SHA-of-SKILL.md | Drift |
|---|---|---|---|
| 源头 `.agents/skills/si-chip/` | 10（含 DESIGN.md） | identical | n/a |
| 镜像 `.cursor/skills/si-chip/` | 9 | identical | DRIFT_ZERO |
| 镜像 `.claude/skills/si-chip/` | 9 | identical | DRIFT_ZERO |

三树汇总判定：**ALL_TREES_DRIFT_ZERO**。

</div>

// CHAPTER 05 //

<div lang="en" markdown="1">

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

</div>

<div lang="zh" markdown="1">

## 5. 8 项规范不变量

默认的 `python tools/spec_validator.py --json` 运行结果为 verdict **PASS**：

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

`--strict-prose-count` 模式会在 `R6_KEYS` 和 `THRESHOLD_TABLE` 上故意失败，
用以标记规范 §13.4 中散文叙述与表格之间的差异——后续 spec bump 应当将其调和。

</div>

// CHAPTER 06 //

<div lang="en" markdown="1">

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

</div>

<div lang="zh" markdown="1">

## 6. 在本地复现这些数字

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

</div>

// CHAPTER 07 //

<div lang="en" markdown="1">

## 7. What ships next (deferred from v0.1.0)

- v2_tightened promotion (2 fresh rounds at v2 thresholds)
- Codex `.codex/` bridge
- Round 3+ continuation, populating R6_routing_latency_p95, R7_routing_token_overhead, L1, U1-U4
- LLM-backed eval runner swap (the `result.json` schema and runner CLI are stable)

See [`CHANGELOG.md`](https://github.com/YoRHa-Agents/Si-Chip/blob/main/CHANGELOG.md)
for the full v0.1.0 release notes.

</div>

<div lang="zh" markdown="1">

## 7. 后续交付（从 v0.1.0 延后）

- 升档至 v2_tightened（在 v2 阈值下完成 2 轮新的 dogfood）
- Codex `.codex/` bridge
- Round 3 及后续轮次持续推进，补齐 R6_routing_latency_p95、R7_routing_token_overhead、L1、U1-U4
- 切换到 LLM 驱动的 eval runner（`result.json` schema 与 runner CLI 已经稳定）

完整的 v0.1.0 发版说明见 [`CHANGELOG.md`](https://github.com/YoRHa-Agents/Si-Chip/blob/main/CHANGELOG.md)。

</div>
