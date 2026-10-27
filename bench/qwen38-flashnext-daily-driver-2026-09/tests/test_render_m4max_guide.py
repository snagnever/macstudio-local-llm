import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_m4max_guide as guide  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def load():
    data = json.loads(guide.REPORTS_JSON.read_text(encoding="utf-8"))
    swift = json.loads(guide.SWIFT_JSON.read_text(encoding="utf-8"))
    return data, swift


def visible_text(html: str) -> str:
    # The page text without scripts, styles and tags: what a reader sees.
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<pre.*?</pre>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def test_default_sources_exist():
    assert guide.REPORTS_JSON == REPO / "bench" / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
    assert guide.SWIFT_JSON == REPO / "bench" / "swift15-flashnext-2026-10" / "results" / "page-data.json"
    assert guide.OUT == REPO / "reports" / "qwen38-flashnext-m4max-guide.html"
    assert guide.REPORTS_JSON.is_file() and guide.SWIFT_JSON.is_file()


def test_payload_has_six_stacks_and_canonical_points():
    data, swift = load()
    data = guide.page_data(data)
    p = guide.build_payload(data, swift)
    # The four servers of the October round, then Swift 1.5 on mlx-serve 26.10.3 and on Splash 1.4.0.
    assert [s["id"] for s in p["stacks"]] == ["n2", "o1", "m1", "d1", "w1", "k2"]
    assert p["ctx"][-1] == 1000000
    ids = {s["id"] for s in p["stacks"]}
    canon = {(g["cand"], g["context"]): g for g in data["groups"]
             if g["canonical"] and not g["refused"] and g["cand"] in ids}
    for (cid, ctx), g in canon.items():
        pt = p["points"][cid][str(ctx)]
        assert pt["turn"] == g["t_turno_s"]
        assert pt["resume"] == g["ttft_s"]["tool_turn"]
        assert pt["cold"] == g["cold_ttft_s"]
        for sc in g["scenarios_run"]:
            assert pt["hits"][sc] == (g["hit"][sc] if sc in g["scenarios_served"] else None)
    # Refused or unsupported bands carry a reason, never a number.
    assert "reason" in p["points"]["m1"]["262144"]
    assert "reason" in p["points"]["o1"]["524288"]
    # Every stack × size shows a number or the reason it has none: 1M ran only on Splash.
    for st in p["stacks"]:
        for ctx in p["ctx"]:
            assert str(ctx) in p["points"][st["id"]], (st["id"], ctx)
    assert p["points"]["k2"]["1000000"]["turn"] > 0
    assert "PrefillDoesNotFit" in p["points"]["w1"]["1000000"]["reason"]
    assert len({s["cv"] for s in p["stacks"]}) == len(p["stacks"])
    assert len({s["marker"] for s in p["stacks"]}) == len(p["stacks"])


def test_js_labels_1m_and_draws_every_marker():
    assert 'c >= 1000000 ? (c / 1000000) + "M"' in guide.JS
    for s in guide.STACKS:
        assert f'shape === "{s["marker"]}"' in guide.JS or s["marker"] == "circle", s["marker"]


def test_splash_command_matches_the_launcher():
    # The page shows the 1M profile of tools/scripts/serve-flashnext-splash.sh with the binary named splash.
    out = subprocess.run(["bash", str(REPO / "tools" / "scripts" / "serve-flashnext-splash.sh"), "1m", "--print"],
                         capture_output=True, text=True, check=True).stdout.split()
    assert out[1] == "serve"
    shown = guide.SPLASH_COMMAND.replace("\\\n", " ").split()
    assert shown == ["splash"] + out[1:]
    assert guide.SPLASH_COMMAND in guide.render(*load())


def test_splash_facts_and_quality():
    data, swift = load()
    f = guide.facts(data, swift)
    assert f["splash_turn_512"] == "6.7" and f["splash_turn_1m"] == "9.3"
    assert f["swift_mlx_turn_512"] == "12.7"
    assert f["splash_cold_1m_min"] == "25.5"
    html = guide.render(data, swift)
    assert 'id="splash"' in html and "incoai/splash/issues/387" in html
    # Terminal-Bench 2.1 is not ready: the page carries no number or placeholder for it.
    assert "Terminal-Bench" not in html and "TB2" not in html
    rows = {r[0]: r for r in guide.SPLASH_QUALITY}
    assert rows["HumanEval (164)"][1:] == ("142/164", "147/164 · 151/164", "147/164", "142/164 · 148/164")


def test_reread_tokens_follow_reuse():
    data, swift = load()
    pt = guide.build_payload(data, swift)["points"]["d1"]["524288"]
    assert pt["reread"] == round((1 - pt["reuse"]) * 524288)


def test_facts_match_data():
    data, swift = load()
    # The October round (post, slides, post charts): the iQ pack on mlx-serve 26.10.1.
    f = guide.facts(data, swift)
    assert f["mlx_turn_512"] == "13.0"
    assert f["mlx_turn_128"] == "8.8"
    assert f["mlx_cold_512_min"] == "13"
    assert f["mlx_resume_512"] == "3.9"
    # The page: the same pack on mlx-serve 26.10.3, the build of the Swift 1.5 stack.
    f = guide.facts(guide.page_data(data), swift)
    assert f["mlx_turn_512"] == "14.5" and f["mlx_turn_128"] == "8.9"


