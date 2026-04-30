---
layout: default
title: Home
---

<div lang="en" markdown="1">

Persistent BasicAbility optimization factory.

[▶ INSTALL](./install/){:.btn} [▶ USER GUIDE](./userguide/){:.btn} [▶ ARCHITECTURE](./architecture/){:.btn} [▶ CHANGELOG](./changelog/){:.btn} [▶ LIVE DEMO](./demo/){:.btn .btn-green}

> **Status (v0.4.0):** SHIP_ELIGIBLE at gate `standard` (= `v2_tightened`).
> **FIRST Si-Chip release at `v2_tightened`** (vs v0.2.0 / v0.3.0 at `relaxed`).
> 19 consecutive `v1_baseline` + 2 consecutive `v2_tightened` passes
> (Round 18 + Round 19). `T2_pass_k` unblocked via
> `evals/si-chip/runners/real_llm_runner.py` — Round 18 ran k=4 sampling
> against `claude-haiku-4-5` + `claude-sonnet-4-6` via Veil litellm-local
> at `127.0.0.1:8086` ($0.20 spend, 640 calls); Round 19 replayed at 100%
> cache hit ($0). `v3_strict` deferred to v0.4.x — single blocker is
> `metadata_tokens = 94` vs `≤ 80` budget.

## What is Si-Chip?

Si-Chip is a persistent **BasicAbility optimization factory**. Its first-class
object is the `BasicAbility`, not any particular file shape. It improves
abilities through metric-driven, multi-round dogfood loops:

```
profile -> evaluate -> diagnose -> improve -> router-test -> half-retire-review -> iterate -> package-register
```

Si-Chip ships **as its own first user**: the v0.4.0 release is the result of
**19 complete dogfood rounds** run against Si-Chip itself, building on the
v0.1.0 ship (2 rounds), v0.2.0 ship (+11), v0.3.0 ship (+2), v0.4.0 ship (+4).

## Headline numbers (v0.4.0 ship)

| metric | v0.1.0 | v0.4.0 (Round 18-19) | ceiling (v2_tightened) |
|---|---:|---:|---:|
| pass_rate | 0.85 | 1.0 best cell, 0.9719 mean | ≥ 0.82 |
| T2_pass_k | 0.5478 (PROXY) | 1.0 best cell | ≥ 0.55 |
| trigger_F1 | 0.89 | 1.0 | ≥ 0.85 |
| near_miss_FP_rate | 0.05 | 0.0 | ≤ 0.10 |
| metadata_tokens | 78 | 94 | ≤ 100 |
| per-invocation footprint | 4071 | 4726 | ≤ 7000 |
| wall_clock_p95 (s) | 1.47 | 17.5726 s | ≤ 30 s |
| routing_latency_p95 | n/a | 0.16 ms | ≤ 1200 ms |
| routing_token_overhead | n/a | 0.0233 | ≤ 0.12 |
| iteration_delta (task_quality) | +0.31 (context_delta) | +0.4522 (Round 18) | ≥ +0.10 |

See the [demo page](./demo/) for the full ship-report walkthrough and the
[changelog](./changelog/) for the per-round v0.1.x → v0.4.0 story.

## What's new in v0.4.0

- **§18 Token-Tier Invariant** — `token_tier {C7_eager_per_session,
  C8_oncall_per_trigger, C9_lazy_avg_per_load}` decomposition; OPTIONAL
  EAGER-weighted `iteration_delta` formula; `lazy_manifest` packaging gate.
- **§19 Real-Data Verification** — 3-layer pattern (msw fixture provenance
  + user-install + post-recovery live verification); BLOCKER 13
  `REAL_DATA_FIXTURE_PROVENANCE`.
- **§20 Stage Transitions & Promotion History** — `stage_transition_table`
  forbids reverse transitions; `promotion_history` append-only;
  `ship_decision.yaml` is the **7th evidence file** when
  `round_kind == ship_prep`.
- **§21 Health Smoke Check** — 4-axis `{read, write, auth, dependency}`
  pre-ship probes; REQUIRED when `live_backend: true`; BLOCKER 14
  `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`.
- **§22 Eval-Pack Curation** — 40-prompt minimum @ `v2_tightened`; G1
  `_provenance` REQUIRED; deterministic seeding `hash(round_id + ability_id)`.
