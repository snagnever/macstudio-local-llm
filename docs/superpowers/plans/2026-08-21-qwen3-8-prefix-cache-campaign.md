# Qwen3.8-27B Prefix-Cache Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir e executar uma campanha reproduzível que selecione o setup de maior desempenho — runtime, cache, decode especulativo, quantização e prefill — do Qwen3.8-27B no Mac Studio M4 Max.

**Architecture:** Um probe HTTP mede streaming, cache, especulação e estado do template sem depender do runtime. Launchers separados iniciam `mlx-serve`, `llama.cpp`, `oMLX` e `mlx-dspark`. Perfis isolam cache, MTP, DSpark, DFlash 2, SpecPrefill e prefill ANE. Um loop de ferramentas valida o comportamento agentic antes dos benchmarks caros.

**Tech Stack:** Python 3.9+, biblioteca padrão, shell POSIX, OpenAI Chat Completions API, Prometheus metrics, `macmon`, `mlx-serve`, `llama.cpp`, `oMLX`, `mlx-dspark`, Harbor.

**Spec:** `bench/qwen3.8-prefix-cache/plan.md`

## Global Constraints

- Execute inferência somente no Mac Studio M4 Max com 128 GB e GPU de 40 núcleos.
- Use o MacBook Pro somente como driver e host do Docker.
- Use um runtime por vez.
- Use concorrência igual a 1.
- Use contextos de 8.192, 32.768 e 65.536 tokens.
- Use 16.384 tokens para as comparações de SpecPrefill e ANE.
- Mantenha `preserve_thinking=true` e `reasoning_effort=xhigh` nos braços canônicos.
- Use `reasoning_effort=medium` somente em ablação identificada.
- Preserve os defaults do vendor nos braços canônicos; desligue PLD somente nos controles diagnósticos.
- Use `OMLX_BASE_PATH` isolado por execução. Não altere `~/.omlx`.
- Fixe o `oMLX` v0.6.3 estável. Use `v0.6.3rc2` somente quando a versão estável não existir.
- Não misture revisões do `oMLX` numa comparação.
- Fixe `mlx-dspark` em `v0.15.0` (`69cd5c1`) e não misture versões.
- Use o mesmo target `mlx-community/Qwen3.8-27B-8bit` nos braços P–S.
- Use `--max-draft auto`; não copie caps publicados em outro Mac.
- Preserve lookup drafts nos braços canônicos; ablações devem ser identificadas.
- Use o AWQ 5,0 bpw somente no `oMLX`.
- Compare SpecPrefill com o braço L no mesmo contexto.
- Compare ANE com o braço J no mesmo contexto.
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
| `bench/qwen3.8-prefix-cache/config/omlx-arms.json` | Fixar os perfis I–O e os drafts |
| `bench/qwen3.8-prefix-cache/scripts/omlx_config.py` | Gerar configuração isolada do oMLX |
| `bench/qwen3.8-prefix-cache/scripts/run-omlx.sh` | Iniciar os braços oMLX |
| `bench/qwen3.8-prefix-cache/config/mlx-dspark-arms.json` | Fixar target, drafters e perfis P–S |
| `bench/qwen3.8-prefix-cache/scripts/mlx_dspark_config.py` | Validar perfis e construir comandos reproduzíveis |
| `bench/qwen3.8-prefix-cache/scripts/run-mlx-dspark.sh` | Iniciar baseline, DSpark ou DFlash 2 na porta 8484 |
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

## Progress Snapshot

- Tasks 1–8 foram implementadas nos commits `cf6c832` até `27ca205`.
- O preflight foi salvo em `results/environment.json` no commit `e56d5e2`.
- O preflight comum, o preflight do rig e o check do Metal passaram.
- Os snapshots `mlx8`, GGUF Q4 e MTP foram baixados e verificados; AWQ, Q6/Q8,
  drafts do SpecPrefill e artefatos do `mlx-dspark` continuam pendentes.
- Tentativas diagnósticas de inferência encontraram e corrigiram problemas no harness,
  mas ainda não existe uma sessão canônica completa aprovada pelos gates.

### Task 1: Add the Taskfile dependency graph

**Files:**
- Create: `Taskfile.yml`
- Create: `bench/qwen3.8-prefix-cache/Taskfile.yml`

