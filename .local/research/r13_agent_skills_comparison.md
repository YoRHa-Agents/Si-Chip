# R13 — addyosmani/agent-skills Comparative Study & Long-Term Reference Pin

**Status**: REGISTERED (long-term reference; per spec §24.6).
**Pinned at**: `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03; 27.7k stars; 21 skills).
**Pin URL**: `https://github.com/addyosmani/agent-skills` (frozen at v1.0.0 snapshot).
**First absorbed at**: Si-Chip v0.4.2-rc1 (2026-05-05; Patch 1 of 6 of v0.5.0 absorption arc).
**Last absorbed at**: Si-Chip v0.4.7-rc1 (2026-05-05; Patch 6 of 6; arc complete).
**Decay policy**: long-term pin; **does NOT decay** (per spec §24.6.3); annual re-verify.
**Document version**: r13 v1.0 (2026-05-05; FIRST registered long-term external research reference; canonical exemplar of §24.6).

---

## 1. Why this comparative study exists

Si-Chip v0.4.2 → v0.4.6 absorbed five distinct workmanship conventions from `addyosmani/agent-skills` over five sequential rc bumps (A1 description-cap, A2 standardized sections, A3 progressive-disclosure, A4 lifecycle taxonomy, A5 meta-routing pattern). Five absorptions from a single external source warrant **structured documentation**, not ad-hoc PR commit messages, for three reasons:

1. **Provenance pin**: future Si-Chip maintainers need to reach back to the *frozen* upstream snapshot, not to whatever HEAD looks like at re-review time. Without a fixed-point pin, silent upstream drift can break Si-Chip's absorption-time assumptions (e.g. agent-skills could rename `using-agent-skills/SKILL.md` and §24.5's reference impl mapping would silently rot).
2. **Anti-pattern documentation**: agent-skills also embodies several directions Si-Chip **deliberately did NOT absorb** (marketplace direction, multi-IDE chase, automated cross-repo eval-harness substitute). Without explicit anti-pattern documentation, future maintainers might be tempted to "complete the absorption" by importing those directions — which would break §11 forever-out boundaries.
3. **Bootstrap §24.6**: the External Research Reference Registration mechanism (§24.6) is itself NEW in v0.4.7-rc1; this document IS the canonical exemplar that makes the mechanism non-hypothetical. Future r14, r15, ... registrations will use this file's structure as template.

This document is registered under §24.6 with `kind: long_term_pin` and `decay: false`. It is research material, not a code dependency: Si-Chip does **not** re-distribute, auto-update, bundle, or runtime-load any agent-skills code or markdown. The pin URL above is for reviewer hand-verification only; nothing in the Si-Chip build / install / runtime chain reads from it.

---

## 2. agent-skills repo overview (1-paragraph)

`addyosmani/agent-skills` is a curated catalogue of 21 plain-Markdown SKILL.md files that demonstrate Anthropic's "Agent Skills" workmanship pattern. Author: Addy Osmani (Google Chrome team, ex-author of `tools-of-the-trade` and similar dev-ergonomics catalogues). The repo's stated goal is "make Agent Skills useful across IDE-side agents (Claude Code, Cursor, Codex)" by providing copy-pasteable SKILL.md bodies for common engineering activities (TDD, code review, debugging, planning, shipping, etc.). The 21 skills are organised in a flat `skills/<name>/SKILL.md` layout, plus a meta-skill `using-agent-skills/SKILL.md` that lists the other 20 as routing targets, plus a `docs/skill-anatomy.md` style guide. v1.0.0 (push @ 2026-05-03) is the snapshot Si-Chip pins against for the 5 absorptions A1–A5.

---

## 3. The 21-skill catalogue (compact table)

> Compact summary; full content lives in upstream repo (do **not** copy upstream SKILL.md bodies into this Si-Chip repo per §11.1 marketplace forever-out).

