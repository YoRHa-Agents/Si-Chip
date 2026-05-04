#!/usr/bin/env python3
"""Static structural validator for the Si-Chip spec.

Implements the **fifteen** machine-checkable invariants declared across
spec §13.4 (v0.2.0 — 9 BLOCKERs), §13.5.4 (v0.3.0-rc1 — 2 additive
BLOCKERs), §13.6.4 (v0.4.0-rc1 — 3 additive BLOCKERs) and §24.1.1
(v0.4.2-rc1 — 1 additive BLOCKER). Round 12 (Si-Chip v0.1.11) added
the 9th BLOCKER ``REACTIVATION_DETECTOR_EXISTS``. Stage 4 Wave 2a
(v0.3.0-rc1, 2026-04-29) added the 10th (``CORE_GOAL_FIELD_PRESENT``)
and 11th (``ROUND_KIND_TEMPLATE_VALID``). Stage 4 Wave 1b (v0.4.0-rc1,
2026-04-30) added the 12th, 13th and 14th. Stage 4 Wave 1d (v0.4.2-rc1,
2026-05-05) adds the 15th:

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
* ``TOKEN_TIER_DECLARED_WHEN_REPORTED`` (v0.4.0 §18.1) — asserts that
  any ``metrics_report.yaml`` reporting C7/C8/C9 token-tier axes also
  declares the top-level ``token_tier`` block with all three fields
  (null placeholders allowed). Skipped as PASS when no reporting is
  found (abilities that haven't adopted §18 yet).
* ``REAL_DATA_FIXTURE_PROVENANCE`` (v0.4.0 §19.3) — asserts that any
  ability declaring entries in ``feedback_real_data_samples.yaml`` has
  grep-able ``real-data sample provenance`` comments in its test
  fixtures. Skipped when no real_data_samples.yaml exists.
* ``HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`` (v0.4.0 §21.2) — asserts
  that every BasicAbilityProfile with
  ``current_surface.dependencies.live_backend: true`` also carries a
  non-empty ``packaging.health_smoke_check`` array. Skipped when no
  profile declares live_backend.
* ``DESCRIPTION_CAP_1024`` (v0.4.2 §24.1) — asserts that every
  ``SKILL.md`` frontmatter ``description`` (across the
  ``.agents/skills/``, ``.cursor/skills/`` and ``.claude/skills/``
  trees) and every ``basic_ability_profile.yaml``'s
  ``basic_ability.description`` (or fallback ``basic_ability.intent``)
  satisfies ``min(len(s), len(s.encode('utf-8'))) <= 1024``. Skipped
  as PASS when no SKILL.md / BAP files exist OR when the validated
  spec lacks the §24 marker (pre-v0.4.2 backward compat per §13.6.4
  grace period).

Spec path defaults to ``.local/research/spec_v0.2.0.md`` (Si-Chip v0.2.0
ship, 2026-04-28; promoted from v0.2.0-rc1 with no Normative semantic
change). §13.4 prose counts remain aligned with the §3.1 / §4.1 TABLES
(37 sub-metrics / 30 threshold cells). Spec v0.2.0-rc1 is also accepted
via ``--spec .local/research/spec_v0.2.0-rc1.md`` (pinned historical
record). Spec v0.1.0 remains accepted via
``--spec .local/research/spec_v0.1.0.md`` for backward-compat
verification of Rounds 1–10 artefacts. Spec v0.3.0-rc1 / v0.3.0 /
v0.4.0-rc1 are each accepted via ``--spec .local/research/…``; the
default spec flip remains at L0 step 8 (final ship), not in this stage.

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
# 0.3.0 — Stage 4 Wave 1b (v0.4.0-rc1): accepts spec v0.4.0-rc1 alongside
# earlier versions; adds 3 new BLOCKERs TOKEN_TIER_DECLARED_WHEN_REPORTED,
# REAL_DATA_FIXTURE_PROVENANCE, HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND;
# version-aware EXPECTED_VALUE_VECTOR_AXES_BY_SPEC (7 axes ≤ v0.3.0;
# 8 axes @ v0.4.0-rc1 with eager_token_delta); R6_KEYS ignores §23
# method-tag companion suffixes; EVIDENCE_FILES is round_kind-aware
# (7 files when round_kind == 'ship_prep', else 6); 0.3.0 schema key
# bucket mirrors 0.2.0 (additive sub-fields don't change top-level set).
# 0.4.0 — Stage 4 Wave 1d (v0.4.2-rc1, 2026-05-05): accepts spec
# v0.4.2-rc1 alongside earlier versions; adds 1 new BLOCKER
# DESCRIPTION_CAP_1024 (§24.1; absorbed from addyosmani/agent-skills
# v1.0.0 docs/skill-anatomy.md 1024-char description cap convention).
# Skipped as PASS when the spec being validated lacks the §24 marker
# (pre-v0.4.2 backward compat per §13.6.4 grace period). Top-level
# spec / schema layout unchanged from 0.3.0; this is purely additive.
SCRIPT_VERSION = "0.4.0"

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
# v0.4.0-rc1 added Stage 4 Wave 1b (2026-04-30); v0.3.0 + v0.4.0 listed
# so a later ship-time default flip (L0 step 8) is a no-op for callers.
SUPPORTED_SPEC_VERSIONS = {
    "v0.1.0",
    "v0.2.0-rc1",
    "v0.2.0",
    "v0.3.0-rc1",
    "v0.3.0",
    "v0.4.0-rc1",
    "v0.4.0",
    "v0.4.2-rc1",
}

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
# 0.3.0 — additive: v0.4.0-rc1 adds OPTIONAL sub-fields on existing
#         top-level keys (lifecycle.promotion_history,
#         current_surface.dependencies.live_backend,
#         packaging.health_smoke_check, metrics.<dim>._method companions).
#         Top-level key set is IDENTICAL to 0.2.0 — no new entries in
#         basic_ability.required. Round 14+ profiles validate against
#         this key set; legacy Round 1-13 profiles continue to validate
#         against the 0.1.0 key set.
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
    "0.3.0": {
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
#   v0.3.0:      prose claimed 37 (promoted from v0.3.0-rc1; ship)
#   v0.4.0-rc1:  prose claimed 37 (§13.4 byte-identical to v0.3.0; v0.4.0
#                                  add-on lives in §13.6.4 instead —
#                                  §23 method-tag companions are NOT counted
#                                  as sub-metrics per §23.6; §18 token-tier
#                                  is top-level invariant NOT a sub-metric)
#   v0.4.0:      prose claimed 37 (inherits v0.4.0-rc1 when promoted)
# strict-prose-count mode picks the correct expected value from this map
# using the spec's own version frontmatter.
EXPECTED_R6_PROSE_BY_SPEC = {
    "v0.1.0": 28,
    "v0.2.0-rc1": 37,
    "v0.2.0": 37,
    "v0.3.0-rc1": 37,
    "v0.3.0": 37,
    "v0.4.0-rc1": 37,
    "v0.4.0": 37,
    "v0.4.2-rc1": 37,
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
#   v0.3.0:      prose claimed 30 (promoted from v0.3.0-rc1; ship)
#   v0.4.0-rc1:  prose claimed 30 (§13.4 byte-identical to v0.3.0;
#                                  only §6.1 value_vector axes count changes
#                                  from 7 → 8 per §13.6.4, NOT threshold cells)
#   v0.4.0:      prose claimed 30 (inherits v0.4.0-rc1 when promoted)
EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC = {
    "v0.1.0": 21,
    "v0.2.0-rc1": 30,
    "v0.2.0": 30,
    "v0.3.0-rc1": 30,
    "v0.3.0": 30,
    "v0.4.0-rc1": 30,
    "v0.4.0": 30,
    "v0.4.2-rc1": 30,
}
EXPECTED_THRESHOLD_CELLS_PROSE_DEFAULT = EXPECTED_THRESHOLD_CELLS_PROSE_BY_SPEC["v0.2.0"]

# §6.1 value vector axes — version-keyed dict.
# v0.1.0 → v0.3.0 (inclusive): 7 axes.
# v0.4.0-rc1+: 8 axes (adds ``eager_token_delta`` per §6.1 v0.4.0 modification).
# The 7 → 8 break is the FIRST byte-identicality break since v0.1.0 →
# v0.2.0 prose-count alignment (per Reconciliation Log entry (c)).
#
# Lookup pattern mirrors EXPECTED_BAP_KEYS_BY_SCHEMA (version-aware) but
# keys on --spec version, NOT on template $schema_version. Rationale:
# half_retire_decision.template.yaml stays at v0.1.0 schema (spec §9 add-on
# marks it UNCHANGED); the 8th axis appears in
# iteration_delta_report.template.yaml example_instance.axis_status
# (§6.1 + §18.6 — tier_transitions). Check consults both templates when
# --spec >= v0.4.0-rc1.
EXPECTED_VALUE_VECTOR_AXES_BASE: Set[str] = {
    "task_delta",
    "token_delta",
    "latency_delta",
    "context_delta",
    "path_efficiency_delta",
    "routing_delta",
    "governance_risk_delta",
}
EXPECTED_VALUE_VECTOR_AXES_V0_4_0: Set[str] = (
    EXPECTED_VALUE_VECTOR_AXES_BASE | {"eager_token_delta"}
)

EXPECTED_VALUE_VECTOR_AXES_BY_SPEC: Dict[str, Set[str]] = {
    "v0.1.0": EXPECTED_VALUE_VECTOR_AXES_BASE,
    "v0.2.0-rc1": EXPECTED_VALUE_VECTOR_AXES_BASE,
    "v0.2.0": EXPECTED_VALUE_VECTOR_AXES_BASE,
    "v0.3.0-rc1": EXPECTED_VALUE_VECTOR_AXES_BASE,
    "v0.3.0": EXPECTED_VALUE_VECTOR_AXES_BASE,
    "v0.4.0-rc1": EXPECTED_VALUE_VECTOR_AXES_V0_4_0,
    "v0.4.0": EXPECTED_VALUE_VECTOR_AXES_V0_4_0,
    "v0.4.2-rc1": EXPECTED_VALUE_VECTOR_AXES_V0_4_0,
}

# Default fallback: the legacy 7-axis set (v0.3.0 ship default). This
# keeps ``check_value_vector_axes`` backward-compat when spec version
# cannot be detected.
EXPECTED_VALUE_VECTOR_AXES = EXPECTED_VALUE_VECTOR_AXES_BASE

# §6.1 prose axis count per spec version (mirrors the TABLE semantics
# above but exposes a scalar for strict-prose-count callers).
EXPECTED_VALUE_VECTOR_PROSE_BY_SPEC: Dict[str, int] = {
    "v0.1.0": 7,
    "v0.2.0-rc1": 7,
    "v0.2.0": 7,
    "v0.3.0-rc1": 7,
    "v0.3.0": 7,
    "v0.4.0-rc1": 8,
    "v0.4.0": 8,
    "v0.4.2-rc1": 8,
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

# §8.2 minimum evidence files (6; v0.4.0 add: +1 ship_decision when
# next_action_plan.round_kind == 'ship_prep').
EXPECTED_EVIDENCE_FILES = [
    "BasicAbilityProfile",
    "metrics_report",
    "router_floor_report",
    "half_retire_decision",
    "next_action_plan",
    "iteration_delta_report",
]
# v0.4.0 §20.4 additive: 7th evidence file when round_kind == 'ship_prep'.
EXPECTED_EVIDENCE_FILES_SHIP_PREP = EXPECTED_EVIDENCE_FILES + ["ship_decision"]

# §23.6 companion-field suffixes ignored by R6_KEYS BLOCKER.
# Primary metric keys (e.g. ``T1_pass_rate``, ``C1_metadata_tokens``)
# count toward the 37 sub-metric total; companion keys ending in any
# of these suffixes are metadata about the primary value and MUST be
# filtered out before counting. This preserves R6 7×37 frozen count
# under v0.4.0 method-tag schema.
COMPANION_SUFFIXES: Tuple[str, ...] = (
    "_method",
    "_ci_low",
    "_ci_high",
    "_language_breakdown",
    "_state",
    "_provenance",
    "_sampled_at",
    "_sample_size_per_cell",
)


def _is_companion_key(key: str) -> bool:
    """Return True when ``key`` is a §23 companion-field suffix.

    Primary example: ``T1_pass_rate_method`` → True;
    ``T1_pass_rate`` → False. Used by R6_KEYS to exclude method-tag
    companions from the 7×37 sub-metric count (§23.6).

    >>> _is_companion_key("T1_pass_rate_method")
    True
    >>> _is_companion_key("U1_language_breakdown")
    True
    >>> _is_companion_key("U4_state")
    True
    >>> _is_companion_key("T1_pass_rate")
    False
    """

    return any(key.endswith(suffix) for suffix in COMPANION_SUFFIXES)

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
    """Count sub-metric keys per dimension, ignoring §23 companion fields.

    Each dimension's ``properties`` mapping enumerates the sub-metric
    names; a missing ``properties`` mapping yields zero (this is a
    template-shape error, surfaced by R6_KEYS). Companion suffixes
    (``_method``, ``_ci_low``, ``_ci_high``, ``_language_breakdown``,
    ``_state``, ``_provenance``, ``_sampled_at``,
    ``_sample_size_per_cell``) are excluded from the count per
    spec §23.6 (R6 7×37 frozen count unchanged under v0.4.0 method-tag
    schema).

    >>> m = {"d1": {"properties": {"T1": {}, "T2": {}}}, "d2": {"properties": {}}}
    >>> _count_metric_keys(m)
    {'d1': 2, 'd2': 0}
    >>> m_with_companions = {
    ...     "d1": {"properties": {
    ...         "T1_pass_rate": {},
    ...         "T1_pass_rate_method": {},
    ...         "T2_pass_k": {},
    ...         "T2_pass_k_ci_low": {},
    ...         "T2_pass_k_ci_high": {},
    ...     }}
    ... }
    >>> _count_metric_keys(m_with_companions)
    {'d1': 2}
    """

    out: Dict[str, int] = {}
    for dim, body in metrics.items():
        if not isinstance(body, dict):
            out[dim] = 0
            continue
        props = body.get("properties")
        if isinstance(props, dict):
            # §23.6: primary metric keys count; companion suffixes don't.
            out[dim] = sum(1 for k in props if not _is_companion_key(k))
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


def _collect_value_vector_axes_from_iteration_delta(
    templates_dir: Path,
) -> Set[str]:
    """Return any ``*_delta`` axis names found in iteration_delta_report.

    Per spec §6.1 v0.4.0 modification and §18.6 ``tier_transitions``
    design, the 8th axis ``eager_token_delta`` is expected to surface
    in ``iteration_delta_report.template.yaml`` as an additional entry
    under ``example_instance.axis_status`` (7 R6 dimensions +
    ``eager_token_delta``). Scan both the schema and example surfaces
    and return only ``*_delta``-suffixed keys (filtering out R6
    dimension-name keys like ``task_quality``).

    Returns an empty set if the template or path is missing — caller
    decides whether to fail. Workspace rule "No Silent Failures": we
    do NOT raise here because the historical template surface may omit
    the 8th axis for ≤ v0.3.0 spec verifications; the caller enforces.
    """

    idr_path = templates_dir / "iteration_delta_report.template.yaml"
    if not idr_path.exists():
        return set()
    data = _load_yaml(idr_path)
    axes: Set[str] = set()
    if not isinstance(data, dict):
        return axes
    example = data.get("example_instance") or {}
    if isinstance(example, dict):
        axis_status = example.get("axis_status") or {}
        if isinstance(axis_status, dict):
            for k in axis_status.keys():
                if isinstance(k, str) and k.endswith("_delta"):
                    axes.add(k)
    # Also accept top-level ``tier_transitions``-adjacent declaration
    # of axes if the template later standardizes on that surface.
    verdict = example.get("verdict") if isinstance(example, dict) else None
    if isinstance(verdict, dict):
        for k in verdict.keys():
            if isinstance(k, str) and k.endswith("_delta"):
                axes.add(k)
    return axes


def check_value_vector_axes(
    templates_dir: Path,
    *,
    spec_version: Optional[str] = None,
) -> AssertionResult:
    """Invariant 5 — VALUE_VECTOR_AXES: §6.1 axes count (7 ≤ v0.3.0; 8 @ v0.4.0+).

    Version-aware (same pattern as BAP_SCHEMA's version-awareness from
    Stage 4 Wave 2a): the expected axis count comes from
    ``EXPECTED_VALUE_VECTOR_AXES_BY_SPEC`` keyed on ``spec_version``.
    For v0.4.0-rc1+ the 8th axis (``eager_token_delta``) is expected
    in ``iteration_delta_report.template.yaml`` per spec §6.1 + §18.6
    (the half_retire_decision template remains UNCHANGED at 0.1.0 with
    the legacy 7 axes — that's intentional per §9 v0.4.0 add-on).

    When ``spec_version`` is ``None``, falls back to the 7-axis base
    set (legacy behavior) so callers that omit spec version continue
    to work against v0.3.0 + earlier specs.
    """

    expected = EXPECTED_VALUE_VECTOR_AXES_BY_SPEC.get(
        spec_version or "", EXPECTED_VALUE_VECTOR_AXES
    )

    hrd_path = templates_dir / "half_retire_decision.template.yaml"
    hrd_data = _load_yaml(hrd_path)
    try:
        hrd_axes_props = hrd_data["schema"]["value_vector"]["properties"]
    except (KeyError, TypeError) as exc:
        return AssertionResult(
            id="VALUE_VECTOR_AXES",
            name="Value vector axes per spec §6.1 (version-aware: 7 ≤ v0.3.0; 8 @ v0.4.0+)",
            passed=False,
            severity="BLOCKER",
            message=(
                f"template missing schema.value_vector.properties: {exc}"
            ),
            evidence={"template_path": str(hrd_path)},
        )
    hrd_axes = set(hrd_axes_props.keys())
    all_axes = set(hrd_axes)

    # For v0.4.0+ specs we also consult iteration_delta_report, where
    # the new ``eager_token_delta`` is declared additively. v0.4.2-rc1
    # is additive on top of v0.4.0 (no new axes; same 8) — same idr
    # consultation applies.
    idr_axes: Set[str] = set()
    if spec_version in {"v0.4.0-rc1", "v0.4.0", "v0.4.2-rc1"}:
        idr_axes = _collect_value_vector_axes_from_iteration_delta(
            templates_dir
        )
        all_axes |= idr_axes

    missing = sorted(expected - all_axes)
    extra = sorted(all_axes - expected)
    passed = not missing and not extra and len(all_axes) == len(expected)
    return AssertionResult(
        id="VALUE_VECTOR_AXES",
        name=(
            "Value vector axes per spec §6.1 "
            "(version-aware: 7 ≤ v0.3.0; 8 @ v0.4.0+)"
        ),
        passed=passed,
        severity="BLOCKER",
        message=(
            f"spec_version={spec_version!r} expected={sorted(expected)} "
            f"actual={sorted(all_axes)} missing={missing} extra={extra} "
            f"(hrd={sorted(hrd_axes)}, idr={sorted(idr_axes)})"
        ),
        evidence={
            "spec_version": spec_version,
            "expected": sorted(expected),
            "actual": sorted(all_axes),
            "missing": missing,
            "extra": extra,
            "hrd_axes": sorted(hrd_axes),
            "idr_axes": sorted(idr_axes),
        },
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


def _expected_evidence_count_for_round(
    round_dir: Path,
) -> Tuple[int, Optional[str], List[str]]:
    """Return (expected_count, round_kind, warnings) for a round directory.

    Reads ``next_action_plan.yaml`` from ``round_dir``; when
    ``round_kind == 'ship_prep'``, the expected count is 7 (§20.4 + §8.2
    v0.4.0 add-on); otherwise 6. Missing / unparseable next_action_plan
    defaults to 6 with a WARNING string in ``warnings``.
    """

    nap = round_dir / "next_action_plan.yaml"
    warnings: List[str] = []
    if not nap.exists():
        warnings.append(
            f"{round_dir}: next_action_plan.yaml missing; defaulting to "
            "evidence count = 6"
        )
        return 6, None, warnings
    try:
        data = yaml.safe_load(nap.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        warnings.append(
            f"{nap}: YAML parse error ({exc}); defaulting to evidence "
            "count = 6"
        )
        return 6, None, warnings
    if not isinstance(data, dict):
        warnings.append(
            f"{nap}: not a YAML mapping; defaulting to evidence count = 6"
        )
        return 6, None, warnings
    rk = data.get("round_kind")
    if rk == "ship_prep":
        return 7, "ship_prep", warnings
    return 6, rk if isinstance(rk, str) else None, warnings


def check_evidence_count_for_round(round_dir: Path) -> AssertionResult:
    """Round-level evidence-count check (§8.2 + §20.4 v0.4.0 add-on).

    Inspects a single round directory:
        1. Determine expected count (6 default; 7 when
           ``next_action_plan.yaml.round_kind == 'ship_prep'``; missing
           plan → default 6 with WARNING).
        2. Enumerate present evidence files from the expected list; fail
           when the count of present files is less than expected.

    Returns a BLOCKER ``AssertionResult``. When the round directory
    does not exist (e.g. unit-test fixture with no `.local/` tree) the
    check is PASS-as-SKIP with ``evidence.skipped_reason = "round_dir_missing"``.

    This helper is used both by ``check_dogfood_protocol`` (when it
    walks actual round directories) and by direct test callers.
    """

    if not round_dir.exists() or not round_dir.is_dir():
        return AssertionResult(
            id="EVIDENCE_FILES",
            name="§8.2 evidence-file count (round_kind-aware)",
            passed=True,
            severity="BLOCKER",
            message=f"round_dir missing: {round_dir}",
            evidence={
                "round_dir": str(round_dir),
                "skipped_reason": "round_dir_missing",
            },
        )

    expected_count, rk, warnings = _expected_evidence_count_for_round(round_dir)
    expected_names = (
        EXPECTED_EVIDENCE_FILES_SHIP_PREP
        if expected_count == 7
        else EXPECTED_EVIDENCE_FILES
    )
    present: List[str] = []
    missing: List[str] = []
    for name in expected_names:
        # Map logical name → filename convention. BasicAbilityProfile is
        # emitted as basic_ability_profile.yaml; others are lowercase_snake.
        if name == "BasicAbilityProfile":
            fname = "basic_ability_profile.yaml"
        else:
            fname = f"{name}.yaml"
        if (round_dir / fname).exists():
            present.append(name)
        else:
            missing.append(name)
    passed = len(present) >= expected_count and not missing
    return AssertionResult(
        id="EVIDENCE_FILES",
        name="§8.2 evidence-file count (round_kind-aware)",
        passed=passed,
        severity="BLOCKER",
        message=(
            f"round_dir={round_dir} round_kind={rk!r} expected_count="
            f"{expected_count} present={len(present)} missing={missing} "
            f"warnings={warnings}"
        ),
        evidence={
            "round_dir": str(round_dir),
            "round_kind": rk,
            "expected_count": expected_count,
            "expected_names": expected_names,
            "present": present,
            "missing": missing,
            "warnings": warnings,
        },
    )


def check_dogfood_protocol(spec_text: str) -> AssertionResult:
    """Invariant 7 — DOGFOOD_PROTOCOL: §8.1 8 steps + §8.2 6 evidence files.

    Evidence-file list is the BASE 6 per §8.2 main list; v0.4.0 add-on
    adds a 7th optional file (``ship_decision.yaml``) keyed on
    ``round_kind == 'ship_prep'`` — that round-level conditional count
    is enforced by ``check_evidence_count_for_round`` against actual
    round directories. At the spec-text level, we still assert the
    BASE 6 names appear in §8.2.
    """

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
        name="§8.1 8 ordered steps + §8.2 6 evidence files (base)",
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
            "expected_evidence_ship_prep": EXPECTED_EVIDENCE_FILES_SHIP_PREP,
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


# ─────────────────────────── v0.4.0 BLOCKERs 12 / 13 / 14 ────────
#
# Stage 4 Wave 1b (v0.4.0-rc1): three new round-level BLOCKERs walk
# the `.local/dogfood/<DATE>/[abilities/<id>/]round_<N>/` tree and
# check spec §18.1 / §19.3 / §21.2 invariants. When no artefacts are
# found, each BLOCKER PASSes as SKIP — but when artefacts exist and
# declare the relevant conditional, the invariant is HARD. No silent
# pass: every BLOCKER has a concrete failure surface against broken
# inputs (workspace rule "No Silent Failures").
# ─────────────────────────────────────────────────────────────────

# §18.1 token-tier axes.
TOKEN_TIER_AXES: Tuple[str, ...] = (
    "C7_eager_per_session",
    "C8_oncall_per_trigger",
    "C9_lazy_avg_per_load",
)


def _iter_round_metrics_reports(repo_root: Path) -> List[Path]:
    """Enumerate ``metrics_report.yaml`` files under the dogfood tree.

    Covers both layouts per §16:
      * Legacy: ``.local/dogfood/<DATE>/round_<N>/metrics_report.yaml``
      * Multi-ability: ``.local/dogfood/<DATE>/abilities/<id>/round_<N>/metrics_report.yaml``

    Returns an empty list when neither tree exists.
    """

    roots = [repo_root / ".local" / "dogfood"]
    out: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        # Walk the tree; include both layouts.
        for p in root.rglob("metrics_report.yaml"):
            out.append(p)
    return sorted(out)


def _iter_basic_ability_profiles(repo_root: Path) -> List[Path]:
    """Enumerate ``basic_ability_profile.yaml`` files under the dogfood tree."""

    root = repo_root / ".local" / "dogfood"
    if not root.exists():
        return []
    return sorted(root.rglob("basic_ability_profile.yaml"))


def _find_any_token_tier_axis(metrics_report: Dict[str, Any]) -> bool:
    """Return True iff the report includes any C7/C8/C9 axis value.

    Searches two surfaces:
      * Top-level ``token_tier`` block (the §18.1 normative surface).
      * Per-dimension ``context_economy.C7_*`` / ``C8_*`` / ``C9_*``
        keys (pre-§18 ad-hoc placements we still want to detect).

    Any presence (even ``null``) triggers the BLOCKER. Absence of all
    axes → SKIP.
    """

    # Canonical top-level surface.
    tier = metrics_report.get("token_tier")
    if isinstance(tier, dict):
        for axis in TOKEN_TIER_AXES:
            if axis in tier:
                return True
    # Ad-hoc surfaces (e.g. stuffed under D2 context_economy).
    metrics = metrics_report.get("metrics")
    if isinstance(metrics, dict):
        for dim_body in metrics.values():
            if not isinstance(dim_body, dict):
                continue
            for axis in TOKEN_TIER_AXES:
                if axis in dim_body:
                    return True
    return False


def check_token_tier_declared_when_reported(
    repo_root: Optional[Path] = None,
) -> AssertionResult:
    """BLOCKER 12 — TOKEN_TIER_DECLARED_WHEN_REPORTED (v0.4.0 §18.1).

    When any ``metrics_report.yaml`` in the dogfood tree includes even
    one of {C7_eager_per_session, C8_oncall_per_trigger,
    C9_lazy_avg_per_load} (even as ``null``), the SAME report MUST
    declare a top-level ``token_tier`` block with all three fields
    present (null placeholders allowed; missing keys = FAIL).

    Skipped as PASS when no metrics_report reports any token-tier axis
    (abilities that haven't adopted §18 yet).
    """

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    reports = _iter_round_metrics_reports(repo_root)
    findings: List[str] = []
    per_report: List[Dict[str, Any]] = []
    any_tier_reported = False

    for path in reports:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            findings.append(f"{path}: parse error: {exc}")
            per_report.append({"path": str(path), "parse_error": str(exc)})
            continue
        if not isinstance(data, dict):
            per_report.append({"path": str(path), "shape": "non_mapping"})
            continue
        reports_tier = _find_any_token_tier_axis(data)
        top_tier = data.get("token_tier")
        has_top_block = isinstance(top_tier, dict)
        missing_axes: List[str] = []
        if reports_tier:
            any_tier_reported = True
            # Top-level block is REQUIRED.
            if not has_top_block:
                findings.append(
                    f"{path}: token-tier axis reported but top-level "
                    "`token_tier` block missing (spec §18.1 REQUIRED)"
                )
            else:
                for axis in TOKEN_TIER_AXES:
                    if axis not in top_tier:
                        missing_axes.append(axis)
                if missing_axes:
                    findings.append(
                        f"{path}: top-level token_tier block is missing axes "
                        f"{missing_axes} (spec §18.1 requires all 3, null OK)"
                    )
        per_report.append(
            {
                "path": str(path),
                "reports_tier": reports_tier,
                "has_top_block": has_top_block,
                "missing_axes": missing_axes,
            }
        )

    if not any_tier_reported:
        return AssertionResult(
            id="TOKEN_TIER_DECLARED_WHEN_REPORTED",
            name=(
                "metrics_report.yaml declares top-level token_tier block "
                "when any C7/C8/C9 axis is reported (spec §18.1)"
            ),
            passed=True,
            severity="BLOCKER",
            message=(
                f"skipped: no metrics_report among {len(reports)} inspected "
                "reports includes any of C7/C8/C9 (abilities not yet "
                "adopting §18)"
            ),
            evidence={
                "reports_inspected": len(reports),
                "skipped_reason": "no_token_tier_axis_reported",
                "per_report": per_report,
            },
        )

    passed = not findings
    return AssertionResult(
        id="TOKEN_TIER_DECLARED_WHEN_REPORTED",
        name=(
            "metrics_report.yaml declares top-level token_tier block "
            "when any C7/C8/C9 axis is reported (spec §18.1)"
        ),
        passed=passed,
        severity="BLOCKER",
        message=(
            "all reports declare token_tier correctly"
            if passed
            else "; ".join(findings)
        ),
        evidence={
            "reports_inspected": len(reports),
            "findings": findings,
            "per_report": per_report,
        },
    )


# §19.3 fixture-citation grep pattern.
_REAL_DATA_PROVENANCE_RE = re.compile(
    r"real-data sample provenance", re.IGNORECASE
)


def _iter_real_data_samples_files(repo_root: Path) -> List[Tuple[str, Path]]:
    """Return (ability_id, path) pairs for every real_data_samples.yaml.

    Discovery paths (per §19.2):
      * ``.local/feedbacks/feedbacks_while_using/<ability_id>/real_data_samples.yaml``
      * ``.agents/skills/<ability_id>/real_data_samples.yaml``

    ``ability_id`` is derived from the enclosing directory name.
    """

    out: List[Tuple[str, Path]] = []
    roots = [
        repo_root / ".local" / "feedbacks" / "feedbacks_while_using",
        repo_root / ".agents" / "skills",
    ]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("real_data_samples.yaml"):
            ability = p.parent.name
            out.append((ability, p))
    return sorted(out, key=lambda entry: (entry[0], str(entry[1])))


def _ability_fixture_roots(repo_root: Path, ability_id: str) -> List[Path]:
    """Return candidate test-fixture root directories for an ability.

    Searches the following heuristic locations (spec §19.3 is
    language-agnostic; test trees vary by stack):
      * ``.agents/skills/<ability_id>/tests/``
      * ``ChipPlugins/chips/<ability_id>/tests/``
      * ``evals/<ability_id>/``
      * Any repo-wide directory path that includes the ability id.

    Returns only paths that exist.
    """

    candidates = [
        repo_root / ".agents" / "skills" / ability_id / "tests",
        repo_root / ".agents" / "skills" / ability_id / "__tests__",
        repo_root
        / "ChipPlugins"
        / "chips"
        / ability_id.replace("-", "_")
        / "tests",
        repo_root
        / "ChipPlugins"
        / "chips"
        / ability_id.replace("-", "_")
        / "__tests__",
        repo_root / "evals" / ability_id,
        repo_root / "evals" / "si-chip" / "runners" / ability_id,
    ]
    return [p for p in candidates if p.exists() and p.is_dir()]


def _fixture_has_provenance(
    fixture_root: Path,
) -> Tuple[bool, List[Path]]:
    """Return (found, paths_with_match) for any file citing provenance.

    Scans common fixture extensions (.json, .ts, .tsx, .js, .jsx, .py,
    .yaml, .yml, .md, .test.ts, .test.tsx). The presence of the
    canonical ``real-data sample provenance`` phrase anywhere in the
    file is sufficient; §19.3 allows any language-specific comment
    syntax as long as the phrase is grep-able.
    """

    matches: List[Path] = []
    for p in fixture_root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {
            ".json",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".py",
            ".yaml",
            ".yml",
            ".md",
            ".html",
        }:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _REAL_DATA_PROVENANCE_RE.search(text):
            matches.append(p)
    return bool(matches), matches


def check_real_data_fixture_provenance(
    repo_root: Optional[Path] = None,
) -> AssertionResult:
    """BLOCKER 13 — REAL_DATA_FIXTURE_PROVENANCE (v0.4.0 §19.3).

    For every discovered ``feedback_real_data_samples.yaml`` with a
    non-empty ``real_data_samples`` array, the owning ability's test
    fixture tree MUST contain at least one file citing ``real-data
    sample provenance`` (case-insensitive). Missing citation = FAIL.

    Skipped as PASS when no real_data_samples.yaml exists OR when each
    discovered file has an empty/zero ``real_data_samples`` list.
    """

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    samples_files = _iter_real_data_samples_files(repo_root)
    findings: List[str] = []
    per_ability: List[Dict[str, Any]] = []
    any_nonempty = False

    for ability_id, path in samples_files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            findings.append(f"{path}: parse error: {exc}")
            per_ability.append(
                {"ability_id": ability_id, "path": str(path), "parse_error": str(exc)}
            )
            continue
        samples = None
        if isinstance(data, dict):
            samples = data.get("real_data_samples")
        if not isinstance(samples, list) or not samples:
            per_ability.append(
                {
                    "ability_id": ability_id,
                    "path": str(path),
                    "samples_count": 0,
                    "skipped_reason": "no_samples_declared",
                }
            )
            continue
        any_nonempty = True
        fixture_roots = _ability_fixture_roots(repo_root, ability_id)
        if not fixture_roots:
            findings.append(
                f"{ability_id}: real_data_samples declared in {path} "
                "(non-empty) but no test fixture root found under "
                f".agents/skills/{ability_id}/tests, "
                f"ChipPlugins/chips/{ability_id.replace('-', '_')}/tests, "
                "or evals/"
            )
            per_ability.append(
                {
                    "ability_id": ability_id,
                    "path": str(path),
                    "samples_count": len(samples),
                    "fixture_roots": [],
                    "provenance_found": False,
                }
            )
            continue
        any_root_has_match = False
        per_root: List[Dict[str, Any]] = []
        for root in fixture_roots:
            found, matches = _fixture_has_provenance(root)
            per_root.append(
                {
                    "root": str(root),
                    "found": found,
                    "matched_files": [str(m) for m in matches[:20]],
                }
            )
            if found:
                any_root_has_match = True
        if not any_root_has_match:
            findings.append(
                f"{ability_id}: real_data_samples declared in {path} "
                f"({len(samples)} sample(s)) but fixture tree(s) "
                f"{[str(r) for r in fixture_roots]} contain no "
                "`real-data sample provenance` citation "
                "(spec §19.3 + hard rule 12)"
            )
        per_ability.append(
            {
                "ability_id": ability_id,
                "path": str(path),
                "samples_count": len(samples),
                "fixture_roots": [str(r) for r in fixture_roots],
                "provenance_found": any_root_has_match,
                "per_root": per_root,
            }
        )

    if not samples_files or not any_nonempty:
        return AssertionResult(
            id="REAL_DATA_FIXTURE_PROVENANCE",
            name=(
                "Test fixtures cite `real-data sample provenance` when "
                "feedback_real_data_samples.yaml is non-empty "
                "(spec §19.3)"
            ),
            passed=True,
            severity="BLOCKER",
            message=(
                f"skipped: no real_data_samples.yaml with a non-empty "
                f"real_data_samples list (inspected {len(samples_files)} "
                "file(s))"
            ),
            evidence={
                "samples_files_inspected": len(samples_files),
                "skipped_reason": (
                    "no_real_data_samples_files"
                    if not samples_files
                    else "all_samples_empty"
                ),
                "per_ability": per_ability,
            },
        )

    passed = not findings
    return AssertionResult(
        id="REAL_DATA_FIXTURE_PROVENANCE",
        name=(
            "Test fixtures cite `real-data sample provenance` when "
            "feedback_real_data_samples.yaml is non-empty "
            "(spec §19.3)"
        ),
        passed=passed,
        severity="BLOCKER",
        message=(
            "all abilities with real_data_samples have grep-able "
            "provenance citations"
            if passed
            else "; ".join(findings)
        ),
        evidence={
            "samples_files_inspected": len(samples_files),
            "findings": findings,
            "per_ability": per_ability,
        },
    )


def check_health_smoke_declared_when_live_backend(
    repo_root: Optional[Path] = None,
) -> AssertionResult:
    """BLOCKER 14 — HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND (v0.4.0 §21.2).

    For every discovered ``basic_ability_profile.yaml`` in the dogfood
    tree (both legacy and multi-ability layouts), assert that when
    ``current_surface.dependencies.live_backend == true``, the SAME
    profile's ``packaging.health_smoke_check`` is a non-empty list.
    Missing / empty = FAIL.

    Skipped as PASS when no profile declares ``live_backend: true``.
    """

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    profiles = _iter_basic_ability_profiles(repo_root)
    findings: List[str] = []
    per_profile: List[Dict[str, Any]] = []
    any_live_backend = False

    for path in profiles:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            findings.append(f"{path}: parse error: {exc}")
            per_profile.append({"path": str(path), "parse_error": str(exc)})
            continue
        if not isinstance(data, dict):
            per_profile.append({"path": str(path), "shape": "non_mapping"})
            continue
        bap = data.get("basic_ability")
        if not isinstance(bap, dict):
            per_profile.append({"path": str(path), "shape": "no_basic_ability"})
            continue
        current_surface = bap.get("current_surface") or {}
        deps = current_surface.get("dependencies") if isinstance(
            current_surface, dict
        ) else None
        live_backend = False
        if isinstance(deps, dict):
            live_backend = bool(deps.get("live_backend", False))
        packaging = bap.get("packaging") or {}
        smoke = packaging.get("health_smoke_check") if isinstance(
            packaging, dict
        ) else None
        smoke_is_list = isinstance(smoke, list)
        smoke_len = len(smoke) if smoke_is_list else 0
        if live_backend:
            any_live_backend = True
            if not smoke_is_list or smoke_len == 0:
                findings.append(
                    f"{path}: current_surface.dependencies.live_backend=true "
                    "but packaging.health_smoke_check is missing or empty "
                    "(spec §21.2 + hard rule 13)"
                )
        per_profile.append(
            {
                "path": str(path),
                "ability_id": bap.get("id"),
                "live_backend": live_backend,
                "smoke_is_list": smoke_is_list,
                "smoke_len": smoke_len,
            }
        )

    if not profiles or not any_live_backend:
        return AssertionResult(
            id="HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND",
            name=(
                "BasicAbilityProfile with live_backend:true declares "
                "non-empty packaging.health_smoke_check (spec §21.2)"
            ),
            passed=True,
            severity="BLOCKER",
            message=(
                "skipped: no basic_ability_profile.yaml declares "
                "current_surface.dependencies.live_backend = true "
                f"(inspected {len(profiles)} profile(s))"
            ),
            evidence={
                "profiles_inspected": len(profiles),
                "skipped_reason": (
                    "no_basic_ability_profiles"
                    if not profiles
                    else "no_live_backend_declared"
                ),
                "per_profile": per_profile,
            },
        )

    passed = not findings
    return AssertionResult(
        id="HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND",
        name=(
            "BasicAbilityProfile with live_backend:true declares "
            "non-empty packaging.health_smoke_check (spec §21.2)"
        ),
        passed=passed,
        severity="BLOCKER",
        message=(
            "all live_backend profiles declare non-empty health_smoke_check"
            if passed
            else "; ".join(findings)
        ),
        evidence={
            "profiles_inspected": len(profiles),
            "findings": findings,
            "per_profile": per_profile,
        },
    )


# §24.1 description-cap discovery + extraction helpers.
# Search trees: source-of-truth + 2 platform mirrors.
DESCRIPTION_CAP_CHARS: int = 1024
SKILL_MD_TREES: Tuple[str, ...] = (
    ".agents/skills",
    ".cursor/skills",
    ".claude/skills",
)

# Frontmatter detection: first ``---``-delimited block at the very top
# of the file. Matches both LF and CRLF line endings.
_FRONTMATTER_RE = re.compile(
    r"\A---\s*\r?\n(.+?)\r?\n---\s*(?:\r?\n|\Z)",
    re.DOTALL,
)
# In-frontmatter ``description: <value>`` line. Permissive on the value
# side: takes everything up to a newline.  Block-scalar (``|`` / ``>``)
# values yield empty string after this regex which we treat as "no
# scalar description present"; multi-line block descriptions are not
# the convention §24.1 enforces and would themselves indicate a
# description-discipline violation (informational, not BLOCKER).
_FRONTMATTER_DESC_RE = re.compile(
    r"^description:\s*(.*?)\s*$",
    re.MULTILINE,
)


def _iter_skill_md_files(repo_root: Path) -> List[Path]:
    """Enumerate every ``SKILL.md`` under the 3 skill-tree roots.

    Walks ``.agents/skills/<name>/SKILL.md``,
    ``.cursor/skills/<name>/SKILL.md`` and
    ``.claude/skills/<name>/SKILL.md``. Returns a sorted, de-duplicated
    list. Empty when the trees do not exist (pre-bootstrap repo).
    """

    out: List[Path] = []
    for tree in SKILL_MD_TREES:
        root = repo_root / tree
        if not root.exists():
            continue
        for p in root.rglob("SKILL.md"):
            out.append(p)
    return sorted(set(out))


def _extract_skill_description(skill_md_path: Path) -> Optional[str]:
    """Pull the YAML frontmatter ``description`` field from a SKILL.md.

    Returns ``None`` when the file has no frontmatter, or when the
    frontmatter has no ``description`` key, or when the value is a
    block scalar (``|`` / ``>`` start) that we deliberately decline to
    interpret as a single-line description (§24.1 expects a single-
    line scalar). The caller treats ``None`` as "no description to
    measure" — equivalent to a SKIP for this individual file (other
    files may still trigger the BLOCKER).
    """

    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        LOGGER.warning(
            "spec_validator: cannot read %s for description-cap check: %s",
            skill_md_path,
            exc,
        )
        return None
    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        return None
    fm_body = fm_match.group(1)
    desc_match = _FRONTMATTER_DESC_RE.search(fm_body)
    if not desc_match:
        return None
    raw = desc_match.group(1)
    # Block-scalar indicator → not a single-line scalar. Decline to
    # measure (a multi-line block already violates §24.1's "what +
    # when" single-paragraph shape; that violation is left to
    # informational reporting in §24.1.2 rather than this BLOCKER).
    if raw.startswith(("|", ">")):
        return None
    # Strip surrounding quotes if present (YAML allows both).
    if (
        len(raw) >= 2
        and raw[0] == raw[-1]
        and raw[0] in ('"', "'")
    ):
        raw = raw[1:-1]
    return raw


def _binding_description_length(s: str) -> Tuple[int, int, int]:
    """Return (chars, bytes, binding_length) for the §24.1 cap measurement.

    ``binding_length = min(chars, bytes)``. CJK fairness: 1 汉字 ≈ 3
    UTF-8 bytes but 1 character; the binding length walks the *smaller*
    of the two so multi-byte alphabets are not penalised by UTF-8 byte
    expansion (per §24.1 invariant #1).
    """

    chars = len(s)
    bytes_len = len(s.encode("utf-8"))
    return chars, bytes_len, min(chars, bytes_len)


def _spec_text_has_section_24(spec_text: str) -> bool:
    """Return True iff ``spec_text`` carries a §24 / DESCRIPTION_CAP_1024 marker.

    The marker must appear in one of:
      * H2 header ``## 24. ...`` (canonical placement; spec §24)
      * H3 header ``### 24.1 ...`` (canonical sub-section)
      * Inline reference to ``DESCRIPTION_CAP_1024`` (rule layer
        compatibility — appears in the §17.7 hard-rule prose).
      * Inline reference to ``§24.1`` (cross-reference convention used
        in §17.7 and the v0.4.2 lineage paragraph).

    Used by ``check_description_cap_1024`` to SKIP-as-PASS against
    pre-v0.4.2 specs (per §13.6.4 grace period).
    """

    return bool(
        re.search(r"^##\s+24\.\s", spec_text, re.MULTILINE)
        or re.search(r"^###\s+24\.1\s", spec_text, re.MULTILINE)
        or "DESCRIPTION_CAP_1024" in spec_text
        or "§24.1" in spec_text
    )


def check_description_cap_1024(
    repo_root: Optional[Path] = None,
    *,
    spec_text: Optional[str] = None,
) -> AssertionResult:
    """BLOCKER 15 — DESCRIPTION_CAP_1024 (v0.4.2 §24.1).

    For every ``SKILL.md`` under ``.agents/skills/``, ``.cursor/skills/``
    and ``.claude/skills/``, plus every ``basic_ability_profile.yaml``
    under ``.local/dogfood/**/round_*/``, assert that the
    routing-time description satisfies
    ``min(len(s), len(s.encode('utf-8'))) <= 1024`` per §24.1
    (binding cap convention — CJK fairness via the lower of the two
    measurements).

    For SKILL.md, the value comes from the YAML frontmatter
    ``description`` field. For BasicAbilityProfile, the value comes
    from ``basic_ability.description`` if present, falling back to
    ``basic_ability.intent`` (the schema does not currently declare a
    top-level ``description``; the rule absorbs the field as OPTIONAL,
    and ``intent`` is the closest existing semantic surface — §24.1.2
    explicitly excludes ``core_goal.statement`` and reference docs).

    Skipped as PASS in two cases (per §13.6.4 grace period):

      1. The validated spec text does not declare §24 (i.e. the
         ``--spec`` target is pre-v0.4.2). This keeps backward
         compatibility with the v0.4.0, v0.3.0 and v0.2.0 spec runs
         (all 14 historical BLOCKERs still PASS; the 15th SKIP-PASSes).
      2. No SKILL.md files and no BAP files are found in the repo
         (pre-bootstrap repository).
    """

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    # SKIP-as-PASS path 1: spec lacks the §24 marker (pre-v0.4.2).
    if spec_text is not None and not _spec_text_has_section_24(spec_text):
        return AssertionResult(
            id="DESCRIPTION_CAP_1024",
            name=(
                "SKILL.md frontmatter description and BasicAbility "
                "description ≤ 1024 chars (spec §24.1)"
            ),
            passed=True,
            severity="BLOCKER",
            message=(
                "skipped: spec does not declare §24 / "
                "DESCRIPTION_CAP_1024 (pre-v0.4.2 backward compat per "
                "§13.6.4 grace period)"
            ),
            evidence={
                "skipped_reason": "spec_lacks_section_24_marker",
                "cap_chars": DESCRIPTION_CAP_CHARS,
            },
        )

    skill_md_files = _iter_skill_md_files(repo_root)
    bap_files = _iter_basic_ability_profiles(repo_root)

    findings: List[str] = []
    per_artifact: List[Dict[str, Any]] = []
    measured_count = 0

    # ── 1. SKILL.md frontmatter description ──
    for path in skill_md_files:
        desc = _extract_skill_description(path)
        if desc is None:
            per_artifact.append(
                {
                    "kind": "skill_md",
                    "path": str(path.relative_to(repo_root)),
                    "skipped_reason": "no_scalar_description_in_frontmatter",
                }
            )
            continue
        chars, bytes_len, binding = _binding_description_length(desc)
        measured_count += 1
        entry: Dict[str, Any] = {
            "kind": "skill_md",
            "path": str(path.relative_to(repo_root)),
            "chars": chars,
            "bytes": bytes_len,
            "binding_length": binding,
            "cap": DESCRIPTION_CAP_CHARS,
        }
        if binding > DESCRIPTION_CAP_CHARS:
            cap_axis = "chars" if chars <= bytes_len else "bytes"
            findings.append(
                f"{path.relative_to(repo_root)}: SKILL.md frontmatter "
                f"description binding length {binding} > "
                f"{DESCRIPTION_CAP_CHARS} (chars={chars}, "
                f"bytes={bytes_len}, binding-axis={cap_axis}; spec "
                "§24.1 + hard rule 14)"
            )
            entry["pass"] = False
        else:
            entry["pass"] = True
        per_artifact.append(entry)

    # ── 2. BasicAbilityProfile.basic_ability.description (or .intent) ──
    for path in bap_files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            findings.append(f"{path}: parse error: {exc}")
            per_artifact.append(
                {
                    "kind": "bap",
                    "path": str(path.relative_to(repo_root)),
                    "parse_error": str(exc),
                }
            )
            continue
        if not isinstance(data, dict):
            per_artifact.append(
                {
                    "kind": "bap",
                    "path": str(path.relative_to(repo_root)),
                    "shape": "non_mapping",
                }
            )
            continue
        bap = data.get("basic_ability")
        if not isinstance(bap, dict):
            per_artifact.append(
                {
                    "kind": "bap",
                    "path": str(path.relative_to(repo_root)),
                    "shape": "no_basic_ability",
                }
            )
            continue
        desc = bap.get("description")
        source_field = "description"
        if not isinstance(desc, str) or not desc:
            # Fallback to intent (REQUIRED per §2.1 schema). §24.1.2
            # explicitly notes this fallback is only for description-
            # absence; when description is present, intent is left
            # untouched (intent may legitimately be a longer narrative).
            intent = bap.get("intent")
            if isinstance(intent, str) and intent:
                desc = intent
                source_field = "intent_fallback"
            else:
                per_artifact.append(
                    {
                        "kind": "bap",
                        "path": str(path.relative_to(repo_root)),
                        "ability_id": bap.get("id"),
                        "skipped_reason": "no_description_or_intent_string",
                    }
                )
                continue
        chars, bytes_len, binding = _binding_description_length(desc)
        measured_count += 1
        entry = {
            "kind": "bap",
            "path": str(path.relative_to(repo_root)),
            "ability_id": bap.get("id"),
            "source_field": source_field,
            "chars": chars,
            "bytes": bytes_len,
            "binding_length": binding,
            "cap": DESCRIPTION_CAP_CHARS,
        }
        if binding > DESCRIPTION_CAP_CHARS:
            cap_axis = "chars" if chars <= bytes_len else "bytes"
            findings.append(
                f"{path.relative_to(repo_root)}: "
                f"basic_ability.{source_field} (ability_id="
                f"{bap.get('id')!r}) binding length {binding} > "
                f"{DESCRIPTION_CAP_CHARS} (chars={chars}, "
                f"bytes={bytes_len}, binding-axis={cap_axis}; spec "
                "§24.1 + hard rule 14)"
            )
            entry["pass"] = False
        else:
            entry["pass"] = True
        per_artifact.append(entry)

    # SKIP-as-PASS path 2: nothing in scope.
    if not skill_md_files and not bap_files:
        return AssertionResult(
            id="DESCRIPTION_CAP_1024",
            name=(
                "SKILL.md frontmatter description and BasicAbility "
                "description ≤ 1024 chars (spec §24.1)"
            ),
            passed=True,
            severity="BLOCKER",
            message=(
                "skipped: no SKILL.md files under .agents/skills/, "
                ".cursor/skills/, .claude/skills/ AND no "
                "basic_ability_profile.yaml under .local/dogfood/ "
                "(pre-bootstrap repo)"
            ),
            evidence={
                "skipped_reason": "no_skill_md_or_bap_files",
                "cap_chars": DESCRIPTION_CAP_CHARS,
                "skill_md_trees": list(SKILL_MD_TREES),
            },
        )

    passed = not findings
    return AssertionResult(
        id="DESCRIPTION_CAP_1024",
        name=(
            "SKILL.md frontmatter description and BasicAbility "
            "description ≤ 1024 chars (spec §24.1)"
        ),
        passed=passed,
        severity="BLOCKER",
        message=(
            f"all {measured_count} measured description(s) ≤ "
            f"{DESCRIPTION_CAP_CHARS} chars (binding=min(chars,bytes))"
            if passed
            else "; ".join(findings)
        ),
        evidence={
            "skill_md_files_inspected": len(skill_md_files),
            "bap_files_inspected": len(bap_files),
            "descriptions_measured": measured_count,
            "cap_chars": DESCRIPTION_CAP_CHARS,
            "findings": findings,
            "per_artifact": per_artifact,
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

    Stage 4 Wave 1b (v0.4.0-rc1) widened the BLOCKER set to fourteen:
    the 11 historical invariants plus ``TOKEN_TIER_DECLARED_WHEN_REPORTED``
    (§18.1), ``REAL_DATA_FIXTURE_PROVENANCE`` (§19.3), and
    ``HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`` (§21.2). Each of the 3
    new BLOCKERs PASSes as SKIP when no v0.4.0 artefacts exist in the
    repo (backward compat with pre-v0.4.0 round histories).

    Stage 4 Wave 1d (v0.4.2-rc1) widens the set further to **fifteen**:
    adds ``DESCRIPTION_CAP_1024`` (§24.1; absorbed from
    addyosmani/agent-skills v1.0.0). Skipped as PASS when the validated
    spec lacks the §24 marker (pre-v0.4.2 backward compat per §13.6.4
    grace period) OR when no SKILL.md / BAP files exist.

    Total order:

    1. ``BAP_SCHEMA``
    2. ``R6_KEYS``
    3. ``THRESHOLD_TABLE``
    4. ``ROUTER_MATRIX_CELLS``
    5. ``VALUE_VECTOR_AXES`` *(version-aware: 7 ≤ v0.3.0; 8 @ v0.4.0+)*
    6. ``PLATFORM_PRIORITY``
    7. ``DOGFOOD_PROTOCOL``
    8. ``FOREVER_OUT_LIST``
    9. ``REACTIVATION_DETECTOR_EXISTS``
    10. ``CORE_GOAL_FIELD_PRESENT``
    11. ``ROUND_KIND_TEMPLATE_VALID``
    12. ``TOKEN_TIER_DECLARED_WHEN_REPORTED`` *(NEW @ Stage 4 Wave 1b)*
    13. ``REAL_DATA_FIXTURE_PROVENANCE`` *(NEW @ Stage 4 Wave 1b)*
    14. ``HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND`` *(NEW @ Stage 4 Wave 1b)*
    15. ``DESCRIPTION_CAP_1024`` *(NEW @ Stage 4 Wave 1d, v0.4.2-rc1)*
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
        check_value_vector_axes(templates_dir, spec_version=spec_version),
        check_platform_priority(spec_text),
        check_dogfood_protocol(spec_text),
        check_forever_out_list(spec_text),
        check_reactivation_detector_exists(repo_root=repo_root),
        check_core_goal_field_present(templates_dir),
        check_round_kind_template_valid(templates_dir),
        check_token_tier_declared_when_reported(repo_root=repo_root),
        check_real_data_fixture_provenance(repo_root=repo_root),
        check_health_smoke_declared_when_live_backend(repo_root=repo_root),
        check_description_cap_1024(
            repo_root=repo_root, spec_text=spec_text
        ),
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
            "Static structural validator for the Si-Chip spec. Runs 15 "
            "BLOCKERs (9 historical + 2 v0.3.0 additive: "
            "CORE_GOAL_FIELD_PRESENT, ROUND_KIND_TEMPLATE_VALID; + 3 "
            "v0.4.0 additive: TOKEN_TIER_DECLARED_WHEN_REPORTED, "
            "REAL_DATA_FIXTURE_PROVENANCE, "
            "HEALTH_SMOKE_DECLARED_WHEN_LIVE_BACKEND; + 1 v0.4.2 "
            "additive: DESCRIPTION_CAP_1024)."
        ),
    )
    parser.add_argument(
        "--spec",
        default=DEFAULT_SPEC,
        help=(
            f"Path to spec markdown (default: {DEFAULT_SPEC}). "
            "Latest accepted spec version is v0.4.2-rc1 "
            "(`.local/research/spec_v0.4.2-rc1.md`); v0.4.0 / v0.4.0-rc1 / "
            "v0.3.0 / v0.3.0-rc1 / v0.2.0 / v0.2.0-rc1 / v0.1.0 remain "
            "accepted for historical artefact regression."
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
            "/ v0.3.0 / v0.4.0-rc1 expect 37 sub-metrics + 30 threshold cells "
            "(post-Round-11 reconciliation; v0.3.0 + v0.4.0 §13.4 preserve "
            "byte-identicality; v0.4.0 §6.1 axes change is separate from §13.4 "
            "prose counts); v0.1.0 expects 28 + 21 (legacy; validator preserves "
            "the mode for historical regression). Spec version is auto-detected "
            "from frontmatter."
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
