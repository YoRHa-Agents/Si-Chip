# Round 28 — Canvas Information-Density Redesign (Cycle 6, post-round-27)

**Date**: 2026-04-30 · **Branch**: `feature/v1.2.0-api-migration` · **Round kind**: `code_change` · **Gate bound**: `v1_baseline`

## What happened
Targeted info-density redesign of `usage.canvas.template.tsx` per dispatch §28.2: typography hierarchy + truncation transparency + visual grouping for the 4 conditional supplementary sections. **No version bump** (per dispatch §AC.7). 130 → **133 tests** PASS (canvas-template-contract +3 assertions pinning the new invariants). typecheck/lint clean. +115 tokens (within +200 dispatch budget; measured via tiktoken cl100k_base).

## Changes (per measurement.yaml)
| Change | Lines | Tokens |
|---|---:|---:|
| `MoreRowsFooter` helper component (`+N more` truncation indicator) | +10 | ~+50 |
| Single `<H2>Cross-source &amp; advanced</H2>` group wrapper + subtitle + `hasSupplementary` boolean | +15 | ~+70 |
| Demote 4 supplementary section H2 → H3; replace verbose `<H2>+<Text>` with inline H3 | -8 | ~-20 |
| Add `<MoreRowsFooter>` usage in 3 leaderboard tables | +6 | ~+30 |
| Replace 4 individual `<Divider />` with 1 outer Divider (group-level) | -4 | ~-15 |
| **Net canvas template** | **+3** | **+115** |
| `mcp/tests/unit/canvas-template-contract.test.ts` (+3 round-28 invariant assertions) | +27 | n/a |

## Cycle 6 cumulative token axis (rounds 26 + 27 + 28)
| Round | Action | Surface tokens | Delta vs v1.1.0 |
|---|---|---:|---:|
| 26 | v1.2.0 ship (8 new tools + 4 new canvas sections) | 15793 | +5325 |
| 27 | trim (comments + descriptions) | 14467 | +3999 |
| 28 | canvas info-density redesign | 14582 | +4114 |
| **Dispatch net (rounds 27+28)** |  |  | **−1211 tokens recovered** = **+0.077 axis** (clears v1_baseline +0.05) |

## Value vector
`task_delta=0.00, token_delta=-0.008, latency_delta=0.00, context_delta=-0.008, path_efficiency_delta=0.00, routing_delta=0.00, governance_risk_delta=+0.01_qualitative` — round 28 standalone is a **reasoned negative** on the token axis (+115 tokens) in exchange for **+1 qualitative on U1 readability** and **+1 qualitative on V3 drift signal** (3 new contract tests pin the round-28 hierarchy → mechanical drift prevention).

## Decision
`keep` at `productized` stage. NO version bump. Round 29 is identity-flow consolidation (next v2_tightened promotion attempt: target C4 ≤ 7000 + an efficiency axis ≥ +0.10).
