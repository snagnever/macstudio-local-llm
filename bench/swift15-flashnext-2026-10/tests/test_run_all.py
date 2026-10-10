import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN_ALL = HERE / "scripts" / "run-all.sh"


def dry(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ALL_", "AB_"))}
    env.update({"ALL_DRY": "1", **(extra or {})})
    return subprocess.run(["bash", str(RUN_ALL)], capture_output=True, text=True, env=env,
                          check=True).stdout.splitlines()


def test_default_queue_is_the_plan_order():
    names = [l.split(":")[0] for l in dry() if not l.startswith("===")]
    assert names == ["ab-n2", "ab-w1", "fn-n2-32768", "fn-w1-32768", "fn-w1-131072", "fn-n2-131072"]


def test_resume_steps_with_profile_and_suites():
    # Retomada depois da pausa de 2026-10-10: resto do t1 do n2, t0 do n2, e o resto da fila.
    lines = dry({"ALL_STEPS": "ab-n2-t1:gpqa,livecodebench,jdhodges,veerman,if ab-n2-t0 ab-w1 fn-n2-32768"})
    assert lines[0] == ("ab-n2-t1: AB_SUITES='gpqa livecodebench jdhodges veerman if' caffeinate -i bash "
                        f"{HERE}/scripts/run-ab.sh n2 --profiles t1")
    assert lines[1] == f"ab-n2-t0: caffeinate -i bash {HERE}/scripts/run-ab.sh n2 --profiles t0"
    assert lines[2] == f"ab-w1: caffeinate -i bash {HERE}/scripts/run-ab.sh w1"
    assert lines[3] == f"fn-n2-32768: caffeinate -i bash {HERE}/scripts/run-arm.sh n2 32768 --repeat 3 --tag fn"


def test_unknown_step_is_refused():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ALL_", "AB_"))}
    res = subprocess.run(["bash", str(RUN_ALL)], capture_output=True, text=True,
                         env={**env, "ALL_DRY": "1", "ALL_STEPS": "ab-x9"})
    assert res.returncode == 64 and "ab-x9" in res.stderr
