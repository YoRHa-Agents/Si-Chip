---
title: "Si-Chip Core-Goal Invariant & v0.3.0 Capacity Lifts"
task_id: R11
version: "v0.0.1"
status: "draft"
effective_date: "2026-04-29"
target_spec_bump: "v0.3.0"
authoring_round: "Stage 1 — research only; spec authoring is Stage 2"
language: "zh-CN + en (mixed; technical names in en)"
authoritative_inputs:
  - .local/feedbacks/feedbacks_for_product/feedback_for_v0.2.0.md
  - .local/research/spec_v0.2.0.md
  - .local/research/r6_metric_taxonomy.md
  - .local/research/r9_half_retirement_framework.md
  - .local/research/spec_v0.1.0.md
  - .local/dogfood/2026-04-28/v0.2.0_ship_report.md
  - .local/dogfood/2026-04-29/abilities/chip-usage-helper/eval_pack.yaml
  - .local/dogfood/2026-04-29/abilities/chip-usage-helper/tools/eval_chip_usage_helper.py
  - .local/dogfood/2026-04-29/abilities/chip-usage-helper/round_1/iteration_delta_report.yaml
  - .local/dogfood/2026-04-29/abilities/chip-usage-helper/round_10/iteration_delta_report.yaml
  - templates/basic_ability_profile.schema.yaml
  - templates/iteration_delta_report.template.yaml
  - templates/next_action_plan.template.yaml
  - tools/spec_validator.py
related_artifacts:
  - r6_metric_taxonomy.md       # 7 dim / 37 sub-metric taxonomy this doc must extend additively
  - r9_half_retirement_framework.md   # value-vector lineage (this doc adopts the Normative-axis design)
  - r10_self_registering_skill_roadmap.md   # multi-platform packaging pipeline (this doc proposes per-ability sub-tree)
sources_count: 9
proposes_normative_sections: ["§14 core_goal", "§15 round_kind", "§16 multi-ability layout (informative @ v0.3.0)"]
preserves_normative_sections: ["§3", "§4", "§5", "§6", "§7", "§8", "§11"]   # byte-identical from v0.2.0
forever_out_compliance: "verified — see §3.5 and §11 boundary discussion"
---

# R11 · Core-Goal Invariant & v0.3.0 Capacity Lifts (Si-Chip Spec v0.3.0 design brief)

> 核心修正：**优化的前提是核心目标严格无回退**。每一轮 dogfood 不是去找 "任意效率轴 ≥ +0.05 的便宜 bonus"，而是先证明 "ability 的核心、不可让渡的功能输出仍然 100 % 通过"，再在此基础上拿性能、上下文、路径、路由的净收益。`v0.2.0` 13 轮 dogfood + `chip-usage-helper` 10 轮 dogfood 联合暴露了一个共同失效模式：当 spec 不显式锁定 "core goal"，迭代轮就会自然漂向 measurement-fill —— 这不是恶意，而是激励梯度的方向问题。
>
> 本文是 v0.3.0 spec 的 **research-stage design brief**，覆盖 5 个 v0.3.0 候选改动：(1) `core_goal` 字段 + `core_goal_test_pack` + `core_goal_pass_rate` C0 指标 + 严格无回退 + 失败回滚；(2) `round_kind` 4 值枚举；(3) 多 ability 目录布局；(4) 通用 CJK-aware trigger evaluator；(5) 通用 `eval_skill.py` harness + L4 multi-handler 分析器。
>
> 本文 **不是** spec 本体；spec 本体由 Stage 2 写出，并满足 §9 验收清单。所有 v0.2.0 Normative §3–§11 在 v0.3.0 中保持字节级不变（additivity discipline；同 v0.1.0 → v0.2.0 reconciliation 模式）。

---

## 0. TL;DR

1. **加 `core_goal` 字段**：`BasicAbility` 现有 `intent`（"this ability solves what"，高层叙述）和 `description`（router metadata）都不是可测试的功能契约。新增 `core_goal`：**持久的、不可回退的、可被一组测例验证的功能输出**。
2. **加 `core_goal_test_pack`**：每个 ability 必须定义 ≥3 prompts/cases，每轮 dogfood 必须 100 % 通过；`core_goal_pass_rate` (C0) 任何回退 = round failure，无论其它指标多漂亮。
3. **加 `round_kind` 枚举**：`code_change` / `measurement_only` / `ship_prep` / `maintenance`。`measurement_only` 轮的 iteration_delta 子句放宽为 "monotonicity-only"（无源码变更 → 不要求效率轴改善，仅要求不回退）。这一条直接修复 Si-Chip Round 4–12 的 measurement-fill 失真。
4. **加多 ability 目录布局**：`.local/dogfood/<DATE>/abilities/<id>/round_<N>/` 解锁并行 dogfood；旧布局对 Si-Chip 自身保留向下兼容。
5. **加通用 CJK-aware trigger evaluator + 通用 eval_skill.py harness + L4 multi-handler 分析器**：为下一个 ability（v0.3.x 计划新增 1-3 个）节省 ~600 LoC / ability，并避免 chip-usage-helper R5/R8 单 handler 盲点。
6. **§11 forever-out 合规**：本文所有 5 项均不引入 marketplace / router-model-training / generic-IDE-compat / Markdown-to-CLI converter；`core_goal` 是 **观测层不变量**，不是 distribution surface。
7. **附加约束（c_recommendation）**：C0 应作为 **顶层 invariant** 落 `BasicAbility` 根字段，**不计入** R6 7×37 子指标（保持 R6 frozen count）；详细论证见 §3.4 与 §10.

---

## 1. Problem Statement

### 1.1 The 13-round Si-Chip cycle and the 10-round chip-usage-helper cycle: two natural experiments

Si-Chip v0.2.0 ship report 记录了一个无法掩盖的事实：

> "Round 13 satisfies §4.1 v1_baseline iteration_delta any axis >= +0.05 via the genuine task_quality axis pass_k RECOVERY ... This is the FIRST round (since Round 4) where the iteration_delta clause is satisfied without a measurement-fill bonus flavour. **Rounds 4-12 all used measurement-fill flavours on D5/D2/D3/D6/D7/D4 dimensions**." — `.local/dogfood/2026-04-28/v0.2.0_ship_report.md`, §"Iteration-delta clause satisfaction"

13 轮中有 9 轮（Rounds 4-12）的 iteration_delta 是通过 "本轮新增了对一个之前没测的 sub-metric 的覆盖" 满足的，而不是通过 "本轮真的让 ability 更好用了" 满足的。Round 4 hoist L1+L3+L4，Round 5 hoist U1+U2，……一路到 Round 10 hoist G1 partial proxy。每一轮都合法地满足了 spec §4.1 的 iteration_delta 子句，但 ability 的 **核心功能输出**（"Si-Chip 是否真的让一个新 ability 走完 8 步 dogfood 协议并落 6 件证据"）在这 9 轮中并没有改变。

`chip-usage-helper` 是另一个独立证据。Round 1 的 iteration_delta 是 task_quality +0.80（"chip-usage-helper unlocks a previously impossible task"），是真实的；Round 10 的 iteration_delta 是 latency_path +0.0107（"L2 1.865 -> 1.845 (within noise band)"），是 measurement-fill 的退化形态：噪声窗内的微调被记账为 "正向轴"。

### 1.2 The Round 12 7th-case experiment regression: a near-miss precedent

Si-Chip Round 12 主动添加了一个第 7 个 eval case `evals/si-chip/cases/reactivation_review.yaml`，目的是把 `T2_pass_k` 推过 v2_tightened 的 0.55 阈值。结果该 case 在 SHA-256 deterministic simulator 下 per-case `pass_rate=0.65`，把 7-case 平均从 Round 11 的 0.5478 拉低到 Round 12 的 0.4950 —— **regression -0.0528**。

L0 决定 `PATH=REVERT-ONLY`，Round 13 把第 7 个 case 与 Round 12 baselines 全部 `git rm`，T2_pass_k 字节级恢复到 Round 11 的 0.5477708333333333。

这是一个 **near-miss precedent**：

- 如果 spec 当时已经有 "core_goal_pass_rate 严格无回退" 条款，Round 12 在产生 -0.0528 的同时就会被 spec 自动判定为 round failure，REVERT 决策不需要 L0 介入；
- 如果 spec 当时已经有 `round_kind=code_change` vs `measurement_only` 区分，Round 12 添加 case 是 "measurement coverage 扩张" + "task quality 实测变化"，那个紧张的张力会在 spec 层面就显形（"你既改了 measurement surface 又改了 ability 输出，这两件事必须分两轮做"）。

### 1.3 Why "core goal" is not the same as "intent" or "description"

v0.2.0 §2.1 schema 已有 `intent` 和 `description`（后者在 SKILL.md 的 frontmatter）。两者都不是可测试的功能契约：

- `intent: "this ability solves what"`：**叙述性**。`chip-usage-helper.intent = "show Cursor usage / billing / ranking dashboards"` 既不指定输入，也不指定输出，更不指定通过判据。
- `description`：**routing metadata**。Anthropic skill-creator 文档明确 `description` 的目的是 "help Claude decide whether to load the skill" —— 它 优化的是 trigger F1，不是功能正确性。

`core_goal` 与上述两者正交：它要回答的问题是 **"如果这一段功能输出不存在，user 会不会立刻知道？"** 对应到 `chip-usage-helper`：用户问 "本月 cursor 花了多少钱"，正确回答必须包含一个 numeric 金额（不是空字符串、不是 "我不知道"、不是把这个问题 routes 到别的 skill）。这个判据可以写成 ≥3 个 test cases，每轮 dogfood run 一遍，pass_rate 必须 100%。

