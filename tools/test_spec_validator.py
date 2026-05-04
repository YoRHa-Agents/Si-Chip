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

Stage 4 Wave 2a (v0.3.0-rc1, 2026-04-29) extends the BLOCKER set
additively from 9 to 11:

* ``CORE_GOAL_FIELD_PRESENT`` — checks that the BasicAbilityProfile
  schema declares a REQUIRED ``core_goal`` block per spec §14.1.1.
* ``ROUND_KIND_TEMPLATE_VALID`` — checks that the iteration-delta and
  next-action-plan templates declare ``round_kind`` from the §15.1.1
  4-value enum (``code_change`` / ``measurement_only`` / ``ship_prep``
  / ``maintenance``).

Both new BLOCKERs PASS-as-SKIP for legacy ``$schema_version < "0.2.0"``
inputs to preserve backward-compat with Round 1-13 / Round 1-10
artefacts. The historical 9 BLOCKERs continue to PASS unchanged.

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
from typing import Any, Dict, List, Optional

import yaml

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import spec_validator as sv  # noqa: E402

# Surface tools.round_kind so tests can verify the spec_validator imports
# the live module instead of a vendor copy.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from tools.round_kind import ROUND_KINDS  # noqa: E402


REAL_TEMPLATES_DIR = _REPO_ROOT / "templates"
SPEC_V0_3_0_RC1 = _REPO_ROOT / ".local/research/spec_v0.3.0-rc1.md"
SPEC_V0_2_0 = _REPO_ROOT / ".local/research/spec_v0.2.0.md"


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
    """End-to-end: ``tools/spec_validator.py --json`` still exits 0 (>= 9/9 PASS).

    Stage 4 Wave 2a additively widened the BLOCKER set from 9 to 11 (added
    CORE_GOAL_FIELD_PRESENT and ROUND_KIND_TEMPLATE_VALID; both PASS-as-SKIP
    against pre-v0.3.0 schemas). The original 9 historical BLOCKERs still
    PASS at default v0.2.0 spec mode; this test enforces the historical
    floor while remaining forward-compatible with the v0.3.0 widening.
    """

    def test_default_mode_9_of_9_pass(self) -> None:
        """Round 12 added the 9th invariant REACTIVATION_DETECTOR_EXISTS;
        Stage 4 Wave 2a widened to 11 BLOCKERs but the 9 historical
        invariants must still PASS unchanged at default v0.2.0 spec mode.
        """

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
        # Historical floor: at least 9 BLOCKERs (Round 12). Wave 2a adds 2
        # more (10 / 11) but the floor is preserved so older callers / CI
        # gates that count >= 9 are not surprised.
        self.assertGreaterEqual(len(payload["results"]), 9)
        for r in payload["results"]:
            with self.subTest(invariant=r["id"]):
                self.assertTrue(r["passed"], msg=r["message"])
        matrix = next(
            r for r in payload["results"] if r["id"] == "ROUTER_MATRIX_CELLS"
        )
        self.assertEqual(matrix["evidence"]["schema_version"], "0.1.1")
        # The 9th invariant must be REACTIVATION_DETECTOR_EXISTS.
        ids = [r["id"] for r in payload["results"]]
        self.assertIn("REACTIVATION_DETECTOR_EXISTS", ids)


class CheckReactivationDetectorExistsTests(unittest.TestCase):
    """Round 12 §6.4 invariant — REACTIVATION_DETECTOR_EXISTS."""

    def test_real_repo_passes_invariant(self) -> None:
        """The shipped detector + tests must satisfy the BLOCKER."""

        result = sv.check_reactivation_detector_exists(repo_root=_REPO_ROOT)
        self.assertEqual(result.id, "REACTIVATION_DETECTOR_EXISTS")
        self.assertEqual(result.severity, "BLOCKER")
        self.assertTrue(result.passed, msg=result.message)
        self.assertEqual(
            result.evidence["expected_trigger_ids"],
            list(sv.EXPECTED_REACTIVATION_TRIGGER_IDS),
        )
        self.assertEqual(result.evidence["missing_in_detector"], [])
        self.assertEqual(result.evidence["missing_in_tests"], [])

    def test_missing_detector_fails_blocker(self) -> None:
        """An empty repo without the detector file must FAIL the BLOCKER."""

        with tempfile.TemporaryDirectory() as td:
            empty_root = Path(td)
            (empty_root / "tools").mkdir()
            result = sv.check_reactivation_detector_exists(repo_root=empty_root)
            self.assertFalse(result.passed)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("missing detector", result.message)

    def test_missing_trigger_id_in_detector_fails_blocker(self) -> None:
        """A detector that omits one trigger ID must FAIL the BLOCKER."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tools").mkdir()
            # Omit "manual_invocation_rebound" deliberately.
            kept = [
                tid for tid in sv.EXPECTED_REACTIVATION_TRIGGER_IDS
                if tid != "manual_invocation_rebound"
            ]
            (root / "tools" / "reactivation_detector.py").write_text(
                "# detector stub\n"
                + "\n".join(f"# {tid}" for tid in kept)
                + "\n",
                encoding="utf-8",
            )
            (root / "tools" / "test_reactivation_detector.py").write_text(
                "# test stub\n"
                + "\n".join(
                    f"# test for {tid}"
                    for tid in sv.EXPECTED_REACTIVATION_TRIGGER_IDS
                )
                + "\n",
                encoding="utf-8",
            )
            result = sv.check_reactivation_detector_exists(repo_root=root)
            self.assertFalse(result.passed)
            self.assertIn(
                "manual_invocation_rebound", result.evidence["missing_in_detector"]
            )

    def test_missing_test_file_fails_blocker(self) -> None:
        """A detector with no sibling test file must FAIL the BLOCKER."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tools").mkdir()
            (root / "tools" / "reactivation_detector.py").write_text(
                "\n".join(f"# {tid}" for tid in sv.EXPECTED_REACTIVATION_TRIGGER_IDS),
                encoding="utf-8",
            )
            result = sv.check_reactivation_detector_exists(repo_root=root)
            self.assertFalse(result.passed)
            self.assertIn("missing tests", result.message)


# ─────────────────────────────────────────────────────────────────────
# Stage 4 Wave 2a tests — v0.3.0-rc1 BLOCKER widening
# ─────────────────────────────────────────────────────────────────────


def _bap_schema_min_v0_2_0() -> Dict[str, Any]:
    """Return a minimum-shape v0.2.0 BAP schema usable in test fixtures.

    Mirrors the real templates/basic_ability_profile.schema.yaml shape
    just enough for ``check_core_goal_field_present`` to exercise its
    happy-path (and provides the surface that negative tests can
    selectively mutate).
    """

    return {
        "$schema_version": "0.2.0",
        "properties": {
            "basic_ability": {
                "required": [
                    "id",
                    "intent",
                    "core_goal",
                    "current_surface",
                    "packaging",
                    "lifecycle",
                    "eval_state",
                    "metrics",
                    "value_vector",
                    "router_floor",
                    "decision",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "intent": {"type": "string"},
                    "core_goal": {
                        "type": "object",
                        "required": [
                            "statement",
                            "test_pack_path",
                            "minimum_pass_rate",
                        ],
                        "properties": {
                            "statement": {"type": "string", "minLength": 16},
                            "test_pack_path": {"type": "string"},
                            "minimum_pass_rate": {
                                "type": "number",
                                "const": 1.0,
                            },
                        },
                    },
                    "current_surface": {"type": "object"},
                    "packaging": {"type": "object"},
                    "lifecycle": {"type": "object"},
                    "eval_state": {"type": "object"},
                    "metrics": {"type": "object"},
                    "value_vector": {"type": "object"},
                    "router_floor": {"type": ["string", "null"]},
                    "decision": {"type": "object"},
                },
            },
        },
    }


def _bap_schema_min_v0_1_0() -> Dict[str, Any]:
    """Return a minimum-shape v0.1.0 BAP schema (no core_goal)."""

    return {
        "$schema_version": "0.1.0",
        "properties": {
            "basic_ability": {
                "required": [
                    "id",
                    "intent",
                    "current_surface",
                    "packaging",
                    "lifecycle",
                    "eval_state",
                    "metrics",
                    "value_vector",
                    "router_floor",
                    "decision",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "intent": {"type": "string"},
                    "current_surface": {"type": "object"},
                    "packaging": {"type": "object"},
                    "lifecycle": {"type": "object"},
                    "eval_state": {"type": "object"},
                    "metrics": {"type": "object"},
                    "value_vector": {"type": "object"},
                    "router_floor": {"type": ["string", "null"]},
                    "decision": {"type": "object"},
                },
            },
        },
    }


