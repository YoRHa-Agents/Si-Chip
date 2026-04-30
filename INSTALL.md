# Installing Si-Chip

## Quick Install (one-line)

The fastest path. Picks Cursor or Claude Code (or both) and installs to a global location (`~/.cursor/skills/si-chip/` and/or `~/.claude/skills/si-chip/`) or to a single repo (`<repo>/.cursor/skills/si-chip/` etc.).

```bash
# Interactive (TTY): prompts for target and scope
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash

# Non-interactive: install Cursor globally
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- \
  --target cursor --scope global --yes

# Non-interactive: install Claude Code into a specific repo
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- \
  --target claude --scope repo --repo-root ~/code/myrepo --yes

# Install for both Cursor and Claude Code, globally
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- \
  --target both --scope global --yes
```

### Installer flags

| Flag | Values | Default | Required |
|---|---|---|---|
| `--target` | `cursor` / `claude` / `both` | (interactive prompt) | when `--yes` |
| `--scope` | `global` / `repo` | (interactive prompt) | when `--yes` |
| `--repo-root` | path | `$PWD` | when `--scope repo --yes` |
| `--version` | tag | `v0.4.0` | no |
| `--source-url` | URL | `https://yorha-agents.github.io/Si-Chip` | no (mostly for testing) |
| `--yes` / `-y` | flag | `false` | no |
| `--dry-run` | flag | `false` | no |
| `--force` | flag | `false` | no |
| `--uninstall` | flag | `false` | no |
| `--help` | flag | `false` | no |

### What gets installed (21 files via tarball, ~115 KB)

The HTTPS installer downloads `docs/skills/si-chip-0.4.0.tar.gz` (SHA-256 `2cfcce00f989faf2467014e638b0ea1fa67870b5a1ee6b0531942be5a4be21ab`; 83060 bytes; deterministic and reproducible — `--mtime '2026-04-30 00:00:00 UTC'`) and extracts 21 files (1 SKILL.md + 1 DESIGN.md + 14 references + 5 scripts):

```
<install-dir>/
  SKILL.md                                              (metadata 94 / body 4646 tokens)
  DESIGN.md                                             (internal architecture notes)
  references/basic-ability-profile.md                   (§2)
  references/self-dogfood-protocol.md                   (§8)
  references/metrics-r6-summary.md                      (§3 — 7 dim / 37 sub-metrics)
  references/router-test-r8-summary.md                  (§5 — 8-cell MVP / 96-cell Full)
  references/half-retirement-r9-summary.md              (§6 — 8-axis value vector)
  references/core-goal-invariant-r11-summary.md         (§14 — C0 invariant; v0.3.0)
  references/round-kind-r11-summary.md                  (§15 — round_kind enum; v0.3.0)
  references/multi-ability-layout-r11-summary.md        (§16 — Informative; v0.3.0)
  references/token-tier-invariant-r12-summary.md        (§18 — C7/C8/C9; v0.4.0)
  references/real-data-verification-r12-summary.md      (§19 — fixture provenance; v0.4.0)
  references/lifecycle-state-machine-r12-summary.md     (§20 — promotion history; v0.4.0)
  references/health-smoke-check-r12-summary.md          (§21 — 4-axis probes; v0.4.0)
  references/eval-pack-curation-r12-summary.md          (§22 — 40-prompt v2 minimum; v0.4.0)
  references/method-tagged-metrics-r12-summary.md       (§23 — _method companions; v0.4.0)
  scripts/profile_static.py                             (§8 step 1)
  scripts/count_tokens.py                               (packaging gate)
  scripts/aggregate_eval.py                             (§8 step 2)
  scripts/eval_skill_quickstart.md                      (CLI cheat-sheet; v0.3.0)
  scripts/real_llm_runner_quickstart.md                 (CLI cheat-sheet; v0.4.0)
```

`DESIGN.md` carries internal architecture notes and is included in the tarball / file:// install but is not mirrored into `.cursor/skills/si-chip/` or `.claude/skills/si-chip/` (those mirror the 20-file `SKILL.md + references + scripts` set per the cross-tree drift contract — see `CONTRIBUTING.md` §9).

Where `<install-dir>` is one of:

| target  | scope  | install dir                              |
|---|---|---|
| cursor  | global | `~/.cursor/skills/si-chip/`              |
| cursor  | repo   | `<repo-root>/.cursor/skills/si-chip/`    |
| claude  | global | `~/.claude/skills/si-chip/`              |
| claude  | repo   | `<repo-root>/.claude/skills/si-chip/`    |

### Verify the install

```bash
# Replace <install-dir> with the path the installer printed.
python3 <install-dir>/scripts/count_tokens.py --file <install-dir>/SKILL.md --both
# Expected: metadata_tokens=94, body_tokens=4646, pass=true
#           (against the v0.4.0 v2_tightened budget: meta <= 100, body <= 5000)
```

### Uninstall

```bash
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- \
  --target cursor --scope global --uninstall --yes
```

---

## Manual install (clone the repo)

If you prefer to inspect everything first, or if you want the full source tree (templates, evals, dogfood evidence, spec, ...), clone the repo. This path covers Cursor and Claude Code (the two priorities per spec §7.2), the Codex bridge (still bridge-only at v0.4.0 per spec §11.2), developer setup, and smoke tests.

## Prerequisites

- Python >= 3.10
- git
- Optional: `tiktoken` (for accurate token counting; otherwise
  `count_tokens.py` falls back to a deterministic whitespace splitter and
  reports `backend=fallback`).
- Optional: `devolaflow` (R7 §1 upstream — `pip install
  git+https://github.com/YoRHa-Agents/DevolaFlow.git`).
- Optional: `nines` CLI (legacy live-LLM runner; the included
  `evals/si-chip/runners/real_llm_runner.py` is the v0.4.0 production
  runner and does NOT depend on `nines`).
- Optional: `requests` (only required if you actually call
  `evals/si-chip/runners/real_llm_runner.py` against a live Anthropic
  Messages endpoint; cache-replay mode does not need it).

## 1. Clone the Repository

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
```

## 2. Cursor Install (priority 1)

The Skill is mirrored at `.cursor/skills/si-chip/`. Cursor auto-discovers it
on workspace open. The optional bridge rule
`.cursor/rules/si-chip-bridge.mdc` is included and points back at
`.cursor/skills/si-chip/SKILL.md` plus `AGENTS.md` (which is itself compiled
from `.rules/si-chip-spec.mdc`; AGENTS.md §13 carries 13 hard rules at v0.4.0).

Reload Cursor; the Skill should appear under the project's local skills.

Verify:

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .cursor/skills/si-chip/SKILL.md --both
```

Expect `metadata_tokens=94`, `body_tokens=4646`, `pass=true` (matches the
spec §7.3 v2_tightened packaging gate; identical to the canonical mirror per
the cross-tree drift contract — see `CONTRIBUTING.md` §9).

## 3. Claude Code Install (priority 2)

The Skill is mirrored at `.claude/skills/si-chip/`. Claude Code
auto-discovers it on session start.

Verify:

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .claude/skills/si-chip/SKILL.md --both
```

Same gate numbers as the Cursor mirror (drift = 0).

## 4. Developer Setup

```bash
pip install pyyaml                                              # required for scripts
pip install tiktoken                                            # optional; matches CI
pip install requests                                            # optional; only for live real_llm_runner runs
pip install git+https://github.com/YoRHa-Agents/DevolaFlow.git  # optional
```

`pyyaml` is the only hard dependency for the bundled scripts. `tiktoken`
matches CI's token counting backend; `devolaflow` is required only when you
want to drive Si-Chip through the upstream `template_engine` /
`memory_router` paths (spec §5.1, §9). `requests` is only needed for live
Anthropic Messages calls from `evals/si-chip/runners/real_llm_runner.py`;
the `--seal-cache` / cache-replay flow does not require it.

## 5. Smoke Tests

```bash
# 14 BLOCKER spec invariants — verdict PASS
python tools/spec_validator.py --json

# Generate self-profile
python .agents/skills/si-chip/scripts/profile_static.py \
  --ability si-chip --out /tmp/profile.yaml

# Deterministic seeded baseline runners (no LLM cost)
python evals/si-chip/runners/no_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/no_ability/ --seed 42

python evals/si-chip/runners/with_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/with_ability/ --seed 42