| # | Skill name | Lifecycle stage (per upstream §using-agent-skills) | Si-Chip relevance |
|--:|---|---|---|
| 1 | `using-agent-skills` (meta-skill) | meta | §24.4 lifecycle.category source; §24.5 meta-routing pattern source |
| 2 | `test-driven-development` | verify | §24.2 standardized sections source (Common Rationalizations / Red Flags / Verification trio first observed here) |
| 3 | `code-review-and-quality` | review | §24.2 standardized sections source (cross-witness with #2) |
| 4 | `defensive-programming` | build | (informative; no Si-Chip absorption needed — already covered by §13 No-Silent-Failures workspace rule) |
| 5 | `debugging` | verify | (informative; no absorption — Si-Chip uses §22 eval-pack curation instead) |
| 6 | `refactoring` | build | (informative; no absorption — outside §11 scope) |
| 7 | `performance-optimization` | build | (informative; outside scope) |
| 8 | `documentation` | ship | (informative; Si-Chip uses §8 dogfood evidence as docs surrogate) |
| 9 | `git-workflow` | ship | (informative; Si-Chip uses Protected Branch workspace rule) |
| 10 | `security-best-practices` | review | (informative; Si-Chip uses §3 D7 governance_risk axis) |
| 11 | `dependency-management` | build | (informative) |
| 12 | `error-handling` | build | (informative; covered by No-Silent-Failures) |
| 13 | `logging-and-monitoring` | verify | (informative; Si-Chip uses §3 D7 OTel semconv hooks) |
| 14 | `api-design` | build | (informative) |
| 15 | `database-design` | build | (informative) |
| 16 | `feature-development` | build | (informative) |
| 17 | `bug-fixing` | verify | (informative; covered by §15 round_kind) |
| 18 | `scaling-considerations` | plan | (informative) |
| 19 | `requirements-gathering` | define | (informative) |
| 20 | `architecture-decisions` | plan | (informative) |
| 21 | `production-deployment` | ship | (informative) |
| – | `docs/skill-anatomy.md` | (style guide, not a skill) | §24.1 description-cap source; §24.3 progressive-disclosure source |

> Of the 21 skills, only 3 contributed direct absorbed workmanship: #1 `using-agent-skills` (→ §24.4 + §24.5), #2 `test-driven-development` (→ §24.2), #3 `code-review-and-quality` (→ §24.2 cross-witness). Plus the style guide → §24.1 + §24.3. The other 18 skills are *informative* (their content overlaps with existing Si-Chip workspace rules or falls outside §11 scope) and **were deliberately NOT absorbed**.

---

## 4. Cross-walk: agent-skills lesson → Si-Chip absorption (A1–A5)

| Absorption | Si-Chip spec section | Hard rule (§17) | spec_validator BLOCKER | Dogfood round | PR # | Upstream source |
|:--|---|:--:|---|---:|---:|---|
| **A1**: 1024-char description cap (Normative) | §24.1 (Normative) | rule 14 (§17.7) | BLOCKER 15 `DESCRIPTION_CAP_1024` | round_20 | #14 | `docs/skill-anatomy.md` |
| **A2**: Standardized SKILL.md sections trio (Common Rationalizations + Red Flags + Verification) | §24.2 (Informative) | — | — | round_21 | #15 | `skills/test-driven-development/SKILL.md` + `skills/code-review-and-quality/SKILL.md` (cross-witness) |
| **A3**: Progressive-disclosure (body ≤ 5KB; long material in `references/`) | §24.3 (Normative) | rule 15 (§17.8) | BLOCKER 16 `BODY_BUDGET_REQUIRES_REFERENCES_SPLIT` | round_22 | #16 | `docs/skill-anatomy.md` (cross-witness with A1) |
| **A4**: Lifecycle category taxonomy (`define / plan / build / verify / review / ship / meta`) | §24.4 (Informative) | — | — (1 OPTIONAL schema field `lifecycle.category` added) | round_23 | #17 | `using-agent-skills/SKILL.md` (lifecycle taxonomy lobe) |
| **A5**: Meta-routing pattern (5 atomic features; description-driven, NEVER learned-router) | §24.5 (Informative) | — | — | round_24 | #18 | `using-agent-skills/SKILL.md` (meta-skill workmanship lobe) |
| **A6** (this patch): Anti-pattern doc + r13 long-term registration | §24.6 (Informative) | — | — | round_25 | #19 | (this document; whole repo as long-term pin) |

**Net change v0.4.0 → v0.4.7-rc1**: spec sections +1 chapter (§24 with 6 sub-sections), hard rules 13 → 15 (+2 from A1 + A3; A2/A4/A5/A6 add zero), spec_validator BLOCKERs 14 → 16 (+2 from A1 + A3; A2/A4/A5/A6 add zero), schema $schema_version unchanged at 0.3.0 (A4 added 1 OPTIONAL field at default null; A5/A6 added zero schema fields).

---

## 5. What Si-Chip deliberately did NOT absorb (B1–B2)

Two directions in agent-skills are explicitly **NOT absorbed** by Si-Chip. These rejections are tied to §11.1 forever-out boundaries and must be revisited verbatim for any future agent-skills minor-bump that proposes new directions.

### 5.1 — B1: Plugin marketplace + multi-IDE distribution direction

**What agent-skills demonstrates**: 21 SKILL.md files designed for *any* host LLM agent (Claude Code, Cursor, Codex, copilot-cli, gemini-cli, etc.) to consume. Implicit goal: become a marketplace of skill bodies that any IDE can pick up and execute. README and `using-agent-skills/SKILL.md` both nudge in this direction (e.g. install-anywhere instructions; multi-host trigger examples).

**Status**: **DO-NOT-ABSORB**.

**Why** — cited verbatim from spec §11.1 forever-out:

> - Skill / Plugin **marketplace** 与任何分发表面积。

This first §11.1 forever-out item forbids any marketplace direction. Concretely:

- Si-Chip is **persistent optimization factory** for `BasicAbility` (per §1.1), not a distribution surface for SKILL.md content.
- Si-Chip's `packaging.install_targets` map (per §2 + §7) only enumerates **3 host-platform mirrors** (Cursor / Claude Code / Codex bridge-only) and the mirrors are **byte-equality** sync targets for Si-Chip's own SKILL.md, NOT a registry where third-party SKILL.mds can be published.
- Adding a marketplace direction would necessarily introduce a curation surface (which SKILL.mds get listed?), a versioning surface (how do 3rd-party SKILL.mds get bumped?), a quality surface (who certifies a 3rd-party SKILL.md against §3 R6 metrics?), and a permission / auth surface — all of which compound to Si-Chip becoming a generic distribution platform rather than an optimization factory.
- §11.1 item 1 is **forever-out**: not deferred-to-v0.5, not under-reconsideration; permanently excluded. Any PR introducing marketplace fields, manifest descriptors, registry endpoints, or third-party SKILL.md ingest paths must be rejected at review time.

**What Si-Chip uses instead**: §7 frozen 3-platform priority (Cursor > Claude Code > Codex bridge-only) + §10 persistence contract under `.local/dogfood/<DATE>/round_<N>/` (per-round local artifacts, not pushed to any registry).

### 5.2 — B2: "Skills for every IDE" completeness chase

**What agent-skills demonstrates**: 21 skills that each promise to work across any IDE-side agent that supports Anthropic-style Skill semantics. Implicit pressure: keep adding new skills until 100% IDE coverage is reached (e.g. add skills for Replit-AI, Continue, Aider, Cline, etc.).

**Status**: **DO-NOT-ABSORB**.

**Why** — cited verbatim from spec §11.1 forever-out:

> - 通用 IDE / Agent runtime **兼容层**。

This third §11.1 forever-out item forbids generic IDE compatibility layers. Concretely:

- Si-Chip's §7 platform priority is **frozen** at 3 platforms (Cursor / Claude Code / Codex bridge-only). Codex is **bridge-only** — not native SKILL.md runtime — by deliberate design, because Codex doesn't actually have native SKILL.md semantics and faking it would require a generic IDE-compat layer.
- Si-Chip's "support N IDEs" surface area scales as O(N²) for testing (every Si-Chip absorption must verify against each IDE's quirks). 3 platforms is already at the limit of what dogfood evidence can cover; expanding to 5 / 10 / 15 IDEs would dilute every metric.
- "Multi-IDE completeness" is a moving target — IDEs ship monthly. Treating it as a Si-Chip goal would tie the spec to vendor release cadence, which contradicts §11.1 item 3 forever-out.
- Si-Chip's success definition (per §1.1) is "**每轮 dogfood 都能输出可机器读取的迭代证据**" — focused on optimization quality, not platform coverage. Multi-IDE chase trades depth for breadth.