**Interfaces:**
- Consumes: `go-task` instalado com `brew install go-task`.
- Produces: namespace `qwen38` e checks separados para rig e driver.

- [x] **Step 1: Create the root Taskfile**

```yaml
version: "3"

includes:
  qwen38:
    taskfile: ./bench/qwen3.8-prefix-cache/Taskfile.yml
```

- [x] **Step 2: Create the campaign Taskfile**

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

- [x] **Step 3: Verify the Taskfile namespace**

Run:

```bash
task --list
```

Expected: output lists tasks under the `qwen38:` namespace.

- [x] **Step 4: Verify the common dependency task**

Run:

```bash
task qwen38:deps:common
```

Expected: exits 0 on the development Mac.

- [x] **Step 5: Commit the Taskfiles**

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

- [x] **Step 1: Write the fixture tests**

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

- [x] **Step 2: Run the fixture tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_fixtures.py -v
```

Expected: FAIL because `fixtures` does not exist.

- [x] **Step 3: Implement the fixture module**

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

- [x] **Step 4: Run the fixture tests and verify success**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_fixtures.py -v
```

Expected: 3 tests pass.

- [x] **Step 5: Commit the fixture module**

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

- [x] **Step 1: Write SSE parser tests**

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

- [x] **Step 2: Run the SSE tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_sse_client.py -v
```

Expected: FAIL because `sse_client` does not exist.

- [x] **Step 3: Implement SSE parsing and timing**

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

- [x] **Step 4: Run the SSE tests and verify success**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_sse_client.py -v
```

Expected: 2 tests pass.

- [x] **Step 5: Commit the streaming client**

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

- [x] **Step 1: Write metrics tests**

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

- [x] **Step 2: Run metrics tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_metrics.py -v
```

Expected: FAIL because `metrics` does not exist.

- [x] **Step 3: Implement metrics parsing**

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

- [x] **Step 4: Run metrics tests and verify success**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_metrics.py -v
```

Expected: 2 tests pass.

- [x] **Step 5: Commit metrics support**

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

- [x] **Step 1: Write scenario and ratio tests**

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

- [x] **Step 2: Run cache probe tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_cache_probe.py -v
```

Expected: FAIL because `cache_probe` does not exist.

- [x] **Step 3: Implement pure scenario helpers**

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

- [x] **Step 4: Add the CLI and JSONL writer**

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

- [x] **Step 5: Run all unit tests**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
```

Expected: 9 tests pass.

- [x] **Step 6: Verify the CLI help**

Run:

```bash
python3 bench/qwen3.8-prefix-cache/scripts/cache_probe.py --help
```

Expected: exits 0 and lists all 12 options.

- [x] **Step 7: Commit the cache probe**

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

- [x] **Step 1: Write stable-schema and message tests**

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

- [x] **Step 2: Run tool loop tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_tool_loop.py -v
```

Expected: FAIL because `tool_loop` does not exist.

- [x] **Step 3: Implement fixed tool definitions**

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

- [x] **Step 4: Implement exact message preservation**

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

- [x] **Step 5: Add the 20-turn CLI loop**

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

- [x] **Step 6: Run all unit tests**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
```

Expected: 11 tests pass.

- [x] **Step 7: Commit the tool loop**

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

- [x] **Step 1: Write launcher validation**

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

- [x] **Step 2: Run launcher validation and verify failure**

Run:

```bash
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
```

Expected: FAIL because the launchers do not exist.

- [x] **Step 3: Implement the MLX launcher**

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

- [x] **Step 4: Implement the GGUF launcher**

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

- [x] **Step 5: Run launcher validation and verify success**

Run:

```bash
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
```

Expected: exits 0 without output.

- [x] **Step 6: Commit the launchers**

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

- [x] **Step 1: Write gate tests**

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

- [x] **Step 2: Run summary tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_summarize.py -v
```

Expected: FAIL because `summarize` does not exist.

- [x] **Step 3: Implement gate evaluation**

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

- [x] **Step 4: Implement staged orchestration**

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

- [x] **Step 5: Run all tests**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
```

Expected: 13 Python tests pass. The shell test exits 0.

- [x] **Step 6: Commit orchestration and summary**

