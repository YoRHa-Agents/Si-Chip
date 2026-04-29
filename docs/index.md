---
layout: default
title: Home
---

<div lang="en" markdown="1">

Persistent BasicAbility optimization factory.

[▶ INSTALL](./install/){:.btn} [▶ USER GUIDE](./userguide/){:.btn} [▶ ARCHITECTURE](./architecture/){:.btn} [▶ CHANGELOG](./changelog/){:.btn} [▶ LIVE DEMO](./demo/){:.btn .btn-green}

> **Status (v0.2.0):** SHIP_ELIGIBLE at gate `relaxed` (= `v1_baseline`; same as v0.1.0 ship).
> 13 consecutive `v1_baseline` passes across the v0.2.0 iteration cycle.
> `v2_tightened` promotion deferred to v0.3.0 pending real-LLM runner upgrade
> (current `T2_pass_k = 0.5478` fails `v2_tightened ≥ 0.55` by -0.0022 via
> the `pass_k_4 = pass_rate^4` PROXY formula; real k=4 sampling expected
> to clear).

## What is Si-Chip?

Si-Chip is a persistent **BasicAbility optimization factory**. Its first-class
object is the `BasicAbility`, not any particular file shape. It improves
abilities through metric-driven, multi-round dogfood loops:

```
profile -> evaluate -> diagnose -> improve -> router-test -> half-retire-review -> iterate -> package-register
```

Si-Chip ships **as its own first user**: the v0.2.0 release is the result of
**13 complete dogfood rounds** run against Si-Chip itself, building on the
v0.1.0 ship (which itself ran 2 rounds).

## Headline numbers (v0.2.0 ship)

| metric | v0.1.0 | v0.2.0 | ceiling (v1_baseline) |
|---|---:|---:|---:|
| pass_rate | 0.85 | 0.85 | ≥ 0.75 |
| trigger_F1 | 0.89 | 0.8934 | ≥ 0.80 |
| per-invocation footprint | 4071 / 3598 | 3704 | ≤ 9000 |
| wall_clock_p95 (s) | 1.47 | 1.4693 s | ≤ 45 s |
| routing_latency_p95 | n/a | 1100 ms | ≤ 2000 ms |
| R6 metric coverage | 8 MVP | 28/37 measured across 6 of 7 dims | ≥ 8 MVP |
| reactivation triggers | 0 | 6 coded (§6.4) | ≥ 5 per §6.4 |

See the [demo page](./demo/) for the full ship-report walkthrough and the
[changelog](./changelog/) for the per-round v0.1.x → v0.2.0 story.

## What's new in v0.2.0

- **R6 coverage** at 6 of 7 dimensions full or near-full (D1 3/4, D2 5/6,
  D3 4/7, D4 1/4, D5 4/4 FULL, D6 7/8 measured, D7 4/4 FULL).
- **§6.4 Reactivation Detector** at `tools/reactivation_detector.py` with
  all 6 triggers + 31 unit tests.
- **Spec reconciliation** v0.1.0 → v0.2.0 (prose 28 → 37 sub-metrics; 21 →
  30 threshold cells); §3/§4/§5/§6/§7/§8/§11 Normative semantics
  byte-identical to v0.1.0.
- **16-cell intermediate router-test profile** added Round 9 (additive to
  8-cell MVP and 96-cell Full).
- **Installer telemetry** validates the v0.1.1 one-line installer claim
  (U3=1 step non-interactive; U4≈0.0073 s dry-run floor estimate).
- **Spec validator** at 9 BLOCKER invariants (was 8); accepts v0.1.0 /
  v0.2.0-rc1 / v0.2.0 (backward-compat).
- **Deterministic tarball** `docs/skills/si-chip-0.2.0.tar.gz`
  (1 SKILL.md + 5 references + 3 scripts).

## Quick install

