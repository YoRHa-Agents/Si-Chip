#!/usr/bin/env python3
"""Static BasicAbilityProfile emitter for the Si-Chip ability itself.

Implements spec §2 (Core Object: BasicAbility) and §8.1 step 1 (profile)
of `.local/research/spec_v0.1.0.md`.  The output YAML populates every field
that can be derived without running an evaluation: identity, surface,
packaging, lifecycle, eval_state defaults, decision intent.  Numeric
``metrics.*`` and ``value_vector.*`` axes are emitted as explicit ``null``
per spec §3.2 frozen constraint #2 (28 sub-metric keys + 7 value-vector
axes always present).

Reads ``templates/basic_ability_profile.schema.yaml`` (when present) to
cross-validate the field set; missing template is logged at WARNING and
the script falls back to the built-in structure derived from spec §2.1
so that this S2.W2.B2 wave does not block on the templates wave.

CLI::

    python scripts/profile_static.py --ability si-chip [--out PATH] \
        [--templates-dir templates/] [--repo-root .]

Exits non-zero on any error (workspace rule "No Silent Failures").
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

LOGGER = logging.getLogger("si_chip.profile_static")

SCRIPT_VERSION = "0.1.0"

METRIC_KEYS: Dict[str, List[str]] = {
    "task_quality": [
        "T1_pass_rate",
        "T2_pass_k",
        "T3_baseline_delta",
        "T4_error_recovery_rate",
    ],
    "context_economy": [
        "C1_metadata_tokens",
        "C2_body_tokens",
        "C3_resolved_tokens",
        "C4_per_invocation_footprint",
        "C5_context_rot_risk",
        "C6_scope_overlap_score",
    ],
    "latency_path": [
        "L1_wall_clock_p50",
        "L2_wall_clock_p95",
        "L3_step_count",
        "L4_redundant_call_ratio",
        "L5_detour_index",
        "L6_replanning_rate",
        "L7_think_act_split",
    ],
    "generalizability": [
        "G1_cross_model_pass_matrix",
        "G2_cross_domain_transfer_pass",
        "G3_OOD_robustness",
        "G4_model_version_stability",
    ],
    "usage_cost": [
        "U1_description_readability",
        "U2_first_time_success_rate",
        "U3_setup_steps_count",
        "U4_time_to_first_success",
    ],
    "routing_cost": [
        "R1_trigger_precision",
        "R2_trigger_recall",
        "R3_trigger_F1",
        "R4_near_miss_FP_rate",
        "R5_router_floor",
        "R6_routing_latency_p95",
        "R7_routing_token_overhead",
        "R8_description_competition_index",
    ],
    "governance_risk": [
        "V1_permission_scope",
        "V2_credential_surface",
        "V3_drift_signal",
        "V4_staleness_days",
    ],
}

VALUE_VECTOR_AXES: List[str] = [
    "task_delta",
    "token_delta",
    "latency_delta",
    "context_delta",
    "path_efficiency_delta",
    "routing_delta",
    "governance_risk_delta",
]


def _today_utc() -> _dt.date:
    """Return today's UTC date.

    >>> isinstance(_today_utc(), _dt.date)
    True
    """

    return _dt.datetime.now(_dt.timezone.utc).date()


def _empty_metrics() -> Dict[str, Dict[str, Any]]:
    """Return a metrics block with every sub-metric key present and ``null``.

    >>> m = _empty_metrics()
    >>> sorted(m.keys()) == sorted(METRIC_KEYS.keys())
    True
    >>> all(v is None for sub in m.values() for v in sub.values())
    True
    """

    return {dim: {k: None for k in keys} for dim, keys in METRIC_KEYS.items()}


def _empty_value_vector() -> Dict[str, Any]:
    return {axis: None for axis in VALUE_VECTOR_AXES}


def build_profile(ability: str) -> Dict[str, Any]:
    """Construct the static BasicAbilityProfile for ``ability``.

    Currently only the ``si-chip`` ability has a hard-coded surface; other
    ability ids produce a generic skeleton with ``current_surface.path``
    pointing at ``.agents/skills/<id>/`` per spec §7.1.

    >>> p = build_profile("si-chip")
    >>> p["basic_ability"]["id"]
    'si-chip'
    >>> p["basic_ability"]["lifecycle"]["stage"]
    'exploratory'
    >>> p["basic_ability"]["decision"]["action"]
    'create_eval_set'
    """

    today = _today_utc()
    next_review = today + _dt.timedelta(days=30)

    if ability == "si-chip":
        intent = (
            "Persistent BasicAbility optimization factory: capture, profile, "
            "evaluate, diagnose, improve, router-test, half-retire-review, "
            "iterate, package/register the Si-Chip skill against itself."
        )
    else:
        intent = f"BasicAbility '{ability}' — intent TBD pending evaluation."

    profile: Dict[str, Any] = {
        "basic_ability": {
            "id": ability,
            "intent": intent,
            "current_surface": {
                "type": "mixed",
                "path": f".agents/skills/{ability}/",
                "shape_hint": "markdown_first",
            },
            "packaging": {
                "install_targets": {
                    "cursor": True,
                    "claude_code": True,
                    "codex": False,
                },
                "source_of_truth": f".agents/skills/{ability}/",
                "generated_targets": [
                    f".cursor/skills/{ability}/",
                    f".claude/skills/{ability}/",
                ],
            },
            "lifecycle": {
                "stage": "exploratory",
                "last_reviewed_at": today.isoformat(),
                "next_review_at": next_review.isoformat(),
            },
            "eval_state": {
                "has_eval_set": False,
                "has_no_ability_baseline": False,
                "has_self_eval": False,
                "has_router_test": False,
                "has_iteration_delta": False,
            },
            "metrics": _empty_metrics(),
            "value_vector": _empty_value_vector(),
            "router_floor": None,
            "decision": {
                "action": "create_eval_set",
                "rationale": "static profile, no metrics yet",
                "risk_flags": [],
            },
        },
        "provenance": {
            "generator": "profile_static.py",
            "script_version": SCRIPT_VERSION,
            "spec_version": "v0.1.0",
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        },
    }
    return profile


def _load_schema(templates_dir: Path) -> Optional[Dict[str, Any]]:
    schema_path = templates_dir / "basic_ability_profile.schema.yaml"
    if not schema_path.exists():
        LOGGER.warning(
            "schema file not found at %s; using built-in spec §2.1 structure",
            schema_path,
        )
        return None
    try:
        with schema_path.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
    except yaml.YAMLError as exc:
        raise RuntimeError(f"failed to parse {schema_path}: {exc}") from exc
    LOGGER.info("loaded schema from %s", schema_path)
    return data


def _cross_check(profile: Dict[str, Any], schema: Optional[Dict[str, Any]]) -> None:
    """Best-effort cross-check the profile against a loaded schema.

    Emits a WARNING per missing/extra top-level key under
    ``basic_ability``; does not raise — the schema may not yet be frozen
    (parallel S2 wave).
    """

    if not schema:
        return
    expected = schema.get("basic_ability") if isinstance(schema, dict) else None
    if not isinstance(expected, dict):
        LOGGER.warning("schema does not declare a 'basic_ability' mapping; skipping cross-check")
        return
    actual_keys = set(profile["basic_ability"].keys())
    expected_keys = set(expected.keys())
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if missing:
        LOGGER.warning("profile missing schema-declared keys: %s", sorted(missing))
    if extra:
        LOGGER.warning("profile has extra keys not in schema: %s", sorted(extra))


def _default_out_path(repo_root: Path) -> Path:
    today = _today_utc().isoformat()
    return repo_root / ".local" / "dogfood" / today / "round_static" / "basic_ability_profile.yaml"


def write_profile(profile: Dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fp:
        yaml.safe_dump(profile, fp, sort_keys=False, allow_unicode=True)
    LOGGER.info("wrote profile to %s", out_path)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a static BasicAbilityProfile YAML for a Si-Chip ability.",
    )
    parser.add_argument("--ability", required=True, help="Ability id (e.g. si-chip).")
    parser.add_argument("--out", default=None, help="Output YAML path (default under .local/dogfood/<date>/round_static/).")
    parser.add_argument(
        "--templates-dir",
        default="templates",
        help="Directory containing basic_ability_profile.schema.yaml (default: templates/).",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument("--verbose", action="store_true", help="Set log level to INFO.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    repo_root = Path(args.repo_root).resolve()
    templates_dir = (repo_root / args.templates_dir).resolve() if not os.path.isabs(args.templates_dir) else Path(args.templates_dir)

    schema = _load_schema(templates_dir)
    profile = build_profile(args.ability)
    _cross_check(profile, schema)

    out_path = Path(args.out).resolve() if args.out else _default_out_path(repo_root)
    write_profile(profile, out_path)
    print(out_path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.profile_static").error("fatal: %s", exc)
        sys.exit(1)
