#!/usr/bin/env python3
"""§6.4 Reactivation-trigger detector for Si-Chip Round 12.

Implements all 6 reactivation triggers enumerated in spec §6.4 of
``.local/research/spec_v0.2.0-rc1.md`` (verbatim from v0.1.0; the v0.2.0-rc1
reconciliation did NOT touch §6 Normative semantics — only §13.4 prose
counts; see ``.local/dogfood/2026-04-28/round_11/raw/normative_diff_check.json``
``verdict=NORMATIVE_TABLES_BYTE_IDENTICAL``). The detector ingests the
canonical Round-N evidence triple — ``basic_ability_profile.yaml``,
``half_retire_decision.yaml``, ``metrics_report.yaml`` — and answers the
question "should this ability return to ``evaluated`` for review?".

The 6 triggers (canonical ordering / IDs match spec §6.4 + the
``review.triggers`` list in ``half_retire_decision.template.yaml``):

1. ``new_model_no_ability_baseline_gap`` (a.k.a. ``trigger_new_model_task_delta``)
   — On a NEW no-ability baseline, ``T3_baseline_delta`` rebounds to
   ``>= +0.10``. Fires when the underlying base model has regressed on
   this task (the wrapper is once-again worth keeping).

2. ``new_scenario_or_domain_match`` (``trigger_new_scenario_or_domain_match``)
   — A new scenario or domain emerges that the ability's
   ``references`` / ``scripts`` happen to cover. Detected by an
   intent-token overlap against an external scenario catalog; for
   v0.1.11 no catalog exists so the trigger is deterministically
   parameterised-off.

3. ``router_test_requires_ability_for_cheap_model``
   (``trigger_router_floor_drop``) — Router-test shows a cheaper model
   now needs the ability to pass; ``router_floor`` drops by one tier
   (e.g. ``composer_2/default`` → ``composer_2/fast``). Tier ordering
   is deterministic (cheaper-first).

4. ``efficiency_axis_becomes_significant`` (``trigger_efficiency_axis_significant``)
   — Any one of ``context_delta`` / ``token_delta`` / ``latency_delta``
   crosses ``≥ 0.25``.

5. ``upstream_api_change_wrapper_stabilizes`` (``trigger_upstream_api_change``)
   — A dependency API or CLI change makes the wrapper more stable than
   the base model's freeform output. Detected via an opt-in
   ``wrapper_stability_log`` JSON file; for v0.1.11 no such log
   exists so the trigger is deterministically parameterised-off.

6. ``manual_invocation_rebound`` (``trigger_manual_invocation_rebound``)
   — Manual call frequency rises back to ``≥ 5`` invocations in the
   trailing 30 days (window configurable). Detected via an opt-in
   ``invocation_log`` file; for v0.1.11 no log exists so the trigger
   is deterministically parameterised-off.

Top-level entry point :func:`detect_reactivation` ingests the three
artefact paths and returns
``{"triggered_count": int, "triggered_names": list[str], "per_trigger":
{name: {"triggered": bool, "reason": str, "evidence": dict}}}``. The CLI
``--check`` flag wraps that and applies the spec §6.4 sanity rule:

* exit 0 if ``triggered_count == 0`` (no wake-up needed; or the ability
  is already ``keep`` and nothing fires);
* exit 0 if ``triggered_count > 0`` AND ``decision.action ==
  half_retired`` (the ability IS half_retired and the detector correctly
  flags it for wake-up review);
* exit 2 if ``triggered_count > 0`` AND ``decision.action != half_retired``
  (an UNEXPECTED fire on an active ability — warrants investigation,
  not a silent pass; workspace rule "No Silent Failures" applied).

Workspace-rule compliance
-------------------------
* "No Silent Failures": missing input files raise; malformed YAML / JSON
  raise; invalid value-vector axes raise. The CLI exit-2 path on the
  unexpected-fire case is the equivalent of a re-raised assertion.
* "Mandatory Verification": sibling test ``tools/test_reactivation_detector.py``
  covers ≥ 18 unit tests including each trigger's positive + negative
  paths, edge cases at the threshold boundary, the integration via
  :func:`detect_reactivation`, and CLI exit codes.
* Spec §11.1 forever-out compliance: no marketplace, no router model
  training, no Markdown-to-CLI converter, no generic IDE compat layer.
  This module is a pure-Python deterministic detector that consumes
  YAML/JSON inputs and emits a JSON verdict — no learned weights, no
  online learning, no distribution surface.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.reactivation_detector")

SCRIPT_VERSION = "0.1.0"

# ─────────────── Frozen §6.4 trigger metadata ───────────────
# Six canonical trigger IDs (verbatim, byte-equal to spec §6.4 prose
# AND the ``review.triggers`` list in
# ``templates/half_retire_decision.template.yaml`` AND every prior
# ``half_retire_decision.yaml`` artifact's review.triggers). Reordering
# is forbidden — the IDs are the runtime contract.
TRIGGER_IDS: Tuple[str, ...] = (
    "new_model_no_ability_baseline_gap",
    "new_scenario_or_domain_match",
    "router_test_requires_ability_for_cheap_model",
    "efficiency_axis_becomes_significant",
    "upstream_api_change_wrapper_stabilizes",
    "manual_invocation_rebound",
)

# Spec §6.4 default thresholds (frozen; any change MUST bump spec version).
DEFAULT_TASK_DELTA_THRESHOLD = 0.10        # trigger 1
DEFAULT_EFFICIENCY_AXIS_THRESHOLD = 0.25   # trigger 4
DEFAULT_MANUAL_INVOCATION_THRESHOLD = 5    # trigger 6
DEFAULT_MANUAL_INVOCATION_WINDOW_DAYS = 30  # trigger 6

# Deterministic tier ordering for trigger 3. Lower tier = cheaper /
# faster (router_floor "drops" toward this end means a cheaper model
# now suffices — a wake-up signal). Mirrors the cost_order used by
# ``with_ability_runner.simulate_router_sweep`` and the §5.1
# Fallback policy ladder ``deterministic_memory_router → composer_2/fast
# → sonnet/default → opus/extended``.
ROUTER_FLOOR_TIER_ORDER: Tuple[str, ...] = (
    "deterministic_memory_router/fast",
    "deterministic_memory_router/default",
    "composer_2/fast",
    "composer_2/default",
    "composer_2/extended",
    "sonnet_shallow/fast",
    "sonnet_shallow/default",
    "haiku_4_5/fast",
    "haiku_4_5/default",
    "sonnet_4_6/fast",
    "sonnet_4_6/default",
    "sonnet_4_6/extended",
    "opus_4_7/default",
    "opus_4_7/extended",
    "gpt_5_mini/default",
    "gpt_5_mini/extended",
)

# Efficiency axes considered for trigger 4 (spec §6.1 + §6.4).
EFFICIENCY_AXES_FOR_REACTIVATION: Tuple[str, ...] = (
    "context_delta",
    "token_delta",
    "latency_delta",
)


# ─────────────── helpers ───────────────


def _load_yaml(path: Path) -> Any:
    """Load a YAML file or raise (no silent failure)."""

    if not path.exists():
        raise FileNotFoundError(f"yaml path not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"failed to parse YAML {path}: {exc}") from exc


def _load_json(path: Path) -> Any:
    """Load a JSON file or raise (no silent failure)."""

    if not path.exists():
        raise FileNotFoundError(f"json path not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"failed to parse JSON {path}: {exc}") from exc


def _trigger_result(
    name: str,
    triggered: bool,
    reason: str,
    *,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the canonical per-trigger verdict shape."""

    return {
        "trigger": name,
        "triggered": bool(triggered),
        "reason": reason,
        "evidence": evidence or {},
    }


