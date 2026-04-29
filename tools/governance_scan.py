#!/usr/bin/env python3
"""Governance-risk scanner for Si-Chip Round 8 D7 V1-V4 fill.

Implements spec §3.1 D7 (``governance_risk`` dimension, 4 sub-metrics)
and spec §6 ``governance_risk_delta`` (formula ``risk_without - risk_with``
per the §6.1 7-axis value vector table). Produces a deterministic,
reproducible report consumed by
``.agents/skills/si-chip/scripts/aggregate_eval.py`` to hoist V1-V4 into
``metrics_report.yaml``.

Four sub-metrics (spec §3.1 D7):

* ``V1_permission_scope``  — count of filesystem paths that the skill
  writes to **outside** ``.local/dogfood/`` and outside the skill's own
  ``.agents/skills/si-chip/`` tree. For Si-Chip v0.1.7 this is ``0``
  (clean; all writes land under the caller-provided ``--out`` path which
  convention routes into ``.local/dogfood/<date>/round_<N>/``).
* ``V2_credential_surface`` — count of credential / secret patterns
  (AWS access key format, generic 40-char hex tokens, PEM private key
  markers, and assignment-style ``api_key = "..."`` literals) found in
  any skill artifact body. **MUST NOT log the secret value itself** —
  only the pattern name + the aggregate count per file.
* ``V3_drift_signal`` — ``1.0 - cross_tree_drift_zero_ratio`` across the
  three SKILL.md mirrors (``.agents`` canonical + ``.cursor`` + ``.claude``).
  All three byte-equal → ``V3 = 0.0``.
* ``V4_staleness_days`` — ``(today - last_reviewed_at).days`` from
  ``basic_ability_profile.lifecycle.last_reviewed_at`` (ISO date string).

§6 ``governance_risk_delta`` derivation
---------------------------------------
The §6.1 formula is ``risk_without - risk_with`` (D7). For the
deterministic simulator used by Si-Chip, the no-ability baseline does
not interact with the filesystem / credentials / mirror tree, so
``risk_without = 0`` always. ``risk_with`` is a monotone combination of
V1-V4 (see :func:`compute_governance_risk_delta`) — when V1-V4 are all
zero (the clean Si-Chip baseline), ``risk_with = 0.0`` and the delta
is also ``0.0``. The half_retire_decision.yaml consumes this **live**
from the scanner rather than hard-coding ``0.0`` (the Round 8 audit
closure).

CLI::

    python tools/governance_scan.py \
        --repo-root . \
        --basic-ability-profile .local/dogfood/2026-04-28/round_8/basic_ability_profile.yaml \
        --json

Outputs a single-line JSON payload with V1-V4 + provenance. ``--json``
is the shape consumed by ``aggregate_eval.py --governance-report``.

Workspace-rule notes
--------------------
* "No Silent Failures": missing files, malformed YAML, and malformed
  input dates all raise (never swallow). The credential scanner logs a
  warning with pattern name + file + count whenever a match fires, but
  never the matched value.
* "Mandatory Verification": sibling test ``tools/test_governance_scan.py``
  covers ≥ 15 unit tests across V1/V2/V3/V4 happy paths, degenerate
  paths, missing-input raises, and the MUST-NOT-log-secret invariant.
* Safety: V2 never emits the secret body in any LOG, return value, or
  serialised report field. Only pattern name + file path + per-file
  count are surfaced.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.governance_scan")

SCRIPT_VERSION = "0.1.0"

# ─────────────── V1 permission_scope ───────────────

# Python write-call primitives we scan for. The scanner extracts the
# FIRST positional / first string-literal argument as the candidate
# write path. Non-string args (variables / expressions) are reported as
# "unknown" but do NOT count toward V1 (variables are parameterised by
# the caller and land wherever the caller says — typically a
# ``--out`` path that tooling is expected to route into
# ``.local/dogfood/``).
_WRITE_OPEN_RE = re.compile(
    r"""\bopen\s*\(\s*["']([^"']+)["']\s*,\s*["']([wax]\+?b?|[wax]b?\+?)["']""",
    re.MULTILINE,
)
_WRITE_PATH_METHOD_RE = re.compile(
    r"""(?:Path\s*\(\s*["']([^"']+)["']\s*\))\s*\.\s*(?:write_text|write_bytes|mkdir|touch)""",
    re.MULTILINE,
)
_OS_MKDIR_RE = re.compile(
    r"""\b(?:os\.makedirs|os\.mkdir|pathlib\.Path\s*\(\s*["']([^"']+)["']\s*\)\.mkdir)""",
    re.MULTILINE,
)

# Shell-style write patterns (bash installers / scripts). Used for
# ``install.sh``-style scans when a Path is passed via ``skill_paths``
# that points at a shell file.
_SHELL_REDIRECT_RE = re.compile(
    r"""(?:^|\s)(?:>|>>)\s*["']?(/[^\s"';&|)]+)["']?""",
    re.MULTILINE,
)

# Default allow-list prefixes. V1 counts a write path as in-scope
# (i.e. does NOT contribute to the count) when it is under one of
# these prefixes. Relative paths (not starting with ``/``) are also
# treated as in-scope because they are caller-parameterised by
# convention (tests assert this explicitly — scope is the skill's
# hardcoded ABSOLUTE write surface).
DEFAULT_V1_ALLOWED_PREFIXES: Tuple[str, ...] = (
    ".local/dogfood/",
    ".agents/skills/si-chip/",
    ".cursor/skills/si-chip/",  # mirror target — §7.2 priority 1
    ".claude/skills/si-chip/",  # mirror target — §7.2 priority 2
)


def _scan_python_writes(text: str) -> List[Tuple[str, str]]:
    """Return ``[(pattern_name, path_literal), ...]`` for a Python source.

    Only string-literal paths are surfaced; variable / f-string / joined
    arguments are intentionally skipped (see module docstring — they are
    caller-parameterised).
    """

    hits: List[Tuple[str, str]] = []
    for m in _WRITE_OPEN_RE.finditer(text):
        hits.append(("open_write", m.group(1)))
    for m in _WRITE_PATH_METHOD_RE.finditer(text):
        hits.append(("pathlib_write", m.group(1)))
    for m in _OS_MKDIR_RE.finditer(text):
        if m.group(1):
            hits.append(("os_mkdir", m.group(1)))
    return hits


def _scan_shell_writes(text: str) -> List[Tuple[str, str]]:
    """Return ``[(pattern_name, path_literal), ...]`` for a shell script.

    Only absolute-path redirects (``>`` / ``>>``) with a literal
    ``/...`` destination are surfaced. Variable-driven redirects
    (``>"$OUT"``) are intentionally skipped — again, caller-parameterised.
    """

    hits: List[Tuple[str, str]] = []
    for m in _SHELL_REDIRECT_RE.finditer(text):
        target = m.group(1)
        # Ignore /dev/null and /tmp/ as they are explicitly non-scope.
        if target.startswith(("/dev/null", "/tmp/")):
            continue
        hits.append(("shell_redirect", target))
    return hits


def _is_out_of_scope(path_literal: str, allowed_prefixes: Iterable[str]) -> bool:
    """Return True when ``path_literal`` falls outside every prefix.

    Relative paths are considered in-scope (see module docstring).
    Absolute paths under ``/tmp/`` are also considered in-scope (temp
    directories are ephemeral and never touch the persistent source
    tree).
    """

    if not path_literal.startswith("/") and not path_literal.startswith("\\"):
        return False  # relative — caller-parameterised
    if path_literal.startswith("/tmp/"):
        return False
    for prefix in allowed_prefixes:
        if path_literal.startswith(prefix):
            return False
        # Handle path_literal that begins with a leading '/' but the
        # prefix is relative (caller-invoked from repo_root).
        if path_literal.startswith("/" + prefix):
            return False
    return True


def scan_permission_scope(
    repo_root: Path,
    skill_paths: Iterable[Path],
    *,
    allowed_prefixes: Iterable[str] = DEFAULT_V1_ALLOWED_PREFIXES,
) -> int:
    """V1: count skill-hardcoded write paths outside the allowed prefixes.

    Spec §3.1 D7 V1 ``permission_scope``: the number of distinct filesystem
    paths a skill script / installer writes to that fall **outside**
    ``.local/dogfood/`` AND outside the skill's own ``.agents/skills/si-chip/``
    tree. Lower is better; a clean skill should report ``0``.

    Parameters
    ----------
    repo_root :
        Repository root (used only for logging / provenance).
    skill_paths :
        Iterable of paths to scan. Each path should be either a Python
        source (``*.py``) or a shell script (``*.sh``). Markdown
        artifacts are silently skipped (they cannot write to disk).
    allowed_prefixes :
        Path prefixes that count as in-scope. Default is
        :data:`DEFAULT_V1_ALLOWED_PREFIXES`.

    Returns
    -------
    int
        The distinct out-of-scope write-path count. Zero for Si-Chip
        v0.1.7 (all scripts route writes through caller-provided
        ``--out`` arguments which convention places under
        ``.local/dogfood/<date>/round_<N>/``).

    Raises
    ------
    FileNotFoundError
        If any path in ``skill_paths`` does not exist.

    >>> # Empty input → 0 by convention.
    >>> scan_permission_scope(Path('/tmp'), [])
    0
    """

    out_of_scope: set = set()
    for p in skill_paths:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"skill artifact path not found: {path}")
        if path.is_dir():
            # Recursively scan .py and .sh files within; skip others.
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix in {".py", ".sh"}:
                    out_of_scope |= _collect_writes(child, allowed_prefixes)
            continue
        out_of_scope |= _collect_writes(path, allowed_prefixes)
    LOGGER.info(
        "scan_permission_scope: repo_root=%s out_of_scope_count=%d",
        repo_root, len(out_of_scope),
    )
    return len(out_of_scope)


