# Qwen3.8-27B Prefix-Cache Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir e executar uma campanha reproduzível que selecione o melhor runtime, cache e quantização do Qwen3.8-27B no Mac Studio M4 Max.

**Architecture:** Um probe HTTP mede streaming, cache e estado do template sem depender do runtime. Scripts separados iniciam `mlx-serve` e `llama.cpp`. Um loop de ferramentas valida o comportamento agentic antes dos benchmarks caros.

**Tech Stack:** Python 3.9+, biblioteca padrão, shell POSIX, OpenAI Chat Completions API, Prometheus metrics, `macmon`, `mlx-serve`, `llama.cpp`, Harbor.

**Spec:** `bench/qwen3.8-prefix-cache/plan.md`

## Global Constraints

- Execute inferência somente no Mac Studio M4 Max com 128 GB e GPU de 40 núcleos.
- Use o MacBook Pro somente como driver e host do Docker.
- Use um runtime por vez.
- Use concorrência igual a 1.
- Use contextos de 8.192, 32.768 e 65.536 tokens.
- Mantenha `preserve_thinking=true` e `reasoning_effort=xhigh` nos braços canônicos.
- Use `reasoning_effort=medium` somente em ablação identificada.
- Preserve os defaults do vendor nos braços canônicos; desligue PLD somente nos controles diagnósticos.
- Deixe KV quantization desligada na fase inicial.
- Salve resultados destilados em `bench/qwen3.8-prefix-cache/results/`.
- Salve logs brutos em `bench/qwen3.8-prefix-cache/logs/`.
- Não execute Terminal-Bench completo antes dos gates baratos.
- Preserve alterações existentes e o diretório `.obsidian/`.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `Taskfile.yml` | Expor a campanha no namespace `qwen38` |
| `bench/qwen3.8-prefix-cache/Taskfile.yml` | Verificar dependências e executar fases |
| `bench/qwen3.8-prefix-cache/scripts/fixtures.py` | Construir prefixes determinísticos e mutações |
| `bench/qwen3.8-prefix-cache/scripts/sse_client.py` | Medir streaming e tempo até o primeiro token |
| `bench/qwen3.8-prefix-cache/scripts/metrics.py` | Ler Prometheus e telemetria do `macmon` |
| `bench/qwen3.8-prefix-cache/scripts/cache_probe.py` | Executar a matriz de cache e gravar JSONL |
| `bench/qwen3.8-prefix-cache/scripts/tool_loop.py` | Executar 20 tool turns com schemas estáveis |
| `bench/qwen3.8-prefix-cache/scripts/summarize.py` | Criar tabelas e aplicar gates |
| `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh` | Iniciar os braços MLX |
| `bench/qwen3.8-prefix-cache/scripts/run-llama-cpp.sh` | Iniciar os braços GGUF |
| `bench/qwen3.8-prefix-cache/scripts/run-campaign.sh` | Orquestrar smoke, 32K e 65K |
| `bench/qwen3.8-prefix-cache/scripts/run-tbench-qwen38-REMOTE.sh` | Executar Harbor no MacBook Pro |
| `bench/qwen3.8-prefix-cache/tests/` | Testar fixtures, SSE, métricas e mensagens |
| `bench/qwen3.8-prefix-cache/results/environment.json` | Fixar ambiente, versões e revisões |
| `bench/qwen3.8-prefix-cache/results/cache-probe.jsonl` | Medições do cache |
| `bench/qwen3.8-prefix-cache/results/tool-loop.jsonl` | Medições do loop agentic |
| `bench/qwen3.8-prefix-cache/results/summary.md` | Resultado destilado e gates |
| `bench/qwen3.8-prefix-cache/results/runtime-survivors.json` | Braços aprovados nos gates funcionais |
| `bench/qwen3.8-prefix-cache/results/selection.json` | Runtime, modelo, porta e braço vencedores |
| `docs/models/qwen3.8-27b/README.md` | Card final do modelo no rig |

### Task 1: Add the Taskfile dependency graph

**Files:**
- Create: `Taskfile.yml`
- Create: `bench/qwen3.8-prefix-cache/Taskfile.yml`

**Interfaces:**
- Consumes: `go-task` instalado com `brew install go-task`.
- Produces: namespace `qwen38` e checks separados para rig e driver.

- [ ] **Step 1: Create the root Taskfile**

```yaml
version: "3"

includes:
  qwen38:
    taskfile: ./bench/qwen3.8-prefix-cache/Taskfile.yml
```

- [ ] **Step 2: Create the campaign Taskfile**

