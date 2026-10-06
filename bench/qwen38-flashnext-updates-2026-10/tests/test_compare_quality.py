import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_quality import load, compare, markdown  # noqa: E402


def write(tmp_path, name, rows):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p


def test_load_last_occurrence_wins(tmp_path):
    p1 = write(tmp_path, "a1.jsonl", [{"question_num": 1, "correct": False}])
    p2 = write(tmp_path, "a2.jsonl", [{"question_num": 1, "correct": True}])
    assert load([p1, p2], "question_num", "correct") == {1: True}


def test_load_skips_rows_without_key_or_field(tmp_path):
    p = write(tmp_path, "a.jsonl", [{"question_num": 1}, {"correct": True}, {"question_num": 2, "correct": True}])
    assert load([p], "question_num", "correct") == {2: True}


def test_compare_counts_and_discordant():
    a = {1: True, 2: True, 3: False, 4: True}
    b = {1: True, 2: False, 3: True, 5: True}
    c = compare(a, b)
    assert c["n"] == 3
    assert c["pass_a"] == 2 and c["pass_b"] == 2
    assert c["only_a"] == [2] and c["only_b"] == [3]
    assert c["missing_a"] == [5] and c["missing_b"] == [4]


def test_markdown_reports_delta():
    c = compare({1: True, 2: True}, {1: True, 2: False})
    md = markdown("HumanEval", "n1", "n2", c)
    assert "## HumanEval" in md
    assert "| n1 | 2/2 |" in md and "| n2 | 1/2 |" in md
    assert "n2 − n1: **-1**" in md
    assert "só n1 passa: 2" in md
