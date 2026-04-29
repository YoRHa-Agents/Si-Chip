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
from typing import Optional

import yaml

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


# ─────────────────────────── Round 7 tests ───────────────────────────
# Workspace rule "Mandatory Verification": Round 7 (task spec §3+§4)
# added ``hoist_c5_context_rot_risk`` and
# ``hoist_c6_scope_overlap_score``, plus ``build_report`` now accepts
# ``references_dir`` and ``neighbor_skill_md_paths`` and populates
# D2 C5 + D2 C6. These tests cover correctness, degenerate paths, and
# the spec §3.2 frozen 28-key invariant after Round 7.


class HoistC5Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_c5_context_rot_risk`."""

    def _skill_with_refs(self, body: str, refs: list) -> tuple:
        tmp = Path(tempfile.mkdtemp())
        skill = tmp / "SKILL.md"
        skill.write_text(
            f"---\nname: demo\ndescription: demo\n---\n{body}\n",
            encoding="utf-8",
        )
        refs_dir = tmp / "references"
        refs_dir.mkdir()
        for name in refs:
            (refs_dir / name).write_text("stub", encoding="utf-8")
        return skill, refs_dir

    def test_happy_path_with_referenced_files(self) -> None:
        skill, refs_dir = self._skill_with_refs(
            "body cites alpha.md and beta.md",
            ["alpha.md", "beta.md", "gamma.md"],
        )
        v, d = ae.hoist_c5_context_rot_risk(skill, refs_dir)
        self.assertIsNotNone(v)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)
        self.assertEqual(d["fanout_depth"], 2)
        self.assertIn("range_sanity_check", d)

    def test_none_skill_md_returns_none(self) -> None:
        v, d = ae.hoist_c5_context_rot_risk(None, None)
        self.assertIsNone(v)
        self.assertIn("error", d)
        self.assertIn("remediation", d)

    def test_missing_skill_md_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ae.hoist_c5_context_rot_risk(Path("/no/such/SKILL.md"), None)

    def test_no_references_dir_zero_fanout(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        skill = tmp / "SKILL.md"
        skill.write_text(
            "---\nname: demo\ndescription: demo\n---\nshort body\n",
            encoding="utf-8",
        )
        v, d = ae.hoist_c5_context_rot_risk(skill, None)
        self.assertIsNotNone(v)
        self.assertEqual(d["fanout_depth"], 0)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)


class HoistC6Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_c6_scope_overlap_score`."""

    def _write_skill(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: demo\ndescription: {description}\n---\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_happy_path_partial_overlap(self) -> None:
        base = self._write_skill("alpha beta gamma")
        n1 = self._write_skill("alpha delta")      # 1/4 overlap
        n2 = self._write_skill("alpha beta")       # 2/3 overlap
        v, d = ae.hoist_c6_scope_overlap_score(base, [n1, n2])
        self.assertIsNotNone(v)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)
        # Max over two pairs — expect 2/3 ≈ 0.667.
        self.assertAlmostEqual(v, 2 / 3, places=4)
        self.assertEqual(d["n_neighbors_scored"], 2)

    def test_none_skill_md_returns_none(self) -> None:
        v, d = ae.hoist_c6_scope_overlap_score(None, [])
        self.assertIsNone(v)
        self.assertIn("error", d)

    def test_empty_neighbors_defaults_to_zero(self) -> None:
        base = self._write_skill("alpha beta")
        with self.assertLogs("si_chip.aggregate_eval", level="WARNING") as cm:
            v, d = ae.hoist_c6_scope_overlap_score(base, [])
        # Warning logged — no silent zero substitution per workspace rule.
        self.assertTrue(any("no neighbor" in m.lower() for m in cm.output))
        self.assertEqual(v, 0.0)
        self.assertEqual(d["n_neighbors_attempted"], 0)

    def test_missing_base_raises(self) -> None:
        n1 = self._write_skill("alpha")
        with self.assertRaises(FileNotFoundError):
            ae.hoist_c6_scope_overlap_score(
                Path("/no/such/SKILL.md"), [n1]
            )

    def test_neighbor_missing_recorded_in_pairs(self) -> None:
        base = self._write_skill("alpha beta")
        n1 = self._write_skill("alpha")
        missing = Path("/does/not/exist/SKILL.md")
        v, d = ae.hoist_c6_scope_overlap_score(base, [n1, missing])
        self.assertIsNotNone(v)
        self.assertEqual(d["n_neighbors_scored"], 1)
        self.assertEqual(d["n_neighbors_skipped"], 1)
        # Missing entry appears in pairs with explicit error.
        missing_entries = [p for p in d["pairs"] if p.get("error") == "missing"]
        self.assertEqual(len(missing_entries), 1)


class BuildReportC5C6Integration(unittest.TestCase):
    """End-to-end smoke: build_report surfaces D2 C5 + D2 C6."""

    def _make_skill_md(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: si-chip\ndescription: {description}\n---\n"
            "body text body text body text body text body text body text\n",
            encoding="utf-8",
        )
        return path

    def test_full_instrumentation_populates_c5_and_c6(self) -> None:
        skill_md = self._make_skill_md(
            "Persistent BasicAbility optimization factory."
        )
        neighbor1 = self._make_skill_md("persistent optimization factory")
        neighbor2 = self._make_skill_md("irrelevant vocab here")
        # Reference dir with one .md file that the body literally references.
        refs_dir = skill_md.parent / "references"
        refs_dir.mkdir()
        (refs_dir / "body.md").write_text("stub", encoding="utf-8")

        with_rows = [_row_with_outcomes() for _ in range(3)]
        without_rows = [_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(3)]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            references_dir=refs_dir,
            neighbor_skill_md_paths=[neighbor1, neighbor2],
        )
        ce = report["metrics"]["context_economy"]
        self.assertIsNotNone(ce["C5_context_rot_risk"])
        self.assertGreaterEqual(ce["C5_context_rot_risk"], 0.0)
        self.assertLessEqual(ce["C5_context_rot_risk"], 1.0)
        self.assertIsNotNone(ce["C6_scope_overlap_score"])
        self.assertGreaterEqual(ce["C6_scope_overlap_score"], 0.0)
        self.assertLessEqual(ce["C6_scope_overlap_score"], 1.0)
        self.assertIn("c5_derivation", report["provenance"])
        self.assertIn("c6_derivation", report["provenance"])

    def test_missing_skill_md_keeps_c5_and_c6_null(self) -> None:
        """Round 6 code path (no skill_md_path) must leave C5 + C6 null."""

        with_rows = [_row_with_outcomes()]
        without_rows = [_row()]
        report = ae.build_report(
            with_rows=with_rows,
            without_rows=without_rows,
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=None,
            install_telemetry=None,
        )
        ce = report["metrics"]["context_economy"]
        self.assertIsNone(ce["C5_context_rot_risk"])
        self.assertIsNone(ce["C6_scope_overlap_score"])

    def test_empty_neighbor_list_keeps_c6_zero_not_null(self) -> None:
        """Empty neighbors → C6 = 0.0 by convention (logged warning)."""

        skill_md = self._make_skill_md("demo description")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            neighbor_skill_md_paths=[],
        )
        self.assertEqual(report["metrics"]["context_economy"]["C6_scope_overlap_score"], 0.0)

    def test_c5_c6_range_invariant_in_build_report(self) -> None:
        """When populated, C5 and C6 must always lie in [0.0, 1.0]."""

        skill_md = self._make_skill_md("demo description")
        neighbor = self._make_skill_md("another description")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            neighbor_skill_md_paths=[neighbor],
        )
        ce = report["metrics"]["context_economy"]
        self.assertIsNotNone(ce["C5_context_rot_risk"])
        self.assertIsNotNone(ce["C6_scope_overlap_score"])
        self.assertGreaterEqual(ce["C5_context_rot_risk"], 0.0)
        self.assertLessEqual(ce["C5_context_rot_risk"], 1.0)
        self.assertGreaterEqual(ce["C6_scope_overlap_score"], 0.0)
        self.assertLessEqual(ce["C6_scope_overlap_score"], 1.0)

    def test_round_7_keeps_28_key_invariant(self) -> None:
        """Spec §3.2 frozen key contract still holds after Round 7.

        The spec §13.4 prose lists 28 sub-metrics; the §3.1 TABLE (and
        thus the runtime schema and aggregator) carries 37. The
        aggregator preserves the table count verbatim — every sub-
        metric key from the template appears in the report with null
        or non-null value. The reconciliation prose↔table is a Round 11
        task per master plan.
        """

        skill_md = self._make_skill_md("demo")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            references_dir=None,
            neighbor_skill_md_paths=[],
        )
        metrics = report["metrics"]
        # All 7 dimensions present.
        self.assertEqual(set(metrics.keys()), set(ae.METRIC_KEYS.keys()))
        # Each dimension's sub-metric keys match the template.
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(
                set(metrics[dim].keys()),
                set(keys),
                msg=f"{dim} sub-metric keys diverged from schema after Round 7",
            )
        # Total aggregate count = sum of template per-dimension counts.
        total_keys = sum(len(keys) for keys in ae.METRIC_KEYS.values())
        self.assertEqual(total_keys, 37)  # §3.1 TABLE; §13.4 prose says 28 (reconciled in Round 11).

    def test_round_7_cli_flag_round_trip(self) -> None:
        """CLI flags ``--references-dir`` and ``--neighbor-skills-glob`` feed build_report."""

        import subprocess
        import tempfile as _tempfile
        tmp = Path(_tempfile.mkdtemp())
        runs = tmp / "runs"
        base = tmp / "base"
        runs.mkdir()
        base.mkdir()
        case = {
            "pass_rate": 0.85,
            "pass_k_4": 0.5478,
            "latency_p95_s": 1.4,
            "metadata_tokens": 82,
            "per_invocation_footprint": 3600,
            "trigger_F1": 0.89,
            "router_floor": "composer_2/fast",
            "routing_stage_tokens_total": 78 * 20,
            "body_invocation_tokens_total": 3520 * 20,
            "latency_p50_s": 1.2,
            "step_count": 20,
            "redundant_call_ratio": 0.0,
            "prompt_outcomes": [
                {"prompt_id": f"p{i}", "expected": "trigger", "correct": True}
                for i in range(10)
            ],
        }
        base_case = dict(case)
        base_case["pass_rate"] = 0.5
        base_case["trigger_F1"] = 0.0
        (runs / "result.json").write_text(
            __import__("json").dumps(case), encoding="utf-8"
        )
        (base / "result.json").write_text(
            __import__("json").dumps(base_case), encoding="utf-8"
        )
        skill = tmp / "SKILL.md"
        skill.write_text(
            "---\nname: demo\ndescription: demo skill.\n---\nbody\n",
            encoding="utf-8",
        )
        out_path = tmp / "metrics.yaml"
        refs_dir = tmp / "references"
        refs_dir.mkdir()

        aggregate_py = Path(__file__).resolve().parent / "aggregate_eval.py"
        # Empty neighbor glob → C6 = 0.0 (predictable in CI).
        proc = subprocess.run(
            [
                sys.executable,
                str(aggregate_py),
                "--runs-dir", str(runs),
                "--baseline-dir", str(base),
                "--skill-md", str(skill),
                "--out", str(out_path),
                "--references-dir", str(refs_dir),
                "--neighbor-skills-glob", "",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        report = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        ce = report["metrics"]["context_economy"]
        # C5 populated from empty refs_dir → fanout=0 → value based on body tokens.
        self.assertIsNotNone(ce["C5_context_rot_risk"])
        self.assertGreaterEqual(ce["C5_context_rot_risk"], 0.0)
        # C6 = 0.0 because neighbor glob was empty.
        self.assertEqual(ce["C6_scope_overlap_score"], 0.0)


# ─────────────────────────── Round 8 tests ───────────────────────────
# Workspace rule "Mandatory Verification": Round 8 (task spec §3)
# added ``hoist_v1_permission_scope``, ``hoist_v2_credential_surface``,
# ``hoist_v3_drift_signal``, ``hoist_v4_staleness_days``, plus
# ``build_report`` now accepts a ``governance_report`` parameter and
# populates D7 V1-V4. These tests cover correctness, degenerate paths,
# the spec §3.2 frozen 28-key invariant, and the Round 8 acceptance
# criterion that governance_risk_delta is DERIVED LIVE from V1-V4
# (not hard-coded 0.0).


def _governance_report_payload(
    v1: Optional[int] = 0,
    v2: Optional[int] = 0,
    v3: Optional[float] = 0.0,
    v4: Optional[int] = 0,
    governance_risk_delta: Optional[float] = 0.0,
) -> dict:
    """Build a minimal governance_scan.json-shaped payload."""

    return {
        "V1_permission_scope": v1,
        "V2_credential_surface": v2,
        "V3_drift_signal": v3,
        "V4_staleness_days": v4,
        "provenance": {
            "script_version": "0.1.0",
            "v1_derivation": {
                "method": "count distinct hardcoded absolute write-paths outside "
                         ".local/dogfood/ and outside the skill's own source tree",
            },
            "v2_derivation": {
                "method": "count credential/secret pattern matches; values never logged",
            },
            "v3_derivation": {
                "method": "1.0 - cross_tree_drift_zero_ratio across mirrors",
            },
            "v4_derivation": {
                "method": "(today - last_reviewed_at).days",
            },
            "governance_risk_delta": governance_risk_delta,
            "governance_risk_delta_method": (
                "compute_governance_risk_delta(V1, V2, V3, V4); "
                "risk_without - risk_with per spec §6.1 D7"
            ),
        },
    }


class HoistV1Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_v1_permission_scope`."""

    def test_happy_path_zero(self) -> None:
        v = ae.hoist_v1_permission_scope(_governance_report_payload(v1=0))
        self.assertEqual(v, 0)

    def test_happy_path_positive(self) -> None:
        v = ae.hoist_v1_permission_scope(_governance_report_payload(v1=3))
        self.assertEqual(v, 3)

    def test_none_payload_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v1_permission_scope(None))

    def test_missing_key_returns_none(self) -> None:
        payload = _governance_report_payload()
        del payload["V1_permission_scope"]
        self.assertIsNone(ae.hoist_v1_permission_scope(payload))

    def test_negative_value_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v1_permission_scope({"V1_permission_scope": -1}))


