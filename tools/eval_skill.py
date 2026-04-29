#!/usr/bin/env python3
"""Generic per-ability evaluation harness for Si-Chip spec v0.3.0-rc1.

Replaces ability-specific 768-line harnesses (e.g.
``eval_chip_usage_helper.py``) with a pluggable entry point that any new
BasicAbility can use by supplying only its vocabulary yaml + eval_pack +
core_goal_test_pack + test runner command. Per R11 §7 design brief the
saving is ~600 LoC per new ability.

The harness wires four measurement surfaces together:

1. **Trigger eval (D6 R1/R2/R3/R4)** — delegates to
   ``tools/cjk_trigger_eval.py::evaluate_pack``.
2. **Token / context economy (D2 C1/C2/C4)** — subprocesses
   ``.agents/skills/si-chip/scripts/count_tokens.py`` (the canonical
   C1/C2 counter; spec §3.2 frozen constraint #3).
3. **Functional tests + wall-clock (D1 T1/T3 + D3 L1/L2)** — runs the
   ability-specific test command N times under ``--test-runner-cwd``.
4. **Core-goal test pack (C0, v0.3.0 §14 top-level invariant)** —
   executes each case via per-case command (if the pack supplies one)
   or the global test runner. Emits ``core_goal_check`` block
   mirroring ``iteration_delta_report.template.yaml``.

R6 7×37 placeholder discipline (spec §3.2 frozen #2): every one of the
37 sub-metric keys is emitted; unmeasured ones are ``null``. The
``R6_KEYS`` constant enumerates them verbatim from spec §3.1.

CLI::

    python tools/eval_skill.py \\
        --ability <id> \\
        --skill-md <path/to/SKILL.md> \\
        --vocabulary <path/to/vocabulary.yaml> \\
        --eval-pack <path/to/eval_pack.yaml> \\
        --core-goal-test-pack <path/to/core_goal_test_pack.yaml> \\
        --test-runner-cmd "<shell cmd>" \\
        --test-runner-cwd <path> \\
        --runs 3 \\
        --out <path/to/metrics_report.yaml> \\
        [--round-kind code_change|measurement_only|ship_prep|maintenance] \\
        [--baseline-runner-cmd "<shell cmd>"]

Exit code is ``0`` on successful measurement (even if thresholds would
fail; ``tools/spec_validator.py`` is the gate). A ``C0 < 1.0`` fills
``core_goal_check.rollback_required = true`` per §15.3 universal
invariant but does NOT change the exit code — the rollback action is
the operator's to take.

Workspace-rule notes
--------------------
* "No Silent Failures": missing paths / unknown round_kind raise
  explicitly. Token-counter / test-runner subprocess failures propagate
  via return codes captured in the metrics_report.
* "Mandatory Verification": sibling test ``tools/test_eval_skill.py``
  covers R6_KEYS 37-count + per-dim counts, ROUND_KINDS size,
  core_goal_test_pack runner happy-path and failure path, and the
  metrics_report R6 placeholder invariant.
"""

from __future__ import annotations

import argparse
import json
import logging
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

# Ensure sibling tools import (tools/ is not a package; inject repo root).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.cjk_trigger_eval import (  # noqa: E402
    Vocabulary,
    evaluate_pack as cjk_evaluate_pack,
)
from tools.round_kind import (  # noqa: E402
    REQUIRED_C0_VALUE,
    ROUND_KINDS,
    validate_round_kind,
)

LOGGER = logging.getLogger("si_chip.eval_skill")

SCRIPT_VERSION = "0.1.0"

# --- R6 7×37 constant ---------------------------------------------------

