import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from attach_mtp import parse_spec_stats, attach_mtp  # noqa: E402


LOG_TWO_STATS = """
[boot] loading model...
  [spec-stats] mode=mtp attempts=23 accepts=44 avg_per_round=1.91 per_draft_pct=53.2% depth=6 drafted=88 ext_rounds=13 partial_rounds=0 runtime_disabled=false reason=none
[server] request served
  [spec-stats] mode=mtp attempts=23 accepts=88 avg_per_round=3.83 per_draft_pct=100.0% depth=6 drafted=88 ext_rounds=13 partial_rounds=0 runtime_disabled=false reason=none
[server] shutting down
"""

LOG_NO_STATS = """
[boot] loading model...
[server] request served
[server] shutting down
"""


def test_parse_takes_last_spec_stats():
    stats = parse_spec_stats(LOG_TWO_STATS)
    assert stats is not None
    assert stats["mtp_acceptance"] == 1.0
    assert stats["mtp_depth"] == 6
    assert stats["mtp_avg_per_round"] == 3.83
    assert stats["mtp_mode"] == "mtp"


def test_parse_returns_none_without_stats():
    assert parse_spec_stats(LOG_NO_STATS) is None


def test_attach_does_not_overwrite_existing():
    records = [{"run_id": "a", "mtp_acceptance": 0.9}]
    stats = {"mtp_acceptance": 1.0, "mtp_avg_per_round": 3.83, "mtp_depth": 6, "mtp_mode": "mtp"}
    out = attach_mtp(records, stats)
    assert out[0]["mtp_acceptance"] == 0.9
    assert out[0]["mtp_depth"] == 6
    assert out[0]["mtp_avg_per_round"] == 3.83
    assert out[0]["mtp_mode"] == "mtp"


def test_attach_fills_null():
    records = [{"run_id": "a", "mtp_acceptance": None}]
    stats = {"mtp_acceptance": 0.532, "mtp_avg_per_round": 1.91, "mtp_depth": 6, "mtp_mode": "mtp"}
    out = attach_mtp(records, stats)
    assert out[0]["mtp_acceptance"] == 0.532
    assert out[0]["mtp_depth"] == 6
