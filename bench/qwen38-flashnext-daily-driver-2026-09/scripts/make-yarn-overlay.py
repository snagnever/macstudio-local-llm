#!/usr/bin/env python3
"""Build a YaRN-patched config.json overlay for an MTPLX model pack.

MTPLX 2.11.2's qwen4_exp model code implements static YaRN rope scaling
correctly (see task-11-yarn-mapping.md), but there is no serve-time flag,
env var, or settings file that injects rope_type/factor/
original_max_position_embeddings into it — the only way to exercise that
code path is to bake those keys into the model directory's config.json
before MTPLX loads it.

This script does that without touching the source pack: it creates a
sibling directory (same basename as the source, so run-mtplx.sh's
MODEL_ROOT/MODEL_NAME-MODEL_REVISION lookup still finds it when pointed at
the overlay root) containing symlinks to every file/subdirectory of the
source pack except config.json and .cache, plus a patched config.json and a
real, empty .cache directory of its own.

.cache is deliberately NOT a symlink: MTPLX's hf_loader treats
<model dir>/.cache as writable hub bookkeeping (lock files, download
metadata), so a symlinked .cache would make the overlay write through into
the source pack the moment the server touched it.

No server is started. This only creates symlinks and writes one JSON file.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

# Fixed per the c4 512K capacity-probe design: the pack's native
# max_position_embeddings, used as YaRN's "original" length regardless of
# --ctx (the target length we are extending *to*).
ORIGINAL_MAX_POSITION_EMBEDDINGS = 262144

REFUSED_ANCESTOR_NAME = "qwen3.8-prefix-cache"


class OverlayError(RuntimeError):
    pass


def _refuses_dst_root(dst_root: Path) -> bool:
    """oMLX and MTPLX both auto-discover every subdirectory under
    ~/.cache/local-llms/qwen3.8-prefix-cache/ as a servable model pack, so an
    overlay root that lives inside a directory named qwen3.8-prefix-cache
    would get picked up as if it were a real, independent pack. Refuse by
    path-component name rather than resolving symlinks, so this also fires
    for a not-yet-created destination."""
    parts = Path(os.path.expanduser(str(dst_root))).absolute().parts
    return REFUSED_ANCESTOR_NAME in parts


def _find_rope_container(config: dict[str, Any]) -> dict[str, Any]:
    """Locate the dict that holds the rope-scaling block the qwen4_exp model
    code reads, mirroring MTPLX's own config shape: text_config.rope_parameters
    (confirmed against the real Youssofal Flash-Next MTPLX pack). Falls back
    to a top-level rope_parameters/rope_scaling block for a pack shaped
    differently, so the script does not silently no-op on an unexpected
    layout."""
    text_config = config.get("text_config")
    if isinstance(text_config, dict) and isinstance(
        text_config.get("rope_parameters"), dict
    ):
        return text_config
    if isinstance(config.get("rope_parameters"), dict):
        return config
    if isinstance(text_config, dict) and isinstance(
        text_config.get("rope_scaling"), dict
    ):
        return text_config
    if isinstance(config.get("rope_scaling"), dict):
        return config
    raise OverlayError(
        "could not find a rope_parameters/rope_scaling block in config.json "
        "(checked top level and text_config)"
    )


def _rope_key(container: dict[str, Any]) -> str:
    return "rope_parameters" if "rope_parameters" in container else "rope_scaling"


def patch_config(config: dict[str, Any], factor: float, ctx: int) -> dict[str, Any]:
    """Return a deep-copied, patched config. Never mutates the input."""
    patched = copy.deepcopy(config)

    container = _find_rope_container(patched)
    key = _rope_key(container)
    rope = dict(container[key])  # preserve mrope_section, rope_theta, etc.
    rope["rope_type"] = "yarn"
    rope["factor"] = factor
    rope["original_max_position_embeddings"] = ORIGINAL_MAX_POSITION_EMBEDDINGS
    container[key] = rope

    # max_position_embeddings must be raised at the same level(s) the model
    # code (TextConfig) and MTPLX's _resolve_context_window() model_max scan
    # read from. The model code reads text_config.max_position_embeddings;
    # _resolve_context_window scans both the top level and text_config and
    # takes the max sane candidate, so raising it in text_config alone is
    # sufficient for both. Only touch a level that already carries the key,
    # to avoid inventing new top-level keys in an unfamiliar pack shape.
    touched_max = False
    if "max_position_embeddings" in container:
        container["max_position_embeddings"] = ctx
        touched_max = True
    if "max_position_embeddings" in patched:
        patched["max_position_embeddings"] = ctx
        touched_max = True
    if not touched_max:
        # container is where rope lives; put max_position_embeddings there
        # too so the model code (which reads it alongside rope_parameters)
        # sees the raised value.
        container["max_position_embeddings"] = ctx

    return patched


def _is_correct_symlink(link: Path, expected_target: Path) -> bool:
    if not link.is_symlink():
        return False
    try:
        return Path(os.readlink(link)) == expected_target
    except OSError:
        return False


def _ensure_real_empty_cache_dir(path: Path) -> None:
    """Give the overlay its own real, empty .cache instead of symlinking the
    source pack's. If an earlier (buggy) build left a symlink here, replace
    only the symlink entry itself -- unlink() removes the directory-entry,
    never the target it used to point at, so the source pack's real .cache
    (and whatever MTPLX has written into it) is never touched."""
    if path.is_symlink():
        path.unlink()
    if path.exists():
        if path.is_dir():
            return  # already a real dir (idempotent rerun); leave contents alone
        raise OverlayError(f"refusing to replace non-directory path: {path}")
    path.mkdir(parents=True)


def make_overlay(src: Path, dst_root: Path, factor: float, ctx: int) -> Path:
    src = Path(src)
    dst_root = Path(dst_root)

    if not src.is_dir():
        raise OverlayError(f"--src is not a directory: {src}")
    if _refuses_dst_root(dst_root):
        raise OverlayError(
            f"refusing --dst-root {dst_root}: it lives inside a directory named "
            f"{REFUSED_ANCESTOR_NAME!r}, which oMLX/MTPLX auto-discover as a "
            "model root; pick an overlay root outside it."
        )

    src_abs = src.absolute()
    dst = dst_root / src.name
    dst.mkdir(parents=True, exist_ok=True)

    for entry in sorted(src_abs.iterdir()):
        if entry.name == "config.json":
            continue
        link = dst / entry.name
        if entry.name == ".cache":
            _ensure_real_empty_cache_dir(link)
            continue
        if link.exists() or link.is_symlink():
            if _is_correct_symlink(link, entry):
                continue
            raise OverlayError(
                f"refusing to overwrite existing non-matching path: {link}"
            )
        link.symlink_to(entry, target_is_directory=entry.is_dir())

    src_config_path = src_abs / "config.json"
    src_config = json.loads(src_config_path.read_text())
    patched = patch_config(src_config, factor=factor, ctx=ctx)

    dst_config_path = dst / "config.json"
    dst_config_path.write_text(json.dumps(patched, indent=2, sort_keys=True) + "\n")

    return dst


def _print_report(dst: Path, factor: float, ctx: int) -> None:
    config = json.loads((dst / "config.json").read_text())
    container = _find_rope_container(config)
    key = _rope_key(container)
    rope = container[key]
    print(f"overlay: {dst}")
    print(
        "rope: "
        f"type={rope.get('rope_type')} factor={rope.get('factor')} "
        f"original_max_position_embeddings={rope.get('original_max_position_embeddings')}"
    )
    print(f"max_position_embeddings: {container.get('max_position_embeddings')}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a YaRN-patched config.json overlay (symlink farm + one "
            "patched config.json) for an MTPLX qwen4_exp model pack."
        )
    )
    parser.add_argument("--src", required=True, help="source model pack directory")
    parser.add_argument(
        "--dst-root",
        required=True,
        help="overlay root; the overlay pack is created at <dst-root>/<basename of src>",
    )
    parser.add_argument("--factor", required=True, type=float, help="YaRN factor")
    parser.add_argument(
        "--ctx", required=True, type=int, help="target max_position_embeddings"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        dst = make_overlay(
            src=Path(args.src).expanduser(),
            dst_root=Path(args.dst_root).expanduser(),
            factor=args.factor,
            ctx=args.ctx,
        )
    except OverlayError as exc:
        print(f"make-yarn-overlay: {exc}", file=sys.stderr)
        return 65
    _print_report(dst, args.factor, args.ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