```yaml
version: "3"

vars:
  ROOT: "{{.TASKFILE_DIR}}/../.."
  CAMPAIGN: "{{.ROOT}}/bench/qwen3.8-prefix-cache"

tasks:
  deps:common:
    desc: Check common campaign dependencies
    dir: "{{.ROOT}}"
    preconditions:
      - {sh: "command -v python3", msg: "Install Python 3.9 or newer."}
      - {sh: "command -v curl", msg: "Install curl."}
      - {sh: "command -v jq", msg: "Install jq with: brew install jq"}
      - {sh: "command -v git", msg: "Install Git."}
    cmds:
      - python3 -c 'import sys; assert sys.version_info >= (3, 9), sys.version'

  deps:rig:
    desc: Check Mac Studio runtime dependencies
    deps: [deps:common]
    preconditions:
      - {sh: "command -v macmon", msg: "Install macmon with: brew install macmon"}
      - {sh: "command -v mlx-serve", msg: "Install the pinned mlx-serve release."}
      - {sh: "command -v llama-server", msg: "Install the pinned llama.cpp release."}

  deps:driver:
    desc: Check MacBook Pro driver dependencies
    deps: [deps:common]
    preconditions:
      - {sh: "command -v docker", msg: "Install Docker Desktop."}
      - {sh: "command -v harbor", msg: "Install Harbor 0.8.0."}

  unit:
    desc: Run campaign unit tests
    deps: [deps:common]
    dir: "{{.ROOT}}"
    cmds:
      - python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
      - bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh

  docs:check:
    desc: Check campaign Markdown links and whitespace
    deps: [deps:common]
    dir: "{{.ROOT}}"
    cmds:
      - git diff --check

  validate:
    desc: Run all local campaign checks
    deps: [unit, docs:check]

  smoke:
    desc: Run the 8K runtime smoke stage on the rig
    deps: [deps:rig, unit]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh smoke

  cache:32k:
    desc: Run 32K cache-only arms on the rig
    deps: [deps:rig, unit]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh cache-32k

  mtp:32k:
    desc: Run 32K MTP arms on the rig
    deps: [deps:rig, unit]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh mtp-32k

  cache:65k:
    desc: Run approved arms at 65K on the rig
    deps: [deps:rig, unit]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh cache-65k

  tool-loop:
    desc: Run the controlled 20-turn tool loop on the rig
    deps: [deps:rig, unit]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh tool-loop

  summary:
    desc: Regenerate the campaign summary
    deps: [deps:common, unit]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh summary

  quality:
    desc: Run the cheap quality screen on the rig
    deps: [deps:rig, unit]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-quality-screen.sh

  tbench:
    desc: Run Terminal-Bench from the driver
    deps: [deps:driver]
    dir: "{{.ROOT}}"
    cmds:
      - bash bench/qwen3.8-prefix-cache/scripts/run-tbench-qwen38-REMOTE.sh
```

- [ ] **Step 3: Verify the Taskfile namespace**

Run:

```bash
task --list
```

Expected: output lists tasks under the `qwen38:` namespace.

- [ ] **Step 4: Verify the common dependency task**

Run:

```bash
task qwen38:deps:common
```

Expected: exits 0 on the development Mac.

- [ ] **Step 5: Commit the Taskfiles**

```bash
git add Taskfile.yml bench/qwen3.8-prefix-cache/Taskfile.yml
git commit -m "build: add Qwen3.8 campaign tasks"
```

### Task 2: Build deterministic context fixtures

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/fixtures.py`
- Create: `bench/qwen3.8-prefix-cache/tests/test_fixtures.py`
- Create: `bench/qwen3.8-prefix-cache/results/.gitkeep`

**Interfaces:**
- Consumes: `encode(text: str) -> list[int]` fornecido pelo tokenizer do modelo.
- Produces: `PromptFixture`, `build_fixture()`, `mutate_middle()` e `sha256_tokens()`.

- [ ] **Step 1: Write the fixture tests**

```python
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fixtures import build_fixture, mutate_middle, sha256_tokens


