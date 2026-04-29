# Si-Chip — `abilities/si-chip/` tree (v0.3.0-rc1 §16 multi-ability layout)

This directory is the **abilities-tree** entry for Si-Chip itself under the
v0.3.0-rc1 §16.1 multi-ability layout. It carries the per-ability
**static** artifacts (`core_goal_test_pack.yaml`, `eval_pack.yaml`,
`vocabulary.yaml`) that any round can pick up. The **per-round** evidence
(the 6 §8.2 files) lives in the legacy single-ability path
`.local/dogfood/<DATE>/round_<N>/` per spec §16.2 (Si-Chip self-dogfood
retains the legacy layout; new abilities MUST use the new layout).

## Layout

```
.local/dogfood/2026-04-29/
├── abilities/
│   └── si-chip/                                    <--- THIS DIRECTORY
│       ├── README.md                               (this file)
│       ├── core_goal_test_pack.yaml                 §14.2 — 5 cases; v1.0.0
│       ├── eval_pack.yaml                           §5.3 — 20 + 20 prompts
│       └── vocabulary.yaml                          §5.1 — CJK trigger vocab
└── round_14/                                       <--- 6 EVIDENCE FILES
    ├── basic_ability_profile.yaml                   §8.2 #1; spec_version v0.3.0-rc1
    ├── metrics_report.yaml                          §8.2 #2; round_kind code_change
    ├── router_floor_report.yaml                     §8.2 #3; carry-forward composer_2/default
    ├── half_retire_decision.yaml                    §8.2 #4; action keep
    ├── next_action_plan.yaml                        §8.2 #5; targets round_15 measurement_only
    ├── iteration_delta_report.yaml                  §8.2 #6; pass_v1_baseline true
    └── raw/                                         OTel / spec_validator / pytest / etc.
```

## Why both paths

Per spec §16.2 migration table:

| Surface | v0.3.0 status | Why |
|---|---|---|
| Si-Chip self-dogfood (Round 1-13 history) | **legacy layout retained** | Round 1-13 evidence is canonical; spec_validator accepts both layouts |
| **Si-Chip Round 14+** | **legacy layout retained** | Round 14 stays legacy to avoid bulk migration in the same round that introduces the new layout (mixed-kind prohibition per §15.1) |
| chip-usage-helper (Round 1-14+) | **new layout adopted** | already at `.local/dogfood/2026-04-29/abilities/chip-usage-helper/round_<N>/` |
| Any **new** ability introduced in v0.3.x | **MUST use new layout** | spec_validator BLOCKER if a new ability writes to legacy (would collide with Si-Chip self) |

So Si-Chip Round 14 lives in **both** trees:
- **Authoritative copy**: the 6 evidence files at `.local/dogfood/2026-04-29/round_14/` (legacy single-ability path).
- **Static cross-reference**: this `abilities/si-chip/` tree carries the
  per-ability static artifacts that any round picks up. **No byte-duplicate**
  of the 6 evidence files lives here per §16.2 — only the static pack /
  eval / vocab files.

## How to re-run Round 14 evidence regeneration

```bash
# 1. Run the core_goal_test_pack (5 cases; expected C0 = 1.0):
python .local/dogfood/2026-04-29/round_14/raw/run_core_goal_cases.py

# 2. Run the generic eval harness (writes raw/eval_skill_output.yaml):
python tools/eval_skill.py \
  --ability si-chip \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --vocabulary .local/dogfood/2026-04-29/abilities/si-chip/vocabulary.yaml \
  --eval-pack .local/dogfood/2026-04-29/abilities/si-chip/eval_pack.yaml \
  --core-goal-test-pack .local/dogfood/2026-04-29/abilities/si-chip/core_goal_test_pack.yaml \
  --test-runner-cmd "python -m pytest tools/ --tb=no -q" \
  --test-runner-cwd . \
  --runs 1 \
  --round-kind code_change \
  --prior-c0-pass-rate 1.0 \
  --out .local/dogfood/2026-04-29/round_14/raw/eval_skill_output.yaml

# 3. Cross-check: spec_validator dual-spec (both must exit 0 with 11/11 BLOCKERs):
python tools/spec_validator.py --json
python tools/spec_validator.py --spec .local/research/spec_v0.3.0-rc1.md --json

# 4. Cross-check: full pytest (target 395+ pass, 1 skipped):
python -m pytest tools/ .agents/skills/si-chip/scripts/ -v
```

## Round 14 acceptance summary

- 6 evidence files in `.local/dogfood/2026-04-29/round_14/` — all `yaml.safe_load` clean
- 4 abilities-tree files in `.local/dogfood/2026-04-29/abilities/si-chip/` — this README + pack + eval_pack + vocabulary
- C0_core_goal_pass_rate = 1.0 (5/5 cases pass)
- spec_validator dual-spec PASS = 11/11 BLOCKERs (v0.2.0) and 11/11 BLOCKERs (v0.3.0-rc1)
- pytest 395 passed / 1 skipped
- iteration_delta: 2 efficiency axes at v1 bucket (governance_risk +0.05; generalizability +0.05)
- v1_baseline 9-row check: ALL PASS (14th consecutive v1 pass)

## Pointers

- Spec: `.local/research/spec_v0.3.0-rc1.md` (especially §14 core_goal, §15 round_kind, §16 multi-ability layout)
- Skill source-of-truth: `.agents/skills/si-chip/SKILL.md` (v0.3.0-rc1; metadata 97 / body 3022 tokens)
- chip-usage-helper sibling: `.local/dogfood/2026-04-29/abilities/chip-usage-helper/` (Rounds 1-14 in new layout)
- Round 13 (v0.2.0 ship): `.local/dogfood/2026-04-28/round_13/` (predecessor; predecessor of Round 14's monotonicity check)
- Round 15 (next, measurement_only): blueprint in `.local/dogfood/2026-04-29/round_14/next_action_plan.yaml`

## Provenance

- Authored: 2026-04-29 by Round 14 dogfood L3 Task Agent
- Spec version: v0.3.0-rc1
- Branch: feat/v0.3.0-core-goal-invariant
- Target commit base: 6dc04e3e344486cc3b621af5f3a5258b9e744588
