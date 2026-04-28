#!/usr/bin/env python3
"""Aggregate per-run eval results into a Si-Chip ``metrics_report.yaml``.

Implements spec §3 (Metric Taxonomy) and §8.1 step 2 / §8.2 evidence
file #2 of `.local/research/spec_v0.1.0.md`.  Walks the
``--runs-dir`` (with-ability) and ``--baseline-dir`` (no-ability)
trees, ingests each ``result.json`` (or ``.yaml``), and emits a
``metrics_report.yaml`` whose ``metrics`` block mirrors the schema in
``templates/basic_ability_profile.schema.yaml``: every one of the 28
sub-metric keys is present; the MVP-8 set
(``T1, T2, T3, C1, C4, L2, R3, R5``) is populated; the remaining 20
keys carry an explicit ``null`` per spec §3.2 frozen constraint #2.

R7 risk #3 mitigation: at startup we ``import devolaflow`` and log
``devolaflow.__version__`` at INFO level so dogfood rounds capture the
upstream library version that produced the report.

CLI::

    python scripts/aggregate_eval.py --runs-dir RUNS \\
        --baseline-dir BASELINE [--out PATH] \\
        [--templates-dir templates/] [--skill-md PATH]

Required input convention — every leaf ``result.json`` (or
``result.yaml``) must contain::

    {
      "pass_rate": 0.83,
      "pass_k_4": 0.62,
      "latency_p95_s": 18.4,
      "metadata_tokens": 92,
      "per_invocation_footprint": 6100,
      "trigger_F1": 0.88,
      "router_floor": "composer_2/fast"
    }

Missing required keys or missing baseline counterparts cause a
non-zero exit (no silent zero substitution).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.aggregate_eval")

SCRIPT_VERSION = "0.1.2"

REQUIRED_KEYS: Tuple[str, ...] = (
    "pass_rate",
    "pass_k_4",
    "latency_p95_s",
    "metadata_tokens",
    "per_invocation_footprint",
    "trigger_F1",
    "router_floor",
)

# Round 4 (S5 task spec Edit C) added per-row latency_p50_s, step_count
# and redundant_call_ratio from the runners. They are OPTIONAL during
# the read because Round 3 result.json snapshots predate them; the
# aggregator falls back to ``None`` when the key is absent and records
# the degenerate path in ``provenance.l_derivation`` instead of silently
# zeroing.
OPTIONAL_LATENCY_PATH_KEYS: Tuple[str, ...] = (
    "latency_p50_s",
    "step_count",
    "redundant_call_ratio",
)

# Round 4 (S5 task spec Edit C): optional latency-path instrumentation.
# When every ``with_rows`` row carries these keys, the aggregator hoists
# spec §3.1 D3 L1 / L3 / L4 into the metrics_report. Missing keys are
# the documented degenerate path (report field stays ``None`` per §3.2).
OPTIONAL_L134_KEYS: Tuple[str, ...] = (
    "latency_p50_s",
    "step_count",
    "redundant_call_ratio",
)

METRIC_KEYS: Dict[str, List[str]] = {
    "task_quality": [
        "T1_pass_rate",
        "T2_pass_k",
        "T3_baseline_delta",
        "T4_error_recovery_rate",
    ],
    "context_economy": [
        "C1_metadata_tokens",
        "C2_body_tokens",
        "C3_resolved_tokens",
        "C4_per_invocation_footprint",
        "C5_context_rot_risk",
        "C6_scope_overlap_score",
    ],
    "latency_path": [
        "L1_wall_clock_p50",
        "L2_wall_clock_p95",
        "L3_step_count",
        "L4_redundant_call_ratio",
        "L5_detour_index",
        "L6_replanning_rate",
        "L7_think_act_split",
    ],
    "generalizability": [
        "G1_cross_model_pass_matrix",
        "G2_cross_domain_transfer_pass",
        "G3_OOD_robustness",
        "G4_model_version_stability",
    ],
    "usage_cost": [
        "U1_description_readability",
        "U2_first_time_success_rate",
        "U3_setup_steps_count",
        "U4_time_to_first_success",
    ],
    "routing_cost": [
        "R1_trigger_precision",
        "R2_trigger_recall",
        "R3_trigger_F1",
        "R4_near_miss_FP_rate",
        "R5_router_floor",
        "R6_routing_latency_p95",
        "R7_routing_token_overhead",
        "R8_description_competition_index",
    ],
    "governance_risk": [
        "V1_permission_scope",
        "V2_credential_surface",
        "V3_drift_signal",
        "V4_staleness_days",
    ],
}


def _load_result_file(path: Path) -> Dict[str, Any]:
    """Load a single ``result.json`` / ``result.yaml`` file.

    >>> import json, tempfile, pathlib
    >>> tmp = pathlib.Path(tempfile.mkdtemp()) / "result.json"
    >>> _ = tmp.write_text(json.dumps({"pass_rate": 0.9}))
    >>> _load_result_file(tmp)["pass_rate"]
    0.9
    """

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON/YAML object, got {type(data).__name__}")
    return data


def _walk_runs(root: Path) -> List[Path]:
    if not root.exists():
        raise FileNotFoundError(f"directory not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")
    found: List[Path] = []
    for pattern in ("result.json", "result.yaml", "result.yml"):
        found.extend(sorted(root.rglob(pattern)))
    if not found:
        raise FileNotFoundError(f"no result.{{json,yaml,yml}} files found under {root}")
    return found


def _collect(runs: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in runs:
        row = _load_result_file(path)
        missing = [k for k in REQUIRED_KEYS if k not in row]
        if missing:
            raise KeyError(f"{path} missing required keys: {missing}")
        rows.append(row)
    return rows


def _mean(values: List[float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def _maybe_skill_md_metadata_tokens(skill_md: Optional[Path]) -> Optional[int]:
    if skill_md is None:
        return None
    if not skill_md.exists():
        raise FileNotFoundError(f"--skill-md path not found: {skill_md}")
    here = Path(__file__).resolve().parent
    cmd = [sys.executable, str(here / "count_tokens.py"), "--file", str(skill_md), "--metadata-only", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"count_tokens.py crashed (rc={proc.returncode}): {proc.stderr.strip()}")
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError(f"could not parse count_tokens.py JSON: {exc}; stdout={proc.stdout!r}") from exc
    return int(payload["metadata_tokens"])


def _empty_metrics_block() -> Dict[str, Dict[str, Any]]:
    return {dim: {k: None for k in keys} for dim, keys in METRIC_KEYS.items()}


PASS_CELL_THRESHOLD = 0.80


def hoist_r6_routing_latency_p95(
    router_floor_report: Dict[str, Any],
    *,
    pass_threshold: float = PASS_CELL_THRESHOLD,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist R6 from a router_floor_report.yaml dict.

    Spec §3.1 D6 R6 ``routing_latency_p95`` (ms): the cheapest passing
    cell's latency_p95_ms across the router-test sweep. "Passing" means
    the per-cell ``pass_rate >= pass_threshold`` (default 0.80, the spec
    §5.3 router-test cell pass criterion).

    Returns ``(value_ms, derivation_dict)``. ``value_ms`` is the
    selected ``min(latency_p95_ms)`` across passing cells, or ``None``
    if no cells meet the threshold (defensive null preserves the §3.2
    explicit-null contract).

    >>> rf = {"cells": [{"pass_rate": 0.86, "latency_p95_ms": 1100},
    ...                  {"pass_rate": 0.74, "latency_p95_ms": 900}]}
    >>> v, _ = hoist_r6_routing_latency_p95(rf)
    >>> v
    1100.0
    """

    if not isinstance(router_floor_report, dict):
        return None, {"error": "router_floor_report is not a dict"}
    cells = router_floor_report.get("cells")
    if not isinstance(cells, list) or not cells:
        return None, {"error": "router_floor_report has no cells"}

    passing: List[Dict[str, Any]] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        pr = cell.get("pass_rate")
        lat = cell.get("latency_p95_ms")
        if pr is None or lat is None:
            continue
        try:
            pr_f = float(pr)
            lat_f = float(lat)
        except (TypeError, ValueError):
            continue
        if pr_f >= pass_threshold:
            passing.append(
                {
                    "model": cell.get("model"),
                    "thinking_depth": cell.get("thinking_depth"),
                    "scenario_pack": cell.get("scenario_pack"),
                    "pass_rate": pr_f,
                    "latency_p95_ms": lat_f,
                }
            )

    if not passing:
        return None, {
            "error": "no passing cells",
            "pass_threshold": pass_threshold,
            "n_cells_total": len(cells),
        }

    chosen = min(passing, key=lambda c: c["latency_p95_ms"])
    derivation = {
        "method": "min(latency_p95_ms across cells where pass_rate >= threshold)",
        "pass_threshold": pass_threshold,
        "n_cells_total": len(cells),
        "n_cells_passing": len(passing),
        "passing_cells": passing,
        "chosen_cell": chosen,
    }
    return chosen["latency_p95_ms"], derivation


