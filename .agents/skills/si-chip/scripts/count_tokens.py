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
import math
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

LOGGER = logging.getLogger("si_chip.count_tokens")

SCRIPT_VERSION = "0.1.3"

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


# ─────────── Round 7: D2/C5 context_rot_risk (spec §3.1 D2/C5) ───────────
#
# Round 7 fills the last two D2 context_economy cells (C5 + C6). The C3
# cell stays explicit-null by design (Si-Chip references are loaded on
# demand only — resolved_tokens has no deterministic static value).
#
# C5 formula (spec §3.1 D2/C5; Round 6 next_action_plan a1):
#
#     C5 = clip(body_tokens / typical_context_window
#               + 0.05 * reference_fanout_depth, 0.0, 1.0)
#
# ``typical_context_window`` defaults to 200_000 (Sonnet 4.6 baseline, per
# references/metrics-r6-summary.md). The multiplier 0.05 per fanout hop
# captures the empirical "each additional ref loads ~5% more context" rule
# from the 2026 frontier-model context-rot studies cited by
# references/metrics-r6-summary.md.
#
# ``reference_fanout_depth`` is the count of ``.md`` files under
# ``references_dir`` that the SKILL.md body literally references by
# filename (substring match). Depth = 1 when no references_dir is
# passed or the directory is missing (a single-layer SKILL.md still
# has the SKILL.md body itself on the context rot graph).
#
# Helpers preserve workspace rule "No Silent Failures": negative or
# nonsensical inputs raise ``ValueError`` rather than being clamped.

DEFAULT_TYPICAL_CONTEXT_WINDOW = 200_000


def context_rot_risk(
    body_tokens: int,
    fanout_depth: int,
    typical_window: int = DEFAULT_TYPICAL_CONTEXT_WINDOW,
) -> float:
    """Compute the C5 context_rot_risk proxy.

    Formula: ``C5 = clip(body_tokens / typical_window
    + 0.05 * fanout_depth, 0.0, 1.0)``.

    Args:
        body_tokens: Token count of the SKILL.md body (spec §3.1 D2/C2).
            Must be ``>= 0``.
        fanout_depth: Integer count of references the SKILL.md body
            loads on-demand. Must be ``>= 0``. Per the workspace
            "No Silent Failures" rule, negative values raise
            ``ValueError`` instead of being silently clamped.
        typical_window: Nominal context-window size in tokens against
            which ``body_tokens`` is normalised. Defaults to 200_000
            (Sonnet 4.6 baseline per references/metrics-r6-summary.md);
            raise to 1_000_000 for Opus-class models. Must be ``> 0``.

    Returns:
        A float in ``[0.0, 1.0]``. Higher = more context-rot risk.

    Raises:
        ValueError: on negative ``body_tokens`` / ``fanout_depth`` or
            non-positive ``typical_window``.

    >>> context_rot_risk(2020, 1)
    0.0601
    >>> context_rot_risk(200_000, 0)
    1.0
    >>> context_rot_risk(0, 2)
    0.1
    >>> 0.0 <= context_rot_risk(1000, 3) <= 1.0
    True
    """

    if body_tokens < 0:
        raise ValueError(f"body_tokens must be >= 0, got {body_tokens}")
    if fanout_depth < 0:
        raise ValueError(f"fanout_depth must be >= 0, got {fanout_depth}")
    if typical_window <= 0:
        raise ValueError(f"typical_window must be > 0, got {typical_window}")

    raw = body_tokens / typical_window + 0.05 * fanout_depth
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    # Round to 4 decimals for stable comparisons / YAML stability;
    # this is cosmetic — the clip is already enforced above.
    return round(raw, 4)


