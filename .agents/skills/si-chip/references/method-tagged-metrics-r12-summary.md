# Method-Tagged Metrics — R12 Summary (Spec §23)

> Reader-friendly summary of the §23 method-tagged-metrics Normative
> chapter (v0.4.0-rc1). Authoritative sources:
> `.local/research/spec_v0.4.0-rc1.md` §23 and
> `.local/research/r12_v0_4_0_industry_practice.md` §2.5 + §4.6.

## Why this section exists

chip-usage-helper Round 17 R36 measured three parallel token values:

- ASCII-heavy text: char-heuristic vs tiktoken ±5%.
- CJK-heavy text: ±20%.
- Code blocks: 2–5× off.
- Template extraction: **2.4× off** (1.9K char-heuristic predicted
  vs 786 tiktoken actual — the biggest miss).

Without `_method` tags in `metrics_report.yaml`, reviewers couldn't
see that a "big token win" round-on-round actually came from a
measurement-method swap, not an ability improvement. §23 makes every
metric's method and confidence band first-class so round-on-round
deltas stop getting confounded.

## `<metric>_method` companion fields (§23.1)

`templates/method_taxonomy.template.yaml` (Wave 1b lands the full
schema) defines allowed values per metric:

| Metric class | `_method` enum | Default |
|---|---|---|
| Token metrics (C1, C2, C3, C4, §18 C7/C8/C9) | `{tiktoken, char_heuristic, llm_actual}` (C3 is `{tiktoken, llm_actual}` — runtime trace required) | `tiktoken` |
| Quality metrics (T1, T2, T3, §14 C0) | `{real_llm, deterministic_simulator, mixed}` (C0 only first two) | `real_llm` |
| Routing metrics (R3, R3_eager_only, R3_post_trigger) | `{real_llm, deterministic_simulator}` | `real_llm` |
| Generalizability G1 | `{real_llm_sweep, deterministic_simulation, mixed}` | `real_llm_sweep` |

Emit pattern in `metrics_report.yaml`:

```yaml
metrics:
  task_quality:
    T1_pass_rate: 0.97
    T1_pass_rate_method: real_llm
    T2_pass_k: 0.78
    T2_pass_k_method: real_llm
    T3_baseline_delta: 0.85
    T3_baseline_delta_method: real_llm
    T4_error_recovery_rate: 0.85
    T4_error_recovery_rate_method: deterministic_simulator
  context_economy:
    C1_metadata_tokens: 86
    C1_metadata_tokens_method: tiktoken
    C4_per_invocation_footprint: 4612
    C4_per_invocation_footprint_method: tiktoken
token_tier:
  C7_eager_per_session: 365
  C7_eager_per_session_method: tiktoken
```

## Confidence band `_ci_low` / `_ci_high` (§23.2)

When `_method == char_heuristic`, two additional fields are REQUIRED
to encode measurement uncertainty:

```yaml
C1_metadata_tokens: 1900
C1_metadata_tokens_method: char_heuristic
C1_metadata_tokens_ci_low: 1500
C1_metadata_tokens_ci_high: 2300
```

Suggested half-widths by content type (§23.2.1):

- ASCII-heavy text: ±5% (char / 4 ≈ tokens).
- CJK-heavy text: ±20% (chars ≈ tokens but emoji + punctuation skew).
- Code blocks: 2–5× (char count >> tokens because BPE compresses).
- Template extraction: **2.4×** (biggest observed).

When content type is uncertain, use the widest applicable band
(±100% for template-extraction unknowns).

### Round-on-round overlap rule (§23.2.2)

When two rounds both use `char_heuristic` and their `_ci` intervals
overlap, spec_validator WARNs:

> "metric delta within confidence band; consider switching to tiktoken
> before claiming axis improvement"

This prevents measurement noise from being published as ability wins.

## `U1_language_breakdown` (§23.3)

§3.1 D5 U1 `description_readability` currently returns a single
Flesch-Kincaid grade. chip-usage-helper R29 showed bilingual SKILL.md
descriptions inflate FK-grade because CJK single characters count as
1 syllable under the stdlib heuristic. §23.3 adds per-language
breakdown:

