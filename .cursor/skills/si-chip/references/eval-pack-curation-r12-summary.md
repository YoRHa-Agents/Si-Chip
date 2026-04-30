# Eval-Pack Curation Discipline — R12 Summary (Spec §22)

> Reader-friendly summary of the §22 eval-pack-curation Normative
> chapter (v0.4.0-rc1). Authoritative sources:
> `.local/research/spec_v0.4.0-rc1.md` §22 and
> `.local/research/r12_v0_4_0_industry_practice.md` §2.5 + §4.5.

## Why this section exists

chip-usage-helper Round 1's `R3` jump from `0.7778` to `0.9524`
turned out to be **entirely methodology fixes**, not ability
improvements — CJK substring tokenization and a 40-prompt curated
pack replaced a naive `\w+` splitter and a 20-prompt pack. If §22
hadn't been lifted to spec, the next ability author would have
fallen into the same 30-minute methodology trap. §22 captures the
Cycle 1 lessons plus MLPerf / OpenAI-Evals / DSPy industry
precedent as a Normative curation discipline.

## 40-prompt minimum for v2_tightened (§22.1)

Pack size scales with gate promotion risk:

| Gate | Eval-pack minimum | Rationale |
|---|---|---|
| `v1_baseline` | 20 prompts (10 should + 10 should-not) | §5.3 MVP harness; smallest creditable sample |
| `v2_tightened` | **40 prompts** (20 should + 20 should-not + curated near-miss bucket) | 1 FP at 20 prompts shifts F1 by 0.05 (chip-usage-helper Round 1 evidence); 40 prompts halves that noise window to 0.025 so `R3 ≥ 0.85` decisions are creditable |
| `v3_strict` | 40 minimum / 60+ recommended | `R3 ≥ 0.90` still has ~0.025 noise window at 40 prompts; 60 prompts stabilizes |

§5.3's existing "Dataset" row is preserved byte-identical; §22.1.1
appends one v0.4.0 add-on sentence after the Normative table
declaring the 40-prompt floor for v2 promotion decisions. Wave 1b
`spec_validator` enforces the floor against
`next_action_plan.yaml.target_gate`.

## G1 `provenance` REQUIRED first-class field (§22.2)

`metrics_report.yaml.metrics.generalizability.G1_cross_model_pass_matrix`
is no longer a bare matrix; three first-class fields are now
required:

```yaml
G1_cross_model_pass_matrix:
  provenance: real_llm_sweep|deterministic_simulation|mixed
  matrix:
    composer_2/fast: 0.92
    claude-haiku-4-5: 1.00
    claude-sonnet-4-6: 0.97
    deterministic_memory_router: 0.85
  sampled_at: "2026-04-30T08:14:00Z"
  sample_size_per_cell: 20
```

### `provenance` enum semantics (§22.2.1)

- `real_llm_sweep` — matrix came from real LLM calls (r12.5
  PROCEED_MAJOR runner output).
- `deterministic_simulation` — matrix came from a deterministic
  simulator (e.g. SHA-256 `pass_k = pass_rate^k`). **Cannot
  underwrite v2/v3 promotion** — simulator output is algebraic and
  can't demonstrate cross-model robustness.
- `mixed` — some cells real, some simulated (e.g. `composer_2`
  unreachable from sandbox → deterministic substitute; claude family
  real). The yaml MUST note which cells are which.

§3.1 D4 G1 sub-metric count remains 1 (R6 7×37 frozen), with a prose
row added referencing the first-class `provenance`/`sampled_at`/
`sample_size_per_cell` fields.

## `templates/eval_pack_qa_checklist.md` (§22.3; Informative)

Six sections (abridged here; full template lands Wave 1b):

1. **Bilingual coverage** — CJK abilities use 50/50 EN/CJK ratio
   (chip-usage-helper R29 evidence); EN-only abilities must
   document why CJK is omitted.
2. **Near-miss curation** — every positive trigger paired with 2–5
   negatives, including "spend time" discriminators and cross-skill
   ambiguity.
