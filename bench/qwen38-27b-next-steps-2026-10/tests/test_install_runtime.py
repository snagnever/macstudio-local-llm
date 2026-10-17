import os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALL = ROOT / "bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh"


def _run(*args, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("QWEN38_", "MLX_TAG", "SPLASH_TAG", "INSTALL_"))}
    e.update(env)
    return subprocess.run(["bash", str(INSTALL), *args, "--print"], capture_output=True, text=True, env=e)


def test_mlx_tag_override_changes_destination():
    out = _run("mlx-serve", MLX_TAG="v26.10.2")
    assert out.returncode == 0, out.stderr
    assert "mlx-serve-v26.10.2" in out.stdout
    assert "pre-release" not in out.stdout


def test_default_mlx_tag_is_unchanged():
    out = _run("mlx-serve")
    assert out.returncode == 0, out.stderr
    assert "mlx-serve-v26.10.2-pre-release.1" in out.stdout


def test_splash_target_prints_release_and_dest():
    out = _run("splash")
    assert out.returncode == 0, out.stderr
    assert "incoai/splash" in out.stdout
    assert "1.3.1" in out.stdout
    assert "splash-1.3.1-arm64-macos26.tar.gz" in out.stdout
    assert "/download/v1.3.1/" not in out.stdout
    assert "splash-v1.3.1" in out.stdout