class FixtureTests(unittest.TestCase):
    def test_fixture_reaches_target_and_has_three_needles(self):
        encode = lambda text: text.split()
        fixture = build_fixture(8192, encode)
        self.assertGreaterEqual(len(fixture.token_ids), 8192)
        self.assertEqual(fixture.needles, (
            "XENON-7592-FALCON",
            "ARGON-1844-EMBER",
            "NEON-6301-ORBIT",
        ))
        for needle in fixture.needles:
            self.assertIn(needle, fixture.text)

    def test_middle_mutation_preserves_prefix_before_boundary(self):
        words = [f"w{i}" for i in range(1000)]
        original = " ".join(words)
        changed, boundary = mutate_middle(original, 64)
        self.assertEqual(original.split()[:boundary], changed.split()[:boundary])
        self.assertNotEqual(original.split()[boundary:], changed.split()[boundary:])

    def test_token_hash_is_stable(self):
        self.assertEqual(sha256_tokens([1, 2, 3]), sha256_tokens([1, 2, 3]))
        self.assertNotEqual(sha256_tokens([1, 2, 3]), sha256_tokens([1, 2, 4]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the fixture tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_fixtures.py -v
```

Expected: FAIL because `fixtures` does not exist.

- [ ] **Step 3: Implement the fixture module**

```python
from dataclasses import dataclass
from hashlib import sha256
from struct import pack
from typing import Callable


@dataclass(frozen=True)
class PromptFixture:
    text: str
    token_ids: list[int]
    needles: tuple[str, str, str]


NEEDLES = (
    "XENON-7592-FALCON",
    "ARGON-1844-EMBER",
    "NEON-6301-ORBIT",
)


def _record(index: int) -> str:
    return (
        f"Record {index:06d} stores audit value {index * 7919 % 104729:06d}. "
        f"Its owner is unit-{index % 97:02d} and its revision is r{index % 31:02d}."
    )


def build_fixture(target_tokens: int, encode: Callable[[str], list[int]]) -> PromptFixture:
    records: list[str] = []
    index = 0
    while len(encode("\n".join(records))) < target_tokens:
        records.append(_record(index))
        index += 1
    for fraction, needle in zip((0.1, 0.5, 0.9), NEEDLES):
        position = min(len(records) - 1, int(len(records) * fraction))
        records[position] += f" Verified key: {needle}."
    text = "\n".join(records)
    return PromptFixture(text=text, token_ids=encode(text), needles=NEEDLES)


def mutate_middle(text: str, count: int) -> tuple[str, int]:
    words = text.split()
    boundary = max(1, len(words) // 2 - count // 2)
    end = min(len(words), boundary + count)
    changed = words[:boundary] + [f"mutation-{i:03d}" for i in range(end - boundary)] + words[end:]
    return " ".join(changed), boundary


def sha256_tokens(token_ids: list[int]) -> str:
    digest = sha256()
    for token_id in token_ids:
        digest.update(pack(">I", token_id))
    return digest.hexdigest()
```

- [ ] **Step 4: Run the fixture tests and verify success**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_fixtures.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit the fixture module**

```bash
git add bench/qwen3.8-prefix-cache/scripts/fixtures.py \
  bench/qwen3.8-prefix-cache/tests/test_fixtures.py \
  bench/qwen3.8-prefix-cache/results/.gitkeep
git commit -m "bench(qwen3.8): add deterministic cache fixtures"
```

### Task 3: Build the streaming timing client

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/sse_client.py`
- Create: `bench/qwen3.8-prefix-cache/tests/test_sse_client.py`

**Interfaces:**
- Consumes: OpenAI-compatible `/v1/chat/completions` streaming responses.
- Produces: `StreamResult` and `stream_chat()`.

- [ ] **Step 1: Write SSE parser tests**

```python
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sse_client import iter_sse_json


class SseTests(unittest.TestCase):
    def test_parser_reads_json_and_stops_at_done(self):
        lines = [
            b'data: {"choices":[{"delta":{"content":"A"}}]}\n',
            b'\n',
            b'data: {"choices":[{"delta":{"content":"B"}}]}\n',
            b'data: [DONE]\n',
        ]
        chunks = list(iter_sse_json(lines))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["choices"][0]["delta"]["content"], "A")

    def test_parser_ignores_comments(self):
        lines = [b': ping\n', b'data: {"usage":{"prompt_tokens":8}}\n']
        self.assertEqual(list(iter_sse_json(lines))[0]["usage"]["prompt_tokens"], 8)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the SSE tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_sse_client.py -v
```

Expected: FAIL because `sse_client` does not exist.

- [ ] **Step 3: Implement SSE parsing and timing**

```python
import json
import time
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class StreamResult:
    text: str
    ttft_ms: float
    e2e_ms: float
    usage: dict[str, Any]
    raw_chunks: int


def iter_sse_json(lines: Iterable[bytes]):
    for raw_line in lines:
        line = raw_line.decode("utf-8").strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        yield json.loads(data)


def stream_chat(base_url: str, payload: dict[str, Any], timeout_s: int = 900) -> StreamResult:
    body = dict(payload)
    body["stream"] = True
    body["stream_options"] = {"include_usage": True}
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    first_content_at = None
    content: list[str] = []
    usage: dict[str, Any] = {}
    chunk_count = 0
    with urlopen(request, timeout=timeout_s) as response:
        for chunk in iter_sse_json(response):
            chunk_count += 1
            if chunk.get("usage"):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            delta = choices[0].get("delta", {}) if choices else {}
            piece = delta.get("content") or delta.get("reasoning_content") or ""
            if piece and first_content_at is None:
                first_content_at = time.perf_counter()
            content.append(piece)
    finished = time.perf_counter()
    first = first_content_at or finished
    return StreamResult(
        text="".join(content),
        ttft_ms=(first - started) * 1000,
        e2e_ms=(finished - started) * 1000,
        usage=usage,
        raw_chunks=chunk_count,
    )
```

- [ ] **Step 4: Run the SSE tests and verify success**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_sse_client.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit the streaming client**

```bash
git add bench/qwen3.8-prefix-cache/scripts/sse_client.py \
  bench/qwen3.8-prefix-cache/tests/test_sse_client.py
git commit -m "bench(qwen3.8): measure streaming TTFT"
```

### Task 4: Parse runtime and system metrics

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/metrics.py`
- Create: `bench/qwen3.8-prefix-cache/tests/test_metrics.py`

**Interfaces:**
- Consumes: Prometheus text and one `macmon pipe` JSON object.
- Produces: `parse_prometheus()`, `metric_delta()` e `parse_macmon()`.

- [ ] **Step 1: Write metrics tests**

```python
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from metrics import metric_delta, parse_prometheus


class MetricsTests(unittest.TestCase):
    def test_prometheus_parser_reads_labels(self):
        text = 'prefix_cache_hits_total{model="qwen"} 3\nprefix_cache_tokens_total 8192\n'
        metrics = parse_prometheus(text)
        self.assertEqual(metrics['prefix_cache_hits_total{model="qwen"}'], 3.0)
        self.assertEqual(metrics["prefix_cache_tokens_total"], 8192.0)

    def test_metric_delta_subtracts_snapshots(self):
        before = {"hits": 4.0, "tokens": 100.0}
        after = {"hits": 5.0, "tokens": 250.0}
        self.assertEqual(metric_delta(before, after), {"hits": 1.0, "tokens": 150.0})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run metrics tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_metrics.py -v
```

Expected: FAIL because `metrics` does not exist.

- [ ] **Step 3: Implement metrics parsing**

```python
import json
from typing import Any


def parse_prometheus(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, value = line.rsplit(None, 1)
        result[name] = float(value)
    return result


def metric_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    keys = before.keys() | after.keys()
    return {key: after.get(key, 0.0) - before.get(key, 0.0) for key in keys}


def parse_macmon(line: str) -> dict[str, Any]:
    sample = json.loads(line)
    memory = sample.get("memory", {})
    gpu_usage = sample.get("gpu_usage", [None, 0])
    return {
        "ram_gb": memory.get("ram_usage", 0) / 1e9,
        "swap_gb": memory.get("swap_usage", 0) / 1e9,
        "gpu_pct": float(gpu_usage[1]) * 100 if len(gpu_usage) > 1 else 0.0,
        "power_w": float(sample.get("all_power", 0.0)),
        "gpu_temp_c": float(sample.get("gpu_temp", 0.0)),
    }
```

- [ ] **Step 4: Run metrics tests and verify success**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_metrics.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit metrics support**

```bash
git add bench/qwen3.8-prefix-cache/scripts/metrics.py \
  bench/qwen3.8-prefix-cache/tests/test_metrics.py
git commit -m "bench(qwen3.8): capture cache and system metrics"
```

### Task 5: Implement the cache scenario runner

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/cache_probe.py`
- Create: `bench/qwen3.8-prefix-cache/tests/test_cache_probe.py`

**Interfaces:**
- Consumes: `PromptFixture`, `stream_chat()`, `/metrics` e command-line parameters.
- Produces: one schema-version-1 JSON object per measured request.

- [ ] **Step 1: Write scenario and ratio tests**

```python
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cache_probe import cache_hit_ratio, scenario_messages


class CacheProbeTests(unittest.TestCase):
    def test_cache_ratio_is_bounded(self):
        self.assertEqual(cache_hit_ratio(900, 1000), 0.9)
        self.assertEqual(cache_hit_ratio(1200, 1000), 1.0)
        self.assertEqual(cache_hit_ratio(10, 0), 0.0)

    def test_append_keeps_prior_messages(self):
        base = [{"role": "user", "content": "base"}]
        updated = scenario_messages("append", base, "suffix")
        self.assertEqual(updated[:1], base)
        self.assertEqual(updated[-1]["content"], "suffix")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run cache probe tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_cache_probe.py -v
```

Expected: FAIL because `cache_probe` does not exist.

- [ ] **Step 3: Implement pure scenario helpers**

Start `cache_probe.py` with these interfaces:

```python
#!/usr/bin/env python3
import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fixtures import build_fixture, mutate_middle, sha256_tokens
from sse_client import stream_chat


SCENARIOS = (
    "cold",
    "identical",
    "append",
    "middle_mutation",
    "tool_turn",
)


def cache_hit_ratio(cached_tokens: int, prompt_tokens: int) -> float:
    if prompt_tokens <= 0:
        return 0.0
    return min(1.0, max(0.0, cached_tokens / prompt_tokens))


def scenario_messages(name: str, base: list[dict[str, Any]], suffix: str) -> list[dict[str, Any]]:
    messages = deepcopy(base)
    if name == "identical" or name == "cold":
        return messages
    if name == "append":
        messages.append({"role": "user", "content": suffix})
        return messages
    if name == "tool_turn":
        messages.extend([
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_fixture_1",
                    "type": "function",
                    "function": {"name": "read_fixture", "arguments": '{"path":"audit.txt"}'},
                }],
            },
            {"role": "tool", "tool_call_id": "call_fixture_1", "content": suffix},
        ])
        return messages
    raise ValueError(f"scenario requires dedicated mutation path: {name}")
```

- [ ] **Step 4: Add the CLI and JSONL writer**

The CLI must accept these exact options:

```text
--base-url
--model
--runtime
--runtime-revision
--model-revision
--arm
--context
--repeat
--cache-enabled
--mtp-enabled
--output
--metrics-url
```

Use the runtime `/tokenize` endpoint as the source of token IDs.
Abort the run when the endpoint is unavailable or returns non-integer token IDs.

Read cached tokens from the standard usage field:

```python
def cached_tokens_from_usage(usage: dict) -> int:
    details = usage.get("prompt_tokens_details") or {}
    return int(details.get("cached_tokens") or 0)
```

Write one JSON object after each request. Flush the file after every line.
Use the schema from `bench/qwen3.8-prefix-cache/plan.md`.

- [ ] **Step 5: Run all unit tests**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
```

Expected: 9 tests pass.

- [ ] **Step 6: Verify the CLI help**

Run:

```bash
python3 bench/qwen3.8-prefix-cache/scripts/cache_probe.py --help
```

Expected: exits 0 and lists all 12 options.

- [ ] **Step 7: Commit the cache probe**

```bash
git add bench/qwen3.8-prefix-cache/scripts/cache_probe.py \
  bench/qwen3.8-prefix-cache/tests/test_cache_probe.py
git commit -m "bench(qwen3.8): add prefix-cache scenario probe"
```

### Task 6: Implement the controlled tool loop

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/tool_loop.py`
- Create: `bench/qwen3.8-prefix-cache/tests/test_tool_loop.py`

**Interfaces:**
- Consumes: OpenAI tool calls and `stream_chat()`.
- Produces: 20 turn records and one final-verdict record.

- [ ] **Step 1: Write stable-schema and message tests**

```python
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tool_loop import TOOLS, append_tool_exchange


class ToolLoopTests(unittest.TestCase):
    def test_tools_have_stable_serialization(self):
        first = json.dumps(TOOLS, sort_keys=True, separators=(",", ":"))
        second = json.dumps(TOOLS, sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)

    def test_exchange_preserves_reasoning_content(self):
        messages = [{"role": "user", "content": "start"}]
        call = {
            "role": "assistant",
            "content": "",
            "reasoning_content": "inspect fixture",
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_fixture", "arguments": '{"path":"audit.txt"}'},
            }],
        }
        updated = append_tool_exchange(messages, call, "fixture-value")
        self.assertEqual(updated[-2]["reasoning_content"], "inspect fixture")
        self.assertEqual(updated[-1]["tool_call_id"], "call_1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tool loop tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_tool_loop.py -v
```

Expected: FAIL because `tool_loop` does not exist.

- [ ] **Step 3: Implement fixed tool definitions**

Define these tools in this order:

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_fixture",
            "description": "Read a deterministic campaign fixture.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_fixture",
            "description": "Search the deterministic campaign fixture.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_fixture_test",
            "description": "Run a named deterministic fixture test.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_result",
            "description": "Record one deterministic result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
                "additionalProperties": False,
            },
        },
    },
]
```

- [ ] **Step 4: Implement exact message preservation**

```python
from copy import deepcopy
from typing import Any


