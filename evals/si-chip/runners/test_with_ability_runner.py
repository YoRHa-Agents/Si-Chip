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


if __name__ == "__main__":
    unittest.main(verbosity=2)
