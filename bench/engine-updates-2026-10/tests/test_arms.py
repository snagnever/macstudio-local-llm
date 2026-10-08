import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
DRIVER = REPO / "bench" / "qwen38-flashnext-daily-driver-2026-09" / "scripts" / "run-candidate.sh"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
MC27 = "mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
DFLASH2 = "incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4"
M27NEW = "Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-1d5087d2062c02b279180a53e4016cf9cd7a3d7e"
FXPACK = "Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6"
OQ4E = "Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "MLX_DSPARK_", "MTPLX_", "OMLX_", "ENGINE_"))}
    env.update(extra or {})
    return env


def show(cand, ctx="32768", *args):
    out = subprocess.run(["bash", str(DRIVER), cand, ctx, *args, "--print"],
                         capture_output=True, text=True, env=_env(), check=True)
    return out.stdout


def test_m1_is_mtplx_2122_flashnext_pack():
    out = show("m1")
    assert "mtplx-v2.12.2/bin/mtplx" in out
    assert FXPACK in out
    assert "--runtime-revision v2.12.2 " in out
    assert "MTPLX_MEMORY_LIMIT_BYTES" not in out


def test_m1b_sets_memory_limit():
    out = show("m1b")
    assert FXPACK in out
    assert "MTPLX_MEMORY_LIMIT_BYTES=96G" in out
    assert "--runtime-revision v2.12.2-mem96g " in out


def test_o1_is_omlx_070_oq4e():
    out = show("o1")
    assert "omlx-v0.7.0/bin/omlx" in out
    assert OQ4E in out or "flashnext-oq4e" in out
    assert "--runtime-revision v0.7.0 " in out


def test_d1_is_ds4_upstream_with_mtp_and_disk_kv():
    out = show("d1")
    assert "ds4-upstream" in out
    assert "--mtp-timing" in out
    assert "--kv-disk-dir" in out
    assert "--tokenizer-path" in out and IQ in out
    assert "--runtime ds4 " in out


def test_r27_mlxserve_with_dflash2_drafter():
    out = show("r27")
    assert "mlx-serve-v26.10.1/mlx-serve" in out
    assert MC27 in out
    assert "--drafter" in out and DFLASH2 in out
    for flag in ("--prefix-cache-mem 16GB", "--prefix-cache-disk 100GB", "--prefix-cache-entries 64"):
        assert flag in out
    assert "--mtp " not in out


def test_r27_yarn_keeps_mrope():
    out = show("r27", "524288", "--yarn", "2.0")
    assert "--kv-quant 8" in out
    assert "mrope_section" in out and "partial_rotary_factor" in out
    assert "yarn" in out and "524288" in out
    assert "--runtime-revision v26.10.1-yarn2.0-kv8 " in out


def test_n2_yarn_matches_c1_profile():
    out = show("n2", "524288", "--yarn", "2.0")
    assert IQ in out
    assert "--kv-quant 8" in out
    assert "original_max_position_embeddings" in out
    assert "--runtime-revision v26.10.1-yarn2.0-kv8 " in out


def test_m27_uses_new_pack_and_mtplx_2122():
    out = show("m27")
    assert "mtplx-v2.12.2/bin/mtplx" in out
    assert M27NEW in out


def test_o27_is_omlx_070_oq8e():
    out = show("o27")
    assert "omlx-v0.7.0/bin/omlx" in out
    assert "oq8e" in out


def test_s27_is_dspark_0203_dflash2():
    out = show("s27")
    assert "mlx-dspark-v0.20.3" in out
    assert MC27 in out and DFLASH2 in out
    assert "dflash" in out


def test_old_candidates_unchanged():
    assert "mlx-serve-v26.9.2/mlx-serve" in show("c1")
    assert "mtplx-v2.11.2/bin/mtplx" in show("c4")
    assert "--drafter" not in show("n2")


def test_d1_selects_base_model_id():
    # ds4-server serve qwen3.8-flash-next, -chat e -reasoner; nenhum casa com o diretório.
    assert "model_select: qwen3.8-flash-next\n" in show("d1")


def test_other_arms_select_by_dir_basename():
    assert f"model_select: {IQ}\n" in show("n2")


def test_inherited_mtplx_limit_does_not_leak_into_default_arms():
    # Um MTPLX_MEMORY_LIMIT_BYTES esquecido no shell não pode rodar m1/m27 com outro limite e rótulo v2.12.2.
    for cand in ("m1", "m27"):
        out = subprocess.run(["bash", str(DRIVER), cand, "32768", "--print"], capture_output=True, text=True,
                             env=_env({"MTPLX_MEMORY_LIMIT_BYTES": "80G"}), check=True).stdout
        assert "MTPLX_MEMORY_LIMIT_BYTES" not in out
    out = subprocess.run(["bash", str(DRIVER), "m1b", "32768", "--print"], capture_output=True, text=True,
                         env=_env({"MTPLX_MEMORY_LIMIT_BYTES": "80G"}), check=True).stdout
    assert "MTPLX_MEMORY_LIMIT_BYTES=96G" in out


# Etapa F: um knob por braço.
def test_m1t_disables_session_pin_ttl():
    out = show("m1t")
    assert FXPACK in out
    assert "MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0" in out
    assert "--runtime-revision v2.12.2-pin0 " in out
    assert "--session-header" not in out


def test_m1h_probe_sends_mtplx_session_header():
    out = show("m1h")
    assert "--session-header x-mtplx-session-id" in out
    assert "--runtime-revision v2.12.2-sesshdr " in out
    assert "MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S" not in out


def test_m1th_combines_both_knobs():
    out = show("m1th")
    assert "MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0" in out
    assert "--session-header x-mtplx-session-id" in out
    assert "--runtime-revision v2.12.2-pin0-sesshdr " in out


def test_m27f_takes_knob_from_env():
    out = subprocess.run(["bash", str(DRIVER), "m27f", "131072", "--print"], capture_output=True, text=True,
                         env=_env({"ENGINE_M27F": "sesshdr"}), check=True).stdout
    assert M27NEW in out
    assert "--session-header x-mtplx-session-id" in out
    assert "--runtime-revision v2.12.2-sesshdr " in out


def test_m27f_requires_knob():
    res = subprocess.run(["bash", str(DRIVER), "m27f", "131072", "--print"], capture_output=True, text=True, env=_env())
    assert res.returncode != 0


def test_r27b_clamps_draft_block_to_5():
    out = show("r27b")
    assert "--drafter" in out and DFLASH2 in out
    assert "--draft-block-size 5" in out
    assert "--runtime-revision v26.10.1-blk5 " in out


def test_s27g_disables_memory_guard():
    out = show("s27g")
    assert MC27 in out and DFLASH2 in out
    assert "--no-memory-guard" in out
    assert "--runtime-revision v0.20.3-noguard " in out


def test_inherited_fix_knobs_do_not_leak_into_original_arms():
    leak = {"MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S": "0", "QWEN38_MLX_DRAFT_BLOCK_SIZE": "5",
            "QWEN38_MLX_DSPARK_NO_MEMORY_GUARD": "1"}
    for cand in ("m1", "m27", "r27", "s27"):
        out = subprocess.run(["bash", str(DRIVER), cand, "32768", "--print"], capture_output=True, text=True,
                             env=_env(leak), check=True).stdout
        for marker in ("PIN_TTL", "--draft-block-size", "--no-memory-guard", "--session-header"):
            assert marker not in out, (cand, marker)
