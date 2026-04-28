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

Si-Chip ships the Skill payload in **three platform trees** (each consumed
by a specific local skill discovery system) plus **one derived release
tarball** (consumed by the `install.sh` one-line installer):

| Tree | Role |
|---|---|
| `.agents/skills/si-chip/` | **Source of truth** (canonical; `DESIGN.md` is internal-only and lives here only) |
| `.cursor/skills/si-chip/` | Cursor mirror (consumed by Cursor's local skill discovery) |
| `.claude/skills/si-chip/` | Claude Code mirror (consumed by Claude Code's local skill discovery) |
| `docs/skills/si-chip-<version>.tar.gz` | Pages-served release tarball (consumed by `install.sh`; URL: `https://yorha-agents.github.io/Si-Chip/skills/si-chip-<version>.tar.gz`) |

The 9-file payload (SKILL.md + 5 references + 3 scripts) MUST be byte-
identical across the three platform trees. The tarball, when extracted,
MUST yield the same 9 files byte-identical to the source-of-truth.
`DESIGN.md` is intentionally NOT in any mirror or in the tarball.

To verify locally:

```bash
# Three-tree drift check
for f in SKILL.md references/basic-ability-profile.md references/self-dogfood-protocol.md \
         references/metrics-r6-summary.md references/router-test-r8-summary.md \
         references/half-retirement-r9-summary.md scripts/profile_static.py \
         scripts/count_tokens.py scripts/aggregate_eval.py; do
  src=".agents/skills/si-chip/$f"
  for dst in ".cursor/skills/si-chip/$f" ".claude/skills/si-chip/$f"; do
    diff -q "$src" "$dst" || echo "DRIFT: $src vs $dst"
  done
done

# Tarball-vs-source check
TMP=$(mktemp -d)
tar -xzf docs/skills/si-chip-0.1.0.tar.gz -C "$TMP"
diff -r .agents/skills/si-chip "$TMP" | grep -v DESIGN.md
# Expect ONLY: "Only in .agents/skills/si-chip: DESIGN.md"
rm -rf "$TMP"
```

Re-build the tarball whenever the source-of-truth changes:

```bash
tar --owner=0 --group=0 --numeric-owner --sort=name \
    --mtime='2026-04-28 00:00:00 UTC' --format=ustar \
    -C .agents/skills/si-chip -cf - SKILL.md references scripts \
  | gzip -n -9 > docs/skills/si-chip-0.1.0.tar.gz
```

The deterministic options (`--owner=0 --group=0 --numeric-owner --sort=name`,
fixed `--mtime`, `--format=ustar`, `gzip -n`) make the tarball reproducible:
the same source produces the same SHA256.

### Why the tarball
The `docs/skills/si-chip/` per-file mirror was tried in PR #5 but Jekyll
treats `SKILL.md` (which has YAML front-matter) as a renderable page and
serves it at `/skills/si-chip/SKILL/` (HTML-rendered, body-only) instead
of the raw `.md` URL the installer expects. The tarball sidesteps this
because Jekyll passes `.tar.gz` files through unmodified.
