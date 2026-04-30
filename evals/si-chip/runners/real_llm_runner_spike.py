#!/usr/bin/env python3
"""Si-Chip v0.4.0 Stage 1 spike: prove real-LLM k=4 sampling can produce
honest T2_pass_k > the deterministic SHA-256 simulator's structural lower
bound (`pass_rate**4 = 0.5478` at chip-usage-helper Round 4 quality).

This is a SPIKE, not the production runner. Stage 4 Wave 1c builds the real
``evals/si-chip/runners/real_llm_runner.py`` (model-pluggable, prod-ready).
This file's ONLY purpose is feasibility verification for the v0.4.0 plan
gate (PROCEED_MAJOR / DOWNGRADE_TO_MINOR / BLOCKED_NEED_USER decision).

What the spike does
-------------------
1. Loads an eval_pack.yaml with ``should_trigger`` and
   ``should_not_trigger`` prompt buckets (chip-usage-helper format).
2. For each prompt, calls a real LLM ``--k`` times with a routing-classifier
   system prompt asking ``YES`` (this prompt SHOULD fire chip-usage-helper)
   or ``NO`` (it should NOT fire).
3. Computes:
   - ``T1_pass_rate`` = mean per-call accuracy (single-sample classifier
     accuracy across the whole dataset).
   - ``T2_pass_at_k`` = fraction of prompts where AT LEAST ONE of ``k``
     samples is correct (this is the spec §3.1 D1 T2 metric).
4. Caches every (prompt, sample_idx) result keyed by
   ``sha256(model + prompt + system_prompt)`` so re-runs are free and
   determinism survives across CI invocations.
5. Caps total LLM calls at ``--max-calls`` (default 80) for budget safety.

Why this matters
----------------
v0.2.0 / v0.3.0 ship reports document T2_pass_k stuck at the algebraic
lower bound ``pass_rate**4 = 0.7222**4 = 0.5478`` because the deterministic
SHA-256 simulator is a single classifier — there is no Bernoulli variance
across samples, so ``Pr[any of k succeed]`` == ``Pr[one succeeds]`` ==
``pass_rate``, and any "k-axis" reduction is an algebraic artifact, NOT
the spec §3.1 D1 T2 semantic. v2_tightened gate `T2 >= 0.55` is therefore
unreachable WITHOUT a stochastic sampler. A real LLM with non-zero
variance typically produces ``T2_pass_at_k > T1_pass_rate``, so the
spike's job is purely to prove this difference is real on this dataset.

CLI
---
::

    python evals/si-chip/runners/real_llm_runner_spike.py \\
        --eval-pack <path/to/eval_pack.yaml> \\
        --model <claude-haiku-4-5|claude-sonnet-4-6|claude-opus-4-6> \\
        --k 4 \\
        --out <path/to/raw/spike_run.json> \\
        [--endpoint http://127.0.0.1:8086] \\
        [--max-calls 80] \\
        [--cache-dir .local/research/raw] \\
        [--max-prompts 10]   # subsample for budget safety

Endpoint contract
-----------------
The spike points at an Anthropic-Messages-compatible endpoint
(``POST {endpoint}/v1/messages`` with ``model``, ``max_tokens``,
``messages`` body). The default ``http://127.0.0.1:8086`` is the
``litellm-local`` egress configured in ``~/.config/veil/config.toml``,
which routes to ``http://ad-litellm.neolix.cn`` with the
``LITELLM_TOKEN`` from the local enva vault. This keeps the spike off
the public internet (sandbox firewall blocks ``api.anthropic.com``).

Workspace rules
---------------
* "No Silent Failures": every HTTP / JSON / cache error logged + raised.
* Forever-out (spec §11.1): NO marketplace, NO router-model-training,
  NO IDE compat layer, NO MD-to-CLI converter — this script is purely
  a measurement spike.
* No new dependencies: stdlib + ``requests`` + ``yaml`` only (both
  already present in the sandbox; verified in Step 1 probe).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

LOGGER = logging.getLogger("si_chip.real_llm_runner_spike")

SCRIPT_VERSION = "0.1.0-spike"

DEFAULT_ENDPOINT = "http://127.0.0.1:8086"
DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_K = 4
DEFAULT_MAX_CALLS = 80
DEFAULT_CACHE_DIR = Path(".local/research/raw")

ROUTING_SYSTEM_PROMPT = (
    "You are a routing classifier. The skill `chip-usage-helper` answers "
    "questions about a user's Cursor IDE billing/usage (their personal "
    "or team spend, model cost breakdown, agent hours, billing dashboard, "
    "/usage-report slash command). It does NOT answer general Cursor "
    "questions (settings, plugins, keybindings, how Composer works) or "
    "unrelated programming/devops questions. Decide whether the user "
    "prompt below should ROUTE to chip-usage-helper. Reply with exactly "
    "one token: YES or NO. No punctuation, no explanation."
)


# --- Cache --------------------------------------------------------------

def _cache_key(model: str, prompt: str, sample_idx: int) -> str:
    """Stable cache key per (model, prompt, sample_idx).

    ``sample_idx`` is part of the key so each of the k samples is cached
    independently — this lets the LLM exhibit per-sample variance while
    still preserving CI determinism on re-runs.
    """

    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "sample_idx": sample_idx,
            "system": ROUTING_SYSTEM_PROMPT,
        },
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _load_cache(cache_dir: Path, model: str) -> Dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_model = model.replace("/", "_").replace(":", "_")
    cache_file = cache_dir / f"r12.5_spike_cache_{safe_model}.json"
    if not cache_file.exists():
        return {"_cache_file": str(cache_file), "entries": {}}
    try:
        with cache_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        LOGGER.warning("cache load failed (%s); starting fresh", exc)
        return {"_cache_file": str(cache_file), "entries": {}}
    data.setdefault("entries", {})
    data["_cache_file"] = str(cache_file)
    return data


def _save_cache(cache: Dict[str, Any]) -> None:
    cache_file = Path(cache["_cache_file"])
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in cache.items() if k != "_cache_file"}
    with cache_file.open("w", encoding="utf-8") as fh:
        json.dump(serializable, fh, indent=2, ensure_ascii=False)


# --- LLM call -----------------------------------------------------------

class LlmCallError(RuntimeError):
    """Raised when the LLM endpoint returns a non-200 or malformed body."""


def call_llm(
    endpoint: str,
    model: str,
    prompt: str,
    max_tokens: int = 5,
    timeout_s: int = 30,
) -> Dict[str, Any]:
    """POST to an Anthropic-Messages-compatible endpoint.

    Returns ``{"text": str, "usage": {...}, "raw": {...}, "elapsed_s": float}``.
    Raises ``LlmCallError`` on any failure (no silent failures).
    """

    url = f"{endpoint.rstrip('/')}/v1/messages"
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": ROUTING_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    t0 = time.perf_counter()
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout_s)
    except requests.RequestException as exc:
        raise LlmCallError(f"network error calling {url}: {exc}") from exc
    elapsed = round(time.perf_counter() - t0, 4)
    if resp.status_code != 200:
        raise LlmCallError(
            f"non-200 from {url}: HTTP {resp.status_code} "
            f"body={resp.text[:300]}"
        )
    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise LlmCallError(
            f"invalid JSON from {url}: {exc}; body={resp.text[:300]}"
        ) from exc
    content = data.get("content") or []
    text_parts: List[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            text_parts.append(part.get("text", ""))
    text = "".join(text_parts).strip()
    usage = data.get("usage") or {}
    return {
        "text": text,
        "usage": usage,
        "raw_stop_reason": data.get("stop_reason"),
        "elapsed_s": elapsed,
    }


# --- Classification -----------------------------------------------------

def parse_yes_no(text: str) -> Optional[bool]:
    """Return ``True`` for YES, ``False`` for NO, ``None`` for unparseable.

    Tolerant of trailing punctuation / case / leading whitespace because
    even instruction-following models occasionally append a period or a
    newline. Anything else maps to ``None`` (counted as a wrong answer
    against the expected label).
    """

    if not text:
        return None
    head = text.strip().upper().rstrip(".!?,;:")
    head = head.split()[0] if head else ""
    if head == "YES":
        return True
    if head == "NO":
        return False
    return None


# --- Eval-pack execution -----------------------------------------------

def _flatten_pack(
    pack: Dict[str, Any], max_prompts: Optional[int]
) -> List[Tuple[str, bool]]:
    """Return [(prompt, expected_yes), ...] in stable order.

    ``expected_yes`` is True for ``should_trigger`` items, False for
    ``should_not_trigger``. ``max_prompts``, when set, takes the first
    N from EACH bucket (preserves the should/should-not balance).
    """

    items: List[Tuple[str, bool]] = []
    sh = list(pack.get("should_trigger") or [])
    snt = list(pack.get("should_not_trigger") or [])
    if max_prompts is not None:
        per = max(1, max_prompts // 2)
        sh = sh[:per]
        snt = snt[:per]
    for p in sh:
        items.append((str(p), True))
    for p in snt:
        items.append((str(p), False))
    return items


def run_spike(
    eval_pack_path: Path,
    model: str,
    k: int,
    out_path: Path,
    endpoint: str,
    max_calls: int,
    cache_dir: Path,
    max_prompts: Optional[int],
) -> Dict[str, Any]:
    """Execute the spike and return the run summary dict.

    Side effects:
    * Calls the LLM up to ``min(max_calls, len(items) * k)`` times.
    * Writes the per-sample cache to ``cache_dir/r12.5_spike_cache_<model>.json``.
    * Writes the run summary to ``out_path`` as JSON.
    """

    if not eval_pack_path.exists():
        raise FileNotFoundError(f"eval_pack not found: {eval_pack_path}")
    with eval_pack_path.open("r", encoding="utf-8") as fh:
        pack = yaml.safe_load(fh) or {}
    items = _flatten_pack(pack, max_prompts=max_prompts)
    if not items:
        raise ValueError(
            f"eval_pack {eval_pack_path} contains no should/should-not items"
        )

    cache = _load_cache(cache_dir, model)
    entries: Dict[str, Any] = cache["entries"]

    n_calls_made = 0
    cap_hit = False
    per_prompt: List[Dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0
    wall_t0 = time.perf_counter()

    for prompt, expected_yes in items:
        sample_results: List[Dict[str, Any]] = []
        for sample_idx in range(k):
            key = _cache_key(model, prompt, sample_idx)
            entry = entries.get(key)
            if entry is None:
                if n_calls_made >= max_calls:
                    cap_hit = True
                    LOGGER.warning(
                        "max_calls=%d cap reached; remaining samples skipped",
                        max_calls,
                    )
                    break
                LOGGER.info(
                    "calling LLM (call %d/%d): prompt=%r sample=%d",
                    n_calls_made + 1,
                    max_calls,
                    prompt[:40],
                    sample_idx,
                )
                resp = call_llm(endpoint, model, prompt)
                n_calls_made += 1
                entry = {
                    "text": resp["text"],
                    "usage": resp["usage"],
                    "stop_reason": resp["raw_stop_reason"],
                    "elapsed_s": resp["elapsed_s"],
                    "fetched_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                }
                entries[key] = entry
                _save_cache(cache)
            else:
                LOGGER.debug("cache hit: %s", key)
            usage = entry.get("usage") or {}
            total_input_tokens += int(usage.get("input_tokens") or 0)
            total_output_tokens += int(usage.get("output_tokens") or 0)
            parsed = parse_yes_no(entry.get("text", ""))
            sample_results.append(
                {
                    "sample_idx": sample_idx,
                    "text": entry.get("text"),
                    "parsed": parsed,
                    "correct": (parsed is expected_yes)
                    if parsed is not None
                    else False,
                    "cache_key": key,
                    "elapsed_s": entry.get("elapsed_s"),
                }
            )
        completed_samples = len(sample_results)
        correct_samples = sum(1 for s in sample_results if s["correct"])
        any_correct = any(s["correct"] for s in sample_results) if sample_results else False
        per_prompt.append(
            {
                "prompt": prompt,
                "expected_yes": expected_yes,
                "samples_requested": k,
                "samples_completed": completed_samples,
                "samples_correct": correct_samples,
                "any_correct_at_k": any_correct,
                "samples": sample_results,
            }
        )
        if cap_hit:
            break

    wall_clock_s = round(time.perf_counter() - wall_t0, 4)

    # T1: per-call accuracy (each sample is its own data point).
    sample_total = sum(p["samples_completed"] for p in per_prompt)
    sample_correct = sum(p["samples_correct"] for p in per_prompt)
    t1_pass_rate = (
        round(sample_correct / sample_total, 4) if sample_total > 0 else 0.0
    )

    # T2: per-prompt any-of-k success.
    prompts_with_full_k = [
        p for p in per_prompt if p["samples_completed"] == k
    ]
    n_full = len(prompts_with_full_k)
    n_any = sum(1 for p in prompts_with_full_k if p["any_correct_at_k"])
    t2_pass_at_k = round(n_any / n_full, 4) if n_full > 0 else 0.0

    # T1 deterministic baseline reference (the Round 4 chip-usage-helper
    # simulator floor was pass_rate=0.7222 -> pass_k_4 = 0.5478).
    deterministic_baseline = {
        "pass_rate_round4": 0.7222,
        "pass_k_4_round4": 0.5478,
        "v2_tightened_threshold": 0.55,
        "rationale": (
            "with_ability_runner.py uses pass_k_4 = pass_rate**4 because "
            "SHA-256 hashing is deterministic; v2_tightened T2 >= 0.55 is "
            "structurally unreachable with this proxy. A real LLM with "
            "non-zero per-sample variance produces pass_at_k > pass_rate "
            "in expectation."
        ),
    }

    summary = {
        "schema_version": "0.1.0",
        "script_version": SCRIPT_VERSION,
        "spike_round": "r12.5",
        "model": model,
        "endpoint": endpoint,
        "k": k,
        "max_calls": max_calls,
        "max_prompts": max_prompts,
        "n_should_trigger": sum(1 for _, e in items if e),
        "n_should_not_trigger": sum(1 for _, e in items if not e),
        "n_prompts_evaluated": len(per_prompt),
        "n_prompts_with_full_k": n_full,
        "calls_made_this_run": n_calls_made,
        "cap_hit": cap_hit,
        "wall_clock_s": wall_clock_s,
        "tokens_input_total": total_input_tokens,
        "tokens_output_total": total_output_tokens,
        "t1_pass_rate": t1_pass_rate,
        "t2_pass_at_k": t2_pass_at_k,
        "delta_t2_minus_t1": round(t2_pass_at_k - t1_pass_rate, 4),
        "deterministic_baseline": deterministic_baseline,
        "v2_tightened_reachable": t2_pass_at_k > deterministic_baseline[
            "v2_tightened_threshold"
        ],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cache_file": cache.get("_cache_file"),
        "eval_pack": str(eval_pack_path),
        "per_prompt": per_prompt,
        "system_prompt_used": ROUTING_SYSTEM_PROMPT,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    LOGGER.info("wrote spike summary to %s", out_path)
    return summary


# --- CLI ----------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="real_llm_runner_spike",
        description=(
            "Si-Chip v0.4.0 Stage 1 spike — prove real-LLM k=4 sampling "
            "produces T2_pass_at_k > deterministic-simulator floor "
            "(0.5478). Spike-only; production runner is Stage 4 Wave 1c."
        ),
    )
    p.add_argument(
        "--eval-pack",
        required=True,
        help="Path to eval_pack.yaml (chip-usage-helper format).",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model id forwarded to the endpoint (default {DEFAULT_MODEL}).",
    )
    p.add_argument(
        "--k",
        type=int,
        default=DEFAULT_K,
        help=f"Number of samples per prompt for T2_pass_k (default {DEFAULT_K}).",
    )
    p.add_argument(
        "--out",
        required=True,
        help="Path to write the spike run JSON summary.",
    )
    p.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=(
            "Anthropic-Messages-compatible HTTP base URL "
            f"(default {DEFAULT_ENDPOINT}, the local Veil litellm egress)."
        ),
    )
    p.add_argument(
        "--max-calls",
        type=int,
        default=DEFAULT_MAX_CALLS,
        help=(
            "Hard cap on LLM calls per invocation (cost guard). "
            f"Default {DEFAULT_MAX_CALLS}."
        ),
    )
    p.add_argument(
        "--cache-dir",
        default=str(DEFAULT_CACHE_DIR),
        help=(
            "Directory for the per-(model, prompt, sample_idx) JSON cache "
            f"(default {DEFAULT_CACHE_DIR})."
        ),
    )
    p.add_argument(
        "--max-prompts",
        type=int,
        default=None,
        help=(
            "Optional: subsample this many prompts (split evenly between "
            "should/should-not buckets). Use to stay under --max-calls."
        ),
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable INFO-level logging.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    eval_pack_path = Path(args.eval_pack)
    out_path = Path(args.out)
    cache_dir = Path(args.cache_dir)

    summary = run_spike(
        eval_pack_path=eval_pack_path,
        model=args.model,
        k=args.k,
        out_path=out_path,
        endpoint=args.endpoint,
        max_calls=args.max_calls,
        cache_dir=cache_dir,
        max_prompts=args.max_prompts,
    )

    print("=" * 70)
    print(f"real_llm_runner_spike v{SCRIPT_VERSION}")
    print(f"  model        : {summary['model']}")
    print(f"  endpoint     : {summary['endpoint']}")
    print(
        f"  prompts      : {summary['n_prompts_evaluated']} "
        f"({summary['n_should_trigger']} YES + "
        f"{summary['n_should_not_trigger']} NO)"
    )
    print(
        f"  k            : {summary['k']}  "
        f"(prompts_with_full_k={summary['n_prompts_with_full_k']})"
    )
    print(
        f"  calls        : {summary['calls_made_this_run']} this run "
        f"(cap={summary['max_calls']}, cap_hit={summary['cap_hit']})"
    )
    print(
        f"  tokens       : in={summary['tokens_input_total']} "
        f"out={summary['tokens_output_total']}"
    )
    print(f"  wall_clock_s : {summary['wall_clock_s']}")
    print(f"  T1_pass_rate : {summary['t1_pass_rate']}")
    print(f"  T2_pass_at_k : {summary['t2_pass_at_k']}")
    print(
        f"  delta T2-T1  : {summary['delta_t2_minus_t1']}  "
        "(positive => stochastic gain over single-sample accuracy)"
    )
    print(
        f"  vs determ.   : T2={summary['t2_pass_at_k']} vs "
        f"baseline {summary['deterministic_baseline']['pass_k_4_round4']} "
        f"(threshold {summary['deterministic_baseline']['v2_tightened_threshold']})"
    )
    print(f"  v2_tightened reachable: {summary['v2_tightened_reachable']}")
    print(f"  wrote        : {out_path}")
    print(f"  cache        : {summary['cache_file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
