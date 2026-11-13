import pytest
from conftest import FIXTURES, run_arm, show_arm

TAG = {"FLASHNEXT_SPLASH_TAG": "1.6.1"}
PACKS = {
    "z0": ("ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF:IQ3_S", "99bb8f7f95c7aa7b24a36a7786a4f657b30f5d3d"),
    "z1": ("jackjusko/Swift-1.5-Flash-Next-Heretic-ReverseEngineer:IQ4_XS", "bd3bca068a544d459cf42902bf21a0fac00ec853"),
    "z2": ("huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF:swift-IQ3_S",
           "cbc7fba13f1939ac3fa42b18d77ccf43847d74ef"),
    "z3": ("SC117/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF:IQ3_S",
           "3db919a964b1f0ae0d1000ba7be90b3e38b1f7a3"),
}


@pytest.mark.parametrize("pack", sorted(PACKS))
def test_z_arms_print_pinned_weights(pack):
    model, rev = PACKS[pack]
    out = show_arm(pack + "h")
    assert "splash-v1.6.1/bin/splash" in out and model in out and f"--revision {rev}" in out
    assert "--verify-rows auto" in out and "--runtime-revision v1.6.1-verify-auto" in out
    assert "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS" not in out


def test_z_arms_take_xargs():
    out = show_arm("z1h", extra_env={"FLASHNEXT_SPLASH_XARGS": "--ple-memory off", "FLASHNEXT_SPLASH_REVX": "-ple-off"})
    assert "--verify-rows auto --ple-memory off" in out and "-verify-auto-ple-off " in out


@pytest.mark.parametrize("arm", ["k2h", "k8h"])
def test_k_arms_stay_the_same(arm):
    assert show_arm(arm) == (FIXTURES / f"print-{arm}-32768.txt").read_text()


def test_rc_arms_default_to_k2_weights():
    assert show_arm("rc2", "131072", extra_env=TAG) == (FIXTURES / "print-rc2-131072-161.txt").read_text()


@pytest.mark.parametrize("pack", ["z1", "z3"])
def test_rc_arms_take_pack(pack):
    model, rev = PACKS[pack]
    out = show_arm("rc2", "131072", extra_env=dict(TAG, FLASHNEXT_SPLASH_PACK=pack))
    assert model in out and f"--revision {rev}" in out and "splash-v1.6.1/bin/splash" in out
    assert "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS" not in out


def test_rc_pack_k2_is_the_default():
    assert show_arm("rc2", "131072", extra_env=dict(TAG, FLASHNEXT_SPLASH_PACK="k2")) == \
        (FIXTURES / "print-rc2-131072-161.txt").read_text()


def test_bad_pack_is_refused():
    assert run_arm("rc2", "131072", extra_env=dict(TAG, FLASHNEXT_SPLASH_PACK="z9")).returncode == 64
