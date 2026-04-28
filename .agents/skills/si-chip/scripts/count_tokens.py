#!/usr/bin/env python3
"""Deterministic token counter for SKILL.md frontmatter and body.

Implements spec §3.2 (C1 metadata_tokens / C2 body_tokens) and §7.3
packaging gate budget enforcement (`metadata_tokens ≤ 100`,
`body_tokens ≤ 5000`) of `.local/research/spec_v0.1.0.md`.

Two backends:

* ``tiktoken`` when importable: ``encoding_for_model("gpt-4o")`` with
  fallback to ``get_encoding("cl100k_base")``.  Cursor and Claude Code
  use Anthropic-family tokenizers; ``cl100k_base`` is a pragmatic,
  deterministic stand-in until the runtime tokenizer is wired (DESIGN.md
  §5).
* Stdlib fallback: split on any whitespace **or** any single
  non-alphanumeric character, drop empties, count surviving units.  This
  approximates BPE token counts within ~30% on prose, which is enough to
  keep the §7.3 gate honest when ``tiktoken`` is unavailable.

Round 5 addition — Flesch-Kincaid grade level helper (spec §3.1 D5/U1):

* :func:`flesch_kincaid_grade` computes ``FK = 0.39 * (words/sentences)
  + 11.8 * (syllables/words) - 15.59`` against a plaintext string. The
  syllable counter is a deterministic vowel-group heuristic with a
  silent-e adjustment; the sentence counter strips periods that fall
  between digits (e.g. ``v0.1.0``) so version strings are not mistaken
  for sentence boundaries. Result is clamped to ``[0.0, 24.0]`` (the
  nominal FK grade-level range used in v0.1.0 §3.1 D5).

CLI::

    python scripts/count_tokens.py --file PATH \\
        [--metadata-only|--body-only|--both] \\
        [--budget-meta 100] [--budget-body 5000] [--json] \\
        [--fk-description]

Exit code is 0 when both observed token counts are within their
respective budgets, else 1 (workspace rule "No Silent Failures").
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

LOGGER = logging.getLogger("si_chip.count_tokens")

SCRIPT_VERSION = "0.1.1"

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<meta>.*?)\n---\s*\n?(?P<body>.*)\Z",
    re.DOTALL,
)


def split_frontmatter(text: str) -> Tuple[str, str]:
    """Split a markdown file into (frontmatter, body).

    Returns ``("", text)`` when there is no leading ``---`` block.

    >>> split_frontmatter("---\\nname: x\\n---\\nbody here")
    ('name: x', 'body here')
    >>> split_frontmatter("no frontmatter here")
    ('', 'no frontmatter here')
    """

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group("meta").strip("\n"), m.group("body")


def _fallback_count(text: str) -> int:
    """Stdlib-only deterministic token count.

    Splits on whitespace and any single non-alphanumeric character,
    drops empty units.

    >>> _fallback_count("hello, world!  ok")
    3
    >>> _fallback_count("")
    0
    """

    if not text:
        return 0
    units = re.split(r"[\s\W_]+", text, flags=re.UNICODE)
    return sum(1 for u in units if u)


def _tiktoken_count(text: str, _cache: dict = {}) -> Optional[int]:
    """Return tiktoken count for ``text`` or ``None`` when unavailable."""

    if "enc" not in _cache:
        try:
            import tiktoken
        except ImportError:
            _cache["enc"] = None
            return None
        try:
            _cache["enc"] = tiktoken.encoding_for_model("gpt-4o")
        except Exception:
            try:
                _cache["enc"] = tiktoken.get_encoding("cl100k_base")
            except Exception as exc:
                LOGGER.warning("tiktoken init failed (%s); falling back", exc)
                _cache["enc"] = None
                return None
    enc = _cache["enc"]
    if enc is None:
        return None
    return len(enc.encode(text))


def count_tokens(text: str) -> Tuple[int, str]:
    """Count tokens in ``text``; return ``(count, backend)``.

    >>> n, backend = count_tokens("hello world")
    >>> n > 0 and backend in {"tiktoken", "fallback"}
    True
    """

    n = _tiktoken_count(text)
    if n is None:
        return _fallback_count(text), "fallback"
    return n, "tiktoken"


# ─────────────── Flesch-Kincaid grade level (spec §3.1 D5/U1) ───────────────
#
# Added in Round 5 (project_version 0.1.4). The goal is a deterministic,
# stdlib-only FK grade level computed against the SKILL.md ``description``
# frontmatter field so U1_description_readability can be populated every
# round without pulling in a text-analysis dependency.
#
# Formula (spec §3.1 D5):
#     FK = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
#
# Heuristics:
#   * word = maximal run of ``[A-Za-z][A-Za-z'-]*``.
#   * syllable counter = vowel-group heuristic. Lowercase the word,
#     strip non-alphabetic characters, count non-empty runs of
#     ``[aeiouy]+``. Adjust by -1 if the word ends in a silent ``e``
#     (``w.endswith("e")`` AND ``not w.endswith("le")`` AND len > 3).
#     Minimum 1 syllable per non-empty word.
#   * sentence counter = count of ``[.!?]+`` runs AFTER stripping
#     periods that fall between two digits (so ``v0.1.0`` is ONE
#     sentence terminator, not three). Minimum 1 sentence for a
#     non-empty text.
#   * final grade clamped to ``[0.0, 24.0]``.
#
# The FK grade is computed deterministically across rebuilds because the
# regex heuristics are stdlib-only and do not depend on any external
# wordlist (workspace rule: reproducibility > best-case accuracy).


_FK_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
_FK_SENT_RE = re.compile(r"[.!?]+")
_FK_DIGIT_PERIOD_RE = re.compile(r"(?<=\d)\.(?=\d)")
_FK_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")
_FK_NON_ALPHA_RE = re.compile(r"[^a-z]")
_FK_GRADE_MIN = 0.0
_FK_GRADE_MAX = 24.0


def _fk_count_syllables(word: str) -> int:
    """Count syllables in a single word (vowel-group heuristic).

    Returns 0 for empty / non-alphabetic input; at least 1 for any
    non-empty word with at least one alpha character.

    >>> _fk_count_syllables("factory")
    3
    >>> _fk_count_syllables("Persistent")
    3
    >>> _fk_count_syllables("")
    0
    >>> _fk_count_syllables("a")
    1
    """

    w = word.lower()
    w = _FK_NON_ALPHA_RE.sub("", w)
    if not w:
        return 0
    groups = _FK_VOWEL_GROUP_RE.findall(w)
    n = len(groups)
    if len(w) > 3 and w.endswith("e") and not w.endswith("le"):
        if n >= 1:
            n -= 1
    return max(n, 1)


def _fk_count_words(text: str) -> int:
    """Count alpha-led words in ``text`` (whitespace + punctuation split).

    A "word" here is a maximal run starting with an alphabetic character
    followed by letters, apostrophes, or hyphens. Pure-numeric tokens are
    ignored. Version strings such as ``v0.1.0`` contribute one word (the
    leading ``v``), which is the deliberate behaviour — single letters
    like ``a`` and ``I`` also count as words in FK-style analyses.

    >>> _fk_count_words("Use when profiling, evaluating.")
    4
    >>> _fk_count_words("v0.1.0")
    1
    >>> _fk_count_words("12345 98 00")
    0
    """

    return len(_FK_WORD_RE.findall(text))


def _fk_count_sentences(text: str) -> int:
    """Count sentence terminators, ignoring periods between digits.

    Returns 0 for empty input; at least 1 for any non-empty text so
    FK does not divide by zero on single-fragment descriptions.

    >>> _fk_count_sentences("One. Two. Three.")
    3
    >>> _fk_count_sentences("Version v0.1.0 released.")
    1
    >>> _fk_count_sentences("")
    0
    >>> _fk_count_sentences("No terminal punctuation here")
    1
    """

    if not text or not text.strip():
        return 0
    cleaned = _FK_DIGIT_PERIOD_RE.sub("", text)
    runs = _FK_SENT_RE.findall(cleaned)
    return max(len(runs), 1)


def flesch_kincaid_grade(text: str) -> Tuple[float, Dict[str, Any]]:
    """Compute the Flesch-Kincaid grade level of ``text``.

    FK = ``0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59``.

    Returns ``(grade, details)`` where ``details`` is a dict carrying
    the raw counts (``words``, ``sentences``, ``syllables``), the
    un-clamped grade (``raw_grade``), and the final clamped grade
    (``grade``). ``grade`` is clamped to ``[0.0, 24.0]``; the
    un-clamped value is kept for provenance.

    Empty / whitespace-only input returns ``(0.0, {"words": 0, ...})``
    without raising (workspace rule: this helper is used by the
    aggregator which must not crash on missing description strings).

    >>> g, d = flesch_kincaid_grade("The cat sat on the mat.")
    >>> d["words"]
    6
    >>> d["sentences"]
    1
    >>> 0.0 <= g <= 24.0
    True
    >>> flesch_kincaid_grade("")[0]
    0.0
    """

    details: Dict[str, Any] = {
        "words": 0,
        "sentences": 0,
        "syllables": 0,
        "raw_grade": 0.0,
        "grade": 0.0,
        "formula": "0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59",
    }
    if not text or not text.strip():
        return 0.0, details

    words_list = _FK_WORD_RE.findall(text)
    n_words = len(words_list)
    details["words"] = n_words
    if n_words == 0:
        details["sentences"] = _fk_count_sentences(text)
        return 0.0, details

    n_sentences = _fk_count_sentences(text)
    if n_sentences == 0:
        n_sentences = 1
    details["sentences"] = n_sentences

    n_syllables = sum(_fk_count_syllables(w) for w in words_list)
    details["syllables"] = n_syllables

    raw_grade = (
        0.39 * (n_words / n_sentences)
        + 11.8 * (n_syllables / n_words)
        - 15.59
    )
    details["raw_grade"] = raw_grade

    grade = max(_FK_GRADE_MIN, min(_FK_GRADE_MAX, raw_grade))
    details["grade"] = grade
    return grade, details


def extract_description_from_frontmatter(frontmatter_text: str) -> Optional[str]:
    """Pull the ``description:`` value out of a YAML frontmatter string.

    Returns ``None`` when the field is missing or the YAML is
    malformed. Uses a lazy import of :mod:`yaml` so environments that
    only need the token counter still work without PyYAML.

    >>> extract_description_from_frontmatter("name: x\\ndescription: hi there")
    'hi there'
    >>> extract_description_from_frontmatter("name: x") is None
    True
    """

    if not frontmatter_text.strip():
        return None
    try:
        import yaml  # local import: PyYAML is optional for callers that skip FK.
    except ImportError:
        LOGGER.warning("PyYAML not available; cannot extract frontmatter description")
        return None
    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        LOGGER.warning("frontmatter YAML parse failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    desc = data.get("description")
    if desc is None:
        return None
    return str(desc).strip()


def skill_md_description_fk_grade(
    skill_md_path: Path,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Read ``skill_md_path`` and return the FK grade of its description.

    This is the helper the Round 5 aggregator wires into
    ``U1_description_readability``. Returns ``(None, {"error": ...})``
    when the file is missing, has no frontmatter, or the description
    field is absent (workspace rule "No Silent Failures" is upheld by
    raising FileNotFoundError on the path check only; structural
    errors propagate as an explicit error record so the aggregator
    can skip the hoist without silently emitting a zero).
    """

    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md path not found: {skill_md_path}")
    text = skill_md_path.read_text(encoding="utf-8")
    meta_text, _body_text = split_frontmatter(text)
    if not meta_text:
        return None, {
            "error": "no frontmatter block",
            "path": str(skill_md_path),
        }
    desc = extract_description_from_frontmatter(meta_text)
    if desc is None:
        return None, {
            "error": "no description field in frontmatter",
            "path": str(skill_md_path),
        }
    grade, details = flesch_kincaid_grade(desc)
    details["description_text"] = desc
    details["path"] = str(skill_md_path)
    return grade, details


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count metadata/body tokens in a SKILL.md or any text file.",
    )
    parser.add_argument("--file", required=True, help="Path to the file to count.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--metadata-only", action="store_true", help="Count only the YAML frontmatter.")
    scope.add_argument("--body-only", action="store_true", help="Count only the body (after frontmatter).")
    scope.add_argument("--both", action="store_true", help="Count both (default).")
    parser.add_argument("--budget-meta", type=int, default=100, help="Frontmatter budget (default: 100).")
    parser.add_argument("--budget-body", type=int, default=5000, help="Body budget (default: 5000).")
    parser.add_argument(
        "--fk-description",
        action="store_true",
        help=(
            "Also compute the Flesch-Kincaid grade level of the SKILL.md "
            "description frontmatter field (spec §3.1 D5/U1). Added in Round 5."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    parser.add_argument("--verbose", action="store_true", help="Set log level to INFO.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    path = Path(args.file)
    if not path.exists():
        LOGGER.error("file not found: %s", path)
        return 1
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        LOGGER.error("failed to read %s: %s", path, exc)
        return 1

    meta_text, body_text = split_frontmatter(text)
    backend = "fallback"
    meta_count = 0
    body_count = 0

    want_meta = args.metadata_only or args.both or not (args.body_only)
    want_body = args.body_only or args.both or not (args.metadata_only)
    if not (args.metadata_only or args.body_only or args.both):
        want_meta = want_body = True

    if want_meta:
        meta_count, backend = count_tokens(meta_text)
    if want_body:
        body_count, backend = count_tokens(body_text)

    meta_ok = (not want_meta) or (meta_count <= args.budget_meta)
    body_ok = (not want_body) or (body_count <= args.budget_body)
    passed = meta_ok and body_ok

    fk_grade: Optional[float] = None
    fk_details: Optional[Dict[str, Any]] = None
    if args.fk_description:
        try:
            fk_grade, fk_details = skill_md_description_fk_grade(path)
        except FileNotFoundError:
            LOGGER.error("cannot compute --fk-description: %s missing", path)
            return 1

    if args.json:
        payload = {
            "metadata_tokens": meta_count if want_meta else None,
            "body_tokens": body_count if want_body else None,
            "budget_meta": args.budget_meta,
            "budget_body": args.budget_body,
            "pass": passed,
            "backend": backend,
            "script_version": SCRIPT_VERSION,
        }
        if args.fk_description:
            payload["fk_description"] = {
                "grade": fk_grade,
                "details": fk_details,
            }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if want_meta:
            print(f"metadata_tokens={meta_count}")
        if want_body:
            print(f"body_tokens={body_count}")
        if args.fk_description and fk_grade is not None:
            print(f"fk_description_grade={fk_grade:.4f}")
        print(f"verdict={'pass' if passed else 'fail'}")

    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.count_tokens").error("fatal: %s", exc)
        sys.exit(1)