def _write_only_bap_schema(
    tmp_dir: Path, schema_data: Dict[str, Any]
) -> Path:
    """Write ``schema_data`` as the BAP schema in ``tmp_dir/templates``.

    Used by tests that only touch BAP_SCHEMA / CORE_GOAL_FIELD_PRESENT
    and don't need other templates to be present.
    """

    templates = tmp_dir / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    target = templates / "basic_ability_profile.schema.yaml"
    target.write_text(
        yaml.safe_dump(schema_data, sort_keys=False),
        encoding="utf-8",
    )
    return templates


def _write_round_kind_templates(
    tmp_dir: Path,
    iteration_delta: Optional[Dict[str, Any]] = None,
    next_action_plan: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write minimal round-kind templates into ``tmp_dir/templates``.

    Either parameter may be omitted to skip writing that template.
    Returns the templates directory.
    """

    templates = tmp_dir / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    if iteration_delta is not None:
        (templates / "iteration_delta_report.template.yaml").write_text(
            yaml.safe_dump(iteration_delta, sort_keys=False),
            encoding="utf-8",
        )
    if next_action_plan is not None:
        (templates / "next_action_plan.template.yaml").write_text(
            yaml.safe_dump(next_action_plan, sort_keys=False),
            encoding="utf-8",
        )
    return templates


def _round_kind_template_v0_2_0(name: str, value: str = "code_change") -> Dict[str, Any]:
    """Return a minimal v0.2.0 round-kind-bearing template."""

    return {
        "$schema_version": "0.2.0",
        "metadata": {"name": name, "version": "0.2.0"},
        "required_fields": ["round_kind"],
        "schema": {
            "round_kind": {
                "type": "string",
                "required": True,
                "enum": sorted(ROUND_KINDS),
                "description": "spec v0.3.0-rc1 §15.1.1 enum",
            },
        },
        "example_instance": {
            "round_kind": value,
        },
    }


def _round_kind_template_v0_1_0(name: str) -> Dict[str, Any]:
    """Return a minimal v0.1.0 round-kind template (no round_kind required)."""

    return {
        "$schema_version": "0.1.0",
        "metadata": {"name": name, "version": "0.1.0"},
        "required_fields": ["round_id"],
        "schema": {"round_id": {"type": "string", "required": True}},
        "example_instance": {"round_id": "r0"},
    }


class V030Rc1AcceptanceTests(unittest.TestCase):
    """v0.3.0-rc1 spec acceptance: 11/11 BLOCKER PASS via subprocess."""

    def test_v0_3_0_rc1_spec_loads_11_of_11_pass(self) -> None:
        """``--spec spec_v0.3.0-rc1.md --json`` exits 0 with >= 11/11 PASS.

        Stage 4 Wave 1b (v0.4.0-rc1) widened to 14 BLOCKERs (added
        TOKEN_TIER_DECLARED_WHEN_REPORTED, REAL_DATA_FIXTURE_PROVENANCE,
        HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND). All 11 historical
        BLOCKERs MUST still PASS against v0.3.0-rc1 spec; the 3 new
        ones PASS-as-SKIP when no v0.4.0 artefacts exist. Total = 14.
        """

        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools/spec_validator.py"),
                "--spec",
                str(SPEC_V0_3_0_RC1),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["verdict"], "PASS")
        # Floor: at least 11 BLOCKERs (v0.3.0-rc1). Wave 1b adds 3 more
        # (12-14) but the v0.3.0 floor is preserved for backward-compat.
        self.assertGreaterEqual(len(payload["results"]), 11)
        passed_count = sum(1 for r in payload["results"] if r["passed"])
        self.assertEqual(passed_count, len(payload["results"]))
        ids = [r["id"] for r in payload["results"]]
        self.assertIn("CORE_GOAL_FIELD_PRESENT", ids)
        self.assertIn("ROUND_KIND_TEMPLATE_VALID", ids)
        # spec_path is echoed back in the report.
        self.assertEqual(payload["spec_path"], str(SPEC_V0_3_0_RC1.resolve()))

    def test_v0_2_0_default_mode_still_9_of_9_pass(self) -> None:
        """Default v0.2.0 spec still PASS; 9 historical + 2 new BLOCKERs (= 11 PASS).

        Stage 4 Wave 1b widens the set to 14 (11 historical + 3 v0.4.0
        BLOCKERs that PASS-as-SKIP against the default v0.2.0 spec).
        """

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
        # Floor: at least 11 BLOCKERs. Wave 1b adds 3 more (total 14).
        self.assertGreaterEqual(len(payload["results"]), 11)
        # All 9 historical BLOCKERs MUST be present and PASSed.
        historical = {
            "BAP_SCHEMA",
            "R6_KEYS",
            "THRESHOLD_TABLE",
            "ROUTER_MATRIX_CELLS",
            "VALUE_VECTOR_AXES",
            "PLATFORM_PRIORITY",
            "DOGFOOD_PROTOCOL",
            "FOREVER_OUT_LIST",
            "REACTIVATION_DETECTOR_EXISTS",
        }
        observed_ids = {r["id"] for r in payload["results"]}
        self.assertEqual(historical & observed_ids, historical)
        for r in payload["results"]:
            with self.subTest(invariant=r["id"]):
                self.assertTrue(r["passed"], msg=r["message"])

    def test_strict_prose_count_v0_3_0_rc1_passes(self) -> None:
        """``--strict-prose-count`` against v0.3.0-rc1 spec exits 0."""

        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools/spec_validator.py"),
                "--spec",
                str(SPEC_V0_3_0_RC1),
                "--strict-prose-count",
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["verdict"], "PASS")
        # SUPPORTED_SPEC_VERSIONS must include v0.3.0-rc1.
        self.assertIn("v0.3.0-rc1", sv.SUPPORTED_SPEC_VERSIONS)
        # Prose-count maps must include v0.3.0-rc1 (37 sub-metrics, 30 cells).
        self.assertEqual(sv.EXPECTED_R6_PROSE_BY_SPEC["v0.3.0-rc1"], 37)
        self.assertEqual(
            sv.EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.3.0-rc1"], 30
        )


class CheckCoreGoalFieldPresentTests(unittest.TestCase):
    """v0.3.0 §14 BLOCKER — CORE_GOAL_FIELD_PRESENT."""

    def test_real_v0_2_0_schema_passes(self) -> None:
        """The real shipped BAP schema satisfies §14.1.1 / §14.3.

        The shipped schema's ``$schema_version`` is now 0.3.0 (additive
        v0.4.0 extension per Stage 4 Wave 1a); the v0.3.0 +core_goal
        contract from Stage 4 Wave 2a is preserved in both 0.2.0 and
        0.3.0 schema buckets.
        """

        result = sv.check_core_goal_field_present(REAL_TEMPLATES_DIR)
        self.assertEqual(result.id, "CORE_GOAL_FIELD_PRESENT")
        self.assertEqual(result.severity, "BLOCKER")
        self.assertTrue(result.passed, msg=result.message)
        self.assertIn(result.evidence["schema_version"], {"0.2.0", "0.3.0"})
        self.assertNotIn("skipped_reason", result.evidence)

    def test_core_goal_field_present_blocker_skips_for_v0_1_0_schema(self) -> None:
        """v0.1.0 schemas predate v0.3.0 → PASS-as-SKIP, no FAIL."""

        with tempfile.TemporaryDirectory() as td:
            templates = _write_only_bap_schema(
                Path(td), _bap_schema_min_v0_1_0()
            )
            result = sv.check_core_goal_field_present(templates)
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.evidence["schema_version"], "0.1.0")
            self.assertEqual(
                result.evidence["skipped_reason"], "schema_pre_v0_3_0"
            )

    def test_core_goal_field_present_blocker_fails_when_missing(self) -> None:
        """v0.2.0 schema without core_goal block → BLOCKER FAIL."""

        with tempfile.TemporaryDirectory() as td:
            schema = _bap_schema_min_v0_2_0()
            del schema["properties"]["basic_ability"]["properties"]["core_goal"]
            schema["properties"]["basic_ability"]["required"].remove("core_goal")
            templates = _write_only_bap_schema(Path(td), schema)
            result = sv.check_core_goal_field_present(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("core_goal block missing", result.message)

    def test_core_goal_minimum_pass_rate_must_be_const_1_0(self) -> None:
        """v0.2.0 schema with minimum_pass_rate.const != 1.0 → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            schema = _bap_schema_min_v0_2_0()
            schema["properties"]["basic_ability"]["properties"]["core_goal"][
                "properties"
            ]["minimum_pass_rate"]["const"] = 0.95
            templates = _write_only_bap_schema(Path(td), schema)
            result = sv.check_core_goal_field_present(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn("const != 1.0", result.message)

    def test_core_goal_required_subfield_missing_fails(self) -> None:
        """v0.2.0 schema with core_goal.required missing 'statement' → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            schema = _bap_schema_min_v0_2_0()
            schema["properties"]["basic_ability"]["properties"]["core_goal"][
                "required"
            ] = ["test_pack_path", "minimum_pass_rate"]
            templates = _write_only_bap_schema(Path(td), schema)
            result = sv.check_core_goal_field_present(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn(
                "core_goal.required missing 'statement'", result.message
            )

    def test_core_goal_not_in_basic_ability_required_fails(self) -> None:
        """v0.2.0 schema where basic_ability.required omits core_goal → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            schema = _bap_schema_min_v0_2_0()
            schema["properties"]["basic_ability"]["required"] = [
                k
                for k in schema["properties"]["basic_ability"]["required"]
                if k != "core_goal"
            ]
            templates = _write_only_bap_schema(Path(td), schema)
            result = sv.check_core_goal_field_present(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn(
                "basic_ability.required does not list core_goal",
                result.message,
            )


class CheckRoundKindTemplateValidTests(unittest.TestCase):
    """v0.3.0 §15 BLOCKER — ROUND_KIND_TEMPLATE_VALID."""

    def test_round_kind_template_valid_pass(self) -> None:
        """Real shipped templates declare round_kind from the §15.1.1 enum.

        Real templates were bumped to 0.3.0 by Stage 4 Wave 1a
        (additive v0.4.0 extensions: tier_transitions + promotion_state).
        Both 0.2.0 and 0.3.0 are acceptable for this BLOCKER — neither
        widens the round_kind enum past the §15.1.1 4-value set.
        """

        result = sv.check_round_kind_template_valid(REAL_TEMPLATES_DIR)
        self.assertEqual(result.id, "ROUND_KIND_TEMPLATE_VALID")
        self.assertEqual(result.severity, "BLOCKER")
        self.assertTrue(result.passed, msg=result.message)
        self.assertEqual(
            sorted(result.evidence["expected_enum"]),
            sorted(ROUND_KINDS),
        )
        # Real templates are at $schema_version 0.2.0 or 0.3.0 (Wave 1a bump).
        per_t = result.evidence["per_template"]
        self.assertIn(
            per_t["iteration_delta_report.template.yaml"]["schema_version"],
            {"0.2.0", "0.3.0"},
        )
        self.assertIn(
            per_t["next_action_plan.template.yaml"]["schema_version"],
            {"0.2.0", "0.3.0"},
        )

    def test_round_kind_template_valid_fail_on_unknown_kind(self) -> None:
        """A v0.2.0 template with round_kind=bogus must FAIL."""

        with tempfile.TemporaryDirectory() as td:
            iteration_delta = _round_kind_template_v0_2_0(
                "iteration_delta_report", value="bogus"
            )
            next_action = _round_kind_template_v0_2_0(
                "next_action_plan", value="code_change"
            )
            templates = _write_round_kind_templates(
                Path(td),
                iteration_delta=iteration_delta,
                next_action_plan=next_action,
            )
            result = sv.check_round_kind_template_valid(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("'bogus'", result.message)
            self.assertIn(
                "iteration_delta_report.template.yaml", result.message
            )

    def test_round_kind_template_valid_skips_legacy_template(self) -> None:
        """v0.1.0 template with no round_kind → PASS-as-SKIP per backward compat."""

        with tempfile.TemporaryDirectory() as td:
            iteration_delta = _round_kind_template_v0_1_0(
                "iteration_delta_report"
            )
            next_action = _round_kind_template_v0_1_0("next_action_plan")
            templates = _write_round_kind_templates(
                Path(td),
                iteration_delta=iteration_delta,
                next_action_plan=next_action,
            )
            result = sv.check_round_kind_template_valid(templates)
            self.assertTrue(result.passed, msg=result.message)
            per_t = result.evidence["per_template"]
            self.assertEqual(
                per_t["iteration_delta_report.template.yaml"]["skipped_reason"],
                "template_pre_v0_2_0",
            )
            self.assertEqual(
                per_t["next_action_plan.template.yaml"]["skipped_reason"],
                "template_pre_v0_2_0",
            )

    def test_round_kind_template_missing_field_fails(self) -> None:
        """v0.2.0 template that does NOT declare round_kind anywhere → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            iteration_delta = {
                "$schema_version": "0.2.0",
                "metadata": {"name": "iteration_delta_report"},
                "required_fields": ["round_id"],
                "schema": {"round_id": {"type": "string"}},
                "example_instance": {"round_id": "r0"},
            }
            next_action = _round_kind_template_v0_2_0(
                "next_action_plan", value="code_change"
            )
            templates = _write_round_kind_templates(
                Path(td),
                iteration_delta=iteration_delta,
                next_action_plan=next_action,
            )
            result = sv.check_round_kind_template_valid(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn("round_kind field missing", result.message)

    def test_round_kind_template_widened_enum_fails(self) -> None:
        """v0.2.0 template that widens schema.round_kind.enum → FAIL.

        Spec §15.1.1 freezes the enum at exactly 4 values; any widening
        would silently let agents pick a non-spec value through the
        template.
        """

        with tempfile.TemporaryDirectory() as td:
            iteration_delta = _round_kind_template_v0_2_0(
                "iteration_delta_report"
            )
            iteration_delta["schema"]["round_kind"]["enum"] = sorted(
                ROUND_KINDS
            ) + ["wishful_thinking"]
            next_action = _round_kind_template_v0_2_0(
                "next_action_plan", value="code_change"
            )
            templates = _write_round_kind_templates(
                Path(td),
                iteration_delta=iteration_delta,
                next_action_plan=next_action,
            )
            result = sv.check_round_kind_template_valid(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn("wishful_thinking", result.message)


class LegacyArtefactBackwardCompatTests(unittest.TestCase):
    """Round 1-13 Si-Chip + Round 1-10 chip-usage-helper artefacts must still load.

    These artefacts predate v0.3.0 and never had ``core_goal`` blocks; the
    validator must not regress on them. The check loads each YAML with
    ``yaml.safe_load`` and confirms (a) the BAP shape is intact, (b) no
    ``core_goal`` block is present (= legacy), and (c) the
    BAP_SCHEMA-style key set matches the v0.1.0 expected set (10 keys).
    """

    LEGACY_CHIP_USAGE_HELPER = (
        _REPO_ROOT
        / ".local/dogfood/2026-04-29/abilities/chip-usage-helper/round_10/basic_ability_profile.yaml"
    )
    LEGACY_SI_CHIP_ROUND_13 = (
        _REPO_ROOT / ".local/dogfood/2026-04-28/round_13/basic_ability_profile.yaml"
    )

    def _assert_legacy_profile(self, path: Path) -> None:
        """Common assertions for legacy v0.1.0 BAP profiles."""

        self.assertTrue(path.exists(), msg=f"legacy fixture missing: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        self.assertIn("basic_ability", data)
        bap = data["basic_ability"]
        self.assertIsInstance(bap, dict)
        # Legacy artefact: MUST NOT carry core_goal (predates v0.3.0).
        self.assertNotIn(
            "core_goal",
            bap,
            msg=(
                "legacy artefact unexpectedly grew a core_goal block; "
                "Stage 4 Wave 2a expects round_<= 13 / round_<= 10 to "
                "remain v0.1.0-shaped per §16.2 Si-Chip self-dogfood "
                "history retention"
            ),
        )
        # The 10 v0.1.0 BAP keys MUST all be present.
        v0_1_0_keys = sv.EXPECTED_BAP_KEYS_BY_SCHEMA["0.1.0"]
        observed = set(bap.keys())
        missing = v0_1_0_keys - observed
        self.assertFalse(
            missing,
            msg=f"legacy {path.name} missing v0.1.0 keys: {sorted(missing)}",
        )

    def test_legacy_chip_usage_helper_round_10_profile_still_validates(
        self,
    ) -> None:
        """chip-usage-helper Round 10 profile: yaml.safe_load + v0.1.0 shape OK."""

        self._assert_legacy_profile(self.LEGACY_CHIP_USAGE_HELPER)

    def test_legacy_si_chip_round_13_profile_still_validates(self) -> None:
        """Si-Chip Round 13 profile: yaml.safe_load + v0.1.0 shape OK."""

        self._assert_legacy_profile(self.LEGACY_SI_CHIP_ROUND_13)


class BapSchemaVersionAwareTests(unittest.TestCase):
    """Stage 4 Wave 2a: BAP_SCHEMA branches on schema's own $schema_version."""

    def test_real_v0_2_0_schema_yields_11_keys(self) -> None:
        """Real templates at $schema_version 0.2.0 or 0.3.0 → expect 11 keys.

        Stage 4 Wave 1a bumped the shipped schema to 0.3.0 (additive
        v0.4.0 sub-fields); the 0.3.0 top-level key set is IDENTICAL
        to 0.2.0 (11 keys including core_goal), per the version-keyed
        ``EXPECTED_BAP_KEYS_BY_SCHEMA`` dict.
        """

        result = sv.check_bap_schema(REAL_TEMPLATES_DIR)
        self.assertEqual(result.id, "BAP_SCHEMA")
        self.assertTrue(result.passed, msg=result.message)
        self.assertIn(result.evidence["schema_version"], {"0.2.0", "0.3.0"})
        self.assertIn("core_goal", result.evidence["actual"])
        self.assertEqual(len(result.evidence["actual"]), 11)

    def test_v0_1_0_schema_yields_10_keys(self) -> None:
        """v0.1.0 schema fixture → expects the 10-key set (no core_goal)."""

        with tempfile.TemporaryDirectory() as td:
            templates = _write_only_bap_schema(
                Path(td), _bap_schema_min_v0_1_0()
            )
            result = sv.check_bap_schema(templates)
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.evidence["schema_version"], "0.1.0")
            self.assertNotIn("core_goal", result.evidence["actual"])
            self.assertEqual(len(result.evidence["actual"]), 10)

    def test_unknown_schema_version_fails_with_explicit_message(self) -> None:
        """Unknown $schema_version → FAIL with explicit 'unknown' message."""

        with tempfile.TemporaryDirectory() as td:
            schema = _bap_schema_min_v0_1_0()
            schema["$schema_version"] = "9.9.9"
            templates = _write_only_bap_schema(Path(td), schema)
            result = sv.check_bap_schema(templates)
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn("unknown $schema_version", result.message)
            self.assertIn("9.9.9", result.message)


# ─────────────────────────────────────────────────────────────────────
# Stage 4 Wave 1b tests — v0.4.0-rc1 additive BLOCKERs 12 / 13 / 14
# ─────────────────────────────────────────────────────────────────────


SPEC_V0_4_0_RC1 = _REPO_ROOT / ".local/research/spec_v0.4.0-rc1.md"
SPEC_V0_4_0 = _REPO_ROOT / ".local/research/spec_v0.4.0.md"
SPEC_V0_4_2_RC1 = _REPO_ROOT / ".local/research/spec_v0.4.2-rc1.md"
SPEC_V0_4_3_RC1 = _REPO_ROOT / ".local/research/spec_v0.4.3-rc1.md"
SPEC_V0_4_4_RC1 = _REPO_ROOT / ".local/research/spec_v0.4.4-rc1.md"


def _write_round(
    root: Path,
    ability_id: str,
    round_id: str,
    round_kind: str,
    present_files: List[str],
    layout: str = "multi_ability",
) -> Path:
    """Helper: materialize a round directory with selected evidence files.

    ``layout``:
      * ``multi_ability`` → ``.local/dogfood/<DATE>/abilities/<id>/<round_id>/``
      * ``legacy``        → ``.local/dogfood/<DATE>/<round_id>/`` (Si-Chip self)

    ``present_files`` is a list of logical evidence names from the
    EXPECTED_EVIDENCE_FILES set; each is materialized as a minimal
    YAML stub ``{spec_section: dummy}``. ``next_action_plan.yaml`` is
    always materialized (with round_kind embedded) so the round-level
    ``_expected_evidence_count_for_round`` helper has something to
    parse.
    """

    date = "2026-04-30"
    if layout == "multi_ability":
        round_dir = root / ".local" / "dogfood" / date / "abilities" / ability_id / round_id
    else:
        round_dir = root / ".local" / "dogfood" / date / round_id
    round_dir.mkdir(parents=True, exist_ok=True)
    # next_action_plan.yaml always written with round_kind.
    nap = round_dir / "next_action_plan.yaml"
    nap.write_text(
        yaml.safe_dump({"round_id": round_id, "round_kind": round_kind}),
        encoding="utf-8",
    )
    for logical in present_files:
        if logical == "BasicAbilityProfile":
            fname = "basic_ability_profile.yaml"
        elif logical == "next_action_plan":
            continue  # already written
        else:
            fname = f"{logical}.yaml"
        (round_dir / fname).write_text(
            yaml.safe_dump(
                {"spec_section": "stub", "ability_id": ability_id}
            ),
            encoding="utf-8",
        )
    return round_dir


class V040Rc1AcceptanceTests(unittest.TestCase):
    """v0.4.0-rc1 spec acceptance: 15/15 BLOCKER PASS via subprocess.

    Wave 1d (v0.4.2-rc1, 2026-05-05) extended the BLOCKER set to 15
    by adding ``DESCRIPTION_CAP_1024``. Wave 1e (v0.4.4-rc1,
    2026-05-05) extends further to 16 by adding
    ``BODY_BUDGET_REQUIRES_REFERENCES_SPLIT``. The 15th and 16th
    SKIP-PASS against pre-v0.4.2 / pre-v0.4.4 specs (v0.4.0-rc1 /
    v0.4.0 / v0.3.0 / v0.2.0) per §13.6.4 grace period. All 14
    historical BLOCKERs must continue to PASS.
    """

    def test_v0_4_0_rc1_spec_loads_15_of_15_pass(self) -> None:
        """``--spec spec_v0.4.0-rc1.md --json`` exits 0 with 16/16 PASS.

        BLOCKER 15 ``DESCRIPTION_CAP_1024`` and BLOCKER 16
        ``BODY_BUDGET_REQUIRES_REFERENCES_SPLIT`` both SKIP-PASS here
        because the v0.4.0-rc1 spec lacks the §24 / §24.3 markers
        (pre-v0.4.2 / pre-v0.4.4 backward compat).
        """

        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools/spec_validator.py"),
                "--spec",
                str(SPEC_V0_4_0_RC1),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["verdict"], "PASS")
        self.assertEqual(len(payload["results"]), 16)
        passed_count = sum(1 for r in payload["results"] if r["passed"])
        self.assertEqual(passed_count, 16)
        ids = [r["id"] for r in payload["results"]]
        # All 3 v0.4.0 BLOCKERs must be present.
        self.assertIn("TOKEN_TIER_DECLARED_WHEN_REPORTED", ids)
        self.assertIn("REAL_DATA_FIXTURE_PROVENANCE", ids)
        self.assertIn("HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND", ids)
        # v0.4.2 BLOCKER must also be present (skip-pass on pre-v0.4.2 spec).
        self.assertIn("DESCRIPTION_CAP_1024", ids)
        # v0.4.4 BLOCKER must also be present (skip-pass on pre-v0.4.4 spec).
        self.assertIn("BODY_BUDGET_REQUIRES_REFERENCES_SPLIT", ids)
        desc_cap = next(
            r for r in payload["results"] if r["id"] == "DESCRIPTION_CAP_1024"
        )
        self.assertEqual(
            desc_cap["evidence"]["skipped_reason"],
            "spec_lacks_section_24_marker",
        )
        body_blocker = next(
            r
            for r in payload["results"]
            if r["id"] == "BODY_BUDGET_REQUIRES_REFERENCES_SPLIT"
        )
        self.assertEqual(
            body_blocker["evidence"]["skipped_reason"],
            "spec_lacks_section_24_3_marker",
        )
        # VALUE_VECTOR should report 8 expected axes under v0.4.0-rc1.
        value_vector = next(
            r for r in payload["results"] if r["id"] == "VALUE_VECTOR_AXES"
        )
        self.assertEqual(
            value_vector["evidence"]["spec_version"], "v0.4.0-rc1"
        )
        self.assertEqual(len(value_vector["evidence"]["expected"]), 8)
        self.assertIn("eager_token_delta", value_vector["evidence"]["expected"])

    def test_v0_4_0_rc1_strict_prose_count_passes(self) -> None:
        """``--strict-prose-count`` against v0.4.0-rc1 spec exits 0."""

        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools/spec_validator.py"),
                "--spec",
                str(SPEC_V0_4_0_RC1),
                "--strict-prose-count",
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["verdict"], "PASS")
        self.assertIn("v0.4.0-rc1", sv.SUPPORTED_SPEC_VERSIONS)
        self.assertEqual(sv.EXPECTED_R6_PROSE_BY_SPEC["v0.4.0-rc1"], 37)
        self.assertEqual(
            sv.EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.4.0-rc1"], 30
        )
        self.assertEqual(
            sv.EXPECTED_VALUE_VECTOR_PROSE_BY_SPEC["v0.4.0-rc1"], 8
        )

    def test_default_v0_2_0_mode_still_11_of_11_pass(self) -> None:
        """Default v0.2.0 spec still PASS.

        Back-compat floor: 11 historical BLOCKERs (9 + Wave 2a's 2
        additive) still PASS; Wave 1b's 3 additive BLOCKERs PASS-as-SKIP
        when no v0.4.0 artefacts exist; Wave 1d's DESCRIPTION_CAP_1024
        PASS-as-SKIP when the spec lacks §24 marker; Wave 1e's
        BODY_BUDGET_REQUIRES_REFERENCES_SPLIT PASS-as-SKIP when the
        spec lacks §24.3 marker → total 16/16.
        """

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
        # v0.4.4 Wave 1e widens to 16 but the 11 historical floor holds.
        self.assertEqual(len(payload["results"]), 16)
        for r in payload["results"]:
            with self.subTest(invariant=r["id"]):
                self.assertTrue(r["passed"], msg=r["message"])


