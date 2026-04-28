#!/usr/bin/env python3
"""Unit tests for ``aggregate_eval.py`` Round 3 R6/R7 hoist logic.

Workspace rule "Mandatory Verification": the R6/R7 hoist functions
landed in Round 3 (S5 task spec Edit B) and MUST carry tests. These
tests exercise:

* ``hoist_r6_routing_latency_p95`` — picks min(latency_p95_ms) across
  cells with ``pass_rate >= 0.80``; returns ``None`` when no cell
  passes; gracefully handles malformed cells.
* ``hoist_r7_routing_token_overhead`` — sums the per-row totals and
  divides; returns ``None`` when no row carries the new
  ``routing_stage_tokens_total`` / ``body_invocation_tokens_total``
  fields.
* ``build_report`` end-to-end smoke: when both data sources are
  present, the report's ``metrics.routing_cost.R6_routing_latency_p95``
  and ``R7_routing_token_overhead`` are non-null and within
  v1_baseline ceilings.

Run::

    python3 .agents/skills/si-chip/scripts/test_aggregate_eval.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import aggregate_eval as ae  # noqa: E402


# Simulated 8-cell router_floor_report based on Round 2's deterministic sweep.
ROUND_2_SWEEP = {
    "round_id": "round_2",
    "matrix_profile": "mvp",
    "cells": [
        {"model": "composer_2", "thinking_depth": "fast", "scenario_pack": "trigger_basic",
         "pass_rate": 0.86, "latency_p50_ms": 720, "latency_p95_ms": 1100},
        {"model": "composer_2", "thinking_depth": "fast", "scenario_pack": "near_miss",
         "pass_rate": 0.78, "latency_p50_ms": 740, "latency_p95_ms": 1180},
        {"model": "composer_2", "thinking_depth": "default", "scenario_pack": "trigger_basic",
         "pass_rate": 0.90, "latency_p50_ms": 940, "latency_p95_ms": 1480},
        {"model": "composer_2", "thinking_depth": "default", "scenario_pack": "near_miss",
         "pass_rate": 0.83, "latency_p50_ms": 980, "latency_p95_ms": 1560},
        {"model": "sonnet_shallow", "thinking_depth": "fast", "scenario_pack": "trigger_basic",
         "pass_rate": 0.83, "latency_p50_ms": 880, "latency_p95_ms": 1340},
        {"model": "sonnet_shallow", "thinking_depth": "fast", "scenario_pack": "near_miss",
         "pass_rate": 0.74, "latency_p50_ms": 900, "latency_p95_ms": 1400},
        {"model": "sonnet_shallow", "thinking_depth": "default", "scenario_pack": "trigger_basic",
         "pass_rate": 0.88, "latency_p50_ms": 1180, "latency_p95_ms": 1820},
        {"model": "sonnet_shallow", "thinking_depth": "default", "scenario_pack": "near_miss",
         "pass_rate": 0.81, "latency_p50_ms": 1230, "latency_p95_ms": 1900},
    ],
}


def _row(pass_rate: float = 0.85,
         pass_k_4: float = 0.5478,
         latency_p95_s: float = 1.469,
         latency_p50_s: float = 1.2,
         metadata_tokens: int = 78,
         per_invocation_footprint: int = 3598,
         trigger_F1: float = 0.8934,
         router_floor: str = "composer_2/fast",
         routing_stage_tokens_total: int = 78 * 20,
         body_invocation_tokens_total: int = 3520 * 20,
         step_count: int = 20,
         redundant_call_ratio: float = 0.0) -> dict:
    return {
        "pass_rate": pass_rate,
        "pass_k_4": pass_k_4,
        "latency_p95_s": latency_p95_s,
        "latency_p50_s": latency_p50_s,
        "metadata_tokens": metadata_tokens,
        "per_invocation_footprint": per_invocation_footprint,
        "trigger_F1": trigger_F1,
        "router_floor": router_floor,
        "routing_stage_tokens_total": routing_stage_tokens_total,
        "body_invocation_tokens_total": body_invocation_tokens_total,
        "step_count": step_count,
        "redundant_call_ratio": redundant_call_ratio,
    }


class HoistR6Tests(unittest.TestCase):

    def test_round_2_sweep_yields_1100ms(self) -> None:
        v, d = ae.hoist_r6_routing_latency_p95(ROUND_2_SWEEP)
        self.assertEqual(v, 1100)
        self.assertEqual(d["n_cells_total"], 8)
        self.assertEqual(d["n_cells_passing"], 6)
        self.assertEqual(d["chosen_cell"]["latency_p95_ms"], 1100)

    def test_v1_baseline_ceiling_2000ms(self) -> None:
        """Spec §4.1 routing_latency_p95 v1_baseline ceiling = 2000 ms."""

        v, _ = ae.hoist_r6_routing_latency_p95(ROUND_2_SWEEP)
        self.assertIsNotNone(v)
        self.assertLess(v, 2000)

    def test_no_passing_cells_returns_none(self) -> None:
        all_failing = {"cells": [
            {"pass_rate": 0.5, "latency_p95_ms": 100},
            {"pass_rate": 0.6, "latency_p95_ms": 200},
        ]}
        v, d = ae.hoist_r6_routing_latency_p95(all_failing)
        self.assertIsNone(v)
        self.assertIn("error", d)
        self.assertEqual(d["error"], "no passing cells")

    def test_empty_cells_returns_none(self) -> None:
        v, d = ae.hoist_r6_routing_latency_p95({"cells": []})
        self.assertIsNone(v)
        self.assertIn("error", d)

    def test_malformed_cells_skipped(self) -> None:
        rf = {"cells": [
            "not-a-dict",
            {"pass_rate": "nope", "latency_p95_ms": 999},
            {"pass_rate": 0.95, "latency_p95_ms": 500},
        ]}
        v, d = ae.hoist_r6_routing_latency_p95(rf)
        self.assertEqual(v, 500)
        self.assertEqual(d["n_cells_passing"], 1)


class HoistR7Tests(unittest.TestCase):

    def test_six_cases_yields_v1_baseline_pass(self) -> None:
        rows = [_row() for _ in range(6)]
        v, d = ae.hoist_r7_routing_token_overhead(rows)
        self.assertIsNotNone(v)
        self.assertEqual(d["n_rows_counted"], 6)
        # 78*20 / 3520*20 = 78/3520 ~= 0.02216
        self.assertAlmostEqual(v, 78 / 3520, places=6)
        self.assertLess(v, 0.20)

    def test_no_instrumentation_returns_none(self) -> None:
        rows = [{
            "pass_rate": 0.85,
            "pass_k_4": 0.5,
            "latency_p95_s": 1.0,
            "metadata_tokens": 78,
            "per_invocation_footprint": 3598,
            "trigger_F1": 0.9,
            "router_floor": "composer_2/fast",
        }]
        v, d = ae.hoist_r7_routing_token_overhead(rows)
        self.assertIsNone(v)
        self.assertIn("error", d)
        self.assertIn("remediation", d)

    def test_zero_body_total_returns_none(self) -> None:
        rows = [_row(routing_stage_tokens_total=10, body_invocation_tokens_total=0)]
        v, d = ae.hoist_r7_routing_token_overhead(rows)
        self.assertIsNone(v)
        self.assertIn("error", d)

    def test_skipped_rows_counted_in_derivation(self) -> None:
        rows = [
            _row(),
            {"pass_rate": 0.85, "pass_k_4": 0.5, "latency_p95_s": 1.0,
             "metadata_tokens": 78, "per_invocation_footprint": 3598,
             "trigger_F1": 0.9, "router_floor": "composer_2/fast"},
        ]
        v, d = ae.hoist_r7_routing_token_overhead(rows)
        self.assertIsNotNone(v)
        self.assertEqual(d["n_rows_counted"], 1)
        self.assertEqual(d["n_rows_skipped"], 1)


class BuildReportR6R7Integration(unittest.TestCase):
    """End-to-end smoke: build_report wires R6 + R7 hoist into routing_cost."""

    def test_with_router_floor_report_and_instrumented_rows(self) -> None:
        with_rows = [_row() for _ in range(6)]
        without_rows = [{
            "pass_rate": 0.5,
            "pass_k_4": 0.0625,
            "latency_p95_s": 0.95,
            "metadata_tokens": 0,
            "per_invocation_footprint": 1500,
            "trigger_F1": 0.0,
            "router_floor": "composer_2/fast",
        } for _ in range(6)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=78,
            router_floor_report=ROUND_2_SWEEP,
        )
        rc = report["metrics"]["routing_cost"]
        self.assertEqual(rc["R6_routing_latency_p95"], 1100)
        self.assertIsNotNone(rc["R7_routing_token_overhead"])
        self.assertLess(rc["R7_routing_token_overhead"], 0.20)
        self.assertAlmostEqual(rc["R3_trigger_F1"], 0.8934, places=4)
        self.assertEqual(rc["R5_router_floor"], "composer_2/fast")
        self.assertIn("r6_derivation", report["provenance"])
        self.assertIn("r7_derivation", report["provenance"])
        self.assertTrue(report["provenance"]["r6_derivation"]["loaded"])

    def test_without_router_floor_report_keeps_r6_null(self) -> None:
        with_rows = [_row()]
        without_rows = [_row(pass_rate=0.5, trigger_F1=0.0,
                             routing_stage_tokens_total=0,
                             body_invocation_tokens_total=1500 * 20)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=78,
            router_floor_report=None,
        )
        self.assertIsNone(report["metrics"]["routing_cost"]["R6_routing_latency_p95"])
        self.assertFalse(report["provenance"]["r6_derivation"]["loaded"])

    def test_28_keys_still_present(self) -> None:
        """Spec §3.2 frozen constraint #2: 28 keys must always be present."""

        with_rows = [_row()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=78,
            router_floor_report=ROUND_2_SWEEP,
        )
        metrics = report["metrics"]
        self.assertEqual(set(metrics.keys()), set(ae.METRIC_KEYS.keys()))
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(set(metrics[dim].keys()), set(keys),
                             msg=f"{dim} sub-metric keys diverged from schema")


