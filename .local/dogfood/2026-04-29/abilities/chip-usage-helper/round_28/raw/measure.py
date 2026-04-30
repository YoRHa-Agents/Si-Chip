#!/usr/bin/env python3
"""Round 27 token-tier measurement for chip-usage-helper.

Measures v1.1.0 (commit 8001e4e) vs v1.2.0 (current HEAD) for the
EAGER / ON-CALL / LAZY / MCP-tool-description tiers per Si-Chip §3 / R6.

Backend: tiktoken (cl100k_base).  Falls back to whitespace-split if
tiktoken unavailable (documented in measurement.yaml `backend`).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/agent/workspace/ChipPlugins/chips/chip_usage_helper")
BASELINE_COMMIT = "8001e4e"  # v1.1.0 head, prior to v1.2.0 migration


def count_tokens(text: str) -> tuple[int, str]:
    try:
        import tiktoken
    except ImportError:
        units = re.split(r"[\s\W_]+", text, flags=re.UNICODE)
        return sum(1 for u in units if u), "fallback_whitespace"
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text)), "tiktoken_cl100k_base"


def show_at(commit: str, path: str) -> str | None:
    """Return file content at given commit, or None if missing."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO), "show", f"{commit}:{path}"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return None


def read_current(path: str) -> str | None:
    p = REPO / path
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


# Files per tier
TIERS = {
    "EAGER": [
        "rules/usage-helper.mdc",
    ],
    "ON_CALL": [
        "skills/chip-usage-helper/SKILL.md",
    ],
    "LAZY": [
        "skills/chip-usage-helper/templates/types.d.ts",
        "skills/chip-usage-helper/templates/empty-data.ts",
        "skills/chip-usage-helper/templates/usage.canvas.template.tsx",
    ],
}

# Tools to inspect (file → tool name); v1.1.0 had 9, v1.2.0 has 16.
TOOL_FILES = [
    ("mcp/src/tools/get-me.ts", "get_me"),
    ("mcp/src/tools/get-week-usage.ts", "get_week_usage"),
    ("mcp/src/tools/get-month-totals.ts", "get_month_totals"),
    ("mcp/src/tools/get-agent-hours.ts", "get_agent_hours"),
    ("mcp/src/tools/get-rankings.ts", "get_rankings"),
    ("mcp/src/tools/get-dashboard-data.ts", "get_dashboard_data"),
    ("mcp/src/tools/diagnose-identity.ts", "diagnose_identity"),
    ("mcp/src/tools/get-upstream-health.ts", "get_upstream_health"),
    ("mcp/src/tools/get-litellm-usage-by-user.ts", "get_litellm_usage_by_user"),
    ("mcp/src/tools/get-litellm-usage-by-model.ts", "get_litellm_usage_by_model"),
    ("mcp/src/tools/get-litellm-spend-series.ts", "get_litellm_spend_series"),
    ("mcp/src/tools/get-litellm-spend-snapshot.ts", "get_litellm_spend_snapshot"),
    ("mcp/src/tools/get-me-summary.ts", "get_me_summary"),
    ("mcp/src/tools/get-team-summary-by-user.ts", "get_team_summary_by_user"),
    ("mcp/src/tools/get-team-summary-series.ts", "get_team_summary_series"),
    ("mcp/src/tools/get-my-tasks.ts", "get_my_tasks"),
]

DESC_RE = re.compile(
    r"description:\s*(?:\"((?:[^\"\\]|\\.)*)\"|\"((?:[^\"\\]|\\.)*)\"\s*\+\s*\n\s*\"((?:[^\"\\]|\\.)*)\")",
)
# Simpler approach: pull the description value using a multi-line aware matcher.
DESC_BLOCK = re.compile(
    r"description:\s*((?:\"[^\"\\]*(?:\\.[^\"\\]*)*\"\s*(?:\+\s*\n\s*\"[^\"\\]*(?:\\.[^\"\\]*)*\"\s*)*)+)",
    re.MULTILINE,
)


def extract_description(src: str) -> str | None:
    m = DESC_BLOCK.search(src)
    if not m:
        return None
    chunk = m.group(1)
    parts = re.findall(r"\"((?:[^\"\\]|\\.)*)\"", chunk)
    if not parts:
        return None
    raw = "".join(parts)
    return bytes(raw, "utf-8").decode("unicode_escape")


