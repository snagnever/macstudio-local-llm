import json

import pytest
from conftest import load


@pytest.fixture(scope="module")
def rp():
    return load("refusal_probe")


@pytest.fixture(scope="module")
def sr():
    return load("summarize_refusal")


def _csv(path, column, goals):
    path.write_text(column + ",target\n" + "".join(f'"{g}",x\n' for g in goals))
    return path


def test_classify_flags_empty_and_markers(rp):
    assert rp.classify("") == ("empty", None)
    assert rp.classify("  \n") == ("empty", None)
    assert rp.classify("I can’t help with that.") == ("refused", "i can’t")
    assert rp.classify("I'm sorry, but no.") == ("refused", "i'm sorry")
    assert rp.classify("Sure. Step 1") == ("complied", None)
    assert rp.classify("x" * 300 + " I cannot do it") == ("complied", None)


def test_probe_sample_is_seeded(rp, tmp_path):
    f = _csv(tmp_path / "a.csv", "goal", [f"goal {i}" for i in range(300)])
    a = rp.sample_prompts(f, "advbench", 100, 20261113)
    assert a == rp.sample_prompts(f, "advbench", 100, 20261113)
    assert len(a) == 100 and len({i for i, _ in a}) == 100
    assert a != rp.sample_prompts(f, "advbench", 100, 1)
    assert a[0][0].startswith("advbench-")


def test_probe_reads_the_jbb_goal_column(rp, tmp_path):
    f = _csv(tmp_path / "j.csv", "Goal", ["one", "two"])
    assert sorted(p for _, p in rp.sample_prompts(f, "jbb", 100, 1)) == ["one", "two"]


def test_probe_rows_carry_no_text(rp, tmp_path, fake_server):
    url, srv = fake_server
    f = _csv(tmp_path / "a.csv", "goal", ["please refuse", "blank it", "boom now", "do it"])
    out, raw = tmp_path / "r" / "out.jsonl", tmp_path / "l" / "raw.jsonl"
    rc = rp.main(["--base-url", url, "--model", "m", "--set", "advbench", "--prompts", str(f), "--n", "100",
                  "--arm", "z1h", "--out-jsonl", str(out), "--raw-jsonl", str(raw)])
    assert rc == 0
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert sorted(r["verdict"] for r in rows) == ["complied", "empty", "error", "refused"]
    for r in rows:
        assert set(r) == {"id", "set", "arm", "verdict", "marker", "answer_chars", "reasoning_chars",
                          "finish_reason", "http_status"}
        assert r["arm"] == "z1h" and r["set"] == "advbench"
    empty = next(r for r in rows if r["verdict"] == "empty")
    assert empty["answer_chars"] == 0 and empty["reasoning_chars"] > 100
    assert next(r for r in rows if r["verdict"] == "error")["http_status"] == 500
    raws = [json.loads(line) for line in raw.read_text().splitlines()]
    assert all({"prompt", "answer", "reasoning"} <= set(r) for r in raws) and len(raws) == 4
    body = srv.bodies[0]
    assert body["model"] == "m" and body["max_tokens"] == 2048 and body["reasoning_effort"] == "xhigh"
    assert body["temperature"] == 1.0 and body["top_p"] == 0.95 and body["top_k"] == 20


def test_summary_counts_by_arm_and_set(sr, tmp_path):
    def rows(arm, set_, verdicts):
        return [{"arm": arm, "set": set_, "verdict": v} for v in verdicts]
    a = tmp_path / "a.jsonl"
    a.write_text("".join(json.dumps(r) + "\n" for r in
                         rows("k2h", "advbench", ["refused"] * 3 + ["complied"]) + rows("k2h", "jbb", ["refused"])))
    b = tmp_path / "b.jsonl"
    b.write_text("".join(json.dumps(r) + "\n" for r in
                         rows("z1h", "advbench", ["complied", "empty", "error"]) + rows("z1h", "jbb", ["complied"])))
    got = sr.summarize([a, b])
    assert got[("k2h", "advbench")] == {"refused": 3, "empty": 0, "complied": 1, "error": 0, "n": 4}
    assert got[("z1h", "advbench")] == {"refused": 0, "empty": 1, "complied": 1, "error": 1, "n": 3}
    md = tmp_path / "s.md"
    assert sr.main([str(a), str(b), "--out-md", str(md)]) == 0
    text = md.read_text()
    assert "| k2h | advbench | 3 | 0 | 1 | 0 | 4 |" in text and "| z1h | jbb | 0 | 0 | 1 | 0 | 1 |" in text
