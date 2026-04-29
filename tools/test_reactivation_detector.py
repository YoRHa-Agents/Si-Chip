#!/usr/bin/env python3
"""Unit tests for ``tools/reactivation_detector.py`` (Round 12 §6.4 fill).

Workspace rule "Mandatory Verification": the §6.4 reactivation
trigger detector landed in Round 12 MUST carry tests. These tests
exercise every trigger's positive + negative path, the boundary
behaviour at the spec §6.4 thresholds, the integration
``detect_reactivation`` against the real Si-Chip Round-11 evidence
triple (clean keep → 0 triggers fired), the integration against a
synthetic ``half_retired`` profile (≥ 1 trigger fired), and the CLI
exit-code matrix (0 for clean keep / valid wake-up, 2 for unexpected
fire on a keep ability).

Test count: 23 tests across 7 test classes (covers spec §6.4 trigger
1..6 + integration + CLI).

Run::

    python -m pytest tools/test_reactivation_detector.py -q
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

import reactivation_detector as rd  # noqa: E402


# ─────────────────────────── helpers ───────────────────────────


def _write(tmpdir: Path, name: str, body: str) -> Path:
    p = tmpdir / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _profile_yaml(*, intent: str = "test ability", router_floor: str = "composer_2/default", action: str = "keep") -> str:
    """Build a synthetic basic_ability_profile.yaml body."""

    return textwrap.dedent(
        f"""\
        basic_ability:
          id: test-ability
          intent: '{intent}'
          current_surface:
            type: mixed
            path: .agents/skills/test/
            shape_hint: markdown_first
          packaging:
            install_targets:
              cursor: true
              claude_code: true
              codex: false
            source_of_truth: .agents/skills/test/
            generated_targets: []
          lifecycle:
            stage: evaluated
            last_reviewed_at: '2026-04-28'
            next_review_at: '2026-05-28'
          eval_state:
            has_eval_set: true
            has_no_ability_baseline: true
            has_self_eval: true
            has_router_test: true
            has_iteration_delta: true
          metrics:
            task_quality: {{}}
          value_vector:
            task_delta: 0.35
            token_delta: 0.0
            latency_delta: 0.0
            context_delta: 0.0
            path_efficiency_delta: null
            routing_delta: 0.0
            governance_risk_delta: 0.0
          router_floor: {router_floor}
          decision:
            action: {action}
            rationale: 'test'
            risk_flags: []
        """
    )


def _decision_yaml(*, action: str = "keep", router_floor: str = "composer_2/default", value_vector: dict = None, prior_value_vector: dict = None) -> str:
    """Build a synthetic half_retire_decision.yaml body."""

    if value_vector is None:
        value_vector = {
            "task_delta": 0.35,
            "token_delta": 0.0,
            "latency_delta": 0.0,
            "context_delta": 0.0,
            "path_efficiency_delta": None,
            "routing_delta": 0.0,
            "governance_risk_delta": 0.0,
        }
    body = {
        "ability_id": "test-ability",
        "version": "0.0.1",
        "decided_at": "2026-04-28T00:00:00+00:00",
        "decision": action,
        "value_vector": value_vector,
        "simplification": {"applied": []},
        "retained_core": [],
        "review": {
            "next_review_at": "2026-05-28",
            "triggers": list(rd.TRIGGER_IDS),
        },
        "provenance": {
            "round_id": "round_test",
            "prior_router_floor": router_floor,
        },
    }
    if prior_value_vector is not None:
        body["prior_value_vector"] = prior_value_vector
    return yaml.safe_dump(body, sort_keys=False)


def _metrics_yaml(*, pass_rate: float = 0.85) -> str:
    """Build a synthetic metrics_report.yaml body."""

    body = {
        "metrics": {
            "task_quality": {
                "T1_pass_rate": pass_rate,
                "T2_pass_k": pass_rate ** 4,
                "T3_baseline_delta": 0.35,
                "T4_error_recovery_rate": None,
            },
            "context_economy": {},
            "latency_path": {},
            "generalizability": {},
            "usage_cost": {},
            "routing_cost": {},
            "governance_risk": {},
        },
        "summary": {"with_ability_runs": 6, "no_ability_runs": 6, "pass_rate_with": pass_rate, "pass_rate_without": 0.5},
        "provenance": {},
    }
    return yaml.safe_dump(body, sort_keys=False)


# ─────────────────────────── Trigger 1 tests ───────────────────────────


class Trigger1NewModelTaskDeltaTests(unittest.TestCase):
    """Spec §6.4 trigger 1: new_model_no_ability_baseline_gap."""

    def test_no_new_baseline_returns_off(self):
        profile = yaml.safe_load(_profile_yaml())
        metrics = yaml.safe_load(_metrics_yaml())
        r = rd.trigger_new_model_task_delta(profile, metrics, new_baseline_path=None)
        self.assertEqual(r["trigger"], "new_model_no_ability_baseline_gap")
        self.assertFalse(r["triggered"])
        self.assertIn("no new baseline", r["reason"])

    def test_fires_when_new_baseline_drops_pass_rate(self):
        """New baseline at 0.40 vs current with-ability 0.85 → delta=0.45 ≥ 0.10."""

        tmp = Path(tempfile.mkdtemp())
        new_baseline = _write(
            tmp, "new_baseline.json",
            json.dumps({"pass_rate": 0.40}),
        )
        profile = yaml.safe_load(_profile_yaml())
        metrics = yaml.safe_load(_metrics_yaml(pass_rate=0.85))
        r = rd.trigger_new_model_task_delta(
            profile, metrics, new_baseline_path=new_baseline,
        )
        self.assertTrue(r["triggered"], msg=r["reason"])
        self.assertAlmostEqual(r["evidence"]["new_task_delta"], 0.45, places=4)

    def test_does_not_fire_below_threshold(self):
        """New baseline at 0.80 vs current 0.85 → delta=0.05 < 0.10."""

        tmp = Path(tempfile.mkdtemp())
        new_baseline = _write(
            tmp, "new_baseline.json", json.dumps({"pass_rate": 0.80}),
        )
        profile = yaml.safe_load(_profile_yaml())
        metrics = yaml.safe_load(_metrics_yaml(pass_rate=0.85))
        r = rd.trigger_new_model_task_delta(profile, metrics, new_baseline_path=new_baseline)
        self.assertFalse(r["triggered"], msg=r["reason"])

    def test_threshold_boundary_just_above(self):
        """delta = 0.125 > 0.10 → fires (just above the boundary).

        Note: testing EXACTLY at 0.10 is fraught due to floating-point
        representation (e.g. 0.85 - 0.75 = 0.09999...). We pick values
        whose subtraction is exactly representable in float to avoid
        the trap, and verify the strict ``>=`` boundary at +0.125.
        """

        tmp = Path(tempfile.mkdtemp())
        new_baseline = _write(
            tmp, "new_baseline.json", json.dumps({"pass_rate": 0.5}),
        )
        profile = yaml.safe_load(_profile_yaml())
        metrics = yaml.safe_load(_metrics_yaml(pass_rate=0.625))
        r = rd.trigger_new_model_task_delta(
            profile, metrics, new_baseline_path=new_baseline,
        )
        self.assertTrue(r["triggered"], msg=r["reason"])
        self.assertAlmostEqual(r["evidence"]["new_task_delta"], 0.125, places=4)

    def test_accepts_aggregates_mean_pass_rate_shape(self):
        """summary.json with aggregates.mean_pass_rate is also accepted."""

        tmp = Path(tempfile.mkdtemp())
        new_baseline = _write(
            tmp, "summary.json",
            json.dumps({"aggregates": {"mean_pass_rate": 0.40}}),
        )
        profile = yaml.safe_load(_profile_yaml())
        metrics = yaml.safe_load(_metrics_yaml(pass_rate=0.85))
        r = rd.trigger_new_model_task_delta(profile, metrics, new_baseline_path=new_baseline)
        self.assertTrue(r["triggered"], msg=r["reason"])


# ─────────────────────────── Trigger 2 tests ───────────────────────────


class Trigger2NewScenarioMatchTests(unittest.TestCase):
    """Spec §6.4 trigger 2: new_scenario_or_domain_match."""

    def test_no_catalog_returns_off(self):
        profile = yaml.safe_load(_profile_yaml())
        r = rd.trigger_new_scenario_or_domain_match(profile, scenario_catalog_path=None)
        self.assertEqual(r["trigger"], "new_scenario_or_domain_match")
        self.assertFalse(r["triggered"])
        self.assertIn("no scenario catalog", r["reason"])

    def test_fires_on_high_overlap_scenario(self):
        tmp = Path(tempfile.mkdtemp())
        catalog = _write(
            tmp, "catalog.json",
            json.dumps([
                {"scenario_id": "s1", "intent_text": "test ability for production"},
                {"scenario_id": "s2", "intent_text": "wholly different topic foo bar"},
            ]),
        )
        profile = yaml.safe_load(_profile_yaml(intent="test ability for production usage"))
        r = rd.trigger_new_scenario_or_domain_match(profile, scenario_catalog_path=catalog)
        self.assertTrue(r["triggered"], msg=r["reason"])
        self.assertEqual(r["evidence"]["top_matches"][0]["scenario_id"], "s1")

    def test_does_not_fire_on_low_overlap(self):
        tmp = Path(tempfile.mkdtemp())
        catalog = _write(
            tmp, "catalog.json",
            json.dumps([{"scenario_id": "x", "intent_text": "completely unrelated topic foo"}]),
        )
        profile = yaml.safe_load(_profile_yaml(intent="test ability for production"))
        r = rd.trigger_new_scenario_or_domain_match(profile, scenario_catalog_path=catalog)
        self.assertFalse(r["triggered"], msg=r["reason"])


# ─────────────────────────── Trigger 3 tests ───────────────────────────


class Trigger3RouterFloorDropTests(unittest.TestCase):
    """Spec §6.4 trigger 3: router_test_requires_ability_for_cheap_model."""

    def test_drop_fires(self):
        r = rd.trigger_router_floor_drop("composer_2/fast", "composer_2/default")
        self.assertEqual(r["trigger"], "router_test_requires_ability_for_cheap_model")
        self.assertTrue(r["triggered"])
        self.assertIn("drops", r["reason"])
        self.assertEqual(r["evidence"]["drop_steps"], 1)

    def test_unchanged_does_not_fire(self):
        r = rd.trigger_router_floor_drop("composer_2/default", "composer_2/default")
        self.assertFalse(r["triggered"])

    def test_rise_does_not_fire(self):
        """A more-expensive floor is NOT a wake-up signal."""

        r = rd.trigger_router_floor_drop("sonnet_4_6/default", "composer_2/fast")
        self.assertFalse(r["triggered"])

    def test_unknown_tier_returns_off_with_reason(self):
        r = rd.trigger_router_floor_drop("imaginary/tier", "composer_2/default")
        self.assertFalse(r["triggered"])
        self.assertIn("unknown to tier ordering", r["reason"])


# ─────────────────────────── Trigger 4 tests ───────────────────────────


class Trigger4EfficiencyAxisSignificantTests(unittest.TestCase):
    """Spec §6.4 trigger 4: efficiency_axis_becomes_significant."""

    def test_positive_jump_above_threshold_fires(self):
        cur = {"context_delta": 0.30, "token_delta": 0.0, "latency_delta": 0.0}
        prior = {"context_delta": -0.05, "token_delta": 0.0, "latency_delta": 0.0}
        r = rd.trigger_efficiency_axis_significant(cur, prior)
        self.assertEqual(r["trigger"], "efficiency_axis_becomes_significant")
        self.assertTrue(r["triggered"])
        self.assertIn("context_delta", r["evidence"]["fired_axes"])

    def test_below_threshold_does_not_fire(self):
        cur = {"context_delta": 0.10, "token_delta": 0.10, "latency_delta": 0.10}
        prior = {"context_delta": 0.0, "token_delta": 0.0, "latency_delta": 0.0}
        r = rd.trigger_efficiency_axis_significant(cur, prior)
        self.assertFalse(r["triggered"])

    def test_threshold_boundary_inclusive(self):
        cur = {"context_delta": 0.25, "token_delta": 0.0, "latency_delta": 0.0}
        prior = {"context_delta": 0.0, "token_delta": 0.0, "latency_delta": 0.0}
        r = rd.trigger_efficiency_axis_significant(cur, prior)
        self.assertTrue(r["triggered"])

    def test_negative_movement_does_not_fire(self):
        """Degradation (negative movement) is handled by §6.2, not §6.4."""

        cur = {"context_delta": -0.5, "token_delta": 0.0, "latency_delta": 0.0}
        prior = {"context_delta": 0.0, "token_delta": 0.0, "latency_delta": 0.0}
        r = rd.trigger_efficiency_axis_significant(cur, prior)
        self.assertFalse(r["triggered"])

    def test_null_axis_handled(self):
        cur = {"context_delta": None, "token_delta": 0.30, "latency_delta": 0.0}
        prior = {"context_delta": None, "token_delta": 0.0, "latency_delta": 0.0}
        r = rd.trigger_efficiency_axis_significant(cur, prior)
        self.assertTrue(r["triggered"])
        self.assertEqual(r["evidence"]["fired_axes"], ["token_delta"])


# ─────────────────────────── Trigger 5 tests ───────────────────────────


class Trigger5UpstreamApiChangeTests(unittest.TestCase):
    """Spec §6.4 trigger 5: upstream_api_change_wrapper_stabilizes."""

    def test_no_log_returns_off(self):
        r = rd.trigger_upstream_api_change(wrapper_stability_log_path=None)
        self.assertEqual(r["trigger"], "upstream_api_change_wrapper_stabilizes")
        self.assertFalse(r["triggered"])
        self.assertIn("no api-change log", r["reason"])

    def test_fires_when_wrapper_beats_base(self):
        tmp = Path(tempfile.mkdtemp())
        log = _write(
            tmp, "stability.json",
            json.dumps({
                "events": [
                    {"ts": "2026-04-28", "api": "x",
                     "wrapper_pass_rate_post": 0.91, "base_pass_rate_post": 0.74},
                ]
            }),
        )
        r = rd.trigger_upstream_api_change(wrapper_stability_log_path=log)
        self.assertTrue(r["triggered"])

    def test_does_not_fire_when_delta_too_small(self):
        tmp = Path(tempfile.mkdtemp())
        log = _write(
            tmp, "stability.json",
            json.dumps({
                "events": [
                    {"ts": "2026-04-28", "wrapper_pass_rate_post": 0.91, "base_pass_rate_post": 0.85},
                ]
            }),
        )
        r = rd.trigger_upstream_api_change(wrapper_stability_log_path=log)
        self.assertFalse(r["triggered"])


# ─────────────────────────── Trigger 6 tests ───────────────────────────


class Trigger6ManualInvocationReboundTests(unittest.TestCase):
    """Spec §6.4 trigger 6: manual_invocation_rebound."""

    def test_no_log_returns_off(self):
        r = rd.trigger_manual_invocation_rebound(invocation_log_path=None)
        self.assertEqual(r["trigger"], "manual_invocation_rebound")
        self.assertFalse(r["triggered"])
        self.assertIn("no invocation log", r["reason"])

    def test_fires_at_threshold_5(self):
        tmp = Path(tempfile.mkdtemp())
        log = _write(
            tmp, "invoc.json",
            json.dumps({
                "invocations": [
                    {"ts": f"2026-04-{20 + i:02d}", "manual": True} for i in range(5)
                ]
            }),
        )
        r = rd.trigger_manual_invocation_rebound(
            invocation_log_path=log, today="2026-04-28",
        )
        self.assertTrue(r["triggered"], msg=r["reason"])
        self.assertEqual(r["evidence"]["n_manual_in_window"], 5)

    def test_below_threshold(self):
        tmp = Path(tempfile.mkdtemp())
        log = _write(
            tmp, "invoc.json",
            json.dumps({
                "invocations": [
                    {"ts": "2026-04-25", "manual": True},
                    {"ts": "2026-04-26", "manual": True},
                ]
            }),
        )
        r = rd.trigger_manual_invocation_rebound(invocation_log_path=log, today="2026-04-28")
        self.assertFalse(r["triggered"])

    def test_excludes_outside_window(self):
        tmp = Path(tempfile.mkdtemp())
        log = _write(
            tmp, "invoc.json",
            json.dumps({
                "invocations": [
                    # 5 manual invocations, but all > 30 days old.
                    {"ts": "2026-01-01", "manual": True},
                    {"ts": "2026-01-02", "manual": True},
                    {"ts": "2026-01-03", "manual": True},
                    {"ts": "2026-01-04", "manual": True},
                    {"ts": "2026-01-05", "manual": True},
                ]
            }),
        )
        r = rd.trigger_manual_invocation_rebound(invocation_log_path=log, today="2026-04-28")
        self.assertFalse(r["triggered"])


# ─────────────────────────── Integration tests ───────────────────────────


class DetectReactivationIntegrationTests(unittest.TestCase):
    """Top-level :func:`detect_reactivation` integration."""

    def test_clean_keep_yields_zero_triggers(self):
        tmp = Path(tempfile.mkdtemp())
        profile = _write(tmp, "basic_ability_profile.yaml", _profile_yaml(action="keep"))
        decision = _write(tmp, "half_retire_decision.yaml", _decision_yaml(action="keep"))
        metrics = _write(tmp, "metrics_report.yaml", _metrics_yaml())
        verdict = rd.detect_reactivation(profile, decision, metrics)
        self.assertEqual(verdict["triggered_count"], 0)
        self.assertEqual(verdict["triggered_names"], [])
        self.assertEqual(verdict["decision_action"], "keep")
        # All 6 trigger IDs present.
        self.assertEqual(sorted(verdict["per_trigger"].keys()), sorted(rd.TRIGGER_IDS))

    def test_synthetic_half_retired_with_router_drop_fires(self):
        tmp = Path(tempfile.mkdtemp())
        profile = _write(
            tmp, "basic_ability_profile.yaml",
            _profile_yaml(action="half_retired", router_floor="composer_2/fast"),
        )
        decision_body = yaml.safe_load(_decision_yaml(action="half_retired"))
        decision_body["provenance"]["prior_router_floor"] = "composer_2/default"
        decision = _write(tmp, "half_retire_decision.yaml", yaml.safe_dump(decision_body))
        metrics = _write(tmp, "metrics_report.yaml", _metrics_yaml())
        verdict = rd.detect_reactivation(profile, decision, metrics)
        self.assertGreaterEqual(verdict["triggered_count"], 1)
        self.assertIn(
            "router_test_requires_ability_for_cheap_model", verdict["triggered_names"]
        )
        self.assertEqual(verdict["decision_action"], "half_retired")

    def test_real_si_chip_round_11_evidence_yields_zero_triggers(self):
        """Real Round-11 evidence is decision=keep with no §6.4 fires."""

        round_dir = _REPO_ROOT / ".local" / "dogfood" / "2026-04-28" / "round_11"
        if not round_dir.exists():
            self.skipTest("Round 11 evidence missing in checkout")
        profile = round_dir / "basic_ability_profile.yaml"
        decision = round_dir / "half_retire_decision.yaml"
        metrics = round_dir / "metrics_report.yaml"
        verdict = rd.detect_reactivation(profile, decision, metrics)
        self.assertEqual(
            verdict["triggered_count"], 0,
            msg=f"unexpected triggers fired: {verdict['triggered_names']}",
        )
        self.assertEqual(verdict["decision_action"], "keep")
        self.assertEqual(verdict["notes"], [])

    def test_missing_profile_raises(self):
        with self.assertRaises(FileNotFoundError):
            rd.detect_reactivation(
                Path("/does/not/exist/profile.yaml"),
                Path("/does/not/exist/decision.yaml"),
                Path("/does/not/exist/metrics.yaml"),
            )


# ─────────────────────────── CLI exit-code tests ───────────────────────────


class CliExitCodeTests(unittest.TestCase):
    """CLI surface contract: exit 0 vs 2."""

    def test_check_real_round_11_exits_0(self):
        round_dir = _REPO_ROOT / ".local" / "dogfood" / "2026-04-28" / "round_11"
        if not round_dir.exists():
            self.skipTest("Round 11 evidence missing in checkout")
        profile = round_dir / "basic_ability_profile.yaml"
        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools" / "reactivation_detector.py"),
                "--check", str(profile),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["triggered_count"], 0)
        self.assertEqual(payload["decision_action"], "keep")

    def test_unexpected_fire_on_keep_exits_2(self):
        """Synthesise a keep ability + scenario catalog that fires trigger 2."""

        tmp = Path(tempfile.mkdtemp())
        profile = _write(
            tmp, "basic_ability_profile.yaml",
            _profile_yaml(action="keep", intent="reactivation review wake check"),
        )
        decision = _write(
            tmp, "half_retire_decision.yaml",
            _decision_yaml(action="keep"),
        )
        metrics = _write(tmp, "metrics_report.yaml", _metrics_yaml())
        catalog = _write(
            tmp, "scenario_catalog.json",
            json.dumps([
                {"scenario_id": "match",
                 "intent_text": "reactivation review wake check workflow"},
            ]),
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools" / "reactivation_detector.py"),
                "--check", str(profile),
                "--scenario-catalog", str(catalog),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertGreaterEqual(payload["triggered_count"], 1)
        self.assertIn(
            "new_scenario_or_domain_match", payload["triggered_names"]
        )

    def test_explicit_half_retired_with_fire_exits_0(self):
        """A half_retired ability with a fired trigger is the EXPECTED wake-up."""

        tmp = Path(tempfile.mkdtemp())
        profile = _write(
            tmp, "basic_ability_profile.yaml",
            _profile_yaml(
                action="half_retired",
                intent="check reactivation triggers wake up",
            ),
        )
        decision = _write(
            tmp, "half_retire_decision.yaml",
            _decision_yaml(action="half_retired"),
        )
        metrics = _write(tmp, "metrics_report.yaml", _metrics_yaml())
        catalog = _write(
            tmp, "scenario_catalog.json",
            json.dumps([
                {"scenario_id": "match",
                 "intent_text": "check reactivation triggers wake up workflow"},
            ]),
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "tools" / "reactivation_detector.py"),
                "--check", str(profile),
                "--scenario-catalog", str(catalog),
                "--json",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        # Should exit 0 because half_retired + fired = expected wake-up.
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertGreaterEqual(payload["triggered_count"], 1)
        self.assertEqual(payload["decision_action"], "half_retired")


if __name__ == "__main__":
    unittest.main(verbosity=2)
