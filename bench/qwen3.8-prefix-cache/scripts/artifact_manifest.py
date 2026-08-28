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


def model_records(
    specifications: list[tuple[str, str, Path]],
) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for model_id, revision, directory in specifications:
        key = (model_id, revision)
        if key in seen:
            raise ValueError(f"duplicate artifact specification: {model_id}@{revision}")
        if not directory.is_dir():
            raise ValueError(f"artifact directory does not exist: {directory}")
        files = artifact_records(directory)
        if not files:
            raise ValueError(f"artifact directory has no files: {directory}")
        weight_paths = {
            record["path"]
            for record in files
            if Path(record["path"]).suffix in {".safetensors", ".gguf", ".bin"}
        }
        if not weight_paths:
            raise ValueError(f"artifact directory has no model weights: {directory}")
        for index_path in sorted(directory.rglob("*.safetensors.index.json")):
            try:
                index = json.loads(index_path.read_text(encoding="utf-8"))
                indexed_weights = set(index["weight_map"].values())
            except (OSError, json.JSONDecodeError, KeyError, AttributeError) as error:
                raise ValueError(f"invalid weight index: {index_path}") from error
            missing = sorted(
                weight
                for weight in indexed_weights
                if not (index_path.parent / weight).is_file()
            )
            if missing:
                raise ValueError(
                    f"artifact directory has missing indexed weight files: {directory}"
                )
        seen.add(key)
        models.append(
            {"model_id": model_id, "revision": revision, "files": files}
        )
    return models


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record local hashes for pinned Qwen3.8 artifacts."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mlx-dir", type=Path)
    parser.add_argument("--mlx-revision")
    parser.add_argument("--gguf-dir", type=Path)
    parser.add_argument("--gguf-revision")
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        nargs=3,
        metavar=("MODEL_ID", "REVISION", "DIRECTORY"),
        help="repeatable pinned model specification",
    )
    args = parser.parse_args()

    legacy = (
        args.mlx_dir,
        args.mlx_revision,
        args.gguf_dir,
        args.gguf_revision,
    )
    if any(value is not None for value in legacy) and not all(
        value is not None for value in legacy
    ):
        parser.error("legacy MLX/GGUF arguments must be provided together")
    specifications: list[tuple[str, str, Path]] = []
    if all(value is not None for value in legacy):
        specifications.extend(
            [
                (
                    "ddalcu/Qwen3.8-27B-MLX-Serve-8bit",
                    args.mlx_revision,
                    args.mlx_dir,
                ),
                ("unsloth/Qwen3.8-27B-GGUF", args.gguf_revision, args.gguf_dir),
            ]
        )
    specifications.extend(
        (model_id, revision, Path(directory))
        for model_id, revision, directory in args.model
    )
    if not specifications:
        parser.error("provide legacy MLX/GGUF arguments or at least one --model")
    try:
        models = model_records(specifications)
    except ValueError as error:
        parser.error(str(error))

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
