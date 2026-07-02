# Hermes Claude-Agent-SDK Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `claude-agent` model provider + `claude_agent_sdk` runtime to hermes-agent so Claude models run through the Claude Agent SDK authenticated by a Claude subscription (Claude Code OAuth login) — the Anthropic-sanctioned subscription path — upstreamable as a PR for [NousResearch/hermes-agent#25267](https://github.com/NousResearch/hermes-agent/issues/25267).

**Architecture:** Mirror Hermes' existing `codex_app_server` runtime 1:1. A `ProviderProfile` plugin registers the provider; a new `api_mode="claude_agent_sdk"` short-circuits `run_conversation()` and hands the whole turn to a `ClaudeAgentSession` adapter that drives the async `claude-agent-sdk` `ClaudeSDKClient` from Hermes' synchronous agent loop (event loop on a dedicated thread). Claude Code owns the tool loop; Hermes' own tool surface is injected into it via the existing `agent/transports/hermes_tools_mcp_server.py` (reused verbatim) as a stdio MCP server. Events are projected back into Hermes' messages/usage accounting exactly like `agent/codex_runtime.py` does for Codex.

**Tech Stack:** Python 3.11+, hermes-agent (fork), `claude-agent-sdk` (PyPI), Claude Code CLI, pytest, uv.

## Global Constraints

- Target repo: a fork of `https://github.com/NousResearch/hermes-agent`, branch `feat/claude-agent-sdk-runtime`. Working clone at `~/LocalProjects/hermes-agent` (NOT the local-llms repo this plan is saved in).
- New api_mode string: exactly `claude_agent_sdk` (everywhere: profile, `_VALID_API_MODES`, conversation-loop gate).
- Provider canonical name: `claude-agent`; aliases: `claude-sdk`, `claude-subscription`.
- Config opt-in gate: `model.anthropic_runtime: claude_agent_sdk` in config.yaml; eligible providers: `{"anthropic", "claude-agent"}`. Default (unset/"auto") is a no-op — existing Anthropic API-key path unchanged.
- Auth on this path: Claude Code login (subscription) or `CLAUDE_CODE_OAUTH_TOKEN`. `ANTHROPIC_API_KEY` must be **stripped** from the SDK subprocess env so subscription auth is never silently bypassed into pay-per-token API billing.
- `claude-agent-sdk` is a lazy import inside functions (module import must not fail when the package is absent) — same pattern as `hermes_tools_mcp_server._build_server`.
- Follow existing codex sibling files as canonical patterns: `agent/transports/codex_app_server_session.py`, `agent/codex_runtime.py`, `agent/conversation_loop.py:620-633`, `hermes_cli/runtime_provider.py:361-386`.
- TDD: every task = failing test → minimal implementation → pass → commit. Run tests with `uv run pytest <path> -v` from the repo root.
- Tests must not require the `claude-agent-sdk` package, the `claude` binary, or network: stub the SDK by injecting a fake `claude_agent_sdk` module into `sys.modules` via a pytest fixture.

---

### Task 0: Workspace setup and baseline

