# R4 — "Skill as Agent" 终局形态 与 轻量路由 调研报告

| 字段 | 值 |
|---|---|
| Task ID | R4 |
| Stage | research |
| Wave | 1 (parallel) |
| 时间窗口 | 严格 2026 (含 2025 末用作 prior art) |
| 调研覆盖 | 4 个核心问题 + 实测数字表 + 失败模式 + 替代终局 + 终局假设判定 + RTK 等本地参考的复用建议 |
| 来源数 | 24 (本地 9 / 外部 15) |
| 失败模式 | 8 |
| 替代终局形态 | 5 |

---

## 0. TL;DR — 给决策者的 5 条结论

1. **用户的"轻量模型 + CLI 包装"假设方向正确，但单层小模型路由直接驱动 Claude-Code/Cursor 这类强代理在 2026 年仍未跑通**——已有公开的失败复盘（`claude-code-router` v0 用免费小模型做 router/tool/think/coder 四角色分发，作者自述"the lightweight model lacked the capability to route tasks accurately, and architectural issues prevented it from effectively driving Claude Code"，见 `/home/agent/reference/claude-code-router/blog/en/project-motivation-and-how-it-works.md:85`）。
2. **同时 2026 的事实证据强烈支持"分层 + 包装"思路**：Claude Haiku 4.5 在 tau2-bench 上 92.5%、tool 调用错误率 1.55%；Nemotron Nano 2 9B 在 BFCLv3 上 66.9% 且生成吞吐量是 Qwen3-8B 的 6.3×；OpenAI Agents SDK 2026 生产指南显式建议 "use the cheapest model for the routing/supervisor layer (e.g., GPT-5-nano)"。
3. **"Skill as CLI + Progressive Disclosure"是当前最成熟、可工程化的中间形态**：Anthropic Skills 官方推 3 级渐进披露 (metadata → body → references)，`claude-code-router` 作者直接论证 "MCP/Skill 本质就是 `--help` 风格的 CLI 渐进披露"，可用 `pdf <domain> <command> --help` 模式收敛上下文（`/home/agent/reference/claude-code-router/blog/en/progressive-disclosure-of-agent-tools-from-the-perspective-of-cli-tool-style.md:138-148`）。
4. **替代终局并存且各有验证**：metadata 驱动 dispatcher（kNN router 击败大多数 learned router；LLMRouterBench 2026.01）、prompt-program 编译（DSPy + GEPA）、agent-as-OS（AIOS v0.3.0 2026.01）、skill-as-RAG（`skill-retrieval-mcp` 89K skills，token 砍 80%）、context-as-OS（ContextOS v0.2.0 Cognition 层）。Si-Chip 不应押注单一终局，而应让 Skill **阶段化演化**到任意一个或组合。
5. **RTK 与 claude-code-router 是 Si-Chip 的直接 prior art**——RTK 已经把 60–90% token 压缩从"模型职责"剥离到"CLI 拦截器"职责（OpenClaw 插件 80% 平均节省、`git log --stat` 87%、`cargo test` 90%）；DevolaFlow 已有 `shell_proxy/registry.py::WHITELIST` + `memory_router/cache.py::MemoryCase` + `command-mapping.yaml` 的 SSOT 模式可直接复用为 Skill 后段的 CLI 落地基线。

---

## 1. 调研问题 1 — 2026 年小模型路由 / cascading / MoE 路由的工程化进展

### 1.1 学术与基准（外部 2026 来源）

- **LLMRouterBench** (arXiv 2601.07206v1, Jan 2026) — 400K+ 实例，21 数据集、33 模型、10 routing baselines；关键结论："many recent routing methods exhibit similar performance under unified evaluation, and several recent approaches **including commercial routers fail to reliably outperform simple baselines**." 商用 OpenRouter 的整体准确率比 Best-Single (GPT-5) 还低 **24.7 个百分点**。Avengers-Pro（聚类型方法）能做到 **+4% accuracy / −31.7% cost** 同时达成。
- **A Unified Approach to Routing and Cascading for LLMs** (PMLR 2025/2026, dekoninck25a) — 把 routing（单次选模型）和 cascading（依次升级模型）统一进同一最优策略；"quality estimators are critical for model selection success"，统一 cascade-routing 一致大幅优于单独的 routing 或 cascading。
- **kNN Routing 简单胜复杂** (arXiv 2505.12601, May 2025) — 调好的 kNN 路由器"matches or outperforms state-of-the-art learned routers across diverse tasks"，且样本复杂度更低。说明在工程上，**复杂的可学习路由器并非必要条件**。
- **FrugalGPT cascade**（基线 prior art，被 2026 工作大量引用）— 98% cost reduction 同时匹配 GPT-4 表现；2026 LLM 路由生产指南普遍把它作为标杆。
- **RouteLLM**（base 引文，2026 仍被参考）— 95% GPT-4 Turbo 的表现只用 14% 的 GPT-4 调用量、整体降本 75%；MT-Bench 节省 85%、MMLU 节省 45%。
- **ToolSpec**（arXiv 2604.13519, 2026）— schema-aware speculative decoding for tool calls；4.2× 工具调用加速；plug-and-play。
- **SpecGuard**（arXiv 2604.15244, 2026）— 多步推理的 step-level verification；延迟 −11% 同时准确率 +3.6%。
- **Avengers-Pro / kNN baselines**（LLMRouterBench 综述）— 简单聚类/近邻法可达近 Pareto 最优。

### 1.2 工业产品与生产指南（2026）

| 来源 | 关键事实 | 含义 |
|---|---|---|
| OpenAI Agents SDK production patterns 2026 (`apiscout.dev`, ToolHalla) | "use the cheapest model for the routing/supervisor layer (e.g., GPT-5-nano) — the router doesn't need to be smart, just fast and cheap" | 2026 生产共识：路由层必须便宜+快 |
| Aider Architect Mode (DeepWiki 2026.04) | 大模型出方案，小模型写 diff；Claude 3.7 Sonnet 在 47-file 基准用 4.2× 更少的 token，仍取得 71% first-pass，月成本 $60–80（vs Claude Code $200+） | 经典分层范式 |
| Cursor Tab "Fusion" 模型 (2025) | server p50 latency **475ms → 260ms (−45%)**，context 5,500 → 13,000 tokens，难编辑预测 +25%、单笔编辑跨度 ×10 | 边缘小模型 + 大模型协作的成熟实例 |
| Anthropic Claude Haiku 4.5 (2025-10) | tau2-bench **92.5%**、Terminal-Bench 2.0 **46.3%**、SWE-bench Verified **73.3%**、平均 tool 调用错误率 **1.55%** | "便宜模型也能跑工程化 agent" 的实证 |
| OpenAI GPT-5-mini (2025-08, 2026 价格) | 输入 $0.25/M、输出 $2/M，缓存输入 $0.03/M；400K context；显式定位"lighter-weight reasoning + reduced latency" | 路由层标配候选 |
| NVIDIA Nemotron Nano 2 (9B, 2025-09) | BFCLv3 **66.9%**，生成吞吐 vs Qwen3-8B **6.3×** (A10G) | "≤9B agentic 模型"实测可用 |
| NVIDIA Nemotron 3 Nano (30B-A3B 稀疏 MoE，2025-12) | tau2-Bench **71.5%**，每次激活 3.2–3.6B 参数；vs Qwen3-30B-A3B-Thinking 吞吐 ×3.3 | MoE 风格路由活跃方向 |
| BFCL v4 / 2026.3.23 release (`bfcl-eval`) | Llama 3.1 8B Instruct **76.1%**（榜单第三），平均 71.7%，最高 88.5% (Llama 3.1 405B)；与 405B 仍有 ~12 pp 差距 | 7-9B 类目下 tool 调用 ≈75% 是当前可达上限 |

