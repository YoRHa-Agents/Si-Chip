#!/usr/bin/env python3
"""Generic per-ability evaluation harness for Si-Chip spec v0.3.0-rc1.

Replaces ability-specific 768-line harnesses (e.g.
``eval_chip_usage_helper.py``) with a pluggable entry point that any new
BasicAbility can use by supplying only its vocabulary yaml + eval_pack +
core_goal_test_pack + test runner command. Per R11 §7 design brief the
saving is ~600 LoC per new ability.

The harness wires four measurement surfaces together:

1. **Trigger eval (D6 R1/R2/R3/R4)** — delegates to
   ``tools/cjk_trigger_eval.py::evaluate_pack``.
2. **Token / context economy (D2 C1/C2/C4)** — subprocesses
   ``.agents/skills/si-chip/scripts/count_tokens.py`` (the canonical
   C1/C2 counter; spec §3.2 frozen constraint #3).
3. **Functional tests + wall-clock (D1 T1/T3 + D3 L1/L2)** — runs the
   ability-specific test command N times under ``--test-runner-cwd``.
4. **Core-goal test pack (C0, v0.3.0 §14 top-level invariant)** —
   executes each case via per-case command (if the pack supplies one)
   or the global test runner. Emits ``core_goal_check`` block
   mirroring ``iteration_delta_report.template.yaml``.

R6 7×37 placeholder discipline (spec §3.2 frozen #2): every one of the
37 sub-metric keys is emitted; unmeasured ones are ``null``. The
``R6_KEYS`` constant enumerates them verbatim from spec §3.1.

CLI::

    python tools/eval_skill.py \\
        --ability <id> \\
        --skill-md <path/to/SKILL.md> \\
        --vocabulary <path/to/vocabulary.yaml> \\
        --eval-pack <path/to/eval_pack.yaml> \\
        --core-goal-test-pack <path/to/core_goal_test_pack.yaml> \\
        --test-runner-cmd "<shell cmd>" \\
        --test-runner-cwd <path> \\
        --runs 3 \\
        --out <path/to/metrics_report.yaml> \\
        [--round-kind code_change|measurement_only|ship_prep|maintenance] \\
        [--baseline-runner-cmd "<shell cmd>"]

Exit code is ``0`` on successful measurement (even if thresholds would
fail; ``tools/spec_validator.py`` is the gate). A ``C0 < 1.0`` fills
``core_goal_check.rollback_required = true`` per §15.3 universal
invariant but does NOT change the exit code — the rollback action is
the operator's to take.

Workspace-rule notes
--------------------
* "No Silent Failures": missing paths / unknown round_kind raise
  explicitly. Token-counter / test-runner subprocess failures propagate
  via return codes captured in the metrics_report.
* "Mandatory Verification": sibling test ``tools/test_eval_skill.py``
  covers R6_KEYS 37-count + per-dim counts, ROUND_KINDS size,
  core_goal_test_pack runner happy-path and failure path, and the
  metrics_report R6 placeholder invariant.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

# Ensure sibling tools import (tools/ is not a package; inject repo root).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.cjk_trigger_eval import (  # noqa: E402
    Vocabulary,
    evaluate_pack as cjk_evaluate_pack,
)
from tools.round_kind import (  # noqa: E402
    REQUIRED_C0_VALUE,
    ROUND_KINDS,
    validate_round_kind,
)

LOGGER = logging.getLogger("si_chip.eval_skill")

# 0.1.0 — initial generic per-ability harness (Stage 4 Wave 2a).
# 0.2.0 — Stage 4 Wave 1b (v0.4.0-rc1): additive public helpers for
#         §18.1 token-tier decomposition, §18.2 MCP pretty-text detection,
#         §18.6 canvas-template default-data anti-pattern detection, and
#         §21.4 health-smoke-check runner dispatch.
SCRIPT_VERSION = "0.2.0"

# --- R6 7×37 constant ---------------------------------------------------

R6_KEYS: Dict[str, List[str]] = {
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

DEFAULT_COUNT_TOKENS_SCRIPT = (
    REPO_ROOT / ".agents" / "skills" / "si-chip" / "scripts" / "count_tokens.py"
)


# --- Configuration dataclass -------------------------------------------

@dataclass
class EvalSkillConfig:
    """Holds every CLI-supplied path / command needed to run one round."""

    ability: str
    skill_md: Path
    vocabulary: Path
    eval_pack: Path
    core_goal_test_pack: Path
    test_runner_cmd: str
    test_runner_cwd: Path
    runs: int = 3
    out: Optional[Path] = None
    round_kind: Optional[str] = None
    baseline_runner_cmd: Optional[str] = None
    count_tokens_script: Path = field(
        default_factory=lambda: DEFAULT_COUNT_TOKENS_SCRIPT
    )

    def validate(self) -> None:
        """Fail fast on missing paths / invalid round_kind.

        Raises ``FileNotFoundError`` / ``ValueError`` per workspace
        rule "No Silent Failures".
        """

        required_files: Dict[str, Path] = {
            "skill_md": self.skill_md,
            "vocabulary": self.vocabulary,
            "eval_pack": self.eval_pack,
            "core_goal_test_pack": self.core_goal_test_pack,
        }
        for name, path in required_files.items():
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"{name} path does not exist: {path}"
                )
        if not Path(self.test_runner_cwd).is_dir():
            raise NotADirectoryError(
                f"test_runner_cwd is not a directory: {self.test_runner_cwd}"
            )
        if self.round_kind is not None and not validate_round_kind(
            self.round_kind
        ):
            raise ValueError(
                f"unknown round_kind {self.round_kind!r}; expected one of "
                f"{sorted(ROUND_KINDS)}"
            )
        if self.runs <= 0:
            raise ValueError(f"runs must be >= 1, got {self.runs}")


# --- R6 placeholder construction --------------------------------------

def build_r6_placeholder() -> Dict[str, Dict[str, Any]]:
    """Return a dict with all 37 keys set to ``None`` (placeholders).

    Consumers fill in measured values; unmeasured keys remain ``None``
    per spec §3.2 frozen constraint #2.
    """

    return {
        dim: {key: None for key in keys}
        for dim, keys in R6_KEYS.items()
    }


# --- Token / context ---------------------------------------------------

def _count_tokens_via_subprocess(
    skill_md: Path, count_tokens_script: Path
) -> Dict[str, Any]:
    """Run ``count_tokens.py --file <skill> --both --json`` and parse."""

    if not count_tokens_script.exists():
        raise FileNotFoundError(
            f"count_tokens.py script not found: {count_tokens_script}"
        )
    result = subprocess.run(
        [
            sys.executable,
            str(count_tokens_script),
            "--file",
            str(skill_md),
            "--both",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        raise RuntimeError(
            f"count_tokens.py produced no stdout for {skill_md}; "
            f"stderr: {result.stderr}"
        )
    return json.loads(result.stdout)


# --- Functional tests --------------------------------------------------

def _run_test_command_once(
    cmd: str, cwd: Path, timeout_s: int = 300
) -> Dict[str, Any]:
    """Execute one invocation of the ability's test runner.

    Returns a dict with ``exit_code``, ``duration_s``, ``passed``,
    ``stdout_tail``, ``stderr_tail``. ``passed`` is ``exit_code == 0``.
    """

    tokens = shlex.split(cmd)
    if not tokens:
        raise ValueError("test_runner_cmd expanded to empty token list")
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            tokens,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        t1 = time.perf_counter()
        LOGGER.warning("test_runner_cmd timed out: %s", exc)
        return {
            "exit_code": -1,
            "duration_s": round(t1 - t0, 4),
            "passed": False,
            "stdout_tail": "",
            "stderr_tail": f"TIMEOUT after {timeout_s}s",
        }
    t1 = time.perf_counter()
    return {
        "exit_code": result.returncode,
        "duration_s": round(t1 - t0, 4),
        "passed": result.returncode == 0,
        "stdout_tail": (result.stdout or "")[-500:],
        "stderr_tail": (result.stderr or "")[-500:],
    }


def _percentile(values: Sequence[float], pct: float) -> float:
    """Deterministic percentile for short lists (used for L1/L2)."""

    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = min(int(pct * len(ordered)), len(ordered) - 1)
    return ordered[idx]


def run_functional_tests(
    cmd: str, cwd: Path, runs: int
) -> Dict[str, Any]:
    """Run the test command ``runs`` times; return T1 / L1 / L2 / traces."""

    traces: List[Dict[str, Any]] = []
    for i in range(runs):
        trace = _run_test_command_once(cmd, cwd)
        trace["run_index"] = i
        traces.append(trace)
    passed = sum(1 for t in traces if t["passed"])
    durations = [t["duration_s"] for t in traces]
    return {
        "T1_pass_rate": round(passed / runs, 4) if runs > 0 else 0.0,
        "L1_wall_clock_p50": round(_percentile(durations, 0.5), 4),
        "L2_wall_clock_p95": round(_percentile(durations, 0.95), 4),
        "runs": runs,
        "passed": passed,
        "per_run": traces,
    }


# --- Core-goal test pack ----------------------------------------------

def run_core_goal_test_pack(
    pack_path: Path,
    default_runner_cmd: str,
    cwd: Path,
    timeout_s: int = 300,
) -> Dict[str, Any]:
    """Execute every case in the pack; return C0 metrics.

    Each case may define its own ``command`` (or ``case_runner_cmd``)
    field; otherwise ``default_runner_cmd`` is used. The command is
    invoked with ``SI_CHIP_CASE_ID`` / ``SI_CHIP_CASE_PROMPT`` in env
    so runners can route per-case without parsing CLI args.

    A case passes when the runner exits 0. The overall C0 pass rate is
    ``cases_passed / cases_total``; spec §14.3 locks the target at 1.0.
    """

    pack_path = Path(pack_path)
    if not pack_path.exists():
        raise FileNotFoundError(f"core_goal_test_pack not found: {pack_path}")
    with pack_path.open("r", encoding="utf-8") as fh:
        pack = yaml.safe_load(fh) or {}
    cases = pack.get("cases") or []
    if not isinstance(cases, list):
        raise ValueError(
            f"core_goal_test_pack cases must be a list, got {type(cases).__name__}"
        )
    if not cases:
        LOGGER.warning(
            "core_goal_test_pack has zero cases; C0 pass_rate will be 0.0"
        )

    per_case: List[Dict[str, Any]] = []
    passed = 0
    for idx, case in enumerate(cases):
        case_id = str(case.get("id") or f"case_{idx}")
        prompt = str(case.get("prompt") or "")
        runner_cmd = (
            case.get("command")
            or case.get("case_runner_cmd")
            or default_runner_cmd
        )
        if not runner_cmd:
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "exit_code": None,
                    "error": "no runner command (case or default)",
                }
            )
            continue
        try:
            tokens = shlex.split(runner_cmd)
        except ValueError as exc:
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "exit_code": None,
                    "error": f"shlex.split failed: {exc}",
                }
            )
            continue
        env_updates = {
            "SI_CHIP_CASE_ID": case_id,
            "SI_CHIP_CASE_PROMPT": prompt,
        }
        import os

        env = os.environ.copy()
        env.update(env_updates)
        try:
            result = subprocess.run(
                tokens,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                check=False,
            )
            case_passed = result.returncode == 0
            if case_passed:
                passed += 1
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": case_passed,
                    "exit_code": result.returncode,
                    "stdout_tail": (result.stdout or "")[-300:],
                    "stderr_tail": (result.stderr or "")[-300:],
                }
            )
        except subprocess.TimeoutExpired as exc:
            LOGGER.warning(
                "core_goal case %s timed out after %ss", case_id, timeout_s
            )
            per_case.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "exit_code": -1,
                    "error": f"timeout after {timeout_s}s: {exc}",
                }
            )

    total = len(cases)
    pass_rate = round(passed / total, 4) if total > 0 else 0.0
    return {
        "pass_rate": pass_rate,
        "cases_passed": passed,
        "cases_total": total,
        "per_case": per_case,
    }


def build_core_goal_check(
    c0_pass_rate: float,
    cases_passed: int,
    cases_total: int,
    prior_c0_pass_rate: Optional[float],
    round_kind: Optional[str],
    failed_case_ids: Sequence[str],
) -> Dict[str, Any]:
    """Construct the ``core_goal_check`` block per §14.3 / §15.3.

    Per spec §15.3 the C0 MUST = 1.0 invariant is **universal** across
    all four round_kinds. Any ``c0_pass_rate < REQUIRED_C0_VALUE`` sets
    ``rollback_required = True`` regardless of round_kind (cross-check
    R11 §4 + spec §15.3). A drop relative to ``prior_c0_pass_rate``
    sets ``regression_detected = True`` independently (it's possible to
    stay at 1.0 if prior was already 1.0 but still fail the
    monotonicity axis if prior was somehow >1 — guarded here for
    completeness).
    """

    regression_detected = (
        prior_c0_pass_rate is not None
        and c0_pass_rate < prior_c0_pass_rate
    )
    below_target = c0_pass_rate < REQUIRED_C0_VALUE
    rollback_required = bool(below_target or regression_detected)
    verdict_pass = (
        c0_pass_rate >= REQUIRED_C0_VALUE and not regression_detected
    )
    return {
        "C0_pass_rate_current": c0_pass_rate,
        "C0_pass_rate_prior": prior_c0_pass_rate,
        "cases_passed": cases_passed,
        "cases_total": cases_total,
        "failed_case_ids": list(failed_case_ids),
        "regression_detected": regression_detected,
        "rollback_required": rollback_required,
        "round_kind": round_kind,
        "required_c0_value": REQUIRED_C0_VALUE,
        "verdict": {"core_goal_pass": verdict_pass},
        "spec_section": "v0.3.0-rc1 §14.3 / §15.3",
    }


# --- v0.4.0 Wave 1b helpers (§18.1 / §18.2 / §18.6 / §21.4) -----------

# §18.1 char-heuristic ratio (industrial default; tiktoken is preferred
# when available but we keep a deterministic fallback for sandbox CI).
_CHAR_HEURISTIC_RATIO = 3.8


def _estimate_tokens_char_heuristic(text: str) -> int:
    """Return floor(len(text) / 3.8) — the §23.2 char_heuristic estimator.

    The canonical char_heuristic ratio is 3.8 chars/token (industrial
    default per method_taxonomy.template.yaml `confidence_band`). For
    bilingual / CJK-heavy bodies the ratio has ±20% band; callers that
    care emit ``_ci_low`` / ``_ci_high`` separately.
    """

    if not text:
        return 0
    return int(len(text) // _CHAR_HEURISTIC_RATIO)


def _extract_frontmatter_and_body(md_text: str) -> tuple:
    """Split ``---\nfrontmatter\n---\nbody`` into two strings.

    Returns ``(frontmatter, body)``. When no frontmatter block is
    present, returns ``("", md_text)``. Follows the common Markdown
    frontmatter convention (leading ``---`` line + closing ``---`` on
    its own line).
    """

    if not md_text.startswith("---"):
        return "", md_text
    rest = md_text[3:]
    # Find the next ``---`` line (with possible leading newline).
    end_match = re.search(r"^---\s*$", rest, re.MULTILINE)
    if end_match is None:
        return "", md_text
    frontmatter = rest[: end_match.start()]
    body = rest[end_match.end():]
    return frontmatter.strip("\n"), body.lstrip("\n")


def decompose_token_tiers(
    skill_md_path: Path,
    rule_path: Optional[Path] = None,
    lazy_manifest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """§18.1 token-tier decomposition — return EAGER/ON-CALL/LAZY counts.

    Returns a dict with three tier axes (matching the §18.1 schema):

      * ``C7_eager_per_session`` — tokens always paid per session
        (rule frontmatter + rule body; Cursor/Claude always-apply
        rules are loaded every conversation).
      * ``C8_oncall_per_trigger`` — tokens paid once per skill trigger
        (SKILL.md body + any references cited in the body).
      * ``C9_lazy_avg_per_load`` — avg tokens per LAZY load (files
        listed in ``.lazy-manifest`` that aren't imported by the
        SKILL.md body).

    Token counts use the §23.2 char_heuristic estimator
    (``chars / 3.8``). The method tag is ``char_heuristic`` — callers
    that want tiktoken precision can swap ``_estimate_tokens_char_heuristic``
    with a tiktoken-backed implementation without changing the public
    API.

    Parameters
    ----------
    skill_md_path:
        Path to the ability's ``SKILL.md``. Used to compute C8.
    rule_path:
        Optional path to the ability's bridge rule (e.g.
        ``.cursor/rules/<ability>-bridge.mdc``). When provided, used
        to compute C7 (EAGER = rule frontmatter + rule body).
    lazy_manifest_path:
        Optional path to the ability's ``.lazy-manifest``. When
        provided, sums the on-disk bytes of declared files and
        averages to compute C9. When absent, C9 falls back to scanning
        a sibling ``references/`` directory for ``.md`` files NOT
        cited in the SKILL.md body.

    Returns
    -------
    dict
        ``{C7_eager_per_session, C7_eager_per_session_method,
           C8_oncall_per_trigger, C8_oncall_per_trigger_method,
           C9_lazy_avg_per_load, C9_lazy_avg_per_load_method,
           measured_with_sessions, measured_with_triggers,
           measured_with_lazy_loads}`` per spec §18.1.1.

    Raises
    ------
    FileNotFoundError
        When ``skill_md_path`` does not exist (workspace rule "No
        Silent Failures").
    """

    skill_md_path = Path(skill_md_path)
    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_md_path}")

    skill_text = skill_md_path.read_text(encoding="utf-8")

    # C7 — EAGER: rule frontmatter + rule body (when rule_path given).
    eager_tokens = 0
    if rule_path is not None and Path(rule_path).exists():
        rule_text = Path(rule_path).read_text(encoding="utf-8")
        eager_tokens = _estimate_tokens_char_heuristic(rule_text)

    # C8 — ON-CALL: SKILL.md body (the body minus any frontmatter).
    _, skill_body = _extract_frontmatter_and_body(skill_text)
    oncall_tokens = _estimate_tokens_char_heuristic(skill_body)

    # C9 — LAZY: lazy_manifest files OR references/**/*.md NOT cited in body.
    lazy_tokens = 0
    lazy_loads_sampled = 0
    if lazy_manifest_path is not None and Path(lazy_manifest_path).exists():
        try:
            manifest = yaml.safe_load(
                Path(lazy_manifest_path).read_text(encoding="utf-8")
            ) or {}
        except yaml.YAMLError as exc:
            raise RuntimeError(
                f"failed to parse .lazy-manifest: {exc}"
            ) from exc
        lazy_files = manifest.get("lazy_paths") or manifest.get("lazy_files") or []
        ability_root = Path(lazy_manifest_path).parent
        sum_tokens = 0
        for entry in lazy_files:
            if not isinstance(entry, dict):
                continue
            path_str = entry.get("path")
            if not isinstance(path_str, str):
                continue
            candidate = ability_root / path_str
            if candidate.exists() and candidate.is_file():
                sum_tokens += _estimate_tokens_char_heuristic(
                    candidate.read_text(encoding="utf-8", errors="replace")
                )
                lazy_loads_sampled += 1
            else:
                avg = entry.get("avg_tokens")
                if isinstance(avg, int):
                    sum_tokens += avg
                    lazy_loads_sampled += 1
        if lazy_loads_sampled > 0:
            lazy_tokens = sum_tokens // lazy_loads_sampled
    else:
        # Fallback: references/**/*.md that aren't cited in body.
        ability_root = skill_md_path.parent
        references_dir = ability_root / "references"
        if references_dir.exists() and references_dir.is_dir():
            sum_tokens = 0
            for ref in references_dir.rglob("*.md"):
                if not ref.is_file():
                    continue
                rel = str(ref.relative_to(ability_root))
                # Simple heuristic: if the SKILL body mentions the
                # relative path, assume it's loaded on trigger
                # (ON-CALL), not LAZY.
                if rel in skill_body:
                    continue
                sum_tokens += _estimate_tokens_char_heuristic(
                    ref.read_text(encoding="utf-8", errors="replace")
                )
                lazy_loads_sampled += 1
            if lazy_loads_sampled > 0:
                lazy_tokens = sum_tokens // lazy_loads_sampled

    return {
        "C7_eager_per_session": eager_tokens,
        "C7_eager_per_session_method": "char_heuristic",
        "C8_oncall_per_trigger": oncall_tokens,
        "C8_oncall_per_trigger_method": "char_heuristic",
        "C9_lazy_avg_per_load": lazy_tokens,
        "C9_lazy_avg_per_load_method": "char_heuristic",
        "measured_with_sessions": 1 if eager_tokens > 0 else 0,
        "measured_with_triggers": 1 if oncall_tokens > 0 else 0,
        "measured_with_lazy_loads": lazy_loads_sampled,
    }


# §18.2 MCP pretty-text anti-pattern detector.
# Matches ``JSON.stringify(..., null, N)`` where N is a positive integer.
_PRETTY_JSON_RE = re.compile(
    r"JSON\.stringify\s*\([^)]*,\s*null\s*,\s*(?P<indent>\d+)\s*\)",
    re.MULTILINE,
)
# Matches ``structuredContent`` usage (MCP response field that should
# carry machine-parseable data, NOT pretty-printed strings).
_STRUCTURED_CONTENT_RE = re.compile(r"\bstructuredContent\b")


def detect_mcp_pretty_text_issue(mcp_src_dir: Path) -> Dict[str, Any]:
    """§18.2 static check — find MCP handlers mixing pretty JSON + structuredContent.

    Walks ``.ts`` / ``.tsx`` / ``.js`` / ``.jsx`` / ``.py`` files under
    ``mcp_src_dir`` and flags any file that contains BOTH:

      * a ``JSON.stringify(..., null, N)`` call where ``N > 0``
        (pretty-printed output, which costs extra EAGER/ON-CALL tokens
        when returned through the MCP response text channel), AND
      * a ``structuredContent`` reference (MCP's machine-parseable
        response field; when present the text channel is redundant).

    Returns ``{found: [{file, line, code_excerpt}]}``. Empty ``found``
    means no issues. The check is intentionally conservative: files
    without ``structuredContent`` are ignored because pretty JSON in
    pure-text MCP handlers is sometimes intentional (for debugging).

    Parameters
    ----------
    mcp_src_dir:
        Path to an MCP handler source tree. Missing directory returns
        ``{found: []}`` (not an error — some abilities have no MCP
        handlers at all).
    """

    mcp_src_dir = Path(mcp_src_dir)
    found: List[Dict[str, Any]] = []
    if not mcp_src_dir.exists() or not mcp_src_dir.is_dir():
        return {"found": [], "src_dir_exists": False}

    for ext in (".ts", ".tsx", ".js", ".jsx", ".py"):
        for src in mcp_src_dir.rglob(f"*{ext}"):
            if not src.is_file():
                continue
            try:
                text = src.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not _STRUCTURED_CONTENT_RE.search(text):
                continue
            for m in _PRETTY_JSON_RE.finditer(text):
                indent = int(m.group("indent"))
                if indent <= 0:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                if line_end == -1:
                    line_end = len(text)
                excerpt = text[line_start:line_end].strip()
                found.append(
                    {
                        "file": str(src),
                        "line": line_no,
                        "code_excerpt": excerpt[:300],
                        "indent": indent,
                    }
                )

    return {"found": found, "src_dir_exists": True}


# §18.6 canvas template default-data anti-pattern.
# Matches TypeScript-style ``export const DEFAULT_DATA = {...}`` or
# ``export default { ... }`` blocks that carry non-stub values when a
# SKILL recipe is expected to substitute before rendering.
_DEFAULT_DATA_RE = re.compile(
    r"export\s+const\s+(?P<name>[A-Z_][A-Z0-9_]*)\s*[:=]",
    re.MULTILINE,
)
# A "stub" is a minimal placeholder: empty object, null, or a literal
# single-key marker (``{stub: true}``). Anything else = suspect.
_STUB_VALUE_RE = re.compile(
    r"=\s*(?:\{\s*\}|null|undefined|\{\s*stub\s*:\s*true\s*\})",
    re.MULTILINE,
)


def detect_template_default_data_antipattern(
    templates_dir: Path,
) -> Dict[str, Any]:
    """§18.6 static check — canvas templates with non-stub default data.

    Walks ``.ts`` / ``.tsx`` files under ``templates_dir`` and flags
    files declaring ``DEFAULT_DATA`` (or similar ALL_CAPS exported
    constant) with a non-stub initializer. The anti-pattern is: SKILL
    recipes expect to substitute data into the template before
    rendering, so any non-empty default ends up as LAZY-tier payload
    that inflates C9 without adding user-observable value.

    Returns ``{found: [{file, bytes, default_keys}]}``. ``bytes`` is
    the approximate size of the template file on disk (since §18.6
    tier_transitions accounting uses byte movement between tiers).
    ``default_keys`` lists the ALL_CAPS export names that look
    problematic.

    Parameters
    ----------
    templates_dir:
        Directory to scan. Missing → ``{found: []}`` (not an error).
    """

    templates_dir = Path(templates_dir)
    found: List[Dict[str, Any]] = []
    if not templates_dir.exists() or not templates_dir.is_dir():
        return {"found": [], "templates_dir_exists": False}

    for ext in (".ts", ".tsx"):
        for tpl in templates_dir.rglob(f"*{ext}"):
            if not tpl.is_file():
                continue
            try:
                text = tpl.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            suspect_keys: List[str] = []
            for m in _DEFAULT_DATA_RE.finditer(text):
                name = m.group("name")
                # Check if the matching RHS is a stub.
                rhs_start = m.end()
                # Look at the next ~50 chars to see if stub matches.
                rhs_window = text[rhs_start : rhs_start + 200]
                if _STUB_VALUE_RE.search(
                    # Re-anchor the pattern to start of window.
                    "=" + rhs_window
                ):
                    continue
                suspect_keys.append(name)
            if suspect_keys:
                try:
                    size_bytes = tpl.stat().st_size
                except OSError:
                    size_bytes = 0
                found.append(
                    {
                        "file": str(tpl),
                        "bytes": size_bytes,
                        "default_keys": suspect_keys,
                    }
                )

    return {"found": found, "templates_dir_exists": True}


def run_health_smoke_check(
    health_smoke_config: List[Dict[str, Any]],
    timeout_s: int = 30,
    smoke_script: Optional[Path] = None,
) -> Dict[str, Any]:
    """§21.4 packaging-gate helper — invoke ``tools/health_smoke.py``.

    Dispatches the health-smoke CLI for EACH entry in
    ``health_smoke_config``; returns an aggregated results dict. Each
    per-check result carries:

      * ``endpoint`` — the probed URL.
      * ``axis`` — ``read`` / ``write`` / ``auth`` / ``dependency``
        (per §21.3).
      * ``pass`` — boolean; ``True`` iff the probe returned the
        expected status + sentinel predicate passed.
      * ``observed`` — ``{status, sentinel_value, error}`` dict.
      * ``attempt_count`` — retries used (≤ ``max_attempts``).
      * ``duration_s`` — wall clock elapsed for this endpoint.

    Parameters
    ----------
    health_smoke_config:
        List of dicts matching the §21.1 schema: each MUST carry
        ``endpoint``, ``expected_status``, ``max_attempts``,
        ``retry_delay_ms``, ``sentinel_field``,
        ``sentinel_value_predicate``, ``axis``, ``description``.
    timeout_s:
        Per-request timeout in seconds (default 30). Applied per
        probe attempt (NOT per endpoint across retries).
    smoke_script:
        Optional path override to the ``health_smoke.py`` CLI. When
        ``None``, uses ``tools/health_smoke.py`` alongside this module.

    Returns
    -------
    dict
        ``{total, passed, per_check, errors}`` where ``per_check`` is
        the list described above.

    Raises
    ------
    ValueError
        When ``health_smoke_config`` is not a list.

    Notes
    -----
    The §21.4 packaging-gate enforcement contract: all entries MUST
    return ``pass: True`` for the ability to be ship-eligible. Callers
    typically emit ``{total, passed, per_check}`` into
    ``.local/dogfood/<DATE>/<round_id>/raw/health_smoke_results.yaml``.
    """

    if not isinstance(health_smoke_config, list):
        raise ValueError(
            f"health_smoke_config must be a list, got "
            f"{type(health_smoke_config).__name__}"
        )

    if smoke_script is None:
        smoke_script = Path(__file__).resolve().parent / "health_smoke.py"

    per_check: List[Dict[str, Any]] = []
    errors: List[str] = []
    passed_count = 0

    for idx, check in enumerate(health_smoke_config):
        if not isinstance(check, dict):
            errors.append(
                f"entry[{idx}]: not a dict ({type(check).__name__})"
            )
            continue
        endpoint = check.get("endpoint")
        axis = check.get("axis")
        if not isinstance(endpoint, str) or not isinstance(axis, str):
            errors.append(
                f"entry[{idx}]: missing endpoint / axis "
                f"(endpoint={endpoint!r}, axis={axis!r})"
            )
            continue
        # Build CLI invocation: pass the single check JSON via --check.
        try:
            check_json = json.dumps(check)
        except (TypeError, ValueError) as exc:
            errors.append(f"entry[{idx}]: JSON serialize failed: {exc}")
            continue
        t0 = time.perf_counter()
        cmd = [
            sys.executable,
            str(smoke_script),
            "--check",
            check_json,
            "--json",
            "--timeout",
            str(timeout_s),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(timeout_s * 2, 60),
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            duration_s = round(time.perf_counter() - t0, 4)
            errors.append(
                f"entry[{idx}] endpoint={endpoint}: subprocess failed: {exc}"
            )
            per_check.append(
                {
                    "endpoint": endpoint,
                    "axis": axis,
                    "pass": False,
                    "observed": {"error": str(exc)},
                    "attempt_count": 0,
                    "duration_s": duration_s,
                }
            )
            continue
        duration_s = round(time.perf_counter() - t0, 4)
        try:
            payload = json.loads(result.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as exc:
            errors.append(
                f"entry[{idx}] endpoint={endpoint}: unparseable JSON: {exc}; "
                f"stdout={result.stdout[-200:]!r}"
            )
            per_check.append(
                {
                    "endpoint": endpoint,
                    "axis": axis,
                    "pass": False,
                    "observed": {"error": "unparseable_subprocess_output"},
                    "attempt_count": 0,
                    "duration_s": duration_s,
                }
            )
            continue
        pc = payload.get("per_check") or []
        entry = pc[0] if pc else {}
        probe_pass = bool(entry.get("pass"))
        if probe_pass:
            passed_count += 1
        per_check.append(
            {
                "endpoint": endpoint,
                "axis": axis,
                "pass": probe_pass,
                "observed": entry.get("observed") or {},
                "attempt_count": entry.get("attempt_count", 0),
                "duration_s": duration_s,
            }
        )

    return {
        "total": len(health_smoke_config),
        "passed": passed_count,
        "per_check": per_check,
        "errors": errors,
    }


# --- Main evaluation flow ---------------------------------------------

def run_evaluation(
    config: EvalSkillConfig,
    prior_c0_pass_rate: Optional[float] = None,
    skip_functional_tests: bool = False,
) -> Dict[str, Any]:
    """Orchestrate one round of per-ability evaluation.

    Returns a metrics_report dict matching the shape
    ``eval_chip_usage_helper.py`` emits, extended with the new
    ``core_goal_check`` block and ``round_kind`` field per spec
    v0.3.0-rc1 §14 / §15. The dict is also what is written to
    ``config.out`` if supplied.
    """

    config.validate()
    metrics = build_r6_placeholder()

    # --- (1) Trigger eval (D6 R1/R2/R3/R4) ---
    with Path(config.eval_pack).open("r", encoding="utf-8") as fh:
        eval_pack = yaml.safe_load(fh) or {}
    vocab = Vocabulary.from_yaml(Path(config.vocabulary))
    trigger = cjk_evaluate_pack(eval_pack, vocab)
    metrics["routing_cost"]["R1_trigger_precision"] = trigger.precision
    metrics["routing_cost"]["R2_trigger_recall"] = trigger.recall
    metrics["routing_cost"]["R3_trigger_F1"] = trigger.f1
    metrics["routing_cost"]["R4_near_miss_FP_rate"] = trigger.near_miss_fp_rate

    # --- (2) Token / context (D2 C1/C2/C4) ---
    token_info = None
    try:
        token_info = _count_tokens_via_subprocess(
            Path(config.skill_md), Path(config.count_tokens_script)
        )
    except (FileNotFoundError, RuntimeError) as exc:
        LOGGER.warning("token counter unavailable: %s", exc)
    if token_info is not None:
        c1 = token_info.get("metadata_tokens")
        c2 = token_info.get("body_tokens")
        metrics["context_economy"]["C1_metadata_tokens"] = c1
        metrics["context_economy"]["C2_body_tokens"] = c2
        if isinstance(c1, int) and isinstance(c2, int):
            metrics["context_economy"]["C4_per_invocation_footprint"] = c1 + c2

    # --- (3) Functional tests (D1 T1/T3 + D3 L1/L2) ---
    functional_trace: Dict[str, Any] = {}
    if not skip_functional_tests:
        functional_trace = run_functional_tests(
            config.test_runner_cmd,
            Path(config.test_runner_cwd),
            runs=config.runs,
        )
        metrics["task_quality"]["T1_pass_rate"] = functional_trace["T1_pass_rate"]
        metrics["latency_path"]["L1_wall_clock_p50"] = functional_trace[
            "L1_wall_clock_p50"
        ]
        metrics["latency_path"]["L2_wall_clock_p95"] = functional_trace[
            "L2_wall_clock_p95"
        ]

    # --- (3b) T3 baseline delta (if baseline provided) ---
    baseline_trace: Dict[str, Any] = {}
    t3 = None
    if config.baseline_runner_cmd and not skip_functional_tests:
        baseline_trace = run_functional_tests(
            config.baseline_runner_cmd,
            Path(config.test_runner_cwd),
            runs=config.runs,
        )
        t3 = round(
            functional_trace.get("T1_pass_rate", 0.0)
            - baseline_trace.get("T1_pass_rate", 0.0),
            4,
        )
    metrics["task_quality"]["T3_baseline_delta"] = t3

    # --- (4) Core-goal test pack (C0) ---
    core_goal_result = run_core_goal_test_pack(
        Path(config.core_goal_test_pack),
        config.test_runner_cmd,
        Path(config.test_runner_cwd),
    )
    failed_case_ids = [
        c["case_id"] for c in core_goal_result["per_case"] if not c["passed"]
    ]
    core_goal_check = build_core_goal_check(
        c0_pass_rate=core_goal_result["pass_rate"],
        cases_passed=core_goal_result["cases_passed"],
        cases_total=core_goal_result["cases_total"],
        prior_c0_pass_rate=prior_c0_pass_rate,
        round_kind=config.round_kind,
        failed_case_ids=failed_case_ids,
    )

    # --- (5) Assemble metrics_report ---
    metrics_report = {
        "schema_version": "0.2.0",
        "script_version": SCRIPT_VERSION,
        "ability_id": config.ability,
        "round_kind": config.round_kind,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metrics": metrics,
        "core_goal": {
            "C0_core_goal_pass_rate": core_goal_result["pass_rate"],
            "cases_passed": core_goal_result["cases_passed"],
            "cases_total": core_goal_result["cases_total"],
            "failed_case_ids": failed_case_ids,
            "per_case": core_goal_result["per_case"],
        },
        "core_goal_check": core_goal_check,
        "trigger_confusion": {
            "tp": trigger.tp,
            "fp": trigger.fp,
            "fn": trigger.fn,
            "tn": trigger.tn,
        },
        "trigger_per_prompt": trigger.per_prompt,
        "token_info": token_info,
        "functional_tests": functional_trace,
        "baseline_tests": baseline_trace or None,
        "spec_section": "v0.3.0-rc1 §3 + §14 + §15",
    }

    # --- (6) Write metrics_report.yaml if --out supplied ---
    if config.out is not None:
        out_path = Path(config.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                metrics_report,
                fh,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
        LOGGER.info("wrote metrics_report to %s", out_path)

    return metrics_report


# --- CLI --------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval_skill",
        description=(
            "Generic Si-Chip per-ability evaluation harness. Produces a "
            "metrics_report.yaml covering R6 7×37 + C0 core_goal_check + "
            "round_kind per spec v0.3.0-rc1."
        ),
    )
    parser.add_argument(
        "--ability", required=True, help="Ability id (BasicAbility.id)"
    )
    parser.add_argument(
        "--skill-md",
        required=True,
        help="Path to the ability's SKILL.md (for C1/C2).",
    )
    parser.add_argument(
        "--vocabulary",
        required=True,
        help="Path to the ability's vocabulary yaml (for R1/R2/R3/R4).",
    )
    parser.add_argument(
        "--eval-pack",
        required=True,
        help="Path to the ability's trigger eval pack yaml.",
    )
    parser.add_argument(
        "--core-goal-test-pack",
        required=True,
        help="Path to the ability's core_goal_test_pack yaml (C0).",
    )
    parser.add_argument(
        "--test-runner-cmd",
        required=True,
        help="Shell command to run functional tests (e.g. 'npm test --silent').",
    )
    parser.add_argument(
        "--test-runner-cwd",
        required=True,
        help="Working directory for the test runner.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of times to run the functional test runner (default 3).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Path to write metrics_report.yaml (optional).",
    )
    parser.add_argument(
        "--round-kind",
        choices=sorted(ROUND_KINDS),
        default=None,
        help="round_kind value per spec §15.1; optional at the harness level.",
    )
    parser.add_argument(
        "--baseline-runner-cmd",
        default=None,
        help="Optional no-ability baseline runner (used for T3 delta).",
    )
    parser.add_argument(
        "--prior-c0-pass-rate",
        type=float,
        default=None,
        help="Prior round's C0 for regression-detection (optional).",
    )
    parser.add_argument(
        "--count-tokens-script",
        default=str(DEFAULT_COUNT_TOKENS_SCRIPT),
        help="Path to count_tokens.py (default: .agents/skills/si-chip/scripts).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config = EvalSkillConfig(
        ability=args.ability,
        skill_md=Path(args.skill_md),
        vocabulary=Path(args.vocabulary),
        eval_pack=Path(args.eval_pack),
        core_goal_test_pack=Path(args.core_goal_test_pack),
        test_runner_cmd=args.test_runner_cmd,
        test_runner_cwd=Path(args.test_runner_cwd),
        runs=args.runs,
        out=Path(args.out) if args.out else None,
        round_kind=args.round_kind,
        baseline_runner_cmd=args.baseline_runner_cmd,
        count_tokens_script=Path(args.count_tokens_script),
    )
    report = run_evaluation(
        config, prior_c0_pass_rate=args.prior_c0_pass_rate
    )

    print(f"eval_skill v{SCRIPT_VERSION} — ability={config.ability}")
    print(f"  round_kind : {report['round_kind']}")
    rc_metrics = report["metrics"]["routing_cost"]
    print(
        "  R3_trigger_F1={} (R1={} R2={} R4={})".format(
            rc_metrics["R3_trigger_F1"],
            rc_metrics["R1_trigger_precision"],
            rc_metrics["R2_trigger_recall"],
            rc_metrics["R4_near_miss_FP_rate"],
        )
    )
    ce_metrics = report["metrics"]["context_economy"]
    print(
        "  C1={} C2={} C4={}".format(
            ce_metrics["C1_metadata_tokens"],
            ce_metrics["C2_body_tokens"],
            ce_metrics["C4_per_invocation_footprint"],
        )
    )
    lp_metrics = report["metrics"]["latency_path"]
    print(
        "  T1={} L1={} L2={}".format(
            report["metrics"]["task_quality"]["T1_pass_rate"],
            lp_metrics["L1_wall_clock_p50"],
            lp_metrics["L2_wall_clock_p95"],
        )
    )
    cg = report["core_goal_check"]
    print(
        "  C0={} (pass_rate, {}/{} cases); rollback_required={}".format(
            cg["C0_pass_rate_current"],
            cg["cases_passed"],
            cg["cases_total"],
            cg["rollback_required"],
        )
    )
    if args.out:
        print(f"  wrote: {args.out}")
    return 0


# --- v0.4.0 Wave 1c additions: G2 / G3 / G4 helpers (append-only) -----
#
# These three helpers consume output produced by
# ``evals/si-chip/runners/real_llm_runner.py`` and return the D4
# Generalizability sub-metrics (G2 / G3 / G4) per spec §3.1. They are
# pure functions over the runner output dict — they do NOT make LLM
# calls themselves — so a Stage 6c dogfood run can measure G2/G3/G4
# against a single cached matrix run without re-paying API cost.
#
# Runner output shape consumed (see real_llm_runner.RealLLMRunner.
# evaluate_matrix) is::
#
#     {
#       "ability_id": str,
#       "matrix_mode": "mvp"|"intermediate"|"full",
#       "cells": [
#         {"model": str, "thinking_depth": str, "scenario_pack": str,
#          "prompts_run": int, "passes": int, "pass_rate": float,
#          "pass_at_k": float, "tokens_in": int, "tokens_out": int,
#          "duration_s": float, "provenance": str,
#          "per_prompt": [{"prompt": str, "pass_at_k": float, ...}]},
#         ...
#       ],
#       "summary": {...},
#     }


def compute_g2_cross_domain_transfer_pass(
    runner_output: Dict[str, Any],
    source_domain: str,
    target_domain: str,
) -> Dict[str, Any]:
    """§3.1 D4 G2 ``cross_domain_transfer_pass`` from a runner_output.

    Selects cells whose ``scenario_pack`` (or an explicit ``domain``
    tag) matches ``target_domain`` and computes the mean ``pass_rate``
    weighted by ``prompts_run``. The ``source_domain`` argument is
    recorded in ``provenance`` so downstream consumers can see which
    domain the ability was tuned on.

    Returns ``{pass_rate, sample_count, cells_matched, provenance}``.
    """

    if not isinstance(runner_output, dict):
        raise TypeError(
            f"runner_output must be a dict, got {type(runner_output).__name__}"
        )
    cells = runner_output.get("cells") or []
    matched: List[Dict[str, Any]] = [
        c
        for c in cells
        if (c.get("domain") == target_domain)
        or (c.get("scenario_pack") == target_domain)
    ]
    total_prompts = 0
    weighted_pass_sum = 0.0
    for cell in matched:
        n = int(cell.get("prompts_run") or 0)
        if n <= 0:
            continue
        total_prompts += n
        weighted_pass_sum += float(cell.get("pass_rate") or 0.0) * n
    pass_rate = (
        round(weighted_pass_sum / total_prompts, 4)
        if total_prompts > 0
        else 0.0
    )
    return {
        "pass_rate": pass_rate,
        "sample_count": total_prompts,
        "cells_matched": len(matched),
        "provenance": {
            "source_domain": source_domain,
            "target_domain": target_domain,
            "ability_id": runner_output.get("ability_id"),
            "matrix_mode": runner_output.get("matrix_mode"),
            "runner_source": "evals/si-chip/runners/real_llm_runner.py",
        },
    }


def compute_g3_ood_robustness(
    runner_output: Dict[str, Any], ood_pack_path: Path
) -> Dict[str, Any]:
    """§3.1 D4 G3 ``OOD_robustness`` against a curated OOD prompt pack.

    Loads the OOD pack (chip-usage-helper eval_pack format —
    ``should_trigger`` + ``should_not_trigger`` buckets), then scans
    every ``per_prompt`` entry in the runner_output cells for prompts
    that appear in the OOD set. Returns the mean ``pass_at_k`` across
    the matched entries and a list of fail cases (where ``pass_at_k``
    is 0.0 — i.e. ALL k samples were wrong for that prompt in that
    cell).

    Returns ``{pass_rate, sample_count, fail_cases, provenance}``.
    """

    if not isinstance(runner_output, dict):
        raise TypeError(
            f"runner_output must be a dict, got {type(runner_output).__name__}"
        )
    ood_pack_path = Path(ood_pack_path)
    if not ood_pack_path.exists():
        raise FileNotFoundError(
            f"OOD pack not found: {ood_pack_path}"
        )
    with ood_pack_path.open("r", encoding="utf-8") as fh:
        ood_pack = yaml.safe_load(fh) or {}
    ood_prompts: set[str] = set(
        str(p) for p in (ood_pack.get("should_trigger") or [])
    ) | set(
        str(p) for p in (ood_pack.get("should_not_trigger") or [])
    )
    pass_at_k_values: List[float] = []
    fail_cases: List[Dict[str, Any]] = []
    for cell in runner_output.get("cells") or []:
        for pp in cell.get("per_prompt") or []:
            if pp.get("prompt") in ood_prompts:
                pak = float(pp.get("pass_at_k") or 0.0)
                pass_at_k_values.append(pak)
                if pak == 0.0:
                    fail_cases.append(
                        {
                            "prompt": pp.get("prompt"),
                            "model": cell.get("model"),
                            "thinking_depth": cell.get("thinking_depth"),
                            "scenario_pack": cell.get("scenario_pack"),
                        }
                    )
    pass_rate = (
        round(sum(pass_at_k_values) / len(pass_at_k_values), 4)
        if pass_at_k_values
        else 0.0
    )
    return {
        "pass_rate": pass_rate,
        "sample_count": len(pass_at_k_values),
        "fail_cases": fail_cases,
        "provenance": {
            "ood_pack_path": str(ood_pack_path),
            "ood_prompt_count": len(ood_prompts),
            "ability_id": runner_output.get("ability_id"),
            "runner_source": "evals/si-chip/runners/real_llm_runner.py",
        },
    }


def compute_g4_model_version_stability(
    current_runner_output: Dict[str, Any],
    prior_runner_output: Dict[str, Any],
    drift_threshold: float = 0.05,
) -> Dict[str, Any]:
    """§3.1 D4 G4 ``model_version_stability`` across two runner runs.

    Matches cells by ``(model, thinking_depth, scenario_pack)``;
    computes per-cell ``pass_rate`` delta (current − prior) and
    considers the cell stable iff ``|delta| < drift_threshold``.

    Returns
    -------
    dict with ``stability_ratio`` (fraction of matched cells that are
    stable), ``drift_cases`` (list of cells whose |delta| ≥ threshold),
    ``per_model_delta`` (mean delta per model), ``matched_cells``,
    ``drift_threshold``, and ``provenance``.
    """

    if not isinstance(current_runner_output, dict):
        raise TypeError(
            "current_runner_output must be a dict, got "
            f"{type(current_runner_output).__name__}"
        )
    if not isinstance(prior_runner_output, dict):
        raise TypeError(
            "prior_runner_output must be a dict, got "
            f"{type(prior_runner_output).__name__}"
        )

    def _index(output: Dict[str, Any]) -> Dict[tuple, Dict[str, Any]]:
        return {
            (
                c.get("model"),
                c.get("thinking_depth"),
                c.get("scenario_pack"),
            ): c
            for c in (output.get("cells") or [])
        }

    cur_idx = _index(current_runner_output)
    prior_idx = _index(prior_runner_output)
    matched_keys = sorted(
        set(cur_idx.keys()) & set(prior_idx.keys()),
        key=lambda k: tuple(str(x) for x in k),
    )
    drift_cases: List[Dict[str, Any]] = []
    per_model_deltas: Dict[str, List[float]] = {}
    stable = 0
    for key in matched_keys:
        cur_pr = float(cur_idx[key].get("pass_rate") or 0.0)
        prior_pr = float(prior_idx[key].get("pass_rate") or 0.0)
        delta = round(cur_pr - prior_pr, 4)
        model = key[0] or "<unknown>"
        per_model_deltas.setdefault(model, []).append(delta)
        if abs(delta) < drift_threshold:
            stable += 1
        else:
            drift_cases.append(
                {
                    "model": key[0],
                    "thinking_depth": key[1],
                    "scenario_pack": key[2],
                    "prior_pass_rate": prior_pr,
                    "current_pass_rate": cur_pr,
                    "delta": delta,
                }
            )
    per_model_delta_mean = {
        m: round(sum(ds) / len(ds), 4) for m, ds in per_model_deltas.items()
    }
    stability_ratio = (
        round(stable / len(matched_keys), 4) if matched_keys else 0.0
    )
    return {
        "stability_ratio": stability_ratio,
        "drift_cases": drift_cases,
        "per_model_delta": per_model_delta_mean,
        "matched_cells": len(matched_keys),
        "drift_threshold": drift_threshold,
        "provenance": {
            "current_ability_id": current_runner_output.get("ability_id"),
            "prior_ability_id": prior_runner_output.get("ability_id"),
            "current_matrix_mode": current_runner_output.get("matrix_mode"),
            "prior_matrix_mode": prior_runner_output.get("matrix_mode"),
            "runner_source": "evals/si-chip/runners/real_llm_runner.py",
        },
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    sys.exit(main())
