#!/usr/bin/env python3
"""Unit tests for ``tools/multi_handler_redundant_call.py``.

Covers default glob enumeration, redundancy-free baseline, redundancy
detection, worst-case aggregation across handlers, and full CLI JSON
output schema.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.multi_handler_redundant_call import (  # noqa: E402
    DEFAULT_HANDLER_GLOBS,
    AggregateReport,
    HandlerAnalysis,
    _expand_braces,
    analyze_all,
    analyze_handler_file,
    analyze_handler_text,
    enumerate_handlers,
    main,
)

HANDLER_SCRIPT = REPO_ROOT / "tools" / "multi_handler_redundant_call.py"


def test_expand_braces():
    assert _expand_braces("**/*.js") == ["**/*.js"]
    expanded = _expand_braces("**/*handler*.{js,ts,py}")
    assert sorted(expanded) == sorted(
        ["**/*handler*.js", "**/*handler*.ts", "**/*handler*.py"]
    )


def test_enumerate_handlers_default_glob(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "get-dashboard-handler.ts").write_text("// handler a")
    (tmp_path / "tools" / "get-rankings-handler.ts").write_text("// handler b")
    (tmp_path / "commands" / "nested").mkdir(parents=True)
    (tmp_path / "commands" / "nested" / "deploy-command.py").write_text("# handler c")
    (tmp_path / "README.md").write_text("# not a handler")
    (tmp_path / "random_file.ts").write_text("// not matching default glob")

    handlers = enumerate_handlers(tmp_path)
    names = sorted(p.name for p in handlers)
    assert names == [
        "deploy-command.py",
        "get-dashboard-handler.ts",
        "get-rankings-handler.ts",
    ]


def test_enumerate_handlers_custom_brace_glob(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.js").write_text("// one")
    (tmp_path / "src" / "b.ts").write_text("// two")
    (tmp_path / "src" / "c.py").write_text("# three")
    (tmp_path / "src" / "d.md").write_text("# not matching")

    handlers = enumerate_handlers(
        tmp_path, handler_globs=["**/*.{js,ts,py}"]
    )
    names = sorted(p.name for p in handlers)
    assert names == ["a.js", "b.ts", "c.py"]


def test_enumerate_handlers_missing_source_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        enumerate_handlers(tmp_path / "does-not-exist")


def test_static_analysis_no_redundancy(tmp_path):
    # Body of 5 unique calls; no function wrapper to avoid counting the
    # declaration's own name as an extra call.
    handler = tmp_path / "handler.ts"
    handler.write_text(
        """
          const user = await fetchUser();
          const team = await fetchTeam();
          const bills = await fetchBills();
          const report = formatReport(user, team, bills);
          writeResponse(report);
        """
    )
    analysis = analyze_handler_file(handler, source_dir=tmp_path)
    assert analysis.calls_total == 5
    assert analysis.calls_unique == 5
    assert analysis.redundant_call_ratio == 0.0
    assert analysis.examples == []


def test_static_analysis_with_redundancy(tmp_path):
    # 4 total calls (foo + bar each twice); no function wrapper.
    handler = tmp_path / "handler.ts"
    handler.write_text(
        """
          const a = foo();
          const b = bar();
          const c = foo();
          const d = bar();
        """
    )
    analysis = analyze_handler_file(handler, source_dir=tmp_path)
    assert analysis.calls_total == 4
    assert analysis.calls_unique == 2
    assert analysis.redundant_call_ratio == 0.5
    assert any(e.startswith("foo") for e in analysis.examples)
    assert any(e.startswith("bar") for e in analysis.examples)


def test_analyze_handler_text_zero_calls():
    analysis = analyze_handler_text("empty.ts", "// comment only")
    assert analysis.calls_total == 0
    assert analysis.calls_unique == 0
    assert analysis.redundant_call_ratio == 0.0


def test_analyze_handler_filters_keywords(tmp_path):
    # if/for/while are language keywords; only the user-defined calls
    # (ready, running, doWork) should count. No function wrapper.
    handler = tmp_path / "handler.ts"
    handler.write_text(
        """
          if (ready()) {
            for (let i = 0; i < 10; i++) {
              while (running()) {
                doWork();
              }
            }
          }
        """
    )
    analysis = analyze_handler_file(handler, source_dir=tmp_path)
    assert analysis.calls_total == 3
    assert analysis.calls_unique == 3


def test_worst_case_picks_max_across_handlers(tmp_path):
    # Handler bodies only; no function wrappers (so the wrapper's own
    # name doesn't leak into the call count).
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "clean-handler.ts").write_text(
        """
          foo();
          bar();
          baz();
        """
    )
    (tmp_path / "tools" / "dup-handler.ts").write_text(
        """
          foo();
          bar();
          foo();
          bar();
        """
    )
    report = analyze_all(tmp_path)
    assert isinstance(report, AggregateReport)
    assert len(report.handlers_analyzed) == 2
    assert report.worst_case_redundant_call_ratio == 0.5
    assert report.ability_l4 == 0.5
    assert report.worst_case_handler is not None
    assert "dup-handler" in report.worst_case_handler


def test_analyze_all_with_no_handlers(tmp_path):
    report = analyze_all(tmp_path)
    assert report.handlers_analyzed == []
    assert report.per_handler == {}
    assert report.worst_case_handler is None
    assert report.ability_l4 == 0.0


def test_analyze_all_missing_source_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyze_all(tmp_path / "does-not-exist")


def test_cli_json_output_schema(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "a-handler.ts").write_text("foo();")
    (tmp_path / "tools" / "b-handler.ts").write_text(
        """
          redundant();
          redundant();
          redundant();
        """
    )
    result = subprocess.run(
        [
            sys.executable,
            str(HANDLER_SCRIPT),
            "--source-dir",
            str(tmp_path),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert set(payload.keys()) >= {
        "handlers_analyzed",
        "per_handler",
        "worst_case_handler",
        "worst_case_redundant_call_ratio",
        "ability_l4",
    }
    assert len(payload["handlers_analyzed"]) == 2
    assert payload["ability_l4"] > 0
    assert payload["worst_case_handler"] is not None
    assert "b-handler" in payload["worst_case_handler"]


def test_cli_help():
    result = subprocess.run(
        [sys.executable, str(HANDLER_SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--source-dir" in result.stdout
    assert "--handler-glob" in result.stdout


def test_default_handler_globs_triple():
    assert DEFAULT_HANDLER_GLOBS == [
        "**/*handler*.*",
        "**/*tool*.*",
        "**/*command*.*",
    ]


def test_handler_analysis_dataclass_roundtrip():
    analysis = HandlerAnalysis(
        path="tools/foo-handler.ts",
        calls_total=4,
        calls_unique=2,
        redundant_call_ratio=0.5,
        examples=["foox2", "barx2"],
    )
    d = analysis.to_dict()
    assert d["path"] == "tools/foo-handler.ts"
    assert d["redundant_call_ratio"] == 0.5