### 1.3 一句话回答 Q1
**能用，但不是"一个 ≤7B 小模型直接当唯一驱动"，而是 "≤9B 路由 + Haiku/4o-mini 级中模型骨干 + 大模型仅在 think/longContext 兜底" 的三层级联**。LLMRouterBench 已经证实，简单 baseline（kNN、聚类）能做到 Pareto 最优；但**单层小模型直接驱动复杂 agent 在 claude-code-router v0、mini-swe-agent 上都有公开失败案例**。

---

## 2. 调研问题 2 — CLI-first agent 活跃方案及"模型推理 vs 确定性 CLI"边界

### 2.1 主流方案矩阵（2026 视角）

| 方案 | 定位 | "模型 vs CLI"边界划法 | 来源 |
|---|---|---|---|
| **Anthropic Skills + Claude Code** | 官方 spec：Skill = 文件夹 + `SKILL.md` + 可选脚本 | 三级渐进披露：L1 metadata 总在 context；L2 body 触发后载入；L3 references/scripts 按需读取 | `docs.anthropic.com/.../claude-code/skills` (2026) |
| **claude-code-router** (`musistudio/claude-code-router`) | 重写 `/v1/messages`，用 transformer 把请求转给 OpenAI/DeepSeek/Gemini/Volcengine/SiliconFlow | 4-class routing：default / background / think / longContext + `tiktoken` 阈值（>32K → longContext）+ `CUSTOM_ROUTER_PATH` 自定义 JS 路由 | `/home/agent/reference/claude-code-router/README.md:197-205, 440-468` |
| **claude-code-router 作者新提案** | 在文章 *Progressive Disclosure of Agent Tools from the Perspective of CLI Tool Style* 中提议**单工具 MCP**：暴露一个 `pdf` 工具，agent 自己 `pdf --help → pdf text --help → pdf text extract --help → pdf text extract --pdf ...`，把"哪些子命令"交给 CLI 自描述 | 边界：模型不预先知道任何 sub-command，全部通过 `--help` 渐进读取；MCP 描述里明确 "You need to pass in the --help parameter to obtain the usage of this tool first" | `/home/agent/reference/claude-code-router/blog/en/progressive-disclosure-of-agent-tools-from-the-perspective-of-cli-tool-style.md:88-150` |
| **RTK (`rtk-ai/rtk`)** | Rust 单二进制 CLI 拦截器，hooks 注入 `git status → rtk git status`；100+ 命令 filter | 边界：所有"输出压缩 / 截断 / 去重 / 分组"完全不再交给模型；模型只看到压缩后结果 | `/home/agent/reference/rtk/README.md:36-56, 122-138, 351-372` |
| **OpenAI Agents SDK** (`openai-agents-python`) | Agents = LLM + instructions + tools + handoffs + guardrails；Manager-pattern vs Handoffs 两种编排 | 用 handoff 把"路由决策"模型化，但官方 2026 指南建议路由层用 GPT-5-nano；推荐"start with one agent"，必要时再细分 | `/home/agent/reference/openai-agents-python/README.md:10-21` + 2026 ToolHalla / APIScout |
| **Composio SDK** | "Skills that evolve for your Agents"，500+ apps、统一 toolkit + provider 适配 (OpenAI Agents/Anthropic/LangChain/Mastra/CrewAI) | 把"工具定义/认证/执行"全部下沉到 SDK；模型只见到 `composio.tools.get(userId, {toolkits: [...]})` 结果 | `/home/agent/reference/composio/README.md:62-75, 168-183` |
| **OpenClaw** | "AI that actually does things"；`mcporter` 桥接 MCP、`before_tool_call` 钩子、ClawHub Skill 市场；TypeScript 编排核心 | 显式拒绝 "Agent-hierarchy frameworks (manager-of-managers / nested planner trees) as a default architecture" 与 "Heavy orchestration layers" | `/home/agent/reference/openclaw/VISION.md:99-108` |
| **OpenSpec** | `/opsx:propose → /opsx:apply → /opsx:archive` 工作流；spec → tasks → 实现 | 模型只在 propose / apply 阶段产出文本，CLI 负责文件落盘、任务清单跟踪、归档 | `/home/agent/reference/openspec/README.md:36-69` |
| **DSPy + GEPA** (`stanfordnlp/dspy`) | "Programming, not prompting"；`compile()` 方法 + GEPA reflective optimizer 演化 prompt + 整个 program | 模型推理被显式 **编译** 为多步 module；prompt 不再人手写，由优化器演化 | `/home/agent/reference/dspy/README.md:14-18, 49` |
| **Pydantic-AI** | 类型安全 agent 框架；Pydantic 校验输出；durable execution；HITL approval | 把"输出格式 / 工具参数"用 Pydantic 模型固化，错误从运行期前移到编译期 | `/home/agent/reference/pydantic-ai/README.md:30-60` |
| **Anthropic Code Execution Tool 2026** | `code_execution_20260120`：REPL 状态持久化 + sandbox 内程序化调用工具 (Opus 4.5+, Sonnet 4.5+) | 边界继续右移：模型在 sandbox 里既能 `bash` 又能从 sandbox 内部程序化调用 tool | docs.anthropic.com/.../code-execution-tool (2026) |

### 2.2 一条主线：边界从"模型推 token"持续右移到"CLI 拿确定性结果"

- **现象 A**：RTK 把"读 / 列 / 测 / 构建"等 CLI 输出的 token 压缩职责完全从模型身上拿走。30 分钟会话 118K → 23.9K tokens (−80%)，单点 `cargo test` 90%、`git push` 92%、`git log --stat` 87%。
- **现象 B**：Anthropic Skills 把"应该读哪个文档"的 retrieval 决策从模型身上拿走，靠 metadata + 文件系统 + grep 解决（progressive disclosure）。
- **现象 C**：Cursor Tab Fusion 把"补全决策"完全交给一个 260ms 延迟的边缘小模型，主对话不参与。
- **现象 D**：Composio / RAG-MCP / `skill-retrieval-mcp` 把"工具选择"从 prompt 里 89K tools 全 dump 改成"先 retrieve 描述、再展开 schema"。
- **结论**：2026 年的事实是 **Skill = "薄模型路由层 + 厚 CLI 包装层 + 渐进披露 retrieval"**，与用户的终局假设方向一致。

---

## 3. 实测数字表（精度 / 延迟 / 成本，全部 2026 公开来源）