```bash
git add bench/qwen3.8-prefix-cache/scripts/run-campaign.sh \
  bench/qwen3.8-prefix-cache/scripts/summarize.py \
  bench/qwen3.8-prefix-cache/tests/test_summarize.py
git commit -m "bench(qwen3.8): orchestrate cache campaign gates"
```

### Task 9: Add isolated oMLX profiles and launcher

**Files:**
- Create: `bench/qwen3.8-prefix-cache/config/omlx-arms.json`
- Create: `bench/qwen3.8-prefix-cache/scripts/omlx_config.py`
- Create: `bench/qwen3.8-prefix-cache/scripts/run-omlx.sh`
- Create: `bench/qwen3.8-prefix-cache/tests/test_omlx_config.py`
- Modify: `bench/qwen3.8-prefix-cache/tests/test_launchers.sh`

**Interfaces:**
- Consumes: arm I–O, local model directory, draft paths and an isolated base path.
- Produces: `settings.json`, `model_settings.json` and one `omlx serve` process on port 8000.

- [ ] **Step 1: Write failing profile tests**

Test these mappings in `test_omlx_config.py`:

```text
I: mlx8, cache off, MTP off, SpecPrefill off, ANE off
J: awq5, cache off, MTP off, SpecPrefill off, ANE off
K: awq5, cache on, MTP off, SpecPrefill off, ANE off
L: awq5, cache on, MTP on, SpecPrefill off, ANE off
M: awq5, cache on, MTP on, draft-2b, keep 0.40, threshold 8192
N: awq5, cache on, MTP on, draft-08b, keep 0.50, threshold 8192
O: awq5, cache off, MTP off, SpecPrefill off, ANE on
```

Assert that every arm writes one model entry.
Assert that the generator rejects an unknown arm.
Assert that M and N require local draft paths.
Assert that O requires a recorded tuner profile.

- [ ] **Step 2: Run the profile tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_omlx_config.py -v
```

Expected: FAIL because `omlx_config` does not exist.

- [ ] **Step 3: Implement the declarative arm map**

Store model repository IDs, pinned revisions and per-model fields in `config/omlx-arms.json`.
Do not store machine-specific absolute paths.

Implement these functions in `omlx_config.py`:

```python
def load_arm(path: Path, arm: str) -> dict: ...
def validate_arm(profile: dict, model_paths: dict[str, Path]) -> None: ...
def write_omlx_state(base_path: Path, profile: dict, model_paths: dict[str, Path]) -> None: ...
```

Write global state to `<base_path>/settings.json`.
Write per-model state to `<base_path>/model_settings.json`.
Use the oMLX versioned envelopes for both files.

- [ ] **Step 4: Implement the isolated launcher**

`run-omlx.sh` must accept an arm and optional `--print`.
It must require `OMLX_MODEL_ROOT`.
It must require `OMLX_DRAFT_2B_PATH` for M.
It must require `OMLX_DRAFT_08B_PATH` for N.
It must require `OMLX_ANE_PROFILE` for O.

Create the execution state under:

```text
bench/qwen3.8-prefix-cache/logs/omlx/<run-id>/
```

Export these values before `omlx serve`:

```text
OMLX_BASE_PATH=<isolated path>
OMLX_MODEL_DIR=<model root>
OMLX_PORT=8000
OMLX_CACHE_ENABLED=<arm value>
```

Print the shell-escaped command and resolved profile for `--print`.
Never read or write `~/.omlx`.

- [ ] **Step 5: Extend launcher validation**

Add `bash -n` for `run-omlx.sh`.
Check printed profiles for arms I–O.
Check that M and N use the required draft and keep values.
Check that O enables only `qwen35_ane_prefill_enabled` among prefill techniques.

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_omlx_config.py -v
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
```

Expected: all new Python tests pass. The shell test exits 0.

- [ ] **Step 6: Commit the oMLX integration**

```bash
git add bench/qwen3.8-prefix-cache/config/omlx-arms.json \
  bench/qwen3.8-prefix-cache/scripts/omlx_config.py \
  bench/qwen3.8-prefix-cache/scripts/run-omlx.sh \
  bench/qwen3.8-prefix-cache/tests/test_omlx_config.py \
  bench/qwen3.8-prefix-cache/tests/test_launchers.sh
git commit -m "bench(qwen3.8): add isolated oMLX arms"
```

