# eval_skill.py Quickstart

> CLI cheat-sheet for `tools/eval_skill.py` — the generic per-ability
> evaluation harness introduced in Si-Chip spec v0.3.0-rc1.

## Purpose

Single entry point for any `BasicAbility`'s per-round evaluation.
Replaces ability-specific ~768-line harnesses (e.g.
`eval_chip_usage_helper.py`) with a ~50-line ability adapter calling
this CLI; R11 §7 estimates ~600 LoC saved per new ability.

Emits a `metrics_report.yaml` matching the §3.1 R6 7×37 schema with
all 37 keys present (null placeholders allowed per §3.2 frozen
constraint #2), plus the `core_goal_check` block per §14.3 and the
root `round_kind` field per §15.

## Per-ability inputs

| Flag | Required | Purpose |
|---|:---:|---|
| `--ability <id>` | yes | `BasicAbility.id` (e.g. `si-chip`, `chip-usage-helper`). |
| `--skill-md <path>` | yes | Ability SKILL.md — feeds C1 metadata / C2 body via `count_tokens.py`. |
| `--vocabulary <path>` | yes | Per-ability YAML for `tools/cjk_trigger_eval.py` (R1/R2/R3/R4). |
| `--eval-pack <path>` | yes | 20-40 prompt trigger eval pack (should / should_not lists). |
| `--core-goal-test-pack <path>` | yes | ≥3 case core_goal pack (§14.2); drives C0. |
| `--test-runner-cmd "<cmd>"` | yes | Shell command for functional tests (T1 + L1/L2). |
| `--test-runner-cwd <path>` | yes | CWD for the test runner. |
| `--runs <N>` | no | Repetitions for L1/L2 percentiles (default `3`). |
| `--round-kind <kind>` | no | One of `code_change` / `measurement_only` / `ship_prep` / `maintenance` (§15.1). |
| `--baseline-runner-cmd "<cmd>"` | no | No-ability baseline runner (enables T3 delta). |
| `--prior-c0-pass-rate <f>` | no | Prior round's C0 for §14.3.2 no-regression check. |
| `--count-tokens-script <path>` | no | Override path to `count_tokens.py` (default `.agents/skills/si-chip/scripts/count_tokens.py`). |
| `--out <path>` | no | Destination `metrics_report.yaml` (omit to only print summary). |

## Example: Si-Chip self-dogfood Round 14 (`code_change`)

```bash
python tools/eval_skill.py \
  --ability si-chip \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --vocabulary .local/dogfood/$(date -u +%F)/abilities/si-chip/vocabulary.yaml \
  --eval-pack .local/dogfood/$(date -u +%F)/abilities/si-chip/eval_pack.yaml \
  --core-goal-test-pack .local/dogfood/$(date -u +%F)/abilities/si-chip/core_goal_test_pack.yaml \
  --test-runner-cmd "pytest -q tools/ .agents/skills/si-chip/scripts/" \
  --test-runner-cwd . \
  --runs 3 \
  --round-kind code_change \
  --out .local/dogfood/$(date -u +%F)/round_14/metrics_report.yaml
```

Exit code is `0` on successful measurement (even when thresholds
would fail — `tools/spec_validator.py` is the gate). `C0 < 1.0`
fills `core_goal_check.rollback_required = true` per §15.3 universal
invariant but does not change the exit code; the REVERT-only action
(§14.4) is the operator's to take.

## Output shape

`metrics_report.yaml` top-level keys emitted by the harness:

- `schema_version: "0.2.0"` / `script_version` / `ability_id` / `round_kind` / `generated_at`
- `metrics` — the R6 7×37 dict with all 37 keys present (null where
  unmeasured; MVP-8 filled per §3.2 frozen constraint #1).
- `core_goal` — C0 block (`C0_core_goal_pass_rate`, `cases_passed`,
  `cases_total`, `failed_case_ids`, `per_case`).
- `core_goal_check` — §14.3 verdict block consumed by
  `iteration_delta_report.yaml.core_goal_check`.
- `trigger_confusion` + `trigger_per_prompt` — from
  `cjk_trigger_eval`.
- `token_info` / `functional_tests` / `baseline_tests` — raw traces.

## Composition with the other v0.3.0 tools

| Metric block | Measured by |
|---|---|
| D1 T1/T3 + D3 L1/L2 | `--test-runner-cmd` (+ `--baseline-runner-cmd` for T3 delta) |
| D2 C1/C2/C4 | `.agents/skills/si-chip/scripts/count_tokens.py` (subprocess) |
| D3 L4 (multi-handler) | `tools/multi_handler_redundant_call.py` (ability-adapter call) |
| D6 R1/R2/R3/R4 | `tools/cjk_trigger_eval.py::evaluate_pack` (+ pluggable vocabulary) |
| C0 core_goal_pass_rate | `run_core_goal_test_pack()` internal, per `--core-goal-test-pack` |
| round_kind field | `tools/round_kind.py` (shared enum + validator) |

Unmeasured R6 keys stay `null` by construction — downstream
ability-specific adapters can hoist them by editing the emitted
`metrics_report.yaml` in place.

## Cross-References

- `references/core-goal-invariant-r11-summary.md` — §14 C0 semantics
  and the `core_goal_check` verdict block consumed here.
- `references/round-kind-r11-summary.md` — §15 enum, decision tree,
  and promotion-counter eligibility.
- `references/metrics-r6-summary.md` — R6 7-dim / 37-sub-metric map
  behind the `metrics_report.yaml` shape.
- `scripts/count_tokens.py` / `scripts/aggregate_eval.py` /
  `scripts/profile_static.py` — canonical Si-Chip scripts this
  harness composes with.

Source: Si-Chip v0.3.0-rc1 §14, §15, and `tools/eval_skill.py` CLI
(verified via `python tools/eval_skill.py --help`).
