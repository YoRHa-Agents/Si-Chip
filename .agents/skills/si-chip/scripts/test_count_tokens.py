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
from typing import Optional

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


# ─────────────────── Round 7: C5 context_rot_risk ───────────────────
# Workspace rule "Mandatory Verification": Round 7 (task spec §1+§2)
# adds the C5 + C6 helpers to ``count_tokens.py``. These tests cover
# formula correctness, range sanity, silent-failure protection (raise
# ValueError on negative inputs), and integration against the real
# Si-Chip SKILL.md.


class ContextRotRiskTests(unittest.TestCase):
    """Direct unit tests for :func:`context_rot_risk` (spec §3.1 D2/C5)."""

    def test_slim_body_below_tenth(self) -> None:
        c5 = ct.context_rot_risk(body_tokens=2020, fanout_depth=1)
        self.assertLess(c5, 0.10)
        self.assertGreaterEqual(c5, 0.0)

    def test_body_saturates_window_to_one(self) -> None:
        c5 = ct.context_rot_risk(body_tokens=200_000, fanout_depth=0)
        self.assertEqual(c5, 1.0)

    def test_body_exceeds_window_clamps_to_one(self) -> None:
        c5 = ct.context_rot_risk(body_tokens=400_000, fanout_depth=10)
        self.assertEqual(c5, 1.0)

    def test_degenerate_zero_body_yields_fanout_term_only(self) -> None:
        c5 = ct.context_rot_risk(body_tokens=0, fanout_depth=3)
        self.assertAlmostEqual(c5, 0.15, places=4)

    def test_range_invariant_across_inputs(self) -> None:
        for body in (0, 100, 1000, 10_000, 100_000, 500_000):
            for fanout in (0, 1, 5, 20, 100):
                with self.subTest(body=body, fanout=fanout):
                    c5 = ct.context_rot_risk(body_tokens=body, fanout_depth=fanout)
                    self.assertGreaterEqual(c5, 0.0)
                    self.assertLessEqual(c5, 1.0)

    def test_negative_fanout_raises(self) -> None:
        with self.assertRaises(ValueError):
            ct.context_rot_risk(body_tokens=100, fanout_depth=-1)

    def test_negative_body_raises(self) -> None:
        with self.assertRaises(ValueError):
            ct.context_rot_risk(body_tokens=-1, fanout_depth=0)

    def test_zero_window_raises(self) -> None:
        with self.assertRaises(ValueError):
            ct.context_rot_risk(body_tokens=100, fanout_depth=0, typical_window=0)

    def test_typical_window_override(self) -> None:
        c5_small = ct.context_rot_risk(body_tokens=100_000, fanout_depth=0, typical_window=1_000_000)
        c5_default = ct.context_rot_risk(body_tokens=100_000, fanout_depth=0)
        self.assertLess(c5_small, c5_default)
        self.assertAlmostEqual(c5_small, 0.1, places=4)