Cursor and Claude Code auto-discover the included Skill mirrors. See
[Install](./install/) for full instructions.

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
python tools/spec_validator.py --json    # 9 invariants — verdict PASS
```

## Out of scope (per spec section 11.1)

- Skill / plugin marketplace
- Router model training
- Markdown-to-CLI converter
- Generic IDE compatibility layer

PRs introducing any of these will be closed without review.

## Install v0.2.0

    curl -fsSL https://raw.githubusercontent.com/YoRHa-Agents/Si-Chip/main/install.sh | bash -s -- --yes --target cursor --scope repo

or

    wget https://github.com/YoRHa-Agents/Si-Chip/releases/download/v0.2.0/si-chip-0.2.0.tar.gz
    tar xzf si-chip-0.2.0.tar.gz -C .agents/skills/

</div>

<div lang="zh" markdown="1">

持久化的 BasicAbility 优化工厂。

[▶ 安装](./install/){:.btn} [▶ 用户指南](./userguide/){:.btn} [▶ 架构](./architecture/){:.btn} [▶ 更新日志](./changelog/){:.btn} [▶ 演示](./demo/){:.btn .btn-green}

> **状态（v0.2.0）：** 在 gate `relaxed`（即 `v1_baseline`，与 v0.1.0 同档）达到 SHIP_ELIGIBLE。
> 在 v0.2.0 迭代周期中累计 13 轮连续 `v1_baseline` 通过。
> `v2_tightened` 升档延后至 v0.3.0，等待 real-LLM runner 解锁
> （当前 `T2_pass_k = 0.5478` 经 `pass_k_4 = pass_rate^4` PROXY 公式
> 距 `v2_tightened ≥ 0.55` 仅差 -0.0022；real k=4 采样预期可通过）。

## 什么是 Si-Chip？

Si-Chip 是一个持久化的 **BasicAbility 优化工厂**。它的第一类对象是
`BasicAbility`，而不是任何特定的文件形态。它通过指标驱动的多轮 dogfood
循环来改进能力：

```
profile -> evaluate -> diagnose -> improve -> router-test -> half-retire-review -> iterate -> package-register
```

Si-Chip 以自身作为第一个用户进行交付：本仓库附带的 v0.2.0 版本是对
Si-Chip 自身运行 **13 轮完整 dogfood**（在 v0.1.0 已完成 2 轮基础上）后产出的结果。

## 关键指标（v0.2.0 交付）

| 指标 | v0.1.0 | v0.2.0 | v1_baseline 阈值 |
|---|---:|---:|---:|
| pass_rate | 0.85 | 0.85 | ≥ 0.75 |
| trigger_F1 | 0.89 | 0.8934 | ≥ 0.80 |
| per-invocation footprint | 4071 / 3598 | 3704 | ≤ 9000 |
| wall_clock_p95（秒） | 1.47 | 1.4693 s | ≤ 45 s |
| routing_latency_p95 | n/a | 1100 ms | ≤ 2000 ms |
| R6 子指标覆盖 | 8 MVP | 28/37 measured，覆盖 6/7 维 | ≥ 8 MVP |
| §6.4 reactivation triggers | 0 | 6 coded | ≥ 5 per §6.4 |

完整的 ship-report 走查详见 [演示页面](./demo/)，每轮 v0.1.x → v0.2.0 故事详见
[更新日志](./changelog/)。

## v0.2.0 新增亮点

- **R6 维度覆盖**：6 / 7 个维度达到完整或接近完整（D1 3/4、D2 5/6、
  D3 4/7、D4 1/4、D5 4/4 FULL、D6 7/8 measured、D7 4/4 FULL）。
- **§6.4 Reactivation Detector**：`tools/reactivation_detector.py`
  涵盖全部 6 个 trigger + 31 个单元测试。
- **Spec reconciliation** v0.1.0 → v0.2.0（prose 28 → 37 sub-metrics；
  21 → 30 threshold cells）；§3/§4/§5/§6/§7/§8/§11 Normative 语义
  与 v0.1.0 字节级一致。
- **16-cell intermediate router-test profile**（Round 9 新增；与 8-cell
  MVP / 96-cell Full 共存）。
- **Installer telemetry** 验证 v0.1.1 一行安装器说法
  （U3=1 步非交互；U4≈0.0073 s dry-run floor estimate）。
- **Spec validator** 升至 9 个 BLOCKER 不变量（原 8 个）；同时接受
  v0.1.0 / v0.2.0-rc1 / v0.2.0（向后兼容）。
- **Deterministic tarball** `docs/skills/si-chip-0.2.0.tar.gz`
  （1 SKILL.md + 5 references + 3 scripts）。

## 快速安装

Cursor 与 Claude Code 会自动发现本仓库内置的 Skill 镜像。完整说明见
[安装](./install/)。

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
python tools/spec_validator.py --json    # 9 项不变量 — verdict PASS
```

## 范围之外（依据规范 §11.1）

- Skill / plugin marketplace（技能 / 插件市场）
- Router model training（路由模型训练）
- Markdown-to-CLI converter（Markdown 到 CLI 转换器）
- Generic IDE compatibility layer（通用 IDE 兼容层）

任何引入上述方向的 PR 将被直接关闭，不进入评审。

## 安装 v0.2.0

    curl -fsSL https://raw.githubusercontent.com/YoRHa-Agents/Si-Chip/main/install.sh | bash -s -- --yes --target cursor --scope repo

或

    wget https://github.com/YoRHa-Agents/Si-Chip/releases/download/v0.2.0/si-chip-0.2.0.tar.gz
    tar xzf si-chip-0.2.0.tar.gz -C .agents/skills/

</div>
