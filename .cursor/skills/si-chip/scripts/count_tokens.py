#!/usr/bin/env python3
"""Deterministic token counter for SKILL.md frontmatter and body.

Implements spec §3.2 (C1 metadata_tokens / C2 body_tokens) and §7.3
packaging gate budget enforcement (`metadata_tokens ≤ 100`,
`body_tokens ≤ 5000`) of `.local/research/spec_v0.1.0.md`.

Two backends:

* ``tiktoken`` when importable: ``encoding_for_model("gpt-4o")`` with
  fallback to ``get_encoding("cl100k_base")``.  Cursor and Claude Code
  use Anthropic-family tokenizers; ``cl100k_base`` is a pragmatic,
  deterministic stand-in until the runtime tokenizer is wired (DESIGN.md
  §5).
* Stdlib fallback: split on any whitespace **or** any single
  non-alphanumeric character, drop empties, count surviving units.  This
  approximates BPE token counts within ~30% on prose, which is enough to
  keep the §7.3 gate honest when ``tiktoken`` is unavailable.

CLI::

    python scripts/count_tokens.py --file PATH \\
        [--metadata-only|--body-only|--both] \\
        [--budget-meta 100] [--budget-body 5000] [--json]

Exit code is 0 when both observed token counts are within their
respective budgets, else 1 (workspace rule "No Silent Failures").
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

LOGGER = logging.getLogger("si_chip.count_tokens")

SCRIPT_VERSION = "0.1.0"

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<meta>.*?)\n---\s*\n?(?P<body>.*)\Z",
    re.DOTALL,
)


def split_frontmatter(text: str) -> Tuple[str, str]:
    """Split a markdown file into (frontmatter, body).

    Returns ``("", text)`` when there is no leading ``---`` block.

    >>> split_frontmatter("---\\nname: x\\n---\\nbody here")
    ('name: x', 'body here')
    >>> split_frontmatter("no frontmatter here")
    ('', 'no frontmatter here')
    """

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group("meta").strip("\n"), m.group("body")


def _fallback_count(text: str) -> int:
    """Stdlib-only deterministic token count.

    Splits on whitespace and any single non-alphanumeric character,
    drops empty units.

    >>> _fallback_count("hello, world!  ok")
    3
    >>> _fallback_count("")
    0
    """

    if not text:
        return 0
    units = re.split(r"[\s\W_]+", text, flags=re.UNICODE)
    return sum(1 for u in units if u)


def _tiktoken_count(text: str, _cache: dict = {}) -> Optional[int]:
    """Return tiktoken count for ``text`` or ``None`` when unavailable."""

    if "enc" not in _cache:
        try:
            import tiktoken
        except ImportError:
            _cache["enc"] = None
            return None
        try:
            _cache["enc"] = tiktoken.encoding_for_model("gpt-4o")
        except Exception:
            try:
                _cache["enc"] = tiktoken.get_encoding("cl100k_base")
            except Exception as exc:
                LOGGER.warning("tiktoken init failed (%s); falling back", exc)
                _cache["enc"] = None
                return None
    enc = _cache["enc"]
    if enc is None:
        return None
    return len(enc.encode(text))


def count_tokens(text: str) -> Tuple[int, str]:
    """Count tokens in ``text``; return ``(count, backend)``.

    >>> n, backend = count_tokens("hello world")
    >>> n > 0 and backend in {"tiktoken", "fallback"}
    True
    """

    n = _tiktoken_count(text)
    if n is None:
        return _fallback_count(text), "fallback"
    return n, "tiktoken"


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count metadata/body tokens in a SKILL.md or any text file.",
    )
    parser.add_argument("--file", required=True, help="Path to the file to count.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--metadata-only", action="store_true", help="Count only the YAML frontmatter.")
    scope.add_argument("--body-only", action="store_true", help="Count only the body (after frontmatter).")
    scope.add_argument("--both", action="store_true", help="Count both (default).")
    parser.add_argument("--budget-meta", type=int, default=100, help="Frontmatter budget (default: 100).")
    parser.add_argument("--budget-body", type=int, default=5000, help="Body budget (default: 5000).")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    parser.add_argument("--verbose", action="store_true", help="Set log level to INFO.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    path = Path(args.file)
    if not path.exists():
        LOGGER.error("file not found: %s", path)
        return 1
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        LOGGER.error("failed to read %s: %s", path, exc)
        return 1

    meta_text, body_text = split_frontmatter(text)
    backend = "fallback"
    meta_count = 0
    body_count = 0

    want_meta = args.metadata_only or args.both or not (args.body_only)
    want_body = args.body_only or args.both or not (args.metadata_only)
    if not (args.metadata_only or args.body_only or args.both):
        want_meta = want_body = True

    if want_meta:
        meta_count, backend = count_tokens(meta_text)
    if want_body:
        body_count, backend = count_tokens(body_text)

    meta_ok = (not want_meta) or (meta_count <= args.budget_meta)
    body_ok = (not want_body) or (body_count <= args.budget_body)
    passed = meta_ok and body_ok

    if args.json:
        payload = {
            "metadata_tokens": meta_count if want_meta else None,
            "body_tokens": body_count if want_body else None,
            "budget_meta": args.budget_meta,
            "budget_body": args.budget_body,
            "pass": passed,
            "backend": backend,
            "script_version": SCRIPT_VERSION,
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if want_meta:
            print(f"metadata_tokens={meta_count}")
        if want_body:
            print(f"body_tokens={body_count}")
        print(f"verdict={'pass' if passed else 'fail'}")

    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.count_tokens").error("fatal: %s", exc)
        sys.exit(1)