def append_tool_exchange(
    messages: list[dict[str, Any]],
    assistant_message: dict[str, Any],
    tool_result: str,
) -> list[dict[str, Any]]:
    updated = deepcopy(messages)
    preserved = deepcopy(assistant_message)
    updated.append(preserved)
    tool_call = preserved["tool_calls"][0]
    updated.append({
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": tool_result,
    })
    return updated
```

- [ ] **Step 5: Add the 20-turn CLI loop**

Use non-streaming requests for tool-call parsing. Measure each request from send to complete response.
Capture `/metrics` before and after each turn.

Write these fields for every turn:

```text
turn
tool_name
tool_arguments_valid
consecutive_same_tool
prompt_tokens
cached_tokens
cache_hit_ratio
elapsed_ms
reasoning_preserved
response_empty
```

Return exit code 2 when a turn fails. Return exit code 0 after all 20 turns pass.

- [ ] **Step 6: Run all unit tests**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
```

Expected: 11 tests pass.

- [ ] **Step 7: Commit the tool loop**

```bash
git add bench/qwen3.8-prefix-cache/scripts/tool_loop.py \
  bench/qwen3.8-prefix-cache/tests/test_tool_loop.py
git commit -m "bench(qwen3.8): add controlled agent tool loop"
```

### Task 7: Add reproducible runtime launchers

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh`
- Create: `bench/qwen3.8-prefix-cache/scripts/run-llama-cpp.sh`
- Create: `bench/qwen3.8-prefix-cache/tests/test_launchers.sh`

**Interfaces:**
- Consumes: arm name `A` through `H` and an optional `--print` argument.
- Produces: one server process with flags fixed by the campaign spec.

- [ ] **Step 1: Write launcher validation**

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS="$ROOT/bench/qwen3.8-prefix-cache/scripts"

bash -n "$SCRIPTS/run-mlx-serve.sh"
bash -n "$SCRIPTS/run-llama-cpp.sh"

MLX_A="$(bash "$SCRIPTS/run-mlx-serve.sh" A --print)"
MLX_B="$(bash "$SCRIPTS/run-mlx-serve.sh" B --print)"
MLX_C="$(bash "$SCRIPTS/run-mlx-serve.sh" C --print)"
GGUF_D="$(bash "$SCRIPTS/run-llama-cpp.sh" D --print)"
GGUF_E="$(bash "$SCRIPTS/run-llama-cpp.sh" E --print)"
GGUF_F="$(bash "$SCRIPTS/run-llama-cpp.sh" F --print)"
GGUF_G="$(bash "$SCRIPTS/run-llama-cpp.sh" G --print)"
GGUF_H="$(bash "$SCRIPTS/run-llama-cpp.sh" H --print)"

grep -q -- '--prefix-cache-entries 0' <<<"$MLX_A"
grep -q -- '--no-mtp' <<<"$MLX_B"
! grep -q -- '--no-mtp' <<<"$MLX_C"
! grep -q -- '--mtp-depth' <<<"$MLX_C"
grep -q -- 'UD-Q4_K_XL' <<<"$GGUF_D"
grep -q -- '--no-cache-prompt' <<<"$GGUF_D"
! grep -q -- '--spec-type' <<<"$GGUF_E"
grep -q -- '--spec-type draft-mtp' <<<"$GGUF_F"
grep -q -- 'UD-Q6_K_XL' <<<"$GGUF_G"
grep -q -- 'UD-Q8_K_XL' <<<"$GGUF_H"
```