def _router_floor_tier_index(floor: Optional[str]) -> Optional[int]:
    """Return the index of ``floor`` in :data:`ROUTER_FLOOR_TIER_ORDER`.

    Returns ``None`` for an unknown floor (so the caller can decide
    whether to skip or warn). The ordering is cheaper-first:
    ``ROUTER_FLOOR_TIER_ORDER[0]`` is the cheapest tier.

    >>> _router_floor_tier_index("composer_2/fast")
    2
    >>> _router_floor_tier_index("composer_2/default")
    3
    >>> _router_floor_tier_index("unknown/tier") is None
    True
    """

    if not isinstance(floor, str):
        return None
    try:
        return ROUTER_FLOOR_TIER_ORDER.index(floor)
    except ValueError:
        return None


# ─────────────── §6.4 Trigger 1 ───────────────


def trigger_new_model_task_delta(
    profile: Dict[str, Any],
    metrics_report: Dict[str, Any],
    *,
    threshold: float = DEFAULT_TASK_DELTA_THRESHOLD,
    new_baseline_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Spec §6.4 trigger 1: ``new_model_no_ability_baseline_gap``.

    "On a new no-ability baseline, ``task_delta`` returns to ``>= +0.10``"
    (spec §6.4 trigger #1 verbatim; threshold tunable for future spec
    revisions but defaults to the §6.4 frozen ``+0.10``).

    The trigger fires when:

    * ``new_baseline_path`` is supplied (a fresh ``no_ability``
      ``summary.json`` from a NEW model run), AND
    * the recomputed ``task_delta = pass_with(current) - pass_without(new)``
      is ``>= threshold``.

    For v0.1.11 no such fresh new-model baseline exists yet, so when
    ``new_baseline_path`` is ``None`` the trigger returns ``triggered=False``
    with reason "no new baseline available" — a documented degenerate
    path that is NOT silent (the per-trigger ``reason`` field carries
    the explanation; workspace rule "No Silent Failures" satisfied).

    Args:
        profile: Loaded ``basic_ability_profile.yaml`` mapping.
        metrics_report: Loaded ``metrics_report.yaml`` mapping (needed
            for the current ``pass_with`` value).
        threshold: Task-delta threshold; defaults to spec §6.4 ``+0.10``.
        new_baseline_path: Path to a NEW ``no_ability/summary.json`` (or
            ``result.json``) produced under a freshly-released base
            model. ``None`` parameterises the trigger off.

    Returns:
        ``{trigger, triggered, reason, evidence}`` dict (see
        :func:`_trigger_result`).

    >>> # No new baseline => trigger off (degenerate but documented).
    >>> r = trigger_new_model_task_delta(
    ...     {"basic_ability": {}}, {"metrics": {}}, new_baseline_path=None,
    ... )
    >>> r["triggered"], "no new baseline" in r["reason"]
    (False, True)
    """

    if not isinstance(profile, dict):
        raise ValueError("profile must be a dict")
    if not isinstance(metrics_report, dict):
        raise ValueError("metrics_report must be a dict")

    if new_baseline_path is None:
        return _trigger_result(
            TRIGGER_IDS[0],
            False,
            "no new baseline available (parameterised off — pass --new-baseline to enable)",
            evidence={"threshold": threshold},
        )

    new_baseline = _load_json(Path(new_baseline_path))
    pass_without_new: Optional[float] = None
    if isinstance(new_baseline, dict):
        # Accept either a flat summary.json shape (with "pass_rate" or
        # "aggregates.mean_pass_rate") OR a per-case result.json
        # (with "pass_rate"). Both forms are loaded as a single dict.
        if "pass_rate" in new_baseline:
            try:
                pass_without_new = float(new_baseline["pass_rate"])
            except (TypeError, ValueError):
                pass_without_new = None
        elif (
            "aggregates" in new_baseline
            and isinstance(new_baseline["aggregates"], dict)
            and "mean_pass_rate" in new_baseline["aggregates"]
        ):
            try:
                pass_without_new = float(new_baseline["aggregates"]["mean_pass_rate"])
            except (TypeError, ValueError):
                pass_without_new = None

    if pass_without_new is None:
        return _trigger_result(
            TRIGGER_IDS[0],
            False,
            "new baseline payload missing pass_rate / aggregates.mean_pass_rate",
            evidence={
                "threshold": threshold,
                "new_baseline_path": str(new_baseline_path),
            },
        )

    metrics = (
        metrics_report.get("metrics")
        if isinstance(metrics_report.get("metrics"), dict)
        else {}
    )
    task_quality = metrics.get("task_quality", {}) if isinstance(metrics, dict) else {}
    pass_with = task_quality.get("T1_pass_rate")
    if pass_with is None:
        return _trigger_result(
            TRIGGER_IDS[0],
            False,
            "current metrics_report missing T1_pass_rate",
            evidence={
                "threshold": threshold,
                "new_baseline_path": str(new_baseline_path),
            },
        )
    try:
        pass_with_f = float(pass_with)
    except (TypeError, ValueError):
        return _trigger_result(
            TRIGGER_IDS[0],
            False,
            f"T1_pass_rate is not a float: {pass_with!r}",
            evidence={"threshold": threshold},
        )

    new_task_delta = pass_with_f - pass_without_new
    triggered = new_task_delta >= threshold
    reason = (
        f"new no-ability baseline pass_rate={pass_without_new:.4f}; "
        f"task_delta_new={new_task_delta:.4f}; threshold={threshold:.2f}; "
        f"{'fires' if triggered else 'below threshold'}"
    )
    return _trigger_result(
        TRIGGER_IDS[0],
        triggered,
        reason,
        evidence={
            "threshold": threshold,
            "pass_with": pass_with_f,
            "pass_without_new": pass_without_new,
            "new_task_delta": new_task_delta,
            "new_baseline_path": str(new_baseline_path),
        },
    )


# ─────────────── §6.4 Trigger 2 ───────────────


def trigger_new_scenario_or_domain_match(
    profile: Dict[str, Any],
    *,
    scenario_catalog_path: Optional[Path] = None,
    overlap_threshold: float = 0.30,
) -> Dict[str, Any]:
    """Spec §6.4 trigger 2: ``new_scenario_or_domain_match``.

    "A new scenario or domain emerges that the ability's references /
    scripts happen to cover" (spec §6.4 trigger #2 verbatim).

    Detected by:

    1. Loading a scenario catalog (JSON list of
       ``{scenario_id, intent_text}`` entries describing newly-discovered
       scenarios in the workspace).
    2. Tokenising the ability's ``intent`` field (BasicAbility schema
       §2.1) and each scenario's ``intent_text``.
    3. Computing the Jaccard similarity of token sets per scenario.
    4. Firing the trigger when ANY scenario's overlap exceeds
       ``overlap_threshold`` (default 0.30 — a conservative starting
       point; future tuning per spec §3.2 frozen-constraint #4).

    For v0.1.11 NO scenario catalog exists in the workspace
    (``.local/scenario_catalog/`` is unborn); the trigger is
    deterministically parameterised-off in that state with
    ``triggered=False`` and reason "no scenario catalog". This is
    surface-area-bounded so future rounds can wire in a real catalog
    without changing the per-trigger contract.

    Args:
        profile: Loaded ``basic_ability_profile.yaml`` mapping.
        scenario_catalog_path: Optional path to a JSON file listing
            workspace scenarios.
        overlap_threshold: Jaccard threshold above which a scenario
            counts as "covered". Defaults to 0.30.

    Returns:
        ``{trigger, triggered, reason, evidence}`` dict.

    >>> r = trigger_new_scenario_or_domain_match(
    ...     {"basic_ability": {"intent": "x"}}, scenario_catalog_path=None,
    ... )
    >>> r["triggered"], "no scenario catalog" in r["reason"]
    (False, True)
    """

    if not isinstance(profile, dict):
        raise ValueError("profile must be a dict")

    if scenario_catalog_path is None:
        return _trigger_result(
            TRIGGER_IDS[1],
            False,
            "no scenario catalog (parameterised off — pass --scenario-catalog to enable)",
            evidence={"overlap_threshold": overlap_threshold},
        )

    catalog = _load_json(Path(scenario_catalog_path))
    if not isinstance(catalog, list):
        raise ValueError(
            f"scenario catalog must be a JSON list, got {type(catalog).__name__}"
        )

    ba = profile.get("basic_ability", {})
    if not isinstance(ba, dict):
        ba = {}
    intent = ba.get("intent")
    if not isinstance(intent, str) or not intent.strip():
        return _trigger_result(
            TRIGGER_IDS[1],
            False,
            "basic_ability.intent missing or empty — cannot compute overlap",
            evidence={
                "overlap_threshold": overlap_threshold,
                "scenario_catalog_path": str(scenario_catalog_path),
            },
        )

    base_tokens = _tokenise(intent)
    if not base_tokens:
        return _trigger_result(
            TRIGGER_IDS[1],
            False,
            "intent tokenises to empty set",
            evidence={"overlap_threshold": overlap_threshold},
        )

    matches: List[Dict[str, Any]] = []
    for entry in catalog:
        if not isinstance(entry, dict):
            continue
        sid = entry.get("scenario_id") or "<unnamed>"
        text = entry.get("intent_text")
        if not isinstance(text, str) or not text.strip():
            continue
        tokens = _tokenise(text)
        if not tokens:
            continue
        intersect = base_tokens & tokens
        union = base_tokens | tokens
        jaccard = len(intersect) / len(union) if union else 0.0
        matches.append({"scenario_id": sid, "jaccard": jaccard})

    matches.sort(key=lambda m: m["jaccard"], reverse=True)
    top = matches[0] if matches else None
    triggered = bool(top is not None and top["jaccard"] >= overlap_threshold)

    reason = (
        f"top scenario={top['scenario_id'] if top else None!r} "
        f"jaccard={top['jaccard'] if top else 0.0:.4f} "
        f"threshold={overlap_threshold:.2f}; "
        f"{'fires' if triggered else 'below threshold'}"
    )
    return _trigger_result(
        TRIGGER_IDS[1],
        triggered,
        reason,
        evidence={
            "overlap_threshold": overlap_threshold,
            "scenario_catalog_path": str(scenario_catalog_path),
            "n_scenarios": len(catalog),
            "n_scored": len(matches),
            "top_matches": matches[:5],
            "intent": intent,
        },
    )


def _tokenise(text: str) -> set:
    """Return a normalised token set for Jaccard comparison.

    Lowercases, splits on non-alphanumerics, drops 1-char tokens. Keep
    deterministic for reproducible reactivation verdicts (workspace rule
    "No Silent Failures" — same input must yield same output).

    >>> sorted(_tokenise("Hello, World!  hello-WORLD"))
    ['hello', 'world']
    """

    import re

    normalised = re.split(r"[^a-z0-9]+", text.lower())
    return {tok for tok in normalised if len(tok) > 1}


# ─────────────── §6.4 Trigger 3 ───────────────


def trigger_router_floor_drop(
    current_router_floor: Optional[str],
    prior_router_floor: Optional[str],
) -> Dict[str, Any]:
    """Spec §6.4 trigger 3: ``router_test_requires_ability_for_cheap_model``.

    "Router-test shows a cheaper model now needs the ability to pass;
    ``router_floor`` drops by one tier" (spec §6.4 trigger #3 verbatim).

    Compares the current ``router_floor`` against a prior value using
    the deterministic :data:`ROUTER_FLOOR_TIER_ORDER`. Fires when the
    current floor is STRICTLY CHEAPER (lower index) than the prior — a
    cheaper model now passes, which means the ability's value at the
    cheaper tier is significant.

    Args:
        current_router_floor: Current ``"<model>/<thinking_depth>"``.
        prior_router_floor: Prior round's value (the comparison anchor).

    Returns:
        ``{trigger, triggered, reason, evidence}`` dict.

    >>> r = trigger_router_floor_drop("composer_2/fast", "composer_2/default")
    >>> r["triggered"], "drops" in r["reason"]
    (True, True)
    >>> r2 = trigger_router_floor_drop("composer_2/default", "composer_2/default")
    >>> r2["triggered"]
    False
    """

    cur_idx = _router_floor_tier_index(current_router_floor)
    pri_idx = _router_floor_tier_index(prior_router_floor)
    if cur_idx is None or pri_idx is None:
        return _trigger_result(
            TRIGGER_IDS[2],
            False,
            (
                f"router_floor unknown to tier ordering: "
                f"current={current_router_floor!r} prior={prior_router_floor!r}"
            ),
            evidence={
                "current_router_floor": current_router_floor,
                "prior_router_floor": prior_router_floor,
                "tier_order": list(ROUTER_FLOOR_TIER_ORDER),
            },
        )
    triggered = cur_idx < pri_idx
    reason = (
        f"current={current_router_floor} (tier {cur_idx}); "
        f"prior={prior_router_floor} (tier {pri_idx}); "
        f"{'drops' if triggered else 'unchanged or rises'}"
    )
    return _trigger_result(
        TRIGGER_IDS[2],
        triggered,
        reason,
        evidence={
            "current_router_floor": current_router_floor,
            "current_tier_index": cur_idx,
            "prior_router_floor": prior_router_floor,
            "prior_tier_index": pri_idx,
            "drop_steps": pri_idx - cur_idx if triggered else 0,
        },
    )


# ─────────────── §6.4 Trigger 4 ───────────────


def trigger_efficiency_axis_significant(
    value_vector: Dict[str, Any],
    prior_value_vector: Dict[str, Any],
    *,
    threshold: float = DEFAULT_EFFICIENCY_AXIS_THRESHOLD,
    axes: Iterable[str] = EFFICIENCY_AXES_FOR_REACTIVATION,
) -> Dict[str, Any]:
    """Spec §6.4 trigger 4: ``efficiency_axis_becomes_significant``.

    "context_delta / token_delta / latency_delta becomes significant
    (any one crosses ``≥ +0.25``)" (spec §6.4 trigger #4 verbatim).

    Compares each axis's current value against its prior-round value
    and fires when the absolute change is ``>= threshold``. The "≥ 0.25"
    is interpreted as the magnitude of POSITIVE movement on the axis
    (per spec §6.1 axes are "positive = ability helps"); a sudden
    positive jump means the wrapper is once-again worth waking up.

    Negative movement (efficiency degraded) does NOT fire trigger 4 —
    that path is handled by the ``half_retire`` rule in spec §6.2 or
    the ``disable_auto_trigger`` rule, not §6.4.

    Args:
        value_vector: Current half_retire_decision.value_vector mapping.
        prior_value_vector: Prior half_retire_decision.value_vector
            mapping.
        threshold: Per-axis magnitude threshold; defaults to
            spec §6.4 ``+0.25``.
        axes: Iterable of axis names to consider; defaults to
            :data:`EFFICIENCY_AXES_FOR_REACTIVATION` (the three
            spec-named axes).

    Returns:
        ``{trigger, triggered, reason, evidence}`` dict.

    >>> # context_delta moved from -0.05 to +0.30; absolute movement = 0.35
    >>> # current value (+0.30) - prior (-0.05) = +0.35 >= 0.25 → fires.
    >>> r = trigger_efficiency_axis_significant(
    ...     {"context_delta": 0.30, "token_delta": 0.0, "latency_delta": 0.0},
    ...     {"context_delta": -0.05, "token_delta": 0.0, "latency_delta": 0.0},
    ... )
    >>> r["triggered"], "context_delta" in r["reason"]
    (True, True)
    """

    if not isinstance(value_vector, dict) or not isinstance(prior_value_vector, dict):
        raise ValueError("value_vector and prior_value_vector must be dicts")

    movements: Dict[str, Optional[float]] = {}
    for axis in axes:
        cur = value_vector.get(axis)
        pri = prior_value_vector.get(axis)
        if cur is None or pri is None:
            movements[axis] = None
            continue
        try:
            movements[axis] = float(cur) - float(pri)
        except (TypeError, ValueError):
            movements[axis] = None

    fired_axes: List[str] = []
    for axis, delta in movements.items():
        if delta is None:
            continue
        # Spec §6.4 trigger 4: "becomes significant (any crosses ≥ +0.25)".
        # We interpret this as POSITIVE movement of magnitude >= threshold,
        # because §6.1 axes encode "positive = ability helps" — a positive
        # jump is the wake-up signal. Magnitude-only would also fire on
        # degradation, which is handled by §6.2 half_retire / retire rules.
        if delta >= threshold:
            fired_axes.append(axis)

    triggered = bool(fired_axes)
    reason = (
        f"axes movements {movements}; threshold={threshold:.2f}; "
        f"fired={fired_axes if fired_axes else 'none'}"
    )
    return _trigger_result(
        TRIGGER_IDS[3],
        triggered,
        reason,
        evidence={
            "threshold": threshold,
            "axes_considered": list(axes),
            "movements": movements,
            "fired_axes": fired_axes,
        },
    )


# ─────────────── §6.4 Trigger 5 ───────────────


def trigger_upstream_api_change(
    *,
    wrapper_stability_log_path: Optional[Path] = None,
    min_stability_delta: float = 0.10,
) -> Dict[str, Any]:
    """Spec §6.4 trigger 5: ``upstream_api_change_wrapper_stabilizes``.

    "After a dependency API change, the wrapper is more stable than
    the base model's freeform output" (spec §6.4 trigger #5 verbatim).

    Detected via an opt-in JSON log shape::

        {
          "events": [
            {
              "ts": "ISO-8601",
              "api": "<dependency-name>",
              "wrapper_pass_rate_post": 0.91,
              "base_pass_rate_post": 0.74
            },
            ...
          ]
        }

    Fires when ANY event shows ``wrapper_pass_rate_post -
    base_pass_rate_post >= min_stability_delta`` (default ``+0.10``).
    For v0.1.11 NO such log exists, so the trigger is deterministically
    parameterised-off with reason "no api-change log".

    Args:
        wrapper_stability_log_path: Optional JSON file path.
        min_stability_delta: Min wrapper-vs-base pass-rate delta.

    Returns:
        ``{trigger, triggered, reason, evidence}`` dict.

    >>> r = trigger_upstream_api_change(wrapper_stability_log_path=None)
    >>> r["triggered"], "no api-change log" in r["reason"]
    (False, True)
    """

    if wrapper_stability_log_path is None:
        return _trigger_result(
            TRIGGER_IDS[4],
            False,
            (
                "no api-change log (parameterised off — pass "
                "--wrapper-stability-log to enable)"
            ),
            evidence={"min_stability_delta": min_stability_delta},
        )
    payload = _load_json(Path(wrapper_stability_log_path))
    if not isinstance(payload, dict):
        raise ValueError("wrapper_stability_log payload must be a JSON object")
    events = payload.get("events")
    if not isinstance(events, list):
        return _trigger_result(
            TRIGGER_IDS[4],
            False,
            "wrapper_stability_log missing 'events' list",
            evidence={
                "min_stability_delta": min_stability_delta,
                "wrapper_stability_log_path": str(wrapper_stability_log_path),
            },
        )

    fired_events: List[Dict[str, Any]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        try:
            wrapper = float(ev.get("wrapper_pass_rate_post"))
            base = float(ev.get("base_pass_rate_post"))
        except (TypeError, ValueError):
            continue
        delta = wrapper - base
        if delta >= min_stability_delta:
            fired_events.append({**ev, "delta": delta})
    triggered = bool(fired_events)
    reason = (
        f"events={len(events)} fired={len(fired_events)} "
        f"min_stability_delta={min_stability_delta:.2f}; "
        f"{'fires' if triggered else 'no qualifying event'}"
    )
    return _trigger_result(
        TRIGGER_IDS[4],
        triggered,
        reason,
        evidence={
            "min_stability_delta": min_stability_delta,
            "wrapper_stability_log_path": str(wrapper_stability_log_path),
            "n_events": len(events),
            "n_fired": len(fired_events),
            "fired_events": fired_events[:5],
        },
    )


# ─────────────── §6.4 Trigger 6 ───────────────


def trigger_manual_invocation_rebound(
    *,
    invocation_log_path: Optional[Path] = None,
    threshold: int = DEFAULT_MANUAL_INVOCATION_THRESHOLD,
    window_days: int = DEFAULT_MANUAL_INVOCATION_WINDOW_DAYS,
    today: Optional[str] = None,
) -> Dict[str, Any]:
    """Spec §6.4 trigger 6: ``manual_invocation_rebound``.

    "Manual call frequency rises back to ``≥ 5`` invocations in the
    trailing 30 days" (spec §6.4 trigger #6 verbatim).

    Detected via an opt-in JSON log shape::

        {
          "invocations": [
            {"ts": "YYYY-MM-DD", "manual": true},
            {"ts": "YYYY-MM-DD", "manual": false},
            ...
          ]
        }

    Counts entries with ``manual=True`` whose ``ts`` falls within the
    trailing ``window_days`` from ``today`` (defaults to ``date.today()``).
    Fires when the count is ``>= threshold`` (default 5). For v0.1.11 NO
    such log exists, so the trigger is deterministically parameterised-off
    with reason "no invocation log".

    Args:
        invocation_log_path: Optional JSON file path.
        threshold: Invocation count threshold; defaults to spec §6.4 5.
        window_days: Trailing-window length in days; defaults to spec §6.4 30.
        today: Optional ISO date string; defaults to ``date.today()``.

    Returns:
        ``{trigger, triggered, reason, evidence}`` dict.

    >>> r = trigger_manual_invocation_rebound(invocation_log_path=None)
    >>> r["triggered"], "no invocation log" in r["reason"]
    (False, True)
    """

    if invocation_log_path is None:
        return _trigger_result(
            TRIGGER_IDS[5],
            False,
            (
                "no invocation log (parameterised off — pass "
                "--invocation-log to enable)"
            ),
            evidence={"threshold": threshold, "window_days": window_days},
        )
    if window_days <= 0:
        raise ValueError(f"window_days must be > 0, got {window_days}")
    if threshold < 0:
        raise ValueError(f"threshold must be >= 0, got {threshold}")

    payload = _load_json(Path(invocation_log_path))
    if not isinstance(payload, dict):
        raise ValueError("invocation_log payload must be a JSON object")
    invocations = payload.get("invocations")
    if not isinstance(invocations, list):
        return _trigger_result(
            TRIGGER_IDS[5],
            False,
            "invocation_log missing 'invocations' list",
            evidence={
                "threshold": threshold,
                "window_days": window_days,
                "invocation_log_path": str(invocation_log_path),
            },
        )

    import datetime as _dt

    if today is None:
        ref = _dt.date.today()
    else:
        try:
            ref = _dt.date.fromisoformat(today)
        except ValueError as exc:
            raise ValueError(f"today must be YYYY-MM-DD, got {today!r}: {exc}") from exc
    cutoff = ref - _dt.timedelta(days=window_days)

    counted = 0
    skipped = 0
    for inv in invocations:
        if not isinstance(inv, dict):
            skipped += 1
            continue
        if not bool(inv.get("manual")):
            continue
        ts_raw = inv.get("ts")
        if not isinstance(ts_raw, str):
            skipped += 1
            continue
        try:
            ts = _dt.date.fromisoformat(ts_raw)
        except ValueError:
            skipped += 1
            continue
        if cutoff <= ts <= ref:
            counted += 1
    triggered = counted >= threshold
    reason = (
        f"manual invocations in last {window_days}d = {counted} "
        f"(threshold={threshold}, today={ref.isoformat()}, "
        f"cutoff={cutoff.isoformat()}); "
        f"{'fires' if triggered else 'below threshold'}"
    )
    return _trigger_result(
        TRIGGER_IDS[5],
        triggered,
        reason,
        evidence={
            "threshold": threshold,
            "window_days": window_days,
            "today": ref.isoformat(),
            "cutoff": cutoff.isoformat(),
            "n_invocations_total": len(invocations),
            "n_manual_in_window": counted,
            "n_skipped": skipped,
            "invocation_log_path": str(invocation_log_path),
        },
    )


# ─────────────── Top-level integration ───────────────


@dataclass
class ReactivationVerdict:
    """Aggregate detector output, JSON-serialisable."""

    triggered_count: int
    triggered_names: List[str]
    per_trigger: Dict[str, Dict[str, Any]]
    decision_action: Optional[str]
    profile_path: str
    half_retire_decision_path: str
    metrics_report_path: str
    script_version: str = SCRIPT_VERSION
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered_count": self.triggered_count,
            "triggered_names": self.triggered_names,
            "per_trigger": self.per_trigger,
            "decision_action": self.decision_action,
            "profile_path": self.profile_path,
            "half_retire_decision_path": self.half_retire_decision_path,
            "metrics_report_path": self.metrics_report_path,
            "script_version": self.script_version,
            "notes": list(self.notes),
        }


def detect_reactivation(
    basic_ability_profile: Path,
    half_retire_decision: Path,
    metrics_report: Path,
    *,
    new_baseline_path: Optional[Path] = None,
    scenario_catalog_path: Optional[Path] = None,
    wrapper_stability_log_path: Optional[Path] = None,
    invocation_log_path: Optional[Path] = None,
    today: Optional[str] = None,
) -> Dict[str, Any]:
    """Run all 6 §6.4 triggers and return the aggregate verdict.

    The function loads the three artefacts, computes each trigger
    independently (parameterised-off triggers do not fire), and
    returns a JSON-serialisable dict with:

    * ``triggered_count`` — number of fired triggers (0..6).
    * ``triggered_names`` — sorted list of fired trigger IDs.
    * ``per_trigger`` — mapping of every trigger ID (all 6) to its
      :func:`_trigger_result` payload.
    * ``decision_action`` — the ability's current ``decision.action``
      from the half_retire_decision artifact (e.g. ``keep``,
      ``half_retired``, ``retire``).
    * Provenance fields (paths, script version, notes).

    Workspace rule "No Silent Failures": missing input files raise
    ``FileNotFoundError``; malformed YAML raises ``ValueError``; the CLI
    enforces an exit-2 on the unexpected-fire case (a fired trigger on
    a non-half_retired ability).

    Args:
        basic_ability_profile: Path to ``basic_ability_profile.yaml``.
        half_retire_decision: Path to ``half_retire_decision.yaml``.
        metrics_report: Path to ``metrics_report.yaml``.
        new_baseline_path: Optional path for trigger 1.
        scenario_catalog_path: Optional path for trigger 2.
        wrapper_stability_log_path: Optional path for trigger 5.
        invocation_log_path: Optional path for trigger 6.
        today: Optional ISO date for trigger 6 deterministic testing.

    Returns:
        Aggregate verdict dict (see above).
    """

    profile = _load_yaml(Path(basic_ability_profile))
    if not isinstance(profile, dict):
        raise ValueError(f"profile YAML must be a mapping: {basic_ability_profile}")
    decision = _load_yaml(Path(half_retire_decision))
    if not isinstance(decision, dict):
        raise ValueError(
            f"half_retire_decision YAML must be a mapping: {half_retire_decision}"
        )
    metrics = _load_yaml(Path(metrics_report))
    if not isinstance(metrics, dict):
        raise ValueError(f"metrics_report YAML must be a mapping: {metrics_report}")

    ba = profile.get("basic_ability", {})
    if not isinstance(ba, dict):
        ba = {}
    decision_action_str = decision.get("decision")
    if not isinstance(decision_action_str, str):
        # Fallback: half_retire_decision may carry decision under
        # basic_ability.decision.action (cross-artefact contract).
        ba_dec = ba.get("decision", {}) if isinstance(ba.get("decision"), dict) else {}
        decision_action_str = ba_dec.get("action") if isinstance(ba_dec, dict) else None
    if not isinstance(decision_action_str, str):
        decision_action_str = None

    current_router_floor = ba.get("router_floor")
    prior_router_floor = decision.get("provenance", {}).get("prior_router_floor") if isinstance(decision.get("provenance"), dict) else None
    if prior_router_floor is None:
        # Convention: when no prior is recorded, treat current as prior
        # so trigger 3 cannot fire on the first round.
        prior_router_floor = current_router_floor

    value_vector = decision.get("value_vector", {}) if isinstance(decision.get("value_vector"), dict) else {}
    prior_value_vector = (
        decision.get("prior_value_vector", {})
        if isinstance(decision.get("prior_value_vector"), dict)
        else {}
    )
    if not prior_value_vector:
        # Convention mirror: when no prior value vector recorded, treat
        # current as prior so trigger 4 cannot fire on the first round.
        prior_value_vector = dict(value_vector)

    per_trigger: Dict[str, Dict[str, Any]] = {}
    per_trigger[TRIGGER_IDS[0]] = trigger_new_model_task_delta(
        profile, metrics, new_baseline_path=new_baseline_path,
    )
    per_trigger[TRIGGER_IDS[1]] = trigger_new_scenario_or_domain_match(
        profile, scenario_catalog_path=scenario_catalog_path,
    )
    per_trigger[TRIGGER_IDS[2]] = trigger_router_floor_drop(
        current_router_floor, prior_router_floor,
    )
    per_trigger[TRIGGER_IDS[3]] = trigger_efficiency_axis_significant(
        value_vector, prior_value_vector,
    )
    per_trigger[TRIGGER_IDS[4]] = trigger_upstream_api_change(
        wrapper_stability_log_path=wrapper_stability_log_path,
    )
    per_trigger[TRIGGER_IDS[5]] = trigger_manual_invocation_rebound(
        invocation_log_path=invocation_log_path,
        today=today,
    )

    triggered_names = sorted(
        name for name, payload in per_trigger.items() if payload.get("triggered")
    )

    notes: List[str] = []
    if decision_action_str == "keep" and triggered_names:
        notes.append(
            f"unexpected-fire on keep ability: {triggered_names!r} — investigate"
        )
    if decision_action_str == "half_retired" and not triggered_names:
        notes.append(
            "ability is half_retired but no §6.4 trigger fires — keep half_retired"
        )

    verdict = ReactivationVerdict(
        triggered_count=len(triggered_names),
        triggered_names=triggered_names,
        per_trigger=per_trigger,
        decision_action=decision_action_str,
        profile_path=str(basic_ability_profile),
        half_retire_decision_path=str(half_retire_decision),
        metrics_report_path=str(metrics_report),
        notes=notes,
    )
    return verdict.to_dict()


# ─────────────── CLI ───────────────


def _resolve_sibling(profile_path: Path, name: str) -> Path:
    """Resolve a sibling artefact path next to ``profile_path``.

    Used by the ``--check`` shortcut to locate
    ``half_retire_decision.yaml`` and ``metrics_report.yaml`` in the
    same round directory as the supplied profile.
    """

    return profile_path.parent / name


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Spec §6.4 reactivation-trigger detector for a Si-Chip "
            "BasicAbility. Loads basic_ability_profile.yaml + sibling "
            "half_retire_decision.yaml + metrics_report.yaml; reports "
            "which of the 6 triggers fire."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        type=Path,
        default=None,
        help=(
            "Shortcut: pass the basic_ability_profile.yaml path; sibling "
            "half_retire_decision.yaml + metrics_report.yaml are "
            "auto-located in the same directory."
        ),
    )
    group.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="basic_ability_profile.yaml path (use with --decision and --metrics).",
    )
    parser.add_argument("--decision", type=Path, default=None, help="half_retire_decision.yaml path")
    parser.add_argument("--metrics", type=Path, default=None, help="metrics_report.yaml path")
    parser.add_argument(
        "--new-baseline",
        type=Path,
        default=None,
        help="Optional new no-ability baseline JSON for trigger 1.",
    )
    parser.add_argument(
        "--scenario-catalog",
        type=Path,
        default=None,
        help="Optional scenario catalog JSON for trigger 2.",
    )
    parser.add_argument(
        "--wrapper-stability-log",
        type=Path,
        default=None,
        help="Optional wrapper-stability log JSON for trigger 5.",
    )
    parser.add_argument(
        "--invocation-log",
        type=Path,
        default=None,
        help="Optional invocation log JSON for trigger 6.",
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override today (ISO date) for trigger 6 determinism.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a single-line JSON verdict on stdout.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set log level to INFO.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.check is not None:
        profile_path = args.check.resolve()
        decision_path = _resolve_sibling(profile_path, "half_retire_decision.yaml")
        metrics_path = _resolve_sibling(profile_path, "metrics_report.yaml")
    else:
        if args.decision is None or args.metrics is None:
            parser.error("--profile requires both --decision and --metrics")
        profile_path = args.profile.resolve()
        decision_path = args.decision.resolve()
        metrics_path = args.metrics.resolve()

    verdict = detect_reactivation(
        profile_path,
        decision_path,
        metrics_path,
        new_baseline_path=args.new_baseline,
        scenario_catalog_path=args.scenario_catalog,
        wrapper_stability_log_path=args.wrapper_stability_log,
        invocation_log_path=args.invocation_log,
        today=args.today,
    )

    if args.json:
        print(json.dumps(verdict, ensure_ascii=False))
    else:
        print(f"decision_action     = {verdict['decision_action']}")
        print(f"triggered_count     = {verdict['triggered_count']}")
        print(f"triggered_names     = {verdict['triggered_names']}")
        for name, payload in verdict["per_trigger"].items():
            mark = "FIRE" if payload["triggered"] else "    "
            print(f"  [{mark}] {name}: {payload['reason']}")
        for note in verdict.get("notes", []):
            print(f"NOTE: {note}")

    triggered_count = verdict["triggered_count"]
    decision_action = verdict["decision_action"]
    if triggered_count == 0:
        # Clean keep / clean half_retired without trigger — no wake-up.
        return 0
    if decision_action == "half_retired":
        # Expected wake-up flag — exit 0 (caller flips ability back to evaluated).
        return 0
    # Unexpected fire on a non-half_retired ability — investigate.
    LOGGER.warning(
        "unexpected reactivation fire on decision_action=%r "
        "(triggered=%s); exit 2",
        decision_action,
        verdict["triggered_names"],
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.reactivation_detector").error("fatal: %s", exc)
        raise
