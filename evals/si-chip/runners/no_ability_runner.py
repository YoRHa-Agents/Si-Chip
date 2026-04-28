#!/usr/bin/env python3
"""No-ability baseline runner for the Si-Chip self-eval suite.

Implements spec §8.1 step 2 ("evaluate no-ability baseline vs with-ability")
of `.local/research/spec_v0.1.0.md`. This runner SIMULATES the behavior of
a vanilla model that does NOT have the Si-Chip skill installed: it never
"triggers" Si-Chip, so every `should_trigger` prompt is recorded as a miss
and every `should_not_trigger` prompt is recorded as a correct (negative)
outcome.

DETERMINISTIC SIMULATED BASELINE
================================
These results are DETERMINISTIC SIMULATED outcomes intended for v0.1.0
dogfood scaffolding (S3.W3.B). No LLM calls are made; per-prompt hashes
(SHA-256) drive all simulated quantities so a re-run with the same
``--seed`` and case files yields byte-identical ``result.json`` payloads.
Real-LLM eval substitution is the upgrade path; the per-case
``result.json`` schema and runner CLI are stable so an LLM-backed runner
can be swapped in without changing
``.agents/skills/si-chip/scripts/aggregate_eval.py``.

Output schema (per case)
------------------------
``<out-dir>/<case_id>/result.json`` carries EXACTLY the keys
``aggregate_eval.py`` requires::

    {
      "pass_rate": <float>,
      "pass_k_4": <float>,
      "latency_p95_s": <float>,
      "latency_p50_s": <float>,            # NEW IN ROUND 4 (D3/L1)
      "metadata_tokens": 0,
      "per_invocation_footprint": 1500,
      "trigger_F1": 0.0,
      "router_floor": "n/a (no_ability)",
      "step_count": <int>,                 # NEW IN ROUND 4 (D3/L3)
      "redundant_call_ratio": <float>,     # NEW IN ROUND 4 (D3/L4)
      "prompt_outcomes": [{...}, ...]
    }

A top-level ``<out-dir>/summary.json`` carries cross-case aggregates.

CLI
---
::

    python evals/si-chip/runners/no_ability_runner.py \\
        --cases-dir evals/si-chip/cases/ \\
        --out-dir evals/si-chip/baselines/no_ability/ \\
        [--seed 42] [--verbose]

Notes
-----
* ``pass_k_4`` is computed as ``pass_rate ** 4`` here as a documented
  proxy for true k=4 sampling (we cannot sample without an LLM); when the
  LLM-backed runner replaces this scaffold it should produce a real
  ``pass_k_4`` and overwrite this column. The proxy is preserved so the
  schema stays stable.
* Workspace rule "No Silent Failures": malformed case files raise and the
  process exits non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.no_ability_runner")

SCRIPT_VERSION = "0.1.0"
ROUTER_FLOOR_NO_ABILITY = "n/a (no_ability)"
NO_ABILITY_FOOTPRINT = 1500
NO_ABILITY_METADATA_TOKENS = 0

REQUIRED_RESULT_KEYS: Tuple[str, ...] = (
    "pass_rate",
    "pass_k_4",
    "latency_p95_s",
    "latency_p50_s",
    "metadata_tokens",
    "per_invocation_footprint",
    "trigger_F1",
    "router_floor",
    "step_count",
    "redundant_call_ratio",
)

CASE_KEYWORDS: Dict[str, List[str]] = {
    "profile_self": ["profile", "basic_ability_profile", "basicabilityprofile"],
    "docs_boundary": ["boundary", "scope", "out-of-scope", "marketplace"],
    "metrics_gap": ["metrics", "gap", "sub-metric", "r6"],
    "router_matrix": ["router_floor", "router-floor", "router floor", "router_test", "router-test", "router matrix"],
    "half_retire_review": ["half_retire", "half-retire", "retire", "value vector", "value_vector"],
    "next_action_plan": ["next action", "next_action_plan", "action plan", "next round"],
}

GENERIC_KEYWORDS: List[str] = sorted({k for kws in CASE_KEYWORDS.values() for k in kws})


def stable_hash(text: str) -> int:
    """Deterministic 32-bit hash for a string (SHA-256 truncated).

    >>> stable_hash("abc") == stable_hash("abc")
    True
    >>> 0 <= stable_hash("foo") < 2**32
    True
    """

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def keyword_match_for_case(case_id: str, prompt: str) -> bool:
    """Return True if ``prompt`` mentions any keyword for ``case_id``.

    Falls back to the union of all known case keywords when ``case_id``
    is not in :data:`CASE_KEYWORDS` (forward-compatible with new cases).

    >>> keyword_match_for_case("router_matrix", "what router floor?")
    True
    >>> keyword_match_for_case("router_matrix", "hello world")
    False
    """

    lower = prompt.lower()
    keywords = CASE_KEYWORDS.get(case_id, GENERIC_KEYWORDS)
    return any(kw in lower for kw in keywords)


def percentile_p95(values: List[float]) -> float:
    """Return ``sorted(values)[int(0.95 * len(values))]`` clamped in-bounds.

    Matches the simple p95 definition prescribed by the task contract.

    >>> percentile_p95([0.1, 0.2, 0.3, 0.4, 0.5])
    0.5
    >>> percentile_p95([1.0])
    1.0
    """

    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(0.95 * len(ordered))
    if idx >= len(ordered):
        idx = len(ordered) - 1
    return float(ordered[idx])


def percentile_p50(values: List[float]) -> float:
    """Return ``sorted(values)[int(0.50 * len(values))]`` clamped in-bounds.

    Round 4 (S5 task spec Edit B): sibling to :func:`percentile_p95`.
    Populates spec §3.1 D3/L1 ``wall_clock_p50`` for the no-ability
    baseline. By construction ``percentile_p50(xs) <= percentile_p95(xs)``
    for any non-empty ``xs`` — same invariant as the with-ability runner.

    >>> percentile_p50([0.1, 0.2, 0.3, 0.4, 0.5])
    0.3
    >>> percentile_p50([1.0])
    1.0
    >>> percentile_p50([])
    0.0
    """

    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(0.50 * len(ordered))
    if idx >= len(ordered):
        idx = len(ordered) - 1
    return float(ordered[idx])


def step_count_from_outcomes(prompt_outcomes: List[Dict[str, Any]]) -> int:
    """Return spec §3.1 D3/L3 ``step_count`` for a single case.

    Round 4 (S5 task spec Edit B): each prompt evaluation is treated
    as one execution step. No-ability semantics are identical to the
    with-ability runner — the baseline must supply the same field so
    the aggregator can compare the two.

    >>> step_count_from_outcomes([{"prompt_id": "a"}, {"prompt_id": "b"}])
    2
    >>> step_count_from_outcomes([])
    0
    """

    return int(len(prompt_outcomes))


def redundant_call_ratio_from_outcomes(prompt_outcomes: List[Dict[str, Any]]) -> float:
    """Return spec §3.1 D3/L4 ``redundant_call_ratio`` for a single case.

    Defined as ``(total_calls - unique_call_names) / total_calls``,
    clamped to ``[0.0, 1.0]``. The "tool name" of a simulated call is
    its ``prompt_id``. Per Round 4 master plan risk_flag, the 6
    simulated cases yield L4 = 0.0 because every prompt within a case
    has a unique ``prompt_id``; the no-ability arm has the same
    structural property.

    >>> redundant_call_ratio_from_outcomes([{"prompt_id": "a"}, {"prompt_id": "a"}])
    0.5
    >>> redundant_call_ratio_from_outcomes([{"prompt_id": "a"}, {"prompt_id": "b"}])
    0.0
    >>> redundant_call_ratio_from_outcomes([])
    0.0
    """

    total = len(prompt_outcomes)
    if total <= 0:
        return 0.0
    names: List[str] = []
    for entry in prompt_outcomes:
        name = entry.get("prompt_id") if isinstance(entry, dict) else None
        if isinstance(name, str) and name:
            names.append(name)
        else:
            names.append(f"_anonymous_{len(names)}")
    unique = len(set(names))
    redundant = max(0, total - unique)
    ratio = redundant / total
    if ratio < 0.0:
        return 0.0
    if ratio > 1.0:
        return 1.0
    return float(ratio)


def _validate_case(case: Any, source: Path) -> Dict[str, Any]:
    """Validate a parsed case object; raise on malformed input.

    Raises ``ValueError`` with a descriptive message; aggregate_eval-style
    "no silent zero substitution" applies here too.
    """

    if not isinstance(case, dict):
        raise ValueError(f"{source}: top-level YAML must be a mapping, got {type(case).__name__}")
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError(f"{source}: missing or invalid 'case_id'")
    prompts = case.get("prompts")
    if not isinstance(prompts, dict):
        raise ValueError(f"{source}: 'prompts' must be a mapping (got {type(prompts).__name__})")
    for key in ("should_trigger", "should_not_trigger"):
        block = prompts.get(key)
        if not isinstance(block, list) or not block:
            raise ValueError(f"{source}: 'prompts.{key}' must be a non-empty list")
        for i, entry in enumerate(block):
            if not isinstance(entry, dict):
                raise ValueError(f"{source}: 'prompts.{key}[{i}]' must be a mapping")
            if not isinstance(entry.get("id"), str) or not entry.get("id"):
                raise ValueError(f"{source}: 'prompts.{key}[{i}].id' missing")
            if not isinstance(entry.get("prompt"), str) or not entry.get("prompt"):
                raise ValueError(f"{source}: 'prompts.{key}[{i}].prompt' missing")
    return case


def _load_case(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: failed to parse YAML: {exc}") from exc
    return _validate_case(data, path)


def _list_case_files(cases_dir: Path) -> List[Path]:
    if not cases_dir.exists():
        raise FileNotFoundError(f"cases dir not found: {cases_dir}")
    if not cases_dir.is_dir():
        raise NotADirectoryError(f"not a directory: {cases_dir}")
    files: List[Path] = []
    for pattern in ("*.yaml", "*.yml"):
        files.extend(sorted(cases_dir.glob(pattern)))
    return files


def evaluate_case(case: Dict[str, Any], seed: int) -> Dict[str, Any]:
    """Compute the no-ability per-case result payload."""

    case_id = case["case_id"]
    should_trigger = case["prompts"]["should_trigger"]
    should_not_trigger = case["prompts"]["should_not_trigger"]

    prompt_outcomes: List[Dict[str, Any]] = []
    latencies: List[float] = []
    correct = 0
    total = len(should_trigger) + len(should_not_trigger)

    for entry in should_trigger:
        prompt_id = entry["id"]
        prompt_text = entry["prompt"]
        h = stable_hash(f"{seed}|{case_id}|{prompt_id}|{prompt_text}")
        latency_s = 0.5 + (h % 500) / 1000.0
        latencies.append(latency_s)
        kw = keyword_match_for_case(case_id, prompt_text)
        outcome = {
            "prompt_id": prompt_id,
            "expected": "trigger",
            "triggered": False,
            "keyword_match": kw,
            "ac_met": False,
            "correct": False,
            "latency_s": latency_s,
        }
        prompt_outcomes.append(outcome)

    for entry in should_not_trigger:
        prompt_id = entry["id"]
        prompt_text = entry["prompt"]
        h = stable_hash(f"{seed}|{case_id}|{prompt_id}|{prompt_text}")
        latency_s = 0.5 + (h % 500) / 1000.0
        latencies.append(latency_s)
        outcome = {
            "prompt_id": prompt_id,
            "expected": "no_trigger",
            "triggered": False,
            "keyword_match": keyword_match_for_case(case_id, prompt_text),
            "negative_acceptance_met": True,
            "correct": True,
            "latency_s": latency_s,
        }
        prompt_outcomes.append(outcome)
        correct += 1

    pass_rate = correct / total if total else 0.0
    pass_k_4 = pass_rate ** 4
    latency_p95_s = percentile_p95(latencies)
    latency_p50_s = percentile_p50(latencies)
    case_step_count = step_count_from_outcomes(prompt_outcomes)
    case_redundant_call_ratio = redundant_call_ratio_from_outcomes(prompt_outcomes)

    return {
        "pass_rate": pass_rate,
        "pass_k_4": pass_k_4,
        "latency_p95_s": latency_p95_s,
        "latency_p50_s": latency_p50_s,
        "metadata_tokens": NO_ABILITY_METADATA_TOKENS,
        "per_invocation_footprint": NO_ABILITY_FOOTPRINT,
        "trigger_F1": 0.0,
        "router_floor": ROUTER_FLOOR_NO_ABILITY,
        "step_count": case_step_count,
        "redundant_call_ratio": case_redundant_call_ratio,
        "prompt_outcomes": prompt_outcomes,
        "_meta": {
            "case_id": case_id,
            "runner": "no_ability_runner",
            "runner_version": SCRIPT_VERSION,
            "seed": seed,
            "n_should_trigger": len(should_trigger),
            "n_should_not_trigger": len(should_not_trigger),
            "n_total": total,
            "n_correct": correct,
            "step_count_basis": (
                "L3_step_count = len(prompt_outcomes); each prompt eval is one "
                "logical execution step in the simulated runner."
            ),
            "redundant_call_ratio_basis": (
                "L4_redundant_call_ratio = (total_calls - unique_call_names) / "
                "total_calls; tool name = prompt_id; degenerate 0.0 expected for "
                "the simulated runner because every prompt_id in a case is unique."
            ),
        },
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=False, ensure_ascii=False)
        fp.write("\n")


def _ensure_required_keys(result: Dict[str, Any], source: str) -> None:
    missing = [k for k in REQUIRED_RESULT_KEYS if k not in result]
    if missing:
        raise KeyError(f"{source}: result missing required keys: {missing}")


def run(cases_dir: Path, out_dir: Path, seed: int) -> Dict[str, Any]:
    cases = _list_case_files(cases_dir)
    if not cases:
        LOGGER.warning("no case files found under %s", cases_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_case: List[Dict[str, Any]] = []
    for case_path in cases:
        case = _load_case(case_path)
        result = evaluate_case(case, seed)
        _ensure_required_keys(result, str(case_path))
        case_id = case["case_id"]
        out_path = out_dir / case_id / "result.json"
        _write_json(out_path, result)
        per_case.append({
            "case_id": case_id,
            "source": str(case_path),
            "out": str(out_path),
            "pass_rate": result["pass_rate"],
            "pass_k_4": result["pass_k_4"],
            "latency_p95_s": result["latency_p95_s"],
            "latency_p50_s": result["latency_p50_s"],
            "trigger_F1": result["trigger_F1"],
            "step_count": result["step_count"],
            "redundant_call_ratio": result["redundant_call_ratio"],
        })
        LOGGER.info(
            "wrote %s pass_rate=%.4f latency_p50=%.4f latency_p95=%.4f step_count=%d redundant=%.4f",
            out_path, result["pass_rate"],
            result["latency_p50_s"], result["latency_p95_s"],
            result["step_count"], result["redundant_call_ratio"],
        )

    summary = {
        "runner": "no_ability_runner",
        "runner_version": SCRIPT_VERSION,
        "seed": seed,
        "cases_dir": str(cases_dir),
        "out_dir": str(out_dir),
        "case_count": len(per_case),
        "per_case": per_case,
        "aggregates": {
            "mean_pass_rate": sum(p["pass_rate"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_pass_k_4": sum(p["pass_k_4"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_latency_p95_s": sum(p["latency_p95_s"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_latency_p50_s": sum(p["latency_p50_s"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_trigger_F1": sum(p["trigger_F1"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_step_count": (
                sum(p["step_count"] for p in per_case) / len(per_case) if per_case else 0.0
            ),
            "mean_redundant_call_ratio": (
                sum(p["redundant_call_ratio"] for p in per_case) / len(per_case)
                if per_case else 0.0
            ),
            "router_floor": ROUTER_FLOOR_NO_ABILITY,
        },
    }
    _write_json(out_dir / "summary.json", summary)
    return summary


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="No-ability baseline runner for Si-Chip self-eval (SIMULATED).",
    )
    parser.add_argument("--cases-dir", required=True, help="Directory of case YAML files.")
    parser.add_argument("--out-dir", required=True, help="Directory to write per-case result.json + summary.json.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed (default: 42).")
    parser.add_argument("--verbose", action="store_true", help="Set log level to INFO.")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    cases_dir = Path(args.cases_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    summary = run(cases_dir, out_dir, args.seed)
    LOGGER.info("ran %d cases", summary["case_count"])
    print(out_dir / "summary.json")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.no_ability_runner").error("fatal: %s", exc)
        sys.exit(1)
