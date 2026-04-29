#!/usr/bin/env python3
"""Unit tests for ``tools/eval_skill.py``.

Covers R6 7×37 invariant, ROUND_KINDS enum size, core_goal_test_pack
runner (pass / fail), metrics_report completeness, and the §15.3
universal C0 rollback rule.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.eval_skill import (  # noqa: E402
    R6_KEYS,
    EvalSkillConfig,
    build_core_goal_check,
    build_r6_placeholder,
    main,
    run_core_goal_test_pack,
    run_evaluation,
)
from tools.round_kind import REQUIRED_C0_VALUE, ROUND_KINDS  # noqa: E402

EVAL_SKILL_SCRIPT = REPO_ROOT / "tools" / "eval_skill.py"


# --- R6 7×37 invariants ------------------------------------------------

def test_r6_keys_count_37():
    total = sum(len(v) for v in R6_KEYS.values())
    assert total == 37


def test_r6_keys_dimension_counts():
    assert len(R6_KEYS["task_quality"]) == 4
    assert len(R6_KEYS["context_economy"]) == 6
    assert len(R6_KEYS["latency_path"]) == 7
    assert len(R6_KEYS["generalizability"]) == 4
    assert len(R6_KEYS["usage_cost"]) == 4
    assert len(R6_KEYS["routing_cost"]) == 8
    assert len(R6_KEYS["governance_risk"]) == 4


def test_r6_keys_prefixes_match_dimension():
    # Every key starts with its dimension's expected prefix letter.
    prefix_of = {
        "task_quality": "T",
        "context_economy": "C",
        "latency_path": "L",
        "generalizability": "G",
        "usage_cost": "U",
        "routing_cost": "R",
        "governance_risk": "V",
    }
    for dim, keys in R6_KEYS.items():
        for key in keys:
            assert key[0] == prefix_of[dim], (
                f"{key} in {dim} must start with {prefix_of[dim]}"
            )


def test_r6_placeholder_has_all_37_keys():
    placeholder = build_r6_placeholder()
    total = sum(len(v) for v in placeholder.values())
    assert total == 37
    for dim, keys in R6_KEYS.items():
        for key in keys:
            assert key in placeholder[dim]
            assert placeholder[dim][key] is None


# --- ROUND_KINDS -------------------------------------------------------

def test_round_kinds_4():
    assert len(ROUND_KINDS) == 4
    assert ROUND_KINDS == {
        "code_change",
        "measurement_only",
        "ship_prep",
        "maintenance",
    }


# --- core_goal_test_pack runner ----------------------------------------

def _write_pack(path: Path, cases):
    pack = {"cases": cases}
    path.write_text(yaml.safe_dump(pack), encoding="utf-8")


def test_run_core_goal_test_pack_pass_all(tmp_path):
    # 3 cases, each runs `true` → all pass → pass_rate = 1.0
    pack_path = tmp_path / "pack.yaml"
    _write_pack(
        pack_path,
        [
            {"id": "c1", "prompt": "p1", "command": "true"},
            {"id": "c2", "prompt": "p2", "command": "true"},
            {"id": "c3", "prompt": "p3", "command": "true"},
        ],
    )
    result = run_core_goal_test_pack(
        pack_path, default_runner_cmd="true", cwd=tmp_path
    )
    assert result["cases_total"] == 3
    assert result["cases_passed"] == 3
    assert result["pass_rate"] == 1.0
    assert all(c["passed"] for c in result["per_case"])


def test_run_core_goal_test_pack_one_fail(tmp_path):
    # 3 cases; 2 pass (true), 1 fail (false). pass_rate = 2/3 ≈ 0.667
    pack_path = tmp_path / "pack.yaml"
    _write_pack(
        pack_path,
        [
            {"id": "c1", "prompt": "p1", "command": "true"},
            {"id": "c2", "prompt": "p2", "command": "false"},
            {"id": "c3", "prompt": "p3", "command": "true"},
        ],
    )
    result = run_core_goal_test_pack(
        pack_path, default_runner_cmd="true", cwd=tmp_path
    )
    assert result["cases_total"] == 3
    assert result["cases_passed"] == 2
    assert abs(result["pass_rate"] - (2 / 3)) < 1e-4
    failed = [c for c in result["per_case"] if not c["passed"]]
    assert len(failed) == 1
    assert failed[0]["case_id"] == "c2"


def test_run_core_goal_test_pack_uses_default_runner(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(
        pack_path,
        [
            {"id": "c1", "prompt": "p1"},
            {"id": "c2", "prompt": "p2"},
        ],
    )
    result = run_core_goal_test_pack(
        pack_path, default_runner_cmd="true", cwd=tmp_path
    )
    assert result["cases_passed"] == 2
    assert result["pass_rate"] == 1.0


def test_run_core_goal_test_pack_missing_pack(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_core_goal_test_pack(
            tmp_path / "missing.yaml",
            default_runner_cmd="true",
            cwd=tmp_path,
        )


# --- §15.3 universal C0 invariant tests -------------------------------

def test_round_kind_blocker_on_c0_lt_1_and_code_change():
    check = build_core_goal_check(
        c0_pass_rate=0.667,
        cases_passed=2,
        cases_total=3,
        prior_c0_pass_rate=1.0,
        round_kind="code_change",
        failed_case_ids=["c2"],
    )
    assert check["rollback_required"] is True
    assert check["regression_detected"] is True
    assert check["verdict"]["core_goal_pass"] is False


def test_round_kind_blocker_on_c0_lt_1_and_maintenance():
    # Per spec §15.3: "C0 MUST = 1.0" is universal across ALL round_kinds.
    # Even maintenance rounds must set rollback_required=True when C0<1.0.
    check = build_core_goal_check(
        c0_pass_rate=0.5,
        cases_passed=1,
        cases_total=2,
        prior_c0_pass_rate=None,
        round_kind="maintenance",
        failed_case_ids=["c2"],
    )
    assert check["rollback_required"] is True
    assert check["verdict"]["core_goal_pass"] is False


def test_core_goal_check_c0_1_0_no_rollback():
    check = build_core_goal_check(
        c0_pass_rate=1.0,
        cases_passed=3,
        cases_total=3,
        prior_c0_pass_rate=1.0,
        round_kind="code_change",
        failed_case_ids=[],
    )
    assert check["rollback_required"] is False
    assert check["regression_detected"] is False
    assert check["verdict"]["core_goal_pass"] is True
    assert check["required_c0_value"] == REQUIRED_C0_VALUE


# --- run_evaluation smoke + metrics_report R6 placeholder -------------

@pytest.fixture
def minimal_ability(tmp_path):
    """Build a minimal ability layout: SKILL.md, vocabulary, eval_pack,
    core_goal_test_pack, and a test runner cwd.

    Returns an ``EvalSkillConfig`` pointed at these temp files.
    """

    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\nname: tiny-ability\ndescription: a tiny ability for testing\n---\n"
        "# tiny ability body\n\nShort body for token counting.\n",
        encoding="utf-8",
    )
    vocabulary = tmp_path / "vocabulary.yaml"
    vocabulary.write_text(
        yaml.safe_dump(
            {
                "ascii_anchors": ["tiny"],
                "min_weak_hits": 100,
            }
        ),
        encoding="utf-8",
    )
    eval_pack = tmp_path / "eval_pack.yaml"
    eval_pack.write_text(
        yaml.safe_dump(
            {
                "should_trigger": ["please run the tiny thing"],
                "should_not_trigger": ["what's the weather"],
            }
        ),
        encoding="utf-8",
    )
    core_goal_pack = tmp_path / "core_goal_test_pack.yaml"
    core_goal_pack.write_text(
        yaml.safe_dump(
            {
                "cases": [
                    {"id": "c1", "prompt": "p1", "command": "true"},
                    {"id": "c2", "prompt": "p2", "command": "true"},
                    {"id": "c3", "prompt": "p3", "command": "true"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return EvalSkillConfig(
        ability="tiny-ability",
        skill_md=skill_md,
        vocabulary=vocabulary,
        eval_pack=eval_pack,
        core_goal_test_pack=core_goal_pack,
        test_runner_cmd="true",
        test_runner_cwd=tmp_path,
        runs=1,
        round_kind="code_change",
    )


def test_metrics_report_includes_all_37_r6_keys(minimal_ability):
    report = run_evaluation(minimal_ability)
    metrics = report["metrics"]
    for dim, keys in R6_KEYS.items():
        assert dim in metrics, f"missing R6 dimension {dim}"
        for key in keys:
            assert key in metrics[dim], f"missing R6 key {dim}.{key}"
    # At least the 4 trigger keys must be populated (non-null)
    assert metrics["routing_cost"]["R1_trigger_precision"] is not None
    assert metrics["routing_cost"]["R2_trigger_recall"] is not None
    assert metrics["routing_cost"]["R3_trigger_F1"] is not None
    assert metrics["routing_cost"]["R4_near_miss_FP_rate"] is not None


def test_metrics_report_includes_core_goal_and_round_kind(minimal_ability):
    report = run_evaluation(minimal_ability)
    assert report["round_kind"] == "code_change"
    assert "core_goal_check" in report
    assert "core_goal" in report
    assert report["core_goal_check"]["round_kind"] == "code_change"
    assert report["core_goal_check"]["required_c0_value"] == REQUIRED_C0_VALUE
    assert report["core_goal"]["cases_total"] == 3


def test_metrics_report_written_to_disk(minimal_ability, tmp_path):
    out_path = tmp_path / "metrics_report.yaml"
    minimal_ability.out = out_path
    run_evaluation(minimal_ability)
    assert out_path.exists()
    loaded = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert loaded["ability_id"] == "tiny-ability"
    assert loaded["round_kind"] == "code_change"
    assert "metrics" in loaded
    # R6 keys present (null where not measured)
    total = sum(len(v) for v in loaded["metrics"].values())
    assert total == 37


def test_config_validate_rejects_missing_paths(tmp_path):
    config = EvalSkillConfig(
        ability="x",
        skill_md=tmp_path / "missing.md",
        vocabulary=tmp_path / "missing.yaml",
        eval_pack=tmp_path / "missing_pack.yaml",
        core_goal_test_pack=tmp_path / "missing_core.yaml",
        test_runner_cmd="true",
        test_runner_cwd=tmp_path,
    )
    with pytest.raises(FileNotFoundError):
        config.validate()


def test_config_validate_rejects_bad_round_kind(tmp_path, minimal_ability):
    minimal_ability.round_kind = "bogus"
    with pytest.raises(ValueError):
        minimal_ability.validate()


def test_config_validate_rejects_zero_runs(minimal_ability):
    minimal_ability.runs = 0
    with pytest.raises(ValueError):
        minimal_ability.validate()


# --- CLI ---------------------------------------------------------------

def test_cli_help():
    result = subprocess.run(
        [sys.executable, str(EVAL_SKILL_SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    for flag in (
        "--ability",
        "--skill-md",
        "--vocabulary",
        "--eval-pack",
        "--core-goal-test-pack",
        "--test-runner-cmd",
        "--test-runner-cwd",
        "--runs",
        "--out",
        "--round-kind",
    ):
        assert flag in result.stdout, f"expected {flag} in --help output"
