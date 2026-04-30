---
layout: default
title: Demo
---

<div lang="en" markdown="1">

This page walks through the actual evidence Si-Chip produced when it
self-shipped v0.4.0 on 2026-04-30. v0.4.0 is the **first Si-Chip release at
the `v2_tightened` (= `standard`) gate** — Round 18 + Round 19 are the two
consecutive `v2_tightened` passes that unlocked promotion. The historical
v0.1.0 evidence (Round 1 + Round 2; `v1_baseline`; 2026-04-28) is preserved
in chapter 8 as an additive baseline.

</div>

<div lang="zh" markdown="1">

本页面逐章呈现 Si-Chip 在 2026-04-30 自我交付 v0.4.0 时实际产出的证据。
v0.4.0 是 Si-Chip **首次在 `v2_tightened`（= `standard`）档位发版**——
Round 18 + Round 19 是解锁升档的两轮连续 `v2_tightened` 通过。历史的 v0.1.0
证据（Round 1 + Round 2；`v1_baseline`；2026-04-28）作为对照基线保留在第 8 章。

</div>

// CHAPTER 01 //

<div lang="en" markdown="1">

## 1. Two consecutive `v2_tightened` passes (v0.4.0)

| Round | T1 pass_rate | T2 pass_k | trigger_F1 | metadata_tokens | per_invocation_footprint | wall_clock_p95 (s) | router_floor |
|---|---|---|---|---|---|---|---|
| 18 (live) | 1.0 best cell, 0.9719 mean | 1.0 best cell | 1.0 | 94 (Stage 8 frozen) | 4726 | 17.0028 | composer_2/fast |
| 19 (replay) | same (cache replay) | same (cache replay) | 1.0 | 94 | 4726 | 17.5726 | composer_2/fast |

Round 18 was the first dogfood-side `evals/si-chip/runners/real_llm_runner.py`
invocation against `claude-haiku-4-5` + `claude-sonnet-4-6` via Veil
litellm-local at `127.0.0.1:8086` — $0.20 spend, 640 calls, 16-min
wall-clock; **honest k=4 sampling** unblocked T2_pass_k from the deterministic
SHA-256 PROXY 0.5478 lower bound it had been stuck at since Round 1.
Round 19 replayed the cache at 100% hit ($0; ~20 ms wall-clock) for the
second consecutive v2 pass.

</div>

<div lang="zh" markdown="1">

## 1. 连续两轮 `v2_tightened` 通过（v0.4.0）

| 轮次 | T1 pass_rate | T2 pass_k | trigger_F1 | metadata_tokens | per_invocation_footprint | wall_clock_p95（秒） | router_floor |
|---|---|---|---|---|---|---|---|
| 18（live） | 1.0 best cell，0.9719 mean | 1.0 best cell | 1.0 | 94（Stage 8 已冻结） | 4726 | 17.0028 | composer_2/fast |
| 19（replay） | 同上（cache replay） | 同上（cache replay） | 1.0 | 94 | 4726 | 17.5726 | composer_2/fast |

Round 18 是 dogfood 侧首次调用 `evals/si-chip/runners/real_llm_runner.py`，
通过 Veil litellm-local（`127.0.0.1:8086`）打到 `claude-haiku-4-5` +
`claude-sonnet-4-6` —— 共花 $0.20、640 次调用、16 分钟 wall-clock；**honest
k=4 采样**把 T2_pass_k 从 Round 1 起一直困在 SHA-256 PROXY 下界 0.5478 解放出来。
Round 19 用 100% 命中的 cache replay 完成第二轮 v2 通过（$0、约 20 ms wall-clock）。

</div>

// CHAPTER 02 //

<div lang="en" markdown="1">

## 2. The 8-axis value vector (Round 19; v0.4.0)

v0.4.0 broke `value_vector` byte-identicality with the addition of an
8th axis `eager_token_delta` per the Q4 user decision (the FIRST §6.1
break since v0.1.0).

| Axis | Round 19 | Direction |
|---|---|---|
| `task_delta` | +0.95 | improvement vs no-ability baseline (real-LLM) |
| `token_delta` | +0.0 | unchanged at v0.4.0 ship |
| `latency_delta` | +0.0 | unchanged at v0.4.0 ship |
| `context_delta` | +0.0 | unchanged at v0.4.0 ship |
| `path_efficiency_delta` | null | not measured this round |
| `routing_delta` | +1.0 | improvement (full trigger_F1) |
| `governance_risk_delta` | 0.0 | unchanged |
| `eager_token_delta` (NEW @ v0.4.0) | per `token_tier` block | EAGER tokens / session decomposition |

