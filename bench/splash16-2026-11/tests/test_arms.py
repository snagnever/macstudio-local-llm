from conftest import show_arm

UKISAI = "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS"
ISTA = "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF:IQ1_M"


def test_k2g_runs_splash_160():
    out = show_arm("k2g")
    assert "splash-v1.6.0/bin/splash" in out and UKISAI in out
    assert "--revision 0142554c963a8653912c0c8283f05f13f63653f3" in out and "--verify-rows auto" in out
    assert "--runtime-revision v1.6.0-verify-auto" in out


def test_k2f_runs_splash_150():
    out = show_arm("k2f")
    assert "splash-v1.5.0/bin/splash" in out and UKISAI in out and "--verify-rows auto" in out
    assert "--runtime-revision v1.5.0-verify-auto" in out


def test_k3g_runs_ista_on_160():
    out = show_arm("k3g")
    assert "splash-v1.6.0/bin/splash" in out and ISTA in out
    assert "--revision bba88856f8c3c0c9e40e45f82d05e228b814ac43" in out


def test_xargs_reach_the_server():
    for arm in ("k2f", "k2g", "k3f", "k3g"):
        assert "--verify-rows auto --max-memory 96G" in show_arm(arm, extra_env={"FLASHNEXT_SPLASH_XARGS": "--max-memory 96G"})


def test_xargs_do_not_reach_older_arms():
    assert "--max-memory" not in show_arm("k2a", extra_env={"FLASHNEXT_SPLASH_XARGS": "--max-memory 96G"})


def test_rc_and_k2c_default_stays_150():
    for arm in ("rc2", "k2c2a"):
        assert "splash-v1.5.0/bin/splash" in show_arm(arm)


def test_tag_override_moves_rc_and_k2c():
    for arm in ("rc2", "k2c2a"):
        out = show_arm(arm, extra_env={"FLASHNEXT_SPLASH_TAG": "1.6.0"})
        assert "splash-v1.6.0/bin/splash" in out and "splash-v1.5.0" not in out
    assert "--runtime-revision v1.6.0-verify-auto" in show_arm("k2c2a", extra_env={"FLASHNEXT_SPLASH_TAG": "1.6.0"})
