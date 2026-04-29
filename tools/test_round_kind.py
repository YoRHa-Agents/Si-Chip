#!/usr/bin/env python3
"""Unit tests for ``tools/round_kind.py``.

Coverage targets spec v0.3.0-rc1 §15.1.1 enum membership, §15.2
iteration_delta clauses, §15.4 promotion-counter eligibility, and §15.3
universal C0 invariant.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.round_kind import (  # noqa: E402
    ITERATION_DELTA_CLAUSES,
    PROMOTION_ELIGIBLE,
    REQUIRED_C0_VALUE,
    ROUND_KINDS,
    counts_toward_consecutive_promotion,
    describe_all,
    iteration_delta_clause_for,
    main,
    validate_round_kind,
)

ROUND_KIND_SCRIPT = REPO_ROOT / "tools" / "round_kind.py"


def test_round_kinds_set_size_4():
    assert isinstance(ROUND_KINDS, frozenset)
    assert len(ROUND_KINDS) == 4
    assert ROUND_KINDS == {
        "code_change",
        "measurement_only",
        "ship_prep",
        "maintenance",
    }


def test_validate_valid():
    for kind in ("code_change", "measurement_only", "ship_prep", "maintenance"):
        assert validate_round_kind(kind) is True, f"{kind} should validate"


def test_validate_invalid():
    for kind in ("shipped", "test", "", None, "CODE_CHANGE", "code-change"):
        assert validate_round_kind(kind) is False, f"{kind!r} should NOT validate"


def test_iteration_delta_clause():
    assert iteration_delta_clause_for("code_change") == "strict"
    assert iteration_delta_clause_for("measurement_only") == "monotonicity_only"
    assert iteration_delta_clause_for("ship_prep") == "waived"
    assert iteration_delta_clause_for("maintenance") == "waived"

    with pytest.raises(ValueError):
        iteration_delta_clause_for("bogus")


def test_counts_toward_consecutive_promotion():
    assert counts_toward_consecutive_promotion("code_change") is True
    assert counts_toward_consecutive_promotion("measurement_only") is True
    assert counts_toward_consecutive_promotion("ship_prep") is False
    assert counts_toward_consecutive_promotion("maintenance") is False

    with pytest.raises(ValueError):
        counts_toward_consecutive_promotion("bogus")


def test_required_c0_value_universal():
    assert REQUIRED_C0_VALUE == 1.0


def test_iteration_delta_clauses_dict_has_all_kinds():
    assert set(ITERATION_DELTA_CLAUSES.keys()) == ROUND_KINDS
    for label in ITERATION_DELTA_CLAUSES.values():
        assert label in {"strict", "monotonicity_only", "waived"}


def test_promotion_eligible_dict_has_all_kinds():
    assert set(PROMOTION_ELIGIBLE.keys()) == ROUND_KINDS
    assert all(isinstance(v, bool) for v in PROMOTION_ELIGIBLE.values())


def test_describe_all_shape():
    payload = describe_all()
    assert sorted(payload["round_kinds"]) == sorted(ROUND_KINDS)
    assert payload["iteration_delta_clauses"] == ITERATION_DELTA_CLAUSES
    assert payload["promotion_eligible"] == PROMOTION_ELIGIBLE
    assert payload["required_c0_value"] == 1.0
    assert "spec_section" in payload


def test_cli_validate_exit_0_on_valid():
    result = subprocess.run(
        [sys.executable, str(ROUND_KIND_SCRIPT), "validate", "code_change"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_cli_validate_exit_1_on_invalid():
    result = subprocess.run(
        [sys.executable, str(ROUND_KIND_SCRIPT), "validate", "bogus"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1


def test_cli_clause_for():
    result = subprocess.run(
        [sys.executable, str(ROUND_KIND_SCRIPT), "clause-for", "measurement_only"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "monotonicity_only"


def test_cli_json():
    result = subprocess.run(
        [sys.executable, str(ROUND_KIND_SCRIPT), "json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert sorted(payload["round_kinds"]) == sorted(ROUND_KINDS)
    assert payload["required_c0_value"] == 1.0


def test_main_returns_1_on_invalid_validate():
    rc = main(["validate", "bogus"])
    assert rc == 1


def test_main_returns_0_on_valid_validate():
    rc = main(["validate", "code_change"])
    assert rc == 0