**Files:**
- Create: `~/LocalProjects/hermes-agent` (clone of user's fork)

**Interfaces:**
- Produces: a working dev checkout on branch `feat/claude-agent-sdk-runtime` where `uv run pytest tests/agent/transports/test_codex_app_server_session.py` passes.

- [ ] **Step 1: Fork and clone**

```bash
cd ~/LocalProjects
gh repo fork NousResearch/hermes-agent --clone --remote
cd hermes-agent
git checkout -b feat/claude-agent-sdk-runtime
```

- [ ] **Step 2: Install dev environment**

```bash
uv sync --all-extras || uv sync   # repo uses uv.lock; fall back to plain sync
```

Expected: dependencies resolve without error.

- [ ] **Step 3: Baseline — run the codex-runtime tests we will mirror**

```bash
uv run pytest tests/agent/transports/test_codex_app_server_session.py tests/hermes_cli/test_codex_runtime_switch.py -q
```

Expected: PASS (or record pre-existing failures — they define the baseline; do not fix them).

- [ ] **Step 4: Read the pattern files** (no code yet)

Read in full: `agent/transports/codex_app_server_session.py`, `agent/codex_runtime.py`, `agent/transports/hermes_tools_mcp_server.py`, `plugins/model-providers/openai-codex/__init__.py`, `hermes_cli/runtime_provider.py` (the `_VALID_API_MODES` / `_maybe_apply_codex_app_server_runtime` region), `agent/conversation_loop.py:600-640`.

- [ ] **Step 5: Commit** (empty marker so the branch exists remotely)

```bash
git commit --allow-empty -m "chore: start claude-agent-sdk runtime branch (refs #25267)"
```

---

### Task 1: Provider profile plugin

**Files:**
- Create: `plugins/model-providers/claude-agent/__init__.py`
- Create: `plugins/model-providers/claude-agent/plugin.yaml`
- Test: `tests/providers/test_claude_agent_profile.py`

**Interfaces:**
- Produces: registry entry `get_provider_profile("claude-agent")` returning a `ProviderProfile` with `api_mode == "claude_agent_sdk"`, `auth_type == "oauth_external"`. Later tasks reference the provider name `"claude-agent"` and api_mode `"claude_agent_sdk"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/providers/test_claude_agent_profile.py
"""Registry contract for the claude-agent provider plugin."""


def test_claude_agent_profile_registered():
    from providers import get_provider_profile

    profile = get_provider_profile("claude-agent")
    assert profile is not None
    assert profile.api_mode == "claude_agent_sdk"
    assert profile.auth_type == "oauth_external"
    assert profile.supports_health_check is False  # no REST /models probe
    assert "CLAUDE_CODE_OAUTH_TOKEN" in profile.env_vars
    assert profile.supports_vision is True


def test_claude_agent_aliases_resolve():
    from providers import get_provider_profile

    for alias in ("claude-sdk", "claude-subscription"):
        assert get_provider_profile(alias) is get_provider_profile("claude-agent")


def test_claude_agent_fallback_models_nonempty():
    from providers import get_provider_profile

    profile = get_provider_profile("claude-agent")
    assert len(profile.fallback_models) >= 3
    assert any("opus" in m for m in profile.fallback_models)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/providers/test_claude_agent_profile.py -v`
Expected: FAIL — `assert profile is not None` (profile not registered).

- [ ] **Step 3: Write the plugin**

```python
# plugins/model-providers/claude-agent/__init__.py
"""Claude via the Claude Agent SDK (subscription OAuth) provider profile.

Auth is external: the Claude Code CLI's login (`claude` → /login) or a
CLAUDE_CODE_OAUTH_TOKEN minted by `claude setup-token`. There is no REST
/models catalog on this path, so fetch_models returns None and the picker
uses fallback_models.
"""

from providers import register_provider
from providers.base import ProviderProfile


class ClaudeAgentProfile(ProviderProfile):
    def fetch_models(self, *, api_key=None, base_url=None, timeout=8.0):
        return None  # no REST catalog on subscription OAuth


claude_agent = ClaudeAgentProfile(
    name="claude-agent",
    aliases=("claude-sdk", "claude-subscription"),
    display_name="Claude (subscription)",
    description="Claude via the Claude Agent SDK using your Claude subscription",
    signup_url="https://claude.ai/settings/subscription",
    api_mode="claude_agent_sdk",
    env_vars=("CLAUDE_CODE_OAUTH_TOKEN",),
    base_url="",              # no HTTP endpoint — SDK spawns Claude Code
    auth_type="oauth_external",
    supports_health_check=False,
    supports_vision=True,
    fallback_models=(
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "opus",    # SDK aliases resolve to the subscription's latest
        "sonnet",
    ),
)

register_provider(claude_agent)
```

```yaml
# plugins/model-providers/claude-agent/plugin.yaml
name: claude-agent-profile
kind: model-provider
version: 1.0.0
description: Claude models through the Claude Agent SDK with Claude-subscription OAuth
author: vitor
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/providers/test_claude_agent_profile.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/model-providers/claude-agent tests/providers/test_claude_agent_profile.py
git commit -m "feat(providers): claude-agent profile plugin (Agent SDK, subscription OAuth)"
```

---

### Task 2: api_mode plumbing in runtime_provider

**Files:**
- Modify: `hermes_cli/runtime_provider.py` (the `_VALID_API_MODES` set ~line 328, and add a sibling of `_maybe_apply_codex_app_server_runtime` ~line 361)
- Test: `tests/hermes_cli/test_claude_agent_runtime_switch.py`

**Interfaces:**
- Consumes: provider name `"claude-agent"` from Task 1.
- Produces: `_maybe_apply_claude_agent_runtime(provider: str, api_mode: str, model_cfg: dict | None) -> str` — returns `"claude_agent_sdk"` when `model_cfg["anthropic_runtime"] == "claude_agent_sdk"` and provider ∈ {"anthropic", "claude-agent"}; otherwise returns `api_mode` unchanged. `"claude_agent_sdk"` is a member of `_VALID_API_MODES`.

- [ ] **Step 1: Write the failing test**

```python
# tests/hermes_cli/test_claude_agent_runtime_switch.py
from hermes_cli.runtime_provider import (
    _VALID_API_MODES,
    _maybe_apply_claude_agent_runtime,
)


def test_claude_agent_sdk_is_valid_api_mode():
    assert "claude_agent_sdk" in _VALID_API_MODES


def test_gate_rewrites_for_anthropic_provider_when_opted_in():
    out = _maybe_apply_claude_agent_runtime(
        provider="anthropic",
        api_mode="anthropic_messages",
        model_cfg={"anthropic_runtime": "claude_agent_sdk"},
    )
    assert out == "claude_agent_sdk"


def test_gate_rewrites_for_claude_agent_provider():
    out = _maybe_apply_claude_agent_runtime(
        provider="claude-agent",
        api_mode="chat_completions",
        model_cfg={"anthropic_runtime": "claude_agent_sdk"},
    )
    assert out == "claude_agent_sdk"


def test_gate_noop_when_unset_or_auto():
    for cfg in (None, {}, {"anthropic_runtime": ""}, {"anthropic_runtime": "auto"}):
        out = _maybe_apply_claude_agent_runtime(
            provider="anthropic", api_mode="anthropic_messages", model_cfg=cfg
        )
        assert out == "anthropic_messages"


def test_gate_noop_for_other_providers():
    out = _maybe_apply_claude_agent_runtime(
        provider="openrouter",
        api_mode="chat_completions",
        model_cfg={"anthropic_runtime": "claude_agent_sdk"},
    )
    assert out == "chat_completions"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hermes_cli/test_claude_agent_runtime_switch.py -v`
Expected: FAIL — ImportError (`_maybe_apply_claude_agent_runtime` not defined).

- [ ] **Step 3: Implement**

In `hermes_cli/runtime_provider.py`, add `"claude_agent_sdk"` to `_VALID_API_MODES` (with a comment mirroring the codex one), then add directly below `_maybe_apply_codex_app_server_runtime`:

```python
def _maybe_apply_claude_agent_runtime(
    *,
    provider: str,
    api_mode: str,
    model_cfg: Optional[Dict[str, Any]],
) -> str:
    """Optional opt-in: rewrite api_mode → "claude_agent_sdk" for Anthropic
    providers when the user has enabled the runtime via
    `model.anthropic_runtime: claude_agent_sdk` in config.yaml.

    Default behavior preserved: unset/"auto"/empty is a no-op. Only
    providers in {"anthropic", "claude-agent"} are eligible.
    Returns the (possibly-rewritten) api_mode."""
    if not model_cfg:
        return api_mode
    if provider not in {"anthropic", "claude-agent"}:
        return api_mode
    runtime = str(model_cfg.get("anthropic_runtime") or "").strip().lower()
    if runtime == "claude_agent_sdk":
        return "claude_agent_sdk"
    return api_mode
```

Then grep for every call site of `_maybe_apply_codex_app_server_runtime` in `hermes_cli/runtime_provider.py` (`grep -n "_maybe_apply_codex_app_server_runtime" hermes_cli/runtime_provider.py`) and chain the new gate immediately after each call, in the same style:

```python
api_mode = _maybe_apply_codex_app_server_runtime(provider=provider, api_mode=api_mode, model_cfg=model_cfg)
api_mode = _maybe_apply_claude_agent_runtime(provider=provider, api_mode=api_mode, model_cfg=model_cfg)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/hermes_cli/test_claude_agent_runtime_switch.py tests/hermes_cli/test_codex_runtime_switch.py -v`
Expected: all PASS (codex tests prove no regression).

- [ ] **Step 5: Commit**

```bash
git add hermes_cli/runtime_provider.py tests/hermes_cli/test_claude_agent_runtime_switch.py
git commit -m "feat(runtime): claude_agent_sdk api_mode + anthropic_runtime config gate"
```

---

### Task 3: Fake-SDK test fixture

**Files:**
- Create: `tests/agent/transports/conftest.py` (or extend if it exists — check first with `ls tests/agent/transports/`)

**Interfaces:**
- Produces: pytest fixture `fake_claude_sdk` that installs a stub `claude_agent_sdk` module into `sys.modules` and yields a controllable `FakeSDK` object. Later tasks' tests consume `fake_claude_sdk.script_turn(...)`, `fake_claude_sdk.clients` (list of constructed fake clients), and the stub message classes `TextBlock`, `ToolUseBlock`, `AssistantMessage`, `ResultMessage`.

- [ ] **Step 1: Write the fixture (this task is infrastructure — its "test" is Task 4 using it)**

```python
# tests/agent/transports/conftest.py  (append if the file exists)
"""Stub claude_agent_sdk so ClaudeAgentSession tests run without the
package, the claude binary, or network."""

import asyncio
import sys
import types
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict


@dataclass
class AssistantMessage:
    content: list
    model: str = "claude-opus-4-6"
    usage: dict | None = None


@dataclass
class ResultMessage:
    subtype: str = "success"
    is_error: bool = False
    session_id: str = "sess-fake-1"
    result: str | None = None
    usage: dict | None = None
    total_cost_usd: float | None = None
    num_turns: int = 1


class FakeClient:
    """Mimics ClaudeSDKClient: connect/query/receive_response/interrupt/disconnect."""

    def __init__(self, options=None):
        self.options = options
        self.connected = False
        self.queries: list[str] = []
        self.interrupted = False
        self._scripted: list[list[Any]] = []  # one message-list per turn

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def query(self, prompt: str):
        self.queries.append(prompt)

    async def interrupt(self):
        self.interrupted = True

    async def receive_response(self):
        messages = self._scripted.pop(0) if self._scripted else []
        for m in messages:
            await asyncio.sleep(0)  # yield control like a real stream
            yield m


class FakeSDK:
    def __init__(self, module):
        self.module = module
        self.clients: list[FakeClient] = []
        self._pending_scripts: list[list[Any]] = []

    def script_turn(self, messages: list):
        """Queue one turn's message stream for the next/current client."""
        if self.clients:
            self.clients[-1]._scripted.append(messages)
        else:
            self._pending_scripts.append(messages)


@pytest.fixture
def fake_claude_sdk(monkeypatch):
    module = types.ModuleType("claude_agent_sdk")
    sdk = FakeSDK(module)

    def _client_factory(options=None):
        client = FakeClient(options)
        client._scripted = list(sdk._pending_scripts)
        sdk._pending_scripts = []
        sdk.clients.append(client)
        return client

    module.ClaudeSDKClient = _client_factory
    module.ClaudeAgentOptions = lambda **kw: types.SimpleNamespace(**kw)
    module.TextBlock = TextBlock
    module.ToolUseBlock = ToolUseBlock
    module.AssistantMessage = AssistantMessage
    module.ResultMessage = ResultMessage
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", module)
    return sdk
```

- [ ] **Step 2: Sanity-run collection**

Run: `uv run pytest tests/agent/transports/ --collect-only -q | tail -5`
Expected: no collection errors.

- [ ] **Step 3: Commit**

```bash
git add tests/agent/transports/conftest.py
git commit -m "test: fake claude_agent_sdk fixture for session tests"
```

---

### Task 4: ClaudeAgentSession — lifecycle (start/close, sync-over-async bridge)

**Files:**
- Create: `agent/transports/claude_agent_session.py`
- Test: `tests/agent/transports/test_claude_agent_session.py`

**Interfaces:**
- Consumes: `fake_claude_sdk` fixture (Task 3).
- Produces:
  - `class ClaudeTurnResult` — dataclass: `final_text: str = ""`, `projected_messages: list[dict]`, `tool_iterations: int = 0`, `interrupted: bool = False`, `error: str | None = None`, `session_id: str | None = None`, `usage: dict | None = None`, `should_retire: bool = False`.
  - `class ClaudeAgentSession(model: str, cwd: str, system_prompt: str | None = None, approval_callback=None, auto_approve: bool = False, enable_hermes_tools: bool = True, env: dict | None = None)` with methods `ensure_started() -> None`, `run_turn(user_input, *, turn_timeout: float = 600.0) -> ClaudeTurnResult` (Task 5), `request_interrupt() -> None` (Task 7), `close() -> None`, `is_alive() -> bool`, and context-manager support.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/transports/test_claude_agent_session.py
import sys


def _make_session(tmp_path, **kw):
    from agent.transports.claude_agent_session import ClaudeAgentSession

    defaults = dict(model="claude-opus-4-6", cwd=str(tmp_path), enable_hermes_tools=False)
    defaults.update(kw)
    return ClaudeAgentSession(**defaults)


def test_import_without_sdk_installed(monkeypatch, tmp_path):
    """Module import and construction must not require claude_agent_sdk."""
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", None)
    session = _make_session(tmp_path)
    assert session is not None  # lazy import: no error until ensure_started


def test_ensure_started_connects_client(fake_claude_sdk, tmp_path):
    session = _make_session(tmp_path)
    session.ensure_started()
    try:
        assert len(fake_claude_sdk.clients) == 1
        assert fake_claude_sdk.clients[0].connected
        assert session.is_alive()
    finally:
        session.close()


def test_close_disconnects_and_stops_loop(fake_claude_sdk, tmp_path):
    session = _make_session(tmp_path)
    session.ensure_started()
    session.close()
    assert not fake_claude_sdk.clients[0].connected
    assert not session.is_alive()
    session.close()  # idempotent


def test_options_strip_api_key_and_set_bypass(fake_claude_sdk, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    session = _make_session(tmp_path, auto_approve=True)
    session.ensure_started()
    try:
        opts = fake_claude_sdk.clients[0].options
        assert opts.model == "claude-opus-4-6"
        assert opts.permission_mode == "bypassPermissions"
        assert opts.setting_sources == []
        assert opts.env.get("ANTHROPIC_API_KEY", "") == ""
    finally:
        session.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v`
Expected: FAIL — `ModuleNotFoundError: agent.transports.claude_agent_session`.

- [ ] **Step 3: Implement lifecycle**

```python
# agent/transports/claude_agent_session.py
"""Claude Agent SDK session adapter for the claude_agent_sdk runtime.

Sibling of codex_app_server_session.py: Hermes' AIAgent loop is
synchronous, the Claude Agent SDK is asyncio — so we run one event loop
on a dedicated daemon thread per session and drive coroutines with
run_coroutine_threadsafe. One ClaudeAgentSession per AIAgent instance,
reused across turns (the SDK client keeps conversation context).

Auth is the Claude Code credential chain (subscription login or
CLAUDE_CODE_OAUTH_TOKEN). ANTHROPIC_API_KEY is deliberately blanked in
the child env so a stray key never flips billing to pay-per-token.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

_START_TIMEOUT = 30.0


@dataclass
class ClaudeTurnResult:
    """Result of one user→assistant→tools turn through the Agent SDK."""

    final_text: str = ""
    projected_messages: list[dict] = field(default_factory=list)
    tool_iterations: int = 0
    interrupted: bool = False
    error: Optional[str] = None
    session_id: Optional[str] = None
    usage: Optional[dict[str, Any]] = None
    should_retire: bool = False


class ClaudeAgentSession:
    def __init__(
        self,
        *,
        model: str,
        cwd: str,
        system_prompt: Optional[str] = None,
        approval_callback=None,
        auto_approve: bool = False,
        enable_hermes_tools: bool = True,
        env: Optional[dict[str, str]] = None,
    ) -> None:
        self._model = model
        self._cwd = cwd
        self._system_prompt = system_prompt
        self._approval_callback = approval_callback
        self._auto_approve = auto_approve
        self._enable_hermes_tools = enable_hermes_tools
        self._extra_env = dict(env or {})
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client: Any = None
        self._session_id: Optional[str] = None
        self._closed = False

    # ---------- lifecycle ----------

    def ensure_started(self) -> None:
        if self._client is not None and not self._closed:
            return
        try:
            import claude_agent_sdk  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "claude_agent_sdk runtime requires the 'claude-agent-sdk' "
                "package: pip install claude-agent-sdk (and the Claude Code "
                "CLI, logged in with your Claude subscription)"
            ) from exc

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="claude-agent-sdk", daemon=True
        )
        self._thread.start()
        self._closed = False

        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

        options = ClaudeAgentOptions(**self._build_options_kwargs())
        self._client = ClaudeSDKClient(options=options)
        self._run(self._client.connect(), timeout=_START_TIMEOUT)

    def _build_options_kwargs(self) -> dict[str, Any]:
        # Subscription-auth hygiene: never let a stray API key hijack billing.
        child_env = {"ANTHROPIC_API_KEY": "", **self._extra_env}
        kwargs: dict[str, Any] = {
            "model": self._model,
            "cwd": self._cwd,
            "setting_sources": [],  # isolate from the user's personal ~/.claude config
            "env": child_env,
            "permission_mode": "bypassPermissions" if self._auto_approve else "default",
            "mcp_servers": self._mcp_server_config(),
        }
        if self._system_prompt:
            kwargs["system_prompt"] = self._system_prompt
        if self._session_id:
            kwargs["resume"] = self._session_id  # survive session respawn
        if not self._auto_approve and self._approval_callback is not None:
            kwargs["can_use_tool"] = self._make_permission_handler()
        return kwargs

    def _mcp_server_config(self) -> dict[str, Any]:
        if not self._enable_hermes_tools:
            return {}
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return {
            "hermes-tools": {
                "type": "stdio",
                "command": sys.executable,
                "args": ["-m", "agent.transports.hermes_tools_mcp_server"],
                "env": {
                    "PYTHONPATH": repo_root,
                    "HERMES_QUIET": "1",
                    "HERMES_REDACT_SECRETS": "true",
                },
            }
        }

    def _make_permission_handler(self):
        # Filled in by Task 6; lifecycle task ships a permissive stub.
        async def _handler(tool_name, input_data, context):  # pragma: no cover
            from claude_agent_sdk import PermissionResultAllow

            return PermissionResultAllow(updated_input=input_data)

        return _handler

    def _run(self, coro, timeout: float):
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout)

    def is_alive(self) -> bool:
        return (
            not self._closed
            and self._client is not None
            and self._thread is not None
            and self._thread.is_alive()
        )

    def close(self, timeout: float = 5.0) -> None:
        if self._closed:
            return
        self._closed = True
        if self._client is not None and self._loop is not None:
            try:
                self._run(self._client.disconnect(), timeout=timeout)
            except Exception:
                logger.debug("claude-agent disconnect failed", exc_info=True)
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._client = None

    def __enter__(self) -> "ClaudeAgentSession":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/transports/claude_agent_session.py tests/agent/transports/test_claude_agent_session.py
git commit -m "feat(transports): ClaudeAgentSession lifecycle (sync bridge over Agent SDK)"
```

---

### Task 5: ClaudeAgentSession.run_turn — text, tools projection, usage

**Files:**
- Modify: `agent/transports/claude_agent_session.py`
- Test: `tests/agent/transports/test_claude_agent_session.py` (append)

**Interfaces:**
- Consumes: stub message classes from Task 3.
- Produces: `run_turn(user_input, *, turn_timeout=600.0) -> ClaudeTurnResult` where: `final_text` concatenates TextBlocks of the last assistant message; `projected_messages` is OpenAI-shaped (`{"role": "assistant", "content": ...}` plus one `{"role": "assistant", "tool_calls": [...]}` / synthetic `{"role": "tool", ...}` pair per ToolUseBlock, matching how `codex_app_server_session.py` projects items — read its `run_turn` item-projection block and mirror the message dicts exactly); `usage`/`session_id` copied from ResultMessage; startup or turn exceptions land in `result.error` (never raise); a callable `tool_progress_callback` attribute is invoked `(tool_name, preview_str, args_dict)` per tool use.

- [ ] **Step 1: Write the failing tests (append to the test file)**

```python
def test_run_turn_returns_text_and_usage(fake_claude_sdk, tmp_path):
    m = fake_claude_sdk.module  # stub classes live on the injected module
    AssistantMessage, ResultMessage, TextBlock = (
        m.AssistantMessage, m.ResultMessage, m.TextBlock,
    )

    session = _make_session(tmp_path)
    session.ensure_started()
    try:
        fake_claude_sdk.script_turn([
            AssistantMessage(content=[TextBlock("Hello from Claude")]),
            ResultMessage(
                session_id="sess-abc",
                result="Hello from Claude",
                usage={"input_tokens": 10, "output_tokens": 5,
                       "cache_read_input_tokens": 2, "cache_creation_input_tokens": 1},
            ),
        ])
        result = session.run_turn("hi")
        assert result.error is None
        assert result.final_text == "Hello from Claude"
        assert result.session_id == "sess-abc"
        assert result.usage["input_tokens"] == 10
        assert fake_claude_sdk.clients[0].queries == ["hi"]
    finally:
        session.close()


def test_run_turn_projects_tool_use(fake_claude_sdk, tmp_path):
    m = fake_claude_sdk.module
    AssistantMessage, ResultMessage, TextBlock, ToolUseBlock = (
        m.AssistantMessage, m.ResultMessage, m.TextBlock, m.ToolUseBlock,
    )

    session = _make_session(tmp_path)
    seen = []
    session.tool_progress_callback = lambda name, preview, args: seen.append(name)
    session.ensure_started()
    try:
        fake_claude_sdk.script_turn([
            AssistantMessage(content=[ToolUseBlock(id="t1", name="Bash", input={"command": "ls"})]),
            AssistantMessage(content=[TextBlock("done")]),
            ResultMessage(session_id="s", result="done", usage={}),
        ])
        result = session.run_turn("list files")
        assert result.tool_iterations == 1
        assert seen == ["Bash"]
        assert result.final_text == "done"
        roles = [m["role"] for m in result.projected_messages]
        assert "assistant" in roles and "tool" in roles
    finally:
        session.close()


def test_run_turn_error_is_captured_not_raised(fake_claude_sdk, tmp_path):
    ResultMessage = fake_claude_sdk.module.ResultMessage

    session = _make_session(tmp_path)
    session.ensure_started()
    try:
        fake_claude_sdk.script_turn([
            ResultMessage(subtype="error_during_execution", is_error=True,
                          session_id="s", result=None, usage=None),
        ])
        result = session.run_turn("boom")
        assert result.error is not None
        assert "error_during_execution" in result.error
    finally:
        session.close()
```

- [ ] **Step 2: Run to verify failures**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v -k run_turn`
Expected: FAIL — `AttributeError: 'ClaudeAgentSession' object has no attribute 'run_turn'`.

- [ ] **Step 3: Implement run_turn**

Add to `ClaudeAgentSession` (`tool_progress_callback: Any = None` as an instance attribute in `__init__`):

```python
    def run_turn(self, user_input: Any, *, turn_timeout: float = 600.0) -> ClaudeTurnResult:
        """Send one user message; block until the SDK's ResultMessage."""
        result = ClaudeTurnResult()
        try:
            self.ensure_started()
        except (RuntimeError, TimeoutError) as exc:
            result.error = f"claude-agent-sdk startup failed: {exc}"
            result.should_retire = True
            return result
        text = user_input if isinstance(user_input, str) else _coerce_input_text(user_input)
        try:
            self._run(self._turn_coro(text, result), timeout=turn_timeout)
        except TimeoutError:
            result.error = f"claude-agent-sdk turn timed out after {turn_timeout}s"
            result.should_retire = True
        except Exception as exc:
            result.error = f"claude-agent-sdk turn failed: {exc}"
            result.should_retire = True
        if result.session_id:
            self._session_id = result.session_id
        return result

    async def _turn_coro(self, text: str, result: ClaudeTurnResult) -> None:
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

        await self._client.query(text)
        last_text_parts: list[str] = []
        async for message in self._client.receive_response():
            if isinstance(message, AssistantMessage):
                text_parts: list[str] = []
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        result.tool_iterations += 1
                        self._emit_tool_progress(block)
                        result.projected_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": block.id,
                                "type": "function",
                                "function": {"name": block.name,
                                             "arguments": _json_dumps(block.input)},
                            }],
                        })
                        # Claude Code executes the tool itself; project a
                        # synthetic ack so the transcript stays well-formed.
                        result.projected_messages.append({
                            "role": "tool",
                            "tool_call_id": block.id,
                            "content": "[executed inside Claude Code runtime]",
                        })
                if text_parts:
                    last_text_parts = text_parts
                    result.projected_messages.append(
                        {"role": "assistant", "content": "".join(text_parts)}
                    )
            elif isinstance(message, ResultMessage):
                result.session_id = message.session_id
                result.usage = message.usage or {}
                if message.is_error:
                    result.error = f"claude-agent-sdk: {message.subtype}"
                final = message.result or "".join(last_text_parts)
                result.final_text = final or ""

    def _emit_tool_progress(self, block) -> None:
        callback = self.tool_progress_callback
        if callback is None:
            return
        try:
            preview = _json_dumps(block.input)[:120]
            callback(block.name, preview, dict(block.input or {}))
        except Exception:
            logger.debug("tool progress callback raised", exc_info=True)
