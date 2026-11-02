import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_matrix as M  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def visible_text(html: str) -> str:
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


@pytest.fixture(scope="module")
def payload():
    return M.collect()


@pytest.fixture(scope="module")
def html(payload):
    return M.render(payload)


def test_out_path_and_sources():
    assert M.OUT == REPO / "reports" / "qwen38-flashnext-base-vs-swift.html"
    assert M.REPORTS_JSON == REPO / "bench" / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
    assert M.SPLASH == REPO / "bench" / "splash-longctx-2026-10" / "results"


def test_cells_are_the_four_model_engine_combinations():
    assert [c["id"] for c in M.CELLS] == ["bm", "sm", "bs", "ss"]
    assert {(c["model"], c["engine"]) for c in M.CELLS} == {
        ("base", "mlx-serve"), ("swift", "mlx-serve"), ("base", "splash"), ("swift", "splash")}


def test_mlx_serve_quality_pair_counts(payload):
    q = payload["quality"]["mlx"]["t1"]
    assert q["bm"]["gpqa"]["passed"] == 45 and q["sm"]["gpqa"]["passed"] == 43
    assert q["bm"]["humaneval"]["with_imports"] == 158 and q["sm"]["humaneval"]["with_imports"] == 158


def test_swift_engine_pair_counts(payload):
    q = payload["quality"]["swift262"]
    assert q["sm"]["livecodebench"]["passed"] == 47 and q["ss"]["livecodebench"]["passed"] == 47
    assert q["ss"]["humaneval"]["with_imports"] == 158
    assert q["ss"]["humaneval"]["with_imports_r2"] == 159


def test_base_on_splash_quality_is_not_measured(payload, html):
    q = payload["quality"]["splash262"]
    assert q["bs"] is None
    assert q["ss"]["gpqa"]["passed"] == 41
    cov = payload["coverage"]
    assert cov["bs"]["battery"]["measured"] is False
    assert cov["ss"]["battery"]["measured"] is True
    assert "not measured" in visible_text(html)


def test_speed_series_per_cell(payload):
    sp = payload["speed"]
    assert [p["ctx"] for p in sp["ss"]] == [8192, 32768, 131072, 262144, 524288, 1000000]
    assert [p["ctx"] for p in sp["bs"]] == [8192, 32768, 131072, 262144, 524288, 1000000]
    assert sp["ss"][3]["t_turno_s"] == 6.57 and sp["bs"][3]["t_turno_s"] == 6.98
    mlx = {p["ctx"]: p for p in sp["sm"]}
    assert mlx[262144]["t_turno_s"] == 9.23 and mlx[524288]["t_turno_s"] == 12.69
    assert mlx[1000000]["absent"] and "PrefillDoesNotFit" in mlx[1000000]["absent"]
    base = {p["ctx"]: p for p in sp["bm"]}
    assert base[262144]["t_turno_s"] == 11.91


def test_mcnemar_exact():
    assert M.mcnemar_exact(4, 5) == pytest.approx(1.0)
    assert M.mcnemar_exact(0, 0) == 1.0
    assert M.mcnemar_exact(10, 0) < 0.01


def test_terminal_bench_pair(payload):
    tb = payload["tbench"]
    assert tb["sm"]["passed"] == 58 and tb["ss"]["passed"] == 57
    assert tb["pair"]["only_sm"] == 5 and tb["pair"]["only_ss"] == 4 and tb["pair"]["both"] == 53
    assert tb["pair"]["p"] == 1.0
    assert tb["bm"] is None and tb["bs"] is None


def test_effort_rows(payload):
    e = payload["effort"]
    assert e["bm"]["xhigh"]["gpqa"]["passed"] == 45
    assert e["bm"]["medium"]["gpqa"]["passed"] == 41
    assert e["sm"]["low"]["rounds"] == 2
    # e3d LCB rows carry the old grader; the regrade of the next-steps campaign applies (42 and 41 → 41.5)
    assert e["sm"]["low"]["livecodebench"]["passed"] == 41.5
    assert e["bs"] is None and e["ss"] is None


def test_claude_code_alone_times(payload):
    cc = payload["claude_code"]
    assert cc["ss"]["alone_s"]["c"] == pytest.approx(162.8)
    assert cc["sm"]["alone_s"]["d"] == pytest.approx(303.35)
    assert cc["bm"] is None


def test_longctx_counts_only_question_records(payload):
    rows = {(r["server"], r["band"]): r for r in payload["longctx"]["sm"]}
    assert rows[(262144, 262144)] == {"arm": "w1z", "server": 262144, "band": 262144, "n": 8, "correct": 8}
    ss = {(r["server"], r["band"]): r for r in payload["longctx"]["ss"]}
    assert ss[(1000000, 131072)]["correct"] == 7 and ss[(1000000, 1000000)]["correct"] == 8
    assert payload["longctx"]["bs"] is None


def test_toolcall_sessions_from_verdicts_and_turns_from_tool_turns(payload):
    tc = payload["toolcall"]
    assert tc["sm"]["fp0"] == {"sessions": 20, "sessions_ok": 20, "turns": 80, "turns_ok": 80}
    assert tc["sm"]["fp1"]["sessions_ok"] == 14
    assert tc["ss"]["fp1"] == {"sessions": 20, "sessions_ok": 13, "turns": 64, "turns_ok": 58}
    assert tc["bs"] is None


def test_page_sections_and_cell_names(html):
    for sid in ("tiles", "grid", "accuracy", "time", "effort", "speed", "cache", "memory", "agent",
                "longctx", "coverage", "method"):
        assert f'id="{sid}"' in html, sid
    text = visible_text(html)
    assert "Qwen3.8-Flash-Next" in text and "Swift 1.5" in text and "Splash" in text and "mlx-serve" in text


def test_page_is_self_contained(html):
    assert "<script src=" not in html
    assert "<!doctype html>" in html.lower()
    assert "/*__CSS__*/" not in html and ".tiles4{" in html  # the stylesheet is inlined, not left as the placeholder


def test_bar_rows_share_one_track_width(html):
    # a fixed value column: equal values draw equal bars whatever the label text beside them
    assert ".bline{display:grid; grid-template-columns:var(--lw,150px) 1fr var(--vw,230px);" in html
    assert "minmax(110px,auto)" not in html
    assert 'style="--lw:215px;--vw:72px"' in html  # the accuracy panels: the run label moves to the row label