def measure_file(path: str) -> dict:
    cur = read_current(path)
    base = show_at(BASELINE_COMMIT, path)
    cur_tokens, backend_cur = (count_tokens(cur) if cur is not None else (None, None))
    base_tokens, backend_base = (count_tokens(base) if base is not None else (None, None))
    return {
        "path": path,
        "v110_tokens": base_tokens,
        "v110_lines": (None if base is None else base.count("\n") + (0 if base.endswith("\n") else 1)),
        "v120_tokens": cur_tokens,
        "v120_lines": (None if cur is None else cur.count("\n") + (0 if cur.endswith("\n") else 1)),
        "delta_tokens": (
            None if (cur_tokens is None or base_tokens is None)
            else cur_tokens - base_tokens
        ),
        "v110_present": base is not None,
        "v120_present": cur is not None,
        "backend": backend_cur or backend_base,
    }


def measure_tools() -> list[dict]:
    rows = []
    for path, tool_name in TOOL_FILES:
        cur_src = read_current(path)
        base_src = show_at(BASELINE_COMMIT, path)
        cur_desc = extract_description(cur_src) if cur_src else None
        base_desc = extract_description(base_src) if base_src else None
        cur_tokens = count_tokens(cur_desc)[0] if cur_desc is not None else None
        base_tokens = count_tokens(base_desc)[0] if base_desc is not None else None
        rows.append({
            "tool": tool_name,
            "path": path,
            "v110_present": base_src is not None,
            "v120_present": cur_src is not None,
            "v110_desc_tokens": base_tokens,
            "v120_desc_tokens": cur_tokens,
            "v110_desc_chars": (len(base_desc) if base_desc else None),
            "v120_desc_chars": (len(cur_desc) if cur_desc else None),
            "v120_desc": cur_desc,
        })
    return rows


def main() -> int:
    out = {
        "baseline_commit": BASELINE_COMMIT,
        "head_commit_at_measurement": subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"]
        ).decode().strip(),
        "tiers": {},
        "tools": [],
        "tool_summary": {},
        "totals": {},
    }
    for tier_name, files in TIERS.items():
        out["tiers"][tier_name] = [measure_file(p) for p in files]

    out["tools"] = measure_tools()

    # Totals
    eager_v110 = sum(r["v110_tokens"] or 0 for r in out["tiers"]["EAGER"])
    eager_v120 = sum(r["v120_tokens"] or 0 for r in out["tiers"]["EAGER"])
    on_call_v110 = sum(r["v110_tokens"] or 0 for r in out["tiers"]["ON_CALL"])
    on_call_v120 = sum(r["v120_tokens"] or 0 for r in out["tiers"]["ON_CALL"])
    lazy_v110 = sum(r["v110_tokens"] or 0 for r in out["tiers"]["LAZY"] if r["v110_present"])
    lazy_v120 = sum(r["v120_tokens"] or 0 for r in out["tiers"]["LAZY"] if r["v120_present"])

    tools_v110 = sum(t["v110_desc_tokens"] or 0 for t in out["tools"] if t["v110_present"])
    tools_v120 = sum(t["v120_desc_tokens"] or 0 for t in out["tools"] if t["v120_present"])
    tools_count_v110 = sum(1 for t in out["tools"] if t["v110_present"])
    tools_count_v120 = sum(1 for t in out["tools"] if t["v120_present"])

    out["tool_summary"] = {
        "tools_present_v110": tools_count_v110,
        "tools_present_v120": tools_count_v120,
        "sum_description_tokens_v110": tools_v110,
        "sum_description_tokens_v120": tools_v120,
        "delta_description_tokens": tools_v120 - tools_v110,
        "max_description_tokens_v120": max((t["v120_desc_tokens"] or 0 for t in out["tools"]), default=0),
        "tools_over_25_v120": [
            t["tool"] for t in out["tools"]
            if (t["v120_desc_tokens"] or 0) > 25
        ],
        "tools_over_30_v120": [
            t["tool"] for t in out["tools"]
            if (t["v120_desc_tokens"] or 0) > 30
        ],
    }

    out["totals"] = {
        "eager": {"v110": eager_v110, "v120": eager_v120, "delta": eager_v120 - eager_v110},
        "on_call": {"v110": on_call_v110, "v120": on_call_v120, "delta": on_call_v120 - on_call_v110},
        "lazy": {"v110": lazy_v110, "v120": lazy_v120, "delta": lazy_v120 - lazy_v110},
        "mcp_tool_descriptions": {"v110": tools_v110, "v120": tools_v120, "delta": tools_v120 - tools_v110},
    }
    out["totals"]["all_tiers_combined"] = {
        "v110": eager_v110 + on_call_v110 + lazy_v110 + tools_v110,
        "v120": eager_v120 + on_call_v120 + lazy_v120 + tools_v120,
        "delta": (eager_v120 + on_call_v120 + lazy_v120 + tools_v120)
                 - (eager_v110 + on_call_v110 + lazy_v110 + tools_v110),
    }

    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