### Task 10: Measure SpecPrefill and ANE without confounding effects

**Files:**
- Modify: `bench/qwen3.8-prefix-cache/scripts/cache_probe.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/metrics.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/sse_client.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/summarize.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/run-campaign.sh`
- Modify: `bench/qwen3.8-prefix-cache/Taskfile.yml`
- Modify: `bench/qwen3.8-prefix-cache/tests/test_cache_probe.py`
- Modify: `bench/qwen3.8-prefix-cache/tests/test_metrics.py`
- Modify: `bench/qwen3.8-prefix-cache/tests/test_summarize.py`

**Interfaces:**
- Consumes: oMLX response usage, structured server logs and `macmon` telemetry.
- Produces: schema version 3 records and separate gates for SpecPrefill and ANE.

- [ ] **Step 1: Write failing schema and gate tests**

Require these schema fields:

```text
specprefill_enabled
specprefill_draft_model
specprefill_draft_revision
specprefill_keep_pct
specprefill_threshold
specprefill_selected_tokens
specprefill_scored_tokens
specprefill_draft_ms
specprefill_target_ms
static_prefix_cached_tokens
ane_prefill_enabled
ane_prefill_tuned
ane_compiled_mlp_layers
ane_compiled_gdn_layers
prompt_work_mode
speculation_mode
drafter_id
drafter_revision
draft_cap_policy
draft_cap_resolved
drafted_tokens
accepted_tokens
accept_length
verification_steps
decode_speedup_vs_baseline
machine_roofline_tps
decode_roofline_ratio
```

Add a SpecPrefill gate fixture with L and M at the same context.
Verify PASS at 20% lower median TTFT with correct needles.
Verify FAIL when a needle or tool-loop verdict fails.

Add an ANE gate fixture with J and O at the same context.
Verify PASS at 5% lower median TTFT with confirmed ANE operations.
Verify INCONCLUSIVE when the operation count is zero.

- [ ] **Step 2: Run the new tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_cache_probe.py -v
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_metrics.py -v
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_summarize.py -v
```

Expected: FAIL because schema version 3 and the new gates do not exist.

- [ ] **Step 3: Extend request and measurement records**

Send `specprefill`, `specprefill_keep_pct` and `specprefill_threshold` for M and N.
Send `specprefill=false` for J, K, L and O.

Record unavailable server metrics as `null`.
Never infer selected-token counts from prompt length.
Set `prompt_work_mode` from observed execution: `full`, `cached` or `sparse`.

Use unique cold prompts for each repetition.
Reuse the exact system and tool prefix for warm repetitions.
Preserve the existing response-content policy.

- [ ] **Step 4: Implement pairwise gates**

Compare L against M and N at 16K and 32K.
Compare J against O at 16K and 32K.
Reject comparisons with different model revisions, contexts or sampling settings.

Use median TTFT and median total time.
Report `prompt_tps` without using it for the SpecPrefill verdict.
Advance one SpecPrefill profile to 65K only after both 16K and 32K pass.

- [ ] **Step 5: Extend stages and Taskfile tasks**

Add these stages to `run-campaign.sh`:

```text
omlx-smoke
omlx-cache-32k
omlx-mtp-32k
specprefill-16k
specprefill-32k
ane-16k
ane-32k
```

Add matching tasks under the `qwen38:` namespace.
Add `omlx` to `deps:rig`.
Keep the existing A–H stages unchanged.

- [ ] **Step 6: Run local verification**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
task qwen38:validate
```

Expected: all Python tests pass. The shell test and validation task exit 0.

- [ ] **Step 7: Commit SpecPrefill and ANE support**

```bash
git add bench/qwen3.8-prefix-cache/Taskfile.yml \
  bench/qwen3.8-prefix-cache/scripts/cache_probe.py \
  bench/qwen3.8-prefix-cache/scripts/metrics.py \
  bench/qwen3.8-prefix-cache/scripts/sse_client.py \
  bench/qwen3.8-prefix-cache/scripts/summarize.py \
  bench/qwen3.8-prefix-cache/scripts/run-campaign.sh \
  bench/qwen3.8-prefix-cache/tests/test_cache_probe.py \
  bench/qwen3.8-prefix-cache/tests/test_metrics.py \
  bench/qwen3.8-prefix-cache/tests/test_summarize.py
git commit -m "bench(qwen3.8): measure speculative prefill paths"
```