```

Module-level helpers:

```python
def _json_dumps(obj: Any) -> str:
    import json

    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _coerce_input_text(user_input: Any) -> str:
    """Collapse Hermes/OpenAI rich content into plain turn text — mirror
    codex_app_server_session._coerce_turn_input_text (read it and copy the
    list/dict handling so images degrade to their text parts identically)."""
    if isinstance(user_input, list):
        parts = []
        for item in user_input:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(p for p in parts if p)
    return str(user_input)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/transports/claude_agent_session.py tests/agent/transports/test_claude_agent_session.py
git commit -m "feat(transports): ClaudeAgentSession.run_turn with tool projection + usage"
```

---

### Task 6: Approval bridging (can_use_tool → Hermes approval callback)

**Files:**
- Modify: `agent/transports/claude_agent_session.py` (`_make_permission_handler`)
- Test: `tests/agent/transports/test_claude_agent_session.py` (append)

**Interfaces:**
- Consumes: Hermes approval callback convention — read `agent/transports/codex_app_server_session.py::_decide_exec_approval` and `tools/terminal_tool._get_approval_callback` to copy the exact callback signature; the callback returns a choice string (`"approve"`/`"deny"` family — mirror `_approval_choice_to_codex_decision` mapping).
- Produces: async `can_use_tool` handler that (a) auto-allows all `mcp__hermes-tools__*` tools (they run inside Hermes' own dispatch, already policy-checked), (b) forwards Bash/Write/Edit to the Hermes approval callback via `asyncio.to_thread` (callback is blocking/UI-bound), (c) fails closed (deny) when no callback is installed.

- [ ] **Step 1: Write the failing tests**

Stub `PermissionResultAllow`/`PermissionResultDeny` in the conftest fake module first (add to Task 3's module setup):

```python
# append inside fake_claude_sdk fixture, before monkeypatch.setitem:
@dataclass
class PermissionResultAllow:
    updated_input: dict | None = None

