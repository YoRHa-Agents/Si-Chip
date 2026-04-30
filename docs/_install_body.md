
<div lang="en" markdown="1">

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

The HTTPS installer downloads `docs/skills/si-chip-0.4.0.tar.gz` (SHA-256 `2cfcce00f989faf2467014e638b0ea1fa67870b5a1ee6b0531942be5a4be21ab`; 83060 bytes; deterministic and reproducible) and extracts 21 files (1 SKILL.md + 1 DESIGN.md + 14 references + 5 scripts):

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

</div>

<div lang="zh" markdown="1">

## 一键安装

最快的安装方式。选择 Cursor 或 Claude Code（或两者），安装到全局位置（`~/.cursor/skills/si-chip/` 和/或 `~/.claude/skills/si-chip/`）或指定的单个仓库（`<repo>/.cursor/skills/si-chip/` 等）。

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

### 安装器选项

| 选项 | 值 | 默认值 | 必填 |
|---|---|---|---|
| `--target` | `cursor` / `claude` / `both` | （交互式提示） | `--yes` 时必填 |
| `--scope` | `global` / `repo` | （交互式提示） | `--yes` 时必填 |
| `--repo-root` | 路径 | `$PWD` | `--scope repo --yes` 时必填 |
| `--version` | 版本标签 | `v0.4.0` | 否 |
| `--source-url` | URL | `https://yorha-agents.github.io/Si-Chip` | 否（主要用于测试） |
| `--yes` / `-y` | 开关 | `false` | 否 |
| `--dry-run` | 开关 | `false` | 否 |
| `--force` | 开关 | `false` | 否 |
| `--uninstall` | 开关 | `false` | 否 |
| `--help` | 开关 | `false` | 否 |

### 安装内容（通过 tarball 安装 21 个文件，约 115 KB）

HTTPS 安装器会下载 `docs/skills/si-chip-0.4.0.tar.gz`（SHA-256 `2cfcce00f989faf2467014e638b0ea1fa67870b5a1ee6b0531942be5a4be21ab`；83060 字节；确定性可复现），并解压出 21 个文件（1 个 SKILL.md + 1 个 DESIGN.md + 14 个 references + 5 个 scripts）：

```
<install-dir>/
  SKILL.md                                              (metadata 94 / body 4646 tokens)
  DESIGN.md                                             (内部架构说明)
  references/basic-ability-profile.md                   (§2)
  references/self-dogfood-protocol.md                   (§8)
  references/metrics-r6-summary.md                      (§3 — 7 维 / 37 子指标)
  references/router-test-r8-summary.md                  (§5 — 8-cell MVP / 96-cell Full)
  references/half-retirement-r9-summary.md              (§6 — 8 维 value vector)
  references/core-goal-invariant-r11-summary.md         (§14 — C0 不变量；v0.3.0)
  references/round-kind-r11-summary.md                  (§15 — round_kind 枚举；v0.3.0)
  references/multi-ability-layout-r11-summary.md        (§16 — Informative；v0.3.0)
  references/token-tier-invariant-r12-summary.md        (§18 — C7/C8/C9；v0.4.0)
  references/real-data-verification-r12-summary.md      (§19 — fixture 溯源；v0.4.0)
  references/lifecycle-state-machine-r12-summary.md     (§20 — 升档历史；v0.4.0)
  references/health-smoke-check-r12-summary.md          (§21 — 4 维探针；v0.4.0)
  references/eval-pack-curation-r12-summary.md          (§22 — v2 最少 40 prompt；v0.4.0)
  references/method-tagged-metrics-r12-summary.md       (§23 — _method 伴随字段；v0.4.0)
  scripts/profile_static.py                             (§8 步骤 1)
  scripts/count_tokens.py                               (打包闸门)
  scripts/aggregate_eval.py                             (§8 步骤 2)
  scripts/eval_skill_quickstart.md                      (CLI 速查；v0.3.0)
  scripts/real_llm_runner_quickstart.md                 (CLI 速查；v0.4.0)
```

`DESIGN.md` 是内部架构说明，包含在 tarball / file:// 安装中，但不会被镜像到 `.cursor/skills/si-chip/` 或 `.claude/skills/si-chip/`（这两个镜像只包含 20 个文件的公开 `SKILL.md + references + scripts` 集合，遵循跨树漂移契约——详见 `CONTRIBUTING.md` §9）。

`<install-dir>` 取值如下：

