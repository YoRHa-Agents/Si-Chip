---
task_id: R7
scope: DevolaFlow + NineS + 本地 reference 仓库 可直接复用能力盘点
upstream_count: 21
integration_points: 28
self_build_surface_count: 6
risk_count: 9
last_updated: 2026-04-27
provenance: "L0-direct fallback after subagent capacity exhausted"
related_artifacts:
  - r6_metric_taxonomy.md
  - .local/feedbacks/feedbacks_for_research/feedback_for_research_v0.0.1.md
---

# R7 · DevolaFlow + NineS + Reference Repos 可复用能力盘点

> v0.0.2 · 用户 feedback：必须结合 DevolaFlow 与 NineS 能力，从更多维度对 Skill 进行分解。
> 中文为主，专有名词 / API 名 / CLI 保留英文。

---

## 0. TL;DR（给决策者的 5 条）

1. **Si-Chip 至少 80% 的"测试 + 指标驱动"基础设施可以直接复用现有上游**：DevolaFlow 提供 gate scoring、entropy/staleness、memory router、compression、template engine、learnings + decay、pre-decision、AC generator、NineS bridge、agent workspace 等 ≥ 13 个直接相关模块；NineS CLI 提供 7 个 subcommand 闭环（eval / collect / analyze / self-eval / iterate / install / update）。
2. **Si-Chip 真正需要自研的"薄层"只有 6 块**：Skill 级 schema、28 子指标桥接器、Stage classifier、半退役评审器、Router-test harness、工厂模板（templates/）。其余皆为复用。
3. **DevolaFlow `task_adaptive_selector.select_context` + `apply_round_escalation` 直接对应 R8 的"思考深度"档位**——Si-Chip 不需自己实现 plan/agent/round 等档位切换，调用即可。
4. **DevolaFlow `entropy_manager` + `learnings.decay_confidence` 共同支撑 Stage 0 半退役判定**：drift 信号 + staleness + decay 三合一，无需自研。
5. **OpenSpec / DSPy / ACE / ContextOS / Superpowers** 五个 reference 仓库分别覆盖 propose-apply-verify 工作流、prompt 编译、skillbook 自演化、context-as-OS 与 skill marketplace 分发；Si-Chip 第一版只**学其设计哲学**，不集成。

---

## 1. DevolaFlow — 直接对接 17 处

### 1.1 Gate / 评分核心

| # | 模块 | 入口 | 输入 | 输出 | Si-Chip 对接位置 | 是否需封装 | 路径:行 |
|---|---|---|---|---|---|---|---|
| 1 | `gate/scorer.py` | `score_dimension(findings)` / `composite_score(dims, weights)` | `list[Finding]` / `dict[str, float]` | `float` 0-100 | R6 D1 + Stage gate 闸门评分（直接对应 T1/T3 + 复合分） | 直接调用 | `gate/scorer.py:110-180` [^df-gate-scorer] |
| 2 | `gate/models.py` | `Severity` / `ProfileConfig` / `DimensionScore` | dataclass | dataclass | R6 阈值结构 + Stage 通过/失败/转移条件直接复用；不要重新发明 blocker/critical/major/minor/info | 直接复用类型 | `gate/models.py:12,87,158,175-187` [^df-gate-models] |
| 3 | `gate/profiles.py` | `Profile.relaxed/standard/strict/audit` | name | profile | Si-Chip 阶段 gate 开始可借 `relaxed`，到 Stage 3+ 用 `standard`，Stage 5 用 `strict` | 直接 | `gate/profiles.py` [^df-gate-profiles] |
| 4 | `gate/convergence.py` + `gate/ratchet.py` + `gate/cycle_detector.py` | convergence loop / 单调上升 ratchet / 重复模式检测 | round history | decision | Stage 2/3/4 的 gen-verify 收敛闭环直接复用；R6 G4 model_version_stability 输入 | 直接 | `gate/{convergence,ratchet,cycle_detector}.py` [^df-gate-convergence] |
| 5 | `gate/budget.py` + `gate/complexity_detector.py` | budget 检查 + over-complexity 检测 | task | budget action | Stage 3 / Stage 4 跃迁时校验 token / 步数预算；R6 D3 数据源 | 直接 | `gate/{budget,complexity_detector}.py` [^df-gate-budget] |
| 6 | `gate/reinforcement.py` | reinforcement 规则注入 | prior findings | dispatch ctx | Stage gate 失败时把 top-N 反馈注入下一轮 (R3/R6 都需要) | 直接 | `gate/reinforcement.py` [^df-gate-reinforcement] |