def hoist_l1_wall_clock_p50(
    with_rows: List[Dict[str, Any]],
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist L1 from with-ability per-case ``result.json`` rows.

    Spec §3.1 D3/L1 ``wall_clock_p50`` (seconds): the mean of each
    case's ``latency_p50_s`` across the 6 simulated cases (or whichever
    case set the runner produced). The per-case p50 is emitted by
    Round 4's runner edit (``percentile_p50`` helper).

    The aggregator-level "mean of p50s" is the same aggregate as the
    existing ``L2_wall_clock_p95`` hoist (``mean of p95s``), which
    preserves the L1 ≤ L2 sanity invariant the master plan's
    acceptance criterion requires.

    Returns ``(value_s, derivation_dict)``. ``value_s`` is ``None``
    when no row carries the Round 4 instrumentation (documented
    degenerate path; aggregator MUST NOT silently substitute a
    placeholder per workspace rule "No Silent Failures").

    >>> rows = [{"latency_p50_s": 1.0}, {"latency_p50_s": 1.2}]
    >>> v, _ = hoist_l1_wall_clock_p50(rows)
    >>> round(v, 4)
    1.1
    """

    values: List[float] = []
    skipped_rows = 0
    for r in with_rows:
        val = r.get("latency_p50_s")
        if val is None:
            skipped_rows += 1
            continue
        try:
            values.append(float(val))
        except (TypeError, ValueError):
            skipped_rows += 1

    if not values:
        return None, {
            "error": "no rows carried L1 instrumentation",
            "n_rows_total": len(with_rows),
            "n_rows_skipped": skipped_rows,
            "remediation": (
                "rerun evals/si-chip/runners/with_ability_runner.py — Round 4 "
                "Edit A added per-case latency_p50_s to result.json"
            ),
        }

    value = statistics.fmean(values)
    derivation = {
        "method": "mean(latency_p50_s across with-ability rows)",
        "n_rows_counted": len(values),
        "n_rows_skipped": skipped_rows,
        "n_rows_total": len(with_rows),
        "per_row_values": values,
    }
    return float(value), derivation


def hoist_l3_step_count(
    with_rows: List[Dict[str, Any]],
) -> Tuple[Optional[int], Dict[str, Any]]:
    """Hoist L3 from with-ability per-case ``result.json`` rows.

    Spec §3.1 D3/L3 ``step_count`` (integer >= 1): the mean of each
    case's ``step_count`` rounded to the nearest integer. Each case
    contributes one count because ``step_count`` is a per-invocation
    metric in the simulator (each prompt is one execution step).

    Rounded-mean is defensible for the deterministic simulator because
    every case has exactly 20 prompts; the real-LLM upgrade path will
    report integer steps per invocation and the aggregator rounding
    will remain consistent.

    >>> rows = [{"step_count": 20}, {"step_count": 20}]
    >>> v, _ = hoist_l3_step_count(rows)
    >>> v
    20
    """

    values: List[int] = []
    skipped_rows = 0
    for r in with_rows:
        val = r.get("step_count")
        if val is None:
            skipped_rows += 1
            continue
        try:
            values.append(int(val))
        except (TypeError, ValueError):
            skipped_rows += 1

    if not values:
        return None, {
            "error": "no rows carried L3 instrumentation",
            "n_rows_total": len(with_rows),
            "n_rows_skipped": skipped_rows,
            "remediation": (
                "rerun evals/si-chip/runners/with_ability_runner.py — Round 4 "
                "Edit A added per-case step_count to result.json"
            ),
        }

    mean_value = statistics.fmean(values)
    rounded = int(round(mean_value))
    derivation = {
        "method": "round(mean(step_count across with-ability rows))",
        "n_rows_counted": len(values),
        "n_rows_skipped": skipped_rows,
        "n_rows_total": len(with_rows),
        "per_row_values": values,
        "mean_value": mean_value,
    }
    return rounded, derivation


def hoist_l4_redundant_call_ratio(
    with_rows: List[Dict[str, Any]],
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist L4 from with-ability per-case ``result.json`` rows.

    Spec §3.1 D3/L4 ``redundant_call_ratio`` (float in [0.0, 1.0]):
    the mean of each case's ``redundant_call_ratio``. Degenerate 0.0
    expected for the deterministic simulator (prompt_ids are unique
    within a case). This is a valid value and documented per the
    Round 4 master plan risk_flag.

    >>> rows = [{"redundant_call_ratio": 0.0}, {"redundant_call_ratio": 0.0}]
    >>> v, _ = hoist_l4_redundant_call_ratio(rows)
    >>> v
    0.0
    """

    values: List[float] = []
    skipped_rows = 0
    for r in with_rows:
        val = r.get("redundant_call_ratio")
        if val is None:
            skipped_rows += 1
            continue
        try:
            values.append(float(val))
        except (TypeError, ValueError):
            skipped_rows += 1

    if not values:
        return None, {
            "error": "no rows carried L4 instrumentation",
            "n_rows_total": len(with_rows),
            "n_rows_skipped": skipped_rows,
            "remediation": (
                "rerun evals/si-chip/runners/with_ability_runner.py — Round 4 "
                "Edit A added per-case redundant_call_ratio to result.json"
            ),
        }

    value = statistics.fmean(values)
    if value < 0.0:
        value = 0.0
    if value > 1.0:
        value = 1.0
    derivation = {
        "method": "mean(redundant_call_ratio across with-ability rows) clamped to [0,1]",
        "n_rows_counted": len(values),
        "n_rows_skipped": skipped_rows,
        "n_rows_total": len(with_rows),
        "per_row_values": values,
    }
    return float(value), derivation


