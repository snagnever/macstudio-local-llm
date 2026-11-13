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


def run_in(area, argv, **kw):
    cmd = sandboxed(Cmd(argv, {"HOME": str(area / "home"), "PATH": "/usr/bin:/bin"}, area / "work"), **kw)
    return subprocess.run(cmd.argv, cwd=cmd.cwd, env=cmd.env, capture_output=True, text=True)


def test_session_cannot_read_the_reference_solutions(area):
    assert run_in(area, ["/bin/cat", str(HERE / "tests" / "solutions.py")]).returncode != 0


def test_session_cannot_list_the_real_home(area):
    assert run_in(area, ["/bin/ls", str(Path.home())]).returncode != 0


def test_extra_read_paths_open_one_directory(area):
    assert run_in(area, ["/bin/cat", str(HERE / "scripts" / "tasks.py")], read=[HERE / "scripts"]).returncode == 0
    assert run_in(area, ["/bin/cat", str(HERE / "tests" / "solutions.py")], read=[HERE / "scripts"]).returncode != 0


def test_write_outside_the_user_tree_is_denied(area):
    target = "/private/etc/harness-delivery-probe"
    assert run_in(area, [sys.executable, "-c", f"open({target!r}, 'w')"]).returncode != 0


def test_tmpdir_points_inside_the_session_home(area):
    cmd = sandboxed(Cmd(["true"], {"HOME": str(area / "home")}, area / "work"))
    assert cmd.env["TMPDIR"] == str(area / "home" / "tmp") and (area / "home" / "tmp").is_dir()
    r = run_in(area, [sys.executable, "-c", "import tempfile; tempfile.NamedTemporaryFile().write(b'x')"])
    assert r.returncode == 0, r.stderr


def test_launch_helpers_cannot_run(area):
    assert run_in(area, ["/bin/launchctl", "version"]).returncode != 0
    assert run_in(area, ["/usr/bin/osascript", "-e", "1"]).returncode != 0


def test_missing_sandbox_fails_closed(area, monkeypatch):
    import harness
    monkeypatch.setattr(harness, "SANDBOX_EXEC", "/nonexistent/sandbox-exec")
    with pytest.raises(RuntimeError):
        sandboxed(Cmd(["true"], {"HOME": str(area / "home")}, area / "work"))


def test_launchd_refuses_job_submission_from_any_sandboxed_process(area):
    """The exec denylist is not the barrier against launchd persistence: macOS refuses job submission from a
    sandboxed client. This pins that assumption on the machine that runs the sessions."""
    label = "harness-delivery.sandbox-probe"
    r = subprocess.run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/bin/launchctl", "submit",
                        "-l", label, "--", "/usr/bin/true"], capture_output=True, text=True)
    listed = subprocess.run(["/bin/launchctl", "list"], capture_output=True, text=True).stdout
    subprocess.run(["/bin/launchctl", "remove", label], capture_output=True)
    assert r.returncode != 0 and label not in listed


def test_profile_denies_job_creation(area):
    cmd = sandboxed(Cmd(["true"], {"HOME": str(area / "home")}, area / "work"))
    assert "(deny job-creation)" in cmd.argv[2]


def test_read_allowlist_names_runtime_directories_only(area):
    import harness
    assert ".local" not in harness.TOOLCHAIN_DIRS
    profile = sandboxed(Cmd(["true"], {"HOME": str(area / "home")}, area / "work")).argv[2]
    assert str(Path.home() / ".local/share/opencode") not in profile
    assert str(Path.home() / ".local/bin") in profile


def test_harness_credentials_under_dot_local_are_unreadable(area):
    assert run_in(area, ["/bin/ls", str(Path.home() / ".local/share")]).returncode != 0
