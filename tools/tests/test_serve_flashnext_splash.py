import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / "tools" / "scripts" / "serve-flashnext-splash.sh"
SWIFT = "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS"
SWIFT_REV = "0142554c963a8653912c0c8283f05f13f63653f3"


def _print(*args, extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("FLASHNEXT_SPLASH_")}
    env.update(extra or {})
    return subprocess.run(["bash", str(LAUNCHER), *args, "--print"], capture_output=True, text=True,
                          env=env, check=True).stdout


def test_default_is_k2a_at_256k():
    # bench/splash-longctx-2026-10: k2a = Swift 1.5 GGUF IQ4_XS on Splash 1.4.0, --verify-rows auto, KV int8.
    out = _print()
    assert f"serve --model {SWIFT} --host 0.0.0.0 --port 8585 --max-context 262144 --revision {SWIFT_REV} " in out
    assert "splash-v1.4.0/bin/splash" in out
    assert out.rstrip().endswith("--idle-release off --language-only --no-webui --offline --verify-rows auto")
    assert "--kv-format" not in out


def test_512k_and_1m_profiles_use_the_measured_contexts():
    # Etapa 2 (6.7 s, folga 10.1 GB) and Etapa 3 (9.3 s, folga 16.9 GB), quality in Etapa 4.
    assert "--max-context 524288 " in _print("512k")
    assert "--max-context 1000000 " in _print("1m")


def test_every_profile_keeps_idle_release_off():
    for profile in ("256k", "512k", "1m"):
        assert "--idle-release off" in _print(profile)


def test_unknown_profile_is_refused():
    run = subprocess.run(["bash", str(LAUNCHER), "2m", "--print"], capture_output=True, text=True)
    assert run.returncode == 64


def test_port_override():
    assert "--port 9000 " in _print(extra={"FLASHNEXT_SPLASH_PORT": "9000"})