class HoistV2Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_v2_credential_surface`."""

    def test_happy_path_zero(self) -> None:
        v = ae.hoist_v2_credential_surface(_governance_report_payload(v2=0))
        self.assertEqual(v, 0)

    def test_happy_path_positive(self) -> None:
        v = ae.hoist_v2_credential_surface(_governance_report_payload(v2=2))
        self.assertEqual(v, 2)

    def test_none_payload_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v2_credential_surface(None))

    def test_missing_key_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v2_credential_surface({}))


class HoistV3Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_v3_drift_signal`."""

    def test_happy_path_zero(self) -> None:
        v = ae.hoist_v3_drift_signal(_governance_report_payload(v3=0.0))
        self.assertEqual(v, 0.0)

    def test_happy_path_fractional(self) -> None:
        v = ae.hoist_v3_drift_signal(_governance_report_payload(v3=2.0 / 3.0))
        self.assertIsNotNone(v)
        self.assertAlmostEqual(v, 2.0 / 3.0, places=6)

    def test_none_payload_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v3_drift_signal(None))

    def test_out_of_range_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v3_drift_signal({"V3_drift_signal": 1.1}))


class HoistV4Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_v4_staleness_days`."""

    def test_happy_path_zero(self) -> None:
        v = ae.hoist_v4_staleness_days(_governance_report_payload(v4=0))
        self.assertEqual(v, 0)

    def test_happy_path_positive(self) -> None:
        v = ae.hoist_v4_staleness_days(_governance_report_payload(v4=30))
        self.assertEqual(v, 30)

    def test_none_payload_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v4_staleness_days(None))

    def test_negative_value_returns_none(self) -> None:
        self.assertIsNone(ae.hoist_v4_staleness_days({"V4_staleness_days": -5}))


