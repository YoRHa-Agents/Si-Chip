---
title: "Si-Chip Spec v1.0.0-rc1 (DESIGN PAPER — NOT SHIPPED)"
version: "v1.0.0-rc1"
status: "design_paper"
archived: true
effective_date: null
promoted_from: null
compiled_into_rules: false
supersedes: null
successor_of: "v0.5.0"
language: zh-CN
intent: "Articulate the criteria for promoting Si-Chip from v0.x to v1.0.0 stable. This is a design reference, not a shippable spec rc. Its purpose is to make the v1.0.0 promotion criteria explicit BEFORE Si-Chip attempts to satisfy them, so future rounds can be measured against a fixed target."
not_for_compile: true
not_for_ship: true
ship_blockers_listed: true
---

# Si-Chip Spec v1.0.0-rc1 — DESIGN PAPER (Archived; NOT for Ship)

> **WARNING — non-shippable artefact.** This file is a *design paper*, not a normal spec rc.
> It articulates what would need to be true before a v1.0.0 stable promotion ceremony
> can run. It is **archived** — it does NOT enter `.rules/` compile, does NOT trigger
> `spec_validator` runs, does NOT bump version, does NOT change any current Si-Chip
> behavior. It is a research-only design artefact for future maintainers.
>
> Authored 2026-05-05 by Round 27 L3 Task Agent (post-ship self-iter + v1.0.0-rc1
> design paper PR; stacked on PR #21 v0.5.0 aggregate ship). Companion to
> `.local/dogfood/2026-05-05/round_27/` measurement_only stability witness round.

## §1 Purpose

Si-Chip's promotion path is governed by **§4.2 promotion rule** (verbatim from
`spec_v0.5.0.md`):

> 新能力默认绑定 `v1_baseline`。必须在当前 gate **连续两轮 dogfood 全部硬门槛通过**，方可
> 升档至 N+1。

That rule defines `v1_baseline → v2_tightened → v3_strict` gate progression. It does
NOT, however, say anything about when a *spec version* itself promotes from v0.x
(unstable; minor releases) to v1.0.0 (stable; backward-compatible API contract).

The semver discipline this paper articulates is the **complement** to §4.2: a
promotion-gate ladder for the spec itself, not for individual abilities. Just as a
single ability needs 2 consecutive `v3_strict` PASSes to claim `v3_strict` gate
maturity, the *spec* needs sufficient evidence of stability before it can claim the
`v1.0.0` semver contract — which implies "no breaking changes within v1.x without a
v2.0.0 bump".

This paper makes the v1.0.0 promotion criteria **explicit BEFORE** Si-Chip attempts
to satisfy them. Doing so up front prevents post-hoc rationalization: future
maintainers can grep this paper, measure current state against the 6 gates, and
honestly report which gates are satisfied vs deferred. Without this paper, a future
"let's ship v1.0.0" PR would inevitably end up trading off honest gate criteria for
shipping pressure — exactly the failure mode `r11_core_goal_invariant.md` §1.1
documented for `iteration_delta` virtualization.

## §2 Promotion Gate Criteria

Six gates must ALL be satisfied for v1.0.0 to ship. Today (2026-05-05, Round 27),
**0 of 6 are satisfied**; current state is honestly ~5–10 rounds away from gate 1
and unbounded rounds away from gates 4 + 5.

### GATE 1 — v3_strict ladder: 2 consecutive `v3_strict` rounds

Si-Chip is currently at `v2_tightened` (= standard) gate, achieved Round 18 + 19,
maintained through Round 27 (10 consecutive v2 PASSes). The §4.2 promotion rule
requires 2 consecutive `v3_strict` PASSes before the spec can claim `v3_strict`
gate maturity at the meta level (not just per-ability).

Currently 0/2 v3_strict consecutive passes. Per `monotonicity_witness.json` from
Round 27, `v3_strict_consecutive_passes: 0`; `v3_strict_eligible: false`. Reasons:

1. `metadata_tokens = 94` exceeds v3_strict ≤ 80 row by 14 tokens.
2. `per_invocation_footprint = 5074` exceeds v3_strict ≤ 5000 row by 74.
3. `iteration_delta any axis` requires fresh ≥ +0.15 round-over-round; cache-replay
   measurement_only rounds cannot satisfy this — needs code_change rounds engineering
   specific axis lifts.

