import json
import re
import sys
from pathlib import Path

import pytest

from conftest import HERE

sys.path.insert(0, str(HERE / "scripts"))
import render_page as R  # noqa: E402

ARMS = ("k2f", "k6f", "k1f", "k5f", "k8f", "k4f", "k3f")


@pytest.fixture(scope="module")
def data():
    return R.collect()


@pytest.fixture(scope="module")
def html(data):
    return R.render(data)


def _section(html, sid):
    return re.search(rf'<section[^>]*id="{sid}".*?</section>', html, re.S).group(0)


def _visible_text(html):
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# ---- collect(): pinned against etapaW1-fila.md and etapaW2-segunda-passada.md ----

def test_arm_order_and_packs(data):
    assert data["arms"] == list(ARMS)
    assert data["packs"]["k2f"]["repo"] == "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF"
    assert data["packs"]["k2f"]["variant"] == "IQ4_XS" and data["packs"]["k2f"]["rev"] == "0142554"
    assert data["packs"]["k6f"]["rev"] == "084c631" and data["packs"]["k1f"]["rev"] == "766911a"
    assert data["packs"]["k3f"]["variant"] == "IQ1_M"


def test_revisions_match_the_speed_test_records(data):
    # The pack table is static; the speed-test JSONL records the revision the server loaded.
    for a in ARMS:
        assert data["speed"][a]["model_revision"].startswith(data["packs"][a]["rev"]), a


def test_battery_totals_w1(data):
    totals = {a: data["battery"]["w1"][a]["total"] for a in ARMS}
    assert totals == {"k2f": 293, "k6f": 294, "k1f": 297, "k5f": 300, "k8f": 301, "k4f": 294, "k3f": 291}
    assert all(data["battery"]["w1"][a]["n"] == 336 for a in ARMS)


def test_battery_totals_w2(data):
    assert {a: data["battery"]["w2"][a]["total"] for a in ("k2f", "k6f")} == {"k2f": 302, "k6f": 304}


def test_battery_per_suite_k3f_gpqa(data):
    assert data["battery"]["w1"]["k3f"]["suites"]["gpqa"]["passed"] == 25
    assert data["battery"]["w1"]["k8f"]["suites"]["humaneval"]["passed"] == 156


def test_decode_p50(data):
    dec = {a: data["speed"][a]["decode_p50"] for a in ARMS}
    assert dec == {"k2f": 110.9, "k6f": 105.8, "k1f": 95.5, "k5f": 105.3, "k8f": 123.2, "k4f": 117.3, "k3f": 108.6}


def test_e2e_ram_and_speed_accuracy(data):
    sp = data["speed"]
    assert sp["k2f"]["e2e_p50_s"] == 12.0 and sp["k1f"]["e2e_p50_s"] == 31.1
    assert sp["k2f"]["ram_peak_gb"] == 116.6 and sp["k3f"]["ram_peak_gb"] == 79.7
    assert (sp["k8f"]["correct"], sp["k8f"]["n"]) == (10, 13)
    assert (sp["k4f"]["correct"], sp["k2f"]["correct"]) == (12, 13)


def test_tool_calls(data):
    tc = {a: (data["toolcalls"][a]["fp0"]["clean"], data["toolcalls"][a]["fp1"]["clean"]) for a in ARMS}
    assert tc == {"k2f": (20, 11), "k6f": (20, 7), "k1f": (20, 13), "k5f": (20, 8), "k8f": (20, 15),
                  "k4f": (18, 10), "k3f": (20, 9)}
    assert all(data["toolcalls"][a][p]["sessions"] == 20 for a in ARMS for p in ("fp0", "fp1"))


def test_tool_call_session_needs_every_turn(tmp_path):
    rows = []
    for sid, oks in (("s1", [True] * 5), ("s2", [True, False, True, True, True]), ("s3", [True, True, True])):
        rows += [{"session_id": sid, "record_type": "tool_turn", "correct": ok} for ok in oks[:-1]]
        rows.append({"session_id": sid, "record_type": "verdict", "correct": oks[-1], "turns_requested": 4})
    p = tmp_path / "x.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    # s3 stopped after 2 tool turns: it does not count, even with a correct verdict.
    assert R.tool_score(p) == {"sessions": 3, "clean": 1}


def test_token_ratios_vs_swift_w1(data):
    r = {a: (data["ratios"][a]["tokens"]["gpqa"], data["ratios"][a]["tokens"]["livecodebench"]) for a in ARMS[1:]}
    assert r == {"k6f": (1.37, 2.15), "k1f": (1.09, 1.83), "k5f": (1.31, 1.86), "k8f": (1.81, 1.91),
                 "k4f": (1.96, 3.05), "k3f": (7.75, 2.16)}


def test_time_ratios_match_the_w1_report(data):
    # etapaW1-fila.md divides the medians that summarize_ab prints (rounded to 0.1 s).
    t = {a: (data["ratios"][a]["time"]["gpqa"], data["ratios"][a]["time"]["livecodebench"]) for a in ARMS[1:]}
    assert t["k6f"] == (1.57, 2.59) and t["k1f"] == (1.29, 2.24) and t["k3f"] == (8.88, 2.26)


def test_token_spread_for_the_headline(data):
    assert (data["token_spread"]["min"], data["token_spread"]["max"]) == (1.09, 7.75)


