"""Command line, isolated environment and version of each coding harness.

Every harness runs non-interactive, with a temporary HOME that holds its whole configuration, reasoning effort
xhigh and a 131072-token context. Nothing here reads or writes the user's global configuration.
HARNESS_BIN_<NAME> replaces the executable (tests use it). HARNESS_TOOLS_BIN, when set, goes first on PATH.
HARNESS_SANDBOX=0 turns the macOS sandbox off (see sandboxed).
HARNESS_PASS_ENV is a comma-separated list of extra parent variables to pass through (tests use it).
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

HARNESSES = ("claude", "opencode", "dsh", "pi")
EFFORT = "xhigh"
CONTEXT = 131072
MAX_OUTPUT = 32768
PROVIDER = "rig"
PASSTHROUGH = ("LANG", "TERM")


@dataclass(frozen=True)
class Target:
    host: str
    port: int
    model_id: str

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass(frozen=True)
class Cmd:
    argv: list[str]
    env: dict[str, str]
    cwd: Path


def _bin(name: str) -> str:
    return os.environ.get(f"HARNESS_BIN_{name.upper()}", name)


def _base_env(home: Path) -> dict[str, str]:
    path = os.environ.get("PATH", "/usr/bin:/bin")
    tools = os.environ.get("HARNESS_TOOLS_BIN")
    env = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "XDG_DATA_HOME": str(home / ".local/share"), "XDG_CACHE_HOME": str(home / ".cache"),
           "XDG_STATE_HOME": str(home / ".local/state"), "PATH": f"{tools}:{path}" if tools else path}
    extra = [k for k in os.environ.get("HARNESS_PASS_ENV", "").split(",") if k]
    env.update({k: os.environ[k] for k in (*PASSTHROUGH, *extra) if k in os.environ})
    return env


def _opencode_config(target: Target) -> str:
    model = f"{PROVIDER}/{target.model_id}"
    agent = {"model": model, "variant": EFFORT}
    return json.dumps({
        "model": model,
        "provider": {PROVIDER: {
            "npm": "@ai-sdk/openai-compatible", "name": "rig",
            "options": {"baseURL": f"{target.url}/v1", "apiKey": "local"},
            "models": {target.model_id: {
                "name": target.model_id, "reasoning": True, "tool_call": True,
                "limit": {"context": CONTEXT, "output": MAX_OUTPUT},
                "variants": {EFFORT: {"reasoningEffort": EFFORT}}}}}},
        "agent": {"build": agent, "plan": agent},
        "permission": {"edit": "allow", "bash": "allow"},
    })


def _claude(prompt: str, home: Path, target: Target):
    env = {"ANTHROPIC_BASE_URL": target.url, "ANTHROPIC_AUTH_TOKEN": "local",
           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "CLAUDE_CODE_MAX_CONTEXT_TOKENS": str(CONTEXT),
           "CLAUDE_CODE_EFFORT_LEVEL": EFFORT, "CLAUDE_CONFIG_DIR": str(home / ".claude")}
    for var in ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                "ANTHROPIC_DEFAULT_OPUS_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"):
        env[var] = target.model_id
    argv = [_bin("claude"), "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--setting-sources", "project", "--strict-mcp-config", "--permission-mode", "bypassPermissions"]
    return argv, env


def _opencode(prompt: str, home: Path, target: Target):
    argv = [_bin("opencode"), "run", prompt, "--model", f"{PROVIDER}/{target.model_id}", "--pure"]
    return argv, {"OPENCODE_CONFIG_CONTENT": _opencode_config(target)}


def _dsh(prompt: str, home: Path, target: Target):
    env = {"DSH_HOME": str(home / ".dsh"), "RIG_API_KEY": "local", "DSH_TELEMETRY_MODE": "DISABLED"}
    return [_bin("dsh"), "--profile", "headless", prompt], env


def _pi(prompt: str, home: Path, target: Target):
    argv = [_bin("pi"), "-p", prompt, "--provider", PROVIDER, "--model", target.model_id, "--thinking", EFFORT,
            "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-context-files", "--offline"]
    return argv, {"PI_OFFLINE": "1"}


_BUILD = {"claude": _claude, "opencode": _opencode, "dsh": _dsh, "pi": _pi}


def command(name: str, prompt: str, repo: Path, home: Path, target: Target) -> Cmd:
    """The process to start for one session. The prompt is one argv item."""
    argv, extra = _BUILD[name](prompt, Path(home), target)
    return Cmd(argv=argv, env={**_base_env(Path(home)), **extra}, cwd=Path(repo))


SANDBOX_EXEC = "/usr/bin/sandbox-exec"
SECRET_DIRS = (".ssh", ".gnupg", ".aws", ".kube", ".docker", ".netrc", ".claude", ".claude-instances", ".claude.json",
               ".config", ".dsh", ".pi", ".codex", "Library/Keychains", "Library/Cookies",
               "Library/Application Support/Claude", "Library/Application Support/Google")


def _sandbox_profile(repo: Path, home: Path) -> str:
    """Allow by default; deny writes under /Users except the repository copy and the session HOME; deny reads
    of the user's credentials and harness configuration."""
    real = Path.home()
    q = lambda p: '"' + str(Path(p).resolve()).replace('"', '\\"') + '"'  # noqa: E731
    secrets = " ".join(f"(subpath {q(real / d)})" for d in SECRET_DIRS)
    return ("(version 1)(allow default)"
            '(deny file-write* (subpath "/Users"))'
            f"(allow file-write* (subpath {q(repo)}) (subpath {q(home)}))"
            f"(deny file-read* {secrets})")


