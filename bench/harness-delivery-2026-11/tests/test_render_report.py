import re
import shutil

import pytest

import render_report as rr
from conftest import HERE

REPO = HERE.parents[1]
SWIFT = REPO / "bench/swift-uncensored-2026-11/results"
PAGE = REPO / "reports/qwen38-flashnext-harness-delivery.html"


@pytest.fixture(scope="module")
def data():
    return rr.collect()


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# ---- Task 1: collect

def test_collect_counts_match_the_summary(data):
    assert data["sessions"] == {"total": 112, "done": 105}
    assert {h["name"]: h["done"] for h in data["harness"]} == {"pi": 27, "claude": 27, "dsh": 26, "opencode": 25}
    assert all(h["n"] == 28 for h in data["harness"])
    res = data["reserva"]
    assert (res["done_base"], res["done_cand"], res["pass"]) == (54, 51, True)


def test_collect_has_one_cause_per_failed_session(data):
    assert len(data["failures"]) == 7 and all(f["cause"] for f in data["failures"])


def test_collect_refuses_an_incomplete_matrix(tmp_path):
    shutil.copytree(HERE / "results/sessions", tmp_path / "sessions")
    (tmp_path / "sessions/k2-pi-a-r1.json").unlink()
    with pytest.raises(ValueError, match="k2-pi-a-r1"):
        rr.collect(delivery_results=tmp_path)


def test_refusal_counts_recomputed_from_jsonl(data):
    r = data["refusal"]
    assert r[("k2h", "advbench")] == {"refused": 96, "empty": 1, "complied": 3, "n": 100}
    assert r[("z4h", "jbb")] == {"refused": 0, "empty": 4, "complied": 96, "n": 100}


def test_speed_constants_match_the_stage_report(data):
    md = (SWIFT / "etapa2-um-stream.md").read_text()
    ctx = {"32K": 32768, "128K": 131072, "256K": 262144}
    seen = 0
    for line in md.splitlines():
        m = re.match(r"\| `(\w+)` \| (\d+K) \| ([\d.]+) s \|.*?\| ([\d.]+) \| \d+ \| ([\d.]+) GB \|", line)
        if m:
            arm, c, t, decode, wired = m.group(1), ctx[m.group(2)], float(m.group(3)), float(m.group(4)), float(m.group(5))
            got = data["speed"][arm][c]
            assert (got["t_turn_s"], got["decode_tps"], got["wired_gb"]) == (t, decode, wired)
            seen += 1
        m = re.match(r"\| `(\w+)` \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| \*\*(\w+)\*\*", line)
        if m:
            arm = m.group(1)
            assert [data["speed"][arm][c]["ratio"] for c in ctx.values()] == [float(m.group(i)) for i in (2, 3, 4)]
            assert data["speed_verdict"][arm] == {"passa": "pass", "falha": "fail"}[m.group(5)]
            seen += 1
    assert seen == 15
    assert data["speed"]["z4h"][131072]["ratio"] == 1.051
    assert data["speed_verdict"] == {"z4h": "fail", "z2h": "fail", "z3h": "pass"}
