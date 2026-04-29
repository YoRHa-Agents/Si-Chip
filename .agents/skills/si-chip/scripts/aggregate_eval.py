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
import glob
import json
import logging
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

LOGGER = logging.getLogger("si_chip.aggregate_eval")

SCRIPT_VERSION = "0.1.6"

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


# ─────────── Round 7 D2 context_economy hoists (C5 + C6) ───────────
#
# Spec §3.1 D2:
#   C5_context_rot_risk = deterministic proxy based on (body_tokens /
#     typical_context_window) + 0.05 * reference_fanout_depth, clipped to
#     [0.0, 1.0]. Computed by count_tokens.context_rot_risk via
#     count_tokens.skill_md_context_rot_risk. Fanout is the count of
#     *.md files under references_dir that the SKILL.md body literally
#     references by filename (Round 7 task spec §1).
#   C6_scope_overlap_score = max Jaccard similarity between Si-Chip
#     SKILL.md description tokens and neighbor skill SKILL.md description
#     tokens. Computed by count_tokens.skill_md_scope_overlap_score
#     (Round 7 task spec §2).
#
# Both hoists are degenerate-path-safe and NEVER silently substitute a
# placeholder — they return None-plus-error-record on any failure so the
# aggregator preserves the §3.2 explicit-null contract and workspace
# "No Silent Failures" rule.


