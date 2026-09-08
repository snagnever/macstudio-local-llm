#!/usr/bin/env python3
"""Download the two pinned Flash-Next test packs; preserve resumable partials."""
import json
import os
from pathlib import Path
import shutil
import time

from huggingface_hub import snapshot_download

CAMPAIGN = Path(__file__).resolve().parents[1]
SOURCE = CAMPAIGN / "results/download-candidates-20260904-source.json"
STATUS = CAMPAIGN / "logs/download-candidates-20260904-status.json"
RECEIPT = CAMPAIGN / "results/download-candidates-20260904.json"
ROOT = Path.home() / ".cache/local-llms/qwen3.8-prefix-cache"


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def main():
    manifest = json.loads(SOURCE.read_text())
    receipt = []
    for repo, metadata in manifest.items():
        files = [
            f for f in metadata["siblings"]
            if not (
                "DS4-Q4" in repo and f["rfilename"].endswith(".gguf")
                and not (f["rfilename"].endswith("-MTP.gguf") or "-PLE-" in f["rfilename"])
            )
        ]
        total = sum(f["size"] for f in files)
        destination = ROOT / (repo.replace("/", "-") + "-" + metadata["sha"])
        if shutil.disk_usage(ROOT).free < total + 50 * 1024**3:
            raise RuntimeError("Insufficient free disk space including 50 GiB reserve")
        state = {"pid": os.getpid(), "state": "downloading", "repo": repo,
                 "revision": metadata["sha"], "local_dir": str(destination),
                 "bytes_expected": total, "started_at_unix": time.time()}
        save(STATUS, state)
        print("START", repo, total, flush=True)
        for attempt in range(1, 6):
            try:
                snapshot_download(repo_id=repo, revision=metadata["sha"],
                                  local_dir=str(destination),
                                  allow_patterns=[f["rfilename"] for f in files],
                                  max_workers=8)
                break
            except Exception as error:
                print("RETRY", attempt, type(error).__name__, flush=True)
                if attempt == 5:
                    state.update(state="failed", error_type=type(error).__name__)
                    save(STATUS, state)
                    raise
                time.sleep(30)
        for f in files:
            if (destination / f["rfilename"]).stat().st_size != f["size"]:
                raise RuntimeError("File size mismatch: " + f["rfilename"])
        receipt.append({"repo": repo, "revision": metadata["sha"],
                        "local_dir": str(destination), "bytes": total,
                        "files": [{"path": f["rfilename"], "size": f["size"],
                                   "lfs_sha256": (f.get("lfs") or {}).get("sha256")}
                                  for f in files],
                        "validation": "all selected files present; sizes match pinned Hub metadata",
                        "completed_at_unix": time.time()})
        save(RECEIPT, receipt)
        print("COMPLETE", repo, flush=True)
    save(STATUS, {"state": "complete", "completed_at_unix": time.time(),
                  "receipt": str(RECEIPT)})
    print("ALL COMPLETE", flush=True)


if __name__ == "__main__":
    main()
