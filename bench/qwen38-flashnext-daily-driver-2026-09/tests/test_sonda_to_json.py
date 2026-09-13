from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sonda_to_json as sj  # noqa: E402
import render_dashboard as rd  # noqa: E402


def probe_rec(cand, scen, ttft_s=5.0, decode=70.0, wired=95.0, correct=True, error=None,
              runtime_revision="v26.9.2-yarn2.0-kv8"):
    return {
        "arm": cand, "context_target": 524288, "scenario": scen,
        "ttft_ms": ttft_s * 1000, "decode_tps": decode, "ram_peak_gb": wired,
        "correct": correct, "error": error, "runtime_revision": runtime_revision,
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_success_case(tmp_path):
    write_jsonl(
        tmp_path / "c1-524288-t1.0-yarn2.jsonl",
        [
            probe_rec("c1", "cold", ttft_s=8.0, decode=72.3, wired=101.2),
            probe_rec("c1", "identical", ttft_s=0.2, decode=71.0, wired=103.9),
        ],
    )
    by_cand = sj.load_records(str(tmp_path), sj.DEFAULT_GLOB)
    sonda = sj.convert(by_cand, [])
    row = sonda["c1"]
    assert row["reaches"] is True
    assert row["followup"] is True
    assert row["decode_tps"] == 72.3
    assert row["cold_ttft_s"] == 8.0
    assert row["wired_peak_gb"] == 103.9  # max across both records
    assert row["mechanism"] == "v26.9.2-yarn2.0-kv8"
    assert row["note"] == ""


def test_followup_refused(tmp_path):
    write_jsonl(
        tmp_path / "c2-524288-t1.0-yarn2.jsonl",
        [
            probe_rec("c2", "cold", ttft_s=9.0, decode=60.0),
            probe_rec("c2", "identical", correct=False, error="server refused the follow-up request"),
        ],
    )
    by_cand = sj.load_records(str(tmp_path), sj.DEFAULT_GLOB)
    sonda = sj.convert(by_cand, [])
    row = sonda["c2"]
    assert row["reaches"] is True
    assert row["followup"] is False
    assert row["note"] == "follow-up recusado"


def test_cold_missing(tmp_path):
    write_jsonl(
        tmp_path / "c3-524288-t1.0-yarn2.jsonl",
        [probe_rec("c3", "identical", ttft_s=0.3, decode=50.0)],
    )
    by_cand = sj.load_records(str(tmp_path), sj.DEFAULT_GLOB)
    sonda = sj.convert(by_cand, [])
    row = sonda["c3"]
    assert row["reaches"] is False
    assert row["followup"] is None
    assert row["note"] == "sem registro cold (recusa ou crash; ver boot log)"


def test_cold_refused_note_truncated(tmp_path):
    long_error = "connection reset by peer " * 10  # > 160 chars
    write_jsonl(
        tmp_path / "c4-524288-t1.0-yarn2.jsonl",
        [probe_rec("c4", "cold", correct=False, error=long_error)],
    )
    by_cand = sj.load_records(str(tmp_path), sj.DEFAULT_GLOB)
    sonda = sj.convert(by_cand, [])
    row = sonda["c4"]
    assert row["reaches"] is False
    assert len(row["note"]) <= 160
    assert row["note"] == sj._truncate(long_error)


def test_no_yarn_ids_without_a_probe_file(tmp_path):
    # No probe files at all for c2/c3 in this results dir.
    by_cand = sj.load_records(str(tmp_path), sj.DEFAULT_GLOB)
    sonda = sj.convert(by_cand, ["c2", "c3"])
    assert sonda["c2"] == {
        "reaches": False,
        "followup": None,
        "note": "runtime sem YaRN (oMLX): teto 262K",
    }
    assert sonda["c3"] == {
        "reaches": False,
        "followup": None,
        "note": "runtime sem YaRN (oMLX): teto 262K",
    }


def test_no_yarn_id_with_existing_probe_file_is_not_overridden(tmp_path):
    write_jsonl(
        tmp_path / "c2-524288-t1.0-yarn2.jsonl",
        [probe_rec("c2", "cold", ttft_s=3.0, decode=40.0)],
    )
    by_cand = sj.load_records(str(tmp_path), sj.DEFAULT_GLOB)
    sonda = sj.convert(by_cand, ["c2"])
    assert sonda["c2"]["reaches"] is True
    assert sonda["c2"]["note"] != "runtime sem YaRN (oMLX): teto 262K"


def test_main_writes_json(tmp_path):
    write_jsonl(
        tmp_path / "c1-524288-t1.0-yarn2.jsonl",
        [probe_rec("c1", "cold"), probe_rec("c1", "identical")],
    )
    out_path = tmp_path / "sonda-512k.json"
    rc = sj.main(["--results-dir", str(tmp_path), "--out", str(out_path)])
    assert rc == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["c1"]["reaches"] is True


def test_integration_feeds_render_dashboard(tmp_path):
    """The converter's output must be exactly what render_dashboard.py's
    --sonda expects: no exception, and the sonda values land in the page's
    embedded SONDA data untouched."""
    write_jsonl(
        tmp_path / "c1-524288-t1.0-yarn2.jsonl",
        [probe_rec("c1", "cold", ttft_s=8.0, decode=72.3), probe_rec("c1", "identical")],
    )
    sonda_path = tmp_path / "sonda-512k.json"
    rc = sj.main(["--results-dir", str(tmp_path), "--out", str(sonda_path)])
    assert rc == 0

    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({}), encoding="utf-8")
    out_path = tmp_path / "out.html"
    rc = rd.main(
        ["--summary", str(summary_path), "--sonda", str(sonda_path), "--out", str(out_path)]
    )
    assert rc == 0

    page = out_path.read_text(encoding="utf-8")
    m = re.search(r"const SONDA = (\{.*?\});\n", page, re.S)
    assert m, "const SONDA not found in generated HTML"
    sonda = json.loads(m.group(1))
    assert sonda["c1"]["reaches"] is True
    assert sonda["c1"]["decode_tps"] == 72.3
    assert sonda["c1"]["cold_ttft_s"] == 8.0
