#!/usr/bin/env python3
"""Unit tests for ``tools/health_smoke.py`` (Si-Chip spec v0.4.0-rc1 §21.4).

Covers:
  * ``evaluate_predicate`` — all §21.1 predicate forms.
  * ``extract_sentinel_value`` — dot-path traversal.
  * ``probe_check`` — single-endpoint probe behavior (success,
    sentinel fail, predicate fail, timeout, retry).
  * ``load_health_smoke_from_profile`` — BAP file loading + error
    paths.
  * ``run_all_checks`` — per_axis aggregation.
  * CLI integration (``--help`` + empty-check-list PASS case).

All HTTP probing is tested against an in-process ``http.server`` on
localhost so no external network access is required (workspace rule
"No Silent Failures": we test real syscall paths, not mocks).

Run::

    python -m pytest tools/test_health_smoke.py -q
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import health_smoke as hs  # noqa: E402

HEALTH_SMOKE_SCRIPT = _REPO_ROOT / "tools" / "health_smoke.py"


# --- In-process HTTP server fixture -----------------------------------


class _FixtureHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that replays ``cls.routes[path]``.

    ``cls.routes`` maps URL path → (status, body_json_or_text). The
    handler honors explicit delay (``cls.delay_s``) to exercise
    retry/timeout paths.
    """

    routes: Dict[str, Tuple[int, Any]] = {}
    delay_s: float = 0.0
    # Count how many times a path was hit — useful for retry tests.
    hit_counts: Dict[str, int] = {}

    def do_GET(self) -> None:  # noqa: N802 (stdlib API)
        if self.delay_s > 0:
            time.sleep(self.delay_s)
        self.hit_counts[self.path] = self.hit_counts.get(self.path, 0) + 1
        route = self.routes.get(self.path)
        if route is None:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"not found")
            return
        status, body = route
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = (
            json.dumps(body).encode("utf-8")
            if not isinstance(body, (bytes, str))
            else (body.encode("utf-8") if isinstance(body, str) else body)
        )
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D401
        """Silence the stdlib handler's stderr logging."""


