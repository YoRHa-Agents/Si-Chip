#!/usr/bin/env python3
"""Unit tests for ``evals/si-chip/runners/real_llm_runner.py``.

Covers the Stage 4 Wave 1c acceptance-gate tests (≥ 10 tests, mocked;
plus one env-gated live integration test that runs only when
``SI_CHIP_REAL_LLM_LIVE=1`` is set in the environment, so CI stays
offline and deterministic).

Runnable both directly and under pytest::

    python evals/si-chip/runners/test_real_llm_runner.py
    python -m pytest evals/si-chip/runners/test_real_llm_runner.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import real_llm_runner as rlr  # noqa: E402


# --- Minimal eval_pack fixture shared across tests ---------------------

_MINIMAL_PACK_YAML = """
should_trigger:
  - "show me my cursor usage dashboard"
  - "how much did I spend on cursor this month"
should_not_trigger:
  - "how do I install a plugin?"
  - "fix this typescript error"
"""


def _write_minimal_pack(tmp_dir: Path) -> Path:
    p = tmp_dir / "eval_pack.yaml"
    p.write_text(_MINIMAL_PACK_YAML, encoding="utf-8")
    return p


# --- Mock client that answers YES/NO deterministically ----------------


class _ScriptedClient:
    """Mock ``AnthropicMessagesClient.call`` replacement for tests.

    ``responses`` is a dict ``(model, prompt_substring) -> text`` or a
    default ``text`` when no match. ``call_log`` records every call so
    tests can assert the client was (or wasn't) invoked.
    """

    def __init__(self, default_text: str = "YES", responses=None, usage=None):
        self.default_text = default_text
        self.responses = responses or {}
        self.usage = usage or {"input_tokens": 100, "output_tokens": 1}
        self.call_log = []

    def call(self, model, system, prompt, max_tokens):
        self.call_log.append(
            {"model": model, "prompt": prompt, "max_tokens": max_tokens}
        )
        text = self.default_text
        for (m, sub), t in self.responses.items():
            if m == model and sub in prompt:
                text = t
                break
        return {
            "text": text,
            "usage": dict(self.usage),
            "raw_stop_reason": "end_turn",
            "elapsed_s": 0.01,
        }


class _NoCallClient:
    """Client that fails any call — used to assert cache-only paths."""

    def __init__(self):
        self.call_log = []

    def call(self, model, system, prompt, max_tokens):
        self.call_log.append({"model": model, "prompt": prompt})
        raise AssertionError(
            "_NoCallClient.call was invoked — this test expected cache-only"
        )


# --- Tests -------------------------------------------------------------


class ModelRemapTests(unittest.TestCase):
    """MODEL_REMAP + resolve_model correctness (task acceptance #1)."""

    def test_model_remap_composer_2_fast(self):
        """composer_2/fast must physically call claude-haiku-4-5 per r12.5 §2.4."""

        self.assertEqual(
            rlr.MODEL_REMAP["composer_2/fast"], "claude-haiku-4-5"
        )
        self.assertEqual(rlr.resolve_model("composer_2/fast"), "claude-haiku-4-5")

    def test_model_remap_covers_full_6_models(self):
        for logical in rlr.FULL_MODELS:
            self.assertIn(
                logical, rlr.MODEL_REMAP,
                f"FULL_MODELS label {logical!r} missing from MODEL_REMAP",
            )

    def test_deterministic_memory_router_is_nominal(self):
        self.assertIsNone(
            rlr.MODEL_REMAP["deterministic_memory_router"]
        )
        self.assertIsNone(
            rlr.resolve_model("deterministic_memory_router")
        )

    def test_unknown_model_raises_keyerror(self):
        with self.assertRaises(KeyError):
            rlr.resolve_model("some-unknown-model-5.7")


class ThinkingDepthsTests(unittest.TestCase):
    """THINKING_DEPTHS enum (task acceptance #2)."""

    def test_thinking_depths_4_values(self):
        self.assertEqual(len(rlr.THINKING_DEPTHS), 4)
        self.assertEqual(
            set(rlr.THINKING_DEPTHS),
            {"fast", "default", "extended", "round_escalated"},
        )

    def test_build_system_prompt_depth_varies(self):
        fast = rlr.build_system_prompt("fast")
        ext = rlr.build_system_prompt("extended")
        self.assertIn("YES or NO", fast)
        self.assertNotEqual(fast, ext)
        with self.assertRaises(ValueError):
            rlr.build_system_prompt("ultra-fast")

    def test_max_tokens_extended_larger_than_fast(self):
        self.assertGreater(
            rlr.max_tokens_for_depth("extended"),
            rlr.max_tokens_for_depth("fast"),
        )


class MatrixShapesTests(unittest.TestCase):
    """MATRIX_SHAPES acceptance (tasks 3–5)."""

    def test_matrix_shapes_mvp_8(self):
        m, d, p = rlr.MATRIX_SHAPES["mvp"]
        self.assertEqual((m, d, p), (2, 2, 2))
        self.assertEqual(m * d * p, 8)
        self.assertEqual(len(rlr.MVP_MODELS), 2)
        self.assertEqual(len(rlr.MVP_DEPTHS), 2)
        self.assertEqual(len(rlr.MVP_PACKS), 2)

    def test_matrix_shapes_intermediate_16(self):
        m, d, p = rlr.MATRIX_SHAPES["intermediate"]
        self.assertEqual((m, d, p), (4, 2, 2))
        self.assertEqual(m * d * p, 16)
        self.assertEqual(len(rlr.INTERMEDIATE_MODELS), 4)

    def test_matrix_shapes_full_96(self):
        m, d, p = rlr.MATRIX_SHAPES["full"]
        self.assertEqual((m, d, p), (6, 4, 4))
        self.assertEqual(m * d * p, 96)
        self.assertEqual(len(rlr.FULL_MODELS), 6)
        self.assertEqual(len(rlr.FULL_DEPTHS), 4)
        self.assertEqual(len(rlr.FULL_PACKS), 4)


class PassAtKTests(unittest.TestCase):
    """compute_pass_at_k (tasks 6–7)."""

    def test_compute_pass_at_k_all_pass(self):
        self.assertEqual(rlr.compute_pass_at_k(4, [True, True, True, True]), 1.0)

    def test_compute_pass_at_k_partial(self):
        self.assertEqual(rlr.compute_pass_at_k(4, [False, True, False, True]), 1.0)
        self.assertEqual(rlr.compute_pass_at_k(4, [True, False, False, False]), 1.0)

    def test_compute_pass_at_k_all_fail_returns_zero(self):
        self.assertEqual(rlr.compute_pass_at_k(4, [False, False, False, False]), 0.0)

    def test_compute_pass_at_k_rejects_bad_args(self):
        with self.assertRaises(ValueError):
            rlr.compute_pass_at_k(0, [True])
        with self.assertRaises(ValueError):
            rlr.compute_pass_at_k(4, [])


class ParseYesNoTests(unittest.TestCase):
    """parse_yes_no tolerates CoT traces + punctuation."""

    def test_parse_yes_no_bare(self):
        self.assertIs(rlr.parse_yes_no("YES"), True)
        self.assertIs(rlr.parse_yes_no(" no."), False)
        self.assertIsNone(rlr.parse_yes_no("maybe"))

    def test_parse_yes_no_with_cot_trailer(self):
        txt = "The user asks about billing. So the answer is YES."
        self.assertIs(rlr.parse_yes_no(txt), True)

    def test_parse_yes_no_multiline_last_line_wins(self):
        txt = "Step 1: intent = billing\nStep 2: decide\nYES"
        self.assertIs(rlr.parse_yes_no(txt), True)


class CacheKeyTests(unittest.TestCase):
    """cache_key determinism + sensitivity."""

    def test_cache_key_deterministic_same_inputs(self):
        a = rlr.cache_key("claude-haiku-4-5", "fast", "hello", 0, seed=42)
        b = rlr.cache_key("claude-haiku-4-5", "fast", "hello", 0, seed=42)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_cache_key_sensitive_to_sample_idx(self):
        a = rlr.cache_key("claude-haiku-4-5", "fast", "hello", 0)
        b = rlr.cache_key("claude-haiku-4-5", "fast", "hello", 1)
        self.assertNotEqual(a, b)

    def test_cache_key_sensitive_to_seed(self):
        a = rlr.cache_key("claude-haiku-4-5", "fast", "hello", 0, seed=0)
        b = rlr.cache_key("claude-haiku-4-5", "fast", "hello", 0, seed=1)
        self.assertNotEqual(a, b)


class CacheBehaviourTests(unittest.TestCase):
    """Cache round-trip + --no-live + on-disk layout."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="si_chip_rlr_cache_"))
        self.pack_path = _write_minimal_pack(self.tmp)
        self.cache_dir = self.tmp / "real_llm_runner_cache"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_runner(self, client, no_live=False):
        config = rlr.RunnerConfig(
            ability="test-ability",
            eval_pack=self.pack_path,
            matrix_mode="mvp",
            k=1,
            cache_dir=self.cache_dir,
            no_live=no_live,
            max_spend_usd=1.0,
            max_prompts_per_cell=1,
        )
        return rlr.RealLLMRunner(config, client=client)

    def test_cache_hit_avoids_live_call(self):
        """After populating the cache, a second runner with a 'no-call' client
        must be able to replay without triggering the client."""

        # First pass: populate with a scripted client.
        scripted = _ScriptedClient(default_text="YES")
        runner1 = self._make_runner(scripted, no_live=False)
        out1 = runner1.evaluate_pack(depth="fast", scenario="trigger_basic")
        self.assertGreater(len(scripted.call_log), 0)
        # Cache files must be on disk (one file per key).
        cached_files = list(self.cache_dir.glob("*.json"))
        self.assertGreater(len(cached_files), 0)

        # Second pass: replay through a fresh no-call client.
        nocall = _NoCallClient()
        runner2 = self._make_runner(nocall, no_live=False)
        out2 = runner2.evaluate_pack(depth="fast", scenario="trigger_basic")
        self.assertEqual(len(nocall.call_log), 0)
        self.assertEqual(out1["cell"]["prompts_run"], out2["cell"]["prompts_run"])
        self.assertEqual(out2["summary"]["cache_hits"], runner2._cache_hits)  # noqa: SLF001
        self.assertGreater(runner2._cache_hits, 0)  # noqa: SLF001

    def test_cache_miss_raises_when_no_live(self):
        """With --no-live and an empty cache, we must raise CacheMissInNoLiveMode."""

        nocall = _NoCallClient()
        runner = self._make_runner(nocall, no_live=True)
        with self.assertRaises(rlr.CacheMissInNoLiveMode):
            runner.evaluate_pack(depth="fast", scenario="trigger_basic")
        # Nothing was written, and the client was never called.
        self.assertEqual(len(nocall.call_log), 0)

    def test_cache_per_key_json_layout(self):
        scripted = _ScriptedClient(default_text="YES")
        runner = self._make_runner(scripted, no_live=False)
        runner.evaluate_pack(depth="fast", scenario="trigger_basic")
        files = list(self.cache_dir.glob("*.json"))
        self.assertGreater(len(files), 0)
        for f in files:
            # Each file is a valid json doc with text + usage keys.
            data = json.loads(f.read_text(encoding="utf-8"))
            self.assertIn("text", data)
            self.assertIn("usage", data)
            self.assertEqual(len(f.stem), 16, f"expected 16-hex name, got {f.stem}")


class CostCapTests(unittest.TestCase):
    """--max-spend hard-stop enforcement."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="si_chip_rlr_cost_"))
        self.pack_path = _write_minimal_pack(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cost_cap_stops_run(self):
        """A scripted client that reports massive per-call usage must trip
        the hard-cap (soft_cap * 2) before the full pack completes."""

        expensive = _ScriptedClient(
            default_text="YES",
            usage={"input_tokens": 10_000_000, "output_tokens": 10_000_000},
        )
        config = rlr.RunnerConfig(
            ability="cost-cap-test",
            eval_pack=self.pack_path,
            matrix_mode="mvp",
            k=4,
            cache_dir=self.tmp / "cache",
            no_live=False,
            max_spend_usd=0.01,
        )
        runner = rlr.RealLLMRunner(config, client=expensive)
        with self.assertRaises(rlr.CostCapExceeded):
            runner.evaluate_matrix()


class AuthErrorTests(unittest.TestCase):
    """Auth errors must propagate as AuthError (fail-fast, not silent)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="si_chip_rlr_auth_"))
        self.pack_path = _write_minimal_pack(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_auth_error_surfaces_explicitly(self):
        class _AuthFailingClient:
            def call(self, model, system, prompt, max_tokens):
                raise rlr.AuthError("HTTP 401: test auth failure")

        config = rlr.RunnerConfig(
            ability="auth-test",
            eval_pack=self.pack_path,
            matrix_mode="mvp",
            k=1,
            cache_dir=self.tmp / "cache",
            no_live=False,
            max_spend_usd=1.0,
            max_prompts_per_cell=1,
        )
        runner = rlr.RealLLMRunner(config, client=_AuthFailingClient())
        with self.assertRaises(rlr.AuthError):
            runner.evaluate_pack(depth="fast", scenario="trigger_basic")


class RunnerOutputShapeTests(unittest.TestCase):
    """The runner output shape must match what G2/G3/G4 helpers consume."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="si_chip_rlr_out_"))
        self.pack_path = _write_minimal_pack(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_matrix_output_has_cells_and_summary(self):
        scripted = _ScriptedClient(default_text="YES")
        config = rlr.RunnerConfig(
            ability="shape-test",
            eval_pack=self.pack_path,
            matrix_mode="mvp",
            k=1,
            cache_dir=self.tmp / "cache",
            no_live=False,
            max_spend_usd=1.0,
            max_prompts_per_cell=1,
        )
        runner = rlr.RealLLMRunner(config, client=scripted)
        out = runner.evaluate_matrix()
        self.assertEqual(out["matrix_mode"], "mvp")
        self.assertIn("cells", out)
        self.assertIn("summary", out)
        # MVP = 2 * 2 * 2 = 8 expected cells.
        self.assertEqual(out["summary"]["total_cells"], 8)
        self.assertEqual(len(out["cells"]), 8)
        for cell in out["cells"]:
            for required in (
                "model",
                "thinking_depth",
                "scenario_pack",
                "prompts_run",
                "passes",
                "pass_rate",
                "pass_at_k",
                "tokens_in",
                "tokens_out",
                "duration_s",
            ):
                self.assertIn(required, cell, f"cell missing {required!r}")


# --- Optional live integration test (env-gated) ------------------------


@unittest.skipUnless(
    os.environ.get("SI_CHIP_REAL_LLM_LIVE") == "1",
    "SI_CHIP_REAL_LLM_LIVE!=1; skipping live integration test",
)
class LiveIntegrationTests(unittest.TestCase):
    """One optional live test against the Veil litellm-local egress.

    Runs ONLY when ``SI_CHIP_REAL_LLM_LIVE=1`` is set. Keeps CI offline.
    """

    def test_live_haiku_one_call(self):
        tmp = Path(tempfile.mkdtemp(prefix="si_chip_rlr_live_"))
        try:
            pack = _write_minimal_pack(tmp)
            config = rlr.RunnerConfig(
                ability="live-haiku",
                eval_pack=pack,
                matrix_mode="mvp",
                k=1,
                cache_dir=tmp / "cache",
                max_spend_usd=0.05,
                max_prompts_per_cell=1,
            )
            runner = rlr.RealLLMRunner(config)
            out = runner.evaluate_pack(depth="fast", scenario="trigger_basic")
            self.assertIn("cell", out)
            self.assertGreaterEqual(out["cell"]["prompts_run"], 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
