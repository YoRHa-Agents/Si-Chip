#!/usr/bin/env python3
"""Static structural validator for the Si-Chip spec.

Implements the eight machine-checkable invariants declared in
`.local/research/spec_v0.1.0.md` §13.4 and frozen in
`tools/spec_validator.DESIGN.md`.

The validator does NOT execute the dogfood loop, the router test, or any
metric collection. It only verifies that the spec markdown plus the six
templates under ``templates/`` remain structurally aligned with the §3,
§4, §5.3, §6.1, §7.2, §8.1, §8.2, §11.1 Normative content.

CLI::

    python tools/spec_validator.py [--spec PATH] [--strict] [--json] \\
        [--strict-prose-count]

``--spec PATH`` selects the spec markdown (default
``.local/research/spec_v0.1.0.md``).

``--strict`` treats WARNING findings as failures.

``--json`` emits a structured JSON report on stdout.

``--strict-prose-count`` enforces the spec §13.4 prose number for two
invariants (R6 metric key count == 28, threshold table cells == 21);
both will fail until a future spec bump reconciles the prose with the
§3.1 / §4.1 tables.

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
from typing import Any, Dict, List, Optional

import yaml

LOGGER = logging.getLogger("si_chip.spec_validator")

SCRIPT_VERSION = "0.1.1"

# §5 router_test_matrix template accepts BOTH schema versions as of
# Round 9 (Si-Chip v0.1.8). 0.1.0 = initial (mvp:8 + full:96); 0.1.1 =
# additive intermediate:16 profile. Backward compatibility is intentional —
# previous rounds' evidence stays valid.
SUPPORTED_ROUTER_TEMPLATE_SCHEMAS = {"0.1.0", "0.1.1"}

# Round 9 intermediate invariants (only asserted when schema is 0.1.1).
EXPECTED_INTERMEDIATE_CELLS = 16
EXPECTED_INTERMEDIATE_GATE_BINDING = "relaxed"

DEFAULT_SPEC = ".local/research/spec_v0.1.0.md"
DEFAULT_TEMPLATES_DIR = "templates"

# §2.1 frozen field set under basic_ability.
EXPECTED_BAP_KEYS = {
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
}

# §3.1 R6 metric dimension -> sub-metric count (TABLE form, 37 total).
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
EXPECTED_R6_PROSE_TOTAL = 28  # §13.4 prose claim

# §4.1 threshold table — 10 metrics × 3 profiles = 30 cells.
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
EXPECTED_THRESHOLD_CELLS_PROSE = 21  # §13.4 prose claim

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


def check_bap_schema(templates_dir: Path) -> AssertionResult:
    """Invariant 1 — BAP_SCHEMA: §2.1 top-level field set match."""

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

    actual = set(ba_props.keys())
    missing = sorted(EXPECTED_BAP_KEYS - actual)
    extra = sorted(actual - EXPECTED_BAP_KEYS)
    passed = not missing and not extra
    return AssertionResult(
        id="BAP_SCHEMA",
        name="BasicAbilityProfile schema field set matches spec §2.1",
        passed=passed,
        severity="BLOCKER",
        message=(
            f"expected={sorted(EXPECTED_BAP_KEYS)} actual={sorted(actual)}"
            f" missing={missing} extra={extra}"
        ),
        evidence={"missing": missing, "extra": extra, "actual": sorted(actual)},
    )


def check_r6_keys(templates_dir: Path, *, strict_prose: bool) -> AssertionResult:
    """Invariant 2 — R6_KEYS: §3.1 metric key count.

    Default: assert per-dimension {D1:4, D2:6, D3:7, D4:4, D5:4, D6:8,
    D7:4} = 37 total (§3.1 TABLE).

    With ``strict_prose=True``: assert total == 28 (§13.4 prose claim;
    will fail until reconciled). The INFO note about the discrepancy is
    always emitted in the message body.
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
            name="R6 metric key set matches spec §3.1 (TABLE=37, prose=28)",
            passed=False,
            severity="BLOCKER",
            message=f"schema missing metrics.properties: {exc}",
            evidence={"schema_path": str(schema_path)},
        )

    counts = _count_metric_keys(metrics)
    total = sum(counts.values())
    info_note = (
        "INFO: spec §3.1 TABLE enumerates 37 sub-metrics while §13.4 prose says 28; "
        "templates use the TABLE count."
    )

    if strict_prose:
        passed = total == EXPECTED_R6_PROSE_TOTAL
        msg = (
            f"strict-prose-count: expected total={EXPECTED_R6_PROSE_TOTAL}, observed={total} "
            f"(per-dim={counts}). {info_note}"
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
        name="R6 metric key set matches spec §3.1 (TABLE=37, prose=28)",
        passed=passed,
        severity="BLOCKER",
        message=msg,
        evidence={
            "per_dimension": counts,
            "total": total,
            "expected_table": EXPECTED_R6_TABLE_COUNTS,
            "expected_prose_total": EXPECTED_R6_PROSE_TOTAL,
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


def check_threshold_table(spec_text: str, *, strict_prose: bool) -> AssertionResult:
    """Invariant 3 — THRESHOLD_TABLE: §4.1 cells + monotonicity."""

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

    info_note = (
        "INFO: §4.1 actual table is 10 metrics x 3 profiles = 30 numeric cells; "
        "§13.4 prose says 21 cells across 7 metrics x 3 profiles."
    )

    if strict_prose:
        passed = cells == EXPECTED_THRESHOLD_CELLS_PROSE and not monotone_failures
        msg = (
            f"strict-prose-count: expected={EXPECTED_THRESHOLD_CELLS_PROSE} cells, "
            f"observed={cells} cells; missing_metrics={missing_metrics}; "
            f"monotone_failures={monotone_failures}. {info_note}"
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


# ─────────────────────────── runner ───────────────────────────


def run_all(
    spec_path: Path,
    templates_dir: Path,
    *,
    strict_prose: bool,
) -> ValidationReport:
    """Execute every invariant in declared order."""

    spec_text = _read_text(spec_path)
    results: List[AssertionResult] = [
        check_bap_schema(templates_dir),
        check_r6_keys(templates_dir, strict_prose=strict_prose),
        check_threshold_table(spec_text, strict_prose=strict_prose),
        check_router_matrix_cells(templates_dir),
        check_value_vector_axes(templates_dir),
        check_platform_priority(spec_text),
        check_dogfood_protocol(spec_text),
        check_forever_out_list(spec_text),
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
        description="Static structural validator for the Si-Chip spec.",
    )
    parser.add_argument(
        "--spec",
        default=DEFAULT_SPEC,
        help=f"Path to spec markdown (default: {DEFAULT_SPEC}).",
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
        help="Enforce spec §13.4 prose counts (R6 sub-metrics == 28, threshold cells == 21). Will fail until prose is reconciled with the §3.1 / §4.1 tables.",
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