- [ ] **Step 2: Run launcher validation and verify failure**

Run:

```bash
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
```

Expected: FAIL because the launchers do not exist.

- [ ] **Step 3: Implement the MLX launcher**

Use a shell array. Map arms exactly:

```text
A: prefix-cache-entries=0, no-mtp, no-pld
B: cache default, no-mtp, no-pld
C: defaults do vendor para cache, MTP, PLD e profundidade especulativa
```

Always include these options:

```text
--model ddalcu/Qwen3.8-27B-MLX-Serve-8bit
--serve
--host 0.0.0.0
--port 11234
--ctx-size 65536
--metrics
```

Print the shell-escaped command and exit when the second argument is `--print`.

- [ ] **Step 4: Implement the GGUF launcher**

Map arms exactly:

```text
D: UD-Q4_K_XL, --no-cache-prompt, sem draft-mtp
E: UD-Q4_K_XL, defaults do runtime, sem draft-mtp
F: UD-Q4_K_XL, defaults do runtime, draft-mtp depth 3
G: UD-Q6_K_XL, defaults do runtime, draft-mtp depth 3
H: UD-Q8_K_XL, defaults do runtime, draft-mtp depth 3
```

Use the base command from `bench/qwen3.8-prefix-cache/plan.md`.
Validate from the startup log that the Unsloth MTP sidecar was loaded and that draft acceptance counters are present.
Print the shell-escaped command and exit when the second argument is `--print`.

