#!/usr/bin/env python3
"""Generic CJK-aware trigger F1 evaluator for Si-Chip BasicAbility eval packs.

Implements the reusable three-layer tokenisation + discriminator algorithm
extracted from ``.local/dogfood/2026-04-29/abilities/chip-usage-helper/tools/eval_chip_usage_helper.py``
(``tokenize_prompt`` + ``load_trigger_vocabulary`` + ``trigger_match`` +
``eval_trigger_F1``; ~140 LoC collapsed into a pluggable API so any future
ability supplies only its own vocabulary yaml).

Per spec v0.3.0-rc1 §14/§15 (and R11 §6 design brief), every ability's
trigger evaluation must surface ``R1_trigger_precision`` /
``R2_trigger_recall`` / ``R3_trigger_F1`` / ``R4_near_miss_FP_rate``.
This module is the shared harness; its output shape mirrors the R6 D6
sub-metric keys that ``tools/eval_skill.py`` hoists into
``metrics_report.yaml``.

Three-layer tokenisation (CJK-Aware Default):

* **Layer A** — ASCII bag-of-words (``[\\w]+`` after lowercase).
* **Layer B** — CJK substring matching (``[\\u4e00-\\u9fff]+`` runs,
  kept whole in the token set; anchor matching walks via ``in`` against
  the raw prompt to catch n-grams).
* **Layer C** — discriminator phrase rules (anti-trigger; suppresses
  false positives). The ``cursor_meta`` and ``time_spend`` discriminators
  from ``eval_chip_usage_helper.py`` ship as built-ins and fire when a
  vocabulary ``discriminators`` entry names them; custom entries support
  a simple ``if_token_in_prompt`` / ``and_any_token_in_prompt`` /
  ``or_cjk_substring_in_prompt`` / ``and_no_money_cue`` schema.

CLI::

    python tools/cjk_trigger_eval.py \\
        --eval-pack <path/to/eval_pack.yaml> \\
        --vocabulary <path/to/vocabulary.yaml> \\
        [--json] [--min-weak-hits 2]

``--json`` emits the ``EvaluationResult`` dataclass as JSON on stdout.
Pretty-prints otherwise. Exit code is always ``0`` — this is a
measurement tool, not a gate (``tools/spec_validator.py`` is the gate).

Workspace-rule notes
--------------------
* "No Silent Failures": missing vocabulary / eval-pack files raise
  ``FileNotFoundError``; malformed YAML raises. Unknown built-in
  discriminator names raise ``ValueError`` (no fallthrough).
* "Mandatory Verification": sibling test
  ``tools/test_cjk_trigger_eval.py`` covers tokenisation, every rule
  phase (slash command / built-in discriminators / strong anchors /
  weak accumulation), and an end-to-end F1 sanity test.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.cjk_trigger_eval")

SCRIPT_VERSION = "0.1.0"

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)

# Built-in discriminators extracted from eval_chip_usage_helper.py.
# Each built-in is keyed by `name`; vocabulary yaml references the name
# (optional rule prose is kept for operator-facing documentation only).

_CURSOR_META_PHRASES: FrozenSet[str] = frozenset(
    {
        "composer",
        "settings",
        "extension",
        "keybinding",
        "update",
        "install",
        "marketplace",
    }
)

_TIME_SPEND_TIME_WORDS: FrozenSet[str] = frozenset(
    {
        "time",
        "debugging",
        "debug",
        "reviewing",
        "review",
        "sprint",
        "hour",
        "minute",
        "minutes",
    }
)

_TIME_SPEND_MONEY_ANCHORS_ASCII: FrozenSet[str] = frozenset(
    {
        "cost",
        "billed",
        "charged",
        "fee",
        "bill",
        "billing",
        "money",
        "dollar",
        "dollars",
        "$",
    }
)

_TIME_SPEND_MONEY_ANCHORS_CJK: FrozenSet[str] = frozenset(
    {
        "费用",
        "账单",
        "计费",
        "花费",
        "消耗",
        "花了",
        "多少钱",
        "钱",
        "扣费",
    }
)

_TIME_SPEND_CJK_TRIGGERS: FrozenSet[str] = frozenset({"花时间", "花一"})

BUILTIN_DISCRIMINATOR_NAMES: FrozenSet[str] = frozenset({"cursor_meta", "time_spend"})


@dataclass
class Vocabulary:
    """Pluggable vocabulary loaded from a per-ability yaml file.

    Fields mirror the schema documented at R11 §6.2 / §6.3::

        ascii_anchors: list[str]        # strong ASCII triggers → YES
        ascii_weak: list[str]           # weak ASCII hits; accumulate
        cjk_strong: list[str]           # strong CJK substrings → YES
        cjk_weak: list[str]             # weak CJK hits; accumulate
        discriminators: list[dict]      # ordered; built-in names or custom
        slash_commands: list[str]       # short-circuit YES
        min_weak_hits: int              # default 2
        cursor_plus_cjk_usage: list[str]  # CJK substrings that, co-
                                           # occurring with ASCII
                                           # "cursor", trigger YES
    """

    ascii_anchors: Set[str] = field(default_factory=set)
    ascii_weak: Set[str] = field(default_factory=set)
    cjk_strong: List[str] = field(default_factory=list)
    cjk_weak: List[str] = field(default_factory=list)
    discriminators: List[Dict[str, Any]] = field(default_factory=list)
    slash_commands: List[str] = field(default_factory=list)
    min_weak_hits: int = 2
    cursor_plus_cjk_usage: List[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "Vocabulary":
        """Load a vocabulary yaml. Raises on missing / malformed file."""

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"vocabulary yaml not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError(
                f"vocabulary yaml at {path} must be a mapping, got "
                f"{type(raw).__name__}"
            )
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Vocabulary":
        """Build a ``Vocabulary`` from an in-memory mapping."""

        return cls(
            ascii_anchors=set(raw.get("ascii_anchors") or []),
            ascii_weak=set(raw.get("ascii_weak") or []),
            cjk_strong=list(raw.get("cjk_strong") or []),
            cjk_weak=list(raw.get("cjk_weak") or []),
            discriminators=list(raw.get("discriminators") or []),
            slash_commands=list(raw.get("slash_commands") or []),
            min_weak_hits=int(raw.get("min_weak_hits", 2)),
            cursor_plus_cjk_usage=list(raw.get("cursor_plus_cjk_usage") or []),
        )


@dataclass
class TriggerDecision:
    """Per-prompt trigger outcome, JSON-serialisable."""

    match: bool
    reason: str
    layer_hit: str = "unknown"


@dataclass
class EvaluationResult:
    """Aggregate trigger F1 metrics over an eval pack."""

    n_should: int
    n_should_not: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    near_miss_fp_rate: float
    per_prompt: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def tokenize_prompt(text: str) -> Set[str]:
    """ASCII bag-of-words + CJK runs as single tokens.

    Lowercase first, then split on ``[\\w\\u4e00-\\u9fff]+``. CJK runs stay
    as single tokens; ASCII word boundaries are ``[\\w]+``. Returns a
    ``set`` for O(1) overlap checks.
    """

    if not isinstance(text, str):
        raise TypeError(f"tokenize_prompt expected str, got {type(text).__name__}")
    return set(_TOKEN_RE.findall(text.lower()))


def _extract_cjk_runs(text: str, min_len: int = 2, max_len: int = 6) -> Set[str]:
    """Helper — all CJK substrings of length [min_len, max_len] in text."""

    runs = set()
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if min_len <= len(run) <= max_len:
            runs.add(run)
    return runs


def _apply_builtin_discriminator(
    name: str, prompt: str, tokens: Set[str]
) -> bool:
    """Return True iff the named built-in discriminator fires (suppress)."""

    if name == "cursor_meta":
        # cursor-meta context: "cursor" + any of composer/settings/... → NO
        return "cursor" in tokens and bool(tokens & _CURSOR_META_PHRASES)
    if name == "time_spend":
        # "spend"/花时间/花一 + time word + no money cue → NO
        has_money_cue_ascii = bool(tokens & _TIME_SPEND_MONEY_ANCHORS_ASCII)
        has_money_cue_cjk = any(s in prompt for s in _TIME_SPEND_MONEY_ANCHORS_CJK)
        has_money_cue = has_money_cue_ascii or has_money_cue_cjk
        triggers = ("spend" in tokens) or any(
            s in prompt for s in _TIME_SPEND_CJK_TRIGGERS
        )
        return (
            triggers and bool(tokens & _TIME_SPEND_TIME_WORDS) and not has_money_cue
        )
    raise ValueError(
        f"unknown built-in discriminator name {name!r}; "
        f"expected one of {sorted(BUILTIN_DISCRIMINATOR_NAMES)}"
    )


def _apply_custom_discriminator(
    entry: Dict[str, Any], prompt: str, tokens: Set[str]
) -> bool:
    """Evaluate a custom discriminator defined in vocabulary yaml.

    Supported keys (all optional; a missing key is a no-op on that axis):

    * ``if_token_in_prompt``: list[str] — at least one token must appear
      in the ``tokens`` set to consider the rule armed.
    * ``or_cjk_substring_in_prompt``: list[str] — alternative arming
      path: any listed CJK substring present in raw ``prompt``.
    * ``and_any_token_in_prompt``: list[str] — conjunctive: at least one
      must appear in ``tokens`` for the rule to fire.
    * ``and_no_money_cue``: bool — if True, rule fires only when neither
      ASCII nor CJK money anchor appears (reuses the time_spend
      cue sets — this is the most common custom pattern).

    A rule without at least one of the above axes is skipped with a
    logged warning (no silent fallthrough).

    Returns True iff the rule fires. Firing means the prompt is
    suppressed (match=False with reason ``discriminator:<name>``).
    """

    name = entry.get("name", "<unnamed>")
    armed_by_token = False
    if "if_token_in_prompt" in entry:
        armed_by_token = bool(tokens & set(entry.get("if_token_in_prompt") or []))
    armed_by_cjk = False
    if "or_cjk_substring_in_prompt" in entry:
        armed_by_cjk = any(
            s in prompt for s in entry.get("or_cjk_substring_in_prompt") or []
        )

    if not (armed_by_token or armed_by_cjk):
        return False

    # Conjunctive axes
    if "and_any_token_in_prompt" in entry:
        required = set(entry.get("and_any_token_in_prompt") or [])
        if not (tokens & required):
            return False
    if entry.get("and_no_money_cue"):
        has_money_cue_ascii = bool(tokens & _TIME_SPEND_MONEY_ANCHORS_ASCII)
        has_money_cue_cjk = any(s in prompt for s in _TIME_SPEND_MONEY_ANCHORS_CJK)
        if has_money_cue_ascii or has_money_cue_cjk:
            return False

    if entry.get("suppress", True):
        LOGGER.debug("custom discriminator %r fired on prompt %r", name, prompt)
        return True
    return False


def trigger_match(prompt: str, vocab: Vocabulary) -> Dict[str, Any]:
    """Apply the three-layer deterministic trigger rule.

    Returns a dict with ``match: bool`` and ``reason: str`` (plus
    ``layer_hit``). Mirrors ``eval_chip_usage_helper.py::trigger_match``
    but takes a pluggable ``Vocabulary`` instead of the chip-specific
    hard-coded rules.
    """

    if not isinstance(prompt, str):
        raise TypeError(f"trigger_match expected str prompt, got {type(prompt).__name__}")

    plow = prompt.lower()

    # Phase 1: slash command short-circuit
    for cmd in vocab.slash_commands:
        if cmd and cmd.lower() in plow:
            return {
                "match": True,
                "reason": "slash_command",
                "layer_hit": "slash_command",
            }

    tokens = tokenize_prompt(prompt)

    # Phase 2: discriminator suppressions
    for entry in vocab.discriminators:
        if not isinstance(entry, dict):
            LOGGER.warning("skipping non-dict discriminator entry: %r", entry)
            continue
        name = entry.get("name")
        if not name:
            LOGGER.warning("skipping discriminator missing name: %r", entry)
            continue
        if name in BUILTIN_DISCRIMINATOR_NAMES:
            fired = _apply_builtin_discriminator(name, prompt, tokens)
        else:
            fired = _apply_custom_discriminator(entry, prompt, tokens)
        if fired:
            return {
                "match": False,
                "reason": f"discriminator:{name}",
                "layer_hit": "C_discriminator",
            }

    # Phase 3: strong ASCII anchors
    if tokens & vocab.ascii_anchors:
        return {
            "match": True,
            "reason": "strong_ascii",
            "layer_hit": "A_ascii",
        }

    # Phase 4: strong CJK substrings
    for sub in vocab.cjk_strong:
        if sub and sub in prompt:
            return {
                "match": True,
                "reason": f"strong_cjk:{sub}",
                "layer_hit": "B_cjk_substring",
            }

    # Phase 5: cursor + CJK usage co-occurrence
    if "cursor" in tokens and vocab.cursor_plus_cjk_usage:
        if any(s in prompt for s in vocab.cursor_plus_cjk_usage):
            return {
                "match": True,
                "reason": "cursor+cjk_usage",
                "layer_hit": "B_cjk_substring",
            }

    # Phase 6: weak accumulation — count CJK weak + ASCII weak hits
    cjk_weak_hits = sum(1 for s in vocab.cjk_weak if s and s in prompt)
    ascii_weak_hits = len(tokens & vocab.ascii_weak)
    total_hits = cjk_weak_hits + ascii_weak_hits
    if total_hits >= vocab.min_weak_hits:
        return {
            "match": True,
            "reason": f"weak_accumulation:{total_hits}",
            "layer_hit": "B_cjk_substring",
        }

    # Phase 7: default NO
    return {"match": False, "reason": "no_match", "layer_hit": "default"}


def _compute_f1(
    tp: int, fp: int, fn: int, tn: int
) -> Tuple[float, float, float, float]:
    """Return (precision, recall, f1, near_miss_fp_rate) from the confusion matrix."""

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    near_miss_fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return precision, recall, f1, near_miss_fp_rate


def evaluate_pack(
    eval_pack: Dict[str, Any], vocab: Vocabulary
) -> EvaluationResult:
    """Run ``trigger_match`` across every should/should-not prompt.

    ``eval_pack`` is the already-parsed yaml: a dict with optional keys
    ``should_trigger`` and ``should_not_trigger`` (each a list of
    strings). Missing keys are treated as empty lists (explicit log,
    no silent short-circuit).
    """

    if not isinstance(eval_pack, dict):
        raise TypeError(
            f"evaluate_pack expected dict eval_pack, got {type(eval_pack).__name__}"
        )

    should_trigger = list(eval_pack.get("should_trigger") or [])
    should_not_trigger = list(eval_pack.get("should_not_trigger") or [])

    if not should_trigger and not should_not_trigger:
        LOGGER.warning(
            "eval_pack has neither should_trigger nor should_not_trigger; "
            "all metrics will be zero"
        )

    tp = fp = fn = tn = 0
    per_prompt: List[Dict[str, Any]] = []

    for prompt in should_trigger:
        decision = trigger_match(prompt, vocab)
        per_prompt.append(
            {"prompt": prompt, "expected": True, **decision}
        )
        if decision["match"]:
            tp += 1
        else:
            fn += 1

    for prompt in should_not_trigger:
        decision = trigger_match(prompt, vocab)
        per_prompt.append(
            {"prompt": prompt, "expected": False, **decision}
        )
        if decision["match"]:
            fp += 1
        else:
            tn += 1

    precision, recall, f1, near_miss_fp_rate = _compute_f1(tp, fp, fn, tn)

    return EvaluationResult(
        n_should=len(should_trigger),
        n_should_not=len(should_not_trigger),
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        near_miss_fp_rate=round(near_miss_fp_rate, 4),
        per_prompt=per_prompt,
    )


def evaluate_pack_from_paths(
    eval_pack_path: Path, vocabulary_path: Path
) -> EvaluationResult:
    """Load both yaml files and run ``evaluate_pack``.

    Raises on missing / malformed files (explicit; per workspace rule
    "No Silent Failures").
    """

    eval_pack_path = Path(eval_pack_path)
    if not eval_pack_path.exists():
        raise FileNotFoundError(f"eval_pack yaml not found: {eval_pack_path}")
    with eval_pack_path.open("r", encoding="utf-8") as fh:
        eval_pack = yaml.safe_load(fh) or {}

    vocab = Vocabulary.from_yaml(vocabulary_path)
    return evaluate_pack(eval_pack, vocab)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cjk_trigger_eval",
        description=(
            "Generic CJK-aware trigger F1 evaluator. Measures R1/R2/R3/R4 "
            "per Si-Chip spec §3.1 D6 using a pluggable vocabulary yaml."
        ),
    )
    parser.add_argument(
        "--eval-pack",
        required=True,
        help="Path to eval_pack.yaml (should_trigger + should_not_trigger lists).",
    )
    parser.add_argument(
        "--vocabulary",
        required=True,
        help="Path to per-ability vocabulary.yaml (see Vocabulary schema).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit EvaluationResult as JSON on stdout.",
    )
    parser.add_argument(
        "--min-weak-hits",
        type=int,
        default=None,
        help=(
            "Override vocabulary's min_weak_hits threshold (optional). "
            "Default uses the value declared in vocabulary.yaml."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    vocab = Vocabulary.from_yaml(Path(args.vocabulary))
    if args.min_weak_hits is not None:
        vocab.min_weak_hits = args.min_weak_hits

    eval_pack_path = Path(args.eval_pack)
    if not eval_pack_path.exists():
        raise FileNotFoundError(f"eval_pack yaml not found: {eval_pack_path}")
    with eval_pack_path.open("r", encoding="utf-8") as fh:
        eval_pack = yaml.safe_load(fh) or {}

    result = evaluate_pack(eval_pack, vocab)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    else:
        print(f"CJK Trigger Eval Result (script v{SCRIPT_VERSION})")
        print(f"  should_trigger     : {result.n_should}")
        print(f"  should_not_trigger : {result.n_should_not}")
        print(
            f"  tp={result.tp}  fp={result.fp}  tn={result.tn}  fn={result.fn}"
        )
        print(f"  R1_trigger_precision    : {result.precision:.4f}")
        print(f"  R2_trigger_recall       : {result.recall:.4f}")
        print(f"  R3_trigger_F1           : {result.f1:.4f}")
        print(f"  R4_near_miss_FP_rate    : {result.near_miss_fp_rate:.4f}")

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    sys.exit(main())
