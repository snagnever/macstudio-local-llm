import importlib.util
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN_ARM = HERE / "scripts" / "run-arm.sh"
ISTA = "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF:IQ1_M"
ISTA_REV = "bba88856f8c3c0c9e40e45f82d05e228b814ac43"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "AB_", "SPLASH_", "TBENCH_"))}
    env.update(extra or {})
    return env


def show(cand, ctx="32768", *args):
    return subprocess.run(["bash", str(RUN_ARM), cand, ctx, *args, "--print"], capture_output=True, text=True,
                          env=_env(), check=True).stdout


def server(out):
    lines = out.splitlines()
    return lines[[i for i, l in enumerate(lines) if l.startswith("launcher:")][0] + 1]


def _longctx():
    spec = importlib.util.spec_from_file_location("longctx_probe", HERE / "scripts" / "longctx_probe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_k3_arms_are_the_ista_gguf_with_the_k2_flags():
    k3, k3a, k3ab = server(show("k3")), server(show("k3a")), server(show("k3ab"))
    assert f"--model {ISTA} " in k3 and f"--revision {ISTA_REV} " in k3
    assert k3.endswith("--verify-rows all") and k3a.endswith("--verify-rows auto")
    assert k3ab.endswith("--verify-rows auto --kv-format bf16")
    strip = lambda s: s.split("--revision")[1].split(" ", 2)[2]
    assert strip(k3a) == strip(server(show("k2a")))


def test_k3ma_is_k3a_on_the_main_build():
    out = show("k3ma")
    assert "--runtime-revision v1.4.0-main-3135ab4-verify-auto " in out
    assert server(out).replace("splash-main-3135ab4", "BIN") == server(show("k3a")).replace("splash-v1.4.0", "BIN")


def test_k2as_adds_bf16_state():
    assert server(show("k2as")) == server(show("k2a")) + " --state-format bf16"


def test_w1zq4_is_w1q4_on_26103():
    out = show("w1zq4", "524288", "--yarn", "2.0")
    old = show("w1q4", "524288", "--yarn", "2.0")
    assert "--runtime-revision v26.10.3-yarn2.0-kv4 " in out
    assert server(out).replace("mlx-serve-v26.10.3", "BIN") == server(old).replace("mlx-serve-v26.10.1", "BIN")
    assert "--kv-quant 4 " in server(out)


def test_r1zy_is_r1z_with_yarn_and_4bit_kv():
    out = show("r1zy", "1000000", "--yarn", "3.815")
    assert "mbrown-uno-Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX-50fa68c" in out
    assert "--kv-quant 4 " in server(out) and '\\"max_position_embeddings\\":1000000' in server(out)
    assert "--ctx-size 1000000 " in server(out)


def test_splash_1m_band_uses_1000000():
    assert "--max-context 1000000" in server(show("k2a", "1000000"))


def test_longctx_prompt_leaves_room_for_output():
    lc = _longctx()
    prefix, questions = lc.build_case(1000000, seed=0)
    longest = max(len(q["question"]) for q in questions)
    assert lc.estimate_tokens(prefix) + lc.estimate_tokens("x" * longest) <= 1000000 - 8192
    assert lc.estimate_tokens(prefix) >= 0.85 * 1000000
    for q in questions:
        if q["kind"] == "lookup":
            assert str(q["answer"]) in prefix


def test_longctx_question_mix_and_sums():
    lc = _longctx()
    prefix, questions = lc.build_case(32768, seed=0)
    kinds = [q["kind"] for q in questions]
    assert kinds.count("lookup") == 3 and kinds.count("sum") == 3 and kinds.count("hop") == 2
    records = lc.parse_records(prefix)
    assert len(records) == 16
    for q in questions:
        if q["kind"] == "sum":
            assert q["answer"] == sum(n for src, n, dst in records if src == q["account"])


def test_longctx_is_deterministic():
    lc = _longctx()
    assert lc.build_case(32768, seed=0) == lc.build_case(32768, seed=0)
    assert lc.build_case(32768, seed=0)[1] != lc.build_case(32768, seed=1)[1]


def test_longctx_scores_exact_answers():
    lc = _longctx()
    assert lc.score("The total is 1,234 units.", 1234)
    assert lc.score("ANSWER: ORION", "ORION")
    assert not lc.score("The total is 1235.", 1234)


def test_tbench_runner_uses_21_and_caffeinate():
    out = subprocess.run(["bash", str(HERE / "scripts" / "run-tbench-remote.sh"), "k2a", "http://rig:8585/v1",
                          "--print"], capture_output=True, text=True, env=_env({"TBENCH_MODEL_ID": "m"}),
                         check=True).stdout
    for part in ("caffeinate -i harbor run", "--dataset terminal-bench/terminal-bench-2-1", "--agent terminus-2",
                 "-n 1", "--agent-timeout-multiplier 1.0", "--environment-build-timeout-multiplier 3.0",
                 "--job-name tb21-k2a", "--model openai/m"):
        assert part in out, part


def test_hold_arm_waits_for_the_flag_file():
    out = subprocess.run(["bash", str(HERE / "scripts" / "hold-arm.sh"), "k2a", "262144", "logs/tb21-k2a.done",
                          "--print"], capture_output=True, text=True, env=_env(), check=True).stdout
    assert "-hold.jsonl" in out and f"until [ -f {HERE}/logs/tb21-k2a.done ]" in out


def tasks(*args, extra=None):
    return subprocess.run(["bash", str(HERE / "scripts" / "run-tasks.sh"), *args, "--dry-run"],
                          capture_output=True, text=True, env=_env(extra), check=True).stdout


def test_run_tasks_t1_bands_and_k3_switch():
    out = tasks("t1")
    assert "k1a:8192:3:lc k2a:8192:3:lc w1z:8192:3:lc" in out
    assert "k1a:262144:3:lc k2a:262144:3:lc" in out and "k3a" not in out
    assert "k3a:8192:3:lc k3a:32768:3:lc k3a:131072:3:lc" in tasks("t1", extra={"K3": "1"})


def test_run_tasks_t2_sweep_then_chosen_kv():
    assert "k2a:524288:1:sw k2ab:524288:1:sw w1zq4:524288:1:sw:2.0" in tasks("t2a")
    out = tasks("t2b", extra={"SW": "k2ab"})
    assert "k2ab:524288:3:lc w1zq4:524288:3:lc:2.0 k1a:524288:3:lc" in out


def test_run_tasks_t3_uses_1000000():
    assert "k2a:1000000:1:lc k1a:1000000:1:lc" in tasks("t3", extra={"SW": "k2a"})


def test_longctx_arm_runs_every_band_on_one_server():
    out = subprocess.run(["bash", str(HERE / "scripts" / "longctx-arm.sh"), "k2a", "524288", "131072", "524288",
                          "--print"], capture_output=True, text=True, env=_env(), check=True).stdout
    assert "--max-context 524288" in server(out) and "-lc-q.jsonl" in out
    assert "for b in 131072 524288" in out and "longctx/k2a-524288-$b.jsonl" in out
    # Single quotes kept $b literal: every band of a server went to one file named "<arm>-<ctx>-$b.jsonl".
    assert "-$b.jsonl'" not in out


def test_run_tasks_t4_quality_matrix():
    out = tasks("t4", extra={"SW": "k2a"})
    assert "run-battery.sh w1z q262 --ctx 262144 --suites humaneval gpqa livecodebench if jdhodges veerman" in out
    assert "run-battery.sh k2a q1m --ctx 1000000" in out and "run-battery.sh k2a q512 --ctx 524288" in out
    assert "longctx-arm.sh w1zq4 524288 131072 262144 524288 --yarn 2.0" in out
    assert "longctx-arm.sh k2a 1000000 131072 262144 524288 1000000" in out
    assert "toolcall-probe.sh k2a --sessions 20 --suffix t4 --max-tokens 2048" in out
    assert "k3a" not in out


def test_run_tasks_t5_gsq_on_mlx_serve():
    out = tasks("t5")
    assert "r1z:8192:3:lc r1z:262144:3:lc" in out
    assert "run-battery.sh r1z q262 --ctx 262144" in out
    assert "toolcall-probe.sh r1z --sessions 20" in out
    # The user limited the GSQ to 256K (2026-10-25): no YaRN arm, longctx on the 262144 server.
    assert "longctx-arm.sh r1z 262144 131072 262144" in out and "r1zy" not in out


def test_run_tasks_t5m_gsq_on_the_splash_main_build():
    out = tasks("t5m")
    assert "k3ma:8192:3:lc k3ma:262144:3:lc" in out and "idle-gate.sh" in out
    assert "run-battery.sh" not in out and "longctx-arm.sh" not in out


def test_longctx_fill_shrinks_small_contexts():
    lc = _longctx()
    assert len(lc.build_case(32768, fill=0.8)[0]) < 0.9 * len(lc.build_case(32768, fill=0.97)[0])


def test_longctx_respects_measured_ratio():
    lc = _longctx()
    prefix, questions = lc.build_case(32768, chars_per_token=2.4)
    assert len(prefix) / 2.4 <= 32768 - 8192


def test_longctx_calibrates_chars_per_token_from_usage():
    lc = _longctx()
    seen = {}

    def fake_chat(base_url, payload, timeout):
        seen["max_tokens"] = payload["max_tokens"]
        return {"usage": {"prompt_tokens": len(payload["messages"][0]["content"]) // 2}}

    assert abs(lc.calibrate("u", "m", chat=fake_chat) - 2.0) < 0.05
    assert seen["max_tokens"] == 1
