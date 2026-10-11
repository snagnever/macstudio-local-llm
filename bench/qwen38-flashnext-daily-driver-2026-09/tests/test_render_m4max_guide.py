import json
import re
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


def test_payload_has_four_stacks_and_canonical_points():
    data, swift = load()
    p = guide.build_payload(data, swift)
    assert [s["id"] for s in p["stacks"]] == ["n2", "o1", "m1", "d1"]
    canon = {(g["cand"], g["context"]): g for g in data["groups"] if g["canonical"] and not g["refused"]}
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


def test_reread_tokens_follow_reuse():
    data, swift = load()
    pt = guide.build_payload(data, swift)["points"]["d1"]["524288"]
    assert pt["reread"] == round((1 - pt["reuse"]) * 524288)


def test_facts_match_data():
    data, swift = load()
    f = guide.facts(data, swift)
    assert f["mlx_turn_512"] == "13.0"
    assert f["mlx_turn_128"] == "8.8"
    assert f["mlx_cold_512_min"] == "13"
    assert f["mlx_resume_512"] == "3.9"


def test_render_has_no_placeholders_or_internal_terms():
    data, swift = load()
    html = guide.render(data, swift)
    assert "__" not in visible_text(html)
    assert not re.search(r"\{[a-z_0-9]+\}", visible_text(html))
    text = visible_text(html)
    for term in ("T_turn", "T_turno", "middle_mutation", "tool_turn", "n2", "n2q4", "o1", "m1", "m1x", "d1",
                 "gates?", "bands?"):
        assert not re.search(rf"\b{term}\b", text), term


def test_render_has_open_graph_card():
    data, swift = load()
    html = guide.render(data, swift)
    assert 'property="og:image" content="https://snagnever.github.io/macstudio-local-llm/assets/qwen38-flashnext-m4max-guide-card.png"' in html
    card = guide.render_card(data, swift)
    for s in guide.STACKS:
        assert s["short"] in card
    assert guide.facts(data, swift)["mlx_turn_512"] in card
    assert guide.CARD_PNG == REPO / "reports" / "assets" / "qwen38-flashnext-m4max-guide-card.png"


def test_post_image_has_the_four_charts_and_the_512k_bars():
    data, swift = load()
    post = guide.render_post(data, swift)
    for title in ("Agent turn time", "Time to first token on the next turn", "Decode speed", "Peak memory"):
        assert title in post
    # Only mlx-serve and ds4 serve 512K, so the cache-miss bars name those two.
    assert post.count("tokens prefilled again ·") == 2
    assert guide.POST_PNG == REPO / "reports" / "assets" / "qwen38-flashnext-m4max-guide-post.png"
