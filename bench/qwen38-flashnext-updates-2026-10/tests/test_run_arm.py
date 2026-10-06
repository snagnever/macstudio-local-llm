import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
RUN_ARM = HERE / "scripts" / "run-arm.sh"
ETAPA1 = HERE / "scripts" / "run-etapa1.sh"
OLD_DRIVER = REPO / "bench" / "qwen38-flashnext-daily-driver-2026-09" / "scripts" / "run-candidate.sh"
DDALCU = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "ETAPA1_"))}
    env.update(extra or {})
    return env


def print_cmd(script, arm, ctx="32768", extra_env=None):
    out = subprocess.run(["bash", str(script), arm, ctx, "--print"],
                         capture_output=True, text=True, env=_env(extra_env), check=True)
    return out.stdout


def test_n1_new_binary_incumbent_weights():
    out = print_cmd(RUN_ARM, "n1")
    assert "mlx-serve-v26.10.1/mlx-serve" in out
    assert DDALCU in out
    for flag in ("--mtp", "--prefix-cache-mem 16GB", "--prefix-cache-disk 100GB",
                 "--prefix-cache-entries 64", "--ssm-checkpoint-max 16", "--ctx-size 32768"):
        assert flag in out
    assert "--ple-gpu" not in out
    assert "--kv-quant" not in out
    assert "--runtime-revision v26.10.1 " in out


def test_n2_new_binary_iq_weights():
    out = print_cmd(RUN_ARM, "n2")
    assert "mlx-serve-v26.10.1/mlx-serve" in out
    assert IQ in out
    assert DDALCU not in out
    assert "--ple-gpu" not in out


def test_n2p_adds_ple_gpu_only():
    out = print_cmd(RUN_ARM, "n2p")
    assert IQ in out
    assert "--ple-gpu" in out
    assert "--runtime-revision v26.10.1-plegpu " in out


def test_c1_keeps_incumbent_binary():
    out = print_cmd(RUN_ARM, "c1")
    assert "mlx-serve-v26.9.2/mlx-serve" in out
    assert DDALCU in out
    assert "--ple-gpu" not in out


def test_run_arm_writes_to_this_campaign():
    out = print_cmd(RUN_ARM, "n1")
    assert f"saida: {HERE}/results/n1-32768-t1.0.jsonl" in out


def test_old_driver_default_output_unchanged():
    out = print_cmd(OLD_DRIVER, "c1")
    assert "qwen38-flashnext-daily-driver-2026-09/results/c1-32768-t1.0.jsonl" in out


def _dry(ctx):
    out = subprocess.run(["bash", str(ETAPA1), ctx], capture_output=True, text=True,
                         env=_env({"ETAPA1_DRY": "1"}), check=True)
    return [l.split()[2] for l in out.stdout.splitlines() if l.startswith("bash ")]


def test_etapa1_order_32k():
    assert _dry("32768") == ["c1", "n1", "n2"]


def test_etapa1_order_128k_reversed():
    assert _dry("131072") == ["n2", "n1", "c1"]


def test_etapa1_rejects_other_band():
    r = subprocess.run(["bash", str(ETAPA1), "262144"], capture_output=True, text=True,
                       env=_env({"ETAPA1_DRY": "1"}))
    assert r.returncode == 64