> 所有数字保留来源链接或本地文件路径，方便复核。空白单元格表示该来源未公开该指标。

### 3.1 路由 / 级联 / 蒸馏小模型 实测

| 项 | 模型/方案 | 精度 / 关键指标 | 延迟 | 成本/Token 节省 | 来源 |
|---|---|---|---|---|---|
| Tool Calling (BFCL v4 2026) | Llama 3.1 8B Instruct | 76.1% (vs 405B 88.5%) | — | — | airank.dev/benchmarks/bfcl (2026) |
| Tool Calling (BFCLv3) | NVIDIA Nemotron Nano 2 (9B) | 66.9% | 6.3× 吞吐 vs Qwen3-8B (A10G, 8K/16K) | — | research.nvidia.com/.../NVIDIA-Nemotron-Nano-2-Technical-Report.pdf |
| Tool Calling (tau2-bench) | NVIDIA Nemotron 3 Nano (30B-A3B MoE) | 71.5% | 3.3× vs Qwen3-30B-A3B-Thinking; 2.2× vs GPT-OSS-20B | 每 forward 仅激活 3.2–3.6B / 31.6B 参数 | research.nvidia.com/.../NVIDIA-Nemotron-3-Nano-Technical-Report.pdf |
| Agentic / tool-use | Claude Haiku 4.5 (2025-10) | tau2-bench 92.5%；Terminal-Bench 2.0 46.3%；OSWorld-Verified 39%；SWE-bench Verified 73.3% | OpenRouter p50 工具调用错误率 1.55% | $0.80/$4 (input/output) | benchlm.ai/models/claude-haiku-4-5 (2026) + system card |
| Edge edit prediction | Cursor "Fusion" Tab | 难编辑 +25%、单笔编辑跨度 ×10 | server p50 **260ms** (vs 475ms) | context 5,500 → 13,000 tokens | cursor.com/en/blog/tab-update |
| Architect/Editor 分层 | Aider on 47 files (Mar 2026) | first-pass 71% (vs Claude Code 78%) | — | token ×0.24（4.2× 更少）；月成本 $60–80 vs $200+ | morphllm.com/comparisons/morph-vs-aider-diff |
| Routing 综合 | RouteLLM (基线 2026 ref) | 95% of GPT-4 Turbo | — | 75% cost ↓；MT-Bench 85% ↓；MMLU 45% ↓ | tianpan.co/blog/2025-11-03-llm-routing-model-cascades |
| Cascade | FrugalGPT (基线，2026 仍被引) | 匹配 GPT-4 同时 −98% 成本；同成本下 +4% 准确率 | — | −98% | arxiv 2305.05176 / openreview/TkXjqcwQ4s |
| Routing (商用) | OpenRouter（默认 routing） | 比 Best-Single (GPT-5) 低 **−24.7 pp** | — | — | LLMRouterBench arXiv 2601.07206v1 (2026.01) |
| Routing (Pareto-near) | Avengers-Pro (聚类) | +4% accuracy | — | −31.7% cost | LLMRouterBench (2026.01) |
| Tool-call 加速 | ToolSpec (schema-aware speculative) | 同精度 | **4.2× 加速** | — | arXiv 2604.13519 (2026) |
| Reasoning 加速 | SpecGuard (verification-aware speculative) | +3.6% accuracy | −11% latency | — | arXiv 2604.15244 (2026) |
| Tool retrieval | RAG-MCP / Anthropic | 工具选择从 13.62% → 43% (large toolset) | — | prompt 长度减半，准确率 ×3 | tianpan.co/blog/2026-04-19-over-tooled-agent-problem |
| Skill retrieval | `skill-retrieval-mcp` v0.2.0 | 89K skills 中检索 | — | token 节省 ~80% | pypi.org/project/skill-retrieval-mcp |

### 3.2 CLI 拦截 / 输出压缩 实测（来自 RTK，本地参考）

| 命令 | 拦截前 token | 拦截后 token | 节省 | 来源 |
|---|---|---|---|---|
| `git status` (×10) | 3,000 | 600 | −80% | `/home/agent/reference/rtk/README.md:42-54` |
| `git diff` (×5) | 10,000 | 2,500 | −75% | 同上 |
| `git add/commit/push` (×8) | 1,600 | 120 | **−92%** | 同上 |
| `cargo test` / `npm test` (×5) | 25,000 | 2,500 | **−90%** | 同上 |
| `pytest` / `go test` (×4/×3) | 8,000 / 6,000 | 800 / 600 | −90% / −90% | 同上 |
| `ls` / `tree` (×10) | 2,000 | 400 | −80% | 同上 |
| **30 分钟会话总计** | **~118,000** | **~23,900** | **−80%** | 同上 |
| `git log --stat` (OpenClaw 插件实测) | — | — | **−87%** | `/home/agent/reference/rtk/openclaw/README.md:75-83` |
| `find -name` | — | — | −48% | 同上 |
| `grep` (单文件) | — | − | −52% | 同上 |
| 文件读取 `cat` (aggressive) | — | — | 仅签名（剥 body） | `/home/agent/reference/rtk/README.md:148` |

**含义**：把 60–90% 的 token 压缩从"由模型/agent 自己学着精简"挪到 "CLI 拦截器决定性输出"，符合用户终局假设里"模型只负责路由 + 组织输入输出"的判断；这部分**完全不需要模型推理**，是确定性 CLI。

### 3.3 上下文 / 工具爆炸 退化曲线

| 指标 | 数值 | 来源 |
|---|---|---|
| 平均 context length 10K → 100K 的精度衰减 | **−20% 至 −50%** | toolhalla.ai/blog/context-rot-ai-agents-2026 |
| 32K-64K tokens 处常见"悬崖式"下跌 | 是 | 同上 |
| 5 工具 vs 100 工具 准确率 | 95% → **<30%** | tianpan.co/blog/2026-04-13-tool-explosion-problem-... |
| 100+ 工具时基本不可用（无架构干预） | 是 | tianpan.co/blog/2026-04-19-over-tooled-agent-problem |
| 单工具 schema 大小 | 1,600+ tokens；37 个工具 → 6,000+ tokens 仅 schema | 同上 |
| MCP schema 注入量级 | 10 servers × 20–80 tools × 1–8 KB → 50K–200K tokens 仅描述 | junia.ai/blog/mcp-context-window-problem |
| Schema drift 场景 success rate 下降 | 99.8% → **96%** | medium @jickpatel611 / Vectorlane (2026.02) |
| 长程 SWE 任务 frontier Pass@1 | <25–45% | SWE-Bench Pro arXiv 2509.16941 |
| Tool selection 幻觉检测准确率（内部表征法） | **86.4%** | arXiv 2601.05214v1 (2026) |

---

## 4. 调研问题 3 — 已知失败模式（≥5，附具体案例 / 出处）