### Task 11: Add mlx-dspark performance arms

**Files:**
- Create: `bench/qwen3.8-prefix-cache/config/mlx-dspark-arms.json`
- Create: `bench/qwen3.8-prefix-cache/scripts/mlx_dspark_config.py`
- Create: `bench/qwen3.8-prefix-cache/scripts/run-mlx-dspark.sh`
- Create: `bench/qwen3.8-prefix-cache/tests/test_mlx_dspark_config.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/sse_client.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/cache_probe.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/summarize.py`
- Modify: `bench/qwen3.8-prefix-cache/scripts/run-campaign.sh`
- Modify: `bench/qwen3.8-prefix-cache/Taskfile.yml`
- Modify: `bench/qwen3.8-prefix-cache/tests/test_sse_client.py`
- Modify: `bench/qwen3.8-prefix-cache/tests/test_summarize.py`
- Modify: `bench/qwen3.8-prefix-cache/tests/test_launchers.sh`

**Interfaces:**
- Consumes: pinned local target and drafter snapshots, arms P–S and the existing OpenAI-compatible probe.
- Produces: one `mlx-dspark serve` process on port 8484, schema-version-3 speculation telemetry and a pairwise performance verdict against Q.

- [ ] **Step 1: Write failing config, telemetry and gate tests**

In `test_mlx_dspark_config.py`, require these exact mappings:

```text
P: baseline, prefix cache off, no drafter
Q: baseline, prefix cache on, no drafter
R: dspark, prefix cache on, RadixArk/Qwen3.8-27B-DSpark, max-draft auto
S: dflash, prefix cache on, incoai/Qwen3.8-27B-DFlash2, max-draft auto
```

Assert that every arm uses target `mlx-community/Qwen3.8-27B-8bit` at revision
`815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9`. Assert that R and S require local
draft paths, no arm contains an integer draft cap, and an unknown arm is rejected.

In `test_sse_client.py`, pass an `x_mlx_dspark` fixture containing TTFT, prefill
seconds, decode seconds, cached prompt tokens, accept length, resolved draft cap and
decode-only tok/s. Assert exact normalization into the schema-version-3 fields.