R6_KEYS: Dict[str, List[str]] = {
    "task_quality": [
        "T1_pass_rate",
        "T2_pass_k",
        "T3_baseline_delta",
        "T4_error_recovery_rate",
    ],
    "context_economy": [
        "C1_metadata_tokens",
        "C2_body_tokens",
        "C3_resolved_tokens",
        "C4_per_invocation_footprint",
        "C5_context_rot_risk",
        "C6_scope_overlap_score",
    ],
    "latency_path": [
        "L1_wall_clock_p50",
        "L2_wall_clock_p95",
        "L3_step_count",
        "L4_redundant_call_ratio",
        "L5_detour_index",
        "L6_replanning_rate",
        "L7_think_act_split",
    ],
    "generalizability": [
        "G1_cross_model_pass_matrix",
        "G2_cross_domain_transfer_pass",
        "G3_OOD_robustness",
        "G4_model_version_stability",
    ],
    "usage_cost": [
        "U1_description_readability",
        "U2_first_time_success_rate",
        "U3_setup_steps_count",
        "U4_time_to_first_success",
    ],
    "routing_cost": [
        "R1_trigger_precision",
        "R2_trigger_recall",
        "R3_trigger_F1",
        "R4_near_miss_FP_rate",
        "R5_router_floor",
        "R6_routing_latency_p95",
        "R7_routing_token_overhead",
        "R8_description_competition_index",
    ],
    "governance_risk": [
        "V1_permission_scope",
        "V2_credential_surface",
        "V3_drift_signal",
        "V4_staleness_days",
    ],
}

DEFAULT_COUNT_TOKENS_SCRIPT = (
    REPO_ROOT / ".agents" / "skills" / "si-chip" / "scripts" / "count_tokens.py"
)


# --- Configuration dataclass -------------------------------------------

@dataclass
class EvalSkillConfig:
    """Holds every CLI-supplied path / command needed to run one round."""

    ability: str
    skill_md: Path
    vocabulary: Path
    eval_pack: Path
    core_goal_test_pack: Path
    test_runner_cmd: str
    test_runner_cwd: Path
    runs: int = 3
    out: Optional[Path] = None
    round_kind: Optional[str] = None
    baseline_runner_cmd: Optional[str] = None
    count_tokens_script: Path = field(
        default_factory=lambda: DEFAULT_COUNT_TOKENS_SCRIPT
    )

    def validate(self) -> None:
        """Fail fast on missing paths / invalid round_kind.

        Raises ``FileNotFoundError`` / ``ValueError`` per workspace
        rule "No Silent Failures".
        """

        required_files: Dict[str, Path] = {
            "skill_md": self.skill_md,
            "vocabulary": self.vocabulary,
            "eval_pack": self.eval_pack,
            "core_goal_test_pack": self.core_goal_test_pack,
        }
        for name, path in required_files.items():
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"{name} path does not exist: {path}"
                )
        if not Path(self.test_runner_cwd).is_dir():
            raise NotADirectoryError(
                f"test_runner_cwd is not a directory: {self.test_runner_cwd}"
            )
        if self.round_kind is not None and not validate_round_kind(
            self.round_kind
        ):
            raise ValueError(
                f"unknown round_kind {self.round_kind!r}; expected one of "
                f"{sorted(ROUND_KINDS)}"
            )
        if self.runs <= 0:
            raise ValueError(f"runs must be >= 1, got {self.runs}")


# --- R6 placeholder construction --------------------------------------

def build_r6_placeholder() -> Dict[str, Dict[str, Any]]:
    """Return a dict with all 37 keys set to ``None`` (placeholders).

    Consumers fill in measured values; unmeasured keys remain ``None``
    per spec §3.2 frozen constraint #2.
    """

    return {
        dim: {key: None for key in keys}
        for dim, keys in R6_KEYS.items()
    }


# --- Token / context ---------------------------------------------------