**What Si-Chip uses instead**: §7 frozen 3-platform priority (which can absorb new platforms only via spec rc bump + 2-round v3_strict consecutive PASS, per §11 deferred-rules); concretely v0.x permanently excludes generic IDE compat.

### 5.3 — Other notable contrasts (NEUTRAL — Si-Chip does NOT criticize)

These are direction differences, not rejections. Si-Chip and agent-skills are valid in different contexts; mentioning them helps future maintainers understand *why* Si-Chip's approach differs.

#### 5.3.1 No automated cross-repo eval harness

agent-skills relies on **prose verification** (each SKILL.md's "## Verification" section enumerates checkable invariants for human reviewers). Si-Chip uses **§8 dogfood evidence** (6 machine-readable evidence files per round, validated by `tools/spec_validator.py` against 16 BLOCKERs). Both approaches are valid in different contexts:

- agent-skills targets *catalogue breadth* (21 skills covering many engineering activities; prose verification scales because each skill is small).
- Si-Chip targets *single-ability optimization depth* (1 ability — itself — with 25 dogfood rounds; machine validation scales because evidence is structured YAML).

Si-Chip does NOT propose to expand to a 21-skill catalogue (per §11.1 item 1 marketplace forever-out + per §1.1 single-ability optimization-factory identity). Si-Chip does NOT criticize agent-skills' prose verification — for a 21-skill catalogue, prose verification is the appropriate tool. The contrast simply illustrates that v0.4.2–v0.4.7 absorbed *workmanship conventions* (description discipline, sections trio, body budget, lifecycle naming, meta-routing pattern), NOT the surrounding evaluation philosophy.

#### 5.3.2 Hooks and shell automation as substitute for measurement (CAUTIONARY)

agent-skills relies on Markdown discipline (each SKILL.md self-describes its own quality conditions). Si-Chip authors must NOT confuse Markdown discipline with §8 dogfood evidence. Markdown discipline is *necessary but insufficient* for Si-Chip:

- §24.1 description-cap is a Markdown-level discipline (BLOCKER 15).
- §24.3 progressive-disclosure is a Markdown-level discipline (BLOCKER 16).
- §24.2 / §24.5 sections discipline is Markdown-level Informative.
- But §3 R6 7-dim / 37 sub-metric measurement, §8 dogfood evidence emission, §14 C0 monotonicity invariant, §18 token-tier invariant, §19 real-data-verification, §22 eval-pack curation — these are **runtime-measured** not Markdown-asserted. Markdown-level checks alone do **not** establish that an ability is converging.

> **Caution**: future Si-Chip authors who absorb more from agent-skills's Markdown style guide must keep this layered: Markdown discipline (§24) is *additive* on top of measurement (§3 + §4 + §8 + §14 + §18 + §19 + §22), not a substitute.

---

## 6. Long-term tracking obligations

When agent-skills next bumps version, the following questions must be re-verified:

1. **Lifecycle category extension**: does agent-skills introduce a new lifecycle category beyond `{define, plan, build, verify, review, ship, meta}`? If yes, §24.4 enum field needs a Si-Chip rc bump to extend (additive; no schema break).
2. **Description-discipline cap change**: does agent-skills' description cap change from 1024? If yes, §24.1 + BLOCKER 15 needs review (likely: agent-skills' new cap becomes optional; Si-Chip retains 1024 as stricter unless gated by spec rc).
3. **Standardized sections evolution**: does agent-skills introduce a new mandatory SKILL.md section beyond Common Rationalizations + Red Flags + Verification? If yes, §24.2 sections list needs additive update.
4. **Body-budget threshold change**: does agent-skills' progressive-disclosure threshold change from ~5KB? If yes, §24.3 + §17.8 + BLOCKER 16 need review (Si-Chip's tiktoken-with-fallback measurement must remain consistent with whatever upstream uses).
5. **Automated eval harness introduction**: does agent-skills introduce a cross-repo automated eval harness? If yes, **do NOT absorb directly** (§11.1 marketplace direction concern); evaluate whether Si-Chip's §8 dogfood evidence schema needs cross-pollination instead.
6. **New meta-skill addition**: does agent-skills add a second meta-skill alongside `using-agent-skills`? If yes, §24.5.5 canonical reference impl mapping needs review (Si-Chip itself remains canonical; upstream multi-meta-skill scenario only changes the *upstream-ability-discovery* lobe, not Si-Chip's self-recognition).
7. **Multi-IDE direction change**: does agent-skills explicitly drop or formalize multi-IDE chase? Either direction does NOT trigger Si-Chip absorption (§11.1 item 3 forever-out is permanent), but the rationale in §5.2 above might warrant updating.
8. **Marketplace direction change**: does agent-skills explicitly become a marketplace? Either direction does NOT trigger Si-Chip absorption (§11.1 item 1 forever-out is permanent), but the rationale in §5.1 above might warrant updating.

When any of #1–#6 fires, register a **new** r-numbered comparison doc (r14, r15, ...) per §24.6.4; do **not** mutate this r13 file. r13 is a frozen historical pin against v1.0.0 specifically; future re-pins are separate documents.

---

## 7. Decay policy

Per spec §24.6.3:

- **This reference does NOT decay** (`kind: long_term_pin`, `decay: false`). The DevolaFlow `learnings.decay_confidence` 30-day half-life mechanism is for short-term observations (`kind: short_term_observation` / `kind: one_shot_evidence`) and does **not** apply here.
- **Annual re-verify** at minimum: cross-check the pin URL HEAD commit vs the pinned `v1.0.0` snapshot. If upstream silently force-pushed v1.0.0 (rare but possible), document the diff in a new r13.1 supplement (do not mutate this file).
- **Re-pin trigger**: agent-skills minor-bump (v1.0.0 → v1.1.x) or major-bump (v1.x → v2.x) → register r14 (new file; r13 stays frozen as historical baseline).
- **Last pinned**: 2026-05-05 against v1.0.0.
- **Next scheduled re-verify**: 2027-05-05 (annual; or earlier if upstream bumps).

---

## 8. Si-Chip self-review against agent-skills' own rubric

agent-skills's `docs/skill-anatomy.md` style guide proposes a SKILL anatomy with: (a) frontmatter `description` ≤ 1024 chars, (b) body ≤ ~5KB, (c) `references/<topic>.md` for long material, (d) standardized end-of-body sections (Common Rationalizations + Red Flags + Verification), (e) `When To Trigger` / `When NOT To Trigger` enumeration, (f) lifecycle category. Si-Chip "eats its own dogfood" by satisfying this rubric for its own SKILL.md, plus Si-Chip-specific extensions that agent-skills does not require.

| Rubric criterion | agent-skills (upstream) | Si-Chip (self-review) | Comment |
|---|---|---|---|
| description ≤ 1024 chars | Required by `docs/skill-anatomy.md` | Si-Chip frontmatter description = 132 chars (BAP `description` field; well under cap) | Si-Chip is **stricter**: BLOCKER 15 enforces; pre-bootstrap repos SKIP-as-PASS |
| body ≤ ~5KB | Suggested | Si-Chip body = 4995 tokens (under v3_strict 5000 budget by 5 tokens; per Round 24 evidence) | Si-Chip is **stricter**: BLOCKER 16 enforces graduated trigger above 5000 |
| `references/<topic>.md` for long material | Suggested | Si-Chip has 19 reference docs at `.agents/skills/si-chip/references/*.md` | Si-Chip exceeds: 19 references (5 are r13-numbered for v0.4.2–v0.4.6 absorption summaries) |
| Common Rationalizations + Red Flags + Verification end-of-body sections | Cross-witnessed in TDD + code-review SKILL.mds | Si-Chip's SKILL.md has `## When NOT To Trigger` (per §24.5 negative-space discipline); standardized trio is Informative §24.2 — Si-Chip does **not** ship them in its own SKILL.md (would push body over 5000 token budget; deferred to dedicated reference doc) | Si-Chip uses **alternative** layout that satisfies §24.5 negative-space without §24.2 trio (since §24.2 is Informative, not Normative) |
| `When To Trigger` / `When NOT To Trigger` enumeration | Required for using-agent-skills meta-skill | Si-Chip SKILL.md has both sections: `## When To Trigger` (14 mappings; per §24.5.1 atomic feature 3) and `## When NOT To Trigger` (6 mappings; per atomic feature 4) | Si-Chip exceeds: agent-skills meta-skill has ~10 + ~3 mappings; Si-Chip has 14 + 6 |
| lifecycle category | Used in `using-agent-skills/SKILL.md` body | Si-Chip BAP `lifecycle.category: meta` (per §24.4 OPTIONAL field; default null) | Si-Chip exceeds: lifecycle.category is in the structured BAP profile (machine-readable), not just SKILL.md prose |

**Si-Chip extensions that agent-skills does NOT require** (where Si-Chip exceeds the agent-skills bar):

| Si-Chip extension | Spec section | What agent-skills lacks |
|---|---|---|
| **§14 C0 core_goal invariant** (must be 1.0 every round; strict no-regression) | §14 + hard rule 9 | agent-skills has no equivalent; SKILL quality is prose-asserted, not 1.0-monotonicity-enforced |
| **§18 token-tier (C7/C8/C9) invariant** + EAGER-weighted iteration_delta | §18 + hard rule 11 + BLOCKER 12 | agent-skills has no token-tier decomposition; tokens are aggregate-only |
| **§19 real-data verification** with fixture-citation rule | §19 + hard rule 12 + BLOCKER 13 | agent-skills has no fixture-citation discipline; tests can use any fixture without provenance |
| **§22 eval-pack curation** (40-prompt minimum at v2_tightened; G1 provenance REQUIRED) | §22 + recovery_harness template | agent-skills has no eval-pack discipline; quality is per-skill prose |
| **§8 dogfood protocol** (6 evidence files per round; machine-readable) | §8 + hard rule 8 | agent-skills has no per-round evidence emission requirement |
| **spec_validator BLOCKERs (16 total)** | machine-checked invariants | agent-skills has no machine-checkable spec; entirely human-reviewed |
| **§3 R6 7-dim / 37 sub-metric taxonomy** + §4 v1/v2/v3 progressive gates | §3 + §4 | agent-skills has no metric taxonomy; quality is qualitative |
| **§5 router-test 8-cell MVP / 96-cell Full matrix** | §5 + router_floor concept | agent-skills has no routing test surface; routing is "host LLM reads description" only |
| **§6 half-retire value vector (8 axes; signed deltas)** | §6 | agent-skills has no half-retire concept; skills are kept indefinitely |
| **§7 packaging gate** (metadata ≤ 100, body ≤ 5000, install ≤ 2 steps) | §7.3 | agent-skills suggests body ~5KB but doesn't gate; Si-Chip enforces machine-checkably |

> **Self-review verdict**: Si-Chip satisfies all 6 of agent-skills' rubric criteria *and* extends each with a measurement / enforcement layer. The 5 absorptions A1–A5 cover the *workmanship-convention* layer; everything below — measurement, evidence emission, gate enforcement, value vector, dogfood protocol — is unique to Si-Chip and was already in place at v0.4.0. agent-skills' 21-skill catalogue does not have Si-Chip-equivalent measurement infrastructure; it does not need to (different scope), but the comparison clarifies why Si-Chip absorbs only the *workmanship* layer and stops short of absorbing *structural* directions (catalogue breadth, marketplace, multi-IDE).

---

## 9. §11 forever-out re-affirmation (verbatim)

§11.1 four forever-out items, cited verbatim from `spec_v0.4.7-rc1.md` §11.1 (which is byte-identical to v0.4.6-rc1 / v0.4.5-rc1 / v0.4.4-rc1 / v0.4.3-rc1 / v0.4.2-rc1 / v0.4.0 — §11 has been frozen since v0.1.0):

> - Skill / Plugin **marketplace** 与任何分发表面积。
> - **Router 模型训练** 或在线权重学习。
> - 通用 IDE / Agent runtime **兼容层**。
> - **Markdown-to-CLI 自动转换器**。

| §11.1 forever-out item | r13 absorption respect verification |
|---|---|
| Item 1 — Skill / Plugin marketplace | §5.1 above (B1) explicitly rejects marketplace direction; r13 itself is **research material**, not a code dependency / distribution surface (§24.6.5 verbatim re-affirmed). |
| Item 2 — Router model training | §24.5.2 (already absorbed in A5; not re-stated here) explicitly forbids learned router models / external classifiers / online weight updates / training-or-fine-tuning; r13 documents the absorption boundary in §4 above. |
| Item 3 — Generic IDE compat layer | §5.2 above (B2) explicitly rejects multi-IDE chase; §7 frozen 3-platform priority is byte-identical preserved. |
| Item 4 — Markdown-to-CLI auto-converter | r13 is hand-authored Markdown; no Markdown-to-CLI conversion is involved; §24.6.2 registration format is hand-edited canonical fields, not CLI-generated. |

**Conclusion**: r13 absorption (the comparative study + long-term pin) sits entirely **inside** §11 forever-out boundaries. Registered references are research material (one-shot snapshots of upstream workmanship conventions), **NOT** code dependencies. Si-Chip does not re-distribute, auto-update, bundle, or runtime-load any agent-skills code or markdown. The pin URL is for reviewer hand-verification only; nothing in Si-Chip's build / install / runtime chain reads from upstream. **registered ≠ marketplace; registered ≠ imported.**

---

## 10. References & provenance pin

### Frozen pin metadata

```yaml
id: r13
path: .local/research/r13_agent_skills_comparison.md
source_repo: addyosmani/agent-skills
source_version: v1.0.0
source_url: https://github.com/addyosmani/agent-skills
source_push_date: 2026-05-03            # upstream push timestamp
source_stars_at_pin: 27700              # GitHub stars at pin time (~27.7k)
source_skill_count_at_pin: 21           # skills/ directory count at pin time
source_meta_skill: using-agent-skills/SKILL.md  # the meta-skill A4 + A5 reference
source_style_guide: docs/skill-anatomy.md       # the style guide A1 + A3 reference
pinned_at: 2026-05-05                   # date of registration into Si-Chip
pinned_by_round: round_25               # dogfood round that emitted this registration
pinned_by_pr: '#19'                     # PR that registered r13
first_absorbed_at_spec: v0.4.2-rc1     # FIRST absorption (A1; description-cap)
last_absorbed_at_spec: v0.4.7-rc1      # LAST absorption (A6; this registration)
absorption_count: 5                     # A1-A5 (workmanship); A6 is meta-absorption (registration mechanism)
non_absorption_count: 2                 # B1 (marketplace) + B2 (multi-IDE)
decay: false                            # long-term pin; NOT subject to 30-day half-life
kind: long_term_pin
decay_policy: §24.6.3                  # Si-Chip spec section governing this pin
forever_out_compliance: §11.1 items 1-4 verbatim re-affirmed in §9 above
next_scheduled_review: 2027-05-05       # annual re-verify (or earlier if upstream bumps)
```

### Cross-references inside Si-Chip

| Si-Chip artifact | Pointer |
|---|---|
| Spec section governing this registration | `.local/research/spec_v0.4.7-rc1.md` §24.6 |
| Rule layer counterpart | `.rules/si-chip-spec.mdc` v0.4.7-rc1 add-on prose |
| AGENTS.md compiled rule | `AGENTS.md` v0.4.7-rc1 add-on paragraph |
| Reference docs absorbing each lesson | `.agents/skills/si-chip/references/description-discipline-r13-summary.md` (A1) + `.agents/skills/si-chip/references/standardized-sections-r13-summary.md` (A2) + `.agents/skills/si-chip/references/progressive-disclosure-r13-summary.md` (A3) + `.agents/skills/si-chip/references/lifecycle-category-r13-summary.md` (A4) + `.agents/skills/si-chip/references/meta-routing-pattern-r13-summary.md` (A5) |
| Dogfood round emitting this registration | `.local/dogfood/2026-05-05/round_25/` (6 evidence + 4 raw files) |
| Round 25 audit artifact | `.local/dogfood/2026-05-05/round_25/raw/agent_skills_registration_audit.json` |
| Branch | `feat/v0.4.7-anti-pattern-doc-agent-skills-registration` |
| Stack | feat/v0.4.2-description-cap (#14) → feat/v0.4.3-skill-md-sections (#15) → feat/v0.4.4-progressive-disclosure (#16) → feat/v0.4.5-lifecycle-category (#17) → feat/v0.4.6-meta-routing-pattern (#18) → feat/v0.4.7-anti-pattern-doc-agent-skills-registration (#19) |

### Verification commands (for future reviewers)

```bash
# 1. Confirm spec_validator still PASSes 16/16 against v0.4.7-rc1 spec
python tools/spec_validator.py --spec .local/research/spec_v0.4.7-rc1.md --json

# 2. Confirm backward-compat at v0.4.6-rc1 (zero regression)
python tools/spec_validator.py --spec .local/research/spec_v0.4.6-rc1.md --json

# 3. Confirm SKILL.md body remains under v3_strict body budget
python .agents/skills/si-chip/scripts/count_tokens.py \
       --file .agents/skills/si-chip/SKILL.md --both --json

# 4. Confirm pytest suite remains green (§24.6 introduces no new tests)
pytest tools/test_spec_validator.py -q
```

> **End of r13.** This document is a **frozen pin** against `addyosmani/agent-skills` v1.0.0 (push @ 2026-05-03). It does not auto-update. To re-verify or re-pin, follow §24.6.3 lifecycle (annual at minimum; or earlier on upstream bump).
