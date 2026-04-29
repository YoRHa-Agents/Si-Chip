"""
Round 14 core_goal_test_pack runner.

Reads .local/dogfood/2026-04-29/abilities/si-chip/core_goal_test_pack.yaml,
runs each case as a subprocess, verifies expected_shape, and emits a
machine-readable summary to .local/dogfood/2026-04-29/round_14/raw/core_goal_test_pack_run.json.

Deterministic: every case is a deterministic CLI invocation. No LLM / RNG.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
PACK_PATH = REPO_ROOT / ".local/dogfood/2026-04-29/abilities/si-chip/core_goal_test_pack.yaml"
OUT_PATH = REPO_ROOT / ".local/dogfood/2026-04-29/round_14/raw/core_goal_test_pack_run.json"


def _run_shell(cmd: str) -> tuple[int, str, str]:
    """Run a shell command and capture exit code + stdout + stderr."""
    proc = subprocess.run(
        cmd,
        shell=True,
        executable="/bin/bash",
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _evaluate_case(case: dict) -> dict:
    """Run one case; return a structured verdict dict."""
    case_id = case["case_id"]
    prompt = case["prompt"]
    expected = case["expected_shape"]

    started = time.time()
    exit_code, stdout, stderr = _run_shell(prompt)
    wall = time.time() - started

    checks: dict[str, bool] = {}

    if "exit_code" in expected:
        checks["exit_code"] = (exit_code == expected["exit_code"])

    if "stdout_contains" in expected:
        missing = [s for s in expected["stdout_contains"] if s not in stdout]
        checks["stdout_contains"] = (len(missing) == 0)

    if "all_4_exit_zero" in expected and expected["all_4_exit_zero"] is True:
        checks["all_4_exit_zero"] = (exit_code == 0)

    if "both_verdicts" in expected:
        wanted_verdict = expected["both_verdicts"]
        checks["both_verdicts"] = (
            stdout.count(f'"verdict": "{wanted_verdict}"') == 2
        )

    if "both_blocker_counts" in expected:
        wanted_count = expected["both_blocker_counts"]
        count = 0
        for payload in stdout.split("}{"):
            try:
                start = stdout.find("{")
            except Exception:
                continue
        try:
            parts: list[dict] = []
            _buf = ""
            depth = 0
            for ch in stdout:
                _buf += ch
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            parts.append(json.loads(_buf))
                        except Exception:
                            pass
                        _buf = ""
            blocker_counts = [
                sum(1 for r in p.get("results", []) if r.get("severity") == "BLOCKER")
                for p in parts
            ]
            count = len(blocker_counts)
            all_eleven = all(c == wanted_count for c in blocker_counts)
            checks["both_blocker_counts"] = (count == 2 and all_eleven)
        except Exception as exc:
            checks["both_blocker_counts"] = False

    if "both_exit_zero" in expected and expected["both_exit_zero"] is True:
        checks["both_exit_zero"] = (exit_code == 0)

    if "metadata_le_100" in expected or "body_le_5000" in expected or "pass" in expected:
        try:
            parsed = json.loads(stdout.strip().splitlines()[-1])
            if "metadata_le_100" in expected:
                checks["metadata_le_100"] = (
                    parsed.get("metadata_tokens") is not None
                    and parsed["metadata_tokens"] <= 100
                )
            if "body_le_5000" in expected:
                checks["body_le_5000"] = (
                    parsed.get("body_tokens") is not None
                    and parsed["body_tokens"] <= 5000
                )
            if "pass" in expected:
                checks["pass"] = bool(parsed.get("pass") is True)
        except Exception:
            if "metadata_le_100" in expected:
                checks["metadata_le_100"] = False
            if "body_le_5000" in expected:
                checks["body_le_5000"] = False
            if "pass" in expected:
                checks["pass"] = False

    if "file_count" in expected:
        lines = [ln for ln in stdout.splitlines() if ln.strip()]
        checks["file_count"] = (len(lines) == expected["file_count"])

    case_passed = bool(checks) and all(checks.values())
    return {
        "case_id": case_id,
        "prompt": prompt,
        "exit_code": exit_code,
        "wall_seconds": round(wall, 4),
        "stdout_excerpt": stdout[:400],
        "stderr_excerpt": stderr[:400],
        "expected_shape": expected,
        "checks": checks,
        "passed": case_passed,
    }


def main() -> int:
    with PACK_PATH.open() as fh:
        pack = yaml.safe_load(fh)

    case_results = [_evaluate_case(c) for c in pack["cases"]]
    cases_total = len(case_results)
    cases_passed = sum(1 for r in case_results if r["passed"])
    c0 = cases_passed / cases_total if cases_total else 0.0

    summary = {
        "ability_id": pack["ability_id"],
        "pack_version": pack["pack_version"],
        "spec_version": pack["spec_version"],
        "pack_path": str(PACK_PATH.relative_to(REPO_ROOT)),
        "cases_total": cases_total,
        "cases_passed": cases_passed,
        "c0_core_goal_pass_rate": c0,
        "c0_must_equal_1_0": (abs(c0 - 1.0) < 1e-9),
        "failed_case_ids": [r["case_id"] for r in case_results if not r["passed"]],
        "cases": case_results,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    print(json.dumps({
        "c0": c0,
        "cases_total": cases_total,
        "cases_passed": cases_passed,
        "failed": summary["failed_case_ids"],
    }))
    return 0 if summary["c0_must_equal_1_0"] else 1


if __name__ == "__main__":
    sys.exit(main())