### 1.2 退役 / staleness / 半退役（Stage 0 关键）

| # | 模块 | 入口 | 输入 | 输出 | Si-Chip 对接 | 是否需封装 | 路径:行 |
|---|---|---|---|---|---|---|---|
| 7 | `entropy_manager.py` | `DocFreshness.scan(root)` / `DeviationScanner.scan(...)` / `cleanup(...)` | dir tree + retention rules | `DocFreshnessReport` / `DeviationReport` / `DryRunReport` or `ApplyReport` | R6 V3 drift_signal + V4 staleness_days；Stage 0 半退役评审 / 完全退役 cleanup | 薄包装 (改 retention 规则) | `entropy_manager.py:1-90` [^df-entropy] |
| 8 | `learnings.py` | `decay_confidence` / `consolidate_session` / `pin_learning_for_session` / `prune_learnings` / `get_learnings_stats` | jsonl path | jsonl + stats | Stage 0 半退役状态跟踪：长期未触发 → confidence 衰减 → 进入 deprecation review；同时供 R6 V4 直接读 last_accessed | 直接 | `learnings.py:74,189,473,610,762,836,870` [^df-learnings] |
| 9 | `feedback.py` | feedback tracking | feedback record | tracker entry | Si-Chip 把 R6 7 维 finding → feedback 落盘；与 `.local/feedbacks/` 目录直接连通 | 直接 | `feedback.py` [^df-feedback] |

### 1.3 Context 经济性（D2）

| # | 模块 | 入口 | 输入 | 输出 | Si-Chip 对接 | 是否需封装 | 路径:行 |
|---|---|---|---|---|---|---|---|
| 10 | `compression_pipeline.py` | `CompressionPipeline.run(payload, context)` + `make_stage(...)` | text/dict | `PipelineRunResult` | C2/C3 压缩前/后 token 比；C4 footprint baseline；可作 D2 全维 baseline | 直接 | `compression_pipeline.py:108-490` [^df-compression] |
| 11 | `compressor.py` | `wrap_data_envelope` / `unwrap_data_envelope` / `detect_data_channel_instructions` | text | text + metadata | C3 resolved tokens 包装 / 拆包；D2 子指标补丁 | 直接 | `compressor.py:245-323` [^df-compressor] |

### 1.4 Routing 测试床（D6 / R8 直接复用）

| # | 模块 | 入口 | 输入 | 输出 | Si-Chip 对接 | 是否需封装 | 路径:行 |
|---|---|---|---|---|---|---|---|
| 12 | `memory_router/router.py` | `MemoryRouter.lookup_case(query, ...)` / `lookup_case_strict(...)` | query + index.yaml | `MemoryCase` 或 None | R5 router_floor 测试床的"deterministic baseline"（与小模型路由对照）；R6/R7 routing latency / overhead 直接测 | 直接（数据层） | `memory_router/router.py:95-335` [^df-router-router] |
| 13 | `memory_router/cache.py` | `MemoryCase` / `is_ttl_expired` / `is_version_stale` / `build_case_from_dict` | yaml row | dataclass | C6 scope_overlap 数据池；R8 description_competition 多 skill 入口 | 直接 | `memory_router/cache.py:28-260` [^df-router-cache] |
| 14 | `shell_proxy/{registry,proxy,commands}.py` | RTK CLI 拦截 + WHITELIST | shell call | wrapped output | （次要）若 Stage 3 提供 CLI 表面，可直接复用拦截+压缩；不在 MVP | 包装 (Stage 3+) | `shell_proxy/*.py` [^df-shell-proxy] |

### 1.5 NineS 集成 + 分析（直接桥接 NineS CLI）