```yaml
U1_description_readability: 9.2
U1_description_readability_method: flesch_kincaid_chinese_character_lossy
U1_language_breakdown:
  en:
    char_count: 1024
    flesch_kincaid: 8.4
  zh:
    char_count: 320
    chinese_readability_grade: "中等"
  mixed_warning: true  # readers MUST NOT cross-ability compare on FK alone when true
```

## `U4_state` (§23.4)

§3.1 D5 U4 `time_to_first_success` returns a single number of
seconds. chip-usage-helper R19 showed `npm ci` cold cache is 30–90s
vs warm cache <2s — the same metric value means entirely different
things in the two states. §23.4 adds:

```yaml
U4_time_to_first_success: 12.4
U4_time_to_first_success_state: warm
```

`state ∈ {warm, cold, semicold}`:

- `warm` — dependency cache populated (`node_modules/` exists +
  `package-lock.json` hash matches).
- `cold` — dependency cache empty (fresh checkout, full
  `npm ci` required).
- `semicold` — partial hit (`node_modules/` exists but lockfile has
  drifted, partial reinstall).

## R3 split cross-reference (§23.5 → §18.3)

`R3_eager_only` and `R3_post_trigger` take the routing-metric
`_method` enum `{real_llm, deterministic_simulator}`. See
`references/token-tier-invariant-r12-summary.md` §18.3 for the split
rationale. §23.5 is a pure cross-list to keep the method-taxonomy
table complete.

## spec_validator ignores companion suffixes (§23.6)

`tools/spec_validator.py::R6_KEYS` BLOCKER strips these suffixes
before counting:

- `_method`
- `_ci_low`
- `_ci_high`
- `_language_breakdown`
- `_state`
- `_provenance` (G1 specific)
- `_sampled_at`
- `_sample_size_per_cell`

Implementation sketch:

```python
COMPANION_SUFFIXES = (
    "_method", "_ci_low", "_ci_high",
    "_language_breakdown", "_state",
    "_provenance", "_sampled_at", "_sample_size_per_cell",
)

def is_companion_key(key: str) -> bool:
    return any(key.endswith(suffix) for suffix in COMPANION_SUFFIXES)

def count_r6_keys(metrics_dim: dict) -> int:
    return sum(1 for k in metrics_dim if not is_companion_key(k))
```

The 7 × 37 = 37 sub-metric count stays frozen; companions are
metadata, not additional sub-metrics.

## Forever-out re-check (§23.7)

| §11.1 forever-out | Touched by §23? |
|---|---|
| Marketplace | NO — `_method` tags are field suffixes in `metrics_report.yaml`; `method_taxonomy.template.yaml` is spec-internal. |
| Router model training | NO — method tags are measurement provenance; `{tiktoken, char_heuristic, llm_actual}` are BPE / regex / runtime variants, not model weights. |
| Generic IDE compat | NO — schema is spec-internal; tiktoken is a BPE encoder, not an IDE adapter. |
| Markdown-to-CLI | NO — emit is evaluator runtime behaviour; taxonomy is a hand-written controlled vocabulary. |

## Cross-References

| §23 subsection | Spec section | R12 section |
|---|---|---|
| 23.1 method companions | spec §23.1 | r12 §2.5.b Inspect AI + §2.1.d DSPy |
| 23.2 CI bands for char-heuristic | spec §23.2 | r12 §4.6 |
| 23.3 U1 language breakdown | spec §23.3 | r12 §4.6 |
| 23.4 U4 state | spec §23.4 | r12 §4.6 |
| 23.5 R3 split cross-list | spec §23.5 | r12 §4.1 (cross-ref §18.3) |
| 23.6 spec_validator strip | spec §23.6 | r12 §4.6 |
| 23.7 forever-out re-affirm | spec §23.7 | r12 §7 |

Cross-ref: `references/token-tier-invariant-r12-summary.md`
(§18.3 R3 split origin), `references/eval-pack-curation-r12-summary.md`
(§22.2 G1 provenance first-class field is an instance of this
pattern), `references/metrics-r6-summary.md` (R6 7×37 frozen count
preserved because companions don't count).

Source spec section: Si-Chip v0.4.0-rc1 §23 (Normative); distilled
from `.local/research/r12_v0_4_0_industry_practice.md` §2.5 + §4.6.
This reference is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
