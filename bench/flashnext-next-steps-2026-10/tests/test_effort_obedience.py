import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

import effort_obedience  # noqa: E402

FACTOR = {"xhigh": 1.0, "medium": 0.6, "low": 0.4}


def _write(root: Path, arm: str, factors: dict[str, float], seed: int, n: int = 40):
    rng = random.Random(seed)
    base_len = [rng.randint(800, 8000) for _ in range(n)]
    for e, f in factors.items():
        for r in ("r1", "r2"):
            d = root / f"{arm}-{e}-{r}"
            d.mkdir(parents=True)
            rows = [{"dataset_idx": str(i), "reasoning_tokens": str(int(L * f * rng.uniform(0.8, 1.25))), "error": "None"}
                    for i, L in enumerate(base_len)]
            (d / "gpqa.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))


def test_same_behaviour_passes(tmp_path):
    _write(tmp_path, "w1", FACTOR, 1)
    _write(tmp_path, "w1t", FACTOR, 1)
    rc = effort_obedience.main(["--base-root", str(tmp_path), "--cand-root", str(tmp_path), "--suites", "gpqa"])
    assert rc == 0


def test_ignored_low_instruction_fails(tmp_path, capsys):
    _write(tmp_path, "w1", FACTOR, 1)
    _write(tmp_path, "w1t", dict(FACTOR, low=0.6), 1)  # low behaves like medium: the instruction had no effect
    rc = effort_obedience.main(["--base-root", str(tmp_path), "--cand-root", str(tmp_path), "--suites", "gpqa"])
    out = capsys.readouterr().out
    assert rc == 1 and "OBEDIENCE: fail" in out
    res = effort_obedience.analyse(tmp_path, tmp_path, "w1", "w1t", ["r1", "r2"], ["gpqa"], 0.223)
    assert math.exp(res["shift"]["low"]["mean"]) > 1.3
    assert abs(res["shift"]["medium"]["mean"]) < 0.1


def test_missing_round_is_an_error(tmp_path):
    _write(tmp_path, "w1", FACTOR, 1)
    assert effort_obedience.main(["--base-root", str(tmp_path), "--cand-root", str(tmp_path), "--cand", "w1x",
                                  "--suites", "gpqa"]) == 66


def test_errors_and_missing_tokens_are_skipped(tmp_path):
    d = tmp_path / "w1-xhigh-r1"
    d.mkdir()
    (d / "gpqa.jsonl").write_text(json.dumps({"dataset_idx": "1", "reasoning_tokens": "None", "completion_tokens": "None",
                                              "error": "None"}) + "\n" +
                                  json.dumps({"dataset_idx": "2", "reasoning_tokens": "100", "error": "timeout"}) + "\n" +
                                  json.dumps({"dataset_idx": "3", "reasoning_tokens": "None", "completion_tokens": "50",
                                              "error": "None"}) + "\n")
    assert effort_obedience.load(tmp_path, "w1", "xhigh", ["r1"], ["gpqa"]) == {"gpqa:3": math.log(50)}
