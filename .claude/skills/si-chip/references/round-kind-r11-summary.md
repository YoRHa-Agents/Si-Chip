# round_kind Enum — R11 Summary (Spec §15)

> Reader-friendly summary of §15 (v0.3.0-rc1, Normative). Sources:
> `.local/research/spec_v0.3.0-rc1.md` §15 and
> `.local/research/r11_core_goal_invariant.md` §4.

Every `next_action_plan.yaml` in v0.3.0+ MUST declare a root
`round_kind` from a 4-value enum. The kind decides how §4.1 row 10
(`iteration_delta any axis ≥ +0.05`) is interpreted and whether the
round counts toward §4.2 gate promotion. `C0 = 1.0` is UNIVERSAL
across all 4 kinds (§14.3.1, restated in §15.3).

## The 4 Values (§15.1 / §15.2 / §15.3 / §15.4 combined)

| round_kind | Definition | iteration_delta clause | C0 clause | Promotion counter |
|---|---|---|---|---|
| `code_change` | Modifies ability source files (≥1 file under `.agents/skills/<id>/` or the impl tree) | **strict** — ≥1 axis improvement at gate bucket (v1 ≥ +0.05 / v2 ≥ +0.10 / v3 ≥ +0.15) | `== 1.0` AND `>= prior` | YES |
| `measurement_only` | Adds metric coverage / eval cases / instrumentation, **no** source touch | **monotonicity_only** — no axis regression below v1_baseline; no improvement required | `== 1.0` AND `== prior` | YES |
| `ship_prep` | Release finalization — mirror sync `.cursor/skills/`/`.claude/skills/`, version bumps, tarball | **WAIVED** | `== 1.0` AND `== prior` | NO |
| `maintenance` | Post-ship review — 30/60/90d cadence (§6.4), model-upgrade re-verify, dependency-bump smoke | **WAIVED** | `== 1.0` | NO |

Historical anchors: `code_change` = Si-Chip R1-R3, chip-usage-helper
R1-R2; `measurement_only` = Si-Chip R4-R12 (measurement-fill era, now
correctly relabeled); `ship_prep` = Si-Chip R13, chip-usage-helper
R10; `maintenance` = not yet observed (chip-usage-helper
`next_review_at = round_10 + 30d` implies a future one).

## Decision Tree (§15.1.2)

Exactly one kind per round:

```
START
  │
  ├── (Q1) Does this round modify any file under
  │         .agents/skills/<id>/  OR  the ability's impl tree?
  │
  ├── YES ──→ (Q2) Also a release-finalization round
  │                 (mirror sync + version bump + tarball)?
  │           ├── YES ──→ ship_prep
  │           └── NO  ──→ code_change
  │
  └── NO ───→ (Q3) Post-ship periodic review (≥30d after last ship,
                   post-model-upgrade re-verify, or post-dependency
                   smoke)?
              ├── YES ──→ maintenance
              └── NO  ──→ measurement_only
```

Boundary rules:

- **Mixed `code_change` + `measurement_only` NOT ALLOWED** — splitting
  into two rounds is mandatory (R11 §1.2 Round 12 precedent:
  simultaneous source + measurement changes make regression
  attribution impossible).
- **`ship_prep` must not change ability behavior** — mirror sync
  modifies `.cursor/skills/` / `.claude/skills/`; source-of-truth
  changes only version bumps / docs. Ad-hoc fix? Relabel `code_change`
  and defer ship.
- **`maintenance` failure escalates** — C0 drop or v1_baseline gate
  fall during maintenance → immediately trigger §6 half-retire review
  / §6.4 reactivation; mark next round `code_change` for repair.

## Promotion-Counter Eligibility (§15.4)

v0.2.0 §4.2 requires "two consecutive rounds fully passing" to
promote v1 → v2 or v2 → v3. §15.4 clarifies which kinds count:
`code_change` and `measurement_only` (fresh observations under C0
discipline) YES; `ship_prep` and `maintenance` (carry-forward /
re-verify metrics) NO.

§14.3.2 strict no-regression **overrides** §15.4 eligibility: any C0
regression zeros the counter and locks all `verdict.pass` to `false`,
regardless of `round_kind`.

Why `measurement_only` counts: it still produces fresh observations
(new metric readings against current source). Incentivizing coverage
without distorting quality is the point of separating the labels.
Why `ship_prep` / `maintenance` don't: their metrics are reused —
letting them tick the counter lets teams climb gates via mirror-sync
work alone, defeating §4.2's intent.

## CLI

```bash
python tools/round_kind.py validate <kind>      # exit 0 iff valid
python tools/round_kind.py clause-for <kind>    # prints strict / monotonicity_only / waived
python tools/round_kind.py json                 # full enum + clauses + eligibility
```

## Why this matters (chip-usage-helper precedent)

13 Si-Chip rounds + 10 chip-usage-helper rounds = 23 observations.
R11 §1.1 concludes ~78% (18/23) were measurement-fill: rounds whose
iteration_delta was satisfied by adding coverage for a
previously-unmeasured sub-metric, not by a real ability improvement.
Pre-v0.3.0 §4.1 row 10 did not distinguish measurement-fill from
genuine code-change improvement, so teams drifted toward whichever
axis was cheapest. §15 fixes the incentive gradient:

- `code_change` keeps the strict ≥ +0.05 bar, rewarding real changes.
- `measurement_only` legitimizes coverage-only work without forcing
  fabricated axis improvements.
- `ship_prep` / `maintenance` are explicitly waived, keeping the
  iteration-delta signal clean.

## Cross-References

| §15 subsection | Spec section | R11 section |
|---|---|---|
| 15.1 4-value enum + decision tree | spec §15.1 | r11 §4.1 |
| 15.2 per-kind iteration_delta clause | spec §15.2 | r11 §4.2 |
| 15.3 per-kind C0 clause (universal) | spec §15.3 | r11 §4.1 C0 sub-bullet |
| 15.4 interaction with §4.2 promotion | spec §15.4 | r11 §4.3 + §10.3 |

Related templates: `round_kind` lives as a root field in
`templates/next_action_plan.template.yaml`
(`$schema_version: 0.2.0`) and is mirrored in the `core_goal_check`
block of `templates/iteration_delta_report.template.yaml`. See
`references/core-goal-invariant-r11-summary.md` for the C0 pair.

Source spec section: Si-Chip v0.3.0-rc1 §15 (Normative); distilled
from `.local/research/r11_core_goal_invariant.md` §4. This reference
is loaded on demand and is excluded from the §7.3 SKILL.md body
budget.
