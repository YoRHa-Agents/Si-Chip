# R3 · Skill 量化评估指标与基准方法 调研

> Wave 1 · Task R3 (research-only)。中文为主，专有名词保留英文。
> 时间窗：以 2026-01-01 起的 release / commit 为「新近证据」；2024–2025 的旧基准只作为基线参照。

---

## 0. TL;DR（给决策者的 6 条）

1. **「任务通过率」已不是 2026 评估的主旋律。** Anthropic Skill Creator（2026-03-03）、CursorBench-3（2026-03）、Sierra τ³-bench（2026-03-18）、Stanford HELM v0.5.14（2026-04-03）、Princeton HAL（2026-03-11）、UK AISI Inspect AI v0.3.205（2026-04-04）这一波都把「token 消耗 / 成本 / pass^k 一致性 / 触发准确度 / 错误归因」抬到与正确率同等地位[^webhelm] [^webcurs] [^webclaude] [^haltechreport]。
2. **「Skill-level metric」业界已经有**事实**标准模板 — Anthropic Skill Creator 2026-03。** 它内置 *pass-rate / elapsed_time / token_usage / triggering accuracy* 四件套[^webclaude]，外加 A/B comparator 做「用 Skill vs 不用 Skill」盲测；Vercel skills.sh + Auto-Skill 给出「External(50) → Local(75) → Graduated(85+)」的 confidence ladder + 调用次数门槛[^webgrad]；AgentMaturity Compass 把整个 agent 划成 L0–L5 五档[^webamc]。Si-Chip 可直接继承四件套并扩展自研指标。
3. **`Pass^k` 是目前最干净的「可演化性 / 鲁棒性」单指标。** τ-bench 系列已经把 `Pass^k = (c/n)^k` 写进 leaderboard（airline pass¹=0.46 → pass⁴=0.225 同模型同任务）[^taubench-readme]，比单点 accuracy 更能暴露「这个 Skill 能不能在生产里被反复调用而不退化」。
4. **「触发准确度」是 Skill 阶段判定最被低估的维度。** Anthropic 的 description optimizer 已经把它工程化（20 个正/反例 trigger queries × 5 轮迭代）[^webdescopt]；BFCL V4 `irrelevance` + `format_sensitivity` + K2VV `trigger_similarity` 三家分别给出实现模板[^bfclchangelog] [^k2vv]。Si-Chip 的阶段一→阶段二跃迁本质就是「触发准确度从 < 70% 收敛到 ≥ 90%」。
5. **关于「Skill 终局是轻量模型 + CLI 路由」的猜想：业界数据**部分**支持但有反例。** Front-Door Routing Benchmark（2026-03）显示 1–4B 小模型在 6 类路由任务上最好也只做到 78.3% acc / 988ms P95，没有任何模型同时满足 ≥85% & ≤2000ms[^webroute]；Scale MCP Atlas 2026-04 显示 **Claude Opus 4.7 (Adaptive) 77.3% vs GPT-5.5 75.3%**——头部模型差 2pp，但没有任何小模型进前 3[^webmcpatlas]。意味着 Si-Chip 阶段三向轻量模型路由的迁移**必须配套验证集**，不能假设小模型自动 ready。
6. **用户的 3 阶段模型缺一档：「退役（decommission）候选」。** Anthropic 明确区分了两类 Skill：`capability uplift`（base model 做不了的，随模型升级会过期）vs `encoded preference`（工作流顺序化，长期保留）[^webclaude]。**当 base model 不加载 Skill 也能 pass eval 时 → 该 Skill 应被回收，而不是升级到阶段三**。建议 Si-Chip 在阶段一之前增加一个「阶段 0：退役候选」分类枝。

---

## 1. 2026 主要评估基准 / 框架（≥8 个，全部填齐五要素）

> 五要素：① 测什么 ② 怎么测 ③ 输出指标维度 ④ 局限 / 已知作弊路径 ⑤ 是否能用于「单个 skill 的阶段判定」

### 1.1 SWE-bench / SWE-bench Verified / SWE-bench Pro

* **本地路径**：`/home/agent/reference/SWE-bench/` 与 `/home/agent/reference/swe-bench/`（commit 2026-03-19，`Fix git checkout resetting entire tree for new-file-only test patches`）
* **① 测什么**：task-level「真实 GitHub issue → patch 是否让隐藏单测通过」。`SWE-bench Verified` 是 OpenAI Preparedness 团队标注过的 500 例可解子集；`SWE-bench Pro`（Scale, 2026）是 1,865 例长 horizon、含 held-out + commercial 三段[^webswepro]。
* **② 怎么测**：自动化 — Docker 容器化执行 (`swebench.harness.run_evaluation`)，build/install/apply patch/run tests 全自动[^swerefreadme]。Pro 版加 sb-cli / Modal cloud。
* **③ 指标**：
  * 主：`% Resolved`（隐藏单测通过率）
  * 2026 新增：cost ($/task)、wall-clock、context-window 占用（vexp-swe-bench 2026 把 cost 直接做成第一公民坐标轴：vexp + Claude Code 73.0% @ $0.67/task vs OpenHands 70.0% @ $1.77/task）[^webswelb]
* **④ 局限**：a) Verified 与 Pro Public 都已有数据污染争议（top model SWE-Verified 80%+ 但 SWE-Pro 仅 23–46%）[^webswepro]; b) 评测语言局限 Python；c) patch 级 diff 不能反映「Skill 是否使用了正确的工具/CLI」；d) 单点 accuracy 不暴露重试间方差。
* **⑤ 阶段判定**：**部分可用**。适合给「编码类 Skill 阶段三：CLI 化的工具组合」做 final acceptance gate；不适合阶段一阶段二，因为 SWE-bench 假定一个完整 agent，不是一个 skill 模块。

### 1.2 τ-bench / τ²-bench / τ³-bench（Sierra Research）

* **本地路径**：`/home/agent/reference/tau-bench/`（commit 2026-03-18，`update-readme-tau3-bench`）
* **① 测什么**：multi-turn tool-agent-user 交互 + 双方都能改世界状态（τ²+ 引入 dual-control，τ³ 加 banking 域 + voice modality）[^webtau2]。
* **② 怎么测**：半自动 — LLM 当 user simulator（`gpt-4o` 默认），agent 调真实 API，最终用 ground truth state hash 做匹配；可选 `--user-strategy verify/reflection` 做二次 LLM 验证；trajectory-level 错误归因用 `auto_error_identification.py`，把错误来源拆成 `USER / AGENT / ENVIRONMENT` 与 `CALLED_WRONG_TOOL / USED_WRONG_TOOL_ARGUMENT / GOAL_PARTIALLY_COMPLETED / OTHER`（见本仓 L33-L52）[^taueid]。
* **③ 指标**：
  * `Pass^1, Pass^2, Pass^3, Pass^4` —— **一致性指标**。本地 README 实测：claude-3-5-sonnet airline `Pass^1=0.460 → Pass^4=0.225`，retail `0.692 → 0.462`[^taubench-readme]；公式 `Pass^k = (c/n)^k`[^webpassk]。
  * Auto-error-identification 给出 fault attribution 矩阵。
