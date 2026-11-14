import struct

import pytest
from conftest import load
from test_header import _s


@pytest.fixture(scope="module")
def rc():
    return load("gguf_recast")


@pytest.fixture(scope="module")
def gh():
    return load("gguf_header")


def bf16(values):
    return b"".join(struct.pack("<f", v)[2:] for v in values)


def gguf_file(path, tensors, alignment=32):
    """tensors: (name, dims, type, data bytes). Returns the file with the data section aligned."""
    head = b"GGUF" + struct.pack("<IQQ", 3, len(tensors), 2)
    head += _s("general.architecture") + struct.pack("<I", 8) + _s("qwen4exp")
    head += _s("general.alignment") + struct.pack("<II", 4, alignment)
    data, off = b"", 0
    for name, dims, ty, raw in tensors:
        head += _s(name) + struct.pack("<I", len(dims)) + b"".join(struct.pack("<Q", d) for d in dims)
        head += struct.pack("<IQ", ty, off)
        pad = -len(raw) % alignment
        data += raw + b"\0" * pad
        off += len(raw) + pad
    head += b"\0" * (-len(head) % alignment)
    path.write_bytes(head + data)
    return path


EXACT = [0.0, 1.0, -2.5, 0.15625, 1024.0, -0.0078125]


def test_f16_to_bf16_is_exact_for_bf16_values(rc):
    assert rc.f16_to_bf16(struct.pack("<6e", *EXACT)) == bf16(EXACT)


def test_f16_to_bf16_refuses_a_value_bf16_cannot_hold(rc):
    with pytest.raises(ValueError):
        rc.f16_to_bf16(struct.pack("<2e", 1.0, 1.0009765625))  # 1 + 2**-10 needs 10 mantissa bits; BF16 has 7


def test_recast_rewrites_only_the_f16_indexer_tensors(rc, gh, tmp_path):
    other = bytes(range(64))
    src = gguf_file(tmp_path / "a.gguf", [
        ("blk.3.indexer.q_proj.weight", [3, 2], 1, struct.pack("<6e", *EXACT)),
        ("blk.3.ffn_down.weight", [64], 24, other),
        ("blk.3.indexer.k_proj.weight", [2, 3], 1, struct.pack("<6e", *reversed(EXACT))),
        ("blk.3.ple_conv1d.weight", [6], 1, struct.pack("<6e", *EXACT)),
    ])
    before = src.read_bytes()
    dst = tmp_path / "out" / "a.gguf"
    assert rc.recast_file(src, dst) == 2
    assert src.read_bytes() == before
    out = dst.read_bytes()
    assert len(out) == len(before)
    _, kv, ts = gh.parse(out)
    assert [(n, t) for n, _, t in ts] == [("blk.3.indexer.q_proj.weight", 30), ("blk.3.ffn_down.weight", 24),
                                          ("blk.3.indexer.k_proj.weight", 30), ("blk.3.ple_conv1d.weight", 1)]
    tensors, start = rc.layout(out)
    blob = {t["name"]: out[start + t["offset"]: start + t["offset"] + t["nbytes"]] for t in tensors}
    assert blob["blk.3.indexer.q_proj.weight"] == bf16(EXACT)
    assert blob["blk.3.indexer.k_proj.weight"] == bf16(list(reversed(EXACT)))
    assert blob["blk.3.ffn_down.weight"] == other
    assert blob["blk.3.ple_conv1d.weight"] == struct.pack("<6e", *EXACT)
    diff = sum(a != b for a, b in zip(before, out))
    assert 0 < diff <= 2 * 4 + 2 * 12  # two type fields and two 12-byte tensors, nothing else


def test_recast_leaves_no_file_when_a_value_is_not_exact(rc, tmp_path):
    src = gguf_file(tmp_path / "a.gguf", [("blk.0.indexer.q_proj.weight", [2], 1, struct.pack("<2e", 1.0, 1.0009765625))])
    dst = tmp_path / "out" / "a.gguf"
    with pytest.raises(ValueError):
        rc.recast_file(src, dst)
    assert not dst.exists()


def test_recast_copies_a_file_without_indexer_tensors(rc, tmp_path):
    src = gguf_file(tmp_path / "a.gguf", [("blk.0.ffn_down.weight", [64], 24, bytes(64))])
    dst = tmp_path / "out" / "a.gguf"
    assert rc.recast_file(src, dst) == 0 and dst.read_bytes() == src.read_bytes()
