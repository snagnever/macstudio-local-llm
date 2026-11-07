import os
import subprocess

from conftest import SCRIPTS, clean_env


def _fake(tmp_path, name, body):
    path = tmp_path / name
    path.write_text("#!/bin/bash\n" + body + "\n")
    path.chmod(0o755)
    return str(path)


def _run(tmp_path, hours, pair_exit=0):
    log = tmp_path / "calls.log"
    env = clean_env({"BASE_URL": "http://x/v1", "MODEL_ID": "m",
                     "SOAK_PAIR": _fake(tmp_path, "pair", f'echo "pair $*" >> {log}; sleep 1; exit {pair_exit}'),
                     "SOAK_PROBE": _fake(tmp_path, "probe", f'echo "probe $*" >> {log}')})
    subprocess.run(["bash", str(SCRIPTS / "agent_soak.sh"), "--hours", hours, "--tag", "g1", "--out", str(tmp_path)],
                   env=env, check=True, capture_output=True, text=True, timeout=60)
    return log.read_text().splitlines()


def test_soak_stops_after_hours_and_probes_between_pairs(tmp_path):
    calls = _run(tmp_path, "0.001")  # 3 s: pairs of 1 s each
    assert calls[0].startswith("probe") and "--label pre" in calls[0]
    assert calls[1].startswith("pair") and "--sessions 2 --pair c,d --proxy 8686 --tag soakg1p1 " in calls[1]
    assert "--label pair1" in calls[2]
    assert sum(c.startswith("pair") for c in calls) in (2, 3, 4)


def test_soak_keeps_going_when_a_pair_fails(tmp_path):
    calls = _run(tmp_path, "0.001", pair_exit=3)
    assert sum(c.startswith("pair") for c in calls) >= 2
