import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from attach_memory import attach_memory  # noqa: E402


def test_attach_fills_peak_and_swap_delta():
    records = [{"run_id": "a", "ram_peak_gb": None, "swap_delta_gb": None}]
    samples = [
        {"t": 1, "wired_gb": 70.0, "free_gb": 30.0, "swap_used_gb": 1.7},
        {"t": 6, "wired_gb": 105.2, "free_gb": 0.4, "swap_used_gb": 1.7},
        {"t": 11, "wired_gb": 90.0, "free_gb": 5.0, "swap_used_gb": 2.2},
    ]
    out = attach_memory(records, samples)
    assert out[0]["ram_peak_gb"] == 105.2
    assert out[0]["swap_delta_gb"] == 0.5
    assert out[0]["mem_free_min_gb"] == 0.4


def test_attach_without_samples_keeps_null():
    out = attach_memory([{"run_id": "a", "ram_peak_gb": None, "swap_delta_gb": None}], [])
    assert out[0]["ram_peak_gb"] is None
