#!/usr/bin/env python3
"""Copy the GGUF shards of a pack and store the F16 QSA indexer projections as BF16, without loss.

Splash 1.6.1 refuses indexer.q_proj.weight and indexer.k_proj.weight in F16 and loads them in BF16. The base model
is BF16, so each F16 value of these tensors must fit BF16 exactly; a value that does not fit stops the recast and
leaves no output file. F16 and BF16 have the same size, so only the tensor type and the tensor bytes change.
usage: gguf_recast.py <source dir> <output dir>
"""
import shutil
import struct
import subprocess
import sys
from array import array
from pathlib import Path

F16, BF16 = 1, 30
FLOAT_BYTES = {0: 4, 1: 2, 30: 2}
INDEXER = ("indexer.q_proj.weight", "indexer.k_proj.weight")
SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<B", 10: "<Q", 11: "<q", 12: "<d"}


def f16_to_bf16(raw):
    """The same values as BF16 bytes. ValueError if a value needs more mantissa bits than BF16 has."""
    n = len(raw) // 2
    bits = array("I")
    bits.frombytes(struct.pack(f"<{n}f", *struct.unpack(f"<{n}e", raw)))
    if sys.byteorder != "little":
        bits.byteswap()
    if any(b & 0xFFFF for b in bits):
        raise ValueError("an F16 value does not fit BF16 exactly")
    out = array("H", (b >> 16 for b in bits))
    if sys.byteorder != "little":
        out.byteswap()
    return out.tobytes()


def layout(b):
    """(tensors, data_start) of a GGUF whose whole header is in b. Each tensor is a dict with name, dims, type,
    type_pos (file position of the type field), offset (from data_start) and nbytes. struct.error or IndexError
    means b ends inside the header."""
    pos = [4]

    def rd(fmt):
        v = struct.unpack_from(fmt, b, pos[0])[0]
        pos[0] += struct.calcsize(fmt)
        return v

    def text():
        n = rd("<Q")
        if pos[0] + n > len(b):
            raise IndexError("short header")
        pos[0] += n
        return b[pos[0] - n:pos[0]].decode("utf-8", "replace")

    def value(t):
        if t == 8:
            return text()
        if t == 9:
            et, n = rd("<I"), rd("<Q")
            if et in SCALAR:
                pos[0] += struct.calcsize(SCALAR[et]) * n
            else:
                for _ in range(n):
                    value(et)
            return None
        return rd(SCALAR[t])

    if b[:4] != b"GGUF":
        raise ValueError("not a GGUF file")
    rd("<I")
    n_tensors, n_kv = rd("<Q"), rd("<Q")
    kv = {}
    for _ in range(n_kv):
        key = text()
        kv[key] = value(rd("<I"))
    tensors = []
    for _ in range(n_tensors):
        name = text()
        dims = [rd("<Q") for _ in range(rd("<I"))]
        type_pos = pos[0]
        tensors.append({"name": name, "dims": dims, "type": rd("<I"), "type_pos": type_pos, "offset": rd("<Q")})
    if pos[0] > len(b):
        raise IndexError("short header")
    align = kv.get("general.alignment") or 32
    by_offset = sorted(tensors, key=lambda t: t["offset"])
    for t, nxt in zip(by_offset, by_offset[1:] + [None]):
        count = 1
        for d in t["dims"]:
            count *= d
        t["nbytes"] = count * FLOAT_BYTES[t["type"]] if t["type"] in FLOAT_BYTES else (
            nxt["offset"] - t["offset"] if nxt else None)
    return tensors, -(-pos[0] // align) * align


def read_layout(path):
    size = 8 << 20
    while True:
        with open(path, "rb") as f:
            head = f.read(size)
        try:
            return layout(head)
        except (struct.error, IndexError):
            if len(head) < size:
                raise
            size *= 2


def recast_file(src, dst):
    """Copy src to dst with the F16 indexer projections stored as BF16. Returns the number of tensors changed."""
    src, dst = Path(src), Path(dst)
    tensors, start = read_layout(src)
    todo = [t for t in tensors if t["type"] == F16 and t["name"].endswith(INDEXER)]
    new = []
    with open(src, "rb") as f:
        for t in todo:
            f.seek(start + t["offset"])
            new.append(f16_to_bf16(f.read(t["nbytes"])))
    dst.parent.mkdir(parents=True, exist_ok=True)
    # cp -c clones the file on APFS: only the changed blocks take new disk space.
    if subprocess.run(["cp", "-c", str(src), str(dst)], capture_output=True).returncode != 0:
        shutil.copyfile(src, dst)
    with open(dst, "r+b") as f:
        for t, raw in zip(todo, new):
            f.seek(t["type_pos"])
            f.write(struct.pack("<I", BF16))
            f.seek(start + t["offset"])
            f.write(raw)
    return len(todo)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 64
    src, dst = Path(argv[0]), Path(argv[1])
    files = sorted(src.glob("*.gguf"))
    if not files:
        print(f"no .gguf in {src}", file=sys.stderr)
        return 66
    for f in files:
        print(f"{f.name}: {recast_file(f, dst / f.name)} tensors recast", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
