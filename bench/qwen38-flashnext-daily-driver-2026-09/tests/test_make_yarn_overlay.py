from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "make-yarn-overlay.py"
)
_spec = importlib.util.spec_from_file_location("make_yarn_overlay", _SCRIPT_PATH)
make_yarn_overlay = importlib.util.module_from_spec(_spec)
sys.modules["make_yarn_overlay"] = make_yarn_overlay
_spec.loader.exec_module(make_yarn_overlay)  # type: ignore[union-attr]

make_overlay = make_yarn_overlay.make_overlay
OverlayError = make_yarn_overlay.OverlayError


def _build_fake_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "packs" / "Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-deadbeef"
    pack.mkdir(parents=True)
    config = {
        "architectures": ["Qwen4ExpForConditionalGeneration"],
        "model_type": "qwen4_exp",
        "text_config": {
            "max_position_embeddings": 262144,
            "model_type": "qwen4_exp",
            "rope_parameters": {
                "mrope_interleaved": True,
                "mrope_section": [11, 11, 10],
                "partial_rotary_factor": 0.25,
                "rope_theta": 10000000,
                "rope_type": "default",
            },
            "vocab_size": 151936,
        },
        "vision_config": {"depth": 32},
    }
    (pack / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    (pack / "model.safetensors").write_text("fake-weights")
    (pack / "sub").mkdir()
    (pack / "sub" / "inner.bin").write_text("fake-inner")
    (pack / ".cache").mkdir()
    (pack / ".cache" / "hub-lock.json").write_text("fake-hub-bookkeeping")
    return pack


def test_make_overlay_symlinks_and_patches_rope(tmp_path):
    src = _build_fake_pack(tmp_path)
    src_config_before = (src / "config.json").read_text()
    dst_root = tmp_path / "overlays" / "yarn2"

    dst = make_overlay(src=src, dst_root=dst_root, factor=2.0, ctx=524288)

    assert dst == dst_root / src.name

    # Non-config entries are symlinks pointing at the source, files and dirs alike.
    weights_link = dst / "model.safetensors"
    assert weights_link.is_symlink()
    assert Path(os.readlink(weights_link)) == (src / "model.safetensors").absolute()

    sub_link = dst / "sub"
    assert sub_link.is_symlink()
    assert Path(os.readlink(sub_link)) == (src / "sub").absolute()
    # Symlinked subdirectory is not recursed into — it's a single link, and
    # its contents are reachable only through the source.
    assert (sub_link / "inner.bin").read_text() == "fake-inner"

    # config.json itself is a real, independent file, never a symlink.
    dst_config_path = dst / "config.json"
    assert not dst_config_path.is_symlink()

    # Source config is untouched.
    assert (src / "config.json").read_text() == src_config_before

    patched = json.loads(dst_config_path.read_text())
    rope = patched["text_config"]["rope_parameters"]
    assert rope["rope_type"] == "yarn"
    assert rope["factor"] == 2.0
    assert rope["original_max_position_embeddings"] == 262144
    # Untouched rope fields survive.
    assert rope["mrope_section"] == [11, 11, 10]
    assert rope["rope_theta"] == 10000000
    assert patched["text_config"]["max_position_embeddings"] == 524288
    # Unrelated keys preserved.
    assert patched["vision_config"] == {"depth": 32}


def test_make_overlay_leaves_correct_existing_symlink(tmp_path):
    src = _build_fake_pack(tmp_path)
    dst_root = tmp_path / "overlays" / "yarn2"

    make_overlay(src=src, dst_root=dst_root, factor=2.0, ctx=524288)
    # Second call is idempotent: existing correct symlinks are left alone.
    dst = make_overlay(src=src, dst_root=dst_root, factor=2.0, ctx=524288)
    assert (dst / "model.safetensors").is_symlink()


def test_make_overlay_refuses_dst_root_inside_prefix_cache(tmp_path):
    src = _build_fake_pack(tmp_path)
    dst_root = tmp_path / "qwen3.8-prefix-cache" / "yarn2"

    with pytest.raises(OverlayError):
        make_overlay(src=src, dst_root=dst_root, factor=2.0, ctx=524288)


def test_cache_dir_is_real_not_symlink(tmp_path):
    src = _build_fake_pack(tmp_path)
    src_cache_file = src / ".cache" / "hub-lock.json"
    src_cache_before = src_cache_file.read_text()
    dst_root = tmp_path / "overlays" / "yarn2"

    dst = make_overlay(src=src, dst_root=dst_root, factor=2.0, ctx=524288)

    overlay_cache = dst / ".cache"
    assert overlay_cache.exists()
    assert not overlay_cache.is_symlink()
    assert overlay_cache.is_dir()
    assert list(overlay_cache.iterdir()) == []

    # A write MTPLX makes into the overlay's .cache must never reach the source.
    assert src_cache_file.read_text() == src_cache_before

    # Migration: an overlay built by the older, buggy script left .cache as a
    # symlink into the source. Simulate that, then rebuild and confirm it is
    # replaced by a real empty dir without touching the source file.
    overlay_cache.rmdir()
    overlay_cache.symlink_to((src / ".cache").absolute(), target_is_directory=True)
    assert overlay_cache.is_symlink()

    make_overlay(src=src, dst_root=dst_root, factor=2.0, ctx=524288)

    assert overlay_cache.exists()
    assert not overlay_cache.is_symlink()
    assert overlay_cache.is_dir()
    assert list(overlay_cache.iterdir()) == []
    assert src_cache_file.exists()
    assert src_cache_file.read_text() == src_cache_before


def test_rebuild_with_new_factor_rewrites_config(tmp_path):
    src = _build_fake_pack(tmp_path)
    dst_root = tmp_path / "overlays" / "yarn2"

    dst = make_overlay(src=src, dst_root=dst_root, factor=2.0, ctx=524288)
    config = json.loads((dst / "config.json").read_text())
    rope = config["text_config"]["rope_parameters"]
    assert rope["factor"] == 2.0
    assert config["text_config"]["max_position_embeddings"] == 524288

    dst = make_overlay(src=src, dst_root=dst_root, factor=2.5, ctx=655360)
    config = json.loads((dst / "config.json").read_text())
    rope = config["text_config"]["rope_parameters"]
    assert rope["factor"] == 2.5
    assert config["text_config"]["max_position_embeddings"] == 655360