def _collect_writes(
    path: Path, allowed_prefixes: Iterable[str]
) -> set:
    """Return a set of out-of-scope write paths in a single file."""

    suffix = path.suffix.lower()
    if suffix not in {".py", ".sh", ".bash"}:
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".py":
        hits = _scan_python_writes(text)
    else:
        hits = _scan_shell_writes(text)
    out_of_scope = set()
    allowed_list = list(allowed_prefixes)
    for _pattern_name, candidate in hits:
        if _is_out_of_scope(candidate, allowed_list):
            out_of_scope.add((str(path), candidate))
    return out_of_scope


# ─────────────── V2 credential_surface ───────────────

# Credential / secret patterns. Matches are COUNTED but never logged
# verbatim. The ``name`` in each tuple is safe to log; the regex is
# applied to the artifact body but only the file + pattern name + count
# are surfaced.
CREDENTIAL_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "generic_high_entropy_40",
        re.compile(r"\b[A-F0-9]{40}\b"),  # uppercase hex SHA-1-like
    ),
    (
        "pem_private_key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    (
        "credential_assignment",
        re.compile(
            r"""(?i)(?:api[_-]?key|token|password|secret|bearer)\s*[:=]\s*["'][^"']{8,}["']""",
        ),
    ),
]


def scan_credential_surface(
    repo_root: Path,
    skill_paths: Iterable[Path],
    extra_artifacts: Iterable[Path] = (),
) -> int:
    """V2: count credential/secret pattern occurrences in skill artifacts.

    Spec §3.1 D7 V2 ``credential_surface``: the count of credential /
    secret PATTERN matches (not distinct tokens) across every skill
    artifact body. Clean skill should report ``0``.

    The scanner MUST NOT log the matched value itself. Only the
    pattern name, file path, and per-file match count appear in the
    return value or logs (workspace rule "No Silent Failures" applied
    inversely here — the scan is loud about COUNTS / LOCATIONS, silent
    on VALUES).

    Parameters
    ----------
    repo_root :
        Repository root (provenance only).
    skill_paths :
        Iterable of paths to scan (files or directories). Binary-looking
        files are silently skipped.
    extra_artifacts :
        Additional artifact paths to include (e.g. SKILL.md mirrors for
        completeness). Default empty.

    Returns
    -------
    int
        Total pattern-match count across all artifacts. Zero for
        Si-Chip v0.1.7 (no hard-coded credentials in any skill body).

    Raises
    ------
    FileNotFoundError
        If any path in ``skill_paths`` / ``extra_artifacts`` is missing.

    >>> # Empty scan → 0 by convention.
    >>> scan_credential_surface(Path('/tmp'), [], extra_artifacts=())
    0
    """

    total_matches = 0
    seen: set = set()

    def _walk_target(p: Path) -> List[Path]:
        if not p.exists():
            raise FileNotFoundError(f"artifact path not found: {p}")
        if p.is_dir():
            return [
                child
                for child in sorted(p.rglob("*"))
                if child.is_file()
                and child.suffix.lower()
                in {".py", ".sh", ".bash", ".md", ".yaml", ".yml", ".json", ".txt"}
            ]
        return [p]

    file_list: List[Path] = []
    for src in skill_paths:
        file_list.extend(_walk_target(Path(src)))
    for src in extra_artifacts:
        file_list.extend(_walk_target(Path(src)))

    for path in file_list:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            LOGGER.info("scan_credential_surface: skipping non-utf-8 file %s", path)
            continue
        per_file = 0
        for name, pattern in CREDENTIAL_PATTERNS:
            matches = pattern.findall(body)
            n = len(matches)
            if n > 0:
                # Workspace rule: log pattern name + location + count.
                # NEVER log the matched value itself.
                LOGGER.warning(
                    "V2 credential pattern '%s' matched %d time(s) in %s "
                    "(values suppressed per workspace safety rule)",
                    name, n, path,
                )
                per_file += n
        total_matches += per_file
    LOGGER.info(
        "scan_credential_surface: repo_root=%s total_matches=%d",
        repo_root, total_matches,
    )
    return total_matches


