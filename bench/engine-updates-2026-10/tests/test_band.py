import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN_ARM = HERE / "scripts" / "run-arm.sh"
BAND = HERE / "scripts" / "run-band.sh"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "MTPLX_", "ENGINE_"))}
    env.update(extra or {})
    return env


def dry(part, ctx, extra=None):
    out = subprocess.run(["bash", str(BAND), part, ctx], capture_output=True, text=True,
                         env=_env({"ENGINE_BAND_DRY": "1", **(extra or {})}), check=True)
    return [l.split() for l in out.stdout.splitlines() if l.startswith("bash ")]


def test_band_order_flashnext_32k_without_d1():
    assert [c[2] for c in dry("fn", "32768")] == ["n2", "m1", "o1"]


def test_band_order_flashnext_128k_reversed_with_d1():
    assert [c[2] for c in dry("fn", "131072", {"ENGINE_D1": "1"})] == ["d1", "o1", "m1", "n2"]


def test_band_order_27b():
    assert [c[2] for c in dry("27b", "32768")] == ["r27", "m27", "o27", "s27"]
    assert [c[2] for c in dry("27b", "131072")] == ["s27", "o27", "m27", "r27"]


def test_band_uses_3_reps_and_part_tag():
    for cmd in dry("fn", "32768"):
        assert cmd[-4:] == ["--repeat", "3", "--tag", "fn"]
    for cmd in dry("27b", "32768"):
        assert cmd[-1] == "d27"


def test_band_rejects_other_ctx():
    r = subprocess.run(["bash", str(BAND), "fn", "262144"], capture_output=True, text=True,
                       env=_env({"ENGINE_BAND_DRY": "1"}))
    assert r.returncode == 64


def test_run_arm_names_by_tag():
    out = subprocess.run(["bash", str(RUN_ARM), "m1", "32768", "--tag", "fn", "--print"],
                         capture_output=True, text=True, env=_env(), check=True).stdout
    assert f"saida: {HERE}/results/m1-32768-t1.0-fn.jsonl" in out
