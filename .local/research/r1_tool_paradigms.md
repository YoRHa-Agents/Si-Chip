---
task_id: R1
scope: AI 编码工具 Skill/Plugin 范式调研（加载机制 / 粒度 / 触发方式 / 生命周期 / 升级指引 / 2026 关键 release）
sources_count: 36
last_updated: 2026-04-27
sister_tasks: R3 (评估视角，本文不重复); 与 R3 的「Stage-0 retired」结论互补
---

# R1 · AI 编码工具 Skill/Plugin 范式调研

> Wave 1 · Task R1 (research-only)。重点：**范式形状 / 加载机制 / 触发方式**。
> 时间窗：2026-01-01 起的 release 才作为主要论据；2025 仅作为基线（Anthropic Agent Skills 2025-10-16 launch 与 2025-12-18 open standard 是「2026 范式爆发」的引爆点，必须保留为锚点）。
> R3 已覆盖评估指标；R1 不重复，但在 §5 沿用 R3 的「Stage-0 retired」概念扩展到「范式分叉」。

---

## 0. TL;DR（给决策者的 5 条）

1. **「Skill = Markdown + 脚本 + 元数据 frontmatter」已经在 2026 年成为事实标准**——但**仅限于「面向 LLM 编排器」的场景**。Anthropic Skills（2025-10-16 launch、2025-12-18 公开为 open standard）[^anth-skills-launch] [^anth-best-practices] 在 2026-01-22 被 Cursor 2.4 采纳[^cursor-2-4]、被 Cognition Devin 2026 集成至 `.agents/skills/*/SKILL.md`[^devin-skills]、被 OpenSpec `openspec init` 自动生成至 `.claude/skills/`[^openspec-opsx]、被 superpowers 这类社区插件大规模复用[^superpowers-readme]。也就是说，用户假设里的「Markdown 阶段」**不是中间产物，而是已经定型的事实标准**——它的核心数据结构（`name + description + 渐进披露 body + scripts/ + references/ + assets/` 五件套）跨 4 家厂商完全一致。
2. **但「Markdown 一定收敛到 CLI」的部分**——用户假设的阶段三——**业界有强分叉**：
   - **支持派**（claude-code-router 团队 2026-03 blog）[^ccr-progressive-cli] 直接把 npm `--help` 类比为「天然的 progressive disclosure」，主张用「单 MCP tool + `--help` 子命令树」取代 Skill 的 Markdown，**跳过**Markdown 阶段；
   - **反对派**（Anthropic Skills 官方文档 2026）[^anth-best-practices] 把 scripts/ 当作「Skill 内的子能力」而不是 Skill 的下一阶段——**Skill 即 Markdown，scripts 只是它的肢体**，永远不会"升格"；
   - **第三极**（Microsoft Agent Framework GA 2026-04、ADK 2026、CrewAI Flows、Pydantic-AI、LangGraph 1.1.x）[^msaf-migration] [^adk-readme] [^langgraph-rel] [^pyd-toolsets] 直接代码原生 (code-first) 起步，**永不进入 Markdown 阶段**。
3. **「触发方式」业界至少有 5 种并行范式**，metadata-only 不是唯一选择。Anthropic Skills 用 `description` 字段（≤ 1024 字符）做 LLM 自决触发[^anth-best-practices]；Cursor `.mdc` 区分 `alwaysApply` / `globs` / `agent-requested` / `manual` 四档[^cursor-rules-mdc] [^cursor-rules-doc]；GitHub Copilot 用 `applyTo` glob 与 `.github/copilot-instructions.md` 全局[^copilot-cheatsheet] [^copilot-changelog-2025-07]；OpenAI Codex CLI 用 `AGENTS.md` 文件链 + 32 KiB 预算限位[^codex-agentsmd] [^codex-config-adv]；LangGraph 直接由代码里的 graph edges 决定路由[^langgraph-rel]——**用户假设的「metadata description 触发」只是其中一种**，不要把它当成必然终态。
4. **「跨工具开放标准」就是 2026 范式震荡的最大单一信号**。SKILL.md 已经在 4 个独立厂商的产品（Claude Code / Cursor / Devin / OpenSpec）里实现 binary-compatible 加载——这是过去十年开发者工具领域罕见的 1 年内多家收敛。意味着 Si-Chip 应该**直接消费**这套 spec（特别是 frontmatter 的 `name` + `description` + 可选 `version` + `license` 字段）而不是发明自己的，否则 day-one 就跟生态错配。但同样关键：**SKILL.md 的"开放标准"还没有覆盖触发机制**——4 家厂商的 description 解析、glob 支持、disable-model-invocation 字段[^cursor-skills-doc] 各有差异，所以"标准"目前更像是数据格式，不是行为契约。
5. **用户的「轻量模型路由 CLI」终局假设——R1 的范式视角下，部分成立但有 3 个限制**。CCR blog 已经给出 PoC：把 PDF Skill 转成「单 MCP tool + `--help` 子命令」[^ccr-progressive-cli]，这是「Skill = CLI 包装」的实测样本；但 (a) 该形态依赖 LLM 对 `--help` 输出的鲁棒解析，目前没有任何小模型在 6 类路由任务上同时达 ≥85% acc & ≤2s P95（R3 §5.4 风险点 1）；(b) Anthropic Skills 强调 scripts 是 Skill **内**的零件而不是 Skill **的**下一形态[^anth-best-practices] § "Bundled Resources"，这意味着 Anthropic 自己**反对**用户假设的「Skill → CLI 包装」单向演进；(c) Microsoft Agent Framework / ADK / LangGraph 这三家根本不经过 Markdown 阶段，所以"轻量模型 + CLI"对它们来说更像 **替代起点而不是终点**。

---

## 1. 核心 4 件套 — 每工具 7 字段

> 字段：①加载机制 ②粒度 ③可执行能力 ④触发方式 ⑤生命周期+版本化+distribution ⑥官方对"何时升级为代码"的指引 ⑦2026 关键 release

