import subprocess

import pytest
from conftest import HERE, SCRIPTS, clean_env, show_arm

UKISAI = "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS"
FIXTURES = HERE / "tests" / "fixtures"
PLE_OFF = {"FLASHNEXT_SPLASH_XARGS": "--ple-memory off", "FLASHNEXT_SPLASH_REVX": "-ple-off"}


def test_k2h_runs_splash_161():
    out = show_arm("k2h")
    assert "splash-v1.6.1/bin/splash" in out and UKISAI in out
    assert "--revision 0142554c963a8653912c0c8283f05f13f63653f3" in out and "--verify-rows auto" in out
    assert "--runtime-revision v1.6.1-verify-auto" in out


def test_k2f_and_k2g_are_unchanged():
    f, g = show_arm("k2f"), show_arm("k2g")
    assert "splash-v1.5.0/bin/splash" in f and "--runtime-revision v1.5.0-verify-auto" in f
    assert "splash-v1.6.0/bin/splash" in g and "--runtime-revision v1.6.0-verify-auto" in g


def test_tag_161_moves_k2c_and_rc():
    for arm, ctx in (("k2c2LL", "262144"), ("rc2", "131072")):
        out = show_arm(arm, ctx, extra_env={"FLASHNEXT_SPLASH_TAG": "1.6.1"})
        assert "splash-v1.6.1/bin/splash" in out and "splash-v1.5.0" not in out
    # rc* arms run run-claude-pair.sh, which takes no --runtime-revision; only k2c* prints one.
    assert "--runtime-revision v1.6.1-verify-auto" in show_arm("k2c2LL", "262144", extra_env={"FLASHNEXT_SPLASH_TAG": "1.6.1"})


def test_bad_tag_is_refused():
    r = subprocess.run(["bash", str(SCRIPTS / "run-arm.sh"), "k2c2a", "32768", "--print"], capture_output=True,
                       text=True, env=clean_env({"FLASHNEXT_SPLASH_TAG": "1.7.0"}))
    assert r.returncode == 64


@pytest.mark.parametrize("arm,ctx", [("k2h", "32768"), ("k2c2LL", "262144"), ("rc2", "131072")])
def test_xargs_and_revx_reach_k2c_and_rc(arm, ctx):
    out = show_arm(arm, ctx, extra_env=dict(PLE_OFF, FLASHNEXT_SPLASH_TAG="1.6.1"))
    assert "--verify-rows auto --ple-memory off" in out
    if not arm.startswith("rc"):
        assert "-verify-auto-ple-off " in out


@pytest.mark.parametrize("arm,ctx", [("k2c2LL", "262144"), ("k2c2a", "131072"), ("rc2", "131072"),
                                     ("rc2s", "131072")])
def test_old_k2c_commands_stay_the_same(arm, ctx):
    want = (FIXTURES / f"print-{arm}-{ctx}-150.txt").read_text()
    assert show_arm(arm, ctx, args=("--tag", "f1")) == want
