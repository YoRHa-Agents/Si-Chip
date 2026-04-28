---
layout: default
title: Architecture
---

# Architecture

## 1. Source-of-truth and platform mirrors

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

## 2. Dogfood loop (spec section 8.1 Frozen Order)

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

## 3. Three progressive gate profiles

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

## 4. Decision tree for half-retirement (spec section 6.2)

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

## 5. Cross-tree drift contract (zero drift required)

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

> Mermaid lint compliance: every node id is camelCase / snake_case (no spaces);
> labels with quoted text use double quotes; no reserved keywords as ids.