In `test_summarize.py`, build paired Q/R/S records for code, math, chat and tool JSON.
Assert PASS for a candidate with 1.25x aggregate decode at 8K, 1.15x at 32K,
positive gain in three classes, no class below 0.95x, and 10% lower warm loop time.
Assert FAIL when token equivalence, telemetry completeness or any threshold fails.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_mlx_dspark_config.py -v
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_sse_client.py -v
python3 -m unittest bench/qwen3.8-prefix-cache/tests/test_summarize.py -v
```

Expected: the config module and schema-version-3 speculation fields are missing.

- [ ] **Step 3: Implement the declarative arm map**

Write `config/mlx-dspark-arms.json` with runtime version `v0.15.0`, port 8484,
the three pinned Hugging Face revisions and arms P–S. Do not store absolute paths.

Implement these functions in `mlx_dspark_config.py`:

```python
load_arm(path: Path, arm: str) -> dict
validate_arm(profile: dict, model_paths: dict[str, Path]) -> None
build_command(profile: dict, model_paths: dict[str, Path]) -> list[str]
```

`build_command` must always emit `--host 0.0.0.0`, `--port 8484`,
`--context-window 65536` and `--reasoning-effort xhigh`. Emit
`--no-prefix-cache` only for P. Emit explicit `--mode`, `--drafter` and
`--max-draft auto` for R and S. Do not emit `--kv-bits`.

- [ ] **Step 4: Implement the launcher and auto-resolution smoke**

`run-mlx-dspark.sh` must accept P, Q, R, S or `auto-smoke`, plus optional `--print`.
Require `MLX_DSPARK_TARGET_PATH` for every arm, `MLX_DSPARK_DSPARK_PATH` for R and
`MLX_DSPARK_DFLASH2_PATH` for S. Verify `mlx-dspark --version` reports `0.15.0`.

For `auto-smoke`, start `--mode auto`, query `/health`, assert the resolved mode is
`dflash` and the drafter identifies `incoai/Qwen3.8-27B-DFlash2`, then stop without
writing a benchmark record. For P–S, print the shell-escaped command and `exec` it.

- [ ] **Step 5: Normalize telemetry and implement the performance gate**

Add nullable speculation fields from schema version 3 to every probe record.
Implement:

```python
normalize_mlx_dspark_metrics(extension: dict, machine: dict | None) -> dict
evaluate_speculative_decode(records: list[dict], baseline_arm: str = "Q") -> dict
```

Use only observed `x_mlx_dspark`, `/metrics` and `/machine` values. Pair records by
target revision, context, content class, sampling and output limit. Report R and S
separately, including median decode speedup, warm-loop speedup, class coverage,
cache regression and the selected winner. Missing pairs produce `INCONCLUSIVE`, not 0.

- [ ] **Step 6: Add mlx-dspark campaign stages and tasks**

Add these stages to `run-campaign.sh`:

```text
dspark-smoke
dspark-decode-8k
dspark-cache-32k
dspark-decode-32k
```

Add matching `dspark:smoke`, `dspark:decode:8k`, `dspark:cache:32k` and
`dspark:decode:32k` tasks. Add `mlx-dspark` to `deps:rig`. The decode stages must
run the four fixed content classes with at least 512 requested completion tokens.
The cache stage must run `cold`, `identical`, `append`, `middle_mutation` and
`tool_turn`. Keep concurrency at 1 and one runtime process active at a time.

- [ ] **Step 7: Verify and commit the integration**

Run:

```bash
python3 -m unittest discover -s bench/qwen3.8-prefix-cache/tests -v
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh
task qwen38:validate
```

Expected: all Python and shell tests pass; validation exits 0.

```bash
git add bench/qwen3.8-prefix-cache/config/mlx-dspark-arms.json \
  bench/qwen3.8-prefix-cache/scripts/mlx_dspark_config.py \
  bench/qwen3.8-prefix-cache/scripts/run-mlx-dspark.sh \
  bench/qwen3.8-prefix-cache/scripts/sse_client.py \
  bench/qwen3.8-prefix-cache/scripts/cache_probe.py \
  bench/qwen3.8-prefix-cache/scripts/summarize.py \
  bench/qwen3.8-prefix-cache/scripts/run-campaign.sh \
  bench/qwen3.8-prefix-cache/Taskfile.yml \
  bench/qwen3.8-prefix-cache/tests/test_mlx_dspark_config.py \
  bench/qwen3.8-prefix-cache/tests/test_sse_client.py \
  bench/qwen3.8-prefix-cache/tests/test_summarize.py \
  bench/qwen3.8-prefix-cache/tests/test_launchers.sh
git commit -m "bench(qwen3.8): add dspark performance arms"
```

### Task 12: Execute rig preflight and runtime stages

**Files:**
- Create: `bench/qwen3.8-prefix-cache/results/environment.json`
- Create: `bench/qwen3.8-prefix-cache/results/cache-probe.jsonl`
- Create: `bench/qwen3.8-prefix-cache/results/tool-loop.jsonl`
- Create: `bench/qwen3.8-prefix-cache/results/summary.md`
- Create: `bench/qwen3.8-prefix-cache/results/runtime-survivors.json`

**Interfaces:**
- Consumes: tested campaign scripts and live runtimes on the rig.
- Produces: pinned environment and distilled measurements.

- [x] **Step 1: Record the rig environment**

Run on the rig:

```bash
system_profiler SPHardwareDataType
sw_vers
mlx-serve --version
llama-server --version
omlx --version
mlx-dspark --version
macmon pipe
```

Store structured values in `results/environment.json`.
Include the output of `git rev-parse HEAD` for source-built runtimes.

- [ ] **Step 2: Download and verify model artifacts**

Download the six target artifacts and four drafts from their pinned revisions.
Record each local path, size and SHA-256 in `results/environment.json`.
Record `omlx --version` and `mlx-dspark --version` after installing the pinned runtimes.

Verify the AWQ revision:

```text
dc699a76ddcbef44c188a8aee2ccc79ccc339a04
```

Confirm that its history contains the repaired MTP-head commit.
Do not continue with an older AWQ snapshot.

- [ ] **Step 3: Run the 8K baseline smoke stage**

Run on the rig:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh smoke
```

