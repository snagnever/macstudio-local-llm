import pytest
from conftest import show_arm

UNSLOTH_V31 = "084c631ac221016019d6e0a863afe92d90edd3b0"
BIN = {"f": ("splash-v1.5.0/bin/splash", "v1.5.0"), "g": ("splash-v1.6.0/bin/splash", "v1.6.0")}
ARMS = {
    "k1": ("unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ4_XS", "766911a6b7369840a91dbcd95f9f997acaab6cd6"),
    "k4": ("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF:Q2_0", "ed59f92082b1e93c0e96d60a8b11aab089b52f09"),
    "k5": ("unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ3_XXS", UNSLOTH_V31),
    "k6": ("unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ4_XS", UNSLOTH_V31),
}


@pytest.mark.parametrize("stem", ARMS)
@pytest.mark.parametrize("suffix", BIN)
def test_arm_pins_pack_revision_and_release(stem, suffix):
    out = show_arm(stem + suffix)
    hub, rev = ARMS[stem]
    path, tag = BIN[suffix]
    assert path in out and hub in out and f"--revision {rev}" in out
    assert "--verify-rows auto" in out and f"--runtime-revision {tag}-verify-auto" in out


@pytest.mark.parametrize("arm", ["k1f", "k1g", "k4f", "k4g", "k5f", "k5g", "k6f", "k6g"])
def test_xargs_reach_the_new_arms(arm):
    assert "--max-memory 96G" in show_arm(arm, {"FLASHNEXT_SPLASH_XARGS": "--max-memory 96G"})


def test_old_k1a_keeps_its_release():
    out = show_arm("k1a")
    assert "--revision 766911a6b7369840a91dbcd95f9f997acaab6cd6" in out
    assert "--max-memory" not in show_arm("k1a", {"FLASHNEXT_SPLASH_XARGS": "--max-memory 96G"})
    assert "splash-v1.6.0" not in out and "splash-v1.5.0" not in out
