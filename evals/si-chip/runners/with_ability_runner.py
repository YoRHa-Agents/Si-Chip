#!/usr/bin/env python3
"""With-ability baseline runner for the Si-Chip self-eval suite.

Implements spec §8.1 step 2 ("evaluate no-ability baseline vs with-ability")
of `.local/research/spec_v0.1.0.md`. This runner SIMULATES the behavior of
a model that DOES have the Si-Chip skill installed: it triggers ~90% of the
``should_trigger`` prompts and 92% of the ``should_not_trigger`` prompts
correctly resolve to "no-trigger". Of the triggered set, ~85% are recorded
as having satisfied the case's acceptance criteria.

DETERMINISTIC SIMULATED BASELINE
================================
These results are DETERMINISTIC SIMULATED outcomes intended for v0.1.0
dogfood scaffolding (S3.W3.B). No LLM calls are made; per-prompt SHA-256
hashes drive every simulated outcome so a re-run with the same ``--seed``
and case files yields byte-identical ``result.json`` payloads. Real-LLM
eval substitution is the upgrade path; the per-case ``result.json`` schema
and runner CLI are stable so an LLM-backed runner can be swapped in
without changing
``.agents/skills/si-chip/scripts/aggregate_eval.py``.

Output schema (per case)
------------------------
``<out-dir>/<case_id>/result.json`` carries EXACTLY the keys
``aggregate_eval.py`` requires::

    {
      "pass_rate": <float>,
      "pass_k_4": <float>,
      "latency_p95_s": <float>,
      "metadata_tokens": <int>,            # from SKILL.md frontmatter
      "per_invocation_footprint": <int>,   # metadata + body + 1500 prompt
      "trigger_F1": <float>,               # 2 * p * r / (p + r)
      "router_floor": "composer_2/fast",
      "prompt_outcomes": [{...}, ...]
    }

A top-level ``<out-dir>/summary.json`` carries cross-case aggregates.

CLI
---
::

    python evals/si-chip/runners/with_ability_runner.py \\
        --cases-dir evals/si-chip/cases/ \\
        --out-dir evals/si-chip/baselines/with_si_chip/ \\
        [--seed 42] [--verbose]

Notes
-----
* ``pass_k_4`` is computed as ``pass_rate ** 4`` here as a documented
  proxy for true k=4 sampling (we cannot sample without an LLM); when the
  LLM-backed runner replaces this scaffold it should produce a real
  ``pass_k_4`` and overwrite this column. The proxy is preserved so the
  schema stays stable.
* ``router_floor`` is hard-coded to ``"composer_2/fast"`` because the
  v0.1.0 ship target binds Si-Chip to ``v1_baseline`` (spec §4.1, §5.4).
  Future router-test runs may rewrite this; the runner does not gate on
  it.
* Workspace rule "No Silent Failures": malformed case files raise and the
  process exits non-zero; a missing SKILL.md is also a hard failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.with_ability_runner")

SCRIPT_VERSION = "0.1.0"
ROUTER_FLOOR = "composer_2/fast"
USER_PROMPT_FOOTPRINT = 1500

REQUIRED_RESULT_KEYS: Tuple[str, ...] = (
    "pass_rate",
    "pass_k_4",
    "latency_p95_s",
    "metadata_tokens",
    "per_invocation_footprint",
    "trigger_F1",
    "router_floor",
)

CASE_KEYWORDS: Dict[str, List[str]] = {
    "profile_self": ["profile", "basic_ability_profile", "basicabilityprofile"],
    "docs_boundary": ["boundary", "scope", "out-of-scope", "marketplace"],
    "metrics_gap": ["metrics", "gap", "sub-metric", "r6"],
    "router_matrix": ["router_floor", "router-floor", "router floor", "router_test", "router-test", "router matrix"],
    "half_retire_review": ["half_retire", "half-retire", "retire", "value vector", "value_vector"],
    "next_action_plan": ["next action", "next_action_plan", "action plan", "next round"],
}


def stable_hash(text: str) -> int:
    """Deterministic 32-bit hash for a string (SHA-256 truncated).

    >>> stable_hash("abc") == stable_hash("abc")
    True
    """

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def keyword_match_for_case(case_id: str, prompt: str) -> bool:
    """Return True if any case keyword appears in ``prompt`` (lowercased)."""

    lower = prompt.lower()
    keywords = CASE_KEYWORDS.get(case_id)
    if not keywords:
        keywords = sorted({k for kws in CASE_KEYWORDS.values() for k in kws})
    return any(kw in lower for kw in keywords)


def percentile_p95(values: List[float]) -> float:
    """Return ``sorted(values)[int(0.95 * len(values))]`` clamped in-bounds.

    >>> percentile_p95([0.1, 0.2, 0.3, 0.4, 0.5])
    0.5
    """

    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(0.95 * len(ordered))
    if idx >= len(ordered):
        idx = len(ordered) - 1
    return float(ordered[idx])


def f1_score(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    """Return ``(precision, recall, f1)`` for the given confusion counts.

    >>> p, r, f = f1_score(9, 1, 1)
    >>> round(p, 2), round(r, 2), round(f, 2)
    (0.9, 0.9, 0.9)
    >>> f1_score(0, 0, 0)
    (0.0, 0.0, 0.0)
    """

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def _validate_case(case: Any, source: Path) -> Dict[str, Any]:
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


def _find_repo_root() -> Path:
    """Walk up from this file until ``.agents/skills/si-chip/SKILL.md`` exists.

    Raises ``FileNotFoundError`` when the marker is not found.
    """

    cur = Path(__file__).resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / ".agents" / "skills" / "si-chip" / "SKILL.md").exists():
            return parent
    raise FileNotFoundError(
        "could not locate repo root (no .agents/skills/si-chip/SKILL.md ancestor)"
    )


def _count_tokens_subprocess(skill_md: Path, count_tokens_script: Path) -> Tuple[int, int]:
    """Run ``count_tokens.py --both --json`` and return ``(meta, body)``.

    Treats both rc==0 (within budget) and rc==1 (over budget) as valid
    JSON outputs; any other rc is fatal.
    """

    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_md}")
    if not count_tokens_script.exists():
        raise FileNotFoundError(f"count_tokens.py not found at {count_tokens_script}")
    cmd = [
        sys.executable,
        str(count_tokens_script),
        "--file",
        str(skill_md),
        "--both",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"count_tokens.py crashed (rc={proc.returncode}): "
            f"stdout={proc.stdout!r} stderr={proc.stderr.strip()!r}"
        )
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError(
            f"could not parse count_tokens.py JSON output: {exc}; stdout={proc.stdout!r}"
        ) from exc
    meta = payload.get("metadata_tokens")
    body = payload.get("body_tokens")
    if not isinstance(meta, int) or not isinstance(body, int):
        raise RuntimeError(
            f"count_tokens.py returned non-int counts: meta={meta!r} body={body!r}"
        )
    return meta, body


def evaluate_case(
    case: Dict[str, Any],
    seed: int,
    metadata_tokens: int,
    body_tokens: int,
) -> Dict[str, Any]:
    """Compute the with-ability per-case result payload."""

    case_id = case["case_id"]
    should_trigger = case["prompts"]["should_trigger"]
    should_not_trigger = case["prompts"]["should_not_trigger"]

    prompt_outcomes: List[Dict[str, Any]] = []
    latencies: List[float] = []

    tp = fp = fn = tn = 0
    correct = 0

    for entry in should_trigger:
        prompt_id = entry["id"]
        prompt_text = entry["prompt"]
        latency_h = stable_hash(f"{seed}|{case_id}|{prompt_id}|{prompt_text}|lat")
        latency_s = 0.8 + (latency_h % 700) / 1000.0
        latencies.append(latency_s)

        trig_h = stable_hash(f"{seed}|{case_id}|{prompt_id}|trigger")
        triggered = (trig_h % 10) < 9

        ac_met = False
        if triggered:
            ac_h = stable_hash(f"{seed}|{case_id}|{prompt_id}|ac")
            ac_met = (ac_h % 100) < 85

        if triggered:
            tp += 1
        else:
            fn += 1

        is_correct = bool(triggered and ac_met)
        if is_correct:
            correct += 1

        prompt_outcomes.append({
            "prompt_id": prompt_id,
            "expected": "trigger",
            "triggered": triggered,
            "keyword_match": keyword_match_for_case(case_id, prompt_text),
            "ac_met": ac_met,
            "correct": is_correct,
            "latency_s": latency_s,
        })

    for entry in should_not_trigger:
        prompt_id = entry["id"]
        prompt_text = entry["prompt"]
        latency_h = stable_hash(f"{seed}|{case_id}|{prompt_id}|{prompt_text}|lat")
        latency_s = 0.8 + (latency_h % 700) / 1000.0
        latencies.append(latency_s)

        trig_h = stable_hash(f"{seed}|{case_id}|{prompt_id}|trigger")
        not_triggered_correctly = (trig_h % 100) < 92
        triggered = not not_triggered_correctly

        if triggered:
            fp += 1
        else:
            tn += 1

        is_correct = not triggered
        if is_correct:
            correct += 1

        prompt_outcomes.append({
            "prompt_id": prompt_id,
            "expected": "no_trigger",
            "triggered": triggered,
            "keyword_match": keyword_match_for_case(case_id, prompt_text),
            "negative_acceptance_met": not triggered,
            "near_miss_FP": triggered,
            "correct": is_correct,
            "latency_s": latency_s,
        })

    total = len(should_trigger) + len(should_not_trigger)
    pass_rate = correct / total if total else 0.0
    pass_k_4 = pass_rate ** 4
    latency_p95_s = percentile_p95(latencies)
    precision, recall, f1 = f1_score(tp, fp, fn)
    per_invocation_footprint = int(metadata_tokens) + int(body_tokens) + USER_PROMPT_FOOTPRINT

    return {
        "pass_rate": pass_rate,
        "pass_k_4": pass_k_4,
        "latency_p95_s": latency_p95_s,
        "metadata_tokens": int(metadata_tokens),
        "per_invocation_footprint": per_invocation_footprint,
        "trigger_F1": f1,
        "router_floor": ROUTER_FLOOR,
        "prompt_outcomes": prompt_outcomes,
        "_meta": {
            "case_id": case_id,
            "runner": "with_ability_runner",
            "runner_version": SCRIPT_VERSION,
            "seed": seed,
            "n_should_trigger": len(should_trigger),
            "n_should_not_trigger": len(should_not_trigger),
            "n_total": total,
            "n_correct": correct,
            "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
            "precision": precision,
            "recall": recall,
            "metadata_tokens_source": "SKILL.md (count_tokens.py --both --json)",
            "body_tokens": int(body_tokens),
            "user_prompt_footprint": USER_PROMPT_FOOTPRINT,
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

    repo_root = _find_repo_root()
    skill_md = repo_root / ".agents" / "skills" / "si-chip" / "SKILL.md"
    count_tokens_script = repo_root / ".agents" / "skills" / "si-chip" / "scripts" / "count_tokens.py"
    metadata_tokens, body_tokens = _count_tokens_subprocess(skill_md, count_tokens_script)
    LOGGER.info(
        "SKILL.md tokens: meta=%d body=%d (source=%s)",
        metadata_tokens, body_tokens, skill_md,
    )

    per_case: List[Dict[str, Any]] = []
    for case_path in cases:
        case = _load_case(case_path)
        result = evaluate_case(case, seed, metadata_tokens, body_tokens)
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
            "trigger_F1": result["trigger_F1"],
            "per_invocation_footprint": result["per_invocation_footprint"],
        })
        LOGGER.info(
            "wrote %s pass_rate=%.4f F1=%.4f latency_p95=%.4f",
            out_path, result["pass_rate"], result["trigger_F1"], result["latency_p95_s"],
        )

    summary = {
        "runner": "with_ability_runner",
        "runner_version": SCRIPT_VERSION,
        "seed": seed,
        "cases_dir": str(cases_dir),
        "out_dir": str(out_dir),
        "skill_md": str(skill_md),
        "metadata_tokens": int(metadata_tokens),
        "body_tokens": int(body_tokens),
        "case_count": len(per_case),
        "per_case": per_case,
        "aggregates": {
            "mean_pass_rate": sum(p["pass_rate"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_pass_k_4": sum(p["pass_k_4"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_latency_p95_s": sum(p["latency_p95_s"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_trigger_F1": sum(p["trigger_F1"] for p in per_case) / len(per_case) if per_case else 0.0,
            "mean_per_invocation_footprint": (
                sum(p["per_invocation_footprint"] for p in per_case) / len(per_case)
                if per_case else 0.0
            ),
            "router_floor": ROUTER_FLOOR,
        },
    }
    _write_json(out_dir / "summary.json", summary)
    return summary


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="With-ability runner for Si-Chip self-eval (SIMULATED).",
    )
    parser.add_argument("--cases-dir", required=True, help="Directory of case YAML files.")
    parser.add_argument("--out-dir", required=True, help="Directory to write per-case result.json + summary.json.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed (default: 42).")
    parser.add_argument("--verbose", action="store_true", help="Set log level to INFO.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
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
        logging.getLogger("si_chip.with_ability_runner").error("fatal: %s", exc)
        sys.exit(1)