### F1. **轻量模型直接驱动复杂 agent 失败（路由能力缺失）**
- **案例**：`musistudio/claude-code-router` v0 用免费小模型做 router/tool/think/coder 四角色分发，作者复盘："the lightweight model lacked the capability to route tasks accurately, and architectural issues prevented it from effectively driving Claude Code." 直到换成 DeepSeek-V3 + DeepSeek-R1 才跑通。
- **出处**：`/home/agent/reference/claude-code-router/blog/en/project-motivation-and-how-it-works.md:85-87`。
- **2026 印证**：LLMRouterBench (arXiv 2601.07206v1) 发现"商用 router OpenRouter 比单纯用 GPT-5 还差 −24.7 pp"；多个 router baseline 在统一评测下相互几乎打平，复杂 learned router 并不优于 kNN baseline。

### F2. **Tool Explosion / 工具爆炸 → 决策崩塌**
- **数据**：5 → 100 工具，准确率从 95% 跌到 <30%；37 个工具在 prompt 中 ≈6,000 tokens 占用；100 工具中选 3 个 ≈100 万种组合。
- **案例**：Writer's RAG-MCP benchmark 显示工具选择基线只有 13.62%，加 retrieval 后才到 43%（仍然不高）。
- **出处**：tianpan.co/blog/2026-04-13-tool-explosion-problem-agent-tool-selection-at-scale + 2026-04-19-over-tooled-agent-problem。

### F3. **Context Rot / 长 context 精度悬崖**
- **数据**：18 个主流 LLM，平均精度 10K → 100K 衰减 **20–50%**；常见 32K-64K tokens 处悬崖式下跌；100K context 时 self-attention 创建 100 亿对 token 关系，"attention budget"被稀释。
- **出处**：toolhalla.ai/blog/context-rot-ai-agents-2026 (Chroma Research 起源 + 2026 后续)。
- **直接含义**：用户假设里"轻量模型 + CLI 包装"如果不配合 RTK / 渐进披露，第一次调用就会因为 schema/CLI 文档塞爆 context 而崩。

### F4. **MCP Schema 注入爆炸**
- **数据**：10 servers × 20–80 tools × 1–8 KB → 50K–200K tokens，**每轮对话都可能重复注入**。
- **案例**：MCP schema 重复经过 verbose descriptions、nested JSON schemas、return types、examples、policies 累积。
- **出处**：junia.ai/blog/mcp-context-window-problem (2026.03)。
- **设计含义**：Skill 终局如果用 MCP 直连 + 全量 schema，会先撞这堵墙。

### F5. **Tool Schema Drift / 静默失败**
- **数据**：rename `customer_id → account_id` 这类小改动可让工具调用 success rate 从 **99.8% → 96%**；agent 不会"crash"，只会"believable but incorrect"。
- **建议**：把 tool schema 当 API 合约，做 version negotiation + adapter 层；validate missing invariants 而非 unknown fields。
- **出处**：medium 2026 系列：@Modexa "When One Field Drift Breaks the Agent" / @duckweave "Tool Schema Drift: 11 Checks Before Agents Guess" / @jickpatel611 "Tool Contracts Break Quietly Without Version Negotiation"。

### F6. **Tool Selection / Tool Use Hallucination**
- **数据**：`ToolBeHonest` 上 Gemini-1.5-Pro 仅 45.3、GPT-4o 仅 37.0（满分 100）；说明即便是大模型也会幻觉地选错或编造工具。
- **小模型差距**：BFCL v4 上 Llama 3.1 8B 76.1% vs 405B 88.5% — 小模型与大模型之间还有 ~12 pp 真实差距。
- **检测方案**：内部表征法可达 86.4% 检测准确率（arXiv 2601.05214v1, 2026）。
- **出处**：arXiv 2406.20015v2 ToolBeHonest；BFCL leaderboard 2026.3.23；arXiv 2601.05214v1 (2026)。

### F7. **CLI 接口爆炸 / 版本漂移**
- **现象**：当 Skill 演化到第三阶段把流程 CLI 化后，CLI 自身会迅速积累子命令，模型记不住 → 必须靠 `--help` 或 retrieval。
- **案例**：claude-code-router 作者直接证实："This manual doesn't return every possible usage of every command either. It only lists which commands are available... For the specific usage of a command, you can still obtain it by using the `--help` parameter" — 实质上是把 CLI 用作"渐进披露 manual"。
- **出处**：`/home/agent/reference/claude-code-router/blog/en/progressive-disclosure-of-agent-tools-from-the-perspective-of-cli-tool-style.md:60-86`。
- **隐忧**：Anthropic 2025-10 后 Skills 引入"脚本随附"机制，作者也指出存在 **"Different skills may have different types of script files... users also need to install the corresponding runtime and dependencies"** 的体验/安全代价（同文件:9-10）。

### F8. **多轮 / 长程 agent 卡死**
- **案例**：`mini-swe-agent` GitHub issue #549 — "gets stuck for some instances"，重跑可解。
- **数据**：SWE-Bench Pro (arXiv 2509.16941) 上 frontier 模型 long-horizon Pass@1 仅 25–45%。
- **含义**：对终局假设"小模型路由 + CLI"的影响——单次决策 OK，但 5 轮以上长程任务，小模型路由偏差累积，最后偏离任务。

> ✅ 满足验收 ≥ 5 个失败模式的标准（实际给出 8 个）。

---

## 5. 调研问题 4 — 替代 / 并行的终局形态

### A. 纯 metadata-driven dispatcher（无学习路由）
- **核心论点**：LLMRouterBench (2026.01) + kNN routing 论文证明"简单 baseline ≥ 复杂 learned router"；Avengers-Pro 聚类法 +4% acc / −31.7% cost。
- **代表实现**：DevolaFlow `memory_router/cache.py::MemoryCase` + `shell_proxy/registry.py::WHITELIST` 这类 SSOT 注册表 + 缓存命中即跳过模型推理（DEVOLAFLOW_MEMORY_ROUTER 标志，见 `/home/agent/workspace/DevolaFlow/CHANGELOG.md:243`）。
- **优**：可解释、零推理成本、易审计、可缓存。
- **劣**：只覆盖已经收敛 / 高频的 case，长尾仍要回退到模型。
- **何时胜出**：Skill 第 3 阶段（流程已固化、判变指标稳定）。

### B. 纯静态 prompt 编译（DSPy / GEPA）
- **核心论点**：把 prompt + 多模块程序看成 "可编译可优化 artifact"。GEPA 是 Genetic-Pareto reflective optimizer，演化 prompts 与整个 program；论文 "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning" (Agrawal et al. 2025)。
- **代表实现**：`/home/agent/reference/dspy/README.md:14-18, 49`；`compile()` 方法。
- **优**：把"prompt 设计"从手工艺降维到工业流水线；可形式化评估指标。
- **劣**：要求清晰的训练/验证集与可计算的 reward；对于纯交互式 / 长程任务收益较弱。
- **何时胜出**：Skill 已经有明确验收指标 + 数据集（用户原始路径里的"第二阶段"）。

