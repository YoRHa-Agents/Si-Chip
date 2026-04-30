# Round 30 — v2.0.0-pre Release (Cycle 6 close)

**Date**: 2026-04-30 · **Branch**: `feature/v1.2.0-api-migration` · **Round kind**: `ship_prep` · **Gate bound**: `v1_baseline` · **Release state**: `pre_release`

## What happened
Major-version pre-release marker for the v1.x ai-bill REST migration arc. Bumped 10 anchors from `1.2.0` → `2.0.0-pre`, prepended a v2.0.0-pre entry to `CHANGELOG.md` (above v1.2.0), built `dist/chip-usage-helper-2.0.0-pre.tgz` (377,207 bytes; sha256 `c74d6b0e...`), and ran `npm run package:smoke` (PASS, 16 tools detected). **133/133 tests PASS** post-bump; **typecheck clean** post-bump. npm did NOT reject the `2.0.0-pre` semver — we did NOT need the `2.0.0-pre.0` fallback.

## Anchors bumped (10)
| File | Anchor |
|---|---|
| `mcp/package.json` | `"version": "2.0.0-pre"` |
| `package.json` | `"version": "2.0.0-pre"` + `scripts.package:inspect` tarball name |
| `.cursor-plugin/plugin.json` | `"version": "2.0.0-pre"` |
| `scripts/package-plugin.mjs` | `const VERSION = "2.0.0-pre"` |
| `scripts/package-smoke-test.mjs` | `const VERSION = "2.0.0-pre"` |
| `mcp/src/index.ts` | server constructor `version: "2.0.0-pre"` |
| `mcp/package-lock.json` | self-version (top + lockfile workspace entry) |
| `README.md` | install paths + `### Packaged v2.0.0-pre` heading |
| `docs/user-guide.md` | install paths + `Version:` header |
| `docs/admin-integration-guide.md` | install paths + `Version:` header |

## Cycle 6 cumulative — full v1.x → v2.x arc
| Round | Action | Surface tokens | Tests | Notes |
|---|---|---:|---:|---|
| 26 | v1.2.0 ship (ai-bill REST migration + 8 new tools) | 15793 | 130/130 | +5325 vs v1.1.0; 9 → 16 tools |
| 27 | trim (comments + descriptions) | 14467 | 130/130 | −1326 trim recovery |
| 28 | canvas info-density redesign | 14582 | 133/133 | +115 for hierarchy + 3 contract assertions |
| 29 | identity-flow doc consolidation | 14582 | 133/133 | 0 token cost; +0.05 V3 governance |
| **30** | **v2.0.0-pre release marker** | **14582** | **133/133** | **+1211 cumulative trim recovery; major-bump pre-release shipped** |
| **Cumulative dispatch (rounds 27-30)** | | | | **+1211 tokens net recovered = +0.077 axis (clears v1_baseline +0.05)** |

## Value vector (cumulative cycle 6)
`task_delta=0.00 (correctness floor preserved through 116→133 tests; no regression), token_delta=+0.077 (clears v1_baseline +0.05; SHY of v2_tightened +0.10 by 0.023), latency_delta=null (Cycle 7 baseline), context_delta=+0.077, path_efficiency_delta=null, routing_delta=0.00 (router-stable across 4 rounds), governance_risk_delta=+0.20 qualitative (migration_axis_tracking + canvas-template-contract + identity-flow doc + CHANGELOG breaking-changes restated)`

## Decision
**SHIP** at gate `v1_baseline`; release_state = `pre_release`. Lifecycle stage = `productized` (unchanged). Cycle 7 = production validation (1-2 weeks); v2.0.0 stable IFF green. Cycle 8 = identity-flow code refactor for v2_tightened gate promotion. **Tarball**: `dist/chip-usage-helper-2.0.0-pre.tgz` (377,207 bytes; sha256 `c74d6b0ea0c571c09532674516cdac5747fa58757a73a9278b7c036f88c16b8f`).
