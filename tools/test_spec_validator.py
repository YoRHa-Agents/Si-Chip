#!/usr/bin/env python3
"""Unit tests for ``tools/spec_validator.py``.

Workspace rule "Mandatory Verification": Round 9 (task spec §6) extends
the validator's ``check_router_matrix_cells`` invariant to accept BOTH
the pre-Round-9 0.1.0 schema (mvp:8 + full:96) AND the Round 9 0.1.1
schema (+ additive intermediate:16). These tests lock down that
behaviour:

* **0.1.1 happy path** — real template on disk: intermediate invariants
  hold (cells==16, gate_binding=="relaxed", axis product=16);
  default-mode ``--json`` exits 0 with 8/8 PASS.
* **0.1.0 backward compatibility** — pre-Round-9 template shape on a
  temp fixture: validator still passes (no intermediate assertion
  when schema is 0.1.0).
* **0.1.1 negative path** — template with wrong intermediate cells
  fails the ROUTER_MATRIX_CELLS invariant.

These are the minimum 3 tests the Round 9 task spec requires; the
default-mode ``spec_validator.py --json`` end-to-end 8/8 PASS
integration is additionally asserted via subprocess.

Run::

    python -m pytest tools/test_spec_validator.py -q
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import spec_validator as sv  # noqa: E402


REAL_TEMPLATES_DIR = _REPO_ROOT / "templates"


def _write_template(
    tmp_templates_dir: Path,
    router_template_yaml: str,
) -> None:
    """Copy the real BAP schema, value-vector template, and write a router fixture.

    Only the router_test_matrix template is varied across tests; the
    other templates are read from the real ``templates/`` tree so the
    BAP_SCHEMA + VALUE_VECTOR_AXES invariants remain intact.
    """

    tmp_templates_dir.mkdir(parents=True, exist_ok=True)
    # Copy the unchanged template files from the real tree.
    for name in (
        "basic_ability_profile.schema.yaml",
        "half_retire_decision.template.yaml",
        "iteration_delta_report.template.yaml",
        "next_action_plan.template.yaml",
        "self_eval_suite.template.yaml",
    ):
        src = REAL_TEMPLATES_DIR / name
        if src.exists():
            (tmp_templates_dir / name).write_text(
                src.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
    (tmp_templates_dir / "router_test_matrix.template.yaml").write_text(
        router_template_yaml, encoding="utf-8",
    )


class CheckRouterMatrixCellsSchema011Tests(unittest.TestCase):
    """Round 9 schema 0.1.1 (intermediate additive) happy path."""

    def test_real_template_passes_intermediate_invariants(self) -> None:
        """Real templates/router_test_matrix.template.yaml is schema 0.1.1."""

        result = sv.check_router_matrix_cells(REAL_TEMPLATES_DIR)
        self.assertTrue(result.passed, msg=result.message)
        self.assertEqual(result.id, "ROUTER_MATRIX_CELLS")
        ev = result.evidence
        self.assertEqual(ev["schema_version"], "0.1.1")
        self.assertEqual(ev["mvp"], 8)
        self.assertEqual(ev["full"], 96)
        self.assertEqual(ev["intermediate"]["cell_counts_intermediate"], 16)
        self.assertEqual(ev["intermediate"]["profile_cells"], 16)
        self.assertEqual(ev["intermediate"]["profile_gate_binding"], "relaxed")
        self.assertEqual(ev["intermediate"]["profile_axis_product"], 16)

    def test_intermediate_axis_product_equals_16(self) -> None:
        """2 models × 2 depths × 4 scenario_packs = 16 for intermediate."""

        path = REAL_TEMPLATES_DIR / "router_test_matrix.template.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        inter = data["profiles"]["intermediate"]
        self.assertEqual(
            len(inter["models"])
            * len(inter["thinking_depths"])
            * len(inter["scenario_packs"]),
            16,
        )
        self.assertEqual(inter["cells"], 16)
        self.assertEqual(inter["gate_binding"], "relaxed")


class CheckRouterMatrixCellsSchema010BackwardCompatTests(unittest.TestCase):
    """Pre-Round-9 schema 0.1.0 (no intermediate) must still pass."""

    def test_schema_010_template_passes_without_intermediate(self) -> None:
        """Synthetic 0.1.0-shaped template: validator should accept it."""

        with tempfile.TemporaryDirectory() as td:
            tmp_templates = Path(td) / "templates"
            _write_template(
                tmp_templates,
                textwrap.dedent(
                    """\
                    $schema_version: "0.1.0"
                    $spec_section: "§5"
                    $source_of_truth: ".agents/skills/si-chip/"
                    metadata:
                      name: "si-chip-router-test-matrix"
                      version: "0.1.0"
                      description: "legacy 0.1.0 template (pre-Round-9)"
                    cell_counts:
                      mvp: 8
                      full: 96
                    profiles:
                      mvp:
                        cells: 8
                        models: [composer_2, sonnet_shallow]
                        thinking_depths: [fast, default]
                        scenario_packs: [trigger_basic, near_miss]
                      full:
                        cells: 96
                        models: [composer_2, haiku_4_5, sonnet_4_6, opus_4_7, gpt_5_mini, deterministic_memory_router]
                        thinking_depths: [fast, default, extended, round_escalated]
                        scenario_packs: [trigger_basic, near_miss, multi_skill_competition, execution_handoff]
                    profile_to_gate_binding:
                      relaxed: v1_baseline
                      standard: v2_tightened
                      strict: v3_strict
                    """
                ),
            )
            result = sv.check_router_matrix_cells(tmp_templates)
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.evidence["schema_version"], "0.1.0")
            # No intermediate block on schema 0.1.0.
            self.assertNotIn("intermediate", result.evidence)


class CheckRouterMatrixCellsSchema011NegativeTests(unittest.TestCase):
    """Round 9 schema 0.1.1 with wrong intermediate count must fail."""

    def test_wrong_intermediate_cell_count_fails(self) -> None:
        """cell_counts.intermediate=12 (not 16) → BLOCKER fails."""

        with tempfile.TemporaryDirectory() as td:
            tmp_templates = Path(td) / "templates"
            _write_template(
                tmp_templates,
                textwrap.dedent(
                    """\
                    $schema_version: "0.1.1"
                    $spec_section: "§5"
                    $source_of_truth: ".agents/skills/si-chip/"
                    metadata:
                      name: "si-chip-router-test-matrix"
                      version: "0.1.1"
                      description: "malformed fixture"
                    cell_counts:
                      mvp: 8
                      intermediate: 12   # WRONG — must be 16
                      full: 96
                    profiles:
                      mvp:
                        cells: 8
                        models: [composer_2, sonnet_shallow]
                        thinking_depths: [fast, default]
                        scenario_packs: [trigger_basic, near_miss]
                      intermediate:
                        cells: 12          # WRONG — must be 16
                        models: [composer_2, sonnet_shallow]
                        thinking_depths: [fast, default]
                        scenario_packs: [trigger_basic, near_miss, multi_skill_competition]
                        gate_binding: relaxed
                      full:
                        cells: 96
                        models: [composer_2, haiku_4_5, sonnet_4_6, opus_4_7, gpt_5_mini, deterministic_memory_router]
                        thinking_depths: [fast, default, extended, round_escalated]
                        scenario_packs: [trigger_basic, near_miss, multi_skill_competition, execution_handoff]
                    """
                ),
            )
            result = sv.check_router_matrix_cells(tmp_templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")

    def test_wrong_intermediate_gate_binding_fails(self) -> None:
        """intermediate.gate_binding='standard' (not relaxed) → fails."""

        with tempfile.TemporaryDirectory() as td:
            tmp_templates = Path(td) / "templates"
            _write_template(
                tmp_templates,
                textwrap.dedent(
                    """\
                    $schema_version: "0.1.1"
                    $spec_section: "§5"
                    $source_of_truth: ".agents/skills/si-chip/"
                    metadata:
                      name: "si-chip-router-test-matrix"
                      version: "0.1.1"
                      description: "malformed fixture"
                    cell_counts:
                      mvp: 8
                      intermediate: 16
                      full: 96
                    profiles:
                      mvp:
                        cells: 8
                        models: [composer_2, sonnet_shallow]
                        thinking_depths: [fast, default]
                        scenario_packs: [trigger_basic, near_miss]
                      intermediate:
                        cells: 16
                        models: [composer_2, sonnet_shallow]
                        thinking_depths: [fast, default]
                        scenario_packs: [trigger_basic, near_miss, multi_skill_competition, execution_handoff]
                        gate_binding: standard   # WRONG — §11 scope: intermediate must stay at relaxed, not a §5.4 binding change
                      full:
                        cells: 96
                        models: [composer_2, haiku_4_5, sonnet_4_6, opus_4_7, gpt_5_mini, deterministic_memory_router]
                        thinking_depths: [fast, default, extended, round_escalated]
                        scenario_packs: [trigger_basic, near_miss, multi_skill_competition, execution_handoff]
                    """
                ),
            )
            result = sv.check_router_matrix_cells(tmp_templates)
            self.assertFalse(result.passed, msg=result.message)

    def test_unsupported_schema_version_fails(self) -> None:
        """$schema_version='0.2.0' → validator refuses (not yet bumped)."""

        with tempfile.TemporaryDirectory() as td:
            tmp_templates = Path(td) / "templates"
            _write_template(
                tmp_templates,
                textwrap.dedent(
                    """\
                    $schema_version: "0.2.0"
                    cell_counts: {mvp: 8, full: 96}
                    profiles:
                      mvp:
                        cells: 8
                        models: [composer_2, sonnet_shallow]
                        thinking_depths: [fast, default]
                        scenario_packs: [trigger_basic, near_miss]
                      full:
                        cells: 96
                        models: [composer_2, haiku_4_5, sonnet_4_6, opus_4_7, gpt_5_mini, deterministic_memory_router]
                        thinking_depths: [fast, default, extended, round_escalated]
                        scenario_packs: [trigger_basic, near_miss, multi_skill_competition, execution_handoff]
                    """
                ),
            )
            result = sv.check_router_matrix_cells(tmp_templates)
            self.assertFalse(result.passed)
            self.assertIn("0.2.0", result.message)


class SpecValidatorJsonCliPassesTests(unittest.TestCase):
    """End-to-end: ``tools/spec_validator.py --json`` still exits 0 (8/8 PASS)."""

    def test_default_mode_8_of_8_pass(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools/spec_validator.py"),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["verdict"], "PASS")
        self.assertEqual(len(payload["results"]), 8)
        # All 8 invariants must pass in default mode.
        for r in payload["results"]:
            with self.subTest(invariant=r["id"]):
                self.assertTrue(r["passed"], msg=r["message"])
        # ROUTER_MATRIX_CELLS result explicitly reports schema 0.1.1 now.
        matrix = next(
            r for r in payload["results"] if r["id"] == "ROUTER_MATRIX_CELLS"
        )
        self.assertEqual(matrix["evidence"]["schema_version"], "0.1.1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