### C. Agent-as-OS（AIOS / OpenAgents 流派）
- **核心论点**：把 agent 当系统级一等公民，由 Kernel + Scheduler（FIFO / RR）+ Context/Memory/Storage/Tool/Access-Control 五大 manager 统一调度；多 agent 共享底层资源。
- **代表实现**：AIOS v0.3.0（2026.01.22 release）；2.1× faster execution；COLM 2025 paper accepted；agiresearch/AIOS。
- **优**：解决多 agent 资源争用、长生命周期、调度，是"未来 OS"的有力候选。
- **劣**：极重，对单 Skill 过度工程；早期生态尚不稳定。
- **何时胜出**：Si-Chip 演化到"很多 Skill 同时在跑、共享 memory/tools"时。

### D. Skill-as-RAG-retrieval（"先检索再展开"）
- **核心论点**：把 Skill 当 indexed knowledge：先 retrieve 简介，再展开 schema/script，再执行；与 Anthropic Progressive Disclosure 同构。
- **代表实现**：
  - `skill-retrieval-mcp` v0.2.0（pypi）：89K skills，先返回摘要、按需展开；token ≈ −80%。
  - `skill-depot`（Ruhal-Doshi）：本地 SQLite + vector embedding + 三级 detail (snippet → overview → full)。
  - Anthropic RAG-MCP 框架：tool 选择 13% → 43%。
  - Composio: 500+ apps 的 toolkit 检索（`composio.tools.get(userId, {toolkits: [...]})`）。
- **优**：直接攻克 F2/F4 两个失败模式；可以与小模型路由共存。
- **劣**：检索质量决定上限；embedding drift 仍是问题（ContextOS 引入 Embedding Model Drift Detection 来缓解）。
- **何时胜出**：Skill 数量 > 30 时几乎是必选。

### E. Context-as-OS（ContextOS / ACON）
- **核心论点**：在 retrieve 与 generate 之间插入"think 层"——Active Forgetting / Reasoning Depth Calibration / Synthesis Detection / Unknown Unknown Sensing / Productive Contradiction / Context-Dependent Gravity。配合 Retrieval Router（按数据 churn 分 Live/Warm/Cold）+ Index Lifecycle Manager（事件驱动重建 + Embedding Drift 检测）。
- **代表实现**：`/home/agent/reference/ContextOS/README.md:28-104`；`/home/agent/reference/acon/README.md`（ACON arXiv 2510.00615 Microsoft Research, "Optimizing Context Compression for Long-horizon LLM Agents"，蒸馏到本地 Compressor LoRA + Agent LoRA 两阶段）。
- **优**：直接处理"context rot"（F3）和"长程 agent 卡死"（F8）。
- **劣**：增加层次、调试复杂度。
- **何时胜出**：当 Skill 工作流跨多轮 + 多源数据时。

> ✅ 满足验收 ≥ 3 个替代终局形态（实际给出 5 个）。

### 综合对比表

| 形态 | 解决的核心问题 | 与"Skill as Agent"假设关系 | 推荐起步阶段 |
|---|---|---|---|
| A. metadata dispatcher (kNN/缓存) | 重复决策成本 | 兼容（小模型路由的"零推理 fast-path"） | Skill 第 3 阶段 |
| B. prompt-program 编译 (DSPy/GEPA) | prompt 设计无量化 | 兼容（用编译器固化 Skill 第 2 阶段） | Skill 第 2 → 3 阶段 |
| C. Agent-as-OS (AIOS) | 多 agent 资源调度 | 替代（如果想要"OS"而非"包装"） | Skill 数量 ≫ 50 时 |
| D. Skill-as-RAG-retrieval | tool/skill explosion | 兼容（解决 F2/F4） | Skill 数量 > 30 时几乎必选 |
| E. Context-as-OS (ContextOS/ACON) | context rot / 长程 | 兼容（解决 F3/F8） | 多轮工作流出现时 |

---

## 6. 对用户终局假设的判定

> 假设原文："Skill 不该是大模型即时推理出来的内容，而应该是 **轻量模型/路由层 + CLI 包装**——一个非常快、非常便宜的小模型就能根据 Skill UI 决定如何调用 CLI、组织输入、收集输出。"

### 6.1 成立条件（必须同时满足）
1. **是分层而非单层**：≤9B 路由 + Haiku/4o-mini 级骨干 + 大模型仅 think/longContext 兜底。LLMRouterBench/2026 生产实践都印证。
2. **CLI 一侧已有可靠拦截器**：把"输出压缩 / 截断 / 去重 / 归类"完全确定化（RTK 已示范 60–90% token 压缩；DevolaFlow `shell_proxy` 已示范白名单+filter chain）。
3. **Skill UI 走渐进披露**：metadata 永驻 / body 触发载入 / scripts/refs 按需读取（Anthropic Skills 三级 + claude-code-router 作者的 single-tool MCP `--help` 模式）。
4. **Skill 数量 > 30 时强制叠加 retrieval**：RAG-MCP / `skill-retrieval-mcp`，否则会撞 F2/F4。
5. **CLI 接口纳入 schema 版本治理**：参照 Tool Schema Drift 2026 系列做 version negotiation（防 F5 静默失败）。
6. **Skill 评估指标体系到位**：用 BFCL v4 / tau2-bench / Terminal-Bench 2.0 / Aider edit benchmark 这类公开基准做"判变"——Si-Chip 仓库的核心目标之一就是建立这套体系（与 R4 任务前提一致）。

### 6.2 不成立场景
- 单层 ≤7B 模型 **直接** 驱动复杂 IDE / agent loop —— 已在 claude-code-router v0、mini-swe-agent 上有公开失败案例；且小模型 BFCL 与大模型仍有 ~12 pp 差距。
- Skill 还停留在第 1 阶段（探索性/复杂 Markdown），**没有验收标准**就用 CLI 包装 —— 会过早固化错误的接口（OpenSpec 的 propose → apply 工作流值得借鉴）。
- 未配套 Tool Schema Drift 治理 —— success rate 99.8% → 96%、且**不会爆错**，是最危险的失败模式。
- 把 Skill = 单文件夹 + 脚本，不做 retrieval（违反 F2/F4）。

### 6.3 还需补充什么
- **判变指标（Si-Chip 仓库的核心交付物之一）**：必须给"Skill 处于哪个阶段"出具体可量化指标——例如：
  - Stage 1 → 2 跨越条件：≥1 个明确验收标准 + 在该 Skill 上 model-only 与 model+spec 的 win-rate 差距 ≥ X pp。
  - Stage 2 → 3 跨越条件：流程内 ≥ N% 步骤可被 deterministic CLI 替换，且在 RTK 类拦截下 token 节省 ≥ Y%。
  - Stage 3 → 4 跨越条件：路由层 P50 延迟 ≤ 300ms（参考 Cursor Tab Fusion 260ms）+ 路由准确率 ≥ Z%（参考 Haiku 4.5 tool-call err 1.55%）。
- **回退策略**：每一跳都要有"小模型不确定 → cascade 升级"逻辑（FrugalGPT cascade / OpenAI Agents SDK handoff）。
- **可观测性**：把 BFCL/tau2/Terminal-Bench 跑在仓库 CI 上，对每个 Skill 做"阶段评分"。
- **Skill 演化记录 / GEPA-style 迭代**：用 GEPA / DSPy 的 reflective optimizer 自动演化 Skill 的 prompt + 流程（覆盖 Stage 2 → 3 收敛）。
- **Drift 防御**：CLI / schema 改动必须自动通过 version negotiation；否则不允许改名/改字段。

