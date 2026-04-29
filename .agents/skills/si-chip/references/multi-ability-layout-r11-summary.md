# Multi-Ability Dogfood Layout — R11 Summary (Spec §16, Informative @ v0.3.0)

> Reader-friendly summary of §16 (v0.3.0-rc1, **Informative**; target
> Normative at v0.3.x). Sources:
> `.local/research/spec_v0.3.0-rc1.md` §16 and
> `.local/research/r11_core_goal_invariant.md` §5.

§16 generalizes the v0.2.0 per-round evidence tree so multiple
abilities can dogfood in parallel without colliding at
`.local/dogfood/<DATE>/round_<N>/`. **Informative** at v0.3.0:
`spec_validator` may emit WARNINGs but not BLOCKERs for legacy-layout
new abilities until §16.3 promotion triggers fire.

## Layout (§16.1)

New (multi-ability):

```
.local/dogfood/<YYYY-MM-DD>/abilities/<ability-id>/
    eval_pack.yaml                       # trigger eval pack (R3_trigger_F1)
    core_goal_test_pack.yaml             # NEW v0.3.0 §14.2 pack (or path-ref)
    vocabulary.yaml                      # for tools/cjk_trigger_eval.py
    tools/
        <ability-id>_specific.py         # OPTIONAL adapter (non-generic steps)
    round_<N>/
        basic_ability_profile.yaml
        metrics_report.yaml
        router_floor_report.yaml
        half_retire_decision.yaml
        next_action_plan.yaml            # MUST contain round_kind ∈ §15.1
        iteration_delta_report.yaml      # MUST contain core_goal_check per §14.3
        raw/                             # OTel traces, NineS reports, drift checks
```

Legacy (single-ability, retained for Si-Chip self):

```
.local/dogfood/<YYYY-MM-DD>/round_<N>/
    basic_ability_profile.yaml
    ...                                  # same 6 evidence files
    raw/
```

Path-style rules (§16.1.1):

- Ability id must NOT contain `/` — use kebab-case
  (`lark-cli-im`, not `lark-cli/im`).
- `tools/<ability-id>_specific.py` is OPTIONAL; when present it plugs
  into `tools/eval_skill.py` as an adapter, never forks the harness.
- `core_goal_test_pack.yaml` may be standalone or a path-ref to the
  source-of-truth pack (recommended:
  `.agents/skills/<id>/core_goal_test_pack.yaml` canonical; dogfood
  subtree carries a path-ref to avoid duplication).

## Migration Path (§16.2)

| Ability | Layout @ v0.3.0 | Status | Action |
|---|---|---|---|
| Si-Chip itself | Legacy `.local/dogfood/<DATE>/round_<N>/` | Round 1-13 canonical | KEEP. Round 14+ MAY opt in; validator accepts both. |
| chip-usage-helper | New `.local/dogfood/<DATE>/abilities/chip-usage-helper/round_<N>/` | Round 1-10 migrated | No action. |
| Any NEW ability post-v0.3.0 | New layout | REQUIRED | BLOCKER if a non-Si-Chip ability writes to legacy path. |

Backward-compat contract (§16.2.1):

- `tools/spec_validator.py` MUST accept both layouts; path-shape
  BLOCKERs must distinguish "legacy is OK for Si-Chip self" from
  "legacy is FAIL for a second-or-later ability".
- Round 1-13 Si-Chip + Round 1-10 chip-usage-helper evidence PASS
  under v0.3.0-rc1 without retrofit.
- If Si-Chip self ever migrates: mass-rename via
  `mv .local/dogfood/<DATE>/round_<N>/ .local/dogfood/<DATE>/abilities/si-chip/round_<N>/`
  in a single `round_kind: ship_prep` round (§15.4: does not count
  toward promotion counter).

## Promotion to Normative (§16.3)

§16 promotes from Informative to Normative when ALL hold:

1. **≥2 abilities** shipped under new layout (chip-usage-helper = 1;
   need either a 3rd ability or Si-Chip self migration).
2. **2 consecutive ship cycles** complete without layout regression.
3. **Migration script** in `tools/` for legacy → new (single command).
4. **`spec_validator` layout BLOCKER** clean on both abilities for
   2 consecutive rounds before §16 itself is promoted.

### Why Informative @ v0.3.0 (§16.3.1)

Currently only one second-ability witness exists (chip-usage-helper,
10 rounds). Forcing Si-Chip self to migrate now without two
independent witnesses would break the additivity discipline.
Informative at v0.3.0 = one grace window (a 3rd ability or Si-Chip
self migration) before full Normative — the same staged pattern
used for v0.1.0 → v0.2.0 reconciliation.

### Soft-Normative at v0.3.0 (§16.3.2)

`spec_validator` MAY emit **WARNING** (not BLOCKER) when a NEW
ability lands in legacy layout at v0.3.0. Authors see the warning
and tend toward the new layout; legacy + Si-Chip self stay untouched.

## Why this matters

Spec §10 default layout implicitly assumed a single ability. When
chip-usage-helper (the first second ability) came online ahead of
v0.3.0 spec, its evidence naturally landed under `abilities/<id>/`
to avoid colliding with Si-Chip's round numbering. §16 additively
generalizes this pattern: no breaking change for Si-Chip self, an
explicit rule for the 3rd+ ability, and deferred Normative promotion
that keeps §10 main text byte-identical to v0.2.0.

## Cross-References

| §16 subsection | Spec section | R11 section |
|---|---|---|
| 16.1 layout + path-style | spec §16.1 | r11 §5.1 / §5.2 / §5.5 |
| 16.2 migration + backward compat | spec §16.2 | r11 §5.3 |
| 16.3 promotion-to-Normative trigger | spec §16.3 | r11 §5.4 |

§16 is the multi-ability companion to
`references/self-dogfood-protocol.md`; the 8-step protocol and 6
evidence files are the same under both layouts.

Source spec section: Si-Chip v0.3.0-rc1 §16 (Informative;
Normative-target at v0.3.x); distilled from
`.local/research/r11_core_goal_invariant.md` §5. This reference is
loaded on demand and is excluded from the §7.3 SKILL.md body budget.
