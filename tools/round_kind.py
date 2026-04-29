#!/usr/bin/env python3
"""`round_kind` enum validator for Si-Chip spec v0.3.0-rc1 §15.

Implements the 4-value enum declared at spec v0.3.0-rc1 §15.1.1 and the
per-kind iteration_delta / promotion-counter semantics declared at §15.2
and §15.4. Also surfaces the universal C0 ``MUST = 1.0`` invariant
(§15.3) as ``REQUIRED_C0_VALUE``.

The module is a thin, standalone primitive imported by
``tools/eval_skill.py`` (to populate metrics_report's round_kind field),
by ``tools/spec_validator.py`` (v0.3.0 BLOCKER
``ROUND_KIND_FIELD_PRESENT_AND_VALID``), and by any other tooling that
consumes or emits ``next_action_plan.yaml``.

CLI::

    python tools/round_kind.py validate <kind>
    python tools/round_kind.py clause-for <kind>
    python tools/round_kind.py json

``validate`` exits 0 when ``<kind>`` is a valid member of the enum; 1
otherwise. ``clause-for`` prints the iteration_delta clause label
(``strict`` / ``monotonicity_only`` / ``waived``). ``json`` prints a
single-line JSON payload describing the full enum.

Workspace-rule notes
--------------------
* "No Silent Failures": ``validate_round_kind`` returns a bool (explicit
  error state); the CLI dispatches exceptions to ``sys.exit(1)`` with a
  non-zero exit code and an error log.
* "Mandatory Verification": sibling test ``tools/test_round_kind.py``
  covers ≥ 6 unit tests (enum size, valid / invalid kinds, per-kind
  iteration_delta clause, per-kind promotion eligibility, universal C0
  invariant).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Dict, FrozenSet, List, Optional

LOGGER = logging.getLogger("si_chip.round_kind")

SCRIPT_VERSION = "0.1.0"

ROUND_KINDS: FrozenSet[str] = frozenset(
    {"code_change", "measurement_only", "ship_prep", "maintenance"}
)

ITERATION_DELTA_CLAUSES: Dict[str, str] = {
    "code_change": "strict",
    "measurement_only": "monotonicity_only",
    "ship_prep": "waived",
    "maintenance": "waived",
}

PROMOTION_ELIGIBLE: Dict[str, bool] = {
    "code_change": True,
    "measurement_only": True,
    "ship_prep": False,
    "maintenance": False,
}

REQUIRED_C0_VALUE: float = 1.0


def validate_round_kind(kind: Optional[str]) -> bool:
    """Return ``True`` iff ``kind`` is a valid member of ``ROUND_KINDS``.

    Per spec §15.1.1 the four valid values are ``code_change``,
    ``measurement_only``, ``ship_prep``, ``maintenance``. Empty / None
    / unknown strings all return ``False``.
    """

    if not isinstance(kind, str):
        return False
    return kind in ROUND_KINDS


def iteration_delta_clause_for(kind: str) -> str:
    """Return the per-kind iteration_delta clause label (§15.2).

    Valid labels: ``strict`` (code_change), ``monotonicity_only``
    (measurement_only), ``waived`` (ship_prep / maintenance). Raises
    ``ValueError`` on unknown kind (explicit; no silent fallback).
    """

    if not validate_round_kind(kind):
        raise ValueError(
            f"unknown round_kind {kind!r}; must be one of "
            f"{sorted(ROUND_KINDS)}"
        )
    return ITERATION_DELTA_CLAUSES[kind]


def counts_toward_consecutive_promotion(kind: str) -> bool:
    """Return ``True`` iff this kind counts toward §4.2 consecutive-rounds.

    Per spec §15.4: ``code_change`` and ``measurement_only`` count
    (fresh observations); ``ship_prep`` and ``maintenance`` do not
    (carry-forward / re-verify). Raises ``ValueError`` on unknown kind.
    """

    if not validate_round_kind(kind):
        raise ValueError(
            f"unknown round_kind {kind!r}; must be one of "
            f"{sorted(ROUND_KINDS)}"
        )
    return PROMOTION_ELIGIBLE[kind]


def describe_all() -> Dict[str, object]:
    """Return the full enum as a JSON-serialisable dict for ``--json``.

    Shape::

        {
            "round_kinds": [...4 sorted values...],
            "iteration_delta_clauses": {kind: clause},
            "promotion_eligible": {kind: bool},
            "required_c0_value": 1.0,
            "spec_section": "v0.3.0-rc1 §15",
            "script_version": "0.1.0",
        }
    """

    return {
        "round_kinds": sorted(ROUND_KINDS),
        "iteration_delta_clauses": dict(ITERATION_DELTA_CLAUSES),
        "promotion_eligible": dict(PROMOTION_ELIGIBLE),
        "required_c0_value": REQUIRED_C0_VALUE,
        "spec_section": "v0.3.0-rc1 §15",
        "script_version": SCRIPT_VERSION,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="round_kind",
        description=(
            "Validate Si-Chip spec v0.3.0-rc1 §15 round_kind enum values "
            "and surface per-kind iteration_delta clauses / promotion "
            "eligibility / universal C0 invariant."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser(
        "validate",
        help="Exit 0 if <kind> is a valid round_kind; exit 1 otherwise.",
    )
    p_validate.add_argument("kind", help="round_kind value to validate")

    p_clause = sub.add_parser(
        "clause-for",
        help="Print the iteration_delta clause label for <kind>.",
    )
    p_clause.add_argument("kind", help="round_kind value")

    sub.add_parser(
        "json",
        help="Print the full enum as a single-line JSON payload.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Returns process exit code (0 on success, 1 on validation failure or
    unknown kind).
    """

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        if validate_round_kind(args.kind):
            return 0
        LOGGER.error(
            "invalid round_kind %r; expected one of %s",
            args.kind,
            sorted(ROUND_KINDS),
        )
        print(
            f"INVALID round_kind: {args.kind!r}; expected one of "
            f"{sorted(ROUND_KINDS)}",
            file=sys.stderr,
        )
        return 1

    if args.command == "clause-for":
        try:
            label = iteration_delta_clause_for(args.kind)
        except ValueError as exc:
            LOGGER.error("%s", exc)
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(label)
        return 0

    if args.command == "json":
        payload = describe_all()
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0

    parser.error(f"unknown command {args.command!r}")
    return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    sys.exit(main())