| # | 模块 | 入口 | 输入 | 输出 | Si-Chip 对接 | 是否需封装 | 路径:行 |
|---|---|---|---|---|---|---|---|
| 15 | `nines/scorer.py` | `nines_dimension_scores(NinesScorerConfig, artifact_path)` + `run_nines_eval` / `run_nines_analyze` | scorer config + path | dict[dim → float] | T1/T3/G3 接 NineS eval；与 gate 4 维 (test_quality / code_review / architecture / benchmark) 桥接 | 直接 | `nines/scorer.py:34-141` [^df-nines-scorer] |
| 16 | `nines/researcher.py` | `collect_research(query, source, limit)` / `analyze_target(target, depth)` | query / path | json | C6 scope_overlap 数据池：`collect` + `analyze` 拉同类 skill 描述 | 直接 | `nines/researcher.py:1-90` [^df-nines-researcher] |
| 17 | `nines/advisor.py` | `get_research_advice(NinesAdvisorConfig, target_path)` | path | recommendations + raw | Stage 1 → 2 跃迁前给"下一步建议" | 直接 | `nines/advisor.py:1-90` [^df-nines-advisor] |
| 18 | `nines/detector.py` | `detect_nines()` / `ensure_nines(auto_install=False)` | (none) | `NinesStatus(available, version, path, capabilities)` | Si-Chip 启动时探测 nines 是否在 PATH；缺失则降级 | 直接 | `nines/detector.py:33-90` [^df-nines-detector] |

### 1.6 Pre-Decision / Workflow Selection / AC

| # | 模块 | 入口 | 输入 | 输出 | Si-Chip 对接 | 是否需封装 | 路径:行 |
|---|---|---|---|---|---|---|---|
| 19 | `pre_decision/recommend.py` | `recommend_workflow(text)` | user intent | `Recommendation` 列表 + 置信度 | Stage 1 → 2 跃迁前帮用户选迭代 workflow | 直接 | `pre_decision/recommend.py:258-330` [^df-pre-decision] |
| 20 | `pre_decision/{checklist,validate,freeze}.py` | `auto_detect(repo_path)` / `validate_consistency(checklist)` / `freeze_config(...)` | repo path | checklist + validation | Stage 5 治理化字段冻结 | 直接 | `pre_decision/{checklist,validate,freeze}.py` [^df-pre-decision] |
| 21 | `ac_generator.py` | acceptance criteria 生成 | task spec | AC list | Stage 2 自动生成 eval 之前的 AC 草稿 | 直接 | `ac_generator.py` [^df-ac-gen] |
| 22 | `task_adaptive_selector.py` | `select_context(task_type, round_num=N)` / `apply_round_escalation` / `match_profile` | task spec | dispatch ctx + 思考深度档 | **R8 router-test 的"思考深度"档位 = `select_context` 的 round / plan_mode / model_hint 组合**——直接复用 | 直接 | `task_adaptive_selector.py:844,1011,1066,1088` [^df-tas] |

### 1.7 Template Engine / Local Workspace（Si-Chip 工厂模板的 IR）

| # | 模块 | 入口 | 输入 | 输出 | Si-Chip 对接 | 是否需封装 | 路径:行 |
|---|---|---|---|---|---|---|---|
| 23 | `template_engine/parser.py` + `models.py` | `parse_template(yaml_path)` / `WorkflowTemplate` IR | yaml | dataclass tree | Si-Chip"工厂模板"直接复用此 IR — Stage / Wave / Gate / Loop 全部已有 dataclass | 直接 | `template_engine/{parser,models}.py` [^df-template-parser] |
| 24 | `template_engine/validator.py` | `validate_template(template)` (schema / stage refs / loop termination / gate completeness / reachability / orphan / dependency lattice) | template | `ValidationResult` | Si-Chip 工厂模板上线前自检 | 直接 | `template_engine/validator.py:55-180` [^df-template-validator] |
| 25 | `template_engine/runtime.py` + `composer.py` | `select_stages_for_runtime(...)` / `evaluate_skip_condition` / `SequenceOp/ParallelOp/ChoiceOp/LoopOp/GateOp` | template + ctx | ordered stages | Si-Chip 真正的"按阶段跑"运行时；不要自己写迭代器 | 直接 | `template_engine/{runtime,composer}.py` [^df-template-runtime] |
| 26 | `template_engine/registry.py` | `TemplateRegistry.discover/load_template/register` | dir | template metadata | Si-Chip 模板目录化 + 多版本管理 | 直接 | `template_engine/registry.py:21-138` [^df-template-registry] |
| 27 | `template_engine/inheritance.py` | `resolve_inheritance(child, parent)` | templates | merged template | Skill 模板继承（baseline / domain-specific / project-specific 三层） | 直接 | `template_engine/inheritance.py` [^df-template-inheritance] |
| 28 | `local/{compiler,workspace,merge,drift}.py` | `RuleCompiler` / scaffold / drift 检测 | rules + targets | compiled outputs + hashes | Si-Chip 输出 SKILL.md / docs 时直接复用 | 直接 | `local/*.py` [^df-local] |