- **§23 Method-Tagged Metrics** — `<metric>_method` companion fields,
  `_ci_low` / `_ci_high` 95% CI bands, `U1_language_breakdown`, `U4_state`.
- **§6.1 value_vector axes 7 → 8** — adds `eager_token_delta` (FIRST
  byte-identicality break since v0.1.0 → v0.2.0 prose-count alignment).
- **Real-LLM runner** at `evals/si-chip/runners/real_llm_runner.py` (884
  LoC + 27 tests) — first dogfood-side invocation against real models
  unblocks `T2_pass_k` v2_tightened.
- **Spec validator** at 14 BLOCKER invariants (was 11 at v0.3.0); accepts
  v0.1.0 / v0.2.0 / v0.3.0 / v0.4.0-rc1 / v0.4.0 (backward-compat).
- **AGENTS.md §13** at 13 hard rules (was 10 at v0.3.0).
- **Deterministic tarball** `docs/skills/si-chip-0.4.0.tar.gz` (SHA-256
  `2cfcce00f989faf2467014e638b0ea1fa67870b5a1ee6b0531942be5a4be21ab`;
  1 SKILL.md + 1 DESIGN.md + 14 references + 5 scripts; 21 files).

## Quick install

Cursor and Claude Code auto-discover the included Skill mirrors. See
[Install](./install/) for full instructions.

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
python tools/spec_validator.py --json    # 14 invariants — verdict PASS
```

## Out of scope (per spec section 11.1)

- Skill / plugin marketplace
- Router model training
- Markdown-to-CLI converter
- Generic IDE compatibility layer

PRs introducing any of these will be closed without review.

## Install v0.4.0

    curl -fsSL https://raw.githubusercontent.com/YoRHa-Agents/Si-Chip/main/install.sh | bash -s -- --yes --target cursor --scope repo

or

    wget https://github.com/YoRHa-Agents/Si-Chip/releases/download/v0.4.0/si-chip-0.4.0.tar.gz
    tar xzf si-chip-0.4.0.tar.gz -C .agents/skills/

</div>

<div lang="zh" markdown="1">

持久化的 BasicAbility 优化工厂。

[▶ 安装](./install/){:.btn} [▶ 用户指南](./userguide/){:.btn} [▶ 架构](./architecture/){:.btn} [▶ 更新日志](./changelog/){:.btn} [▶ 演示](./demo/){:.btn .btn-green}

> **状态（v0.4.0）：** 在 gate `standard`（即 `v2_tightened`）达到 SHIP_ELIGIBLE。
> **Si-Chip 首次在 `v2_tightened` 档位发版**（v0.2.0 / v0.3.0 仍在 `relaxed`）。
> 19 轮连续 `v1_baseline` + 2 轮连续 `v2_tightened`（Round 18 + Round 19）。
> `T2_pass_k` 由 `evals/si-chip/runners/real_llm_runner.py` 解锁——
> Round 18 通过 Veil litellm-local（`127.0.0.1:8086`）在 `claude-haiku-4-5` +
> `claude-sonnet-4-6` 上跑 k=4 采样（$0.20、640 次调用）；Round 19 用 100%
> 命中的 cache replay（$0）完成第二轮通过。`v3_strict` 延后到 v0.4.x——唯一
> 阻塞项是 `metadata_tokens = 94` vs `≤ 80` 预算。

## 什么是 Si-Chip？

Si-Chip 是一个持久化的 **BasicAbility 优化工厂**。它的第一类对象是
`BasicAbility`，而不是任何特定的文件形态。它通过指标驱动的多轮 dogfood
循环来改进能力：

```
profile -> evaluate -> diagnose -> improve -> router-test -> half-retire-review -> iterate -> package-register
```

Si-Chip 以自身作为第一个用户进行交付：v0.4.0 是对 Si-Chip 自身运行 **19 轮
完整 dogfood** 后产出的结果（v0.1.0 完成 2 轮、v0.2.0 加 11 轮、v0.3.0 加 2 轮、
v0.4.0 加 4 轮）。

## 关键指标（v0.4.0 交付）

| 指标 | v0.1.0 | v0.4.0（Round 18-19） | 上限（v2_tightened） |
|---|---:|---:|---:|
| pass_rate | 0.85 | 1.0 best cell，0.9719 mean | ≥ 0.82 |
| T2_pass_k | 0.5478（PROXY） | 1.0 best cell | ≥ 0.55 |
| trigger_F1 | 0.89 | 1.0 | ≥ 0.85 |
| near_miss_FP_rate | 0.05 | 0.0 | ≤ 0.10 |
| metadata_tokens | 78 | 94 | ≤ 100 |
| per-invocation footprint | 4071 | 4726 | ≤ 7000 |
| wall_clock_p95（秒） | 1.47 | 17.5726 s | ≤ 30 s |
| routing_latency_p95 | n/a | 0.16 ms | ≤ 1200 ms |
| routing_token_overhead | n/a | 0.0233 | ≤ 0.12 |
| iteration_delta（task_quality） | +0.31（context_delta） | +0.4522（Round 18） | ≥ +0.10 |

完整的 ship-report 走查详见 [演示页面](./demo/)，每轮 v0.1.x → v0.4.0 故事详见
[更新日志](./changelog/)。

## v0.4.0 新增亮点

- **§18 Token-Tier Invariant** —— `token_tier {C7_eager_per_session,
  C8_oncall_per_trigger, C9_lazy_avg_per_load}` 三层分解；可选 EAGER 加权
  `iteration_delta` 公式；`lazy_manifest` 打包闸门。
- **§19 Real-Data Verification** —— 三层模式（msw fixture 溯源 + user-install
  + post-recovery live verification）；BLOCKER 13 `REAL_DATA_FIXTURE_PROVENANCE`。
- **§20 Stage Transitions & Promotion History** —— `stage_transition_table`
  禁止反向迁移；`promotion_history` 仅可追加；当 `round_kind == ship_prep`
  时新增 **第 7 件证据文件** `ship_decision.yaml`。
- **§21 Health Smoke Check** —— 4 维 `{read, write, auth, dependency}`
  pre-ship probe；当 `live_backend: true` 时 REQUIRED；BLOCKER 14
  `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`。
- **§22 Eval-Pack Curation** —— `v2_tightened` 最少 40 prompt；G1 `_provenance`
  REQUIRED；确定性种子 `hash(round_id + ability_id)`。
- **§23 Method-Tagged Metrics** —— `<metric>_method` 伴随字段、`_ci_low` /
  `_ci_high` 95% CI 区间、`U1_language_breakdown`、`U4_state`。
- **§6.1 value_vector 7 → 8 维** —— 新增 `eager_token_delta`（自 v0.1.0 → v0.2.0
  prose-count alignment 之后首次破坏字节一致性）。
- **Real-LLM runner** `evals/si-chip/runners/real_llm_runner.py`（884 LoC + 27
  tests）—— dogfood 侧首次对接真实模型，解锁 `T2_pass_k` v2_tightened。
- **Spec validator** 升至 14 个 BLOCKER（v0.3.0 时 11 个）；接受
  v0.1.0 / v0.2.0 / v0.3.0 / v0.4.0-rc1 / v0.4.0（向后兼容）。
- **AGENTS.md §13** 升至 13 条 hard rules（v0.3.0 时 10 条）。
- **Deterministic tarball** `docs/skills/si-chip-0.4.0.tar.gz`（SHA-256
  `2cfcce00f989faf2467014e638b0ea1fa67870b5a1ee6b0531942be5a4be21ab`；
  1 SKILL.md + 1 DESIGN.md + 14 references + 5 scripts；21 个文件）。

## 快速安装

Cursor 与 Claude Code 会自动发现本仓库内置的 Skill 镜像。完整说明见
[安装](./install/)。

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
python tools/spec_validator.py --json    # 14 项不变量 — verdict PASS
```

## 范围之外（依据规范 §11.1）

- Skill / plugin marketplace（技能 / 插件市场）
- Router model training（路由模型训练）
- Markdown-to-CLI converter（Markdown 到 CLI 转换器）
- Generic IDE compatibility layer（通用 IDE 兼容层）

任何引入上述方向的 PR 将被直接关闭，不进入评审。

## 安装 v0.4.0

    curl -fsSL https://raw.githubusercontent.com/YoRHa-Agents/Si-Chip/main/install.sh | bash -s -- --yes --target cursor --scope repo

或

    wget https://github.com/YoRHa-Agents/Si-Chip/releases/download/v0.4.0/si-chip-0.4.0.tar.gz
    tar xzf si-chip-0.4.0.tar.gz -C .agents/skills/

</div>