# ─────────────────────────── Round 4 tests ───────────────────────────
# Workspace rule "Mandatory Verification": Round 4 (S5 task spec Edit C)
# added `hoist_l1_wall_clock_p50`, `hoist_l3_step_count`, and
# `hoist_l4_redundant_call_ratio`, plus `build_report` now populates
# D3/L1/L3/L4. These tests cover correctness, degenerate paths, and the
# spec §3.2 frozen 28-key invariant.


class HoistL1Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_l1_wall_clock_p50`."""

    def test_mean_of_p50s_across_six_cases(self) -> None:
        rows = [_row(latency_p50_s=1.0), _row(latency_p50_s=1.2),
                _row(latency_p50_s=1.4), _row(latency_p50_s=1.1),
                _row(latency_p50_s=1.3), _row(latency_p50_s=1.5)]
        v, d = ae.hoist_l1_wall_clock_p50(rows)
        self.assertIsNotNone(v)
        self.assertAlmostEqual(v, (1.0 + 1.2 + 1.4 + 1.1 + 1.3 + 1.5) / 6.0, places=6)
        self.assertEqual(d["n_rows_counted"], 6)
        self.assertEqual(d["n_rows_skipped"], 0)

    def test_no_instrumentation_returns_none(self) -> None:
        rows = [{
            "pass_rate": 0.85, "pass_k_4": 0.5, "latency_p95_s": 1.469,
            "metadata_tokens": 78, "per_invocation_footprint": 3598,
            "trigger_F1": 0.9, "router_floor": "composer_2/fast",
        }]
        v, d = ae.hoist_l1_wall_clock_p50(rows)
        self.assertIsNone(v)
        self.assertIn("error", d)
        self.assertIn("remediation", d)

    def test_l1_le_l2_sanity_invariant(self) -> None:
        rows = [_row(latency_p50_s=1.2, latency_p95_s=1.469) for _ in range(6)]
        v_l1, _ = ae.hoist_l1_wall_clock_p50(rows)
        v_l2 = sum(r["latency_p95_s"] for r in rows) / len(rows)
        self.assertIsNotNone(v_l1)
        self.assertLessEqual(v_l1, v_l2)

    def test_partial_instrumentation_counted(self) -> None:
        rows = [_row(latency_p50_s=1.2), {"pass_rate": 0.85, "pass_k_4": 0.5,
                                          "latency_p95_s": 1.0, "metadata_tokens": 78,
                                          "per_invocation_footprint": 3598,
                                          "trigger_F1": 0.9, "router_floor": "x"}]
        v, d = ae.hoist_l1_wall_clock_p50(rows)
        self.assertIsNotNone(v)
        self.assertEqual(d["n_rows_counted"], 1)
        self.assertEqual(d["n_rows_skipped"], 1)


class HoistL3Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_l3_step_count`."""

    def test_six_cases_with_twenty_steps_each(self) -> None:
        rows = [_row(step_count=20) for _ in range(6)]
        v, d = ae.hoist_l3_step_count(rows)
        self.assertEqual(v, 20)
        self.assertEqual(d["n_rows_counted"], 6)
        self.assertIsInstance(v, int)

    def test_no_instrumentation_returns_none(self) -> None:
        rows = [{
            "pass_rate": 0.85, "pass_k_4": 0.5, "latency_p95_s": 1.0,
            "metadata_tokens": 78, "per_invocation_footprint": 3598,
            "trigger_F1": 0.9, "router_floor": "composer_2/fast",
        }]
        v, d = ae.hoist_l3_step_count(rows)
        self.assertIsNone(v)
        self.assertIn("error", d)

    def test_returns_integer(self) -> None:
        rows = [_row(step_count=15), _row(step_count=20)]
        v, _ = ae.hoist_l3_step_count(rows)
        self.assertIsInstance(v, int)
        self.assertGreaterEqual(v, 1)


class HoistL4Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_l4_redundant_call_ratio`."""

    def test_degenerate_zero_across_six_cases(self) -> None:
        rows = [_row(redundant_call_ratio=0.0) for _ in range(6)]
        v, d = ae.hoist_l4_redundant_call_ratio(rows)
        self.assertEqual(v, 0.0)
        self.assertEqual(d["n_rows_counted"], 6)

    def test_non_zero_mean(self) -> None:
        rows = [_row(redundant_call_ratio=0.1), _row(redundant_call_ratio=0.3)]
        v, _ = ae.hoist_l4_redundant_call_ratio(rows)
        self.assertAlmostEqual(v, 0.2, places=6)

    def test_clamped_in_unit_interval(self) -> None:
        rows = [_row(redundant_call_ratio=0.9), _row(redundant_call_ratio=0.1)]
        v, _ = ae.hoist_l4_redundant_call_ratio(rows)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)

    def test_no_instrumentation_returns_none(self) -> None:
        rows = [{"pass_rate": 0.85, "pass_k_4": 0.5, "latency_p95_s": 1.0,
                 "metadata_tokens": 78, "per_invocation_footprint": 3598,
                 "trigger_F1": 0.9, "router_floor": "composer_2/fast"}]
        v, d = ae.hoist_l4_redundant_call_ratio(rows)
        self.assertIsNone(v)
        self.assertIn("error", d)


