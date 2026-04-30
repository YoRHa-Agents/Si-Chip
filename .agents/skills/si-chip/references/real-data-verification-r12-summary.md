# Real-Data Verification — R12 Summary (Spec §19)

> Reader-friendly summary of the §19 real-data-verification Normative
> chapter (v0.4.0-rc1). Authoritative sources:
> `.local/research/spec_v0.4.0-rc1.md` §19 and
> `.local/research/r12_v0_4_0_industry_practice.md` §2.2 + §4.2.

## Why this section exists

chip-usage-helper Cycle 5 v0.9.0 shipped with every test fixture
green; production was ai-bill returning `latestTsMs: 0` because the
events ingestion pipeline had stalled for 4 hours, and the dashboard
silently crashed on the zero-events shape that no hand-crafted mock
had ever contained. The failure wasn't in the code — it was in the
**mock-vs-production payload divergence**. §19 codifies the Cycle 5
fix as a Normative three-layer verification pattern so the next
ability cannot ship without a grep-able production-payload provenance
trail.

## Layer A — msw fixture provenance

Every test fixture (typically under `tests/fixtures/`,
`tests/__mocks__/`, or the ability implementation tree's equivalent
test path) MUST cite the production payload sample its mock JSON
shape was derived from. Citation format is a one-line comment at the
top of the fixture file or in its filename:

```ts
// real-data sample provenance: 2026-04-30T08:14:00Z / yorha@anthropic.local
export const dashboardTop10Fixture = { ... };
```

Equivalent in other languages:

- Python: `# real-data sample provenance: <captured_at> / <observer>`
- HTML / Markdown: `<!-- real-data sample provenance: ... -->`

A post-ship reviewer audits via `grep -rn "real-data sample provenance"
tests/ | sort -t: -k1`.

## Layer B — user-install verification

Once the release branch is pushed, the ability's author or reviewer
MUST run a live user-install cycle:

1. `git push origin feature/<release-branch>`
2. Build tarball: `npm pack` (TS) or `python -m build` (Python).
3. User installs: `npm install <tarball>` or `cursor install
   <plugin.zip>` in a production Cursor / Claude Code instance.
4. Manually trigger the ability in ≥3 cases (typical: 1 EN prompt +
   1 CJK prompt + 1 slash-command) covering the `core_goal.statement`.
5. Log the outcome to `.local/dogfood/<DATE>/<round_id>/raw/user_install_verification.md`
   with prompt + observed output + verdict (PASS / FAIL) per case.

Any FAIL triggers §14.4 REVERT-only rollback: reset the release
branch to the last passing round and write a negative-result trace
under `raw/` (workspace rule "No Silent Failures").

## Layer C — post-recovery live verification

