import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
BATTERY = HERE / "scripts" / "ab-battery.sh"


def test_failed_runner_does_not_copy_a_stale_run(tmp_path):
    # bench2 morre antes de gravar: o arquivo mais novo em benchmarks/runs é de outro perfil ou braço,
    # e não pode ir para results/ab/<perfil>/<braço>/.
    bench = tmp_path / "bench"
    runs = bench / "benchmarks" / "runs"
    runs.mkdir(parents=True)
    (runs / "humaneval_other-model_20261010_000000.jsonl").write_text('{"stale": true}\n')
    venv = bench / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text("#!/bin/sh\nexit 1\n")
    (venv / "python").chmod(0o755)
    out_root = tmp_path / "results"
    env = {k: v for k, v in os.environ.items() if not k.startswith("AB_")}
    env.update({"BASE_URL": "http://127.0.0.1:9/v1", "MODEL_ID": "m", "AB_ARM": "n2", "AB_PROFILES": "t1",
                "AB_SUITES": "humaneval", "AB_BENCH": str(bench), "AB_RESULTS": str(out_root)})
    res = subprocess.run(["bash", str(BATTERY)], capture_output=True, text=True, env=env, timeout=60)
    assert res.returncode != 0
    assert not (out_root / "ab" / "t1" / "n2" / "humaneval.jsonl").exists()
    assert "nenhum run novo" in res.stderr


def test_new_run_is_copied(tmp_path):
    bench = tmp_path / "bench"
    runs = bench / "benchmarks" / "runs"
    runs.mkdir(parents=True)
    (runs / "humaneval_old_20261010_000000.jsonl").write_text('{"stale": true}\n')
    venv = bench / ".venv" / "bin"
    venv.mkdir(parents=True)
    # O runner falso grava um run novo no cwd do bench, como o bench2.py.
    (venv / "python").write_text('#!/bin/sh\necho \'{"fresh": true}\' > benchmarks/runs/humaneval_new_20261011_000000.jsonl\n')
    (venv / "python").chmod(0o755)
    out_root = tmp_path / "results"
    env = {k: v for k, v in os.environ.items() if not k.startswith("AB_")}
    env.update({"BASE_URL": "http://127.0.0.1:9/v1", "MODEL_ID": "m", "AB_ARM": "n2", "AB_PROFILES": "t1",
                "AB_SUITES": "humaneval", "AB_BENCH": str(bench), "AB_RESULTS": str(out_root)})
    res = subprocess.run(["bash", str(BATTERY)], capture_output=True, text=True, env=env, timeout=60)
    assert res.returncode == 0, res.stderr
    assert (out_root / "ab" / "t1" / "n2" / "humaneval.jsonl").read_text() == '{"fresh": true}\n'


def test_toolcall_suite_runs_uv_outside_the_path(tmp_path):
    # A fila do rig roda sob nohup com PATH=/usr/bin:/bin, sem o uv do Homebrew: jdhodges e veerman não rodavam.
    bench = tmp_path / "bench"
    (bench / "benchmarks" / "runs").mkdir(parents=True)
    uv = tmp_path / "uv"
    uv.write_text('#!/bin/sh\necho \'{"fresh": true}\' > benchmarks/runs/toolcall_ab_t1_n2_jdhodges_20261024.jsonl\n')
    uv.chmod(0o755)
    out_root = tmp_path / "results"
    env = {k: v for k, v in os.environ.items() if not k.startswith("AB_")}
    env.update({"PATH": "/usr/bin:/bin", "BASE_URL": "http://127.0.0.1:9/v1", "MODEL_ID": "m", "AB_ARM": "n2",
                "AB_PROFILES": "t1", "AB_SUITES": "jdhodges", "AB_BENCH": str(bench), "AB_RESULTS": str(out_root),
                "AB_UV": str(uv)})
    res = subprocess.run(["bash", str(BATTERY)], capture_output=True, text=True, env=env, timeout=60)
    assert res.returncode == 0, res.stderr
    assert (out_root / "ab" / "t1" / "n2" / "jdhodges.jsonl").read_text() == '{"fresh": true}\n'
