# Round 29 — Identity Flow Consolidation Review (Cycle 6, post-round-28)

**Date**: 2026-04-30 · **Branch**: `feature/v1.2.0-api-migration` · **Round kind**: `code_change` (doc-only) · **Gate bound**: `v1_baseline`

## What happened
Read-only review of the post-v1.2.0 identity flow per dispatch §29.1 + §29.2, followed by light doc-only changes. Verified the chain `resolveMe() → me.email → emailLocalpart() → asUserHeader(me) → endpoints with X-User-Name` end-to-end across `mcp/src/util/{me,cursor-ide-state,email}.ts` + `mcp/src/tools/{get-me,diagnose-identity}.ts`. **No orphan code found** — every helper feeds the chain or is consumed by it. Decision per dispatch rationale: KEEP the multi-source resolver (avoids single-source coupling) + DOCUMENT its post-v1.2.0 role explicitly. **No version bump** (v2.0.0-pre is the round-30 commit).

## Doc additions (3 surfaces)
| File | Lines | Tier | Content |
|---|---:|---|---|
| `mcp/src/util/me.ts` | +10 | `///` JSDoc (out-of-tier) | Top-of-file addendum: post-v1.2.0 X-User-Name role + lookup precedence + cost characterization (O(1) IO, cached) + rationale for keeping multi-source in v2.0.0-pre |
| `docs/admin-integration-guide.md` | +49 | admin docs (out-of-tier) | New `## Identity flow (v2.0.0-pre)` section with ASCII chain visualization + "why keep the multi-source resolver?" justification |
| `README.md` | +11 | user docs (out-of-tier) | New `### Identity & X-User-Name` sub-section under `## How it works`; cross-link to admin guide |
| **Net source change** | **0 LOC executable** | | |

## Cycle 6 cumulative token axis (rounds 26 + 27 + 28 + 29) — UNCHANGED from round 28
| Round | Action | Surface tokens | Delta vs v1.1.0 |
|---|---|---:|---:|
| 26 | v1.2.0 ship | 15793 | +5325 |
| 27 | trim | 14467 | +3999 |
| 28 | canvas redesign | 14582 | +4114 |
| 29 | doc-only consolidation | 14582 | +4114 (0 delta) |
| **Dispatch net (rounds 27+28+29)** |  |  | **−1211 tokens recovered** = **+0.077 axis** (clears v1_baseline +0.05) |

## Value vector
`task_delta=0.00, token_delta=0.00, latency_delta=0.00, context_delta=0.00, path_efficiency_delta=0.00, routing_delta=0.00, governance_risk_delta=+0.05` — round 29 is the most conservative `code_change` round in Cycle 6 (one .ts JSDoc + two markdown docs; no executable code). The +0.05 governance_risk axis captures the new identity-flow audit trail: future maintainers proposing single-source coupling will encounter all three doc surfaces and have to defeat the recorded v2.0.0-pre rationale before they can ship.

## Decision
`keep` at `productized` stage. NO version bump (round 30 = v2.0.0-pre release commit). **133/133 tests PASS** post-doc-update; **typecheck clean** post-doc-update. Round 30 (v2.0.0-pre release) is the next action; round 31 = post-release production validation in Cycle 7; round 32+ = deferred identity-flow code-extraction refactor for v2_tightened gate promotion.
