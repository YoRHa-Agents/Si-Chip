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

The current frozen spec is `.local/research/spec_v0.4.0.md` (promoted from
`spec_v0.4.0-rc1.md` body byte-identical except metadata; v0.1.0 / v0.2.0 /
v0.3.0 retained as pinned historical snapshots). NORMATIVE sections are
§3, §4, §5, §6, §7, §8, §11, plus the v0.3.0 add-ons §14 (Core Goal
Invariant) + §15 (round_kind enum) + §17 (Hard Rules add-ons), and the
v0.4.0 add-ons §18 (Token-Tier Invariant) + §19 (Real-Data Verification) +
§20 (Stage Transitions & Promotion History) + §21 (Health Smoke Check) +
§22 (Eval-Pack Curation) + §23 (Method-Tagged Metrics). Any PR that
contradicts a Normative section is rejected.

Permanently out of scope (spec §11.1 — will be rejected without discussion;
re-affirmed verbatim in §14.6 + §18.7 + §19.6 + §20.6 + §21.6 + §22.7 +
§23.7 across the v0.3.0 + v0.4.0 add-on chapters):

- Skill / Plugin marketplaces and any distribution surface
- Router model training or online weight learning
- Markdown-to-CLI converters
- Generic IDE / agent-runtime compatibility layers

Deferred (spec §11.2 — open for re-evaluation once gate `v3_strict` has
been earned; v0.4.0 currently sits at `v2_tightened`):

- Codex native SKILL.md runtime
- Plugin distribution (commands / hooks / marketplace upgrade)
- Broader IDE coverage (OpenCode, Copilot CLI, Gemini CLI, ...)
- Multi-tenant hosted API surface

## 3. Branching & PR Workflow

- `main` is protected; never push directly. Create a feature branch and open a PR.
- Branch naming: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`, `docs/<topic>`.
- One logical change per PR. Use `git commit --amend` only on commits that have
  not been pushed.
- Every PR must reference (a) the spec section it touches and (b) the dogfood
  round number that produced or validated the change.

## 4. Required Local Checks Before Pushing

```bash
# Packaging gate (v2_tightened: metadata <= 100, body <= 5000)
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .agents/skills/si-chip/SKILL.md --both \
  --budget-meta 100 --budget-body 5000 --json
# Expected at v0.4.0: metadata_tokens=94, body_tokens=4646, pass=true

# 14 BLOCKER spec invariants (9 historical + 2 v0.3.0 + 3 v0.4.0)
python tools/spec_validator.py --json

# Cross-tree drift (after any SKILL.md / references / scripts sync)
diff -r .agents/skills/si-chip .cursor/skills/si-chip | grep -v DESIGN.md
diff -r .agents/skills/si-chip .claude/skills/si-chip | grep -v DESIGN.md
```

All three MUST pass.

Optional but recommended whenever you touch a `metrics_report.yaml` or a
`basic_ability_profile.yaml` under `.local/dogfood/`:

```bash
# §23 method-tag companion validator (token / quality / G1 method enums)
python tools/method_tag_validator.py --json