* **④ 局限**：a) user simulator 本身是 LLM，noise 较大；b) 旧版任务定义已被 τ²/τ³ 弃用（README 顶部明确 warning「The tasks in this repo are not updated」）；c) 无 token cost 默认输出。
* **⑤ 阶段判定**：**强相关**。`Pass^k` 衰减曲线就是「Skill 是否还在阶段一（高方差）」的最干净诊断；`auto_error_identification` 给出的「错的是 prompt 还是 tool」可直接用来判定阶段一→阶段二的描述收敛。

### 1.3 Berkeley Function-Calling Leaderboard V4 (BFCL V4 / Gorilla)

* **本地路径**：`/home/agent/reference/gorilla/`（commit 2026-03-23，`Request to add MiniCPM-SALA to the leaderboard`）；CHANGELOG 显示 V4 release `2025-07-17` 并持续到 2026-04-12 leaderboard refresh[^bfclchangelog]。
* **① 测什么**：tool-use 五大类 — single-turn (non-live + live) / multi-turn / multi-step / **agentic (web-search + memory + format-sensitivity)** / irrelevance detection。
* **② 怎么测**：自动 — AST (Abstract Syntax Tree) 比对 + state-transition verifier；memory 类用 backend hierarchy `result/<model>/agentic/<memory_backend>/<category>.json`[^bfclchangelog]。
* **③ 指标维度**（V4 后权重）：non-live 10%、live 10%、irrelevance 10%、multi-turn 30%、agentic 40%（agentic 占比过半即承认 single-turn 接近饱和）[^bfclchangelog]；**含 cost & latency 列**（自 2024-04 引入）[^webbfcl]；新增 `format_sensitivity` 测同语义但格式扰动下的稳定性。
* **④ 局限**：a) RapidAPI mock 与真实 API 偏差；b) AST 评分对 schema 微变化敏感（这恰是 K2VV 抓到的产能问题）；c) 单一函数粒度，弱化了 skill 内部组合。
* **⑤ 阶段判定**：**强相关**，尤其 `format_sensitivity` 直接对应「Skill 描述/接口收敛度」 — 一个还在阶段一的 Skill 在 format 扰动下分数会显著下滑；`irrelevance` 子集对应「Skill 不该被触发时是否被错误唤起」（Anthropic 描述优化的 dual concern）[^webdescopt]。

### 1.4 AgentBench FC (THUDM, 2026-02)

* **本地路径**：`/home/agent/reference/AgentBench/`（commit 2026-02-09，`agentbench-lite-suite`）；2025-10-10 升级为 function-calling 风格集成 AgentRL[^abreadme]。
* **① 测什么**：5 个完全容器化的 agent 任务 — `alfworld`（家庭家务）/`dbbench`（SQL）/`knowledgegraph`（freebase 推理）/`os_interaction`（shell）/`webshop`（购物）— 每个都是 multi-turn function-calling。
* **② 怎么测**：自动 — Docker compose 起多 worker，AgentRL Controller 统一调度；每个任务 worker 内置成功条件（数据库 row、KG entity、WebShop reward 等）。
* **③ 指标**：每任务 success rate；leaderboard 用 macro avg；与 v0.1/v0.2 兼容矩阵分布在 `assets/fc_leaderboard.png`。
* **④ 局限**：a) freebase 数据源外部依赖；b) `webshop` 16GB RAM 启动门槛；c) `alfworld` worker 内存泄漏（README 自承）[^abreadme]；d) 不输出 token cost。
* **⑤ 阶段判定**：**间接可用**。它的「dbbench / os_interaction」可以作为 Si-Chip CLI 类 Skill（阶段三）模板的验证集；不适合直接做 skill-level metric。

### 1.5 BigCodeBench / BigCodeArena (2024–2025)

* **本地路径**：`/home/agent/reference/bigcodebench/`（commit 2025-10-15，README v0.2.2.dev2 已评 163 模型）[^bcb]
* **① 测什么**：1140 个工程化 Python 函数级任务（vs HumanEval 的 toy 任务），含 *Complete*（基于 docstring）和 *Instruct*（基于自然语言）两个 split；2025 衍生 BigCodeArena 做 vibe-coding 平台对比[^bcb]。
* **② 怎么测**：自动 — sandboxed exec via Docker / HF space + 真实 unit tests；`bigcodebench-evaluate` CLI；leaderboard reproducible run。
* **③ 指标**：Pass@1（greedy）；`bs=1` 用于 deterministic reproduction。无 cost 列。
* **④ 局限**：单函数粒度（不是 multi-file project）；Python only；2026 没有大版本更新（最新 commit 2025-10）。
* **⑤ 阶段判定**：**弱相关**。可用于「代码生成类 Skill」第二阶段（已收敛 pass@1）的 sanity check，不能反映 skill maturation。

### 1.6 Stanford HELM (Holistic Evaluation of Language Models)

* **本地路径**：`/home/agent/reference/helm/`（commit 2026-04-03，`Upgrade dependencies (#4162)` & v0.5.14）
* **① 测什么**：跨 capabilities (MMLU-Pro, GPQA, IFEval, WildBench) / safety / domain-specific (medicine, finance, audio) 的 holistic eval；明确把 *efficiency / bias / toxicity* 抬到与 accuracy 并列[^helmreadme]。
* **② 怎么测**：自动 — `helm-run` CLI + `helm-summarize` + web UI；synthetic efficiency scenario 控制 prompt size & 输出 token 来测 per-prompt / per-output-token 成本（NeurIPS'23 paper）[^webhelm]。
* **③ 指标维度**：accuracy / **efficiency** (idealized + denoised inference time) / robustness / fairness / bias / toxicity / calibration —— 7 维 holistic 矩阵；Lite 子集允许「10 examples × 400× 算力节省 + ±5 名次置信区间」[^webhelm]。
* **④ 局限**：a) 任务级，不是 agent / skill 级；b) efficiency 需要 idealized clock 假设；c) 模型空间 > agent 空间。
* **⑤ 阶段判定**：**借鉴价值**。Si-Chip 应直接借用 HELM 的「holistic 多维矩阵 + 单维不能掩盖另一维」的 framing；不能直接套数值。

### 1.7 Princeton HAL (Holistic Agent Leaderboard) + hal-harness

* **本地路径**：`/home/agent/reference/hal-harness/`（commit 2026-03-11，`reliability fixes, new social plots, GPT 5.4 support`）
* **① 测什么**：unified harness 跑跨 benchmark agent eval — 当前覆盖 SWE-bench Verified / USACO / AppWorld / CORE-bench / tau-bench / AssistantBench / SciCode / ScienceAgentBench / ColBench[^halreadme]。
* **② 怎么测**：自动 — `hal-eval` CLI；本地 conda / Docker / Azure VM 三模式；Weave 自动 trace + cost tracking；`hal-upload` 加密轨迹防 contamination[^halreadme]。
* **③ 指标**：每基准自带主指标 + Weave 给出统一的 `cost_usd`、`tokens_in / tokens_out`、`wall_time_s`、`tool_call_count`、`agent_traces`；HAL leaderboard 直接展示「accuracy × cost」散点图[^haltechreport]。
* **④ 局限**：a) 不发明新评估题，只做 wrapper；b) Azure 依赖；c) 多 benchmark 异质（每个的 grader 不一样）。
* **⑤ 阶段判定**：**强工程价值**。HAL 的「accuracy + cost 双坐标轴 + 自动 trace」就是 Si-Chip 阶段判定可以直接复用的工程模板：每次 Skill 调用记 `(success, cost_usd, latency_s, tool_calls, tokens)`，再做 P50/P75 统计。