class ValueVectorAxesVersionAwareTests(unittest.TestCase):
    """BLOCKER 5 VALUE_VECTOR_AXES is version-aware (7 ≤ v0.3.0; 8 @ v0.4.0+)."""

    def test_value_vector_8_axes_for_v0_4_0_rc1(self) -> None:
        """Spec v0.4.0-rc1 → expect 8 axes (eager_token_delta added)."""

        result = sv.check_value_vector_axes(
            REAL_TEMPLATES_DIR, spec_version="v0.4.0-rc1"
        )
        self.assertTrue(result.passed, msg=result.message)
        expected = set(result.evidence["expected"])
        self.assertEqual(len(expected), 8)
        self.assertIn("eager_token_delta", expected)

    def test_value_vector_7_axes_for_v0_3_0(self) -> None:
        """Spec v0.3.0 → expect 7 axes (no eager_token_delta); backward-compat."""

        result = sv.check_value_vector_axes(
            REAL_TEMPLATES_DIR, spec_version="v0.3.0"
        )
        self.assertTrue(result.passed, msg=result.message)
        expected = set(result.evidence["expected"])
        self.assertEqual(len(expected), 7)
        self.assertNotIn("eager_token_delta", expected)

    def test_value_vector_7_axes_for_v0_3_0_rc1(self) -> None:
        """Spec v0.3.0-rc1 preserves the 7-axis set (byte-identical to v0.3.0)."""

        result = sv.check_value_vector_axes(
            REAL_TEMPLATES_DIR, spec_version="v0.3.0-rc1"
        )
        self.assertTrue(result.passed, msg=result.message)
        self.assertEqual(len(result.evidence["expected"]), 7)

    def test_value_vector_default_spec_version_uses_7_axes_base(self) -> None:
        """When spec_version is None, default falls back to 7 axes (legacy)."""

        result = sv.check_value_vector_axes(REAL_TEMPLATES_DIR)
        self.assertTrue(result.passed, msg=result.message)
        self.assertEqual(len(result.evidence["expected"]), 7)