def skill_md_context_rot_risk(
    skill_md_path: Path,
    references_dir: Optional[Path],
    typical_window: int = DEFAULT_TYPICAL_CONTEXT_WINDOW,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Compute C5 for a SKILL.md + its references directory.

    Reads the SKILL.md body, tokenises it via :func:`count_tokens`, and
    derives ``fanout_depth`` as the count of ``*.md`` files under
    ``references_dir`` whose filename appears (literal substring match)
    in the SKILL.md body. When ``references_dir`` is ``None`` or missing
    on disk, ``fanout_depth`` defaults to ``0`` and the derivation record
    documents the degenerate path.

    Returns ``(value, derivation_dict)``. ``value`` is ``None`` when the
    SKILL.md path is missing (raises ``FileNotFoundError`` in that case
    to honour "No Silent Failures") or when the body cannot be split.
    """

    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md path not found: {skill_md_path}")

    text = skill_md_path.read_text(encoding="utf-8")
    _meta_text, body_text = split_frontmatter(text)
    body_tokens, backend = count_tokens(body_text)

    fanout_depth = 0
    referenced_files: List[str] = []
    refs_dir_exists = False
    refs_dir_resolved: Optional[str] = None
    if references_dir is not None:
        refs_dir_resolved = str(references_dir)
        if references_dir.exists() and references_dir.is_dir():
            refs_dir_exists = True
            for md_path in sorted(references_dir.glob("*.md")):
                if md_path.name in body_text:
                    referenced_files.append(md_path.name)
            fanout_depth = len(referenced_files)
        else:
            LOGGER.warning(
                "references_dir %s does not exist or is not a directory; "
                "fanout_depth defaults to 0 (documented degenerate path)",
                references_dir,
            )

    value = context_rot_risk(body_tokens, fanout_depth, typical_window)
    derivation: Dict[str, Any] = {
        "method": (
            "context_rot_risk(body_tokens, fanout_depth, typical_window=200_000); "
            "formula = clip(body_tokens/typical_window + 0.05*fanout_depth, 0, 1)"
        ),
        "body_tokens": body_tokens,
        "body_tokens_backend": backend,
        "typical_window": typical_window,
        "fanout_depth": fanout_depth,
        "referenced_files": referenced_files,
        "references_dir": refs_dir_resolved,
        "references_dir_exists": refs_dir_exists,
        "skill_md_path": str(skill_md_path),
        "value_c5": value,
    }
    return value, derivation


# ─────────── Round 7: D2/C6 scope_overlap_score (spec §3.1 D2/C6) ───────────
#
# C6 is a Jaccard-similarity metric that compares the Si-Chip SKILL.md
# description against neighbour SKILL.md descriptions in the workspace.
# The value surfaces the "description competition" surface area that
# Round 9 R8 widens into R8_description_competition_index.
#
# C6 formula (Round 6 next_action_plan a2):
#   1. Tokenise each description (NFKD + lowercase + strip ASCII-
#      non-alphanumeric + split whitespace).
#   2. Filter a minimal English stopword list.
#   3. Compute Jaccard = |A ∩ B| / |A ∪ B| per pair.
#   4. C6 = max(Jaccard) across the neighbour set (conservative —
#      surfaces the WORST description-competition offender).

DEFAULT_STOPWORDS: FrozenSet[str] = frozenset({
    "the",
    "a",
    "an",
    "when",
    "use",
    "this",
    "for",
    "it",
    "with",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "is",
    "are",
    "be",
})


_SCOPE_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def tokenize_description(
    text: str,
    stopwords: Optional[FrozenSet[str]] = None,
) -> Set[str]:
    """Normalise and tokenise a SKILL.md description string.

    Pipeline:
      * NFKD-normalise (compatibility decomposition so Unicode
        characters split cleanly into ASCII + combining marks).
      * Lowercase.
      * Replace every non-ASCII-alphanumeric run with a single space.
      * Split on whitespace and drop empty tokens.
      * Drop tokens in ``stopwords`` (default: :data:`DEFAULT_STOPWORDS`).

    Args:
        text: Raw description text.
        stopwords: Optional stopword set; defaults to the minimal
            English set declared in :data:`DEFAULT_STOPWORDS`. Pass
            ``frozenset()`` to disable stopword filtering explicitly.

    Returns:
        A ``set[str]`` of surviving tokens. Empty input yields an
        empty set (workspace rule: deterministic, no silent error).

    >>> sorted(tokenize_description("Use when profiling: test."))
    ['profiling', 'test']
    >>> tokenize_description("") == set()
    True
    """

    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS

    if not text:
        return set()

    normalised = unicodedata.normalize("NFKD", text)
    lowered = normalised.lower()
    cleaned = _SCOPE_NON_ALNUM_RE.sub(" ", lowered)
    tokens = {t for t in cleaned.split() if t and t not in stopwords}
    return tokens


def jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    """Compute the Jaccard similarity ``|A ∩ B| / |A ∪ B|``.

    Empty-vs-empty returns ``0.0`` by convention (documented: the
    workspace cannot have "competition" between two nothings).

    Args:
        a: First token set.
        b: Second token set.

    Returns:
        A float in ``[0.0, 1.0]``.

    >>> jaccard_similarity({"a", "b"}, {"a", "b"})
    1.0
    >>> jaccard_similarity({"a", "b"}, {"c", "d"})
    0.0
    >>> round(jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"}), 4)
    0.5
    >>> jaccard_similarity(set(), set())
    0.0
    """

    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    intersection = a & b
    return len(intersection) / len(union)


def skill_md_scope_overlap_score(
    skill_md_path: Path,
    neighbor_skill_md_paths: Iterable[Path],
    stopwords: Optional[FrozenSet[str]] = None,
) -> Tuple[Optional[float], List[Dict[str, Any]]]:
    """Compute the C6 scope_overlap_score for a SKILL.md.

    Extracts Si-Chip's SKILL.md description, tokenises it, and computes
    Jaccard similarity against each neighbour SKILL.md's description.
    Returns ``(max_jaccard, pairs_list)`` where ``pairs_list`` is
    sorted by ``jaccard`` DESCENDING. Missing neighbour files are
    skipped with a ``LOGGER.warning`` (workspace rule: log + continue,
    never silently swallow — the caller sees every skip in the
    derivation record).

    Returns ``(None, [])`` when the Si-Chip SKILL.md has no
    description field (documented degenerate path).

    Raises:
        FileNotFoundError: when ``skill_md_path`` is missing.
    """

    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md path not found: {skill_md_path}")

    text = skill_md_path.read_text(encoding="utf-8")
    meta_text, _body_text = split_frontmatter(text)
    if not meta_text:
        LOGGER.warning(
            "SKILL.md at %s has no frontmatter; C6 cannot be computed",
            skill_md_path,
        )
        return None, []

    base_desc = extract_description_from_frontmatter(meta_text)
    if base_desc is None:
        LOGGER.warning(
            "SKILL.md at %s has no description field; C6 cannot be computed",
            skill_md_path,
        )
        return None, []

    base_tokens = tokenize_description(base_desc, stopwords=stopwords)

    pairs: List[Dict[str, Any]] = []
    for neighbor_path in neighbor_skill_md_paths:
        if not neighbor_path.exists():
            LOGGER.warning(
                "neighbor SKILL.md at %s is missing; skipping",
                neighbor_path,
            )
            pairs.append({
                "neighbor_path": str(neighbor_path),
                "jaccard": None,
                "error": "missing",
            })
            continue
        try:
            ntext = neighbor_path.read_text(encoding="utf-8")
        except OSError as exc:
            LOGGER.warning(
                "failed to read neighbor %s: %s; skipping",
                neighbor_path,
                exc,
            )
            pairs.append({
                "neighbor_path": str(neighbor_path),
                "jaccard": None,
                "error": f"read-failure: {exc}",
            })
            continue
        n_meta, _ = split_frontmatter(ntext)
        n_desc = extract_description_from_frontmatter(n_meta) if n_meta else None
        if n_desc is None:
            LOGGER.warning(
                "neighbor %s has no description field; recording jaccard=0.0",
                neighbor_path,
            )
            pairs.append({
                "neighbor_path": str(neighbor_path),
                "jaccard": 0.0,
                "neighbor_tokens_count": 0,
            })
            continue
        n_tokens = tokenize_description(n_desc, stopwords=stopwords)
        j = jaccard_similarity(base_tokens, n_tokens)
        pairs.append({
            "neighbor_path": str(neighbor_path),
            "jaccard": j,
            "neighbor_tokens_count": len(n_tokens),
        })

    scored_pairs = [p for p in pairs if isinstance(p.get("jaccard"), (int, float))]
    if not scored_pairs:
        LOGGER.warning(
            "no scorable neighbors for %s; C6 defaults to 0.0 (no competition observed)",
            skill_md_path,
        )
        return 0.0, pairs

    max_jaccard = max(p["jaccard"] for p in scored_pairs)
    # Sort pairs by jaccard DESC (None/error values go last).
    pairs_sorted = sorted(
        pairs,
        key=lambda p: (
            0 if isinstance(p.get("jaccard"), (int, float)) else 1,
            -(p["jaccard"] if isinstance(p.get("jaccard"), (int, float)) else 0),
        ),
    )
    return float(max_jaccard), pairs_sorted


# ─────────── Round 9: D6/R8 description_competition_index (spec §3.1 D6/R8) ───────────
#
# R8 = formal across-matrix description-competition index — how "loud" the
# Si-Chip SKILL.md description is within its neighbor set. Distinct from
# Round 7's C6 which is a conservative max-Jaccard against the same
# neighbor set (surfaces the WORST single offender). R8 supports two
# complementary methods so the operator can choose the right signal:
#
#   * method="max_jaccard"   — token-set Jaccard; R8 == max(Jaccard over
#     neighbors). This is the SAME family as C6 — surfaces the WORST
#     description-competition offender. Default because Round 7's C6
#     infrastructure is already battle-tested and the Jaccard signal
#     is the stable choice across diverse neighbor sets.
#   * method="tfidf_cosine_mean" — TF-IDF cosine similarity between the
#     base description and each neighbor, averaged. Surfaces AVERAGE
#     competition rather than WORST competition. Complements the Jaccard
#     max with a mean signal.
#
# Both methods are DETERMINISTIC (sorted vocab; no RNG); re-running on
# the same corpus yields byte-identical outputs. Workspace rule
# "No Silent Failures" applies: unknown method or empty neighbor list
# raises ValueError.
#
# R8 is metadata-retrieval / kNN-heuristic expansion per spec §5.1
# surface 1+2 — NOT router model training (§5.2 forbidden).


def tokenize_description_list(
    text: str,
    stopwords: Optional[FrozenSet[str]] = None,
) -> List[str]:
    """Tokenise a description string into a LIST preserving duplicates.

    Pipeline mirrors :func:`tokenize_description` but returns a
    duplicate-preserving list (TF-IDF needs term frequencies).

    >>> tokenize_description_list("alpha alpha beta")
    ['alpha', 'alpha', 'beta']
    >>> tokenize_description_list("")
    []
    """

    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS
    if not text:
        return []
    normalised = unicodedata.normalize("NFKD", text)
    lowered = normalised.lower()
    cleaned = _SCOPE_NON_ALNUM_RE.sub(" ", lowered)
    return [t for t in cleaned.split() if t and t not in stopwords]


def tf_idf_vector(
    tokens: List[str],
    corpus: List[List[str]],
) -> Dict[str, float]:
    """Compute a standard TF-IDF vector for ``tokens`` given ``corpus``.

    Formula (smoothed, sklearn-style):

        TF(t, d)  = count(t, d) / max(len(d), 1)
        IDF(t)    = ln((1 + N) / (1 + df(t))) + 1
        TFIDF(t)  = TF(t, d) * IDF(t)

    Where ``N = len(corpus)`` and ``df(t) = |{ d' in corpus : t in d' }|``.

    Returns a dict ``{term: tfidf_weight}`` sorted-key-iterable by
    construction (we iterate over ``sorted(set(tokens))`` so the output
    is byte-identical across re-runs with the same input — no RNG).

    Args:
        tokens: Token list for the target document (may contain duplicates).
        corpus: List of token lists covering every document. The target
            document's tokens SHOULD be included in ``corpus`` so its own
            term counts contribute to ``df``.

    Returns:
        A ``dict[str, float]`` TF-IDF vector. Empty input → empty dict.
        Empty corpus → empty dict (df denominators cannot be computed).

    >>> v = tf_idf_vector(["alpha", "beta"], [["alpha", "beta"], ["alpha"]])
    >>> sorted(v.keys())
    ['alpha', 'beta']
    >>> v["beta"] > v["alpha"]  # beta is rarer across corpus → higher idf
    True
    >>> tf_idf_vector([], [["alpha"]])
    {}
    >>> tf_idf_vector(["alpha"], [])
    {}
    """

    if not tokens:
        return {}
    if not corpus:
        return {}

    n_docs = len(corpus)
    doc_len = len(tokens)

    term_counts: Dict[str, int] = {}
    for t in tokens:
        term_counts[t] = term_counts.get(t, 0) + 1

    # df(term) computed deterministically by iterating corpus in order.
    df_counts: Dict[str, int] = {}
    for term in sorted(term_counts.keys()):
        df = 0
        for doc in corpus:
            if term in doc:
                df += 1
        df_counts[term] = df

    vector: Dict[str, float] = {}
    for term in sorted(term_counts.keys()):
        tf = term_counts[term] / doc_len
        df = df_counts[term]
        idf = math.log((1.0 + n_docs) / (1.0 + df)) + 1.0
        vector[term] = tf * idf
    return vector


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse TF-IDF vectors.

    Returns ``0.0`` when either vector is empty or has zero norm
    (documented degenerate path — the workspace cannot have
    "competition" between two nothings, nor between something and
    nothing). Workspace rule "No Silent Failures" is preserved by
    returning a deterministic sentinel rather than raising
    ``ZeroDivisionError``.

    Args:
        a: First TF-IDF vector as ``{term: weight}``.
        b: Second TF-IDF vector as ``{term: weight}``.

    Returns:
        Cosine similarity in ``[0.0, 1.0]``. For negative weights the
        range extends to ``[-1.0, 1.0]`` but TF-IDF weights are
        non-negative so the standard range holds.

    >>> round(cosine_similarity({"a": 1.0, "b": 1.0}, {"a": 1.0, "b": 1.0}), 6)
    1.0
    >>> cosine_similarity({"a": 1.0}, {"b": 1.0})
    0.0
    >>> cosine_similarity({}, {"a": 1.0})
    0.0
    >>> cosine_similarity({}, {})
    0.0
    """

    if not a or not b:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    # Iterate over the smaller vector for efficiency; intersection only.
    if len(a) > len(b):
        a, b = b, a
    dot = 0.0
    for term, va in a.items():
        vb = b.get(term)
        if vb is not None:
            dot += va * vb
    return dot / (norm_a * norm_b)


_R8_METHODS: FrozenSet[str] = frozenset({"max_jaccard", "tfidf_cosine_mean"})


def skill_md_description_competition_index(
    skill_md_path: Path,
    neighbor_skill_md_paths: Iterable[Path],
    *,
    method: str = "max_jaccard",
    stopwords: Optional[FrozenSet[str]] = None,
) -> Tuple[float, List[Dict[str, Any]]]:
    """Compute R8 description-competition index for a SKILL.md.

    R8 = how strongly the base SKILL.md description competes with its
    neighbor skill descriptions on the routing surface. Two methods:

    * ``method="max_jaccard"`` (default): R8 = max Jaccard similarity
      between the base description's token SET and each neighbor
      description's token SET. This is the SAME formula family as
      C6 (Round 7); chosen as default because the set-based Jaccard
      is deterministic, bounded in ``[0.0, 1.0]``, and surfaces the
      WORST single offender (the neighbor most likely to steal a
      routing invocation). Mirrors the workspace's existing C6
      infrastructure.

    * ``method="tfidf_cosine_mean"``: R8 = MEAN TF-IDF cosine
      similarity across the neighbor set. Surfaces AVERAGE
      competition across the neighbor population — complementary
      signal to Jaccard max. Corpus = [base_tokens] + neighbor_tokens
      (base included so its own term counts contribute to df).

    Args:
        skill_md_path: Base SKILL.md path. Must exist (raises
            ``FileNotFoundError`` otherwise per "No Silent Failures").
        neighbor_skill_md_paths: Iterable of neighbor SKILL.md paths.
            Must be non-empty — an empty iterable raises
            ``ValueError`` (the "competition" question is
            ill-defined against zero neighbors; the caller should
            short-circuit to 0.0 explicitly upstream, which matches
            C6's :func:`skill_md_scope_overlap_score` behaviour).
        method: One of ``"max_jaccard"`` or ``"tfidf_cosine_mean"``.
            Any other value raises ``ValueError``.
        stopwords: Optional stopword override (defaults to
            :data:`DEFAULT_STOPWORDS`).

    Returns:
        ``(value, pairs_list)`` where ``value`` is in ``[0.0, 1.0]``
        and ``pairs_list`` enumerates per-neighbor similarity
        (deterministic sort: DESC by similarity).

    Raises:
        FileNotFoundError: when ``skill_md_path`` does not exist.
        ValueError: on empty ``neighbor_skill_md_paths`` or unknown
            ``method``.
    """

    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md path not found: {skill_md_path}")
    if method not in _R8_METHODS:
        raise ValueError(
            f"unknown R8 method {method!r}; must be one of {sorted(_R8_METHODS)}"
        )

    neighbor_list: List[Path] = list(neighbor_skill_md_paths)
    if not neighbor_list:
        raise ValueError(
            "empty neighbor list; R8 competition requires at least one neighbor"
        )

    text = skill_md_path.read_text(encoding="utf-8")
    meta_text, _body_text = split_frontmatter(text)
    if not meta_text:
        LOGGER.warning(
            "SKILL.md at %s has no frontmatter; R8 cannot be computed",
            skill_md_path,
        )
        return 0.0, []

    base_desc = extract_description_from_frontmatter(meta_text)
    if base_desc is None:
        LOGGER.warning(
            "SKILL.md at %s has no description field; R8 cannot be computed",
            skill_md_path,
        )
        return 0.0, []

    base_token_list = tokenize_description_list(base_desc, stopwords=stopwords)
    base_token_set = set(base_token_list)

    # Collect per-neighbor tokens; skip missing / undescribed neighbors
    # with explicit error records (workspace "No Silent Failures").
    neighbor_records: List[Dict[str, Any]] = []
    for neighbor_path in neighbor_list:
        record: Dict[str, Any] = {"neighbor_path": str(neighbor_path)}
        if not neighbor_path.exists():
            LOGGER.warning(
                "neighbor SKILL.md at %s is missing; skipping",
                neighbor_path,
            )
            record["error"] = "missing"
            record["similarity"] = None
            record["tokens"] = None
            neighbor_records.append(record)
            continue
        try:
            ntext = neighbor_path.read_text(encoding="utf-8")
        except OSError as exc:
            LOGGER.warning(
                "failed to read neighbor %s: %s; skipping",
                neighbor_path, exc,
            )
            record["error"] = f"read-failure: {exc}"
            record["similarity"] = None
            record["tokens"] = None
            neighbor_records.append(record)
            continue
        n_meta, _ = split_frontmatter(ntext)
        n_desc = extract_description_from_frontmatter(n_meta) if n_meta else None
        if n_desc is None:
            LOGGER.warning(
                "neighbor %s has no description field; recording similarity=0.0",
                neighbor_path,
            )
            record["similarity"] = 0.0
            record["tokens"] = []
            record["note"] = "no description field"
            neighbor_records.append(record)
            continue
        record["tokens"] = tokenize_description_list(n_desc, stopwords=stopwords)
        neighbor_records.append(record)

    if method == "max_jaccard":
        for rec in neighbor_records:
            if "similarity" in rec and rec.get("tokens") in (None, []):
                continue
            neighbor_tokens = rec.get("tokens")
            if neighbor_tokens is None:
                continue
            rec["similarity"] = jaccard_similarity(
                base_token_set, set(neighbor_tokens)
            )
            rec["neighbor_tokens_count"] = len(set(neighbor_tokens))
        scored = [
            r for r in neighbor_records
            if isinstance(r.get("similarity"), (int, float))
        ]
        if not scored:
            LOGGER.warning(
                "no scorable neighbors for %s; R8(max_jaccard) defaults to 0.0",
                skill_md_path,
            )
            value = 0.0
        else:
            value = max(float(r["similarity"]) for r in scored)
    else:
        # tfidf_cosine_mean: build corpus including base; compute cosine
        # against every scorable neighbor; return mean.
        corpus_tokens_list: List[List[str]] = [base_token_list]
        for rec in neighbor_records:
            tokens = rec.get("tokens")
            if isinstance(tokens, list):
                corpus_tokens_list.append(tokens)
        base_vec = tf_idf_vector(base_token_list, corpus_tokens_list)
        cosines: List[float] = []
        for rec in neighbor_records:
            neighbor_tokens = rec.get("tokens")
            if neighbor_tokens is None:
                continue
            neighbor_vec = tf_idf_vector(neighbor_tokens, corpus_tokens_list)
            sim = cosine_similarity(base_vec, neighbor_vec)
            rec["similarity"] = float(sim)
            rec["neighbor_tokens_count"] = len(set(neighbor_tokens))
            cosines.append(float(sim))
        if not cosines:
            LOGGER.warning(
                "no scorable neighbors for %s; R8(tfidf_cosine_mean) defaults to 0.0",
                skill_md_path,
            )
            value = 0.0
        else:
            value = sum(cosines) / len(cosines)

    # Sort DESC by similarity (missing/errored → last).
    pairs_sorted = sorted(
        neighbor_records,
        key=lambda p: (
            0 if isinstance(p.get("similarity"), (int, float)) else 1,
            -(p["similarity"] if isinstance(p.get("similarity"), (int, float)) else 0),
        ),
    )

    # Clamp computed value to [0.0, 1.0] — TF-IDF cosine with non-negative
    # weights is guaranteed in range, but arithmetic round-off could
    # leave a trailing ~+1e-16 that would fail a strict range assertion.
    if value < 0.0:
        value = 0.0
    if value > 1.0:
        value = 1.0
    return float(value), pairs_sorted


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