@dataclass
class PermissionResultDeny:
    message: str = ""
    interrupt: bool = False

module.PermissionResultAllow = PermissionResultAllow
module.PermissionResultDeny = PermissionResultDeny
```

Then the tests:

```python
def test_permission_handler_denies_without_callback(fake_claude_sdk, tmp_path):
    import asyncio

    session = _make_session(tmp_path, auto_approve=False, approval_callback=None)
    handler = session._make_permission_handler()
    result = asyncio.run(handler("Bash", {"command": "rm -rf /"}, None))
    assert type(result).__name__ == "PermissionResultDeny"


def test_permission_handler_allows_hermes_tools(fake_claude_sdk, tmp_path):
    import asyncio

    session = _make_session(tmp_path, auto_approve=False, approval_callback=None)
    handler = session._make_permission_handler()
    result = asyncio.run(handler("mcp__hermes-tools__web_search", {"query": "x"}, None))
    assert type(result).__name__ == "PermissionResultAllow"


def test_permission_handler_forwards_to_hermes_callback(fake_claude_sdk, tmp_path):
    import asyncio

    calls = []

    def approval(tool_name, preview, args=None):
        calls.append(tool_name)
        return "approve"

    session = _make_session(tmp_path, auto_approve=False, approval_callback=approval)
    handler = session._make_permission_handler()
    result = asyncio.run(handler("Bash", {"command": "ls"}, None))
    assert type(result).__name__ == "PermissionResultAllow"
    assert calls == ["Bash"]