# §21 health-smoke 4-axis probe runner (REQUIRED when live_backend: true)
python tools/health_smoke.py --profile <profile.yaml> --json
```

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

1. A NEW spec file under `.local/research/spec_v<X.Y.Z>.md` (DO NOT edit
   any frozen historical spec — `spec_v0.1.0.md` / `spec_v0.2.0.md` /
   `spec_v0.3.0.md` / `spec_v0.4.0.md` are pinned snapshots).
2. Updated `effective_date` and `supersedes` frontmatter.
3. Refreshed `.rules/si-chip-spec.mdc` and re-compiled `AGENTS.md`
   (the Hard Rules block in §13 must mirror the Normative add-ons).
4. Refreshed `.rules/.compile-hashes.json` so drift detection passes
   (`devolaflow.local.drift` SHA-256).
5. A passing run of `python tools/spec_validator.py --spec <new_path> --json`
   under both default and `--strict-prose-count` mode (the latter enforces
   §13.4 prose counts; v0.2.0+ specs reconciled to 37 sub-metrics + 30
   threshold cells).
6. If the spec change breaks byte-identicality of any prior Normative
   section (e.g. v0.4.0 adding the 8th `value_vector` axis
   `eager_token_delta`), update the validator's
   `EXPECTED_VALUE_VECTOR_AXES_BY_SPEC` mapping to keep older rounds
   passing under their own spec version.
7. Bump the `SUPPORTED_SPEC_VERSIONS` set in
   `tools/spec_validator.py` and add the new spec to its accepted-spec
   help text.

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
| `.agents/skills/si-chip/` | **Source of truth** (canonical; carries the internal-only `DESIGN.md` plus the full 20-file public payload) |
| `.cursor/skills/si-chip/` | Cursor mirror (consumed by Cursor's local skill discovery; 20 files = 1 SKILL.md + 14 references + 5 scripts; no `DESIGN.md`) |
| `.claude/skills/si-chip/` | Claude Code mirror (consumed by Claude Code's local skill discovery; same 20-file payload as the Cursor mirror) |
| `docs/skills/si-chip-<version>.tar.gz` | Pages-served release tarball (consumed by `install.sh`; URL: `https://yorha-agents.github.io/Si-Chip/skills/si-chip-<version>.tar.gz`) |

At v0.4.0 the **20-file public payload** (1 SKILL.md + 14 references + 5
scripts) MUST be byte-identical across the three platform trees. The
tarball additionally carries `DESIGN.md` (21 files total in the tarball);
when extracted, the 20-file public subset MUST be byte-identical to the
source-of-truth. The `.cursor/` and `.claude/` mirrors deliberately omit
`DESIGN.md` because it is an internal architecture note and is not
needed at runtime.

To verify locally (post-v0.4.0 file list — all 14 references + 5 scripts):

```bash
# Three-tree drift check
for f in SKILL.md \
         references/basic-ability-profile.md \
         references/self-dogfood-protocol.md \
         references/metrics-r6-summary.md \
         references/router-test-r8-summary.md \
         references/half-retirement-r9-summary.md \
         references/core-goal-invariant-r11-summary.md \
         references/round-kind-r11-summary.md \
         references/multi-ability-layout-r11-summary.md \
         references/token-tier-invariant-r12-summary.md \
         references/real-data-verification-r12-summary.md \
         references/lifecycle-state-machine-r12-summary.md \
         references/health-smoke-check-r12-summary.md \
         references/eval-pack-curation-r12-summary.md \
         references/method-tagged-metrics-r12-summary.md \
         scripts/profile_static.py \
         scripts/count_tokens.py \
         scripts/aggregate_eval.py \
         scripts/eval_skill_quickstart.md \
         scripts/real_llm_runner_quickstart.md; do
  src=".agents/skills/si-chip/$f"
  for dst in ".cursor/skills/si-chip/$f" ".claude/skills/si-chip/$f"; do
    diff -q "$src" "$dst" || echo "DRIFT: $src vs $dst"
  done
done

# Tarball-vs-source check (v0.4.0 tarball INCLUDES DESIGN.md)
TMP=$(mktemp -d)
tar -xzf docs/skills/si-chip-0.4.0.tar.gz -C "$TMP"
diff -r .agents/skills/si-chip "$TMP/si-chip"
# Expect: no output (full 21-file byte-identical match)
rm -rf "$TMP"
```

Re-build the tarball whenever the source-of-truth changes (v0.4.0 mtime
baked into the SHA-256 `2cfcce00...be21ab` reproducibility contract):

```bash
tar --owner=0 --group=0 --numeric-owner --sort=name \
    --mtime='2026-04-30 00:00:00 UTC' --format=ustar \
    -C .agents/skills -cf - si-chip \
  | gzip -n -9 > docs/skills/si-chip-0.4.0.tar.gz
```

The deterministic options (`--owner=0 --group=0 --numeric-owner --sort=name`,
fixed `--mtime`, `--format=ustar`, `gzip -n`) make the tarball reproducible:
the same source produces the same SHA-256. After rebuilding, refresh the
sidecar:

```bash
sha256sum docs/skills/si-chip-0.4.0.tar.gz \
  | awk '{print $1}' > docs/skills/si-chip-0.4.0.tar.gz.sha256
```

### Why the tarball
The `docs/skills/si-chip/` per-file mirror was tried in PR #5 but Jekyll
treats `SKILL.md` (which has YAML front-matter) as a renderable page and
serves it at `/skills/si-chip/SKILL/` (HTML-rendered, body-only) instead
of the raw `.md` URL the installer expects. The tarball sidesteps this
because Jekyll passes `.tar.gz` files through unmodified.

## 10. Pages bilingualization (en/zh) and dark mode

The GitHub Pages site at `https://yorha-agents.github.io/Si-Chip/` ships with three independent UX state machines:

| State | Storage key | Default | Toggle UI |
|---|---|---|---|
| Language | `localStorage["si-chip-lang"]` ∈ {`en`, `zh`} | `navigator.language` (`zh*` → `zh`, else `en`) | Hero top-right `[ LANG / EN ]` button |
| Theme | `localStorage["si-chip-theme"]` ∈ {`day`, `night`} | `prefers-color-scheme` (`dark` → `night`, else `day`) | Hero top-right `[ THEME / DAY ]` button |

Both are applied by `docs/assets/js/nier.js` on `DOMContentLoaded` and persisted to `localStorage` on each toggle. The body's `data-lang` and `data-theme` attributes drive the CSS in `docs/assets/css/nier.css`:

- `body[data-theme="night"]` overrides the `:root` palette tokens (`--bg`, `--fg`, `--accent`, etc.).
- `body[data-lang="en"] [lang="zh"]:not(html):not([data-i18n]) { display: none; }` (and the inverse for zh) hides the inactive language block.

### Bilingual content convention

Each Pages markdown body contains two top-level kramdown blocks:

```markdown
<div lang="en" markdown="1">

English content...

</div>

<div lang="zh" markdown="1">

中文内容……

</div>
```

Mermaid diagrams, code blocks, file paths, URLs, numeric data, and enum strings (`keep`, `relaxed`, `composer_2/default`, etc.) are kept VERBATIM and shared (placed OUTSIDE the lang blocks when feasible) — only descriptive prose, headings, and bullet labels are translated.

### Sync contracts (revised by this change)

| Source | Mirror | Old contract | New contract |
|---|---|---|---|
| `INSTALL.md` (root, English git README) | `docs/_install_body.md` (Pages, bilingual) | `tail -n +2 INSTALL.md == docs/_install_body.md` (byte-identical) | The English `<div lang="en">` block of `docs/_install_body.md` matches `tail -n +2 INSTALL.md` body content (semantic equivalent; structural diff allowed for the wrapping `<div>` tags) |
| `USERGUIDE.md` (root, English) | `docs/_userguide_body.md` (Pages, bilingual) | `tail -n +2 USERGUIDE.md == docs/_userguide_body.md` | Same: en block of partial matches root tail (semantic equivalent) |

### Adding a new translation key

Hero/footer chrome translations live in the JSON island inside `docs/_layouts/default.html` under `<script type="application/json" id="si-chip-i18n">`. Both `en` and `zh` buckets MUST be symmetric (same key set). To add a key: edit the JSON island, then mark the relevant DOM element with `data-i18n="<key>"`.

### Dark mode token overrides

If you introduce a new color token in `docs/assets/css/nier.css`:
1. Define the day-mode value in `:root`.
2. Add the night-mode override under `body[data-theme="night"]`.
3. If the new color is referenced by a hover state or animation, verify both modes in the browser (the toggle button at the hero top-right flips them live).

### Out-of-scope reminders (carry over from §9)

The bilingualization and theme toggles do NOT relax any spec §11.1 forever-out items. PRs introducing a marketplace, router-model training, MD-to-CLI converter, or generic IDE compat layer remain out of scope regardless of which language they are described in.