---

## 2. NineS — 7 subcommand 全覆盖

| # | Subcommand | 接口 | Si-Chip 对接 | 路径 |
|---|---|---|---|---|
| 1 | `nines eval` | `nines eval <task-or-suite> [--scorer TYPE] [--format FORMAT] [--sandbox] [--seed N]` | T1 pass_rate / T2 pass_k / T3 baseline_delta 数据源；`--seed` + 多次跑实现 Pass^k | `commands/eval.md` [^nines-eval] |
| 2 | `nines self-eval` | `nines self-eval [--dimensions DIM,...] [--baseline VERSION] [--compare] [--report]` | G4 model_version_stability / Stage 5 治理化对比；`--baseline + --compare` 是 Skill 升级时的核心命令 | `commands/self-eval.md` [^nines-self-eval] |
| 3 | `nines iterate` | `nines iterate [--max-rounds N] [--convergence-threshold F] [--dry-run]` | Stage 2/3/4 收敛闭环；与 DevolaFlow `gate/convergence.py` 联动 | `commands/iterate.md` [^nines-iterate] |
| 4 | `nines analyze` | `nines analyze --target-path <path> [--depth shallow|deep]` | C6 scope overlap + V3 drift；`deep` 模式给 Stage 0 半退役提供证据 | `commands/analyze.md` [^nines-analyze] |
| 5 | `nines collect` | `nines collect --source <github|arxiv|...> --query <q> --max-results <n>` | 自动抓 reference / 同类 skill 描述池供 C6 使用 | `commands/collect.md` [^nines-collect] |
| 6 | `nines install` / `nines update` | install / update self | Si-Chip CI 验证 NineS 可用性；与 `nines/detector.py::ensure_nines` 联动 | `commands/{install,update}.md` [^nines-install] [^nines-update] |

> **关键观察**：DevolaFlow `nines/scorer.py::nines_dimension_scores` 已经把 NineS 4 维度（test_quality / code_review / architecture / benchmark）桥接到 gate scoring。Si-Chip 不需要自己写 NineS 适配层。

---

## 3. 本地 reference 仓库 — 5 个直接相关

| # | 仓库 | 关键文件 | Si-Chip 借鉴点 | 集成深度 |
|---|---|---|---|---|
| 1 | OpenSpec | `/home/agent/reference/openspec/README.md:36-69` | `/opsx:propose → /opsx:apply → /opsx:archive` 工作流 = Si-Chip Stage 1 → 2 → 3 跃迁的成熟范式；`openspec init` + 25+ 工具支持 | 学设计哲学；不集成 | [^opsx-readme] |
| 2 | DSPy | `/home/agent/reference/dspy/README.md:14-18,49-51` | `compile()` + GEPA reflective optimizer；Skill description 优化器的方法学（与 Anthropic skill-creator description optimizer 双源） | 学方法学 | [^dspy-readme] |
| 3 | ACE / Agentic Context Engine | `/home/agent/reference/agentic-context-engine/README.md:17-26,92-112` | Skillbook 自演化；49% token reduction + 20-35% 提升 + tau2 pass^k 倍增 | 学结果 + 引用为基线 | [^ace-readme] |
| 4 | ContextOS | `/home/agent/reference/ContextOS/README.md:18-50,52-75` | Cognition Layer (Active Forgetting / Synthesis Detection / Reasoning Depth Calibration / Unknown Unknown Sensing) + Retrieval Router (live/warm/cold churn class) + Index Lifecycle Manager | 学高阶生命周期 | [^contextos-readme] |
| 5 | Superpowers | `/home/agent/reference/superpowers/README.md:1-15,27-63` | 跨工具 marketplace 分发：Claude Code / Cursor / Codex / OpenCode / GitHub Copilot CLI / Gemini CLI 一键 install | 学分发，不集成 | [^superpowers-readme] |

