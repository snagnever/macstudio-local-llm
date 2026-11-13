import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_perf_lines  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def test_default_data_is_october_profile():
    # A página publicada é a de outubro; o default não pode reescrevê-la com o reports.json de setembro.
    assert render_perf_lines.REPORTS_JSON == REPO / "bench" / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
    assert render_perf_lines.REPORTS_JSON.is_file()


def test_driver_labels_carry_their_dates():
    # The daily driver moved: n2 (iQ) until 2026-10-11, w1 (Swift 1.5 MLX) until 2026-11-12, then the k2 weights on
    # Splash 1.6.1 (bench/splash161-2026-11). The October table must not call two stacks "daily driver" today.
    import json
    data = json.loads(render_perf_lines.REPORTS_JSON.read_text(encoding="utf-8"))
    cfg = render_perf_lines.build_payload(data)["cfg"]
    assert cfg["n2"]["status"] == "daily driver until 2026-10-11"
    assert cfg["w1"]["status"] == "daily driver until 2026-11-12"
    assert cfg["k2"]["status"] == "daily driver since 2026-11-12, on Splash 1.6.1"
    assert not [k for k, v in cfg.items() if v["status"] == "daily driver"]
    takeaways = json.dumps(render_perf_lines.build_payload(data)["takeaways"])
    assert "(the daily driver)" not in takeaways and "(the daily driver until 2026-11-12)" in takeaways
