# Health Smoke Check — R12 Summary (Spec §21)

> Reader-friendly summary of the §21 health-smoke-check Normative
> chapter (v0.4.0-rc1). Authoritative sources:
> `.local/research/spec_v0.4.0-rc1.md` §21 and
> `.local/research/r12_v0_4_0_industry_practice.md` §2.6 + §4.4.

## Why this section exists

chip-usage-helper Cycle 5 v0.9.0 was spec-compliant the moment it
shipped: six evidence files, green eval pack, bound router floor.
Production ai-bill returned `latestTsMs: 0` within hours of ship and
the dashboard silently crashed. §8's frozen eight-step protocol had
**no pre-ship live-backend probe**; the rest of industry (GitHub
Actions URL health checks, fitgap post-deploy 4-axis verification)
has made such probes standard for a decade. §21 lifts that pattern
into the Normative layer so ability authors cannot ship against a
degraded backend without explicitly overriding.

## `health_smoke_check` schema (§21.1)

`BasicAbility.packaging.health_smoke_check` is OPTIONAL at schema
level. Each entry declares:

| Field | Type | Meaning |
|---|---|---|
| `endpoint` | URL string | Probed backend endpoint |
| `expected_status` | int | Expected HTTP status (typically 200; some 204) |
| `max_attempts` | int | Retry cap (default 3) |
| `retry_delay_ms` | int | Retry spacing (default 1000) |
| `sentinel_field` | dot-path string | Field to extract from response JSON (e.g. `"data.latestTsMs"`) |
| `sentinel_value_predicate` | string | Assertion on field: `">0"`, `"non_empty_array"`, `"!= null"`, `"== <val>"`, etc. |
| `axis` | enum | `read | write | auth | dependency` (per §21.3) |
| `description` | string | One-line human-readable purpose |

Worked example (chip-usage-helper):

```yaml
packaging:
  health_smoke_check:
    - { endpoint: "https://ai-bill.example.com/api/v1/cursor/events/health", expected_status: 200, max_attempts: 3, retry_delay_ms: 2000, sentinel_field: "data.latestTsMs", sentinel_value_predicate: ">0", axis: dependency, description: "ai-bill events stream non-empty" }
    - { endpoint: "https://ai-bill.example.com/api/v1/cursor/dashboard/top10", expected_status: 200, max_attempts: 2, retry_delay_ms: 1000, sentinel_field: "data.leaderboard", sentinel_value_predicate: "non_empty_array", axis: read, description: "Dashboard top-10 returns non-empty leaderboard" }
```

## OPTIONAL-REQUIRED-when-live-backend (§21.2)

`current_surface.dependencies.live_backend: bool` (NEW v0.4.0) is
the trigger. When true, `packaging.health_smoke_check` MUST be a
non-empty array. Hard rule 13 (§17.6) binds this as
spec_validator's BLOCKER 14 `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`:

1. Load `current_surface.dependencies.live_backend`.
2. If true: `packaging.health_smoke_check` must be non-empty array.
3. If false or field absent: BLOCKER PASS by absence.
4. FAIL message includes ability id + suggestion to declare
   `live_backend` if the ability actually does depend on one.

`live_backend: true` examples: chip-usage-helper (depends on
ai-bill); a GitHub-issue-creator (depends on api.github.com); an
analytics-ingest ability (depends on a queue). `live_backend: false`
or absent examples: Si-Chip self-dogfood (all evidence on disk); a
boilerplate generator (pure file system).

## 4-axis taxonomy (§21.3)

Post-deploy verification industry practice uses a 4-axis
decomposition; each ability picks only the axes its `live_backend`
actually uses:

| `axis` | Meaning | Typical probe |
|---|---|---|
| `read` | GET critical resource | `GET /api/v1/users/me` returns 200 + non-empty profile |
| `write` | POST create + GET verify | `POST /api/v1/test-resource` then round-trip `GET` |
| `auth` | Auth-protected flow | `POST /api/v1/login` with test creds returns 200 + token |
| `dependency` | Downstream / queue / cache touch | `GET /api/v1/health/redis` or downstream health endpoint |

Partial coverage is fine: chip-usage-helper ≡ `read` + `dependency`;
an issue-creator ≡ `write` + `auth`; a cache-warmer ≡ `dependency`
only. The spec does NOT require all four axes for every ability —
only that the ability's live backend dependencies are exhaustively
probed.

### ≥ 1 axis required (§21.3.2)

