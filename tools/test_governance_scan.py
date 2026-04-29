#!/usr/bin/env python3
"""Unit tests for ``tools/governance_scan.py`` (Round 8 D7 V1-V4 fill).

Workspace rule "Mandatory Verification": the V1/V2/V3/V4 helpers
landed in Round 8 MUST carry tests. These tests exercise:

* ``scan_permission_scope`` — happy path (empty / clean Si-Chip tree
  → 0), positive-count fixture with a synthetic script writing to
  ``/etc/`` (out-of-scope), missing-path raises, allowed-prefix
  handling.
* ``scan_credential_surface`` — happy path (clean tree → 0), positive
  count from a synthetic fixture carrying each pattern, the
  MUST-NOT-log-secret-value invariant (assert captured log records
  never contain the actual secret body, only the pattern name +
  count), missing-path raises.
* ``scan_drift_signal`` — zero drift (identical mirrors → 0.0),
  non-zero drift when one mirror diverges, requires-two-mirrors raises,
  missing mirror raises.
* ``scan_staleness_days`` — same-day (today == last_reviewed_at → 0),
  positive-days case, missing YAML raises, malformed YAML raises, the
  future-date guard raises.
* ``build_governance_report`` — returns all 4 V keys + provenance, CLI
  JSON round-trip via subprocess.

Run::

    python3 tools/test_governance_scan.py
    python -m pytest tools/test_governance_scan.py -q
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import governance_scan as gs  # noqa: E402


REPO_ROOT = _THIS_DIR.parent
REPO_SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "si-chip"
REPO_CURSOR_MIRROR = REPO_ROOT / ".cursor" / "skills" / "si-chip" / "SKILL.md"
REPO_CLAUDE_MIRROR = REPO_ROOT / ".claude" / "skills" / "si-chip" / "SKILL.md"
REPO_CANONICAL_MIRROR = REPO_SKILL_DIR / "SKILL.md"


def _write(tmpdir: Path, name: str, body: str) -> Path:
    """Write a file under a tmp dir, creating parent dirs as needed."""

    p = tmpdir / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


# ─────────────────────────── V1 tests ───────────────────────────


class ScanPermissionScopeTests(unittest.TestCase):
    """Direct unit tests for :func:`scan_permission_scope`."""

    def test_empty_input_returns_zero(self) -> None:
        self.assertEqual(gs.scan_permission_scope(REPO_ROOT, []), 0)

    def test_real_si_chip_tree_is_clean(self) -> None:
        """The canonical Si-Chip script tree must report V1 = 0."""

        if not REPO_SKILL_DIR.exists():
            self.skipTest("canonical skill tree missing in this checkout")
        v1 = gs.scan_permission_scope(
            REPO_ROOT, [REPO_SKILL_DIR / "scripts"]
        )
        self.assertEqual(v1, 0)

    def test_positive_count_with_out_of_scope_write(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _write(
            tmp,
            "naughty.py",
            "from pathlib import Path\n"
            "open('/etc/passwd_append', 'w').write('boom')\n",
        )
        v1 = gs.scan_permission_scope(tmp, [tmp])
        self.assertEqual(v1, 1)

    def test_missing_path_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            gs.scan_permission_scope(
                REPO_ROOT, [Path("/does/not/exist/skill.py")]
            )

    def test_in_scope_write_under_dogfood_not_counted(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _write(
            tmp,
            "helper.py",
            "open('.local/dogfood/round_1/result.json', 'w').write('{}')\n",
        )
        v1 = gs.scan_permission_scope(tmp, [tmp])
        self.assertEqual(v1, 0)

    def test_relative_path_treated_as_in_scope(self) -> None:
        """Relative paths are caller-parameterised — treated as in-scope."""

        tmp = Path(tempfile.mkdtemp())
        _write(
            tmp,
            "param.py",
            "open('metrics_report.yaml', 'w').write('x')\n",
        )
        self.assertEqual(gs.scan_permission_scope(tmp, [tmp]), 0)

    def test_mirror_targets_are_in_scope(self) -> None:
        """Writes to .cursor/skills/si-chip/ and .claude/skills/si-chip/ are OK."""

        tmp = Path(tempfile.mkdtemp())
        _write(
            tmp,
            "install.sh",
            "#!/usr/bin/env bash\n"
            "cat SKILL.md > /.cursor/skills/si-chip/SKILL.md\n",
        )
        # The shell redirect target starts with /.cursor/skills/si-chip/ which
        # matches the allowed prefix (DEFAULT_V1_ALLOWED_PREFIXES handles the
        # leading slash in _is_out_of_scope).
        v1 = gs.scan_permission_scope(tmp, [tmp])
        self.assertEqual(v1, 0)


# ─────────────────────────── V2 tests ───────────────────────────


class ScanCredentialSurfaceTests(unittest.TestCase):
    """Direct unit tests for :func:`scan_credential_surface`."""

    def test_empty_input_returns_zero(self) -> None:
        self.assertEqual(
            gs.scan_credential_surface(REPO_ROOT, [], extra_artifacts=()), 0
        )

    def test_real_si_chip_tree_is_clean(self) -> None:
        """The canonical Si-Chip tree must report V2 = 0."""

        if not REPO_SKILL_DIR.exists():
            self.skipTest("canonical skill tree missing in this checkout")
        v2 = gs.scan_credential_surface(REPO_ROOT, [REPO_SKILL_DIR])
        self.assertEqual(v2, 0)

    def test_positive_count_aws_key(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _write(
            tmp,
            "secret.py",
            "aws_key = 'AKIAIOSFODNN7EXAMPLE'  # looks like an AWS key\n",
        )
        self.assertGreaterEqual(
            gs.scan_credential_surface(tmp, [tmp]), 1
        )

    def test_positive_count_pem_private_key(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _write(
            tmp,
            "keys.txt",
            "here is the key:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "ZEROSGARBAGE\n"
            "-----END RSA PRIVATE KEY-----\n",
        )
        self.assertGreaterEqual(gs.scan_credential_surface(tmp, [tmp]), 1)

    def test_positive_count_credential_assignment(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _write(
            tmp,
            "config.yaml",
            "api_key: \"super_secret_value_abc123\"\n",
        )
        self.assertGreaterEqual(gs.scan_credential_surface(tmp, [tmp]), 1)

    def test_must_not_log_secret_value(self) -> None:
        """V2 CRITICAL invariant: scanner MUST NOT emit the matched secret."""

        secret = "AKIAIOSFODNN7SECRET1"  # nosec - test fixture only
        tmp = Path(tempfile.mkdtemp())
        _write(tmp, "leaky.py", f"aws_key = '{secret}'\n")
        with self.assertLogs("si_chip.governance_scan", level="WARNING") as cm:
            _ = gs.scan_credential_surface(tmp, [tmp])
        joined = "\n".join(cm.output)
        self.assertIn("aws_access_key", joined)  # pattern name is fine
        self.assertIn("1 time", joined)           # count is fine
        self.assertNotIn(secret, joined)           # THE VALUE IS NOT LOGGED
        # Also assert no prefix of the secret leaks.
        self.assertNotIn(secret[:10], joined)

    def test_missing_path_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            gs.scan_credential_surface(
                REPO_ROOT, [Path("/does/not/exist/SKILL.md")],
            )

    def test_extra_artifacts_merged_and_deduped(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _write(tmp, "a.py", "x = 1\n")
        # Single file scanned via BOTH skill_paths and extra_artifacts
        # should not be double-counted.
        v2 = gs.scan_credential_surface(
            tmp, [tmp / "a.py"], extra_artifacts=[tmp / "a.py"]
        )
        self.assertEqual(v2, 0)


# ─────────────────────────── V3 tests ───────────────────────────


class ScanDriftSignalTests(unittest.TestCase):
    """Direct unit tests for :func:`scan_drift_signal`."""

    def test_two_identical_mirrors_yield_zero(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        a = _write(tmp, "A/SKILL.md", "hello\n")
        b = _write(tmp, "B/SKILL.md", "hello\n")
        self.assertEqual(gs.scan_drift_signal([a, b]), 0.0)

    def test_three_identical_mirrors_yield_zero(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        a = _write(tmp, "A/SKILL.md", "hello world\n")
        b = _write(tmp, "B/SKILL.md", "hello world\n")
        c = _write(tmp, "C/SKILL.md", "hello world\n")
        self.assertEqual(gs.scan_drift_signal([a, b, c]), 0.0)

    def test_one_divergent_mirror_yields_nonzero(self) -> None:
        """One drifts → drift_zero_ratio = 1/3 → V3 = 2/3."""

        tmp = Path(tempfile.mkdtemp())
        a = _write(tmp, "A/SKILL.md", "hello\n")
        b = _write(tmp, "B/SKILL.md", "hello\n")
        c = _write(tmp, "C/SKILL.md", "goodbye\n")
        v3 = gs.scan_drift_signal([a, b, c])
        self.assertAlmostEqual(v3, 2.0 / 3.0, places=6)

    def test_real_si_chip_mirrors_drift_zero(self) -> None:
        """Repo mirrors must be byte-equal per spec §7.2."""

        for m in (REPO_CANONICAL_MIRROR, REPO_CURSOR_MIRROR, REPO_CLAUDE_MIRROR):
            if not m.exists():
                self.skipTest(f"missing repo mirror: {m}")
        self.assertEqual(
            gs.scan_drift_signal(
                [REPO_CANONICAL_MIRROR, REPO_CURSOR_MIRROR, REPO_CLAUDE_MIRROR]
            ),
            0.0,
        )

    def test_requires_two_mirrors_raises(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        a = _write(tmp, "A/SKILL.md", "x\n")
        with self.assertRaises(ValueError):
            gs.scan_drift_signal([a])

    def test_missing_mirror_raises(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        a = _write(tmp, "A/SKILL.md", "x\n")
        with self.assertRaises(FileNotFoundError):
            gs.scan_drift_signal([a, tmp / "does_not_exist.md"])

    def test_range_invariant_in_unit_interval(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        paths = [
            _write(tmp, f"M{i}/SKILL.md", f"body-{i}\n") for i in range(4)
        ]
        v3 = gs.scan_drift_signal(paths)
        self.assertGreaterEqual(v3, 0.0)
        self.assertLessEqual(v3, 1.0)


# ─────────────────────────── V4 tests ───────────────────────────


class ScanStalenessDaysTests(unittest.TestCase):
    """Direct unit tests for :func:`scan_staleness_days`."""

    def _profile(self, tmp: Path, last_reviewed: str) -> Path:
        body = (
            "basic_ability:\n"
            "  lifecycle:\n"
            f"    last_reviewed_at: '{last_reviewed}'\n"
        )
        return _write(tmp, "profile.yaml", body)

    def test_same_day_returns_zero(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = self._profile(tmp, "2026-04-28")
        self.assertEqual(
            gs.scan_staleness_days(p, today=_dt.date(2026, 4, 28)),
            0,
        )

    def test_positive_days(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = self._profile(tmp, "2026-04-28")
        self.assertEqual(
            gs.scan_staleness_days(p, today=_dt.date(2026, 5, 28)),
            30,
        )

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            gs.scan_staleness_days(
                Path("/does/not/exist/profile.yaml"),
                today=_dt.date(2026, 4, 28),
            )

    def test_malformed_yaml_raises(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "bad.yaml", "this is: [not: valid\n")
        with self.assertRaises(ValueError):
            gs.scan_staleness_days(p, today=_dt.date(2026, 4, 28))

    def test_missing_last_reviewed_at_raises(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "profile.yaml", "basic_ability:\n  lifecycle: {}\n")
        with self.assertRaises(ValueError):
            gs.scan_staleness_days(p, today=_dt.date(2026, 4, 28))

    def test_bad_iso_date_raises(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = self._profile(tmp, "not-a-date")
        with self.assertRaises(ValueError):
            gs.scan_staleness_days(p, today=_dt.date(2026, 4, 28))

    def test_future_date_raises(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = self._profile(tmp, "2027-01-01")
        with self.assertRaises(ValueError):
            gs.scan_staleness_days(p, today=_dt.date(2026, 4, 28))


# ─────────────────────────── Build report + CLI tests ───────────────────────────


class BuildGovernanceReportTests(unittest.TestCase):
    """Direct tests for :func:`build_governance_report`."""

    def test_real_si_chip_returns_all_zero_plus_provenance(self) -> None:
        if not REPO_SKILL_DIR.exists():
            self.skipTest("canonical skill tree missing")
        if not REPO_CURSOR_MIRROR.exists() or not REPO_CLAUDE_MIRROR.exists():
            self.skipTest("mirror trees missing")
        tmp = Path(tempfile.mkdtemp())
        profile = _write(
            tmp,
            "profile.yaml",
            "basic_ability:\n"
            "  lifecycle:\n"
            "    last_reviewed_at: '2026-04-28'\n",
        )
        report = gs.build_governance_report(
            REPO_ROOT,
            [REPO_SKILL_DIR],
            [REPO_CANONICAL_MIRROR, REPO_CURSOR_MIRROR, REPO_CLAUDE_MIRROR],
            profile,
            today=_dt.date(2026, 4, 28),
        )
        self.assertEqual(report["V1_permission_scope"], 0)
        self.assertEqual(report["V2_credential_surface"], 0)
        self.assertEqual(report["V3_drift_signal"], 0.0)
        self.assertEqual(report["V4_staleness_days"], 0)
        self.assertIn("provenance", report)
        prov = report["provenance"]
        for key in (
            "script_version",
            "v1_derivation",
            "v2_derivation",
            "v3_derivation",
            "v4_derivation",
            "governance_risk_delta",
            "governance_risk_delta_method",
        ):
            self.assertIn(key, prov)
        # Clean baseline → delta is exactly 0.0.
        self.assertEqual(prov["governance_risk_delta"], 0.0)

    def test_cli_json_round_trip(self) -> None:
        """CLI ``--json`` round-trip feeds the aggregator."""

        if not REPO_SKILL_DIR.exists():
            self.skipTest("canonical skill tree missing")
        if not REPO_CURSOR_MIRROR.exists() or not REPO_CLAUDE_MIRROR.exists():
            self.skipTest("mirror trees missing")
        tmp = Path(tempfile.mkdtemp())
        profile = _write(
            tmp,
            "profile.yaml",
            "basic_ability:\n"
            "  lifecycle:\n"
            "    last_reviewed_at: '2026-04-28'\n",
        )
        script = _THIS_DIR / "governance_scan.py"
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo-root", str(REPO_ROOT),
                "--basic-ability-profile", str(profile),
                "--today", "2026-04-28",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["V1_permission_scope"], 0)
        self.assertEqual(payload["V2_credential_surface"], 0)
        self.assertEqual(payload["V3_drift_signal"], 0.0)
        self.assertEqual(payload["V4_staleness_days"], 0)
        self.assertIn("provenance", payload)


class ComputeGovernanceRiskDeltaTests(unittest.TestCase):
    """Direct tests for :func:`compute_governance_risk_delta`."""

    def test_all_zero_inputs_give_zero_delta(self) -> None:
        self.assertEqual(gs.compute_governance_risk_delta(0, 0, 0.0, 0), 0.0)

    def test_v1_only_moves_delta_negative(self) -> None:
        v = gs.compute_governance_risk_delta(1, 0, 0.0, 0)
        self.assertLess(v, 0.0)
        self.assertAlmostEqual(v, -0.25, places=6)

    def test_all_worst_case_clamped_at_minus_one(self) -> None:
        v = gs.compute_governance_risk_delta(99, 99, 1.0, 10_000)
        self.assertEqual(v, -1.0)

    def test_staleness_cap_validation(self) -> None:
        with self.assertRaises(ValueError):
            gs.compute_governance_risk_delta(0, 0, 0.0, 0, v4_staleness_cap_days=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