Decision rule (spec §6.2): `task_delta = +0.95 >= +0.10` → **keep**.

</div>

<div lang="zh" markdown="1">

## 2. 8 维 value_vector（Round 19；v0.4.0）

v0.4.0 按 Q4 用户决策新增第 8 维 `eager_token_delta`，破坏了 §6.1 自 v0.1.0 以来的
字节级一致性（这是首次破坏）。

| 维度 | Round 19 | 方向 |
|---|---|---|
| `task_delta` | +0.95 | 相对 no-ability baseline 改善（real-LLM） |
| `token_delta` | +0.0 | v0.4.0 发版时未变 |
| `latency_delta` | +0.0 | v0.4.0 发版时未变 |
| `context_delta` | +0.0 | v0.4.0 发版时未变 |
| `path_efficiency_delta` | null | 本轮未测量 |
| `routing_delta` | +1.0 | 改善（trigger_F1 满分） |
| `governance_risk_delta` | 0.0 | 未变化 |
| `eager_token_delta`（v0.4.0 新增） | 由 `token_tier` 块描述 | 每会话 EAGER token 分解 |

判定规则（规范 §6.2）：`task_delta = +0.95 >= +0.10` → **keep**。

</div>

// CHAPTER 03 //

<div lang="en" markdown="1">

## 3. Real-LLM router-test sweep (8-cell MVP @ v0.4.0)

Round 18 ran the 8-cell MVP matrix via `real_llm_runner.py` against two real
models (and a replay vs deterministic baseline). Best-cell pass_rate hits
1.0 across all 4 trigger_basic cells; near_miss_FP_rate sits at 0.0 across
the entire matrix.

| model | thinking_depth | scenario_pack | T1 pass_rate (best) |
|---|---|---|---|
| claude-haiku-4-5 | fast | trigger_basic | 1.0 |
| claude-haiku-4-5 | fast | near_miss | 1.0 (FP=0) |
| claude-haiku-4-5 | default | trigger_basic | 1.0 |
| claude-haiku-4-5 | default | near_miss | 1.0 (FP=0) |
| claude-sonnet-4-6 | fast | trigger_basic | 1.0 |
| claude-sonnet-4-6 | fast | near_miss | 1.0 (FP=0) |
| claude-sonnet-4-6 | default | trigger_basic | 1.0 |
| claude-sonnet-4-6 | default | near_miss | 1.0 (FP=0) |

`router_floor = composer_2/fast` (the cheapest tuple where both packs reach
the v2_tightened pass_rate >= 0.82 hard threshold; recorded in
`router_floor_report.yaml`).

> Si-Chip does **not** train router models (spec §5.2). The sweep evaluates
> existing `model x thinking-depth` combinations to find the cheapest cell
> that meets the gate, exactly as v0.1.0 did — only the harness backend
> swapped from deterministic SHA-256 simulation to real-LLM cache.

</div>

<div lang="zh" markdown="1">

## 3. Real-LLM router-test 矩阵（8-cell MVP @ v0.4.0）

Round 18 用 `real_llm_runner.py` 跑了 8-cell MVP 矩阵，对接两个真实模型
（外加 replay 与确定性 baseline）。最佳 cell 的 pass_rate 在 4 个 trigger_basic
cell 上都达到 1.0；near_miss_FP_rate 在整个矩阵上都是 0.0。

| model | thinking_depth | scenario_pack | T1 pass_rate（best） |
|---|---|---|---|
| claude-haiku-4-5 | fast | trigger_basic | 1.0 |
| claude-haiku-4-5 | fast | near_miss | 1.0（FP=0） |
| claude-haiku-4-5 | default | trigger_basic | 1.0 |
| claude-haiku-4-5 | default | near_miss | 1.0（FP=0） |
| claude-sonnet-4-6 | fast | trigger_basic | 1.0 |
| claude-sonnet-4-6 | fast | near_miss | 1.0（FP=0） |
| claude-sonnet-4-6 | default | trigger_basic | 1.0 |
| claude-sonnet-4-6 | default | near_miss | 1.0（FP=0） |

`router_floor = composer_2/fast`（两个 scenario_pack 均达到 v2_tightened
pass_rate >= 0.82 硬门槛的最便宜组合；记录在 `router_floor_report.yaml`）。

> Si-Chip **不**训练 router 模型（规范 §5.2）。该扫描评估的是既有
> `model × thinking-depth` 组合，目的是找到达到 gate 阈值的最便宜单元——与
> v0.1.0 的做法一致，只是 harness 后端从确定性 SHA-256 模拟换成 real-LLM cache。

