import os, subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
NO_DRAFTER = (C / "results/mlx-serve-26102-no-drafter-flag.txt")


def _env():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "SPLASH_"))}


def _print(arm, ctx="32768", **extra):
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), arm, ctx, "--print"],
                         capture_output=True, text=True, env={**_env(), **extra})
    assert out.returncode == 0, f"{arm}: {out.stderr}"
    return out.stdout


def _server_line(text):
    lines = text.splitlines()
    i = next(i for i, l in enumerate(lines) if l.startswith("launcher:"))
    return lines[i + 1]


def test_unknown_arm_is_rejected():
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), "zz9", "32768", "--print"],
                         capture_output=True, text=True, env=_env())
    assert out.returncode == 64


def test_omlx_refit_arms_use_0711_and_new_packs():
    for arm, pack, letter in (("o27q8", "Jundot-Qwen3.8-27B-oQ8e-mtp-6c76ddfb82af", "T8R"),
                              ("o27q4", "Jundot-Qwen3.8-27B-oQ4e-mtp-49c1d60367d9", "T4R"),
                              ("o27sw", "scottlowry-Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc1914f65", "TSW")):
        out = _print(arm)
        assert f"run-omlx.sh {letter}" in out
        assert "omlx-v0.7.1.dev1/bin/omlx" in out
        assert pack in out


def test_mlx_serve_27b_arms_use_26102_and_ddalcu_pack():
    d = _print("r27d")
    assert "mlx-serve-v26.10.2/mlx-serve" in _server_line(d)
    assert "ddalcu-Qwen3.8-27B-MLX-Serve-8bit-7775059e955f" in _server_line(d)
    for flag in ("--prefix-cache-mem 16GB", "--prefix-cache-disk 100GB", "--prefix-cache-entries 64", "--mtp-max-depth 3"):
        assert flag in _server_line(d)
    assert "--ple-gpu" not in _server_line(d)
    assert "--kv-quant" not in _server_line(d)


def test_r27m_disables_the_bundled_drafter():
    flag = NO_DRAFTER.read_text().strip() if NO_DRAFTER.exists() else "NONE"
    m, d = _server_line(_print("r27m")), _server_line(_print("r27d"))
    if flag == "NONE":
        assert "-nodrafter" in m and "-nodrafter" not in d
    else:
        assert flag in m and flag not in d


def test_splash_arm_uses_tokenizer_path_and_port_8585():
    out = _print("k27")
    assert "run-splash.sh K" in out
    s = _server_line(out)
    assert "8585" in s and "mlx-community--Qwen3.8-27B-8bit-815b83c0" in s and "--idle-release off" in s
    assert "--tokenizer-path" in out


def test_llama_arms_flags():
    # Phases always pass FLASHNEXT_EFFORT; the driver default (xhigh) is covered by the next test.
    m = _server_line(_print("l27", "65536", FLASHNEXT_EFFORT="medium"))
    n = _server_line(_print("l27n", "65536", FLASHNEXT_EFFORT="medium"))
    for flag in ("-np 1", "--no-kv-unified", "-fa on", "-ngl 99", "-c 65536", "--jinja",
                 '"reasoning_effort":"medium"', "--alias qwen38-27b-gguf"):
        assert flag in m and flag in n
    assert "--spec-type draft-mtp" in m and "--spec-draft-n-max 2" in m and "mtp-Qwen3.8-27B-Q8_0.gguf" in m
    assert "--spec-type" not in n


def test_llama_effort_follows_env():
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), "l27", "65536", "--print"],
                         capture_output=True, text=True, env={**_env(), "FLASHNEXT_EFFORT": "xhigh"})
    assert '"reasoning_effort":"xhigh"' in _server_line(out.stdout)


@pytest.mark.skipif(not Path.home().joinpath('.local/opt/qwen38/mlx-dspark-v0.20.3/bin/mlx-dspark').exists(),
                    reason='mlx-dspark not installed (rig only)')
def test_reference_arm_s27r_still_prints():
    assert "run-mlx-dspark.sh S" in _print("s27r") and "--prefix-cache-rungs 1024" in _print("s27r")
