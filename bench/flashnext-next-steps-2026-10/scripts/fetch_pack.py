#!/usr/bin/env python3
"""Download one Hugging Face pack pinned to a full revision into the rig's model root.

The local directory is ``<root>/<repo with / -> ->-<full sha>``, the layout every launcher of the rig
expects. Before downloading, files whose LFS SHA256 matches a file of ``--link-from`` (same relative path)
are hardlinked instead of downloaded; the hash of the local file is computed, never assumed. The download
refuses to start when free disk is below the bytes still to fetch plus ``--reserve-gb``. A receipt (repo,
full sha, files, sizes, LFS hashes, linked files) is appended to ``--receipt``.

Needs ``huggingface_hub`` (the rig has it in ~/LocalProjects/local-llms/.venv).
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path.home() / ".cache/local-llms/qwen3.8-prefix-cache"
CAMPAIGN = Path(__file__).resolve().parents[1]


def lfs_sha(sibling) -> str | None:
    lfs = getattr(sibling, "lfs", None)
    if lfs is None:
        return None
    if isinstance(lfs, dict):
        return lfs.get("sha256")
    return getattr(lfs, "sha256", None)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(64 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def select(files: list[dict], include: list[str]) -> list[dict]:
    if not include:
        return files
    return [f for f in files if any(fnmatch.fnmatch(f["path"], pat) for pat in include)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--revision", required=True, help="short or full commit sha, or a branch name")
    ap.add_argument("--include", action="append", default=[], help="fnmatch pattern; repeat for several")
    ap.add_argument("--link-from", type=Path, help="older local pack whose identical files are hardlinked")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--reserve-gb", type=float, default=50.0)
    ap.add_argument("--receipt", type=Path, default=CAMPAIGN / "results" / "downloads.json")
    ap.add_argument("--dry-run", action="store_true", help="resolve and print the plan; no hashing, no download")
    a = ap.parse_args(argv)

    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().model_info(a.repo, revision=a.revision, files_metadata=True)
    sha = info.sha
    files = select([{"path": s.rfilename, "size": int(s.size or 0), "lfs_sha256": lfs_sha(s)}
                    for s in info.siblings], a.include)
    if not files:
        print(f"fetch_pack: no file of {a.repo}@{sha} matches {a.include}", file=sys.stderr)
        return 66
    dest = a.root / f"{a.repo.replace('/', '-')}-{sha}"
    total = sum(f["size"] for f in files)
    print(f"repo={a.repo} revision={a.revision} sha={sha}")
    print(f"dest={dest}")
    print(f"files={len(files)} total_gb={total / 1e9:.1f}")

    linked: list[str] = []
    if a.link_from:
        for f in files:
            src, dst = a.link_from / f["path"], dest / f["path"]
            if not f["lfs_sha256"] or not src.is_file() or src.stat().st_size != f["size"]:
                continue
            if a.dry_run:
                print(f"link candidate (size match, hash not checked in dry run): {f['path']}")
                continue
            if dst.exists():
                continue
            if sha256_file(src) != f["lfs_sha256"]:
                print(f"same size, different hash, will download: {f['path']}")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.link(src, dst)
            linked.append(f["path"])
            print(f"hardlinked: {f['path']}")

    def present(f: dict) -> bool:
        p = dest / f["path"]
        return p.is_file() and p.stat().st_size == f["size"]

    remaining = [f for f in files if not present(f)]
    need = sum(f["size"] for f in remaining)
    a.root.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(a.root).free
    print(f"to_download_gb={need / 1e9:.1f} free_gb={free / 1e9:.1f} reserve_gb={a.reserve_gb}")
    if a.dry_run:
        print("DEST=" + str(dest))
        return 0
    if free < need + a.reserve_gb * 1e9:
        print("fetch_pack: not enough free disk (need download + reserve)", file=sys.stderr)
        return 75
    if remaining:
        for attempt in range(1, 6):
            try:
                snapshot_download(repo_id=a.repo, revision=sha, local_dir=str(dest),
                                  allow_patterns=[f["path"] for f in remaining], max_workers=8)
                break
            except Exception as error:  # network errors: retry, the download resumes
                print(f"retry {attempt}: {type(error).__name__}: {error}", flush=True)
                if attempt == 5:
                    raise
                time.sleep(30)
    bad = [f["path"] for f in files if not present(f)]
    if bad:
        print(f"fetch_pack: size mismatch or missing: {bad}", file=sys.stderr)
        return 70
    receipt = json.loads(a.receipt.read_text()) if a.receipt.exists() else []
    receipt.append({"repo": a.repo, "requested_revision": a.revision, "revision": sha, "local_dir": str(dest),
                    "bytes": total, "files": files, "hardlinked": linked,
                    "validation": "all selected files present; sizes match pinned Hub metadata",
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.write_text(json.dumps(receipt, indent=1) + "\n")
    print("DEST=" + str(dest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
