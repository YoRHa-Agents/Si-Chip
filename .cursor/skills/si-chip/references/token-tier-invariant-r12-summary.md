# Token-Tier Invariant — R12 Summary (Spec §18)

> Reader-friendly summary of the §18 token-tier Normative chapter
> (v0.4.0-rc1). Authoritative sources:
> `.local/research/spec_v0.4.0-rc1.md` §18 and
> `.local/research/r12_v0_4_0_industry_practice.md` §2.1 + §4.1.

## What is the token-tier invariant?

Each `BasicAbility` that reports any token usage MUST decompose the
report along three cumulative-payment tiers. The v0.3.0 spec pooled
metadata tokens (`C1`) and per-invocation footprint (`C4`) into a
single "tokens with/without" axis; chip-usage-helper Cycle 2–3 proved
that pooling hides user-impact magnitude — a `-55%` EAGER reduction
buys ~10× the agent-session savings a `-55%` ON-CALL reduction does.

The three tiers mirror Anthropic's published Skill progressive
disclosure (Metadata ~100 tokens / Instructions <500 lines / Resources
unlimited) one-for-one:

| Tier | Key | Semantics | Paid frequency |
|---|---|---|---|
| **EAGER** | `C7_eager_per_session` | Metadata + always-apply rules + AGENTS.md fragments loaded every agent session | Per session (~1:10 vs trigger) |
| **ON-CALL** | `C8_oncall_per_trigger` | SKILL.md body + references loaded on activation | Per trigger (~1:10 vs LAZY) |
| **LAZY** | `C9_lazy_avg_per_load` | Resources / templates loaded only when explicitly read | Per explicit load |

## Schema (from spec §18.1)

`token_tier` is a REQUIRED-when-reported top-level block on
`metrics_report.yaml`, **adjacent** to `metrics` and `core_goal`:

```yaml
metrics_report.yaml:
  token_tier:
    C7_eager_per_session: <int|null>
    C7_eager_per_session_method: tiktoken|char_heuristic|llm_actual
    C8_oncall_per_trigger: <int|null>
    C8_oncall_per_trigger_method: tiktoken|char_heuristic|llm_actual
    C9_lazy_avg_per_load: <int|null>
    C9_lazy_avg_per_load_method: tiktoken|char_heuristic|llm_actual
    measured_with_sessions: <int>
    measured_with_triggers: <int>
    measured_with_lazy_loads: <int>
```

C7/C8/C9 are **top-level invariants**, NOT D8 sub-metrics — R6 stays
frozen at 7 × 37 keys (type-isomorphic to §14.5 C0 placement). If an
ability has not measured the tier split yet, all three keys appear as
`null` and `measured_with_*` as `0`; spec_validator BLOCKER 12
(`TOKEN_TIER_DECLARED_WHEN_REPORTED`) passes by absence.

## EAGER-weighted `iteration_delta` formula (§18.2)

§4.1 row 10's existing "≥1 axis at gate bucket" clause stays intact
and continues to gate promotion. §18.2 adds an OPTIONAL headline
formula for PR-review dashboards:

```text
weighted_token_delta = 10 × eager_delta + 1 × oncall_delta + 0.1 × lazy_delta
```

Weights encode cumulative-payment frequency: 1 EAGER session-cost ≈
10 trigger-costs ≈ 100 LAZY-costs. The chip-usage-helper Round 14
move that traded `EAGER -447 / ON-CALL +407` maps to `+5.45` under
the weighted formula but ~zero under the v0.3.0 pooled `token_delta`.
The weighted number is emitted on
`iteration_delta_report.yaml.verdict.weighted_token_delta_v0_4_0` for
review ergonomics; promotion eligibility still uses the 8-axis
`value_vector` bucket test (§6.1 now 8-axis including
`eager_token_delta`).

## R3 split (§18.3)

`R3_trigger_F1` splits into two siblings that can be measured
independently:

- **`R3_eager_only`** — router hit-rate when only EAGER prose (the
  description) is visible to the trigger classifier.
- **`R3_post_trigger`** — router hit-rate when full EAGER + ON-CALL
  prose is visible (ability has been attempt-triggered).

Legacy `R3_trigger_F1 = harmonic_mean(R3_eager_only, R3_post_trigger)`,
so v0.3.0 reports remain numerically reproducible. The split lets
teams diagnose EAGER-to-ON-CALL prose moves without confounding.
§3.1 D6 R3 sub-metric count stays at 1 (R6 7×37 frozen), with 2 rows
of explanatory prose added.