# ─────────────── V3 drift_signal ───────────────


def scan_drift_signal(skill_mirrors: Iterable[Path]) -> float:
    """V3: ``1.0 - cross_tree_drift_zero_ratio`` across mirror files.

    Spec §3.1 D7 V3 ``drift_signal``: measures whether the canonical
    source of truth and its cross-tree mirrors (§7.2) have drifted. For
    Si-Chip v0.1.7 the three mirrors are:

    * ``.agents/skills/si-chip/SKILL.md`` (canonical)
    * ``.cursor/skills/si-chip/SKILL.md``
    * ``.claude/skills/si-chip/SKILL.md``

    Ratio definition: take all unordered pairs of mirror files; count
    the pairs that are byte-equal (``SHA-256 a == SHA-256 b``); divide
    by the total number of pairs. When ``N == 3`` there are 3 pairs.
    All three identical → ratio = 1.0 → drift = 0.0. One mirror drifts
    → ratio = 1/3 → drift = 2/3.

    Returns
    -------
    float
        A value in ``[0.0, 1.0]``. Zero for Si-Chip v0.1.7 (canonical
        + 2 mirrors byte-equal per Round 6/7 drift=0 verdict).

    Raises
    ------
    ValueError
        If fewer than 2 mirror paths are supplied (pair ratio
        undefined).
    FileNotFoundError
        If any mirror path does not exist.

    >>> # Zero-drift quick sanity on two identical synthetic files.
    >>> import tempfile
    >>> tmp = Path(tempfile.mkdtemp())
    >>> _ = (tmp / 'a').write_text('hello', encoding='utf-8')
    >>> _ = (tmp / 'b').write_text('hello', encoding='utf-8')
    >>> scan_drift_signal([tmp / 'a', tmp / 'b'])
    0.0
    """

    mirrors = [Path(m) for m in skill_mirrors]
    if len(mirrors) < 2:
        raise ValueError(
            f"scan_drift_signal requires >=2 mirror paths (got {len(mirrors)})"
        )
    hashes: List[str] = []
    for m in mirrors:
        if not m.exists():
            raise FileNotFoundError(f"mirror path not found: {m}")
        body = m.read_bytes()
        hashes.append(hashlib.sha256(body).hexdigest())

    n = len(hashes)
    total_pairs = n * (n - 1) // 2
    equal_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            if hashes[i] == hashes[j]:
                equal_pairs += 1
    drift_zero_ratio = equal_pairs / total_pairs if total_pairs else 1.0
    drift = 1.0 - drift_zero_ratio
    # Clamp to [0.0, 1.0] defensively (floating rounding only).
    if drift < 0.0:
        drift = 0.0
    if drift > 1.0:
        drift = 1.0
    LOGGER.info(
        "scan_drift_signal: n_mirrors=%d equal_pairs=%d total_pairs=%d drift=%.4f",
        n, equal_pairs, total_pairs, drift,
    )
    return drift