def _count_tokens_via_subprocess(
    skill_md: Path, count_tokens_script: Path
) -> Dict[str, Any]:
    """Run ``count_tokens.py --file <skill> --both --json`` and parse."""

    if not count_tokens_script.exists():
        raise FileNotFoundError(
            f"count_tokens.py script not found: {count_tokens_script}"
        )
    result = subprocess.run(
        [
            sys.executable,
            str(count_tokens_script),
            "--file",
            str(skill_md),
            "--both",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        raise RuntimeError(
            f"count_tokens.py produced no stdout for {skill_md}; "
            f"stderr: {result.stderr}"
        )
    return json.loads(result.stdout)


# --- Functional tests --------------------------------------------------

def _run_test_command_once(
    cmd: str, cwd: Path, timeout_s: int = 300
) -> Dict[str, Any]:
    """Execute one invocation of the ability's test runner.

    Returns a dict with ``exit_code``, ``duration_s``, ``passed``,
    ``stdout_tail``, ``stderr_tail``. ``passed`` is ``exit_code == 0``.
    """

    tokens = shlex.split(cmd)
    if not tokens:
        raise ValueError("test_runner_cmd expanded to empty token list")
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            tokens,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        t1 = time.perf_counter()
        LOGGER.warning("test_runner_cmd timed out: %s", exc)
        return {
            "exit_code": -1,
            "duration_s": round(t1 - t0, 4),
            "passed": False,
            "stdout_tail": "",
            "stderr_tail": f"TIMEOUT after {timeout_s}s",
        }
    t1 = time.perf_counter()
    return {
        "exit_code": result.returncode,
        "duration_s": round(t1 - t0, 4),
        "passed": result.returncode == 0,
        "stdout_tail": (result.stdout or "")[-500:],
        "stderr_tail": (result.stderr or "")[-500:],
    }


def _percentile(values: Sequence[float], pct: float) -> float:
    """Deterministic percentile for short lists (used for L1/L2)."""

    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = min(int(pct * len(ordered)), len(ordered) - 1)
    return ordered[idx]


def run_functional_tests(
    cmd: str, cwd: Path, runs: int
) -> Dict[str, Any]:
    """Run the test command ``runs`` times; return T1 / L1 / L2 / traces."""

    traces: List[Dict[str, Any]] = []
    for i in range(runs):
        trace = _run_test_command_once(cmd, cwd)
        trace["run_index"] = i
        traces.append(trace)
    passed = sum(1 for t in traces if t["passed"])
    durations = [t["duration_s"] for t in traces]
    return {
        "T1_pass_rate": round(passed / runs, 4) if runs > 0 else 0.0,
        "L1_wall_clock_p50": round(_percentile(durations, 0.5), 4),
        "L2_wall_clock_p95": round(_percentile(durations, 0.95), 4),
        "runs": runs,
        "passed": passed,
        "per_run": traces,
    }


# --- Core-goal test pack ----------------------------------------------

def run_core_goal_test_pack(
    pack_path: Path,
    default_runner_cmd: str,
    cwd: Path,
    timeout_s: int = 300,
) -> Dict[str, Any]:
    """Execute every case in the pack; return C0 metrics.

    Each case may define its own ``command`` (or ``case_runner_cmd``)
    field; otherwise ``default_runner_cmd`` is used. The command is
    invoked with ``SI_CHIP_CASE_ID`` / ``SI_CHIP_CASE_PROMPT`` in env
    so runners can route per-case without parsing CLI args.

    A case passes when the runner exits 0. The overall C0 pass rate is
    ``cases_passed / cases_total``; spec §14.3 locks the target at 1.0.
    """

    pack_path = Path(pack_path)
    if not pack_path.exists():
        raise FileNotFoundError(f"core_goal_test_pack not found: {pack_path}")
    with pack_path.open("r", encoding="utf-8") as fh:
        pack = yaml.safe_load(fh) or {}
    cases = pack.get("cases") or []
    if not isinstance(cases, list):
        raise ValueError(
            f"core_goal_test_pack cases must be a list, got {type(cases).__name__}"
        )
    if not cases:
        LOGGER.warning(
            "core_goal_test_pack has zero cases; C0 pass_rate will be 0.0"
        )

    per_case: List[Dict[str, Any]] = []
    passed = 0
    for idx, case in enumerate(cases):
        case_id = str(case.get("id") or f"case_{idx}")
        prompt = str(case.get("prompt") or "")
        runner_cmd = (
            case.get("command")
            or case.get("case_runner_cmd")
            or default_runner_cmd
        )
        if not runner_cmd:
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "exit_code": None,
                    "error": "no runner command (case or default)",
                }
            )
            continue
        try:
            tokens = shlex.split(runner_cmd)
        except ValueError as exc:
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "exit_code": None,
                    "error": f"shlex.split failed: {exc}",
                }
            )
            continue
        env_updates = {
            "SI_CHIP_CASE_ID": case_id,
            "SI_CHIP_CASE_PROMPT": prompt,
        }
        import os

        env = os.environ.copy()
        env.update(env_updates)
        try:
            result = subprocess.run(
                tokens,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                check=False,
            )
            case_passed = result.returncode == 0
            if case_passed:
                passed += 1
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": case_passed,
                    "exit_code": result.returncode,
                    "stdout_tail": (result.stdout or "")[-300:],
                    "stderr_tail": (result.stderr or "")[-300:],
                }
            )
        except subprocess.TimeoutExpired as exc:
            LOGGER.warning(
                "core_goal case %s timed out after %ss", case_id, timeout_s
            )
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "exit_code": -1,
                    "error": f"timeout after {timeout_s}s: {exc}",
                }
            )

    total = len(cases)
    pass_rate = round(passed / total, 4) if total > 0 else 0.0
    return {
        "pass_rate": pass_rate,
        "cases_passed": passed,
        "cases_total": total,
        "per_case": per_case,
    }


