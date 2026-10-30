from conftest import SCRIPTS, run, run_candidate_print

SPLASH_150 = "splash-v1.5.0/bin/splash serve --model ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS"


def test_rc1_is_k2c1_server_with_one_claude_session():
    out = run_candidate_print("rc1", "131072", env_extra={"FLASHNEXT_CC_TASK": "c"})
    assert SPLASH_150 in out and "--port 8585" in out and "--max-context 131072" in out
    assert "--verify-rows auto" in out and "--idle-release off" in out and "--offline" in out
    assert "--decode-share" not in out and "--max-concurrent" not in out and "cache_probe" not in out
    assert "run-claude-pair.sh" in out and "--sessions 1 --task c" in out and "--proxy 8686" in out and "--tag rc1r1" in out
    assert "--out " in out and "claude-code-concurrency-2026-11/results" not in out  # results dir comes from run-arm.sh


def test_rc1_task_defaults_to_a():
    assert "--sessions 1 --task a" in run_candidate_print("rc1", "131072")


def test_rc2_pairs_cd_by_default_and_ab_on_request():
    assert "--sessions 2 --pair c,d" in run_candidate_print("rc2", "131072")
    assert "--pair a,b" in run_candidate_print("rc2", "131072", env_extra={"FLASHNEXT_CC_PAIR": "a,b"})


def test_rc2s_adds_subagents_and_rc2d_adds_decode_share():
    out = run_candidate_print("rc2s", "131072")
    assert "--pair c,d --subagents" in out and "--decode-share" not in out
    out = run_candidate_print("rc2d", "131072")
    assert "--decode-share 1.0" in out and "--subagents" not in out and "--pair c,d" in out


def test_rm_arms_run_on_mlx_serve_26103_without_max_concurrent():
    out = run_candidate_print("rm2", "131072")
    assert "mlx-serve-v26.10.3" in out and "--port 11234" in out and "--max-concurrent" not in out
    assert "13839b7191e0973ff9fea58232267c395b76c6c0" in out and "--sessions 2 --pair c,d" in out
    assert "--subagents" in run_candidate_print("rm2s", "131072")
    assert "--sessions 1 --task a" in run_candidate_print("rm1", "131072", env_extra={"FLASHNEXT_CC_TASK": "a"})


def test_run_arm_points_results_and_logs_at_this_campaign():
    out = run("bash", SCRIPTS / "run-arm.sh", "rc2", "131072", "--tag", "r1", "--print").stdout
    assert "claude-code-concurrency-2026-11/results" in out