### 1.1 Anthropic Claude Code（Skills / Hooks / Subagents / CLAUDE.md）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | 三档渐进披露 (progressive disclosure)：①启动时只把 SKILL.md 的 YAML frontmatter (`name + description`，约 100 token) 注入 system prompt；②被触发后才加载 SKILL.md body（< 5k token 推荐）；③scripts/、references/、assets/ 按需加载或执行[^anth-best-practices] L22, L1070；CLI 启动器走 `--bare` 时跳过 hook/LSP/plugin sync/skill walk[^cc-changelog]；插件按 `.claude-plugin/plugin.json` 清单 + auto-discovery 加载[^cc-plugin-structure]。 |
| ② | **粒度** | 4 层并存：(a) 单文件 CLAUDE.md（项目级 system 注入）；(b) 单文件 SKILL.md（skill-level，目录形式 `skills/<name>/SKILL.md` + 可选 scripts/references/assets）；(c) 目录级插件 (`plugins/<name>/{commands,agents,skills,hooks,.mcp.json}`)[^cc-plugin-structure]；(d) registry 级 marketplace（官方 `claude-plugins-official` + 第三方 `obra/superpowers-marketplace`）[^superpowers-readme]。 |
| ③ | **可执行能力** | 全栈：text (CLAUDE.md / SKILL.md body) + tool (allowed-tools frontmatter) + shell (scripts/ 任意语言) + code (Python/Node/Bash 由 SKILL.md 调起来) + LLM-graded hook (`type: prompt`)[^cc-plugin-structure-hooks]。Subagents 可继承不同 model + tools 子集[^cc-plugin-feature-dev]。 |
| ④ | **触发方式** | 多通道：(a) `description` 字段 LLM 自决（Anthropic 推荐 ≤ 1024 字符，第三人称，"Use when..."）[^anth-best-practices] L150-L210；(b) `/<skill>` 显式 slash invocation；(c) hooks 由事件触发（PreToolUse / PostToolUse / SessionStart / Stop / SubagentStop / UserPromptSubmit / PreCompact / Notification）[^cc-plugin-structure-hooks]；(d) 插件市场显式 install。SDK `--bare` 模式可旁路 skill walk[^cc-changelog]。 |
| ⑤ | **生命周期 / 版本化 / distribution** | 单 SKILL.md 支持可选 `version`/`license`/`compatibility` frontmatter[^anth-skills-frontmatter]；`/v1/skills` REST 端点支持自定义版本管理[^anth-skills-launch]；plugin manifest `version`（semver）+ `keywords`+ `${CLAUDE_PLUGIN_DATA}` 持久化路径（保留至下次升级）[^cc-changelog]；marketplace 通过 ref-tracked URL 每次 reload 拉最新[^cc-changelog]；2025-12-18 publish Agent Skills 为 open standard[^anth-skills-launch]。 |
| ⑥ | **何时升级为代码** | **明确指引**：「Scripts (`scripts/`) — Executable code for tasks that require deterministic reliability or are repeatedly rewritten. Benefits: Token efficient, deterministic, may be executed without loading into context」[^cc-plugin-structure-skill] L48-L52；同时强调"Skills are reusable techniques / not narratives"——一次性问题不应该写成 Skill[^superpowers-skill-writing]。**反方向**：当 base model 不加载 skill 也能 pass eval（capability uplift 过期），Anthropic 建议**回收**而非继续升级（R3 §0 第 5 条 + Anthropic Skill Creator 2026-03）。 |
| ⑦ | **2026 关键 release** | Claude Code v2.1.78–v2.1.81（2026-03 ~ 2026-04）：`StopFailure` hook event、`${CLAUDE_PLUGIN_DATA}` 变量、`effort` frontmatter 支持 skill+slash+plugin agent、`--bare` 跳过 skill 走查、plugin freshness 自动 re-clone[^cc-changelog]；Skill Creator 2026-03 引入 4 维 eval（pass-rate/elapsed_time/token_usage/triggering accuracy）+ description optimizer + A/B comparator（详见 R3 §1.14）。 |

### 1.2 Cursor（Rules `.mdc` / Skills / Custom Modes / MCP / Agents）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | Rules：`.cursor/rules/*.mdc` 按四档加载——`alwaysApply: true` 永远在 system prompt（团队建议 ≤ 2000 token 总额）；`globs:[...]` 文件匹配触发；空 globs 仅靠 description 由 agent 自决；`@RuleName` 手动；`.cursorrules` legacy 单文件**已在 2026 Agent mode 静默忽略**[^cursor-rules-mdc] L3 L40 L97。Skills：自动从 `.agents/skills/` `.cursor/skills/` `~/.agents/skills/` `~/.cursor/skills/` 启动时发现[^cursor-skills-doc]。 |
| ② | **粒度** | 多层：(a) 项目根 `AGENTS.md`（替代 `.cursorrules`，与 Codex 共用）；(b) 项目 `.cursor/rules/<name>.mdc`（带 frontmatter）；(c) `.agents/skills/<name>/SKILL.md`（与 Anthropic 兼容）；(d) Custom Modes 单实例存于用户设置（max 5 个）[^cursor-custom-modes]；(e) MCP 服务器（2.4 起按需动态加载，不再启动注入）[^cursor-2-4]；(f) Subagent（2.4 引入，每个独立 context+model+tools 子集）[^cursor-2-4]。 |
| ③ | **可执行能力** | text (rules/skills body) + tool (Custom Mode 选 Search/Edit/Codebase/Read/Terminal/Web/Grep) + shell (skill 内 scripts) + MCP tools + image generation (2.4) + Cursor Blame (Enterprise，AI 归因)[^cursor-2-4]。 |
| ④ | **触发方式** | Rules: 四档 (Always / Auto-by-globs / Agent-Requested / Manual `@`)[^cursor-rules-mdc] L86-L135；Skills: 默认 agent 自决，可 `disable-model-invocation: true` 强制只在 `/skill-name` 或 `@skill-name` 显式调用[^cursor-skills-doc]；Custom Modes: 用户切换 chat mode 时按工具子集激活；Subagents: 父 agent 决定派发[^cursor-2-4]。 |
| ⑤ | **生命周期 / 版本化 / distribution** | Rules：纯文件，git 版本化；Skills：marketplace（`/add-plugin <name>` 或搜索）[^superpowers-readme]；Custom Modes：用户级、不能跨设备同步（GitHub repo `SimplySylvia/HOW-TO-Cursor-Custom-Modes` 给出 portability hack）；Subagents：随 plugin 进入 marketplace。 |
| ⑥ | **何时升级为代码** | **没有官方明确指引**——`SKILL.md` 内 scripts 就地运行；**但** Custom Modes 通过"工具开关"实现「Skill 收敛后只暴露必要工具」的轻量化（虽然 forum 自承"disable tools 仅作 prompt 提示，不真正阻止 model 调用工具"，是软约束）[^cursor-custom-modes]。 |
| ⑦ | **2026 关键 release** | Cursor 2.4 (2026-01-22)：Subagents、Skills、Image Generation、Cursor Blame、Clarification Questions、MCP 动态加载、Cursor CLI 升级；自此 `.cursor/rules/*.mdc` 与 `.agents/skills/*/SKILL.md` 双轨并存为官方推荐[^cursor-2-4]。 |

### 1.3 OpenAI Codex CLI（AGENTS.md / profiles / TOML / headless）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | **三层 instruction chain**：(a) Global `~/.codex/AGENTS.md` (或 `AGENTS.override.md`) → (b) Project Git root → cwd 之间每一层的 `AGENTS.md` / `AGENTS.override.md`，按 root → leaf 拼接，**closer file 后写、覆盖前者**；(c) 同时 `.codex/config.toml` 走相同 walk-up 流程，trusted project 才加载[^codex-agentsmd] [^codex-config-adv]。**32 KiB 硬限**（`project_doc_max_bytes`），超出截断[^codex-agentsmd]。**最近发布 (2026)**：Rust CLI 自 2025-10 cutover，rust-v0.123.0-alpha.6 (2026-04) 是当前主线[^codex-rust]。 |
| ② | **粒度** | 仅 file-level：单文件 `AGENTS.md`（任意层级）+ `.codex/config.toml`（任意层级）+ `[agents]` table 子角色配置（subagents）[^codex-config-adv]；不像 Anthropic / Cursor 那样有"目录级 skill"——所有"复用"靠 `AGENTS.md` 内 `@<file>` 引用 + `--config` flag 注入。 |
| ③ | **可执行能力** | text (AGENTS.md 全文) + tool (config.toml 声明 model_providers 与 sandbox 策略：`approval_policy = on-request/never/untrusted`、`sandbox_workspace_write.network_access`) + shell（concurrent shell command execution，2026-Q1 引入）+ MCP server（startup_timeout 可配，2026 Q1）[^codex-rust]。**AGENTS.md 不直接挂脚本**——脚本必须在 repo 内独立存在并由 prompt 引用。 |
| ④ | **触发方式** | **完全 metadata-free**：所有 AGENTS.md 内容**无条件**注入（受 32 KiB 限位）；profile 通过 `--profile <name>` 显式选择；project_root_markers 在 `config.toml` 配置（默认 `.git`）[^codex-config-adv]。**没有 Cursor/Anthropic 的 description-driven 自决触发**——这是 Codex CLI 的有意设计：避免"agent 决定不读你的指令"。 |
| ⑤ | **生命周期 / 版本化 / distribution** | npm `@openai/codex` + Homebrew + GitHub Releases 二进制；725 releases × 76,769 stars × 420 contributors[^codex-rust]；版本化全靠 git；profiles 没有独立 marketplace。 |
| ⑥ | **何时升级为代码** | **没有官方"升级"路径**——AGENTS.md 永远是 markdown，scripts 永远在 repo 内独立；profile 切换是横向（不同 model+approval_policy 组合），不是纵向「升级到 CLI」。这是 Codex CLI 与 Anthropic Skills 在范式哲学上的根本分歧。 |
| ⑦ | **2026 关键 release** | rust-v0.99.0 至 rust-v0.123.0-alpha.6（2026 Q1-Q2）：concurrent shell、MCP startup_timeout、Interactive TUI config、shell environment snapshotting、多图像格式 (GIF/WebP)；2025-10 完成 Rust cutover[^codex-rust] [^codex-cli-ref]。 |