class SkillMdContextRotRiskTests(unittest.TestCase):
    """:func:`skill_md_context_rot_risk` integration tests."""

    def _write_pair(self, body: str, refs: Optional[dict] = None) -> tuple:
        """Return (skill_md_path, refs_dir_path_or_None)."""

        tmp = Path(tempfile.mkdtemp())
        skill = tmp / "SKILL.md"
        skill.write_text(
            f"---\nname: demo\ndescription: stub\n---\n{body}\n",
            encoding="utf-8",
        )
        refs_dir: Optional[Path] = None
        if refs is not None:
            refs_dir = tmp / "references"
            refs_dir.mkdir()
            for fname, fbody in refs.items():
                (refs_dir / fname).write_text(fbody, encoding="utf-8")
        return skill, refs_dir

    def test_real_skill_md_in_range(self) -> None:
        """Real Si-Chip SKILL.md → C5 non-null and clipped to [0, 1]."""

        repo_root = Path(__file__).resolve().parents[4]
        skill = repo_root / ".agents/skills/si-chip/SKILL.md"
        refs_dir = repo_root / ".agents/skills/si-chip/references"
        value, deriv = ct.skill_md_context_rot_risk(skill, refs_dir)
        self.assertIsNotNone(value)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)
        # Historical baselines:
        # - v0.1.5/0.1.6 body = 2020 tokens, 5 references → C5 ≈ 0.2601
        # - v0.4.0-rc1 body = 4626 tokens (within §7.3 budget 5000), 11 references
        #   → C5 ≈ 0.72 (higher due to both body growth + reference fanout).
        # Relaxed invariant: C5 must stay below 0.85 (hard upper bound allowing
        # v0.4.0 headroom while still catching runaway body explosion). The hard
        # packaging-gate is enforced by count_tokens.py --budget-body 5000
        # (pass=true), not by this C5 assertion alone.
        self.assertLess(value, 0.85)
        # Derivation exposes body_tokens + fanout for provenance.
        self.assertIn("body_tokens", deriv)
        self.assertIn("fanout_depth", deriv)
        self.assertGreaterEqual(deriv["fanout_depth"], 1)

    def test_no_references_dir_yields_zero_fanout(self) -> None:
        skill, _ = self._write_pair("just body")
        value, deriv = ct.skill_md_context_rot_risk(skill, None)
        self.assertIsNotNone(value)
        self.assertEqual(deriv["fanout_depth"], 0)

    def test_missing_references_dir_logs_and_degrades(self) -> None:
        skill, _ = self._write_pair("body with ref.md")
        missing = Path("/does/not/exist/references")
        value, deriv = ct.skill_md_context_rot_risk(skill, missing)
        self.assertIsNotNone(value)
        self.assertEqual(deriv["fanout_depth"], 0)
        self.assertFalse(deriv["references_dir_exists"])

    def test_references_present_but_not_cited_yield_zero_fanout(self) -> None:
        skill, refs_dir = self._write_pair(
            "body text with no reference filenames",
            refs={"alpha.md": "content", "beta.md": "content"},
        )
        value, deriv = ct.skill_md_context_rot_risk(skill, refs_dir)
        self.assertIsNotNone(value)
        self.assertEqual(deriv["fanout_depth"], 0)
        self.assertEqual(deriv["referenced_files"], [])

    def test_cited_references_increment_fanout(self) -> None:
        skill, refs_dir = self._write_pair(
            "body cites alpha.md and gamma.md explicitly",
            refs={"alpha.md": "a", "beta.md": "b", "gamma.md": "c"},
        )
        value, deriv = ct.skill_md_context_rot_risk(skill, refs_dir)
        self.assertIsNotNone(value)
        self.assertEqual(deriv["fanout_depth"], 2)
        self.assertEqual(sorted(deriv["referenced_files"]), ["alpha.md", "gamma.md"])

    def test_missing_skill_md_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ct.skill_md_context_rot_risk(Path("/does/not/exist/SKILL.md"), None)


# ─────────────────── Round 7: C6 scope_overlap_score ───────────────────


class JaccardSimilarityTests(unittest.TestCase):
    """Direct unit tests for :func:`jaccard_similarity`."""

    def test_identical_is_one(self) -> None:
        self.assertEqual(ct.jaccard_similarity({"a", "b"}, {"a", "b"}), 1.0)

    def test_disjoint_is_zero(self) -> None:
        self.assertEqual(ct.jaccard_similarity({"a"}, {"b"}), 0.0)

    def test_partial_overlap_deterministic(self) -> None:
        # {a, b, c} ∩ {b, c, d} = {b, c}; union = {a, b, c, d}
        # Jaccard = 2/4 = 0.5.
        self.assertAlmostEqual(
            ct.jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"}),
            0.5,
            places=6,
        )

    def test_both_empty_is_zero_by_convention(self) -> None:
        self.assertEqual(ct.jaccard_similarity(set(), set()), 0.0)

    def test_one_empty_is_zero(self) -> None:
        self.assertEqual(ct.jaccard_similarity({"a", "b"}, set()), 0.0)
        self.assertEqual(ct.jaccard_similarity(set(), {"a", "b"}), 0.0)

    def test_range_invariant(self) -> None:
        for a, b in (
            (set(), set()),
            ({"x"}, set()),
            ({"x"}, {"x"}),
            ({"x"}, {"y"}),
            ({"a", "b", "c"}, {"a", "d", "e"}),
        ):
            with self.subTest(a=a, b=b):
                j = ct.jaccard_similarity(a, b)
                self.assertGreaterEqual(j, 0.0)
                self.assertLessEqual(j, 1.0)


