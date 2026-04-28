#!/usr/bin/env python3
"""Unit tests for the no-ability runner's L1 / L3 / L4 instrumentation (Round 4).

Workspace rule "Mandatory Verification": Round 4 added
``percentile_p50``, ``step_count_from_outcomes`` and
``redundant_call_ratio_from_outcomes`` helpers plus
``latency_p50_s`` / ``step_count`` / ``redundant_call_ratio``
fields to the no-ability baseline runner's per-case payload. These
tests assert the new fields are present, deterministic, and that
the L1 ≤ L2 sanity invariant holds on the no-ability arm too.

Run::

    python3 -m unittest evals.si-chip.runners.test_no_ability_runner -v

or directly::

    python3 evals/si-chip/runners/test_no_ability_runner.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import no_ability_runner as runner  # noqa: E402


SYNTHETIC_CASE = {
    "case_id": "synthetic_no_ability",
    "prompts": {
        "should_trigger": [
            {"id": "t01", "prompt": "Profile the Si-Chip basic_ability and write a profile."},
            {"id": "t02", "prompt": "Compute the trigger F1 for the router_test matrix."},
        ],
        "should_not_trigger": [
            {"id": "n01", "prompt": "What is the weather in Beijing today?"},
            {"id": "n02", "prompt": "Translate this sentence into French."},
        ],
    },
}


class PercentileP50Tests(unittest.TestCase):
    """Direct unit tests for the new percentile_p50 helper."""

    def test_simple_sequence(self) -> None:
        self.assertEqual(runner.percentile_p50([0.1, 0.2, 0.3, 0.4, 0.5]), 0.3)

    def test_empty_returns_zero(self) -> None:
        self.assertEqual(runner.percentile_p50([]), 0.0)

    def test_single_element(self) -> None:
        self.assertEqual(runner.percentile_p50([0.75]), 0.75)

    def test_p50_le_p95_invariant(self) -> None:
        """Spec L1 <= L2 sanity invariant must hold for any non-empty input."""

        for values in (
            [0.5, 0.6, 0.7, 0.8, 0.9],
            [0.95, 0.95, 0.95],
            [0.1, 10.0],
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        ):
            with self.subTest(values=values):
                self.assertLessEqual(
                    runner.percentile_p50(values),
                    runner.percentile_p95(values),
                    msg=f"p50 > p95 for {values}",
                )


class StepCountAndRedundantTests(unittest.TestCase):
    """Direct unit tests for the L3/L4 helpers on the no-ability arm."""

    def test_step_count_matches_outcome_length(self) -> None:
        outcomes = [{"prompt_id": f"p{i}"} for i in range(4)]
        self.assertEqual(runner.step_count_from_outcomes(outcomes), 4)

    def test_step_count_empty(self) -> None:
        self.assertEqual(runner.step_count_from_outcomes([]), 0)

    def test_step_count_returns_int(self) -> None:
        self.assertIsInstance(
            runner.step_count_from_outcomes([{"prompt_id": "p"}]), int
        )

    def test_redundant_call_ratio_zero_when_unique(self) -> None:
        outcomes = [{"prompt_id": f"p{i:02d}"} for i in range(20)]
        self.assertEqual(runner.redundant_call_ratio_from_outcomes(outcomes), 0.0)

    def test_redundant_call_ratio_half_when_duplicated(self) -> None:
        outcomes = [
            {"prompt_id": "a"},
            {"prompt_id": "a"},
            {"prompt_id": "b"},
            {"prompt_id": "b"},
        ]
        self.assertEqual(runner.redundant_call_ratio_from_outcomes(outcomes), 0.5)

    def test_redundant_call_ratio_clamped_zero_when_empty(self) -> None:
        self.assertEqual(runner.redundant_call_ratio_from_outcomes([]), 0.0)

    def test_redundant_call_ratio_bounded_0_1(self) -> None:
        outcomes = [{"prompt_id": "a"}] * 7 + [{"prompt_id": "b"}]
        v = runner.redundant_call_ratio_from_outcomes(outcomes)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)


class EvaluateCaseLatencyPathTests(unittest.TestCase):
    """End-to-end: no-ability evaluate_case must surface L1 / L3 / L4 fields."""

    def test_top_level_l1_l3_l4_fields_present(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        self.assertIn("latency_p50_s", result)
        self.assertIn("step_count", result)
        self.assertIn("redundant_call_ratio", result)
        self.assertIsInstance(result["step_count"], int)
        self.assertIsInstance(result["redundant_call_ratio"], float)

    def test_l1_le_l2_sanity_invariant(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        self.assertLessEqual(result["latency_p50_s"], result["latency_p95_s"])

    def test_step_count_equals_n_total(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        n_total = len(SYNTHETIC_CASE["prompts"]["should_trigger"]) + len(
            SYNTHETIC_CASE["prompts"]["should_not_trigger"]
        )
        self.assertEqual(result["step_count"], n_total)

    def test_redundant_call_ratio_is_zero_for_unique_prompt_ids(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        self.assertEqual(result["redundant_call_ratio"], 0.0)

    def test_required_keys_now_include_l1_l3_l4(self) -> None:
        for k in ("latency_p50_s", "step_count", "redundant_call_ratio"):
            self.assertIn(k, runner.REQUIRED_RESULT_KEYS)

    def test_meta_records_basis_explanations(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        meta = result["_meta"]
        self.assertIn("step_count_basis", meta)
        self.assertIn("redundant_call_ratio_basis", meta)

    def test_determinism_of_l1_l3_l4(self) -> None:
        a = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        b = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        self.assertEqual(a["latency_p50_s"], b["latency_p50_s"])
        self.assertEqual(a["step_count"], b["step_count"])
        self.assertEqual(a["redundant_call_ratio"], b["redundant_call_ratio"])

    def test_no_ability_constants_unchanged(self) -> None:
        """Round 4 must not change the historical no-ability baseline constants."""

        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        self.assertEqual(result["metadata_tokens"], 0)
        self.assertEqual(result["per_invocation_footprint"], 1500)
        self.assertEqual(result["trigger_F1"], 0.0)
        self.assertEqual(result["router_floor"], "n/a (no_ability)")


class ResultJsonRoundTripL1L3L4Tests(unittest.TestCase):
    """The new L1/L3/L4 fields must survive the JSON round-trip."""

    def test_round_trip_preserves_l1_l3_l4(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "round4_test" / "result.json"
            runner._write_json(out_path, result)
            with out_path.open("r", encoding="utf-8") as fp:
                round_trip = json.load(fp)
        self.assertIn("latency_p50_s", round_trip)
        self.assertIn("step_count", round_trip)
        self.assertIn("redundant_call_ratio", round_trip)
        self.assertEqual(round_trip["latency_p50_s"], result["latency_p50_s"])
        self.assertEqual(round_trip["step_count"], result["step_count"])
        self.assertEqual(round_trip["redundant_call_ratio"], result["redundant_call_ratio"])

    def test_ensure_required_keys_rejects_missing_l1(self) -> None:
        partial = {
            k: 0.5 if k in {"pass_rate", "pass_k_4", "latency_p95_s", "latency_p50_s", "redundant_call_ratio", "trigger_F1"}
            else 0 if k in {"metadata_tokens", "per_invocation_footprint", "step_count"}
            else "x"
            for k in runner.REQUIRED_RESULT_KEYS
        }
        del partial["latency_p50_s"]
        with self.assertRaises(KeyError):
            runner._ensure_required_keys(partial, "<test>")


if __name__ == "__main__":
    unittest.main(verbosity=2)
