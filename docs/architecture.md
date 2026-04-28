---
layout: default
title: Architecture
---

<div lang="en" markdown="1">

# Architecture

</div>

<div lang="zh" markdown="1">

# 架构

</div>

// CHAPTER 01 //

<div lang="en" markdown="1">

## 1. Source-of-truth and platform mirrors

The skill payload is mirrored from a single canonical source into the two
runtime platform trees, plus a derived release tarball that the one-line
installer consumes.

</div>

<div lang="zh" markdown="1">

## 1. 源头与平台镜像

技能负载从单一规范源头镜像到两个运行时平台目录树，外加一个由 install.sh
一键安装脚本所消费的衍生发布 tarball。

</div>

```mermaid
flowchart LR
    spec[".local/research/spec_v0.1.0.md<br/>(frozen)"]
    rules[".rules/si-chip-spec.mdc"]
    agentsmd["AGENTS.md"]
    skill[".agents/skills/si-chip/<br/>SKILL.md + references + scripts"]
    cursor[".cursor/skills/si-chip/"]
    claude[".claude/skills/si-chip/"]
    bridge[".cursor/rules/si-chip-bridge.mdc"]
    spec --> rules --> agentsmd
    spec --> skill
    skill --> cursor
    skill --> claude
    cursor -.-> bridge
```

// CHAPTER 02 //

<div lang="en" markdown="1">

## 2. Dogfood loop (spec section 8.1 Frozen Order)

Each dogfood round walks the 8 frozen steps in order; the package-register
step closes the loop and feeds the next round's profile step.

</div>

<div lang="zh" markdown="1">

## 2. Dogfood 循环（规范 §8.1 冻结顺序）

每一轮 dogfood 都按顺序走完 8 个冻结步骤；package-register 步骤完成闭环，
并为下一轮的 profile 步骤提供输入。

</div>

```mermaid
flowchart TB
    profile["1. profile<br/>basic_ability_profile.yaml"]
    evaluate["2. evaluate<br/>metrics_report.yaml"]
    diagnose["3. diagnose<br/>R6 7-dim scan"]
    improve["4. improve<br/>next_action_plan.yaml"]
    routerTest["5. router-test<br/>router_floor_report.yaml"]
    halfRetire["6. half-retire-review<br/>half_retire_decision.yaml"]
    iterate["7. iterate<br/>iteration_delta_report.yaml"]
    package["8. package-register"]
    profile --> evaluate --> diagnose --> improve --> routerTest --> halfRetire --> iterate --> package
    package -. "next round" .-> profile
```

// CHAPTER 03 //

<div lang="en" markdown="1">

## 3. Three progressive gate profiles

Promotion requires 2 consecutive passes at the current gate; demotion is
triggered by 2 consecutive failures. v0.1.0 ships at `v1_baseline` (relaxed).

</div>

<div lang="zh" markdown="1">

## 3. 三档渐进 gate profile

升档需要在当前 gate 连续两轮通过；降档由连续两轮失败触发。v0.1.0 在
`v1_baseline`（relaxed）档位交付。

</div>

```mermaid
flowchart LR
    v1["v1_baseline<br/>relaxed"]
    v2["v2_tightened<br/>standard"]
    v3["v3_strict<br/>strict"]
    v1 -- "2 consecutive passes" --> v2
    v2 -- "2 consecutive passes" --> v3
    v3 -- "2 consecutive failures" --> v2
    v2 -- "2 consecutive failures" --> v1
```

// CHAPTER 04 //

<div lang="en" markdown="1">

## 4. Decision tree for half-retirement (spec section 6.2)

The 7-axis value_vector is computed every round. The decision branches on
`task_delta`, the efficiency axes, and `governance_risk_delta`.

</div>

<div lang="zh" markdown="1">

## 4. 半退役决策树（规范 §6.2）

每一轮都会计算 7 维 value_vector。决策分支由 `task_delta`、各效率维度以及
`governance_risk_delta` 共同决定。

</div>

```mermaid
flowchart TB
    vv["7-axis value_vector<br/>computed"]
    keep["decision: keep"]
    halfRetire["decision: half_retire"]
    retire["decision: retire"]
    disable["decision: disable_auto_trigger"]
    vv -- "task_delta >= +0.10<br/>OR all v1 hard gates pass" --> keep
    vv -- "task_delta near 0<br/>AND any efficiency axis<br/>>= gate threshold" --> halfRetire
    vv -- "all axes <= 0<br/>OR governance_risk_delta < 0" --> retire
    vv -- "governance_risk_delta<br/>significantly negative" --> disable
```

// CHAPTER 05 //

<div lang="en" markdown="1">

## 5. Cross-tree drift contract (zero drift required)

Every ship-eligible commit must satisfy `ALL_TREES_DRIFT_ZERO`: the
`devolaflow.local.drift` hash check compares SHA256 across the source-of-truth
and the two platform mirrors. Any mismatch fails CI.

</div>

<div lang="zh" markdown="1">

## 5. 跨树漂移契约（要求零漂移）

任何具备 ship 资格的提交都必须满足 `ALL_TREES_DRIFT_ZERO`：
`devolaflow.local.drift` 哈希检查会在源头与两个平台镜像之间比对 SHA256。
任意不匹配都会让 CI 失败。

</div>

```mermaid
flowchart LR
    src[".agents/skills/si-chip/"]
    cur[".cursor/skills/si-chip/"]
    cla[".claude/skills/si-chip/"]
    drift["devolaflow.local.drift hash check"]
    src --> drift
    cur --> drift
    cla --> drift
    drift -- "any mismatch" --> fail["DRIFT_DETECTED -> CI fail"]
    drift -- "all SHA256 match" --> pass["ALL_TREES_DRIFT_ZERO -> ship-eligible"]
```

<div lang="en" markdown="1">

> Mermaid lint compliance: every node id is camelCase / snake_case (no spaces);
> labels with quoted text use double quotes; no reserved keywords as ids.

</div>

<div lang="zh" markdown="1">

> Mermaid 规范遵从：每个节点 id 都使用 camelCase / snake_case（不含空格）；
> 含引号文本的 label 使用双引号；不使用保留字作为 id。

</div>