# Aggregate to MVP-8 + 29 explicit-null R6 keys
python .agents/skills/si-chip/scripts/aggregate_eval.py \
  --runs-dir /tmp/with_ability --baseline-dir /tmp/no_ability \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --templates-dir templates --out /tmp/metrics_report.yaml
```

Expected: `spec_validator` exits 0 with `verdict: PASS` (14/14 BLOCKER
invariants — the original 9 + `REACTIVATION_DETECTOR_EXISTS` + 2 v0.3.0
additive invariants `CORE_GOAL_FIELD_PRESENT` + `ROUND_KIND_TEMPLATE_VALID`
+ 3 v0.4.0 additive invariants `TOKEN_TIER_DECLARED_WHEN_REPORTED` +
`REAL_DATA_FIXTURE_PROVENANCE` + `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`);
`profile_static` emits a `BasicAbilityProfile` YAML against the §2.1 schema
(`$schema_version: 0.3.0`); the two runners populate per-case `result.json`
files; `aggregate_eval` produces a `metrics_report.yaml` with the MVP-8
keys filled and the remaining 29 keys explicitly `null` (matches
[`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md)).

### Optional — real-LLM runner cache replay (v0.4.0)

The Round 18 / Round 19 cache lives at `.local/dogfood/2026-04-30/round_18/raw/real_llm_runner_cache/` (640 entries). To replay it without paying for live calls:

```bash
python evals/si-chip/runners/real_llm_runner.py --help
# See .agents/skills/si-chip/scripts/real_llm_runner_quickstart.md for the
# full Round 18 / Round 19 invocation; cache replay is $0 and ~20 ms.
```

## 6. Troubleshooting

- `count_tokens.py` reports `backend=fallback`: install `tiktoken` for
  parity with CI; the fallback uses a deterministic whitespace splitter and
  may report different token counts.
- `aggregate_eval.py` warns about a schema cross-check: expected. The
  templates are JSON-Schema-shaped (`properties.basic_ability.properties.metrics.properties`),
  not a direct `basic_ability.metrics` map. MVP-8 keys are still validated
  independently. The smoke report documents this as a non-blocking warning.
- `spec_validator.py --strict-prose-count` exits 1 against `spec_v0.1.0.md`
  but PASS against v0.2.0+: expected. The legacy v0.1.0 prose contained
  "28 sub-metrics" / "21 threshold cells" while §3.1 / §4.1 TABLE counts
  were 37 / 30. v0.2.0+ §13.4 prose was reconciled to 37 / 30 and the
  validator now passes strict mode against any v0.2.0 / v0.3.0 / v0.4.0
  spec; the v0.1.0 mode is preserved for historical regression.
- The packaging gate fails with `metadata_tokens=94 > 80`: expected. v0.4.0
  ships at `v2_tightened` (`meta <= 100`); `v3_strict` (`meta <= 80`) is
  deferred to v0.4.x. See README "Headline Numbers" and the v0.4.0 ship
  report under `.local/dogfood/2026-04-30/v0.4.0_ship_report.md`.

## 7. Uninstall

- Cursor: delete `.cursor/skills/si-chip/` and reload the workspace.
- Claude Code: delete `.claude/skills/si-chip/` and restart the session.
- Repo: `rm -rf Si-Chip/`.

---

## Codex (bridge-only at v0.4.0)

Si-Chip ships [`AGENTS.md`](./AGENTS.md), which is compiled from
`.rules/si-chip-spec.mdc`. Codex reads `AGENTS.md`, so the Normative spec
content (§3 / §4 / §5 / §6 / §7 / §8 / §11 / §14 / §15 / §17 / §18 / §19 /
§20 / §21 / §22 / §23 plus the 13 hard rules in §13) is in front of Codex
on every session.

Native `.codex/profiles/si-chip.md` plus
`.codex/instructions/si-chip-bridge.md` remain deferred per spec §11.2
("Codex native SKILL.md runtime support; v0.x is bridge-only"). This is
re-affirmed in spec §14.6 + §18.7 + §19.6 + §20.6 + §21.6 + §22.7 + §23.7
across the v0.3.0 + v0.4.0 add-on chapters; native Codex SKILL.md runtime
will be re-evaluated in a future spec bump once `v3_strict` is earned.