class BuildReportL1L3L4Integration(unittest.TestCase):
    """End-to-end smoke: build_report surfaces D3 L1/L3/L4 in metrics_report."""

    def test_full_instrumentation_populates_l1_l3_l4(self) -> None:
        with_rows = [_row(latency_p50_s=1.2, step_count=20, redundant_call_ratio=0.0)
                     for _ in range(6)]
        without_rows = [_row(latency_p50_s=0.8, step_count=20,
                             redundant_call_ratio=0.0, pass_rate=0.5,
                             trigger_F1=0.0) for _ in range(6)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
        )
        lp = report["metrics"]["latency_path"]
        self.assertAlmostEqual(lp["L1_wall_clock_p50"], 1.2, places=6)
        self.assertEqual(lp["L3_step_count"], 20)
        self.assertEqual(lp["L4_redundant_call_ratio"], 0.0)
        self.assertIsNotNone(lp["L2_wall_clock_p95"])
        # L1 must be <= L2 (the master plan acceptance criterion)
        self.assertLessEqual(lp["L1_wall_clock_p50"], lp["L2_wall_clock_p95"])

    def test_l1_l3_l4_derivation_recorded_in_provenance(self) -> None:
        with_rows = [_row() for _ in range(3)]
        without_rows = [_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(3)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
        )
        self.assertIn("l1_derivation", report["provenance"])
        self.assertIn("l3_derivation", report["provenance"])
        self.assertIn("l4_derivation", report["provenance"])

    def test_missing_instrumentation_keeps_l1_l3_l4_null(self) -> None:
        """Rows without the Round 4 fields keep L1/L3/L4 at None."""

        with_rows = [{
            "pass_rate": 0.85, "pass_k_4": 0.5478, "latency_p95_s": 1.469,
            "metadata_tokens": 82, "per_invocation_footprint": 3602,
            "trigger_F1": 0.8934, "router_floor": "composer_2/fast",
        }]
        without_rows = [{
            "pass_rate": 0.5, "pass_k_4": 0.0625, "latency_p95_s": 0.95,
            "metadata_tokens": 0, "per_invocation_footprint": 1500,
            "trigger_F1": 0.0, "router_floor": "n/a (no_ability)",
        }]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=None,
        )
        lp = report["metrics"]["latency_path"]
        self.assertIsNone(lp["L1_wall_clock_p50"])
        self.assertIsNone(lp["L3_step_count"])
        self.assertIsNone(lp["L4_redundant_call_ratio"])
        self.assertIsNotNone(lp["L2_wall_clock_p95"])

    def test_round_4_keeps_28_key_invariant(self) -> None:
        """Round 4 must not drop the spec §3.2 frozen 28-key invariant."""

        with_rows = [_row()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
        )
        metrics = report["metrics"]
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(set(metrics[dim].keys()), set(keys),
                             msg=f"{dim} sub-metric keys diverged from schema after Round 4")