def test_no_pack_is_a_candidate(data):
    c = data["candidate"]
    assert not any(c[a]["candidate"] for a in ARMS[1:])
    assert c["k8f"]["g1_fail"] == ["gpqa", "livecodebench"] and c["k3f"]["g1_fail"] == ["gpqa"]
    assert c["k6f"]["g1_fail"] == [] and c["k4f"]["g1_fail"] == []
    assert [a for a in ARMS[1:] if c[a]["tools_ok"]] == ["k1f", "k8f"]
    assert not any(c[a]["tokens_ok"] or c[a]["time_ok"] or c[a]["e2e_ok"] for a in ARMS[1:])


def test_pass_to_pass_noise(data):
    n = data["noise"]
    assert n["max_total_move"] == 10 and n["max_suite_move"] == 6
    assert (n["k2f_token_ratio"]["gpqa"], n["k2f_token_ratio"]["livecodebench"]) == (0.62, 1.13)
    assert (n["k6f_vs_k2f_w2"]["gpqa"], n["k6f_vs_k2f_w2"]["livecodebench"]) == (1.85, 1.79)
    assert n["sum_two_passes"] == {"k2f": 595, "k6f": 598}


def test_vendor_claims_numbers(data):
    v = data["claims"]
    assert v["v31_tokens_vs_base"] == {"gpqa": 26, "livecodebench": 18}  # percent more, k6f vs k1f
    assert v["v31_decode_vs_base"] == 11
    assert v["swift_tokens_vs_base"] == {"gpqa": -8, "livecodebench": -45}


def test_collect_is_json_serializable(data):
    assert json.loads(json.dumps(data))["battery"]["w1"]["k2f"]["total"] == 293


# ---- render() ----

SECTIONS = ("verdict", "packs", "tokens", "accuracy", "noise", "claims", "method", "commands")


def test_title_is_short(html):
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    assert title == "Flash-Next GGUF weights"
    assert 2 <= len(title.split()) <= 4


def test_render_has_every_section(html):
    for sid in SECTIONS:
        assert re.search(rf'<section[^>]*id="{sid}"', html), sid


def test_render_leaves_no_placeholder(html):
    assert not re.search(r"__[A-Z_]+__", html)


def test_no_external_requests_except_fonts(html):
    assert html.startswith("<!doctype html>")
    assert not re.search(r"<script[^>]+src=", html)
    assert not re.search(r"<img\b", html)
    assert not re.search(r"@import|url\(\s*['\"]?https?:", html)
    for tag in re.findall(r"<link\b[^>]*>", html):
        href = re.search(r'href="([^"]+)"', tag).group(1)
        assert href.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com")), href


def test_dark_mode_tokens(html):
    assert "@media (prefers-color-scheme: dark)" in html
    assert ':root:not([data-theme="light"])' in html and ':root[data-theme="dark"]' in html
    assert "background:var(--plane)" in html
    assert 'id="themeBtn"' in html


def test_page_is_small(html):
    assert len(html.encode("utf-8")) < 150_000


def test_headline_states_the_verdict(html):
    hero = _visible_text(_section(html, "verdict"))
    assert "Swift 1.5 IQ4_XS" in hero
    assert "1.09–7.75×" in hero
    assert "ThinkingCap" in hero


def test_packs_table_lists_every_pack(html):
    sec = _section(html, "packs")
    assert re.findall(r'<tr data-arm="(k\df)"', sec) == list(ARMS)
    assert "0142554" in sec and "084c631" in sec and "20 / 11" in sec and "18 / 10" in sec
    assert "110.9" in sec and "293" in sec


def test_tokens_chart_marks_the_candidate_line(html):
    sec = _section(html, "tokens")
    assert "<svg" in sec and "0.90" in sec
    assert sec.count('class="tbar') == 12  # 6 packs × GPQA and LiveCodeBench
    assert "7.75" in sec


def test_noise_section_numbers(html):
    text = _visible_text(_section(html, "noise"))
    assert "10 of 336" in text and "0.62–1.13×" in text
    assert "302" in text and "304" in text


def test_claims_section(html):
    text = _visible_text(_section(html, "claims"))
    for word in ("not confirmed", "confirmed", "partial", "not run", "+11%"):
        assert word in text, word


def test_commands_section_pins_the_swift_pack(html):
    text = _visible_text(_section(html, "commands"))
    assert "splash serve --model ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS" in text
    assert "--revision 0142554c963a8653912c0c8283f05f13f63653f3" in text
    assert "--max-context 262144" in text


def test_render_escapes_text(data):
    d = json.loads(json.dumps(data))
    d["packs"]["k2f"]["name"] = "<b>x</b>"
    out = R.render(d)
    assert "&lt;b&gt;x&lt;/b&gt;" in out and "<b>x</b>" not in out


def test_page_text_is_english(html):
    text = _visible_text(html)
    for word in ("passada", "braço", "questões", "não", "fila"):
        assert word not in text, word


def test_main_writes_json_and_html(tmp_path):
    out, js = tmp_path / "page.html", tmp_path / "page.json"
    assert R.main(["--out", str(out), "--json-out", str(js)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert json.loads(js.read_text(encoding="utf-8"))["battery"]["w2"]["k6f"]["total"] == 304


def test_main_data_reuses_json(tmp_path, data):
    js, out = tmp_path / "page.json", tmp_path / "page.html"
    js.write_text(json.dumps(data), encoding="utf-8")
    assert R.main(["--data", str(js), "--out", str(out), "--json-out", ""]) == 0
    assert 'id="accuracy"' in out.read_text(encoding="utf-8")


def test_method_notes_the_161_quality_recheck(html):
    # bench/splash161-2026-11 Task 6: the Swift 1.5 IQ4_XS scored 300 of 336 on Splash 1.6.1.
    method = _section(html, "method")
    assert "Splash 1.6.1" in method and "300 of 336" in method
    assert 'href="qwen38-flashnext-splash161.html"' in method
