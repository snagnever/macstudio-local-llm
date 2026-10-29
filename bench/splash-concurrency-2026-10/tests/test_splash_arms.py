from conftest import HERE, SCRIPTS, run, run_candidate_print

SPLASH_150 = "splash-v1.5.0/bin/splash serve --model ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS"
REV = "--revision 0142554c963a8653912c0c8283f05f13f63653f3"


def test_arm_k2c1_is_k2a_on_splash_150_with_one_stream():
    out = run_candidate_print("k2c1", "32768")
    assert SPLASH_150 in out and REV in out and "--port 8585" in out and "--verify-rows auto" in out
    assert "--idle-release off" in out and "--offline" in out and "--max-context 32768" in out
    assert "--max-concurrent" not in out
    assert "run-parallel-probes.sh --streams 1 " in out and "--aux" not in out
    assert "--runtime splash" in out and "--runtime-revision v1.5.0-verify-auto " in out
    assert "--status-url http://127.0.0.1:8585/status" in out


def test_arm_k2c2a_two_streams_with_aux():
    out = run_candidate_print("k2c2a", "131072")
    assert "--streams 2 --aux" in out and "--serialize" not in out and "--max-concurrent" not in out


def test_arm_k2c2_and_k2c4_have_no_aux():
    assert "--aux" not in run_candidate_print("k2c2", "32768")
    out = run_candidate_print("k2c4", "32768")
    assert "--streams 4" in out and "--aux" not in out


def test_arm_k2c3a_and_k2c4a_streams():
    assert "--streams 3 --aux" in run_candidate_print("k2c3a", "131072")
    assert "--streams 4 --aux" in run_candidate_print("k2c4a", "32768")


def test_arm_k2c1x2_serializes_on_the_client():
    out = run_candidate_print("k2c1x2", "32768")
    assert "--streams 2 --aux --serialize" in out


def test_arm_k2c2L_asymmetric_and_k2c2LL_symmetric():
    out = run_candidate_print("k2c2L", "262144")
    assert "--contexts 262144,32768" in out and "--max-context 262144" in out
    out = run_candidate_print("k2c2LL", "262144")
    assert "--contexts" not in out and "--streams 2 --aux" in out and "--state-format" not in out


def test_arm_k2c2Ls_state_bf16():
    out = run_candidate_print("k2c2Ls", "262144")
    assert "--verify-rows auto --state-format bf16" in out and "-state-bf16" in out


def test_arm_decode_share_and_verify_variants():
    out = run_candidate_print("k2c2ad1", "131072")
    assert "--decode-share 1.0" in out and "v1.5.0-verify-auto-ds1.0" in out
    out = run_candidate_print("k2c2ad0", "131072")
    assert "--decode-share 0" in out and "v1.5.0-verify-auto-ds0" in out
    out = run_candidate_print("k2c2v", "131072")
    assert "--verify-rows all" in out and "v1.5.0-verify-all" in out and "--decode-share" not in out


def test_arm_w1zc_runs_on_mlx_serve_26103():
    out = run_candidate_print("w1zc2a", "32768")
    assert "mlx-serve-v26.10.3/mlx-serve" in out and "--max-concurrent 2" in out
    assert "--streams 2 --aux" in out and "--runtime-revision v26.10.3-mc2" in out
    out = run_candidate_print("w1zc1", "131072")
    assert "mlx-serve-v26.10.3/mlx-serve" in out and "--max-concurrent" not in out and "--streams 1 " in out


def test_previous_campaign_arm_keeps_26101():
    out = run_candidate_print("w1c2a", "32768")
    assert "mlx-serve-v26.10.1/mlx-serve" in out and "--runtime-revision v26.10.1-mc2" in out


def test_run_arm_writes_into_this_campaign():
    out = run("bash", SCRIPTS / "run-arm.sh", "k2c2a", "32768", "--repeat", "3", "--tag", "e1", "--print").stdout
    assert f"--out {HERE / 'results'}" in out
