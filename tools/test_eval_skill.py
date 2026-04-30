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
    decompose_token_tiers,
    detect_mcp_pretty_text_issue,
    detect_template_default_data_antipattern,
    main,
    run_core_goal_test_pack,
    run_evaluation,
    run_health_smoke_check,
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


# --- Stage 4 Wave 1b: v0.4.0-rc1 helper tests -------------------------


def test_decompose_token_tiers_returns_three_axes(tmp_path):
    """§18.1 token-tier decomposition returns C7/C8/C9 with method tags."""

    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\nname: tiny-ability\ndescription: tiny\n---\n"
        "# tiny ability body\nShort body content for estimation.\n",
        encoding="utf-8",
    )
    rule = tmp_path / "ability-bridge.mdc"
    rule.write_text(
        "---\nalwaysApply: true\n---\n"
        "This is an always-apply rule that is loaded on every session.\n",
        encoding="utf-8",
    )
    result = decompose_token_tiers(skill_md, rule_path=rule)
    assert "C7_eager_per_session" in result
    assert "C8_oncall_per_trigger" in result
    assert "C9_lazy_avg_per_load" in result
    assert result["C7_eager_per_session_method"] == "char_heuristic"
    assert result["C8_oncall_per_trigger_method"] == "char_heuristic"
    assert result["C9_lazy_avg_per_load_method"] == "char_heuristic"
    # With both rule + skill populated, C7 and C8 must be > 0.
    assert result["C7_eager_per_session"] > 0
    assert result["C8_oncall_per_trigger"] > 0
    # measured_with_* fields are emitted
    assert result["measured_with_sessions"] == 1
    assert result["measured_with_triggers"] == 1


def test_decompose_token_tiers_missing_skill_md_raises(tmp_path):
    """Workspace rule 'No Silent Failures': missing SKILL.md raises."""

    with pytest.raises(FileNotFoundError):
        decompose_token_tiers(tmp_path / "nonexistent_SKILL.md")


def test_decompose_token_tiers_with_lazy_manifest(tmp_path):
    """A .lazy-manifest file populates C9 averaged over declared files."""

    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("# tiny body\n", encoding="utf-8")
    # Create two lazy files with known content.
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "history.md").write_text("x" * 380, encoding="utf-8")  # ~100 tokens
    (refs / "design.md").write_text("y" * 760, encoding="utf-8")  # ~200 tokens
    lazy_manifest = tmp_path / ".lazy-manifest"
    lazy_manifest.write_text(
        yaml.safe_dump(
            {
                "ability_id": "tiny",
                "lazy_paths": [
                    {"path": "references/history.md"},
                    {"path": "references/design.md"},
                ],
            }
        ),
        encoding="utf-8",
    )
    result = decompose_token_tiers(
        skill_md, lazy_manifest_path=lazy_manifest
    )
    # Average of ~100 + ~200 = ~150 tokens (floor division)
    assert result["C9_lazy_avg_per_load"] > 0
    assert result["measured_with_lazy_loads"] == 2


def test_detect_mcp_pretty_text_issue_flags_offender(tmp_path):
    """MCP handler with both pretty JSON and structuredContent → flagged."""

    src = tmp_path / "handler.ts"
    src.write_text(
        "export const handler = async () => {\n"
        "  const data = { ok: true };\n"
        "  return {\n"
        "    content: [{ type: 'text', text: JSON.stringify(data, null, 2) }],\n"
        "    structuredContent: data,\n"
        "  };\n"
        "};\n",
        encoding="utf-8",
    )
    result = detect_mcp_pretty_text_issue(tmp_path)
    assert result["src_dir_exists"] is True
    assert len(result["found"]) >= 1
    entry = result["found"][0]
    assert "handler.ts" in entry["file"]
    assert entry["indent"] == 2
    assert "JSON.stringify" in entry["code_excerpt"]


def test_detect_mcp_pretty_text_issue_clean_file_passes(tmp_path):
    """Pretty JSON without structuredContent → not flagged."""

    src = tmp_path / "logger.ts"
    src.write_text(
        "console.log(JSON.stringify({a: 1}, null, 2));\n",
        encoding="utf-8",
    )
    result = detect_mcp_pretty_text_issue(tmp_path)
    assert result["found"] == []


def test_detect_mcp_pretty_text_issue_missing_dir_returns_empty(tmp_path):
    """Missing src_dir → empty found, src_dir_exists=False, no raise."""

    result = detect_mcp_pretty_text_issue(tmp_path / "nonexistent")
    assert result["found"] == []
    assert result["src_dir_exists"] is False