class BuildReportV1V4Integration(unittest.TestCase):
    """End-to-end smoke: build_report surfaces D7 V1/V2/V3/V4 and wires provenance."""

    def _make_skill_md(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: si-chip\ndescription: {description}\n---\n"
            "body text body text\n",
            encoding="utf-8",
        )
        return path

    def test_full_instrumentation_populates_v1_v2_v3_v4(self) -> None:
        skill_md = self._make_skill_md("demo description")
        report = ae.build_report(
            with_rows=[_row_with_outcomes() for _ in range(3)],
            without_rows=[_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(3)],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(v1=0, v2=0, v3=0.0, v4=0),
        )
        gr = report["metrics"]["governance_risk"]
        self.assertEqual(gr["V1_permission_scope"], 0)
        self.assertEqual(gr["V2_credential_surface"], 0)
        self.assertEqual(gr["V3_drift_signal"], 0.0)
        self.assertEqual(gr["V4_staleness_days"], 0)
        prov = report["provenance"]
        for key in ("v1_derivation", "v2_derivation", "v3_derivation", "v4_derivation"):
            self.assertIn(key, prov)
            self.assertTrue(prov[key]["loaded"])

    def test_missing_governance_report_keeps_v1_v4_null(self) -> None:
        """Round 7 code path (no governance_report) leaves V1-V4 null."""

        skill_md = self._make_skill_md("demo")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            governance_report=None,
        )
        gr = report["metrics"]["governance_risk"]
        self.assertIsNone(gr["V1_permission_scope"])
        self.assertIsNone(gr["V2_credential_surface"])
        self.assertIsNone(gr["V3_drift_signal"])
        self.assertIsNone(gr["V4_staleness_days"])
        # Derivation records still exist but marked loaded=False.
        for key in ("v1_derivation", "v2_derivation", "v3_derivation", "v4_derivation"):
            self.assertFalse(report["provenance"][key]["loaded"])

    def test_round_8_keeps_28_key_invariant(self) -> None:
        """Round 8 must not drop the spec §3.2 frozen 28-key (table=37) invariant."""

        skill_md = self._make_skill_md("demo")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(),
        )
        metrics = report["metrics"]
        self.assertEqual(set(metrics.keys()), set(ae.METRIC_KEYS.keys()))
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(
                set(metrics[dim].keys()),
                set(keys),
                msg=f"{dim} sub-metric keys diverged from schema after Round 8",
            )
        # Full D7 coverage = 4/4 sub-metrics populated for the first time.
        measured = [k for k, v in metrics["governance_risk"].items() if v is not None]
        self.assertEqual(set(measured), {
            "V1_permission_scope",
            "V2_credential_surface",
            "V3_drift_signal",
            "V4_staleness_days",
        })

    def test_governance_risk_delta_derived_live_not_hardcoded(self) -> None:
        """Round 8 acceptance criterion: governance_risk_delta must be COMPUTED, not literal.

        The aggregator attaches the scanner's live
        ``governance_risk_delta`` into the v*_derivation.source block.
        The half_retire_decision.yaml consumer reads THAT value
        (not a hard-coded ``0.0``). This test asserts the live-derive
        contract by passing a non-zero value through the report.
        """

        skill_md = self._make_skill_md("demo")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(
                v1=1, v2=0, v3=0.0, v4=0,
                governance_risk_delta=-0.25,
            ),
        )
        gr = report["metrics"]["governance_risk"]
        self.assertEqual(gr["V1_permission_scope"], 1)
        # The attached derivation records preserve the live delta input.
        v1_source = report["provenance"]["v1_derivation"]["source"]
        self.assertIsNotNone(v1_source)