</div>

// CHAPTER 04 //

<div lang="en" markdown="1">

## 4. Cross-platform sync (drift = 0; v0.4.0)

| Tree | Files | SHA-of-SKILL.md | Drift |
|---|---|---|---|
| Source `.agents/skills/si-chip/` | 21 (incl. `DESIGN.md`) | identical | n/a (canonical) |
| Mirror `.cursor/skills/si-chip/` | 20 (no `DESIGN.md`) | identical | DRIFT_ZERO |
| Mirror `.claude/skills/si-chip/` | 20 (no `DESIGN.md`) | identical | DRIFT_ZERO |
| Tarball `docs/skills/si-chip-0.4.0.tar.gz` | 21 (incl. `DESIGN.md`) | identical (extracted) | reproducible |

Three-tree summary verdict: **ALL_TREES_DRIFT_ZERO**. Tarball SHA-256
`2cfcce00f989faf2467014e638b0ea1fa67870b5a1ee6b0531942be5a4be21ab`
(83060 bytes; deterministic options pinned via `--mtime
'2026-04-30 00:00:00 UTC'`).

</div>

<div lang="zh" markdown="1">

## 4. 跨平台同步（drift = 0；v0.4.0）

| 目录树 | 文件数 | SHA-of-SKILL.md | Drift |
|---|---|---|---|
| 源头 `.agents/skills/si-chip/` | 21（含 `DESIGN.md`） | identical | n/a（canonical） |
| 镜像 `.cursor/skills/si-chip/` | 20（无 `DESIGN.md`） | identical | DRIFT_ZERO |
| 镜像 `.claude/skills/si-chip/` | 20（无 `DESIGN.md`） | identical | DRIFT_ZERO |
| Tarball `docs/skills/si-chip-0.4.0.tar.gz` | 21（含 `DESIGN.md`） | identical（解压后） | reproducible |

三树汇总判定：**ALL_TREES_DRIFT_ZERO**。Tarball SHA-256
`2cfcce00f989faf2467014e638b0ea1fa67870b5a1ee6b0531942be5a4be21ab`
（83060 字节；确定性参数固定，`--mtime '2026-04-30 00:00:00 UTC'`）。

</div>

// CHAPTER 05 //

<div lang="en" markdown="1">

## 5. The 14 spec invariants (v0.4.0)

The default `python tools/spec_validator.py --json` run reports verdict
**PASS** at v0.4.0 (9 historical + 1 `REACTIVATION_DETECTOR_EXISTS` +
2 v0.3.0 additive + 3 v0.4.0 additive = 14 BLOCKERs):

```text
[BLOCKER] BAP_SCHEMA: PASS                                  (§2.1)
[BLOCKER] R6_KEYS: PASS (37 keys per §3.1; ignores method-tag suffixes)
[BLOCKER] THRESHOLD_TABLE: PASS (30 cells per §4.1)
[BLOCKER] ROUTER_MATRIX_CELLS: PASS (mvp=8, intermediate=16, full=96)
[BLOCKER] VALUE_VECTOR_AXES: PASS (version-aware: 7 ≤ v0.3.0; 8 @ v0.4.0+)
[BLOCKER] PLATFORM_PRIORITY: PASS (Cursor -> Claude Code -> Codex)
[BLOCKER] DOGFOOD_PROTOCOL: PASS (8 steps + 6 evidence files; 7 when round_kind=ship_prep)
[BLOCKER] FOREVER_OUT_LIST: PASS (4 items; re-affirmed in §14.6/§18.7/§19.6/§20.6/§21.6/§22.7/§23.7)
[BLOCKER] REACTIVATION_DETECTOR_EXISTS: PASS (all 6 §6.4 trigger ids)
[BLOCKER] CORE_GOAL_FIELD_PRESENT: PASS                     (§14, v0.3.0)
[BLOCKER] ROUND_KIND_TEMPLATE_VALID: PASS                   (§15, v0.3.0)
[BLOCKER] TOKEN_TIER_DECLARED_WHEN_REPORTED: PASS           (§18, v0.4.0)
[BLOCKER] REAL_DATA_FIXTURE_PROVENANCE: PASS                (§19, v0.4.0)
[BLOCKER] HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND: PASS     (§21, v0.4.0)
verdict: PASS
```

The `--strict-prose-count` mode passes against any v0.2.0 / v0.3.0 / v0.4.0
spec (since the §13.4 prose was reconciled to 37 / 30 at v0.2.0); it
intentionally fails on `R6_KEYS` and `THRESHOLD_TABLE` against the
historical `spec_v0.1.0.md` (28 / 21 prose) — both verdicts are pinned in
the v0.1.0 ship report under §13.4 for regression purposes.

