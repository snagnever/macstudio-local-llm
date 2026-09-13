import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_hashes import compare  # noqa: E402


def test_compare_pairs_scenarios_by_name():
    a = [{"scenario": "cold", "repeat": 1, "greedy_tokens_hash": "h1"}, {"scenario": "identical", "repeat": 1, "greedy_tokens_hash": "h2"}]
    b = [{"scenario": "identical", "repeat": 1, "greedy_tokens_hash": "h2"}, {"scenario": "cold", "repeat": 1, "greedy_tokens_hash": "hX"}]
    rows = compare(a, b)
    assert rows == [
        {"scenario": "cold", "same": False, "hash_a": "h1", "hash_b": "hX"},
        {"scenario": "identical", "same": True, "hash_a": "h2", "hash_b": "h2"},
    ]
