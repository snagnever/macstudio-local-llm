import json, re, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
sys.path.insert(0, str(C / "scripts"))
import render_27b_page as rp  # noqa: E402

REAL = (C / "results/gates.env").exists()
real_only = pytest.mark.skipif(not REAL, reason="campaign results not committed yet")


def _speed_rows(arm, ctx, tag, t_ttft_ms, dec, prompt=27302, cold_ms=76000.0):
    base = {"arm": arm, "context_target": ctx, "finish_reason": "stop", "error": None, "correct": True,
            "decode_tps": dec, "ttft_ms": t_ttft_ms, "cache_hit_ratio": 0.99, "swap_delta_gb": 0.0,
            "session_id": f"{arm}-{ctx}-{tag}", "runtime": "x", "ram_peak_gb": 40.0, "prompt_tokens": prompt,
            "temperature": 1.0, "top_p": 0.95, "top_k": 20}
    return [dict(base, scenario=s, ttft_ms=cold_ms if s == "cold" else t_ttft_ms)
            for s in ("cold", "identical", "append", "tool_turn")]


def _write_speed(d, arm, tag, ttft, dec, ctxs=(32768, 131072)):
    for ctx in ctxs:
        (d / f"{arm}-{ctx}-t1.0-{tag}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in _speed_rows(arm, ctx, tag, ttft, dec)) + "\n")


def _main(tmp, results, *extra):
    out = tmp / "page.html"
    args = ["--results", str(results), "--out", str(out), "--json-out", str(tmp / "pd.json"),
            "--card", str(tmp / "card.html"), "--post", str(tmp / "post.html"),
            "--reddit-out", str(tmp / "reddit.md"), *extra]
    assert rp.main(args) == 0
    return out.read_text()


@pytest.fixture
def results(tmp_path):
    d = tmp_path / "res"; d.mkdir()
    for arm, tag, ttft, dec in (("s27r", "p0x", 9700, 32.0), ("k27", "p1x", 2500, 60.0), ("k27", "p1m", 2400, 61.0)):
        _write_speed(d, arm, tag, ttft, dec)
    q = d / "q/t1/o27q4-medium"; q.mkdir(parents=True)
    (q / "gpqa.jsonl").write_text("\n".join(json.dumps({"question_num": i, "correct": i % 2 == 0, "finish_reason": "stop",
                                                        "elapsed_s": 20.0 + i, "completion_tokens": 1500, "reasoning_chars": 4000})
                                            for i in range(4)) + "\n")
    (d / "gates.env").write_text("P1_PASS=1\nP1_BEST=k27\nP5_GO=0\n")
    return d


@pytest.fixture(scope="module")
def real():
    p = rp.build_payload(C / "results", w1_summary=rp.load_w1_summary(), w1_ab=rp.load_w1_ab(),
                         n2_ab=rp.load_n2_ab(), ref_jsonl=rp.W1_JSONL)
    return p, rp.render_html(p)


def _outside_raw(html: str) -> str:
    """The page minus the <style> block and the closed raw-data appendix."""
    html = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    return re.sub(r'<details class="block raw".*?</details>', "", html, flags=re.S)


def _body(html: str) -> str:
    return html[html.index("<body>"):]


FORBIDDEN = [r"\bs27r\b", r"\bk27\b", r"\br27d\b", r"\bw1\b", r"\bn2\b", r"T_turno", r"\bP[0-8]\b", r"gates\.env",
             r"scope B", r"\bp\d[xm]\b", r"p&lt;N&gt;", r"(?i)\barms?\b", r"(?i)driver [AB]\b", r"(?i)\bbands?\b",
             r"\b[orwl]27\w*\b", r"tool_turn", r"NO-GO"]


# --- payload (unchanged data layer) ---

def test_payload_has_speed_per_effort_and_quality(results):
    p = rp.build_payload(results, w1_summary={"w1@32768": {"t_turno_s": 7.9}, "w1@131072": {"t_turno_s": 8.6}}, w1_ab=None)
    s = p["speed"]["131072"]
    assert set(s) == {"s27r-xhigh", "k27-xhigh", "k27-medium"}
    assert s["s27r-xhigh"]["t_turno_s"] == 25.7
    assert s["k27-medium"]["t_turno_s"] == round(2.4 + 512 / 61.0, 1)
    assert p["w1"]["131072"]["t_turno_s"] == 8.6
    assert p["quality"]["o27q4-medium"]["gpqa"]["passed"] == 2
    assert p["gates"]["P1_BEST"] == "k27"


def test_prefill_is_cold_prompt_tokens_over_cold_ttft(results):
    p = rp.build_payload(results, w1_summary={}, w1_ab=None)
    row = p["speed"]["32768"]["k27-xhigh"]
    assert row["prefill_tps"] == round(27302 / 76.0, 1)
    assert row["cold_prompt_tokens"] == 27302 and row["reps"] == 1


def test_prefill_missing_prompt_tokens_is_none(tmp_path):
    rows = _speed_rows("k27", 32768, "p1x", 2500, 60.0)
    for r in rows:
        r.pop("prompt_tokens")
    (tmp_path / "k27-32768-t1.0-p1x.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    p = rp.build_payload(tmp_path, w1_summary={}, w1_ab=None)
    assert p["speed"]["32768"]["k27-xhigh"]["prefill_tps"] is None
    html = rp.render_html(p)
    assert "Prefill (tok/s)" in html and "prompt tokens of the cold request" in html


def test_payload_json_written(results, tmp_path):
    _main(tmp_path, results, "--no-w1")
    d = json.loads((tmp_path / "pd.json").read_text())
    assert set(d) >= {"generated_at", "arms", "speed", "w1", "quality", "empty", "loops", "gates", "smoke", "think",
                      "funnel"}
    assert d["arms"][0] == {"id": "s27r", "name": d["arms"][0]["name"], "runtime": "mlx-dspark 0.20.3",
                            "pack": "mlx-community 8bit", "rev": "815b83c0", "port": 8484, "phase": "P0",
                            "public": "mlx-dspark 0.20.3 + DFlash2 (baseline)"}


def test_arms_table_ids_and_public_names():
    ids = [a[0] for a in rp.ARMS]
    assert ids == ["s27r", "k27", "o27q8", "o27q4", "r27d", "r27m", "w27d", "w27m", "o27sw", "l27", "l27n"]
    assert set(rp.PUBLIC) == set(ids)
    assert rp.PUBLIC["s27r"] == "mlx-dspark 0.20.3 + DFlash2 (baseline)"
    assert rp.PUBLIC["k27"] == "Splash 1.3.1 + DFlash2"
    assert rp.PUBLIC["r27d"] == "mlx-serve 26.10.2 + DFlash2"
    assert rp.W1_NAME == "Qwen3.8-Flash-Next · Swift 1.5 quant (our daily model)"
    assert rp.N2_NAME == "Qwen3.8-Flash-Next · ddalcu iQ quant"


def test_gate_doc_covers_p7_p8():
    for k in ("P7_PASS", "P8_PASS", "P7_SMOKE", "P8_SMOKE_w27m"):
        assert rp.GATE_DOC[k]


def test_loops_and_empty_answers(results):
    (results / "loops").mkdir()
    (results / "loops/q-o27q4-medium.jsonl").write_text("\n".join(json.dumps(r) for r in (
        {"prompt": "a", "degenerate": True}, {"prompt": "a", "degenerate": False},
        {"prompt": "b", "degenerate": False}, {"prompt": "b", "error": "boom"})) + "\n")
    q = results / "q/t1/o27q4-medium"
    (q / "if.jsonl").write_text("\n".join(json.dumps(r) for r in (
        {"id": "1", "passed": True, "finish_reason": "stop", "elapsed_s": 3.0, "raw_response": ""},
        {"id": "2", "passed": True, "finish_reason": "stop", "elapsed_s": 3.0, "raw_response": "ok"})) + "\n")
    p = rp.build_payload(results, w1_summary={}, w1_ab=None)
    assert p["loops"]["o27q4-medium"] == {"degenerate": 1, "total": 3}
    assert p["empty"]["o27q4-medium"]["empty"] == 1
    rp.render_html(p)


def test_empty_results_dir_renders_without_data(tmp_path):
    p = rp.build_payload(tmp_path, w1_summary={}, w1_ab=None)
    assert p["speed"] == {} and p["quality"] == {} and p["gates"] == {}
    html = rp.render_html(p)
    assert "not measured" in html and "Flash-Next" in html and "32K" in html and "128K" in html


# --- 1. language: no internal codes outside the raw-data appendix ---

@pytest.mark.parametrize("pat", FORBIDDEN)
def test_no_internal_codes_outside_appendix_fixture(results, pat):
    w1 = {"w1@32768": {"t_turno_s": 7.9}, "w1@131072": {"t_turno_s": 8.6},
          "n2@32768": {"t_turno_s": 8.1}, "n2@131072": {"t_turno_s": 8.9}}
    html = rp.render_html(rp.build_payload(results, w1_summary=w1, w1_ab=None))
    assert not re.search(pat, _outside_raw(html)), pat


@real_only
@pytest.mark.parametrize("pat", FORBIDDEN)
def test_no_internal_codes_outside_appendix_real(real, pat):
    m = re.search(pat, _outside_raw(real[1]))
    assert not m, (pat, _outside_raw(real[1])[max(0, m.start() - 80):m.end() + 80] if m else "")


@real_only
def test_appendix_is_closed_and_maps_codes(real):
    html = real[1]
    raw = html[html.index('<details class="block raw"'):]
    assert raw.startswith('<details class="block raw" id="raw"><summary>Raw data and reproduction</summary>')
    for a in rp.ARMS:
        assert f'<td class="code">{a[0]}</td><td>{rp.PUBLIC[a[0]]}</td>' in raw
    assert "P1_PASS" in raw and "P5_GO" in raw and "run-campaign.sh" in raw
    for a in ("o27q8", "o27q4", "o27sw", "w27d", "r27m", "w27m", "l27", "l27n"):
        assert f"<code>{a}</code>:" in raw


@real_only
def test_agent_turn_defined_at_first_mention_and_effort_wording(real):
    body = _body(real[1])
    i = body.index("agent turn time")
    assert "time to the first token of a turn that carries a tool result, plus 512 generated tokens" in body[i:i + 200]
    assert "thinking effort xhigh" in body and "thinking effort medium" in body
    assert "More effort means more reasoning tokens and lower draft acceptance, so a lower decode speed." in body


# --- 2. TL;DR and what we did not measure ---

@real_only
def test_tldr_numbers_from_real_data(real):
    p, html = real
    tl = html[html.index('id="tldr"'):html.index('id="glossary"')]
    assert "Fastest setup: Splash 1.3.1 + DFlash2" in tl and "8-bit" in tl
    assert "<b>17.7 s</b> at thinking effort xhigh" in tl and "<b>15.9 s</b> at thinking effort medium" in tl
    assert "<b>0.69×</b> the baseline" in tl
    assert "<b>~2×</b> Qwen3.8-Flash-Next" in tl and "2.06× at xhigh, 1.85× at medium" in tl
    assert "for agent loops, Flash-Next is still faster" in tl
    assert "What we did not measure" in tl
    assert "Quality of the 27B" in tl and "Time per real task" in tl and "8 of the 11 candidate setups" in tl
    assert "(5 never ran; 3 ran only the 8K smoke)" in tl
    sub = tl[tl.index('<ul class="nm-sub">'):]
    assert sub.count("<li>") == 8 and "<li>oMLX 0.7.1 · oQ4e refit, 4-bit (8K smoke only)</li>" in sub


def test_tldr_from_fixture_numbers(tmp_path):
    d = tmp_path / "r"; d.mkdir()
    for arm, tag, ttft, dec in (("s27r", "p0x", 9700, 32.3), ("k27", "p1x", 7400, 49.8), ("k27", "p1m", 7400, 60.5)):
        _write_speed(d, arm, tag, ttft, dec, ctxs=(131072,))
    w1 = {"w1@32768": {"t_turno_s": 7.9}, "w1@131072": {"t_turno_s": 8.6}}
    html = rp.render_html(rp.build_payload(d, w1_summary=w1, w1_ab=None))
    tl = html[html.index('id="tldr"'):html.index('id="glossary"')]
    assert "<b>17.7 s</b>" in tl and "<b>15.9 s</b>" in tl and "<b>0.69×</b>" in tl and "<b>~2×</b>" in tl


def test_tldr_without_data_says_not_measured(tmp_path):
    html = rp.render_html(rp.build_payload(tmp_path, w1_summary={}, w1_ab=None))
    tl = html[html.index('id="tldr"'):html.index('id="glossary"')]
    assert "were not measured" in tl and "Fastest setup" not in tl


# --- 3. glossary ---

def test_glossary_terms(results):
    html = rp.render_html(rp.build_payload(results, w1_summary={}, w1_ab=None))
    g = html[html.index('id="glossary"'):html.index('id="funnel"')]
    for term in ("TTFT", "Cold vs warm", "Prefill (prompt processing)", "Decode (token generation)",
                 "Prefix cache and hit rate", "Context 32K / 128K", "Draft model (DFlash2) and speculative decoding",
                 "MTP", "Thinking effort"):
        assert f"<dt>{term}</dt>" in g


# --- 4. funnel ---

@real_only
def test_funnel_counts_and_classes(real):
    p, html = real
    assert [s["count"] for s in p["funnel"]] == [11, 5, 3, 1]
    assert p["funnel"][0]["runtimes"] == ["mlx-dspark", "Splash", "oMLX", "mlx-serve", "llama.cpp"]
    sec = html[html.index('id="funnel"'):html.index('id="results"')]
    assert "How 11 candidate setups came down to Splash</h2>" in sec and "down to 0" not in html
    svg = sec[sec.index('<svg class="funnel"'):sec.index("</svg>")]
    for label in ("candidate setups", "8K smoke test (decode)", "full speed test at 32K and 128K",
                  "fastest: Splash 1.3.1 + DFlash2"):
        assert label in svg
    assert "within 1.25" not in svg and "Flash-Next" not in svg
    lines = re.findall(r'<text class="fn-det"[^>]*>([^<]*)</text>', svg)
    assert " ".join(lines).startswith("5 runtimes: mlx-dspark, Splash, oMLX, mlx-serve, llama.cpp")
    assert svg.count('class="fn-sw cut"') == 8 and svg.count('class="fn-sw fail"') == 1
    assert svg.count('class="fn-sw ref"') == 1 and svg.count('class="fn-sw keep"') == 4  # smoke 2, full 1, final 1
    # smoke decode: summarize_driver definition (median of identical, append, tool_turn), kept and cut
    for v in ("92.3", "80.6", "81.4", "51.5", "35.3"):
        assert f"decode {v} tok/s at 8K" in svg
    for v in ("17.0 / 25.7 s per agent turn", "13.3 / 17.7 s per agent turn", "19.9 / 44.7 s per agent turn",
              "decode 44.0 / 32.3 tok/s", "decode 54.7 / 49.8 tok/s", "decode 36.3 / 15.1 tok/s",
              "1.17× / 1.74× the baseline", "0.78× / 0.69× the baseline"):
        assert v in svg, v
    final = svg[svg.index("fastest: Splash"):]
    assert "13.3 / 17.7 s per agent turn" in final and "decode 54.7 / 49.8 tok/s" in final
    side = sec[sec.index('class="fn-side"'):]
    assert "cut by scope (not measured)" in side and "failed a measurement" in side
    assert "3 of them ran the 8K smoke first and were not taken further after it" in side
    assert "2 of those decoded slower than every setup that went on (under 80.6 tok/s)" in side
    assert "median of the identical, append and tool-turn requests at 8K" in side
    assert "not because they failed" not in sec
    assert "<script" not in svg


@real_only
def test_funnel_text_fits_viewbox(real):
    """At 375 px the figure is ~329 px wide: the SVG must be ≤ 360 units wide and its smallest text ≥ 13.5 units
    (≥ 12 px on screen); wrapped lines stay under the character budget."""
    html = real[1]
    svg = html[html.index('<svg class="funnel"'):]
    svg = svg[:svg.index("</svg>")]
    assert 'viewBox="0 0 360 ' in svg
    css = html[html.index("<style>"):html.index("</style>")]
    sizes = [float(x) for x in re.findall(r"\.fn-(?:lab|det|grp|name|note|n|n0)\{[^}]*font-size:([\d.]+)px", css)]
    assert sizes and min(sizes) >= 13.5
    for t in re.findall(r'<text class="fn-(?:note|det|name[^"]*)"[^>]*>([^<]*)</text>', svg):
        assert len(t) <= 44, t


def test_funnel_without_smoke_files(results):
    p = rp.build_payload(results, w1_summary={}, w1_ab=None)
    assert [s["count"] for s in p["funnel"]] == [11, 0, 2, 1]
    assert '<svg class="funnel"' in rp.render_html(p)


# --- 5. controls ---

@real_only
def test_controls_and_effort_rows(real):
    html = real[1]
    assert '<input type="checkbox" data-effort-toggle="xhigh" checked>' in html
    assert '<input type="checkbox" data-effort-toggle="medium"> medium' in html  # xhigh only by default
    assert "data-ref-toggle checked> show Flash-Next reference" in html
    assert 'data-ctx="32768" aria-selected="false">32K context' in html
    assert 'data-ctx="131072" aria-selected="true">128K context' in html
    assert 'class="ctx-panel tab-off" data-ctx-panel="32768"' in html  # default state rendered: 128K
    assert 'class="ctx-panel" data-ctx-panel="131072"' in html
    assert html.count('data-effort="xhigh"') >= 6 and html.count('data-effort="medium"') >= 6
    assert 'data-ref="flashnext"' in html
    assert "localStorage" in html and "try{ localStorage.setItem" in html
    # baseline medium at 128K: shown as not measured, never dropped
    panel = html[html.index('data-ctx-panel="131072"'):]
    panel = panel[:panel.index("</table>")]
    nm = re.findall(r'<div class="sbar nm off" data-effort="medium" title="([^"]+)"', panel)
    assert nm == ["mlx-dspark 0.20.3 + DFlash2 (baseline) · thinking effort: medium · 128K: not measured"]
    assert re.search(r'<tr data-effort="medium" class="off"><td>.*?\(baseline\).*?not measured</span></td></tr>', panel)
    assert 'const DEF_EFF={"xhigh": true, "medium": false}' in html


def test_default_state_is_xhigh_only_without_js(results):
    html = rp.render_html(rp.build_payload(results, w1_summary={}, w1_ab=None))
    assert "html.js .tab-off{display:none}" in html and "html.js .controls{display:flex}" in html
    assert ".off{display:none!important}" in html
    med = re.findall(r'<(?:div|tr) [^>]*data-effort="medium"[^>]*>', html)
    xh = re.findall(r'<(?:div|tr) [^>]*data-effort="xhigh"[^>]*>', html)
    assert med and all("off" in t for t in med)
    assert xh and not any("off" in t for t in xh)
    assert "Only thinking effort xhigh shows by default" in html


# --- 6. stacked bars ---

@real_only
def test_stacked_bar_segments_and_tooltip(real):
    html = real[1]
    panel = html[html.index('data-ctx-panel="131072"'):]
    m = re.search(r'<div class="sbar" data-effort="xhigh" title="(Splash 1\.3\.1 \+ DFlash2[^"]+)"', panel)
    tip = m.group(1)
    for part in ("agent turn time 17.7 s", "warm TTFT (tool turn) 7.4 s", "decode 49.8 tok/s", "cold TTFT 535.1 s",
                 "peak memory 53.8 GB"):
        assert part in tip
    bar = panel[m.start():panel.index("</div>", m.start())]
    assert 'class="seg ttft"' in bar and 'class="seg gen"' in bar and 'aria-label="' in bar


# --- 7. data fixes ---

@real_only
def test_removed_sections_and_wording(real):
    html = real[1]
    for gone in ("Time per task", "Tokens per answer", "Accuracy", "Wired peak", "do not report cached tokens",
                 "does not report cached tokens"):
        assert gone not in html
    assert "Quality and per-task time were not measured for the 27B." in html
    assert "<th>Peak memory (GB)</th>" in html and "highest wired memory of the whole machine" in html
    assert "<th>Prefill (tok/s)</th>" in html
    panel = html[html.index('data-ctx-panel="32768"'):]
    row = re.search(r'<tr data-effort="xhigh"><td>.*?Splash 1\.3\.1.*?</tr>', panel).group(0)
    assert "<td>358</td>" in row and "<td>0.96</td>" in row  # Splash reports cached tokens: hit 0.96


# --- 8. run it yourself ---

@real_only
def test_run_it_yourself(real):
    html = real[1]
    run = html[html.index('id="run"'):html.index('id="hw"')]
    for s in ("mlx-community/Qwen3.8-27B-8bit", "815b83c0", "815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9",
              "incoai/Qwen3.8-27B-DFlash2", "dedf8df6", "--max-context 131072", "--draft-model",
              "--idle-release off --language-only --no-webui --offline", "--port 8585", "int8",
              "temperature 1.0, top_p 0.95, top_k 20"):
        assert s in run, s
    assert "HTTP 400</b> on every tool turn that sent the previous <code>reasoning_content</code> back (6 of 6" in run
    assert "3 of 3 worked" not in run and "6 of 6 worked, with a TTFT of 7.4 s" in run
    assert 'DRAFT_DIR=&quot;$HOME/models/Qwen3.8-27B-DFlash2&quot;' in run and '--draft-model &quot;$DRAFT_DIR&quot;' in run
    assert ".cache/local-llms" not in run and "qwen3.8-prefix-cache" not in run


def test_splash_command_parsed_from_launchers():
    c = rp.splash_command()
    assert c["model"] == "mlx-community/Qwen3.8-27B-8bit"
    assert c["revision"].startswith("815b83c0") and c["draft_rev"].startswith("dedf8df6")
    assert c["draft_repo"] == "incoai/Qwen3.8-27B-DFlash2" and c["port"] == "8585"


# --- 9-10. hardware, limitations ---

@real_only
def test_hardware_and_limitations(real):
    html = real[1]
    hw = html[html.index('id="hw"'):html.index('id="limits"')]
    assert "M4 Max, 128 GB" in hw and "macOS 26.6.2" in hw and "3 repetitions" in hw
    for v in ("mlx-dspark 0.20.3", "Splash 1.3.1", "mlx-serve 26.10.2", "mlx-serve 26.10.1"):
        assert v in hw
    lim = html[html.index('id="limits"'):html.index('id="raw"')]
    assert "+44% at 32K, +33% at 128K" in lim and "vendor" in lim
    assert "94–104 s (one request per mode, resend and drop)" in lim and "10.8 s in the cache probe" in lim
    assert "One machine" in lim and "synthetic" in lim and "Quality was not measured" in lim


# --- 11. Reddit post, card, og tags, --png ---

@real_only
def test_reddit_post_and_assets(tmp_path):
    html = _main(tmp_path, C / "results")
    md = (tmp_path / "reddit.md").read_text()
    assert md.startswith("# Dense Qwen3.8-27B on an M4 Max 128 GB")
    assert "https://snagnever.github.io/macstudio-local-llm/qwen38-27b-stacks.html" in md
    assert "| Splash 1.3.1 + DFlash2 | medium | 10.4 s | 15.9 s |" in md
    assert "| mlx-dspark 0.20.3 + DFlash2 (baseline) | medium | 13.5 s | not measured |" in md
    assert "| mlx-serve 26.10.2 + DFlash2 | xhigh | 19.9 s | 44.7 s |" in md
    assert "**Limitations.**" in md and "HTTP 400 (6/6)" in md
    assert not re.search(r"\b(s27r|k27|r27d|w1|n2|T_turno)\b", md)
    for tag in ('property="og:title"', 'property="og:description"',
                'property="og:image" content="https://snagnever.github.io/macstudio-local-llm/assets/qwen38-27b-stacks-card.png"'):
        assert tag in html
    card = (tmp_path / "card.html").read_text()
    assert "width:1200px; height:630px" in card and "17.7" in card
    post = (tmp_path / "post.html").read_text()
    assert '<svg class="funnel"' in post and "TL;DR" in post and 'class="sbar"' in post


def test_png_flag_renders_card_and_post(results, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(rp, "write_png", lambda page, png, size=(1200, 630), scale=1: calls.append((page.name, size)) or True)
    _main(tmp_path, results, "--no-w1", "--png")
    assert calls == [("card.html", (1200, 630)), ("post.html", (rp.POST_W, rp.POST_H))]


def test_no_w1_drops_both_references(results, tmp_path):
    html = _main(tmp_path, results, "--no-w1")
    d = json.loads((tmp_path / "pd.json").read_text())
    assert d["w1"]["32768"]["t_turno_s"] is None and d["n2"]["32768"]["t_turno_s"] is None
    body = _outside_raw(_body(html))  # the appendix code table still lists the reference names
    assert rp.W1_NAME not in body and rp.N2_NAME not in body and 'data-ref="flashnext"' not in body


def test_references_rows_and_limit(results):
    w1 = {"w1@32768": {"t_turno_s": 7.9, "decode_tps": 84.6, "warm_ttft_s": {"tool_turn": 1.8}},
          "w1@131072": {"t_turno_s": 8.6, "decode_tps": 76.7, "warm_ttft_s": {"tool_turn": 1.9}},
          "n2@32768": {"t_turno_s": 8.1, "decode_tps": 82.3, "warm_ttft_s": {"tool_turn": 1.8}},
          "n2@131072": {"t_turno_s": 8.9, "decode_tps": 73.2, "warm_ttft_s": {"tool_turn": 1.9}}}
    html = rp.render_html(rp.build_payload(results, w1_summary=w1, w1_ab=None))
    body = _body(html)
    assert body.count(rp.W1_NAME) >= 4 and body.count(rp.N2_NAME) >= 4  # bars + tables, both contexts
    assert "10.1 s" not in body and "11.1 s" not in body  # never 1.25 × the iQ reference


def test_bar_key_does_not_promise_tap(results):
    html = rp.render_html(rp.build_payload(results, w1_summary={}, w1_ab=None))
    assert "hover or tap" not in html and "the table below has the same numbers" in html


def test_missing_drop_probe_and_draft_repo_do_not_crash(results, tmp_path, monkeypatch):
    think = results / "think"; think.mkdir()
    rows = [{"mode": "resend", "scenario": "tool_turn", "error": "HTTPError: HTTP Error 400: Bad Request", "ttft_ms": None},
            {"mode": "drop", "scenario": "tool_turn", "error": "HTTPError: HTTP Error 500", "ttft_ms": None}]
    (think / "k27-xhigh.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    real_cmd = rp.splash_command()
    monkeypatch.setattr(rp, "splash_command", lambda: dict(real_cmd, draft_repo=None, draft_rev=None))
    html = _main(tmp_path, results, "--no-w1")
    run = html[html.index('id="run"'):html.index('id="hw"')]
    assert "None" not in run and "HTTP 400" in run and "0 of 1 worked." in run
    assert "<li>Draft: —</li>" in run
    md = (tmp_path / "reddit.md").read_text()
    assert "None" not in md and "0/1 worked." in md


# --- 12. mobile ---

def test_tables_scroll_inside_container(results):
    html = rp.render_html(rp.build_payload(results, w1_summary={}, w1_ab=None))
    for t in re.findall(r"(.{30})<table", html):
        assert t.endswith('<div class="tbl-scroll">')
    assert "@media (max-width:620px)" in html


@real_only
def test_index_card_uses_public_wording():
    idx = (ROOT / "reports/index.html").read_text()
    i = idx.index('href="qwen38-27b-stacks.html"')
    card = idx[i:idx.index("</a>", i)]
    assert "T_turno" not in card and "agent turn" in card