Non-empty arrays must contain at least 1 axis entry. spec_validator
WARNs in v0.4.0 / BLOCKs post-promotion when `axis: read` is the
only declared axis yet the backend clearly has a `dependency` risk
(e.g. chip-usage-helper-shape abilities: ai-bill is `dependency`,
not `read`, because the `events/health` stream is the failure
surface).

## Packaging-gate enforcement (§21.4)

§8.1 step 8 `package-register` runs every declared probe at ship
time:

1. Read `packaging.health_smoke_check` from the BasicAbilityProfile.
2. Execute HTTP probe with `max_attempts` retries and `retry_delay_ms`
   spacing; verify `expected_status`, extract `sentinel_field`, apply
   `sentinel_value_predicate`.
3. Write per-axis results to
   `.local/dogfood/<DATE>/<round_id>/raw/health_smoke_results.yaml`:
   `{check_id, axis, attempts_used, response_status, sentinel_observed,
   predicate_passed, elapsed_ms}`.
4. **Ship-eligibility declaration**: every declared check must
   `predicate_passed: true`. Any FAIL blocks ship.
5. `live_backend: false` or field absent → probe skipped; ship
   unblocked.

### `tools/eval_skill.py health_smoke` runner (§21.4.1)

Wave 1b lands a dedicated runner subcommand:

```bash
python tools/eval_skill.py health_smoke \
    --skill chip-usage-helper \
    --basic-ability-profile .local/dogfood/2026-04-30/abilities/chip-usage-helper/round_26/basic_ability_profile.yaml \
    --out .local/dogfood/2026-04-30/abilities/chip-usage-helper/round_26/raw/health_smoke_results.yaml
```

Exit 0 = all axes PASS; non-zero = ≥1 axis FAIL.

## OTel semconv extension (§21.5)

Every probe emits an OTel span feeding the ability's existing trace
pipeline:

| OTel attribute | Value |
|---|---|
| `gen_ai.tool.name` | `si-chip.health_smoke` |
| `mcp.method.name` | `health_check` |
| `gen_ai.system` | `<ability_id>` |
| `gen_ai.operation.name` | `health_smoke_check` |
| `gen_ai.client.operation.duration` | `<elapsed_ms>` |
| `http.status_code` | `<response_status>` |
| `si_chip.health_smoke.axis` | `<axis>` |
| `si_chip.health_smoke.predicate_passed` | `<bool>` |

This lets reviewers trace ship-prep probe decisions via trace IDs
rather than log greps. OTel does NOT publish a healthcheck
semconv standard; Si-Chip names the attribute explicitly instead of
borrowing Kubernetes liveness/readiness vocabulary (§21.6 boundary).

## Forever-out re-check (§21.6)

| §11.1 forever-out | Touched by §21? |
|---|---|
| Marketplace | NO — `health_smoke_check` is a BasicAbilityProfile field. |
| Router model training | NO — probes are observations; no weights. |
| Generic IDE compat | NO — schema is ability-local and deliberately NOT bound to Kubernetes liveness/readiness, systemd watchdogs, or IDE-specific health adapters. If an ability needs orchestrator-side probes, that's the ability's deployment pipeline concern, not Si-Chip's. |
| Markdown-to-CLI | NO — schema is hand-written YAML; spans are runtime emit. |

## Cross-References

| §21 subsection | Spec section | R12 section |
|---|---|---|
| 21.1 schema | spec §21.1 | r12 §2.6.a |
| 21.2 live_backend BLOCKER 14 | spec §21.2 | r12 §4.4 |
| 21.3 4-axis taxonomy | spec §21.3 | r12 §2.6.b fitgap pattern |
| 21.4 packaging-gate enforcement | spec §21.4 | r12 §4.4 |
| 21.5 OTel semconv extension | spec §21.5 | r12 §2.6.c |
| 21.6 forever-out re-affirm | spec §21.6 | r12 §7 |

Cross-ref: `references/real-data-verification-r12-summary.md`
(§19.5 Layer C post-recovery verification is triggered by
`health_smoke_check` FAIL→PASS transitions),
`references/lifecycle-state-machine-r12-summary.md` (§20.4
`ship_decision.yaml` ship verdict gated on all probes PASS),
`references/self-dogfood-protocol.md` (§8.1 step 8
`package-register` is where enforcement fires).

Source spec section: Si-Chip v0.4.0-rc1 §21 (Normative); distilled
from `.local/research/r12_v0_4_0_industry_practice.md` §2.6 + §4.4.
This reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