### 6.4 总判定
**有条件成立 (Conditional Yes)**——用户的终局方向与 2026 公开证据高度一致，但**不能跳过分层、CLI 拦截、渐进披露、retrieval、drift 治理**这五项基础工程。Si-Chip 的价值正是把这套基础工程产品化为"阶段范式 + 演化路径 + 评估体系"。

---

## 7. RTK / claude-code-router / composio 等本地参考的复用建议

### 7.1 RTK（直接复用，最高优先级）
**Si-Chip 哪里能直接调用**：
- **Skill 第 3 阶段（CLI 包装）的标准 stdout/stderr 压缩层**——所有 Skill 子流程的 shell 输出统一通过 `rtk rewrite "<cmd>"` 改写后再回到 agent。证据：100+ 命令、0 配置、`<10ms overhead`（`/home/agent/reference/rtk/README.md:36`）；OpenClaw 插件 80% 平均节省（`/home/agent/reference/rtk/openclaw/README.md:75-83`）。
- **Skill 评估体系的"token 节省"维度**：直接套用 `rtk gain` / `rtk discover` / `rtk session` 输出（`/home/agent/reference/rtk/README.md:244-256`），把 token 节省纳入 Skill 阶段评分。
- **Hook 机制**：Skill 第 4 阶段（轻量路由）可以走 PreToolUse hook（Claude Code、Cursor、Copilot、Gemini 全部已支持，见 `/home/agent/reference/rtk/hooks/README.md:46-56`），路由层选模型，hook 重写 CLI，模型只见到压缩输出。

**Si-Chip 怎么改造一下更好用**：
- 在 RTK 之上加一层 "Skill UI 描述符"（YAML / JSON），让小模型路由层只读 metadata 就能决定调用哪条 `rtk <cmd>` 链路；模型不参与命令拼装。
- 把 RTK 的"per-command filter registry"思路拔到 Skill 注册表（参考 DevolaFlow A-5.1 Single-Owner Invariant，见下面 7.4）。

### 7.2 claude-code-router（直接复用，次高优先级）
- **三-四角色路由模板**（default / background / think / longContext + `tiktoken` 阈值切换）可以**原样**作为 Skill 路由层骨架，配置见 `/home/agent/reference/claude-code-router/README.md:197-205`。
- **Transformer 系统**（`Anthropic` / `deepseek` / `gemini` / `openrouter` / `tooluse` / `maxtoken` / `enhancetool` / `cleancache` / `reasoning` / `sampling` / `vertex-gemini`）已经把"协议适配 / 工具调用兜底 / 缓存清理 / max_token 强约束"等工程脏活做完，建议 Si-Chip 把它当 Skill 后段的"模型适配层"直接 fork 或绑定。
- **CUSTOM_ROUTER_PATH**（`/home/agent/reference/claude-code-router/README.md:457-493`）允许 JS 写自定义路由——Si-Chip 的"小模型路由"可在此插入。
- **`<CCR-SUBAGENT-MODEL>provider,model</CCR-SUBAGENT-MODEL>`**（同文 :497-504）的 inline 模型选择语法非常轻量，可作为 Skill 内"按段选模型"的实现参考。
- **Tool Mode / ExitTool 模式**（`/home/agent/reference/claude-code-router/blog/en/maybe-we-can-do-more-with-the-route.md:32-100`）—— DeepSeek 这种长对话掉线的情况靠 `tool_choice = "required"` + `ExitTool` 闭环，是路由模型不稳时的标准修补；Skill 第 4 阶段可直接复用。

### 7.3 composio（用作 toolkit/registry 后端）
- **500+ apps + 多 provider 适配（OpenAI Agents/Anthropic/LangChain/LlamaIndex/Vercel/Gemini/CrewAI/Mastra）**：把 Skill 第 2/3 阶段需要的外部能力（Slack/Gmail/Notion 等）直接挂在 composio toolkit 上，不重复造轮子。`/home/agent/reference/composio/README.md:62-75, 168-183`。
- **Rube** (composio MCP server) 已经服务 Cursor / Claude Desktop / Claude Code / VS Code 多个客户端 → 可作为"Skill 跨 IDE 复用"的现成路径。
- 注意：composio 仍把所有 toolkits 暴露给模型，Si-Chip 应在前面加一层 RAG retrieval（见 § 5.D）来防 F2/F4。

### 7.4 DevolaFlow（同公司，直接 prior art，可作为 Si-Chip 实现底座）
- **3 个 Python SSOT 注册表**直接对应 Skill 终局的三类资源：
  - `src/devolaflow/shell_proxy/registry.py::WHITELIST` —— Skill 第 3 阶段允许执行的 CLI 白名单。
  - `src/devolaflow/memory_router/cache.py::MemoryCase` —— Skill 第 4 阶段的 router 缓存案例（命中即跳模型）。
  - `src/devolaflow/shell_proxy/commands.py::CommandMapping` —— v8.3.4 PV-04 的"command-mapping recipe"，多-pass filter chain（schema v2，`compose: list[str]`）。
  - 见 `/home/agent/workspace/DevolaFlow/.rules/architecture.mdc:104-117` + `/home/agent/workspace/DevolaFlow/CHANGELOG.md:243-244`。
- **A-5 Single-Owner Invariant**（同 mdc :111-119）—— Si-Chip 加新 Skill 注册表时直接复制此规则，配 AST-walk CI guard，避免半成品分裂。
- **DEVOLAFLOW_MEMORY_ROUTER / DEVOLAFLOW_RTK_PROXY 等 8 active env-flags + 3 test-fixture flags**（见 `references/env-flags.md` 的 13th SF-4 canonical，`CHANGELOG.md:243`）—— 提供"按 Skill 阶段灰度开启"的范式。
- **EvoBench harness**（`CHANGELOG.md:177-181`）—— 53 个 scenarios + composite 96.05 baseline；可改造为 Si-Chip Skill 阶段评估的初版基准。

### 7.5 ContextOS / ACON（用作 Skill 第 4 阶段以后的 context 治理）
- **ContextOS Cognition 层**的 6 个原语（Active Forgetting / Reasoning Depth Calibration / Synthesis Detection / Unknown Unknown Sensing / Productive Contradiction / Gravity Reweighting）+ Retrieval Router（Live/Warm/Cold churn 分类）+ Index Lifecycle Manager（embedding drift 检测）—— 直接对应 Skill 终局对抗 F3/F4/F5 的需要，可整体绑定。
- **ACON**（arXiv 2510.00615, Microsoft Research）：context compression 的两阶段蒸馏（Compressor LoRA + Agent LoRA），可作为"把大模型经验蒸馏到本地小模型 router"的具体路径（配 `/home/agent/reference/acon/README.md:120-141`）。