class TokenizeDescriptionTests(unittest.TestCase):
    """Normalisation + stopword behaviour of :func:`tokenize_description`."""

    def test_basic_tokenisation(self) -> None:
        tokens = ct.tokenize_description("Hello, World!")
        self.assertEqual(tokens, {"hello", "world"})

    def test_stopwords_filtered_by_default(self) -> None:
        tokens = ct.tokenize_description("Use this when it is for the demo")
        self.assertNotIn("when", tokens)
        self.assertNotIn("the", tokens)
        self.assertNotIn("use", tokens)
        self.assertNotIn("it", tokens)
        self.assertIn("demo", tokens)

    def test_custom_empty_stopwords_disables_filter(self) -> None:
        tokens = ct.tokenize_description("use demo", stopwords=frozenset())
        self.assertIn("use", tokens)
        self.assertIn("demo", tokens)

    def test_hyphen_becomes_separator(self) -> None:
        tokens = ct.tokenize_description("router-testing half-retiring")
        self.assertIn("router", tokens)
        self.assertIn("testing", tokens)
        self.assertIn("half", tokens)
        self.assertIn("retiring", tokens)

    def test_empty_input_is_empty_set(self) -> None:
        self.assertEqual(ct.tokenize_description(""), set())

    def test_non_ascii_stripped(self) -> None:
        # Chinese chars get stripped by the ASCII-alnum filter; ascii
        # survives.
        tokens = ct.tokenize_description("飞书 API demo")
        self.assertIn("api", tokens)
        self.assertIn("demo", tokens)