> **次要参考**（仅在 Stage 3 CLI 表面成熟时再考虑）：RTK (`/home/agent/reference/rtk`)、claude-code-router (`/home/agent/reference/claude-code-router`) — 已在 R4 详述，R7 不重复。

---

## 4. Anthropic Skill Creator — 外部直接对接

| # | 资源 | URL | Si-Chip 对接 |
|---|---|---|---|
| 1 | `skills/skill-creator/SKILL.md` | `https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md` | Stage 2 工厂模板的事实标准；evals.json / grading.json / history.json / benchmark.md / benchmark.json 五件套 |
| 2 | `scripts/improve_description.py` | 同仓库 | R3 trigger_F1 + R4 near_miss_FP 的 description optimizer；`claude -p` subprocess 调用，不需 ANTHROPIC_API_KEY |
| 3 | `scripts/run_loop.py` | 同仓库 | R8 router-test 的 trigger eval loop 模板；60% train / 40% test / 5 iterations |
| 4 | `eval-viewer/generate_review.py` + `aggregate_benchmark.py` | 同仓库 | benchmark 聚合输出 mean ± stddev + delta；MVP 8 子指标的可视化 |
| 5 | API `/v1/skills/{id}/versions` | console.anthropic.com/docs/en/api/beta/skills/versions | Stage 5 版本治理；create / list / retrieve / delete |
| 6 | beta header `skills-2025-10-02` / `fast-mode-2026-02-01` | 同上 | R8 思考深度档 (fast vs default vs extended thinking) |

---

## 5. Si-Chip 第一版的最小上游依赖集

> 满足 MVP 8 子指标 + 6 个 Stage + 半退役 + 工厂模板 + Router-test 的最小集合。

| Layer | 必须 | 可选 |
|---|---|---|
| 评分 | DevolaFlow `gate/scorer.py` + `gate/models.py` + `gate/profiles.py` | `gate/convergence.py` (Stage 3+) / `gate/ratchet.py` (Stage 4+) |
| 退役 | DevolaFlow `entropy_manager.py` + `learnings.py` | `feedback.py` (Stage 5+) |
| Context | DevolaFlow `compression_pipeline.py` (Stage 3+) | `compressor.py` |
| Routing 测试 | DevolaFlow `task_adaptive_selector.select_context` + `memory_router/cache.MemoryCase` | `memory_router/router.MemoryRouter` (deterministic baseline) |
| NineS | NineS CLI `eval` + `self-eval` + `iterate`；DevolaFlow `nines/scorer.py` + `nines/detector.py` | `nines/researcher.py` + `nines/advisor.py` |
| Workflow / 模板 | DevolaFlow `template_engine/{parser,validator,runtime,registry}.py` | `inheritance.py` (Stage 5+) |
| Pre-Decision | DevolaFlow `pre_decision/recommend.py` + `ac_generator.py` | `checklist/validate/freeze` (Stage 5+) |
| 数据源 | OTel GenAI semconv | LangSmith / Phoenix |
| Skill 工厂模板源 | Anthropic skill-creator (evals.json / grading.json / history.json) | OpenSpec / DSPy / ACE 设计学 |

> **共 12 个必备上游依赖**；其余 9 个是可选 (Stage 3+/4+/5+)。

---

## 6. Si-Chip 必须自研的"薄层"（共 6 块）

