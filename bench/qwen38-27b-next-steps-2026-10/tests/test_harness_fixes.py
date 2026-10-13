import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
FN = ROOT / "bench/flashnext-next-steps-2026-10/scripts"


def _env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "AB_", "BATTERY_"))}
    env.update(extra)
    return env


def _print(arm, ctx="32768", **extra):
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), arm, ctx, "--print"],
                         capture_output=True, text=True, env=_env(**extra))
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_run_arm_writes_into_this_campaign():
    out = _print("r27")
    assert "saida: " + str(C / "results") in out


def test_effort_defaults_to_xhigh_and_is_printed():
    assert "effort: xhigh" in _print("r27")
    assert "effort: medium" in _print("r27", FLASHNEXT_EFFORT="medium")


def test_effort_rejects_high():
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), "r27", "32768", "--print"],
                         capture_output=True, text=True, env=_env(FLASHNEXT_EFFORT="high"))
    assert out.returncode == 64
    assert "FLASHNEXT_EFFORT" in out.stderr


def test_idle_gate_lists_dspark_and_splash_ports():
    out = subprocess.run(["bash", str(FN / "idle-gate.sh"), "--print-ports"],
                         capture_output=True, text=True, env=_env())
    assert out.returncode == 0
    assert out.stdout.split() == ["11234", "8000", "8080", "8484", "8585"]


def test_run_battery_honours_campaign_dir():
    out = subprocess.run(["bash", str(FN / "run-battery.sh"), "r27", "q", "--print"],
                         capture_output=True, text=True,
                         env=_env(BATTERY_CAMPAIGN_DIR=str(C)))
    assert out.returncode == 0, out.stderr
    assert str(C / "results") in out.stdout
