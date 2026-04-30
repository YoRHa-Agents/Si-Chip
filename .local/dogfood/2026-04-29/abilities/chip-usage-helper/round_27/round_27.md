# Round 27 — Token Economy Re-Baseline + Targeted Trims (Cycle 6, post-v1.2.0)

**Date**: 2026-04-30 · **Branch**: `feature/v1.2.0-api-migration` · **Round kind**: `measurement_only` (per spec §15.2) · **Gate bound**: `v1_baseline`

## What happened
Token-tier measurement against v1.1.0 baseline (commit `8001e4e`) using tiktoken cl100k_base. Confirmed v1.2.0 grew the surface by **+5325 tokens** (15793 vs 10468; +50.9%). Applied conservative trims to comments-only / over-eager descriptions. **No functional change.** 130/130 tests pass; tool-contract intact; canvas-template-contract 22/22 intact.

## Trim summary (per measurement_post_trim.yaml)
| Tier | v1.1.0 | v1.2.0 pre-trim | v1.2.0 post-trim | Saved |
|---|---:|---:|---:|---:|
| EAGER (`rules/usage-helper.mdc`) | 378 | 378 | 378 | 0 |
| ON-CALL (`SKILL.md`) | 2144 | 2144 | 2144 | 0 |
| LAZY (`types.d.ts`) | 1159 | 3297 | 2961 | **−336** |
| LAZY (`empty-data.ts`) | 1164 | 1461 | 1155 | **−306** |
| LAZY (`usage.canvas.template.tsx`) | 5370 | 7980 | 7439 | **−541** |
| MCP tool descriptions (16 tools) | 253 | 533 | 390 | **−143** |
| **TOTAL** | **10468** | **15793** | **14467** | **−1326 (8.4%)** |

The trim recovered **24.9% of the v1.2.0 growth** without dropping any trigger token, contract assertion, or correctness test. Two MCP descriptions remain over the 30-token target (`get_me`, `get_agent_hours`) — explicitly accepted because their over-budget bytes carry essential trigger vocab (resolution chain, server-fixed-threshold caveat).

## Value vector
`task_delta=0.00, token_delta=+0.084, latency_delta=0.00, context_delta=+0.084, path_efficiency_delta=0.00, routing_delta=0.00, governance_risk_delta=0.00`. Two axes meet the v1_baseline +0.05 threshold; **token + context** axes both at +0.084 — shy of v2_tightened +0.10 by 0.016, queued for round 28 to push past.

## Decision
`keep` at `productized` stage. NO version bump (per dispatch §AC.7). Commits stack on `feature/v1.2.0-api-migration`. Round 28 is canvas information-density redesign (target: cross +0.10 axis to attempt v2_tightened promotion).