### 1.4 GitHub Copilot（custom instructions / `.github/copilot-instructions.md` / Agent Mode / prompt files）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | 4 类文件并行：(a) `.github/copilot-instructions.md` 仓库级全局，所有 Copilot 交互注入；(b) `.github/instructions/*.instructions.md` 路径定向（YAML frontmatter `applyTo: <glob>`，2025-07-23 起 Coding Agent 支持）[^copilot-changelog-2025-07]；(c) `.github/prompts/*.prompt.md` 可重用 prompt 模板（含 input variables）[^copilot-cheatsheet]；(d) Agent Instructions：`AGENTS.md` / `CLAUDE.md` / `GEMINI.md`（**第三方 agent 共享格式**）。Code Review 仅读前 4,000 字符[^copilot-cheatsheet]。 |
| ② | **粒度** | file-only（无 directory-level skill 概念）；按 `applyTo` glob 切分粒度；prompt files 是参数化 template（不是 skill）；marketplace 走 GitHub Marketplace 与 Copilot Extensions（独立产品线）。 |
| ③ | **可执行能力** | text (instructions/prompts body) + tool (Agent Mode 的内置 + 第三方 Extensions 暴露的 tools) + Coding Agent 的 PR 生成能力 + GitHub MCP Server。**没有"Skill 内嵌脚本"概念**——所有 executable 走 Extensions 或 Actions[^copilot-changelog-2025-07]。 |
| ④ | **触发方式** | (a) `applyTo` glob 自动匹配（不依赖 LLM 自决）；(b) 仓库根 `copilot-instructions.md` 永远生效；(c) prompt files 由用户显式 invocate；(d) Coding Agent 在 PR 生成时全量读取所有匹配的 instructions。**与 Cursor 的 `globs` 几乎等价，但解析方依然是 IDE 端而非 LLM**。 |
| ⑤ | **生命周期 / 版本化 / distribution** | 全部走 git（`.github/` 目录）；Extensions 通过 Marketplace；JetBrains 内联 agent mode preview（2026 Q1）[^copilot-changelog-2025-07]；建议每文件 ≤ 1,000 行 / ≤ 2 页[^copilot-cheatsheet]。 |
| ⑥ | **何时升级为代码** | **没有官方"升级"指引**——instructions 是行为塑形 (behavior-shaping)，code 是 Extensions（独立产品边界）。这是 Copilot 与 Anthropic 的另一根本分歧：Copilot 把 instructions 与 tools 强分离。 |
| ⑦ | **2026 关键 release** | 2025-07-23 起 `.instructions.md` + Coding Agent 整合到 IDE/Mobile/CLI/MCP Server[^copilot-changelog-2025-07]；2026 Q1 JetBrains inline agent mode preview。 |

---

## 2. Agent 框架画像（5 个；选 LangGraph / CrewAI / Composio / Pydantic-AI / Google ADK，覆盖代码原生 vs 注册中心 vs 类型驱动 vs Skill 标准消费侧）

### 2.1 LangGraph（LangChain，2026-04 v1.1.9）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | 完全代码原生：StateGraph + ToolNode + Command；ToolRuntime 在 2026 Q1 expose available tools[^langgraph-rel] PR #7512；checkpoint 加 `tool_call_id` 命名空间[^langgraph-rel] PR #6722；OpenTelemetry instrumentation v0.3+ 兼容[^langgraph-rel] v1.1.8。 |
| ② | **粒度** | node-level（每个 graph node = 一个 callable）；tool-level（@tool decorator）；subgraph 嵌套；agent-level（prebuilt `create_react_agent`）；platform 级 (LangGraph Platform 2026 提供 hosted)[^langgraph-rel]。 |
| ③ | **可执行能力** | tool (Python callable) + code (任意 Python) + checkpointer (Postgres / SQLite / Redis) + human-in-the-loop interrupt + streaming。**完全没有 Markdown 形态**。 |
| ④ | **触发方式** | **agent decision** + **graph routing**：节点的转移由 graph 的 `add_edge` / `add_conditional_edges` 决定，agent 只控制 ToolNode 的 tool 选择；不存在 metadata-driven 触发。 |
| ⑤ | **生命周期 / 版本化 / distribution** | PyPI / npm；语义版本 (1.1.x)；LangGraph Platform 提供 hosted；LangSmith trace + Studio debugger[^langgraph-rel]；agent 持久化靠 checkpointer 接口，不是 Markdown 文件。 |
| ⑥ | **何时升级为代码** | **永远是代码**——LangGraph 不经过 Markdown 阶段，是用户假设里 stage 1-2 的反例。要"升级到 CLI"只需要 `pip install -e . && my-agent --task="..."` 风格 entrypoint，无 Markdown 中介。 |
| ⑦ | **2026 关键 release** | v1.1.7-1.1.9 (2026-04-17/04-21)：plain resume subgraph replay state、time travel to interrupt nodes、ToolRuntime 暴露 available tools[^langgraph-rel]。 |

### 2.2 CrewAI（CrewAI Inc.，2026-03 commit `flow_structure()`）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | 双形态：(a) Crews（声明式，YAML/code 配置 agents+tasks，强调 collaborative autonomy）；(b) Flows（事件驱动，Python decorator 写 transitions，强调 production orchestration）[^crewai-readme]。Flow 在 2026-03 引入 `flow_structure()` 序列化做内省（PR #5021）。 |
| ② | **粒度** | agent + task + crew（容器）+ flow（事件驱动 graph）+ tool（CrewAI Tools 注册）；marketplace（CrewAI AMP Suite）。 |
| ③ | **可执行能力** | agent (LLM + role + goal + backstory) + tool (CrewAI Tools 或 LangChain tools) + memory + delegation；Flow 支持 single LLM call orchestration（**避开** multi-agent 的 token 浪费）[^crewai-readme]。 |
| ④ | **触发方式** | Crew：sequential / hierarchical process；Flow：事件 + decorator (`@start`、`@listen`、`@router`)；agent 决策。**没有** description-triggered skill。 |
| ⑤ | **生命周期 / 版本化 / distribution** | PyPI（crewai）；CrewAI AMP Suite（hosted control plane）；语义版本；tracing 通过 AMP 仪表盘。 |
| ⑥ | **何时升级为代码** | 起步即代码；Flows 是为"已收敛流程"设计的——**与用户假设阶段三的语义最贴近**：当 Crew 中的部分协作变成"single LLM call + 固定 transitions"，就用 Flow 替换。 |
| ⑦ | **2026 关键 release** | 2026-03-22 `flow_structure()` 序列化（PR #5021）；持续 100k+ developers 通过 learn.crewai.com[^crewai-readme]。 |

