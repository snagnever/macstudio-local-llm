from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_dashboard as rd  # noqa: E402

CANDIDATE_IDS = ["c1", "c2", "c3", "c4"]


def _row(t_turno_s=5.0, cold_ttft_s=30.0, decode=64.0, hit=0.96, wired=90.0, warnings=None):
    return {
        "cold_ttft_s": cold_ttft_s,
        "warm_ttft_s": {"identical": 0.1, "append": 1.9, "tool_turn": 2.0},
        "hit": {"identical": 1.0, "append": hit, "tool_turn": hit},
        "prefill_tps": 700.0,
        "decode_tps": decode,
        "t_turno_s": t_turno_s,
        "correctness": "ok",
        "wired_peak_gb": wired,
        "swap_delta_gb": 0.0,
        "mtp_acceptance": 0.8,
        "errors": 0,
        "n": 1,
        "gates_failed": [] if hit >= 0.90 else ["hit_append<0.90"],
        "warnings": warnings if warnings is not None else [],
    }


def _extract_const_array(html: str, name: str):
    m = re.search(r"const " + name + r" = (\[.*?\]);\n", html, re.S)
    assert m, f"const {name} not found in generated HTML"
    return json.loads(m.group(1))


def test_generated_page_has_data_model_and_placeholder_verdict(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps({"c1@32768": _row(t_turno_s=5.0), "c2@32768": _row(t_turno_s=6.0)}),
        encoding="utf-8",
    )
    out_path = tmp_path / "qwen38-flashnext-driver.html"

    rc = rd.main(["--summary", str(summary_path), "--out", str(out_path)])
    assert rc == 0

    page = out_path.read_text(encoding="utf-8")
    assert "const MODELS" in page
    assert "const RESULTS" in page
    for cid in CANDIDATE_IDS:
        assert f'"{cid}"' in page
    assert 'charts-common.js' in page
    assert rd.PLACEHOLDER_VERDICT in page

    results = _extract_const_array(page, "RESULTS")
    rec = next(
        r for r in results if r["model"] == "c1" and r["metric"] == "t_turno_s" and r["context"] == 32768
    )
    assert rec["value"] == 5.0


def test_summary_b_overrides_matching_key(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({"c1@32768": _row(t_turno_s=5.0)}), encoding="utf-8")
    summary_b_path = tmp_path / "summary-b.json"
    summary_b_path.write_text(json.dumps({"c1@32768": _row(t_turno_s=4.2)}), encoding="utf-8")
    out_path = tmp_path / "out.html"

    rc = rd.main(
        [
            "--summary",
            str(summary_path),
            "--summary-b",
            str(summary_b_path),
            "--out",
            str(out_path),
        ]
    )
    assert rc == 0

    page = out_path.read_text(encoding="utf-8")
    results = _extract_const_array(page, "RESULTS")
    rec = next(
        r for r in results if r["model"] == "c1" and r["metric"] == "t_turno_s" and r["context"] == 32768
    )
    assert rec["value"] == 4.2


def test_merge_summaries_override_wins_whole_record():
    base = {"c1@32768": {"t_turno_s": 5.0}, "c1@8192": {"t_turno_s": 1.0}}
    override = {"c1@32768": {"t_turno_s": 4.2}}
    merged = rd.merge_summaries(base, override)
    assert merged["c1@32768"] == {"t_turno_s": 4.2}
    assert merged["c1@8192"] == {"t_turno_s": 1.0}


def test_build_results_missing_context_yields_null_value():
    summary = {"c1@32768": _row(t_turno_s=5.0)}
    del summary["c1@32768"]["wired_peak_gb"]
    rows = rd.build_results(summary)
    rec = next(r for r in rows if r["model"] == "c1" and r["metric"] == "wired_peak_gb")
    assert rec["value"] is None


def test_render_verdict_html_placeholder_when_absent():
    assert rd.PLACEHOLDER_VERDICT in rd.render_verdict_html(None)