# ─────────────── V4 staleness_days ───────────────


def _parse_iso_date(s: Any) -> _dt.date:
    """Parse an ISO-8601 date string. Raises on malformed input."""

    if isinstance(s, _dt.date):
        return s
    if not isinstance(s, str):
        raise ValueError(f"last_reviewed_at must be a string date, got {type(s).__name__}")
    try:
        return _dt.date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"last_reviewed_at is not ISO-8601: {s!r} ({exc})") from exc


def scan_staleness_days(
    basic_ability_profile_path: Path,
    *,
    today: Optional[_dt.date] = None,
) -> int:
    """V4: days since ``basic_ability_profile.lifecycle.last_reviewed_at``.

    Spec §3.1 D7 V4 ``staleness_days``: an integer count of days since
    the last review date. Same-day review → ``0``. Monotonically
    increases with time until the next review happens.

    Parameters
    ----------
    basic_ability_profile_path :
        Path to a ``basic_ability_profile.yaml``.
    today :
        Optional reference date (default ``_dt.date.today()``). Tests
        inject a fixed date for determinism.

    Returns
    -------
    int
        Non-negative day count.

    Raises
    ------
    FileNotFoundError
        If the profile path is missing.
    ValueError
        If the YAML is malformed, or the ``last_reviewed_at`` field is
        absent / not ISO-8601.

    >>> # Deterministic smoke: today == last_reviewed_at → 0.
    >>> import tempfile
    >>> tmp = Path(tempfile.mkdtemp()) / 'profile.yaml'
    >>> _ = tmp.write_text(
    ...     "basic_ability:\\n  lifecycle:\\n    last_reviewed_at: '2026-04-28'\\n",
    ...     encoding='utf-8',
    ... )
    >>> scan_staleness_days(tmp, today=_dt.date(2026, 4, 28))
    0
    """

    path = Path(basic_ability_profile_path)
    if not path.exists():
        raise FileNotFoundError(f"basic_ability_profile not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping, got {type(data).__name__}")

    ba = data.get("basic_ability")
    if not isinstance(ba, dict):
        raise ValueError(f"{path}: missing 'basic_ability' top-level mapping")
    lifecycle = ba.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise ValueError(f"{path}: missing 'basic_ability.lifecycle' mapping")
    raw = lifecycle.get("last_reviewed_at")
    if raw is None:
        raise ValueError(f"{path}: missing 'basic_ability.lifecycle.last_reviewed_at'")
    last_reviewed = _parse_iso_date(raw)

    reference = today if today is not None else _dt.date.today()
    delta = (reference - last_reviewed).days
    if delta < 0:
        # A future review date is a workflow bug — surface loudly.
        raise ValueError(
            f"last_reviewed_at {last_reviewed} is in the future relative to {reference}"
        )
    LOGGER.info(
        "scan_staleness_days: last_reviewed_at=%s today=%s days=%d",
        last_reviewed, reference, delta,
    )
    return delta