### 1.4 The deeper systemic risk: optimization without anchor

R6 7×37 的指标矩阵是 Si-Chip 的力量来源，但也是它的 attack surface。当一个评估系统拥有 37 个可优化轴且 spec 只要求 "≥1 轴正向 ≥ +0.05" 时，Goodhart's Law 自然会把团队推向 "最便宜满足 spec 的那一轴"，而不是 "对用户价值最大的那一轴"。

13 轮 Si-Chip + 10 轮 chip-usage-helper = **23 轮独立观测**，无 measurement-fill 失真的轮只有：Si-Chip Round 1 / Round 13 / chip-usage-helper Round 1 / Round 2-3（CJK F1 真改善）。其余 18 轮 = 78 % 都是 measurement-fill 类。这不是个别工程师懒，而是激励梯度的方向问题 —— spec 没说 **核心目标无回退**，就只能在 spec 写明的事上打转。

### 1.5 What §1 demands of v0.3.0

1. spec 必须显式锁定 "core goal"；
2. spec 必须把 "core goal 不回退" 作为硬前提，不只是 value_vector 的一轴；
3. spec 必须区分 "本轮改了 ability 源码" 与 "本轮只改了测量覆盖"，并对后者放宽 iteration_delta 子句（因为没改源码 → 不该期望源码侧的改善）；
4. spec 必须为多 ability 并行 dogfood 准备目录布局；
5. spec 必须为下一个 ability 提供通用 evaluation harness，避免 chip-usage-helper 768-line ability-specific harness 这种重复发明。

---

## 2. Literature & Practice Survey

> 本节是用户在 v0.2.0 反馈中明确要求的 "进行更多的搜索和调研，以完善这一规则和限制"。每个来源都是 WebSearch / WebFetch 实抓的真 URL，配 1-2 句原文摘录与对 Si-Chip 的具体应用。引用顺序按本文后续章节使用密度排序。

### 2.1 Hyrum's Law — observed behavior is the contract

- **Source**: <https://www.hyrumslaw.com/>
- **Excerpt**: "With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by somebody."
- **Si-Chip application**: 这是 `core_goal_test_pack` 设计的根因。当前 spec 用 7-axis value vector 描述 ability，但用户依赖的不是 vector，是 ability 的 **observable behaviors**。如果 Round 12 把 T2_pass_k 从 0.5478 滑到 0.4950，就算其它 6 轴都赚了，那些依赖 "这个 ability 在我的 prompt 上能给我一个 dashboard URL" 的用户会立刻感知到回退。`core_goal_test_pack` 强制把 "user-observable 的核心行为" 写成可重放的 prompts，是把 Hyrum's Law 从 "事后惩罚" 变成 "事前 sentinel"。

### 2.2 Characterization Testing (Michael Feathers, Working Effectively with Legacy Code) — change detectors

- **Source**: <https://en.wikipedia.org/wiki/Characterization_test> （及 <https://www.oreilly.com/library/view/working-effectively-with/0131177052/ch11.html>）
- **Excerpt**: "Unlike traditional tests that verify correct behavior, characterization tests are 'change detectors'—they verify observed behavior and leave it to analysts to determine if detected changes are desirable."
- **Si-Chip application**: 这正是 `core_goal_test_pack` 的语义。它不是 "新 case 要验证一个新功能是否对"（assertion 测试），而是 "这一组锚定输出在新的 ability 实现下还是不是同一组锚定输出"（change detector）。当 `core_goal_pass_rate` 从 1.00 跌到 0.67，spec 不是说 "你错了"，是说 "你把一个 user-observable 行为改了 —— 是不是故意的？是的话请 bump major；不是的话请 revert"。这与 Round 12 → Round 13 REVERT-ONLY 决策的工艺是同构的，只是 v0.3.0 把这种工艺自动化了。

### 2.3 MLPerf reproducibility & reference-implementation rules

- **Source**: <https://github.com/mlperf/policies/blob/master/submission_rules.adoc>
- **Excerpt**: "Replicability is mandatory: Results that cannot be replicated are not valid results... All valid submissions of a benchmark must be equivalent to the reference implementation... Benchmark detection is not allowed: Systems should not detect and behave differently for benchmarks."
- **Si-Chip application**: MLPerf 用 "must be equivalent to the reference implementation" 来阻止 hyper-optimized but semantically-broken 提交。Si-Chip 的 `core_goal_test_pack` 起到同样作用 —— 它是 ability 的 reference implementation 等价物：无论新版本的 ability 在性能上多漂亮，必须在 core_goal_test_pack 上与上一轮 byte-equivalent（pass/fail level）。MLPerf 的 "benchmark detection is not allowed" 也直接映射到 Si-Chip：ability 不允许识别 "这是 core_goal_test 在跑" 而采取与生产 prompt 不同的策略 —— 这一条要求 core_goal_test_pack 中的 prompts 必须从真实 user prompt 中抽样，不能是合成的玩具 case。

### 2.4 OpenAI Evals — versioned eval registry

- **Source**: <https://github.com/openai/evals/tree/main/evals/registry>
- **Excerpt**: "The Evals registry is organized into ... eval_sets — versioned collections of evaluations ... evals — individual evaluation definitions ... When registering an eval, the format includes an `id` field with a version component."
- **Si-Chip application**: OpenAI Evals 的 registry 结构（versioned eval_sets + 数据 git-LFS + completion_fns）直接启发了 Si-Chip 的 `core_goal_test_pack` schema：每个 ability 在自身的 dogfood 子树下维护一个 versioned `core_goal_test_pack.yaml`，每个 round 跑一遍并把结果落到 `metrics_report.yaml.C0_core_goal_pass_rate`。Si-Chip 不需要 OpenAI Evals 的 git-LFS（数据规模 <100 cases / ability），也不需要 completion_fns（Si-Chip 用 deterministic simulator + 后续 v0.3.0 real-LLM runner），但它需要 OpenAI Evals 的 **"eval pack 是 first-class versioned artifact"** 这一原则。

### 2.5 Pact — consumer-driven contracts

- **Source**: <https://docs.pact.io/faq> （及 <https://docs.pact.io/consumer/>）
- **Excerpt**: "Good Pact tests should be 'as loose as they possibly can be, while still ensuring that the provider can't make changes that will break compatibility with the consumer.' ... The contract serves as a synchronization mechanism between the two sets of tests."
- **Si-Chip application**: `core_goal_test_pack` 与 Pact contract 的形态学非常相似：
  - **consumer side** = 用户（提出 "查月度 cursor 花费" 的人）；
  - **provider side** = ability 实现（chip-usage-helper MCP）；
  - **contract** = `core_goal_test_pack.yaml` 中的 ≥3 prompts/cases；
  - **broker** = `.local/dogfood/<DATE>/abilities/<id>/`。

  Pact 的 "as loose as possible" 原则提示 Si-Chip：`core_goal_test_pack` 不应该断言 "返回值是确切的 $123.45"，而应该断言 "返回值包含一个金额格式 + 一个时间窗 + 不为空"。这避免了 spec 把 ability 锁死在某一轮的具体数值上 —— 是 R8 description_competition_index / R3 trigger_F1 等指标的天然补充而不是替代。

### 2.6 Lighthouse CI — performance assertions and budgets

- **Source**: <https://unlighthouse.dev/learn-lighthouse/lighthouse-ci/budgets> （+ <https://github.com/GoogleChrome/lighthouse-ci/>）
- **Excerpt**: "Define budgets directly in your Lighthouse CI configuration file: assertions: { 'categories:performance': ['error', { minScore: 0.9 }], 'first-contentful-paint': ['warn', { maxNumericValue: 2000 }] } ... Performance budgets translate business requirements into measurable standards, preventing incremental degradation."
- **Si-Chip application**: Lighthouse CI 的 assertion 模式（每个指标 `error` / `warn` 两档 + 阈值）是 Si-Chip §4.1 progressive gate（`v1_baseline / v2_tightened / v3_strict` 三档）的成熟工业版本。两者都是 "性能指标的 CI gate"。区别：Lighthouse CI 没有 core_goal 概念 —— 它只防止 "性能回退"，不能防止 "为了拿 90 分把页面渲染坏了"。这正是 Si-Chip 必须比 Lighthouse CI 多走一步的地方：有了 `core_goal_pass_rate` 作为前置，progressive gate 才不会变成 "把 ability 优化到 spec 满意但用户不满意"。

### 2.7 Semantic Versioning 2.0.0 — MAJOR-bump for incompatible API change

- **Source**: <https://semver.org/>
- **Excerpt**: "Major version X (X.y.z | X > 0) MUST be incremented if any backwards incompatible changes are introduced to the public API. ... The term 'API' includes all of the behavior, not just the interface."
- **Si-Chip application**: 两个直接结论：
  1. Si-Chip 当前在 **0.x.y initial development**，semver 允许 "Anything MAY change at any time"；但本文 v0.3.0 的设计仍然主动遵守 additivity discipline（v0.2.0 §3-§11 byte-identical），这是出于 **future-proofing** —— 当 Si-Chip bump 到 1.0.0 时，§3-§11 的 frozen 语义就变成事实上的 public API，提早守纪律可降低 1.0.0 cutover 时的风险。
  2. semver 把 "API includes all of the behavior" 写在 issue tracker 的官方答复里，正好支持本文的核心论证：**ability 的 user-observable 行为是 ability 的 public API**，所以 `core_goal_pass_rate` 回退 = behavioral breaking change = 在 1.0.0 之后要 MAJOR bump。在 0.x.y 阶段就把这个判据 codify 是为 1.0.0 做准备。

### 2.8 Anthropic Claude Skill authoring best practices