def build_core_goal_check(
    c0_pass_rate: float,
    cases_passed: int,
    cases_total: int,
    prior_c0_pass_rate: Optional[float],
    round_kind: Optional[str],
    failed_case_ids: Sequence[str],
) -> Dict[str, Any]:
    """Construct the ``core_goal_check`` block per §14.3 / §15.3.

    Per spec §15.3 the C0 MUST = 1.0 invariant is **universal** across
    all four round_kinds. Any ``c0_pass_rate < REQUIRED_C0_VALUE`` sets
    ``rollback_required = True`` regardless of round_kind (cross-check
    R11 §4 + spec §15.3). A drop relative to ``prior_c0_pass_rate``
    sets ``regression_detected = True`` independently (it's possible to
    stay at 1.0 if prior was already 1.0 but still fail the
    monotonicity axis if prior was somehow >1 — guarded here for
    completeness).
    """

    regression_detected = (
        prior_c0_pass_rate is not None
        and c0_pass_rate < prior_c0_pass_rate
    )
    below_target = c0_pass_rate < REQUIRED_C0_VALUE
    rollback_required = bool(below_target or regression_detected)
    verdict_pass = (
        c0_pass_rate >= REQUIRED_C0_VALUE and not regression_detected
    )
    return {
        "C0_pass_rate_current": c0_pass_rate,
        "C0_pass_rate_prior": prior_c0_pass_rate,
        "cases_passed": cases_passed,
        "cases_total": cases_total,
        "failed_case_ids": list(failed_case_ids),
        "regression_detected": regression_detected,
        "rollback_required": rollback_required,
        "round_kind": round_kind,
        "required_c0_value": REQUIRED_C0_VALUE,
        "verdict": {"core_goal_pass": verdict_pass},
        "spec_section": "v0.3.0-rc1 §14.3 / §15.3",
    }


# --- Main evaluation flow ---------------------------------------------