- [ ] **Step 5: Run launcher validation and verify success**

Run:

```bash
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
```

Expected: exits 0 without output.

- [ ] **Step 6: Commit the launchers**

```bash
git add bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh \
  bench/qwen3.8-prefix-cache/scripts/run-llama-cpp.sh \
  bench/qwen3.8-prefix-cache/tests/test_launchers.sh
git commit -m "bench(qwen3.8): add pinned runtime launchers"
```

### Task 8: Add campaign orchestration and summary gates

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/run-campaign.sh`
- Create: `bench/qwen3.8-prefix-cache/scripts/summarize.py`
- Create: `bench/qwen3.8-prefix-cache/tests/test_summarize.py`

**Interfaces:**
- Consumes: JSONL from `cache_probe.py` and `tool_loop.py`.
- Produces: `results/summary.md`, `results/runtime-survivors.json` and process exit status for failed gates.

- [ ] **Step 1: Write gate tests**

```python
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize import gate_record


class SummaryTests(unittest.TestCase):
    def test_good_append_record_passes(self):
        record = {
            "scenario": "append",
            "cache_hit_ratio": 0.96,
            "swap_delta_gb": 0.1,
            "ram_peak_gb": 55.0,
            "correct": True,
            "error": None,
        }
        self.assertEqual(gate_record(record), [])

    def test_bad_tool_record_lists_all_failures(self):
        record = {
            "scenario": "tool_turn",
            "cache_hit_ratio": 0.5,
            "swap_delta_gb": 1.0,
            "ram_peak_gb": 90.0,
            "correct": False,
            "error": "HTTP 500",
        }
        failures = gate_record(record)
        self.assertIn("cache_hit_ratio", failures)
        self.assertIn("swap_delta_gb", failures)
        self.assertIn("ram_peak_gb", failures)
        self.assertIn("correct", failures)
        self.assertIn("error", failures)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run summary tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_summarize.py -v
```

Expected: FAIL because `summarize` does not exist.

- [ ] **Step 3: Implement gate evaluation**

```python
def gate_record(record: dict) -> list[str]:
    failures: list[str] = []
    threshold = {
        "identical": 0.95,
        "append": 0.90,
        "tool_turn": 0.90,
    }.get(record.get("scenario"))
    if threshold is not None and record.get("cache_hit_ratio", 0.0) < threshold:
        failures.append("cache_hit_ratio")
    if record.get("swap_delta_gb", 0.0) > 0.5:
        failures.append("swap_delta_gb")
    if record.get("ram_peak_gb", 0.0) > 80.0:
        failures.append("ram_peak_gb")
    if not record.get("correct", False):
        failures.append("correct")
    if record.get("error"):
        failures.append("error")
    return failures