</div>

<div lang="zh" markdown="1">

## 5. 14 项规范不变量（v0.4.0）

默认的 `python tools/spec_validator.py --json` 运行结果在 v0.4.0 为 verdict
**PASS**（9 条历史 + 1 条 `REACTIVATION_DETECTOR_EXISTS` + v0.3.0 新增 2 条 +
v0.4.0 新增 3 条 = 14 BLOCKER）：

```text
[BLOCKER] BAP_SCHEMA: PASS                                  (§2.1)
[BLOCKER] R6_KEYS: PASS (按 §3.1 共 37 key；忽略 method-tag 后缀)
[BLOCKER] THRESHOLD_TABLE: PASS (按 §4.1 共 30 cell)
[BLOCKER] ROUTER_MATRIX_CELLS: PASS (mvp=8, intermediate=16, full=96)
[BLOCKER] VALUE_VECTOR_AXES: PASS (版本敏感：v0.3.0 及以下 7 维；v0.4.0+ 8 维)
[BLOCKER] PLATFORM_PRIORITY: PASS (Cursor -> Claude Code -> Codex)
[BLOCKER] DOGFOOD_PROTOCOL: PASS (8 步 + 6 件证据；ship_prep 轮次 7 件)
[BLOCKER] FOREVER_OUT_LIST: PASS (4 项；§14.6/§18.7/§19.6/§20.6/§21.6/§22.7/§23.7 复申)
[BLOCKER] REACTIVATION_DETECTOR_EXISTS: PASS (§6.4 全部 6 个 trigger id)
[BLOCKER] CORE_GOAL_FIELD_PRESENT: PASS                     (§14，v0.3.0)
[BLOCKER] ROUND_KIND_TEMPLATE_VALID: PASS                   (§15，v0.3.0)
[BLOCKER] TOKEN_TIER_DECLARED_WHEN_REPORTED: PASS           (§18，v0.4.0)
[BLOCKER] REAL_DATA_FIXTURE_PROVENANCE: PASS                (§19，v0.4.0)
[BLOCKER] HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND: PASS     (§21，v0.4.0)
verdict: PASS
```

`--strict-prose-count` 模式在 v0.2.0 / v0.3.0 / v0.4.0 任一 spec 上都 PASS
（§13.4 散文已在 v0.2.0 对齐到 37 / 30）；只在历史 `spec_v0.1.0.md`（28 / 21
散文）上故意失败 `R6_KEYS` 与 `THRESHOLD_TABLE`——两个判定都已固定记录在
v0.1.0 ship report 的 §13.4，用于回归。

</div>

// CHAPTER 06 //

<div lang="en" markdown="1">

## 6. Reproduce the numbers locally

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip

# 1. Spec validator (14 invariants — verdict PASS)
python tools/spec_validator.py --json

# 2. Re-aggregate the included simulated baseline runs
python .agents/skills/si-chip/scripts/aggregate_eval.py \
  --runs-dir evals/si-chip/baselines/with_si_chip \
  --baseline-dir evals/si-chip/baselines/no_ability \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --templates-dir templates \
  --out /tmp/metrics_report.yaml

# 3. Confirm the v2_tightened packaging gate (metadata=94, body=4646, pass=true)
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .agents/skills/si-chip/SKILL.md --both \
  --budget-meta 100 --budget-body 5000 --json

# 4. (optional) Replay the Round 18 real-LLM cache at $0
#    See .agents/skills/si-chip/scripts/real_llm_runner_quickstart.md
python evals/si-chip/runners/real_llm_runner.py --help
```

</div>

<div lang="zh" markdown="1">

## 6. 在本地复现这些数字

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip

# 1. Spec validator (14 invariants — verdict PASS)
python tools/spec_validator.py --json

# 2. Re-aggregate the included simulated baseline runs
python .agents/skills/si-chip/scripts/aggregate_eval.py \
  --runs-dir evals/si-chip/baselines/with_si_chip \
  --baseline-dir evals/si-chip/baselines/no_ability \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --templates-dir templates \
  --out /tmp/metrics_report.yaml

# 3. Confirm v2_tightened packaging gate (metadata=94, body=4646, pass=true)
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .agents/skills/si-chip/SKILL.md --both \
  --budget-meta 100 --budget-body 5000 --json

# 4. (可选) 用 $0 回放 Round 18 real-LLM 缓存
#    详见 .agents/skills/si-chip/scripts/real_llm_runner_quickstart.md
python evals/si-chip/runners/real_llm_runner.py --help
```