class _LocalServer:
    """Context manager wrapping a thread-hosted HTTPServer on 127.0.0.1."""

    def __init__(self, routes: Dict[str, Tuple[int, Any]], delay_s: float = 0.0):
        self.routes = routes
        self.delay_s = delay_s
        self.httpd: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.port: Optional[int] = None

    def __enter__(self) -> "_LocalServer":
        _FixtureHandler.routes = self.routes
        _FixtureHandler.delay_s = self.delay_s
        _FixtureHandler.hit_counts = {}
        self.httpd = HTTPServer(("127.0.0.1", 0), _FixtureHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(
            target=self.httpd.serve_forever, daemon=True
        )
        self.thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        assert self.httpd is not None
        self.httpd.shutdown()
        self.httpd.server_close()
        assert self.thread is not None
        self.thread.join(timeout=2)

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"


# --- evaluate_predicate ------------------------------------------------


class EvaluatePredicateTests(unittest.TestCase):
    """Exercise every §21.1 predicate form."""

    def test_gt_predicate_on_number(self) -> None:
        passed, err = hs.evaluate_predicate(5, ">0")
        self.assertTrue(passed)
        self.assertIsNone(err)

    def test_gt_predicate_fails_on_zero(self) -> None:
        passed, err = hs.evaluate_predicate(0, ">0")
        self.assertFalse(passed)
        self.assertIsNone(err)

    def test_le_predicate_on_bigint(self) -> None:
        passed, _ = hs.evaluate_predicate(1714464840000, ">= 1000000000000")
        self.assertTrue(passed)

    def test_eq_predicate_on_string(self) -> None:
        passed, _ = hs.evaluate_predicate("ok", "== ok")
        self.assertTrue(passed)
        passed, _ = hs.evaluate_predicate("notok", "== ok")
        self.assertFalse(passed)

    def test_non_empty_array_predicate(self) -> None:
        passed, _ = hs.evaluate_predicate([1, 2], "non_empty_array")
        self.assertTrue(passed)
        passed, _ = hs.evaluate_predicate([], "non_empty_array")
        self.assertFalse(passed)
        passed, _ = hs.evaluate_predicate("not a list", "non_empty_array")
        self.assertFalse(passed)

    def test_non_empty_string_predicate(self) -> None:
        passed, _ = hs.evaluate_predicate("hello", "non_empty_string")
        self.assertTrue(passed)
        passed, _ = hs.evaluate_predicate("   ", "non_empty_string")
        self.assertFalse(passed)
        passed, _ = hs.evaluate_predicate(None, "non_empty_string")
        self.assertFalse(passed)

    def test_ne_null_predicate(self) -> None:
        passed, _ = hs.evaluate_predicate("x", "!= null")
        self.assertTrue(passed)
        passed, _ = hs.evaluate_predicate(None, "!= null")
        self.assertFalse(passed)

    def test_eq_null_predicate(self) -> None:
        passed, _ = hs.evaluate_predicate(None, "== null")
        self.assertTrue(passed)

    def test_malformed_predicate_returns_error(self) -> None:
        passed, err = hs.evaluate_predicate(1, "banana")
        self.assertFalse(passed)
        self.assertIn("unsupported predicate", err or "")


# --- extract_sentinel_value -------------------------------------------


class ExtractSentinelValueTests(unittest.TestCase):

    def test_extracts_dot_path(self) -> None:
        val, err = hs.extract_sentinel_value(
            {"data": {"latestTsMs": 1714464840000}}, "data.latestTsMs"
        )
        self.assertEqual(val, 1714464840000)
        self.assertIsNone(err)

    def test_extracts_list_index(self) -> None:
        val, err = hs.extract_sentinel_value(
            {"data": {"leaderboard": [{"name": "a"}, {"name": "b"}]}},
            "data.leaderboard.0.name",
        )
        self.assertEqual(val, "a")
        self.assertIsNone(err)

    def test_empty_field_returns_whole_payload(self) -> None:
        val, err = hs.extract_sentinel_value({"foo": 1}, "")
        self.assertEqual(val, {"foo": 1})
        self.assertIsNone(err)

    def test_missing_key_returns_error(self) -> None:
        val, err = hs.extract_sentinel_value({"foo": 1}, "bar")
        self.assertIsNone(val)
        self.assertIn("bar", err or "")

    def test_cannot_descend_past_primitive(self) -> None:
        val, err = hs.extract_sentinel_value(42, "foo")
        self.assertIsNone(val)
        self.assertIn("descend past", err or "")


# --- probe_check (live HTTP) ------------------------------------------


class ProbeCheckTests(unittest.TestCase):
    """End-to-end HTTP probes using the in-process server fixture."""

    def test_probe_pass_when_status_and_predicate_match(self) -> None:
        with _LocalServer(
            routes={
                "/api/health": (200, {"data": {"ok": True, "latestTsMs": 1714464840000}})
            }
        ) as server:
            check = {
                "endpoint": server.url("/api/health"),
                "expected_status": 200,
                "max_attempts": 1,
                "retry_delay_ms": 0,
                "sentinel_field": "data.latestTsMs",
                "sentinel_value_predicate": ">0",
                "axis": "dependency",
                "description": "ok",
            }
            result = hs.probe_check(check, timeout_s=5)
            self.assertTrue(result.passed, msg=result.observed)
            self.assertEqual(result.attempt_count, 1)
            self.assertEqual(result.axis, "dependency")
            self.assertEqual(
                result.observed["sentinel_value"], 1714464840000
            )

    def test_probe_fails_on_status_mismatch(self) -> None:
        with _LocalServer(
            routes={"/api/missing": (404, {"error": "nope"})}
        ) as server:
            check = {
                "endpoint": server.url("/api/missing"),
                "expected_status": 200,
                "max_attempts": 1,
                "retry_delay_ms": 0,
                "sentinel_field": "error",
                "sentinel_value_predicate": "!= null",
                "axis": "read",
                "description": "expected 200",
            }
            result = hs.probe_check(check, timeout_s=5)
            self.assertFalse(result.passed)
            self.assertIn("status 404", result.observed["error"])

    def test_probe_fails_when_sentinel_predicate_false(self) -> None:
        """Sentinel extracted but predicate returns False → FAIL."""

        with _LocalServer(
            routes={
                "/api/events": (200, {"data": {"latestTsMs": 0, "eventCount": 0}})
            }
        ) as server:
            check = {
                "endpoint": server.url("/api/events"),
                "expected_status": 200,
                "max_attempts": 1,
                "retry_delay_ms": 0,
                "sentinel_field": "data.latestTsMs",
                "sentinel_value_predicate": ">0",
                "axis": "dependency",
                "description": "zero events replay",
            }
            result = hs.probe_check(check, timeout_s=5)
            self.assertFalse(result.passed)
            self.assertEqual(result.observed["sentinel_value"], 0)
            self.assertFalse(result.observed["predicate_passed"])

    def test_probe_retries_until_pass(self) -> None:
        """With max_attempts=3 and second-hit-pass fixture → result passes."""

        # A stateful handler that returns 503 on first hit, 200 on second.
        state = {"hits": 0}

        class _FlakyHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                state["hits"] += 1
                if state["hits"] < 2:
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":"warming"}')
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"data":{"ok":true}}')

            def log_message(self, fmt: str, *args: Any) -> None:
                return

        httpd = HTTPServer(("127.0.0.1", 0), _FlakyHandler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            check = {
                "endpoint": f"http://127.0.0.1:{port}/api/flaky",
                "expected_status": 200,
                "max_attempts": 3,
                "retry_delay_ms": 10,
                "sentinel_field": "data.ok",
                "sentinel_value_predicate": "== true",
                "axis": "read",
                "description": "flaky",
            }
            result = hs.probe_check(check, timeout_s=5)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
        self.assertTrue(result.passed, msg=result.observed)
        self.assertEqual(result.attempt_count, 2)

    def test_probe_timeout_returns_error(self) -> None:
        """Unreachable endpoint → network error captured, pass=False."""

        check = {
            "endpoint": "http://127.0.0.1:1/unreachable",
            "expected_status": 200,
            "max_attempts": 1,
            "retry_delay_ms": 0,
            "sentinel_field": "",
            "sentinel_value_predicate": "!= null",
            "axis": "read",
            "description": "unreachable",
        }
        result = hs.probe_check(check, timeout_s=1)
        self.assertFalse(result.passed)
        self.assertIn("error", result.observed)

    def test_probe_rejects_bad_axis(self) -> None:
        """axis not in {read,write,auth,dependency} → early FAIL."""

        check = {
            "endpoint": "http://127.0.0.1:1/x",
            "expected_status": 200,
            "max_attempts": 1,
            "retry_delay_ms": 0,
            "sentinel_field": "",
            "sentinel_value_predicate": "!= null",
            "axis": "bogus_axis",
            "description": "bad axis",
        }
        result = hs.probe_check(check, timeout_s=1)
        self.assertFalse(result.passed)
        self.assertIn("bogus_axis", result.observed["error"])


# --- load_health_smoke_from_profile -----------------------------------


class LoadProfileTests(unittest.TestCase):

    def test_profile_not_found_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            hs.load_health_smoke_from_profile(
                Path("/nonexistent/profile.yaml")
            )

    def test_profile_with_missing_packaging_returns_empty(self, tmp_dir=None) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "profile.yaml"
            path.write_text(
                yaml.safe_dump(
                    {"basic_ability": {"id": "test", "current_surface": {}}}
                ),
                encoding="utf-8",
            )
            checks = hs.load_health_smoke_from_profile(path)
            self.assertEqual(checks, [])

    def test_profile_with_populated_smoke_returns_list(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "profile.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "basic_ability": {
                            "id": "test",
                            "packaging": {
                                "health_smoke_check": [
                                    {"endpoint": "https://a.com", "axis": "read"},
                                    {"endpoint": "https://b.com", "axis": "write"},
                                ]
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            checks = hs.load_health_smoke_from_profile(path)
            self.assertEqual(len(checks), 2)

    def test_profile_with_non_list_smoke_raises(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "profile.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "basic_ability": {
                            "packaging": {"health_smoke_check": "not a list"}
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                hs.load_health_smoke_from_profile(path)


# --- run_all_checks axis aggregation ----------------------------------


class RunAllChecksTests(unittest.TestCase):

    def test_per_axis_aggregation(self) -> None:
        """Checks are binned per axis; pass/total tracked."""

        with _LocalServer(
            routes={
                "/read_ok": (200, {"ok": True}),
                "/read_fail": (500, {"error": "boom"}),
                "/write_ok": (200, {"data": [1, 2]}),
            }
        ) as server:
            checks = [
                {
                    "endpoint": server.url("/read_ok"),
                    "expected_status": 200,
                    "max_attempts": 1,
                    "retry_delay_ms": 0,
                    "sentinel_field": "ok",
                    "sentinel_value_predicate": "== true",
                    "axis": "read",
                    "description": "r1",
                },
                {
                    "endpoint": server.url("/read_fail"),
                    "expected_status": 200,
                    "max_attempts": 1,
                    "retry_delay_ms": 0,
                    "sentinel_field": "error",
                    "sentinel_value_predicate": "!= null",
                    "axis": "read",
                    "description": "r2",
                },
                {
                    "endpoint": server.url("/write_ok"),
                    "expected_status": 200,
                    "max_attempts": 1,
                    "retry_delay_ms": 0,
                    "sentinel_field": "data",
                    "sentinel_value_predicate": "non_empty_array",
                    "axis": "write",
                    "description": "w1",
                },
            ]
            result = hs.run_all_checks(checks, timeout_s=5)
            self.assertEqual(result["checks_total"], 3)
            self.assertEqual(result["checks_passed"], 2)
            self.assertEqual(result["per_axis"]["read"]["total"], 2)
            self.assertEqual(result["per_axis"]["read"]["passed"], 1)
            self.assertEqual(result["per_axis"]["write"]["total"], 1)
            self.assertEqual(result["per_axis"]["write"]["passed"], 1)
            self.assertEqual(result["per_axis"]["auth"]["total"], 0)
            self.assertEqual(result["per_axis"]["dependency"]["total"], 0)


# --- CLI --------------------------------------------------------------


class CliTests(unittest.TestCase):

    def test_cli_help(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(HEALTH_SMOKE_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        for flag in ("--profile", "--check", "--timeout", "--json"):
            self.assertIn(flag, proc.stdout)

    def test_cli_empty_smoke_from_profile_exits_0(self) -> None:
        """Profile with no health_smoke_check → exit 0, JSON with 0 checks."""

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "profile.yaml"
            profile.write_text(
                yaml.safe_dump(
                    {"basic_ability": {"id": "test"}}
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(HEALTH_SMOKE_SCRIPT),
                    "--profile",
                    str(profile),
                    "--json",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertEqual(payload["checks_total"], 0)
            self.assertEqual(payload["checks_passed"], 0)

    def test_cli_profile_not_found_exits_2(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(HEALTH_SMOKE_SCRIPT),
                "--profile",
                "/nonexistent/profile.yaml",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)

    def test_cli_single_check_mode_via_json(self) -> None:
        """--check with JSON-encoded single check probes once and emits JSON."""

        with _LocalServer(routes={"/api/ok": (200, {"ok": True})}) as server:
            check = {
                "endpoint": server.url("/api/ok"),
                "expected_status": 200,
                "max_attempts": 1,
                "retry_delay_ms": 0,
                "sentinel_field": "ok",
                "sentinel_value_predicate": "== true",
                "axis": "read",
                "description": "ok",
            }
            proc = subprocess.run(
                [
                    sys.executable,
                    str(HEALTH_SMOKE_SCRIPT),
                    "--check",
                    json.dumps(check),
                    "--json",
                    "--timeout",
                    "5",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertEqual(payload["checks_total"], 1)
            self.assertEqual(payload["checks_passed"], 1)
            self.assertTrue(payload["per_check"][0]["pass"])

    def test_cli_single_check_fail_exits_1(self) -> None:
        """--check with a failing probe exits 1."""

        check = {
            "endpoint": "http://127.0.0.1:1/unreachable",
            "expected_status": 200,
            "max_attempts": 1,
            "retry_delay_ms": 0,
            "sentinel_field": "",
            "sentinel_value_predicate": "!= null",
            "axis": "read",
            "description": "unreachable",
        }
        proc = subprocess.run(
            [
                sys.executable,
                str(HEALTH_SMOKE_SCRIPT),
                "--check",
                json.dumps(check),
                "--json",
                "--timeout",
                "1",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