def run_evaluation(
    config: EvalSkillConfig,
    prior_c0_pass_rate: Optional[float] = None,
    skip_functional_tests: bool = False,
) -> Dict[str, Any]:
    """Orchestrate one round of per-ability evaluation.

    Returns a metrics_report dict matching the shape
    ``eval_chip_usage_helper.py`` emits, extended with the new
    ``core_goal_check`` block and ``round_kind`` field per spec
    v0.3.0-rc1 §14 / §15. The dict is also what is written to
    ``config.out`` if supplied.
    """

    config.validate()
    metrics = build_r6_placeholder()

    # --- (1) Trigger eval (D6 R1/R2/R3/R4) ---
    with Path(config.eval_pack).open("r", encoding="utf-8") as fh:
        eval_pack = yaml.safe_load(fh) or {}
    vocab = Vocabulary.from_yaml(Path(config.vocabulary))
    trigger = cjk_evaluate_pack(eval_pack, vocab)
    metrics["routing_cost"]["R1_trigger_precision"] = trigger.precision
    metrics["routing_cost"]["R2_trigger_recall"] = trigger.recall
    metrics["routing_cost"]["R3_trigger_F1"] = trigger.f1
    metrics["routing_cost"]["R4_near_miss_FP_rate"] = trigger.near_miss_fp_rate

    # --- (2) Token / context (D2 C1/C2/C4) ---
    token_info = None
    try:
        token_info = _count_tokens_via_subprocess(
            Path(config.skill_md), Path(config.count_tokens_script)
        )
    except (FileNotFoundError, RuntimeError) as exc:
        LOGGER.warning("token counter unavailable: %s", exc)
    if token_info is not None:
        c1 = token_info.get("metadata_tokens")
        c2 = token_info.get("body_tokens")
        metrics["context_economy"]["C1_metadata_tokens"] = c1
        metrics["context_economy"]["C2_body_tokens"] = c2
        if isinstance(c1, int) and isinstance(c2, int):
            metrics["context_economy"]["C4_per_invocation_footprint"] = c1 + c2

    # --- (3) Functional tests (D1 T1/T3 + D3 L1/L2) ---
    functional_trace: Dict[str, Any] = {}
    if not skip_functional_tests:
        functional_trace = run_functional_tests(
            config.test_runner_cmd,
            Path(config.test_runner_cwd),
            runs=config.runs,
        )
        metrics["task_quality"]["T1_pass_rate"] = functional_trace["T1_pass_rate"]
        metrics["latency_path"]["L1_wall_clock_p50"] = functional_trace[
            "L1_wall_clock_p50"
        ]
        metrics["latency_path"]["L2_wall_clock_p95"] = functional_trace[
            "L2_wall_clock_p95"
        ]

    # --- (3b) T3 baseline delta (if baseline provided) ---
    baseline_trace: Dict[str, Any] = {}
    t3 = None
    if config.baseline_runner_cmd and not skip_functional_tests:
        baseline_trace = run_functional_tests(
            config.baseline_runner_cmd,
            Path(config.test_runner_cwd),
            runs=config.runs,
        )
        t3 = round(
            functional_trace.get("T1_pass_rate", 0.0)
            - baseline_trace.get("T1_pass_rate", 0.0),
            4,
        )
    metrics["task_quality"]["T3_baseline_delta"] = t3

    # --- (4) Core-goal test pack (C0) ---
    core_goal_result = run_core_goal_test_pack(
        Path(config.core_goal_test_pack),
        config.test_runner_cmd,
        Path(config.test_runner_cwd),
    )
    failed_case_ids = [
        c["case_id"] for c in core_goal_result["per_case"] if not c["passed"]
    ]
    core_goal_check = build_core_goal_check(
        c0_pass_rate=core_goal_result["pass_rate"],
        cases_passed=core_goal_result["cases_passed"],
        cases_total=core_goal_result["cases_total"],
        prior_c0_pass_rate=prior_c0_pass_rate,
        round_kind=config.round_kind,
        failed_case_ids=failed_case_ids,
    )

    # --- (5) Assemble metrics_report ---
    metrics_report = {
        "schema_version": "0.2.0",
        "script_version": SCRIPT_VERSION,
        "ability_id": config.ability,
        "round_kind": config.round_kind,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metrics": metrics,
        "core_goal": {
            "C0_core_goal_pass_rate": core_goal_result["pass_rate"],
            "cases_passed": core_goal_result["cases_passed"],
            "cases_total": core_goal_result["cases_total"],
            "failed_case_ids": failed_case_ids,
            "per_case": core_goal_result["per_case"],
        },
        "core_goal_check": core_goal_check,
        "trigger_confusion": {
            "tp": trigger.tp,
            "fp": trigger.fp,
            "fn": trigger.fn,
            "tn": trigger.tn,
        },
        "trigger_per_prompt": trigger.per_prompt,
        "token_info": token_info,
        "functional_tests": functional_trace,
        "baseline_tests": baseline_trace or None,
        "spec_section": "v0.3.0-rc1 §3 + §14 + §15",
    }

    # --- (6) Write metrics_report.yaml if --out supplied ---
    if config.out is not None:
        out_path = Path(config.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                metrics_report,
                fh,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
        LOGGER.info("wrote metrics_report to %s", out_path)

    return metrics_report


# --- CLI --------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval_skill",
        description=(
            "Generic Si-Chip per-ability evaluation harness. Produces a "
            "metrics_report.yaml covering R6 7×37 + C0 core_goal_check + "
            "round_kind per spec v0.3.0-rc1."
        ),
    )
    parser.add_argument(
        "--ability", required=True, help="Ability id (BasicAbility.id)"
    )
    parser.add_argument(
        "--skill-md",
        required=True,
        help="Path to the ability's SKILL.md (for C1/C2).",
    )
    parser.add_argument(
        "--vocabulary",
        required=True,
        help="Path to the ability's vocabulary yaml (for R1/R2/R3/R4).",
    )
    parser.add_argument(
        "--eval-pack",
        required=True,
        help="Path to the ability's trigger eval pack yaml.",
    )
    parser.add_argument(
        "--core-goal-test-pack",
        required=True,
        help="Path to the ability's core_goal_test_pack yaml (C0).",
    )
    parser.add_argument(
        "--test-runner-cmd",
        required=True,
        help="Shell command to run functional tests (e.g. 'npm test --silent').",
    )
    parser.add_argument(
        "--test-runner-cwd",
        required=True,
        help="Working directory for the test runner.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of times to run the functional test runner (default 3).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Path to write metrics_report.yaml (optional).",
    )
    parser.add_argument(
        "--round-kind",
        choices=sorted(ROUND_KINDS),
        default=None,
        help="round_kind value per spec §15.1; optional at the harness level.",
    )
    parser.add_argument(
        "--baseline-runner-cmd",
        default=None,
        help="Optional no-ability baseline runner (used for T3 delta).",
    )
    parser.add_argument(
        "--prior-c0-pass-rate",
        type=float,
        default=None,
        help="Prior round's C0 for regression-detection (optional).",
    )
    parser.add_argument(
        "--count-tokens-script",
        default=str(DEFAULT_COUNT_TOKENS_SCRIPT),
        help="Path to count_tokens.py (default: .agents/skills/si-chip/scripts).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config = EvalSkillConfig(
        ability=args.ability,
        skill_md=Path(args.skill_md),
        vocabulary=Path(args.vocabulary),
        eval_pack=Path(args.eval_pack),
        core_goal_test_pack=Path(args.core_goal_test_pack),
        test_runner_cmd=args.test_runner_cmd,
        test_runner_cwd=Path(args.test_runner_cwd),
        runs=args.runs,
        out=Path(args.out) if args.out else None,
        round_kind=args.round_kind,
        baseline_runner_cmd=args.baseline_runner_cmd,
        count_tokens_script=Path(args.count_tokens_script),
    )
    report = run_evaluation(
        config, prior_c0_pass_rate=args.prior_c0_pass_rate
    )

    print(f"eval_skill v{SCRIPT_VERSION} — ability={config.ability}")
    print(f"  round_kind : {report['round_kind']}")
    rc_metrics = report["metrics"]["routing_cost"]
    print(
        "  R3_trigger_F1={} (R1={} R2={} R4={})".format(
            rc_metrics["R3_trigger_F1"],
            rc_metrics["R1_trigger_precision"],
            rc_metrics["R2_trigger_recall"],
            rc_metrics["R4_near_miss_FP_rate"],
        )
    )
    ce_metrics = report["metrics"]["context_economy"]
    print(
        "  C1={} C2={} C4={}".format(
            ce_metrics["C1_metadata_tokens"],
            ce_metrics["C2_body_tokens"],
            ce_metrics["C4_per_invocation_footprint"],
        )
    )
    lp_metrics = report["metrics"]["latency_path"]
    print(
        "  T1={} L1={} L2={}".format(
            report["metrics"]["task_quality"]["T1_pass_rate"],
            lp_metrics["L1_wall_clock_p50"],
            lp_metrics["L2_wall_clock_p95"],
        )
    )
    cg = report["core_goal_check"]
    print(
        "  C0={} (pass_rate, {}/{} cases); rollback_required={}".format(
            cg["C0_pass_rate_current"],
            cg["cases_passed"],
            cg["cases_total"],
            cg["rollback_required"],
        )
    )
    if args.out:
        print(f"  wrote: {args.out}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    sys.exit(main())
