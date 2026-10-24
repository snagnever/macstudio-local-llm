import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN_ARM = HERE / "scripts" / "run-arm.sh"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
SWIFT = "Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"
NEW = "mlx-serve-v26.10.3/mlx-serve"
OLD = "mlx-serve-v26.10.1/mlx-serve"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "AB_", "SPLASH_"))}
    env.update(extra or {})
    return env


def show(cand, ctx="32768", *args):
    return subprocess.run(["bash", str(RUN_ARM), cand, ctx, *args, "--print"], capture_output=True, text=True,
                          env=_env(), check=True).stdout


def server(out):
    lines = out.splitlines()
    return lines[[i for i, l in enumerate(lines) if l.startswith("launcher:")][0] + 1]


def test_w1z_and_w1_differ_only_in_binary():
    z = show("w1z")
    assert SWIFT in z and "--runtime-revision v26.10.3 " in z
    assert server(z).replace(NEW, "BIN") == server(show("w1")).replace(OLD, "BIN")


def test_n2z_is_n2_on_26103():
    assert server(show("n2z")).replace(NEW, "BIN") == server(show("n2")).replace(OLD, "BIN")


def test_t6z_uses_the_twyx_pack_with_n2_flags():
    t6, n2 = server(show("t6z")), server(show("n2z"))
    assert "twyx-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-6.6bpw-884894d" in t6
    assert t6.split("--serve", 1)[1] == n2.split("--serve", 1)[1]


def test_splash_arms_differ_only_in_verify_rows():
    k1, k1a = show("k1"), show("k1a")
    assert "splash-v1.4.0/bin/splash" in server(k1)
    assert "--model unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ4_XS " in server(k1)
    assert "--revision 766911a6b7369840a91dbcd95f9f997acaab6cd6 " in server(k1)
    assert server(k1).endswith("--verify-rows all") and server(k1a).endswith("--verify-rows auto")
    assert server(k1).replace("all", "X") == server(k1a).replace("auto", "X")
    assert "--draft-model" not in server(k1)


def test_r1_is_the_gsq_coder_on_omlx_072():
    out = show("r1")
    assert "run-omlx.sh FG" in out
    assert '"repository": "mbrown-uno/Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX"' in out
    assert '"omlx_version": "0.7.2"' in out


def test_toolcall_probe_sends_both_penalties():
    out = subprocess.run(["bash", str(HERE / "scripts" / "toolcall-probe.sh"), "w1z", "--print"],
                         capture_output=True, text=True, env=_env(), check=True).stdout
    assert "--frequency-penalty 0;" in out and "--frequency-penalty 1;" in out and "--turns 4 " in out
    assert "w1z-fp0.jsonl" in out and "w1z-fp1.jsonl" in out and " 65536 " in out


def test_k2_arms_are_the_swift_gguf_with_the_k1_flags():
    k2, k2a, k1 = server(show("k2")), server(show("k2a")), server(show("k1"))
    assert "--model ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS " in k2
    assert "--revision 0142554c963a8653912c0c8283f05f13f63653f3 " in k2
    assert k2.endswith("--verify-rows all") and k2a.endswith("--verify-rows auto")
    strip = lambda s: s.split("--revision")[1].split(" ", 2)[2]
    assert strip(k2) == strip(k1)
    assert "model_select: ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS" in show("k2a")
    k2ab = server(show("k2ab"))
    assert k2ab == k2a + " --kv-format bf16"


def test_toolcall_probe_sessions_and_suffix_keep_earlier_files():
    out = subprocess.run(["bash", str(HERE / "scripts" / "toolcall-probe.sh"), "k2a", "--sessions", "20",
                          "--suffix", "x20", "--print"],
                         capture_output=True, text=True, env=_env(), check=True).stdout
    assert "seq 20" in out and "k2a-fp0-x20.jsonl" in out and "k2a-fp1-x20.jsonl" in out
    assert "k2a-fp0.jsonl" not in out and "toolcall-x20" in out


def test_r1z_is_the_r1_pack_with_the_n2_flags_on_26103():
    r1z, n2 = server(show("r1z")), server(show("n2z"))
    assert NEW in r1z and "mbrown-uno-Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX-50fa68c" in r1z
    assert r1z.split("--serve", 1)[1] == n2.split("--serve", 1)[1]
