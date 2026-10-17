import importlib.util
import math
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "render_effort_tail_page.py"
spec = importlib.util.spec_from_file_location("render_effort_tail_page", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

pytestmark = pytest.mark.skipif(not (mod.SWIFT_RES / "ab" / "t1" / "n2" / "gpqa.jsonl").exists(),
                                reason="Swift campaign results missing")


@pytest.fixture(scope="module")
def battery():
    return mod.load_battery()


def test_counts_match_the_stage_writeups(battery):
    # etapa11: GPQA xhigh 85 -> 85 over 2 rounds; LCB regraded 94 -> 94; truncations 4 -> 7.
    w1 = {s: mod.summary(battery["w1"]["xhigh"][s]) for s in mod.SUITES}
    w1t = {s: mod.summary(battery["w1t"]["xhigh"][s]) for s in mod.SUITES}
    assert (w1["gpqa"]["correct"], w1t["gpqa"]["correct"]) == (85, 85)
    assert (w1["livecodebench"]["correct"], w1t["livecodebench"]["correct"]) == (94, 94)
    assert sum(v["trunc"] for v in w1.values()) == 4
    assert sum(v["trunc"] for v in w1t.values()) == 7
    # etapa15: GPQA xhigh 45 -> 42, LCB 45 -> 46 (n2 control regraded 41 -> 45).
    assert mod.summary(battery["n2"]["xhigh"]["gpqa"])["correct"] == 45
    assert mod.summary(battery["n2t"]["xhigh"]["gpqa"])["correct"] == 42
    assert mod.summary(battery["n2"]["xhigh"]["livecodebench"])["correct"] == 45
    assert mod.summary(battery["n2t"]["xhigh"]["livecodebench"])["correct"] == 46


def test_regrade_applies_to_the_old_runner_only(battery):
    # e3d-lcb-regrade.md: w1-low-r1 26/50 original -> 42/50 regraded; w1-low-r2 25 -> 41.
    assert mod.summary(battery["w1"]["low"]["livecodebench"])["correct"] == 83
    # The n2 medium and low runs come from bench2 at 2403125 and are not regraded (etapa15: 44 and 40).
    assert mod.summary(battery["n2"]["medium"]["livecodebench"])["correct"] == 44
    assert mod.summary(battery["n2"]["low"]["livecodebench"])["correct"] == 40


def test_obedience_factors_match_the_writeup():
    ob = mod.load_obedience()
    assert math.exp(ob["swift"]["shift"]["low"]["mean"]) == pytest.approx(0.90, abs=0.005)
    # Shifts are log units; factors are ratios.
    assert ob["iq"]["factor"]["n2"]["low"]["mean"] == pytest.approx(0.26, abs=0.005)
    assert ob["swift"]["factor"]["w1"]["low"]["mean"] == pytest.approx(0.45, abs=0.005)


def test_page_renders_every_section(tmp_path):
    html = mod.render()
    for sec in ("templates", "switch", "short", "obedience", "levels", "per-question", "options", "numbers", "setup", "limits"):
        assert f'id="{sec}"' in html
    assert html.count('<figure class="strip"') == 2 + 2 * len(mod.SUITES) * len(mod.EFFORTS)
    assert "167" in html and "53 → 0" in html
    assert "<svg" in html and "chart.js" not in html.lower()