# ─────────────── Round 5 D5 usage_cost hoists (U1 + U2) ───────────────
#
# Spec §3.1 D5:
#   U1_description_readability = Flesch-Kincaid grade level of the SKILL.md
#     `description` frontmatter field (computed by
#     count_tokens.skill_md_description_fk_grade). Range [0.0, 24.0].
#   U2_first_time_success_rate = share of should_trigger prompts where
#     the FIRST eval attempt produces a correct outcome. In the
#     deterministic simulator there is no retry, so `correct == True`
#     for a prompt with `expected == "trigger"` IS the first-time success
#     signal. Range [0.0, 1.0].
#
# Both hoists are degenerate-path-safe: if the runner result.json does
# not carry the underlying evidence (missing SKILL.md path, missing
# prompt_outcomes), the hoist returns (None, {"error": ...}) — the
# aggregator surfaces the explicit-null per spec §3.2 frozen constraint
# #2 and the workspace "No Silent Failures" rule.


def hoist_u1_description_readability(
    skill_md_path: Optional[Path],
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist U1 from the SKILL.md frontmatter ``description`` field.

    Spec §3.1 D5/U1 ``description_readability`` (float in [0.0, 24.0]):
    the Flesch-Kincaid grade level of the description string. Computed
    via :func:`count_tokens.skill_md_description_fk_grade` which uses a
    deterministic vowel-group syllable heuristic (no external text-
    analysis library is pulled in — reproducibility across rebuilds is
    the contract).

    Returns ``(grade, derivation_dict)``. ``grade`` is ``None`` when
    ``skill_md_path`` is ``None`` or when the description field is
    absent / unparseable (documented degenerate path). The path MUST
    exist when passed — missing files raise ``FileNotFoundError`` per
    the helper's contract (workspace rule "No Silent Failures").

    See ``test_aggregate_eval.py::HoistU1Tests`` for direct unit
    tests (end-to-end correctness, degenerate paths, determinism).
    """

    if skill_md_path is None:
        return None, {
            "error": "no --skill-md provided",
            "remediation": "pass --skill-md to aggregate_eval.py",
        }

    from count_tokens import skill_md_description_fk_grade  # local import

    grade, details = skill_md_description_fk_grade(skill_md_path)
    derivation: Dict[str, Any] = {
        "method": (
            "Flesch-Kincaid grade level of SKILL.md description frontmatter "
            "field; formula = 0.39*(words/sentences) + 11.8*(syllables/words) "
            "- 15.59; helper = count_tokens.skill_md_description_fk_grade"
        ),
        "skill_md_path": str(skill_md_path),
    }
    if details is not None:
        derivation.update(details)
    if grade is None:
        derivation.setdefault("error", "no description extractable")
        derivation["remediation"] = (
            "ensure the SKILL.md frontmatter contains a non-empty 'description:' key"
        )
        return None, derivation
    return float(grade), derivation


def hoist_u2_first_time_success_rate(
    with_rows: List[Dict[str, Any]],
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist U2 from per-prompt outcomes in with-ability runner rows.

    Spec §3.1 D5/U2 ``first_time_success_rate`` (float in [0.0, 1.0]):
    the rate at which the FIRST trigger attempt produces a correct
    outcome on the should_trigger prompts. The deterministic simulator
    does NOT retry prompts, so each prompt's ``correct`` bool is the
    first-time success signal by construction.

    Denominator = count of prompts with ``expected == "trigger"``
    across all with-ability rows.
    Numerator   = count of those prompts with ``correct == True``.

    Returns ``(rate, derivation_dict)`` where ``rate`` is ``None`` when
    no row carries ``prompt_outcomes`` (or no such row has any
    ``expected == "trigger"`` entry) — this is the documented
    degenerate path and is recorded, not zero-substituted (workspace
    rule "No Silent Failures").

    >>> rows = [{"prompt_outcomes": [
    ...     {"expected": "trigger", "correct": True},
    ...     {"expected": "trigger", "correct": False},
    ...     {"expected": "no_trigger", "correct": True},
    ... ]}]
    >>> v, d = hoist_u2_first_time_success_rate(rows)
    >>> round(v, 4)
    0.5
    >>> d["total_should_trigger"]
    2
    """

    total_should_trigger = 0
    total_first_time_success = 0
    n_rows_with_outcomes = 0
    n_rows_skipped = 0
    per_row_counts: List[Dict[str, int]] = []

    for r in with_rows:
        outcomes = r.get("prompt_outcomes")
        if not isinstance(outcomes, list) or not outcomes:
            n_rows_skipped += 1
            continue
        n_rows_with_outcomes += 1
        row_should_trigger = 0
        row_success = 0
        for o in outcomes:
            if not isinstance(o, dict):
                continue
            if o.get("expected") != "trigger":
                continue
            row_should_trigger += 1
            if bool(o.get("correct")):
                row_success += 1
        case_id = r.get("_meta", {}).get("case_id") if isinstance(r.get("_meta"), dict) else None
        per_row_counts.append(
            {
                "case_id": case_id,
                "should_trigger": row_should_trigger,
                "first_time_success": row_success,
            }
        )
        total_should_trigger += row_should_trigger
        total_first_time_success += row_success

    if total_should_trigger == 0:
        return None, {
            "error": "no should_trigger prompt_outcomes in with-ability rows",
            "n_rows_total": len(with_rows),
            "n_rows_with_outcomes": n_rows_with_outcomes,
            "n_rows_skipped": n_rows_skipped,
            "remediation": (
                "rerun evals/si-chip/runners/with_ability_runner.py against "
                "evals/si-chip/cases/; result.json must carry prompt_outcomes "
                "with per-prompt 'expected' and 'correct' fields."
            ),
        }

    rate = total_first_time_success / total_should_trigger
    derivation = {
        "method": (
            "sum(correct for o in prompt_outcomes if o.expected == 'trigger') / "
            "sum(1 for o in prompt_outcomes if o.expected == 'trigger') across "
            "with-ability rows"
        ),
        "total_should_trigger": total_should_trigger,
        "total_first_time_success": total_first_time_success,
        "n_rows_total": len(with_rows),
        "n_rows_with_outcomes": n_rows_with_outcomes,
        "n_rows_skipped": n_rows_skipped,
        "per_row_counts": per_row_counts,
    }
    return float(rate), derivation


# ─────────── Round 6 D5 usage_cost hoists (U3 + U4) ───────────
#
# Spec §3.1 D5:
#   U3_setup_steps_count = integer count of explicit user-facing steps in
#     the canonical one-line installer flow; reported by the self-declared
#     # SI_CHIP_INSTALLER_STEPS=N header in install.sh. Round 6 target
#     <= 2 (per master plan acceptance criterion #1 — matches CHANGELOG
#     v0.1.1 "one-line installer" claim which is 1 in the non-interactive
#     flow and 2 in the interactive flow with --target + --scope prompts).
#   U4_time_to_first_success = wall-clock seconds from installer
#     invocation to the first '[OK] Installed' line. Default dry_run=True
#     path is a valid floor estimate; real wall-clock is opt-in.
#
# Both hoists are degenerate-path-safe: if install_telemetry payload is
# absent (no --install-telemetry supplied), U3 + U4 stay None — the
# aggregator surfaces the explicit-null per spec §3.2 frozen constraint
# #2 and the workspace "No Silent Failures" rule.


def hoist_u3_setup_steps_count(
    install_telemetry: Optional[Dict[str, Any]],
) -> Tuple[Optional[int], Dict[str, Any]]:
    """Hoist U3 from an install_telemetry payload.

    Spec §3.1 D5/U3 ``setup_steps_count`` (integer >= 0): the canonical
    user-facing step count of the one-line installer flow, sourced from
    :func:`install_telemetry.count_setup_steps` via the
    ``install_telemetry.json`` written by
    ``tools/install_telemetry.py --json``.

    Returns ``(value, derivation_dict)``. ``value`` is ``None`` when the
    payload is not supplied or missing the expected key (documented
    degenerate path; aggregator must NOT silently substitute 0 per
    workspace rule "No Silent Failures").

    >>> payload = {"u3_setup_steps_count": 1, "derivation": {}}
    >>> v, _ = hoist_u3_setup_steps_count(payload)
    >>> v
    1
    """

    if install_telemetry is None:
        return None, {
            "error": "no install_telemetry provided",
            "remediation": "pass --install-telemetry to aggregate_eval.py",
        }
    if not isinstance(install_telemetry, dict):
        return None, {"error": "install_telemetry payload is not a dict"}

    raw = install_telemetry.get("u3_setup_steps_count")
    if raw is None:
        return None, {
            "error": "install_telemetry missing u3_setup_steps_count",
            "remediation": (
                "rerun tools/install_telemetry.py --install-sh install.sh --json"
            ),
        }
    try:
        count = int(raw)
    except (TypeError, ValueError):
        return None, {"error": f"u3_setup_steps_count is not an int: {raw!r}"}
    if count < 0:
        return None, {"error": f"u3_setup_steps_count must be >= 0, got {count}"}

    derivation: Dict[str, Any] = {
        "method": (
            "install_telemetry.count_setup_steps(install.sh); parses "
            "# SI_CHIP_INSTALLER_STEPS=N header (fallback: unguarded "
            "'read -p'/'read -r' count)."
        ),
        "value": count,
        "v1_baseline_gate": "<= 2 (matches CHANGELOG v0.1.1 one-line installer claim)",
    }
    if "install_script_path" in install_telemetry:
        derivation["install_script_path"] = install_telemetry["install_script_path"]
    if isinstance(install_telemetry.get("derivation"), dict):
        derivation["telemetry_derivation"] = install_telemetry["derivation"]
    return count, derivation


def hoist_u4_time_to_first_success(
    install_telemetry: Optional[Dict[str, Any]],
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist U4 from an install_telemetry payload.

    Spec §3.1 D5/U4 ``time_to_first_success`` (seconds, [0, 60]):
    wall-clock time from installer invocation to the first
    ``[OK] Installed`` stdout line. The value is sourced from
    :func:`install_telemetry.time_first_success`.

    Returns ``(value, derivation_dict)``. ``value`` is ``None`` in the
    documented degenerate path (no payload supplied, payload has
    ``u4_time_to_first_success_s == null``, or negative duration).
    Aggregator surfaces the explicit null per spec §3.2.

    >>> payload = {"u4_time_to_first_success_s": 0.42, "dry_run": True}
    >>> v, _ = hoist_u4_time_to_first_success(payload)
    >>> round(v, 2)
    0.42
    """

    if install_telemetry is None:
        return None, {
            "error": "no install_telemetry provided",
            "remediation": "pass --install-telemetry to aggregate_eval.py",
        }
    if not isinstance(install_telemetry, dict):
        return None, {"error": "install_telemetry payload is not a dict"}

    raw = install_telemetry.get("u4_time_to_first_success_s")
    if raw is None:
        return None, {
            "error": "install_telemetry missing u4_time_to_first_success_s",
            "remediation": (
                "rerun tools/install_telemetry.py --install-sh install.sh --json; "
                "U4 is None whenever the installer exits non-zero, times out, or "
                "fails to emit '[OK] Installed'."
            ),
        }
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, {"error": f"u4_time_to_first_success_s is not a float: {raw!r}"}
    if value < 0.0:
        return None, {"error": f"u4_time_to_first_success_s must be >= 0, got {value}"}

    derivation: Dict[str, Any] = {
        "method": (
            "install_telemetry.time_first_success(install.sh, dry_run=<mode>); "
            "wall-clock seconds from bash invocation to first '[OK] Installed' line."
        ),
        "value_s": value,
        "dry_run": bool(install_telemetry.get("dry_run", True)),
        "v1_baseline_gate": "<= 60 s (sanity ceiling for one-line install)",
    }
    if "install_script_path" in install_telemetry:
        derivation["install_script_path"] = install_telemetry["install_script_path"]
    if isinstance(install_telemetry.get("derivation"), dict):
        derivation["telemetry_derivation"] = install_telemetry["derivation"]
    return value, derivation


def hoist_r7_routing_token_overhead(
    with_rows: List[Dict[str, Any]],
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist R7 from with-ability per-case result.json rows.

    Spec §3.1 D6 R7 ``routing_token_overhead`` =
    ``sum(routing_stage_tokens) / sum(body_invocation_tokens)`` across
    every prompt invocation (case-aggregate sums work because the
    runner emits per-case totals).

    Returns ``(value, derivation_dict)``. Result is ``None`` if no row
    carries the new R7 instrumentation fields (Round 3 Edit A); this is
    the documented degenerate path and must be recorded in
    ``raw/r7_derivation.json`` per the master iteration plan.

    >>> rows = [{"routing_stage_tokens_total": 78,
    ...          "body_invocation_tokens_total": 3520}]
    >>> v, _ = hoist_r7_routing_token_overhead(rows)
    >>> round(v, 4)
    0.0222
    """

    routing_total = 0
    body_total = 0
    counted_rows = 0
    skipped_rows = 0
    for r in with_rows:
        rs = r.get("routing_stage_tokens_total")
        bi = r.get("body_invocation_tokens_total")
        if rs is None or bi is None:
            skipped_rows += 1
            continue
        try:
            routing_total += int(rs)
            body_total += int(bi)
            counted_rows += 1
        except (TypeError, ValueError):
            skipped_rows += 1

    if counted_rows == 0 or body_total <= 0:
        return None, {
            "error": "no rows carried R7 instrumentation",
            "counted_rows": counted_rows,
            "skipped_rows": skipped_rows,
            "n_rows_total": len(with_rows),
            "remediation": (
                "rerun evals/si-chip/runners/with_ability_runner.py against "
                "evals/si-chip/cases/ — Round 3 Edit A added per-prompt "
                "routing_stage_tokens + body_invocation_tokens to result.json"
            ),
        }

    ratio = routing_total / body_total
    derivation = {
        "method": "sum(routing_stage_tokens_total) / sum(body_invocation_tokens_total) across with-ability rows",
        "sum_routing_stage_tokens": routing_total,
        "sum_body_invocation_tokens": body_total,
        "n_rows_counted": counted_rows,
        "n_rows_skipped": skipped_rows,
        "n_rows_total": len(with_rows),
    }
    return ratio, derivation


def build_report(
    with_rows: List[Dict[str, Any]],
    without_rows: List[Dict[str, Any]],
    runs_dir: Path,
    baseline_dir: Path,
    skill_md_meta_tokens: Optional[int],
    *,
    router_floor_report: Optional[Dict[str, Any]] = None,
    skill_md_path: Optional[Path] = None,
    install_telemetry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute the metrics_report dict from collected rows.

    Populates MVP-8 keys; leaves the other 20 sub-metric keys at
    ``null`` per spec §3.2 frozen constraint #2.

    Round 3 (S5 task spec Edit B) hoists D6 R6 and R7:

    * R6_routing_latency_p95 = ``min(latency_p95_ms across passing
      cells)`` from ``router_floor_report`` when supplied.
    * R7_routing_token_overhead = ``sum(routing_stage_tokens_total) /
      sum(body_invocation_tokens_total)`` across ``with_rows`` when the
      Round 3 Edit A instrumentation is present.

    Round 4 (S5 task spec Edit C) hoists D3 L1 / L3 / L4:

    * L1_wall_clock_p50 = ``mean(latency_p50_s across with-ability rows)``.
    * L3_step_count = ``round(mean(step_count across with-ability rows))``.
    * L4_redundant_call_ratio = ``mean(redundant_call_ratio across with-ability rows)``,
      clamped to ``[0.0, 1.0]``.

    Round 5 (S5 task spec Edit B) hoists D5 U1 / U2:

    * U1_description_readability = Flesch-Kincaid grade level of the
      SKILL.md ``description`` frontmatter field (requires
      ``skill_md_path``). Range [0.0, 24.0].
    * U2_first_time_success_rate = share of should_trigger prompts
      whose first attempt is correct (from ``prompt_outcomes``).
      Range [0.0, 1.0].

    Round 6 (S5 task spec Edit C) hoists D5 U3 / U4:

    * U3_setup_steps_count = integer count of explicit user-facing steps
      in the canonical one-line installer flow (from install_telemetry
      payload; typically 1 for the ``--yes`` non-interactive path). Range
      ``[0, N]``.
    * U4_time_to_first_success = wall-clock seconds from installer
      invocation to first ``[OK] Installed`` line (from install_telemetry
      payload; dry-run floor estimate in CI/offline envs). Range
      ``[0.0, 60.0]``.

    All hoisted fields stay ``null`` when their data source is
    degenerate; the aggregator MUST NOT silently substitute a
    placeholder (workspace rule "No Silent Failures").
    """

    pass_with = _mean([float(r["pass_rate"]) for r in with_rows])
    pass_without = _mean([float(r["pass_rate"]) for r in without_rows])
    pass_k4 = _mean([float(r["pass_k_4"]) for r in with_rows])
    latency_p95 = _mean([float(r["latency_p95_s"]) for r in with_rows])
    footprint = _mean([float(r["per_invocation_footprint"]) for r in with_rows])
    trigger_f1 = _mean([float(r["trigger_F1"]) for r in with_rows])
    floors = sorted({str(r["router_floor"]) for r in with_rows})
    router_floor = floors[0] if len(floors) == 1 else "/".join(floors)

    if skill_md_meta_tokens is not None:
        metadata_tokens: Any = skill_md_meta_tokens
    else:
        metadata_tokens = _mean([float(r["metadata_tokens"]) for r in with_rows])

    metrics = _empty_metrics_block()
    metrics["task_quality"]["T1_pass_rate"] = pass_with
    metrics["task_quality"]["T2_pass_k"] = pass_k4
    metrics["task_quality"]["T3_baseline_delta"] = pass_with - pass_without
    metrics["context_economy"]["C1_metadata_tokens"] = metadata_tokens
    metrics["context_economy"]["C4_per_invocation_footprint"] = footprint
    metrics["latency_path"]["L2_wall_clock_p95"] = latency_p95
    metrics["routing_cost"]["R3_trigger_F1"] = trigger_f1
    metrics["routing_cost"]["R5_router_floor"] = router_floor

    r6_value: Optional[float] = None
    r6_derivation: Dict[str, Any] = {"loaded": False}
    if router_floor_report is not None:
        r6_value, r6_derivation = hoist_r6_routing_latency_p95(router_floor_report)
        r6_derivation["loaded"] = True
    metrics["routing_cost"]["R6_routing_latency_p95"] = r6_value

    r7_value, r7_derivation = hoist_r7_routing_token_overhead(with_rows)
    metrics["routing_cost"]["R7_routing_token_overhead"] = r7_value

    # Round 4 (S5 task spec Edit C): hoist D3 L1 / L3 / L4.
    l1_value, l1_derivation = hoist_l1_wall_clock_p50(with_rows)
    metrics["latency_path"]["L1_wall_clock_p50"] = l1_value
    l3_value, l3_derivation = hoist_l3_step_count(with_rows)
    metrics["latency_path"]["L3_step_count"] = l3_value
    l4_value, l4_derivation = hoist_l4_redundant_call_ratio(with_rows)
    metrics["latency_path"]["L4_redundant_call_ratio"] = l4_value

    if l1_value is not None and l1_value > latency_p95:
        raise ValueError(
            "L1 sanity invariant violated: "
            f"L1_wall_clock_p50={l1_value:.6f} > L2_wall_clock_p95={latency_p95:.6f}; "
            "refusing to silently emit a bad metric (workspace rule 'No Silent Failures')."
        )

    # Round 5 (S5 task spec Edit B): hoist D5 U1 / U2.
    u1_value, u1_derivation = hoist_u1_description_readability(skill_md_path)
    metrics["usage_cost"]["U1_description_readability"] = u1_value
    u2_value, u2_derivation = hoist_u2_first_time_success_rate(with_rows)
    metrics["usage_cost"]["U2_first_time_success_rate"] = u2_value

    # Round 6 (S5 task spec Edit C): hoist D5 U3 / U4.
    u3_value, u3_derivation = hoist_u3_setup_steps_count(install_telemetry)
    metrics["usage_cost"]["U3_setup_steps_count"] = u3_value
    u4_value, u4_derivation = hoist_u4_time_to_first_success(install_telemetry)
    metrics["usage_cost"]["U4_time_to_first_success"] = u4_value

    devolaflow_version = _safe_devolaflow_version()

    report = {
        "metrics": metrics,
        "summary": {
            "with_ability_runs": len(with_rows),
            "no_ability_runs": len(without_rows),
            "pass_rate_with": pass_with,
            "pass_rate_without": pass_without,
            "baseline_delta": pass_with - pass_without,
        },
        "provenance": {
            "runs_dir": str(runs_dir),
            "baseline_dir": str(baseline_dir),
            "computed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "script_version": SCRIPT_VERSION,
            "devolaflow_version": devolaflow_version,
            "metadata_tokens_source": "skill_md" if skill_md_meta_tokens is not None else "result.json mean",
            "r6_derivation": r6_derivation,
            "r7_derivation": r7_derivation,
            "l1_derivation": l1_derivation,
            "l3_derivation": l3_derivation,
            "l4_derivation": l4_derivation,
            "u1_derivation": u1_derivation,
            "u2_derivation": u2_derivation,
            "u3_derivation": u3_derivation,
            "u4_derivation": u4_derivation,
        },
    }
    return report


def _maybe_load_router_floor_report(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Load a router_floor_report.yaml when ``path`` is provided.

    Raises ``FileNotFoundError`` when ``path`` is set but missing
    (workspace rule "No Silent Failures").
    """

    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"--router-floor-report path not found: {path}")
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: router_floor_report must be a YAML mapping")
    return data


def _maybe_load_install_telemetry(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Load an install_telemetry.json when ``path`` is provided.

    Raises ``FileNotFoundError`` when ``path`` is set but missing
    (workspace rule "No Silent Failures"). Returns ``None`` when
    ``path`` is ``None`` (caller has not requested U3/U4 hoisting).
    """

    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"--install-telemetry path not found: {path}")
    with path.open("r", encoding="utf-8") as fp:
        try:
            data = json.load(fp)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: install_telemetry must be a JSON object")
    return data


def _safe_devolaflow_version() -> Optional[str]:
    try:
        import devolaflow  # type: ignore[import-not-found]
    except ImportError as exc:
        LOGGER.warning("devolaflow not importable: %s", exc)
        return None
    version = getattr(devolaflow, "__version__", None)
    LOGGER.info("devolaflow version: %s", version)
    return version


def _load_template_metrics(templates_dir: Path) -> Optional[Dict[str, Any]]:
    schema_path = templates_dir / "basic_ability_profile.schema.yaml"
    if not schema_path.exists():
        LOGGER.warning("schema not found at %s; skipping cross-check", schema_path)
        return None
    try:
        with schema_path.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"failed to parse {schema_path}: {exc}") from exc
    metrics = data.get("basic_ability", {}).get("metrics") if isinstance(data, dict) else None
    if not isinstance(metrics, dict):
        LOGGER.warning("schema lacks 'basic_ability.metrics' mapping; skipping cross-check")
        return None
    return metrics


def _cross_check_metrics(report_metrics: Dict[str, Any], template_metrics: Optional[Dict[str, Any]]) -> None:
    if not template_metrics:
        return
    expected_dims = set(template_metrics.keys())
    actual_dims = set(report_metrics.keys())
    if expected_dims != actual_dims:
        LOGGER.warning(
            "metrics dimensions differ (expected=%s actual=%s)",
            sorted(expected_dims),
            sorted(actual_dims),
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate eval runs into a Si-Chip metrics_report.yaml.",
    )
    parser.add_argument("--runs-dir", required=True, help="Directory of with-ability run outputs.")
    parser.add_argument("--baseline-dir", required=True, help="Directory of no-ability baseline run outputs.")
    parser.add_argument("--out", default=None, help="Output YAML path (default: <runs-dir>/../metrics_report.yaml).")
    parser.add_argument("--templates-dir", default="templates", help="Templates directory (default: templates/).")
    parser.add_argument(
        "--skill-md",
        default=None,
        help="Optional SKILL.md path; when set, C1_metadata_tokens is sourced from count_tokens.py against it.",
    )
    parser.add_argument(
        "--router-floor-report",
        default=None,
        help=(
            "Optional router_floor_report.yaml path; when set, "
            "R6_routing_latency_p95 is hoisted from min(latency_p95_ms) "
            "across cells with pass_rate >= 0.80 (Round 3 Edit B)."
        ),
    )
    parser.add_argument(
        "--install-telemetry",
        default=None,
        help=(
            "Optional install_telemetry.json path (emitted by "
            "tools/install_telemetry.py --json). When set, U3_setup_steps_count "
            "and U4_time_to_first_success are hoisted into metrics.usage_cost "
            "(Round 6 Edit C)."
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Set log level to INFO.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    _ = _safe_devolaflow_version()

    runs_dir = Path(args.runs_dir).resolve()
    baseline_dir = Path(args.baseline_dir).resolve()
    skill_md = Path(args.skill_md).resolve() if args.skill_md else None
    router_floor_path = Path(args.router_floor_report).resolve() if args.router_floor_report else None
    install_telemetry_path = (
        Path(args.install_telemetry).resolve() if args.install_telemetry else None
    )

    with_runs = _walk_runs(runs_dir)
    base_runs = _walk_runs(baseline_dir)
    LOGGER.info("with-ability runs: %d, no-ability runs: %d", len(with_runs), len(base_runs))

    with_rows = _collect(with_runs)
    without_rows = _collect(base_runs)

    skill_md_meta = _maybe_skill_md_metadata_tokens(skill_md)
    router_floor_report = _maybe_load_router_floor_report(router_floor_path)
    install_telemetry = _maybe_load_install_telemetry(install_telemetry_path)
    report = build_report(
        with_rows,
        without_rows,
        runs_dir,
        baseline_dir,
        skill_md_meta,
        router_floor_report=router_floor_report,
        skill_md_path=skill_md,
        install_telemetry=install_telemetry,
    )

    template_metrics = _load_template_metrics(Path(args.templates_dir).resolve())
    _cross_check_metrics(report["metrics"], template_metrics)

    out_path = Path(args.out).resolve() if args.out else (runs_dir.parent / "metrics_report.yaml")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fp:
        yaml.safe_dump(report, fp, sort_keys=False, allow_unicode=True)
    print(out_path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.getLogger("si_chip.aggregate_eval").error("fatal: %s", exc)
        sys.exit(1)
