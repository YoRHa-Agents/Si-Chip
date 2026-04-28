#!/usr/bin/env python3
"""Unit tests for ``tools/install_telemetry.py`` (Round 6 D5 U3/U4 fill).

Workspace rule "Mandatory Verification": the U3/U4 helpers landed in
Round 6 MUST carry tests. These tests exercise:

* ``count_setup_steps`` — the happy path (self-reported header), the
  fallback path (legacy installer without the header), the zero-step
  edge case, malformed headers, missing file, and negative-number
  rejection. Also verifies the actual repo ``install.sh`` advertises
  exactly 1 step (= the CHANGELOG v0.1.1 one-line-installer claim).
* ``time_first_success`` — determinism via ``subprocess.run``
  monkey-patching. We cover:
    - happy path with a fake subprocess that emits ``[OK] Installed``
    - non-zero return code → ``None`` (degenerate path)
    - absent success line despite rc=0 → ``None``
    - ``TimeoutExpired`` → ``None``
    - FileNotFoundError on bash-missing → ``None``
    - real dry-run smoke (gated behind ``SI_CHIP_RUN_DRY_RUN`` env var so
      CI does not spend time running bash if disabled).
* ``build_telemetry_payload`` — shape / key presence / derivation fields.

Run::

    python3 tools/test_install_telemetry.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import install_telemetry as it  # noqa: E402


REPO_INSTALL_SH = _THIS_DIR.parent / "install.sh"


def _write(tmpdir: Path, name: str, body: str) -> Path:
    p = tmpdir / name
    p.write_text(body, encoding="utf-8")
    return p


class CountSetupStepsTests(unittest.TestCase):

    def test_self_reported_header_single_step(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh",
                   "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\necho hi\n")
        self.assertEqual(it.count_setup_steps(str(p)), 1)

    def test_self_reported_header_zero_step(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh",
                   "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=0\n")
        self.assertEqual(it.count_setup_steps(str(p)), 0)

    def test_self_reported_header_two_steps(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh",
                   "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=2\n")
        self.assertEqual(it.count_setup_steps(str(p)), 2)

    def test_fallback_prompt_count_two(self) -> None:
        """No self-reported header → fall back to counting 'read -p'/'read -r'."""

        tmp = Path(tempfile.mkdtemp())
        body = (
            "#!/usr/bin/env bash\n"
            "prompt_target() {\n"
            "  read -p 'foo: ' choice\n"
            "}\n"
            "prompt_scope() {\n"
            "  read -r choice\n"
            "}\n"
        )
        p = _write(tmp, "install.sh", body)
        self.assertEqual(it.count_setup_steps(str(p)), 2)

    def test_fallback_ignores_commented_read(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        body = (
            "#!/usr/bin/env bash\n"
            "# read -p 'commented: ' choice   # does not count\n"
            "read -r choice   # counts\n"
        )
        p = _write(tmp, "install.sh", body)
        self.assertEqual(it.count_setup_steps(str(p)), 1)

    def test_fallback_no_prompts_returns_zero(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh", "#!/usr/bin/env bash\necho hi\n")
        self.assertEqual(it.count_setup_steps(str(p)), 0)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            it.count_setup_steps("/does/not/exist/install.sh")

    def test_negative_header_rejected(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh",
                   "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=-1\n")
        with self.assertRaises(ValueError):
            it.count_setup_steps(str(p))

    def test_header_precedence_over_fallback(self) -> None:
        """A file with both a header AND prompts must prefer the header."""

        tmp = Path(tempfile.mkdtemp())
        body = (
            "#!/usr/bin/env bash\n"
            "# SI_CHIP_INSTALLER_STEPS=1\n"
            "read -p 'a: ' x\n"
            "read -r y\n"
            "read -r z\n"
        )
        p = _write(tmp, "install.sh", body)
        self.assertEqual(it.count_setup_steps(str(p)), 1)

    def test_real_repo_install_sh_header_is_one(self) -> None:
        """The repo's install.sh must advertise U3 == 1 (v0.1.1 claim)."""

        if not REPO_INSTALL_SH.exists():
            self.skipTest("repo install.sh not present in this checkout")
        self.assertEqual(it.count_setup_steps(str(REPO_INSTALL_SH)), 1)