Expected: arms A, B, D and E finish three measurements without crashes.

- [ ] **Step 4: Run the 8K oMLX smoke stage**

Run on the rig:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh omlx-smoke
```

Expected: J finishes three measurements without crashes.
Expected: I either passes or records a loader incompatibility.

- [ ] **Step 5: Run the 8K mlx-dspark smoke and decode stage**

Run on the rig:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh dspark-smoke
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh dspark-decode-8k
```

Expected: auto-smoke resolves DFlash 2. Expected: P, Q, R and S produce complete
code, math, chat and tool-JSON records, and R/S pass greedy token equivalence.

- [ ] **Step 6: Summarize the smoke stages**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh summary
```

Expected: `results/summary.md` contains the completed 8K arms A–S that apply to each runtime stage.

- [ ] **Step 7: Run 32K cache, MTP and speculative-decode stages**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh cache-32k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh mtp-32k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh omlx-cache-32k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh omlx-mtp-32k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh dspark-cache-32k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh dspark-decode-32k
```

Expected: cache-only arms finish before MTP arms begin.
Expected: Q, R and S have paired 32K results for all four content classes.

- [ ] **Step 8: Run SpecPrefill and ANE stages**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh specprefill-16k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh specprefill-32k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh ane-16k
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh ane-32k
```

Expected: L, M and N have pairwise SpecPrefill results.
Expected: J and O have pairwise ANE results.

- [ ] **Step 9: Run approved arms at 65K**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh cache-65k
```

Expected: the script selects only arms that passed 32K gates. For `mlx-dspark`,
run Q and the faster of R/S; retain both speculative modes only within a 5% tie.

- [ ] **Step 10: Run the 20-turn tool loop**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh tool-loop
```

Expected: each selected arm records 20 tool turns and one verdict.

- [ ] **Step 11: Generate the campaign summary**

Run:

```bash
bash bench/qwen3.8-prefix-cache/scripts/run-campaign.sh summary
```

Expected: every selected arm has cache, latency, memory and tool-loop gates.
Expected: every oMLX arm has explicit SpecPrefill and ANE verdicts.
Expected: P–S have explicit cache, decode, time-total and drafter-telemetry verdicts.
Expected: `results/runtime-survivors.json` lists every arm approved for the common quality screen.

- [ ] **Step 12: Commit distilled results**

```bash
git add bench/qwen3.8-prefix-cache/results/environment.json \
  bench/qwen3.8-prefix-cache/results/cache-probe.jsonl \
  bench/qwen3.8-prefix-cache/results/tool-loop.jsonl \
  bench/qwen3.8-prefix-cache/results/summary.md \
  bench/qwen3.8-prefix-cache/results/runtime-survivors.json
git commit -m "bench(qwen3.8): record prefix-cache campaign"
```

### Task 13: Run the quality screen and Terminal-Bench winner

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

### Task 14: Publish the final rig decision

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
DSpark and DFlash 2 behavior
Sustained decode by content class
SpecPrefill behavior and selected draft
ANE prefill behavior
AWQ 5.0 bpw behavior
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

Document the new cache protocol. Add TTFT, cache hit, tool-turn reuse, sustained decode,
speculative acceptance and end-to-end loop time as standard runtime metrics.

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

Expected: the diff check, every Python test and the shell launcher test exit 0.

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

- [x] Every campaign requirement maps to one task.
- [x] All script interfaces have one owner.
- [x] Test names match implementation names.
- [x] Runtime arms match the campaign matrix.
- [x] oMLX state stays inside the campaign log directory.
- [x] SpecPrefill compares M and N only against L at the same context.
- [x] ANE compares O only against J at the same context.
- [x] mlx-dspark compares R and S only against Q with the same target revision.
- [x] Draft caps are calibrated on the M4 Max instead of copied from public results.
- [x] Performance selection uses four fixed content classes and warm-loop time.
- [x] AWQ measurements use revision `dc699a76ddcbef44c188a8aee2ccc79ccc339a04`.
- [x] Sparse prefill verdicts do not use raw prompt TPS.
- [x] Tool schemas keep a fixed order.
- [x] The plan stores raw logs only under ignored paths.
- [x] The plan commits only distilled results.
- [x] Terminal-Bench runs only after cheap gates.
- [x] Final documentation links to local evidence.
