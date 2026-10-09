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


ETAPA_G = HERE / "scripts" / "run-etapa-g.sh"


def dry_g(extra=None):
    out = subprocess.run(["bash", str(ETAPA_G)], capture_output=True, text=True,
                         env=_env({"ENGINE_BAND_DRY": "1", **(extra or {})}), check=True)
    return out.stdout.splitlines()


def test_etapa_g_dry_run_lists_queue():
    lines = dry_g()
    runs = [l.split() for l in lines if l.startswith("bash run-arm.sh")]
    assert [(c[2], c[3]) for c in runs] == [
        ("n2", "8192"), ("o1", "8192"), ("m1", "8192"), ("d1", "8192"),
        ("m1v", "131072"), ("m1v", "262144"),
        ("d1", "131072"), ("d1", "262144"), ("d1", "524288"),
    ]
    assert all(c[-2:] == ["--tag", "pg"] for c in runs)
    assert [c[5] for c in runs] == ["3"] * 5 + ["1", "3", "1", "1"]
    assert runs[-1][6:8] == ["--yarn", "2.0"]
    assert "--yarn" not in runs[-2]
    assert lines[-1].startswith("relaunch daily driver")


def test_etapa_g_mtplx_branch_walks_on_refusal(tmp_path):
    # G2: m1v recusa (HTTP 507) → m1x recusa → m1q; o primeiro que passa ganha 256K com 1 rep.
    lines = dry_g({"ENGINE_G_REFUSED": "m1v,m1x"})
    runs = [(l.split()[2], l.split()[3], l.split()[5]) for l in lines if l.startswith("bash run-arm.sh")]
    g2 = [r for r in runs if r[0].startswith("m1") and r[0] != "m1"]
    assert g2 == [("m1v", "131072", "3"), ("m1x", "131072", "3"), ("m1q", "131072", "3"), ("m1q", "262144", "1")]


def test_etapa_g_first_passing_mtplx_gets_256k():
    lines = dry_g()
    runs = [(l.split()[2], l.split()[3]) for l in lines if l.startswith("bash run-arm.sh")]
    assert ("m1v", "262144") in runs


def test_quality_runs_three_batteries_through_exec_hook():
    out = subprocess.run(["bash", str(HERE / "scripts" / "run-quality.sh"), "o1", "131072"], capture_output=True,
                         text=True, env=_env({"ENGINE_BAND_DRY": "1"}), check=True).stdout
    assert "bench2.py humaneval --examples 164" in out
    assert "--suite jdhodges" in out and "--suite veerman" in out
    assert "--run-prefix toolcall_pg_o1" in out
    assert out.rstrip().endswith("bash run-arm.sh o1 131072 --tag qual")


def test_etapa_g_refusal_counts_any_http_error_on_cold(tmp_path):
    # O m1v (config do vendor) recusou 128K com HTTP 400 context_length_exceeded, não 507.
    res = tmp_path / "results"; res.mkdir()
    (res / "m1v-131072-t1.0-pg.jsonl").write_text(
        '{"scenario": "cold", "error": "http_400: Bad Request: context_length_exceeded"}\n', encoding="utf-8")
    # --lib só define as funções; RESULTS aponta para o diretório temporário.
    out = subprocess.run(["bash", "-c", f'source "{ETAPA_G}" --lib && refused m1v 131072 && echo REFUSED'],
                         capture_output=True, text=True, env=_env({"RESULTS": str(res)}), check=False,
                         timeout=10).stdout
    assert "REFUSED" in out


def test_etapa_g_parts_and_g2_arms_select_queue():
    lines = dry_g({"ENGINE_G_PARTS": "g2", "ENGINE_G2_ARMS": "m1x m1q", "ENGINE_G_REFUSED": "m1x"})
    runs = [(l.split()[2], l.split()[3]) for l in lines if l.startswith("bash run-arm.sh")]
    assert runs == [("m1x", "131072"), ("m1q", "131072"), ("m1q", "262144")]