| # | 自研模块 | 责任 | 估计行数 | 不能复用的原因 |
|---|---|---|---|---|
| 1 | `si_chip/schema/skill_profile.py` | `SkillProfile` dataclass：把 R6 28 个子指标 + Stage + 形态 + telemetry 字段统一 | ~150 行 | DevolaFlow 没有 Skill 级聚合 schema |
| 2 | `si_chip/metrics/bridge.py` | 把 OTel attribute / Skill Creator JSON / NineS 输出 → R6 子指标的桥接 | ~250 行 | 需要 Si-Chip 自己定义 7 维聚合规则 |
| 3 | `si_chip/stage/classifier.py` | 输入 SkillProfile → 输出 (stage 0-5, confidence, next_action, risk_flags) | ~200 行 | Stage 状态机是 Si-Chip 独有逻辑 |
| 4 | `si_chip/stage/half_retire_review.py` | Stage 0 半退役评审：消费 T3 / V3 / V4 + 是否仍有性能优势 | ~120 行 | 半退役判定逻辑 R6 §0 第 1 条专属 |
| 5 | `si_chip/router_test/harness.py` | R8 router-test 协议：跨模型 × 思考深度 × 场景 × 数据集；输出 R5 router_floor | ~300 行 | DevolaFlow `task_adaptive_selector` 提供档位但不提供 harness |
| 6 | `si_chip/templates/` | 工厂模板目录（`evaluated_skill_template.yaml` / `productized_template.yaml` / `routed_template.yaml` / `governed_template.yaml` / `half_retire_template.yaml` / `retirement_template.yaml`） | ~600 行 yaml | 模板 IR 复用 DevolaFlow，但内容是 Si-Chip 专有 |

> 总计 **~1620 行新代码 + 600 行 yaml**。其余全部是上游 API 调用胶水。

---

## 7. 集成风险清单

| # | 风险 | 严重度 | 缓解 |
|---|---|---|---|
| 1 | NineS CLI 不在 PATH | M | `nines/detector.ensure_nines(auto_install=False)` 自动降级；R6 受影响子指标用 placeholder |
| 2 | Python 3.12 + dataclass 强依赖（DevolaFlow） | L | Si-Chip 用同等 Python，统一最小版本 |
| 3 | DevolaFlow `compression_pipeline` API 变化 | M | 锁定 v9.x；CI 在 PR 时跑 `import` smoke test |
| 4 | OTel GenAI semconv 仍处 development | M | `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` 显式启用；Si-Chip 提供 fallback attribute name 映射表 |
| 5 | Anthropic Skill Creator 文件 schema 演化 | M | 从 history.json 字段读取并验证；不验证就报错而非默写 |
| 6 | tau-bench / BFCL 数据集大小 | L | Si-Chip 只引用其方法，不下载完整数据 |
| 7 | DevolaFlow `entropy_manager` 默认 staleness 30 天 | L | Si-Chip 配置层覆盖；Stage 0 默认 90 天，与用户预期对齐 |
| 8 | DevolaFlow `learnings.py` 与 `.local/memory/operational.jsonl` 共享路径 | M | Si-Chip 写自己的 `.local/memory/skill_profiles/<name>/learnings.jsonl` 子目录，避免覆盖 |
| 9 | Cursor Composer / Anthropic Haiku 模型 ID 演化（R8 router-test） | M | Si-Chip 在 router_test config 中使用 alias，不硬编码 model id |

---

## 8. 5 条关键发现 (Top-5)

1. **DevolaFlow + NineS 共同提供了 ≥ 17 个直接可用的 API**，Si-Chip 真正自研只需 6 个薄层模块（~1620 行 Python + ~600 行 yaml）。这与用户 feedback "结合 DevolaFlow 和 NineS 的能力" 完全契合。
2. **`task_adaptive_selector.select_context(task_type, round_num=N)` 是 R8 router-test 的现成档位机制**：plan_mode / round / model_hint 三个旋钮已存在，Si-Chip 直接调用即可测试 Sonnet/Composer/浅思考。
3. **`entropy_manager` + `learnings.decay_confidence` + `feedback.py` 三件套覆盖 Stage 0 全部需求**：drift 信号 / staleness / confidence decay / feedback tracking — 半退役评审无需自研。
4. **Template Engine 是 Si-Chip"工厂模板体系"的现成 IR**：parser / validator / runtime / composer / registry / inheritance 6 个模块已就绪；Si-Chip 只需要在 `templates/` 目录下产出 6 个 yaml 模板即可启动。
5. **本地 reference 仓库（OpenSpec / DSPy / ACE / ContextOS / Superpowers）只学设计哲学，不集成**：减少表面积，符合用户 feedback 中"Si-Chip 重点不是部署/集成/注册模板"的明确收窄。

---

## 9. 来源清单

### 9.1 DevolaFlow 路径:行号

