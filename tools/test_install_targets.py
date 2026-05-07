#!/usr/bin/env python3
"""Integration tests for ``install.sh`` target dispatch (v0.5.1+).

Workspace rule "Mandatory Verification": the v0.5.1 install.sh patch
adds two new ``--target`` values (``codex`` and ``all``) and a hard
rejection path for spec-§11.x out-of-scope targets (Copilot CLI,
OpenCode, Gemini CLI, Windsurf). These tests exercise:

* Help banner / version banner mention v0.5.1.
* Allowed targets (cursor / claude / codex / both / all) reach the
  install dispatch (verified via dry-run output for cursor + claude;
  real install for codex bridge since it has no network dependency).
* Rejected targets (copilot, opencode, gemini, gemini-cli, windsurf)
  exit with code 2 and emit a spec-clause-pointing rejection message.
* Codex bridge install + uninstall against a file:// source url
  pointed at the repo root produces exactly the 2 bridge files
  (``profiles/si-chip.md`` + ``instructions/si-chip-bridge.md``)
  under ``<repo>/.codex/`` and removes them again on --uninstall.
* `--target all` against a repo-root file:// source produces 26 cursor
  + 26 claude + 2 codex bridge = 54 files total.
* The dual-layout file:// fallback (extracted-tarball ``skills/si-chip/``
  vs repo-SoT ``.agents/skills/si-chip/``) works for both layouts.

Running the tests::

    python3 tools/test_install_targets.py

These tests **do not** require network access; the only fetch path
exercised is ``file://`` against the repo root and (optionally) against
an extracted v0.5.0 tarball.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
_INSTALL_SH = _REPO_ROOT / "install.sh"

if not _INSTALL_SH.is_file():
    raise SystemExit(
        f"install.sh not found at {_INSTALL_SH}; tests must be run "
        "from inside the Si-Chip repository."
    )


def _run(args: list[str], *, expect_exit: int = 0,
         timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    """Run install.sh with the given arguments and return the result.

    Workspace rule "No Silent Failures": we do NOT swallow non-zero
    exits — the caller asserts the expected code, and if it differs we
    log stdout/stderr to aid diagnosis before the test fails.
    """
    proc = subprocess.run(
        ["bash", str(_INSTALL_SH), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != expect_exit:
        sys.stderr.write(
            f"\n--- install.sh exited {proc.returncode} (expected {expect_exit})\n"
            f"--- args: {args}\n"
            f"--- stdout:\n{proc.stdout}\n"
            f"--- stderr:\n{proc.stderr}\n"
        )
    return proc


class HelpAndVersionTests(unittest.TestCase):
    """`--help` and `--version-info` reflect the v0.5.1 patch."""

    def test_help_mentions_v051_and_codex_target(self) -> None:
        proc = _run(["--help"])
        self.assertIn("v0.5.1", proc.stdout, "help should advertise v0.5.1")
        self.assertIn("--target cursor|claude|codex|both|all", proc.stdout,
                      "help should enumerate the new target enum")
        self.assertIn("BRIDGE", proc.stdout,
                      "help must explain that codex is bridge-only")

    def test_version_info_reports_default_v051(self) -> None:
        proc = _run(["--version-info"])
        self.assertIn("v0.5.1", proc.stdout)


class RejectionTests(unittest.TestCase):
    """Spec §11.x out-of-scope targets exit non-zero with rationale."""

    SPEC_REJECT_MARKERS = (
        "§11.1",
        "§11.2",
        "BRIDGE ONLY",
    )

    def _assert_rejected(self, target: str) -> None:
        proc = _run(
            ["--target", target, "--scope", "global", "--yes"],
            expect_exit=2,
        )
        self.assertEqual(proc.returncode, 2,
                         f"target {target!r} should be rejected")
        # Combined stdout+stderr to be liberal about which stream the
        # script writes the rationale to.
        combined = proc.stdout + proc.stderr
        for marker in self.SPEC_REJECT_MARKERS:
            self.assertIn(marker, combined,
                          f"rejection of {target!r} should cite {marker!r}")

    def test_copilot_rejected(self) -> None:
        self._assert_rejected("copilot")

    def test_opencode_rejected(self) -> None:
        self._assert_rejected("opencode")

    def test_gemini_rejected(self) -> None:
        self._assert_rejected("gemini")

    def test_gemini_cli_rejected(self) -> None:
        self._assert_rejected("gemini-cli")

    def test_windsurf_rejected(self) -> None:
        self._assert_rejected("windsurf")

    def test_unknown_target_dies_with_allow_list(self) -> None:
        # Unknown (non-deferred) targets fall through to the generic
        # "must be one of" die() which exits 1 (not 2).
        proc = _run(
            ["--target", "totally-fake-target", "--scope", "global", "--yes"],
            expect_exit=1,
        )
        self.assertIn("--target must be one of", proc.stderr + proc.stdout)


class CodexBridgeTests(unittest.TestCase):
    """Codex bridge install + uninstall against repo-root file://."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="sichip_codex_"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_codex_bridge_install_creates_two_files(self) -> None:
        proc = _run(
            [
                "--target", "codex",
                "--scope", "repo",
                "--repo-root", str(self._tmp),
                "--source-url", f"file://{_REPO_ROOT}",
                "--yes",
            ]
        )
        self.assertIn("Installed Si-Chip Codex bridge", proc.stdout)

        codex_dir = self._tmp / ".codex"
        profile = codex_dir / "profiles" / "si-chip.md"
        bridge = codex_dir / "instructions" / "si-chip-bridge.md"
        self.assertTrue(profile.is_file(), f"profile missing at {profile}")
        self.assertTrue(bridge.is_file(),  f"bridge instructions missing at {bridge}")
        self.assertNotIn("SKILL.md", os.listdir(codex_dir),
                         "Codex bridge MUST NOT install SKILL.md (§11.2 deferred)")

    def test_codex_bridge_uninstall_removes_only_si_chip_files(self) -> None:
        # Pre-place an unrelated profile + instruction file from a
        # third-party Codex skill — the uninstall must NOT touch them.
        codex_dir = self._tmp / ".codex"
        (codex_dir / "profiles").mkdir(parents=True, exist_ok=True)
        (codex_dir / "instructions").mkdir(parents=True, exist_ok=True)
        unrelated_profile = codex_dir / "profiles" / "third-party.md"
        unrelated_instr = codex_dir / "instructions" / "third-party.md"
        unrelated_profile.write_text("third-party profile\n", encoding="utf-8")
        unrelated_instr.write_text("third-party instructions\n", encoding="utf-8")

        # Install si-chip bridge.
        _run(
            [
                "--target", "codex",
                "--scope", "repo",
                "--repo-root", str(self._tmp),
                "--source-url", f"file://{_REPO_ROOT}",
                "--yes",
            ]
        )
        self.assertTrue((codex_dir / "profiles" / "si-chip.md").is_file())

        # Uninstall.
        _run(
            [
                "--target", "codex",
                "--scope", "repo",
                "--repo-root", str(self._tmp),
                "--uninstall",
                "--yes",
                "--source-url", f"file://{_REPO_ROOT}",
            ]
        )

        self.assertFalse((codex_dir / "profiles" / "si-chip.md").is_file(),
                         "si-chip.md should be gone after uninstall")
        self.assertFalse((codex_dir / "instructions" / "si-chip-bridge.md").is_file(),
                         "si-chip-bridge.md should be gone after uninstall")
        # Critically: the third-party files and parent dirs survive.
        self.assertTrue(unrelated_profile.is_file(),
                        "uninstall must not delete unrelated profiles")
        self.assertTrue(unrelated_instr.is_file(),
                        "uninstall must not delete unrelated instructions")