# ─────────────── Report aggregation ───────────────


@dataclass
class GovernanceReport:
    """Machine-readable D7 scan result.

    The ``provenance`` block records the exact inputs so the scan is
    reproducible across rebuilds (deterministic runner contract).
    """

    V1_permission_scope: int
    V2_credential_surface: int
    V3_drift_signal: float
    V4_staleness_days: int
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "V1_permission_scope": self.V1_permission_scope,
            "V2_credential_surface": self.V2_credential_surface,
            "V3_drift_signal": self.V3_drift_signal,
            "V4_staleness_days": self.V4_staleness_days,
            "provenance": self.provenance,
        }


def compute_governance_risk_delta(
    v1: int,
    v2: int,
    v3: float,
    v4: int,
    *,
    v4_staleness_cap_days: int = 30,
) -> float:
    """Compute ``governance_risk_delta`` = ``risk_without - risk_with``.

    Per spec §6.1 the axis is ``risk_without - risk_with``. The
    no-ability baseline does not interact with the filesystem, so
    ``risk_without = 0`` (the skill is not installed → it cannot write
    anything outside .local/dogfood, cannot contain credentials, cannot
    drift, and has no review cadence). ``risk_with`` is computed as a
    bounded monotone combination of V1-V4:

        risk_with = min(V1 / 1, 1.0) * 0.25
                  + min(V2 / 1, 1.0) * 0.25
                  + V3                 * 0.25
                  + min(V4 / v4_cap, 1.0) * 0.25

    Each of V1, V2, V3, V4 contributes at most ``0.25`` to ``risk_with``
    so the axis stays within ``[-1.0, +1.0]`` for any input. For Si-Chip
    v0.1.7 with V1=V2=V3=V4=0 the delta is ``0.0`` (no governance
    risk relative to the clean no-ability baseline).

    >>> compute_governance_risk_delta(0, 0, 0.0, 0)
    0.0
    >>> # One write outside scope already moves the delta negative.
    >>> round(compute_governance_risk_delta(1, 0, 0.0, 0), 4)
    -0.25
    """

    if v4_staleness_cap_days <= 0:
        raise ValueError("v4_staleness_cap_days must be > 0")
    risk_without = 0.0
    v1_term = min(float(v1), 1.0) * 0.25
    v2_term = min(float(v2), 1.0) * 0.25
    v3_term = max(0.0, min(float(v3), 1.0)) * 0.25
    v4_term = min(float(v4) / float(v4_staleness_cap_days), 1.0) * 0.25
    risk_with = v1_term + v2_term + v3_term + v4_term
    delta = risk_without - risk_with
    if delta < -1.0:
        delta = -1.0
    if delta > 1.0:
        delta = 1.0
    return float(delta)


