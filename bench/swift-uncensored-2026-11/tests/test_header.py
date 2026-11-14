import json
import struct

import pytest
from conftest import HERE, load

RECORDED = HERE / "results" / "gguf-headers-20261113.json"


@pytest.fixture(scope="module")
def gh():
    return load("gguf_header")


def _s(text):
    b = text.encode()
    return struct.pack("<Q", len(b)) + b


def _gguf(tensors):
    out = b"GGUF" + struct.pack("<IQQ", 3, len(tensors), 1)
    out += _s("general.architecture") + struct.pack("<I", 8) + _s("qwen4exp")
    for name, dims, ty in tensors:
        out += _s(name) + struct.pack("<I", len(dims)) + b"".join(struct.pack("<Q", d) for d in dims)
        out += struct.pack("<IQ", ty, 0)
    return out


def test_parse_reads_synthetic_gguf(gh):
    ver, kv, ts = gh.parse(_gguf([("blk.0.hc_attn_inject.weight", [10240, 4], 30), ("output.weight", [8, 2], 14)]))
    assert ver == 3 and kv["general.architecture"] == "qwen4exp"
    assert ts == [("blk.0.hc_attn_inject.weight", [10240, 4], 30), ("output.weight", [8, 2], 14)]


def test_parse_asks_for_more_bytes_on_a_cut_header(gh):
    with pytest.raises(gh.Need):
        gh.parse(_gguf([("output.weight", [8, 2], 14)])[:-4])


@pytest.mark.parametrize("ty", ["BF16", "F32", "Q8_0"])
def test_check_accepts_float_inject(gh, ty):
    fam = {"blk.N.hc_attn_inject.weight": {ty: 48}, "blk.N.hc_ffn_inject.weight": {ty: 48},
           "blk.N.ffn_gate_exps.weight": {"IQ3_S": 48}}
    assert gh.check(fam) == []


def test_check_refuses_quantized_inject(gh):
    fam = {"blk.N.hc_attn_inject.weight": {"IQ4_XS": 48}, "blk.N.hc_ffn_inject.weight": {"BF16": 48}}
    bad = gh.check(fam)
    assert len(bad) == 1 and "blk.N.hc_attn_inject.weight" in bad[0] and "IQ4_XS" in bad[0]


def test_check_refuses_a_mixed_family(gh):
    assert len(gh.check({"blk.N.hc_ffn_inject.weight": {"BF16": 47, "Q4_K": 1}})) == 1


def test_check_matches_recorded_headers(gh):
    rec = json.loads(RECORDED.read_text())
    passed = {label for label, v in rec.items() if gh.check(v["fam"]) == []}
    assert passed == {"k2", "k8", "hh-swift-iq3s", "sc-iq3s"}
    assert set(rec) - passed == {"jj-iq4xs", "jj-iq3s", "fz-iq4xs", "xop-q4km"}


def test_check_refuses_f16_indexer(gh):
    # Splash 1.6.1 on the rig, 2026-11-13: "GGUF tensors this build cannot load: indexer.q_proj.weight (F16) in 12
    # layers, indexer.k_proj.weight (F16) in 12 layers" for the jackjusko IQ4_XS-plus pack. Every pack that loads has BF16.
    ok = {"blk.N.indexer.q_proj.weight": {"BF16": 12}, "blk.N.indexer.k_proj.weight": {"BF16": 12},
          "blk.N.ple_conv1d.weight": {"F16": 1}}
    assert gh.check(ok) == []
    bad = gh.check({"blk.N.indexer.q_proj.weight": {"F16": 12}, "blk.N.indexer.k_proj.weight": {"F16": 12}})
    assert len(bad) == 2 and all("F16 x12" in line for line in bad)


def test_check_cli_exits_1_on_a_violation(gh, capsys):
    def scan(repo, rev, pat):
        fam = {"blk.N.hc_attn_inject.weight": {"IQ4_XS" if repo == "bad/repo" else "F32": 48}}
        return ["a.gguf"], {}, fam, 48
    assert gh.main(["check", "ok|good/repo|main|*.gguf"], scan_fn=scan) == 0
    assert gh.main(["check", "ok|good/repo|main|*.gguf", "x|bad/repo|main|*.gguf"], scan_fn=scan) == 1
    assert "x: blk.N.hc_attn_inject.weight" in capsys.readouterr().out