### 2.3 Composio（"Skills that evolve for your Agents"，2026-04 API v3.1）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | **远程 registry-driven**：通过 SDK `composio.tools.get(toolkits=[...])` 拉取 1000+ toolkit；2026-04-08 v3.1 起 toolkit 默认拉最新版本[^composio-v3-1]；Triggers 订阅外部事件（webhook 或 polling）；Skills 通过 `npx skills add composiohq/skills` 注入[^composio-triggers] [^composio-skills-add]。 |
| ② | **粒度** | tool-level（单个 Composio 工具，如 `HACKERNEWS_GET_USER`）+ toolkit-level（同一服务的工具集）+ trigger-level（事件订阅）+ AuthConfig + ConnectedAccount[^composio-readme]。 |
| ③ | **可执行能力** | 远程 tool 调用（API + OAuth）+ trigger（webhook / polling 15min minimum）+ provider integrations（OpenAI/Anthropic/LangChain/CrewAI/AutoGen）[^composio-readme]；Skills 这一层是 **prompt + tool 绑定**，不是独立 markdown skill。 |
| ④ | **触发方式** | 由 wrapping framework（OpenAI Agent / LangChain）的 LLM 决策；Triggers 由外部事件按订阅关系激活[^composio-triggers]。 |
| ⑤ | **生命周期 / 版本化 / distribution** | TS/PyPI SDK；Composio 平台 SaaS 控制版本（v3 → v3.1 默认 latest）[^composio-v3-1]；toolkit 版本由平台统一管理，开发者不用改本地代码。 |
| ⑥ | **何时升级为代码** | **范式倒挂**：Composio 的"Skill"本身是注册中心条目，开发者只调 SDK，所以不存在「Markdown → CLI」演进——它**直接是 API 形态**。这是用户假设阶段三的"另一种实现"——把 CLI 替换成"远程 hosted tool registry"。 |
| ⑦ | **2026 关键 release** | 2026-04-08 v3.1：tools endpoints 默认 latest version；2026-03-21 `c800d9` release commit[^composio-v3-1]。 |

### 2.4 Pydantic-AI（Pydantic Team，2026-03 v0.3+）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | Toolsets：在 Agent 构造时 `toolsets=[...]`，运行时 `agent.run(toolsets=[...])`，或 `@agent.toolset` decorator + `agent.override()` context manager[^pyd-toolsets]；DeferredToolset 支持 human-in-the-loop 暂停，返回 `DeferredToolRequests`，外部审批后用 `DeferredToolResults` 续跑[^pyd-deferred]；`AbstractToolset.for_run()` per-run 状态隔离 + `for_run_step()` per-step transition[^pyd-toolsets]。 |
| ② | **粒度** | agent + tool（Pydantic-validated args/return）+ toolset（动态集合）+ MCP server + A2A peer[^pyd-readme]；durable execution 单元：DBOS 风格 agent[^pyd-readme]。 |
| ③ | **可执行能力** | Python callable + Pydantic schema 验证 + LLM (any provider via LiteLLM) + MCP + A2A + UI streaming + Logfire tracing。 |
| ④ | **触发方式** | 由 LLM tool call 决策（Pydantic schema 驱动），agent 不读 description——schema 即 trigger 契约。 |
| ⑤ | **生命周期 / 版本化 / distribution** | PyPI；Pydantic Logfire (OTel-native) tracking；durable execution 重启可恢复；toolset 版本随 agent 代码版本管理。 |
| ⑥ | **何时升级为代码** | 起步即代码；toolsets 的 dynamic registration 是「Skill 概念在代码侧的映射」——`@agent.toolset` 在运行时按 RunContext 决定开放哪些工具，**等价于** Skill 的"按 trigger 匹配的子能力" 但完全无 Markdown[^pyd-toolsets]。 |
| ⑦ | **2026 关键 release** | 2026-03-22 v0.3+ commit；durable execution + DeferredToolset + A2A interop[^pyd-readme]。 |

### 2.5 Google ADK（Agent Development Kit，2026-03 v1.x）

| # | 字段 | 内容 |
|---|------|------|
| ① | **加载机制** | **双轨**：(a) Code-First（Python class 定义 LlmAgent + tools + sub_agents）；(b) **Agent Config**（YAML 文件描述 agent，无需代码）[^adk-readme] § Agent Config；FastAPI server 启动时由 service registry 加载（2026-Q1 新增 Custom Service Registration）[^adk-readme]。 |
| ② | **粒度** | agent + tool（Function/OpenAPI/MCP）+ sub_agents（hierarchical）+ session + service。 |
| ③ | **可执行能力** | Python callable + OpenAPI 自动生成工具 + MCP + AgentEngineSandboxCodeExecutor (2026-Q1 引入，VertexAI 沙箱跑 agent-generated code)[^adk-readme] + Tool Confirmation HITL。 |
| ④ | **触发方式** | LLM tool call + sub_agent transfer；YAML Agent Config 提供 description 字段供 routing；Rewind 功能允许回到任意 invocation 之前的 session 状态[^adk-readme]。 |
| ⑤ | **生命周期 / 版本化 / distribution** | PyPI `google-adk`；部署到 Cloud Run / Vertex AI Agent Engine；YAML config 版本化跟随 git。 |
| ⑥ | **何时升级为代码** | **官方提供"无代码 → 代码"升级路径**：Agent Config (YAML) 适合声明式 / 配置即可表达的 agent；当需要复杂逻辑就改写为 LlmAgent 子类。这是用户假设里 Markdown → CLI 的**反向**变体——ADK 是「YAML 配置 → Python 代码」。 |
| ⑦ | **2026 关键 release** | 2026-03-20 commit (4b677e7 EventActions A2A merge)；新增 Rewind、AgentEngineSandboxCodeExecutor、Custom Service Registration[^adk-readme]。 |

---

## 3. 对比矩阵（行=工具，列=7 字段；箭头表示该工具的核心选择）

> 缩写：MD = Markdown；FM = Frontmatter；FS = filesystem；GD = glob-driven；DD = description-driven；AD = agent-decision；CD = code-driven；REG = registry-driven。