# ─────────────────────────── Round 5 tests ───────────────────────────
# Workspace rule "Mandatory Verification": Round 5 (S5 task spec Edit B)
# added `hoist_u1_description_readability` and
# `hoist_u2_first_time_success_rate`, plus `build_report` now populates
# D5/U1 + D5/U2. These tests cover correctness, degenerate paths, and
# the spec §3.2 frozen 28-key invariant.


import tempfile  # noqa: E402


def _row_with_outcomes(
    expected_correct_pairs=None,
    **kwargs,
) -> dict:
    """Build an eval row with a deterministic ``prompt_outcomes`` list.

    ``expected_correct_pairs`` is a list of ``(expected, correct)`` tuples
    — the helper turns them into minimal prompt_outcomes dicts so the
    U2 hoist has something to work on.
    """

    row = _row(**kwargs)
    if expected_correct_pairs is None:
        # Default: 10 should_trigger (9 correct / 1 wrong) + 10 should_not (all correct)
        expected_correct_pairs = (
            [("trigger", True)] * 9
            + [("trigger", False)] * 1
            + [("no_trigger", True)] * 10
        )
    row["prompt_outcomes"] = [
        {
            "prompt_id": f"p{idx:02d}",
            "expected": expected,
            "correct": correct,
        }
        for idx, (expected, correct) in enumerate(expected_correct_pairs, start=1)
    ]
    return row