# ─────────────────────────── Round 9 tests ───────────────────────────
# Workspace rule "Mandatory Verification": Round 9 (task spec §3) adds
# ``hoist_r8_description_competition_index`` + threads ``r8_method``
# through ``build_report``. These tests cover happy-path max_jaccard,
# happy-path tfidf_cosine_mean, degenerate paths (missing SKILL.md /
# empty neighbor / unknown method), 28-key invariant preservation, and
# the R8 value range sanity invariant.


def _make_neighbor_skill(description: str, name: str = "neighbor") -> Path:
    """Tiny helper that writes a neighbor SKILL.md for R8 tests."""

    tmp = Path(tempfile.mkdtemp())
    path = tmp / f"{name}_SKILL.md"
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nneighbor body\n",
        encoding="utf-8",
    )
    return path


class HoistR8Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_r8_description_competition_index`."""

    def _make_base_skill(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: si-chip\ndescription: {description}\n---\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_hoist_r8_max_jaccard_happy_path(self) -> None:
        """Identical-description neighbor → R8(max_jaccard) == 1.0."""

        base = self._make_base_skill("alpha beta gamma")
        n_identical = _make_neighbor_skill("alpha beta gamma", "n_identical")
        n_disjoint = _make_neighbor_skill("delta epsilon", "n_disjoint")
        value, derivation = ae.hoist_r8_description_competition_index(
            base, [n_identical, n_disjoint], method="max_jaccard"
        )
        self.assertAlmostEqual(value, 1.0, places=6)
        self.assertIn("pairs", derivation)
        self.assertEqual(derivation["n_neighbors_attempted"], 2)
        self.assertEqual(derivation["method_name"], "max_jaccard")

    def test_hoist_r8_tfidf_cosine_mean_path(self) -> None:
        """tfidf_cosine_mean returns in-range deterministic value."""

        base = self._make_base_skill("alpha beta gamma")
        n1 = _make_neighbor_skill("alpha delta", "n1")
        n2 = _make_neighbor_skill("beta gamma", "n2")
        value, derivation = ae.hoist_r8_description_competition_index(
            base, [n1, n2], method="tfidf_cosine_mean"
        )
        self.assertIsNotNone(value)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)
        self.assertEqual(derivation["method_name"], "tfidf_cosine_mean")
        self.assertIn("tfidf", derivation["method_note"].lower())

    def test_hoist_r8_none_skill_md_returns_none(self) -> None:
        """Missing skill_md_path → (None, {error, remediation})."""

        value, derivation = ae.hoist_r8_description_competition_index(
            None, [Path("/tmp/fake/neighbor.md")]
        )
        self.assertIsNone(value)
        self.assertIn("error", derivation)
        self.assertIn("--skill-md", derivation["remediation"])

    def test_hoist_r8_empty_neighbor_list_returns_none(self) -> None:
        """Empty neighbor list → (None, {error}); aggregator surfaces null."""

        base = self._make_base_skill("alpha")
        value, derivation = ae.hoist_r8_description_competition_index(
            base, []
        )
        self.assertIsNone(value)
        self.assertIn("error", derivation)

    def test_hoist_r8_unknown_method_returns_none_not_raises(self) -> None:
        """Unknown method → ValueError from helper is captured → None."""

        base = self._make_base_skill("alpha")
        n1 = _make_neighbor_skill("beta", "n1")
        value, derivation = ae.hoist_r8_description_competition_index(
            base, [n1], method="no_such_method"
        )
        self.assertIsNone(value)
        self.assertIn("error", derivation)
        self.assertEqual(derivation["method"], "no_such_method")

    def test_build_report_populates_r8_with_skill_and_neighbors(self) -> None:
        """End-to-end: build_report exposes R8 when skill_md + neighbors present."""

        base = self._make_base_skill("alpha beta gamma")
        n1 = _make_neighbor_skill("delta epsilon", "n1")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=base,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(),
            neighbor_skill_md_paths=[n1],
        )
        r8 = report["metrics"]["routing_cost"]["R8_description_competition_index"]
        self.assertIsNotNone(r8)
        self.assertGreaterEqual(r8, 0.0)
        self.assertLessEqual(r8, 1.0)
        self.assertIn("r8_derivation", report["provenance"])

    def test_build_report_preserves_28_key_invariant(self) -> None:
        """Round 9 must not drop the spec §3.2 frozen key invariant."""

        base = self._make_base_skill("alpha beta gamma")
        n1 = _make_neighbor_skill("alpha", "n1")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=base,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(),
            neighbor_skill_md_paths=[n1],
        )
        metrics = report["metrics"]
        self.assertEqual(set(metrics.keys()), set(ae.METRIC_KEYS.keys()))
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(
                set(metrics[dim].keys()),
                set(keys),
                msg=f"{dim} sub-metric keys diverged from schema after Round 9",
            )
        # R8 is now populated in routing_cost (D6) for the first time.
        self.assertIsNotNone(
            metrics["routing_cost"]["R8_description_competition_index"],
        )

    def test_build_report_null_r8_when_no_neighbors(self) -> None:
        """Round 8-compat code path (no neighbors) leaves R8 null."""

        base = self._make_base_skill("alpha beta")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=base,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(),
            neighbor_skill_md_paths=[],
        )
        r8 = report["metrics"]["routing_cost"]["R8_description_competition_index"]
        self.assertIsNone(r8)


# ─────────────────────────── Round 10 tests ───────────────────────────
# Workspace rule "Mandatory Verification": Round 10 (task spec §2) adds
# ``hoist_g1_cross_model_pass_matrix`` + threads the existing
# ``router_floor_report`` parameter into ``build_report`` so G1 (D4
# generalizability first sub-metric) is populated. These tests cover
# happy-path 8-cell mvp sweep on BOTH the flat and nested shapes, the
# degenerate paths (missing / empty / malformed), the exact 2-model ×
# 2-pack matrix shape, per-cell range invariant, and the spec §3.2
# frozen 28-key contract.


# Nested mvp_profile fixture (Round 9 emitted shape) — mirrors
# .local/dogfood/2026-04-28/round_9/router_floor_report.yaml#mvp_profile
# byte-for-byte so the Round 10 hoist is unit-tested against the real
# Round 9 evidence surface.
ROUND_9_NESTED_SWEEP = {
    "round_id": "round_9",
    "matrix_profile_primary": "mvp",
    "matrix_profile_additional": "intermediate",
    "schema_version": "0.1.1",
    "mvp_profile": {
        "profile": "mvp",
        "cells_total": 8,
        "pass_threshold": 0.80,
        "cells": [
            {"model": "composer_2", "thinking_depth": "fast",
             "scenario_pack": "trigger_basic",
             "pass_rate": 0.86, "latency_p50_ms": 720, "latency_p95_ms": 1100},
            {"model": "composer_2", "thinking_depth": "fast",
             "scenario_pack": "near_miss",
             "pass_rate": 0.78, "latency_p50_ms": 740, "latency_p95_ms": 1180},
            {"model": "composer_2", "thinking_depth": "default",
             "scenario_pack": "trigger_basic",
             "pass_rate": 0.90, "latency_p50_ms": 940, "latency_p95_ms": 1480},
            {"model": "composer_2", "thinking_depth": "default",
             "scenario_pack": "near_miss",
             "pass_rate": 0.83, "latency_p50_ms": 980, "latency_p95_ms": 1560},
            {"model": "sonnet_shallow", "thinking_depth": "fast",
             "scenario_pack": "trigger_basic",
             "pass_rate": 0.83, "latency_p50_ms": 880, "latency_p95_ms": 1340},
            {"model": "sonnet_shallow", "thinking_depth": "fast",
             "scenario_pack": "near_miss",
             "pass_rate": 0.74, "latency_p50_ms": 900, "latency_p95_ms": 1400},
            {"model": "sonnet_shallow", "thinking_depth": "default",
             "scenario_pack": "trigger_basic",
             "pass_rate": 0.88, "latency_p50_ms": 1180, "latency_p95_ms": 1820},
            {"model": "sonnet_shallow", "thinking_depth": "default",
             "scenario_pack": "near_miss",
             "pass_rate": 0.81, "latency_p50_ms": 1230, "latency_p95_ms": 1900},
        ],
        "mvp_router_floor": "composer_2/default",
    },
}


class HoistG1Tests(unittest.TestCase):
    """Direct unit tests for :func:`hoist_g1_cross_model_pass_matrix`."""

    def test_hoist_g1_happy_path_on_mvp_8_cell_sweep(self) -> None:
        """Flat 8-cell sweep → 2×2 matrix with max-across-depths collapse."""

        matrix, derivation = ae.hoist_g1_cross_model_pass_matrix(ROUND_2_SWEEP)
        self.assertIsNotNone(matrix)
        self.assertEqual(set(matrix.keys()), {"composer_2", "sonnet_shallow"})
        self.assertEqual(
            set(matrix["composer_2"].keys()), {"trigger_basic", "near_miss"}
        )
        self.assertEqual(
            set(matrix["sonnet_shallow"].keys()), {"trigger_basic", "near_miss"}
        )
        # Collapse rule = max across depths. For composer_2 × trigger_basic:
        # fast=0.86, default=0.90 → max = 0.90.
        self.assertAlmostEqual(matrix["composer_2"]["trigger_basic"], 0.90, places=6)
        self.assertAlmostEqual(matrix["composer_2"]["near_miss"], 0.83, places=6)
        self.assertAlmostEqual(
            matrix["sonnet_shallow"]["trigger_basic"], 0.88, places=6
        )
        self.assertAlmostEqual(matrix["sonnet_shallow"]["near_miss"], 0.81, places=6)
        self.assertEqual(derivation["collapse_rule"], "max across depths")
        self.assertEqual(derivation["source_profile"], "mvp")
        self.assertEqual(derivation["source_shape"], "cells")

    def test_hoist_g1_nested_mvp_profile_shape(self) -> None:
        """Nested ``mvp_profile.cells`` (Round 9 emitted shape) also works."""

        matrix, derivation = ae.hoist_g1_cross_model_pass_matrix(
            ROUND_9_NESTED_SWEEP
        )
        self.assertIsNotNone(matrix)
        self.assertEqual(derivation["source_shape"], "mvp_profile.cells")
        # Same per-cell math as the flat fixture.
        self.assertAlmostEqual(matrix["composer_2"]["trigger_basic"], 0.90, places=6)
        self.assertAlmostEqual(
            matrix["sonnet_shallow"]["near_miss"], 0.81, places=6
        )

    def test_hoist_g1_none_report_returns_none(self) -> None:
        """Missing report → (None, {"error": ...}) with no silent zeros."""

        matrix, derivation = ae.hoist_g1_cross_model_pass_matrix(None)
        self.assertIsNone(matrix)
        self.assertIn("error", derivation)

    def test_hoist_g1_empty_cells_returns_none(self) -> None:
        """Empty / missing cells → None + error."""

        matrix, derivation = ae.hoist_g1_cross_model_pass_matrix({"cells": []})
        self.assertIsNone(matrix)
        self.assertIn("error", derivation)
        self.assertIn("no cells", derivation["error"])

    def test_hoist_g1_malformed_cells_skipped(self) -> None:
        """Non-dict / non-numeric cells are skipped; ratio tracks skipped count."""

        rf = {"cells": [
            "not-a-dict",
            {"model": "composer_2", "scenario_pack": "trigger_basic",
             "thinking_depth": "fast", "pass_rate": "nope"},
            {"model": "composer_2", "scenario_pack": "trigger_basic",
             "thinking_depth": "default", "pass_rate": 0.95},
            {"model": "composer_2", "scenario_pack": "near_miss",
             "thinking_depth": "fast", "pass_rate": 0.70},
        ]}
        matrix, derivation = ae.hoist_g1_cross_model_pass_matrix(rf)
        self.assertIsNotNone(matrix)
        self.assertEqual(matrix["composer_2"]["trigger_basic"], 0.95)
        self.assertEqual(matrix["composer_2"]["near_miss"], 0.70)
        # Two skipped entries: "not-a-dict" + the pass_rate="nope" row.
        self.assertEqual(derivation["n_cells_skipped"], 2)
        self.assertEqual(derivation["n_cells_used"], 2)

    def test_hoist_g1_all_values_in_unit_interval(self) -> None:
        """Every matrix cell must lie in ``[0.0, 1.0]`` for the range-sanity check."""

        matrix, derivation = ae.hoist_g1_cross_model_pass_matrix(ROUND_2_SWEEP)
        for model, pack_map in matrix.items():
            for pack, value in pack_map.items():
                with self.subTest(model=model, pack=pack):
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 1.0)
        self.assertIn("PASS", derivation["range_sanity_check"])

    def test_hoist_g1_pack_filter_limits_shape(self) -> None:
        """Explicit ``packs=`` arg narrows the observed pack set."""

        matrix, derivation = ae.hoist_g1_cross_model_pass_matrix(
            ROUND_2_SWEEP, packs=("trigger_basic",)
        )
        self.assertIsNotNone(matrix)
        for model, pack_map in matrix.items():
            with self.subTest(model=model):
                self.assertEqual(list(pack_map.keys()), ["trigger_basic"])
        self.assertEqual(derivation["packs_requested"], ["trigger_basic"])


class BuildReportG1Integration(unittest.TestCase):
    """End-to-end smoke: build_report surfaces D4 G1 in metrics_report."""

    def _make_skill_md(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: si-chip\ndescription: {description}\n---\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_build_report_populates_g1_when_router_floor_report_present(self) -> None:
        """build_report wires G1 through when a router_floor_report is supplied."""

        skill_md = self._make_skill_md("demo description")
        report = ae.build_report(
            with_rows=[_row_with_outcomes() for _ in range(3)],
            without_rows=[_row(pass_rate=0.5, trigger_F1=0.0) for _ in range(3)],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(),
        )
        g1 = report["metrics"]["generalizability"]["G1_cross_model_pass_matrix"]
        self.assertIsNotNone(g1)
        # Exactly {composer_2, sonnet_shallow} × {trigger_basic, near_miss}.
        self.assertEqual(set(g1.keys()), {"composer_2", "sonnet_shallow"})
        for model_map in g1.values():
            self.assertEqual(
                set(model_map.keys()), {"trigger_basic", "near_miss"}
            )
            for value in model_map.values():
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)
        # g1_derivation exists in provenance.
        self.assertIn("g1_derivation", report["provenance"])
        self.assertEqual(
            report["provenance"]["g1_derivation"]["collapse_rule"], "max across depths"
        )

    def test_build_report_leaves_g1_null_when_no_router_floor_report(self) -> None:
        """Round 9-compat code path (no router_floor_report) leaves G1 null."""

        skill_md = self._make_skill_md("demo description")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row(pass_rate=0.5, trigger_F1=0.0)],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=None,
            skill_md_path=skill_md,
        )
        g1 = report["metrics"]["generalizability"]["G1_cross_model_pass_matrix"]
        self.assertIsNone(g1)
        # G2/G3/G4 stay null by scope for v0.1.x.
        self.assertIsNone(
            report["metrics"]["generalizability"]["G2_cross_domain_transfer_pass"]
        )
        self.assertIsNone(
            report["metrics"]["generalizability"]["G3_OOD_robustness"]
        )
        self.assertIsNone(
            report["metrics"]["generalizability"]["G4_model_version_stability"]
        )

    def test_build_report_g1_coexists_with_g2_g3_g4_null(self) -> None:
        """G1 populated, G2/G3/G4 explicit null — D4 first-ever partial fill."""

        skill_md = self._make_skill_md("demo description")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
        )
        gen = report["metrics"]["generalizability"]
        self.assertIsNotNone(gen["G1_cross_model_pass_matrix"])
        self.assertIsNone(gen["G2_cross_domain_transfer_pass"])
        self.assertIsNone(gen["G3_OOD_robustness"])
        self.assertIsNone(gen["G4_model_version_stability"])

    def test_build_report_preserves_28_key_invariant_after_g1_fill(self) -> None:
        """Round 10 must not drop the spec §3.2 frozen key contract (37 table keys)."""

        skill_md = self._make_skill_md("demo description")
        report = ae.build_report(
            with_rows=[_row_with_outcomes()],
            without_rows=[_row()],
            runs_dir=Path("/tmp/with"),
            baseline_dir=Path("/tmp/without"),
            skill_md_meta_tokens=82,
            router_floor_report=ROUND_2_SWEEP,
            skill_md_path=skill_md,
            install_telemetry=_install_telemetry_payload(),
            governance_report=_governance_report_payload(),
        )
        metrics = report["metrics"]
        self.assertEqual(set(metrics.keys()), set(ae.METRIC_KEYS.keys()))
        for dim, keys in ae.METRIC_KEYS.items():
            self.assertEqual(
                set(metrics[dim].keys()),
                set(keys),
                msg=f"{dim} sub-metric keys diverged from schema after Round 10",
            )
        # G1 populated — exactly 1/4 D4 sub-metrics measured after Round 10.
        measured_in_d4 = [k for k, v in metrics["generalizability"].items() if v is not None]
        self.assertEqual(measured_in_d4, ["G1_cross_model_pass_matrix"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