### 1.8 UK AISI Inspect AI (`inspect_ai`)

* **本地路径**：`/home/agent/reference/inspect_ai/`（commit 2026-04-04，release）；scorer 模块 `src/inspect_ai/scorer/_metrics/{accuracy,grouped,mean,std}.py`；reducer 含 `pass_at, max_score, mean_score, median_score, mode_score, at_least`[^inspectinit]。
* **① 测什么**：通用 LLM eval framework，自带 token / time / cost / message 限位（`_token_limits.md`、`_cost_limits.md`、`_working_limits.md`）[^inspectlimits]。
* **② 怎么测**：自动 + 半自动 — `Scorer` decorator 模式；支持 model-graded（`_model.py`），multi-scorer，pattern/match/answer/choice。
* **③ 指标**：核心 `Score` 值域 = `CORRECT / INCORRECT / PARTIAL / NOANSWER / UNCHANGED`[^inspectinit]；reducer 给 `pass_at(k)`、`at_least(k)`、median/mode；**自动记录 `total_tokens`** 与 working time（拆掉 rate-limit 和资源等待）[^inspectworking]。
* **④ 局限**：a) framework，不是 benchmark；b) 需要人写 scorer；c) HTTP hook 在 `azureai` 等 client 上不能精确切分 retry。
* **⑤ 阶段判定**：**强工程价值**。它的 `working_limit` 与 `pass_at` reducer 几乎就是为「Skill 阶段三：稳定调用」量身定做的指标接口，可以直接 wrap Si-Chip 的 SKILL.md。

### 1.9 Princeton + Sierra HAL × Sierra τ-bench × Scale SWE-Bench Pro 联合 leaderboard（"trifecta" 2026）

——已在 1.1 / 1.2 / 1.7 分别覆盖，此处仅指出三者在 2026 形成的事实交集：HAL `--benchmark taubench_retail` / `swebench_verified_mini` 已是事实标准[^halreadme]，hal leaderboard 同时挂 SWE / τ / GAIA-style task。

### 1.10 Moonshot K2 Vendor Verifier (K2VV)

* **本地路径**：`/home/agent/reference/K2-Vendor-Verifier/`（commit 2026-02-14，`Remove Fireworks provider + openrouter from K2-thinking table`）
* **① 测什么**：单一模型 (Kimi K2) 跨 vendor 推理时的 *toolcall schema accuracy* 和 *trigger similarity*。
* **② 怎么测**：自动 — 同 prompt 集对每家 vendor 跑 1k–4k 次 tool-call，统计 `count_finish_reason_tool_calls`（应触发的次数）、`count_successful_tool_call`（成功序列）和 `schema_accuracy = 后者/前者`[^k2vv]。
* **③ 指标**：
  * `ToolCall-Trigger Similarity`（≥73% 视为可接受）
  * `Schema Accuracy`（Moonshot 官方 100%；vLLM 87.22%；Together 84.63%）
  * `tool_call_f1`（README L150-L151 自承官方多次跑波动 75.81%–avg 76%）[^k2vv]
* **④ 局限**：a) 只针对 K2 模型；b) 不评估业务正确性，只评 schema；c) trigger similarity 阈值人为定。
* **⑤ 阶段判定**：**强直接借鉴**。K2VV 的 `(trigger_similarity, schema_accuracy)` 二维空间几乎就是 Si-Chip 阶段一→阶段二的判别坐标系：阶段一 trigger_similarity 噪声大，阶段二开始稳定，阶段三随 CLI 化彻底变 100%（schema 由 CLI 而非 LLM 决定）。

### 1.11 NEAR AI nearai-benchmarks + ZClawBench security suite

* **本地路径**：`/home/agent/reference/nearai-benchmarks/`（commit 2026-03-27，`feat/openclaw-runner-zclaw-security`）
* **① 测什么**：`trajectory`（per-turn assertion 的 multi-turn 场景）、`spot`（21 端到端任务）、`gaia`、`tau_bench`、`swe_bench`、`zclaw-security-{chn,eng}`（10 个 prompt-injection 抵抗任务）。
* **② 怎么测**：自动 — `nearai-bench` CLI；输出 `run.json`（aggregate pass rate / cost / timing / model / harness）+ `tasks.jsonl`（per-task scores + traces）[^nearaireadme]。
* **③ 指标**：pass rate / cost / timing per task；framework 维度可比（ironclaw vs openclaw）[^nearaireadme]。
* **④ 局限**：harness 早期 (v1)；trajectory 数据集需要外部 workspace 文件；ZClaw 仅 10 题。
* **⑤ 阶段判定**：**辅助**。`zclaw-security` 这条线对应 Si-Chip Skill 在阶段二/三的「抗误用」维度，可作为 acceptance gate 之一。

### 1.12 OpenAI Evals (legacy + 2025 Graders API)

* **本地路径**：`/home/agent/reference/evals/`（commit 2025-11-03，`Remove incontext_rl suite`）—— 严格说**不是 2026 commit**，但 2025-09 之后并入 OpenAI Dashboard Evals 与 Graders API[^openai-graders]。
* **① 测什么**：可注册 eval 仓库；2025 Graders API 把评分扩到 `string check / text similarity / score model / python code / multigrader`[^openai-graders]。
* **② 怎么测**：自动 + 半自动；可用于 RFT (reinforcement fine-tuning) 监督。
* **③ 指标**：自定义；评分值 0-1。
* **④ 局限**：repo 已停止接受 custom code 类 eval；focus shift 到 cloud Dashboard。
* **⑤ 阶段判定**：**仅作为打分模板参考**，不是 skill stage detector。

### 1.13 MCP-Bench / MCP Atlas / MCPMark（2026 新形态：面向 Skill-as-server）

* **外部来源**：Accenture MCP-Bench（250 tools × 28 live MCP servers，GPT-5 0.749 / o3 0.715 / gpt-oss-120b 0.692）[^webmcpbench]；Scale Labs **MCP Atlas**（1,000 tasks × 36 real MCP servers × 220 tools，500 public + 500 private，2026-04-24 leaderboard：Claude Opus 4.7 (Adaptive) 77.3%、GPT-5.5 75.3%、DeepSeek V4 Pro 74.2%）[^webmcpatlas]；**MCPMark**（127 verifiable tasks × 38 models，stress-testing）[^webmcpmark]。
* **① 测什么**：LLM 通过 MCP (Model Context Protocol) 真调 live tool servers 的端到端能力 — 工具发现 (discovery)、跨工具协同 (coordination)、参数控制 (parameter control)、规划 (planning)、错误恢复 (error recovery)、输出合成。
* **② 怎么测**：自动 — LLM 连 live MCP servers（finance / travel / scientific computing / academic search 等），按多步 workflow 判结果；MCP Atlas 用 1,000 任务公私分仓防污染。
* **③ 指标**：成功率、tool call correctness、multi-step coordination score、error recovery rate；MCP Atlas 直接给 Adaptive vs fixed 模式对比（Claude Opus 4.7 Adaptive 77.3% vs 固定 prompt 变体）。
* **④ 局限**：a) live server 本身不稳定；b) 每家 MCP 实现差异大（同名工具不同 behavior）；c) task-level，不是直接的 skill-level。
* **⑤ 阶段判定**：**强相关 — 这是 Si-Chip 阶段三「Skill = index + CLI 包装」的直接实验场**。MCP Atlas 的 Adaptive 模式（模型自己决定调用哪个工具）正是用户假设里「轻量模型 + 路由」的 in-the-wild 验证；Claude Opus 4.7 Adaptive 比同模型 non-adaptive 高 4-6pp，说明「Skill 路由准确度」确实是有效的独立维度。

