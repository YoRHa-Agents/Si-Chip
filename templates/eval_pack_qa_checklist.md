# Eval-Pack QA Checklist (Si-Chip §22.3 Informative)

> Checklist for authoring an ability's `eval_pack.yaml` per spec §22. Use during round_1 of any new ability dogfood; re-visit before v2_tightened promotion.
>
> Spec status: **Informative @ v0.4.0**. Promotion-to-Normative trigger lives in spec §22.3.1 (mirror of §16.3 Informative-then-Normative adoption pattern). Once two abilities file out a completed checklist adjacent to their `eval_pack.yaml`, a spec bump flips this file to Normative and introduces a new spec_validator BLOCKER `EVAL_PACK_QA_CHECKLIST_FILLED`.

## 1. Bilingual coverage
- [ ] If ability targets CJK users: pack has >= 40% CJK prompts + >= 40% Latin prompts
- [ ] If English-only: pack size >= 20 (MVP) / >= 40 (v2_tightened promotion)
- [ ] Each natural-language surface the ability users interact with has representative prompts
- [ ] Mixed EN/CJK prompts (common in bilingual workspaces) are labelled `language: mixed` so downstream aggregators do not double-count them

## 2. Near-miss curation (anti-artifact)
- [ ] 2-5 negative prompts per positive category
- [ ] Negatives explicitly include the "trigger word appears but in wrong context" class
  (e.g. "explain how Cursor Composer works" for a chip-usage-helper pack — the word "Cursor" appears but the prompt is meta-questioning, not billing)
- [ ] Time-spend-discriminator / meta-discriminator patterns documented (per chip-usage-helper Round 1-2 findings)
- [ ] Cross-skill ambiguity captured: if another ability plausibly owns a prompt, include a negative covering that case so R8 `description_competition_index` is measurable

## 3. Anti-patterns to avoid
- [ ] No naive `\w+` tokenization for CJK inputs (fails per chip-usage-helper R2 evidence: F1 artifact 0.7778 -> 0.9524 after fix)
- [ ] No single-language packs for multi-language ability
- [ ] No over-trivial positives ("usage" alone is a weak trigger; need contextual anchors)
- [ ] No benchmark detection per MLPerf submission rule discipline
- [ ] No silent truncation: if a prompt is trimmed for fit, the original is preserved in `source_prompt` so audits can reproduce the decision

## 4. 40-prompt minimum gate (v2_tightened)
- [ ] Pack has >= 40 prompts total when aiming for v2_tightened promotion
- [ ] 20 should-trigger + 20 should-not-trigger OR documented asymmetric ratio with rationale
- [ ] Per spec §22.1: 20-prompt packs remain MVP-valid for v1_baseline only
- [ ] Per spec §22.1: v3_strict decisions recommend >= 60 prompts to keep the measurement noise band below the gate delta (0.025 vs 0.05)

## 5. Fixed-seed determinism (§22.5)
- [ ] Deterministic eval simulators seed with `hash(round_id + ability_id)` (spec §22.5 frozen constraint #5)
- [ ] Re-running the harness on unchanged source produces byte-identical metrics
- [ ] Cache dir `.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/` populated for CI replay (§22.6)
- [ ] CI runs the real-LLM runner with `--seal-cache` so cache misses do not silently call the live API; local dev runs without the flag to allow cache build-up

## 6. Provenance labels (§22.2)
- [ ] Every G1 row in metrics_report.yaml has `provenance ∈ {real_llm_sweep, deterministic_simulation, mixed}`
- [ ] T2_pass_k reports `_method ∈ {real_llm, deterministic_simulator}` per §23.1
- [ ] Token-related metrics (C1/C2/C4/C7/C8/C9) carry `_method ∈ {tiktoken, char_heuristic, llm_actual}` — char_heuristic values require `_ci_low` / `_ci_high` per §23.2

## 7. Anti-artifact regression checks
- [ ] Round-over-round F1 delta >= 0.05 counts as "actionable"; < 0.05 is "within noise band" (§3.1 D1 T3 interpretation floor)
- [ ] Add one new case per code_change round that fixed a bug (case becomes permanent regression test)
- [ ] When method swaps (e.g. char_heuristic -> tiktoken) cause a metric jump, annotate the iteration_delta row with `method_swap: true` so the delta is not misread as an ability change

## 8. Pack sizing recommendations by gate

| Gate | Minimum pack size | Recommended |
|------|------------------:|-----------:|
| v1_baseline | 20 | 20-40 |
| v2_tightened | 40 | 40-80 |
| v3_strict | 80 | 80-160 |

> Rationale: at 20 prompts, a single false positive moves F1 by ~0.05 (the v1_baseline bucket); at 40 prompts the same FP moves F1 by ~0.025 (tolerable inside the v2_tightened 0.05 delta window); at 80+ prompts the measurement noise is decoupled from ability drift.

## 9. Cross-references
- spec §3.1 D6 R3/R4 — trigger F1 metric definitions
- spec §5.3 — router-test matrix (MVP 8 cells / Full 96 cells)
- spec §22.1-§22.7 — eval-pack curation discipline (this file is §22.3)
- spec §23.1 — method taxonomy (for `_method` field values)
- spec §23.2 — `_ci_low` / `_ci_high` confidence band for char-heuristic-derived tokens
- `templates/method_taxonomy.template.yaml` — companion-field controlled vocabulary
- `templates/recovery_harness.template.yaml` — canonical T4 4-scenario branch generator
- `r12 §2.5` — industry practice survey (OpenAI Evals / Inspect AI / MLPerf citations)
- `r12 §4.5` — design rationale for the §22 chapter

## 10. How to adopt
1. Copy this checklist into your ability's source tree as `eval_pack_qa.md` (adjacent to `eval_pack.yaml`).
2. Tick boxes as items are satisfied during round_1 of your ability dogfood.
3. Re-open the checklist before filing an `iteration_delta_report.yaml` that requests promotion from v1_baseline to v2_tightened; unchecked items in sections 1-6 count as v2_tightened promotion blockers.
4. Archive the completed checklist alongside the round artifacts under `.local/dogfood/<DATE>/<round_id>/raw/eval_pack_qa.md`.

---

## Provenance
- Authored: 2026-04-30 (Si-Chip v0.4.0-rc1 Stage 4 Wave 1a)
- Spec version: v0.4.0-rc1
- Source: r12 §4.5 + chip-usage-helper Round 1-19 evidence (SUMMARY.md R3/R14/R25)
- Cross-cites: Inspect AI `Sample.metadata` first-class pattern (r12 §2.5.b); MLPerf submission rules (r12 §2.5.c); DSPy `metric_threshold` gating (r12 §2.5.a)
