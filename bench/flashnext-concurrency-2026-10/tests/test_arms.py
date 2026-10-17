from conftest import run_candidate_print


def test_arm_w1c2_prints_max_concurrent():
    out = run_candidate_print("w1c2", "32768")
    assert "--max-concurrent 2" in out and "--prefix-cache-mem 16GB" in out
    assert "exec: " in out and "run-parallel-probes.sh --streams 2" in out and "--aux" not in out


def test_arm_w1c2m8_prefix_cache_8gb():
    out = run_candidate_print("w1c2m8", "131072")
    assert "--max-concurrent 2" in out and "--prefix-cache-mem 8GB" in out and "--aux" in out


def test_arm_w1c2L_asymmetric_contexts():
    out = run_candidate_print("w1c2L", "262144")
    assert "--max-concurrent 2" in out and "--contexts 262144,32768" in out and "--aux" in out


def test_arm_w1c2m4q8_cache_and_kv_quant():
    out = run_candidate_print("w1c2m4q8", "262144")
    assert "--prefix-cache-mem 4GB" in out and "--kv-quant 8" in out and "--max-concurrent 2" in out


def test_arm_w1c1_has_no_extra_args():
    out = run_candidate_print("w1c1", "32768")
    assert "--max-concurrent" not in out and "--streams 1" in out


def test_arm_w1c4a_four_streams_with_aux():
    out = run_candidate_print("w1c4a", "32768")
    assert "--max-concurrent 4" in out and "--streams 4" in out and "--aux" in out


def test_arm_exec_passes_revisions_and_output_dir():
    out = run_candidate_print("w1c2a", "32768")
    assert "--runtime-revision v26.10.1" in out
    assert "--model-revision 13839b7191e0973ff9fea58232267c395b76c6c0" in out
    assert "--reasoning-effort xhigh" in out and "--out " in out and "--repeat 3" in out


def test_command_line_exec_wins_over_arm_exec():
    out = run_candidate_print("w1c2", "32768", "--exec", "echo custom")
    assert "exec: echo custom" in out and "run-parallel-probes.sh" not in out


def test_run_arm_writes_into_this_campaign():
    from conftest import HERE, SCRIPTS, run
    out = run("bash", SCRIPTS / "run-arm.sh", "w1c2a", "32768", "--repeat", "3", "--tag", "e1", "--print").stdout
    assert f"--out {HERE / 'results'}" in out
