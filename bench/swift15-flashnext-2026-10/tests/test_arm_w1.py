import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
DRIVER = REPO / "bench" / "qwen38-flashnext-daily-driver-2026-09" / "scripts" / "run-candidate.sh"
SWIFT = "Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "MTPLX_", "OMLX_", "ENGINE_", "AB_"))}
    env.update(extra or {})
    return env


def show(cand, ctx="32768", *args):
    out = subprocess.run(["bash", str(DRIVER), cand, ctx, *args, "--print"],
                         capture_output=True, text=True, env=_env(), check=True)
    return out.stdout


def test_w1_serves_swift_pack_on_26101():
    out = show("w1")
    assert SWIFT in out
    assert IQ not in out
    assert "mlx-serve-v26.10.1/mlx-serve" in out
    assert "--runtime-revision v26.10.1 " in out


def test_w1_keeps_n2_flags():
    # O A/B só muda os pesos: o comando do servidor do w1 é o do n2 com outro --model.
    w1 = show("w1").replace(SWIFT, "MODEL")
    n2 = show("n2").replace(IQ, "MODEL")
    assert w1.replace("w1", "ARM") == n2.replace("n2", "ARM")
