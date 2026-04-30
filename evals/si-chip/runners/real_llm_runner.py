#!/usr/bin/env python3
"""Si-Chip v0.4.0 Stage 4 Wave 1c: production real-LLM evaluation runner.

Promotes the Stage-1 feasibility spike
(``evals/si-chip/runners/real_llm_runner_spike.py``, verdict
PROCEED_MAJOR in ``.local/research/r12.5_real_llm_runner_feasibility.md``)
to the runner consumed by Stage 6c (Round 18 dogfood) and the 96-cell
Full router matrix (spec §5.3 + §22.6).

Responsibilities
----------------
1. Load an ``eval_pack.yaml`` (``should_trigger`` / ``should_not_trigger``
   buckets, chip-usage-helper format).
2. For each (model × thinking_depth × scenario_pack) cell in the selected
   ``matrix_mode`` (``mvp`` / ``intermediate`` / ``full``), call the
   Veil-egressed Anthropic-Messages endpoint ``k`` times per prompt and
   classify each response YES / NO.
3. Compute per-cell ``pass_rate`` (§3.1 D1 T1) and ``pass_at_k`` (§3.1
   D1 T2, any-of-k).
4. Enforce a hard spend cap (``--max-spend``); raise ``CostCapExceeded``
   when soft_cap × 2 is exceeded — no silent spend.
5. Cache every (model, depth, prompt, sample_idx, seed) response to
   ``<cache_dir>/<cache_key>.json`` (spec §22.6). Re-runs are byte-
   identical and free.

Out of scope (spec §11.1 forever-out, re-affirmed)
--------------------------------------------------
* No model training / fine-tuning / routing-weight persistence (LLM is
  called strictly as a black-box classifier for measurement).
* No marketplace / plugin distribution.
* No Markdown-to-CLI converter, no generic IDE compat layer.

Model remapping (``MODEL_REMAP``)
---------------------------------
Spec-level logical labels (``composer_2``, ``sonnet_4_6``, ...) are
separated from physical Veil aliases (``claude-haiku-4-5`` /
``claude-sonnet-4-6`` / ``claude-opus-4-6``). Cursor-internal /
external models (``composer_2``, ``gpt_5_mini``) remap to
``claude-haiku-4-5`` per r12.5 §2.4. ``deterministic_memory_router``
is nominal (spec §5.1) — no LLM call; cell is marked
``provenance: deterministic``.

Thinking depths (spec §5.3)
---------------------------
* ``fast``            — single call, ``max_tokens=5``.
* ``default``         — single call + "think carefully" CoT hint.
* ``extended``        — single call + "think step-by-step", ``max_tokens=50``.
* ``round_escalated`` — first-pass ``fast``; on mis, retry ``extended``.

Matrix shapes (spec §5.3)
-------------------------
* ``mvp``          —  2×2×2 =  8 cells.
* ``intermediate`` —  4×2×2 = 16 cells (v0.4.0 stepping stone).
* ``full``         —  6×4×4 = 96 cells.

Cost model (Anthropic list pricing, USD/Mtok, verified 2026-04-30)
-----------------------------------------------------------------
* ``claude-haiku-4-5``  — input $1  / output $5.
* ``claude-sonnet-4-6`` — input $3  / output $15.
* ``claude-opus-4-6``   — input $15 / output $75.

CLI
---
::

    python evals/si-chip/runners/real_llm_runner.py \\
        --ability <id> --eval-pack <path> \\
        --matrix-mode {mvp,intermediate,full} --k 4 \\
        --cache-dir <path> --out <path> \\
        [--no-live] [--max-spend 1.0] [--seed 0]

Python API: ``RunnerConfig``, ``RealLLMRunner``, ``MODEL_REMAP``,
``THINKING_DEPTHS``, ``MATRIX_SHAPES``, ``compute_pass_at_k``.

Workspace-rule notes: "No Silent Failures" (every auth / retry / cost
error raised); "Mandatory Verification" (sibling
``test_real_llm_runner.py`` covers ≥10 mocked tests); std lib +
``requests`` + ``pyyaml`` only (no new deps).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import requests
import yaml

LOGGER = logging.getLogger("si_chip.real_llm_runner")

SCRIPT_VERSION = "0.2.0"
SCHEMA_VERSION = "0.1.0"

# --- Endpoint / model constants ----------------------------------------

DEFAULT_ENDPOINT = "http://127.0.0.1:8086"
DEFAULT_TIMEOUT_S = 60
DEFAULT_K = 4
DEFAULT_MAX_SPEND_USD = 1.00
DEFAULT_HARD_CAP_MULTIPLIER = 2.0

DEFAULT_MAX_TOKENS_FAST = 5
DEFAULT_MAX_TOKENS_EXTENDED = 50

# MODEL_REMAP: spec-level logical labels -> physical Veil litellm-local
# aliases. Any unreachable / Cursor-internal model (composer_2, gpt_5_mini)
# is remapped to the cheapest Anthropic analogue per r12.5 §2.4.
# ``None`` signals a nominal / deterministic baseline that does NOT make
# an LLM call (currently only deterministic_memory_router).
MODEL_REMAP: Dict[str, Optional[str]] = {
    # Cursor-internal; not reachable from sandbox (spec §5.1, r12.5 §2.4).
    "composer_2": "claude-haiku-4-5",
    "composer_2/fast": "claude-haiku-4-5",
    "sonnet_shallow": "claude-sonnet-4-6",
    # Anthropic families, reachable via Veil (r12.5 §2.2).
    "haiku_4_5": "claude-haiku-4-5",
    "claude_haiku_4_5": "claude-haiku-4-5",
    "claude-haiku-4-5": "claude-haiku-4-5",
    "sonnet_4_6": "claude-sonnet-4-6",
    "claude_sonnet_4_6": "claude-sonnet-4-6",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "opus_4_7": "claude-opus-4-6",
    "opus_4_6": "claude-opus-4-6",
    "claude_opus_4_6": "claude-opus-4-6",
    "claude-opus-4-6": "claude-opus-4-6",
    # External / Cursor-internal not reachable (r12.5 §1.1).
    "gpt_5_mini": "claude-haiku-4-5",
    # Nominal deterministic baseline (spec §5.1); no LLM call.
    "deterministic_memory_router": None,
}

THINKING_DEPTHS: Tuple[str, ...] = (
    "fast",
    "default",
    "extended",
    "round_escalated",
)

MATRIX_SHAPES: Dict[str, Tuple[int, int, int]] = {
    "mvp": (2, 2, 2),
    "intermediate": (4, 2, 2),
    "full": (6, 4, 4),
}

MVP_MODELS: Tuple[str, ...] = ("composer_2/fast", "sonnet_shallow")
INTERMEDIATE_MODELS: Tuple[str, ...] = (
    "composer_2/fast",
    "haiku_4_5",
    "sonnet_4_6",
    "opus_4_7",
)
FULL_MODELS: Tuple[str, ...] = (
    "composer_2",
    "haiku_4_5",
    "sonnet_4_6",
    "opus_4_7",
    "gpt_5_mini",
    "deterministic_memory_router",
)

MVP_DEPTHS: Tuple[str, ...] = ("fast", "default")
FULL_DEPTHS: Tuple[str, ...] = ("fast", "default", "extended", "round_escalated")

MVP_PACKS: Tuple[str, ...] = ("trigger_basic", "near_miss")
FULL_PACKS: Tuple[str, ...] = (
    "trigger_basic",
    "near_miss",
    "multi_skill_competition",
    "execution_handoff",
)

PRICING_USD_PER_M_TOKEN: Dict[str, Tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-6": (15.0, 75.0),
}

ROUTING_SYSTEM_PROMPT_BASE = (
    "You are a routing classifier. The skill `chip-usage-helper` answers "
    "questions about a user's Cursor IDE billing/usage (their personal "
    "or team spend, model cost breakdown, agent hours, billing dashboard, "
    "/usage-report slash command). It does NOT answer general Cursor "
    "questions (settings, plugins, keybindings, how Composer works) or "
    "unrelated programming/devops questions. Decide whether the user "
    "prompt below should ROUTE to chip-usage-helper. Reply with exactly "
    "one token: YES or NO. No punctuation, no explanation."
)

DEPTH_SYSTEM_SUFFIX: Dict[str, str] = {
    "fast": "",
    "default": " Think carefully before answering.",
    "extended": (
        " Think step-by-step. First identify the user's intent in one "
        "sentence, then conclude with exactly YES or NO on the final line."
    ),
    "round_escalated": "",
}


# --- Exceptions --------------------------------------------------------


class LlmCallError(RuntimeError):
    """Network / HTTP / JSON failure from the LLM endpoint."""


class AuthError(LlmCallError):
    """Non-retryable auth failure (HTTP 401 / 403)."""


class CostCapExceeded(RuntimeError):
    """Raised when the hard spend cap is reached mid-run."""


class CacheMissInNoLiveMode(RuntimeError):
    """Raised when ``--no-live`` is set and a cache key is absent."""


# --- RunnerConfig ------------------------------------------------------


@dataclass
class RunnerConfig:
    """CLI / Python-API configuration for one runner invocation."""

    ability: str
    eval_pack: Path
    matrix_mode: str = "mvp"
    k: int = DEFAULT_K
    cache_dir: Optional[Path] = None
    out: Optional[Path] = None
    endpoint: str = DEFAULT_ENDPOINT
    no_live: bool = False
    max_spend_usd: float = DEFAULT_MAX_SPEND_USD
    seed: int = 0
    max_retries: int = 3
    max_prompts_per_cell: Optional[int] = None
    timeout_s: int = DEFAULT_TIMEOUT_S

    def validate(self) -> None:
        """Raise explicitly on any bad config (no silent failures)."""

        if not Path(self.eval_pack).exists():
            raise FileNotFoundError(
                f"eval_pack not found: {self.eval_pack}"
            )
        if self.matrix_mode not in MATRIX_SHAPES:
            raise ValueError(
                f"unknown matrix_mode {self.matrix_mode!r}; expected one "
                f"of {sorted(MATRIX_SHAPES.keys())}"
            )
        if self.k <= 0:
            raise ValueError(f"k must be >= 1, got {self.k}")
        if self.max_spend_usd <= 0:
            raise ValueError(
                f"max_spend_usd must be > 0, got {self.max_spend_usd}"
            )


# --- Utilities ---------------------------------------------------------


def compute_pass_at_k(k: int, outcomes: Sequence[bool]) -> float:
    """Any-of-k pass@k per spec §3.1 D1 T2; 1.0 iff any of the first k True."""

    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if not outcomes:
        raise ValueError("outcomes must be non-empty")
    return 1.0 if any(list(outcomes)[:k]) else 0.0


def resolve_model(logical_label: str) -> Optional[str]:
    """Map a logical label to its Veil physical alias; None = deterministic."""

    if logical_label in MODEL_REMAP:
        return MODEL_REMAP[logical_label]
    if logical_label in PRICING_USD_PER_M_TOKEN:
        return logical_label
    raise KeyError(
        f"unknown logical model label {logical_label!r}; expected one "
        f"of {sorted(MODEL_REMAP)}"
    )


def build_system_prompt(depth: str) -> str:
    if depth not in THINKING_DEPTHS:
        raise ValueError(
            f"unknown thinking_depth {depth!r}; expected one of "
            f"{sorted(THINKING_DEPTHS)}"
        )
    return ROUTING_SYSTEM_PROMPT_BASE + DEPTH_SYSTEM_SUFFIX.get(depth, "")


def max_tokens_for_depth(depth: str) -> int:
    return DEFAULT_MAX_TOKENS_EXTENDED if depth == "extended" else DEFAULT_MAX_TOKENS_FAST


def parse_yes_no(text: str) -> Optional[bool]:
    """Return True/False/None for YES/NO; tolerant of punctuation + CoT trailer."""

    if not text:
        return None
    for raw in text.strip().upper().splitlines():
        line = raw.strip().rstrip(".!?,;:")
        if not line:
            continue
        tokens = line.split()
        if not tokens:
            continue
        for candidate in (tokens[0].rstrip(".!?,;:"), tokens[-1].rstrip(".!?,;:")):
            if candidate == "YES":
                return True
            if candidate == "NO":
                return False
    return None


def cache_key(
    model: str, depth: str, prompt: str, sample_idx: int, seed: int = 0
) -> str:
    """Stable 16-hex cache key per spec §22.6 (includes system-prompt hash)."""

    system_hash = hashlib.sha256(
        build_system_prompt(depth).encode("utf-8")
    ).hexdigest()[:16]
    payload = json.dumps(
        {
            "model": model,
            "depth": depth,
            "prompt": prompt,
            "sample_idx": sample_idx,
            "seed": seed,
            "system_prompt_hash": system_hash,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def estimate_call_cost_usd(
    physical_model: str, tokens_in: int, tokens_out: int
) -> float:
    """Anthropic list-pricing cost of a single call."""

    price = PRICING_USD_PER_M_TOKEN.get(physical_model)
    if price is None:
        return 0.0
    return (tokens_in * price[0] + tokens_out * price[1]) / 1_000_000.0


def load_eval_pack(eval_pack_path: Path) -> Dict[str, Any]:
    with Path(eval_pack_path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def filter_pack_for_scenario(
    pack: Dict[str, Any], scenario: str
) -> List[Tuple[str, bool]]:
    """Return [(prompt, expected_yes), ...] for the chosen scenario_pack axis.

    ``trigger_basic`` uses the whole pack; ``near_miss`` uses only the
    ``should_not_trigger`` bucket (the pack's hardest false-positive
    axis); ``multi_skill_competition`` / ``execution_handoff`` are
    v0.4.0-rc1 placeholders that evaluate the full pack until curated
    subsets land (spec §5.3 future work).
    """

    should = [str(p) for p in (pack.get("should_trigger") or [])]
    should_not = [str(p) for p in (pack.get("should_not_trigger") or [])]
    if scenario == "trigger_basic":
        return [(p, True) for p in should] + [(p, False) for p in should_not]
    if scenario == "near_miss":
        return [(p, False) for p in should_not]
    if scenario in ("multi_skill_competition", "execution_handoff"):
        return [(p, True) for p in should] + [(p, False) for p in should_not]
    raise ValueError(
        f"unknown scenario_pack {scenario!r}; expected one of "
        f"{sorted(set(MVP_PACKS + FULL_PACKS))}"
    )


def models_for_mode(mode: str) -> Tuple[str, ...]:
    return {"mvp": MVP_MODELS, "intermediate": INTERMEDIATE_MODELS, "full": FULL_MODELS}[mode]


def depths_for_mode(mode: str) -> Tuple[str, ...]:
    return FULL_DEPTHS if mode == "full" else MVP_DEPTHS


def packs_for_mode(mode: str) -> Tuple[str, ...]:
    return FULL_PACKS if mode == "full" else MVP_PACKS


# --- Disk cache --------------------------------------------------------


class DiskCache:
    """Per-key JSON file cache at ``<cache_dir>/<key>.json`` (spec §22.6)."""

    def __init__(self, cache_dir: Optional[Path]):
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self._memory:
            return self._memory[key]
        if self.cache_dir is None:
            return None
        p = self.cache_dir / f"{key}.json"
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.warning("cache file %s unreadable (%s); treating as miss", p, exc)
            return None
        self._memory[key] = data
        return data

    def put(self, key: str, value: Dict[str, Any]) -> None:
        self._memory[key] = value
        if self.cache_dir is None:
            return
        p = self.cache_dir / f"{key}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False, indent=2, sort_keys=True)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# --- HTTP client -------------------------------------------------------


class AnthropicMessagesClient:
    """Minimal ``/v1/messages`` POST client with retry + rate-limit handling."""

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        max_retries: int = 3,
        session: Optional[Any] = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s
        self.max_retries = max(1, int(max_retries))
        self._session = session if session is not None else requests

    def call(self, model: str, system: str, prompt: str, max_tokens: int) -> Dict[str, Any]:
        url = f"{self.endpoint}/v1/messages"
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        last_exc: Optional[BaseException] = None
        for attempt in range(self.max_retries):
            try:
                t0 = time.perf_counter()
                resp = self._session.post(
                    url, headers=headers, json=body, timeout=self.timeout_s
                )
                elapsed = round(time.perf_counter() - t0, 4)
                status = getattr(resp, "status_code", None)
                if status in (401, 403):
                    raise AuthError(
                        f"auth error from {url}: HTTP {status}; "
                        f"body={getattr(resp, 'text', '')[:300]}"
                    )
                if status == 429 or status is None or (status >= 500 or status == 408):
                    wait = 2 ** attempt
                    LOGGER.warning(
                        "retriable HTTP %s attempt %d/%d; sleeping %ds",
                        status, attempt + 1, self.max_retries, wait,
                    )
                    time.sleep(wait)
                    last_exc = LlmCallError(f"HTTP {status} on {url}")
                    continue
                if status != 200:
                    raise LlmCallError(
                        f"non-200 from {url}: HTTP {status} "
                        f"body={getattr(resp, 'text', '')[:300]}"
                    )
                try:
                    data = resp.json()
                except (json.JSONDecodeError, ValueError) as exc:
                    raise LlmCallError(f"invalid JSON from {url}: {exc}") from exc
                text_parts = [
                    part.get("text", "")
                    for part in (data.get("content") or [])
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                return {
                    "text": "".join(text_parts).strip(),
                    "usage": data.get("usage") or {},
                    "raw_stop_reason": data.get("stop_reason"),
                    "elapsed_s": elapsed,
                }
            except AuthError:
                raise
            except requests.RequestException as exc:
                last_exc = exc
                wait = 2 ** attempt
                LOGGER.warning(
                    "network error attempt %d/%d: %s; sleeping %ds",
                    attempt + 1, self.max_retries, exc, wait,
                )
                time.sleep(wait)
                continue
        raise LlmCallError(
            f"exhausted {self.max_retries} retries calling {self.endpoint}/v1/messages; "
            f"last error: {last_exc!r}"
        )


# --- Runner ------------------------------------------------------------


class RealLLMRunner:
    """Model-pluggable, thinking-depth-pluggable real-LLM eval runner.

    Inject ``client`` (any object exposing ``call(model, system, prompt,
    max_tokens) -> dict``) for unit testing; inject ``cache`` for tests
    that pre-populate entries.
    """

    def __init__(
        self,
        config: RunnerConfig,
        client: Optional[AnthropicMessagesClient] = None,
        cache: Optional[DiskCache] = None,
    ) -> None:
        config.validate()
        self.config = config
        self.client = client if client is not None else AnthropicMessagesClient(
            endpoint=config.endpoint,
            timeout_s=config.timeout_s,
            max_retries=config.max_retries,
        )
        self.cache = cache if cache is not None else DiskCache(config.cache_dir)
        self._total_spend_usd: float = 0.0
        self._total_tokens_in: int = 0
        self._total_tokens_out: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._calls_made: int = 0

    @property
    def total_spend_usd(self) -> float:
        return round(self._total_spend_usd, 6)

    @property
    def hard_spend_cap(self) -> float:
        return self.config.max_spend_usd * DEFAULT_HARD_CAP_MULTIPLIER

    def _check_cost_cap(self) -> None:
        if self._total_spend_usd > self.hard_spend_cap:
            raise CostCapExceeded(
                f"spend ${self._total_spend_usd:.4f} exceeded hard cap "
                f"${self.hard_spend_cap:.4f} (soft cap ${self.config.max_spend_usd:.4f}); "
                "aborting run"
            )

    def _call_or_cache(
        self, physical_model: str, depth: str, prompt: str, sample_idx: int
    ) -> Dict[str, Any]:
        key = cache_key(physical_model, depth, prompt, sample_idx, seed=self.config.seed)
        cached = self.cache.get(key)
        if cached is not None:
            self._cache_hits += 1
            return cached
        self._cache_misses += 1
        if self.config.no_live:
            raise CacheMissInNoLiveMode(
                f"cache miss for key={key} (model={physical_model}, "
                f"depth={depth}, sample_idx={sample_idx}) and --no-live "
                "is set; refusing to call LLM"
            )
        resp = self.client.call(
            model=physical_model,
            system=build_system_prompt(depth),
            prompt=prompt,
            max_tokens=max_tokens_for_depth(depth),
        )
        self._calls_made += 1
        usage = resp.get("usage") or {}
        tokens_in = int(usage.get("input_tokens") or 0)
        tokens_out = int(usage.get("output_tokens") or 0)
        self._total_tokens_in += tokens_in
        self._total_tokens_out += tokens_out
        cost = estimate_call_cost_usd(physical_model, tokens_in, tokens_out)
        self._total_spend_usd += cost
        entry = {
            "text": resp.get("text", ""),
            "usage": {"input_tokens": tokens_in, "output_tokens": tokens_out},
            "stop_reason": resp.get("raw_stop_reason"),
            "elapsed_s": resp.get("elapsed_s"),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cost_usd": cost,
            "physical_model": physical_model,
            "depth": depth,
        }
        self.cache.put(key, entry)
        self._check_cost_cap()
        return entry

    def _sample_yes_no(
        self, physical_model: str, depth: str, prompt: str, sample_idx: int
    ) -> Tuple[Optional[bool], Dict[str, Any]]:
        effective_depth = "fast" if depth == "round_escalated" else depth
        entry = self._call_or_cache(physical_model, effective_depth, prompt, sample_idx)
        return parse_yes_no(entry.get("text", "")), entry

    def _run_cell(
        self, logical_model: str, depth: str, scenario: str, pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        items = filter_pack_for_scenario(pack, scenario)
        if self.config.max_prompts_per_cell is not None:
            items = items[: self.config.max_prompts_per_cell]
        cell_t0 = time.perf_counter()

        physical = resolve_model(logical_model)
        if physical is None:
            return {
                "model": logical_model,
                "physical_model": None,
                "thinking_depth": depth,
                "scenario_pack": scenario,
                "prompts_run": len(items),
                "passes": 0,
                "pass_rate": 0.0,
                "pass_at_k": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "duration_s": round(time.perf_counter() - cell_t0, 4),
                "provenance": "deterministic",
                "per_prompt": [],
            }

        per_prompt: List[Dict[str, Any]] = []
        sample_total = 0
        sample_correct = 0
        pass_at_k_hits = 0
        pass_at_k_total = 0
        tok_in0 = self._total_tokens_in
        tok_out0 = self._total_tokens_out

        for prompt, expected_yes in items:
            outcomes: List[bool] = []
            for sample_idx in range(self.config.k):
                parsed, _ = self._sample_yes_no(physical, depth, prompt, sample_idx)
                correct = (parsed is expected_yes)
                # round_escalated: if fast pass was wrong (and parseable),
                # spend one extended call; per spec §5.3 the final answer
                # is taken as correct iff the extended pass is correct.
                if depth == "round_escalated" and not correct and parsed is not None:
                    parsed2, _ = self._sample_yes_no(physical, "extended", prompt, sample_idx)
                    correct = (parsed2 is expected_yes)
                outcomes.append(correct)
                sample_total += 1
                if correct:
                    sample_correct += 1
            if outcomes:
                pass_at_k_total += 1
                if any(outcomes):
                    pass_at_k_hits += 1
            per_prompt.append({
                "prompt": prompt,
                "expected_yes": expected_yes,
                "outcomes": outcomes,
                "passes": sum(1 for o in outcomes if o),
                "pass_at_k": compute_pass_at_k(self.config.k, outcomes) if outcomes else 0.0,
            })

        return {
            "model": logical_model,
            "physical_model": physical,
            "thinking_depth": depth,
            "scenario_pack": scenario,
            "prompts_run": len(items),
            "passes": pass_at_k_hits,
            "pass_rate": round(sample_correct / sample_total, 4) if sample_total else 0.0,
            "pass_at_k": round(pass_at_k_hits / pass_at_k_total, 4) if pass_at_k_total else 0.0,
            "tokens_in": self._total_tokens_in - tok_in0,
            "tokens_out": self._total_tokens_out - tok_out0,
            "duration_s": round(time.perf_counter() - cell_t0, 4),
            "provenance": "real_llm",
            "per_prompt": per_prompt,
        }

    def evaluate_matrix(self) -> Dict[str, Any]:
        """Run the selected (models × depths × packs) matrix (spec §5.3)."""

        pack = load_eval_pack(Path(self.config.eval_pack))
        mode = self.config.matrix_mode
        models = models_for_mode(mode)
        depths = depths_for_mode(mode)
        packs = packs_for_mode(mode)

        run_t0 = time.perf_counter()
        cells: List[Dict[str, Any]] = []
        cells_passed = 0
        expected_cells = len(models) * len(depths) * len(packs)

        for m in models:
            for d in depths:
                for p in packs:
                    cell = self._run_cell(m, d, p, pack)
                    cells.append(cell)
                    if cell["pass_rate"] >= 0.5:
                        cells_passed += 1

        return {
            "schema_version": SCHEMA_VERSION,
            "script_version": SCRIPT_VERSION,
            "ability_id": self.config.ability,
            "matrix_mode": mode,
            "k": self.config.k,
            "seed": self.config.seed,
            "endpoint": self.config.endpoint,
            "cache_dir": str(self.config.cache_dir) if self.config.cache_dir else None,
            "eval_pack": str(self.config.eval_pack),
            "models_requested": list(models),
            "depths_requested": list(depths),
            "packs_requested": list(packs),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cells": cells,
            "summary": {
                "total_cells": expected_cells,
                "cells_emitted": len(cells),
                "cells_passed": cells_passed,
                "cells_failed": len(cells) - cells_passed,
                "total_spend_usd": round(self._total_spend_usd, 6),
                "hard_spend_cap_usd": round(self.hard_spend_cap, 6),
                "total_tokens_input": self._total_tokens_in,
                "total_tokens_output": self._total_tokens_out,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "calls_made": self._calls_made,
                "wall_clock_s": round(time.perf_counter() - run_t0, 4),
            },
        }

    def evaluate_pack(
        self, depth: str = "fast", scenario: str = "trigger_basic"
    ) -> Dict[str, Any]:
        """Convenience: run a single (first-model × depth × pack) cell."""

        pack = load_eval_pack(Path(self.config.eval_pack))
        models = models_for_mode(self.config.matrix_mode)
        if not models:
            raise RuntimeError(f"no models for matrix_mode {self.config.matrix_mode}")
        cell = self._run_cell(models[0], depth, scenario, pack)
        return {
            "ability_id": self.config.ability,
            "matrix_mode": self.config.matrix_mode,
            "k": self.config.k,
            "cell": cell,
            "summary": {
                "total_cells": 1,
                "cells_emitted": 1,
                "cells_passed": 1 if cell["pass_rate"] >= 0.5 else 0,
                "total_spend_usd": round(self._total_spend_usd, 6),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
            },
        }


# --- CLI ---------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="real_llm_runner",
        description=(
            "Si-Chip v0.4.0 production real-LLM runner. Executes "
            "(models x thinking_depths x scenario_packs) per spec §5.3 / §22.6."
        ),
    )
    p.add_argument("--ability", required=True, help="Ability id recorded in output JSON.")
    p.add_argument("--eval-pack", required=True, help="Path to eval_pack.yaml.")
    p.add_argument("--matrix-mode", default="mvp", choices=sorted(MATRIX_SHAPES.keys()),
                   help="Matrix shape: mvp (8), intermediate (16), full (96).")
    p.add_argument("--k", type=int, default=DEFAULT_K,
                   help=f"Samples per prompt for pass@k (default {DEFAULT_K}).")
    p.add_argument("--cache-dir", default=None,
                   help="Directory for per-key JSON cache (spec §22.6).")
    p.add_argument("--out", default=None, help="Path to write the matrix output JSON.")
    p.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                   help=f"Anthropic-Messages endpoint (default {DEFAULT_ENDPOINT}).")
    p.add_argument("--no-live", action="store_true",
                   help="Fail on any cache miss (pure replay mode for CI).")
    p.add_argument("--max-spend", type=float, default=DEFAULT_MAX_SPEND_USD,
                   help=f"Soft spend cap USD (default ${DEFAULT_MAX_SPEND_USD:.2f}); hard cap 2x.")
    p.add_argument("--seed", type=int, default=0,
                   help="Deterministic seed folded into cache key (spec §22.5).")
    p.add_argument("--max-prompts", type=int, default=None,
                   help="Cap prompts per cell (budget guard for MVP runs).")
    p.add_argument("--max-retries", type=int, default=3,
                   help="Network retries per call on 5xx/429/timeout (default 3).")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                   help=f"Per-call HTTP timeout seconds (default {DEFAULT_TIMEOUT_S}).")
    p.add_argument("--verbose", action="store_true", help="INFO-level logging.")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    config = RunnerConfig(
        ability=args.ability,
        eval_pack=Path(args.eval_pack),
        matrix_mode=args.matrix_mode,
        k=args.k,
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
        out=Path(args.out) if args.out else None,
        endpoint=args.endpoint,
        no_live=args.no_live,
        max_spend_usd=args.max_spend,
        seed=args.seed,
        max_retries=args.max_retries,
        max_prompts_per_cell=args.max_prompts,
        timeout_s=args.timeout,
    )
    runner = RealLLMRunner(config)
    try:
        output = runner.evaluate_matrix()
    except CostCapExceeded as exc:
        LOGGER.error("cost cap hit: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except CacheMissInNoLiveMode as exc:
        LOGGER.error("cache miss in --no-live: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except AuthError as exc:
        LOGGER.error("auth failure: %s", exc)
        print(f"ERROR (auth): {exc}", file=sys.stderr)
        return 4
    if config.out is not None:
        config.out.parent.mkdir(parents=True, exist_ok=True)
        with config.out.open("w", encoding="utf-8") as fh:
            json.dump(output, fh, ensure_ascii=False, indent=2)
    s = output["summary"]
    print(f"real_llm_runner v{SCRIPT_VERSION}  ability={config.ability}")
    print(f"  matrix_mode  : {output['matrix_mode']}  k={output['k']}  seed={output['seed']}")
    print(f"  cells        : {s['cells_emitted']}/{s['total_cells']}  "
          f"passed={s['cells_passed']}  failed={s['cells_failed']}")
    print(f"  spend        : ${s['total_spend_usd']:.4f} "
          f"(hard cap ${s['hard_spend_cap_usd']:.4f})")
    print(f"  tokens       : in={s['total_tokens_input']} out={s['total_tokens_output']}")
    print(f"  cache        : hits={s['cache_hits']} misses={s['cache_misses']} "
          f"calls_made={s['calls_made']}")
    print(f"  wall_clock_s : {s['wall_clock_s']}")
    if config.out is not None:
        print(f"  wrote        : {config.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
