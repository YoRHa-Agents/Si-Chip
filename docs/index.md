---
layout: default
title: Home
---

<div lang="en" markdown="1">

# Si-Chip

Persistent BasicAbility optimization factory.

[▶ INSTALL](./install/){:.btn} [▶ USER GUIDE](./userguide/){:.btn} [▶ ARCHITECTURE](./architecture/){:.btn} [▶ LIVE DEMO](./demo/){:.btn .btn-green}

> **Status (v0.1.0):** SHIP_ELIGIBLE at gate `relaxed` (= `v1_baseline`).
> 2 consecutive `v1_baseline` passes — eligible for `v2_tightened` promotion in a follow-up release.

## What is Si-Chip?

Si-Chip is a persistent **BasicAbility optimization factory**. Its first-class
object is the `BasicAbility`, not any particular file shape. It improves
abilities through metric-driven, multi-round dogfood loops:

```
profile -> evaluate -> diagnose -> improve -> router-test -> half-retire-review -> iterate -> package-register
```

Si-Chip ships **as its own first user**: the included v0.1.0 release is the
result of two complete dogfood rounds run against Si-Chip itself.

## Headline numbers (v0.1.0 ship)

| Dimension | Round 1 | Round 2 | v1_baseline gate |
|---|---|---|---|
| pass_rate | 0.85 | 0.85 | >= 0.75 |
| trigger_F1 | 0.89 | 0.89 | >= 0.80 |
| metadata tokens | 78 | 78 | <= 120 |
| per-invocation footprint | 4071 | 3598 (-11.6%) | <= 9000 |
| wall_clock_p95 (s) | 1.47 | 1.47 | <= 45 |
| half_retire decision | keep | keep | numeric vv |
| router_floor | composer_2/default | composer_2/default | spec section 5.3 |

See the [demo page](./demo/) for the full ship-report walkthrough.

## Quick install

Cursor and Claude Code auto-discover the included Skill mirrors. See
[Install](./install/) for full instructions.

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
python tools/spec_validator.py --json    # 8 invariants — verdict PASS
```

## Out of scope (per spec section 11.1)

- Skill / plugin marketplace
- Router model training
- Markdown-to-CLI converter
- Generic IDE compatibility layer

PRs introducing any of these will be closed without review.

</div>

<div lang="zh" markdown="1">

# Si-Chip

持久化的 BasicAbility 优化工厂。

[▶ 安装](./install/){:.btn} [▶ 用户指南](./userguide/){:.btn} [▶ 架构](./architecture/){:.btn} [▶ 演示](./demo/){:.btn .btn-green}

> **状态（v0.1.0）：** 在 gate `relaxed`（即 `v1_baseline`）档位达到 SHIP_ELIGIBLE。
> 已完成 2 轮连续 `v1_baseline` 通过 — 符合在后续版本升档至 `v2_tightened` 的资格。

## 什么是 Si-Chip？

Si-Chip 是一个持久化的 **BasicAbility 优化工厂**。它的第一类对象是
`BasicAbility`，而不是任何特定的文件形态。它通过指标驱动的多轮 dogfood
循环来改进能力：

```
profile -> evaluate -> diagnose -> improve -> router-test -> half-retire-review -> iterate -> package-register
```

Si-Chip 以自身作为第一个用户进行交付：本仓库附带的 v0.1.0 版本即为对
Si-Chip 自身运行两轮完整 dogfood 后产出的结果。

## 关键指标（v0.1.0 交付）

| 指标 | Round 1 | Round 2 | v1_baseline 阈值 |
|---|---|---|---|
| pass_rate | 0.85 | 0.85 | >= 0.75 |
| trigger_F1 | 0.89 | 0.89 | >= 0.80 |
| metadata tokens | 78 | 78 | <= 120 |
| per-invocation footprint | 4071 | 3598 (-11.6%) | <= 9000 |
| wall_clock_p95（秒） | 1.47 | 1.47 | <= 45 |
| half_retire 决策 | keep | keep | 数值 value_vector |
| router_floor | composer_2/default | composer_2/default | 规范 §5.3 |

完整的 ship-report 走查详见 [演示页面](./demo/)。

## 快速安装

Cursor 与 Claude Code 会自动发现本仓库内置的 Skill 镜像。完整说明见
[安装](./install/)。

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
python tools/spec_validator.py --json    # 8 项不变量 — verdict PASS
```

## 范围之外（依据规范 §11.1）

- Skill / plugin marketplace（技能 / 插件市场）
- Router model training（路由模型训练）
- Markdown-to-CLI converter（Markdown 到 CLI 转换器）
- Generic IDE compatibility layer（通用 IDE 兼容层）

任何引入上述方向的 PR 将被直接关闭，不进入评审。

</div>