Estimated: ~5–10 code_change rounds to engineer the metadata + footprint shrinks
+ at least one fresh ≥ +0.15 axis lift. v3_strict ladder work is deliberately
deferred to v0.6.x or later code_change rounds per Round 27's `next_action_plan.yaml`
action `a3_round_28_post_ship_continued_stability`.

### GATE 2 — Spec stable for ≥30 days at last minor version

Currently the v0.5.0 spec was frozen on **2026-05-05**; the 30-day stability window
closes on **2026-06-04** at the earliest. This gate is a **calendar / patience
gate**, not a metric gate — it ensures sufficient time for downstream consumers
(if any) to surface integration issues against the frozen spec before a v1.0.0
contract locks the surface area further.

Currently 0/30 days at v0.5.0 stable; rate of progress: 1 day/day; ETA: 30 days.
This is the lowest-friction gate (just wait), but it is deliberately listed as
a hard gate to prevent rushing v1.0.0 on the same day v0.5.0 ships.

### GATE 3 — C0 = 1.0 maintained ≥ 30 rounds

Si-Chip's `C0_core_goal_pass_rate` has been **1.0 for 11 consecutive rounds**
(Round 17 → 27, per Round 27 monotonicity_witness). The C0 invariant is the
strongest signal of behavioral stability — every round verifies that the core
goal (emit 6 evidence files + 16-BLOCKER spec_validator PASS) still works
end-to-end.

Currently 11/30 consecutive C0 = 1.0 rounds. ETA: ~19 more rounds at the current
pace (Round 27 → Round 46). The 30-round threshold is chosen to ensure C0
stability across multiple round_kind contexts (code_change + measurement_only +
ship_prep + maintenance) and across multiple ability versions (e.g., 11 rounds
covered v0.4.0 → v0.5.0; 30 rounds would cover v0.5.0 → ~v0.7.x or v1.0.0-rc1
exploratory work).

### GATE 4 — External research references ≥ 3

Si-Chip currently has **1 long-term external research reference** registered per
`§24.6.4`: `r13_agent_skills_comparison.md` (addyosmani/agent-skills v1.0.0).
The §24.6 mechanism was introduced precisely to enable absorption of external
ecosystems' lessons WITHOUT depending on or distributing their code; reaching
3 registrations proves the mechanism is **exercised**, not just **declared**.

