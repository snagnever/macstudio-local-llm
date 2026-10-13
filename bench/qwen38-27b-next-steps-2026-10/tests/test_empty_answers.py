import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "bench/qwen38-27b-next-steps-2026-10/scripts"))
sys.path.insert(0, str(ROOT / "bench/flashnext-next-steps-2026-10/scripts"))
import empty_answers  # noqa: E402
import decide  # noqa: E402


def test_think_turn_record_empty_when_content_zero():
    assert empty_answers.is_empty({"finish_reason": "stop", "content_chars": 0, "reasoning_chars": 900})
    assert not empty_answers.is_empty({"finish_reason": "stop", "content_chars": 12})
    assert not empty_answers.is_empty({"finish_reason": "length", "content_chars": 0})


def test_bench2_record_empty_when_raw_response_blank():
    assert empty_answers.is_empty({"finish_reason": "stop", "raw_response": "  \n"})
    assert not empty_answers.is_empty({"finish_reason": "stop", "raw_response": "B"})


def test_if_probe_and_toolbench_records():
    assert empty_answers.is_empty({"finish_reason": "stop", "content_preview": ""})
    assert not empty_answers.is_empty({"finish_reason": "stop", "raw_message": {"content": "ok"}})
    assert empty_answers.is_empty({"finish_reason": "stop", "raw_message": {"content": ""}})


def test_count_over_files(tmp_path):
    f = tmp_path / "a.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in [
        {"finish_reason": "stop", "content_chars": 0},
        {"finish_reason": "stop", "content_chars": 5},
        {"finish_reason": "length", "content_chars": 0},
    ]) + "\n")
    assert empty_answers.count([f]) == (1, 2)


def _rows(arm, ctx, hit):
    base = {"arm": arm, "context_target": ctx, "finish_reason": "stop", "error": None, "correct": True,
            "decode_tps": 40.0, "ttft_ms": 5000, "cache_hit_ratio": hit, "swap_delta_gb": 0.0,
            "session_id": f"s-{arm}", "runtime": "splash"}
    return [dict(base, scenario=s) for s in ("cold", "identical", "append", "tool_turn")]


def test_decide_skip_gates_ignores_hit(tmp_path, capsys):
    (tmp_path / "logs").mkdir()
    for arm, hit in (("s27r", 0.99), ("k27", 0.0)):
        with (tmp_path / f"{arm}-32768-t1.0-p1x.jsonl").open("w") as fh:
            for r in _rows(arm, 32768, hit):
                fh.write(json.dumps(r) + "\n")
    argv = ["--results-dir", str(tmp_path), "--logs-dir", str(tmp_path / "logs"), "--glob", "*-p1x.jsonl",
            "--base", "s27r", "--cand", "k27", "--ctx", "32768", "--mode", "le", "--threshold", "1.03"]
    assert decide.main(argv) == 1
    assert "hit_append" in capsys.readouterr().out
    assert decide.main(argv + ["--skip-gates", "hit_append,hit_tool_turn"]) == 0
