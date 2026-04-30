#!/usr/bin/env python3
"""Si-Chip health-smoke-check CLI runner (spec v0.4.0-rc1 §21.4).

Invokes HTTP probes per ``packaging.health_smoke_check`` declarations
on a ``BasicAbilityProfile``; verifies each probe's ``expected_status``
and ``sentinel_field`` / ``sentinel_value_predicate``; aggregates
results by §21.3 axis (read / write / auth / dependency); emits a
machine-readable JSON report and sets a standard exit code.

Usage::

    python tools/health_smoke.py \\
        --profile <basic_ability_profile.yaml> \\
        --json \\
        --timeout 30

Or for ``eval_skill.py`` dispatch (single-check mode)::

    python tools/health_smoke.py \\
        --check '<json-encoded check dict>' \\
        --json \\
        --timeout 30

Output JSON shape (per ``--profile`` mode)::

    {
        "profile_path": "...",
        "checks_total": <int>,
        "checks_passed": <int>,
        "per_axis": {
            "read": {"total": <int>, "passed": <int>, "checks": [...]},
            "write": {...},
            "auth": {...},
            "dependency": {...}
        },
        "per_check": [
            {
                "endpoint": "...",
                "axis": "read|write|auth|dependency",
                "pass": true|false,
                "observed": {"status": ..., "sentinel_value": ..., "error": ...},
                "attempt_count": <int>,
                "duration_s": <float>
            },
            ...
        ]
    }

Exit codes
----------
* 0 — all checks pass OR ``packaging.health_smoke_check`` is empty /
  missing (no live backend declared).
* 1 — any check failed.
* 2 — profile read / parse error.

Spec v0.4.0-rc1 §21.1 schema fields supported per check:

    endpoint, expected_status, max_attempts, retry_delay_ms,
    sentinel_field, sentinel_value_predicate, axis, description.

Dependencies
------------
Uses stdlib only (``urllib.request``) per the task's "pyyaml + stdlib
only" constraint; no new packages added.

Workspace rule "No Silent Failures": network errors, JSON parse
errors, and predicate evaluation errors are all captured explicitly
in ``observed.error`` and the check is marked ``pass: false`` — we
never silently pass a probe.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.health_smoke")

SCRIPT_VERSION = "0.1.0"

# §21.3 4-axis taxonomy.
VALID_AXES: Tuple[str, ...] = ("read", "write", "auth", "dependency")


# --- Predicate evaluation ---------------------------------------------


def evaluate_predicate(
    sentinel_value: Any, predicate: str
) -> Tuple[bool, Optional[str]]:
    """Evaluate a §21.1 sentinel predicate against an observed value.

    Supported predicate syntax (spec §21.1):

      * ``">0"`` / ``"<0"`` / ``">= 1714464000000"`` / ``"<= N"``
      * ``"== <value>"`` / ``"!= <value>"`` (values compared as
        numbers if parseable, else as strings).
      * ``"!= null"`` — True iff ``sentinel_value is not None``.
      * ``"== null"`` — True iff ``sentinel_value is None``.
      * ``"non_empty_array"`` — True iff ``sentinel_value`` is a
        list with len > 0.
      * ``"non_empty_string"`` — True iff ``sentinel_value`` is a
        str with len > 0 after strip.

    Returns ``(passed, error)``. ``error`` is an explanation string
    when the predicate itself is malformed or the value type is
    incompatible; it's ``None`` on successful evaluation.
    """

    if not isinstance(predicate, str):
        return False, f"predicate not a string: {predicate!r}"
    predicate = predicate.strip()

    if predicate == "non_empty_array":
        return bool(
            isinstance(sentinel_value, list) and len(sentinel_value) > 0
        ), None
    if predicate == "non_empty_string":
        return bool(
            isinstance(sentinel_value, str)
            and len(sentinel_value.strip()) > 0
        ), None

    # Comparison predicates.
    # Order matters: check 2-char operators before 1-char operators so
    # we don't mis-match ``>=`` as ``>``.
    for op in ("!=", "==", ">=", "<=", ">", "<"):
        if predicate.startswith(op):
            rhs_str = predicate[len(op):].strip()
            # Special-case null.
            if rhs_str == "null":
                if op == "==":
                    return sentinel_value is None, None
                if op == "!=":
                    return sentinel_value is not None, None
                return False, (
                    f"predicate {predicate!r}: only ==/!= supported with null"
                )
            # Special-case boolean literals for == / !=.
            if rhs_str.lower() in {"true", "false"} and op in {"==", "!="}:
                rhs_bool = rhs_str.lower() == "true"
                # Coerce obvious string representations.
                if isinstance(sentinel_value, bool):
                    lhs_bool = sentinel_value
                elif isinstance(sentinel_value, str) and sentinel_value.lower() in {
                    "true",
                    "false",
                }:
                    lhs_bool = sentinel_value.lower() == "true"
                else:
                    return False, (
                        f"predicate {predicate!r}: value {sentinel_value!r} "
                        f"(type {type(sentinel_value).__name__}) is not a boolean"
                    )
                if op == "==":
                    return lhs_bool == rhs_bool, None
                return lhs_bool != rhs_bool, None
            # Try numeric comparison first — but exclude booleans (Python
            # treats True/False as int 1/0; we already handled those above).
            rhs_num: Optional[float] = None
            try:
                rhs_num = float(rhs_str)
            except ValueError:
                rhs_num = None
            if (
                rhs_num is not None
                and isinstance(sentinel_value, (int, float))
                and not isinstance(sentinel_value, bool)
            ):
                lhs = float(sentinel_value)
                if op == ">":
                    return lhs > rhs_num, None
                if op == "<":
                    return lhs < rhs_num, None
                if op == ">=":
                    return lhs >= rhs_num, None
                if op == "<=":
                    return lhs <= rhs_num, None
                if op == "==":
                    return lhs == rhs_num, None
                if op == "!=":
                    return lhs != rhs_num, None
            # String comparison fallback (==/!= only).
            lhs_str = str(sentinel_value) if sentinel_value is not None else ""
            # Strip surrounding quotes from rhs (JSON-ish convention).
            rhs_clean = rhs_str.strip("\"'")
            if op == "==":
                return lhs_str == rhs_clean, None
            if op == "!=":
                return lhs_str != rhs_clean, None
            return False, (
                f"predicate {predicate!r}: non-numeric ordering not supported "
                f"for observed value type {type(sentinel_value).__name__}"
            )
    return False, f"unsupported predicate syntax: {predicate!r}"


def extract_sentinel_value(
    payload: Any, sentinel_field: str
) -> Tuple[Any, Optional[str]]:
    """Extract a dot-path field from a JSON payload.

    Example: ``extract_sentinel_value({"data": {"ok": True}}, "data.ok")
    → (True, None)``. Returns ``(None, error)`` when the path is invalid.

    Empty / None ``sentinel_field`` returns ``(payload, None)`` (the
    top-level payload itself is the sentinel).
    """

    if not sentinel_field:
        return payload, None
    parts = sentinel_field.split(".")
    current: Any = payload
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return None, (
                    f"sentinel path {sentinel_field!r}: key {part!r} not found"
                )
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                return None, (
                    f"sentinel path {sentinel_field!r}: non-integer index "
                    f"{part!r} on list"
                )
            if idx < 0 or idx >= len(current):
                return None, (
                    f"sentinel path {sentinel_field!r}: index {idx} out of "
                    f"range (list len {len(current)})"
                )
            current = current[idx]
        else:
            return None, (
                f"sentinel path {sentinel_field!r}: cannot descend past "
                f"{type(current).__name__}"
            )
    return current, None


# --- HTTP probe -------------------------------------------------------


@dataclass
class ProbeResult:
    endpoint: str
    axis: str
    passed: bool
    observed: Dict[str, Any] = field(default_factory=dict)
    attempt_count: int = 0
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "axis": self.axis,
            "pass": self.passed,
            "observed": self.observed,
            "attempt_count": self.attempt_count,
            "duration_s": round(self.duration_s, 4),
        }


def _http_get_once(url: str, timeout_s: int) -> Tuple[
    Optional[int], Any, Optional[str]
]:
    """GET ``url`` once; return ``(status, parsed_json_or_text, error)``.

    When the body isn't valid JSON, returns ``(status, raw_text, None)``.
    ``error`` is None on a successful HTTP round-trip (even for 5xx
    status codes) — HTTP status is reported via ``status``. ``error``
    is non-None only for connection / DNS / timeout failures.
    """

    req = urllib.request.Request(url, headers={"User-Agent": "si-chip/health-smoke"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        # Server returned non-2xx; still a valid round-trip for our purposes.
        raw = exc.read() if hasattr(exc, "read") else b""
        status = exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - decode() won't raise with 'replace'
        return status, None, f"decode error: {exc}"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = text
    return status, parsed, None


def probe_check(check: Dict[str, Any], timeout_s: int = 30) -> ProbeResult:
    """Execute one §21.1 health-smoke-check entry with retries.

    Iterates up to ``max_attempts`` times, sleeping ``retry_delay_ms``
    between attempts. An attempt is SUCCESSFUL when both:
      * HTTP status == ``expected_status``, AND
      * sentinel predicate evaluates True against the extracted
        sentinel value.

    On success the result is returned immediately; on failure we try
    again (up to ``max_attempts``). Final result carries the LAST
    attempt's ``observed`` payload regardless of pass/fail.

    Returns a ``ProbeResult`` dataclass (JSON-serializable via
    ``.to_dict()``).
    """

    endpoint = check.get("endpoint")
    axis = check.get("axis", "read")
    expected_status = int(check.get("expected_status", 200))
    max_attempts = max(1, int(check.get("max_attempts", 3)))
    retry_delay_ms = max(0, int(check.get("retry_delay_ms", 1000)))
    sentinel_field = check.get("sentinel_field", "")
    predicate = check.get("sentinel_value_predicate", "")

    if not isinstance(endpoint, str) or not endpoint:
        return ProbeResult(
            endpoint=str(endpoint),
            axis=str(axis),
            passed=False,
            observed={"error": "endpoint missing or not a string"},
            attempt_count=0,
            duration_s=0.0,
        )
    if axis not in VALID_AXES:
        return ProbeResult(
            endpoint=endpoint,
            axis=str(axis),
            passed=False,
            observed={"error": f"axis {axis!r} not in {list(VALID_AXES)}"},
            attempt_count=0,
            duration_s=0.0,
        )

    result = ProbeResult(endpoint=endpoint, axis=axis, passed=False)
    t0 = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        status, parsed, http_error = _http_get_once(endpoint, timeout_s)
        result.attempt_count = attempt
        observed: Dict[str, Any] = {"status": status}
        if http_error is not None:
            observed["error"] = http_error
            result.observed = observed
            if attempt < max_attempts:
                time.sleep(retry_delay_ms / 1000.0)
                continue
            break
        if status != expected_status:
            observed["error"] = (
                f"status {status} != expected_status {expected_status}"
            )
            result.observed = observed
            if attempt < max_attempts:
                time.sleep(retry_delay_ms / 1000.0)
                continue
            break
        sentinel_val, sentinel_err = extract_sentinel_value(
            parsed, sentinel_field or ""
        )
        observed["sentinel_value"] = sentinel_val
        if sentinel_err is not None:
            observed["error"] = sentinel_err
            result.observed = observed
            if attempt < max_attempts:
                time.sleep(retry_delay_ms / 1000.0)
                continue
            break
        pred_ok, pred_err = evaluate_predicate(sentinel_val, predicate)
        observed["predicate_passed"] = pred_ok
        if pred_err is not None:
            observed["error"] = pred_err
        if pred_ok:
            result.passed = True
            result.observed = observed
            break
        if not pred_ok:
            observed.setdefault(
                "error",
                f"predicate {predicate!r} returned False for value "
                f"{sentinel_val!r}",
            )
        result.observed = observed
        if attempt < max_attempts:
            time.sleep(retry_delay_ms / 1000.0)
    result.duration_s = time.perf_counter() - t0
    return result


# --- Profile-driven batch mode ----------------------------------------


def load_health_smoke_from_profile(
    profile_path: Path,
) -> List[Dict[str, Any]]:
    """Return ``packaging.health_smoke_check`` array from a BAP file.

    Raises ``RuntimeError`` when the file is missing / unparseable /
    shape-invalid (workspace rule "No Silent Failures"). Returns an
    empty list when the profile declares no health_smoke_check array
    (typical for abilities without live backend dependencies).
    """

    profile_path = Path(profile_path)
    if not profile_path.exists():
        raise RuntimeError(f"profile not found: {profile_path}")
    try:
        data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"profile {profile_path}: YAML parse error: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(
            f"profile {profile_path}: top level must be a mapping"
        )
    bap = data.get("basic_ability") or {}
    packaging = bap.get("packaging") if isinstance(bap, dict) else None
    if not isinstance(packaging, dict):
        return []
    smoke = packaging.get("health_smoke_check")
    if smoke is None:
        return []
    if not isinstance(smoke, list):
        raise RuntimeError(
            f"profile {profile_path}: packaging.health_smoke_check must be a list, "
            f"got {type(smoke).__name__}"
        )
    return smoke


def run_all_checks(
    checks: List[Dict[str, Any]], timeout_s: int = 30
) -> Dict[str, Any]:
    """Run every check sequentially; aggregate per_axis summary.

    Returns the output JSON shape documented in the module docstring.
    """

    per_check: List[Dict[str, Any]] = []
    per_axis: Dict[str, Dict[str, Any]] = {
        axis: {"total": 0, "passed": 0, "checks": []}
        for axis in VALID_AXES
    }
    passed_total = 0
    for check in checks:
        result = probe_check(check, timeout_s=timeout_s)
        entry = result.to_dict()
        per_check.append(entry)
        axis = result.axis if result.axis in VALID_AXES else "read"
        per_axis[axis]["total"] += 1
        per_axis[axis]["checks"].append(entry)
        if result.passed:
            per_axis[axis]["passed"] += 1
            passed_total += 1
    return {
        "checks_total": len(checks),
        "checks_passed": passed_total,
        "per_axis": per_axis,
        "per_check": per_check,
    }


# --- CLI --------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="health_smoke",
        description=(
            "Si-Chip health smoke check runner (spec v0.4.0-rc1 §21.4). "
            "Probes each packaging.health_smoke_check entry and verifies "
            "expected_status + sentinel_value_predicate. Exits 0 on all "
            "PASS, 1 on any FAIL, 2 on profile read error."
        ),
    )
    parser.add_argument(
        "--profile",
        default=None,
        help=(
            "Path to a BasicAbilityProfile YAML. When supplied, the "
            "script loads `packaging.health_smoke_check` from this "
            "profile and probes every entry."
        ),
    )
    parser.add_argument(
        "--check",
        default=None,
        help=(
            "JSON-encoded single check dict (alternative to --profile; "
            "used by tools/eval_skill.run_health_smoke_check for "
            "per-entry dispatch)."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-request HTTP timeout in seconds (default 30).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the aggregated JSON report on stdout.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set log level to INFO.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.check is None and args.profile is None:
        parser.error("either --profile or --check must be supplied")

    checks: List[Dict[str, Any]] = []
    profile_path: Optional[Path] = None

    if args.check is not None:
        try:
            single = json.loads(args.check)
        except json.JSONDecodeError as exc:
            print(
                json.dumps(
                    {
                        "error": f"--check JSON parse error: {exc}",
                        "checks_total": 0,
                        "checks_passed": 0,
                    }
                )
            )
            return 2
        if not isinstance(single, dict):
            print(
                json.dumps(
                    {
                        "error": f"--check must encode a dict, got {type(single).__name__}",
                        "checks_total": 0,
                        "checks_passed": 0,
                    }
                )
            )
            return 2
        checks = [single]
    else:
        profile_path = Path(args.profile).resolve()
        try:
            checks = load_health_smoke_from_profile(profile_path)
        except RuntimeError as exc:
            LOGGER.error("profile read failed: %s", exc)
            payload = {
                "error": str(exc),
                "profile_path": str(profile_path),
                "checks_total": 0,
                "checks_passed": 0,
            }
            if args.json:
                print(json.dumps(payload))
            else:
                print(f"ERROR: {exc}")
            return 2

    if not checks:
        # Empty health_smoke_check → PASS (no live backend to probe).
        result = {
            "profile_path": str(profile_path) if profile_path else None,
            "checks_total": 0,
            "checks_passed": 0,
            "per_axis": {
                axis: {"total": 0, "passed": 0, "checks": []}
                for axis in VALID_AXES
            },
            "per_check": [],
        }
        if args.json:
            print(json.dumps(result))
        else:
            print("health_smoke: no checks declared; PASS (no live backend)")
        return 0

    agg = run_all_checks(checks, timeout_s=args.timeout)
    report: Dict[str, Any] = {
        "profile_path": str(profile_path) if profile_path else None,
        **agg,
    }
    if args.json:
        print(json.dumps(report))
    else:
        print(
            f"health_smoke: {report['checks_passed']}/{report['checks_total']} "
            "checks PASSED"
        )
        for entry in report["per_check"]:
            flag = "PASS" if entry["pass"] else "FAIL"
            print(
                f"  [{flag}] {entry['axis']}: {entry['endpoint']} "
                f"({entry['attempt_count']} attempt(s); "
                f"{entry['duration_s']:.3f}s)"
            )
            if not entry["pass"]:
                err = entry["observed"].get("error")
                if err:
                    print(f"      error: {err}")

    if report["checks_passed"] == report["checks_total"]:
        return 0
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.health_smoke").error("fatal: %s", exc)
        raise
