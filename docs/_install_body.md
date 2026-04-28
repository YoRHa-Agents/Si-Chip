
This guide covers Cursor and Claude Code installation (the two v0.1.0
priorities per spec §7.2), the deferred Codex bridge, developer setup, and
smoke tests.

## Prerequisites

- Python >= 3.10
- git
- Optional: `tiktoken` (for accurate token counting; otherwise
  `count_tokens.py` falls back to a deterministic whitespace splitter and
  reports `backend=fallback`).
- Optional: `devolaflow` (R7 §1 upstream — `pip install
  git+https://github.com/YoRHa-Agents/DevolaFlow.git`).
- Optional: `nines` CLI (for live LLM eval; the included runners are
  deterministic seeded simulations otherwise).

## 1. Clone the Repository

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
```

## 2. Cursor Install (priority 1)

The Skill is mirrored at `.cursor/skills/si-chip/`. Cursor auto-discovers it
on workspace open. The optional bridge rule
`.cursor/rules/si-chip-bridge.mdc` is included and points back at
`.cursor/skills/si-chip/SKILL.md` plus `AGENTS.md`.

Reload Cursor; the Skill should appear under the project's local skills.

Verify:

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .cursor/skills/si-chip/SKILL.md --both
```

Expect `metadata_tokens=78`, `body_tokens=2020`, `pass=true` (matches the
spec §7.3 packaging gate; identical to the canonical mirror per the
`three_tree_drift_summary.json` artifact).

## 3. Claude Code Install (priority 2)

The Skill is mirrored at `.claude/skills/si-chip/`. Claude Code
auto-discovers it on session start.

Verify:

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .claude/skills/si-chip/SKILL.md --both
```

Same gate numbers as the Cursor mirror.

## 4. Codex (deferred to follow-up)

v0.1.0 ships [`AGENTS.md`](./AGENTS.md), which is compiled from
`.rules/si-chip-spec.mdc`. Codex reads `AGENTS.md`, so the Normative spec
content (§3 / §4 / §5 / §6 / §7 / §8 / §11) is in front of Codex on every
session.

Native `.codex/profiles/si-chip.md` plus
`.codex/instructions/si-chip-bridge.md` are deferred per spec §7.2 priority
3 ("Codex; v0.1.0 bridge only; no native SKILL.md runtime assumption").
Tracked in the ship report's "Next Steps (post-ship)" section.

## 5. Developer Setup

```bash
pip install pyyaml
pip install tiktoken                                            # optional
pip install git+https://github.com/YoRHa-Agents/DevolaFlow.git  # optional
```

`pyyaml` is the only hard dependency for the bundled scripts. `tiktoken`
matches CI's token counting backend; `devolaflow` is required only when you
want to drive Si-Chip through the upstream `template_engine` /
`memory_router` paths (spec §5.1, §9).

## 6. Smoke Tests

```bash
python tools/spec_validator.py --json

python .agents/skills/si-chip/scripts/profile_static.py \
  --ability si-chip --out /tmp/profile.yaml

python evals/si-chip/runners/no_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/no_ability/ --seed 42

python evals/si-chip/runners/with_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/with_ability/ --seed 42

python .agents/skills/si-chip/scripts/aggregate_eval.py \
  --runs-dir /tmp/with_ability --baseline-dir /tmp/no_ability \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --templates-dir templates --out /tmp/metrics_report.yaml
```

Expected: `spec_validator` exits 0 with `verdict: PASS`; `profile_static`
emits a `BasicAbilityProfile` YAML against the §2.1 schema; the two runners
populate per-case `result.json` files; `aggregate_eval` produces a
`metrics_report.yaml` with the MVP-8 keys filled and the remaining 29 keys
explicitly null (matches
[`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md)).

## 7. Troubleshooting

- `count_tokens.py` reports `backend=fallback`: install `tiktoken` for
  parity with CI; the fallback uses a deterministic whitespace splitter and
  may report different token counts.
- `aggregate_eval.py` warns about a schema cross-check: expected. The
  templates are JSON-Schema-shaped (`properties.basic_ability.properties.metrics.properties`),
  not a direct `basic_ability.metrics` map. MVP-8 keys are still validated
  independently. The smoke report documents this as a non-blocking warning.
- `spec_validator.py --strict-prose-count` exits 1: expected. The strict
  mode treats §13.4 prose counts (28, 21) as authoritative against the §3.1
  / §4.1 TABLE counts (37, 30) and is intentionally designed to flag the
  prose-vs-table discrepancy. Default mode (no `--strict-prose-count`) uses
  the TABLE counts and exits 0.

## 8. Uninstall

- Cursor: delete `.cursor/skills/si-chip/` and reload the workspace.
- Claude Code: delete `.claude/skills/si-chip/` and restart the session.
- Repo: `rm -rf Si-Chip/`.
