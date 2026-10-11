import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "bench" / "terminal-bench" / "scripts" / "run-tbench-flashnext.sh"
PORT = 11998  # nunca a 11234: lá pode estar o servidor de outra sessão


def _busy(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _env(extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FLASHNEXT_", "TBENCH_"))}
    env.update({"TBENCH_DRY": "1", "FLASHNEXT_PORT": str(PORT), **extra})
    return env


def test_busy_port_refuses_before_starting_anything():
    # Com a porta ocupada, o launcher sairia com 69 e o curl acharia o servidor alheio: o harbor rodaria
    # contra o modelo errado e o trap derrubaria esse servidor no fim.
    if _busy(PORT):
        pytest.skip(f"porta {PORT} em uso")
    foreign = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            if _busy(PORT):
                break
            time.sleep(0.1)
        res = subprocess.run(["bash", str(SCRIPT), "w1"], capture_output=True, text=True, env=_env({}), timeout=30)
        assert res.returncode == 75 and "ocupada" in res.stderr
        assert foreign.poll() is None
    finally:
        foreign.kill()
        foreign.wait()


def test_missing_weights_refuse(tmp_path):
    res = subprocess.run(["bash", str(SCRIPT), "w1"], capture_output=True, text=True, timeout=30,
                         env=_env({"HOME": str(tmp_path)}))
    assert res.returncode == 66 and "pesos ausentes" in res.stderr


def test_free_port_and_weights_pass_preflight():
    if _busy(PORT):
        pytest.skip(f"porta {PORT} em uso")
    res = subprocess.run(["bash", str(SCRIPT), "w1"], capture_output=True, text=True, env=_env({}), timeout=30)
    assert res.returncode == 0 and f"port={PORT}" in res.stdout
