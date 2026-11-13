"""Command line, isolated environment and version of each coding harness.

Every harness runs non-interactive, with a temporary HOME that holds its whole configuration, reasoning effort
xhigh and a 131072-token context. Nothing here reads or writes the user's global configuration.
HARNESS_BIN_<NAME> replaces the executable (tests use it). HARNESS_TOOLS_BIN, when set, goes first on PATH.
HARNESS_SANDBOX=0 turns the macOS sandbox off (see sandboxed). HARNESS_SANDBOX_READ adds readable paths (a:b).
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
WRITE_ROOTS = ("/dev", "/private/tmp", "/private/var/folders", "/private/var/tmp")
TOOLCHAIN_DIRS = (".local/bin", ".local/lib", ".local/share/uv", ".local/share/mise", ".cache/uv", ".cache/mise",
                  ".config/mise")   # under the real home: runtimes only, never application data
NO_EXEC = ("/bin/launchctl", "/usr/bin/open", "/usr/bin/osascript", "/usr/bin/crontab", "/usr/bin/at",
           "/usr/bin/ssh", "/usr/bin/scp", "/usr/bin/sftp", "/usr/bin/security")


def _q(path) -> str:
    return '"' + str(Path(path).resolve()).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _sandbox_profile(write: list[Path], read: list[Path]) -> str:
    """Writes: denied everywhere except `write` and the system temp roots. Reads under /Users: denied except
    `read` (path lookups stay allowed). Launch helpers and Apple Events: denied. Network: open.
    The exec denylist is a convenience, not the barrier: launchd refuses job submission from a sandboxed
    client, and macOS kills a copy of a platform binary such as launchctl (tests pin the first)."""
    subpaths = lambda paths: " ".join(f"(subpath {_q(p)})" for p in paths)  # noqa: E731
    return ("(version 1)(allow default)"
            "(deny file-write*)"
            f"(allow file-write* {subpaths([*WRITE_ROOTS, *write])})"
            '(deny file-read* (subpath "/Users"))'
            '(allow file-read-metadata (subpath "/Users"))'
            f"(allow file-read* {subpaths([*write, *read])})"
            "(deny appleevent-send)(deny job-creation)"
            f"(deny process-exec {' '.join(f'(literal {_q(p)})' for p in NO_EXEC)})")


def sandboxed(cmd: Cmd, read: tuple = ()) -> Cmd:
    """Wrap a process in sandbox-exec. The harness runs with its permission prompts off, so the OS confines it:
    it writes only in the repository copy and the session HOME (TMPDIR moves there too), and under /Users it
    reads only those two, the runtimes (TOOLCHAIN_DIRS, HARNESS_TOOLS_BIN), `read` and HARNESS_SANDBOX_READ.
    The campaign's own tests and reference solutions stay unreadable. The network stays open: T5 installs
    packages and every harness calls the server. Fails closed: without sandbox-exec it raises, unless the
    operator sets HARNESS_SANDBOX=0."""
    if os.environ.get("HARNESS_SANDBOX") == "0":
        return cmd
    if not Path(SANDBOX_EXEC).exists():
        raise RuntimeError(f"{SANDBOX_EXEC} is missing; set HARNESS_SANDBOX=0 to run without a sandbox")
    home = Path(cmd.env.get("HOME", cmd.cwd))
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    reads = [Path.home() / d for d in TOOLCHAIN_DIRS] + [Path(p) for p in read]
    tools = os.environ.get("HARNESS_TOOLS_BIN")
    reads += [Path(tools).parent] if tools else []
    reads += [Path(p) for p in os.environ.get("HARNESS_SANDBOX_READ", "").split(":") if p]
    profile = _sandbox_profile([cmd.cwd, home], reads)
    return Cmd([SANDBOX_EXEC, "-p", profile, *cmd.argv], {**cmd.env, "TMPDIR": str(home / "tmp")}, cmd.cwd)


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