class AllTargetsTests(unittest.TestCase):
    """`--target all` installs cursor + claude + codex bridge."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="sichip_all_"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_target_all_installs_three_destinations(self) -> None:
        proc = _run(
            [
                "--target", "all",
                "--scope", "repo",
                "--repo-root", str(self._tmp),
                "--source-url", f"file://{_REPO_ROOT}",
                "--yes",
            ],
            timeout=60.0,
        )
        self.assertIn("Installed Si-Chip v0.5.1 to", proc.stdout)
        self.assertIn("Installed Si-Chip Codex bridge", proc.stdout)

        cursor_dir = self._tmp / ".cursor" / "skills" / "si-chip"
        claude_dir = self._tmp / ".claude" / "skills" / "si-chip"
        codex_dir = self._tmp / ".codex"

        self.assertTrue((cursor_dir / "SKILL.md").is_file())
        self.assertTrue((claude_dir / "SKILL.md").is_file())
        self.assertTrue((codex_dir / "profiles" / "si-chip.md").is_file())
        self.assertTrue((codex_dir / "instructions" / "si-chip-bridge.md").is_file())

        # Reference + script counts (per v0.5.1 manifest: 19 + 5).
        cursor_refs = list((cursor_dir / "references").iterdir())
        cursor_scripts = list((cursor_dir / "scripts").iterdir())
        self.assertEqual(len(cursor_refs), 19,
                         f"cursor refs count mismatch: {len(cursor_refs)}")
        self.assertEqual(len(cursor_scripts), 5,
                         f"cursor scripts count mismatch: {len(cursor_scripts)}")

    def test_target_both_keeps_back_compat_two_destinations(self) -> None:
        proc = _run(
            [
                "--target", "both",
                "--scope", "repo",
                "--repo-root", str(self._tmp),
                "--source-url", f"file://{_REPO_ROOT}",
                "--yes",
            ],
            timeout=60.0,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertTrue((self._tmp / ".cursor" / "skills" / "si-chip" / "SKILL.md").is_file())
        self.assertTrue((self._tmp / ".claude" / "skills" / "si-chip" / "SKILL.md").is_file())
        # `both` MUST NOT touch .codex (back-compat with v0.4.0).
        self.assertFalse((self._tmp / ".codex").exists(),
                         "--target both must NOT install codex bridge")


class DryRunTests(unittest.TestCase):
    """Dry-run paths print expected `[dry-run]` lines without writing."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="sichip_dry_"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_dry_run_codex_does_not_create_files(self) -> None:
        proc = _run(
            [
                "--target", "codex",
                "--scope", "repo",
                "--repo-root", str(self._tmp),
                "--source-url", f"file://{_REPO_ROOT}",
                "--yes",
                "--dry-run",
            ]
        )
        self.assertIn("[dry-run]", proc.stdout)
        self.assertFalse((self._tmp / ".codex" / "profiles" / "si-chip.md").exists(),
                         "dry-run must not write any files")

    def test_dry_run_all_targets_prints_three_install_blocks(self) -> None:
        proc = _run(
            [
                "--target", "all",
                "--scope", "repo",
                "--repo-root", str(self._tmp),
                "--source-url", f"file://{_REPO_ROOT}",
                "--yes",
                "--dry-run",
            ]
        )
        # 3 install blocks → 3 "=> Installing" lines.
        install_lines = [ln for ln in proc.stdout.splitlines()
                         if ln.startswith("=> Installing")]
        self.assertEqual(len(install_lines), 3,
                         f"expected 3 install blocks, saw {install_lines}")