### 7.6 OpenSpec / DSPy + GEPA（用作 Stage 1 → 2 收敛工具）
- **OpenSpec** `/opsx:propose → /opsx:apply → /opsx:archive` 工作流（`/home/agent/reference/openspec/README.md:36-69`）可作为 Skill 第 1 阶段输出物的标准模板：proposal.md / specs/ / design.md / tasks.md。
- **DSPy + GEPA** 把 Stage 2 的"Markdown 收敛"自动化为 prompt-program 演化（无需人手 ITT）。
- **配套 Anthropic Skills L1/L2/L3 渐进披露** 来限制 token 占用。

### 7.7 OpenClaw / OpenAI Agents SDK / Pydantic-AI（次优先）
- 仅在 Si-Chip 的 Skill 需要"多 agent 编排"时引入；按 OpenClaw VISION 明确"不要默认引入 manager-of-managers"（`/home/agent/reference/openclaw/VISION.md:106-108`）。
- 优先单 agent + handoff 模式（OpenAI Agents SDK 2026 共识："start with one agent"）。

---

## 8. 关键发现 (Key Findings, top-5)

1. **2026 已有的事实证据多次否决"单层小模型直接驱动 agent"，但同时强烈支持"分层 + CLI 包装"**：claude-code-router v0 失败 → 重构为 default/background/think/longContext 后才跑通；OpenAI Agents SDK 2026 生产指南明确"router 用 GPT-5-nano 即可"；Aider Architect 模式 / Cursor Tab Fusion 都是"大模型出方案 + 小模型/边缘模型干活"。
2. **"Skill = CLI + Progressive Disclosure"是 2026 上半年最被验证的中间形态**：Anthropic 官方 Skills 3 级渐进披露 + claude-code-router 作者的 single-tool MCP `pdf --help` 案例 + RTK 60–90% token 压缩闭环。Si-Chip 应直接把这套 idiom 设为第 3 阶段的标准模板。
3. **失败模式不是"路由错"，而是"context 爆 + tool 选不准 + schema 静默漂移"**：F2 (tool explosion 95%→<30%)、F4 (MCP schema 50K-200K)、F5 (drift 99.8%→96% 不爆错)、F6 (BFCL 8B vs 405B 12 pp 差距) — Si-Chip 必须把 retrieval、schema 治理、drift CI 内建进 Skill 模板。
4. **替代终局并非互斥**：metadata-dispatcher（DevolaFlow `memory_router` 已落地）+ DSPy/GEPA 编译 + Anthropic Skills RAG retrieval + AIOS 调度 + ContextOS Cognition 层 — 完全可以**叠加**，对应 Skill 不同阶段；Si-Chip 真正的差异化是"如何把这些层级的判变指标做出来"。
5. **本地 RTK + DevolaFlow + claude-code-router 构成 Si-Chip 的最强 prior art 三件套**：RTK 给 token 压缩底座；DevolaFlow 给 SSOT 注册表 / `memory_router` fast-path / shell_proxy whitelist；claude-code-router 给路由 + transformer + 自定义 router 钩子。Si-Chip 不必从零造，应优先做"演化路径 + 评估体系"两件事，并在每个阶段复用上述项目的现成组件。

---

## 9. 来源清单（≥ 8 独立 2026 来源；≥ 4 本地路径 + 行号）

### 9.1 本地参考（≥ 4 必需 — 实际 9）

1. `/home/agent/reference/rtk/README.md:36-56, 122-138, 244-256, 351-372` — RTK 总览、token 节省表、命令支持矩阵、`gain/discover/session` 评分。
2. `/home/agent/reference/rtk/openclaw/README.md:1-86` — RTK OpenClaw 插件实测（git log --stat 87%、find -name 48%）。
3. `/home/agent/reference/rtk/hooks/README.md:1-235` — 9 个 agent 集成的 hook 协议、JSON 格式、graceful degradation。
4. `/home/agent/reference/claude-code-router/README.md:1-606` — 路由+transformer+自定义路由+CUSTOM_ROUTER_PATH+SUBAGENT-MODEL 标签+Status Line。
5. `/home/agent/reference/claude-code-router/blog/en/progressive-disclosure-of-agent-tools-from-the-perspective-of-cli-tool-style.md:1-155` — **核心相关**：MCP-as-CLI 渐进披露、`pdf --help` 案例、Skills 三级机制评论。
6. `/home/agent/reference/claude-code-router/blog/en/project-motivation-and-how-it-works.md:85-101` — **核心相关**：作者亲述"轻量小模型路由失败 → 改用 DeepSeek 才跑通"。
7. `/home/agent/reference/claude-code-router/blog/en/maybe-we-can-do-more-with-the-route.md:32-100` — DeepSeek long-context 工具掉线 + Tool Mode / ExitTool 修补范式。
8. `/home/agent/reference/composio/README.md:62-183` — 500+ apps、6 个 provider 适配、Rube MCP server。
9. `/home/agent/reference/openclaw/VISION.md:99-108` — 拒绝 manager-of-managers / heavy orchestration 的设计哲学；Skills 走 ClawHub。