def test_render_verdict_html_renders_paragraphs(tmp_path):
    md = tmp_path / "verdict.md"
    md.write_text("Primeiro parágrafo.\n\nSegundo parágrafo com <tag> e & escapado.", encoding="utf-8")
    out = rd.render_verdict_html(str(md))
    assert out.count("<p>") == 2
    assert "Primeiro parágrafo." in out
    assert "&lt;tag&gt;" in out
    assert "&amp;" in out


def test_sonda_note_with_script_breakout_is_escaped(tmp_path):
    """A free-text sonda `note` quoting "</script>" must not be able to close
    the page's inline <script> tag early — see finding 1, review round 1."""
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({"c1@32768": _row()}), encoding="utf-8")
    sonda_path = tmp_path / "sonda.json"
    malicious_note = "x</script><script>alert(1)</script>"
    sonda_path.write_text(
        json.dumps(
            {
                "c1": {
                    "reaches": True,
                    "followup": True,
                    "decode_tps": 10.0,
                    "cold_ttft_s": 5.0,
                    "note": malicious_note,
                }
            }
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "out.html"

    rc = rd.main(
        ["--summary", str(summary_path), "--sonda", str(sonda_path), "--out", str(out_path)]
    )
    assert rc == 0

    page = out_path.read_text(encoding="utf-8")
    assert "</script><script>alert" not in page
    # Exactly the 3 CDN `<script src=...>` tags plus the one inline <script>
    # block close with `</script>` in the static template — nothing extra
    # sneaked in from embedded JSON data.
    assert page.count("</script>") == 4

    m = re.search(r"const SONDA = (\{.*?\});\n", page, re.S)
    assert m, "const SONDA not found in generated HTML"
    sonda = json.loads(m.group(1))
    assert sonda["c1"]["note"] == malicious_note


def test_wired_warning_shown_separately_from_gates(tmp_path):
    """The wired>102 ruling: a candidate with no failed gates but a wired
    warning must carry that warning in GATES[...]['warnings'], never inside
    GATES[...]['gates'] — the scoreboard's gates-falhados cell must read
    "passa" for this row, and the warning must show up in its own alertas
    column/data instead."""
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps({"c1@131072": _row(wired=106.35, warnings=["wired>102"])}),
        encoding="utf-8",
    )
    out_path = tmp_path / "out.html"
    rc = rd.main(["--summary", str(summary_path), "--out", str(out_path)])
    assert rc == 0

    page = out_path.read_text(encoding="utf-8")
    m = re.search(r"const GATES = (\{.*?\});\n", page, re.S)
    assert m, "const GATES not found in generated HTML"
    gates = json.loads(m.group(1))
    entry = gates["c1@131072"]
    assert entry["gates"] == []
    assert entry["warnings"] == ["wired>102"]
    assert "wired>102" in page  # present in the embedded page data

    # The scoreboard has its own "alertas" column/JS path, separate from the
    # gates-falhados one, and must not conflate the two.
    assert "alertas" in page
    assert "warningsCell" in page
    assert "gatesCell" in page


def test_scoreboard_default_sort_and_direction_aware_highlight(tmp_path):
    """Finding 2, review round 1: the scoreboard must default-sort ascending
    on T_turno@32K (column index 1) and highlight the best cell per column
    with the correct direction (min for time/memory, max for decode) instead
    of the shared helper's always-max semantics."""
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({"c1@32768": _row()}), encoding="utf-8")
    out_path = tmp_path / "out.html"
    rc = rd.main(["--summary", str(summary_path), "--out", str(out_path)])
    assert rc == 0

    page = out_path.read_text(encoding="utf-8")
    assert "C.setupSortableTable('scoreboardDriver', 1, 1)" in page
    assert "SCOREBOARD_DIRECTIONS" in page
    assert "1:'min'" in page
    assert "4:'max'" in page
    assert "highlightScoreboardBest" in page
    # highlightBestPerColumn (always max-is-best) must not be wired onto this
    # scoreboard — that would mis-highlight the slowest T_turno as "best".
    assert "highlightBestPerColumn('scoreboardDriver')" not in page