- **Source**: <https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices>
- **Excerpt**: "Be concise in SKILL.md since tokens compete with conversation history once the file is loaded ... A good example uses ~50 tokens; verbose explanations waste ~150 tokens ... The description is the single most important design decision—Claude decides whether to load a skill based solely on `name` + `description`. Make descriptions 'pushy' by including specific trigger phrases and contexts."
- **Si-Chip application**: Anthropic 的 best-practices 给了三个关键约束：
  1. **`description` 与 `core_goal` 必须分开**：`description` 服务 router（trigger 决策），是 "pushy" 的、含 trigger phrases 的字符串；`core_goal` 服务 evaluator（功能正确性），是 "测试可重放" 的、含 prompts/expected-shape 的对象。把两者塞同一字段会同时伤害 R3 trigger_F1（描述太长太具体）和 C0 core_goal_pass_rate（描述太抽象 → 不可测）。
  2. **`core_goal_test_pack` 不可超 50-150 tokens 的合理阈值**：每个 prompt ~50 tokens × ≤10 prompts = ~500 tokens 上限；超过这个量是浪费 metadata 预算（C1 ≤ 100, C4 ≤ 9000 等）。
  3. **"Set Appropriate Degrees of Freedom"** 直接说明 `core_goal_test_pack` 的合适粒度：对 chip-usage-helper（low freedom，operation 是 "查 dashboard"），test pack 用 specific scripts；对 Si-Chip itself（high freedom，operation 是 "执行 8 步 dogfood 协议"），test pack 用 high-freedom text 描述（"必须输出 6 件证据" 而不是 "必须输出特定 yaml hash"）。

### 2.9 Jieba — Chinese word segmentation library

- **Source**: <https://jieba.readthedocs.io/> + <https://pypi.org/project/jieba/>
- **Excerpt**: "Jieba uses a Prefix dictionary for efficient word graph scanning, creating a directed acyclic graph (DAG) of all possible word combinations ... Three Segmentation Modes: Exact Mode (precisely segments text for text analysis); Full Mode (scans all possible word combinations quickly but cannot resolve ambiguity); Search Engine Mode (further segments long words to improve recall)."
- **Si-Chip application**: chip-usage-helper R1→R3 的 trigger F1 从 0.7778 跳到 0.9524，根因是 R1 的 naive `re.findall(r"\w+", text)` tokenizer 把 "本月花了" 切成单独的 "本", "月", "花", "了" 四个 unigram，无法匹配 vocabulary 里的 bigram "花了"。R2 用了 substring matching `re.findall(r"[\u4e00-\u9fff]{2,6}", body)`，问题解决。Jieba 的 DAG + 词典 + Viterbi 给了一个工业级的、但 **太重** 的方案（jieba install 包 ~100 MB，启动时间 0.5s）。Si-Chip 的 `tools/cjk_trigger_eval.py`（§6 设计）走 jieba 的轻量替代：(a) ASCII bag-of-words；(b) `[\u4e00-\u9fff]{2,6}` substring match；(c) discriminator phrase rules。pluggable vocabulary 让每个 ability 自带 anchors + discriminators —— 这是从 jieba 的 "custom dictionary support" 借的设计原则。

### 2.10 Survey synthesis & non-results

- 9 distinct sources cited above. 6 是必检领域（regression, ML benchmarks, contract, perf gates, semver, Anthropic, CJK），多出来的 1 个 (OpenAI Evals) 加固了 ML benchmarks 类。
- **Negative result**: 用 "Hugging Face evaluate library no-regression" 关键词的隐含搜索（在背景调研阶段尝试）未返回直接命中文档 —— Hugging Face `evaluate` 库是 metric 容器（accuracy / BLEU / etc.），不是 no-regression 框架。如果 Stage 2 spec 作者认为本文 §2 的 ML 类需要更深的来源，可以追加搜 "EleutherAI lm-evaluation-harness reproducibility" 或 "BIG-bench benchmark schema"。
- 上述 9 个来源已经足够 ground §3–§8 的所有 Normative 提议；本研究阶段不需要再扩。

---

## 3. Core-Goal Invariant — proposed Normative addition for v0.3.0 (§14)

### 3.1 New REQUIRED field on `BasicAbility`: `core_goal`

`core_goal` 与 `intent` 正交。`intent` 是 "this ability solves what"（高层叙述、router-friendly）；`core_goal` 是 **"the persistent, never-regress functional outcome that, if removed, would be immediately user-visible"**（可测试的功能契约）。

#### 3.1.1 Schema sketch (additive to §2.1; existing fields unchanged)

```yaml
basic_ability:
  id: "<ability-name>"
  intent: "<this ability solves what>"        # unchanged from v0.2.0 §2.1
  core_goal:                                  # NEW in v0.3.0 §14, REQUIRED
    statement: "<one-sentence functional contract; testable, not narrative>"
    user_observable_failure_mode: "<what user sees if core_goal regresses>"
    test_pack_path: "<repo-relative path to core_goal_test_pack.yaml>"
    minimum_pass_rate: 1.0                    # spec-locked at 1.0; cannot be lowered
    last_passing_round: "<round_id>"          # updated each successful round
  current_surface: { ... }                    # unchanged
  ... (rest of §2.1 unchanged)
```

#### 3.1.2 Worked example (a) — Si-Chip itself

```yaml
basic_ability:
  id: "si-chip"
  intent: "Persistent BasicAbility optimization factory; profile/evaluate/improve/router-test/half-retire-review/iterate/package any BasicAbility through the 8-step dogfood protocol and emit 6 evidence artifacts per round."
  core_goal:
    statement: "Given any BasicAbility (target ability source path + intent), Si-Chip MUST execute the 8-step dogfood protocol end-to-end and emit 6 evidence files (basic_ability_profile / metrics_report / router_floor_report / half_retire_decision / next_action_plan / iteration_delta_report) into .local/dogfood/<DATE>/[abilities/<id>/]round_<N>/, with all 6 schema-valid against templates/."
    user_observable_failure_mode: "User runs 'profile this new ability through Si-Chip' and gets either a crash, a partial evidence set (≤5 of 6 files), or schema-invalid YAML in any of the 6 files. Either case means Si-Chip cannot deliver its primary value."
    test_pack_path: ".agents/skills/si-chip/core_goal_test_pack.yaml"
    minimum_pass_rate: 1.0
    last_passing_round: "round_13"
```

具体的 ≥3 cases：
1. Profile a synthetic new ability `dummy-ability` (markdown + 1 script). Verify all 6 evidence files land + are template-validated.
2. Run Si-Chip on `chip-usage-helper` (real second ability) Round 1 from scratch. Verify 6 evidence files + iteration_delta accepts `null` as prior_round.
3. Re-run Si-Chip on Si-Chip itself (the meta-case) Round N+1 from Round N artifacts. Verify deltas computed correctly.

#### 3.1.3 Worked example (b) — chip-usage-helper

```yaml
basic_ability:
  id: "chip-usage-helper"
  intent: "Surface a per-user Cursor usage / billing / model-mix / leaderboard dashboard inside the Cursor agent."
  core_goal:
    statement: "Given a user prompt that asks about their own Cursor usage / spend / model mix / team rank in the current or recent billing period, the helper MUST return a response containing (i) a numeric value with currency or percentage unit, (ii) an explicit time window (week / month / period), and (iii) the response is rendered through the chip-usage-helper MCP (not deferred to base model or another skill)."
    user_observable_failure_mode: "User asks '我本月花了多少？' and gets back either an empty string, a generic 'I cannot help with that', a number without time window, or the response is silently routed to a different skill that cannot answer."
    test_pack_path: "ChipPlugins/chips/chip_usage_helper/.dogfood/core_goal_test_pack.yaml"
    minimum_pass_rate: 1.0
    last_passing_round: "round_10"
```

具体的 ≥3 cases：
1. EN: "show me my cursor usage dashboard" → response contains `$<num>`, time window, MCP-rendered.
2. CJK: "我本月花了多少？" → response contains `¥<num>` 或 `$<num>`, "本月" 时间窗, MCP-rendered.
3. Slash command: "/usage-report --window=30d" → response contains numeric, "30 days" / "30d", MCP-rendered.

注意：这 3 cases 与 `eval_pack.yaml` 的 40-prompt **trigger eval pack** 不同。后者测 R3_trigger_F1（routing 决策对不对），前者测 C0_core_goal_pass_rate（routing 后产物对不对）。

### 3.2 New REQUIRED field on `BasicAbility`: `core_goal_test_pack`

`core_goal_test_pack` 是 `core_goal.test_pack_path` 指向的 YAML 文件，是真实磁盘上的可重放 artifact（不是 inline schema）。其骨架：

```yaml
# .agents/skills/<id>/core_goal_test_pack.yaml
$schema_version: "0.1.0"
$spec_section: "v0.3.0 §14.2"

ability_id: "<id>"
last_revised: "YYYY-MM-DD"
revision_log:
  - { round: round_N, change: "added EN case for slash command" }

cases:
  - id: "core_goal_case_1"
    prompt: "<user prompt verbatim>"
    expected_shape:                            # NOT exact equality — Pact-style "loose"
      contains_numeric: true                   # response must contain a number
      contains_unit: ["currency", "percent", "time"]   # at least one of these unit types
      contains_time_window: true               # explicit week/month/period reference
      rendered_by: "<expected_renderer>"       # e.g. "chip-usage-helper-mcp"
      not_empty: true
      not_redirected_to: ["other_skill_id_a", "other_skill_id_b"]
    rationale: "If this case fails, user observes <user_observable_failure_mode>."
    weight: 1.0
  - id: "core_goal_case_2"
    ...
  - id: "core_goal_case_3"
    ...
```

