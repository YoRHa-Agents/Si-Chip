# Si-Chip `evals/si-chip/golden_set/`

> **Status (Round 10, project v0.1.9):** NEW opt-in source for a partial
> generalizability proxy. Non-authoritative — the full golden set
> (≥ 50 prompts per pack + real-LLM eval) is **v0.3.x+** work.

## Purpose

Two YAML files + this README seed a small opt-in "golden set" that
addresses two otherwise-uncovered surfaces in `v0.1.x`:

1. **`nines self-eval` D01 `scoring_accuracy` = 0 / D02 `eval_coverage` = 0 /
   D03 `samples_dir_exists` = 0 / D05 `golden_set_path` = 0 signals.** The
   `.local/dogfood/2026-04-28/round_3/raw/nines_self_eval_out/self_eval_report.txt`
   run flagged these four dimensions as zero because the workspace had no
   canonical `data/golden_test_set/` or `evals/**/golden_set/` path. Round 10
   master plan explicitly adds `evals/si-chip/golden_set/` to seed the
   directory so Round 10+ rounds can opt-in without renaming.
2. **`G1_cross_model_pass_matrix` partial fill.** Round 10 populates G1 by
   collapsing the existing mvp 8-cell router-test sweep along the depth
   dimension. That fills G1 (D4 0/4 → 1/4 sub-metric coverage) but the
   prompts driving those pass-rates are HARD-CODED deterministic anchors
   in `evals/si-chip/runners/with_ability_runner.py::MVP_CELL_OUTCOMES`,
   not real-LLM responses. The golden_set/ YAMLs document what the *real*
   prompts SHOULD be when the router-test is upgraded to a real-LLM
   runner (Round 12+ upgrade path).

## Schema (both `trigger_basic.yaml` and `near_miss.yaml`)

```yaml
pack: trigger_basic | near_miss
expected_outcome: trigger | no_trigger
generated_at: '<ISO-8601>'
spec_version: v0.1.0
source_round: round_10
prompts:
  - prompt_id: gs_tb_NNN | gs_nm_NNN     # unique within pack
    prompt: "<verbatim prompt text>"
    expected: trigger | no_trigger        # must match pack
    rationale: "<one-line justification>"
    source_case: "<case.yaml>#<bucket>.<id>"
provenance:
  generator: "Round 10 dogfood — L3 Task Agent"
  basis: [<case yaml paths>]
  runner_reference: <existing result.json paths>
  notes: "<multi-line>"
```

## Contents

| Pack            | Count | Expected outcome | Source cases                                                                   |
| --------------- | ----- | ---------------- | ------------------------------------------------------------------------------ |
| `trigger_basic` | 12    | `trigger`        | `profile_self`, `metrics_gap`, `router_matrix`, `half_retire_review`, `next_action_plan`, `docs_boundary` |
| `near_miss`     | 12    | `no_trigger`     | `profile_self`, `metrics_gap`, `router_matrix`, `half_retire_review`, `next_action_plan` |

Each entry is copy-paste verbatim from the source case file — NO NEW
PROMPTS were authored in Round 10. This keeps the golden set traceable
to the deterministic runner's existing `prompt_outcomes` coverage.

## What this is NOT

* **NOT authoritative for G1.** G1 from the mvp 8-cell sweep is a
  2-model × 2-pack PARTIAL proxy. Authoritative G1 requires the full
  96-cell router-test matrix (§5.3) + real-LLM runner — a
  `v2_tightened+` / Round 12+ upgrade.
* **NOT a full golden set.** Spec §3.1 D4 G2/G3/G4 (cross-domain,
  OOD, version-stability) are explicitly out of scope for v0.1.x per
  the master plan `.local/.agent/active/v0.2.0-iteration-plan.yaml#round_10`.
* **NOT consumed by the deterministic runner.** The runner uses
  `evals/si-chip/cases/*.yaml` (the 6 canonical cases, 20 prompts each).
  These YAMLs are downstream / opt-in; a future `nines self-eval --golden-dir
  evals/si-chip/golden_set/` invocation will lift the D01/D02/D03/D05
  signals.

## Versioning policy

* Round 10 seeds the directory. No further edits are expected until a
  real-LLM eval runner lands (v0.3.x+).
* If this directory changes semantics between rounds (new entries, schema
  edits, or pack renaming), the changing round's
  `iteration_delta_report.yaml` MUST call it out explicitly. Silent edits
  violate the workspace "No Silent Failures" rule.

## Spec §11 compliance

* **No marketplace surface.** These YAMLs are internal dogfood evidence;
  they do not introduce any distribution/manifest fields.
* **No router-model training.** Golden-set prompts are LABELS for a
  future real-LLM eval, not training data for a learned ranker.
* **No Markdown-to-CLI converter.** Plain YAML only.
* **No generic IDE compatibility layer.** Path is under
  `evals/si-chip/`, scoped to this repo.