[^df-ac-gen]: `/home/agent/workspace/DevolaFlow/src/devolaflow/ac_generator.py`
[^df-compression]: `/home/agent/workspace/DevolaFlow/src/devolaflow/compression_pipeline.py:108-490`
[^df-compressor]: `/home/agent/workspace/DevolaFlow/src/devolaflow/compressor.py:245-323`
[^df-entropy]: `/home/agent/workspace/DevolaFlow/src/devolaflow/entropy_manager.py:1-90` (`DocFreshness` / `DeviationScanner` / `cleanup` / `DEFAULT_STALENESS_THRESHOLD_DAYS=30`)
[^df-feedback]: `/home/agent/workspace/DevolaFlow/src/devolaflow/feedback.py`
[^df-gate-budget]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/{budget,complexity_detector}.py`
[^df-gate-convergence]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/{convergence,ratchet,cycle_detector}.py`
[^df-gate-models]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/models.py:12,87,158,175-187`
[^df-gate-profiles]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/profiles.py`
[^df-gate-reinforcement]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/reinforcement.py`
[^df-gate-scorer]: `/home/agent/workspace/DevolaFlow/src/devolaflow/gate/scorer.py:110-180`
[^df-learnings]: `/home/agent/workspace/DevolaFlow/src/devolaflow/learnings.py:74,189,473,610,762,836,870`
[^df-local]: `/home/agent/workspace/DevolaFlow/src/devolaflow/local/{compiler,workspace,merge,drift}.py`
[^df-nines-advisor]: `/home/agent/workspace/DevolaFlow/src/devolaflow/nines/advisor.py:1-90`
[^df-nines-detector]: `/home/agent/workspace/DevolaFlow/src/devolaflow/nines/detector.py:33-90`
[^df-nines-researcher]: `/home/agent/workspace/DevolaFlow/src/devolaflow/nines/researcher.py:1-90`
[^df-nines-scorer]: `/home/agent/workspace/DevolaFlow/src/devolaflow/nines/scorer.py:34-141`
[^df-pre-decision]: `/home/agent/workspace/DevolaFlow/src/devolaflow/pre_decision/{recommend,checklist,validate,freeze}.py:258-330`
[^df-router-cache]: `/home/agent/workspace/DevolaFlow/src/devolaflow/memory_router/cache.py:28-260`
[^df-router-router]: `/home/agent/workspace/DevolaFlow/src/devolaflow/memory_router/router.py:95-335`
[^df-shell-proxy]: `/home/agent/workspace/DevolaFlow/src/devolaflow/shell_proxy/{registry,proxy,commands}.py`
[^df-tas]: `/home/agent/workspace/DevolaFlow/src/devolaflow/task_adaptive_selector.py:844,1011,1066,1088`
[^df-template-inheritance]: `/home/agent/workspace/DevolaFlow/src/devolaflow/template_engine/inheritance.py:22-110`
[^df-template-parser]: `/home/agent/workspace/DevolaFlow/src/devolaflow/template_engine/{parser,models}.py`
[^df-template-registry]: `/home/agent/workspace/DevolaFlow/src/devolaflow/template_engine/registry.py:21-138`
[^df-template-runtime]: `/home/agent/workspace/DevolaFlow/src/devolaflow/template_engine/{runtime,composer}.py`
[^df-template-validator]: `/home/agent/workspace/DevolaFlow/src/devolaflow/template_engine/validator.py:55-180`

### 9.2 NineS

[^nines-analyze]: `/root/.codex/skills/nines/commands/analyze.md`
[^nines-collect]: `/root/.codex/skills/nines/commands/collect.md`
[^nines-eval]: `/root/.codex/skills/nines/commands/eval.md`
[^nines-install]: `/root/.codex/skills/nines/commands/install.md`
[^nines-iterate]: `/root/.codex/skills/nines/commands/iterate.md`
[^nines-self-eval]: `/root/.codex/skills/nines/commands/self-eval.md`
[^nines-update]: `/root/.codex/skills/nines/commands/update.md`

### 9.3 本地 reference 仓库

[^ace-readme]: `/home/agent/reference/agentic-context-engine/README.md:17-112`
[^contextos-readme]: `/home/agent/reference/ContextOS/README.md:18-75`
[^dspy-readme]: `/home/agent/reference/dspy/README.md:14-51`
[^opsx-readme]: `/home/agent/reference/openspec/README.md:36-69`
[^superpowers-readme]: `/home/agent/reference/superpowers/README.md:1-90`
