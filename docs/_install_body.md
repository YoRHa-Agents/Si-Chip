
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
| `--version` | tag | `v0.1.1` | no |
| `--source-url` | URL | `https://yorha-agents.github.io/Si-Chip` | no (mostly for testing) |
| `--yes` / `-y` | flag | `false` | no |
| `--dry-run` | flag | `false` | no |
| `--force` | flag | `false` | no |
| `--uninstall` | flag | `false` | no |
| `--help` | flag | `false` | no |

### What gets installed (9 files, ~total ~30 KB)

```
<install-dir>/
  SKILL.md                                    (metadata 78 / body 2020 tokens)
  references/basic-ability-profile.md
  references/self-dogfood-protocol.md
  references/metrics-r6-summary.md
  references/router-test-r8-summary.md
  references/half-retirement-r9-summary.md
  scripts/profile_static.py
  scripts/count_tokens.py
  scripts/aggregate_eval.py
```

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
# Expected: metadata_tokens=78, body_tokens=2020, pass=true
```

### Uninstall

```bash
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- \
  --target cursor --scope global --uninstall --yes
```

---

## Manual install (clone the repo)

If you prefer to inspect everything first, or if you want the full source tree (templates, evals, dogfood evidence, spec, ...), clone the repo. This is the same path that v0.1.0 originally shipped with: it covers Cursor and Claude Code (the two v0.1.0 priorities per spec §7.2), the deferred Codex bridge, developer setup, and smoke tests.

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

## 4. Developer Setup

```bash
pip install pyyaml
pip install tiktoken                                            # optional
pip install git+https://github.com/YoRHa-Agents/DevolaFlow.git  # optional
```

`pyyaml` is the only hard dependency for the bundled scripts. `tiktoken`
matches CI's token counting backend; `devolaflow` is required only when you
want to drive Si-Chip through the upstream `template_engine` /
`memory_router` paths (spec §5.1, §9).

## 5. Smoke Tests

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

## 6. Troubleshooting

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

## 7. Uninstall

- Cursor: delete `.cursor/skills/si-chip/` and reload the workspace.
- Claude Code: delete `.claude/skills/si-chip/` and restart the session.
- Repo: `rm -rf Si-Chip/`.

---

## Codex (deferred)

v0.1.0 ships [`AGENTS.md`](./AGENTS.md), which is compiled from
`.rules/si-chip-spec.mdc`. Codex reads `AGENTS.md`, so the Normative spec
content (§3 / §4 / §5 / §6 / §7 / §8 / §11) is in front of Codex on every
session.

Native `.codex/profiles/si-chip.md` plus
`.codex/instructions/si-chip-bridge.md` are deferred per spec §7.2 priority
3 ("Codex; v0.1.0 bridge only; no native SKILL.md runtime assumption").
Tracked in the ship report's "Next Steps (post-ship)" section.

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
| `--version` | 版本标签 | `v0.1.1` | 否 |
| `--source-url` | URL | `https://yorha-agents.github.io/Si-Chip` | 否（主要用于测试） |
| `--yes` / `-y` | 开关 | `false` | 否 |
| `--dry-run` | 开关 | `false` | 否 |
| `--force` | 开关 | `false` | 否 |
| `--uninstall` | 开关 | `false` | 否 |
| `--help` | 开关 | `false` | 否 |

### 安装内容（9 个文件，总计约 30 KB）

```
<install-dir>/
  SKILL.md                                    (metadata 78 / body 2020 tokens)
  references/basic-ability-profile.md
  references/self-dogfood-protocol.md
  references/metrics-r6-summary.md
  references/router-test-r8-summary.md
  references/half-retirement-r9-summary.md
  scripts/profile_static.py
  scripts/count_tokens.py
  scripts/aggregate_eval.py
```

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
# Expected: metadata_tokens=78, body_tokens=2020, pass=true
```

### 卸载

```bash
curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- \
  --target cursor --scope global --uninstall --yes
```

---

## 手动安装（克隆仓库）

如果你想先审视所有内容，或者需要完整的源码树（templates、evals、dogfood 证据、spec 等），请克隆仓库。这与 v0.1.0 最初发布时使用的路径一致：覆盖 Cursor 与 Claude Code（按规范 §7.2，这是 v0.1.0 的两个优先平台）、延后的 Codex bridge、开发环境配置以及冒烟测试。

## 前置依赖

- Python >= 3.10
- git
- 可选：`tiktoken`（用于精确的 token 计数；否则 `count_tokens.py` 会回退到确定性的空白切分器，并报告 `backend=fallback`）。
- 可选：`devolaflow`（R7 §1 上游 — `pip install git+https://github.com/YoRHa-Agents/DevolaFlow.git`）。
- 可选：`nines` CLI（用于真实 LLM 评估；否则内置 runner 使用确定性的种子化模拟）。

