#!/usr/bin/env python3
"""Si-Chip method-tag validator (spec v0.4.0-rc1 §23.1).

Validates ``<metric>_method`` companion-field values in
``metrics_report.yaml`` against the controlled vocabulary declared in
``templates/method_taxonomy.template.yaml`` (NEW v0.4.0).

Public API::

    from tools.method_tag_validator import (
        load_method_taxonomy,
        validate_metric_method_tags,
        get_allowed_methods_for,
    )

    taxonomy = load_method_taxonomy()
    errors, warnings = validate_metric_method_tags(report, taxonomy)

CLI::

    python tools/method_tag_validator.py \\
        --report <metrics_report.yaml> \\
        [--taxonomy <path>] \\
        [--json]

Exit codes:
  * 0 — all method tags valid (or no tags found).
  * 1 — one or more method tags invalid.
  * 2 — taxonomy / report read error.

Workspace rule "No Silent Failures": unknown method values, missing
tags when a metric is present, and malformed YAML all raise explicit
errors — we never silently pass a questionable report.

This module is part of the Stage 4 Wave 1b tooling that supports the
spec v0.4.0-rc1 ship gate (§13.6.4 BLOCKER set). The BLOCKER-level
invariants (TOKEN_TIER_DECLARED_WHEN_REPORTED etc.) live in
``tools/spec_validator.py``; this module is a focused helper for
per-metric method-tag auditing used by evaluation harnesses and CI.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.method_tag_validator")

SCRIPT_VERSION = "0.1.0"

# Canonical default path for the taxonomy template.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
DEFAULT_TAXONOMY_PATH = _REPO_ROOT / "templates" / "method_taxonomy.template.yaml"

# Same suffix list as tools.spec_validator.COMPANION_SUFFIXES (kept
# here as the authoritative source for method-tag auditing; the
# spec_validator re-uses this shape in its own BLOCKER). The ``_method``
# suffix is the primary target of this validator; the other suffixes
# (``_ci_low`` / ``_ci_high`` / ``_language_breakdown`` / ``_state``)
# are recognized by ``validate_metric_method_tags`` as valid companion
# fields so they are not mis-flagged as spurious keys.
COMPANION_SUFFIXES: Tuple[str, ...] = (
    "_method",
    "_ci_low",
    "_ci_high",
    "_language_breakdown",
    "_state",
    "_provenance",
    "_sampled_at",
    "_sample_size_per_cell",
)

# Method-value groups in method_taxonomy.template.yaml. Each key names
# a group; values list allowed methods. The taxonomy template groups
# related metrics (e.g. token_metrics) rather than one-entry-per-metric
# to keep the YAML compact; ``get_allowed_methods_for`` resolves the
# per-metric lookup.
#
# This mapping tells the resolver which metrics belong to which
# taxonomy group. Keys are metric prefixes; values are taxonomy group
# names (as declared in method_taxonomy.template.yaml.method_vocabulary).
METRIC_TO_TAXONOMY_GROUP: Dict[str, str] = {
    # Token-related metrics (D2 C1/C2/C4 + §18 C7/C8/C9).
    "C1_metadata_tokens": "token_metrics",
    "C2_body_tokens": "token_metrics",
    "C3_resolved_tokens": "token_metrics",
    "C4_per_invocation_footprint": "token_metrics",
    "C7_eager_per_session": "token_metrics",
    "C8_oncall_per_trigger": "token_metrics",
    "C9_lazy_avg_per_load": "token_metrics",
    # Core-goal (§14 C0).
    "C0_core_goal_pass_rate": "core_goal_pass_rate",
    # Quality metrics share the same vocabulary as C0 here.
    "T1_pass_rate": "core_goal_pass_rate",
    "T2_pass_k": "core_goal_pass_rate",
    "T3_baseline_delta": "core_goal_pass_rate",
    # Cross-model D4 G1 (provenance first-class).
    "G1_cross_model_pass_matrix": "g1_cross_model_pass_matrix",
    # Latency D3.
    "L1_wall_clock_p50": "latency_metrics",
    "L2_wall_clock_p95": "latency_metrics",
    # Trigger F1 (R3 + split sub-axes).
    "R3_trigger_F1": "trigger_f1",
    "R3_eager_only": "trigger_f1",
    "R3_post_trigger": "trigger_f1",
}


# --- dataclasses ------------------------------------------------------


@dataclass
class ValidationOutcome:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_metrics: List[str] = field(default_factory=list)
    unknown_methods: List[Dict[str, str]] = field(default_factory=list)
    missing_method_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checked_metrics": list(self.checked_metrics),
            "unknown_methods": list(self.unknown_methods),
            "missing_method_tags": list(self.missing_method_tags),
        }


# --- public API -------------------------------------------------------


def load_method_taxonomy(
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load and return ``method_taxonomy.template.yaml`` as a dict.

    Defaults to the canonical path
    ``templates/method_taxonomy.template.yaml``. Raises
    ``FileNotFoundError`` when the taxonomy is missing and
    ``RuntimeError`` when the YAML is malformed (workspace rule "No
    Silent Failures").
    """

    if path is None:
        path = DEFAULT_TAXONOMY_PATH
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"method taxonomy not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"method taxonomy {path}: YAML parse error: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(
            f"method taxonomy {path}: top level must be a mapping"
        )
    vocab = data.get("method_vocabulary")
    if not isinstance(vocab, dict):
        raise RuntimeError(
            f"method taxonomy {path}: missing `method_vocabulary` block"
        )
    return data