class R6KeysCompanionSuffixTests(unittest.TestCase):
    """R6_KEYS BLOCKER ignores §23 method-tag companion suffixes."""

    def test_companion_suffixes_filtered_from_count(self) -> None:
        """Companion fields like T1_pass_rate_method / _ci_low / _ci_high
        do not inflate the sub-metric count.
        """

        metrics = {
            "task_quality": {
                "properties": {
                    "T1_pass_rate": {},
                    "T1_pass_rate_method": {},
                    "T1_pass_rate_ci_low": {},
                    "T1_pass_rate_ci_high": {},
                    "T2_pass_k": {},
                    "T2_pass_k_method": {},
                    "T3_baseline_delta": {},
                    "T4_error_recovery_rate": {},
                }
            },
        }
        counts = sv._count_metric_keys(metrics)
        # Only 4 primary keys; 4 companions excluded.
        self.assertEqual(counts["task_quality"], 4)

    def test_companion_predicate_recognizes_all_suffixes(self) -> None:
        """_is_companion_key returns True for every declared suffix."""

        for key in (
            "T1_pass_rate_method",
            "C1_metadata_tokens_ci_low",
            "C1_metadata_tokens_ci_high",
            "U1_language_breakdown",
            "U4_state",
            "G1_provenance",
            "G1_sampled_at",
            "G1_sample_size_per_cell",
        ):
            with self.subTest(key=key):
                self.assertTrue(sv._is_companion_key(key))

    def test_companion_predicate_rejects_primary_keys(self) -> None:
        """Primary metric keys are NOT companions."""

        for key in (
            "T1_pass_rate",
            "C1_metadata_tokens",
            "U1_description_readability",
            "U4_time_to_first_success",
            "R3_trigger_F1",
            "R5_router_floor",
        ):
            with self.subTest(key=key):
                self.assertFalse(sv._is_companion_key(key))


