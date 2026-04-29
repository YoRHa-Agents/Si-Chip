#!/usr/bin/env python3
"""Unit tests for ``tools/cjk_trigger_eval.py``.

Covers tokenisation (ASCII / CJK / mixed), per-phase rule application
(slash command / built-in discriminators / strong anchors / weak
accumulation), and an end-to-end F1 sanity test on a synthetic pack.
The optional chip-usage-helper baseline test loads the real 40-prompt
pack from ``.local/dogfood/.../abilities/chip-usage-helper/eval_pack.yaml``
and asserts F1 ≥ 0.85 (published Round 1 R3 = 0.9524).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.cjk_trigger_eval import (  # noqa: E402
    EvaluationResult,
    Vocabulary,
    evaluate_pack,
    evaluate_pack_from_paths,
    main,
    tokenize_prompt,
    trigger_match,
)

CJK_SCRIPT = REPO_ROOT / "tools" / "cjk_trigger_eval.py"
CHIP_USAGE_PACK = (
    REPO_ROOT
    / ".local"
    / "dogfood"
    / "2026-04-29"
    / "abilities"
    / "chip-usage-helper"
    / "eval_pack.yaml"
)


@pytest.fixture
def synthetic_vocab() -> Vocabulary:
    """Minimal vocab used by the 4-prompt F1 sanity test."""

    return Vocabulary(
        ascii_anchors={"foo"},
        ascii_weak=set(),
        cjk_strong=[],
        cjk_weak=[],
        discriminators=[],
        slash_commands=[],
        min_weak_hits=100,
        cursor_plus_cjk_usage=[],
    )


@pytest.fixture
def chip_mirror_vocab() -> Vocabulary:
    """Approximate mirror of the chip-usage-helper vocabulary used in
    ``eval_chip_usage_helper.py``. Kept synchronous with that file's
    ``load_trigger_vocabulary`` + ``trigger_match`` bodies so the
    evaluator's F1 converges on the published Round 1 R3 = 0.9524.
    """

    return Vocabulary(
        ascii_anchors={
            "usage",
            "dashboard",
            "billing",
            "ranking",
            "leaderboard",
        },
        ascii_weak={
            "cursor",
            "agent",
            "spend",
            "breakdown",
            "monthly",
            "cost",
            "rank",
            "team",
            "account",
            "events",
            "week",
            "month",
            "usage-report",
        },
        cjk_strong=[
            "用量",
            "工时",
            "排第几",
            "排名",
            "账单",
            "计费",
            "开销",
            "费用",
        ],
        cjk_weak=[
            "花了",
            "花费",
            "消耗",
            "多少钱",
            "多少",
            "占比",
            "模型",
            "分布",
            "本月",
            "上月",
            "上个月",
            "这个月",
            "这周",
            "本周",
            "团队",
            "我排",
            "花的",
            "账户",
        ],
        discriminators=[
            {"name": "cursor_meta"},
            {"name": "time_spend"},
        ],
        slash_commands=["/usage-report"],
        min_weak_hits=2,
        cursor_plus_cjk_usage=["用量", "花了", "花费"],
    )


def test_tokenize_ascii_only():
    tokens = tokenize_prompt("show me cursor usage")
    assert tokens == {"show", "me", "cursor", "usage"}


def test_tokenize_cjk_only():
    tokens = tokenize_prompt("本月花了多少钱")
    assert tokens == {"本月花了多少钱"}


def test_tokenize_mixed():
    tokens = tokenize_prompt("我的 cursor 用量")
    assert tokens == {"我的", "cursor", "用量"}


def test_tokenize_lowercases_ascii():
    tokens = tokenize_prompt("Show Me CURSOR Usage")
    assert tokens == {"show", "me", "cursor", "usage"}


def test_tokenize_rejects_non_str():
    with pytest.raises(TypeError):
        tokenize_prompt(None)  # type: ignore[arg-type]


def test_trigger_slash_command(synthetic_vocab):
    synthetic_vocab.slash_commands = ["/usage-report"]
    decision = trigger_match("/usage-report --window=30d", synthetic_vocab)
    assert decision["match"] is True
    assert decision["reason"] == "slash_command"


def test_trigger_cursor_meta_discriminator(chip_mirror_vocab):
    decision = trigger_match(
        "explain how Cursor Composer works", chip_mirror_vocab
    )
    assert decision["match"] is False
    assert decision["reason"].startswith("discriminator:")
    assert "cursor_meta" in decision["reason"]


def test_trigger_time_spend_discriminator(chip_mirror_vocab):
    decision = trigger_match("spend time reviewing the PR", chip_mirror_vocab)
    assert decision["match"] is False
    assert decision["reason"] == "discriminator:time_spend"


def test_trigger_strong_ascii_anchor(chip_mirror_vocab):
    decision = trigger_match(
        "show me my usage dashboard", chip_mirror_vocab
    )
    assert decision["match"] is True
    assert decision["reason"] == "strong_ascii"
    assert decision["layer_hit"] == "A_ascii"


def test_trigger_strong_cjk_anchor(chip_mirror_vocab):
    decision = trigger_match("我的 cursor 用量", chip_mirror_vocab)
    assert decision["match"] is True
    assert decision["reason"].startswith("strong_cjk:")
    assert "用量" in decision["reason"]


def test_trigger_weak_accumulation(chip_mirror_vocab):
    decision = trigger_match(
        "how much did I spend on cursor this month", chip_mirror_vocab
    )
    assert decision["match"] is True
    assert decision["reason"].startswith("weak_accumulation")


def test_trigger_default_no_match(chip_mirror_vocab):
    decision = trigger_match("how to debug a segfault", chip_mirror_vocab)
    assert decision["match"] is False
    assert decision["reason"] == "no_match"


def test_trigger_custom_discriminator_fires():
    vocab = Vocabulary(
        ascii_anchors={"deploy"},
        discriminators=[
            {
                "name": "dryrun_guard",
                "if_token_in_prompt": ["deploy"],
                "and_any_token_in_prompt": ["dryrun", "dry-run", "preview"],
                "suppress": True,
            }
        ],
        min_weak_hits=10,
    )
    suppressed = trigger_match("deploy in dryrun mode", vocab)
    assert suppressed["match"] is False
    assert suppressed["reason"] == "discriminator:dryrun_guard"

    fired = trigger_match("deploy now", vocab)
    assert fired["match"] is True
    assert fired["reason"] == "strong_ascii"


def test_evaluate_pack_f1(synthetic_vocab):
    # 2 should-trigger (1 TP, 1 FN), 2 should-not (1 FP, 1 TN)
    pack = {
        "should_trigger": ["hello foo world", "no match here"],
        "should_not_trigger": ["unwanted foo pops in", "clean prompt"],
    }
    result = evaluate_pack(pack, synthetic_vocab)
    assert isinstance(result, EvaluationResult)
    assert result.tp == 1
    assert result.fp == 1
    assert result.fn == 1
    assert result.tn == 1
    assert result.precision == 0.5
    assert result.recall == 0.5
    assert result.f1 == 0.5
    assert result.near_miss_fp_rate == 0.5
    assert result.n_should == 2
    assert result.n_should_not == 2
    assert len(result.per_prompt) == 4


def test_evaluate_pack_empty_returns_zero(synthetic_vocab):
    pack = {"should_trigger": [], "should_not_trigger": []}
    result = evaluate_pack(pack, synthetic_vocab)
    assert result.tp == 0 and result.fp == 0 and result.fn == 0 and result.tn == 0
    assert result.f1 == 0.0


def test_vocabulary_from_yaml(tmp_path):
    vocab_yaml = tmp_path / "vocab.yaml"
    vocab_yaml.write_text(
        yaml.safe_dump(
            {
                "ascii_anchors": ["foo", "bar"],
                "ascii_weak": ["baz"],
                "cjk_strong": ["强"],
                "cjk_weak": ["弱"],
                "slash_commands": ["/run"],
                "min_weak_hits": 3,
            }
        ),
        encoding="utf-8",
    )
    vocab = Vocabulary.from_yaml(vocab_yaml)
    assert vocab.ascii_anchors == {"foo", "bar"}
    assert vocab.cjk_strong == ["强"]
    assert vocab.min_weak_hits == 3


def test_vocabulary_from_yaml_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Vocabulary.from_yaml(tmp_path / "does-not-exist.yaml")


def test_evaluate_pack_from_paths_roundtrip(tmp_path, synthetic_vocab):
    pack_path = tmp_path / "pack.yaml"
    vocab_path = tmp_path / "vocab.yaml"
    pack_path.write_text(
        yaml.safe_dump(
            {
                "should_trigger": ["foo bar"],
                "should_not_trigger": ["quux qux"],
            }
        )
    )
    vocab_path.write_text(
        yaml.safe_dump(
            {
                "ascii_anchors": ["foo"],
                "min_weak_hits": 100,
            }
        )
    )
    result = evaluate_pack_from_paths(pack_path, vocab_path)
    assert result.tp == 1
    assert result.tn == 1
    assert result.precision == 1.0
    assert result.recall == 1.0


@pytest.mark.skipif(
    not CHIP_USAGE_PACK.exists(),
    reason="chip-usage-helper eval pack not present in this workspace",
)
def test_evaluate_pack_chip_usage_helper_baseline(chip_mirror_vocab):
    """Integration smoke test: F1 must clear 0.85 vs the real 40-prompt pack.

    Reference: chip-usage-helper Round 1 reported R3_trigger_F1 = 0.9524.
    This generic harness + mirror vocab must stay within rounding of that.
    """

    with CHIP_USAGE_PACK.open("r", encoding="utf-8") as fh:
        pack = yaml.safe_load(fh)
    result = evaluate_pack(pack, chip_mirror_vocab)
    assert result.f1 >= 0.85, (
        f"F1={result.f1:.4f} below 0.85 threshold; "
        f"tp={result.tp} fp={result.fp} fn={result.fn} tn={result.tn}"
    )


def test_cli_json_output(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    vocab_path = tmp_path / "vocab.yaml"
    pack_path.write_text(
        yaml.safe_dump(
            {
                "should_trigger": ["hello foo world"],
                "should_not_trigger": ["no match here"],
            }
        )
    )
    vocab_path.write_text(
        yaml.safe_dump({"ascii_anchors": ["foo"], "min_weak_hits": 100})
    )
    result = subprocess.run(
        [
            sys.executable,
            str(CJK_SCRIPT),
            "--eval-pack",
            str(pack_path),
            "--vocabulary",
            str(vocab_path),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["tp"] == 1
    assert payload["tn"] == 1
    assert payload["precision"] == 1.0
    assert payload["recall"] == 1.0


def test_cli_help():
    result = subprocess.run(
        [sys.executable, str(CJK_SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--eval-pack" in result.stdout
    assert "--vocabulary" in result.stdout