```

**Note to implementer:** before finalizing, open `tools/terminal_tool.py` and confirm the real approval-callback signature; adjust the test's `approval()` stub and the forwarding call to match it exactly. The plan's `(tool_name, preview, args)` is the expected shape based on `_decide_exec_approval` — verify, don't assume.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v -k permission`
Expected: FAIL (stub handler always allows).

- [ ] **Step 3: Implement**

```python
    def _make_permission_handler(self):
        approval_callback = self._approval_callback

        async def _handler(tool_name: str, input_data: dict, context: Any):
            import asyncio as _asyncio

            from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

            # Hermes' own tools re-enter Hermes dispatch, which applies its
            # own approval policy — don't double-gate.
            if tool_name.startswith("mcp__hermes-tools__"):
                return PermissionResultAllow(updated_input=input_data)
            if approval_callback is None:
                # Gateway/cron: no UI to prompt through — fail closed,
                # mirroring the codex runtime's default.
                return PermissionResultDeny(
                    message="no Hermes approval UI available; denied by policy",
                )
            preview = _json_dumps(input_data)[:200]
            try:
                choice = await _asyncio.to_thread(
                    approval_callback, tool_name, preview, dict(input_data or {})
                )
            except Exception:
                logger.debug("hermes approval callback raised", exc_info=True)
                return PermissionResultDeny(message="approval callback error")
            if str(choice).lower() in {"approve", "approved", "yes", "allow", "always"}:
                return PermissionResultAllow(updated_input=input_data)
            return PermissionResultDeny(message=f"denied by user ({choice})")

        return _handler
```