```

Group records by runtime, arm, context and scenario.
Report median, minimum and maximum for TTFT and total time.
Report each gate as `PASS` or `FAIL`.
Write every functionally approved runtime, model, port and arm to `results/runtime-survivors.json`.
Do not choose the winner until the same cheap-quality suites have run on every survivor.

- [ ] **Step 4: Implement staged orchestration**

`run-campaign.sh` must accept one stage:

```text
smoke
cache-32k
mtp-32k
cache-65k
tool-loop
summary
```

The script must refuse unknown stages. It must print each command before execution.
It must create logs under `bench/qwen3.8-prefix-cache/logs/`.

- [ ] **Step 5: Run all tests**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
```

Expected: 13 Python tests pass. The shell test exits 0.

- [ ] **Step 6: Commit orchestration and summary**

```bash
git add bench/qwen3.8-prefix-cache/scripts/run-campaign.sh \
  bench/qwen3.8-prefix-cache/scripts/summarize.py \
  bench/qwen3.8-prefix-cache/tests/test_summarize.py
git commit -m "bench(qwen3.8): orchestrate cache campaign gates"
```

### Task 9: Execute rig preflight and cache stages

**Files:**
- Create: `bench/qwen3.8-prefix-cache/results/environment.json`
- Create: `bench/qwen3.8-prefix-cache/results/cache-probe.jsonl`
- Create: `bench/qwen3.8-prefix-cache/results/tool-loop.jsonl`
- Create: `bench/qwen3.8-prefix-cache/results/summary.md`
- Create: `bench/qwen3.8-prefix-cache/results/runtime-survivors.json`

**Interfaces:**
- Consumes: tested campaign scripts and live runtimes on the rig.
- Produces: pinned environment and distilled measurements.

- [ ] **Step 1: Record the rig environment**

Run on the rig:

```bash
system_profiler SPHardwareDataType
sw_vers
mlx-serve --version
llama-server --version
macmon pipe
```

Store structured values in `results/environment.json`.
Include the output of `git rev-parse HEAD` for source-built runtimes.

- [ ] **Step 2: Run the 8K smoke stage**

Run on the rig:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh smoke
```

Expected: arms A, B, D and E finish three measurements without crashes.

- [ ] **Step 3: Summarize the smoke stage**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh summary
```

Expected: `results/summary.md` contains four 8K arm rows.

- [ ] **Step 4: Run 32K cache and MTP stages**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh cache-32k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh mtp-32k
```

Expected: cache-only arms finish before MTP arms begin.

- [ ] **Step 5: Run approved arms at 65K**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh cache-65k
```

Expected: the script selects only arms that passed 32K gates.

- [ ] **Step 6: Run the 20-turn tool loop**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh tool-loop
```

Expected: each selected arm records 20 tool turns and one verdict.

- [ ] **Step 7: Generate the campaign summary**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh summary
```

Expected: every selected arm has cache, latency, memory and tool-loop gates.
Expected: `results/runtime-survivors.json` lists every arm approved for the common quality screen.

- [ ] **Step 8: Commit distilled results**

```bash
git add bench/qwen3.8-prefix-cache/results/environment.json \
  bench/qwen3.8-prefix-cache/results/cache-probe.jsonl \
  bench/qwen3.8-prefix-cache/results/tool-loop.jsonl \
  bench/qwen3.8-prefix-cache/results/summary.md \
  bench/qwen3.8-prefix-cache/results/runtime-survivors.json
git commit -m "bench(qwen3.8): record prefix-cache campaign"
```

### Task 10: Run the quality screen and Terminal-Bench winner

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/run-quality-screen.sh`
- Create: `bench/qwen3.8-prefix-cache/scripts/run-tbench-qwen38-REMOTE.sh`
- Create: `bench/qwen3.8-prefix-cache/results/quality-screen.jsonl`
- Create: `bench/qwen3.8-prefix-cache/results/selection.json`
- Create: `bench/qwen3.8-prefix-cache/results/tbench-summary.json`

**Interfaces:**
- Consumes: every arm from `results/runtime-survivors.json` and existing benchmark tools.
- Produces: comparable quality records, `results/selection.json`, a 262K winner smoke result and one complete Terminal-Bench result.

- [ ] **Step 1: Implement the quality screen driver**

Run these suites in this order:

```text
jdhodges tool calling
Veerman tool calling
LiveCodeBench fixed questions 1-10
Terminal-Bench fixed five-task subset
65K needle retrieval
```

Use the exact question indexes before reading model answers. Save them in the driver script.
Run the complete fixed set on every survivor before selecting the winner. Never select a candidate from runtime gates alone.

- [ ] **Step 2: Validate the quality driver**

Run:

```bash
bash -n bench/qwen3.8-prefix-cache/scripts/run-quality-screen.sh
```

Expected: exits 0.

- [ ] **Step 3: Execute the quality screen on the rig**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-quality-screen.sh
```

Expected: `quality-screen.jsonl` contains all five suites for every survivor.
Expected: `selection.json` records the winner only after the common quality comparison.

- [ ] **Step 4: Smoke-test the winner at native context**

Run one deterministic needle-retrieval probe at 262.144 tokens with the winning vendor-default configuration.
If the runtime or rig cannot complete it, record the exact limitation; do not silently reduce the context.

- [ ] **Step 5: Implement the remote Terminal-Bench driver**