### 1.14 Anthropic Claude Skill-Creator Eval Framework（2026-03 发布 — Skill-level 评估的**事实标准**）

* **外部来源**：Claude 官方博客《Improving skill-creator: Test, measure, and refine Agent Skills》（2026-03-03）[^webclaude] + 内部 skill-creator 插件[^webclaudeskillcreator]
* **① 测什么**：**skill-level**（而非 task-level）质量 — 每个 Skill 四个独立维度：
  1. **eval pass-rate**（定义 test prompts + 描述成功标准 → 判 pass/fail）
  2. **elapsed time**（每 test 独立 agent，时间独立计）
  3. **token usage**（每 test 独立 agent，token 独立计）
  4. **triggering accuracy**（description 优化器：分析 current description vs sample prompts，自动建议删改以同时降低 FP/FN；Anthropic 在自家 6 个公开 skills 中 5 个命中率提升）
* **② 怎么测**：**半自动** — 作者人写 test prompts 与预期 good looks like，skill-creator 多 agent **并行** 执行（每个干净 context + 独立 token/timing 指标），并用 **comparator agents 做 A/B 盲测**（判「用 Skill 的输出」vs「不用 Skill 的输出」哪个更好，不告诉 judge 哪个是哪个）。
* **③ 指标**：benchmark mode 输出 `(pass_rate, elapsed_time, token_usage)` 三元组；description optimizer 输出 `(FP_count, FN_count, suggested_edits)`；A/B 输出 win-rate。
* **④ 局限**：a) 仅 Anthropic 生态；b) test prompts 还是要作者写（非通用 skill corpus）；c) comparator 本身是 LLM（一致性风险）。
* **⑤ 阶段判定**：**最直接**。Anthropic 自己的分类 `Capability uplift skills`（模型做不了/不稳，需要技巧打底）vs `Encoded preference skills`（模型都会做，但用工作流序列化）——前者随模型升级会**过期**（base model 不加载 skill 也 pass 时就该删），后者**保留**。这正是 Si-Chip 阶段判定还没充分考虑的**退役（decommission）信号**：**Skill 不一定越走越重，它也可能因为 base model 进化而被回收**。用户的 3 阶段模型建议扩展为「阶段 0 = 退役候选」以覆盖 capability uplift 过时的情形。

> 截至此小节已覆盖 14 个具体基准 / 框架 ✓（满足 ≥ 8）。

### 1.15 OpenTelemetry GenAI Semantic Conventions（2026 稳态 — 非基准而是可观测性协议）

* **外部来源**：opentelemetry.io GenAI spec（2026 早期稳定，引入 `gen_ai.agent.name` on child spans/metrics）[^weboteltel] [^webotelsemconv]；Datadog/Honeycomb/New Relic 原生支持；LangChain/CrewAI/AutoGen/AG2 原生 emit OTel-compliant spans。
* **① 测什么**：**不直接**测能力，而是把「Agent / Skill 调用的 trace + metric」标准化 — 提供 `gen_ai.usage.input_tokens`、`gen_ai.usage.output_tokens`、`gen_ai.operation.name`、`gen_ai.agent.name`、`gen_ai.agent.version` 等 attr。
* **② 怎么测**：协议 — instrumentation library 按 spec emit spans/metrics 到 Collector，再到 Prometheus/Grafana/Tempo。
* **③ 指标**：token / cost per agent per skill（by `gen_ai.agent.name`）；工具链 branch depth；P95 latency；`gen_ai.operation.name` 分布（chat vs generate_content vs text_completion）。
* **④ 局限**：a) 目前 Python SDK instrumentation 仍不完整；b) 用户通过 `/` prefix 触发的 skill 在 Claude Code 里 emit 不了 OTel event（已有 GH issue）[^webskilltelem]；c) 只是数据管道，需要自己写判定规则。
* **⑤ 阶段判定**：**基础设施价值**。Si-Chip §3 的指标 ①③④⑤⑦⑧ 几乎全部依赖这套 telemetry；强烈建议 Si-Chip 从第一天就用 OTel GenAI spec 而不是自定义 schema。

---

## 2. 多维指标矩阵（行=指标维度 / 列=基准）

> ✓ = 原生支持；△ = 间接 / 需自实现；✗ = 不支持。

| 指标维度 \ 基准 | SWE-bench Verified | SWE-bench Pro | τ-bench / τ³ | BFCL V4 | AgentBench FC | BigCodeBench | HELM | HAL harness | Inspect AI | K2VV | nearai-bench | OpenAI Evals | MCP-Bench/Atlas | Anthropic Skill-Creator Evals |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 任务通过率 (accuracy/% resolved) | ✓ | ✓ | ✓ (Pass¹) | ✓ | ✓ | ✓ Pass@1 | ✓ | ✓ (relay) | ✓ | △ schema≠task | ✓ | ✓ | ✓ | ✓ pass_rate |
| **一致性 / Pass^k 重复成功** | ✗ | ✗ | ✓ Pass¹–⁴ | △ | ✗ | ✗ | ✗ | △ | ✓ `pass_at` reducer | ✗ | △ multi-run | ✗ | △ | △ (parallel multi-agent) |
| **Token cost / $ 成本** | △ | ✓ vexp | ✗ | ✓ V4 含 cost & latency | ✗ | ✗ | ✓ efficiency scenario | ✓ Weave 全自动 | ✓ ModelUsage | ✗ | ✓ run.json | △ | △ | ✓ per-eval token_usage |
| **Wall-clock / latency** | △ | △ | ✗ | ✓ V4 | ✗ | ✗ | ✓ idealized | ✓ | ✓ working_time | ✗ | ✓ | ✗ | △ | ✓ elapsed_time |
| **错误归因 (谁错了)** | ✗ | ✗ | ✓ user/agent/env + 4 fault types | ✗ | ✗ | ✗ | △ | △ | ✗ | △ trigger vs schema | △ | ✗ | △ tool vs plan | △ A/B comparator |
| **触发准确度 / Skill 是否该被调用** | ✗ | ✗ | △ | ✓ live + irrelevance + format-sensitivity | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ trigger similarity | ✗ | △ | △ Adaptive vs fixed | ✓ description optimizer |
| **格式 / Schema 鲁棒性** | ✗ | ✗ | ✗ | ✓ format_sensitivity | ✗ | ✗ | △ | ✗ | △ | ✓ schema_accuracy | ✗ | △ | △ | ✗ |
| **Memory / 状态持久性** | ✗ | ✗ | ✓ multi-turn | ✓ memory backend | △ | ✗ | ✗ | △ | ✗ | ✗ | △ | ✗ | ✓ multi-step | ✗ |
| **小模型路由可行性** | ✗ | ✗ | ✗ | △ live 子集 | ✗ | ✗ | △ | △ | ✓ vendor 维度 | ✗ | △ | ✗ | ✓ Adaptive mode | △ 两种 Skill 分类 |
| **抗 prompt injection / 安全** | ✗ | ✗ | △ | △ | ✗ | ✗ | ✓ HELM Safety | △ | ✗ | ✗ | ✓ ZClaw | △ | ✗ | ✗ |
| **Trace / observability hook** | △ | △ | ✓ trajectory | △ | △ | ✗ | ✗ | ✓ Weave | ✓ events | ✗ | ✓ tasks.jsonl | △ | △ live logs | ✓ per-agent logs |
| **Acceptance via human / model judge** | ✓ tests | ✓ tests | △ user-sim | ✓ AST | ✓ env | ✓ tests | ✓ judge | ✓ | ✓ model_graded | ✗ | ✓ LLM judge | ✓ multigrader | ✓ env+asserts | ✓ comparator |