## 1. 克隆仓库

```bash
git clone https://github.com/YoRHa-Agents/Si-Chip.git
cd Si-Chip
```

## 2. Cursor 安装（优先级 1）

Skill 镜像位于 `.cursor/skills/si-chip/`。Cursor 在打开工作区时会自动发现它。可选的 bridge 规则 `.cursor/rules/si-chip-bridge.mdc` 也已包含在内，它指回 `.cursor/skills/si-chip/SKILL.md` 与 `AGENTS.md`。

重新加载 Cursor；该 Skill 应当出现在该项目的本地 skills 列表下。

验证：

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .cursor/skills/si-chip/SKILL.md --both
```

预期输出 `metadata_tokens=78`、`body_tokens=2020`、`pass=true`（满足规范 §7.3 的 packaging gate；按 `three_tree_drift_summary.json` 记录，与标准镜像完全一致）。

## 3. Claude Code 安装（优先级 2）

Skill 镜像位于 `.claude/skills/si-chip/`。Claude Code 在 session 启动时会自动发现它。

验证：

```bash
python .agents/skills/si-chip/scripts/count_tokens.py \
  --file .claude/skills/si-chip/SKILL.md --both
```

各项门控数值与 Cursor 镜像相同。

## 4. 开发环境配置

```bash
pip install pyyaml
pip install tiktoken                                            # optional
pip install git+https://github.com/YoRHa-Agents/DevolaFlow.git  # optional
```

`pyyaml` 是内置脚本的唯一硬依赖。`tiktoken` 与 CI 使用的 token 计数后端一致；`devolaflow` 仅在你希望通过上游 `template_engine` / `memory_router` 路径（规范 §5.1、§9）驱动 Si-Chip 时才需要。

## 5. 冒烟测试

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

预期：`spec_validator` 以 `verdict: PASS` 退出码 0 退出；`profile_static` 输出符合 §2.1 schema 的 `BasicAbilityProfile` YAML；两个 runner 为各 case 生成 `result.json`；`aggregate_eval` 生成 `metrics_report.yaml`，其中 MVP-8 keys 已填入数值，剩余 29 个 key 显式置 null（与 [`evals/si-chip/SMOKE_REPORT.md`](./evals/si-chip/SMOKE_REPORT.md) 一致）。

## 6. 常见问题

- `count_tokens.py` 报告 `backend=fallback`：安装 `tiktoken` 以获得与 CI 一致的结果；fallback 使用确定性的空白切分器，可能产生不同的 token 计数。
- `aggregate_eval.py` 提示 schema 交叉校验告警：属于预期行为。模板采用 JSON-Schema 形态（`properties.basic_ability.properties.metrics.properties`），并非直接的 `basic_ability.metrics` 映射；MVP-8 keys 仍会单独校验。冒烟报告将其记为非阻塞告警。
- `spec_validator.py --strict-prose-count` 以退出码 1 退出：属于预期行为。strict 模式将 §13.4 中的 prose 计数（28、21）视为权威，与 §3.1 / §4.1 的 TABLE 计数（37、30）做对照，故意用于暴露 prose-vs-table 的差异。默认模式（不带 `--strict-prose-count`）按 TABLE 计数判定，退出码为 0。

## 7. 卸载

- Cursor：删除 `.cursor/skills/si-chip/` 并重新加载工作区。
- Claude Code：删除 `.claude/skills/si-chip/` 并重启 session。
- 仓库：`rm -rf Si-Chip/`。

---

## Codex（已延后）

v0.1.0 同时分发 [`AGENTS.md`](./AGENTS.md)，它由 `.rules/si-chip-spec.mdc` 编译生成。Codex 会读取 `AGENTS.md`，因此每次 session 都会看到 Normative 规范内容（§3 / §4 / §5 / §6 / §7 / §8 / §11）。

原生的 `.codex/profiles/si-chip.md` 与 `.codex/instructions/si-chip-bridge.md` 已按规范 §7.2 优先级 3（"Codex；v0.1.0 仅 bridge；不假设原生 SKILL.md runtime"）延后。详见 ship report 的 "Next Steps (post-ship)" 章节。

</div>