| target  | scope  | 安装目录                                  |
|---|---|---|
| cursor  | global | `~/.cursor/skills/si-chip/`              |
| cursor  | repo   | `<repo-root>/.cursor/skills/si-chip/`    |
| claude  | global | `~/.claude/skills/si-chip/`              |
| claude  | repo   | `<repo-root>/.claude/skills/si-chip/`    |

### 验证安装

```bash
# Replace <install-dir> with the path the installer printed.
python3 <install-dir>/scripts/count_tokens.py --file <install-dir>/SKILL.md --both
# Expected: metadata_tokens=94, body_tokens=4646, pass=true
#           （对应 v0.4.0 v2_tightened 预算：meta <= 100, body <= 5000）
```

### 卸载

```bash
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- \
  --target cursor --scope global --uninstall --yes
```

---

## 手动安装（克隆仓库）

如果你想先审视所有内容，或者需要完整的源码树（templates、evals、dogfood 证据、spec 等），请克隆仓库。这条路径覆盖 Cursor 与 Claude Code（按规范 §7.2，这是目前的两个优先平台）、依然处于 bridge-only 状态的 Codex（v0.4.0 仍按规范 §11.2 延后原生支持）、开发环境配置以及冒烟测试。

## 前置依赖

- Python >= 3.10
- git
- 可选：`tiktoken`（用于精确的 token 计数；否则 `count_tokens.py` 会回退到确定性的空白切分器，并报告 `backend=fallback`）。
- 可选：`devolaflow`（R7 §1 上游 — `pip install git+https://github.com/YoRHa-Agents/DevolaFlow.git`）。
- 可选：`nines` CLI（旧版 live-LLM runner；v0.4.0 内置的 `evals/si-chip/runners/real_llm_runner.py` 是新版生产 runner，**不**依赖 `nines`）。
- 可选：`requests`（仅当你确实要让 `evals/si-chip/runners/real_llm_runner.py` 调用 Anthropic Messages 端点时才需要；cache-replay 模式不需要它）。

## 1. 克隆仓库

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
```

## 2. Cursor 安装（优先级 1）

Skill 镜像位于 `.cursor/skills/si-chip/`。Cursor 在打开工作区时会自动发现它。可选的 bridge 规则 `.cursor/rules/si-chip-bridge.mdc` 也已包含在内，它指回 `.cursor/skills/si-chip/SKILL.md` 与 `AGENTS.md`（后者由 `.rules/si-chip-spec.mdc` 编译生成；v0.4.0 时 AGENTS.md §13 共有 13 条 hard rules）。

重新加载 Cursor；该 Skill 应当出现在该项目的本地 skills 列表下。

验证：

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .cursor/skills/si-chip/SKILL.md --both
```

预期输出 `metadata_tokens=94`、`body_tokens=4646`、`pass=true`（满足规范 §7.3 的 v2_tightened packaging gate；按跨树漂移契约，与标准镜像完全一致——详见 `CONTRIBUTING.md` §9）。

## 3. Claude Code 安装（优先级 2）

Skill 镜像位于 `.claude/skills/si-chip/`。Claude Code 在 session 启动时会自动发现它。

验证：

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .claude/skills/si-chip/SKILL.md --both
```

各项门控数值与 Cursor 镜像相同（drift = 0）。

## 4. 开发环境配置

```bash
pip install pyyaml                                              # 内置脚本的硬依赖
pip install tiktoken                                            # 可选；与 CI 一致
pip install requests                                            # 可选；仅 live real_llm_runner 调用需要
pip install git+https://github.com/YoRHa-Agents/DevolaFlow.git  # 可选
```

`pyyaml` 是内置脚本的唯一硬依赖。`tiktoken` 与 CI 使用的 token 计数后端一致；`devolaflow` 仅在你希望通过上游 `template_engine` / `memory_router` 路径（规范 §5.1、§9）驱动 Si-Chip 时才需要。`requests` 仅在 `evals/si-chip/runners/real_llm_runner.py` 真正调用 Anthropic Messages 时需要；`--seal-cache` / cache-replay 流程无需安装。

## 5. 冒烟测试

```bash
# 14 个 BLOCKER 规范不变量 — verdict PASS
python tools/spec_validator.py --json

# 生成自身 profile
python .agents/skills/si-chip/scripts/profile_static.py \
  --ability si-chip --out /tmp/profile.yaml

# 确定性种子化的 baseline runner（不消耗 LLM）
python evals/si-chip/runners/no_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/no_ability/ --seed 42

python evals/si-chip/runners/with_ability_runner.py \
  --cases-dir evals/si-chip/cases/ --out-dir /tmp/with_ability/ --seed 42