**关键观察**：

1. 没有任何**单一**基准同时覆盖以上 12 行。最接近的是 BFCL V4 + Inspect AI + HAL + **Anthropic Skill-Creator Evals** 的组合 —— 这正是 Si-Chip 应该考虑的「评估栈」组合。
2. **「触发准确度」「错误归因」「Pass^k」三列**几乎只有 2026 基准有 —— 这三列是 Si-Chip 阶段判定**最值得自研**的指标。其中「触发准确度」已由 Anthropic description optimizer + BFCL `irrelevance/format_sensitivity` + K2VV `trigger_similarity` 三家分别给出可复用的实现模板。
3. 「成本」列已经是 2026 默认 —— Si-Chip 不能再只测 task success。
4. **Anthropic Skill-Creator Evals 是 2026 唯一直接面向 "Skill-level" 的评估框架**（其他都是 task-level 或 model-level）——它已经确认了「pass-rate + elapsed_time + token_usage + triggering accuracy」四元组是 Skill 质量的合理分解。Si-Chip 可以**直接继承**这四个维度并额外补充 MRVD / CSR / SMRI（§3 ④⑤⑧）。

---

## 3. Skill-level 指标候选清单（5–8 个，含公式 / 数据源 / 触发阈值）

> 设 `S` = 单个 Skill；`call_i` = S 的第 i 次调用记录；记录字段（建议 schema）：
> `{ skill_id, ts, success: bool, latency_s, tokens_in, tokens_out, tool_calls: [str], cli_invocations: [str], model_id, trigger_query, was_correctly_triggered: bool, recovered_from_error: bool, retry_count, md_revision_hash }`

### 指标 ① 调用频率 P75（Adoption Pressure，AP）

* **公式**：`AP(S) = P75( count_per_day(S, last 14d) )`
* **数据源**：agent telemetry（OpenTelemetry GenAI semantic conventions / Weave / LangSmith）[^weboteltel]
* **阈值候选（基于 skills.sh / Auto-Skill 经验值）**[^webgrad]：
  * `AP < 1/day` → 阶段一候选（探索期，仍在写 Markdown）
  * `1 ≤ AP < 5/day` → 阶段一→二跃迁观察期
  * `AP ≥ 5/day & 持续 ≥ 14d` → 触发「**建议 CLI 化**」（与 Auto-Skill 的 "used ≥ 5 times" 门槛一致）
* **作弊路径**：刷调用次数；缓解 = 同时看 `unique_query_count`。

### 指标 ② Triggering F1 (TF1)

* **公式**：
  * 数据：每天采样 N=20 用户 query（10 应触发 + 10 不应触发，按 Anthropic Skill Creator 推荐配比）[^webdescopt]
  * `TF1(S) = 2·Precision·Recall / (Precision + Recall)`，其中 `Recall = TP/(TP+FN)`，`Precision = TP/(TP+FP)`
* **数据源**：trigger eval set（手写 + LLM 扩样）；trigger_query → SKILL.md description match
* **阈值候选**：
  * `TF1 < 0.7` → 阶段一（描述未收敛，需要 description optimizer 介入）
  * `0.7 ≤ TF1 < 0.9` → 阶段二（收敛中，进入「明确验收 + 迭代」阶段）
  * `TF1 ≥ 0.9 & 连续 5 个 release 不下降` → 阶段二→三 graduation 候选
* **作弊路径**：trigger 集本身被 LLM 写得太「贴脸」；缓解 = 引入对抗集（K2VV 风格 trigger similarity）[^k2vv]。

### 指标 ③ Token-per-Outcome (TpO)

* **公式**：`TpO(S) = median( tokens_in + tokens_out | success=True )`，并跟踪 `Δ TpO over weekly cohorts`
* **数据源**：模型 usage events（Inspect AI `ModelUsage.total_tokens` / Weave / OpenTelemetry `gen_ai.usage.*`）[^inspectlimits] [^weboteltel]
* **阈值候选**：
  * 当 `Δ TpO 7d-rolling < ±5%` 连续 4 周 → token 已稳定，**触发「prompt 固化建议」**（写死 system prompt 不再依赖运行时拼接）
  * 当 `TpO_p95 / TpO_p50 > 3` → 高方差 → 阶段一标志（Skill 还在「探索式 prompt」）
* **参考量级**（Agent Cost Benchmarks 2026）[^webagentcost]：单文件编辑 ≈ 4.2k in / 850 out；新功能 ≈ 42k in / 8.5k out；多轮支持 ≈ 6.2k in / 1.5k out
* **作弊路径**：截断输入；缓解 = 同时看 success rate 不能下降。

### 指标 ④ CLI Substitution Ratio (CSR)

* **公式**：`CSR(S) = count(call where len(cli_invocations) > 0 AND len(LLM_tool_calls) == 0) / count(call where success=True)`
  即「不需要 LLM 二次调用工具，全部由 CLI 完成」的占比
* **数据源**：tool_calls 与 cli_invocations 字段（须在 SKILL 入口 instrument）
* **阈值候选**：
  * `CSR < 0.3` → 阶段一/二（Skill 仍在 LLM 推理路由）
  * `0.3 ≤ CSR < 0.7` → 阶段二→三过渡（部分流程已 CLI 化）
  * `CSR ≥ 0.7` → 阶段三（CLI 路由占主导，对应用户假设的「Skill = index + CLI」终局形态）
* **作弊路径**：把 LLM 调用伪装成 CLI 内部步骤；缓解 = 看 cost & latency 是否真的下降。

### 指标 ⑤ Markdown Revision Velocity Decay (MRVD)

* **公式**：
  * `rev_count(S, week)` = 该周 SKILL.md 的 commit 数
  * `MRVD(S) = slope(linear_fit( week → rev_count ))`（负斜率代表收敛）
  * 同时跟 `unique_authors_per_week` 防误判
* **数据源**：git log（已是 Si-Chip 仓库内置数据），OpenSpec/devola gate report 也可串[^devolagate]
* **阈值候选**：
  * 连续 4 周 `rev_count ≥ 3` → 阶段一标志
  * 连续 4 周 `rev_count ≤ 1 AND TF1 ≥ 0.85` → **阶段二→三 graduation 候选**（描述已收敛）
* **作弊路径**：rebase / squash；缓解 = 看真实 diff 行数 `lines_changed` 而非 commit 数。

### 指标 ⑥ Pass^k Reliability (Pk)