def test_detect_template_default_data_antipattern_flags_non_stub(tmp_path):
    """Canvas template with non-stub DEFAULT_DATA → flagged."""

    tpl = tmp_path / "Dashboard.tsx"
    tpl.write_text(
        "export const DEFAULT_DATA = {\n"
        "  leaderboard: [\n"
        "    { name: 'user1', spend: 100 },\n"
        "    { name: 'user2', spend: 200 },\n"
        "  ],\n"
        "  latestTsMs: 1714464840000,\n"
        "};\n"
        "export const Component = () => <div>...</div>;\n",
        encoding="utf-8",
    )
    result = detect_template_default_data_antipattern(tmp_path)
    assert result["templates_dir_exists"] is True
    assert len(result["found"]) >= 1
    entry = result["found"][0]
    assert "Dashboard.tsx" in entry["file"]
    assert "DEFAULT_DATA" in entry["default_keys"]
    assert entry["bytes"] > 0


def test_detect_template_default_data_antipattern_stub_passes(tmp_path):
    """Canvas template with stub DEFAULT_DATA ({}) → not flagged."""

    tpl = tmp_path / "Clean.tsx"
    tpl.write_text(
        "export const DEFAULT_DATA = {};\n"
        "export const Component = () => <div>...</div>;\n",
        encoding="utf-8",
    )
    result = detect_template_default_data_antipattern(tmp_path)
    # Only DEFAULT_DATA with non-stub RHS should match; stub should not.
    assert result["found"] == []


def test_detect_template_default_data_antipattern_missing_dir_returns_empty(
    tmp_path,
):
    """Missing templates_dir → empty found, no raise."""

    result = detect_template_default_data_antipattern(
        tmp_path / "nonexistent"
    )
    assert result["found"] == []
    assert result["templates_dir_exists"] is False


def test_run_health_smoke_check_rejects_non_list():
    """run_health_smoke_check raises ValueError on non-list config."""

    with pytest.raises(ValueError):
        run_health_smoke_check("not a list")  # type: ignore[arg-type]


def test_run_health_smoke_check_empty_config_returns_zero_total():
    """Empty config → total=0, passed=0, no per_check entries."""

    result = run_health_smoke_check([])
    assert result["total"] == 0
    assert result["passed"] == 0
    assert result["per_check"] == []


def test_run_health_smoke_check_bad_entries_captured_as_errors():
    """Entries missing endpoint/axis → captured in errors, not raised."""

    result = run_health_smoke_check(
        [
            {"endpoint": "https://example.com", "axis": "read"},  # normal
            "not a dict",  # bad entry
            {"axis": "read"},  # missing endpoint
            {"endpoint": "https://example.com"},  # missing axis
        ]
    )
    # First may still try to run (will fail because no server); others caught.
    assert len(result["errors"]) >= 2
    assert any("not a dict" in e for e in result["errors"])


# --- v0.4.0 Wave 1c additions: G2 / G3 / G4 helper tests --------------
# Append-only section (Wave 1c) — imports are local to avoid touching
# the shared top-of-file import block that Wave 1b is also editing.

from tools.eval_skill import (  # noqa: E402
    compute_g2_cross_domain_transfer_pass,
    compute_g3_ood_robustness,
    compute_g4_model_version_stability,
)


def _sample_runner_output(
    cells, ability_id: str = "chip-usage-helper", matrix_mode: str = "mvp"
):
    """Build a minimal runner_output-shaped dict for G2/G3/G4 tests."""

    return {
        "ability_id": ability_id,
        "matrix_mode": matrix_mode,
        "cells": cells,
        "summary": {"total_cells": len(cells)},
    }


def test_compute_g2_cross_domain_transfer_pass_selects_target_cells():
    """G2 filters cells to the target_domain (scenario_pack match) and
    returns a prompts_run-weighted mean pass_rate."""

    output = _sample_runner_output(
        [
            # source_domain cells (should be ignored)
            {
                "model": "claude-haiku-4-5",
                "thinking_depth": "fast",
                "scenario_pack": "trigger_basic",
                "prompts_run": 20,
                "pass_rate": 1.0,
                "pass_at_k": 1.0,
                "per_prompt": [],
            },
            # target_domain cells (should be aggregated)
            {
                "model": "claude-haiku-4-5",
                "thinking_depth": "fast",
                "scenario_pack": "near_miss",
                "prompts_run": 10,
                "pass_rate": 0.8,
                "pass_at_k": 0.9,
                "per_prompt": [],
            },
            {
                "model": "claude-sonnet-4-6",
                "thinking_depth": "default",
                "scenario_pack": "near_miss",
                "prompts_run": 10,
                "pass_rate": 0.6,
                "pass_at_k": 0.7,
                "per_prompt": [],
            },
        ]
    )
    result = compute_g2_cross_domain_transfer_pass(
        output, source_domain="trigger_basic", target_domain="near_miss"
    )
    # (0.8*10 + 0.6*10) / 20 = 0.7
    assert abs(result["pass_rate"] - 0.7) < 1e-4
    assert result["sample_count"] == 20
    assert result["cells_matched"] == 2
    assert result["provenance"]["source_domain"] == "trigger_basic"
    assert result["provenance"]["target_domain"] == "near_miss"
    assert (
        result["provenance"]["runner_source"]
        == "evals/si-chip/runners/real_llm_runner.py"
    )