def get_allowed_methods_for(
    metric_name: str, taxonomy: Dict[str, Any]
) -> List[str]:
    """Return the list of allowed ``_method`` values for a metric.

    The lookup resolves ``metric_name`` via the module-level
    ``METRIC_TO_TAXONOMY_GROUP`` mapping and then reads
    ``taxonomy.method_vocabulary[<group>].allowed``.

    Returns an empty list when the metric is unknown to the taxonomy
    (callers interpret an empty list as "no constraint — skip").
    """

    group = METRIC_TO_TAXONOMY_GROUP.get(metric_name)
    if group is None:
        return []
    vocab = taxonomy.get("method_vocabulary") or {}
    block = vocab.get(group)
    if not isinstance(block, dict):
        return []
    allowed = block.get("allowed")
    if not isinstance(allowed, list):
        return []
    return [str(x) for x in allowed]


def _collect_metrics_keys(metrics_report: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield ``(dimension_name, dimension_body)`` for the metrics block.

    Returns an empty iterator when the report is shape-invalid (no
    ``metrics`` mapping). Also yields synthetic ``("token_tier", body)``
    when the top-level ``token_tier`` block exists so §18.1 companion
    tags are validated alongside R6 metrics.
    """

    metrics = metrics_report.get("metrics")
    if isinstance(metrics, dict):
        for dim, body in metrics.items():
            if isinstance(body, dict):
                yield dim, body
    # Also treat top-level token_tier as a dimension (C7/C8/C9 live here).
    tier = metrics_report.get("token_tier")
    if isinstance(tier, dict):
        yield "token_tier", tier
    # And core_goal top-level (C0).
    cg = metrics_report.get("core_goal")
    if isinstance(cg, dict):
        yield "core_goal", cg


def _is_companion_key(key: str) -> bool:
    """True when ``key`` ends in a declared companion-field suffix."""

    return any(key.endswith(suffix) for suffix in COMPANION_SUFFIXES)


def validate_metric_method_tags(
    metrics_report: Dict[str, Any],
    taxonomy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate every ``<metric>_method`` tag in a metrics report.

    For each primary metric that appears in the report, this checks:
      1. If a ``<metric>_method`` companion is present, its value MUST
         be a member of the taxonomy's allowed list for that metric.
      2. If the metric is present (non-null OR null placeholder) AND
         the taxonomy declares ``char_heuristic_requires_ci: true``
         for its group, then ``_ci_low`` / ``_ci_high`` companion
         fields MUST also be present when ``_method == char_heuristic``.

    Parameters
    ----------
    metrics_report:
        The full metrics_report dict (top-level shape as emitted by
        ``eval_skill.run_evaluation``).
    taxonomy:
        Optional pre-loaded taxonomy dict. When omitted, loads from
        the default path.

    Returns
    -------
    dict
        ``{errors, warnings, checked_metrics, unknown_methods,
           missing_method_tags}`` (see ``ValidationOutcome``).
    """

    outcome = ValidationOutcome()
    if taxonomy is None:
        taxonomy = load_method_taxonomy()

    for dim, body in _collect_metrics_keys(metrics_report):
        # Identify primary keys (non-companion) in this dimension.
        primary_keys = [k for k in body.keys() if not _is_companion_key(k)]
        for pkey in primary_keys:
            outcome.checked_metrics.append(f"{dim}.{pkey}")
            primary_val = body[pkey]
            method_key = f"{pkey}_method"
            method_val = body.get(method_key)
            allowed = get_allowed_methods_for(pkey, taxonomy)
            if not allowed:
                # Metric not in taxonomy → skip (neither tag absence nor
                # non-standard value is an error). Callers that want
                # stricter enforcement can add the metric to
                # METRIC_TO_TAXONOMY_GROUP.
                continue
            # Rule 1: if method_key is present, value must be allowed.
            if method_key in body:
                # Edge case (spec §23.1 implicit): when both primary and
                # method are None, accept as "not yet measured"
                # placeholder — neither error nor warning.
                if method_val is None and primary_val is None:
                    continue
                if method_val not in allowed:
                    outcome.errors.append(
                        f"{dim}.{method_key}={method_val!r} not in "
                        f"allowed methods {allowed}"
                    )
                    outcome.unknown_methods.append(
                        {
                            "path": f"{dim}.{method_key}",
                            "value": str(method_val),
                            "allowed": list(allowed),
                        }
                    )
                continue
            # Rule 2: primary value is non-null → method tag is REQUIRED.
            if primary_val is not None:
                # Exception: null metric + null method_key is OK
                # (metric not yet measured).
                outcome.errors.append(
                    f"{dim}.{pkey}={primary_val!r} present but "
                    f"{method_key} companion field missing "
                    f"(spec §23.1 requires explicit method tag)"
                )
                outcome.missing_method_tags.append(f"{dim}.{method_key}")
            else:
                # Rule 2b: null metric + null method → WARNING only.
                outcome.warnings.append(
                    f"{dim}.{pkey} is null and {method_key} companion "
                    "is absent; acceptable but consider tagging as "
                    "tiktoken/real_llm explicitly when the value is "
                    "populated in a future round"
                )

        # Rule 3: for char_heuristic token metrics, _ci_low/_ci_high
        # must be present alongside (spec §23.2 + method_taxonomy
        # `confidence_band` block). Detection heuristic:
        #   (a) taxonomy block has explicit ``char_heuristic_requires_ci: true``
        #       (machine-checkable flag), OR
        #   (b) the metric maps to the "token_metrics" taxonomy group AND
        #       the taxonomy's top-level ``confidence_band`` block mentions
        #       ``_ci_low`` / ``_ci_high`` (describes the industrial
        #       default — every token_metrics char_heuristic MUST emit CI).
        confidence_band = taxonomy.get("confidence_band") or {}
        confidence_band_says_emit_ci = False
        if isinstance(confidence_band, dict):
            desc = str(confidence_band.get("description", ""))
            confidence_band_says_emit_ci = (
                "_ci_low" in desc or "_ci_high" in desc
            )
        for pkey in primary_keys:
            method_val = body.get(f"{pkey}_method")
            if method_val != "char_heuristic":
                continue
            group = METRIC_TO_TAXONOMY_GROUP.get(pkey)
            if group is None:
                continue
            vocab = taxonomy.get("method_vocabulary") or {}
            block = vocab.get(group) or {}
            explicit_requires_ci = bool(
                block.get("char_heuristic_requires_ci", False)
            )
            inferred_requires_ci = (
                group == "token_metrics" and confidence_band_says_emit_ci
            )
            if not (explicit_requires_ci or inferred_requires_ci):
                continue
            # Check for _ci_low and _ci_high.
            for suffix in ("_ci_low", "_ci_high"):
                ci_key = f"{pkey}{suffix}"
                if ci_key not in body:
                    outcome.errors.append(
                        f"{dim}.{pkey}_method=char_heuristic but "
                        f"{ci_key} companion field missing "
                        "(spec §23.2: char_heuristic token metrics "
                        "MUST emit _ci_low and _ci_high)"
                    )

    return outcome.to_dict()


# --- CLI --------------------------------------------------------------


def _load_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"metrics_report not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"metrics_report {path}: YAML parse error: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(
            f"metrics_report {path}: top level must be a mapping"
        )
    return data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="method_tag_validator",
        description=(
            "Validate <metric>_method companion-field values in a "
            "metrics_report.yaml against templates/method_taxonomy.template.yaml "
            "(Si-Chip spec v0.4.0-rc1 §23.1). Exits 0 on all valid, "
            "1 on any error, 2 on taxonomy / report read failure."
        ),
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to metrics_report.yaml to validate.",
    )
    parser.add_argument(
        "--taxonomy",
        default=str(DEFAULT_TAXONOMY_PATH),
        help=(
            f"Path to method taxonomy YAML (default: {DEFAULT_TAXONOMY_PATH})."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON validation report on stdout.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set log level to INFO.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        taxonomy = load_method_taxonomy(Path(args.taxonomy))
    except (FileNotFoundError, RuntimeError) as exc:
        print(json.dumps({"error": f"taxonomy: {exc}"}))
        return 2
    try:
        report = _load_report(Path(args.report))
    except (FileNotFoundError, RuntimeError) as exc:
        print(json.dumps({"error": f"report: {exc}"}))
        return 2

    result = validate_metric_method_tags(report, taxonomy)

    if args.json:
        print(json.dumps(result))
    else:
        print(
            f"method_tag_validator: checked {len(result['checked_metrics'])} "
            f"metrics; {len(result['errors'])} error(s), "
            f"{len(result['warnings'])} warning(s)"
        )
        for err in result["errors"]:
            print(f"  [ERROR] {err}")
        for warn in result["warnings"]:
            print(f"  [WARN]  {warn}")

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.method_tag_validator").error("fatal: %s", exc)
        raise
