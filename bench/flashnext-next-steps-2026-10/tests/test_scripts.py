import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SCRIPTS = HERE / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "AB_"))}
    env.update(extra or {})
    return env


def run(*args, env=None, check=True):
    return subprocess.run([*args], capture_output=True, text=True, env=env or _env(), check=check)


def test_run_seq_dry_run_and_bad_spec():
    out = run("bash", str(SCRIPTS / "run-seq.sh"), "--dry-run", "n2:32768:3:e1", "w1xq4:524288:3:e2:2.0").stdout
    assert out.splitlines() == ["bash run-arm.sh n2 32768 --repeat 3 --tag e1",
                                "bash run-arm.sh w1xq4 524288 --repeat 3 --tag e2 --yarn 2.0"]
    bad = run("bash", str(SCRIPTS / "run-seq.sh"), "--dry-run", "n2:32768:3:e1", "n2-32768", check=False)
    assert bad.returncode == 64 and "bad spec" in bad.stderr


def test_idle_gate_dry_run():
    out = run("bash", str(SCRIPTS / "idle-gate.sh"), "--dry-run").stdout
    assert "gpu < 50 C" in out and "free >= 82 GB" in out


def test_llama_launcher_mtp_flags(tmp_path):
    (tmp_path / "Qwen3.8-Flash-Next-IQ4_NL-00001-of-00002.gguf").write_text("")
    (tmp_path / "Qwen3.8-Flash-Next-IQ4_NL-00002-of-00002.gguf").write_text("")
    (tmp_path / "mtp-Qwen3.8-Flash-Next-Q8_0.gguf").write_text("")
    env = _env({"QWEN38_GGUF_DIR": str(tmp_path), "QWEN38_LLAMA_SERVER_BIN": "/opt/llama/llama-server"})
    gm = run("bash", str(SCRIPTS / "run-llama-flashnext.sh"), "GM", "--print", env=env).stdout
    assert "IQ4_NL-00001-of-00002.gguf" in gm
    assert "--spec-type draft-mtp" in gm and "mtp-Qwen3.8-Flash-Next-Q8_0.gguf" in gm
    assert "--parallel 1" in gm and "--kv-unified" not in gm
    gn = run("bash", str(SCRIPTS / "run-llama-flashnext.sh"), "GN", "--print", env=env).stdout
    assert "draft-mtp" not in gn


def test_battery_print_wires_ab_battery_and_loops():
    out = run("bash", str(SCRIPTS / "run-battery.sh"), "w1", "e5-smoke", "--suites", "humaneval",
              "--loops", "--print").stdout
    assert "ab-battery.sh" in out and "degeneration_sweep.py" in out and "vendor_t1_xhigh" in out
    assert "131072" in out


def test_think_turn_probe_dry_run_resends_only_in_resend_mode():
    out = run(sys.executable, str(SCRIPTS / "think_turn_probe.py"), "--dry-run").stdout.splitlines()
    rows = {json.loads(l)["mode"]: json.loads(l) for l in out}
    assert "reasoning_content" in rows["resend"]["assistant_keys"]
    assert "reasoning_content" not in rows["drop"]["assistant_keys"]
    assert rows["drop"]["tool_turn_roles"] == ["system", "user", "assistant", "tool"]


def test_agent_probe_dry_runs():
    for sub in ("contradiction", "charcount", "longsession", "effortswitch"):
        res = run(sys.executable, str(SCRIPTS / "agent_probes.py"), sub, "--dry-run")
        assert res.returncode == 0 and res.stdout.strip()


def test_contradiction_judge():
    import agent_probes as ap
    t = ap.make_turn(2, 1)
    good = ", ".join(t["expected"])
    assert ap.judge_turn(t, good, "stop", None)[0] == "ok"
    assert ap.judge_turn(t, good + ", main.py", "stop", None) == ("invented", ["main.py"])
    assert ap.judge_turn(t, "", "stop", None)[0] == "empty"
    assert ap.judge_turn(t, "", "stop", [{"id": "x"}])[0] == "tool_call"
    p = ap.make_turn(3, 1)
    assert ap.judge_turn(p, p["expected"][0], "stop", None)[0] == "ok"
    assert ap.judge_turn(p, "All tests passed.", "stop", None)[0] == "invented"
    assert len(ap.charcount_prompts()) == 20


def test_char_run_flags_bangs():
    import agent_probes as ap
    assert ap.CHAR_RUN.search("ok " + "!" * 25)
    assert not ap.CHAR_RUN.search("normal text!!!")


def _rec(arm, ctx, scenario, ttft, dec, hit=0.99, **kw):
    r = {"arm": arm, "context_target": ctx, "scenario": scenario, "ttft_ms": ttft * 1000, "decode_tps": dec,
         "cache_hit_ratio": hit, "finish_reason": "stop", "error": None, "correct": True, "runtime": "llama.cpp",
         "ram_peak_gb": 100.0, "swap_delta_gb": 0.0, "mem_free_min_gb": 3.0, "session_id": f"{arm}-{ctx}"}
    r.update(kw)
    return r


def test_decide_ratio_and_verdict(tmp_path):
    import decide
    for arm, tt in (("n2", 2.0), ("n2x", 1.5)):
        recs = [_rec(arm, 32768, s, tt if s == "tool_turn" else 0.2, 80.0) for s in ("identical", "append", "tool_turn")]
        recs.append(_rec(arm, 32768, "cold", 30.0, 70.0))
        (tmp_path / f"{arm}-32768-t1.0-e1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    rc = decide.main(["--results-dir", str(tmp_path), "--logs-dir", str(tmp_path), "--glob", "*-e1.jsonl",
                      "--base", "n2", "--cand", "n2x", "--ctx", "32768", "--threshold", "0.97"])
    assert rc == 0
    rc = decide.main(["--results-dir", str(tmp_path), "--logs-dir", str(tmp_path), "--glob", "*-e1.jsonl",
                      "--base", "n2", "--cand", "n2x", "--ctx", "32768", "--mode", "parity", "--threshold", "0.03"])
    assert rc == 1


def test_decide_needles_split_truncated_and_wrong(tmp_path, capsys):
    import decide
    recs = [_rec("o1x", 32768, "identical", 0.2, 60.0),
            _rec("o1x", 32768, "append", 0.2, 60.0, correct=False, finish_reason="length"),
            _rec("o1x", 32768, "tool_turn", 2.0, 60.0, correct=False),
            _rec("o1x", 32768, "cold", 30.0, 60.0)]
    (tmp_path / "o1x-32768-t1.0-e5.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    decide.main(["--results-dir", str(tmp_path), "--logs-dir", str(tmp_path), "--glob", "*-e5.jsonl"])
    assert "| 2/4 (1 trunc, 1 erro) |" in capsys.readouterr().out