Two more candidate registrations to explore:
1. A second skill ecosystem (e.g., a hypothetical Continue.dev SKILL convention,
   or Anthropic's own internal Skills cookbook if upstream-published) →
   `r14_<name>_comparison.md`.
2. An evaluation framework reference (e.g., LangChain's `langsmith` evaluation
   patterns, OpenAI's evals repo, or Stanford CRFM's HELM benchmark suite)
   to cross-validate Si-Chip's R6 7-dim / 37-sub-metric taxonomy →
   `r15_<framework>_metric_comparison.md`.

Currently 1/3 registered references. ETA: dependent on upstream ecosystem
publication cadence; not directly actionable by Si-Chip-internal work.

### GATE 5 — At least 1 cross-team consumer outside YoRHa

Si-Chip is currently a YoRHa-internal optimization factory (per the GitHub org
`YoRHa-Agents`). To claim v1.0.0 stable, it should have at least 1 *cross-team*
consumer — an external team or org that has installed Si-Chip as a Skill in
their own repo and produced at least 1 dogfood round under Si-Chip's discipline.
This proves the spec is **portable**, not just **local**.

Cross-team consumer scenarios to explore:
1. Another internal team within the same organization adopts Si-Chip for their
   own ability optimization (e.g., a DevolaFlow-adjacent team that already uses
   the §10 persistence contract).
2. An external Anthropic ecosystem partner (e.g., a customer team building
   custom Skills for their Cursor / Claude Code installs).

Currently 0/1 cross-team consumer. ETA: dependent on outreach + onboarding
work outside this repo.

### GATE 6 — v3_strict thresholds met for ALL 10 §4.1 metrics

The §4.1 threshold table has 10 metrics × 3 profiles = 30 cells. Currently
8 of 10 metrics are **at or below** v3_strict thresholds (cache-replay byte-
identical Round 26-27 values):

| Metric | v3_strict threshold | Current observed | PASS? |
|---|---:|---:|:---:|
| pass_rate | ≥ 0.90 | 1.00 | ✓ |
| pass_k | ≥ 0.65 | 1.00 | ✓ |
| trigger_F1 | ≥ 0.90 | 1.00 | ✓ |
| near_miss_FP_rate | ≤ 0.05 | 0.00 | ✓ |
| metadata_tokens | ≤ 80 | 94 | ✗ (FAIL by 14) |
| per_invocation_footprint | ≤ 5000 | 5074 | ✗ (FAIL by 74) |
| wall_clock_p95 | ≤ 20 s | 17.57 s | ✓ |
| routing_latency_p95 | ≤ 800 ms | 0.16 ms | ✓ |
| routing_token_overhead | ≤ 0.08 | 0.0233 | ✓ |
| iteration_delta any axis | ≥ +0.15 (round-over-round, code_change-only honest) | 0.0 (Round 27 measurement_only) | ✗ (FAIL; needs fresh code_change round) |

Currently 8/10 v3_strict-eligible. The 2 failing rows (metadata + footprint) are
both axis-bucketing-impacted by SKILL.md body size; reducing body to ≤ 4488
tokens (current C8_oncall_per_trigger) would shrink C2_body to ~4426, making
C4_per_invocation_footprint = 94 + 4426 = 4520 ≤ 5000 ✓; SKILL.md frontmatter
description shrink (162 → ≤ 80 chars roughly equivalent) would address metadata.
Both shrinks must happen in code_change rounds (measurement_only cannot edit
source per §15.1.4).

## §3 Schema Migration Plan (v0.x → 1.x)

Schema-side changes deferred to v1.0.0:

### 3.1 Bump `$schema_version` 0.3.0 → 1.0.0

The `templates/basic_ability_profile.schema.yaml` and other 6 templates currently
declare `$schema_version: 0.3.0`. v1.0.0 ship would bump these to `1.0.0` to
signal the v1.x semver contract.

Migration cost: low (literal string bump + spec_validator awareness of the new
version string). Does NOT introduce breaking changes to existing v0.x BAP
profiles; the schema field set itself is preserved byte-identical.

### 3.2 Close-out OPTIONAL fields universally adopted

Currently §24.4's `lifecycle.category` field is OPTIONAL (default null). If by
v1.0.0 ALL active abilities (Si-Chip + chip-usage-helper + any new abilities)
declare `lifecycle.category` non-null, it can be promoted to REQUIRED in the
schema for v1.0.0.

Migration cost: medium. Must verify all active BAPs have set the field, then
rerun spec_validator with the new REQUIRED constraint to confirm no
regressions. Backward-compat path: legacy BAPs from v0.x can be migrated
in-place (default null → declared category) since the data is unambiguous.

### 3.3 STRICT enforcement of currently-Informative patterns

Current Informative §24.x sub-sections that are CANDIDATES for promotion to
Normative + spec_validator BLOCKER at v1.0.0:

| Section | Current status | v1.0.0 candidate | Decision rationale |
|---|---|---|---|
| §24.2 Standardized SKILL.md Sections | Informative @ v0.4.3 | **Promote to Normative** | Sufficient adoption witness across Si-Chip + chip-usage-helper SKILL.md trees; mnemonic value clear; promotion would add 1 BLOCKER `STANDARDIZED_SECTIONS_PRESENT` checking for `## Common Rationalizations` / `## Red Flags` / `## Verification` trio. |
| §24.4 Lifecycle Category Taxonomy | Informative @ v0.4.5 | **Stay Informative OR promote with field-required-bump in §3.2** | If §3.2 adopts the field as REQUIRED, the §24.4 taxonomy itself is automatically Normative (the schema enforces). If §3.2 stays OPTIONAL, §24.4 stays Informative. |
| §24.5 Meta-Routing Pattern | Informative @ v0.4.6 | **Stay Informative** | Pattern documentation, not enforcement. Si-Chip is the canonical reference impl; promoting to Normative would require a `META_ROUTING_PATTERN_DECLARED` BLOCKER which is awkward (most non-meta abilities trivially comply by absence). |
| §24.6 External Research Registration | Informative metadocumentary @ v0.4.7 | **Stay Informative** | Registration mechanism documentation; promoting to Normative would require a `RESEARCH_REFERENCE_REGISTRATION_VALID` BLOCKER which is awkward (most rounds have 0 new registrations, so the BLOCKER would be vacuously PASS in nearly every round). |

DECISION: at v1.0.0 ship time, only §24.2 promotes to Normative + adds 1 BLOCKER
(BLOCKER 17 `STANDARDIZED_SECTIONS_PRESENT`); §24.4 / §24.5 / §24.6 stay
Informative. Total BLOCKER count v0.5.0 → v1.0.0: 16 → 17 (+1). Total hard rule
count v0.5.0 → v1.0.0: 15 → 16 (+1; new rule 16 maps to new BLOCKER 17).

### 3.4 Deprecate v0.x grace-period SKIP-as-PASS paths

Currently `tools/spec_validator.py` has §13.6.4 grace-period SKIP-as-PASS paths
for legacy v0.2.0 / v0.3.0 / v0.4.0 specs against v0.4.2+ BLOCKERs (15 + 16). At
v1.0.0 ship, these grace-period paths SHOULD be removed — v1.0.0 is the new
canonical spec, and any pre-v0.5.0 spec in `.local/research/` is purely a
historical artefact (per §6 below) and SHOULD NOT be the target of any active
spec_validator runs.

Migration cost: low (delete grace-period branches; leave the spec files in
`.local/research/` as pinned historical references). Backward-compat impact:
any external consumer pinning to a v0.x spec must migrate to v1.0.0 (or
explicitly accept that v0.x specs are no longer validator targets).

## §4 §11 Forever-Out at v1.0.0

The §11.1 forever-out items are RE-AFFIRMED VERBATIM at v1.0.0:

1. **Skill / Plugin marketplace** — NEVER. v1.0.0 does NOT introduce any
   marketplace surface. The `docs/skills/si-chip-1.0.0.tar.gz` deterministic
   tarball is the only distribution artifact; consumers `tar -xf` it into
   their own repos.
2. **Router-model training** — NEVER. v1.0.0 §5 router work remains description-
   driven; §24.5.2 verbatim prohibition of 4 router-implementation surfaces is
   preserved.
3. **Generic IDE / Agent runtime compatibility layer** — NEVER. v1.0.0 §7
   platform priority remains `Cursor → Claude Code → Codex` (bridge-only). No
   support for arbitrary external IDEs / agent runtimes.
4. **Markdown-to-CLI auto converter** — NEVER. v1.0.0 SKILL.md remains hand-
   authored; templates remain hand-edited canonical fields.

**NEW for v1.0.0** — fifth forever-out item:

5. **NO automated cross-repo absorption of external skills.** The §24.6
   registration mechanism is hand-curated: r13 (agent-skills) was a one-time
   human-curated absorption that landed across 6 patches A1-A6. v1.0.0 does
   NOT introduce a "skill scraper" (auto-clone external Skills repos),
   "convention auto-importer" (auto-detect new SKILL.md conventions and
   submit-PR them), or any other automation that turns absorption into a
   continuously-running process. Each new external research reference (r14,
   r15, ...) MUST be registered via a hand-authored absorption arc PR (the
   v0.5.0 absorption arc as canonical exemplar: 6 patches A1-A6 across 6 PRs
   #14-#20 with a 7th aggregate ship PR #21).

The fifth forever-out item is the **direct lesson** of the v0.5.0 absorption
arc: even with a clean machine-readable registration format (§24.6.2), the
HUMAN judgment of which conventions to absorb vs reject (e.g., B1 marketplace
direction NOT absorbed; B2 multi-IDE chase NOT absorbed) cannot be automated
without violating §11.1 items 1 + 3. Locking this in at v1.0.0 prevents
future maintainers from "improving" the registration mechanism into an
auto-importer.

## §5 v1.0.0-rc1 → v1.0.0 Promotion Procedure

When all 6 gates in §2 are satisfied (estimated ~30+ rounds out from Round 27),
the promotion ceremony runs as follows:

### 5.1 Author final spec_v1.0.0.md from this rc paper

- Copy `.local/research/spec_v1.0.0-rc1.md` → `.local/research/spec_v1.0.0.md`
- Update frontmatter: `status: design_paper → status: frozen`,
  `archived: true → archived: false`, `effective_date: null → <YYYY-MM-DD>`,
  `compiled_into_rules: false → true`, `not_for_compile: true → false`,
  `not_for_ship: true → false`, `promoted_from: null → v1.0.0-rc1`,
  `supersedes: null → v0.5.0`.
- Re-promulgate §1-§24 prose from `spec_v0.5.0.md` byte-identical EXCEPT for
  the §3.3 changes (§24.2 Informative → Normative + new BLOCKER 17 + new hard
  rule 16) and §3.4 changes (delete grace-period prose).

### 5.2 Bump SKILL.md frontmatter to 1.0.0

- `.agents/skills/si-chip/SKILL.md`: `version: 0.5.0 → 1.0.0`
- 3-tree mirror: `.cursor/skills/si-chip/SKILL.md` + `.claude/skills/si-chip/SKILL.md` synced byte-identical
- Recompute and capture sha256 for the 3-tree mirror

### 5.3 Generate v1.0.0 tarball

- `docs/skills/si-chip-1.0.0.tar.gz` produced via the same deterministic
  `--sort=name --owner=0 --group=0 --numeric-owner --mtime='<ship-date>
  00:00:00 UTC'` invocation as v0.5.0 (and v0.4.0)
- Capture sha256 in `docs/skills/si-chip-1.0.0.tar.gz.sha256`
- Verify rebuild byte-identical (re-run the same invocation; sha256 must match)

### 5.4 Tag git as `v1.0.0` (FIRST stable tag)

- `git tag v1.0.0 <sha-of-v1.0.0-ship-merge-commit>`
- This is the FIRST stable git tag for Si-Chip; v0.x tags (if any) were
  deliberately not created — only `feat/v0.4.0-...` branches and PR merges
  carried the v0.x lineage.
- The v1.0.0 tag becomes the canonical anchor for any v1.x patch / minor
  release that follows; v2.0.0 is reserved for backward-incompatible spec
  changes.

### 5.5 Update README to reflect stable status

- Update `README.md` (top-of-repo) "Status" badge / line: `v0.5.0 frozen → v1.0.0 stable`
- Update `.local/research/README.md` Version History table with the v1.0.0
  ship row.
- Update `CHANGELOG.md` `[Unreleased]` → `[1.0.0] - <ship-date>` and document
  all v0.x → v1.0.0 changes (§3 schema migration items + §4 new forever-out
  + §3.3 promoted §24.2 + §3.4 deprecated grace-period paths).

### 5.6 Cross-walk all v0.x deprecations

For any external consumer pinning to a v0.x spec, document the migration
path in `.local/research/v1.0.0_migration_guide.md`:
- Schema field changes (e.g., if §3.2 promoted `lifecycle.category` to REQUIRED)
- New BLOCKERs (BLOCKER 17 `STANDARDIZED_SECTIONS_PRESENT`)
- Removed grace-period paths (§3.4)
- Forever-out additions (§4 item 5)

## §6 Pinned Historical References

The following spec files constitute Si-Chip's v0.x history; they are **NEVER
deleted**, even after v1.0.0 ships. They live under `.local/research/` as
pinned historical references for audit, regression analysis, and future
maintainers' understanding of the v0.x → v1.0.0 absorption arc:

- `spec_v0.1.0.md` (frozen 2026-04-28; FIRST frozen spec; v0.1 ship at v1_baseline)
- `spec_v0.2.0-rc1.md` + `spec_v0.2.0.md` (frozen 2026-04-29; +9 sub-metrics prose alignment)
- `spec_v0.3.0-rc1.md` + `spec_v0.3.0.md` (frozen 2026-04-29; +§14 core_goal + §15 round_kind + §16 multi-ability + §17 hard rules 9+10)
- `spec_v0.4.0-rc1.md` + `spec_v0.4.0.md` (frozen 2026-04-30; +§18-§23 + §17 hard rules 11+12+13; FIRST v2_tightened ship)
- `spec_v0.4.2-rc1.md` (rc 2026-05-05; A1 description-cap absorption from agent-skills v1.0.0)
- `spec_v0.4.3-rc1.md` (rc 2026-05-05; A2 standardized SKILL.md sections)
- `spec_v0.4.4-rc1.md` (rc 2026-05-05; A3 progressive-disclosure)
- `spec_v0.4.5-rc1.md` (rc 2026-05-05; A4 lifecycle.category)
- `spec_v0.4.6-rc1.md` (rc 2026-05-05; A5 meta-routing pattern)
- `spec_v0.4.7-rc1.md` (rc 2026-05-05; A6 anti-pattern doc + r13 long-term registration; v0.5.0 arc complete)
- `spec_v0.5.0.md` (FROZEN 2026-05-05; aggregate ship of A1-A6; current canonical spec @ Round 27)
- `spec_v1.0.0-rc1.md` (THIS DESIGN PAPER; archived 2026-05-05; NOT shipped; status = design_paper)

When v1.0.0 ships, the following ALSO become pinned historical references:
- All v0.x dogfood rounds under `.local/dogfood/2026-04-28/` through
  `.local/dogfood/2026-05-05/round_27/` (and any subsequent v0.6.x rounds)
- All v0.x BAP profiles for Si-Chip + chip-usage-helper
- The 6 absorption-arc PRs #14 / #15 / #16 / #17 / #18 / #20 + the v0.5.0
  aggregate ship PR #21 + the post-ship + design-paper PR (this PR's bundle)

## §7 What This Paper Does NOT Do

Explicit non-scope (defensive enumeration to prevent scope creep):

- ❌ Does NOT bump version. Si-Chip's effective spec remains `v0.5.0` after this
  PR merges. SKILL.md frontmatter remains at `version: 0.5.0`.
- ❌ Does NOT enter `.rules/` compile. `.rules/si-chip-spec.mdc` is NOT regenerated
  from this paper. AGENTS.md is NOT recompiled. `.rules/.compile-hashes.json` is
  NOT updated.
- ❌ Does NOT trigger `spec_validator` runs. This paper is NOT a spec_validator
  target (`tools/spec_validator.py --spec .local/research/spec_v1.0.0-rc1.md`
  would technically run but produce meaningless output since the paper does
  NOT contain the §3.1 / §4.1 / §11.1 / §13 markers spec_validator parses).
- ❌ Does NOT change any current Si-Chip behavior. No SKILL.md edit; no
  template edit; no `tools/` script edit; no eval-pack edit; no eval-runner
  code edit.
- ❌ Does NOT define a roadmap deadline. v1.0.0 ships when (and only when)
  ALL 6 §2 gates are satisfied — no earlier, regardless of external pressure.
- ❌ Does NOT replace `r12_v0_4_0_industry_practice.md` or any other r-numbered
  research reference. This paper is **architectural intent**, not industry
  evidence; it sits beside the r-series, not in place of it.

It IS a **design artifact for future maintainers** — a fixed target articulated
BEFORE the work begins, so honest progress tracking is possible.

## §8 Re-Verification Cadence

This paper SHOULD be reviewed every **90 days** for relevance and gate-criteria
freshness. Trigger conditions:

- **Gate criteria evolve**: e.g., if §4.1 row updates (a new metric is added,
  an existing threshold is tightened) or §15 round_kind clauses are refined
  (e.g., new round_kind value introduced), this paper's §2 gate definitions
  may need updates.
- **Major gate progress**: e.g., when GATE 1 reaches 1/2 v3_strict consecutive
  passes, document the path that achieved it in this paper's §2 GATE 1
  sub-section.
- **External landscape changes**: e.g., if agent-skills v2.0.0 ships with
  fundamentally new conventions, evaluate whether GATE 4 still requires "≥3
  registrations" or if "≥2 with cross-version delta" is more appropriate.
- **Ship-readiness audit**: at the 30-day post-v0.5.0 mark (2026-06-04),
  verify GATE 2 status; at 60 days (2026-07-04), audit gate 1 + gate 3
  progress; at 90 days (2026-08-04), comprehensive review of all 6 gates.

Cadence ownership: this paper is OWNED by the Si-Chip maintainer team. Each
review cycle SHOULD produce a 1-paragraph status note appended to `§8.1
Review History` (below); the paper itself is updated in-place (the
`spec_v1.0.0-rc1.md` filename is preserved across reviews; the `archived: true`
status persists until the v1.0.0 ship ceremony in §5).

### §8.1 Review History

(Empty at first authoring; future maintainers append review notes here.)

- **2026-05-05** — Initial authoring by Round 27 L3 Task Agent (post-ship
  self-iter + v1.0.0-rc1 design paper PR; stacked on PR #21). Status: 0/6
  gates satisfied. Next review: 2026-08-04 (90-day cadence).

---

> **End of Design Paper.** This file is archived; it does NOT enter `.rules/`
> compile or trigger spec_validator. v0.5.0 remains the canonical shipped
> spec. v1.0.0 ships only when ALL 6 §2 gates are satisfied — estimated
> 30+ rounds and ≥30 days from this paper's authoring date.