**冻结约束**：

- 至少 ≥3 cases。建议 5-10 cases。 ≤20 cases（防止 metadata 预算被吃光；按 §2.8 每 case ~50 tokens × 20 = 1000 tokens 上限）。
- `expected_shape` 必须是 **结构断言**（contains, shape, type），**不是值断言**（exact equality）。这是 Pact §2.5 "as loose as possible" 原则的直接应用。
- `cases` 一旦写入，从 round_N 起 **不允许删除任何 case**；只允许 (a) 新增；(b) 修订 `expected_shape` 时必须同时把 `revision_log` 加一条说明，并且修订当轮的 `core_goal_pass_rate` 必须仍 = 1.0（否则 = 把已有用户契约改了 → behavioral breaking change）。
- 删除 case 必须 bump `core_goal` 大版本（v0.3.0 通过 §14 引入此字段；后续删 case = 在 frontmatter `core_goal_version` bump 一次，并在 `revision_log` 留 deprecation reason）。

### 3.3 New metric: `C0 core_goal_pass_rate`

`C0_core_goal_pass_rate` = (number of cases passing in current round) / (total cases). 永远在 [0, 1]。

```yaml
# in metrics_report.yaml
metrics:
  ...
  core_goal:                                   # NEW top-level dimension
    C0_core_goal_pass_rate: 1.0                # MUST be exactly 1.0
    cases_passed: 3
    cases_total: 3
    failed_case_ids: []                        # MUST be []
```

#### 3.3.1 The strict no-regression rule

```text
if metrics_report[round_N+1].C0_core_goal_pass_rate
   < metrics_report[round_N].C0_core_goal_pass_rate
THEN
   round_N+1 IS A FAILURE
   regardless of any other axis
```

具体到 round_N+1 的 metrics_report.yaml 必须包含 `verdict.core_goal_pass: true`，否则 spec_validator 在 BLOCKER 模式抛错（见 §9）。

#### 3.3.2 The rollback rule (强制回滚)

failing rounds（`core_goal_pass_rate` regressed）MUST:

1. Not write `iteration_delta_report.yaml.verdict.pass = true`（无论其它轴 delta 如何）。
2. Source changes that caused the regression MUST be reverted before next round can begin（per Round 12 → Round 13 REVERT-ONLY precedent）。
3. The failing round 的 `next_action_plan.yaml.actions` MUST include 至少一个 `primitive: refine` action with `applies_to_metric: C0_core_goal_pass_rate` and `exit_criterion: "C0_core_goal_pass_rate >= prior_round.C0_core_goal_pass_rate"`.
4. The failing round 仍然 keep 在 `.local/dogfood/<DATE>/...` 下（不删除证据），保留作为 honest negative-result trace（per workspace rule "No Silent Failures"）。

### 3.4 Should `C0` be the 38th R6 sub-metric, or a separate top-level invariant?

**Recommendation**: **separate top-level invariant**, NOT the 38th sub-metric.

Rationale:

| 选项 | Pros | Cons |
|---|---|---|
| **A. Add as R6 D8 / 38th sub-metric** | 统一在 7×N 矩阵下；spec_validator 改动小；OTel attribute mapping 可重用 | 破坏 §3.1 R6 frozen 7×37 count → 与 v0.2.0-rc1 prose-count reconciliation 的成果直接冲突；C0 与其它 R6 子指标的 **语义类型不同**（C0 是 binary go/no-go，其它是 continuous quality scores）；R6 子指标允许 v1/v2/v3 阈值递进，C0 只有 = 1.0 一种合法值 → 不应进 progressive gate table |
| **B. Top-level `core_goal_pass_rate` field; separate from R6 metrics dict** | 保持 R6 7×37 frozen；C0 的 binary 性质对应 binary verdict（go/no-go），不混入 progressive scoring；spec §3.4 promotion rule 不需要为 C0 新设阈值桶；C0 失败的 spec 行为（"failure regardless of other axes"）直接写在 §14，不与 §4.1 阈值表纠缠 | spec_validator 多一个 BLOCKER；agents 需要学一个新的字段位置；OTel attribute 需新增（但反正 D8 也要新增） |

选 B 的关键 tie-breaker：**C0 不是 "评估这个 ability 多好" 的指标，而是 "这个 ability 还存在不存在" 的开关**。R6 的 7 维 37 子指标本质上都是 "更多 / 更少 / 更快 / 更慢" 的连续轴；C0 是 "通过 / 不通过" 的 boolean。强行塞进 R6 会造成 spec semantic 上的类型错误。

另外，§9 acceptance criteria 要求 v0.2.0 §3-§11 byte-identical；如果选 A，§3.1 table 必须 +1 行（D8 task-quality-invariant），等于自己破自己 additivity。

> 与 `r9_half_retirement_framework.md §1` 的 7-axis value vector 的关系：value_vector 度量 "本轮带来的改善"；C0 度量 "本轮没破之前的核心承诺"。两者是 **正交的硬前提 vs 改善信号**，不是同一类东西。spec §6 在 v0.3.0 中 **不变**：value_vector 仍然 7 轴；C0 是 §14 引入的独立机制。

### 3.5 §11 forever-out compliance review

Hard check：本节提议的 `core_goal` / `core_goal_test_pack` / `C0_core_goal_pass_rate` / strict no-regression / rollback rule 是否触碰 §11.1？

| §11.1 forever-out | 本节是否触碰 |
|---|---|
| Skill / Plugin marketplace | NO. `core_goal_test_pack` 落在每个 ability 自己的源码树或 `.agents/skills/<id>/`，不引入注册中心、distribution surface 或 manifest exchange。|
| Router 模型训练 | NO. `core_goal_pass_rate` 是 evaluator metric，不喂任何模型；spec §5.1 允许的 "metadata 检索" / "kNN baseline" / "description 优化" / "thinking-depth escalation" / "fallback policy" 完全无需改动。|
| 通用 IDE 兼容层 | NO. `core_goal` 是 ability-level 的 yaml 字段，与 IDE 无关；§7.2 平台优先级（Cursor → Claude Code → Codex）保持。|
| Markdown-to-CLI 自动转换器 | NO. test_pack 是手写 YAML cases，不做 Markdown → CLI 自动生成；core_goal 的 `statement` 是人写的句子，不是从 SKILL.md 自动 derive 的。|

**结论**: §3 全部提议在 §11 forever-out 内部执行，不踩任何边界。

---

## 4. round_kind Enum (Normative for v0.3.0 §15)

### 4.1 The four values

```yaml
# in next_action_plan.yaml (NEW field; additive to existing schema)
round_kind: code_change | measurement_only | ship_prep | maintenance
```

#### 4.1.1 `code_change`

- **Definition**: 本轮 modifies ability source files（≥1 file under `.agents/skills/<id>/` 或对应 ability 实现树）.
- **iteration_delta clause**: SAME as v0.2.0 §4.1 row 10 — MUST show ≥1 efficiency-axis improvement at gate bucket (`v1 ≥ +0.05`, `v2 ≥ +0.10`, `v3 ≥ +0.15`).
- **C0 clause**: `core_goal_pass_rate` MUST = 1.0 AND `>= prior_round.core_goal_pass_rate`.
- **Examples from history**: Si-Chip Round 1 (initial profile), Round 2 (install.sh), Round 3 (R6+R7 hoist with new instrumentation in source); chip-usage-helper Round 1 (initial), Round 2 (CJK tokenizer fix in source).

#### 4.1.2 `measurement_only`

