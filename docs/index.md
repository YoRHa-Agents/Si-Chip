---
layout: default
title: Home
---

# Si-Chip

Persistent BasicAbility optimization factory.

[Install](./install/){: .btn .btn-blue} [User Guide](./userguide/){: .btn} [Architecture](./architecture/){: .btn} [Live Demo](./demo/){: .btn .btn-green}

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

- No marketplace.
- No router model training.
- No Markdown-to-CLI converter.
- No generic IDE compatibility layer.

PRs introducing any of these will be closed without review.