class TokenTierDeclaredWhenReportedTests(unittest.TestCase):
    """BLOCKER 12 TOKEN_TIER_DECLARED_WHEN_REPORTED (v0.4.0 §18.1)."""

    def test_token_tier_blocker_skips_when_no_c7_c8_c9_present(self) -> None:
        """No metrics_report reports C7/C8/C9 → PASS-as-SKIP."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=[
                    "BasicAbilityProfile",
                    "metrics_report",
                ],
            )
            # Write a metrics_report.yaml with NO token-tier axes.
            (round_dir / "metrics_report.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "0.2.0",
                        "metrics": {
                            "task_quality": {"T1_pass_rate": 1.0},
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_token_tier_declared_when_reported(
                repo_root=root
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(
                result.evidence["skipped_reason"],
                "no_token_tier_axis_reported",
            )

    def test_token_tier_blocker_fails_when_c7_present_but_block_missing(
        self,
    ) -> None:
        """C7 reported without top-level token_tier block → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=["metrics_report"],
            )
            # Report C7 stuffed under context_economy (ad-hoc surface
            # we still detect), but DO NOT emit top-level token_tier.
            (round_dir / "metrics_report.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "0.3.0",
                        "metrics": {
                            "context_economy": {
                                "C7_eager_per_session": 365,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_token_tier_declared_when_reported(
                repo_root=root
            )
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn(
                "top-level `token_tier` block missing", result.message
            )

    def test_token_tier_blocker_fails_when_axis_missing_from_block(
        self,
    ) -> None:
        """token_tier block missing one of C7/C8/C9 → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=["metrics_report"],
            )
            (round_dir / "metrics_report.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "0.4.0-rc1",
                        "token_tier": {
                            "C7_eager_per_session": 365,
                            "C8_oncall_per_trigger": 7338,
                            # C9 intentionally omitted
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_token_tier_declared_when_reported(
                repo_root=root
            )
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn("C9_lazy_avg_per_load", result.message)

    def test_token_tier_blocker_passes_when_block_complete(self) -> None:
        """token_tier block with all 3 fields (null OK) → PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=["metrics_report"],
            )
            (round_dir / "metrics_report.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "0.4.0-rc1",
                        "token_tier": {
                            "C7_eager_per_session": None,
                            "C8_oncall_per_trigger": None,
                            "C9_lazy_avg_per_load": None,
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_token_tier_declared_when_reported(
                repo_root=root
            )
            self.assertTrue(result.passed, msg=result.message)


class RealDataFixtureProvenanceTests(unittest.TestCase):
    """BLOCKER 13 REAL_DATA_FIXTURE_PROVENANCE (v0.4.0 §19.3)."""

    def test_real_data_provenance_blocker_skips_when_no_samples_yaml(
        self,
    ) -> None:
        """No real_data_samples.yaml anywhere → PASS-as-SKIP."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # No .local/feedbacks or .agents/skills → no samples files.
            result = sv.check_real_data_fixture_provenance(repo_root=root)
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(
                result.evidence["skipped_reason"],
                "no_real_data_samples_files",
            )

    def test_real_data_provenance_blocker_skips_when_samples_empty(
        self,
    ) -> None:
        """real_data_samples.yaml with empty list → PASS-as-SKIP."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            feedback_dir = (
                root
                / ".local"
                / "feedbacks"
                / "feedbacks_while_using"
                / "test-ability"
            )
            feedback_dir.mkdir(parents=True)
            (feedback_dir / "real_data_samples.yaml").write_text(
                yaml.safe_dump(
                    {"ability_id": "test-ability", "real_data_samples": []}
                ),
                encoding="utf-8",
            )
            result = sv.check_real_data_fixture_provenance(repo_root=root)
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(
                result.evidence["skipped_reason"], "all_samples_empty"
            )

    def test_real_data_provenance_blocker_fails_when_samples_declared_but_no_fixture_citation(
        self,
    ) -> None:
        """real_data_samples declared but no test fixture cites provenance → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            feedback_dir = (
                root
                / ".local"
                / "feedbacks"
                / "feedbacks_while_using"
                / "test-ability"
            )
            feedback_dir.mkdir(parents=True)
            (feedback_dir / "real_data_samples.yaml").write_text(
                yaml.safe_dump(
                    {
                        "ability_id": "test-ability",
                        "real_data_samples": [
                            {
                                "id": "sample_1",
                                "endpoint": "/api/v1/health",
                                "captured_at": "2026-04-30T00:00:00Z",
                                "observer": "test@example.com",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            # Create test fixture root WITHOUT provenance citation.
            fixture_dir = (
                root
                / ".agents"
                / "skills"
                / "test-ability"
                / "tests"
                / "fixtures"
            )
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "some_fixture.json").write_text(
                '{"data": "mock"}', encoding="utf-8"
            )
            result = sv.check_real_data_fixture_provenance(repo_root=root)
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("test-ability", result.message)
            self.assertIn("real-data sample provenance", result.message)

    def test_real_data_provenance_blocker_passes_when_fixture_cites_provenance(
        self,
    ) -> None:
        """real_data_samples declared + fixture cites provenance → PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            feedback_dir = (
                root
                / ".local"
                / "feedbacks"
                / "feedbacks_while_using"
                / "test-ability"
            )
            feedback_dir.mkdir(parents=True)
            (feedback_dir / "real_data_samples.yaml").write_text(
                yaml.safe_dump(
                    {
                        "ability_id": "test-ability",
                        "real_data_samples": [
                            {
                                "id": "sample_1",
                                "endpoint": "/api/v1/health",
                                "captured_at": "2026-04-30T00:00:00Z",
                                "observer": "test@example.com",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            fixture_dir = (
                root
                / ".agents"
                / "skills"
                / "test-ability"
                / "tests"
                / "fixtures"
            )
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "some_fixture.ts").write_text(
                "// real-data sample provenance: 2026-04-30T00:00:00Z / test\n"
                "export const fixture = { data: 'mock' };\n",
                encoding="utf-8",
            )
            result = sv.check_real_data_fixture_provenance(repo_root=root)
            self.assertTrue(result.passed, msg=result.message)


class HealthSmokeDeclaredWhenLiveBackendTests(unittest.TestCase):
    """BLOCKER 14 HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND (v0.4.0 §21.2)."""

    def test_health_smoke_blocker_skips_when_no_live_backend(self) -> None:
        """No profile declares live_backend:true → PASS-as-SKIP."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=["BasicAbilityProfile"],
            )
            # Profile without live_backend declaration.
            (round_dir / "basic_ability_profile.yaml").write_text(
                yaml.safe_dump(
                    {
                        "basic_ability": {
                            "id": "test-ability",
                            "current_surface": {"type": "script"},
                            "packaging": {},
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_health_smoke_declared_when_live_backend(
                repo_root=root
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(
                result.evidence["skipped_reason"], "no_live_backend_declared"
            )

    def test_health_smoke_blocker_skips_when_no_profiles(self) -> None:
        """No basic_ability_profile.yaml anywhere → PASS-as-SKIP."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = sv.check_health_smoke_declared_when_live_backend(
                repo_root=root
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(
                result.evidence["skipped_reason"],
                "no_basic_ability_profiles",
            )

    def test_health_smoke_blocker_fails_when_live_backend_true_but_smoke_empty(
        self,
    ) -> None:
        """live_backend=true + empty smoke list → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=["BasicAbilityProfile"],
            )
            (round_dir / "basic_ability_profile.yaml").write_text(
                yaml.safe_dump(
                    {
                        "basic_ability": {
                            "id": "test-ability",
                            "current_surface": {
                                "type": "mcp",
                                "dependencies": {"live_backend": True},
                            },
                            "packaging": {
                                "health_smoke_check": [],
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_health_smoke_declared_when_live_backend(
                repo_root=root
            )
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("test-ability", str(result.evidence))

    def test_health_smoke_blocker_fails_when_live_backend_true_but_smoke_missing(
        self,
    ) -> None:
        """live_backend=true + missing smoke field → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=["BasicAbilityProfile"],
            )
            (round_dir / "basic_ability_profile.yaml").write_text(
                yaml.safe_dump(
                    {
                        "basic_ability": {
                            "id": "test-ability",
                            "current_surface": {
                                "type": "mcp",
                                "dependencies": {"live_backend": True},
                            },
                            "packaging": {},
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_health_smoke_declared_when_live_backend(
                repo_root=root
            )
            self.assertFalse(result.passed, msg=result.message)
            self.assertIn(
                "health_smoke_check is missing or empty", result.message
            )

    def test_health_smoke_blocker_passes_when_live_backend_true_and_smoke_populated(
        self,
    ) -> None:
        """live_backend=true + non-empty smoke list → PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=["BasicAbilityProfile"],
            )
            (round_dir / "basic_ability_profile.yaml").write_text(
                yaml.safe_dump(
                    {
                        "basic_ability": {
                            "id": "test-ability",
                            "current_surface": {
                                "type": "mcp",
                                "dependencies": {"live_backend": True},
                            },
                            "packaging": {
                                "health_smoke_check": [
                                    {
                                        "endpoint": "https://example.com/health",
                                        "expected_status": 200,
                                        "max_attempts": 3,
                                        "retry_delay_ms": 1000,
                                        "sentinel_field": "data.ok",
                                        "sentinel_value_predicate": "== true",
                                        "axis": "dependency",
                                        "description": "health probe",
                                    }
                                ],
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = sv.check_health_smoke_declared_when_live_backend(
                repo_root=root
            )
            self.assertTrue(result.passed, msg=result.message)


class DescriptionCap1024Tests(unittest.TestCase):
    """BLOCKER 15 DESCRIPTION_CAP_1024 (v0.4.2 §24.1).

    Stage 4 Wave 1d: spec_validator binds §24.1's "description ≤ 1024
    chars" (binding measurement = ``min(len(s), len(s.encode('utf-8')))``,
    CJK fairness) as a hard BLOCKER. Tests cover the happy path
    (in-bound), the FAIL path (over-bound), the CJK fairness path
    (chars ≤ 1024 < bytes), the SKIP-as-PASS path (no artefacts), and
    the run_all wiring (15/15 BLOCKERs against the v0.4.2-rc1 spec).
    """

    # Spec-text fixture used by the SKIP path. v0.4.2-rc1 carries a
    # §24 H2 header; we synthesise a minimal stub so the unit tests can
    # exercise the function without depending on the full spec file.
    _SPEC_WITH_S24 = (
        "# Si-Chip Spec v0.4.2-rc1\n\n## 24. Skill Hygiene Discipline\n\n"
        "### 24.1 Description Discipline\n\n"
        "BLOCKER 15: DESCRIPTION_CAP_1024.\n"
    )
    _SPEC_WITHOUT_S24 = (
        "# Si-Chip Spec v0.4.0\n\n## 23. Method-Tagged Metrics\n"
    )

    def _write_skill_md(
        self,
        root: Path,
        tree: str,
        name: str,
        description: str,
    ) -> Path:
        skill_dir = root / tree / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"version: 0.0.1-test\n"
            f"---\n\n"
            f"# {name}\n\nbody.\n",
            encoding="utf-8",
        )
        return skill_md

    def test_description_cap_1024_passes_when_within_bound(self) -> None:
        """1023-char description across all SKILL.md trees → PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            desc_1023 = "x" * 1023
            self._write_skill_md(
                root, ".agents/skills", "test-skill", desc_1023
            )
            self._write_skill_md(
                root, ".cursor/skills", "test-skill", desc_1023
            )
            self._write_skill_md(
                root, ".claude/skills", "test-skill", desc_1023
            )
            result = sv.check_description_cap_1024(
                repo_root=root, spec_text=self._SPEC_WITH_S24
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertEqual(result.id, "DESCRIPTION_CAP_1024")
            self.assertEqual(result.evidence["descriptions_measured"], 3)
            self.assertEqual(result.evidence["cap_chars"], 1024)
            for entry in result.evidence["per_artifact"]:
                if entry.get("kind") == "skill_md":
                    self.assertEqual(entry["binding_length"], 1023)
                    self.assertTrue(entry["pass"])

    def test_description_cap_1024_fails_at_1025_chars(self) -> None:
        """1025-char ASCII description → FAIL with binding-axis chars."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            desc_1025 = "y" * 1025
            self._write_skill_md(
                root, ".agents/skills", "long-skill", desc_1025
            )
            result = sv.check_description_cap_1024(
                repo_root=root, spec_text=self._SPEC_WITH_S24
            )
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("long-skill", result.message)
            self.assertIn("1025", result.message)
            # Binding axis should be chars (chars == bytes for pure ASCII;
            # the implementation reports whichever is smaller — for ASCII
            # the two are tied so chars wins by the chars<=bytes test).
            findings = result.evidence["findings"]
            self.assertEqual(len(findings), 1)
            self.assertIn("binding-axis=chars", findings[0])

    def test_description_cap_1024_handles_cjk_correctly(self) -> None:
        """600 CJK chars (~1800 bytes) → PASS via min(chars, bytes) = 600.

        §24.1 invariant #1 CJK fairness: 1 汉字 ≈ 3 UTF-8 bytes but
        1 character; binding length walks the SMALLER of the two so CJK
        descriptions are not penalised by UTF-8 byte expansion. 600
        chars × 3 bytes/char = 1800 bytes (over 1024 in raw bytes), but
        chars=600 ≤ 1024, so PASS.
        """

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cjk_600 = "汉" * 600
            self._write_skill_md(
                root, ".agents/skills", "cjk-skill", cjk_600
            )
            result = sv.check_description_cap_1024(
                repo_root=root, spec_text=self._SPEC_WITH_S24
            )
            self.assertTrue(result.passed, msg=result.message)
            entry = next(
                e for e in result.evidence["per_artifact"]
                if e.get("kind") == "skill_md"
            )
            self.assertEqual(entry["chars"], 600)
            self.assertEqual(entry["bytes"], 1800)
            self.assertEqual(entry["binding_length"], 600)
            self.assertTrue(entry["pass"])

    def test_description_cap_1024_skips_when_no_artefacts(self) -> None:
        """Empty repo (no SKILL.md, no BAP) → SKIP-as-PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = sv.check_description_cap_1024(
                repo_root=root, spec_text=self._SPEC_WITH_S24
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertEqual(
                result.evidence["skipped_reason"],
                "no_skill_md_or_bap_files",
            )
            # SKIP-as-PASS path should also fire when spec lacks §24,
            # regardless of whether artefacts exist.
            result_pre_v042 = sv.check_description_cap_1024(
                repo_root=root, spec_text=self._SPEC_WITHOUT_S24
            )
            self.assertTrue(result_pre_v042.passed)
            self.assertEqual(
                result_pre_v042.evidence["skipped_reason"],
                "spec_lacks_section_24_marker",
            )

    def test_description_cap_1024_wired_into_run_all_total_15(self) -> None:
        """run_all against v0.4.2-rc1 spec emits 16 results (Wave 1e widened
        from 15 to 16); BLOCKER 15 = DESCRIPTION_CAP_1024 PASS, BLOCKER 16 =
        BODY_BUDGET_REQUIRES_REFERENCES_SPLIT SKIP-PASS (pre-v0.4.4 spec).
        """

        if not SPEC_V0_4_2_RC1.exists():
            self.skipTest("spec_v0.4.2-rc1.md not present in this checkout")
        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools/spec_validator.py"),
                "--spec",
                str(SPEC_V0_4_2_RC1),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["verdict"], "PASS")
        self.assertEqual(len(payload["results"]), 16)
        ids = [r["id"] for r in payload["results"]]
        # BLOCKER 15 sits at index -2; BLOCKER 16 is the new tail.
        self.assertEqual(ids[-2], "DESCRIPTION_CAP_1024")
        self.assertEqual(ids[-1], "BODY_BUDGET_REQUIRES_REFERENCES_SPLIT")
        # All 16 BLOCKERs PASS against v0.4.2-rc1 spec (the §24 marker
        # is present so the cap actually runs against the real repo's
        # SKILL.md frontmatters and BAP descriptions; all measured
        # descriptions are ≤ 1024). BLOCKER 16 SKIP-PASSes because
        # v0.4.2-rc1 lacks the §24.3 marker (pre-v0.4.4 grace period).
        passed_count = sum(1 for r in payload["results"] if r["passed"])
        self.assertEqual(passed_count, 16)
        desc_cap = next(
            r for r in payload["results"] if r["id"] == "DESCRIPTION_CAP_1024"
        )
        # Real repo path: at least the 3 si-chip SKILL.md mirrors are
        # measured (and well under cap at ~165 chars each).
        self.assertGreaterEqual(
            desc_cap["evidence"]["descriptions_measured"], 3
        )
        self.assertEqual(desc_cap["evidence"]["cap_chars"], 1024)
        body_blocker = next(
            r
            for r in payload["results"]
            if r["id"] == "BODY_BUDGET_REQUIRES_REFERENCES_SPLIT"
        )
        self.assertEqual(
            body_blocker["evidence"]["skipped_reason"],
            "spec_lacks_section_24_3_marker",
        )


class BodyBudgetRequiresReferencesSplitTests(unittest.TestCase):
    """BLOCKER 16 BODY_BUDGET_REQUIRES_REFERENCES_SPLIT (v0.4.4 §24.3).

    Stage 4 Wave 1e: spec_validator binds §24.3.1's body-budget
    progressive-disclosure rule (when ``body_tokens > 5000`` the
    SKILL.md MUST cite ≥1 existing ``references/<file>.md``) as a
    hard BLOCKER. Tests cover the under-threshold PASS path (body
    ≤ 5000 with no cite required), the FAIL path (body > 5000 with
    no cite), the over-threshold PASS path (body > 5000 + valid
    existing cite), the FAIL path (cited reference file missing),
    the SKIP-as-PASS paths (no SKILL.md / pre-v0.4.4 spec), and the
    run_all wiring (16/16 BLOCKERs against the v0.4.4-rc1 spec).
    """

    # Spec-text fixture used by SKIP path 1. v0.4.4-rc1 carries a
    # §24.3 H3 header. Synthesise minimal stubs for both directions.
    _SPEC_WITH_S24_3 = (
        "# Si-Chip Spec v0.4.4-rc1\n\n## 24. Skill Hygiene Discipline\n\n"
        "### 24.1 Description Discipline\n\n"
        "### 24.3 Progressive Disclosure Discipline\n\n"
        "BLOCKER 16: BODY_BUDGET_REQUIRES_REFERENCES_SPLIT.\n"
    )
    _SPEC_WITHOUT_S24_3 = (
        "# Si-Chip Spec v0.4.3-rc1\n\n## 24. Skill Hygiene Discipline\n"
        "\n### 24.1 Description Discipline\n\n"
        "### 24.2 Standardized SKILL.md Sections\n"
    )

    def _write_skill_md(
        self,
        root: Path,
        tree: str,
        name: str,
        body_word_count: int,
        cited_reference_filename: Optional[str] = None,
        create_referenced_file: bool = False,
    ) -> Path:
        """Build a synthetic SKILL.md whose body has approx ``body_word_count`` words.

        The body is filler (``word ``-style sequence) so the
        word-split heuristic in ``count_tokens.py`` produces a count
        very close to ``body_word_count``. Optionally appends a
        ``references/<filename>.md`` cite line and (if
        ``create_referenced_file=True``) creates that file under the
        SKILL.md's sibling references/ directory.
        """

        skill_dir = root / tree / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skill_dir / "SKILL.md"
        # Build deterministic prose: ``word001 word002 ...`` keeps the
        # tiktoken / fallback counts stable + grep-friendly.
        body_words = [f"word{i:05d}" for i in range(body_word_count)]
        body_text = " ".join(body_words)
        cite_line = ""
        if cited_reference_filename:
            cite_line = (
                f"\n\nSee also: `references/{cited_reference_filename}` "
                "for the long material.\n"
            )
        contents = (
            "---\n"
            f"name: {name}\n"
            "description: Synthetic test skill for BLOCKER 16.\n"
            "version: 0.0.1-test\n"
            "---\n\n"
            f"# {name}\n\n"
            f"{body_text}\n"
            f"{cite_line}"
        )
        skill_md.write_text(contents, encoding="utf-8")

        if cited_reference_filename and create_referenced_file:
            refs_dir = skill_dir / "references"
            refs_dir.mkdir(parents=True, exist_ok=True)
            (refs_dir / cited_reference_filename).write_text(
                f"# {cited_reference_filename}\n\nLong material here.\n",
                encoding="utf-8",
            )
        return skill_md

    def test_body_budget_requires_references_split_passes_when_under_threshold(
        self,
    ) -> None:
        """4900-word body, no reference cited → SKIP-as-PASS (under threshold)."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_skill_md(
                root, ".agents/skills", "small-skill",
                body_word_count=4900,
                cited_reference_filename=None,
            )
            result = sv.check_body_budget_requires_references_split(
                repo_root=root, spec_text=self._SPEC_WITH_S24_3
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertEqual(
                result.id, "BODY_BUDGET_REQUIRES_REFERENCES_SPLIT"
            )
            # Either SKIP-as-PASS path 3 ("all under threshold") or a
            # generic empty-findings PASS — both are acceptable; what
            # matters is no FAIL.
            evidence = result.evidence
            self.assertIn(
                "body_budget_threshold", evidence
            )
            self.assertEqual(evidence["body_budget_threshold"], 5000)

    def test_body_budget_requires_references_split_fails_when_over_threshold_no_reference(
        self,
    ) -> None:
        """5500-word body, no reference cited → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_skill_md(
                root, ".agents/skills", "big-skill-no-refs",
                body_word_count=5500,
                cited_reference_filename=None,
            )
            result = sv.check_body_budget_requires_references_split(
                repo_root=root, spec_text=self._SPEC_WITH_S24_3
            )
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("big-skill-no-refs", result.message)
            self.assertIn("no references", result.message)
            findings = result.evidence["findings"]
            self.assertEqual(len(findings), 1)

    def test_body_budget_requires_references_split_passes_when_over_threshold_with_valid_reference(
        self,
    ) -> None:
        """5500-word body + cites real reference file → PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_skill_md(
                root, ".agents/skills", "big-skill-with-ref",
                body_word_count=5500,
                cited_reference_filename="long-material-r1-summary.md",
                create_referenced_file=True,
            )
            result = sv.check_body_budget_requires_references_split(
                repo_root=root, spec_text=self._SPEC_WITH_S24_3
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            # over-threshold count should be 1
            self.assertEqual(
                result.evidence["files_over_threshold"], 1
            )
            entry = next(
                e for e in result.evidence["per_artifact"]
                if e.get("over_threshold") is True
            )
            self.assertIn(
                "long-material-r1-summary.md",
                entry["references_existing"],
            )
            self.assertEqual(entry["references_missing"], [])
            self.assertTrue(entry["pass"])

    def test_body_budget_requires_references_split_fails_when_cited_reference_missing(
        self,
    ) -> None:
        """5500-word body + cites references/missing.md (file absent) → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_skill_md(
                root, ".agents/skills", "big-skill-broken-cite",
                body_word_count=5500,
                cited_reference_filename="missing.md",
                create_referenced_file=False,
            )
            result = sv.check_body_budget_requires_references_split(
                repo_root=root, spec_text=self._SPEC_WITH_S24_3
            )
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertIn("big-skill-broken-cite", result.message)
            self.assertIn("missing.md", result.message)
            findings = result.evidence["findings"]
            self.assertEqual(len(findings), 1)
            self.assertIn("none of those files exist", findings[0])

    def test_body_budget_requires_references_split_skips_when_no_skill_md_found(
        self,
    ) -> None:
        """Empty repo (no SKILL.md anywhere) → SKIP-as-PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = sv.check_body_budget_requires_references_split(
                repo_root=root, spec_text=self._SPEC_WITH_S24_3
            )
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.severity, "BLOCKER")
            self.assertEqual(
                result.evidence["skipped_reason"], "no_skill_md_files"
            )
            # Pre-v0.4.4 spec path also SKIPs as PASS regardless of artefacts.
            result_pre_v044 = sv.check_body_budget_requires_references_split(
                repo_root=root, spec_text=self._SPEC_WITHOUT_S24_3
            )
            self.assertTrue(result_pre_v044.passed)
            self.assertEqual(
                result_pre_v044.evidence["skipped_reason"],
                "spec_lacks_section_24_3_marker",
            )

    def test_body_budget_requires_references_split_wired_into_run_all_total_16(
        self,
    ) -> None:
        """run_all against v0.4.4-rc1 spec emits 16 results, last = BLOCKER 16."""

        if not SPEC_V0_4_4_RC1.exists():
            self.skipTest("spec_v0.4.4-rc1.md not present in this checkout")
        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools/spec_validator.py"),
                "--spec",
                str(SPEC_V0_4_4_RC1),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["verdict"], "PASS")
        self.assertEqual(len(payload["results"]), 16)
        ids = [r["id"] for r in payload["results"]]
        self.assertEqual(
            ids[-1], "BODY_BUDGET_REQUIRES_REFERENCES_SPLIT"
        )
        passed_count = sum(1 for r in payload["results"] if r["passed"])
        self.assertEqual(passed_count, 16)
        body_blocker = next(
            r
            for r in payload["results"]
            if r["id"] == "BODY_BUDGET_REQUIRES_REFERENCES_SPLIT"
        )
        # Real repo path: SKIP-as-PASS path 3 (Si-Chip's own SKILL.md
        # body is ~4929 tokens — under the 5000 threshold so no
        # SKILL.md crosses the graduated trigger).
        self.assertEqual(
            body_blocker["evidence"]["body_budget_threshold"], 5000
        )
        self.assertEqual(
            body_blocker["evidence"]["skipped_reason"],
            "all_skill_md_under_body_budget",
        )

    def test_body_budget_requires_references_split_backward_compat_legacy_specs_pass_15_blockers(
        self,
    ) -> None:
        """Legacy specs (v0.4.3, v0.4.2, v0.4.0) still PASS 15 historical BLOCKERs (BLOCKER 16 SKIP-PASSes)."""

        for spec_path in (
            SPEC_V0_4_3_RC1, SPEC_V0_4_2_RC1, SPEC_V0_4_0,
        ):
            if not spec_path.exists():
                continue
            proc = subprocess.run(
                [
                    sys.executable,
                    str(_REPO_ROOT / "tools/spec_validator.py"),
                    "--spec",
                    str(spec_path),
                    "--json",
                ],
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                proc.returncode, 0,
                msg=f"spec={spec_path.name} stderr={proc.stderr}",
            )
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertEqual(
                payload["verdict"], "PASS",
                msg=f"spec={spec_path.name}",
            )
            self.assertEqual(len(payload["results"]), 16)
            # BLOCKER 16 must be SKIP-as-PASS for pre-v0.4.4 specs.
            body_blocker = next(
                r
                for r in payload["results"]
                if r["id"] == "BODY_BUDGET_REQUIRES_REFERENCES_SPLIT"
            )
            self.assertTrue(body_blocker["passed"])
            self.assertEqual(
                body_blocker["evidence"]["skipped_reason"],
                "spec_lacks_section_24_3_marker",
                msg=f"spec={spec_path.name}",
            )


class EvidenceFilesPerRoundTests(unittest.TestCase):
    """Round-level evidence-count check (§8.2 + §20.4 round_kind-aware)."""

    def test_evidence_files_6_for_code_change_round_kind(self) -> None:
        """round_kind=code_change with 6 evidence files → PASS."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="code_change",
                present_files=[
                    "BasicAbilityProfile",
                    "metrics_report",
                    "router_floor_report",
                    "half_retire_decision",
                    "iteration_delta_report",
                ],
            )
            # 5 present_files + implicit next_action_plan = 6
            result = sv.check_evidence_count_for_round(round_dir)
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.evidence["expected_count"], 6)
            self.assertEqual(result.evidence["round_kind"], "code_change")
            self.assertEqual(len(result.evidence["present"]), 6)
            self.assertEqual(result.evidence["missing"], [])

    def test_evidence_files_7_for_ship_prep_round_kind(self) -> None:
        """round_kind=ship_prep with ONLY 6 files (missing ship_decision) → FAIL."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="ship_prep",
                present_files=[
                    "BasicAbilityProfile",
                    "metrics_report",
                    "router_floor_report",
                    "half_retire_decision",
                    "iteration_delta_report",
                ],
            )
            result = sv.check_evidence_count_for_round(round_dir)
            self.assertFalse(result.passed, msg=result.message)
            self.assertEqual(result.evidence["expected_count"], 7)
            self.assertEqual(result.evidence["round_kind"], "ship_prep")
            self.assertIn("ship_decision", result.evidence["missing"])

    def test_evidence_files_7_for_ship_prep_with_ship_decision_passes(
        self,
    ) -> None:
        """round_kind=ship_prep WITH ship_decision.yaml → PASS (7 files)."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            round_dir = _write_round(
                root,
                ability_id="test-ability",
                round_id="round_1",
                round_kind="ship_prep",
                present_files=[
                    "BasicAbilityProfile",
                    "metrics_report",
                    "router_floor_report",
                    "half_retire_decision",
                    "iteration_delta_report",
                    "ship_decision",
                ],
            )
            result = sv.check_evidence_count_for_round(round_dir)
            self.assertTrue(result.passed, msg=result.message)
            self.assertEqual(result.evidence["expected_count"], 7)
            self.assertEqual(result.evidence["round_kind"], "ship_prep")
            self.assertIn("ship_decision", result.evidence["present"])

    def test_evidence_files_defaults_to_6_when_next_action_plan_missing(
        self,
    ) -> None:
        """Missing next_action_plan.yaml → default to 6, emit WARNING."""

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Manually create a round directory WITHOUT next_action_plan.
            date = "2026-04-30"
            round_dir = (
                root
                / ".local"
                / "dogfood"
                / date
                / "abilities"
                / "test-ability"
                / "round_1"
            )
            round_dir.mkdir(parents=True)
            for name in (
                "basic_ability_profile",
                "metrics_report",
                "router_floor_report",
                "half_retire_decision",
                "iteration_delta_report",
            ):
                (round_dir / f"{name}.yaml").write_text(
                    yaml.safe_dump({"stub": True}), encoding="utf-8"
                )
            result = sv.check_evidence_count_for_round(round_dir)
            self.assertEqual(result.evidence["expected_count"], 6)
            self.assertIn(
                "next_action_plan.yaml missing",
                " ".join(result.evidence["warnings"]),
            )

    def test_evidence_files_skip_when_round_dir_missing(self) -> None:
        """Non-existent round directory → PASS-as-SKIP."""

        result = sv.check_evidence_count_for_round(
            Path("/nonexistent/round/dir")
        )
        self.assertTrue(result.passed)
        self.assertEqual(
            result.evidence["skipped_reason"], "round_dir_missing"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