class HoistU1Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_u1_description_readability`."""

    def test_none_path_returns_none(self) -> None:
        v, d = ae.hoist_u1_description_readability(None)
        self.assertIsNone(v)
        self.assertIn("error", d)

    def test_real_skill_md_returns_in_range(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            "---\n"
            "name: demo\n"
            "description: A simple demo skill. Use it when testing.\n"
            "---\n"
            "body\n",
            encoding="utf-8",
        )
        v, d = ae.hoist_u1_description_readability(path)
        self.assertIsNotNone(v)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 24.0)
        self.assertIn("method", d)
        self.assertIn("words", d)
        self.assertGreater(d["words"], 0)

    def test_skill_md_without_description_returns_none(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            "---\nname: demo\n---\nbody\n",
            encoding="utf-8",
        )
        v, d = ae.hoist_u1_description_readability(path)
        self.assertIsNone(v)
        self.assertIn("error", d)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ae.hoist_u1_description_readability(Path("/does/not/exist/SKILL.md"))

    def test_deterministic_across_calls(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            "---\nname: x\ndescription: Persistent BasicAbility.\n---\nbody\n",
            encoding="utf-8",
        )
        v1, _ = ae.hoist_u1_description_readability(path)
        v2, _ = ae.hoist_u1_description_readability(path)
        self.assertEqual(v1, v2)


class HoistU2Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_u2_first_time_success_rate`."""

    def test_default_rows_yield_ninety_percent(self) -> None:
        rows = [_row_with_outcomes()]
        v, d = ae.hoist_u2_first_time_success_rate(rows)
        self.assertIsNotNone(v)
        self.assertAlmostEqual(v, 0.9, places=6)
        self.assertEqual(d["total_should_trigger"], 10)
        self.assertEqual(d["total_first_time_success"], 9)

    def test_six_identical_cases_preserve_rate(self) -> None:
        rows = [_row_with_outcomes() for _ in range(6)]
        v, d = ae.hoist_u2_first_time_success_rate(rows)
        self.assertAlmostEqual(v, 0.9, places=6)
        self.assertEqual(d["total_should_trigger"], 60)
        self.assertEqual(d["total_first_time_success"], 54)

    def test_all_correct_yields_one(self) -> None:
        rows = [_row_with_outcomes([("trigger", True)] * 10)]
        v, _ = ae.hoist_u2_first_time_success_rate(rows)
        self.assertEqual(v, 1.0)

    def test_all_wrong_yields_zero(self) -> None:
        rows = [_row_with_outcomes([("trigger", False)] * 10)]
        v, _ = ae.hoist_u2_first_time_success_rate(rows)
        self.assertEqual(v, 0.0)

    def test_no_prompt_outcomes_returns_none(self) -> None:
        rows = [_row()]  # _row() does NOT carry prompt_outcomes
        v, d = ae.hoist_u2_first_time_success_rate(rows)
        self.assertIsNone(v)
        self.assertIn("error", d)
        self.assertIn("remediation", d)

    def test_only_no_trigger_outcomes_returns_none(self) -> None:
        rows = [_row_with_outcomes([("no_trigger", True)] * 5)]
        v, d = ae.hoist_u2_first_time_success_rate(rows)
        self.assertIsNone(v)
        self.assertEqual(d["error"], "no should_trigger prompt_outcomes in with-ability rows")

    def test_range_stays_in_unit_interval(self) -> None:
        for pairs in (
            [("trigger", True)] * 10,
            [("trigger", True)] * 5 + [("trigger", False)] * 5,
            [("trigger", False)] * 10,
        ):
            with self.subTest(pairs=pairs):
                v, _ = ae.hoist_u2_first_time_success_rate([_row_with_outcomes(pairs)])
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)


class BuildReportU1U2Integration(unittest.TestCase):
    """End-to-end smoke: build_report surfaces D5 U1/U2 in metrics_report."""

    def _make_skill_md(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: si-chip\ndescription: {description}\n---\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_full_instrumentation_populates_u1_and_u2(self) -> None:
        skill_md = self._make_skill_md(
            "Persistent BasicAbility optimization factory."
        )
        with_rows = [_row_with_outcomes() for _ in range(6)]
        without_rows = [_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(6)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
        )
        uc = report["metrics"]["usage_cost"]
        self.assertIsNotNone(uc["U1_description_readability"])
        self.assertGreaterEqual(uc["U1_description_readability"], 0.0)
        self.assertLessEqual(uc["U1_description_readability"], 24.0)
        self.assertIsNotNone(uc["U2_first_time_success_rate"])
        self.assertAlmostEqual(uc["U2_first_time_success_rate"], 0.9, places=6)
        # U3/U4 stay null: Round 6 work.
        self.assertIsNone(uc["U3_setup_steps_count"])
        self.assertIsNone(uc["U4_time_to_first_success"])
        # Provenance carries the derivation records.
        self.assertIn("u1_derivation", report["provenance"])
        self.assertIn("u2_derivation", report["provenance"])

    def test_missing_skill_md_keeps_u1_null(self) -> None:
        with_rows = [_row_with_outcomes() for _ in range(3)]
        without_rows = [_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(3)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=None,
        )
        uc = report["metrics"]["usage_cost"]
        self.assertIsNone(uc["U1_description_readability"])
        # U2 still works because it comes from prompt_outcomes.
        self.assertIsNotNone(uc["U2_first_time_success_rate"])

    def test_missing_prompt_outcomes_keeps_u2_null(self) -> None:
        skill_md = self._make_skill_md("A simple description.")
        with_rows = [_row() for _ in range(3)]
        without_rows = [_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(3)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
        )
        uc = report["metrics"]["usage_cost"]
        self.assertIsNotNone(uc["U1_description_readability"])
        self.assertIsNone(uc["U2_first_time_success_rate"])

    def test_round_5_keeps_28_key_invariant(self) -> None:
        """Round 5 must not drop the spec §3.2 frozen 28-key invariant."""

        skill_md = self._make_skill_md("Demo.")
        with_rows = [_row_with_outcomes()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
        )
        metrics = report["metrics"]
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(set(metrics[dim].keys()), set(keys),
                             msg=f"{dim} sub-metric keys diverged from schema after Round 5")


# ─────────────────────────── Round 6 tests ───────────────────────────
# Workspace rule "Mandatory Verification": Round 6 (S5 task spec Edit C)
# added `hoist_u3_setup_steps_count` and `hoist_u4_time_to_first_success`,
# plus `build_report` now accepts an `install_telemetry` payload and
# populates D5/U3 + D5/U4. These tests cover correctness, degenerate
# paths, and the spec §3.2 frozen 28-key invariant after Round 6.


def _install_telemetry_payload(
    u3: Optional[int] = 1,
    u4: Optional[float] = 0.42,
    dry_run: bool = True,
) -> dict:
    """Build a minimal install_telemetry payload in the shape the aggregator expects."""

    return {
        "install_script_path": "/tmp/install.sh",
        "u3_setup_steps_count": u3,
        "u4_time_to_first_success_s": u4,
        "dry_run": dry_run,
        "derivation": {
            "u3_method": "count_setup_steps via self-reported header",
            "u4_method": "wall_clock seconds from bash to first OK line",
            "u4_timeout_s": 60.0,
            "script_version": "0.1.0",
        },
    }


class HoistU3Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_u3_setup_steps_count`."""

    def test_happy_path_single_step(self) -> None:
        v, d = ae.hoist_u3_setup_steps_count(_install_telemetry_payload(u3=1))
        self.assertEqual(v, 1)
        self.assertIn("method", d)
        self.assertIn("telemetry_derivation", d)

    def test_happy_path_zero_steps(self) -> None:
        v, _ = ae.hoist_u3_setup_steps_count(_install_telemetry_payload(u3=0))
        self.assertEqual(v, 0)

    def test_happy_path_two_steps(self) -> None:
        v, _ = ae.hoist_u3_setup_steps_count(_install_telemetry_payload(u3=2))
        self.assertEqual(v, 2)

    def test_none_payload_returns_none(self) -> None:
        v, d = ae.hoist_u3_setup_steps_count(None)
        self.assertIsNone(v)
        self.assertEqual(d["error"], "no install_telemetry provided")

    def test_missing_u3_key_returns_none(self) -> None:
        payload = _install_telemetry_payload()
        del payload["u3_setup_steps_count"]
        v, d = ae.hoist_u3_setup_steps_count(payload)
        self.assertIsNone(v)
        self.assertIn("missing u3_setup_steps_count", d["error"])
        self.assertIn("remediation", d)

    def test_u3_none_returns_none(self) -> None:
        v, d = ae.hoist_u3_setup_steps_count(_install_telemetry_payload(u3=None))
        self.assertIsNone(v)
        self.assertIn("missing u3_setup_steps_count", d["error"])

    def test_u3_negative_returns_none(self) -> None:
        v, d = ae.hoist_u3_setup_steps_count(_install_telemetry_payload(u3=-1))
        self.assertIsNone(v)
        self.assertIn(">= 0", d["error"])

    def test_u3_non_int_returns_none(self) -> None:
        payload = _install_telemetry_payload()
        payload["u3_setup_steps_count"] = "not an int"
        v, d = ae.hoist_u3_setup_steps_count(payload)
        self.assertIsNone(v)
        self.assertIn("not an int", d["error"])

    def test_non_dict_payload_returns_none(self) -> None:
        v, d = ae.hoist_u3_setup_steps_count("not a dict")  # type: ignore[arg-type]
        self.assertIsNone(v)
        self.assertIn("not a dict", d["error"])