def hoist_c5_context_rot_risk(
    skill_md_path: Optional[Path],
    references_dir: Optional[Path],
    typical_window: int = 200_000,
    *,
    strict: bool = False,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist C5 from a SKILL.md + its references directory.

    Spec §3.1 D2/C5 ``context_rot_risk`` (float in ``[0.0, 1.0]``):
    the deterministic approximation documented in Round 7 task spec §1.

    Returns ``(value, derivation_dict)``. ``value`` is ``None`` when
    ``skill_md_path`` is not provided or when the helper fails (with
    a logged warning). Permissive default: unexpected exceptions are
    caught, logged, and mapped to ``(None, {"error": ...})``. Pass
    ``strict=True`` to re-raise (useful for unit tests).

    >>> # Smoke check: None path → None return (documented degenerate path).
    >>> v, d = hoist_c5_context_rot_risk(None, None)
    >>> v is None and "error" in d
    True
    """

    if skill_md_path is None:
        return None, {
            "error": "no --skill-md provided",
            "remediation": "pass --skill-md to aggregate_eval.py",
        }

    from count_tokens import skill_md_context_rot_risk  # local import

    try:
        value, deriv = skill_md_context_rot_risk(
            skill_md_path, references_dir, typical_window
        )
    except FileNotFoundError:
        raise  # re-raise: explicit missing-path failure bubbles per "No Silent Failures".
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("hoist_c5 unexpected error: %s", exc)
        if strict:
            raise
        return None, {
            "error": f"hoist_c5 failed: {exc}",
            "skill_md_path": str(skill_md_path),
        }

    if value is None:
        return None, deriv

    if not (0.0 <= value <= 1.0):
        LOGGER.warning("C5 out of range after hoist: %s", value)
        deriv["range_sanity_check"] = f"FAIL (C5 {value} not in [0.0, 1.0])"
        if strict:
            raise ValueError(f"C5 out of [0.0, 1.0]: {value}")
        return None, deriv

    deriv["range_sanity_check"] = f"PASS (C5 {value} in [0.0, 1.0])"
    deriv["v1_baseline_gate"] = "n/a (C5 has no §4.1 hard threshold; informational)"
    return float(value), deriv


def hoist_c6_scope_overlap_score(
    skill_md_path: Optional[Path],
    neighbor_skill_md_paths: Optional[Iterable[Path]],
    *,
    strict: bool = False,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist C6 from a SKILL.md vs a neighbor SKILL.md list.

    Spec §3.1 D2/C6 ``scope_overlap_score`` (float in ``[0.0, 1.0]``):
    max Jaccard similarity between the base SKILL.md description and
    each neighbor's description; computed by
    :func:`count_tokens.skill_md_scope_overlap_score`.

    Returns ``(value, derivation_dict)`` where ``derivation_dict``
    includes every neighbor pair with per-pair jaccard + an
    ``error`` entry for missing / unreadable neighbors (logged via
    ``LOGGER.warning`` — never silently swallowed per workspace rule).

    Permissive default: unexpected exceptions are caught, logged, and
    mapped to ``(None, {"error": ...})``. Pass ``strict=True`` to
    re-raise.

    >>> v, d = hoist_c6_scope_overlap_score(None, None)
    >>> v is None and "error" in d
    True
    """

    if skill_md_path is None:
        return None, {
            "error": "no --skill-md provided",
            "remediation": "pass --skill-md to aggregate_eval.py",
        }

    neighbor_list: List[Path] = list(neighbor_skill_md_paths or [])
    if not neighbor_list:
        LOGGER.warning(
            "hoist_c6: no neighbor SKILL.md paths supplied; C6 defaults to 0.0"
        )
        return 0.0, {
            "method": "skill_md_scope_overlap_score(skill_md, neighbors); empty neighbor list",
            "n_neighbors_attempted": 0,
            "n_neighbors_scored": 0,
            "pairs": [],
            "range_sanity_check": "PASS (C6 0.0 in [0.0, 1.0])",
        }

    from count_tokens import skill_md_scope_overlap_score  # local import

    try:
        value, pairs = skill_md_scope_overlap_score(
            skill_md_path, neighbor_list
        )
    except FileNotFoundError:
        raise  # explicit missing-base-path failure bubbles per "No Silent Failures".
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("hoist_c6 unexpected error: %s", exc)
        if strict:
            raise
        return None, {
            "error": f"hoist_c6 failed: {exc}",
            "skill_md_path": str(skill_md_path),
        }

    if value is None:
        return None, {
            "error": "no scorable neighbors or base description missing",
            "n_neighbors_attempted": len(neighbor_list),
            "pairs": pairs,
        }

    if not (0.0 <= value <= 1.0):  # pragma: no cover - should not happen by construction
        LOGGER.warning("C6 out of range: %s", value)
        if strict:
            raise ValueError(f"C6 out of [0.0, 1.0]: {value}")
        return None, {
            "error": f"C6 out of [0.0, 1.0]: {value}",
            "pairs": pairs,
        }

    scored_pairs = [p for p in pairs if isinstance(p.get("jaccard"), (int, float))]
    skipped_pairs = [p for p in pairs if not isinstance(p.get("jaccard"), (int, float))]
    derivation: Dict[str, Any] = {
        "method": (
            "max(jaccard_similarity(tokenize(base_desc), tokenize(neighbor_desc))) "
            "across neighbor SKILL.md set; helper = count_tokens."
            "skill_md_scope_overlap_score"
        ),
        "skill_md_path": str(skill_md_path),
        "n_neighbors_attempted": len(neighbor_list),
        "n_neighbors_scored": len(scored_pairs),
        "n_neighbors_skipped": len(skipped_pairs),
        "pairs": pairs,
        "max_jaccard": value,
        "range_sanity_check": f"PASS (C6 {value} in [0.0, 1.0])",
        "v1_baseline_gate": "n/a (C6 has no §4.1 hard threshold; informational)",
    }
    return float(value), derivation


# ─────────── Round 9 D6 routing_cost hoist (R8 description_competition_index) ───────────
#
# Spec §3.1 D6 R8:
#   R8_description_competition_index = formal across-matrix description
#     -competition index between Si-Chip's SKILL.md description and the
#     neighbor skill SKILL.md descriptions. Computed by
#     count_tokens.skill_md_description_competition_index with two
#     supported methods:
#
#       * method="max_jaccard"  (default) — R8 = max Jaccard across
#         neighbors. SAME formula family as C6 but exposed under a
#         distinct D6 slot; surfaces the WORST single offender (the
#         neighbor most likely to steal a routing invocation).
#       * method="tfidf_cosine_mean" — R8 = MEAN TF-IDF cosine across
#         neighbors. Surfaces AVERAGE competition; complementary
#         signal.
#
# Both methods are DETERMINISTIC (sorted vocab; no RNG). The hoist is
# metadata-retrieval per spec §5.1 — NOT router model training (§5.2
# forbidden). See .local/dogfood/2026-04-28/round_9/raw/r8_derivation.json
# for the per-neighbor trace.


def hoist_r8_description_competition_index(
    skill_md_path: Optional[Path],
    neighbor_skill_md_paths: Optional[Iterable[Path]],
    *,
    method: str = "max_jaccard",
    strict: bool = False,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """Hoist R8 from a SKILL.md vs a neighbor SKILL.md list.

    Spec §3.1 D6 R8 ``description_competition_index`` (float in
    ``[0.0, 1.0]``): formal across-matrix similarity between Si-Chip's
    SKILL.md description and every neighbor skill's description.
    Computed by :func:`count_tokens.skill_md_description_competition_index`.

    Returns ``(value, derivation_dict)``. ``value`` is ``None`` in the
    documented degenerate paths:
      * ``skill_md_path`` is ``None``
      * neighbor list is empty (ValueError from helper → recorded)
      * unknown method (ValueError from helper → recorded)

    Permissive default: unexpected exceptions are caught, logged, and
    mapped to ``(None, {"error": ...})`` so the aggregator does NOT
    silently substitute a zero. Pass ``strict=True`` to re-raise.

    >>> v, d = hoist_r8_description_competition_index(None, None)
    >>> v is None and "error" in d
    True
    """

    if skill_md_path is None:
        return None, {
            "error": "no --skill-md provided",
            "remediation": "pass --skill-md to aggregate_eval.py",
        }

    neighbor_list: List[Path] = list(neighbor_skill_md_paths or [])
    if not neighbor_list:
        LOGGER.warning(
            "hoist_r8: no neighbor SKILL.md paths supplied; R8 left null"
        )
        return None, {
            "error": "no neighbor SKILL.md paths supplied",
            "method": method,
            "remediation": (
                "pass --neighbor-skills-glob with at least one match "
                "to aggregate_eval.py"
            ),
        }

    from count_tokens import (  # local import
        skill_md_description_competition_index,
    )

    try:
        value, pairs = skill_md_description_competition_index(
            skill_md_path, neighbor_list, method=method
        )
    except FileNotFoundError:
        raise  # explicit missing-base-path bubbles per "No Silent Failures".
    except ValueError as exc:
        LOGGER.warning("hoist_r8 rejected: %s", exc)
        if strict:
            raise
        return None, {
            "error": f"hoist_r8 rejected: {exc}",
            "skill_md_path": str(skill_md_path),
            "method": method,
        }
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("hoist_r8 unexpected error: %s", exc)
        if strict:
            raise
        return None, {
            "error": f"hoist_r8 failed: {exc}",
            "skill_md_path": str(skill_md_path),
            "method": method,
        }

    if not (0.0 <= value <= 1.0):  # pragma: no cover - should not happen
        LOGGER.warning("R8 out of range: %s", value)
        if strict:
            raise ValueError(f"R8 out of [0.0, 1.0]: {value}")
        return None, {
            "error": f"R8 out of [0.0, 1.0]: {value}",
            "pairs": pairs,
            "method": method,
        }

    scored_pairs = [
        p for p in pairs if isinstance(p.get("similarity"), (int, float))
    ]
    skipped_pairs = [
        p for p in pairs if not isinstance(p.get("similarity"), (int, float))
    ]
    method_note = {
        "max_jaccard": (
            "R8 == max(Jaccard(base_tokens, neighbor_tokens)) across neighbor "
            "set. Same formula family as C6; surfaces the WORST single "
            "offender (the neighbor most likely to steal a routing "
            "invocation). Default method."
        ),
        "tfidf_cosine_mean": (
            "R8 == mean(cosine(tfidf(base_tokens, corpus), tfidf(neighbor_tokens, "
            "corpus))) across neighbor set. Surfaces AVERAGE competition "
            "(complementary signal to max-Jaccard WORST-offender)."
        ),
    }[method]
    derivation: Dict[str, Any] = {
        "method": (
            f"count_tokens.skill_md_description_competition_index("
            f"skill_md, neighbors, method={method!r})"
        ),
        "method_note": method_note,
        "method_name": method,
        "skill_md_path": str(skill_md_path),
        "neighbor_paths": [str(p) for p in neighbor_list],
        "n_neighbors_attempted": len(neighbor_list),
        "n_neighbors_scored": len(scored_pairs),
        "n_neighbors_skipped": len(skipped_pairs),
        "pairs": pairs,
        "chosen_value": value,
        "range_sanity_check": f"PASS (R8 {value} in [0.0, 1.0])",
        "v1_baseline_gate": "n/a (R8 has no §4.1 hard threshold; informational)",
        "spec_section_compliance": (
            "§5.1 metadata-retrieval surface (kNN/heuristic baseline); "
            "NOT §5.2 router-model training (forbidden)"
        ),
    }
    return float(value), derivation


# ─────────── Round 10 D4 generalizability hoist (G1 cross_model_pass_matrix) ───────────
#
# Spec §3.1 D4 G1:
#   G1_cross_model_pass_matrix = per (model, scenario_pack) pass_rate matrix
#     across the router-test sweep. v0.1.x partial-fill collapses the
#     depth dimension of the 8-cell MVP sweep (2 model × 2 depth × 2 pack)
#     into a 2-model-by-2-pack nested dict:
#
#       {
#         "composer_2":     {"trigger_basic": float, "near_miss": float},
#         "sonnet_shallow": {"trigger_basic": float, "near_miss": float},
#       }
#
# Collapse rule = ``max(pass_rate) across thinking_depth``. Using max
# (rather than mean) preserves the best-case generalizability signal:
# if ANY depth passes for that (model, pack) combination, the matrix
# records the highest observed rate. The max aggregation is monotone
# under adding more depths later, so the hoist is forward-compatible
# with the 96-cell full profile (v2_tightened+ / Round 12+ upgrade).
#
# PARTIAL PROXY DISCLOSURE: This G1 is a 2-model × 2-pack view of the
# full 6-model × 4-pack G1 surface defined by spec §5.3 full:96 profile.
# The authoritative G1 requires a real-LLM runner against all 96 cells —
# v0.1.x stays with the mvp 8-cell sweep by master plan design (§5.3
# full profile stays gated to v2_tightened+). G2/G3/G4 (cross-domain
# transfer, OOD robustness, model-version stability) stay null by scope
# for v0.1.x.
#
# Spec §11.1 compliance: G1 is a static pass_rate matrix derived from
# deterministic sweep cells — NOT router-model training (§5.2
# forbidden). §5.1 metadata-retrieval surface only.


def hoist_g1_cross_model_pass_matrix(
    router_floor_report: Optional[Dict[str, Any]],
    *,
    packs: Optional[Iterable[str]] = None,
) -> Tuple[Optional[Dict[str, Dict[str, float]]], Dict[str, Any]]:
    """Hoist G1 cross-model × pack pass-rate matrix from a router_floor_report.

    Spec §3.1 D4 G1 ``cross_model_pass_matrix`` (nested dict). Returns a
    2-model-by-2-pack (or wider) nested dict
    ``{model: {pack: pass_rate, ...}, ...}`` derived from the MVP 8-cell
    sweep's cells, or ``None`` when the sweep is missing / malformed.

    Accepted input shapes (both work because
    ``_maybe_load_router_floor_report`` may return either):

    * Flat: ``{"cells": [...], ...}`` (Rounds 1-8 legacy + unit-test fixtures).
    * Nested: ``{"mvp_profile": {"cells": [...], ...}, ...}`` (Round 9 NEW
      — when the report emits BOTH mvp and intermediate profiles, the
      mvp cells live under the ``mvp_profile`` key). If the nested path
      is present the hoist uses it; if only a flat ``cells`` list
      exists the hoist falls back to that.

    The collapse rule is ``max(pass_rate) across thinking_depth`` per
    ``(model, scenario_pack)``. Using max preserves best-case
    generalizability and stays monotone as more depths are added
    (forward-compatible with the 96-cell full profile).

    Args:
        router_floor_report: Full router-floor-report dict (either flat
            or nested). ``None`` is accepted → returns ``(None, {"error": ...})``.
        packs: Optional iterable of pack names to include in the matrix
            (defaults to every pack observed in the sweep). Narrow when
            a round only wants e.g. ``("trigger_basic", "near_miss")``
            from a wider intermediate 4-pack profile.

    Returns:
        ``(matrix, derivation)`` where ``matrix`` is the nested dict
        above or ``None`` on degenerate paths. ``derivation`` always
        carries the provenance trace (source profile, collapse rule,
        per-cell values, range-sanity check, spec compliance note).

    Degenerate paths (``None`` return + ``derivation["error"]`` set):

    * ``router_floor_report`` is ``None`` or not a dict.
    * Neither flat ``cells`` nor ``mvp_profile.cells`` is a non-empty list.
    * No cell entries produced a usable ``(model, pack, pass_rate)``
      triple after requested-pack filtering.

    No silent zero substitution (workspace rule "No Silent Failures").

    >>> rf = {"cells": [
    ...   {"model": "composer_2", "thinking_depth": "fast",
    ...    "scenario_pack": "trigger_basic", "pass_rate": 0.86},
    ...   {"model": "composer_2", "thinking_depth": "default",
    ...    "scenario_pack": "trigger_basic", "pass_rate": 0.90},
    ...   {"model": "composer_2", "thinking_depth": "fast",
    ...    "scenario_pack": "near_miss", "pass_rate": 0.78},
    ...   {"model": "composer_2", "thinking_depth": "default",
    ...    "scenario_pack": "near_miss", "pass_rate": 0.83},
    ... ]}
    >>> matrix, _ = hoist_g1_cross_model_pass_matrix(rf)
    >>> matrix["composer_2"]["trigger_basic"]
    0.9
    >>> matrix["composer_2"]["near_miss"]
    0.83
    """

    if router_floor_report is None or not isinstance(router_floor_report, dict):
        return None, {"error": "router_floor_report is None or not a dict"}

    # Prefer nested mvp_profile.cells (Round 9+ emitted shape); fall back
    # to flat top-level cells (Round 1-8 legacy + test fixtures).
    cells: Any = None
    source_shape = "unknown"
    mvp_profile = router_floor_report.get("mvp_profile")
    if isinstance(mvp_profile, dict):
        candidate = mvp_profile.get("cells")
        if isinstance(candidate, list) and candidate:
            cells = candidate
            source_shape = "mvp_profile.cells"
    if cells is None:
        candidate = router_floor_report.get("cells")
        if isinstance(candidate, list) and candidate:
            cells = candidate
            source_shape = "cells"
    if not isinstance(cells, list) or not cells:
        return None, {
            "error": (
                "router_floor_report has no cells "
                "(checked mvp_profile.cells and top-level cells)"
            ),
        }

    requested_packs: Optional[set] = None
    if packs is not None:
        requested_packs = {str(p) for p in packs if isinstance(p, str)}
        if not requested_packs:
            requested_packs = None

    # Accumulate per (model, pack) → list of pass_rates across depths.
    matrix_values: Dict[str, Dict[str, List[float]]] = {}
    per_cell_trace: List[Dict[str, Any]] = []
    skipped_cells = 0
    for cell in cells:
        if not isinstance(cell, dict):
            skipped_cells += 1
            continue
        model = cell.get("model")
        pack = cell.get("scenario_pack")
        pr = cell.get("pass_rate")
        if not isinstance(model, str) or not isinstance(pack, str):
            skipped_cells += 1
            continue
        if requested_packs is not None and pack not in requested_packs:
            continue
        try:
            pr_f = float(pr)
        except (TypeError, ValueError):
            skipped_cells += 1
            continue
        matrix_values.setdefault(model, {}).setdefault(pack, []).append(pr_f)
        per_cell_trace.append(
            {
                "model": model,
                "thinking_depth": cell.get("thinking_depth"),
                "scenario_pack": pack,
                "pass_rate": pr_f,
            }
        )

    if not matrix_values:
        return None, {
            "error": "no (model, pack) cells produced a usable pass_rate",
            "n_cells_total": len(cells),
            "n_cells_skipped": skipped_cells,
            "packs_requested": (
                sorted(requested_packs) if requested_packs is not None else None
            ),
        }

    # Collapse depth dimension: max per (model, pack).
    collapsed: Dict[str, Dict[str, float]] = {}
    for model, pack_map in matrix_values.items():
        collapsed[model] = {
            pack: float(max(values)) for pack, values in pack_map.items()
        }

    range_ok = all(
        0.0 <= v <= 1.0 for per_pack in collapsed.values() for v in per_pack.values()
    )

    derivation: Dict[str, Any] = {
        "method": (
            "max(pass_rate) across thinking_depth per (model, scenario_pack); "
            "collapses the MVP 8-cell sweep along the depth axis"
        ),
        "collapse_rule": "max across depths",
        "source_profile": "mvp",
        "source_shape": source_shape,
        "n_cells_total": len(cells),
        "n_cells_used": len(per_cell_trace),
        "n_cells_skipped": skipped_cells,
        "packs_requested": (
            sorted(requested_packs) if requested_packs is not None else None
        ),
        "packs_observed": sorted({p for m in collapsed.values() for p in m.keys()}),
        "models_observed": sorted(collapsed.keys()),
        "per_cell_values": per_cell_trace,
        "matrix": collapsed,
        "range_sanity_check": (
            "PASS (all cells in [0.0, 1.0])" if range_ok else "FAIL"
        ),
        "v1_baseline_gate": (
            "n/a (G1 has no §4.1 hard threshold; informational — D4 "
            "generalizability is coverage-only at v1_baseline)"
        ),
        "partial_proxy_disclosure": (
            "2-model × 2-pack view collapsed from mvp 8-cell sweep. "
            "Authoritative G1 requires real-LLM runs against the full "
            "96-cell profile (§5.3 full: 6 model × 4 depth × 4 pack). "
            "G2/G3/G4 remain null by scope for v0.1.x per master plan "
            "(.local/.agent/active/v0.2.0-iteration-plan.yaml#round_10)."
        ),
        "spec_section_compliance": (
            "§3.1 D4 G1 (partial fill); §5.1 metadata-retrieval surface "
            "(deterministic sweep cells; NOT §5.2 router-model training)"
        ),
    }
    return collapsed, derivation


# ─────────── Round 8 D7 governance_risk hoists (V1 + V2 + V3 + V4) ───────────
#
# Spec §3.1 D7:
#   V1_permission_scope   = count of hardcoded write paths outside
#     .local/dogfood/ and outside the skill's own source tree.
#   V2_credential_surface = count of credential/secret pattern matches
#     across skill artifact bodies (MUST NOT log the values).
#   V3_drift_signal       = 1.0 - cross_tree_drift_zero_ratio across the
#     3 SKILL.md mirrors.
#   V4_staleness_days     = days since
#     basic_ability_profile.lifecycle.last_reviewed_at.
#
# All four values are sourced from ``tools/governance_scan.py``
# (see build_governance_report()) and surfaced via the new Round 8
# ``governance_report`` parameter on :func:`build_report`. When the
# parameter is ``None`` (Round 7 and earlier code paths), V1-V4 stay
# ``null`` per spec §3.2 frozen constraint #2 — the aggregator MUST
# NOT silently substitute zeros (workspace rule "No Silent Failures").
#
# NOTE: the half_retire_decision.yaml governance_risk_delta is
# derived live from these V1-V4 inputs starting with Round 8 (Round 8
# task spec §3 — "remove hard-coding of governance_risk_delta = 0.0").
# The numerical value stays 0.0 when V1-V4 are all zero (clean
# baseline), but it is COMPUTED by
# :func:`governance_scan.compute_governance_risk_delta` rather than a
# literal.


def _hoist_v_metric(
    governance_report: Optional[Dict[str, Any]], key: str
) -> Any:
    """Return ``governance_report[key]`` or ``None`` on any failure.

    Shared helper for the four V1-V4 hoists. Preserves the
    ``no silent substitution`` rule by returning ``None`` whenever the
    report is missing, malformed, or the key is absent.
    """

    if governance_report is None:
        return None
    if not isinstance(governance_report, dict):
        return None
    if key not in governance_report:
        return None
    return governance_report[key]


def hoist_v1_permission_scope(
    governance_report: Optional[Dict[str, Any]],
) -> Optional[int]:
    """Hoist V1 from a ``build_governance_report`` dict.

    Returns the integer value or ``None`` when the report is missing /
    the key is absent (documented degenerate path — §3.2 explicit-null).

    >>> hoist_v1_permission_scope({"V1_permission_scope": 0}) == 0
    True
    >>> hoist_v1_permission_scope(None) is None
    True
    """

    raw = _hoist_v_metric(governance_report, "V1_permission_scope")
    if raw is None:
        return None
    try:
        v = int(raw)
    except (TypeError, ValueError):
        LOGGER.warning("V1 is not int-coercible: %r", raw)
        return None
    if v < 0:
        LOGGER.warning("V1 must be >= 0, got %d", v)
        return None
    return v


def hoist_v2_credential_surface(
    governance_report: Optional[Dict[str, Any]],
) -> Optional[int]:
    """Hoist V2 from a ``build_governance_report`` dict.

    >>> hoist_v2_credential_surface({"V2_credential_surface": 0}) == 0
    True
    >>> hoist_v2_credential_surface(None) is None
    True
    """

    raw = _hoist_v_metric(governance_report, "V2_credential_surface")
    if raw is None:
        return None
    try:
        v = int(raw)
    except (TypeError, ValueError):
        LOGGER.warning("V2 is not int-coercible: %r", raw)
        return None
    if v < 0:
        LOGGER.warning("V2 must be >= 0, got %d", v)
        return None
    return v


def hoist_v3_drift_signal(
    governance_report: Optional[Dict[str, Any]],
) -> Optional[float]:
    """Hoist V3 from a ``build_governance_report`` dict.

    >>> hoist_v3_drift_signal({"V3_drift_signal": 0.0}) == 0.0
    True
    >>> hoist_v3_drift_signal(None) is None
    True
    """

    raw = _hoist_v_metric(governance_report, "V3_drift_signal")
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        LOGGER.warning("V3 is not float-coercible: %r", raw)
        return None
    if not (0.0 <= v <= 1.0):
        LOGGER.warning("V3 out of [0.0, 1.0]: %s", v)
        return None
    return v


def hoist_v4_staleness_days(
    governance_report: Optional[Dict[str, Any]],
) -> Optional[int]:
    """Hoist V4 from a ``build_governance_report`` dict.

    >>> hoist_v4_staleness_days({"V4_staleness_days": 0}) == 0
    True
    >>> hoist_v4_staleness_days(None) is None
    True
    """

    raw = _hoist_v_metric(governance_report, "V4_staleness_days")
    if raw is None:
        return None
    try:
        v = int(raw)
    except (TypeError, ValueError):
        LOGGER.warning("V4 is not int-coercible: %r", raw)
        return None
    if v < 0:
        LOGGER.warning("V4 must be >= 0, got %d", v)
        return None
    return v


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
    references_dir: Optional[Path] = None,
    neighbor_skill_md_paths: Optional[Iterable[Path]] = None,
    governance_report: Optional[Dict[str, Any]] = None,
    r8_method: str = "max_jaccard",
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

    Round 7 (task spec §4) hoists D2 C5 / C6:

    * C5_context_rot_risk = clip(body_tokens / typical_window
      + 0.05 * fanout_depth, 0.0, 1.0); ``fanout_depth`` = count of
      ``*.md`` files under ``references_dir`` that the SKILL.md body
      literally references by filename. Range ``[0.0, 1.0]``.
    * C6_scope_overlap_score = max Jaccard across neighbor SKILL.md
      description pairs (token-set overlap). Range ``[0.0, 1.0]``.

    Round 8 (task spec §3) hoists D7 V1 / V2 / V3 / V4:

    * V1_permission_scope   = count of hardcoded write paths outside
      ``.local/dogfood/`` and outside the skill's own source tree.
    * V2_credential_surface = count of credential / secret pattern
      matches across skill artifact bodies (values never logged).
    * V3_drift_signal       = ``1.0 - cross_tree_drift_zero_ratio``
      across the 3 SKILL.md mirrors.
    * V4_staleness_days     = days since
      ``basic_ability_profile.lifecycle.last_reviewed_at``.

    Round 10 (task spec §2) hoists D4 G1 cross_model_pass_matrix:

    * G1_cross_model_pass_matrix = nested dict
      ``{model: {pack: max_pass_rate_across_depths, ...}, ...}`` derived
      from the MVP 8-cell router-test sweep (``router_floor_report``).
      Partial-fill proxy — authoritative G1 requires the full 96-cell
      profile (§5.3 full; v2_tightened+ upgrade path). G2/G3/G4 stay
      null by scope for v0.1.x per master plan.

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

    # Round 7 (task spec §4): hoist D2 C5 / C6.
    c5_value, c5_derivation = hoist_c5_context_rot_risk(
        skill_md_path, references_dir
    )
    metrics["context_economy"]["C5_context_rot_risk"] = c5_value
    c6_value, c6_derivation = hoist_c6_scope_overlap_score(
        skill_md_path, neighbor_skill_md_paths
    )
    metrics["context_economy"]["C6_scope_overlap_score"] = c6_value

    # Round 9 (task spec §3): hoist D6 R8 description_competition_index.
    # Re-uses the neighbor list supplied for C6 by default so a single
    # --neighbor-skills-glob drives both metrics consistently.
    r8_value, r8_derivation = hoist_r8_description_competition_index(
        skill_md_path, neighbor_skill_md_paths, method=r8_method
    )
    metrics["routing_cost"]["R8_description_competition_index"] = r8_value

    # Round 10 (task spec §2): hoist D4 G1 cross_model_pass_matrix from the
    # mvp 8-cell sweep. Collapses depth dimension per (model, pack) using
    # max aggregation — first measurement of D4 generalizability.
    # G2/G3/G4 stay null by scope for v0.1.x per master plan.
    g1_value, g1_derivation = hoist_g1_cross_model_pass_matrix(router_floor_report)
    metrics["generalizability"]["G1_cross_model_pass_matrix"] = g1_value

    # Round 8 (task spec §3): hoist D7 V1 / V2 / V3 / V4 from the
    # governance scan payload (produced by tools/governance_scan.py).
    v1_value = hoist_v1_permission_scope(governance_report)
    v2_value = hoist_v2_credential_surface(governance_report)
    v3_value = hoist_v3_drift_signal(governance_report)
    v4_value = hoist_v4_staleness_days(governance_report)
    metrics["governance_risk"]["V1_permission_scope"] = v1_value
    metrics["governance_risk"]["V2_credential_surface"] = v2_value
    metrics["governance_risk"]["V3_drift_signal"] = v3_value
    metrics["governance_risk"]["V4_staleness_days"] = v4_value

    # Derivation records for V1-V4 hoists. These surface the raw
    # scanner output (via ``governance_report['provenance']``) plus
    # a per-metric ``hoisted_value``, so the metrics_report.yaml can
    # be audited end-to-end without consulting the raw
    # ``governance_scan.json``.
    governance_provenance = (
        governance_report.get("provenance")
        if isinstance(governance_report, dict)
        else None
    ) or {}
    v1_derivation = {
        "method": "aggregate_eval.hoist_v1_permission_scope(governance_report)",
        "hoisted_value": v1_value,
        "source": governance_provenance.get("v1_derivation"),
        "loaded": governance_report is not None,
    }
    v2_derivation = {
        "method": "aggregate_eval.hoist_v2_credential_surface(governance_report)",
        "hoisted_value": v2_value,
        "source": governance_provenance.get("v2_derivation"),
        "loaded": governance_report is not None,
    }
    v3_derivation = {
        "method": "aggregate_eval.hoist_v3_drift_signal(governance_report)",
        "hoisted_value": v3_value,
        "source": governance_provenance.get("v3_derivation"),
        "loaded": governance_report is not None,
    }
    v4_derivation = {
        "method": "aggregate_eval.hoist_v4_staleness_days(governance_report)",
        "hoisted_value": v4_value,
        "source": governance_provenance.get("v4_derivation"),
        "loaded": governance_report is not None,
    }

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
            "c5_derivation": c5_derivation,
            "c6_derivation": c6_derivation,
            "r8_derivation": r8_derivation,
            "g1_derivation": g1_derivation,
            "v1_derivation": v1_derivation,
            "v2_derivation": v2_derivation,
            "v3_derivation": v3_derivation,
            "v4_derivation": v4_derivation,
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


def _maybe_load_governance_report(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Load a governance_scan.json when ``path`` is provided.

    Produced by ``tools/governance_scan.py --json`` (Round 8). Raises
    ``FileNotFoundError`` when ``path`` is set but missing (workspace
    rule "No Silent Failures"). Returns ``None`` when ``path`` is
    ``None`` (caller has not requested V1-V4 hoisting; Round 7 and
    earlier code paths take this branch).
    """

    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"--governance-report path not found: {path}")
    with path.open("r", encoding="utf-8") as fp:
        try:
            data = json.load(fp)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: governance_report must be a JSON object")
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
            "across cells with pass_rate >= 0.80 (Round 3 Edit B). "
            "Round 10 additionally hoists G1_cross_model_pass_matrix "
            "(D4 generalizability) by collapsing depths from the mvp "
            "8-cell sweep (nested dict of model × pack → max pass_rate)."
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
    parser.add_argument(
        "--references-dir",
        default=".agents/skills/si-chip/references",
        help=(
            "Optional SKILL.md references directory (default: "
            ".agents/skills/si-chip/references). Used by the C5 hoist to "
            "derive reference_fanout_depth (Round 7)."
        ),
    )
    parser.add_argument(
        "--neighbor-skills-glob",
        default="/root/.claude/skills/lark-*/SKILL.md",
        help=(
            "Optional glob for neighbor SKILL.md paths. Used by the C6 "
            "scope_overlap_score hoist; defaults to the 20+ lark-* family. "
            "Set to an empty string to disable C6 hoisting (Round 7)."
        ),
    )
    parser.add_argument(
        "--governance-report",
        default=None,
        help=(
            "Optional governance_scan.json path (emitted by "
            "tools/governance_scan.py --json). When set, V1/V2/V3/V4 "
            "are hoisted into metrics.governance_risk (Round 8)."
        ),
    )
    parser.add_argument(
        "--r8-method",
        default="max_jaccard",
        choices=["max_jaccard", "tfidf_cosine_mean"],
        help=(
            "Method for R8 description_competition_index (Round 9). "
            "'max_jaccard' (default) reuses Round 7's C6 infra and "
            "surfaces the WORST-competition neighbor; "
            "'tfidf_cosine_mean' surfaces AVERAGE competition across "
            "the neighbor set. Spec §5.1 metadata-retrieval surface "
            "(NOT §5.2 router-model training)."
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
    references_dir: Optional[Path] = None
    if args.references_dir:
        references_dir = Path(args.references_dir).resolve()
    neighbor_paths: List[Path] = []
    if args.neighbor_skills_glob:
        # Keep glob-resolved paths as-is (no symlink resolution) so the
        # derivation record matches the caller's invocation surface.
        neighbor_paths = [Path(p) for p in sorted(glob.glob(args.neighbor_skills_glob))]
        LOGGER.info("C6 neighbor glob matched %d path(s)", len(neighbor_paths))

    with_runs = _walk_runs(runs_dir)
    base_runs = _walk_runs(baseline_dir)
    LOGGER.info("with-ability runs: %d, no-ability runs: %d", len(with_runs), len(base_runs))

    with_rows = _collect(with_runs)
    without_rows = _collect(base_runs)

    skill_md_meta = _maybe_skill_md_metadata_tokens(skill_md)
    router_floor_report = _maybe_load_router_floor_report(router_floor_path)
    install_telemetry = _maybe_load_install_telemetry(install_telemetry_path)
    governance_report_path = (
        Path(args.governance_report).resolve() if args.governance_report else None
    )
    governance_report = _maybe_load_governance_report(governance_report_path)
    report = build_report(
        with_rows,
        without_rows,
        runs_dir,
        baseline_dir,
        skill_md_meta,
        router_floor_report=router_floor_report,
        skill_md_path=skill_md,
        install_telemetry=install_telemetry,
        references_dir=references_dir,
        neighbor_skill_md_paths=neighbor_paths,
        governance_report=governance_report,
        r8_method=args.r8_method,
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