- **Definition**: 本轮 adds new metric coverage, new eval cases, new instrumentation 但 **does NOT touch ability source files**. Source 包括：(a) `.agents/skills/<id>/` 下的 SKILL.md / scripts / references; (b) ability 实际实现的代码树（如 `ChipPlugins/chips/chip_usage_helper/mcp/`）.
- **iteration_delta clause**: **RELAXED to monotonicity-only** — no code change → no improvement expected; only assert (a) `core_goal_pass_rate` did not regress; (b) no v1_baseline hard gate fell from PASS to FAIL.
- **C0 clause**: `core_goal_pass_rate` MUST = 1.0 AND `== prior_round.core_goal_pass_rate`（严格相等，因为没改源码）.
- **Examples from history**: Si-Chip Rounds 4-12 (each hoisted a new sub-metric without changing the dogfood protocol's semantics) — under v0.3.0 these would all be `measurement_only` and would NOT need to fake an iteration_delta improvement axis.

#### 4.1.3 `ship_prep`

- **Definition**: 本轮 finalizes for release: mirror sync between `.agents/skills/<id>/` and `.cursor/skills/<id>/` / `.claude/skills/<id>/`; version bumps in SKILL.md frontmatter, install.sh, CHANGELOG, docs; tarball build.
- **iteration_delta clause**: **WAIVED** — no metric change expected.
- **C0 clause**: `core_goal_pass_rate` MUST = 1.0 AND `== prior_round.core_goal_pass_rate`. (Mirror sync 不应改变 ability 行为；如果 sync 后 C0 跌，说明 mirror 与 source 漂移 → §10 archive rule + §7.2 drift detection 联动报错。)
- **Examples from history**: Si-Chip Round 13 (SHIP-PREP REVERT-ONLY); chip-usage-helper Round 10 (5th consecutive v3-row-complete pass — official convergence).

#### 4.1.4 `maintenance`

- **Definition**: 本轮 是 post-ship review (e.g. 30/60/90 day cadence per §6.4 reactivation triggers; or post-model-upgrade re-verify; or post-dependency-bump smoke).
- **iteration_delta clause**: **WAIVED** — no metric change required, just re-verify.
- **C0 clause**: `core_goal_pass_rate` MUST = 1.0. 如果跌 → 进入 §6.4 reactivation review 或 §6 retire 决策。
- **Examples from history**: Not yet seen in Si-Chip's 13 rounds (all rounds were ship-track); but `chip-usage-helper.basic_ability.lifecycle.next_review_at = round_10 + 30 days` 隐含一个未来的 maintenance round。

### 4.2 The decision matrix

```text
                     | iteration_delta clause             | C0 clause
---------------------|------------------------------------|----------------------------------
code_change          | ≥1 axis at gate bucket (≥+0.05/+0.10/+0.15) | == 1.0 AND >= prior
measurement_only     | monotonicity only (no regression)  | == 1.0 AND == prior
ship_prep            | WAIVED                             | == 1.0 AND == prior
maintenance          | WAIVED                             | == 1.0
```

### 4.3 Interaction with §4.2 promotion rule

v0.2.0 §4.2 says: "连续两轮 dogfood 全部通过, 才允许提升至 v2_tightened". v0.3.0 必须澄清 `measurement_only` 轮是否计入 "连续两轮"：

**Recommendation**: **YES**, `measurement_only` 轮计入连续两轮，但 only if (a) `core_goal_pass_rate` clause passed AND (b) no v1_baseline hard gate regressed. Ship_prep and maintenance 轮 **不** 计入（因为它们的 metric 是 carry-forward）.

> 这保证 measurement coverage 的扩张可以推进 promotion，但 ship_prep / maintenance 的 carry-forward 不会偷拿 promotion 票。

### 4.4 Why this fixes the "measurement-fill" pain

回到 §1.1：Si-Chip Rounds 4-12 = 9 轮 measurement-fill。在 v0.3.0 round_kind 下：

- Round 4-12 的每一轮都会被标 `round_kind: measurement_only`（因为 SKILL.md / scripts 的语义没变，只是新增 instrumentation）。
- iteration_delta clause 自动 RELAXED，不需要找 "+0.05 的便宜 bonus"。
- spec 不再误导团队去虚构 axis improvement —— spec 改成承认 "本轮目的是补 coverage，没在改 ability 本身"。
- 真正的 ability 改善（Round 1 / Round 13 的 task_quality 跳变）仍然要求 `code_change` 标签 + ≥+0.05 axis improvement，激励仍然在那里，只是不再被 measurement-fill 冲淡。

### 4.5 Spec citations (so Stage 2 spec authoring can cross-reference)

- §4.1 row 10: `iteration_delta (任一效率轴) ≥ +0.05 / +0.10 / +0.15`
- §8.3: "v0.1.0 ship 前必须完成至少 2 轮 dogfood, 且第 2 轮在 v1_baseline 全部硬门槛通过."
- §13.4 machine-checkable items: 需新增 "round_kind ∈ {code_change, measurement_only, ship_prep, maintenance}" 校验.

---

## 5. Multi-Ability Dogfood Layout (Informative for v0.3.0; later Normative)

### 5.1 The new layout

```text
.local/dogfood/<YYYY-MM-DD>/abilities/<ability-id>/
    eval_pack.yaml                          # trigger eval pack (used by R3_trigger_F1)
    core_goal_test_pack.yaml                # NEW v0.3.0 §14.2 test pack
    tools/
        <ability-id>_specific.py            # OPTIONAL; only if generic harness can't handle
    round_<N>/
        basic_ability_profile.yaml
        metrics_report.yaml
        router_floor_report.yaml
        half_retire_decision.yaml
        next_action_plan.yaml
        iteration_delta_report.yaml
        raw/                                # OTel traces, NineS reports, drift checks
```

### 5.2 Comparison to legacy single-ability layout

```text
# Legacy (Si-Chip self-dogfood, Round 1-13):
.local/dogfood/<YYYY-MM-DD>/round_<N>/
    basic_ability_profile.yaml
    ... (same 6 evidence files)
    raw/

# Current chip-usage-helper layout (already adopted ahead of v0.3.0 spec):
.local/dogfood/2026-04-29/abilities/chip-usage-helper/round_<N>/
    ...
```

### 5.3 Migration path

| Surface | v0.3.0 status | Action |
|---|---|---|
| Si-Chip self-dogfood (Round 1-13 history) | **legacy layout retained** | No migration. Round 14+ MAY adopt new layout but not required (spec_validator accepts both). |
| chip-usage-helper (Round 1-10 already at new layout) | **new layout adopted** | No action (already correct). |
| Any new ability introduced in v0.3.x | **MUST use new layout** | spec_validator BLOCKER if new ability writes to `.local/dogfood/<date>/round_<N>/` (collides with Si-Chip self). |

### 5.4 Why "Informative @ v0.3.0, Normative @ v0.3.x"

**Recommendation**: Informative for v0.3.0 spec; promote to Normative at v0.3.1 once 2+ abilities have shipped under the new layout.

Rationale: spec promotion 需要 evidence（per §4.2 spirit）。当前我们只有 chip-usage-helper 一个 second ability 的实证（10 轮）；Si-Chip self 仍在 legacy layout 上。把 layout Normative 推到 v0.3.0 = forcing a rework of Si-Chip self-dogfood without two independent witnesses. Informative @ v0.3.0 给一轮 grace period（3rd ability 或 Si-Chip 主动迁移）后再升 Normative，符合 v0.1.0 → v0.2.0 reconciliation 用 RC（v0.2.0-rc1）渐进升 Normative 的同样模式。

### 5.5 Path-style choices to make explicit at Stage 2

- 是否允许 ability id 含 `/`（例如 `lark-cli/im` vs `lark-cli-im`）？建议禁止 `/`，统一 kebab-case。理由：避免文件系统跨平台 quirks + spec_validator 的 path glob 简化。
- `tools/<ability-id>_specific.py` 是 ability 的私有 evaluator 钩子，与 §7 generic `tools/eval_skill.py` 的关系：generic harness 在 100 % cases 下应能跑；只有当 ability 有 unique step（如 chip-usage-helper 的 `npm test` 触发 vitest）才需要 specific 钩子，且必须以 plugin/callback 形式接入 generic harness 而不是 fork harness。

---

## 6. Generic CJK-aware Trigger Evaluator — `tools/cjk_trigger_eval.py`

### 6.1 The motivating gain

`chip-usage-helper` Round 1 → Round 3 的 `R3_trigger_F1` 从 **0.7778** → **0.9524**（+0.1746 绝对）的根因（read from `.local/dogfood/2026-04-29/abilities/chip-usage-helper/round_1/iteration_delta_report.yaml` 与 `eval_chip_usage_helper.py:57-102`）：

- Round 1 的 naive `re.findall(r"\w+", text.lower())` 将 "本月花了" 切成单字 `{"本", "月", "花", "了"}`，与 vocabulary 里的 bigram `{"用量", "花了", "本月"}` 完全不能匹配。
- Round 2 加 `re.findall(r"[\u4e00-\u9fff]{2,6}", body)` 给 vocabulary 一份 CJK substring set，trigger_match 改用 substring search `if substring in prompt`。
- Round 3 加 discriminator phrases（e.g. "spend time" 排除非 billing 上下文）+ strong CJK anchors `{"用量", "工时", "排第几", ...}`，把 `near_miss_FP_rate` 同时压下来。

如果 v0.3.0 不把这套 CJK-aware tokenizer 抽取成通用工具，下一个 ability 从 zero CJK awareness 开始，必然踩同样坑。

### 6.2 API outline

```python
# tools/cjk_trigger_eval.py
"""
Generic CJK-aware trigger evaluator for Si-Chip BasicAbility eval packs.

Three-layer tokenization (CJK-Aware Default, CAD):
  Layer A: ASCII bag-of-words (lowercase, [\\w]+ split)
  Layer B: CJK substring matching ([\\u4e00-\\u9fff]{2,6})
  Layer C: discriminator phrase rules (anti-trigger; suppresses false positives)

Each ability supplies its own pluggable vocabulary
(anchors + substrings + discriminators); the harness applies the three layers
deterministically against an eval pack and returns the R1/R2/R3/R4 confusion-matrix.
"""

from pathlib import Path
from typing import TypedDict, Sequence

class TriggerVocabulary(TypedDict):
    """Pluggable vocabulary supplied per-ability (e.g. via ability_id-specific yaml)."""
    ascii_anchors: set[str]            # e.g. {"cursor", "usage", "billing"}
    cjk_substrings: set[str]           # e.g. {"用量", "花了", "排第几"}
    cjk_strong_anchors: set[str]       # subset of cjk_substrings; single-hit triggers YES
    discriminator_phrases: list[dict]  # rules suppressing trigger; see §6.3

class TriggerDecision(TypedDict):
    match: bool
    reason: str                        # human-readable; e.g. "strong_cjk:用量"
    layer_hit: str                     # "A_ascii", "B_cjk_substring", "C_discriminator"

def trigger_match(prompt: str, vocab: TriggerVocabulary, min_hits: int = 2) -> TriggerDecision:
    """Apply 3-layer rules deterministically; return decision + reason + layer."""
    ...

def evaluate_trigger_pack(
    pack_path: Path,                   # yaml with should_trigger / should_not_trigger lists
    vocab: TriggerVocabulary,
    min_hits: int = 2,
) -> dict:
    """Run trigger_match against each prompt; return:
      R1_trigger_precision, R2_trigger_recall, R3_trigger_F1, R4_near_miss_FP_rate,
      confusion: {tp, fp, fn, tn},
      mistakes: [...],   # for diagnosis
      decisions: [...],  # for replay
    """
    ...

def load_vocab_from_yaml(vocab_yaml: Path) -> TriggerVocabulary:
    """Load pluggable vocab from per-ability yaml; raises if schema invalid."""
    ...

def auto_extend_vocab_from_skill(
    base_vocab: TriggerVocabulary,
    skill_md: Path,
    routing_rule: Path | None = None,
) -> TriggerVocabulary:
    """Optional convenience: extract additional ASCII/CJK anchors from
    SKILL.md description + routing rule body; merge with base_vocab."""
    ...
```

### 6.3 The discriminator phrase rule schema

```yaml
# in <ability-id>_vocab.yaml
discriminator_phrases:
  - id: "cursor_meta"
    description: "Cursor-meta context (settings/composer/extension/...) co-occurring with 'cursor' suppresses trigger."
    if_token_in_prompt: ["cursor"]
    and_any_token_in_prompt: ["composer", "settings", "extension", "keybinding", "update", "install", "marketplace"]
    suppress: true
  - id: "time_spend_no_money"
    description: "'spend' or 花 with time-words and no money-cue is non-billing."
    if_token_in_prompt: ["spend"]   # OR cjk match below
    or_cjk_substring_in_prompt: ["花时间", "花一"]
    and_any_token_in_prompt: ["time", "debugging", "debug", "review", "reviewing", "sprint", "hour", "minute"]
    and_no_money_cue: true            # money_anchors_ascii ∪ money_anchors_cjk
    suppress: true
```

抽取自 `eval_chip_usage_helper.py:107-158` 的实际逻辑；通用化后任何 ability 写自己的 yaml 即可。

### 6.4 Where chip-usage-helper's 768-line harness collapses

In §7 we tally the LoC delta in detail; here we note that lines `57-194` of `eval_chip_usage_helper.py`（`tokenize_prompt` + `load_trigger_vocabulary` + `trigger_match` + `eval_trigger_F1`，共 ~140 lines）will collapse to:

```python
# chip-usage-helper-specific eval (post-v0.3.0):
from tools.cjk_trigger_eval import evaluate_trigger_pack, load_vocab_from_yaml
vocab = load_vocab_from_yaml("<ability>_vocab.yaml")
trigger_metrics = evaluate_trigger_pack(eval_pack, vocab)
```

5-line collapse from 140-line ability-specific implementation.

### 6.5 Backward compat with chip-usage-helper Round 1-10 evidence

- New `tools/cjk_trigger_eval.py` 必须在 chip-usage-helper Round 10 vocabulary 上重跑后 R3_trigger_F1 = 0.9524 byte-equivalent（否则 = 把 Round 10 的 measurement 改了）。这是 §9 的一条 acceptance criterion。

---

## 7. Generic `eval_skill.py` Harness — `tools/eval_skill.py`

### 7.1 What the harness covers

```python
# tools/eval_skill.py
"""
Generic Si-Chip ability evaluation harness.

Drives a single ability through one dogfood round (steps 2-3 of §8.1), emitting
metrics_report.yaml in the format spec_validator expects.

Pluggable adapters per ability:
  - vocab_loader      → trigger eval (delegates to cjk_trigger_eval.py)
  - tokens_counter    → C1/C2/C3/C4 (delegates to scripts/count_tokens.py)
  - test_runner       → L1/L2 (ability-specific; e.g. npm test for MCP, pytest for python)
  - handler_walker    → L3/L4 (delegates to multi_handler_redundant_call.py)
  - core_goal_runner  → C0 (NEW v0.3.0; runs core_goal_test_pack.yaml against ability)
"""
```

### 7.2 LoC tally (back-of-envelope)

| `eval_chip_usage_helper.py` extract | LoC | Generic? | Where it lands post-v0.3.0 |
|---|---:|---|---|
| `tokenize_prompt` + `load_trigger_vocabulary` + `trigger_match` + `eval_trigger_F1` | ~140 | Yes | `tools/cjk_trigger_eval.py` |
| `count_tokens_file` + R7 routing token overhead computation | ~30 | Yes | reuse `scripts/count_tokens.py` (already in repo) |
| `run_tests` (vitest wrapper) + `measure_u2_first_time_success` (vitest filter) | ~30 | Mostly (parametrize on test_command) | `tools/eval_skill.py` `test_runner` adapter |
| `_analyze_handler_file` + `measure_path_shape` + `measure_path_shape_legacy` (L3/L4) | ~80 | Yes | `tools/multi_handler_redundant_call.py` (§8) |
| `compute_U1_fk_grade` (FK readability) + `compute_C5_context_rot_risk` + `compute_C6_scope_overlap` | ~80 | Yes | `tools/eval_skill.py` (D2/D5 helpers) |
| `measure_u3_u4_install` (README quick-start parser + npm-test wall-clock) | ~50 | Mostly | `tools/eval_skill.py` (parametrize on quick-start regex) |
| `measure_l5_detour_index` + `measure_l6_l7` (replanning + think_act split) | ~80 | Yes | `tools/eval_skill.py` (D3 helpers) |
| `measure_governance_v3_v4` + `describe_perm_scope` + `describe_credential_surface` (V1/V2/V3/V4) | ~80 | Yes | `tools/eval_skill.py` (D7 helpers) |
| `measure_routing_latency_p95` + `measure_routing_token_overhead` + `measure_description_competition_index` (R6/R7/R8) | ~120 | Yes | `tools/eval_skill.py` (D6 helpers) |
| `compute_G1_cross_model_matrix` (G1) | ~80 | Yes | `tools/eval_skill.py` (D4 helpers) |
| `measure_t2_pass_k` (controlled-jitter pass_k) | ~40 | Yes | `tools/eval_skill.py` (D1 helpers) |
| `main()` (CLI orchestration + JSON serialization) | ~140 | Yes | `tools/eval_skill.py` `main()` |
| **Total reusable** | **~850** | | — |
| **Ability-specific residue** (chip-usage-helper after extraction) | **~50** | No | stays in `tools/eval_<ability>.py` |
| **LoC saved per new ability** | **~600** | | (the difference between 768 lines today and ~50-60 lines once harness exists) |

(Note: 850 reusable > 768 in source because some lines duplicate with the legacy `measure_path_shape_legacy` and the `--si-chip-scripts` CLI plumbing; the net "saved per new ability" is the ~600 figure quoted in the user's brief.)

### 7.3 What stays ability-specific

- The path-style of source files (e.g. `mcp_dir / tools / get-*.ts` regex) — could be parametrized but most abilities will be small enough to ship a 5-line adapter.
- `core_goal_test_pack.yaml` content (per ability).
- `<ability>_vocab.yaml` content (CJK anchors + discriminators per ability).
- The `eval_pack.yaml` (per ability; trigger eval prompts are domain-specific).

### 7.4 CLI sketch

```bash
# Generic harness invocation (one ability per call)
python tools/eval_skill.py \
    --ability-id chip-usage-helper \
    --skill .agents/skills/chip-usage-helper/SKILL.md \
    --rule .cursor/rules/chip-usage-helper.mdc \
    --vocab .agents/skills/chip-usage-helper/vocab.yaml \
    --eval-pack .local/dogfood/2026-04-29/abilities/chip-usage-helper/eval_pack.yaml \
    --core-goal-pack .agents/skills/chip-usage-helper/core_goal_test_pack.yaml \
    --test-cmd "npm test --prefix mcp" \
    --source-tree ChipPlugins/chips/chip_usage_helper/mcp/src \
    --out .local/dogfood/2026-04-29/abilities/chip-usage-helper/round_11/metrics_report.yaml
```

### 7.5 Python API sketch

```python
from tools.eval_skill import EvalSkill, AbilityAdapter

adapter = AbilityAdapter(
    ability_id="chip-usage-helper",
    skill_md=Path("..."),
    routing_rule=Path("..."),
    vocab_path=Path("..."),
    eval_pack_path=Path("..."),
    core_goal_pack_path=Path("..."),
    test_cmd=["npm", "test", "--prefix", "mcp"],
    source_tree=Path("..."),
)
result = EvalSkill(adapter).run_round(round_id="round_11")
result.write_metrics_report(Path("..."))
```

---

## 8. L4 Multi-Handler Redundant-Call Analyzer — `tools/multi_handler_redundant_call.py`

### 8.1 The user's pain (verbatim quote)

> "L4 redundant-call analyzer 走全部 handler — 我这次就是因为 R5 只测了一个 handler 才在 R8 才发现 get-rankings 也有同样模式" — `feedback_for_v0.2.0.md` Top-5 改进建议 #3

### 8.2 Algorithm

For an ability with multiple entrypoints (MCP tools, CLI subcommands, multiple Skill scripts):

1. **Enumerate handlers**:
   - For an MCP: scan `mcp_src/tools/*.ts` (or equivalent registration glob).
   - For a Skill: scan `scripts/` + entries declared in SKILL.md `tools:` frontmatter.
   - For a CLI: enumerate subcommands via `--help` parse.
2. **Per-handler L3/L4 analysis**: apply the same logic as `eval_chip_usage_helper.py:_analyze_handler_file` (count `await x()` + `db.foo.bar()` + `compute*()` calls; compute redundancy = sum(c-1 for c>1) / total_steps).
3. **Aggregate**:
   - `L3_step_count` = step count of the **primary** handler (the one users hit most; typically the composite handler like `get-dashboard-data`).
   - `L4_redundant_call_ratio` = **MAX** across all handlers (any single redundant-call hotspot is a problem).
   - `per_handler` breakdown (list) for diagnosis.
4. **Report**: emit JSON / YAML; integrate into `metrics_report.yaml` under `metrics.latency_path`.

### 8.3 API outline

```python
# tools/multi_handler_redundant_call.py

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Callable

@dataclass
class HandlerAnalysis:
    handler_path: Path
    handler_id: str
    step_count: int
    redundant_call_ratio: float
    redundant_calls: dict[str, int]   # call_name -> dup count

@dataclass
class AggregateAnalysis:
    primary_handler: HandlerAnalysis
    per_handler: list[HandlerAnalysis]
    L3_step_count: int                # = primary.step_count
    L4_redundant_call_ratio: float    # = max(h.redundant_call_ratio for h in per_handler)
    L4_aggregation_method: str        # "max"
    diagnostic_notes: list[str]       # e.g. "get-rankings has redundancy 0.40 — same pattern as get-dashboard"

def enumerate_handlers(
    source_tree: Path,
    registration_glob: str = "tools/*.ts",
    primary_handler_filename: str | None = None,
) -> list[Path]:
    """Find handler files; primary defaults to the first matched alphabetically."""
    ...

def analyze_handler(
    handler_path: Path,
    call_patterns: dict[str, str] | None = None,
) -> HandlerAnalysis:
    """Run the await/db/compute regex pass; default patterns work for TypeScript MCP."""
    ...

def analyze_all(
    source_tree: Path,
    registration_glob: str = "tools/*.ts",
    primary_handler_filename: str | None = None,
    call_patterns: dict[str, str] | None = None,
) -> AggregateAnalysis:
    """Top-level entrypoint; called by tools/eval_skill.py L3/L4 helpers."""
    ...
```

### 8.4 The pattern of the bug

`chip-usage-helper` Round 5 reportedly only analyzed `get-dashboard-data.ts`, missing that `get-rankings.ts` had the **same redundant-DB-call pattern** (`db.users.findMany` called 2x). Round 8 finally surfaced it (when R8 description_competition_index hoist required scanning all neighbor SKILL.md, the harness incidentally walked `tools/*.ts` and exposed the duplicate). The new Multi-Handler analyzer catches this on Round 1 of any new ability.

### 8.5 Diagnostic_notes field

`AggregateAnalysis.diagnostic_notes` is a free-text list of human-readable findings, e.g.:

```yaml
diagnostic_notes:
  - "get-rankings.ts: redundant_call_ratio 0.40, same `db.users.findMany` 2x pattern as primary"
  - "get-week-usage.ts: step_count 5 — within budget"
  - "L4_max = 0.40 from get-rankings, exceeds primary (0.27); consider memoizing db.users in a higher scope"
```

These notes are not metrics but are useful inputs to `next_action_plan.yaml.actions`.

---

## 9. Acceptance Criteria for v0.3.0 Spec (Stage 2 input)

The v0.3.0 spec MUST satisfy ALL of the following before ship:

### 9.1 Additivity discipline (preservation of v0.2.0 Normative)

- [ ] §3 / §4 / §5 / §6 / §7 / §8 / §11 byte-identical to v0.2.0 (verified via `diff` and `tools/spec_validator.py`).
- [ ] §3.1 R6 7×37 sub-metric counts unchanged (no D8 added; C0 lives at top-level per §3.4).
- [ ] §4.1 threshold table 30 cells unchanged.
- [ ] §6.1 value_vector 7 axes unchanged.
- [ ] §11.1 forever-out 4 items unchanged.
- [ ] Frontmatter pattern matches v0.2.0 promotion: `version: v0.3.0`, `supersedes: v0.2.0`, `effective_date: <YYYY-MM-DD>`.

### 9.2 New Normative §14 (Core Goal Invariant)

- [ ] §14.1 defines `core_goal` REQUIRED field on `BasicAbility`.
- [ ] §14.2 defines `core_goal_test_pack.yaml` schema with ≥3 cases requirement and "expected_shape, not exact equality" rule.
- [ ] §14.3 defines `C0_core_goal_pass_rate` metric with `MUST = 1.0` rule and "no regression" rule.
- [ ] §14.4 defines rollback rule (REVERT-only when C0 regresses).
- [ ] §14 explicitly states C0 is **top-level invariant**, NOT R6 D8 (per §3.4 recommendation).

### 9.3 New Normative §15 (round_kind Enum)

- [ ] §15.1 defines `round_kind ∈ {code_change, measurement_only, ship_prep, maintenance}`.
- [ ] §15.2 defines per-kind iteration_delta clause (strict / monotonicity-only / WAIVED / WAIVED).
- [ ] §15.3 defines per-kind C0 clause (= 1.0 + monotonicity).
- [ ] §15.4 clarifies interaction with §4.2 promotion rule (measurement_only counts; ship_prep/maintenance don't).
- [ ] `templates/next_action_plan.template.yaml` extended additively to add `round_kind` field (existing fields unchanged).
- [ ] `templates/iteration_delta_report.template.yaml` extended additively to add `core_goal` block (existing fields unchanged).

### 9.4 New Informative §16 (Multi-Ability Layout)

- [ ] §16.1 specifies `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` layout.
- [ ] §16.2 specifies migration path (legacy retained for Si-Chip self; new ability MUST use new layout).
- [ ] §16.3 marks Informative @ v0.3.0 with explicit "promote to Normative @ v0.3.x once 2+ abilities ship under new layout".

### 9.5 spec_validator.py extensions (additive)

- [ ] **+1 BLOCKER**: `CORE_GOAL_FIELD_PRESENT` — every BasicAbilityProfile YAML in `.local/dogfood/.../basic_ability_profile.yaml` must contain `basic_ability.core_goal.{statement, test_pack_path, minimum_pass_rate}`.
- [ ] **+1 BLOCKER**: `ROUND_KIND_FIELD_PRESENT_AND_VALID` — every `next_action_plan.yaml` must contain `round_kind ∈ {code_change, measurement_only, ship_prep, maintenance}`.
- [ ] (Existing 9 BLOCKERS continue to PASS unchanged — backward compat for Round 1-13 Si-Chip evidence + Round 1-10 chip-usage-helper evidence.)
- [ ] `--strict-prose-count` mode auto-detects v0.3.0 frontmatter and uses the 37/30 prose totals (unchanged from v0.2.0).

### 9.6 Multi-round dogfood evidence (the actual ship gate)

- [ ] Round 14 `code_change`: introduces `tools/cjk_trigger_eval.py` + `tools/eval_skill.py` + `tools/multi_handler_redundant_call.py` + adds `core_goal` block to Si-Chip's own basic_ability_profile + adds `core_goal_test_pack.yaml` for Si-Chip.
   - Required: C0_core_goal_pass_rate = 1.0; v1_baseline all PASS; ≥1 axis improvement at +0.05 (e.g. context_economy from collapsed harness).
- [ ] Round 15 `measurement_only`: re-runs Si-Chip self-eval through new `tools/eval_skill.py` to verify metric byte-equivalence with Round 13.
   - Required: C0_core_goal_pass_rate = 1.0; v1_baseline all PASS (carry-forward); no axis regression.
- [ ] (Optional, builds confidence) Round 16 `code_change` on chip-usage-helper Round 11: refactor 768-line `eval_chip_usage_helper.py` to ~50-line adapter calling generic harness; verify all R6 metrics byte-equivalent.

### 9.7 §11 forever-out re-affirmation

- [ ] §3.5 forever-out review (this doc) cited verbatim in v0.3.0 spec §14 footer.
- [ ] No new field, schema, or template introduces a marketplace surface, router model training surface, generic IDE compat layer, or markdown-to-CLI conversion surface.

### 9.8 Templates extended additively

- [ ] `templates/basic_ability_profile.schema.yaml` extended additively to include `core_goal` REQUIRED block.
- [ ] `templates/next_action_plan.template.yaml` extended additively for `round_kind` (per §9.3).
- [ ] `templates/iteration_delta_report.template.yaml` extended additively for `core_goal` verdict (per §9.3).
- [ ] All other templates (`router_test_matrix`, `half_retire_decision`, `self_eval_suite`) UNCHANGED.
- [ ] All templates' `$schema_version` bumped from 0.1.0 → 0.2.0 (backward-compat sentinel preserved per Round 11 reconciliation pattern).

---

## 10. Open Questions / Risks (≥3 honest unresolved)

### 10.1 Q1: Should `C0` be the 38th R6 sub-metric (breaking the frozen 7×37 count) or a separate top-level invariant?

**Status**: discussed in §3.4.

**My recommendation**: **Separate top-level invariant**. Rationale (recap):
- Preserves §3.1 R6 frozen 7×37 byte-identical (additivity discipline).
- C0 is binary (pass/fail), not continuous; doesn't fit progressive gate semantics.
- C0 failure has SPECIAL semantic ("failure regardless of other axes"), which doesn't fit value_vector / iteration_delta machinery.

**Counter-argument** (to be fair): a future consumer of `metrics_report.yaml` wanting to programmatically iterate "all R6 metrics" will have to remember "+ C0 lives elsewhere". This is a usability tax. Mitigation: spec_validator + harness emit a synthetic top-level `metrics.all_keys` list including C0 for client convenience.

**Open**: if Stage 2 author or L0 prefers Option A (D8), the §3.1 table count must move to 7×38 with reconciliation log mirroring the v0.1.0 → v0.2.0 prose-count pattern.

### 10.2 Q2: Is multi-ability layout Normative or Informative at v0.3.0?

**Status**: discussed in §5.4.

**My recommendation**: **Informative @ v0.3.0; promote to Normative @ v0.3.x once 2+ abilities have shipped under the new layout (chip-usage-helper already counts as one; Si-Chip self-migration would be the second).**

**Counter-argument**: spec consumers (Cursor / Claude Code / Codex) may treat Informative as "optional" and never migrate, leaving a permanent split between legacy and new layout. Mitigation: spec_validator can warn (not fail) on legacy layout for any new ability introduced post-v0.3.0; this gives "soft Normative" without breaking Si-Chip self.

**Open**: if Stage 2 author wants to lock layout immediately, they need to write a migration script for Si-Chip Round 1-13 evidence (move `.local/dogfood/<DATE>/round_<N>/` → `.local/dogfood/<DATE>/abilities/si-chip/round_<N>/`) and bump every existing artifact. This is feasible but costs ~1 round of pure-housekeeping work.

### 10.3 Q3: How does `round_kind=measurement_only` interact with §4.2 promotion rule's "two consecutive rounds" clause?

**Status**: discussed in §4.3.

**My recommendation**: **YES, `measurement_only` rounds count toward "consecutive" — but only if (a) C0 = 1.0 AND (b) no v1_baseline hard gate regressed. `ship_prep` and `maintenance` do NOT count (their metrics are carry-forward, not fresh observations).**

**Counter-argument**: Allowing `measurement_only` to count means a team could artificially extend coverage to climb gates without ever proving ability quality improved. This is the very pattern v0.3.0 is trying to fix. Mitigation: `measurement_only` rounds DON'T satisfy the iteration_delta clause (RELAXED to monotonicity-only) but DO need C0 = 1.0 + no regression — so the consecutive-rounds counter only ticks when the ability still works, and gate promotion still requires the underlying gate thresholds to hold.

**Open**: an alternative is to require **at least one of the two consecutive rounds to be `code_change`** for promotion eligibility. This is stricter but cleaner. Stage 2 author should pick one; I lean toward "measurement_only counts" for simplicity, with the safety net being that the gate thresholds themselves don't budge.

### 10.4 Q4 (bonus): What's the cost of `core_goal_test_pack.yaml` per ability?

**Status**: not pre-discussed; raised here because it's a real adoption friction.

Each ability author has to write ≥3 careful test cases. For chip-usage-helper that's maybe 30 minutes. For Si-Chip itself the cases are subtler ("did the 8-step protocol complete?" requires running an inner Si-Chip on a synthetic ability), maybe 2-3 hours.

**Risk**: if pack-authoring is too painful, ability authors will write the minimum 3 cases that obviously pass and never grow them, defeating the change-detector value.

**Mitigation**: 
1. ship `tools/scaffold_core_goal_test_pack.py` that takes `intent` + 3 sample prompts and emits a starter pack;
2. encourage growth cadence (e.g. add 1 case per `code_change` round that fixed a bug — this case becomes the regression test for that bug);
3. make spec §14 explicit that `core_goal_test_pack` cases ≠ `eval_pack.yaml` trigger cases (the latter are routing tests, the former are functional contract tests).

### 10.5 Q5 (bonus): Does C0 = 1.0 stay realistic forever, or do we need a "breaking change" escape hatch?

**Status**: not pre-discussed.

Real evolution of an ability sometimes requires intentionally changing user-observable behavior (e.g. chip-usage-helper deciding to render USD instead of CNY for non-CN users). Strict no-regression would block such changes.

**Recommendation**: 
- For 0.x.y abilities (still iterating), the answer is "bump `core_goal_version` in the test pack frontmatter, log the change in `revision_log`, and update `expected_shape` in the same commit". The C0 = 1.0 invariant is over the **current pack version**, not over historical packs.
- For 1.0.0+ abilities, intentionally changing `core_goal` semantics MUST be MAJOR-version bump (per §2.7 semver).

This keeps the spec usable while preserving the "no silent regression" guarantee.

### 10.6 Confidence scoring for Stage 2

I assess confidence in each of the 5 v0.3.0 changes:

| Change | My confidence Stage 2 can ship cleanly | Risks |
|---|---|---|
| `core_goal` field + test_pack + C0 + no-regression | **High** | Open: §3.4 D8-vs-top-level decision (§10.1); pack-authoring friction (§10.4) |
| `round_kind` enum | **High** | Open: §10.3 promotion rule interaction |
| Multi-ability layout | **Medium** | Open: §10.2 Normative-vs-Informative; Si-Chip self migration cost |
| Generic CJK trigger evaluator | **High** | Risk: vocab schema needs care to support EN-only abilities (set `cjk_*` to `{}` should work) |
| Generic eval_skill.py + multi-handler L4 | **High** | Risk: `test_runner` adapter must handle 3+ test frameworks (vitest, pytest, custom) — scope for v0.3.0 vs v0.3.x |

Overall confidence Stage 2 spec authoring can proceed from this brief: **High**. The open questions in §10.1-10.5 all have my recommended resolutions; Stage 2 author may agree or override but won't be missing context.

---

## 11. Cross-References (Informative)

| This doc § | v0.2.0 spec § | v0.3.0 spec target § |
|---|---|---|
| §3 (core goal) | §2.1 (BasicAbility schema), §6.1 (value_vector — orthogonal) | NEW §14 |
| §4 (round_kind) | §4.1 row 10 (iteration_delta), §8.3 (multi-round rule) | NEW §15 |
| §5 (multi-ability layout) | §10.1 (落盘位置) | NEW §16 (Informative) |
| §6 (CJK trigger evaluator) | §3.1 D6 (R1/R2/R3/R4), §5.1 #3 (description optimization) | NO new §; tooling only |
| §7 (eval_skill.py harness) | §8.1 step 2 (evaluate), §8.2 evidence #2 (metrics_report) | NO new §; tooling only |
| §8 (multi-handler L4 analyzer) | §3.1 D3 (L3/L4) | NO new §; tooling only |

| This doc § | R-ref (existing) | Relationship |
|---|---|---|
| §3 (core goal) | r9_half_retirement_framework.md §1 | C0 = orthogonal to value_vector; both exist together |
| §4 (round_kind) | spec §4.2 | round_kind is the **kind** dimension; gate thresholds are the **level** dimension; both compose |
| §5 (multi-ability layout) | r10_self_registering_skill_roadmap.md §3-§4 | repository layout extended with `abilities/<id>/` subtree |
| §6 (CJK trigger evaluator) | r6_metric_taxonomy.md §3.1 D6 | concrete tooling for R3_trigger_F1 |
| §7 (eval_skill.py harness) | r6_metric_taxonomy.md §3.1 (all dims) | unified entry point for all 7 dim measurement |
| §8 (multi-handler L4 analyzer) | r6_metric_taxonomy.md §3.1 D3 | L3/L4 measurement covering all entrypoints |

---

## 12. Glossary (Informative)

| Term | Definition |
|---|---|
| **Core goal** | The persistent, never-regress functional outcome of a BasicAbility, expressed as a one-sentence statement + a versioned test pack. (NEW v0.3.0) |
| **Core goal test pack** | YAML file enumerating ≥3 test cases (prompt + expected_shape) that, when run against the ability, MUST always pass. (NEW v0.3.0) |
| **C0_core_goal_pass_rate** | Top-level invariant metric = (cases_passed) / (cases_total); spec-locked at 1.0. (NEW v0.3.0) |
| **round_kind** | Categorical label for each dogfood round ∈ {code_change, measurement_only, ship_prep, maintenance}. (NEW v0.3.0) |
| **measurement_only round** | A round that adds metric coverage / instrumentation without modifying ability source; iteration_delta clause RELAXED to monotonicity-only. (NEW v0.3.0) |
| **Pluggable vocabulary** | Per-ability YAML supplying ASCII anchors + CJK substrings + discriminator phrases for the generic CJK-aware trigger evaluator. (NEW v0.3.0) |
| **Multi-ability layout** | `.local/dogfood/<DATE>/abilities/<id>/round_<N>/` directory structure enabling parallel dogfood. (NEW v0.3.0; Informative @ v0.3.0) |
| **Generic eval_skill.py harness** | `tools/eval_skill.py` providing a single entry point for any BasicAbility's per-round evaluation. (NEW v0.3.0) |
| **Multi-handler L4 analyzer** | `tools/multi_handler_redundant_call.py` walking ALL ability entrypoints (not just primary) to compute L3/L4. (NEW v0.3.0) |
| **Hyrum's Law (citation)** | "All observable behaviors of your system will be depended on by somebody." (https://www.hyrumslaw.com/) |
| **Characterization test (citation)** | A change-detector test for legacy code; coined by Michael Feathers. (https://en.wikipedia.org/wiki/Characterization_test) |

---

## 13. Provenance & Sign-off

- **Author role**: L3 Task Agent for Si-Chip v0.3.0 dogfood cycle, Stage 1: Research.
- **Wall-clock budget**: ~30 minutes; actual elapsed (research + drafting) within budget.
- **Stage**: Research only. **No spec authoring; no template edits; no source code changes** were made by this stage; this doc lives at `.local/research/r11_core_goal_invariant.md` per existing R-doc convention.
- **Owned files (this stage)**: `.local/research/r11_core_goal_invariant.md` (this file).
- **Read-only files (this stage)**: every other file in the repo.
- **Stage 2 input**: this doc's §3-§8 propose the v0.3.0 spec content; §9 is the verification checklist; §10 is the punch list of decisions Stage 2 must make explicitly.
- **§11 forever-out compliance**: re-checked in §3.5; no new fields touch marketplace, router model training, generic IDE compat, or Markdown-to-CLI conversion.
- **Hard rules respected (workspace + AGENTS.md)**: "No Silent Failures" (§3.3.2 rollback rule + §10.4 mitigation); "Mandatory Verification" (§9 acceptance criteria including reverify-via-spec_validator); "Protected Branch Workflow" (this is research; merge happens at Stage 2 + 3 + Round 14/15 dogfood); v0.2.0 §3-§11 byte-identical preservation (§9.1).

---

## End of R11 · Core-Goal Invariant & v0.3.0 Capacity Lifts (research design brief)