# 聚合得到 MVP-8 + 29 个显式 null 的 R6 key
python .agents/skills/si-chip/scripts/aggregate_eval.py \
  --runs-dir /tmp/with_ability --baseline-dir /tmp/no_ability \
  --skill-md .agents/skills/si-chip/SKILL.md \
  --templates-dir templates --out /tmp/metrics_report.yaml
```

预期：`spec_validator` 以 `verdict: PASS` 退出码 0 退出（14/14 个 BLOCKER 不变量——最早的 9 个 + `REACTIVATION_DETECTOR_EXISTS` + v0.3.0 新增的 2 个 `CORE_GOAL_FIELD_PRESENT` + `ROUND_KIND_TEMPLATE_VALID` + v0.4.0 新增的 3 个 `TOKEN_TIER_DECLARED_WHEN_REPORTED` + `REAL_DATA_FIXTURE_PROVENANCE` + `HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`）；`profile_static` 输出符合 §2.1 schema 的 `BasicAbilityProfile` YAML（`$schema_version: 0.3.0`）；两个 runner 为各 case 生成 `result.json`；`aggregate_eval` 生成 `metrics_report.yaml`，其中 MVP-8 keys 已填入数值，剩余 29 个 key 显式置 `null`（与 [`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md) 一致）。

### 可选 — real-LLM runner cache replay（v0.4.0）

Round 18 / Round 19 的缓存位于 `.local/dogfood/2026-04-30/round_18/raw/real_llm_runner_cache/`（640 个条目）。在不消耗 live 调用的情况下回放：

```bash
python evals/si-chip/runners/real_llm_runner.py --help
# 完整的 Round 18 / Round 19 调用方法详见
# .agents/skills/si-chip/scripts/real_llm_runner_quickstart.md；
# cache replay 花费 $0、约 20 ms。
```

## 6. 常见问题

- `count_tokens.py` 报告 `backend=fallback`：安装 `tiktoken` 以获得与 CI 一致的结果；fallback 使用确定性的空白切分器，可能产生不同的 token 计数。
- `aggregate_eval.py` 提示 schema 交叉校验告警：属于预期行为。模板采用 JSON-Schema 形态（`properties.basic_ability.properties.metrics.properties`），并非直接的 `basic_ability.metrics` 映射；MVP-8 keys 仍会单独校验。冒烟报告将其记为非阻塞告警。
- `spec_validator.py --strict-prose-count` 在 `spec_v0.1.0.md` 上以退出码 1 退出，但在 v0.2.0+ 上 PASS：属于预期行为。旧版 v0.1.0 的散文写的是 "28 sub-metrics" / "21 threshold cells"，而 §3.1 / §4.1 表格其实是 37 / 30。v0.2.0+ §13.4 散文已对齐到 37 / 30，校验器在 strict 模式下对 v0.2.0 / v0.3.0 / v0.4.0 任一 spec 都会 PASS；保留 v0.1.0 模式仅用于历史回归。
- packaging gate 报错 `metadata_tokens=94 > 80`：属于预期行为。v0.4.0 在 `v2_tightened`（`meta <= 100`）档位发版；`v3_strict`（`meta <= 80`）已延后到 v0.4.x。详见 README 的 "Headline Numbers" 与 `.local/dogfood/2026-04-30/v0.4.0_ship_report.md`。

## 7. 卸载

- Cursor：删除 `.cursor/skills/si-chip/` 并重新加载工作区。
- Claude Code：删除 `.claude/skills/si-chip/` 并重启 session。
- 仓库：`rm -rf Si-Chip/`。

---

## Codex（v0.4.0 仍为 bridge-only）

Si-Chip 同时分发 [`AGENTS.md`](./AGENTS.md)，它由 `.rules/si-chip-spec.mdc` 编译生成。Codex 会读取 `AGENTS.md`，因此每次 session 都会看到 Normative 规范内容（§3 / §4 / §5 / §6 / §7 / §8 / §11 / §14 / §15 / §17 / §18 / §19 / §20 / §21 / §22 / §23，以及 §13 中的 13 条 hard rules）。

原生的 `.codex/profiles/si-chip.md` 与 `.codex/instructions/si-chip-bridge.md` 仍按规范 §11.2 延后（"Codex native SKILL.md runtime support；v0.x 仅 bridge"）。这一点在 v0.3.0 + v0.4.0 的 §14.6 + §18.7 + §19.6 + §20.6 + §21.6 + §22.7 + §23.7 中被反复重申；只有当 `v3_strict` 达成后，才会在新一轮 spec bump 中重新评估 Codex 原生 SKILL.md runtime。

</div>
