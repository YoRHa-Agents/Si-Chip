#!/usr/bin/env python3
"""Static structural validator for the Si-Chip spec.

Implements the **eleven** machine-checkable invariants declared across
spec §13.4 (v0.2.0 — 9 BLOCKERs) and §13.5.4 (v0.3.0-rc1 — 2 additive
BLOCKERs). Round 12 (Si-Chip v0.1.11) added the 9th BLOCKER
``REACTIVATION_DETECTOR_EXISTS``. Stage 4 Wave 2a (v0.3.0-rc1, 2026-04-29)
adds the 10th and 11th:

* ``CORE_GOAL_FIELD_PRESENT`` — asserts that the BasicAbilityProfile
  schema declares a REQUIRED ``core_goal`` block with the §14.1.1
  sub-fields (``statement`` / ``test_pack_path`` / ``minimum_pass_rate``)
  and that ``minimum_pass_rate.const == 1.0`` (spec §14.3 lock). Skipped
  as PASS when the schema's own ``$schema_version`` is < ``0.2.0``
  (legacy compat for the pre-v0.3.0 10-key schema).
* ``ROUND_KIND_TEMPLATE_VALID`` — asserts that
  ``iteration_delta_report.template.yaml`` and
  ``next_action_plan.template.yaml`` declare a ``round_kind`` field whose
  value is a member of ``tools.round_kind.ROUND_KINDS`` (the
  ``code_change`` / ``measurement_only`` / ``ship_prep`` / ``maintenance``
  4-value enum frozen at spec §15.1.1). Skipped as PASS for
  ``$schema_version < 0.2.0`` templates (legacy compat).

Spec path defaults to ``.local/research/spec_v0.2.0.md`` (Si-Chip v0.2.0
ship, 2026-04-28; promoted from v0.2.0-rc1 with no Normative semantic
change). §13.4 prose counts remain aligned with the §3.1 / §4.1 TABLES
(37 sub-metrics / 30 threshold cells). Spec v0.2.0-rc1 is also accepted
via ``--spec .local/research/spec_v0.2.0-rc1.md`` (pinned historical
record). Spec v0.1.0 remains accepted via
``--spec .local/research/spec_v0.1.0.md`` for backward-compat
verification of Rounds 1–10 artefacts. Spec v0.3.0-rc1 is accepted via
``--spec .local/research/spec_v0.3.0-rc1.md``; the v0.3.0 default flip
happens at L0 step 8 (final ship), not in this stage.

The validator does NOT execute the dogfood loop, the router test, or any
metric collection. It only verifies that the spec markdown plus the six
templates under ``templates/`` remain structurally aligned with the §3,
§4, §5.3, §6.1, §7.2, §8.1, §8.2, §11.1, §14, §15 Normative content.

CLI::

    python tools/spec_validator.py [--spec PATH] [--strict] [--json] \\
        [--strict-prose-count]

``--spec PATH`` selects the spec markdown (default
``.local/research/spec_v0.2.0.md``; latest accepted: ``v0.3.0-rc1``).

``--strict`` treats WARNING findings as failures.

``--json`` emits a structured JSON report on stdout.

``--strict-prose-count`` enforces the spec §13.4 prose number for two
invariants:

* Against v0.2.0 (default spec), v0.2.0-rc1 (pinned historical record),
  and v0.3.0-rc1: prose == 37 sub-metrics + 30 threshold cells (matches
  the §3.1 / §4.1 TABLES) → PASS.
* Against v0.1.0 (``--spec .local/research/spec_v0.1.0.md``): prose ==
  28 + 21 → also PASS (v0.1.0 prose was self-consistent at those
  legacy numbers).
* Against a mixed / drifted spec: FAIL, exposing reconciliation drift.

The mode auto-detects v0.1.0 / v0.2.0-rc1 / v0.2.0 / v0.3.0-rc1 from the
spec's frontmatter ``version:`` field and the ``# Si-Chip Spec v…`` H1
header. This keeps Round 1–10 artefact verification working (they
reference v0.1.0 by ``spec_version``), Rounds 11–13 ship-prep
verification working (they reference v0.2.0-rc1), the live post-ship
checks target v0.2.0, and Round 14+ targets v0.3.0-rc1.

Exit code is 0 when every BLOCKER assertion passes (and, with
``--strict``, when no WARNING fired). Exit code is 1 otherwise. Any
spec-read or template-read failure raises rather than silently passing
(workspace rule "No Silent Failures").
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# tools/ is not a package; inject repo root so ``from tools.round_kind
# import ...`` works regardless of how the script is invoked
# (`python tools/spec_validator.py`, `python -m`, pytest discovery, etc.)
# Workspace rule "No Silent Failures": if the import fails, raise — do
# NOT silently fall back to a vendored copy of the constants.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.round_kind import (  # noqa: E402  (post-sys.path-insert import)
    ROUND_KINDS,
    validate_round_kind,
)

LOGGER = logging.getLogger("si_chip.spec_validator")

# Validator's own semver (independent of spec version).
# 0.2.0 — Stage 4 Wave 2a (v0.3.0-rc1): accepts spec v0.3.0-rc1 alongside
# v0.2.0 / v0.2.0-rc1 / v0.1.0; adds 2 new BLOCKERs CORE_GOAL_FIELD_PRESENT
# and ROUND_KIND_TEMPLATE_VALID; version-aware EXPECTED_BAP_KEYS_BY_SCHEMA.
SCRIPT_VERSION = "0.2.0"

# §5 router_test_matrix template accepts BOTH schema versions as of
# Round 9 (Si-Chip v0.1.8). 0.1.0 = initial (mvp:8 + full:96); 0.1.1 =
# additive intermediate:16 profile. Backward compatibility is intentional —
# previous rounds' evidence stays valid.
SUPPORTED_ROUTER_TEMPLATE_SCHEMAS = {"0.1.0", "0.1.1"}

# Round 9 intermediate invariants (only asserted when schema is 0.1.1).
EXPECTED_INTERMEDIATE_CELLS = 16
EXPECTED_INTERMEDIATE_GATE_BINDING = "relaxed"

# v0.2.0 ship (2026-04-28): spec v0.2.0-rc1 promoted to v0.2.0 (frozen).
# The default spec path points to v0.2.0; v0.2.0-rc1 / v0.1.0 stay
# accepted via --spec as pinned historical records (Rounds 1-13). Stage
# 4 Wave 2a (2026-04-29): spec v0.3.0-rc1 is opt-in via
# `--spec .local/research/spec_v0.3.0-rc1.md`. The default flips to
# v0.3.0 only at L0 step 8 (final ship), not in this stage.
DEFAULT_SPEC = ".local/research/spec_v0.2.0.md"
DEFAULT_TEMPLATES_DIR = "templates"

# Supported spec versions (validator accepts any; strict-prose-count
# auto-adjusts expected numbers based on spec version).
SUPPORTED_SPEC_VERSIONS = {"v0.1.0", "v0.2.0-rc1", "v0.2.0", "v0.3.0-rc1"}

# §2.1 frozen field set under basic_ability — version-keyed dict.
# Lookup by the schema file's own ``$schema_version`` (top-level YAML
# key in templates/basic_ability_profile.schema.yaml). The schema is
# the runtime contract; the spec markdown describes it. This branches
# on the schema, NOT on --spec, mirroring how v0.1.0 → v0.2.0-rc1
# reconciliation was done (schema unchanged, spec prose updated).
#
# 0.1.0 — pre-v0.3.0 schema (10 keys; no core_goal).
# 0.2.0 — additive: spec v0.3.0-rc1 §14 made ``core_goal`` REQUIRED as
#         the 11th key. Existing 10 keys preserved byte-identical.
EXPECTED_BAP_KEYS_BY_SCHEMA: Dict[str, set] = {
    "0.1.0": {
        "id",
        "intent",
        "current_surface",
        "packaging",
        "lifecycle",
        "eval_state",
        "metrics",
        "value_vector",
        "router_floor",
        "decision",
    },
    "0.2.0": {
        "id",
        "intent",
        "core_goal",
        "current_surface",
        "packaging",
        "lifecycle",
        "eval_state",
        "metrics",
        "value_vector",
        "router_floor",
        "decision",
    },
}

# §3.1 R6 metric dimension -> sub-metric count (TABLE form, 37 total).
# This is the RUNTIME CONTRACT (templates + spec_validator default mode
# both assert this). Unchanged across v0.1.0 and v0.2.0-rc1.
EXPECTED_R6_TABLE_COUNTS = {
    "task_quality": 4,
    "context_economy": 6,
    "latency_path": 7,
    "generalizability": 4,
    "usage_cost": 4,
    "routing_cost": 8,
    "governance_risk": 4,
}
EXPECTED_R6_TABLE_TOTAL = sum(EXPECTED_R6_TABLE_COUNTS.values())  # 37

# §13.4 prose total — depends on spec version:
#   v0.1.0:      prose claimed 28 (legacy; misaligned with §3.1 TABLE=37)
#   v0.2.0-rc1:  prose claimed 37 (reconciled with §3.1 TABLE; Round 11)
#   v0.2.0:      prose claimed 37 (inherits v0.2.0-rc1 reconciliation; ship)
#   v0.3.0-rc1:  prose claimed 37 (additive — §13.4 byte-identical to v0.2.0;
#                                  v0.3.0 add-on lives in §13.5.4 instead)
# strict-prose-count mode picks the correct expected value from this map
# using the spec's own version frontmatter.
EXPECTED_R6_PROSE_BY_SPEC = {
    "v0.1.0": 28,
    "v0.2.0-rc1": 37,
    "v0.2.0": 37,
    "v0.3.0-rc1": 37,
}
# Default fallback (when spec version cannot be detected): v0.2.0 (ship default).
EXPECTED_R6_PROSE_DEFAULT = EXPECTED_R6_PROSE_BY_SPEC["v0.2.0"]

# §4.1 threshold table — 10 metrics × 3 profiles = 30 cells.
# This is the RUNTIME CONTRACT. Unchanged across v0.1.0 and v0.2.0-rc1.
THRESHOLD_METRICS = [
    "pass_rate",
    "pass_k",
    "trigger_F1",
    "near_miss_FP_rate",
    "metadata_tokens",
    "per_invocation_footprint",
    "wall_clock_p95",
    "routing_latency_p95",
    "routing_token_overhead",
    "iteration_delta",
]
BIGGER_IS_BETTER = {"pass_rate", "pass_k", "trigger_F1", "iteration_delta"}
EXPECTED_THRESHOLD_CELLS_TABLE = len(THRESHOLD_METRICS) * 3  # 30

# §13.4 threshold-cell prose count — depends on spec version:
#   v0.1.0:      prose claimed 21 (legacy; misaligned with §4.1 TABLE=30)
#   v0.2.0-rc1:  prose claimed 30 (reconciled with §4.1 TABLE; Round 11)
#   v0.2.0:      prose claimed 30 (inherits v0.2.0-rc1 reconciliation; ship)
#   v0.3.0-rc1:  prose claimed 30 (additive — §13.4 byte-identical to v0.2.0)
EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC = {
    "v0.1.0": 21,
    "v0.2.0-rc1": 30,
    "v0.2.0": 30,
    "v0.3.0-rc1": 30,
}
EXPECTED_THRESHOLD_CELLS_PROSE_DEFAULT = EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.2.0"]

# §6.1 frozen 7-axis value vector.
EXPECTED_VALUE_VECTOR_AXES = {
    "task_delta",
    "token_delta",
    "latency_delta",
    "context_delta",
    "path_efficiency_delta",
    "routing_delta",
    "governance_risk_delta",
}

# §8.1 8-step frozen order.
EXPECTED_DOGFOOD_STEPS = [
    "profile",
    "evaluate",
    "diagnose",
    "improve",
    "router-test",
    "half-retire-review",
    "iterate",
    "package-register",
]

# §8.2 minimum evidence files (6).
EXPECTED_EVIDENCE_FILES = [
    "BasicAbilityProfile",
    "metrics_report",
    "router_floor_report",
    "half_retire_decision",
    "next_action_plan",
    "iteration_delta_report",
]

# Round 12 §6.4 reactivation-detector invariant. The 9th BLOCKER asserts
# that ``tools/reactivation_detector.py`` exists, references all 6 §6.4
# trigger IDs verbatim, and that its sibling test file exists with at
# least 1 test per trigger. The 6 IDs MUST appear byte-for-byte in the
# detector source so an automated reader can map verdict trigger names
# back to spec §6.4 prose.
REACTIVATION_DETECTOR_PATH = "tools/reactivation_detector.py"
REACTIVATION_DETECTOR_TEST_PATH = "tools/test_reactivation_detector.py"
EXPECTED_REACTIVATION_TRIGGER_IDS: Tuple[str, ...] = (
    "new_model_no_ability_baseline_gap",
    "new_scenario_or_domain_match",
    "router_test_requires_ability_for_cheap_model",
    "efficiency_axis_becomes_significant",
    "upstream_api_change_wrapper_stabilizes",
    "manual_invocation_rebound",
)

# §11.1 forever-out items — keyword groups (any one keyword from a group
# in the §11.1 block satisfies the item).
FOREVER_OUT_GROUPS: List[Dict[str, Any]] = [
    {
        "id": "marketplace",
        "keywords": ["marketplace"],
    },
    {
        "id": "router_training",
        "keywords": ["Router 模型训练", "router model training", "Router model training"],
    },
    {
        "id": "ide_compat",
        "keywords": ["通用 IDE", "IDE / Agent runtime", "generic IDE", "IDE compatibility"],
    },
    {
        "id": "md_to_cli",
        "keywords": ["Markdown-to-CLI", "Markdown to CLI"],
    },
]


@dataclass
class AssertionResult:
    """Single invariant outcome, JSON-serializable.

    Severity is one of ``BLOCKER`` / ``WARNING`` / ``INFO``.
    """

    id: str
    name: str
    passed: bool
    severity: str
    message: str
    evidence: Any = field(default=None)


@dataclass
class ValidationReport:
    verdict: str
    results: List[AssertionResult]
    spec_path: str
    ran_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "results": [asdict(r) for r in self.results],
            "spec_path": self.spec_path,
            "ran_at": self.ran_at,
        }


# ─────────────────────────── helpers ───────────────────────────


def _read_text(path: Path) -> str:
    """Read a text file or raise (no silent failure)."""

    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_yaml(path: Path) -> Any:
    text = _read_text(path)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuntimeError(f"failed to parse YAML {path}: {exc}") from exc


def _section(spec_text: str, header_re: str, end_re: str = r"^##\s+\d+\.\s") -> str:
    """Extract a section body from the spec markdown.

    ``header_re`` matches the opening ``## N. ...`` line; ``end_re``
    matches the next top-level section header. Returns the substring
    starting immediately after the header match and ending immediately
    before the next top-level header (or end of text).

    >>> _section("## 1. A\\nx\\n## 2. B\\ny\\n", r"^##\\s+1\\.\\s+A\\n")
    'x\\n'
    """

    h = re.search(header_re, spec_text, flags=re.MULTILINE)
    if not h:
        raise RuntimeError(f"section header not found for pattern {header_re!r}")
    start = h.end()
    e = re.search(end_re, spec_text[start:], flags=re.MULTILINE)
    end = start + e.start() if e else len(spec_text)
    return spec_text[start:end]


def _subsection(spec_text: str, header_re: str) -> str:
    """Extract a subsection (### N.M) up to the next ### or ## header."""

    h = re.search(header_re, spec_text, flags=re.MULTILINE)
    if not h:
        raise RuntimeError(f"subsection header not found for pattern {header_re!r}")
    start = h.end()
    e = re.search(r"^(###\s|##\s)", spec_text[start:], flags=re.MULTILINE)
    end = start + e.start() if e else len(spec_text)
    return spec_text[start:end]


_VERSION_FRONTMATTER_RE = re.compile(
    r'^version:\s*"?(?P<version>v\d+(?:\.\d+)*(?:-[\w.]+)?)"?\s*$',
    re.MULTILINE,
)
_VERSION_H1_RE = re.compile(
    r"^#\s+Si-Chip Spec\s+(?P<version>v\d+(?:\.\d+)*(?:-[\w.]+)?)",
    re.MULTILINE,
)


def detect_spec_version(spec_text: str) -> Optional[str]:
    """Extract spec version from frontmatter or H1 header.

    Returns the version string (e.g. ``"v0.1.0"`` or ``"v0.2.0-rc1"``) or
    ``None`` when the spec declares no version. Frontmatter ``version:``
    takes precedence over the H1 fallback.

    >>> detect_spec_version('---\\nversion: "v0.2.0-rc1"\\n---\\n')
    'v0.2.0-rc1'
    >>> detect_spec_version("# Si-Chip Spec v0.1.0（Frozen）\\n")
    'v0.1.0'
    >>> detect_spec_version("no version here") is None
    True
    """

    m = _VERSION_FRONTMATTER_RE.search(spec_text)
    if m:
        return m.group("version")
    m = _VERSION_H1_RE.search(spec_text)
    if m:
        return m.group("version")
    return None


def _count_metric_keys(metrics: Dict[str, Any]) -> Dict[str, int]:
    """Count sub-metric keys per dimension.

    Each dimension's ``properties`` mapping enumerates the sub-metric
    names; a missing ``properties`` mapping yields zero (this is a
    template-shape error, surfaced by R6_KEYS).

    >>> m = {"d1": {"properties": {"T1": {}, "T2": {}}}, "d2": {"properties": {}}}
    >>> _count_metric_keys(m)
    {'d1': 2, 'd2': 0}
    """

    out: Dict[str, int] = {}
    for dim, body in metrics.items():
        if not isinstance(body, dict):
            out[dim] = 0
            continue
        props = body.get("properties")
        if isinstance(props, dict):
            out[dim] = len(props)
        else:
            out[dim] = 0
    return out


# ─────────────────────────── invariants ───────────────────────────


def _read_schema_version(schema: Dict[str, Any]) -> str:
    """Return the BAP schema's own ``$schema_version`` string.

    Falls back to ``"0.1.0"`` when the schema declares none — this
    matches the pre-Stage-4 default and preserves backward-compat with
    Round 1-13 / Round 1-10 fixtures that may not embed a version.
    """

    if not isinstance(schema, dict):
        raise RuntimeError(
            f"BAP schema must be a YAML mapping, got {type(schema).__name__}"
        )
    raw = schema.get("$schema_version", "0.1.0")
    return str(raw)


def check_bap_schema(templates_dir: Path) -> AssertionResult:
    """Invariant 1 — BAP_SCHEMA: §2.1 top-level field set match.

    Branches on the schema file's own ``$schema_version`` (NOT on
    ``--spec``). Lookup table::

        $schema_version 0.1.0 → 10 keys (pre-v0.3.0; no core_goal)
        $schema_version 0.2.0 → 11 keys (v0.3.0 §14: core_goal REQUIRED)

    Unknown ``$schema_version`` is an explicit BLOCKER fail (no silent
    pass) per workspace rule "No Silent Failures".
    """

    schema_path = templates_dir / "basic_ability_profile.schema.yaml"
    schema = _load_yaml(schema_path)
    try:
        ba_props = schema["properties"]["basic_ability"]["properties"]
    except (KeyError, TypeError) as exc:
        return AssertionResult(
            id="BAP_SCHEMA",
            name="BasicAbilityProfile schema field set matches spec §2.1",
            passed=False,
            severity="BLOCKER",
            message=f"schema missing properties.basic_ability.properties: {exc}",
            evidence={"schema_path": str(schema_path)},
        )

    schema_version = _read_schema_version(schema)
    expected = EXPECTED_BAP_KEYS_BY_SCHEMA.get(schema_version)
    if expected is None:
        supported = sorted(EXPECTED_BAP_KEYS_BY_SCHEMA.keys())
        return AssertionResult(
            id="BAP_SCHEMA",
            name="BasicAbilityProfile schema field set matches spec §2.1",
            passed=False,
            severity="BLOCKER",
            message=(
                f"unknown $schema_version={schema_version!r}; "
                f"supported: {', '.join(supported)}"
            ),
            evidence={
                "schema_path": str(schema_path),
                "schema_version": schema_version,
                "supported_versions": supported,
            },
        )

    actual = set(ba_props.keys())
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    passed = not missing and not extra
    return AssertionResult(
        id="BAP_SCHEMA",
        name="BasicAbilityProfile schema field set matches spec §2.1",
        passed=passed,
        severity="BLOCKER",
        message=(
            f"$schema_version={schema_version} "
            f"expected={sorted(expected)} actual={sorted(actual)}"
            f" missing={missing} extra={extra}"
        ),
        evidence={
            "schema_version": schema_version,
            "expected": sorted(expected),
            "actual": sorted(actual),
            "missing": missing,
            "extra": extra,
        },
    )


def _r6_prose_numbers_in_section3(spec_text: str) -> Dict[str, Any]:
    """Extract AUTHORITATIVE R6 prose sub-metric counts from §3 body.

    Matches the two canonical "assertion-of-count" phrases only:
      * ``7 维 / NNN 子指标`` (§3 intro)
      * ``完整 NNN 子指标`` / ``完整 NNN 项 key`` (§3.2 item 2)

    Historical / footnote references (e.g. ``v0.1.0 prose 写作 "28 子指标"``)
    appear in parenthetical annotations and are intentionally ignored —
    only the assertion forms are policy-relevant.

    >>> _r6_prose_numbers_in_section3("必须实现 R6 全部 7 维 / 28 子指标")["matches"]
    [28]
    >>> _r6_prose_numbers_in_section3("完整 37 子指标 的字段...")["matches"]
    [37]
    >>> _r6_prose_numbers_in_section3(
    ...     "7 维 / 37 子指标。v0.1.0 prose 写作 \\"28 子指标\\"。完整 37 子指标"
    ... )["matches"]
    [37, 37]
    """

    try:
        body = _section(spec_text, r"^##\s+3\.\s")
    except RuntimeError:
        body = spec_text
    # Two authoritative assertion patterns:
    #   1. ``7 维 / NNN 子指标`` or ``7 维／NNN 子指标`` (§3 intro)
    #   2. ``完整 NNN 子指标`` / ``完整 NNN 项 key`` (§3.2 frozen constraint)
    patterns = [
        re.compile(r"7\s*维\s*[/／]\s*\*{0,2}(\d+)\s*子指标"),
        re.compile(r"完整\s*\*{0,2}(\d+)\s*(?:子指标|项\s*key)"),
    ]
    ints: List[int] = []
    for p in patterns:
        for m in p.finditer(body):
            ints.append(int(m.group(1)))
    return {"matches": ints}


def check_r6_keys(
    templates_dir: Path,
    *,
    strict_prose: bool,
    spec_version: Optional[str] = None,
    spec_text: Optional[str] = None,
) -> AssertionResult:
    """Invariant 2 — R6_KEYS: §3.1 metric key count.

    Default: assert per-dimension {D1:4, D2:6, D3:7, D4:4, D5:4, D6:8,
    D7:4} = 37 total (§3.1 TABLE).

    With ``strict_prose=True``:

    * v0.1.0 spec: assert template total == 28 (§13.4 legacy prose
      claim). This still FAILS against the real schema (which is 37)
      because the prose is wrong. Kept for historical parity.
    * v0.2.0-rc1 spec (default post-Round-11): assert template total
      == 37 AND spec §3 prose numbers == 37. Both PASS after
      reconciliation.

    ``spec_version`` lets the caller explicitly pin the expected count;
    when omitted, the validator derives it from the spec frontmatter
    (the v0.2.0-rc1 default).
    """

    schema_path = templates_dir / "basic_ability_profile.schema.yaml"
    schema = _load_yaml(schema_path)
    try:
        metrics = schema["properties"]["basic_ability"]["properties"]["metrics"][
            "properties"
        ]
    except (KeyError, TypeError) as exc:
        return AssertionResult(
            id="R6_KEYS",
            name="R6 metric key set matches spec §3.1 (TABLE=37, prose=37 @ v0.2.0-rc1)",
            passed=False,
            severity="BLOCKER",
            message=f"schema missing metrics.properties: {exc}",
            evidence={"schema_path": str(schema_path)},
        )

    counts = _count_metric_keys(metrics)
    total = sum(counts.values())

    # Pick prose expectation from the spec's own version.
    prose_expected = EXPECTED_R6_PROSE_BY_SPEC.get(
        spec_version or "", EXPECTED_R6_PROSE_DEFAULT
    )
    info_note = (
        f"INFO: spec §3.1 TABLE enumerates 37 sub-metrics; §13.4 prose "
        f"under spec_version={spec_version!r} expects {prose_expected}. "
        "Templates use the TABLE count."
    )

    if strict_prose:
        # Two-part check:
        #   (a) TEMPLATE metric-key total matches the prose expectation.
        #   (b) §3 prose integers in the spec match the prose expectation.
        prose_integers_observed: List[int] = []
        prose_integers_ok = True
        if spec_text is not None:
            prose_integers_observed = _r6_prose_numbers_in_section3(spec_text)["matches"]
            # Every prose integer found in §3 next to "子指标" / "项 key"
            # must equal the prose expectation.
            prose_integers_ok = all(n == prose_expected for n in prose_integers_observed)

        template_matches_prose = total == prose_expected
        passed = template_matches_prose and prose_integers_ok
        msg = (
            f"strict-prose-count @ spec_version={spec_version!r}: template total="
            f"{total} expected={prose_expected} (template_matches_prose={template_matches_prose}); "
            f"§3 prose integers observed={prose_integers_observed} "
            f"(prose_integers_ok={prose_integers_ok}). {info_note}"
        )
    else:
        passed = (
            counts == EXPECTED_R6_TABLE_COUNTS and total == EXPECTED_R6_TABLE_TOTAL
        )
        msg = (
            f"expected per-dim={EXPECTED_R6_TABLE_COUNTS} (total {EXPECTED_R6_TABLE_TOTAL}), "
            f"observed per-dim={counts} (total {total}). {info_note}"
        )

    return AssertionResult(
        id="R6_KEYS",
        name="R6 metric key set matches spec §3.1 (TABLE=37, prose=37 @ v0.2.0-rc1)",
        passed=passed,
        severity="BLOCKER",
        message=msg,
        evidence={
            "per_dimension": counts,
            "total": total,
            "expected_table": EXPECTED_R6_TABLE_COUNTS,
            "expected_prose_total": prose_expected,
            "spec_version": spec_version,
            "mode": "strict_prose" if strict_prose else "table",
        },
    )


_THRESHOLD_ROW_RE = re.compile(
    r"^\|\s*`?([^|`]+?)`?\s*(?:\([^)]*\))?\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|"
)


def _parse_threshold_row(line: str) -> Optional[Dict[str, Any]]:
    """Parse one §4.1 markdown row into ``{metric, v1, v2, v3}``.

    Returns ``None`` when the row is the table header / separator or
    when the metric column does not match a known threshold metric.

    >>> _parse_threshold_row("| `pass_rate` | \u2265 0.75 | \u2265 0.82 | \u2265 0.90 |")["metric"]
    'pass_rate'
    >>> _parse_threshold_row("|---|---|---|---|") is None
    True
    """

    m = _THRESHOLD_ROW_RE.match(line)
    if not m:
        return None
    raw_metric = m.group(1).strip()
    metric = re.sub(r"\s*\(.*\)\s*", "", raw_metric).strip()
    if metric not in THRESHOLD_METRICS:
        return None

    def _num(cell: str) -> Optional[float]:
        s = cell.strip().lstrip("≥≤><=+ ").strip()
        s = s.replace("\u2265", "").replace("\u2264", "").strip()
        s = re.sub(r"\s*\(.*\)\s*", "", s).strip()
        try:
            return float(s)
        except ValueError:
            return None

    v1 = _num(m.group(2))
    v2 = _num(m.group(3))
    v3 = _num(m.group(4))
    return {"metric": metric, "v1": v1, "v2": v2, "v3": v3}


def _threshold_prose_numbers_in_section13(spec_text: str) -> Dict[str, Any]:
    """Extract AUTHORITATIVE threshold-cell count from §13.4 wording.

    Matches the canonical "assertion-of-count" phrase only:
      * ``§4 阈值表 NNN 个数`` (§13.4 machine-checkable item)

    Historical / footnote references that may appear AFTER §13.4 (e.g.
    Reconciliation-log appendices in v0.2.0-rc1 that document the prior
    "§4 阈值表 21 个数" wording inside before/after tables) are
    intentionally ignored — only the authoritative §13.4 assertion is
    policy-relevant. The body is therefore narrowed to the §13.4
    subsection itself, stopping at the next ``###`` subsection or
    ``##`` section header (numbered or unnumbered, e.g. 附录).

    >>> _threshold_prose_numbers_in_section13(
    ...     "## 13. X\\n### 13.4 Y\\n§4 阈值表 30 个数\\n## Appendix\\n§4 阈值表 21 个数\\n"
    ... )["matches"]
    [30]
    """

    try:
        body = _section(spec_text, r"^##\s+13\.\s")
    except RuntimeError:
        body = spec_text
    m = re.search(r"^###\s+13\.4\b", body, re.MULTILINE)
    if m:
        sub_start = m.end()
        # Narrow to §13.4 only — stop at next ### subsection or ## section
        # heading (numbered like "## 14." or unnumbered like "## 附录").
        e = re.search(r"^(###\s|##\s)", body[sub_start:], re.MULTILINE)
        sub_end = sub_start + e.start() if e else len(body)
        body = body[sub_start:sub_end]
    # Authoritative phrase only.
    pattern = re.compile(r"§?4(?:\.\d+)?\s*阈值表\s*(\d+)\s*个数")
    ints = [int(m2.group(1)) for m2 in pattern.finditer(body)]
    return {"matches": ints}


def check_threshold_table(
    spec_text: str,
    *,
    strict_prose: bool,
    spec_version: Optional[str] = None,
) -> AssertionResult:
    """Invariant 3 — THRESHOLD_TABLE: §4.1 cells + monotonicity.

    Default: 10 metrics × 3 profiles = 30 cells + strict monotonicity.

    strict_prose:
      * v0.1.0 spec: expects 21 cells (legacy prose misaligned with the
        actual 30-cell §4.1 TABLE) → FAILS.
      * v0.2.0-rc1 spec: expects 30 cells (reconciled prose) AND the
        §13.4 prose integers themselves equal 30 → PASSES.
    """

    body = _section(spec_text, r"^##\s+4\.\s")
    rows: List[Dict[str, Any]] = []
    for line in body.splitlines():
        parsed = _parse_threshold_row(line)
        if parsed:
            rows.append(parsed)

    found_metrics = [r["metric"] for r in rows]
    missing_metrics = [m for m in THRESHOLD_METRICS if m not in found_metrics]
    cells = sum(
        1 for r in rows for v in (r["v1"], r["v2"], r["v3"]) if v is not None
    )

    monotone_failures: List[str] = []
    for r in rows:
        m = r["metric"]
        v1, v2, v3 = r["v1"], r["v2"], r["v3"]
        if v1 is None or v2 is None or v3 is None:
            monotone_failures.append(f"{m}: missing numeric cell ({v1},{v2},{v3})")
            continue
        if m in BIGGER_IS_BETTER:
            if not (v1 <= v2 <= v3):
                monotone_failures.append(
                    f"{m}: bigger-is-better expects v1<=v2<=v3, got {v1},{v2},{v3}"
                )
        else:
            if not (v1 >= v2 >= v3):
                monotone_failures.append(
                    f"{m}: smaller-is-better expects v1>=v2>=v3, got {v1},{v2},{v3}"
                )

    prose_expected = EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC.get(
        spec_version or "", EXPECTED_THRESHOLD_CELLS_PROSE_DEFAULT
    )
    info_note = (
        f"INFO: §4.1 actual table is 10 metrics x 3 profiles = 30 numeric cells; "
        f"§13.4 prose under spec_version={spec_version!r} expects {prose_expected}."
    )

    if strict_prose:
        prose_integers_observed = _threshold_prose_numbers_in_section13(spec_text)["matches"]
        prose_integers_ok = all(n == prose_expected for n in prose_integers_observed)
        cells_match = cells == prose_expected
        passed = cells_match and not monotone_failures and prose_integers_ok
        msg = (
            f"strict-prose-count @ spec_version={spec_version!r}: expected={prose_expected} "
            f"cells, observed={cells} cells (cells_match={cells_match}); "
            f"§13.4 prose integers observed={prose_integers_observed} "
            f"(prose_integers_ok={prose_integers_ok}); "
            f"missing_metrics={missing_metrics}; monotone_failures={monotone_failures}. "
            f"{info_note}"
        )
    else:
        passed = (
            cells == EXPECTED_THRESHOLD_CELLS_TABLE
            and not missing_metrics
            and not monotone_failures
        )
        msg = (
            f"expected={EXPECTED_THRESHOLD_CELLS_TABLE} cells across "
            f"{len(THRESHOLD_METRICS)} metrics x 3 profiles; observed={cells} cells; "
            f"missing_metrics={missing_metrics}; monotone_failures={monotone_failures}. "
            f"{info_note}"
        )

    return AssertionResult(
        id="THRESHOLD_TABLE",
        name="§4.1 threshold table cells and monotonicity",
        passed=passed,
        severity="BLOCKER",
        message=msg,
        evidence={
            "rows": rows,
            "cells": cells,
            "missing_metrics": missing_metrics,
            "monotone_failures": monotone_failures,
            "expected_prose_cells": prose_expected,
            "spec_version": spec_version,
            "mode": "strict_prose" if strict_prose else "table",
        },
    )


def check_router_matrix_cells(templates_dir: Path) -> AssertionResult:
    """Invariant 4 — ROUTER_MATRIX_CELLS: 8 / 96 + optional 16 (intermediate).

    Accepts BOTH schema versions (backward compat):

    * ``0.1.0`` — mvp:8 + full:96 only.
    * ``0.1.1`` — mvp:8 + intermediate:16 + full:96 (Round 9 additive
      widening). When 0.1.1 is active, the intermediate invariants are
      additionally asserted:

        - ``cell_counts.intermediate == 16``
        - ``profiles.intermediate.cells == 16``
        - ``profiles.intermediate.gate_binding == "relaxed"``
          (same as mvp; NOT a §5.4 binding escalation)
        - ``len(models) * len(thinking_depths) * len(scenario_packs) == 16``
          (i.e. the cell count matches the axis multiplication)

    The mvp:8 and full:96 invariants are NEVER relaxed. Any structural
    change to mvp or full fails this invariant regardless of schema
    version.
    """

    path = templates_dir / "router_test_matrix.template.yaml"
    data = _load_yaml(path)
    if not isinstance(data, dict):
        return AssertionResult(
            id="ROUTER_MATRIX_CELLS",
            name="Router-test matrix cells are 8 (MVP) + 16 (intermediate@0.1.1) + 96 (Full) per spec §5.3",
            passed=False,
            severity="BLOCKER",
            message="template is not a YAML mapping",
            evidence={"template_path": str(path)},
        )

    schema_version = data.get("$schema_version")
    if schema_version not in SUPPORTED_ROUTER_TEMPLATE_SCHEMAS:
        return AssertionResult(
            id="ROUTER_MATRIX_CELLS",
            name="Router-test matrix cells are 8 (MVP) + 16 (intermediate@0.1.1) + 96 (Full) per spec §5.3",
            passed=False,
            severity="BLOCKER",
            message=(
                f"unsupported $schema_version {schema_version!r}; "
                f"expected one of {sorted(SUPPORTED_ROUTER_TEMPLATE_SCHEMAS)}"
            ),
            evidence={"schema_version": schema_version, "template_path": str(path)},
        )

    cell_counts = data.get("cell_counts") if isinstance(data, dict) else None
    mvp = cell_counts.get("mvp") if isinstance(cell_counts, dict) else None
    full = cell_counts.get("full") if isinstance(cell_counts, dict) else None
    passed = mvp == 8 and full == 96

    evidence: Dict[str, Any] = {
        "schema_version": schema_version,
        "mvp": mvp,
        "full": full,
        "template_path": str(path),
    }

    # Round 9 intermediate invariants (schema 0.1.1 only).
    intermediate_invariants: Dict[str, Any] = {}
    if schema_version == "0.1.1":
        intermediate_cells = (
            cell_counts.get("intermediate") if isinstance(cell_counts, dict) else None
        )
        profiles = data.get("profiles") if isinstance(data, dict) else None
        intermediate_profile = (
            profiles.get("intermediate") if isinstance(profiles, dict) else None
        )
        cells_in_profile: Optional[int] = None
        gate_binding: Optional[str] = None
        axis_product: Optional[int] = None
        if isinstance(intermediate_profile, dict):
            cells_in_profile = intermediate_profile.get("cells")
            gate_binding = intermediate_profile.get("gate_binding")
            models = intermediate_profile.get("models") or []
            depths = intermediate_profile.get("thinking_depths") or []
            packs = intermediate_profile.get("scenario_packs") or []
            if (
                isinstance(models, list)
                and isinstance(depths, list)
                and isinstance(packs, list)
            ):
                axis_product = len(models) * len(depths) * len(packs)

        intermediate_invariants = {
            "cell_counts_intermediate": intermediate_cells,
            "profile_cells": cells_in_profile,
            "profile_gate_binding": gate_binding,
            "profile_axis_product": axis_product,
        }
        evidence["intermediate"] = intermediate_invariants

        intermediate_ok = (
            intermediate_cells == EXPECTED_INTERMEDIATE_CELLS
            and cells_in_profile == EXPECTED_INTERMEDIATE_CELLS
            and gate_binding == EXPECTED_INTERMEDIATE_GATE_BINDING
            and axis_product == EXPECTED_INTERMEDIATE_CELLS
        )
        passed = passed and intermediate_ok

        message = (
            f"schema={schema_version}: expected mvp=8 full=96 "
            f"intermediate=16 (gate_binding=relaxed; models*depths*packs=16), "
            f"observed mvp={mvp} full={full} intermediate={intermediate_invariants}"
        )
    else:  # schema 0.1.0
        message = (
            f"schema={schema_version}: expected mvp=8 full=96, "
            f"observed mvp={mvp} full={full}"
        )

    return AssertionResult(
        id="ROUTER_MATRIX_CELLS",
        name="Router-test matrix cells are 8 (MVP) + 16 (intermediate@0.1.1) + 96 (Full) per spec §5.3",
        passed=passed,
        severity="BLOCKER",
        message=message,
        evidence=evidence,
    )


def check_value_vector_axes(templates_dir: Path) -> AssertionResult:
    """Invariant 5 — VALUE_VECTOR_AXES: exactly 7 §6.1 axes."""

    path = templates_dir / "half_retire_decision.template.yaml"
    data = _load_yaml(path)
    try:
        axes_props = data["schema"]["value_vector"]["properties"]
    except (KeyError, TypeError) as exc:
        return AssertionResult(
            id="VALUE_VECTOR_AXES",
            name="Value vector has 7 axes per spec §6.1",
            passed=False,
            severity="BLOCKER",
            message=f"template missing schema.value_vector.properties: {exc}",
            evidence={"template_path": str(path)},
        )
    actual = set(axes_props.keys())
    missing = sorted(EXPECTED_VALUE_VECTOR_AXES - actual)
    extra = sorted(actual - EXPECTED_VALUE_VECTOR_AXES)
    passed = not missing and not extra and len(actual) == 7
    return AssertionResult(
        id="VALUE_VECTOR_AXES",
        name="Value vector has 7 axes per spec §6.1",
        passed=passed,
        severity="BLOCKER",
        message=(
            f"expected={sorted(EXPECTED_VALUE_VECTOR_AXES)} actual={sorted(actual)} "
            f"missing={missing} extra={extra}"
        ),
        evidence={"missing": missing, "extra": extra, "actual": sorted(actual)},
    )


def check_platform_priority(spec_text: str) -> AssertionResult:
    """Invariant 6 — PLATFORM_PRIORITY: Cursor → Claude Code → Codex order."""

    body = _section(spec_text, r"^##\s+7\.\s")
    sub = _subsection(body, r"^###\s+7\.2\b")
    cursor_pos = sub.find("Cursor")
    claude_pos = sub.find("Claude Code")
    codex_pos = sub.find("Codex")
    in_order = (
        cursor_pos != -1
        and claude_pos != -1
        and codex_pos != -1
        and cursor_pos < claude_pos < codex_pos
    )
    return AssertionResult(
        id="PLATFORM_PRIORITY",
        name="§7.2 platform priority is Cursor -> Claude Code -> Codex",
        passed=in_order,
        severity="BLOCKER",
        message=(
            f"positions cursor={cursor_pos} claude_code={claude_pos} codex={codex_pos};"
            f" in_order={in_order}"
        ),
        evidence={
            "cursor_pos": cursor_pos,
            "claude_code_pos": claude_pos,
            "codex_pos": codex_pos,
        },
    )


_DOGFOOD_STEP_RE = re.compile(
    r"^(?P<num>\d+)\.\s+`?(?P<step>[a-z][a-z\-_]*)`?\b",
    re.MULTILINE,
)


def check_dogfood_protocol(spec_text: str) -> AssertionResult:
    """Invariant 7 — DOGFOOD_PROTOCOL: §8.1 8 steps + §8.2 6 evidence files."""

    sec8 = _section(spec_text, r"^##\s+8\.\s")
    sub_steps = _subsection(sec8, r"^###\s+8\.1\b")
    sub_evidence = _subsection(sec8, r"^###\s+8\.2\b")

    found_steps: List[str] = []
    for m in _DOGFOOD_STEP_RE.finditer(sub_steps):
        step = m.group("step")
        if step in EXPECTED_DOGFOOD_STEPS and step not in found_steps:
            found_steps.append(step)

    steps_ok = found_steps == EXPECTED_DOGFOOD_STEPS

    evidence_found: List[str] = []
    for ev in EXPECTED_EVIDENCE_FILES:
        if re.search(re.escape(ev), sub_evidence):
            evidence_found.append(ev)
    evidence_ok = sorted(evidence_found) == sorted(EXPECTED_EVIDENCE_FILES)

    passed = steps_ok and evidence_ok
    return AssertionResult(
        id="DOGFOOD_PROTOCOL",
        name="§8.1 8 ordered steps + §8.2 6 evidence files",
        passed=passed,
        severity="BLOCKER",
        message=(
            f"steps expected={EXPECTED_DOGFOOD_STEPS}, observed={found_steps}; "
            f"evidence expected={EXPECTED_EVIDENCE_FILES}, observed={evidence_found}"
        ),
        evidence={
            "expected_steps": EXPECTED_DOGFOOD_STEPS,
            "observed_steps": found_steps,
            "expected_evidence": EXPECTED_EVIDENCE_FILES,
            "observed_evidence": evidence_found,
        },
    )


def check_reactivation_detector_exists(
    repo_root: Optional[Path] = None,
) -> AssertionResult:
    """Invariant 9 — REACTIVATION_DETECTOR_EXISTS: §6.4 detector + 6 IDs.

    Round 12 (Si-Chip v0.1.11) BLOCKER. Asserts that:

    * ``tools/reactivation_detector.py`` exists.
    * Its source contains every one of the 6 §6.4 trigger IDs verbatim
      (the runtime contract — automated readers map detector verdict
      names back to spec §6.4 prose).
    * Its sibling test file ``tools/test_reactivation_detector.py``
      exists.
    * The test file contains at least one test class / test name per
      trigger ID (per workspace rule "Mandatory Verification" — every
      new code path must carry tests).

    The check operates against the repo's source tree on disk; missing
    files OR a missing trigger ID OR a missing test reference is a
    BLOCKER fail (no silent acceptance).

    Args:
        repo_root: Override the repo root. Defaults to the parent of
            this file's parent (i.e. the workspace root).

    Returns:
        :class:`AssertionResult` with ``id="REACTIVATION_DETECTOR_EXISTS"``.
    """

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    detector = repo_root / REACTIVATION_DETECTOR_PATH
    test = repo_root / REACTIVATION_DETECTOR_TEST_PATH

    detector_exists = detector.exists() and detector.is_file()
    test_exists = test.exists() and test.is_file()
    missing_in_detector: List[str] = []
    missing_in_tests: List[str] = []

    detector_text = ""
    test_text = ""
    if detector_exists:
        try:
            detector_text = detector.read_text(encoding="utf-8")
        except OSError as exc:
            return AssertionResult(
                id="REACTIVATION_DETECTOR_EXISTS",
                name=(
                    "tools/reactivation_detector.py exists and references "
                    "all 6 §6.4 trigger IDs (Round 12)"
                ),
                passed=False,
                severity="BLOCKER",
                message=f"detector unreadable: {exc}",
                evidence={"detector_path": str(detector)},
            )
        for tid in EXPECTED_REACTIVATION_TRIGGER_IDS:
            if tid not in detector_text:
                missing_in_detector.append(tid)
    if test_exists:
        try:
            test_text = test.read_text(encoding="utf-8")
        except OSError as exc:
            return AssertionResult(
                id="REACTIVATION_DETECTOR_EXISTS",
                name=(
                    "tools/reactivation_detector.py exists and references "
                    "all 6 §6.4 trigger IDs (Round 12)"
                ),
                passed=False,
                severity="BLOCKER",
                message=f"test file unreadable: {exc}",
                evidence={"test_path": str(test)},
            )
        for tid in EXPECTED_REACTIVATION_TRIGGER_IDS:
            # Each trigger must be referenced in the test file SOMEWHERE
            # (test class name, test method name, or test body) — at
            # least 1 test per trigger.
            if tid not in test_text:
                missing_in_tests.append(tid)

    passed = (
        detector_exists
        and test_exists
        and not missing_in_detector
        and not missing_in_tests
    )
    msg_parts: List[str] = []
    if not detector_exists:
        msg_parts.append(f"missing detector: {detector}")
    if not test_exists:
        msg_parts.append(f"missing tests: {test}")
    if missing_in_detector:
        msg_parts.append(f"trigger IDs missing in detector: {missing_in_detector}")
    if missing_in_tests:
        msg_parts.append(f"trigger IDs missing in tests: {missing_in_tests}")
    msg = "; ".join(msg_parts) if msg_parts else (
        f"detector + tests exist; all {len(EXPECTED_REACTIVATION_TRIGGER_IDS)} §6.4 "
        "trigger IDs referenced verbatim in both"
    )
    return AssertionResult(
        id="REACTIVATION_DETECTOR_EXISTS",
        name=(
            "tools/reactivation_detector.py exists and references "
            "all 6 §6.4 trigger IDs (Round 12)"
        ),
        passed=passed,
        severity="BLOCKER",
        message=msg,
        evidence={
            "detector_path": str(detector),
            "test_path": str(test),
            "expected_trigger_ids": list(EXPECTED_REACTIVATION_TRIGGER_IDS),
            "missing_in_detector": missing_in_detector,
            "missing_in_tests": missing_in_tests,
            "detector_exists": detector_exists,
            "test_exists": test_exists,
        },
    )


def check_forever_out_list(spec_text: str) -> AssertionResult:
    """Invariant 8 — FOREVER_OUT_LIST: §11.1 four items present."""

    sec11 = _section(spec_text, r"^##\s+11\.\s")
    sub = _subsection(sec11, r"^###\s+11\.1\b")
    found_ids: List[str] = []
    missing: List[str] = []
    for group in FOREVER_OUT_GROUPS:
        if any(kw in sub for kw in group["keywords"]):
            found_ids.append(group["id"])
        else:
            missing.append(group["id"])
    passed = not missing
    return AssertionResult(
        id="FOREVER_OUT_LIST",
        name="§11.1 forever-out list contains 4 required items",
        passed=passed,
        severity="BLOCKER",
        message=(
            f"expected={[g['id'] for g in FOREVER_OUT_GROUPS]} found={found_ids} "
            f"missing={missing}"
        ),
        evidence={"found": found_ids, "missing": missing},
    )


def check_core_goal_field_present(templates_dir: Path) -> AssertionResult:
    """Invariant 10 — CORE_GOAL_FIELD_PRESENT (v0.3.0 §14).

    Asserts the BasicAbilityProfile schema declares a REQUIRED
    ``core_goal`` block per spec v0.3.0-rc1 §14.1.1, with at least the
    three ``required`` sub-fields ``statement`` / ``test_pack_path`` /
    ``minimum_pass_rate`` and ``minimum_pass_rate.const == 1.0`` (spec
    §14.3 lock).

    The check runs only when the schema's own ``$schema_version >=
    "0.2.0"``. For ``0.1.0`` schemas (legacy / pre-v0.3.0) it returns
    PASS-as-SKIP with ``evidence.skipped_reason = "schema_pre_v0_3_0"``.
    This preserves backward-compat with any historical artefact that
    pinned the 10-key BAP shape.

    Failure modes (BLOCKER FAIL):

    * ``core_goal`` block missing from
      ``properties.basic_ability.properties``.
    * ``core_goal.required`` lacks ``statement`` / ``test_pack_path`` /
      ``minimum_pass_rate``.
    * ``core_goal.properties.minimum_pass_rate.const`` is absent or not
      exactly ``1.0`` (any value < 1.0 violates spec §14.3).
    * ``basic_ability.required`` does not list ``core_goal``.

    See also: spec v0.3.0-rc1 §13.5.4 ("BLOCKER 1"), §14.1.1 (schema
    sketch), §14.3 (strict ``MUST = 1.0``).
    """

    schema_path = templates_dir / "basic_ability_profile.schema.yaml"
    schema = _load_yaml(schema_path)
    schema_version = _read_schema_version(schema)
    if schema_version < "0.2.0":
        return AssertionResult(
            id="CORE_GOAL_FIELD_PRESENT",
            name="basic_ability.core_goal block present with §14 schema (v0.3.0+ only)",
            passed=True,
            severity="BLOCKER",
            message=(
                f"schema $schema_version={schema_version} predates v0.3.0; "
                "core_goal not required (legacy compat)."
            ),
            evidence={
                "schema_path": str(schema_path),
                "schema_version": schema_version,
                "skipped_reason": "schema_pre_v0_3_0",
            },
        )

    findings: List[str] = []
    try:
        bap = schema["properties"]["basic_ability"]
    except (KeyError, TypeError) as exc:
        return AssertionResult(
            id="CORE_GOAL_FIELD_PRESENT",
            name="basic_ability.core_goal block present with §14 schema",
            passed=False,
            severity="BLOCKER",
            message=f"schema missing properties.basic_ability: {exc}",
            evidence={
                "schema_path": str(schema_path),
                "schema_version": schema_version,
            },
        )
    bap_required = bap.get("required") or []
    properties = bap.get("properties") or {}
    cg = properties.get("core_goal")
    if cg is None:
        findings.append("core_goal block missing from basic_ability.properties")
    else:
        cg_required = set(cg.get("required") or [])
        for required in ("statement", "test_pack_path", "minimum_pass_rate"):
            if required not in cg_required:
                findings.append(f"core_goal.required missing '{required}'")
        cg_props = cg.get("properties") or {}
        mpr = cg_props.get("minimum_pass_rate") or {}
        if mpr.get("const") != 1.0:
            findings.append(
                "core_goal.minimum_pass_rate.const != 1.0 "
                f"(got {mpr.get('const')!r}; spec §14.3 lock)"
            )
        if "core_goal" not in bap_required:
            findings.append("basic_ability.required does not list core_goal")

    if findings:
        return AssertionResult(
            id="CORE_GOAL_FIELD_PRESENT",
            name="basic_ability.core_goal block present with §14 schema",
            passed=False,
            severity="BLOCKER",
            message="; ".join(findings),
            evidence={
                "schema_path": str(schema_path),
                "schema_version": schema_version,
                "findings": findings,
            },
        )
    return AssertionResult(
        id="CORE_GOAL_FIELD_PRESENT",
        name="basic_ability.core_goal block present with §14 schema",
        passed=True,
        severity="BLOCKER",
        message=(
            f"$schema_version={schema_version}: core_goal block present with "
            "{statement, test_pack_path, minimum_pass_rate} REQUIRED and "
            "minimum_pass_rate.const == 1.0; basic_ability.required lists "
            "core_goal."
        ),
        evidence={
            "schema_path": str(schema_path),
            "schema_version": schema_version,
            "core_goal_required": sorted(set(cg.get("required") or [])),
        },
    )


# Templates that MUST declare round_kind when their $schema_version >= 0.2.0.
# Both surface a per-round round_kind classification to spec §15.1; the
# template-level invariant is that the field is declared (in `required_fields`,
# `schema`, or `example_instance`) and any concrete value present matches the
# 4-value enum frozen in tools/round_kind.ROUND_KINDS.
ROUND_KIND_TEMPLATES = (
    "iteration_delta_report.template.yaml",
    "next_action_plan.template.yaml",
)


def _round_kind_template_findings(
    template_path: Path,
) -> Tuple[List[str], Dict[str, Any]]:
    """Inspect one template for the round_kind invariant.

    Returns ``(findings, debug_evidence)``. Findings is empty on PASS;
    one or more strings on FAIL. ``debug_evidence`` carries the parsed
    ``schema_version``, the declared ``required_fields`` (if any), and
    any concrete ``round_kind`` value found in ``example_instance``.

    Skip semantics: when the template's own version is < ``0.2.0``,
    findings is empty and ``debug_evidence["skipped_reason"]`` is set.
    """

    if not template_path.exists():
        return [f"{template_path.name} not found"], {
            "template_path": str(template_path),
            "exists": False,
        }
    data = _load_yaml(template_path)
    if not isinstance(data, dict):
        return [f"{template_path.name}: template is not a YAML mapping"], {
            "template_path": str(template_path),
        }

    # Accept either ``$schema_version`` (preferred) or legacy
    # ``template_version`` (older templates may emit only this).
    schema_v_raw = (
        data.get("$schema_version")
        or data.get("template_version")
        or "0.1.0"
    )
    schema_v = str(schema_v_raw)
    debug: Dict[str, Any] = {
        "template_path": str(template_path),
        "schema_version": schema_v,
    }
    if schema_v < "0.2.0":
        debug["skipped_reason"] = "template_pre_v0_2_0"
        return [], debug

    # Locate every place where ``round_kind`` may be declared:
    #   * top-level ``round_kind:`` (concrete instance)
    #   * ``required_fields:`` list mention
    #   * ``schema.round_kind`` block
    #   * ``example_instance.round_kind`` (concrete value)
    # The invariant requires AT LEAST one of declaration-paths AND a
    # valid concrete value if any is supplied.
    findings: List[str] = []
    declared_in_required = (
        "round_kind" in (data.get("required_fields") or [])
    )
    declared_in_schema = (
        isinstance(data.get("schema"), dict)
        and "round_kind" in data["schema"]
    )
    example = data.get("example_instance") or {}
    declared_in_example = (
        isinstance(example, dict) and "round_kind" in example
    )
    debug.update(
        {
            "declared_in_required": declared_in_required,
            "declared_in_schema": declared_in_schema,
            "declared_in_example": declared_in_example,
        }
    )
    if not (
        declared_in_required or declared_in_schema or declared_in_example
    ):
        findings.append(
            f"{template_path.name}: round_kind field missing"
        )
        return findings, debug

    # Validate the concrete example value (if present).
    example_value = (
        example.get("round_kind") if isinstance(example, dict) else None
    )
    if example_value is not None:
        debug["example_round_kind"] = example_value
        if not validate_round_kind(example_value):
            findings.append(
                f"{template_path.name}: round_kind={example_value!r} "
                f"not in {sorted(ROUND_KINDS)}"
            )

    # Validate any enum declared inside ``schema.round_kind.enum`` is a
    # subset of ROUND_KINDS (spec §15.1.1 freeze; templates may not
    # widen the enum).
    if declared_in_schema:
        rk_block = data["schema"]["round_kind"]
        if isinstance(rk_block, dict):
            enum_values = rk_block.get("enum")
            if isinstance(enum_values, list):
                debug["schema_enum"] = list(enum_values)
                bogus = [v for v in enum_values if not validate_round_kind(v)]
                if bogus:
                    findings.append(
                        f"{template_path.name}: schema.round_kind.enum has "
                        f"non-spec values {bogus}; "
                        f"must be subset of {sorted(ROUND_KINDS)}"
                    )

    return findings, debug


def check_round_kind_template_valid(templates_dir: Path) -> AssertionResult:
    """Invariant 11 — ROUND_KIND_TEMPLATE_VALID (v0.3.0 §15).

    Asserts that the two round-kind-bearing templates
    (``iteration_delta_report.template.yaml`` and
    ``next_action_plan.template.yaml``) declare a ``round_kind`` field
    when their own ``$schema_version >= "0.2.0"``, and that any concrete
    ``round_kind`` value in their ``example_instance`` is a member of
    ``tools.round_kind.ROUND_KINDS`` — the 4-value enum frozen at spec
    §15.1.1: ``code_change`` / ``measurement_only`` / ``ship_prep`` /
    ``maintenance``.

    Skip semantics: a template whose ``$schema_version < "0.2.0"`` is
    treated as PASS-as-SKIP with ``evidence.skipped_reason =
    "template_pre_v0_2_0"`` per the v0.2.0-compat contract.

    Failure modes (BLOCKER FAIL):

    * Template file missing from ``templates_dir``.
    * v0.2.0+ template missing the ``round_kind`` field altogether.
    * Template carries a concrete ``round_kind`` value not in
      ``ROUND_KINDS``.
    * Template's ``schema.round_kind.enum`` widens past
      ``ROUND_KINDS`` (spec §15.1.1 freeze prohibits this).

    See also: spec v0.3.0-rc1 §13.5.4 ("BLOCKER 2"), §15.1.1 (4-value
    enum), §17.2 (rule 10 binding).
    """

    findings_all: List[str] = []
    per_template: Dict[str, Any] = {}
    for tname in ROUND_KIND_TEMPLATES:
        tpath = templates_dir / tname
        findings, debug = _round_kind_template_findings(tpath)
        per_template[tname] = debug
        findings_all.extend(findings)

    if findings_all:
        return AssertionResult(
            id="ROUND_KIND_TEMPLATE_VALID",
            name=(
                "iteration_delta_report + next_action_plan templates declare "
                "round_kind from §15.1.1 4-value enum"
            ),
            passed=False,
            severity="BLOCKER",
            message="; ".join(findings_all),
            evidence={
                "templates_dir": str(templates_dir),
                "expected_enum": sorted(ROUND_KINDS),
                "per_template": per_template,
                "findings": findings_all,
            },
        )
    return AssertionResult(
        id="ROUND_KIND_TEMPLATE_VALID",
        name=(
            "iteration_delta_report + next_action_plan templates declare "
            "round_kind from §15.1.1 4-value enum"
        ),
        passed=True,
        severity="BLOCKER",
        message=(
            f"both round_kind templates valid against §15.1.1 enum "
            f"{sorted(ROUND_KINDS)}; "
            f"per-template status={per_template}"
        ),
        evidence={
            "templates_dir": str(templates_dir),
            "expected_enum": sorted(ROUND_KINDS),
            "per_template": per_template,
        },
    )


# ─────────────────────────── runner ───────────────────────────


def run_all(
    spec_path: Path,
    templates_dir: Path,
    *,
    strict_prose: bool,
    repo_root: Optional[Path] = None,
) -> ValidationReport:
    """Execute every invariant in declared order.

    Stage 4 Wave 2a (v0.3.0-rc1) widens the BLOCKER set to **eleven**:
    the 9 historical invariants plus ``CORE_GOAL_FIELD_PRESENT`` (spec
    §14) and ``ROUND_KIND_TEMPLATE_VALID`` (spec §15). The two new
    BLOCKERs branch on the schema/template's own ``$schema_version``;
    pre-v0.3.0 inputs return PASS-as-SKIP. Total order:

    1. ``BAP_SCHEMA``
    2. ``R6_KEYS``
    3. ``THRESHOLD_TABLE``
    4. ``ROUTER_MATRIX_CELLS``
    5. ``VALUE_VECTOR_AXES``
    6. ``PLATFORM_PRIORITY``
    7. ``DOGFOOD_PROTOCOL``
    8. ``FOREVER_OUT_LIST``
    9. ``REACTIVATION_DETECTOR_EXISTS``
    10. ``CORE_GOAL_FIELD_PRESENT`` *(NEW @ Stage 4 Wave 2a)*
    11. ``ROUND_KIND_TEMPLATE_VALID`` *(NEW @ Stage 4 Wave 2a)*
    """

    spec_text = _read_text(spec_path)
    spec_version = detect_spec_version(spec_text)
    if repo_root is None:
        # Templates dir is conventionally at <repo_root>/templates;
        # walk one level up to recover the repo root.
        repo_root = templates_dir.resolve().parent
    results: List[AssertionResult] = [
        check_bap_schema(templates_dir),
        check_r6_keys(
            templates_dir,
            strict_prose=strict_prose,
            spec_version=spec_version,
            spec_text=spec_text,
        ),
        check_threshold_table(
            spec_text,
            strict_prose=strict_prose,
            spec_version=spec_version,
        ),
        check_router_matrix_cells(templates_dir),
        check_value_vector_axes(templates_dir),
        check_platform_priority(spec_text),
        check_dogfood_protocol(spec_text),
        check_forever_out_list(spec_text),
        check_reactivation_detector_exists(repo_root=repo_root),
        check_core_goal_field_present(templates_dir),
        check_round_kind_template_valid(templates_dir),
    ]
    verdict = "PASS" if all(r.passed for r in results) else "FAIL"
    return ValidationReport(
        verdict=verdict,
        results=results,
        spec_path=str(spec_path),
        ran_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Static structural validator for the Si-Chip spec. Runs 11 "
            "BLOCKERs (9 historical + 2 v0.3.0 additive: "
            "CORE_GOAL_FIELD_PRESENT and ROUND_KIND_TEMPLATE_VALID)."
        ),
    )
    parser.add_argument(
        "--spec",
        default=DEFAULT_SPEC,
        help=(
            f"Path to spec markdown (default: {DEFAULT_SPEC}). "
            "Latest accepted spec version is v0.3.0-rc1 "
            "(`.local/research/spec_v0.3.0-rc1.md`); v0.2.0 / v0.2.0-rc1 / "
            "v0.1.0 remain accepted for historical artefact regression."
        ),
    )
    parser.add_argument(
        "--templates-dir",
        default=DEFAULT_TEMPLATES_DIR,
        help=f"Templates directory (default: {DEFAULT_TEMPLATES_DIR}).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARNING findings as failures (currently no WARNING-level invariants are emitted).",
    )
    parser.add_argument(
        "--strict-prose-count",
        action="store_true",
        help=(
            "Enforce spec §13.4 prose counts: v0.2.0 / v0.2.0-rc1 / v0.3.0-rc1 "
            "expect 37 sub-metrics + 30 threshold cells (post-Round-11 "
            "reconciliation; v0.3.0-rc1 §13.4 is byte-identical to v0.2.0); "
            "v0.1.0 expects 28 + 21 (legacy; validator preserves the mode "
            "for historical regression). Spec version is auto-detected from "
            "frontmatter."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON report on stdout.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set log level to INFO.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    spec_path = Path(args.spec).resolve()
    templates_dir = Path(args.templates_dir).resolve()

    report = run_all(
        spec_path,
        templates_dir,
        strict_prose=args.strict_prose_count,
    )

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False))
    else:
        for r in report.results:
            print(f"[{r.severity}] {r.id}: passed={r.passed} msg={r.message}")
        print(f"verdict: {report.verdict}")

    if report.verdict == "PASS":
        if args.strict and any(
            r.severity == "WARNING" and not r.passed for r in report.results
        ):
            return 1
        return 0
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.spec_validator").error("fatal: %s", exc)
        raise
