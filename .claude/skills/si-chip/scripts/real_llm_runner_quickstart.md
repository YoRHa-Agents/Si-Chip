# real_llm_runner.py Quickstart

> CLI cheat-sheet for `evals/si-chip/runners/real_llm_runner.py` —
> the production real-LLM evaluator promoted from the r12.5 spike
> (PROCEED_MAJOR verdict, `.local/research/r12.5_real_llm_runner_feasibility.md`
> §6.1).

## Purpose

Unblocks `T2_pass_k` from the deterministic `pass_rate^k` algebraic
floor so `v2_tightened` (T2 ≥ 0.55) and `v3_strict` (T2 ≥ 0.65)
promotions become reachable (spec §22.6). Feeds
`tools/eval_skill.py` to emit `_method: real_llm` companion rows
per §23.1.

## Per-ability inputs

| Flag | Required | Purpose |
|---|:---:|---|
| `--ability <id>` | yes | `BasicAbility.id` (e.g. `si-chip`, `chip-usage-helper`). |
| `--eval-pack <path>` | yes | Path to the `eval_pack.yaml` (v2 promotion: ≥ 40 prompts per §22.1). |
| `--matrix-mode <mode>` | yes | `mvp` / `intermediate` / `full` — see below. |
| `--k <N>` | no | Samples per prompt (default 4; T2_pass_k metric). |
| `--out <path>` | yes | Destination JSON path under `raw/real_llm_run.json`. |
| `--endpoint <url>` | no | Override Veil endpoint (default `http://127.0.0.1:8086`). |
| `--max-calls <N>` | no | Hard cap (default derived from `matrix-mode`). |
| `--cache-dir <path>` | no | Override cache dir (default per §22.6 round path). |
| `--seal-cache` | no | CI replay mode — refuse to call LLM on cache miss. |

## Model choices

Physical models via Veil `litellm-local` (`http://127.0.0.1:8086`):

| Model id | Role | ~Cost (100-prompt k=4) |
|---|---|---|
| `claude-haiku-4-5` | Cheapest; v1_baseline floor | ~$0.001 |
| `claude-sonnet-4-6` | v2_tightened default | ~$0.01 |
| `claude-opus-4-6` | v3_strict preferred | ~$0.05 |
| `composer_2/fast` | Cursor-internal; remaps to haiku | (remapped) |

`composer_2` is sandbox-unreachable; the `RouterFloorAdapter`
transparently remaps to `claude-haiku-4-5` and records the
substitution in `runner_provenance` (r12.5 §4.3.b).

## Matrix modes

| Mode | Cells | Wall-clock (p50) | Est. cost |
|---|---|---|---|
| `mvp` | 2 × 2 × 2 = 8 cells | ~1 min | ~$0.01 |
| `intermediate` | 4 × 2 × 2 = 16 cells | ~3 min | ~$0.05 |
| `full` | 6 × 4 × 4 = 96 cells | ~15 min | ~$0.50 |

Cells are the cartesian product of `models × thinking_depths ×
scenario_packs`. `mvp` covers the §5.3 8-cell MVP; `full` covers
the 96-cell harness required for v3_strict cross-model attestation.

## Example: Si-Chip Round 18 v2_tightened push

```bash
python evals/si-chip/runners/real_llm_runner.py \
    --ability si-chip \
    --eval-pack .local/dogfood/2026-04-30/abilities/si-chip/eval_pack.yaml \
    --matrix-mode mvp \
    --k 4 \
    --out .local/dogfood/2026-04-30/abilities/si-chip/round_18/raw/real_llm_run.json
```

Exit codes: `0` on successful evaluation (regardless of gate pass);
non-zero on runner error (LLM non-200, cache seal violation under
`--seal-cache`, or missing eval-pack). Output JSON contains
`T1 / T2 / matrix / runner_provenance` that `tools/eval_skill.py`
ingests to fill the §22.2 / §23.1 companion fields.

## Caching (§22.5 + §22.6)

- Cache dir:
  `.local/dogfood/<DATE>/<round_id>/raw/real_llm_runner_cache/`.
- Key: `sha256(model + prompt + system + sample_idx)[:16]`.
- `meta.json` sibling carries `cache_seed` + `eval_pack_hash` +
  `system_prompt_hash` (edit either → cache invalidates).
- Warm-cache re-runs cost zero API calls (spike: 8/8 replayed in ~5s).
- `--seal-cache` forces pure replay — CI calls MUST set this.
- Deterministic seed per §22.5: `random.seed(hash(round_id +
  ability_id))` so cross-ability / round-on-round byte-reproduces.

## How it composes with `eval_skill.py`

`tools/eval_skill.py`'s G1/G2/G3/G4 helpers consume this runner's
JSON to populate cross-model / cross-domain / OOD metrics with
`G1.provenance: real_llm_sweep` (§22.2):

```bash
python evals/si-chip/runners/real_llm_runner.py \
    --ability <id> --eval-pack <pack> --matrix-mode mvp \
    --out <round>/raw/real_llm_run.json
python tools/eval_skill.py \
    --ability <id> --skill-md <...> --vocabulary <...> \
    --eval-pack <pack> --core-goal-test-pack <...> \
    --real-llm-run <round>/raw/real_llm_run.json \
    --round-kind code_change \
    --out <round>/metrics_report.yaml
```

## Cross-references

- `references/eval-pack-curation-r12-summary.md` — §22.6 cache
  directory spec, §22.1 pack-size gates.
- `references/method-tagged-metrics-r12-summary.md` — §23.1
  `_method` companion emit; `real_llm` vs `deterministic_simulator`.
- `scripts/eval_skill_quickstart.md` — parent harness CLI.
- `.local/research/r12.5_real_llm_runner_feasibility.md` — spike
  origin, PROCEED_MAJOR verdict, retry / rate-limit design notes.

Source: Si-Chip v0.4.0-rc1 §22.6 (real-LLM cache dir) + r12.5 §3.3 +
§5.2 (spike caching strategy + production readiness assessment).
This quickstart is loaded on demand and is excluded from the §7.3
SKILL.md body budget.
