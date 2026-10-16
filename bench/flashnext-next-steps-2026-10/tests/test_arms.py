import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
RUN_ARM = HERE / "scripts" / "run-arm.sh"
ROOT = Path.home() / ".cache/local-llms/qwen3.8-prefix-cache"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
SWIFT = "Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"
OQ4E = "Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
NEW = "mlx-serve-v26.10.2/mlx-serve"
OLD = "mlx-serve-v26.10.1/mlx-serve"

def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "AB_"))}
    env.update(extra or {})
    return env

def show(cand, ctx="32768", *args, env=None):
    return subprocess.run(["bash", str(RUN_ARM), cand, ctx, *args, "--print"], capture_output=True, text=True,
                          env=_env(env), check=True).stdout

def server(out):
    lines = out.splitlines()
    return lines[[i for i, l in enumerate(lines) if l.startswith("launcher:")][0] + 1]

def test_n2x_is_n2_on_the_prerelease():
    x, ref = show("n2x"), show("n2")
    assert NEW in x and IQ in x and "--runtime-revision v26.10.2 " in x
    assert server(x).replace(NEW, "BIN") == server(ref).replace(OLD, "BIN")

def test_w1x_and_w1_differ_only_in_binary():
    assert server(show("w1x")).replace(NEW, "BIN") == server(show("w1")).replace(OLD, "BIN")
    assert SWIFT in show("w1x")

def test_512k_arms_use_4bit_kv_with_yarn():
    for cand, binary in (("w1q4", OLD), ("w1xq4", NEW)):
        out = show(cand, "524288", "--yarn", "2.0")
        assert binary in out and SWIFT in out
        assert "--kv-quant 4 " in out and "rope_type" in out and "-yarn2.0-kv4 " in out

def test_ple_arms_and_control_share_the_8gb_prefix_cache():
    c8, p8 = server(show("w1c8", "131072")), server(show("w1p8", "131072"))
    assert "--prefix-cache-mem 8GB" in c8 and "--ple-gpu" not in c8
    assert "--prefix-cache-mem 8GB" in p8 and "--ple-gpu" in p8
    assert p8.replace(" --ple-gpu", "") == c8
    assert NEW in show("w1xp8", "131072")

def test_extra_args_never_leak_into_other_arms():
    out = show("n2", env={"QWEN38_MLX_EXTRA_ARGS": "--bogus 1"})
    assert "--bogus" not in out

def test_n2xd_passes_the_depth_flag():
    out = show("n2xd", env={"FLASHNEXT_MTP_DEPTH_FLAG": "--mtp-depth", "FLASHNEXT_MTP_DEPTH": "2"})
    assert "--mtp-depth 2" in server(out) and "-mtpd2 " in out

def test_oq4e_refit_on_mlx_serve():
    out = show("o1rm")
    assert NEW in out and "Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5" in out

def test_gguf_arms():
    g1 = show("g1")
    assert "llama-b11609/llama-server" in g1 and "--spec-type draft-mtp" in g1 and "--port 8080" in g1
    assert "--parallel 1" in g1 and "--kv-unified" not in g1
    assert "--spec-type" not in show("g0")
    assert NEW in show("g1m") and "--port 11234" in show("g1m")

@pytest.mark.skipif(not (ROOT / OQ4E).is_dir(), reason="needs the oQ4e pack (rig only)")
def test_o1x_is_old_oq4e_on_omlx_dev2():
    out = show("o1x")
    assert "omlx-v0.7.1.dev2/bin/omlx" in out and OQ4E in out and "--runtime-revision v0.7.1.dev2 " in out

MIX6 = "umixer-Qwen3.8-Flash-Next-oQ4e-mix6-mtp-73d2cd0bc0ac07bde45f374a1f7eff01fb06ac90"

@pytest.mark.skipif(not (ROOT / MIX6).is_dir(), reason="needs the mix6 pack (rig only)")
def test_x1_is_mix6_from_the_consolidated_repo():
    # umixer retired the -v2 repo; its bytes live in the original repo id at 73d2cd0.
    out = show("x1")
    assert MIX6 in out and "MISSING" not in out and "omlx-v0.7.1.dev2/bin/omlx" in out

def test_probe_max_tokens_is_opt_in():
    assert "--max-tokens" not in show("w1")
    assert "--max-tokens 8192" in show("w1", env={"QWEN38_PROBE_MAX_TOKENS": "8192"})

def test_w1t_uses_the_efftail_overlay():
    t = show("w1t", "131072")
    assert SWIFT + "-efftail" in t and "--runtime-revision v26.10.1-efftail " in t
    assert server(t).replace("-efftail", "") == server(show("w1", "131072"))
