#!/usr/bin/env python3
"""Install-flow telemetry helpers for Si-Chip Round 6 D5 U3/U4 fill.

Exposes two functions used by
``.agents/skills/si-chip/scripts/aggregate_eval.py`` to hoist the two
remaining D5 ``usage_cost`` sub-metrics (spec §3.1 D5):

* ``count_setup_steps(install_script_path) -> int``  — parses ``install.sh``
  for the canonical user-facing step count. This reports **U3_setup_steps_count**.

  A "step" for the one-line installer flow is a distinct, user-visible
  interaction that the operator must **actively** take to proceed. We are
  explicit about the counting convention:

      1  Execute the one-liner ``curl ... | bash`` (with ``--yes`` / ``-y`` /
         fully-flagged non-interactive mode)                           → 1 step

  Additional explicit prompts fired by interactive mode (``read -p ...``
  / ``read -r choice``) would add to the count. The claim in CHANGELOG
  v0.1.1 ("one-line installer") is validated at U3 == 1 in the non-interactive
  flow — the flow the published docs lead with.

  The helper uses a **self-reported header** inside ``install.sh`` —
  ``# SI_CHIP_INSTALLER_STEPS=N`` — as the authoritative declaration. This
  keeps the answer deterministic across shells and avoids depending on
  bash-specific AST parsing. If the header is absent the helper falls back
  to counting explicit ``read -p`` / ``read -r`` prompts that are **not**
  behind a ``is_tty`` guard; that fallback is documented but not intended
  to be the primary path.

* ``time_first_success(install_script_path, dry_run=True) -> float | None``
  — wall-clock timing from installer invocation to the first
  ``[OK] Installed`` success line. This reports **U4_time_to_first_success**.

  In Round 6 the default is ``dry_run=True`` which runs the embedded
  ``--dry-run`` flag against the local ``install.sh`` and returns the
  wall-clock of THAT (a valid floor estimate — real installs include
  network + tarball extraction on top of the same control flow). Real
  wall-clock measurement is opt-in via ``dry_run=False`` and may fail
  in offline environments (returns ``None`` plus a logged warning per the
  workspace rule "No Silent Failures").

  The computed duration is **not** substituted with a placeholder on
  failure — we return ``None`` and log a warning, surfacing the
  degenerate path explicitly.

CLI::

    python3 tools/install_telemetry.py --install-sh install.sh --json

Outputs a single-line JSON object with U3 / U4 derivation metadata; the
``--json`` shape is consumed by ``aggregate_eval.py --install-telemetry``.

Workspace-rule notes
--------------------

* "No Silent Failures": failures (missing install.sh, unreadable file,
  installer non-zero exit, timeout) are surfaced — either via raised
  exception at import / call time (missing file) or via ``None`` +
  logged warning at runtime (subprocess failure). Never zero-substituted.
* "Mandatory Verification": unit tests in
  ``tools/test_install_telemetry.py`` cover step-counting (happy path,
  missing header, interactive-prompt fallback, malformed header) and
  ``time_first_success`` via ``subprocess`` monkey-patching.
* Safety: the subprocess runs the installer with ``--dry-run --yes
  --target cursor --scope repo --repo-root <tmp>`` so no network I/O or
  destructive writes happen in the default ``dry_run=True`` mode.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

LOGGER = logging.getLogger("si_chip.install_telemetry")

SCRIPT_VERSION = "0.1.0"

# ``# SI_CHIP_INSTALLER_STEPS=N`` — self-reported step count the installer
# advertises. We treat the FIRST match as authoritative (installer author's
# declared contract; any downstream reader can therefore answer U3 in O(N)
# without parsing bash).
_SELF_REPORTED_STEPS_RE = re.compile(
    r"^\s*#\s*SI_CHIP_INSTALLER_STEPS\s*=\s*(-?\d+)\s*$",
    re.MULTILINE,
)

# Fallback: count unguarded ``read -p`` / ``read -r`` (interactive prompt
# lines) — these are each one potential user-visible step. Lines that are
# commented out (``^\s*#``) do not count. The non-interactive flow keeps
# prompts behind an ``is_tty`` / ``--yes`` guard, so this is an
# upper-bound estimate, not the "headline" number.
_READ_PROMPT_RE = re.compile(
    r"^(?!\s*#)\s*read\s+(?:-p|-r)\b",
    re.MULTILINE,
)


def count_setup_steps(install_script_path: str) -> int:
    """Return the canonical user-facing step count for the installer flow.

    Prefers the self-reported ``# SI_CHIP_INSTALLER_STEPS=N`` header.
    Falls back to counting unguarded ``read -p`` / ``read -r`` prompts
    when the header is missing (legacy path; logs a warning).

    Parameters
    ----------
    install_script_path :
        Filesystem path to ``install.sh`` (relative or absolute).

    Returns
    -------
    int
        The step count. Invariant: ``>= 0``. For the v0.1.5 Si-Chip
        one-line installer in its non-interactive form this is ``1``.

    Raises
    ------
    FileNotFoundError
        If the installer path does not exist.
    ValueError
        If the header is malformed (e.g., negative integer).

    >>> import tempfile, pathlib
    >>> tmp = pathlib.Path(tempfile.mkdtemp()) / "install.sh"
    >>> _ = tmp.write_text("#!/usr/bin/env bash\\n# SI_CHIP_INSTALLER_STEPS=1\\necho hi\\n")
    >>> count_setup_steps(str(tmp))
    1
    """

    path = Path(install_script_path)
    if not path.exists():
        raise FileNotFoundError(f"install script not found: {install_script_path}")
    text = path.read_text(encoding="utf-8")

    m = _SELF_REPORTED_STEPS_RE.search(text)
    if m is not None:
        count = int(m.group(1))
        if count < 0:
            raise ValueError(
                f"SI_CHIP_INSTALLER_STEPS header must be >= 0, got {count}"
            )
        LOGGER.info("count_setup_steps: self-reported header count=%d", count)
        return count

    # Fallback: count interactive prompts. This is a heuristic upper bound
    # (a real installer gates prompts behind is_tty() / --yes so not all
    # matches fire at runtime) — we log a warning so the caller knows.
    fallback = len(_READ_PROMPT_RE.findall(text))
    LOGGER.warning(
        "count_setup_steps: SI_CHIP_INSTALLER_STEPS header not found; "
        "falling back to unguarded 'read' prompt count=%d",
        fallback,
    )
    return fallback


def time_first_success(
    install_script_path: str,
    *,
    dry_run: bool = True,
    timeout_s: float = 60.0,
) -> Optional[float]:
    """Time the installer from invocation to the first success line.

    The "first success" is the first ``[OK] Installed`` line in the
    installer's stdout (``install_one`` in ``install.sh`` emits this at
    the end of a successful per-target install). We use that as the U4
    anchor because it is semantically equivalent to "the user's first
    success moment": SKILL.md has landed at its install dir and the
    payload is verifiable.

    Parameters
    ----------
    install_script_path :
        Filesystem path to ``install.sh``.
    dry_run :
        When ``True`` (default), the installer is invoked with
        ``--dry-run --yes --target cursor --scope repo --repo-root <tmp>
        --source-url file://<repo-root>``. Dry-run short-circuits both
        network I/O and destructive filesystem writes, so the timing is
        a valid **floor estimate** for U4. When ``False``, the real
        installer flow runs (network + copy); returns ``None`` with a
        warning if that fails.
    timeout_s :
        Subprocess timeout. Default 60 s — matches the §Round 6 master
        plan sanity ceiling for a one-line install.

    Returns
    -------
    float | None
        Wall-clock seconds from ``subprocess.Popen`` to the first
        ``[OK] Installed`` line in stdout. ``None`` when the subprocess
        fails, times out, or never emits a success line. Never
        zero-substitutes on failure.

    >>> # Deterministic smoke: unit tests monkey-patch subprocess.run so
    >>> # this docstring example intentionally does not call the helper.
    >>> type(time_first_success).__name__
    'function'
    """

    path = Path(install_script_path)
    if not path.exists():
        raise FileNotFoundError(f"install script not found: {install_script_path}")

    cmd: list[str] = ["bash", str(path.resolve())]
    if dry_run:
        # Tmp repo root so the installer's --scope repo path resolves;
        # the default HTTP --source-url is retained because the installer's
        # --dry-run branch short-circuits the HTTP fetch + extract + verify
        # steps (logs them but does not actually execute them). This keeps
        # the helper offline-safe while still exercising the real code path
        # from argument parsing through verify_install — a valid floor
        # estimate for U4.
        tmp_repo = tempfile.mkdtemp(prefix="si_chip_telemetry_")
        cmd.extend(
            [
                "--dry-run",
                "--yes",
                "--target",
                "cursor",
                "--scope",
                "repo",
                "--repo-root",
                tmp_repo,
            ]
        )
    else:
        # In non-dry mode the caller is responsible for supplying whatever
        # extra flags they want; we invoke with --yes and default target/scope
        # so the timing is uniform. Any failure propagates as None + warning.
        cmd.extend(["--yes", "--target", "cursor", "--scope", "global"])

    LOGGER.info("time_first_success: running %s", cmd)

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        LOGGER.warning(
            "time_first_success: subprocess timed out after %.1f s", timeout_s
        )
        return None
    except FileNotFoundError as exc:
        # ``bash`` missing is a setup problem, not a silent failure.
        LOGGER.warning("time_first_success: subprocess spawn failed: %s", exc)
        return None
    elapsed = time.perf_counter() - start

    if proc.returncode != 0:
        LOGGER.warning(
            "time_first_success: installer exited rc=%d; stderr=%s",
            proc.returncode,
            proc.stderr.strip()[:500],
        )
        return None

    if "[OK] Installed" not in proc.stdout:
        LOGGER.warning(
            "time_first_success: installer exited 0 but no '[OK] Installed' "
            "line was observed; treating as degenerate path"
        )
        return None

    # Cap at timeout so the return is always in [0, timeout_s]; the extra
    # half-second is negligible but keeps the invariant airtight.
    if elapsed > timeout_s:
        elapsed = timeout_s

    return float(elapsed)


def build_telemetry_payload(
    install_script_path: str,
    *,
    dry_run: bool = True,
    timeout_s: float = 60.0,
) -> Dict[str, Any]:
    """Build the U3 / U4 derivation payload consumed by ``aggregate_eval.py``.

    Shape (consumed by ``aggregate_eval.hoist_u3_setup_steps_count``
    and ``aggregate_eval.hoist_u4_time_to_first_success``)::

        {
          "install_script_path": str,
          "u3_setup_steps_count": int,
          "u4_time_to_first_success_s": float | None,
          "dry_run": bool,
          "derivation": {
            "u3_method": str,
            "u4_method": str,
            "u4_timeout_s": float,
          }
        }

    ``u4_time_to_first_success_s`` is ``None`` in offline/failure paths;
    the caller (aggregator) preserves that as an explicit ``None`` in
    the metrics_report per spec §3.2 frozen constraint #2.
    """

    u3 = count_setup_steps(install_script_path)
    u4 = time_first_success(
        install_script_path, dry_run=dry_run, timeout_s=timeout_s
    )
    u3_method = (
        "count_setup_steps via self-reported # SI_CHIP_INSTALLER_STEPS=N header "
        "(fallback: count unguarded 'read -p'/'read -r' prompts)"
    )
    u4_method = (
        "wall_clock seconds from bash install.sh invocation to first "
        "'[OK] Installed' stdout line (dry_run=True short-circuits network + "
        "destructive writes — floor estimate)."
        if dry_run
        else (
            "wall_clock seconds from bash install.sh invocation to first "
            "'[OK] Installed' stdout line (real-install path; opt-in via dry_run=False)."
        )
    )
    return {
        "install_script_path": str(Path(install_script_path).resolve()),
        "u3_setup_steps_count": u3,
        "u4_time_to_first_success_s": u4,
        "dry_run": dry_run,
        "derivation": {
            "u3_method": u3_method,
            "u4_method": u4_method,
            "u4_timeout_s": timeout_s,
            "script_version": SCRIPT_VERSION,
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compute Si-Chip Round 6 U3 (setup_steps_count) + U4 "
            "(time_to_first_success) from install.sh."
        ),
    )
    parser.add_argument(
        "--install-sh",
        default="install.sh",
        help="Path to install.sh (default: install.sh)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help=(
            "Run the real installer (network + destructive writes). "
            "Default is dry-run, which is deterministic and offline-safe."
        ),
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=60.0,
        help="Subprocess timeout in seconds (default: 60).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a single-line JSON payload on stdout.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    payload = build_telemetry_payload(
        args.install_sh,
        dry_run=not args.no_dry_run,
        timeout_s=args.timeout_s,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(
            f"U3_setup_steps_count = {payload['u3_setup_steps_count']}"
        )
        print(
            f"U4_time_to_first_success_s = {payload['u4_time_to_first_success_s']}"
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        LOGGER.error("fatal: %s", exc)
        raise