</div>

// CHAPTER 07 //

<div lang="en" markdown="1">

## 7. What ships next (deferred from v0.4.0)

- `v3_strict` promotion (2 fresh rounds at v3 thresholds; single blocker
  is `metadata_tokens = 94` vs `<= 80`).
- Codex `.codex/` native runtime (still bridge-only at v0.4.0 per spec
  §11.2; re-evaluable after `v3_strict` is earned).
- Broader IDE coverage (OpenCode / Copilot CLI / Gemini CLI; spec §11.2
  deferred).
- Multi-tenant hosted API surface (spec §11.2 deferred).

See [`CHANGELOG.md`](https://github.com/YoRHa-Agents/Si-Chip/blob/main/CHANGELOG.md)
for the full v0.4.0 + v0.4.1 release notes (v0.4.1 is the doc-only patch
that produced this Pages tree).

</div>

<div lang="zh" markdown="1">

## 7. 后续交付（从 v0.4.0 延后）

- 升档至 `v3_strict`（在 v3 阈值下完成 2 轮新的 dogfood；唯一阻塞项是
  `metadata_tokens = 94` vs `<= 80`）。
- Codex `.codex/` 原生 runtime（v0.4.0 仍按规范 §11.2 仅 bridge；待
  `v3_strict` 达成后重新评估）。
- 更广义 IDE（OpenCode / Copilot CLI / Gemini CLI；规范 §11.2 延后）。
- Multi-tenant hosted API 表面（规范 §11.2 延后）。

完整的 v0.4.0 + v0.4.1 发版说明见
[`CHANGELOG.md`](https://github.com/YoRHa-Agents/Si-Chip/blob/main/CHANGELOG.md)
（v0.4.1 是产生本 Pages 树的纯文档 patch）。

</div>

// CHAPTER 08 //

<div lang="en" markdown="1">

## 8. Historical baseline — v0.1.0 ship (2026-04-28; v1_baseline)

The original Si-Chip ship was at `v1_baseline` with deterministic SHA-256
PROXY runners. Preserved here for regression / reproducibility.

| Round | pass_rate | trigger_F1 | metadata_tokens | per_invocation_footprint | wall_clock_p95 (s) | half_retire | router_floor |
|---|---|---|---|---|---|---|---|
| 1 | 0.85 | 0.89 | 78 | 4071 | 1.47 | keep | composer_2/default |
| 2 | 0.85 | 0.89 | 78 | 3598 (-11.6%) | 1.47 | keep | composer_2/default |

Round 2 also populated `R4_near_miss_FP_rate = 0.05`, slimming SKILL.md
body tokens from 2493 to 2020 (-18.97 %). The 7-axis value vector for
Round 1 is preserved below — note `task_delta = +0.35 >= +0.10` triggers
the `keep` rule per spec §6.2:

```yaml
value_vector:           # v0.1.0 — v0.3.0 used 7 axes
  task_delta: 0.35
  token_delta: -1.71
  latency_delta: -0.55
  context_delta: -1.71
  path_efficiency_delta: null
  routing_delta: 0.8934
  governance_risk_delta: 0.0
```

</div>

<div lang="zh" markdown="1">

## 8. 历史基线 —— v0.1.0 发版（2026-04-28；v1_baseline）

最早的 Si-Chip 发版是在 `v1_baseline` 档位、使用确定性 SHA-256 PROXY runner。
此处保留以便回归 / 复现。

| 轮次 | pass_rate | trigger_F1 | metadata_tokens | per_invocation_footprint | wall_clock_p95（秒） | half_retire | router_floor |
|---|---|---|---|---|---|---|---|
| 1 | 0.85 | 0.89 | 78 | 4071 | 1.47 | keep | composer_2/default |
| 2 | 0.85 | 0.89 | 78 | 3598 (-11.6%) | 1.47 | keep | composer_2/default |

Round 2 同时填充了 `R4_near_miss_FP_rate = 0.05`，并将 SKILL.md 正文 token
数从 2493 压缩到 2020（-18.97 %）。Round 1 的 7 维 value vector 见下——按规范
§6.2，`task_delta = +0.35 >= +0.10` 触发 `keep` 规则：

```yaml
value_vector:           # v0.1.0 — v0.3.0 都是 7 维
  task_delta: 0.35
  token_delta: -1.71
  latency_delta: -0.55
  context_delta: -1.71
  path_efficiency_delta: null
  routing_delta: 0.8934
  governance_risk_delta: 0.0
```

</div>