class HoistU4Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_u4_time_to_first_success`."""

    def test_happy_path_dry_run(self) -> None:
        v, d = ae.hoist_u4_time_to_first_success(_install_telemetry_payload(u4=0.42))
        self.assertAlmostEqual(v, 0.42, places=3)
        self.assertTrue(d["dry_run"])

    def test_happy_path_non_dry_run(self) -> None:
        payload = _install_telemetry_payload(u4=2.5, dry_run=False)
        v, d = ae.hoist_u4_time_to_first_success(payload)
        self.assertAlmostEqual(v, 2.5, places=3)
        self.assertFalse(d["dry_run"])

    def test_v1_baseline_sanity_ceiling(self) -> None:
        """U4 must be <= 60 s for the sanity ceiling per master plan."""

        v, _ = ae.hoist_u4_time_to_first_success(_install_telemetry_payload(u4=0.42))
        self.assertLessEqual(v, 60.0)

    def test_none_payload_returns_none(self) -> None:
        v, d = ae.hoist_u4_time_to_first_success(None)
        self.assertIsNone(v)
        self.assertIn("no install_telemetry", d["error"])

    def test_u4_null_returns_none(self) -> None:
        """U4=None in telemetry (offline/failure path) stays None — not 0.0."""

        v, d = ae.hoist_u4_time_to_first_success(_install_telemetry_payload(u4=None))
        self.assertIsNone(v)
        self.assertIn("missing u4_time_to_first_success_s", d["error"])

    def test_u4_negative_returns_none(self) -> None:
        v, d = ae.hoist_u4_time_to_first_success(_install_telemetry_payload(u4=-1.0))
        self.assertIsNone(v)
        self.assertIn(">= 0", d["error"])

    def test_u4_non_float_returns_none(self) -> None:
        payload = _install_telemetry_payload()
        payload["u4_time_to_first_success_s"] = "not a number"
        v, d = ae.hoist_u4_time_to_first_success(payload)
        self.assertIsNone(v)
        self.assertIn("not a float", d["error"])

    def test_non_dict_payload_returns_none(self) -> None:
        v, d = ae.hoist_u4_time_to_first_success(42)  # type: ignore[arg-type]
        self.assertIsNone(v)
        self.assertIn("not a dict", d["error"])


class BuildReportU3U4Integration(unittest.TestCase):
    """End-to-end smoke: build_report surfaces D5 U3/U4 in metrics_report."""

    def _make_skill_md(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: si-chip\ndescription: {description}\n---\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_full_instrumentation_populates_u3_and_u4(self) -> None:
        skill_md = self._make_skill_md("Persistent BasicAbility optimization factory.")
        with_rows = [_row_with_outcomes() for _ in range(6)]
        without_rows = [_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(6)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(u3=1, u4=0.42),
        )
        uc = report["metrics"]["usage_cost"]
        self.assertEqual(uc["U3_setup_steps_count"], 1)
        self.assertAlmostEqual(uc["U4_time_to_first_success"], 0.42, places=3)
        # U1/U2 still populated.
        self.assertIsNotNone(uc["U1_description_readability"])
        self.assertIsNotNone(uc["U2_first_time_success_rate"])
        # Derivations recorded.
        self.assertIn("u3_derivation", report["provenance"])
        self.assertIn("u4_derivation", report["provenance"])

    def test_missing_install_telemetry_keeps_u3_u4_null(self) -> None:
        """Round 5 path (no --install-telemetry supplied) keeps U3+U4 null."""

        skill_md = self._make_skill_md("Demo.")
        with_rows = [_row_with_outcomes()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=None,
        )
        uc = report["metrics"]["usage_cost"]
        self.assertIsNone(uc["U3_setup_steps_count"])
        self.assertIsNone(uc["U4_time_to_first_success"])

    def test_partial_telemetry_u4_null_preserved(self) -> None:
        """U4=null (installer failed/timed out) preserves null, not 0.0."""

        skill_md = self._make_skill_md("Demo.")
        with_rows = [_row_with_outcomes()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(u3=1, u4=None),
        )
        uc = report["metrics"]["usage_cost"]
        self.assertEqual(uc["U3_setup_steps_count"], 1)
        self.assertIsNone(uc["U4_time_to_first_success"])

    def test_round_6_keeps_28_key_invariant(self) -> None:
        """Round 6 must not drop the spec §3.2 frozen 28-key invariant."""

        skill_md = self._make_skill_md("Demo.")
        with_rows = [_row_with_outcomes()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
        )
        metrics = report["metrics"]
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(set(metrics[dim].keys()), set(keys),
                             msg=f"{dim} sub-metric keys diverged from schema after Round 6")

    def test_round_6_full_d5_coverage_populated(self) -> None:
        """With U1+U2+U3+U4 all populated, D5 reaches 4/4 sub-metric coverage."""

        skill_md = self._make_skill_md("Demo.")
        with_rows = [_row_with_outcomes()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(u3=1, u4=0.42),
        )
        uc = report["metrics"]["usage_cost"]
        measured = [k for k, v in uc.items() if v is not None]
        # All 4 D5 sub-metrics measured simultaneously in Round 6 path.
        self.assertEqual(set(measured), {
            "U1_description_readability",
            "U2_first_time_success_rate",
            "U3_setup_steps_count",
            "U4_time_to_first_success",
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
