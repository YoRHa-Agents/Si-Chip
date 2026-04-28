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


if __name__ == "__main__":
    unittest.main(verbosity=2)