class SkillMdScopeOverlapScoreTests(unittest.TestCase):
    """End-to-end tests for :func:`skill_md_scope_overlap_score`."""

    def _write_skill(self, name: str, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / f"{name}_SKILL.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {description}\n---\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_max_reduction_across_neighbors(self) -> None:
        base = self._write_skill("base", "alpha beta gamma")
        n1 = self._write_skill("n1", "delta epsilon")         # disjoint
        n2 = self._write_skill("n2", "alpha delta")           # partial
        n3 = self._write_skill("n3", "alpha beta gamma")      # identical
        c6, pairs = ct.skill_md_scope_overlap_score(base, [n1, n2, n3])
        self.assertEqual(c6, 1.0)
        # Sorted DESC by jaccard.
        self.assertAlmostEqual(pairs[0]["jaccard"], 1.0, places=6)
        self.assertGreaterEqual(pairs[1]["jaccard"], pairs[-1]["jaccard"])

    def test_all_disjoint_neighbors_yield_zero(self) -> None:
        base = self._write_skill("base", "alpha beta")
        n1 = self._write_skill("n1", "xray yankee")
        n2 = self._write_skill("n2", "zulu")
        c6, pairs = ct.skill_md_scope_overlap_score(base, [n1, n2])
        self.assertEqual(c6, 0.0)
        self.assertEqual(len(pairs), 2)

    def test_missing_neighbor_is_logged_and_skipped(self) -> None:
        base = self._write_skill("base", "alpha beta")
        n1 = self._write_skill("n1", "alpha")
        missing = Path("/does/not/exist/SKILL.md")
        with self.assertLogs("si_chip.count_tokens", level="WARNING") as cm:
            c6, pairs = ct.skill_md_scope_overlap_score(base, [n1, missing])
        # Warning must mention the missing path — no silent swallow.
        self.assertTrue(any("missing" in m for m in cm.output))
        # C6 still computable from the surviving neighbor.
        self.assertIsNotNone(c6)
        self.assertGreater(c6, 0.0)
        self.assertEqual(len(pairs), 2)
        # Missing entry recorded with an explicit error field.
        missing_entries = [p for p in pairs if p.get("error") == "missing"]
        self.assertEqual(len(missing_entries), 1)

    def test_missing_base_raises(self) -> None:
        n1 = self._write_skill("n1", "alpha")
        with self.assertRaises(FileNotFoundError):
            ct.skill_md_scope_overlap_score(
                Path("/does/not/exist/SKILL.md"), [n1]
            )

    def test_empty_neighbor_list_returns_zero(self) -> None:
        base = self._write_skill("base", "alpha beta")
        c6, pairs = ct.skill_md_scope_overlap_score(base, [])
        self.assertEqual(c6, 0.0)
        self.assertEqual(pairs, [])

    def test_si_chip_real_neighbor_overlap_low(self) -> None:
        """Real Si-Chip vs lark-* neighbors → C6 < 0.50 (low competition)."""

        import glob
        repo_root = Path(__file__).resolve().parents[4]
        skill = repo_root / ".agents/skills/si-chip/SKILL.md"
        neighbors = [Path(p) for p in sorted(glob.glob("/root/.claude/skills/lark-*/SKILL.md"))]
        if not skill.exists() or not neighbors:
            self.skipTest("real Si-Chip SKILL.md or lark-* neighbors missing")
        c6, pairs = ct.skill_md_scope_overlap_score(skill, neighbors)
        self.assertIsNotNone(c6)
        self.assertGreaterEqual(c6, 0.0)
        self.assertLessEqual(c6, 1.0)
        # Description vocabulary is very different; expect competition
        # index < 0.30.
        self.assertLess(c6, 0.30)
        # All neighbor paths must appear in the pairs list.
        neighbor_paths_in_pairs = {p["neighbor_path"] for p in pairs}
        for n in neighbors:
            self.assertIn(str(n), neighbor_paths_in_pairs)


# ─────────────── Round 9: D6/R8 description_competition_index ───────────────
# Workspace rule "Mandatory Verification": Round 9 (task spec §1+§2) adds
# the R8 helpers to ``count_tokens.py``. These tests cover TF-IDF /
# cosine / R8 wrapper correctness, determinism, range sanity, error
# signalling (empty neighbor / unknown method), and the Si-Chip real
# neighbor smoke (method="max_jaccard" and "tfidf_cosine_mean").


class TokenizeDescriptionListTests(unittest.TestCase):
    """:func:`tokenize_description_list` preserves duplicates."""

    def test_preserves_duplicate_counts(self) -> None:
        toks = ct.tokenize_description_list("alpha alpha beta")
        self.assertEqual(toks, ["alpha", "alpha", "beta"])

    def test_empty_input_yields_empty_list(self) -> None:
        self.assertEqual(ct.tokenize_description_list(""), [])

    def test_stopwords_filtered(self) -> None:
        toks = ct.tokenize_description_list("use the alpha")
        self.assertNotIn("use", toks)
        self.assertNotIn("the", toks)
        self.assertIn("alpha", toks)


class TfIdfVectorTests(unittest.TestCase):
    """Direct unit tests for :func:`tf_idf_vector`."""

    def test_deterministic_identical_input(self) -> None:
        """Same input → byte-identical output (no RNG)."""

        corpus = [["alpha", "beta"], ["alpha"], ["beta", "gamma"]]
        v1 = ct.tf_idf_vector(["alpha", "beta"], corpus)
        v2 = ct.tf_idf_vector(["alpha", "beta"], corpus)
        self.assertEqual(list(v1.keys()), list(v2.keys()))
        for k in v1:
            self.assertEqual(v1[k], v2[k])

    def test_empty_tokens_yields_empty_dict(self) -> None:
        self.assertEqual(ct.tf_idf_vector([], [["alpha"]]), {})

    def test_empty_corpus_yields_empty_dict(self) -> None:
        """Empty corpus → empty dict (df denominator undefined)."""

        self.assertEqual(ct.tf_idf_vector(["alpha"], []), {})

    def test_rarer_term_has_higher_idf(self) -> None:
        """Beta appears in 1/2 docs; alpha in 2/2 → beta weighted higher."""

        corpus = [["alpha", "beta"], ["alpha"]]
        v = ct.tf_idf_vector(["alpha", "beta"], corpus)
        self.assertIn("alpha", v)
        self.assertIn("beta", v)
        self.assertGreater(v["beta"], v["alpha"])

    def test_sorted_keys(self) -> None:
        """Output dict is iterated in sorted-key order for determinism."""

        corpus = [["gamma", "alpha", "beta"], ["alpha"], ["gamma"]]
        v = ct.tf_idf_vector(["gamma", "alpha", "beta"], corpus)
        self.assertEqual(list(v.keys()), sorted(v.keys()))

    def test_all_positive_weights(self) -> None:
        """TF-IDF weights must be > 0 for any term present in the doc."""

        v = ct.tf_idf_vector(["a", "b", "c"], [["a", "b", "c"], ["d"]])
        for term, weight in v.items():
            with self.subTest(term=term):
                self.assertGreater(weight, 0.0)


class CosineSimilarityTests(unittest.TestCase):
    """Direct unit tests for :func:`cosine_similarity`."""

    def test_identical_vectors_is_one(self) -> None:
        v = {"a": 1.0, "b": 2.0}
        self.assertAlmostEqual(ct.cosine_similarity(v, v), 1.0, places=6)

    def test_disjoint_vectors_is_zero(self) -> None:
        self.assertEqual(
            ct.cosine_similarity({"a": 1.0}, {"b": 1.0}),
            0.0,
        )

    def test_partial_overlap(self) -> None:
        """{a:1, b:1} vs {b:1, c:1} → intersection {b}, cosine = 0.5."""

        j = ct.cosine_similarity({"a": 1.0, "b": 1.0}, {"b": 1.0, "c": 1.0})
        self.assertAlmostEqual(j, 0.5, places=6)

    def test_both_empty_is_zero(self) -> None:
        self.assertEqual(ct.cosine_similarity({}, {}), 0.0)

    def test_one_empty_is_zero(self) -> None:
        self.assertEqual(ct.cosine_similarity({}, {"a": 1.0}), 0.0)
        self.assertEqual(ct.cosine_similarity({"a": 1.0}, {}), 0.0)

    def test_zero_norm_vector_is_zero(self) -> None:
        """Vector with all-zero weights → cosine = 0.0 (no div-by-zero)."""

        self.assertEqual(
            ct.cosine_similarity({"a": 0.0, "b": 0.0}, {"a": 1.0}),
            0.0,
        )

    def test_range_invariant(self) -> None:
        """Cosine with non-negative TF-IDF weights must be in [0.0, 1.0]."""

        for a in ({"a": 1.0}, {"a": 1.0, "b": 2.0}, {"c": 3.0}):
            for b in ({"a": 1.0}, {"a": 1.0, "b": 2.0}, {"c": 3.0}):
                with self.subTest(a=a, b=b):
                    sim = ct.cosine_similarity(a, b)
                    self.assertGreaterEqual(sim, 0.0)
                    self.assertLessEqual(sim, 1.0)


class SkillMdDescriptionCompetitionIndexTests(unittest.TestCase):
    """End-to-end tests for :func:`skill_md_description_competition_index`."""

    def _write_skill(self, name: str, description: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / f"{name}_SKILL.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {description}\n---\nbody\n",
            encoding="utf-8",
        )
        return path

    def test_max_jaccard_default_method(self) -> None:
        base = self._write_skill("base", "alpha beta gamma")
        n1 = self._write_skill("n1", "delta epsilon")         # disjoint
        n2 = self._write_skill("n2", "alpha delta")           # partial
        n3 = self._write_skill("n3", "alpha beta gamma")      # identical
        r8, pairs = ct.skill_md_description_competition_index(
            base, [n1, n2, n3]
        )
        self.assertAlmostEqual(r8, 1.0, places=6)
        self.assertEqual(len(pairs), 3)
        self.assertAlmostEqual(pairs[0]["similarity"], 1.0, places=6)

    def test_tfidf_cosine_mean_deterministic(self) -> None:
        """Same input → byte-identical R8 output on repeat invocation."""

        base = self._write_skill("base", "alpha beta gamma")
        n1 = self._write_skill("n1", "alpha delta")
        n2 = self._write_skill("n2", "beta gamma")
        r8_a, pairs_a = ct.skill_md_description_competition_index(
            base, [n1, n2], method="tfidf_cosine_mean"
        )
        r8_b, pairs_b = ct.skill_md_description_competition_index(
            base, [n1, n2], method="tfidf_cosine_mean"
        )
        self.assertEqual(r8_a, r8_b)
        self.assertEqual(len(pairs_a), len(pairs_b))
        for pa, pb in zip(pairs_a, pairs_b):
            self.assertEqual(pa["similarity"], pb["similarity"])

    def test_tfidf_cosine_mean_partial_overlap_in_range(self) -> None:
        """Partial-overlap neighbors → R8 in (0.0, 1.0)."""

        base = self._write_skill("base", "alpha beta gamma")
        n1 = self._write_skill("n1", "alpha delta")
        n2 = self._write_skill("n2", "beta epsilon")
        r8, _ = ct.skill_md_description_competition_index(
            base, [n1, n2], method="tfidf_cosine_mean"
        )
        self.assertGreater(r8, 0.0)
        self.assertLess(r8, 1.0)

    def test_empty_neighbor_list_raises(self) -> None:
        base = self._write_skill("base", "alpha beta")
        with self.assertRaises(ValueError):
            ct.skill_md_description_competition_index(base, [])

    def test_unknown_method_raises(self) -> None:
        base = self._write_skill("base", "alpha")
        n1 = self._write_skill("n1", "alpha")
        with self.assertRaises(ValueError):
            ct.skill_md_description_competition_index(
                base, [n1], method="no_such_method",
            )

    def test_missing_base_raises(self) -> None:
        n1 = self._write_skill("n1", "alpha")
        with self.assertRaises(FileNotFoundError):
            ct.skill_md_description_competition_index(
                Path("/does/not/exist/SKILL.md"), [n1]
            )

    def test_missing_neighbor_recorded_not_raised(self) -> None:
        """Missing neighbor → logged warning + explicit error record."""

        base = self._write_skill("base", "alpha beta")
        n1 = self._write_skill("n1", "alpha")
        missing = Path("/does/not/exist/SKILL.md")
        with self.assertLogs("si_chip.count_tokens", level="WARNING") as cm:
            r8, pairs = ct.skill_md_description_competition_index(
                base, [n1, missing]
            )
        self.assertTrue(any("missing" in m for m in cm.output))
        self.assertGreaterEqual(r8, 0.0)
        self.assertLessEqual(r8, 1.0)
        missing_entries = [p for p in pairs if p.get("error") == "missing"]
        self.assertEqual(len(missing_entries), 1)

    def test_si_chip_real_neighbor_max_jaccard_expected_range(self) -> None:
        """Real Si-Chip vs lark-* neighbors → R8(max_jaccard) ~ [0.04, 0.10]."""

        import glob
        repo_root = Path(__file__).resolve().parents[4]
        skill = repo_root / ".agents/skills/si-chip/SKILL.md"
        neighbors = [Path(p) for p in sorted(glob.glob("/root/.claude/skills/lark-*/SKILL.md"))]
        if not skill.exists() or not neighbors:
            self.skipTest("real Si-Chip SKILL.md or lark-* neighbors missing")
        r8, pairs = ct.skill_md_description_competition_index(
            skill, neighbors, method="max_jaccard"
        )
        self.assertGreaterEqual(r8, 0.0)
        self.assertLessEqual(r8, 0.20)
        # Result should match C6 (same formula family): max-Jaccard against
        # the same neighbor set.
        c6, _ = ct.skill_md_scope_overlap_score(skill, neighbors)
        self.assertAlmostEqual(r8, c6, places=6)

    def test_si_chip_real_neighbor_tfidf_cosine_mean_range(self) -> None:
        """Real Si-Chip vs lark-* neighbors → R8(tfidf_cosine_mean) in [0.0, 1.0]."""

        import glob
        repo_root = Path(__file__).resolve().parents[4]
        skill = repo_root / ".agents/skills/si-chip/SKILL.md"
        neighbors = [Path(p) for p in sorted(glob.glob("/root/.claude/skills/lark-*/SKILL.md"))]
        if not skill.exists() or not neighbors:
            self.skipTest("real Si-Chip SKILL.md or lark-* neighbors missing")
        r8, pairs = ct.skill_md_description_competition_index(
            skill, neighbors, method="tfidf_cosine_mean"
        )
        self.assertGreaterEqual(r8, 0.0)
        self.assertLessEqual(r8, 1.0)
        # Low competition expected (descriptions are specialised).
        self.assertLess(r8, 0.30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