def sandboxed(cmd: Cmd) -> Cmd:
    """Wrap a session in sandbox-exec. The harness runs with its permission prompts off, so the OS keeps its
    writes inside the repository copy and the session HOME and keeps the user's credentials unreadable.
    The network stays open: T5 installs packages and every harness calls the rig."""
    if os.environ.get("HARNESS_SANDBOX") == "0" or not Path(SANDBOX_EXEC).exists():
        return cmd
    profile = _sandbox_profile(cmd.cwd, Path(cmd.env.get("HOME", cmd.cwd)))
    return Cmd([SANDBOX_EXEC, "-p", profile, *cmd.argv], cmd.env, cmd.cwd)


def prepare(name: str, home: Path, target: Target) -> None:
    """Write the configuration files of one harness inside home."""
    _BUILD[name]
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    if name == "claude":
        (home / ".claude").mkdir(exist_ok=True)
    elif name == "dsh":
        (home / ".dsh").mkdir(exist_ok=True)
        (home / ".dsh/settings.yaml").write_text(
            "llm-pi-ai:\n  providers:\n"
            f"    {PROVIDER}:\n      displayName: rig\n      api: openai-completions\n"
            f"      baseURL: {target.url}/v1\n      apiKeyEnv: RIG_API_KEY\n      models:\n"
            f"        - id: \"{target.model_id}\"\n          input: [text]\n"
            f"          reasoningEfforts: {{ {EFFORT}: {EFFORT} }}\n"
            f"agent-default-model:\n  provider: {PROVIDER}\n  model: \"{target.model_id}\"\n"
            f"  reasoningEffort: {EFFORT}\n")
    elif name == "pi":
        (home / ".pi/agent").mkdir(parents=True, exist_ok=True)
        (home / ".pi/agent/models.json").write_text(json.dumps({"providers": {PROVIDER: {
            "baseUrl": f"{target.url}/v1", "api": "openai-completions", "apiKey": "local",
            "models": [{"id": target.model_id, "name": target.model_id, "reasoning": True, "input": ["text"],
                        "contextWindow": CONTEXT, "maxTokens": MAX_OUTPUT}]}}}, indent=2))


def version(name: str) -> str:
    """The first line `<harness> --version` prints, or "unknown"."""
    _BUILD[name]
    try:
        out = subprocess.run([_bin(name), "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    lines = (out.stdout or out.stderr).strip().splitlines()
    return lines[0].strip() if out.returncode == 0 and lines else "unknown"
