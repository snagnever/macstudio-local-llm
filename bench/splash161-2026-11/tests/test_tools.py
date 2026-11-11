import importlib.util
import json
import os
import subprocess
import sys

import pytest
from conftest import HERE, SCRIPTS, load

SPLASH16 = HERE.parent / "splash16-2026-11"


def _ms(max_ms, total_ms, samples):
    return {"p50": 0, "p95": 0, "p99": 0, "max": max_ms, "total": total_ms, "samples": samples}


def _status(cw_max, cw_total, cw_samples, gaps=0, gap_ms=0, pages_cache=7):
    return {"schema_version": 8, "kv": {"pages_cache": pages_cache},
            "metrics": {"ttft_parts_ms": {"claim_wait": _ms(cw_max, cw_total, cw_samples)},
                        "decode_gap_causes": {"prefill_unit": {"gaps": gaps, "ms": gap_ms}}}}


@pytest.fixture(scope="module")
def sc():
    return load("summarize_claims")


def test_claims_summary_reads_last_status_per_boot(sc, tmp_path):
    p = tmp_path / "s.jsonl"
    rows = [{"t": 1, "status": _status(10000, 10000, 1)},
            {"t": 2, "status": _status(30300, 61400, 4, gaps=169, gap_ms=137500)},
            {"t": 3, "status": _status(0, 0, 0)},  # sample counter drops: a new boot
            {"t": 4, "status": _status(0, 0, 2, pages_cache=3)}]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    boots = sc.summarize([p])
    assert [b["claim_wait_max_s"] for b in boots] == [30.3, 0.0]
    assert [b["claim_wait_total_s"] for b in boots] == [61.4, 0.0]
    assert boots[0]["prefill_unit_gaps"] == 169 and boots[0]["prefill_unit_s"] == 137.5
    assert boots[1]["pages_cache"] == 3


def test_claims_summary_accepts_status_without_metrics(sc, tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text(json.dumps({"kind": "status", "t": 1, "schema_version": 6, "kv": {"pages_cache": 2},
                             "metrics": None}) + "\n")
    boots = sc.summarize([p])
    assert boots[0]["claim_wait_max_s"] is None
    assert "–" in sc.to_markdown(boots)


def test_run_seq_records_exit_69_and_continues(tmp_path):
    fake = tmp_path / "scripts"
    fake.mkdir()
    (fake / "run-seq.sh").write_text((SCRIPTS / "run-seq.sh").read_text())
    (fake / "run-arm.sh").write_text('#!/bin/bash\necho "ran $1"\n[ "$1" = bad ] && exit 69\nexit 0\n')
    env = dict(os.environ, RUN_SEQ_GAP_S="0")
    r = subprocess.run(["bash", str(fake / "run-seq.sh"), "bad:32768:1:h1", "good:32768:1:h1"], capture_output=True,
                       text=True, env=env, timeout=60)
    assert r.returncode == 0
    assert "end bad@32768 rc=69" in r.stdout
    assert "ran good" in r.stdout and "end good@32768 rc=0" in r.stdout


@pytest.fixture(scope="module")
def ac():
    spec = importlib.util.spec_from_file_location("api_contract", SPLASH16 / "scripts" / "api_contract.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["api_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_contract_accepts_161_as_16x(ac, monkeypatch, tmp_path):
    sys.path.insert(0, str(SPLASH16 / "tests"))
    from test_contract import Server  # the 1.6.0 stand-in of the splash16 tests
    monkeypatch.setattr(ac, "http_call", lambda base, timeout: Server())
    out = tmp_path / "c.jsonl"
    monkeypatch.setattr(sys, "argv", ["api_contract.py", "--base-url", "http://x", "--model", "m", "--version", "1.6.1",
                                      "--out", str(out)])
    assert ac.main() == 0
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(r["pass"] is True for r in rows if r["check"] != "C7")