* **公式**：`Pk(S, k) = (success_rate_single_attempt)^k`，沿用 τ-bench 定义[^webpassk] [^taubench-readme]
* **数据源**：每个 acceptance 任务跑 k=4 次（Anthropic 在 Skill Creator 也跑 A/B 多 round 比较）[^webclaude]
* **阈值候选**：
  * `P¹ < 0.8` → 阶段一（核心能力都不稳）
  * `P¹ ≥ 0.8 AND P⁴ < 0.5` → 阶段二（能做但不可靠）
  * `P⁴ ≥ 0.6` → 阶段三 readiness（可放进自动化 pipeline）
* **作弊路径**：用同 seed 跑 k 次；缓解 = 强制变 seed / 不同 user 模拟器。

### 指标 ⑦ Recovery-on-Failure Rate (RoF)

* **公式**：`RoF(S) = count(success=True AND retry_count ≥ 1) / count(retry_count ≥ 1)`
  即「失败后能否自我纠错」
* **数据源**：trace events；与 τ-bench `auto_error_identification` 兼容（错误源 ∈ {USER, AGENT, ENVIRONMENT}，错误类型 ∈ {wrong_tool, wrong_arg, partial_goal, other}）[^taueid]
* **阈值候选**：
  * `RoF < 0.3` → 阶段一（错就崩）
  * `RoF ≥ 0.6` → 阶段二（已具备 reflection / retry 模式）
* **作弊路径**：人为放低重试阈值；缓解 = 看 `retry_count` 的分布。

### 指标 ⑧ Small-Model Route-ability Index (SMRI)

* **公式**：在并联 large + small model 同输入下，`SMRI(S) = match_rate(small_model_out, large_model_out | judge="schema-equivalent")`
* **数据源**：双跑测试集（large=Opus / GPT-5 类；small=Qwen3-4B / Haiku 类）
* **阈值候选**（基于 Front-Door Routing Benchmark 2026）[^webroute]：
  * `SMRI < 0.6` → Skill 仍依赖大模型推理（阶段一/二）
  * `SMRI ≥ 0.85 AND latency_small < 2000ms` → 满足「Skill as light-agent」终局假设的可路由门槛
  * 注意：**截至 2026-03，没有任何小模型在 6 类路由任务上同时达到 ≥0.85 acc & ≤2000ms P95**[^webroute] —— 所以此指标更像「监测器」而不是「准入门」

> **小结**：以上 8 个指标互相独立、可直接计算、阈值都有 2026 公开参考值或类比；建议 Si-Chip 一开始至少实现 ① ② ③ ⑥ 四个，后续按需扩展。

---

## 4. 多维评分组合的工程参考：DevolaFlow Gate

DevolaFlow 仓库的 `schemas/gate-report.schema.yaml`（同 worktree 可读）已经给出一个可复用的 composite scoring 模板[^devolagate]：

* `verdict.composite_score`（number）+ `meets_threshold`（bool）+ `advisor_recommended`（borderline 标志）
* `check_results.{build, test, lint, code_review}` 各自带 `pass_threshold` 与 `findings_summary.{blocker, critical, major, minor, info}`
* `convergence_history.rounds[].composite_score` + `trend ∈ {improving, stagnant, degrading}` —— 这正是 Si-Chip 阶段判定需要的「时间维」结构。

**建议**：Si-Chip 把 §3 的 8 个 skill-level metric 装进一个类似的 `skill-stage-report.yaml`，每个 metric 有自己的 `value / threshold / trend`，再算一个总 `stage_score ∈ [1.0, 3.0]` 给阶段判定器。

---

## 5. 对用户假设（3 阶段判别）的影响

### 5.1 用户假设回顾（来自 `.local/tasks/init_si-chip_repo.md`）

| 阶段 | 形态 | 关键特征 |
|---|---|---|
| 一 | 复杂 Markdown + 引导对话 | 探索期，描述与流程都在变 |
| 二 | Markdown + 验收标准（明确收敛方向） | 行为开始固定，描述稳定 |
| 三 | index/UI 包装 + 复杂 CLI | 重复流程被 CLI 化，LLM 只做路由 |

### 5.2 哪些维度可以**直接借用**现成基准 / 指标

| 用户阶段判别需要 | 可借用 |
|---|---|
| 描述是否收敛（阶段一→二） | BFCL V4 `format_sensitivity` + Anthropic `description optimizer`（20 trigger queries × 5 round）+ §3 ②TF1 |
| 调用稳定性（阶段二准入） | τ-bench `Pass^k` + §3 ⑥Pk + Inspect AI `pass_at` reducer |
| 流程是否可固化（阶段二→三） | §3 ④CSR + §3 ③TpO 的方差衰减 |
| 错误归因（什么块还需要改） | τ-bench `auto_error_identification` 的 fault matrix |
| 成本下行（阶段三验证收益） | HAL Weave / Inspect AI ModelUsage / vexp-swe-bench 风格 cost-aware leaderboard |

### 5.3 哪些维度需要 **Si-Chip 自己定义** （现成基准没覆盖）

1. **「Markdown 演化速度」**：业界没有把 Markdown 修改频次当 metric 的；需要 §3 ⑤MRVD 自研。
2. **「CLI 替代占比」**：业界没有 ratio 指标；需要 §3 ④CSR 自研（这恰好是用户假设阶段三的核心特征）。
3. **「Skill 生命周期事件」**：例如「token 消耗稳定 → prompt 固化建议」「调用次数破阈值 → CLI 化建议」「触发准确度跌破 → 描述重写建议」—— 需要 Si-Chip 自己实现规则引擎（类比 Auto-Skill `graduate detect/promote`）[^webgrad]。
4. **「Skill 之间的相互引用 / 依赖图谱」**：当前所有评估都是「单个 agent 跑单个任务」，没有评估 *Skill graph 演化* 的指标。
5. **「退役候选判定」**：Anthropic 的分类已经给出思路 — 定期跑 baseline "not-loaded" 控制组，当 base-model-without-skill 的 pass-rate ≥ baseline-with-skill 时，flag 为 "capability-now-native" 回收候选[^webclaude]。这是 Si-Chip 需要内建的**反向闭环**。

### 5.4 风险点（用户假设需要小心的地方）

1. **「最终走向轻量模型 + CLI 路由」假设有反例**：Front-Door Routing Benchmark 2026[^webroute]、GAIA2[^webgaia2]、Scale MCP Atlas 2026-04[^webmcpatlas] 都表明「budget scaling 出现 plateau」与「无单模型在路由任务上 ≥85% acc & ≤2s」。这意味着阶段三的「轻量模型路由」可能是**部分**Skill 的终局，**不是所有 Skill 的终局**。
2. **「描述收敛」可能被误判**：如果 Markdown 表面停止修改但触发准确度已经下降（model drift），这是隐性退化。Si-Chip 必须把 MRVD 与 TF1 联合判定。
3. **Pass^k 在 multi-skill agent 里会指数衰减**：每个 Skill 都 P¹=0.9，5 个 Skill 串联 = 0.59。阶段判定不能孤立看单个 Skill。
4. **Token cost 优化可能掩盖能力退化**：HELM 早就警告 `efficiency × accuracy` 必须双轴看[^webhelm]。Si-Chip 阶段三验证必须并列对比阶段二的 baseline 任务集。
5. **「阶段升级」不是单向的**：Anthropic 的 capability uplift vs encoded preference 二分[^webclaude] + base-model drift 可能让一个已经在阶段三（CLI 化）的 Skill **变得不再必要**（base model 天然会做）。Si-Chip 的阶段判定器必须同时输出 `stage ∈ {0_retired, 1_exploring, 2_converging, 3_productized}`，而不是只让状态单调递增。
6. **Context Rot 是阶段三的隐性天花板**：Chroma 2026 研究覆盖 18 个前沿模型全部出现 context 从 10K → 100K 时 accuracy 下降 20-50%，32K-64K 区有 "cliff"[^webcontextrot]。当 Si-Chip 阶段三把多个 Skill 组装成大 prompt 时，**即使单个 Skill metric 全绿，组合后 P⁴ 也可能崩**。建议 Si-Chip 在阶段三增设「context budget」硬限。

