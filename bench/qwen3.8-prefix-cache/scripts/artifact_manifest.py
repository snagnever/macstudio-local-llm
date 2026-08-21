#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or ".cache" in relative.parts:
            continue
        records.append(
            {
                "path": relative.as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record local hashes for pinned Qwen3.8 artifacts."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mlx-dir", required=True, type=Path)
    parser.add_argument("--mlx-revision", required=True)
    parser.add_argument("--gguf-dir", required=True, type=Path)
    parser.add_argument("--gguf-revision", required=True)
    args = parser.parse_args()

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": [
            {
                "model_id": "ddalcu/Qwen3.8-27B-MLX-Serve-8bit",
                "revision": args.mlx_revision,
                "files": artifact_records(args.mlx_dir),
            },
            {
                "model_id": "unsloth/Qwen3.8-27B-GGUF",
                "revision": args.gguf_revision,
                "files": artifact_records(args.gguf_dir),
            },
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
