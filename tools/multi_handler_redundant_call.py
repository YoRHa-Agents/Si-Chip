#!/usr/bin/env python3
"""L4 multi-handler redundant-call analyzer for Si-Chip spec §3.1 D3.

Implements the reusable static analyzer required by R11 §8: walk **all**
ability entrypoints (MCP tools / CLI subcommands / multiple Skill
scripts) and compute per-handler ``redundant_call_ratio``, then hoist
the worst-case ratio into the ability's L4 metric. This fixes the
chip-usage-helper failure mode quoted in feedback_for_v0.2.0.md ("R5
只测了一个 handler 才在 R8 才发现 get-rankings 也有同样模式") —
any single redundancy hotspot anywhere in the ability surface is a
problem, so L4 is aggregated as ``max`` across handlers, not averaged.

CLI::

    python tools/multi_handler_redundant_call.py \\
        --source-dir <path/to/ability/source> \\
        [--handler-glob "**/*handler*.{js,ts,py}"] \\
        [--json]

``--handler-glob`` is repeatable; each pattern may include brace sets
(``{a,b,c}``) which this tool expands to ``a``/``b``/``c`` before
matching. When omitted, the default pattern set is
``**/*handler*.*``, ``**/*tool*.*``, ``**/*command*.*``.

Output JSON shape::

    {
      "handlers_analyzed": [<rel path>, ...],
      "per_handler": {
        "<rel path>": {
          "redundant_call_ratio": <float>,
          "calls_total": <int>,
          "calls_unique": <int>,
          "examples": [<call name with count>, ...]
        },
        ...
      },
      "worst_case_handler": "<rel path or null>",
      "worst_case_redundant_call_ratio": <float>,
      "ability_l4": <float>       # = worst_case_redundant_call_ratio
    }

Workspace-rule notes
--------------------
* "No Silent Failures": missing source dir / invalid glob raise (never
  zero-substitute). Handlers that fail to parse are logged at WARNING
  and yield a per-handler record with ``calls_total=0`` so the
  operator can see them; they do NOT get silently skipped.
* "Mandatory Verification": sibling test
  ``tools/test_multi_handler_redundant_call.py`` covers default glob
  enumeration, redundancy-free baseline, redundancy detection,
  worst-case aggregation, and full CLI JSON schema.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

LOGGER = logging.getLogger("si_chip.multi_handler_redundant_call")

SCRIPT_VERSION = "0.1.0"

DEFAULT_HANDLER_GLOBS: List[str] = [
    "**/*handler*.*",
    "**/*tool*.*",
    "**/*command*.*",
]

# A callable token for the redundancy scan. We require at least one
# letter before ``(`` to avoid matching punctuation like ``if (`` or
# ``while (``. Keywords are filtered out post-hoc (see ``_CALL_KEYWORDS``).
_CALL_RE = re.compile(r"(?P<call>[A-Za-z_][A-Za-z0-9_\.]*)\s*\(")

# Tokens that look like calls but are language keywords; filter them
# before counting redundancy so ``if (x)``, ``for (let i)``, etc. don't
# inflate the denominator.
_CALL_KEYWORDS = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "return",
        "typeof",
        "instanceof",
        "new",
        "throw",
        "await",
        "yield",
        "function",
        "async",
        "void",
        "sizeof",
        "assert",
        "elif",
        "print",
        "range",
        "int",
        "str",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "len",
        "super",
    }
)


@dataclass
class HandlerAnalysis:
    """Per-handler static analysis output."""

    path: str
    calls_total: int
    calls_unique: int
    redundant_call_ratio: float
    examples: List[str] = field(default_factory=list)
    parse_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AggregateReport:
    """Aggregate ability L4 across all handlers analysed."""

    handlers_analyzed: List[str]
    per_handler: Dict[str, Dict[str, Any]]
    worst_case_handler: Optional[str]
    worst_case_redundant_call_ratio: float
    ability_l4: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _expand_braces(pattern: str) -> List[str]:
    """Expand one level of ``{a,b,c}`` brace sets.

    ``**/*.{js,ts,py}`` → [``**/*.js``, ``**/*.ts``, ``**/*.py``].

    Only the first brace group is expanded (sufficient for the glob
    patterns the task spec defines). Nested braces are left as-is with
    a logged warning — the operator can pass multiple ``--handler-glob``
    arguments to cover more cases.
    """

    m = re.search(r"\{([^{}]+)\}", pattern)
    if not m:
        return [pattern]
    pieces = [p.strip() for p in m.group(1).split(",") if p.strip()]
    prefix = pattern[: m.start()]
    suffix = pattern[m.end():]
    expanded = [prefix + p + suffix for p in pieces]
    # Recurse for additional brace groups (rare; supports at most a few).
    out: List[str] = []
    for e in expanded:
        out.extend(_expand_braces(e))
    return out


def enumerate_handlers(
    source_dir: Path, handler_globs: Optional[Sequence[str]] = None
) -> List[Path]:
    """Return sorted list of handler files under ``source_dir``.

    ``handler_globs`` defaults to ``DEFAULT_HANDLER_GLOBS``. Each glob
    is brace-expanded then passed to ``Path.rglob``. Duplicate matches
    across globs are de-duplicated.
    """

    source_dir = Path(source_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"source dir not found: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"source path is not a directory: {source_dir}")

    patterns = list(handler_globs) if handler_globs else list(DEFAULT_HANDLER_GLOBS)
    expanded: List[str] = []
    for p in patterns:
        expanded.extend(_expand_braces(p))

    if not expanded:
        raise ValueError("handler_globs expanded to empty list")

    matches: set[Path] = set()
    for pat in expanded:
        # Path.rglob accepts glob patterns but not the leading "**/". Strip
        # the leading "**/" for rglob compatibility when present.
        rglob_pat = pat[3:] if pat.startswith("**/") else pat
        for path in source_dir.rglob(rglob_pat):
            if path.is_file():
                matches.add(path)

    return sorted(matches)


def _extract_calls(text: str) -> List[str]:
    """Extract callable tokens from ``text`` (language-agnostic).

    Returns a list of names (preserving order). Language keywords that
    look like calls are filtered out. The tokens are lowercase-normalised
    so ``Foo()`` and ``foo()`` are counted together (common in mixed-case
    codebases).
    """

    if not text:
        return []
    out: List[str] = []
    for m in _CALL_RE.finditer(text):
        name = m.group("call")
        # Short non-identifier or keyword → skip
        first_component = name.split(".", 1)[0].lower()
        if first_component in _CALL_KEYWORDS:
            continue
        if len(name) < 2:
            continue
        out.append(name.lower())
    return out


def analyze_handler_text(path_hint: str, text: str) -> HandlerAnalysis:
    """Run static redundancy analysis on an in-memory text body.

    Computed L4 follows spec §3.1 D3 L4 and
    ``eval_chip_usage_helper.py::_analyze_handler_file``::

        redundant_call_ratio = (calls_total - calls_unique) / calls_total

    For ``calls_total == 0`` the ratio is ``0.0`` (absence of calls is
    not itself a problem; the operator can see ``calls_total`` in the
    output and decide).
    """

    calls = _extract_calls(text)
    total = len(calls)
    counter = Counter(calls)
    unique = len(counter)
    if total == 0:
        ratio = 0.0
    else:
        ratio = (total - unique) / total
    examples = sorted(
        (f"{name}x{count}" for name, count in counter.items() if count > 1),
        key=lambda s: (-int(s.rsplit("x", 1)[1]), s),
    )
    return HandlerAnalysis(
        path=path_hint,
        calls_total=total,
        calls_unique=unique,
        redundant_call_ratio=round(ratio, 4),
        examples=examples[:10],
    )


def analyze_handler_file(
    path: Path, source_dir: Optional[Path] = None
) -> HandlerAnalysis:
    """Read ``path`` and analyse its body.

    Path reported in the result is relative to ``source_dir`` when
    supplied (for operator-friendly output); otherwise the absolute
    path is used.
    """

    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        LOGGER.warning("could not read handler %s: %s", path, exc)
        rel = str(path if source_dir is None else path.relative_to(source_dir))
        return HandlerAnalysis(
            path=rel,
            calls_total=0,
            calls_unique=0,
            redundant_call_ratio=0.0,
            examples=[],
            parse_error=str(exc),
        )
    rel_path = (
        str(path.relative_to(source_dir))
        if source_dir is not None
        else str(path)
    )
    analysis = analyze_handler_text(rel_path, text)
    return analysis


def analyze_all(
    source_dir: Path,
    handler_globs: Optional[Sequence[str]] = None,
) -> AggregateReport:
    """Walk handlers under ``source_dir`` and aggregate per-handler L4.

    Raises on invalid source dir; logs a warning and returns an empty
    report when no handlers are found (so the operator can see the
    mismatch rather than silently succeed).
    """

    source_dir = Path(source_dir).resolve()
    handlers = enumerate_handlers(source_dir, handler_globs)
    per_handler: Dict[str, Dict[str, Any]] = {}
    worst_handler: Optional[str] = None
    worst_ratio = 0.0
    for handler_path in handlers:
        analysis = analyze_handler_file(handler_path, source_dir=source_dir)
        per_handler[analysis.path] = analysis.to_dict()
        if analysis.redundant_call_ratio > worst_ratio:
            worst_ratio = analysis.redundant_call_ratio
            worst_handler = analysis.path

    if not handlers:
        LOGGER.warning(
            "no handlers matched under %s with globs=%s; L4 will default to 0.0",
            source_dir,
            list(handler_globs) if handler_globs else DEFAULT_HANDLER_GLOBS,
        )

    return AggregateReport(
        handlers_analyzed=[str(Path(p).relative_to(source_dir)) for p in handlers],
        per_handler=per_handler,
        worst_case_handler=worst_handler,
        worst_case_redundant_call_ratio=round(worst_ratio, 4),
        ability_l4=round(worst_ratio, 4),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="multi_handler_redundant_call",
        description=(
            "L4 redundant-call analyzer walking ALL handler files under an "
            "ability source tree (spec §3.1 D3 / R11 §8)."
        ),
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Path to the ability source tree to scan.",
    )
    parser.add_argument(
        "--handler-glob",
        action="append",
        default=None,
        help=(
            "Handler file glob (repeatable). Supports brace sets like "
            "'**/*handler*.{js,ts,py}'. Default: "
            "'**/*handler*.*', '**/*tool*.*', '**/*command*.*'"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit AggregateReport as JSON on stdout.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    source_dir = Path(args.source_dir)
    report = analyze_all(source_dir, args.handler_glob)

    payload = report.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Multi-Handler L4 Report (script v{SCRIPT_VERSION})")
        print(f"  source_dir       : {source_dir}")
        print(f"  handlers analysed: {len(report.handlers_analyzed)}")
        print(
            f"  worst handler    : {report.worst_case_handler} "
            f"(L4={report.worst_case_redundant_call_ratio:.4f})"
        )
        print(f"  ability_l4       : {report.ability_l4:.4f}")
        for path, info in report.per_handler.items():
            print(
                f"    - {path}: L4={info['redundant_call_ratio']:.4f} "
                f"(total={info['calls_total']}, unique={info['calls_unique']})"
            )
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    sys.exit(main())