When a `live_backend` dependency (e.g. chip-usage-helper's ai-bill)
experiences an incident and recovers, the next `round_kind=ship_prep`
round MUST re-run the ability's `core_goal_test_pack` +
`real_data_samples` against the recovered backend, then append a
`verified_with_live_data` block to `ship_decision.yaml` (per §20.4):

```yaml
verified_with_live_data:
  - backend_id: ai-bill
    endpoint: "/api/v1/cursor/events/health"
    verified_at: "2026-04-30T08:14:00Z"
    sentinel: "latestTsMs > 0"
    sentinel_observed: 1714464840000
    observer: "yorha@anthropic.local"
    note: "Backend recovered after Cycle 5 incident; events stream nominal."
```

Trigger: `packaging.health_smoke_check` transitions FAIL → PASS for
the dependency. Rationale: recovered backends may ship a shape
drift (renamed fields, new error codes) that incident-free mocks
never encoded.

## `feedback_real_data_samples.yaml` schema

Every ability with live dependencies maintains a
`feedback_real_data_samples.yaml` next to its source-of-truth tree.
Abridged schema (full version lands Wave 1b):

```yaml
$schema_version: "0.1.0"
$spec_section: "v0.4.0 §19.2"
ability_id: "<id>"
last_revised: "YYYY-MM-DD"
revision_log:
  - { round: round_N, change: "added v1.1.0 ai-bill endpoint sample" }
real_data_samples:
  - id: sample_1_dashboard_top10
    endpoint: "/api/v1/cursor/dashboard/top10"
    request_params: { window: "30d", org_id: "<redacted>" }
    response_json: '{"ok":true,"data":{"leaderboard":[...]}}'
    observed_state: "live, post-recovery, top-10 populated"
    captured_at: "2026-04-30T08:14:00Z"
    observer: "yorha@anthropic.local"
    rationale: "Drives msw fixture for tests/get_dashboard_top10.test.ts"
```

All samples are redacted-by-policy: `request_params` must omit PII,
tokens, credentials; `response_json` is the verbatim response shape
with PII redacted. The provenance is the pair `(captured_at,
observer)` that Layer A citations reference.

## Fixture-citation rule + BLOCKER 13

Hard rule 12 (§17.5) binds the fixture citation as
spec_validator's BLOCKER 13 `REAL_DATA_FIXTURE_PROVENANCE`:

1. Load `feedback_real_data_samples.yaml`; get declared
   `real_data_samples[*].id`.
2. If set is empty → BLOCKER PASS by absence.
3. Otherwise grep the ability's test tree for
   `real-data sample provenance: <captured_at> / <observer>` lines.
4. Every declared sample id MUST have ≥1 fixture citing its
   `(captured_at, observer)` pair.
5. Missing citations fail with an explicit list of unmatched sample
   ids.

This is a **grep-able audit trail**, not a complex diff — the point
is post-ship reviewer ergonomics, not schema enforcement.

## Chip-usage-helper Cycle 5 precedent

Round 24 (v0.9.0) shipped with all vitest green and zero production
fixtures. `ai-bill` `events/health` returned `latestTsMs: 0` the
morning after ship; the dashboard crashed because every mock
implicitly assumed `latestTsMs > 0`. Cycle 5 codified (a) the msw
fixture-provenance convention, (b) the user-install manual cycle
after every push, (c) the post-recovery live verification block on
ship_decision.yaml. §19 is that Cycle 5 pattern lifted to Normative
spec so the next ability cannot silently omit any of the three
layers.

## Forever-out re-check (§19.6)

| §11.1 forever-out | Touched by §19? |
|---|---|
| Marketplace | NO — `feedback_real_data_samples.yaml` is ability-local source-of-truth; user-install uses existing npm/cursor install surfaces. |
| Router model training | NO — samples are mock data, not training data; no model weights involved. |
| Generic IDE compat | NO — user-install uses each IDE's existing install channel; no cross-IDE adapter. |
| Markdown-to-CLI | NO — samples are hand-written YAML; fixtures are hand-curated. |

## Cross-References

| §19 subsection | Spec section | R12 section |
|---|---|---|
| 19.1 3-layer pattern | spec §19.1 | r12 §4.2 |
| 19.2 sample schema | spec §19.2 | r12 §2.2 |
| 19.3 fixture-citation rule | spec §19.3 | r12 §4.2 + §2.2 |
| 19.4 user-install detail | spec §19.4 | r12 §4.2 (Cycle 5) |
| 19.5 post-recovery detail | spec §19.5 | r12 §2.2 (Pact loose assertions) |
| 19.6 forever-out re-affirm | spec §19.6 | r12 §7 |

Cross-ref: `references/lifecycle-state-machine-r12-summary.md`
(§20.4 `ship_decision.yaml` hosts the `verified_with_live_data`
block), `references/health-smoke-check-r12-summary.md` (§21.2
`live_backend: true` triggers Layer C), `references/core-goal-invariant-r11-summary.md`
(§14.4 REVERT-only path applies when Layer B fails).

Source spec section: Si-Chip v0.4.0-rc1 §19 (Normative); distilled
from `.local/research/r12_v0_4_0_industry_practice.md` §2.2 + §4.2.
This reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