- [ ] **Step 4: Run the full session test file**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/transports/claude_agent_session.py tests/agent/transports/conftest.py tests/agent/transports/test_claude_agent_session.py
git commit -m "feat(transports): bridge Agent SDK can_use_tool to Hermes approval flow"
```

---

### Task 7: Interrupt support

**Files:**
- Modify: `agent/transports/claude_agent_session.py`
- Test: `tests/agent/transports/test_claude_agent_session.py` (append)

**Interfaces:**
- Produces: `request_interrupt()` — thread-safe, schedules `client.interrupt()` on the session loop, marks the in-flight `ClaudeTurnResult.interrupted = True` (via an `self._active_result` reference set at `run_turn` entry and cleared at exit).

- [ ] **Step 1: Write the failing test**

```python
def test_request_interrupt_calls_sdk_interrupt(fake_claude_sdk, tmp_path):
    session = _make_session(tmp_path)
    session.ensure_started()
    try:
        session.request_interrupt()
        import time
        deadline = time.time() + 2
        while not fake_claude_sdk.clients[0].interrupted and time.time() < deadline:
            time.sleep(0.01)
        assert fake_claude_sdk.clients[0].interrupted
    finally:
        session.close()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v -k interrupt`
Expected: FAIL — no `request_interrupt` attribute.

- [ ] **Step 3: Implement**

```python
    def request_interrupt(self) -> None:
        """Thread-safe: interrupt the in-flight turn (no-op when idle)."""
        if self._client is None or self._loop is None or self._closed:
            return
        active = getattr(self, "_active_result", None)
        if active is not None:
            active.interrupted = True
        asyncio.run_coroutine_threadsafe(self._client.interrupt(), self._loop)
```

And in `run_turn`, wrap the `self._run(self._turn_coro(...))` call with `self._active_result = result` before and `self._active_result = None` in a `finally:`.

- [ ] **Step 4: Run full file**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/transports/claude_agent_session.py tests/agent/transports/test_claude_agent_session.py
git commit -m "feat(transports): interrupt support for claude_agent_sdk sessions"
```

---

### Task 8: claude_runtime.py — the turn orchestrator

**Files:**
- Create: `agent/claude_runtime.py`
- Test: `tests/agent/test_claude_runtime.py`

**Interfaces:**
- Consumes: `ClaudeAgentSession`, `ClaudeTurnResult` (Tasks 4–7).
- Produces: `run_claude_agent_sdk_turn(agent, *, user_message: str, original_user_message, messages: list, effective_task_id: str, should_review_memory: bool = False) -> dict` returning the **same dict shape as `agent/codex_runtime.py::run_codex_app_server_turn`** (keys: `final_response`, `messages`, `api_calls`, `completed`, `partial`, `error`, `agent_persisted`, plus usage keys). Also `_record_claude_agent_usage(agent, turn) -> dict`.