class TimeFirstSuccessTests(unittest.TestCase):

    def _fake_completed(self, stdout: str, returncode: int = 0) -> "subprocess.CompletedProcess":
        return subprocess.CompletedProcess(
            args=["bash", "install.sh"], returncode=returncode,
            stdout=stdout, stderr="",
        )

    def test_happy_path_returns_positive_duration(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh", "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        with mock.patch.object(
            subprocess, "run",
            return_value=self._fake_completed("[OK] Installed foo\n"),
        ):
            v = it.time_first_success(str(p))
        self.assertIsNotNone(v)
        self.assertGreater(v, 0.0)
        self.assertLess(v, 60.0)

    def test_returncode_nonzero_returns_none(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh", "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        with mock.patch.object(
            subprocess, "run",
            return_value=self._fake_completed("error\n", returncode=2),
        ):
            v = it.time_first_success(str(p))
        self.assertIsNone(v)

    def test_no_success_line_returns_none(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh", "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        with mock.patch.object(
            subprocess, "run",
            return_value=self._fake_completed("some logs without OK marker\n"),
        ):
            v = it.time_first_success(str(p))
        self.assertIsNone(v)

    def test_timeout_returns_none(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh", "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        with mock.patch.object(
            subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd=["bash"], timeout=5.0),
        ):
            v = it.time_first_success(str(p), timeout_s=5.0)
        self.assertIsNone(v)

    def test_bash_missing_returns_none(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh", "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        with mock.patch.object(
            subprocess, "run",
            side_effect=FileNotFoundError("bash: not found"),
        ):
            v = it.time_first_success(str(p))
        self.assertIsNone(v)

    def test_missing_install_sh_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            it.time_first_success("/does/not/exist/install.sh")

    def test_real_dry_run_smoke(self) -> None:
        """Run the real bash install.sh --dry-run; opt-in via env var.

        Gated so CI without bash does not spend a shell subprocess on
        this test by default. The production aggregator still relies on
        the real run at round_6/raw/install_dry_run.log.
        """

        if os.environ.get("SI_CHIP_RUN_DRY_RUN") != "1":
            self.skipTest("gated: set SI_CHIP_RUN_DRY_RUN=1 to run the real dry-run")
        if not REPO_INSTALL_SH.exists():
            self.skipTest("repo install.sh not present in this checkout")
        v = it.time_first_success(str(REPO_INSTALL_SH), dry_run=True, timeout_s=60.0)
        self.assertIsNotNone(v)
        self.assertGreater(v, 0.0)
        self.assertLess(v, 60.0)


class BuildTelemetryPayloadTests(unittest.TestCase):

    def _stub_run(self, tmp_path: Path) -> mock._patch:
        completed = subprocess.CompletedProcess(
            args=["bash", str(tmp_path)], returncode=0,
            stdout="[OK] Installed foo\n", stderr="",
        )
        return mock.patch.object(subprocess, "run", return_value=completed)

    def test_payload_shape_happy_path(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh",
                   "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        with self._stub_run(p):
            payload = it.build_telemetry_payload(str(p))
        self.assertEqual(payload["u3_setup_steps_count"], 1)
        self.assertIsNotNone(payload["u4_time_to_first_success_s"])
        self.assertGreater(payload["u4_time_to_first_success_s"], 0.0)
        self.assertTrue(payload["dry_run"])
        self.assertIn("u3_method", payload["derivation"])
        self.assertIn("u4_method", payload["derivation"])
        self.assertEqual(payload["derivation"]["script_version"], it.SCRIPT_VERSION)
        self.assertEqual(
            Path(payload["install_script_path"]).name, "install.sh"
        )

    def test_payload_with_failure_keeps_u4_none(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh",
                   "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        failed = subprocess.CompletedProcess(
            args=["bash", str(p)], returncode=1,
            stdout="error\n", stderr="failed\n",
        )
        with mock.patch.object(subprocess, "run", return_value=failed):
            payload = it.build_telemetry_payload(str(p))
        self.assertEqual(payload["u3_setup_steps_count"], 1)
        self.assertIsNone(payload["u4_time_to_first_success_s"])

    def test_payload_is_json_serializable(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        p = _write(tmp, "install.sh",
                   "#!/usr/bin/env bash\n# SI_CHIP_INSTALLER_STEPS=1\n")
        with self._stub_run(p):
            payload = it.build_telemetry_payload(str(p))
        # Must round-trip through json.
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["u3_setup_steps_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