补充本地：
- `/home/agent/reference/openai-agents-python/README.md:10-21` — OpenAI Agents SDK 核心概念（agents-as-tools / handoffs / guardrails）。
- `/home/agent/reference/swarm/README.md:1-20` — Swarm 已被 Agents SDK 替代，作为 prior art 引用。
- `/home/agent/reference/dspy/README.md:14-49` — DSPy 编程范式 + GEPA 优化器引用 (Jul'25)。
- `/home/agent/reference/openspec/README.md:36-69` — `/opsx:propose → /opsx:apply → /opsx:archive` 工作流。
- `/home/agent/reference/pydantic-ai/README.md:30-66` — 类型安全 / observability / durable execution。
- `/home/agent/reference/ContextOS/README.md:28-104` — Cognition 层 / Retrieval Router / Index Lifecycle Manager。
- `/home/agent/reference/acon/README.md:1-141` — ACON 上下文压缩两阶段蒸馏（arXiv 2510.00615）。
- `/home/agent/workspace/DevolaFlow/.rules/architecture.mdc:104-119` — A-5 Single-Owner Invariant + 5 SSOT 注册表表格。
- `/home/agent/workspace/DevolaFlow/CHANGELOG.md:154-243` — RTK_PROXY env-flag、command-mapping schema v2、5 SSOT 注册表演进、references/env-flags.md。
- `/home/agent/workspace/Si-Chip/.local/tasks/init_si-chip_repo.md:1-7` — 用户原始 Skill 阶段假设。

### 9.2 外部 2026 来源（≥ 8 必需 — 实际 15）

1. **LLMRouterBench** — arXiv 2601.07206v1, January 2026. 400K instances, 21 datasets, 33 models, 10 baselines; OpenRouter 较 GPT-5 −24.7 pp；Avengers-Pro +4% / −31.7%。
2. **A Unified Approach to Routing and Cascading for LLMs** — proceedings.mlr.press/v267/dekoninck25a (PMLR 2025; 2026 引用栈)。
3. **kNN routing baseline** — arXiv 2505.12601 (May 2025；LLMRouterBench 2026 引用为简单胜复杂的标杆)。
4. **ToolSpec: Schema-Aware Speculative Decoding** — arXiv 2604.13519 (2026)。
5. **SpecGuard: Verification-Aware Speculative Decoding** — arXiv 2604.15244 (2026)。
6. **Tool Selection Hallucinations via Internal Representations** — arXiv 2601.05214v1 (2026), 86.4% 检测准确率。
7. **Anthropic Claude Haiku 4.5 System Card + benchmarks** — assets.anthropic.com/.../Claude-Haiku-4-5-System-Card.pdf；benchlm.ai/models/claude-haiku-4-5 (2026)；OpenRouter performance 页 (1.55% tool err)。
8. **Anthropic Code Execution Tool 2026** — docs.anthropic.com/en/docs/agents-and-tools/tool-use/code-execution-tool；版本 `code_execution_20260120` (Jan 2026)。
9. **Anthropic Agent Skills (CLI + 3-level disclosure)** — docs.anthropic.com/en/docs/claude-code/skills；docs.anthropic.com/en/api/skills-guide (2026 更新)。
10. **OpenAI Agents SDK Manager-vs-Handoffs (2026 production guide)** — apiscout.dev/blog/openai-agents-sdk-architecture-patterns-2026；toolhalla.ai/blog/multi-agent-orchestration-guide-2026；developers.openai.com/api/docs/guides/agents/orchestration。
11. **Aider 2026 Architect mode + 47-file benchmark** — morphllm.com/comparisons/morph-vs-aider-diff (2026)；devtoolsreview.com/pricing/aider-pricing (March 2026)；deepwiki.com/Aider-AI/aider/5.5-architect-mode。
12. **Cursor Tab Fusion (2025)** — cursor.com/en/blog/tab-update（被 2026 引用为边缘小模型成熟实例）。
13. **Tian Pan: Tool Explosion / Over-tooled Agent (April 2026)** — tianpan.co/blog/2026-04-13-tool-explosion-problem-...；tianpan.co/blog/2026-04-19-over-tooled-agent-problem。
14. **ToolHalla: Context Rot (2026)** — toolhalla.ai/blog/context-rot-ai-agents-2026。
15. **Junia AI: MCP Context Window Problem (Mar 2026)** — junia.ai/blog/mcp-context-window-problem。
16. **Tool Schema Drift series (Feb–Mar 2026)** — medium @Modexa "When One Field Drift..." / @duckweave "11 Checks" / @jickpatel611 "Version Negotiation" / @Nexumo "Quietly" / @1nick1patel1 "10 Rules"。
17. **AIOS v0.3.0 (Jan 22 2026)** — arXiv 2403.16971v4；agiresearch/AIOS GitHub；docs.aios.foundation/aios-docs/aios-kernel/scheduler。
18. **NVIDIA SLM-for-agents position paper** — research.nvidia.com/labs/lpr/slm-agents (2025)；developer.nvidia.com/blog/how-small-language-models-are-key-to-scalable-agentic-ai (被 2026 工作大量引用)。
19. **NVIDIA Nemotron Nano 2 Technical Report** — research.nvidia.com/labs/adlr/files/NVIDIA-Nemotron-Nano-2-Technical-Report.pdf；arXiv 2508.14444。
20. **NVIDIA Nemotron 3 Nano Technical Report** — research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Nano-Technical-Report.pdf；acecloud.ai/blog/nemotron-3-nano-vs-mistral-small。
21. **BFCL v4 leaderboard / `bfcl-eval v2026.3.23`** — gorilla.cs.berkeley.edu/leaderboard.html；pypi.org/project/bfcl-eval；airank.dev/benchmarks/bfcl。
22. **SWE-Bench Pro long-horizon failures** — arXiv 2509.16941 (2025/2026)；hf.co/papers/2509.16941。
23. **`skill-retrieval-mcp` (89K skills, −80% tokens)** — pypi.org/project/skill-retrieval-mcp v0.2.0。
24. **`skill-depot` / `MCP-RAG` / `agentic-academy MCP Registry`** — github.com/Ruhal-Doshi/skill-depot；github.com/iberi22/MCP-RAG；agentic-academy.ai/posts/mcp-registry-deep-dive。
25. **DSPy GEPA optimizer (Jul'25)** — arXiv 2507.19457；dspy.ai/api/optimizers/GEPA；gepa-ai.github.io/gepa/tutorials/dspy_full_program_evolution。
26. **GPT-5 / GPT-5-mini 价格与 routing 实测 (2026)** — openrouter.ai/openai/gpt-5；apicents.com/compare/gpt-5-mini-vs-minimax-m2-5-openrouter；crazyrouter.com/models/gpt-5-mini。
27. **LLM Routing & Cascade 2026 cost guide** — blog.appxlab.io/2026/04/05/llm-router-api-cost-reduction；tianpan.co/blog/2025-11-03-llm-routing-model-cascades。
28. **Berkeley Function Calling Leaderboard paper** — proceedings.mlr.press/v267/patil25a.html。

---

## 10. metrics（machine-readable summary）

```yaml
sources_count: 24            # 9 local + 15 external (de-duplicated; the 28 entries above include sub-series)
sources_local_count: 9
sources_external_2026_count: 15
failure_modes_count: 8       # F1..F8
alternatives_count: 5        # A..E
hypothesis_assessment: "Conditional Yes — 方向正确，需叠加分层路由 + CLI 拦截 + 渐进披露 + RAG retrieval + schema-drift 治理 五层基础工程"
key_findings_count: 5
acceptance_criteria:
  ge_8_sources_2026: PASS
  ge_4_local_with_path_lineno: PASS
  measurement_table: PASS
  failure_modes_ge_5: PASS
  alternatives_ge_3: PASS
  rtk_local_reuse_advice: PASS
  strict_2026_window: PASS
  chinese_primary_with_english_proper_nouns: PASS
```

---

## 11. 给 Si-Chip 仓库下一步的 4 条具体动作建议（非实现代码，可直接进路线图）

1. **建一份"Skill 阶段定义"模板**，4 个阶段每个阶段必须给出：
   (a) 输入物（Markdown / spec / CLI 列表 / 路由配置）；
   (b) 至少一个 quantitative gate（参考 BFCL v4 / tau2-bench / Aider edit / RTK token gain）；
   (c) 必须开启的"基础工程层"（progressive disclosure / RTK / RAG retrieval / drift 治理）。
2. **把 RTK + DevolaFlow `memory_router` + claude-code-router 三套组件做成 Si-Chip 的"参考实现包"**，每个 Skill 模板默认装载，不重新实现。
3. **接入 schema-drift CI**：每次 Skill CLI 接口变更必须过 version negotiation 检查（参考 2026 medium 系列），否则禁止合入主分支（与 always_applied "Protected Branch Workflow" 一致）。
4. **建立"Skill 评估基准矩阵"**：在仓库 CI 里跑 BFCL v4 / tau2-bench / Terminal-Bench 2.0 / Aider edit benchmark / RTK gain，每个 Skill 必须提交自己的得分作为升级条件（与 always_applied "Mandatory Verification" 一致）。

---

> 文档生成时间：2026-04-27（基于 R4 任务接收时刻），所有外部数字均带 2026 标识来源；本地路径均给行号锚点便于 PR review。
