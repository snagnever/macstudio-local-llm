import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import HERE
from harness import Cmd, sandboxed

pytestmark = pytest.mark.skipif(not Path("/usr/bin/sandbox-exec").exists(), reason="macOS sandbox-exec only")


@pytest.fixture
def area():
    """A scratch area under the user's home (the checkout), where the sandbox must deny writes by default."""
    d = HERE / "logs" / "sandbox-test"
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    (d / "home").mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def write(area, target):
    cmd = sandboxed(Cmd([sys.executable, "-c", f"open({str(target)!r}, 'w').write('x')"],
                        {"HOME": str(area / "home"), "PATH": "/usr/bin:/bin"}, area / "work"))
    return subprocess.run(cmd.argv, cwd=cmd.cwd, env=cmd.env, capture_output=True, text=True)


def test_wrapper_is_sandbox_exec(area):
    cmd = sandboxed(Cmd(["true"], {"HOME": str(area / "home")}, area / "work"))
    assert cmd.argv[0] == "/usr/bin/sandbox-exec" and cmd.argv[-1] == "true"


def test_writes_inside_the_copy_and_the_session_home_pass(area):
    assert write(area, area / "work" / "ok.txt").returncode == 0
    assert write(area, area / "home" / "ok.txt").returncode == 0


def test_write_outside_the_copy_is_denied(area):
    r = write(area, area / "outside.txt")
    assert r.returncode != 0 and not (area / "outside.txt").exists()


def test_read_of_user_secrets_is_denied(area):
    probe = Path.home() / ".ssh"
    cmd = sandboxed(Cmd(["/bin/ls", str(probe)], {"HOME": str(area / "home")}, area / "work"))
    assert subprocess.run(cmd.argv, cwd=cmd.cwd, env=cmd.env, capture_output=True).returncode != 0


def test_sandbox_can_be_turned_off(area, monkeypatch):
    monkeypatch.setenv("HARNESS_SANDBOX", "0")
    assert sandboxed(Cmd(["true"], {}, area / "work")).argv == ["true"]