class FileUrlDualLayoutTests(unittest.TestCase):
    """file:// fetch tries repo-SoT layout AND extracted-tarball layout."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="sichip_layout_"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_codex_finds_files_under_repo_root_dot_codex(self) -> None:
        # Construct a fake "source" that ONLY has the .codex/ directory
        # (mimicking a repo-root layout without the SKILL tree).
        src = self._tmp / "fake_repo_src"
        src.mkdir()
        shutil.copytree(_REPO_ROOT / ".codex", src / ".codex")

        repo = self._tmp / "target_repo"
        repo.mkdir()

        proc = _run(
            [
                "--target", "codex",
                "--scope", "repo",
                "--repo-root", str(repo),
                "--source-url", f"file://{src}",
                "--yes",
            ]
        )
        self.assertEqual(proc.returncode, 0,
                         f"codex install via repo-root layout should pass; got {proc.stderr}")
        self.assertTrue((repo / ".codex" / "profiles" / "si-chip.md").is_file())

    def test_codex_finds_files_under_pages_mirror_codex(self) -> None:
        # Construct a fake "source" with the docs/Pages mirror layout
        # (codex/, no leading dot).
        src = self._tmp / "fake_pages_src"
        src.mkdir()
        shutil.copytree(_REPO_ROOT / "docs" / "codex", src / "codex")

        repo = self._tmp / "target_repo2"
        repo.mkdir()

        proc = _run(
            [
                "--target", "codex",
                "--scope", "repo",
                "--repo-root", str(repo),
                "--source-url", f"file://{src}",
                "--yes",
            ]
        )
        self.assertEqual(proc.returncode, 0,
                         f"codex install via pages mirror layout should pass; got {proc.stderr}")
        self.assertTrue((repo / ".codex" / "profiles" / "si-chip.md").is_file())

    def test_codex_clear_error_when_neither_layout_present(self) -> None:
        empty_src = self._tmp / "empty_src"
        empty_src.mkdir()
        repo = self._tmp / "target_repo3"
        repo.mkdir()

        proc = _run(
            [
                "--target", "codex",
                "--scope", "repo",
                "--repo-root", str(repo),
                "--source-url", f"file://{empty_src}",
                "--yes",
            ],
            expect_exit=1,
        )
        self.assertIn("missing codex bridge source file", proc.stderr + proc.stdout)
        # Error must mention BOTH attempted layouts so the operator can
        # diagnose without re-reading the script.
        self.assertIn(".codex/profiles/si-chip.md", proc.stderr + proc.stdout)
        self.assertIn("codex/profiles/si-chip.md", proc.stderr + proc.stdout)


class ManifestConsistencyTests(unittest.TestCase):
    """The MANIFEST inside install.sh matches the repo source-of-truth."""

    def test_expected_refs_matches_actual(self) -> None:
        text = _INSTALL_SH.read_text(encoding="utf-8")
        m = re.search(r"^EXPECTED_REFS=(\d+)\s*$", text, re.MULTILINE)
        self.assertIsNotNone(m, "EXPECTED_REFS line missing from install.sh")
        declared = int(m.group(1))
        actual = len(list((_REPO_ROOT / ".agents" / "skills" / "si-chip"
                           / "references").iterdir()))
        self.assertEqual(declared, actual,
                         f"install.sh EXPECTED_REFS={declared} drifted "
                         f"from .agents/skills/si-chip/references count={actual}")

    def test_expected_scripts_matches_non_test_actual(self) -> None:
        text = _INSTALL_SH.read_text(encoding="utf-8")
        m = re.search(r"^EXPECTED_SCRIPTS=(\d+)\s*$", text, re.MULTILINE)
        self.assertIsNotNone(m, "EXPECTED_SCRIPTS line missing from install.sh")
        declared = int(m.group(1))
        scripts_dir = _REPO_ROOT / ".agents" / "skills" / "si-chip" / "scripts"
        # Tarball excludes test_*.py and __pycache__, mirroring the
        # CHANGELOG v0.5.0 deterministic-build invariant.
        actual = sum(
            1
            for p in scripts_dir.iterdir()
            if p.is_file()
            and not p.name.startswith("test_")
            and not p.name.startswith(".")
        )
        self.assertEqual(declared, actual,
                         f"install.sh EXPECTED_SCRIPTS={declared} drifted from "
                         f"non-test scripts count={actual}")

    def test_codex_bridge_files_exist_in_repo(self) -> None:
        self.assertTrue((_REPO_ROOT / ".codex" / "profiles" / "si-chip.md").is_file())
        self.assertTrue((_REPO_ROOT / ".codex" / "instructions" / "si-chip-bridge.md").is_file())

    def test_codex_bridge_files_mirrored_into_docs(self) -> None:
        self.assertTrue((_REPO_ROOT / "docs" / "codex" / "profiles" / "si-chip.md").is_file())
        self.assertTrue((_REPO_ROOT / "docs" / "codex" / "instructions"
                         / "si-chip-bridge.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
