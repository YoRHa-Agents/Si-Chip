#!/usr/bin/env python3
"""Unit tests for ``count_tokens.py``.

Covers the Round 5 Flesch-Kincaid grade level helper (spec §3.1 D5/U1)
plus smoke tests for the pre-existing token counters and frontmatter
splitter. Workspace rule "Mandatory Verification": every new helper
landed in Round 5 carries at least one direct unit test.

Run::

    python3 .agents/skills/si-chip/scripts/test_count_tokens.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import count_tokens as ct  # noqa: E402


# ───────────────────────── pre-existing helpers ─────────────────────────


class SplitFrontmatterTests(unittest.TestCase):
    """Sanity checks for the pre-existing ``split_frontmatter`` helper."""

    def test_typical_skill_md(self) -> None:
        text = "---\nname: x\ndescription: hi\n---\nbody here\n"
        meta, body = ct.split_frontmatter(text)
        self.assertEqual(meta, "name: x\ndescription: hi")
        self.assertIn("body here", body)

    def test_no_frontmatter(self) -> None:
        meta, body = ct.split_frontmatter("no leading delimiter")
        self.assertEqual(meta, "")
        self.assertEqual(body, "no leading delimiter")

    def test_empty_input(self) -> None:
        meta, body = ct.split_frontmatter("")
        self.assertEqual(meta, "")
        self.assertEqual(body, "")


class CountTokensTests(unittest.TestCase):
    """Smoke tests for :func:`count_tokens` and :func:`_fallback_count`."""

    def test_fallback_on_short_prose(self) -> None:
        n = ct._fallback_count("hello, world! ok")
        self.assertEqual(n, 3)

    def test_count_tokens_reports_backend(self) -> None:
        n, backend = ct.count_tokens("hello world")
        self.assertGreater(n, 0)
        self.assertIn(backend, {"tiktoken", "fallback"})


# ─────────────────── Round 5: Flesch-Kincaid grade level ───────────────────


class FkSyllableCountTests(unittest.TestCase):
    """Vowel-group syllable heuristic with silent-e adjustment."""

    def test_empty_word_is_zero(self) -> None:
        self.assertEqual(ct._fk_count_syllables(""), 0)
        self.assertEqual(ct._fk_count_syllables("123"), 0)

    def test_single_char_is_one(self) -> None:
        self.assertEqual(ct._fk_count_syllables("a"), 1)
        self.assertEqual(ct._fk_count_syllables("I"), 1)

    def test_silent_e_is_stripped(self) -> None:
        # "create" has two vowel groups (ea, e) but the final silent e
        # is subtracted, leaving 2-1 = 1... actually vowel groups ignore
        # the split: "create" -> groups (ea, e) = 2, silent-e = 1.
        self.assertEqual(ct._fk_count_syllables("create"), 1)

    def test_silent_e_not_stripped_for_le_words(self) -> None:
        # "table" ends in "le"; the silent-e rule is skipped.
        self.assertEqual(ct._fk_count_syllables("table"), 2)

    def test_minimum_one_when_alpha_present(self) -> None:
        # "rhythm" has no standard vowels (y counted) -> 1.
        self.assertGreaterEqual(ct._fk_count_syllables("rhythm"), 1)

    def test_uppercase_input_lowercased(self) -> None:
        self.assertEqual(
            ct._fk_count_syllables("PERSISTENT"),
            ct._fk_count_syllables("persistent"),
        )

    def test_multi_syllable_words(self) -> None:
        # Sanity: each obviously-multi-syllabic word is >= 2.
        for word in ("evaluating", "diagnosing", "improving", "factory", "ability"):
            with self.subTest(word=word):
                self.assertGreaterEqual(ct._fk_count_syllables(word), 2)


class FkWordAndSentenceTests(unittest.TestCase):
    """Word and sentence segmentation heuristics."""

    def test_word_count_basic(self) -> None:
        self.assertEqual(ct._fk_count_words("Use when profiling, evaluating."), 4)

    def test_word_count_strips_digits_only(self) -> None:
        # Pure-numeric tokens are not words.
        self.assertEqual(ct._fk_count_words("12345"), 0)

    def test_word_count_version_strings_count_leading_alpha(self) -> None:
        # ``v0.1.0`` contributes one word (the leading ``v``).
        self.assertEqual(ct._fk_count_words("v0.1.0"), 1)

    def test_word_count_allows_hyphenated(self) -> None:
        # "router-testing" is one word.
        self.assertEqual(
            ct._fk_count_words("profiling router-testing half-retiring"),
            3,
        )

    def test_sentence_count_empty(self) -> None:
        self.assertEqual(ct._fk_count_sentences(""), 0)
        self.assertEqual(ct._fk_count_sentences("   "), 0)

    def test_sentence_count_non_terminated_text(self) -> None:
        # A non-empty fragment counts as at least one sentence so FK
        # does not divide by zero.
        self.assertEqual(ct._fk_count_sentences("no terminator here"), 1)

    def test_sentence_count_strips_digit_periods(self) -> None:
        # "v0.1.0" is NOT three sentence boundaries.
        self.assertEqual(ct._fk_count_sentences("Version v0.1.0 released."), 1)

    def test_sentence_count_multiple_terminators(self) -> None:
        self.assertEqual(ct._fk_count_sentences("A. B. C!"), 3)


class FkGradeTests(unittest.TestCase):
    """End-to-end :func:`flesch_kincaid_grade` behaviour."""

    def test_empty_text_is_zero(self) -> None:
        g, d = ct.flesch_kincaid_grade("")
        self.assertEqual(g, 0.0)
        self.assertEqual(d["words"], 0)
        self.assertEqual(d["sentences"], 0)
        self.assertEqual(d["syllables"], 0)

    def test_simple_sentence_in_range(self) -> None:
        # "The cat sat on the mat." is nominally grade ~ -2 (clamped to 0).
        g, d = ct.flesch_kincaid_grade("The cat sat on the mat.")
        self.assertEqual(d["words"], 6)
        self.assertEqual(d["sentences"], 1)
        self.assertGreater(d["syllables"], 0)
        self.assertGreaterEqual(g, 0.0)
        self.assertLessEqual(g, 24.0)

    def test_grade_clamped_to_range(self) -> None:
        # Highly complex nested phrase stress-tests the upper clamp.
        long_text = (
            "Electroencephalographically unprecedented polysyllabic sesquipedalian "
            "expressions proliferate ostentatiously throughout interdisciplinary "
            "cross-functional metaheuristic polymorphic implementation frameworks."
        )
        g, _ = ct.flesch_kincaid_grade(long_text)
        self.assertGreaterEqual(g, 0.0)
        self.assertLessEqual(g, 24.0)

    def test_details_include_formula_and_raw_grade(self) -> None:
        g, d = ct.flesch_kincaid_grade("Use when profiling.")
        self.assertIn("formula", d)
        self.assertIn("raw_grade", d)
        self.assertIn("grade", d)
        self.assertAlmostEqual(d["grade"], max(0.0, min(24.0, d["raw_grade"])))
        self.assertEqual(d["grade"], g)

    def test_determinism_across_calls(self) -> None:
        text = "Persistent BasicAbility optimization factory."
        g1, _ = ct.flesch_kincaid_grade(text)
        g2, _ = ct.flesch_kincaid_grade(text)
        self.assertEqual(g1, g2)

    def test_si_chip_description_is_finite(self) -> None:
        desc = (
            "Persistent BasicAbility optimization factory. Use when profiling, "
            "evaluating, diagnosing, improving, router-testing, or half-retiring "
            "a skill/ability per Si-Chip spec v0.1.0."
        )
        g, d = ct.flesch_kincaid_grade(desc)
        self.assertGreater(d["words"], 10)
        self.assertGreaterEqual(d["sentences"], 2)
        self.assertGreaterEqual(g, 0.0)
        self.assertLessEqual(g, 24.0)


class ExtractDescriptionTests(unittest.TestCase):

    def test_extract_simple_description(self) -> None:
        fm = "name: x\ndescription: hello world"
        self.assertEqual(
            ct.extract_description_from_frontmatter(fm), "hello world"
        )

    def test_missing_description_returns_none(self) -> None:
        self.assertIsNone(
            ct.extract_description_from_frontmatter("name: x")
        )

    def test_empty_frontmatter_returns_none(self) -> None:
        self.assertIsNone(
            ct.extract_description_from_frontmatter("")
        )


class SkillMdDescriptionFkTests(unittest.TestCase):

    def _write_skill(self, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text(
            f"---\nname: si-chip\ndescription: {description}\n---\n\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_happy_path(self) -> None:
        path = self._write_skill(
            "Persistent BasicAbility optimization factory."
        )
        grade, details = ct.skill_md_description_fk_grade(path)
        self.assertIsNotNone(grade)
        self.assertIn("description_text", details)
        self.assertIn("words", details)
        self.assertGreaterEqual(grade, 0.0)
        self.assertLessEqual(grade, 24.0)

    def test_missing_description_returns_none(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "SKILL.md"
        path.write_text("---\nname: si-chip\n---\n\nbody\n", encoding="utf-8")
        grade, details = ct.skill_md_description_fk_grade(path)
        self.assertIsNone(grade)
        self.assertIn("error", details)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ct.skill_md_description_fk_grade(Path("/does/not/exist/SKILL.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
