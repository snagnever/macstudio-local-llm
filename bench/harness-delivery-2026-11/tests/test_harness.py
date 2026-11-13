import json
from pathlib import Path

import pytest

from harness import HARNESSES, Target, command, prepare, version

T = Target("mac-studio", 8585, "ukisai/Swift:IQ4_XS")


@pytest.mark.parametrize("name", HARNESSES)
def test_env_isolates_home(name, tmp_path):
    c = command(name, "do it", tmp_path / "repo", tmp_path / "home", T)
    assert c.env["HOME"] == str(tmp_path / "home") and c.cwd == tmp_path / "repo"
    assert c.env["XDG_CONFIG_HOME"] == str(tmp_path / "home/.config")
    rest = " ".join(c.argv) + " ".join(v for k, v in c.env.items() if k != "PATH")
    assert str(Path.home()) not in rest.replace(str(tmp_path), "")


@pytest.mark.parametrize("name", HARNESSES)
def test_env_drops_parent_variables(name, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")
    monkeypatch.setenv("OPENAI_API_KEY", "real-key")
    c = command(name, "x", tmp_path, tmp_path / "h", T)
    assert "real-key" not in c.env.values()


@pytest.mark.parametrize("name", HARNESSES)
def test_prompt_is_one_argv_item(name, tmp_path):
    assert "line 1\nline 2" in command(name, "line 1\nline 2", tmp_path, tmp_path / "h", T).argv


def test_tools_bin_goes_first_on_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_TOOLS_BIN", "/opt/tools/bin")
    assert command("pi", "x", tmp_path, tmp_path / "h", T).env["PATH"].startswith("/opt/tools/bin:")


def test_claude_has_no_turn_cap_and_uses_xhigh(tmp_path):
    c = command("claude", "x", tmp_path, tmp_path / "h", T)
    assert "--max-turns" not in c.argv and c.env["CLAUDE_CODE_EFFORT_LEVEL"] == "xhigh"
    assert c.env["ANTHROPIC_BASE_URL"] == "http://mac-studio:8585"
    assert c.env["CLAUDE_CONFIG_DIR"] == str(tmp_path / "h/.claude")
    assert c.env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "131072"
    assert c.argv[c.argv.index("--permission-mode") + 1] == "bypassPermissions"


def test_opencode_config_has_provider_variant_and_permissions(tmp_path):
    c = command("opencode", "x", tmp_path, tmp_path / "h", T)
    cfg = json.loads(c.env["OPENCODE_CONFIG_CONTENT"])
    assert cfg["provider"]["rig"]["options"]["baseURL"] == "http://mac-studio:8585/v1"
    assert cfg["provider"]["rig"]["models"][T.model_id]["limit"]["context"] == 131072
    assert cfg["agent"]["build"]["variant"] == "xhigh"
    assert cfg["permission"] == {"edit": "allow", "bash": "allow"}
    assert c.argv[:2] == ["opencode", "run"] and c.argv[c.argv.index("--model") + 1] == "rig/" + T.model_id


def test_pi_uses_xhigh_and_ignores_user_resources(tmp_path):
    c = command("pi", "x", tmp_path, tmp_path / "h", T)
    assert c.argv[c.argv.index("--thinking") + 1] == "xhigh"
    assert {"--no-extensions", "--no-skills", "--no-context-files"} <= set(c.argv)


def test_dsh_runs_the_headless_profile_in_its_own_home(tmp_path):
    c = command("dsh", "x", tmp_path, tmp_path / "h", T)
    assert c.argv[:3] == ["dsh", "--profile", "headless"]
    assert c.env["DSH_HOME"] == str(tmp_path / "h/.dsh") and c.env["DSH_TELEMETRY_MODE"] == "DISABLED"


def test_prepare_writes_only_inside_home(tmp_path):
    for name in HARNESSES:
        prepare(name, tmp_path / "h", T)
    assert "reasoningEffort: xhigh" in (tmp_path / "h/.dsh/settings.yaml").read_text()
    models = json.loads((tmp_path / "h/.pi/agent/models.json").read_text())
    assert models["providers"]["rig"]["baseUrl"] == "http://mac-studio:8585/v1"
    assert models["providers"]["rig"]["models"][0]["id"] == T.model_id
    assert (tmp_path / "h/.claude").is_dir()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["h"]


def test_bin_override_replaces_the_executable(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_BIN_PI", "/x/fake.py")
    assert command("pi", "x", tmp_path, tmp_path / "h", T).argv[0] == "/x/fake.py"


def test_version_of_a_missing_binary_is_unknown(monkeypatch):
    monkeypatch.setenv("HARNESS_BIN_PI", "/nonexistent/pi")
    assert version("pi") == "unknown"


def test_unknown_harness_raises():
    with pytest.raises(KeyError):
        command("codex", "x", Path("."), Path("."), T)