3. **Anti-patterns** — no naive `\w+` tokenization for CJK; no
   single-language packs; no over-trivial prompts; no benchmark
   detection (§14.2.1 #5 + MLPerf rule).
4. **Reproducibility floor** — deterministic simulators seed with
   `hash(round_id + ability_id)`; cache keys
   `sha256(model + prompt + system + sample_idx)[:16]`; cache dir
   per §22.6.
5. **Pack size gates** — §22.1 thresholds.
6. **Provenance documentation** — G1.provenance + per-metric
   `_method` companions per §23.1.

Promote-to-Normative trigger (§16.3 pattern): ≥2 abilities fill the
checklist in `eval_pack_qa.md` adjacent files, OR one ability shows
checklist-driven noise reduction across two ships → bump v0.4.x and
add BLOCKER `EVAL_PACK_QA_CHECKLIST_FILLED`.

## `recovery_harness.template.yaml` for T4 (§22.4)

Canonicalizes the 4-scenario × 2-type × 0.25-weight branch pattern
first demonstrated by chip-usage-helper R8:

```yaml
scenarios:
  # identity-resolution type
  - { id: identity_match, type: identity, setup: "exact match", expected: "1 candidate, HIGH confidence", weight: 0.25 }
  - { id: identity_one_candidate, type: identity, setup: "partial match → 1 record", expected: "...", weight: 0.25 }
  - { id: identity_no_candidate, type: identity, setup: "match 0 records", expected: "graceful 'not found'", weight: 0.25 }
  - { id: identity_multi_candidate, type: identity, setup: "match 2+ records", expected: "all + disambiguate", weight: 0.25 }
  # tool-call type
  - { id: tool_success, type: tool_call, setup: "2xx valid payload", expected: "forward", weight: 0.25 }
  - { id: tool_expected_failure, type: tool_call, setup: "4xx", expected: "surface; no retry", weight: 0.25 }
  - { id: tool_recoverable_failure, type: tool_call, setup: "5xx / transient", expected: "retry per max_attempts", weight: 0.25 }
  - { id: tool_unrecoverable_failure, type: tool_call, setup: "persistent 5xx / 401", expected: "clear error; no infinite retry", weight: 0.25 }

t4_computation: "weighted_avg(scenario passes; weights sum to 1.0 per type)"
```

§3.1 D1 T4 sub-metric count unchanged (R6 7×37 frozen); the template
only standardizes how the 1 sub-metric is generated.

## Deterministic seeding rule (§22.5; §3.2 frozen constraint #5)

§3.2 previously had 4 frozen constraints; v0.4.0 adds #5:

> Deterministic eval simulators MUST seed with
> `hash(round_id + ability_id)` (SHA-256 truncated to first 16 hex
> chars used as `random.seed()`).

Rationale (MLPerf analog per r12 §2.5.c):

- **Ability-cross**: different abilities get different seeds so
  simulator artefacts don't spuriously correlate across abilities.
- **Round-on-round**: same ability, different round → different seed;
  simulator artefacts can't masquerade as stable results.
- **CI replay**: seed is a deterministic hash function; CI byte-
  reproduces the same sequence.

## Real-LLM cache directory (§22.6)

Per r12.5 Stage 1 spike PROCEED_MAJOR verdict (details in
`.local/research/r12.5_real_llm_runner_feasibility.md` §3.3 + §5.2):

- **Cache dir shape**:
  `.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/{meta.json, cache_<model>.json}`.
- **`meta.json`** holds `cache_seed`, `eval_pack_path`,
  `eval_pack_hash`, `system_prompt_hash`.
- **Per-sample entries** in `cache_<model>.json`: `{text, usage,
  stop_reason, elapsed_s, fetched_at}`.
- **Cache key**: `sha256(model + prompt + system + sample_idx)[:16]`.
- **CI determinism via `--seal-cache`**: production
  `real_llm_runner.py` refuses to call the LLM on cache miss when
  the flag is set → CI runs are pure replay with zero API cost.
- **Runner provenance into `metrics_report.yaml`**: every runner
  invocation writes `runner_provenance: {runner, runner_version,
  endpoint, models_used, cache_dir, cache_hits, cache_misses,
  total_calls, tokens_input, tokens_output, wall_clock_s}`.

See `scripts/real_llm_runner_quickstart.md` for per-ability usage.

## Forever-out re-check (§22.7)

| §11.1 forever-out | Touched by §22? |
|---|---|
| Marketplace | NO — checklist is hand-written Markdown; templates are spec-internal; cache is ability-local. |
| Router model training | NO — eval-pack curation is testing, not training; `acceptance_threshold` is per-case accept/reject, not a router model (r12 §7 explicit boundary). |
| Generic IDE compat | NO — packs are ability-local; cache uses sandbox-internal Veil egress. |
| Markdown-to-CLI | NO — checklist and templates are hand-written; seeds are hash functions. |

## Cross-References

| §22 subsection | Spec section | R12 section |
|---|---|---|
| 22.1 40-prompt minimum | spec §22.1 | r12 §4.5 + §2.5.c |
| 22.2 G1 provenance | spec §22.2 | r12 §2.5.a MLPerf |
| 22.3 eval_pack_qa_checklist | spec §22.3 | r12 §2.5.b Inspect AI |
| 22.4 recovery_harness template | spec §22.4 | r12 §4.5 |
| 22.5 deterministic seeding | spec §22.5 | r12 §2.5.c MLPerf |
| 22.6 real-LLM cache dir | spec §22.6 | r12.5 §3.3 + §5.2 |
| 22.7 forever-out re-affirm | spec §22.7 | r12 §7 |

Cross-ref: `references/method-tagged-metrics-r12-summary.md` (§23.1
`_method` companions bind to pack provenance),
`references/metrics-r6-summary.md` (D4 G1 row prose row added),
`scripts/real_llm_runner_quickstart.md` (CLI surface).

Source spec section: Si-Chip v0.4.0-rc1 §22 (Normative); distilled
from `.local/research/r12_v0_4_0_industry_practice.md` §2.5 + §4.5.
This reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