def build_governance_report(
    repo_root: Path,
    skill_paths: Iterable[Path],
    skill_mirrors: Iterable[Path],
    basic_ability_profile_path: Path,
    *,
    today: Optional[_dt.date] = None,
    extra_artifacts: Iterable[Path] = (),
) -> Dict[str, Any]:
    """Assemble a full V1-V4 report suitable for ``aggregate_eval.py``.

    Returns
    -------
    dict
        ``{"V1_permission_scope": int, "V2_credential_surface": int,
          "V3_drift_signal": float, "V4_staleness_days": int,
          "provenance": {...}}``

    Raises
    ------
    FileNotFoundError
        From any underlying scan when inputs are missing.
    ValueError
        When the basic ability profile is malformed / last_reviewed_at
        is absent or unparseable.
    """

    skill_paths_list = [Path(p) for p in skill_paths]
    mirror_list = [Path(m) for m in skill_mirrors]
    profile_path = Path(basic_ability_profile_path)

    v1 = scan_permission_scope(repo_root, skill_paths_list)
    v2 = scan_credential_surface(
        repo_root, skill_paths_list, extra_artifacts=extra_artifacts
    )
    v3 = scan_drift_signal(mirror_list)
    v4 = scan_staleness_days(profile_path, today=today)

    governance_risk_delta = compute_governance_risk_delta(v1, v2, v3, v4)
    report = GovernanceReport(
        V1_permission_scope=v1,
        V2_credential_surface=v2,
        V3_drift_signal=v3,
        V4_staleness_days=v4,
        provenance={
            "script_version": SCRIPT_VERSION,
            "repo_root": str(repo_root),
            "skill_paths": [str(p) for p in skill_paths_list],
            "skill_mirrors": [str(m) for m in mirror_list],
            "basic_ability_profile_path": str(profile_path),
            "today": (today or _dt.date.today()).isoformat(),
            "v1_derivation": {
                "method": (
                    "count distinct hardcoded absolute write-paths outside "
                    ".local/dogfood/ and outside the skill's own source tree"
                ),
                "allowed_prefixes": list(DEFAULT_V1_ALLOWED_PREFIXES),
                "n_skill_paths_scanned": len(skill_paths_list),
            },
            "v2_derivation": {
                "method": (
                    "count credential/secret pattern matches across skill "
                    "artifacts; MUST NOT log matched values"
                ),
                "patterns_used": [name for (name, _) in CREDENTIAL_PATTERNS],
            },
            "v3_derivation": {
                "method": (
                    "1.0 - cross_tree_drift_zero_ratio; pairs that are "
                    "SHA-256 byte-equal / total pairs"
                ),
                "n_mirrors": len(mirror_list),
                "total_pairs": (
                    len(mirror_list) * (len(mirror_list) - 1) // 2
                    if mirror_list else 0
                ),
            },
            "v4_derivation": {
                "method": (
                    "(today - basic_ability_profile.lifecycle.last_reviewed_at)"
                    ".days"
                ),
                "profile_path": str(profile_path),
            },
            "governance_risk_delta": governance_risk_delta,
            "governance_risk_delta_method": (
                "compute_governance_risk_delta(V1, V2, V3, V4); "
                "risk_without - risk_with per spec §6.1 D7"
            ),
        },
    )
    return report.to_dict()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan Si-Chip D7 governance risk: V1 permission_scope, V2 "
            "credential_surface, V3 drift_signal, V4 staleness_days."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (provenance only). Default: '.'",
    )
    parser.add_argument(
        "--skill-path",
        action="append",
        default=None,
        help=(
            "Skill artifact directory or file. Repeatable. Default: "
            ".agents/skills/si-chip"
        ),
    )
    parser.add_argument(
        "--skill-mirror",
        action="append",
        default=None,
        help=(
            "Mirror SKILL.md path. Repeatable. Default: "
            ".agents/skills/si-chip/SKILL.md + .cursor/skills/si-chip/SKILL.md "
            "+ .claude/skills/si-chip/SKILL.md"
        ),
    )
    parser.add_argument(
        "--basic-ability-profile",
        required=True,
        help="Path to basic_ability_profile.yaml (required for V4).",
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override 'today' (ISO date YYYY-MM-DD). Default: actual today.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a single-line JSON payload on stdout.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Verbose logging."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    repo_root = Path(args.repo_root).resolve()
    if args.skill_path:
        skill_paths = [Path(p) for p in args.skill_path]
    else:
        skill_paths = [repo_root / ".agents" / "skills" / "si-chip"]
    if args.skill_mirror:
        skill_mirrors = [Path(m) for m in args.skill_mirror]
    else:
        skill_mirrors = [
            repo_root / ".agents" / "skills" / "si-chip" / "SKILL.md",
            repo_root / ".cursor" / "skills" / "si-chip" / "SKILL.md",
            repo_root / ".claude" / "skills" / "si-chip" / "SKILL.md",
        ]
    today: Optional[_dt.date] = None
    if args.today:
        today = _dt.date.fromisoformat(args.today)

    report = build_governance_report(
        repo_root,
        skill_paths,
        skill_mirrors,
        Path(args.basic_ability_profile),
        today=today,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"V1_permission_scope    = {report['V1_permission_scope']}")
        print(f"V2_credential_surface  = {report['V2_credential_surface']}")
        print(f"V3_drift_signal        = {report['V3_drift_signal']}")
        print(f"V4_staleness_days      = {report['V4_staleness_days']}")
        print(
            f"governance_risk_delta  = "
            f"{report['provenance']['governance_risk_delta']}"
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        LOGGER.error("fatal: %s", exc)
        raise
