# Contributing to Si-Chip

Thank you for considering a contribution. Si-Chip is a persistent BasicAbility
optimization factory governed by a frozen specification. Please read this guide
in full before opening a pull request.

## 1. Source of Truth

The canonical Skill body lives at `.agents/skills/si-chip/`. The Cursor mirror
(`.cursor/skills/si-chip/`) and the Claude Code mirror (`.claude/skills/si-chip/`)
are generated from the canonical source and MUST NOT diverge. Drift between
the three trees is a CI failure (see
`.local/dogfood/<DATE>/round_<N>/raw/three_tree_drift_summary.json`).

## 2. Frozen Spec & Out-of-Scope

The frozen spec is `.local/research/spec_v0.1.0.md`. Sections §3, §4, §5, §6,
§7, §8, and §11 are NORMATIVE — any PR that contradicts them is rejected.

Permanently out of scope (spec §11.1 — will be rejected without discussion):

- Skill / Plugin marketplaces and any distribution surface
- Router model training or online weight learning
- Markdown-to-CLI converters
- Generic IDE / agent-runtime compatibility layers

Deferred (spec §11.2 — open for v0.2+ once gate v3_strict has been earned):

- Codex native SKILL.md runtime
- Plugin distribution (commands / hooks / marketplace upgrade)
- Broader IDE coverage (OpenCode, Copilot CLI, Gemini CLI, ...)

## 3. Branching & PR Workflow

- `main` is protected; never push directly. Create a feature branch and open a PR.
- Branch naming: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`, `docs/<topic>`.
- One logical change per PR. Use `git commit --amend` only on commits that have
  not been pushed.
- Every PR must reference (a) the spec section it touches and (b) the dogfood
  round number that produced or validated the change.

## 4. Required Local Checks Before Pushing

```bash
# Packaging gate (metadata <= 100, body <= 5000)
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .agents/skills/si-chip/SKILL.md --both \
  --budget-meta 100 --budget-body 5000 --json

# 8 spec invariants
python tools/spec_validator.py --json

# Cross-tree drift (after any sync)
diff -r .agents/skills/si-chip .cursor/skills/si-chip | grep -v DESIGN.md
diff -r .agents/skills/si-chip .claude/skills/si-chip | grep -v DESIGN.md
```

All three MUST pass.

## 5. Adding a New Eval Case

1. Author `evals/si-chip/cases/<case_id>.yaml` with exactly 10 should_trigger and
   10 should_not_trigger prompts.
2. Each `should_trigger` prompt must have at least 1 `acceptance_criteria` entry
   with `how_verified` ∈ {regex, json_field, file_exists, command_exit_zero, llm_judge}.
3. Run the structural check from `evals/si-chip/SMOKE_REPORT.md` to confirm the
   case parses.
4. Trigger one new dogfood round (`.local/dogfood/<DATE>/round_<N>/`) and attach
   the 6 evidence files to your PR.

## 6. Bumping the Spec

Spec changes require:

1. A NEW spec file (do not edit `.local/research/spec_v0.1.0.md` in place).
2. Updated `effective_date` and `supersedes` frontmatter.
3. Refreshed `.rules/si-chip-spec.mdc` and re-compiled `AGENTS.md`.
4. Refreshed `.rules/.compile-hashes.json`.
5. A passing run of `python tools/spec_validator.py --spec <new_path> --json`.

## 7. Reporting Issues

Please file issues at https://github.com/YoRHa-Agents/Si-Chip/issues with:

- The spec section involved (if applicable).
- The dogfood evidence file showing the regression (if applicable).
- A minimal reproduction (preferably a one-line spec_validator invocation).

## 8. License

By contributing you agree that your contributions are licensed under the
project's Apache-2.0 LICENSE.

## 9. Mirror Drift Contract

Si-Chip ships the Skill payload in **four trees**, all of which MUST stay byte-identical for the 9 manifest files (SKILL.md + 5 references + 3 scripts):

| Tree | Role |
|---|---|
| `.agents/skills/si-chip/` | **Source of truth** (canonical; `DESIGN.md` is internal-only and lives here only) |
| `.cursor/skills/si-chip/` | Cursor mirror (consumed by Cursor's local skill discovery) |
| `.claude/skills/si-chip/` | Claude Code mirror (consumed by Claude Code's local skill discovery) |
| `docs/skills/si-chip/` | Pages-served mirror (consumed by the `install.sh` one-line installer; URL: `https://yorha-agents.github.io/Si-Chip/skills/si-chip/`) |

Drift between any two trees on these 9 files is a CI failure. To verify locally:

```bash
for f in SKILL.md references/basic-ability-profile.md references/self-dogfood-protocol.md \
         references/metrics-r6-summary.md references/router-test-r8-summary.md \
         references/half-retirement-r9-summary.md scripts/profile_static.py \
         scripts/count_tokens.py scripts/aggregate_eval.py; do
  src=".agents/skills/si-chip/$f"
  for dst in ".cursor/skills/si-chip/$f" ".claude/skills/si-chip/$f" "docs/skills/si-chip/$f"; do
    diff -q "$src" "$dst" || echo "DRIFT: $src vs $dst"
  done
done
```

If you edit the canonical `.agents/skills/si-chip/...`, you MUST also update the three mirrors in the same commit (or in a follow-up commit before merge). The dogfood evidence file `.local/dogfood/<DATE>/round_<N>/raw/three_tree_drift_summary.json` (now four-tree) tracks this.

`DESIGN.md` is intentionally NOT included in the mirrors — it documents internal architecture, not user-facing Skill content.

The `install.sh` script at the repo root (and its identical copy at `docs/install.sh`) downloads from the `docs/skills/si-chip/` mirror via Pages. Local installs via `--source-url file://...` can point at any of the four trees.
