import os
import re
import subprocess

from conftest import HERE, _env

QUEUE = HERE / "scripts" / "run-queue.sh"


def run(*args, **env):
    return subprocess.run(["bash", str(QUEUE), *args], capture_output=True, text=True, env=_env() | env)


def arms_of(out, tool):
    return re.findall(rf"{tool} (k\d[fg])\b", out)


def test_queue_keeps_the_user_order_on_160():
    out = run("g", "--dry-run").stdout
    assert arms_of(out, "run-arm.sh") == ["k6g", "k1g", "k5g", "k8g", "k4g", "k3g"]
    assert arms_of(out, "run-battery.sh") == ["k6g", "k1g", "k5g", "k8g", "k4g", "k3g"]
    assert arms_of(out, "toolcall-probe.sh") == ["k6g", "k1g", "k5g", "k8g", "k4g", "k3g"]


def test_queue_on_150_runs_the_swift_reference_first():
    out = run("f", "--dry-run").stdout
    assert arms_of(out, "run-arm.sh") == ["k2f", "k6f", "k1f", "k5f", "k8f", "k4f", "k3f"]


def test_each_arm_finishes_before_the_next_starts():
    lines = run("g", "--dry-run").stdout.splitlines()
    steps = [line for line in lines if "k6g" in line or "k1g" in line or line.startswith("CHECKPOINT")]
    assert "run-arm.sh k6g 262144 --repeat 3 --tag w1" in steps[0]
    assert "run-battery.sh k6g w1" in steps[1] and '--ctx 262144' in steps[1]
    assert "toolcall-probe.sh k6g --sessions 20 --suffix w1 --max-tokens 2048" in steps[2]
    assert steps[3] == "CHECKPOINT-k6g"
    assert "run-arm.sh k1g" in steps[4]


def test_queue_rejects_an_unknown_release():
    assert run("x", "--dry-run").returncode == 64


def test_queue_stops_when_the_disk_is_low():
    result = run("g", "--dry-run", QUEUE_MIN_FREE_GB="999999999")
    assert result.returncode == 3 and "run-arm.sh" not in result.stdout
