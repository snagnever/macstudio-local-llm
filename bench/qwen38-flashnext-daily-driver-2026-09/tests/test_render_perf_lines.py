import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_perf_lines  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def test_default_data_is_october_profile():
    # A página publicada é a de outubro; o default não pode reescrevê-la com o reports.json de setembro.
    assert render_perf_lines.REPORTS_JSON == REPO / "bench" / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
    assert render_perf_lines.REPORTS_JSON.is_file()