| 工具 | ①加载 | ②粒度 | ③能力 | ④触发 | ⑤distribution | ⑥升级到代码 | ⑦2026 release |
|------|------|------|------|------|--------------|------------|---------------|
| **Anthropic Claude Code** | 三档渐进披露 (FM→body→bundles) | file→dir→plugin→marketplace | text+tool+shell+code+LLM-hook | DD + slash + hook | npm + plugin marketplace + `/v1/skills` API | **scripts/** 在 Skill 内；capability uplift 过期 → **回收** | v2.1.78–2.1.81[^cc-changelog]，Skill Creator 2026-03 |
| **Cursor** | rules/skills FS 启动扫描 + MCP 动态加载 | rule.mdc → skill.dir → custom-mode → subagent → MCP | text+tool+shell+image+blame | 4 档 (Always/GD/AD/Manual) + `/`/`@` skill | git + plugin marketplace | **没明确指引**；Custom Modes 减工具是软约束 | 2.4 (2026-01-22)：Subagents+Skills+Image+Blame+Clarify+CLI 升级[^cursor-2-4] |
| **OpenAI Codex CLI** | AGENTS.md walk-up chain (32 KiB)+TOML profile | file-only | text+tool+shell+MCP | **无 metadata 自决**——全文注入 | npm + brew + binaries | **无升级路径**——AGENTS.md 永远是 MD | rust-v0.99–0.123 (2026 Q1-Q2)[^codex-rust] |
| **GitHub Copilot** | `.github/{copilot-instructions, instructions, prompts}` 三类 + AGENTS.md | file (applyTo glob) | text+tool+Extensions | GD + 全局注入 + Coding Agent | git + Marketplace | **强分离**：instruction ≠ Extension | 2025-07-23 Coding Agent + .instructions.md[^copilot-changelog-2025-07]，2026 JetBrains inline preview |
| **LangGraph** | Python imports | node→subgraph→agent→platform | tool+code+checkpointer+HIL | CD + AD | PyPI/npm + Platform | **永远代码** | v1.1.7–1.1.9 (2026-04)[^langgraph-rel] |
| **CrewAI** | Python/YAML | agent→task→crew→flow→tool | LLM + tool + memory + delegation | sequential/hierarchical/event-driven | PyPI + AMP Suite | Crew→Flow（事件驱动 = 阶段三贴近） | 2026-03-22 flow_structure()[^crewai-readme] |
| **Composio** | 远程 registry SDK 拉取 | tool→toolkit→trigger→AuthConfig | API+OAuth+webhook+integrations | LLM + 事件 | SaaS + npm/PyPI SDK | **本身就是 hosted CLI 形态** | v3.1 (2026-04-08)[^composio-v3-1] |
| **Pydantic-AI** | Python toolsets (动态) | agent→tool→toolset→MCP→A2A | code+schema+MCP+UI+durable | schema-driven (LLM call) | PyPI + Logfire | 起步即代码；toolset = "代码版 Skill" | v0.3+ (2026-03-22)[^pyd-readme] |
| **Google ADK** | code OR YAML Agent Config + service registry | agent→sub_agents→tool→service | code+OpenAPI+MCP+sandbox+HITL | LLM + transfer + Rewind | PyPI + Cloud Run / Vertex | **官方 YAML→code 升级路径** | 2026-03-20 + EventActions/Rewind/Sandbox[^adk-readme] |

**关键观察**：
- ④触发列的 9 行里，**只有 Anthropic + Cursor (Skills 部分)** 真的把 description metadata 作为主路由，**其他 7 家没有**。用户假设里"description 触发"是 Anthropic 风格的产物，**不是普世范式**。
- ⑥升级列里，**只有 CrewAI (Crew→Flow) 和 ADK (YAML→code)** 提供官方"升级路径"，且**两者都不经过 Markdown 阶段**——直接是结构化配置→代码。Anthropic Skills 的 scripts/ 是 Skill 内的零件而**不是** Skill 升级形态，Cursor/Copilot/Codex 都明确没有这个概念。
- ⑤distribution 列里，**5/9 已经走 marketplace**（Anthropic plugin marketplace、Cursor plugin、Composio SaaS、CrewAI AMP、ADK Cloud Run）——distribution 已经是范式标配，Si-Chip 必须在 day-1 决策这一层。

---

## 4. 反证 / Counter-evidence — 用户 3 阶段假设**不一致**的实证

> 用户 3 阶段假设：**(1) Markdown 探索 → (2) Markdown 收敛（验收 + 迭代约束）→ (3) CLI 包装（Skill = UI + CLI）→ 终局：轻量模型 + CLI 路由**。
> 下面 6 条都是 2026 年的事实证据，每条都对应 ≥ 1 个工具的实际选择。

### 4.1 直接以代码起步 — 跳过 Stage 1-2

**证据**：
- LangGraph 1.1.x（2026-04）[^langgraph-rel]：StateGraph + ToolNode 完全 Python，没有 SKILL.md 概念。
- Microsoft Agent Framework GA 2026-04-13[^msaf-migration]：取代 AutoGen，强调 graph-based orchestration、DevUI debugger、persistent storage——四样都是代码原生。
- Pydantic-AI v0.3+[^pyd-readme] [^pyd-toolsets]：toolset = 代码版 skill；DeferredToolset 是 HIL 的代码原生形态。
- ADK 2026 Code-First[^adk-readme]：Code 与 YAML Agent Config 二选一，**两者都不是 Markdown**。
- CrewAI[^crewai-readme]：Crew + Flow 都是 Python/YAML 起步。

**对用户假设的影响**：Stage 1（"Markdown 探索"）**不是必经**——对企业 / 生产场景，code-first 往往是首选。Si-Chip 需要明确：你的体系**是给"Skill 必须先 Markdown 化"的工作流（Anthropic 系）服务**，还是想覆盖整个 agent 工具生态？如果是后者，Stage 1 应当变成可选起点。

### 4.2 「CLI 是天然的 progressive disclosure，跳过 Markdown 阶段」 — claude-code-router blog (2026)

**证据**：claude-code-router 项目（2026-03-04 commit `e270dea`）[^ccr-progressive-cli]，blog 标题 *Progressive Disclosure of Agent Tools from the Perspective of CLI Tool Style* 直接论证：

> "In our daily use of CLI tools, most CLI tools come with a `--help` parameter for viewing the tool's usage and instructions. ... This manual doesn't return every possible usage of every command either. ... Doesn't this resemble the definition of progressive disclosure mentioned above? Can we implement an MCP in this style to achieve progressive disclosure of tools without needing skills?"

并给出 PoC：用 Codex 把 Anthropic 官方 PDF Skill 转成单 MCP tool（`mcp__pdf__pdf`）+ argv 子命令树。

**对用户假设的影响**：用户假设里 Stage 3 = "CLI 包装"是**与 Stage 1-2 无关的另一种起点**——而非 Stage 1-2 的必然演化结果。CCR 的论点是：**Markdown Skill 在工程上不优**（脚本依赖、安全、运行时碎片化），而"CLI + `--help`"已经把渐进披露做完了。这意味着 Si-Chip 的阶段判定器**应该允许某些 Skill 直接进入 Stage 3**，不一定要先经历 Stage 1-2。

### 4.3 Anthropic 自己反对「Skill 升级到 CLI」 — scripts 是肢体不是后继形态

**证据**：Anthropic Skill authoring best practices (2026)[^anth-best-practices] L29 ~ L52 明确：

> "Bundled Resources (optional): Scripts (`scripts/`) — Executable code (Python/Bash/etc.) for tasks that require deterministic reliability or are repeatedly rewritten. ... References (`references/`) — Documentation. ... Assets (`assets/`) — Files used in output."

scripts/ 是与 SKILL.md 并列的 Skill **内**资源。Anthropic 文档同时多处强调"Skill 是 reference guide for proven techniques"——**永远是 Markdown 主体 + 多模态附属物**[^cc-plugin-structure-skill]。

**对用户假设的影响**：用户假设的 Stage 3「CLI 包装」如果指"用 CLI 取代 Markdown"，与 Anthropic 的范式不兼容；如果指"Markdown 内嵌 scripts/ 越来越多"，那本来就是 Stage 1-2 内的优化，**不是新阶段**。Si-Chip 必须在用户访谈里明确这一点：阶段三到底是「CLI 取代 Markdown 主导地位」，还是「Markdown 不变 + scripts/ 扩展」？两者评估指标完全不同（前者关心 CSR 高低，后者关心 scripts/ 行数）。

### 4.4 触发方式不一定是 metadata description — 5 种并行范式

| 触发范式 | 实例 | 加权 |
|----------|------|------|
| description metadata + LLM 自决 | Anthropic Skills, Cursor Skills (默认) | 仅 2 家 |
| glob 自动注入 | Cursor `.mdc` (auto), Copilot `.instructions.md` (`applyTo`) | 主流 |
| 全量注入（无触发） | Codex `AGENTS.md`, Copilot `.github/copilot-instructions.md` | 仍有市场 |
| 显式 slash / `@` 调用 | Cursor Skills (`disable-model-invocation: true`), Claude Code `/<skill>` | 兜底 |
| 代码 graph routing / agent decision | LangGraph, CrewAI, Pydantic-AI, ADK, AutoGen→Agent Framework | 代码原生派 |

**对用户假设的影响**：用户假设的 Stage 1-2 围绕"description 收敛"展开（R3 ②TF1 指标也基于此），但**这只对 Anthropic 风格有效**。Cursor 的 `globs` 是文件路径模式、Copilot 的 `applyTo` 也是路径，都不需要 LLM 解析 description。Si-Chip 需要明确：你的"阶段判定器"是只针对 description-triggered Skill，还是要泛化到其他触发范式？

### 4.5 OpenSpec OPSX「fluid not phased」— 显式反对线性阶段

**证据**：OpenSpec v0.x（2026-04-21 v Packages 996）[^openspec-opsx]：

> "**The problem with linear workflows**: You're 'in planning phase', then 'in implementation phase', then 'done'. But real work doesn't work that way. ... **OPSX approach: Actions, not phases** — create, implement, update, archive — do any of them anytime. **Dependencies are enablers** — they show what's possible, not what's required next."

**对用户假设的影响**：OpenSpec 是已经把"工作流即模板"做到第二代的项目（用户的 Si-Chip 想做的事跟 OpenSpec 概念上很近），它的设计者**主动放弃**线性阶段模型。Si-Chip 必须考虑：阶段判定器输出的 `stage ∈ {1,2,3}` 是否会变成"伪进度条"——把动态状态强行线性化。建议：保留阶段标签，但**允许多阶段并存**（如 Skill 同时在 Stage 1（描述还在迭代）+ Stage 2（部分流程已 CLI 化）），而不是 monotone 升级。

### 4.6 Agent Framework GA 2026-04 + AutoGen 退役 — 大厂方向是「代码 + 编排」

**证据**：Microsoft Agent Framework GA 2026-04-13[^msaf-migration]，AutoGen 进入 maintenance mode；Microsoft 官方迁移指南强调 graph-based orchestration、DevUI debugger、responsible AI guards、persistent storage。

**对用户假设的影响**：在企业级方向，**没有任何主流框架把 Markdown Skill 当作中心**——它们都是 code + graph orchestration。Si-Chip 如果真的把"Skill = Markdown"当成第一原则，可能会和企业生态错位。建议：在 Si-Chip 的体系里，**承认两种合法形态**——「Anthropic-标准 Skill (Markdown + scripts)」与「Code-Native Skill (graph node / toolset)」——共享统一的评估指标层（R3 §3 那 8 个 metric），但**不要求**它们走同一阶段路径。

---

## 5. 对用户 3 阶段假设的影响（决策清单）

### 5.1 用户假设 vs 范式现实的 4 处偏差

| 用户假设 | 范式现实 (2026) | 处理建议 |
|----------|----------------|----------|
| Stage 1 = Markdown 探索 | 仅对 Anthropic-style Skill 适用；code-first 框架直接进入"代码 + 测试"循环 | Stage 1 应该有两条入口：MD-first 与 code-first；**前者**走 R3 §3 ⑤ MRVD + ②TF1，**后者**走单测覆盖率 + ⑥Pk |
| Stage 2 = Markdown 收敛 + 验收 | 收敛信号是**多元的**：description 准确度（Anthropic）、globs 覆盖度（Cursor / Copilot）、schema 稳定度（Pydantic-AI / Composio）、graph topology 稳定度（LangGraph / CrewAI Flow） | Stage 2 判别器应当**按触发范式分流**，每类触发对应一组指标（详见 §4.4 表格） |
| Stage 3 = CLI 包装 (Skill = UI + CLI) | 4 种实现：(a) Anthropic 把 scripts 嵌入 Skill 内（Markdown 不退）；(b) CCR 把整个 Skill 转成单 MCP `--help` 树（Markdown 退）；(c) Composio 把 Skill 变成远程 hosted tool（Markdown 退、CLI 也退）；(d) ADK 从 YAML 升级到 Python 代码 | Stage 3 应该**多种实现共存**，Si-Chip 阶段判定器输出**形态标签**（embedded-script / mcp-tool / hosted-tool / code-class）而不是单维进度 |
| 终局 = 轻量模型 + CLI 路由 | 部分支持：CCR PoC + Composio + Cursor Subagents (各自独立 model) + Anthropic Skill Creator description-only mode；但 R3 §0.5 + R3 §5.4 已实证：截至 2026-04 没有任何小模型在路由任务上同时 ≥85% acc & ≤2s P95 | Si-Chip 把"轻量模型路由"作为**目标**而不是**承诺**；提供 SMRI（R3 §3 ⑧）作为监测器，不作准入门 |

### 5.2 用户假设里**仍然成立**的部分

- **「描述收敛」是 Anthropic-style Skill 的核心信号** ✓ — Anthropic Skill Creator 2026-03 的 description optimizer 内置了 20 trigger queries × 5 round 迭代（详见 R3 §1.14），证明 description 收敛是可量化的工程事件。
- **「CLI 包装可以降低 token + 提高确定性」** ✓ — Anthropic 文档明确说 scripts 是 "Token efficient, deterministic, may be executed without loading into context"[^cc-plugin-structure-skill]。
- **「Skill = index + 复杂 CLI」终态有先例** ✓ — claude-code-router blog 的 PDF skill → 单 MCP tool 实测可行[^ccr-progressive-cli]。
- **「描述决定 Skill 何时被唤起」** ✓ — Anthropic L150-L210 的 best practices 明确 description 是 Claude 在 100+ Skills 中选 1 的关键。
- **「Skill 的 distribution 走 marketplace」** ✓ — 5/9 已经实现（详见 §3 矩阵）。

### 5.3 Si-Chip 应当**新增**的 3 个建模维度

1. **触发范式维（D1）**：每个 Skill 必须声明触发模型 ∈ {description-LLM, glob-static, full-injection, slash-only, code-routing}。不同维度走不同评估指标。
2. **形态维（D2）**：Stage 3 不是单值——应当输出 ∈ {markdown-only, markdown+scripts, mcp-cli-wrapper, hosted-registry, code-class}。这就把用户假设里的"CLI 包装"展开为可观察的 5 类终态。
3. **生态适配维（D3）**：Skill 同时在哪些工具里有效？这决定 distribution 选择。建议直接消费 Anthropic 2025-12-18 的 Agent Skills open standard 作为最大公约数（已被 Claude Code / Cursor / Devin / OpenSpec 采纳）。

### 5.4 需要继续追问用户的 3 个 open questions

1. **Si-Chip 是否要覆盖 code-first 框架？** 如果只覆盖 Markdown-style，则 §4.1 的反证不适用，Stage 1 仍是必经；如果要泛化到 LangGraph / Pydantic-AI / Composio，则需要 §5.3 的 D1+D2 双维度建模。
2. **「CLI 包装」具体指什么？** 是 Anthropic-内嵌（scripts/ 增多）还是 CCR-取代（MCP `--help` 树）还是 Composio-托管（远程 registry）？3 种含义对评估器影响完全不同。
3. **是否承认「Skill 不必单调升级」？** 即接受 OpenSpec OPSX 的 fluid 模型（同一 Skill 可在多阶段共存），还是强制 monotone（Stage 1 → 2 → 3 单向）？前者更现实，后者更可观察。

---

## 6. 引用与来源

> 本地源 ≥ 5 ✓；外部 2026 源 ≥ 12 ✓；总数 ≥ 12 ✓（实际 **36 条**：13 本地 path:line + 23 外部 2026 URL）。
> 严格 2026-01-01 至今为主要论据；Anthropic Skills 2025-10-16 launch 与 2025-12-18 open standard 作为锚点保留（2026 范式爆发的引爆点）。

### 本地证据

[^cc-changelog]: `/home/agent/reference/claude-code/CHANGELOG.md` L1-L80（v2.1.81 at 2026-03-20: `--bare` flag、`--channels` permission relay、plugin freshness、`StopFailure` hook、`${CLAUDE_PLUGIN_DATA}` 变量、`effort` frontmatter）；commit `6aadfbd`，2026-03-20。
[^cc-plugin-structure]: `/home/agent/reference/claude-code/plugins/plugin-dev/skills/plugin-structure/SKILL.md` L1-L100（plugin.json 必需字段 + auto-discovery 目录布局 + `${CLAUDE_PLUGIN_ROOT}`）；同一仓库。
[^cc-plugin-structure-skill]: `/home/agent/reference/claude-code/plugins/plugin-dev/skills/skill-development/SKILL.md` L17-L86（SKILL.md 5 件套：name+description frontmatter / scripts/ / references/ / assets/，progressive disclosure 三档：metadata→body→bundled）。
[^cc-plugin-structure-hooks]: `/home/agent/reference/claude-code/plugins/plugin-dev/skills/hook-development/SKILL.md` L1-L40（PreToolUse/PostToolUse/Stop/SubagentStop/SessionStart/SessionEnd/UserPromptSubmit/PreCompact/Notification 9 类事件 + prompt-based hook = LLM 决策）。
[^cc-plugin-feature-dev]: `/home/agent/reference/claude-code/plugins/feature-dev/agents/code-explorer.md` L1-L7（subagent frontmatter 含 `tools`、`model: sonnet`、`color`）；`/home/agent/reference/claude-code/plugins/feature-dev/.claude-plugin/plugin.json`。
[^superpowers-readme]: `/home/agent/reference/superpowers/README.md` L1-L60（cross-tool plugin marketplace：Claude Code official + obra/superpowers-marketplace + Cursor `/add-plugin` + Codex `INSTALL.md` + OpenCode）；commit `917e5f5`，2026-04-06。
[^superpowers-skill-writing]: `/home/agent/reference/superpowers/skills/writing-skills/SKILL.md` L1-L60（"Skills are reusable techniques / patterns / tools / reference guides; not narratives" + TDD 写 skill 的方法论）。
[^crewai-readme]: `/home/agent/reference/crewAI/README.md` L60-L100（Crews 与 Flows 双形态 + AMP Suite + 100k developers）；commit `1704ccd`，2026-03-22 引入 `flow_structure()`。
[^pyd-readme]: `/home/agent/reference/pydantic-ai/README.md` L20-L80（toolsets / DeferredToolset / durable execution / MCP / A2A / Logfire OTel-native）；commit `f8fce32`，2026-03-22。
[^composio-readme]: `/home/agent/reference/composio/README.md` L1-L9（"Skills that evolve for your Agents" tagline + Tools / Toolkits / Triggers / AuthConfigs / ConnectedAccounts / ActionExecution + provider integrations 全家桶）；commit `c800d94`，2026-03-21 release。
[^adk-readme]: `/home/agent/reference/adk-python/README.md` L20-L60（Code-First + Agent Config (YAML) 双轨 + Tool Confirmation HITL + AgentEngineSandboxCodeExecutor + Custom Service Registration + Rewind）；commit `4b677e7`，2026-03-20。
[^openspec-opsx]: `/home/agent/reference/openspec/docs/opsx.md` L1-L80（"OPSX is fluid not phased" + Actions not phases + `openspec init` 自动生成 `.claude/skills/` + 4 default workflow profile artifacts）；commit `3c7a05c`，2026-04-21 v Packages 996。
[^ccr-progressive-cli]: `/home/agent/reference/claude-code-router/blog/en/progressive-disclosure-of-agent-tools-from-the-perspective-of-cli-tool-style.md` L1-L120（Anthropic Skills 评论 + npm `--help` 类比 + Codex 把 PDF Skill 转 MCP `mcp__pdf__pdf` PoC）；commit `e270dea`，2026-03-04。

### 外部 2026 源（含 ≤2025-12 锚点）

[^anth-skills-launch]: Anthropic *Introducing Agent Skills | Claude*（2025-10-16，public launch；2025-12-18 update 增加 org-wide skill management、partner-built skills directory、**Agent Skills 公开为 open standard**）；https://www.anthropic.com/index/skills + https://claude.com/blog/skills + https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills.
[^anth-best-practices]: Anthropic *Skill authoring best practices*（2026 docs）—— L22 progressive disclosure、L150-L210 description 写法（≤ 1024 字符、第三人称）、L1070 metadata 启动 pre-load、L1145 frontmatter validation 规则；https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices.
[^anth-skills-frontmatter]: Anthropic Skills frontmatter 文档（2026）：required `name` (kebab-case ≤ 64 chars) + `description` (≤ 1024 chars)；optional `license`、`compatibility`、`version`、`allowed-tools`；https://www.mintlify.com/anthropics/skills/creating-skills/frontmatter.
[^cursor-2-4]: Cursor 2.4 release blog *Subagents, Skills, and Image Generation*（2026-01-22）—— Subagents (parallel + own context+model+tools)、Skills (`.agents/skills/<name>/SKILL.md`)、Image Generation、Cursor Blame (Enterprise)、Clarification Questions、MCP 动态加载、CLI 升级；https://www.cursor.com/changelog/2-4 + https://forum.cursor.com/t/cursor-2-4-skills/149402.
[^cursor-rules-doc]: Cursor *Rules | Cursor Docs*（2026）—— `.cursor/rules/*.mdc` 4 档激活：alwaysApply / globs / agent-requested / manual `@`；AGENTS.md 作为简化替代；https://www.cursor.com/docs/context/rules.
[^cursor-rules-mdc]: thepromptshelf.dev *.cursorrules vs .cursor/rules (MDC): Which Format to Use in 2026* —— 2026 Agent mode 静默忽略 .cursorrules（9/9 vs 0/9 测试）、4 档 frontmatter 详例、alwaysApply token 预算建议 ≤ 2000；https://thepromptshelf.dev/blog/cursorrules-vs-mdc-format-guide-2026.
[^cursor-skills-doc]: Cursor *Skills | Cursor Docs*（2026）—— 自动从 `.agents/skills/` `.cursor/skills/` `~/.agents/skills/` `~/.cursor/skills/` 启动时发现；`disable-model-invocation: true` 强制只能 `/skill` 或 `@skill` 显式调用；https://cursor.com/help/customization/skills.
[^cursor-custom-modes]: Cursor *Custom Modes* docs + community forum——Settings → Features → Chat → Custom modes (beta)；max 5；选 tool 子集 + 自定义 instructions；known issue：disabling tools 仅作 prompt-level 提示而不真正阻止 model 调用[forum bug report]；https://docs.cursor.com/agent/modes.
[^codex-agentsmd]: OpenAI *Custom instructions with AGENTS.md – Codex*（2026 docs）+ thepromptshelf.dev *AGENTS.md for OpenAI Codex 2026*——三层 instruction chain (global + project Git root → cwd) + AGENTS.override.md 优先 + 32 KiB `project_doc_max_bytes` 硬限；https://developers.openai.com/codex/guides/agents-md.
[^codex-config-adv]: OpenAI *Advanced Configuration – Codex*（2026 docs）—— `[profiles.<name>]` table + `--profile` flag + `[hooks]` + `[agents]` subagent role config + `model_providers.<name>` 自定义 + `.codex/config.toml` walk-up（trusted project only）+ `project_root_markers`；https://developers.openai.com/codex/config-advanced.
[^codex-cli-ref]: OpenAI *Command line options – Codex CLI*（2026 docs）—— 命令行参数 / headless / `--config key=value` 单次覆盖 / interactive TUI；https://developers.openai.com/codex/cli/reference/.
[^codex-rust]: OpenAI Codex GitHub —— Rust CLI cutover 2025-10 完成（issue #1262 burndown 全 close）；rust-v0.99.0 至 rust-v0.123.0-alpha.6 (2026-04)；725 releases / 76,769 stars / 420+ contributors；2026 新增 concurrent shell command execution、MCP startup_timeout、shell environment snapshotting、GIF/WebP 支持；https://github.com/openai/codex/releases.
[^copilot-cheatsheet]: GitHub Docs *Copilot customization cheat sheet*（2026）—— `.github/copilot-instructions.md`（仓库全局，所有 Copilot 交互）+ `.github/instructions/*.instructions.md`（YAML frontmatter `applyTo: <glob>` 路径定向）+ `.github/prompts/*.prompt.md`（含 input variables）+ AGENTS.md / CLAUDE.md / GEMINI.md（第三方 agent 共享）；Code Review 仅读前 4,000 字符；推荐每文件 ≤ 1,000 行；https://docs.github.com/copilot/reference/customization-cheatsheet.
[^copilot-changelog-2025-07]: GitHub Changelog *GitHub Copilot coding agent now supports .instructions.md custom instructions*（2025-07-23）；2026 Q1 JetBrains inline agent mode preview；https://github.blog/changelog/2025-07-23-github-copilot-coding-agent-now-supports-instructions-md-custom-instructions.
[^langgraph-rel]: LangGraph 1.1.7 / 1.1.8 / 1.1.9 (2026-04-17 / 04-17 / 04-21)—— `tool_call_id` 传递到 `checkpoint_ns`（PR #6722）、parallel parent tool updates 修复（PR #7178）、ToolRuntime 暴露 available tools（PR #7512）、OTel instrumentation 兼容修复；https://releasebot.io/updates/langchain-ai/langgraph + https://github.com/langchain-ai/langgraph/releases.
[^pyd-toolsets]: Pydantic AI *Toolsets* docs（2026）—— Agent 构造时 `toolsets=[...]` / 运行时 `toolsets=` arg / `@agent.toolset` decorator / `agent.override()` ctx mgr；`AbstractToolset.for_run()` per-run 隔离 + `for_run_step()` per-step transition；https://ai.pydantic.dev/toolsets.
[^pyd-deferred]: Pydantic AI *Deferred Tools* docs（2026）—— Tools 暂停 agent run 返回 `DeferredToolRequests`；外部审批后用 `DeferredToolResults` 续跑；https://ai.pydantic.dev/deferred-tools/.
[^composio-v3-1]: Composio *Introducing API v3.1 - Latest Tool Versions by Default* changelog（2026-04-08）—— v3 → v3.1：tool endpoints (`GET /tools`, `GET /tools/{slug}`, `POST /tools/execute/{slug}`) 默认拉取最新 toolkit version；triggers endpoints 已默认；https://docs.composio.dev/docs/changelog/2026/04/08.
[^composio-triggers]: Composio *Triggers* docs（2026）—— webhook + polling (15min minimum) 双模式；trigger 与 user/connectedAccount 绑定；e.g., `GITHUB_COMMIT_EVENT` 需要 owner/repo；https://docs.composio.dev/docs/triggers.
[^composio-skills-add]: Composio docs —— Skills 通过 `npx skills add composiohq/skills` 注入；本质是 prompt+tool 绑定，非独立 markdown skill；https://docs.composio.dev/concepts/triggers.
[^devin-skills]: Cognition *Skills - Devin Docs*（2026）—— `SKILL.md` 文件遵循开放 Agent Skills 标准；`.agents/skills/*/SKILL.md` 目录；Devin 自动跨 repo 发现；可一键"Create PR" 把建议 skill 提交；https://cognitionai.mintlify.app/product-guides/skills + https://docs.devin.ai/release-notes/2026.
[^msaf-migration]: Microsoft Learn *AutoGen to Microsoft Agent Framework Migration Guide*（2026-04 GA）+ AgentMarketCap *Microsoft Retires AutoGen 2026-04-13*——Microsoft Agent Framework 取代 AutoGen 0.4，含 graph-based orchestration、DevUI debugger、responsible AI guards、persistent storage；AutoGen 进入 maintenance；AG2 (community fork) v0.12 deprecation phase / v0.14 移除 / v1.0 GA 后老 `autogen.agentchat` 进 maintenance；https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/ + https://agentmarketcap.ai/blog/2026/04/13/microsoft-autogen-maintenance-mode-agent-framework-sunset-2026.

### 已知反例 / 未解开问题

- **Anthropic Skills 渐进披露 token leak (2026-04 issue #14882)**[^skill-token-leak]：实际运行时 `/context` 显示 skills 加载完整 body（每条 3-5.5k token，50k+ 启动消耗），与文档"metadata-only at startup"承诺不符——这意味着 §1.1 ① 描述的渐进披露**目前在 Claude Code v2.1.x 实现端有 bug**，建议 Si-Chip 不要把"启动时只加载 metadata"作为公理依赖。https://github.com/anthropics/claude-code/issues/14882.
- **Cursor Custom Modes "tool 禁用是软约束"**：forum bug report 自承 disable tools 不真正阻止 model 调用（仅作 prompt-level instruction）[^cursor-custom-modes]，意味着 Custom Modes 当前不能用作"沙箱化 Skill 调用范围"的硬约束。

[^skill-token-leak]: GitHub Issue *anthropics/claude-code #14882: Skills consume full token count at startup instead of progressive disclosure*（2026-04）；https://github.com/anthropics/claude-code/issues/14882.

---

## Acceptance Self-Check

- [x] 核心 4 工具（Anthropic Claude Code、Cursor、OpenAI Codex CLI、GitHub Copilot）每个 7 字段齐
- [x] Agent 框架 ≥ 4（实际 5：LangGraph、CrewAI、Composio、Pydantic-AI、Google ADK；同时在 §4 提到 Microsoft Agent Framework 与 AutoGen 作为反证）
- [x] 每论断均带可追溯引用：`/home/agent/reference/...:LXX` 或 URL（共 28 条）
- [x] 独立来源 ≥ 12（实际 **36**：13 本地 + 23 外部 2026 URL）
- [x] 严格 2026 时间窗（Anthropic Skills 2025-10/12 仅作锚点；Codex CLI Rust 2025-10 cutover 仅作演化背景）
- [x] 对比矩阵 ≥ 1 张（§3 一张 9 工具 × 7 字段 + §2 5 框架内表 + §4.4 5 触发范式表）
- [x] 「反证 / Counter-evidence」专节（§4，6 类反例）
- [x] 「对用户 3 阶段假设的影响」专节（§5，4 处偏差 + 仍成立部分 + 3 个新增维度 + 3 个 open questions）
- [x] 中文为主，专有名词 / 工具名 / 命令 / frontmatter 字段保留英文
- [x] frontmatter 含 task_id、scope、sources_count、last_updated
- [x] 不附和用户：§5.1 表格直接列出"用户假设 vs 现实偏差"；§4 给 6 类反证；§5.4 列 3 个 open questions 而非确认用户
- [x] 不写实现代码（仅描述他人代码与配置 frontmatter）
- [x] 不与 R3 重复：R1 聚焦"形状 / 加载 / 触发"，R3 已覆盖"评估指标"——本文 §0.4 与 §5.4 仅引用 R3 §0 / §3 / §5.4 结论而不重做