## `prose_class` taxonomy (§18.4; Informative @ v0.4.0)

Four-value controlled vocabulary for SKILL.md section annotations:

| `prose_class` | Purpose | Target tier |
|---|---|---|
| `trigger` | Description keywords + example user prompts that decide routing | EAGER (C7) |
| `contract` | Functional contract / Pact-style assertions / I/O schema | ON-CALL (C8) |
| `recipe` | Step-by-step instructions once triggered | ON-CALL (C8) |
| `narrative` | Long-form background, history, design rationale | LAZY (C9) |

Annotations are hand-written HTML comments, e.g.
`<!-- prose_class: trigger -->`. Promotion-to-Normative triggers
(§16.3 work): ≥2 abilities annotating ≥80% of sections, OR one
ability demonstrating `prose_class`-driven re-tiering worth ≥+0.10
weighted_token_delta across two ships.

## `lazy_manifest` packaging gate (§18.5; Normative)

`.agents/skills/<id>/.lazy-manifest` is the source-of-truth
declaration of LAZY-tier files. Schema:

```yaml
ability_id: <id>
declared_at: YYYY-MM-DD
lazy_files:
  - { path: "references/long-history.md", avg_tokens: 1200, rationale: "..." }
```

§8.1 step 8 `package-register` verifies each `lazy_files[*].path` is
NOT reachable from the EAGER or ON-CALL load paths. Drift = WARNING
in v0.4.0, BLOCKER after promotion. `C9_lazy_avg_per_load` averages
only `.lazy-manifest`-declared files, preventing ON-CALL miscounted
as LAZY. chip-usage-helper R44 evidence: 700-token reference silently
tier-crept to ON-CALL without a manifest.

## `tier_transitions` block (§18.6)

`iteration_delta_report.yaml` additively gains a `tier_transitions`
array that logs cross-tier token moves within the round:

```yaml
tier_transitions:
  - { from: EAGER, to: ON-CALL, tokens: 447, reason: "...", net_benefit: positive }
  - { from: ON-CALL, to: LAZY, tokens: 1200, reason: "...", net_benefit: positive }
  - { from: LAZY, to: ON-CALL, tokens: 60, reason: "...", net_benefit: neutral }
```

`net_benefit ∈ {positive, neutral, negative}` is computed against the
current gate's `weighted_token_delta` threshold (±0.05 / ±0.10 /
±0.15). Negative transitions only pass review in `ship_prep` or
`maintenance` rounds (per §15 round_kind clauses); otherwise they
trigger §6.2 retire review. Structure mirrors OpenSpec's
ADDED/MODIFIED/REMOVED delta semantics.

## Forever-out re-check (§18.7)

| §11.1 forever-out | Touched by §18? |
|---|---|
| Marketplace | NO — `token_tier` is a `metrics_report` field; `.lazy-manifest` is ability-local. |
| Router model training | NO — C7/C8/C9 are observations; R3 split is an evaluator split inside §5.1 allowed patterns. |
| Generic IDE compat | NO — `prose_class` is an annotation convention; platform priority §7.2 unchanged. |
| Markdown-to-CLI | NO — annotations + manifest are hand-written YAML/HTML comments. |

## Cross-References

| §18 subsection | Spec section | R12 section |
|---|---|---|
| 18.1 schema + worked examples | spec §18.1 | r12 §4.1 |
| 18.2 weighted iteration_delta | spec §18.2 | r12 §4.1 |
| 18.3 R3 split | spec §18.3 | r12 §4.1 |
| 18.4 prose_class taxonomy | spec §18.4 | r12 §2.1.b |
| 18.5 lazy_manifest gate | spec §18.5 | r12 §4.1 |
| 18.6 tier_transitions block | spec §18.6 | r12 §2.3.d |
| 18.7 forever-out re-affirm | spec §18.7 | r12 §7 |

Cross-ref: `references/metrics-r6-summary.md` (R6 7-dim context),
`references/core-goal-invariant-r11-summary.md` (parallel top-level
invariant placement pattern), `references/method-tagged-metrics-r12-summary.md`
(`_method` companions on C7/C8/C9).

Source spec section: Si-Chip v0.4.0-rc1 §18 (Normative); distilled
from `.local/research/r12_v0_4_0_industry_practice.md` §2.1 + §4.1.
This reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