def test_compute_g3_ood_robustness_aggregates_matched_prompts(tmp_path):
    """G3 intersects an OOD pack's prompts with runner per_prompt entries
    and returns mean pass_at_k + fail_cases list."""

    ood_pack = tmp_path / "ood_pack.yaml"
    ood_pack.write_text(
        yaml.safe_dump(
            {
                "should_trigger": ["ood prompt 1"],
                "should_not_trigger": ["ood prompt 2"],
            }
        ),
        encoding="utf-8",
    )
    output = _sample_runner_output(
        [
            {
                "model": "claude-haiku-4-5",
                "thinking_depth": "fast",
                "scenario_pack": "trigger_basic",
                "prompts_run": 3,
                "pass_rate": 0.6667,
                "pass_at_k": 0.6667,
                "per_prompt": [
                    {"prompt": "ood prompt 1", "pass_at_k": 1.0},
                    {"prompt": "ood prompt 2", "pass_at_k": 0.0},
                    {"prompt": "not in ood pack", "pass_at_k": 1.0},
                ],
            }
        ]
    )
    result = compute_g3_ood_robustness(output, ood_pack)
    # Only the 2 matching prompts are considered: (1.0 + 0.0) / 2 = 0.5
    assert abs(result["pass_rate"] - 0.5) < 1e-4
    assert result["sample_count"] == 2
    assert len(result["fail_cases"]) == 1
    assert result["fail_cases"][0]["prompt"] == "ood prompt 2"
    assert result["provenance"]["ood_prompt_count"] == 2
    # Missing OOD pack must raise (no silent failures).
    with pytest.raises(FileNotFoundError):
        compute_g3_ood_robustness(output, tmp_path / "does_not_exist.yaml")


def test_compute_g4_model_version_stability_flags_drift():
    """G4 matches cells across two runs and flags cells whose
    |pass_rate delta| >= drift_threshold as drift_cases."""

    prior = _sample_runner_output(
        [
            {
                "model": "claude-haiku-4-5",
                "thinking_depth": "fast",
                "scenario_pack": "trigger_basic",
                "prompts_run": 20,
                "pass_rate": 0.90,
            },
            {
                "model": "claude-sonnet-4-6",
                "thinking_depth": "default",
                "scenario_pack": "near_miss",
                "prompts_run": 10,
                "pass_rate": 0.80,
            },
        ]
    )
    current = _sample_runner_output(
        [
            # stable: delta 0.02 < 0.05
            {
                "model": "claude-haiku-4-5",
                "thinking_depth": "fast",
                "scenario_pack": "trigger_basic",
                "prompts_run": 20,
                "pass_rate": 0.92,
            },
            # drift: delta 0.10 >= 0.05
            {
                "model": "claude-sonnet-4-6",
                "thinking_depth": "default",
                "scenario_pack": "near_miss",
                "prompts_run": 10,
                "pass_rate": 0.70,
            },
        ]
    )
    result = compute_g4_model_version_stability(current, prior)
    assert result["matched_cells"] == 2
    assert abs(result["stability_ratio"] - 0.5) < 1e-4
    assert len(result["drift_cases"]) == 1
    drift = result["drift_cases"][0]
    assert drift["model"] == "claude-sonnet-4-6"
    assert abs(drift["delta"] - (-0.10)) < 1e-4
    assert "claude-haiku-4-5" in result["per_model_delta"]
    assert "claude-sonnet-4-6" in result["per_model_delta"]
    # Unmatched cells (no overlap) → matched_cells = 0, stability = 0.0
    empty = compute_g4_model_version_stability(
        _sample_runner_output([]), prior
    )
    assert empty["matched_cells"] == 0
    assert empty["stability_ratio"] == 0.0