Copy the protocol from `bench/terminal-bench/scripts/run-tbench-minimax-REMOTE.sh`.
Use these exact settings:

Load the winner with these commands:

```bash
SELECTION="bench/qwen3.8-prefix-cache/results/selection.json"
WINNER_PORT="$(jq -er '.winner.port' "$SELECTION")"
WINNER_MODEL_ID="$(jq -er '.winner.model_id' "$SELECTION")"
export OPENAI_API_BASE="http://macstudio.local:${WINNER_PORT}/v1"
export OPENAI_API_KEY="local-qwen38"
```

Use these Harbor settings:

```text
dataset=terminal-bench/terminal-bench-2
agent=terminus-2
environment=docker
concurrency=1
agent-timeout-multiplier=0.5
```

Pass `"openai/${WINNER_MODEL_ID}"` to Harbor as the model.
The script must not hardcode the winner.

- [ ] **Step 6: Validate and execute Terminal-Bench on the MacBook Pro**

Run:

```bash
bash -n bench/qwen3.8-prefix-cache/scripts/run-tbench-qwen38-REMOTE.sh
bash bench/qwen3.8-prefix-cache/scripts/run-tbench-qwen38-REMOTE.sh
```

Expected: Harbor completes with concurrency 1 and writes its raw job under campaign logs.

- [ ] **Step 7: Convert the Harbor result**

Run the existing adapter:

```bash
SELECTION="bench/qwen3.8-prefix-cache/results/selection.json"
WINNER_MODEL_ID="$(jq -er '.winner.model_id' "$SELECTION")"
JOB_DIR="$(find bench/qwen3.8-prefix-cache/logs/tbench-runs -name result.json -print | sort | tail -1 | xargs dirname)"
python3 tools/local-llm-bench-m4-32gb/scripts/harbor_to_summary.py \
  "$JOB_DIR" \
  --model-label qwen3-8-winner \
  --lm-studio-id "$WINNER_MODEL_ID"
GENERATED="$(find tools/local-llm-bench-m4-32gb/benchmarks/runs -name 'tbench_qwen3-8-winner_*_summary.json' -print | sort | tail -1)"
cp "$GENERATED" bench/qwen3.8-prefix-cache/results/tbench-summary.json
```

Expected: the summary contains pass count, fail count and wall time.

- [ ] **Step 8: Commit quality results**

```bash
git add bench/qwen3.8-prefix-cache/scripts/run-quality-screen.sh \
  bench/qwen3.8-prefix-cache/scripts/run-tbench-qwen38-REMOTE.sh \
  bench/qwen3.8-prefix-cache/results/quality-screen.jsonl \
  bench/qwen3.8-prefix-cache/results/selection.json \
  bench/qwen3.8-prefix-cache/results/tbench-summary.json
git commit -m "bench(qwen3.8): select runtime with agent quality gates"
```

### Task 11: Publish the final rig decision

**Files:**
- Create: `docs/models/qwen3.8-27b/README.md`
- Modify: `docs/models/README.md`
- Modify: `docs/local-llm-reference.md`
- Modify: `docs/testing-plan.md`
- Modify: `bench/qwen3.8-prefix-cache/results/summary.md`

**Interfaces:**
- Consumes: all campaign results.
- Produces: one current daily-driver recommendation and reproducible launch command.

- [ ] **Step 1: Write the model card**

Include these sections:

```text
At a glance
Variants tested
Runtime and revisions
Cold and warm prefill
Tool-turn cache behavior
MTP behavior
Quality screen
Terminal-Bench
Memory and context
Production command
Known limitations
Verdict
History
```

Every measured claim must link to a file under `bench/qwen3.8-prefix-cache/results/`.

- [ ] **Step 2: Update the model index and local reference**

Add one row for Qwen3.8-27B. Mark its role with the campaign verdict.
Do not remove the Qwen3.6 baseline.

- [ ] **Step 3: Update the testing plan**

Document the new cache protocol. Add TTFT, cache hit and tool-turn reuse as standard runtime metrics.

- [ ] **Step 4: Validate documentation links**

Run:

```bash
task qwen38:docs:check
```

Expected: exits 0.

- [ ] **Step 5: Validate the repository**

Run:

```bash
task qwen38:validate
```

Expected: the diff check exits 0, 13 Python tests pass and the shell test exits 0.

- [ ] **Step 6: Commit the final decision**

```bash
git add docs/models/qwen3.8-27b/README.md \
  docs/models/README.md \
  docs/local-llm-reference.md \
  docs/testing-plan.md \
  bench/qwen3.8-prefix-cache/results/summary.md
git commit -m "docs(qwen3.8): publish M4 Max runtime decision"
```

## Self-Review Checklist

- [ ] Every campaign requirement maps to one task.
- [ ] All script interfaces have one owner.
- [ ] Test names match implementation names.
- [ ] Runtime arms match the campaign matrix.
- [ ] Tool schemas keep a fixed order.
- [ ] The plan stores raw logs only under ignored paths.
- [ ] The plan commits only distilled results.
- [ ] Terminal-Bench runs only after cheap gates.
- [ ] Final documentation links to local evidence.