def test_page_runs_the_iq_pack_on_26103_and_the_post_keeps_the_october_round():
    data, swift = load()
    assert guide.STACK["n2"]["name"] == "mlx-serve 26.10.3"
    assert "mlx-serve 26.10.1" not in guide.stacks_table()
    text = re.sub(r"\s+", " ", visible_text(guide.render(data, swift)))
    assert "Use mlx-serve 26.10.3 with the ddalcu iQ-MLX 4.7 bpw quant" in text
    assert "Use mlx-serve 26.10.1" not in text
    post = guide.render_post(data, swift)
    assert "mlx-serve 26.10.1" in post and "mlx-serve 26.10.3" not in post


def test_render_has_no_placeholders_or_internal_terms():
    data, swift = load()
    html = guide.render(data, swift)
    assert "__" not in visible_text(html)
    assert not re.search(r"\{[a-z_0-9]+\}", visible_text(html))
    text = visible_text(html)
    for term in ("T_turn", "T_turno", "middle_mutation", "tool_turn", "n2", "n2q4", "o1", "m1", "m1x", "d1",
                 "w1", "w1z", "w1zq4", "k2", "k2a", "k3ma", "g1", "g2", "folga", "gates?", "bands?"):
        assert not re.search(rf"\b{term}\b", text), term


def test_render_has_open_graph_card():
    data, swift = load()
    html = guide.render(data, swift)
    assert 'property="og:image" content="https://snagnever.github.io/macstudio-local-llm/assets/qwen38-flashnext-m4max-guide-card.png"' in html
    card = guide.render_card(data, swift)
    for s in guide.STACKS:
        assert s["short"] in card
    assert guide.facts(guide.page_data(data), swift)["mlx_turn_512"] in card
    assert guide.CARD_PNG == REPO / "reports" / "assets" / "qwen38-flashnext-m4max-guide-card.png"


def test_post_image_has_the_four_charts_and_the_512k_bars():
    data, swift = load()
    post = guide.render_post(data, swift)
    for title in ("Agent turn time", "Time to first token on the next turn", "Decode speed", "Peak memory"):
        assert title in post
    # The post image is the October round: four servers, 8K to 512K. Only mlx-serve and ds4 serve 512K, so the
    # cache-miss bars name those two.
    assert post.count("tokens prefilled again ·") == 2
    assert "Splash" not in post and "1M" not in post
    assert guide.POST_PNG == REPO / "reports" / "assets" / "qwen38-flashnext-m4max-guide-post.png"


def test_slides_are_numbered_and_filled():
    data, swift = load()
    slides = guide.render_slides(data, swift)
    assert [s[0][:2] for s in slides] == [f"{i:02d}" for i in range(1, len(slides) + 1)]
    for i, (stem, html) in enumerate(slides, 1):
        assert f"{i} / {len(slides)}" in html
        assert not re.search(r"\{[a-z_0-9]+\}", visible_text(html)), stem
    assert "Use mlx-serve 26.10.1" in slides[-1][1]


def test_post_charts_are_charts_not_prose():
    data, swift = load()
    charts = {stem: html for stem, html, _h in guide.render_post_charts(data, swift)}
    assert list(charts) == ["01-turn", "02-first-message", "03-ttft-next-turn", "04-cache-miss", "05-decode-prefill", "06-memory"]
    p = guide.build_payload(data, swift)["points"]
    n256, d256 = p["n2"]["262144"], p["d1"]["262144"]
    first = visible_text(charts["02-first-message"])
    assert f'{n256["cold"] / 60:.1f} min' in first and f'{n256["resume"]:.1f} s' in first
    miss = visible_text(charts["04-cache-miss"])
    assert f'{d256["reuse"] * 100:.1f}% hit' in miss
    # No heading, read line or callout: the post text carries the prose.
    for html in charts.values():
        assert "<h2" not in html and 'class="read"' not in html and 'class="callout"' not in html


def test_quality_has_livecodebench_and_no_mtplx_value():
    data, swift = load()
    rows = {r["id"]: r for r in guide.build_payload(data, swift)["quality"]}
    assert "livecodebench" in dict(guide.QUALITY_SUITES)
    # mlx-serve: the regraded Swift A/B t1 run; oMLX: the regraded o1x run of e5; MTPLX: not measured.
    assert rows["n2"]["livecodebench"] == [45, 50]
    assert rows["o1"]["livecodebench"] == [45, 50]
    assert rows["m1"]["livecodebench"] is None
    assert "not measured" in guide.render(data, swift)


def test_same_build_table_puts_iq_and_swift_on_26103():
    # The iQ pack on 26.10.3 (series n3, t6 of splash-longctx) next to Swift 1.5 on the same build and iQ on 26.10.1.
    data, swift = load()
    canon = guide.canonical(data)
    table = guide.same_build_table(guide.page_data(data))
    for h in ("iQ-MLX 4.7 bpw · mlx-serve 26.10.1", "iQ-MLX 4.7 bpw · mlx-serve 26.10.3", "Swift 1.5 · mlx-serve 26.10.3"):
        assert h in table
    for cid in ("n2", "n3", "w1"):
        for ctx in guide.ROUND_CTX:
            assert f'{canon[(cid, ctx)]["t_turno_s"]:.1f} s' in table, (cid, ctx)
    html = guide.render(data, swift)
    assert table in html
    text = visible_text(html)
    assert "mlx-serve stops at 512K" not in text and "PrefillDoesNotFit" in text
