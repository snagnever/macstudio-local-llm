import subprocess

from conftest import SCRIPTS, clean_env

QUEUE = SCRIPTS / "run-queue.sh"


def dry(*args):
    r = subprocess.run(["bash", str(QUEUE), *args, "--dry-run"], capture_output=True, text=True, env=clean_env())
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def arms_at(lines, ctx):
    return [line.split()[1] for line in lines if line.split()[2] == ctx]


def test_queue_dry_run_orders_steps():
    lines = dry("speed", "z1h", "z2h")
    assert len(lines) == 18 and all(line.startswith("run-arm.sh ") and "--repeat 1 --tag s" in line for line in lines)
    assert arms_at(lines, "32768") == ["k2h", "z1h", "z2h", "z2h", "z1h", "k2h"]
    assert arms_at(lines, "131072") == ["z2h", "z1h", "k2h", "k2h", "z1h", "z2h"]
    assert arms_at(lines, "262144") == ["k2h", "z1h", "z2h", "z2h", "z1h", "k2h"]
    assert len({line.split()[-1] for line in lines}) == 18


def test_queue_refusal_runs_each_arm_once():
    assert dry("refusal", "k2h", "z1h") == ["refusal-arm.sh k2h", "refusal-arm.sh z1h"]


def test_queue_quality_runs_battery_toolcalls_longctx():
    lines = dry("quality", "z1h")
    assert len(lines) == 3
    assert "run-battery.sh z1h su1" in lines[0] and "--ctx 262144" in lines[0]
    assert '--suites "humaneval gpqa livecodebench if jdhodges veerman"' in lines[0]
    assert "toolcall-probe.sh z1h --sessions 20 --suffix su1 --max-tokens 2048" in lines[1]
    assert "longctx-arm.sh z1h 262144 131072 262144" in lines[2]


def test_queue_claude_alternates_packs():
    lines = dry("claude", "z1h")
    assert [line.split()[0] for line in lines] == ["FLASHNEXT_SPLASH_PACK=" + p for p in ("k2", "z1", "z1", "k2")]
    assert all("FLASHNEXT_SPLASH_TAG=1.6.1" in line and "run-arm.sh rc2 131072" in line for line in lines)
    assert len({line.split()[-1] for line in lines}) == 4


def test_queue_refuses_bad_input():
    for args in (["nope", "z1h"], ["speed"], ["speed", "q9h"], ["claude", "z1h", "z2h"]):
        r = subprocess.run(["bash", str(QUEUE), *args, "--dry-run"], capture_output=True, text=True, env=clean_env())
        assert r.returncode == 64, args


def test_queue_records_exit_and_continues(tmp_path):
    fake = tmp_path / "camp" / "scripts"
    fake.mkdir(parents=True)
    (fake / "run-queue.sh").write_text(QUEUE.read_text())
    (fake / "run-arm.sh").write_text('#!/bin/bash\necho "ran $1@$2"\n[ "$1" = z1h ] && exit 69\nexit 0\n')
    env = clean_env({"QUEUE_GAP_S": "0", "QUEUE_IDLE_GATE": "0", "QUEUE_MIN_FREE_GB": "0"})
    r = subprocess.run(["bash", str(fake / "run-queue.sh"), "speed", "z1h"], capture_output=True, text=True,
                       env=env, timeout=120)
    assert r.returncode == 0, r.stderr
    assert "end z1h@32768 rc=69" in r.stdout and r.stdout.count("rc=69") == 6
    assert "ran k2h@262144" in r.stdout and "end k2h@262144 rc=0" in r.stdout


def test_queue_stops_on_low_disk(tmp_path):
    fake = tmp_path / "camp" / "scripts"
    fake.mkdir(parents=True)
    (fake / "run-queue.sh").write_text(QUEUE.read_text())
    (fake / "run-arm.sh").write_text("#!/bin/bash\necho ran\n")
    env = clean_env({"QUEUE_GAP_S": "0", "QUEUE_IDLE_GATE": "0", "QUEUE_MIN_FREE_GB": "99999999"})
    r = subprocess.run(["bash", str(fake / "run-queue.sh"), "speed", "z1h"], capture_output=True, text=True, env=env)
    assert r.returncode == 3 and "ran" not in r.stdout