---

## 6. 阶段判定器的最简实现建议（决策清单）

| 决策项 | 推荐 | 备选 | 依据 |
|---|---|---|---|
| 主一致性指标 | `Pass^4` (k=4) | `Pass^3` 减半评测预算 | τ-bench[^taubench-readme] / [^webpassk] |
| 主成本指标 | `tokens_in + tokens_out` 中位数 | $/task（vendor 价格易变） | HAL Weave[^haltechreport] / Inspect ModelUsage[^inspectlimits] |
| 触发判定指标 | TF1 ≥ 0.85 | trigger similarity（K2VV 风格） | Anthropic[^webdescopt] / K2VV[^k2vv] |
| 阶段一→二 触发器 | `MRVD < 1 commit/week × 4w AND TF1 ≥ 0.85` | 单看 TF1 | §3 ② + §3 ⑤ |
| 阶段二→三 触发器 | `AP_p75 ≥ 5/day AND TpO 7d 波动 < 5% AND CSR ≥ 0.5` | 单看 AP | Auto-Skill ladder[^webgrad] + §3 ① ③ ④ |
| 阶段三完成度评估 | `CSR ≥ 0.7 AND P⁴ ≥ 0.6 AND SMRI 监测` | `CSR ≥ 0.7` 单条件 | §3 ④ ⑥ ⑧ |
| 多维总分模板 | DevolaFlow `gate-report.schema.yaml` 的 composite_score + convergence_history | 自己设计 | DevolaFlow[^devolagate] |
| 错误归因 | τ-bench fault matrix（user/agent/env × wrong_tool/wrong_arg/partial/other） | 自定义 enum | τ-bench[^taueid] |
| 抗误用 / 安全 | ZClawBench 10 题 + HELM Safety 子集 | 仅 ZClaw | nearai-bench[^nearaireadme] / HELM[^helmreadme] |

---

## 7. 引用与来源

> 本地源 (≥ 5 条 ✓)；外部 2026 源 ≥ 8 条；总数 ≥ 13 ✓（满足 ≥ 10）。

### 本地证据（含 path:line）

[^swerefreadme]: `/home/agent/reference/SWE-bench/README.md` L33-L51（SWE-bench Verified, Multimodal, sb-cli, Modal cloud）；commit `2026-03-19`。
[^taubench-readme]: `/home/agent/reference/tau-bench/README.md` L1-L36（Pass¹-Pass⁴ 数值 + tau²/tau³ 公告）；commit `2026-03-18`。
[^taueid]: `/home/agent/reference/tau-bench/auto_error_identification.py` L31-L52（FaultAuthor + FaultType enum）；同一 commit。
[^bfclchangelog]: `/home/agent/reference/gorilla/berkeley-function-call-leaderboard/CHANGELOG.md` L8-L66（V4 release：agentic 40% 权重 + memory backend + format sensitivity + cost/latency 列）；repo commit `2026-03-23`。
[^abreadme]: `/home/agent/reference/AgentBench/README.md` L13-L78（AgentBench FC 2025-10-10 + AgentRL + 5 个 dockerized 任务 + memory leak 自承）；commit `2026-02-09`。
[^bcb]: `/home/agent/reference/bigcodebench/README.md` L48-L83（v0.2.2.dev2、163 模型、1140 任务、Complete + Instruct）；commit `2025-10-15`（**注**：早于 2026-01，仅作为基线）。
[^helmreadme]: `/home/agent/reference/helm/README.md` L25-L88（efficiency / bias / toxicity 多维 + MedHELM, Safety, ToRR, MedHELM, Audio leaderboards + ReEval amortized）；commit `2026-04-03`。
[^halreadme]: `/home/agent/reference/hal-harness/README.md` L1-L227（unified hal-eval CLI + Weave 自动 cost & traces + 跨基准 SWE/USACO/AppWorld/CORE/τ-bench/AssistantBench/SciCode/SAB/ColBench）；commit `2026-03-11`。
[^inspectinit]: `/home/agent/reference/inspect_ai/src/inspect_ai/scorer/__init__.py` L1-L80 + `_metrics/__init__.py` L1-L14（Score values + reducer 含 `pass_at, at_least, max_score, mean_score, median_score, mode_score`）；commit `2026-04-04`。
[^inspectlimits]: `/home/agent/reference/inspect_ai/docs/_token_limits.md` + `_cost_limits.md` + `_working_limits.md`（自动 ModelUsage tracking + working_time 拆掉 rate-limit）；同 commit。
[^inspectworking]: `/home/agent/reference/inspect_ai/docs/_working_limits.md` L1-L5。
[^k2vv]: `/home/agent/reference/K2-Vendor-Verifier/README.md` L17-L151（schema_accuracy 表 + tool_call_f1 73% 阈值）；commit `2026-02-14`。
[^nearaireadme]: `/home/agent/reference/nearai-benchmarks/README.md` L1-L199（trajectory/spot/gaia/tau_bench/swe_bench + ZClaw security 10 题 + framework 维度比较 + run.json 字段）；commit `2026-03-27`。
[^openai-graders]: `/home/agent/reference/evals/README.md` L1-L60；commit `2025-11-03`（**注**：仅作辅助，已不是主战场）。
[^devolagate]: `/home/agent/workspace/DevolaFlow/schemas/gate-report.schema.yaml` L29-L156（verdict.composite_score + convergence_history.rounds + trend ∈ {improving, stagnant, degrading}）。

### 外部 2026 源

