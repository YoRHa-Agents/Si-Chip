#!/usr/bin/env python3
"""Unit tests for the with-ability runner's R7 instrumentation (Round 3).

Workspace rule "Mandatory Verification": every new logic addition has a
test. Round 3 added per-prompt ``routing_stage_tokens`` and
``body_invocation_tokens`` to the simulated runner so the aggregator can
compute spec §3.1 D6 R7 ``routing_token_overhead`` without further
instrumentation. These tests assert the new fields are present, are
integers, are deterministic, and are consistent at the case-aggregate
and prompt levels.

Run::

    python3 -m unittest evals.si-chip.runners.test_with_ability_runner -v

or directly::

    python3 evals/si-chip/runners/test_with_ability_runner.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# evals/si-chip/runners has hyphens in its path so a regular `import` is
# not portable. Add the runners directory to sys.path and import by name.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import with_ability_runner as runner  # noqa: E402


SYNTHETIC_CASE = {
    "case_id": "synthetic_r7_test",
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


class TokenSplitTests(unittest.TestCase):
    """Direct unit tests for the helper that decides the R7 split."""

    def test_split_returns_int_pair(self) -> None:
        out = runner._per_prompt_token_split(78, 2020)
        self.assertEqual(out["routing_stage_tokens"], 78)
        self.assertEqual(out["body_invocation_tokens"], 2020 + runner.USER_PROMPT_FOOTPRINT)
        self.assertIsInstance(out["routing_stage_tokens"], int)
        self.assertIsInstance(out["body_invocation_tokens"], int)

    def test_split_zero_body_is_user_prompt_footprint(self) -> None:
        out = runner._per_prompt_token_split(0, 0)
        self.assertEqual(out["routing_stage_tokens"], 0)
        self.assertEqual(out["body_invocation_tokens"], runner.USER_PROMPT_FOOTPRINT)


class EvaluateCaseTests(unittest.TestCase):
    """Per-case result.json schema tests after Round 3 Edit A."""

    def test_top_level_r7_fields_present(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=78, body_tokens=2020)
        self.assertIn("routing_stage_tokens_total", result)
        self.assertIn("body_invocation_tokens_total", result)
        self.assertEqual(result["routing_stage_tokens_total"], 78 * 4)
        self.assertEqual(result["body_invocation_tokens_total"], (2020 + runner.USER_PROMPT_FOOTPRINT) * 4)

    def test_per_prompt_r7_fields_present(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=78, body_tokens=2020)
        self.assertEqual(len(result["prompt_outcomes"]), 4)
        for entry in result["prompt_outcomes"]:
            self.assertIn("routing_stage_tokens", entry)
            self.assertIn("body_invocation_tokens", entry)
            self.assertEqual(entry["routing_stage_tokens"], 78)
            self.assertEqual(entry["body_invocation_tokens"], 2020 + runner.USER_PROMPT_FOOTPRINT)
            self.assertIsInstance(entry["routing_stage_tokens"], int)
            self.assertIsInstance(entry["body_invocation_tokens"], int)

    def test_meta_block_records_split_basis(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=78, body_tokens=2020)
        meta = result["_meta"]
        self.assertEqual(meta["routing_stage_tokens_per_prompt"], 78)
        self.assertEqual(meta["body_invocation_tokens_per_prompt"], 2020 + runner.USER_PROMPT_FOOTPRINT)
        self.assertIn("r7_token_split_basis", meta)
        self.assertIn("metadata_tokens", meta["r7_token_split_basis"])

    def test_aggregate_r7_ratio_is_within_v1_baseline_ceiling(self) -> None:
        """Spec §4.1 ``routing_token_overhead`` v1_baseline ceiling = 0.20."""

        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=78, body_tokens=2020)
        ratio = result["routing_stage_tokens_total"] / result["body_invocation_tokens_total"]
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 0.20)

    def test_determinism_of_r7_fields(self) -> None:
        a = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=78, body_tokens=2020)
        b = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=78, body_tokens=2020)
        self.assertEqual(a["routing_stage_tokens_total"], b["routing_stage_tokens_total"])
        self.assertEqual(a["body_invocation_tokens_total"], b["body_invocation_tokens_total"])
        for prompt_a, prompt_b in zip(a["prompt_outcomes"], b["prompt_outcomes"]):
            self.assertEqual(prompt_a["routing_stage_tokens"], prompt_b["routing_stage_tokens"])
            self.assertEqual(prompt_a["body_invocation_tokens"], prompt_b["body_invocation_tokens"])


class ResultJsonRoundTripTests(unittest.TestCase):
    """End-to-end smoke test: written result.json must carry the new fields."""

    def test_written_result_json_contains_r7_fields(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=78, body_tokens=2020)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "synthetic_r7_test" / "result.json"
            runner._write_json(out_path, result)
            with out_path.open("r", encoding="utf-8") as fp:
                round_trip = json.load(fp)

        self.assertIn("routing_stage_tokens_total", round_trip)
        self.assertIn("body_invocation_tokens_total", round_trip)
        for entry in round_trip["prompt_outcomes"]:
            self.assertIn("routing_stage_tokens", entry)
            self.assertIn("body_invocation_tokens", entry)


# ── Round 4 (S5 task spec Edit A) — L1 / L3 / L4 plumbing tests ──


class PercentileP50Tests(unittest.TestCase):
    """Direct unit tests for the new percentile_p50 helper."""

    def test_simple_sequence(self) -> None:
        self.assertEqual(runner.percentile_p50([0.1, 0.2, 0.3, 0.4, 0.5]), 0.3)

    def test_empty_returns_zero(self) -> None:
        self.assertEqual(runner.percentile_p50([]), 0.0)

    def test_single_element(self) -> None:
        self.assertEqual(runner.percentile_p50([1.7]), 1.7)

    def test_p50_le_p95_invariant(self) -> None:
        """Spec L1 <= L2 sanity invariant must hold for any non-empty input."""

        for values in (
            [0.5, 0.7, 1.0, 1.4, 1.5],
            [1.469, 1.469, 1.469],
            [0.1, 100.0],
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        ):
            with self.subTest(values=values):
                self.assertLessEqual(
                    runner.percentile_p50(values),
                    runner.percentile_p95(values),
                    msg=f"p50 > p95 for {values}",
                )


class StepCountAndRedundantTests(unittest.TestCase):
    """Direct unit tests for the L3/L4 helpers."""

    def test_step_count_matches_outcome_length(self) -> None:
        self.assertEqual(runner.step_count_from_outcomes([{"prompt_id": "a"}, {"prompt_id": "b"}]), 2)

    def test_step_count_empty(self) -> None:
        self.assertEqual(runner.step_count_from_outcomes([]), 0)

    def test_redundant_call_ratio_zero_when_unique(self) -> None:
        outcomes = [{"prompt_id": f"p{i:02d}"} for i in range(20)]
        self.assertEqual(runner.redundant_call_ratio_from_outcomes(outcomes), 0.0)

    def test_redundant_call_ratio_half_when_duplicated(self) -> None:
        outcomes = [{"prompt_id": "a"}, {"prompt_id": "a"}, {"prompt_id": "b"}, {"prompt_id": "b"}]
        self.assertEqual(runner.redundant_call_ratio_from_outcomes(outcomes), 0.5)

    def test_redundant_call_ratio_clamped_zero_when_empty(self) -> None:
        self.assertEqual(runner.redundant_call_ratio_from_outcomes([]), 0.0)

    def test_redundant_call_ratio_handles_missing_prompt_id(self) -> None:
        outcomes = [{"prompt_id": "a"}, {}, {}]
        ratio = runner.redundant_call_ratio_from_outcomes(outcomes)
        self.assertGreaterEqual(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)


class EvaluateCaseLatencyPathTests(unittest.TestCase):
    """End-to-end: evaluate_case must surface L1 / L3 / L4 fields."""

    def test_top_level_l1_l3_l4_fields_present(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=82, body_tokens=2020)
        self.assertIn("latency_p50_s", result)
        self.assertIn("step_count", result)
        self.assertIn("redundant_call_ratio", result)
        self.assertIsInstance(result["step_count"], int)
        self.assertIsInstance(result["redundant_call_ratio"], float)

    def test_l1_le_l2_sanity_invariant(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=82, body_tokens=2020)
        self.assertLessEqual(result["latency_p50_s"], result["latency_p95_s"])

    def test_step_count_equals_n_total(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=82, body_tokens=2020)
        n_total = len(SYNTHETIC_CASE["prompts"]["should_trigger"]) + len(SYNTHETIC_CASE["prompts"]["should_not_trigger"])
        self.assertEqual(result["step_count"], n_total)

    def test_redundant_call_ratio_is_zero_for_unique_prompt_ids(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=82, body_tokens=2020)
        self.assertEqual(result["redundant_call_ratio"], 0.0)

    def test_required_keys_now_include_l1_l3_l4(self) -> None:
        for k in ("latency_p50_s", "step_count", "redundant_call_ratio"):
            self.assertIn(k, runner.REQUIRED_RESULT_KEYS)

    def test_meta_records_basis_explanations(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=82, body_tokens=2020)
        meta = result["_meta"]
        self.assertIn("step_count_basis", meta)
        self.assertIn("redundant_call_ratio_basis", meta)


class ResultJsonRoundTripL1L3L4Tests(unittest.TestCase):
    """The new L1/L3/L4 fields must survive the JSON round-trip."""

    def test_round_trip_preserves_l1_l3_l4(self) -> None:
        result = runner.evaluate_case(SYNTHETIC_CASE, seed=42, metadata_tokens=82, body_tokens=2020)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