**Implementation guide:** open `agent/codex_runtime.py:231-475` side-by-side and transliterate. The differences are only: session class (`ClaudeAgentSession`), usage key names (SDK uses `input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens` instead of Codex's `inputTokens` / `cachedInputTokens` / `outputTokens`), and no thread/turn ids (use `turn.session_id`). Keep: lazy per-agent session caching on `agent._claude_session`, `agent.session_api_calls += 1`, `CanonicalUsage`/`estimate_usage_cost` from `agent.usage_pricing`, `_iters_since_skill` increment, `_sync_external_memory_for_turn`, `_spawn_background_review`, message projection + `agent._flush_messages_to_session_db`-equivalent flush (copy the exact flush call the codex path makes right after `messages.extend(turn.projected_messages)`), `agent_persisted: True`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_claude_runtime.py
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _fake_agent():
    agent = MagicMock()
    agent.session_api_calls = 0
    agent._iters_since_skill = 0
    agent._skill_nudge_interval = 0
    agent.valid_tool_names = set()
    agent.model = "claude-opus-4-6"
    agent.session_id = None
    agent._session_db = None
    agent._claude_session = None
    agent.session_cwd = "/tmp"
    agent.tool_progress_callback = None
    return agent


def test_turn_returns_codex_shaped_dict():
    from agent.claude_runtime import run_claude_agent_sdk_turn
    from agent.transports.claude_agent_session import ClaudeTurnResult

    turn = ClaudeTurnResult(final_text="hi there", session_id="s1",
                            usage={"input_tokens": 3, "output_tokens": 2})
    fake_session = MagicMock()
    fake_session.run_turn.return_value = turn

    agent = _fake_agent()
    agent._claude_session = fake_session

    out = run_claude_agent_sdk_turn(
        agent,
        user_message="hello",
        original_user_message="hello",
        messages=[{"role": "user", "content": "hello"}],
        effective_task_id="t1",
    )
    assert out["final_response"] == "hi there"
    assert out["completed"] is True
    assert out["partial"] is False
    assert out["error"] is None
    assert out["api_calls"] == 1
    assert out["agent_persisted"] is True


def test_turn_error_marks_partial():
    from agent.claude_runtime import run_claude_agent_sdk_turn
    from agent.transports.claude_agent_session import ClaudeTurnResult

    turn = ClaudeTurnResult(error="boom")
    fake_session = MagicMock()
    fake_session.run_turn.return_value = turn
    agent = _fake_agent()
    agent._claude_session = fake_session

    out = run_claude_agent_sdk_turn(
        agent, user_message="x", original_user_message="x",
        messages=[], effective_task_id="t1",
    )
    assert out["completed"] is False
    assert out["partial"] is True
    assert out["error"] == "boom"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/agent/test_claude_runtime.py -v`
Expected: FAIL — `ModuleNotFoundError: agent.claude_runtime`.

- [ ] **Step 3: Implement by transliterating codex_runtime.py**

Skeleton (fill the marked sections by copying the codex equivalents verbatim and renaming):

```python
# agent/claude_runtime.py
"""claude_agent_sdk runtime path.

* run_claude_agent_sdk_turn — drives one turn through a ClaudeAgentSession
  (Claude Agent SDK / Claude Code subprocess) and projects the results back
  into Hermes' messages + usage accounting.

Sibling of agent/codex_runtime.py — keep the two in structural lockstep.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _coerce_usage_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _record_claude_agent_usage(agent, turn) -> dict[str, Any]:
    """Translate Agent SDK ResultMessage.usage into Hermes accounting.

    SDK keys: input_tokens, output_tokens, cache_read_input_tokens,
    cache_creation_input_tokens. Hermes' canonical prompt bucket includes
    uncached + cached input (mirror _record_codex_app_server_usage)."""
    agent.session_api_calls += 1
    usage = turn.usage
    if not isinstance(usage, dict) or not usage:
        # copy the codex no-usage branch (session-db api_call_count bump)
        return {}

    from agent.usage_pricing import CanonicalUsage, estimate_usage_cost

    input_tokens = _coerce_usage_int(usage.get("input_tokens"))
    cache_read = _coerce_usage_int(usage.get("cache_read_input_tokens"))
    cache_write = _coerce_usage_int(usage.get("cache_creation_input_tokens"))
    output_tokens = _coerce_usage_int(usage.get("output_tokens"))
    # ... construct CanonicalUsage + estimate_usage_cost + session-db update
    # exactly as codex_runtime lines ~133-230 do, with these variables.


def run_claude_agent_sdk_turn(
    agent,
    *,
    user_message: str,
    original_user_message: Any,
    messages: List[Dict[str, Any]],
    effective_task_id: str,
    should_review_memory: bool = False,
) -> Dict[str, Any]:
    from agent.transports.claude_agent_session import ClaudeAgentSession

    if getattr(agent, "_claude_session", None) is None:
        from agent.runtime_cwd import resolve_agent_cwd

        cwd = getattr(agent, "session_cwd", None) or str(resolve_agent_cwd())
        try:
            from tools.terminal_tool import _get_approval_callback
            approval_callback = _get_approval_callback()
        except Exception:
            approval_callback = None
        auto_approve = False
        try:
            from tools.approval import is_approval_bypass_active
            auto_approve = is_approval_bypass_active()
        except Exception:
            logger.debug("approval-bypass lookup failed; fail-closed", exc_info=True)
        agent._claude_session = ClaudeAgentSession(
            model=agent.model,
            cwd=cwd,
            system_prompt=getattr(agent, "system_prompt", None),
            approval_callback=approval_callback,
            auto_approve=auto_approve,
        )
        agent._claude_session.tool_progress_callback = getattr(
            agent, "tool_progress_callback", None
        )

    session = agent._claude_session
    turn = session.run_turn(user_message)
    if turn.should_retire:
        try:
            session.close()
        finally:
            agent._claude_session = None

    if turn.final_text:
        messages.append({"role": "assistant", "content": turn.final_text})
    messages.extend(turn.projected_messages)
    # ── flush to session db + counters + memory sync + background review:
    #    copy the codex_runtime block (lines ~340-440) verbatim, renaming
    #    turn fields per ClaudeTurnResult. ──

    usage_result = _record_claude_agent_usage(agent, turn)
    return {
        "final_response": turn.final_text,
        "messages": messages,
        "api_calls": 1,
        "completed": not turn.interrupted and turn.error is None,
        "partial": turn.interrupted or turn.error is not None,
        "error": turn.error,
        "agent_persisted": True,
        "claude_session_id": turn.session_id,
        **usage_result,
    }
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/agent/test_claude_runtime.py tests/agent/transports/test_claude_agent_session.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/claude_runtime.py tests/agent/test_claude_runtime.py
git commit -m "feat(runtime): run_claude_agent_sdk_turn orchestrator + usage accounting"
```

---

### Task 9: Wire into conversation loop, run_agent forwarder, cleanup

**Files:**
- Modify: `agent/conversation_loop.py` (directly below the `codex_app_server` gate, ~line 633)
- Modify: `run_agent.py` (next to `_run_codex_app_server_turn`, ~line 5749; plus the AIAgent cleanup hook — grep `grep -n "_codex_session" run_agent.py` and mirror its close call)
- Test: `tests/run_agent/test_claude_agent_integration.py`

**Interfaces:**
- Consumes: `run_claude_agent_sdk_turn` (Task 8).
- Produces: `agent.api_mode == "claude_agent_sdk"` short-circuits `run_conversation()` into `agent._run_claude_agent_sdk_turn(...)`; AIAgent shutdown closes `agent._claude_session`.

- [ ] **Step 1: Write the failing test**

Model it on `tests/run_agent/test_codex_app_server_integration.py` — read that file first and copy its agent-construction fixture, changing `api_mode` to `"claude_agent_sdk"`:

```python
# tests/run_agent/test_claude_agent_integration.py
"""run_conversation() dispatches to the claude_agent_sdk runtime.

Mirrors test_codex_app_server_integration.py — reuse its fixture style
for constructing/mocking AIAgent."""
from unittest.mock import MagicMock, patch


def test_conversation_loop_dispatches_claude_agent_sdk():
    # Copy the minimal-agent fixture from test_codex_app_server_integration
    # (same mocked AIAgent), set agent.api_mode = "claude_agent_sdk", then:
    with patch("agent.claude_runtime.run_claude_agent_sdk_turn") as run_turn:
        run_turn.return_value = {"final_response": "ok", "messages": [],
                                 "api_calls": 1, "completed": True,
                                 "partial": False, "error": None,
                                 "agent_persisted": True}
        # invoke run_conversation the same way the codex integration test does
        # and assert run_turn was called exactly once.
```

(The executor fills the fixture from the codex integration test — the assertion contract above is fixed.)

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/run_agent/test_claude_agent_integration.py -v`
Expected: FAIL — dispatch gate missing, `run_claude_agent_sdk_turn` never called.

- [ ] **Step 3: Implement the gate + forwarder + cleanup**

`agent/conversation_loop.py`, directly after the codex gate:

```python
    # Optional opt-in runtime: hand the turn to the Claude Agent SDK
    # (Claude Code subprocess, subscription OAuth). Sibling of the
    # codex_app_server gate above. See agent/claude_runtime.py.
    if agent.api_mode == "claude_agent_sdk":
        return agent._run_claude_agent_sdk_turn(
            user_message=user_message,
            original_user_message=original_user_message,
            messages=messages,
            effective_task_id=effective_task_id,
            should_review_memory=_should_review_memory,
        )
```

`run_agent.py`, next to `_run_codex_app_server_turn`:

```python
    def _run_claude_agent_sdk_turn(
        self,
        *,
        user_message,
        original_user_message,
        messages,
        effective_task_id,
        should_review_memory=False,
    ):
        """Forwarder — see ``agent.claude_runtime.run_claude_agent_sdk_turn``."""
        from agent.claude_runtime import run_claude_agent_sdk_turn
        return run_claude_agent_sdk_turn(self, user_message=user_message, original_user_message=original_user_message, messages=messages, effective_task_id=effective_task_id, should_review_memory=should_review_memory)
```

Cleanup: find where `_codex_session` is closed at AIAgent shutdown (`grep -n "_codex_session" run_agent.py`) and add the identical block for `_claude_session`. Also mirror the codex interrupt hook: `grep -n "request_interrupt" run_agent.py agent/*.py` and forward Hermes interrupts to `agent._claude_session.request_interrupt()` at the same site.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/run_agent/test_claude_agent_integration.py tests/run_agent/test_codex_app_server_integration.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/conversation_loop.py run_agent.py tests/run_agent/test_claude_agent_integration.py
git commit -m "feat(agent): dispatch claude_agent_sdk turns from run_conversation"
```

---

### Task 10: Doctor check + docs

**Files:**
- Modify: `hermes_cli/doctor.py` (find the codex binary check — `grep -n "check_codex_binary" hermes_cli/doctor.py` — add a sibling)
- Create: `plugins/model-providers/claude-agent/README.md`
- Modify: `cli-config.yaml.example` (document `model.anthropic_runtime`)
- Test: `tests/agent/transports/test_claude_agent_session.py` (append binary-check test)

**Interfaces:**
- Produces: `check_claude_binary(claude_bin: str = "claude") -> tuple[bool, str]` in `agent/transports/claude_agent_session.py` (mirroring `codex_app_server.check_codex_binary`).

- [ ] **Step 1: Write the failing test**

```python
def test_check_claude_binary_missing():
    from agent.transports.claude_agent_session import check_claude_binary

    ok, msg = check_claude_binary("definitely-not-a-real-binary-xyz")
    assert ok is False
    assert "not found" in msg
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v -k binary`
Expected: FAIL — ImportError.

- [ ] **Step 3: Implement**

```python
def check_claude_binary(claude_bin: str = "claude") -> tuple[bool, str]:
    """Verify the Claude Code CLI is installed. Returns (ok, message)."""
    import subprocess

    try:
        proc = subprocess.run(
            [claude_bin, "--version"],
            capture_output=True, text=True, timeout=10,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False, (
            f"claude CLI not found at {claude_bin!r}. Install with: "
            f"npm install -g @anthropic-ai/claude-code — then run `claude` "
            f"once and log in with your Claude subscription."
        )
    except subprocess.TimeoutExpired:
        return False, "claude --version timed out"
    if proc.returncode != 0:
        return False, f"claude --version exited {proc.returncode}: {proc.stderr.strip()}"
    return True, proc.stdout.strip()
```

Wire into `hermes_cli/doctor.py` alongside the codex check (only when the `claude-agent` provider or `anthropic_runtime: claude_agent_sdk` is configured — copy the conditional pattern the codex check uses).

- [ ] **Step 4: Write the docs**

`plugins/model-providers/claude-agent/README.md`:

```markdown
# claude-agent — Claude via your Claude subscription (Agent SDK)

Runs Claude models through the Claude Agent SDK, authenticated by your
Claude subscription (Claude Code OAuth). Anthropic's sanctioned path for
subscription-backed third-party use: usage draws from your Pro/Max limits
per Anthropic's current policy (post June-2026 rollback).

## Setup

1. `npm install -g @anthropic-ai/claude-code` and run `claude` once → /login
   with your Claude subscription (or export CLAUDE_CODE_OAUTH_TOKEN from
   `claude setup-token` for headless hosts).
2. `pip install claude-agent-sdk` into Hermes' environment.
3. In config.yaml:

   ```yaml
   model:
     default: claude-opus-4-6
     anthropic_runtime: claude_agent_sdk
   ```
4. `hermes doctor` — the claude CLI check should pass.

## How it works

Claude Code owns the tool loop (terminal, file ops, patching run in its
sandbox). Hermes' own tool surface (web search, browser, vision, kanban,
skills…) is injected into the session via the hermes-tools stdio MCP
server. Tokens/costs are recorded from the SDK's per-turn usage report.

## Caveats

- No `temperature`/`top_p` control — the SDK does not expose sampling params.
- `delegate_task`/`memory`/`todo` Hermes agent-loop tools are unavailable on
  this runtime (same limitation as the codex_app_server runtime).
- ANTHROPIC_API_KEY is deliberately ignored on this path.
```

Add to `cli-config.yaml.example` under the `model:` block:

```yaml
  # Optional opt-in: route Anthropic turns through the Claude Agent SDK
  # (Claude Code subprocess) using your Claude subscription instead of an
  # API key. Requires: npm i -g @anthropic-ai/claude-code (logged in) and
  # pip install claude-agent-sdk. Values: auto (default) | claude_agent_sdk
  # anthropic_runtime: claude_agent_sdk
```

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest tests/agent/transports/test_claude_agent_session.py -v`
Expected: all PASS.

```bash
git add agent/transports/claude_agent_session.py hermes_cli/doctor.py plugins/model-providers/claude-agent/README.md cli-config.yaml.example tests/agent/transports/test_claude_agent_session.py
git commit -m "feat(doctor,docs): claude CLI check + claude-agent provider docs"
```

---

### Task 11: Manual end-to-end smoke test + PR

**Files:**
- No new code — verification and PR prep.

- [ ] **Step 1: Install runtime prerequisites**

```bash
npm install -g @anthropic-ai/claude-code   # skip if already installed
claude --version
uv pip install claude-agent-sdk
```

Run `claude` interactively once and confirm it's logged in with the Claude subscription (`/status` inside the REPL shows the account/plan).

- [ ] **Step 2: Configure and run Hermes**

In `~/.hermes/config.yaml` (or the repo's config): set `model.default: claude-opus-4-6`, `model.provider: claude-agent`, `model.anthropic_runtime: claude_agent_sdk`. Then:

```bash
uv run hermes chat
```

Verify, in order:
1. A plain question returns Claude text (no ANTHROPIC_API_KEY set in the shell — `unset ANTHROPIC_API_KEY` first).
2. "run `ls` in the current directory" triggers a Hermes approval prompt (default mode) and executes after approval.
3. "search the web for today's top HN story" routes through `mcp__hermes-tools__web_search` (visible in tool progress output).
4. A follow-up question retains context (same SDK session).
5. Ctrl-C mid-generation interrupts cleanly and the next turn works.
6. `hermes` session usage/cost display shows nonzero token counts after turns.

- [ ] **Step 3: Full test suite**

```bash
uv run pytest tests/ -q -x --ignore=tests/slow 2>&1 | tail -20
```

Expected: no new failures vs. the Task 0 baseline.

- [ ] **Step 4: PR**

```bash
git push -u origin feat/claude-agent-sdk-runtime
gh pr create --repo NousResearch/hermes-agent \
  --title "feat: claude_agent_sdk runtime — Claude via subscription OAuth (Agent SDK)" \
  --body "Implements #25267. Adds a claude-agent provider profile and a claude_agent_sdk runtime mirroring the codex_app_server runtime: ClaudeAgentSession drives the Claude Agent SDK (Claude Code subprocess, subscription OAuth), Hermes tools are injected via the existing hermes_tools_mcp_server stdio MCP, events/usage project back into Hermes accounting. Opt-in via model.anthropic_runtime: claude_agent_sdk; default paths unchanged."
```

---

## Risks / open questions (carry into execution)

1. **Approval-callback signature** — verified against `tools/terminal_tool.py` in Task 6 Step 1's note; adjust tests before implementing.
2. **System prompt duplication** — Hermes' full system prompt may conflict with Claude Code's preset. If E2E output shows identity confusion, switch Task 8's `system_prompt=` to the SDK's append form: `{"type": "preset", "preset": "claude_code", "append": <hermes prompt>}`.
3. **SDK API drift** — `claude-agent-sdk` is versioned with Claude Code; pin a floor in the docs (`claude-agent-sdk>=0.1`) and re-verify `ClaudeAgentOptions` field names against the installed version during Task 4.
4. **ToS posture** — this uses the Agent SDK + subscription login, the sanctioned path per Anthropic's June-2026 policy state; note in the PR that billing policy is in flux (paused credit-pool plan) so maintainers can gate it behind the existing OAuth provider UX.