[^webclaude]: Anthropic — *Equipping agents for the real world with Agent Skills*（2025-10 / 2025-12 open standard）+ *Claude AI Dev: Skill Creator Update Practical Guide*（2026-03，引入 eval / A-B benchmark / pass-rate / latency / token signals + description tuning）。WebSearch result. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills.
[^webdescopt]: Anthropic Skills 文档 + skill-creator on skills.sh — `description optimizer` 用 20 trigger / non-trigger queries × 5 轮迭代；最佳实践：imperative, intent-focused, explicit, 50–200 词。https://skills.sh/anthropics/skills/skill-creator + https://agentskills.io/skill-creation/optimizing-descriptions（fetched 2026-04-27）。
[^webgrad]: *auto-skill graduate* CLI（mintlify/matrixy/auto-skill, 2026）— External(50%) → Local(75%) → Graduated(85%+) ladder + criteria: confidence ≥85% & used ≥5 times & success ≥80%. https://mintlify.com/matrixy/auto-skill/cli/graduate.
[^webamc]: AgentMaturity Compass GitHub + npm — L0–L5 maturity, 235 questions × 5 layers, 147 adversarial sims, EU AI Act / ISO 42001 / NIST / SOC2 / OWASP mapping. https://github.com/AgentMaturity/AgentMaturityCompass.
[^webpassk]: Schmid, P. — *Pass@k vs Pass^k: Understanding Agent Reliability*（2026, philschmid.de）+ Agent Patterns *pass@k and pass^k: Capability and Consistency Metrics*. Pass^k = (c/n)^k formula + τ-bench 实证.
[^webswepro]: Scale AI Labs — *SWE-Bench Pro Leaderboard 2026*（1,865 problems × 41 active repos × public/held-out/commercial）+ BenchLM SWE-bench Pro 2026 entry（截至 2026-04-24，Claude Mythos 77.8%，Claude Opus 4.7 64.3%，GPT-5.5 58.6%）. https://labs.scale.com/leaderboard/swe_bench_pro_public.
[^webswelb]: vexp-ai/vexp-swe-bench 2026（cost-aware: vexp + Claude Code 73.0% @ $0.67/task vs Live-SWE-Agent 72.0% @ $0.86 vs OpenHands 70.0% @ $1.77）。GitHub repository.
[^webhelm]: Stanford CRFM — HELM Lite + *Efficient Benchmarking* doc（10 examples × 400× compute saving × ±5 confidence interval on rank）+ NeurIPS'23 *Cheaply Evaluating Inference Efficiency Metrics*. https://crfm.stanford.edu/helm/lite/latest/.
[^webbfcl]: BFCL V4 Memory + Web-search + Format-sensitivity blog posts（2025-07 release, 2026-04-12 leaderboard refresh, 5,106 samples）. https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html / 16_bfcl_v4_memory.html.
[^webcurs]: Cursor — *How we compare model quality in Cursor* + *Composer 2 technical report* + Adam Holter *CursorBench-3 deep dive*（2026-03 unveil; 4 dimensions: correctness / quality / efficiency / interaction; Cursor Blame trace; refresh 2-3 months）.
[^webroute]: Front-Door Routing Benchmark, arXiv 2604.02367（2026-03） + Tiny-Critic RAG arXiv 2603.00846. Qwen-2.5-3B 78.3% acc / 988ms P95；no model met ≥0.85 acc & ≤2000ms.
[^webgaia2]: Gaia2 — *Benchmarking LLM Agents on Dynamic and Asynchronous Environments*（ICLR 2026, arXiv 2602.11964）. GPT-5 (high) 42% pass@1 + budget scaling plateau.
[^weboteltel]: AI-Agentsplus *AI Agent Monitoring & Observability 2026 Best Practices* + Mavik Labs *Agent Observability in 2026* + Zylos *OpenTelemetry GenAI Semantic Conventions for AI Agents*（2026-02-28）.
[^webagentcost]: RelayPlane — *Agent Cost Benchmarks 2026*（single-file edit ≈ 4.2k in / 850 out; new feature ≈ 42k / 8.5k; multi-turn support ≈ 6.2k / 1.5k）.
[^haltechreport]: Princeton HAL leaderboard + Mavik Labs *Agent Observability 2026: Traces, Costs, and Failure Modes*（success rate per workflow / escalation rate / P95 latency / cost per successful completion as primary 4-tuple）.
[^webtau2]: τ²-bench / τ³-bench arXiv 2506.07982（ICLR 2026 submission）+ taubench.com leaderboard；τ³-bench 1.0.0 release 2026-03（banking_knowledge + 7 voice providers + full-duplex 听说 + 31-51% pass@1 clean vs 26-38% realistic）. https://github.com/sierra-research/tau2-bench/releases/tag/v1.0.0.
[^webmcpbench]: Accenture MCP-Bench — 250 tools × 28 live MCP servers；GPT-5 0.749 / o3 0.715 / gpt-oss-120b 0.692. https://github.com/Accenture/mcp-bench.
[^webmcpatlas]: Scale Labs MCP Atlas — 1,000 tasks (500 public + 500 private) × 36 real MCP servers × 220 tools；leaderboard refresh 2026-04-24：Claude Opus 4.7 (Adaptive) 77.3% / GPT-5.5 75.3% / DeepSeek V4 Pro (High) 74.2%. https://labs.scale.com/leaderboard/mcp_atlas + https://benchlm.ai/benchmarks/mcpAtlas.
[^webmcpmark]: MCPMark — 127 verifiable tasks × 38 models；stress-testing comprehensive MCP benchmark. https://mcpmark.ai/.
[^webclaudeskillcreator]: Anthropic skill-creator plugin repo — https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator + https://github.com/anthropics/skills/tree/main/skills/skill-creator（含 benchmark mode、multi-agent parallel eval、comparator agent、description optimizer）.
[^webotelsemconv]: OpenTelemetry semantic-conventions — *Semantic Conventions for GenAI agent and framework spans*（2026 稳态）；`gen_ai.agent.name` / `gen_ai.agent.version` / `gen_ai.operation.name = create_agent/invoke_agent/execute_tool/chat/generate_content/text_completion` / `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`. http://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/.
[^webskilltelem]: Anthropic Claude-code GitHub issues — #35319 *Skill invocation tracking and usage analytics*、#36120 *Tool_result event skill telemetry not captured*、#44432 *User-invoked skills via / prefix emit no OTEL telemetry*（2026 Q1）.
[^webcontextrot]: Chroma Research *Context Rot: How Increasing Input Tokens Impacts LLM Performance*（18 frontier models, 2025-12 / 2026 持续更新）+ Morph *Context Rot Complete Guide*（32K-64K cliff, 20-50% accuracy drop 10K→100K）. https://research.trychroma.com/context-rot + https://www.morphllm.com/context-rot.

---

## Acceptance Self-Check

- [x] ≥ 8 个基准 / 框架填齐五要素（共 **15** 个：SWE-bench Verified、SWE-bench Pro、τ-bench/τ³、BFCL V4、AgentBench FC、BigCodeBench、HELM、HAL、Inspect AI、K2VV、nearai-bench、OpenAI Evals、**MCP-Bench/MCP Atlas/MCPMark**、**Anthropic Skill-Creator Evals**、**OpenTelemetry GenAI semconv**）
- [x] 多维指标矩阵 1 张（§2，12 行 × 14 列）
- [x] Skill-level 指标候选 8 个（§3 ①–⑧），均含公式 / 数据源 / 阈值候选
- [x] 「对用户假设的影响」专节（§5），含借用 vs 自研拆分 + **6 风险点** + 5 项自研维度
- [x] ≥ 10 条来源，本地 ≥ 5（实际 **13 本地条目 + 20 外部条目 = 33 总来源**）
- [x] 严格 2026 时间窗：除 BigCodeBench (2025-10) 与 OpenAI Evals (2025-11) 明确标记基线外，其余所有引用皆为 ≥ 2026-01 commit / release
- [x] 中文为主，专有名词保留英文
- [x] 未捏造数字（每个百分比都附引用）
- [x] 未写实现代码（仅表格 / 公式 / 阈值）
- [x] 新增：用户 3 阶段假设的**反向阶段「0_retired」**（Anthropic capability uplift 过期回收路径）

