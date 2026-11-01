# Claude Code concurrency 2026-11 — campaign runbook

> **Para agentes:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recomendado) ou
> superpowers:executing-plans para executar este plano task a task. Os steps usam checkbox (`- [ ]`).
> As Tasks 6 a 8 rodam no rig e dependem da janela combinada com a sessão "Atualizações de stack preferidas"
> (ver Restrições globais). Pare só nos quatro casos da skill ou se o rig cair.

**Objetivo:** medir, com tarefas realistas de Claude Code, quanto a segunda sessão custa no Splash 1.5.0 e no
mlx-serve 26.10.3, se subagentes multiplicam esse custo, e se `--decode-share 1.0` ajuda o par real no Splash.

**Arquitetura:** o harness da [flashnext-concurrency-2026-10](../flashnext-concurrency-2026-10/plan.md) continua
em `bench/flashnext-concurrency-2026-10/scripts/` e ganha três peças: um proxy HTTP (`request_log.py`) que grava
um registro por request no mesmo esquema do `claude_requests.py`, duas tarefas novas (c, d) com repositórios de
exemplo, e flags novas no `run-claude-pair.sh` (`--pair`, `--subagents`, `--proxy`). Os braços `rc*` e `rm*`
entram no `run-candidate.sh` como os `kcc*`: um boot de servidor por rep e `--exec` para o par. O
`summarize_claude.py` escreve `claude-summary-splash.json` e `claude-summary-mlx.json` nesta pasta, e o
`collect()` do report os lê sem mudar de contrato; a única mudança no report é ler as chaves novas
`subagents` e `decode_share`.

**Tech stack:** bash 3.2 (rig), Python 3.9 stdlib (rig: `python3 -m py_compile` em cada script novo), pytest via
`uv run --no-project --with pytest`, Claude Code 2.1.292 (`/opt/homebrew/bin/claude` no rig).

**Spec:** [docs/superpowers/specs/2026-10-30-coding-concurrency-report-design.md](../../docs/superpowers/specs/2026-10-30-coding-concurrency-report-design.md),
seção "Entrega B". A spec manda; este plano argumenta a partir dela.

## Restrições globais

- **Servidores e pesos fixos.** Splash 1.5.0 em `~/.local/opt/qwen38/splash-v1.5.0/bin/splash` com
  `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS` `0142554c963a8653912c0c8283f05f13f63653f3` (flags do `k2c1`).
  mlx-serve 26.10.3 em `~/.local/opt/qwen38/mlx-serve-v26.10.3/mlx-serve` com Dankpaws Swift 1.5 MLX 4.7bpw
  `13839b7191e0973ff9fea58232267c395b76c6c0` (flags do `w1zc1`, o build do driver diário). Não alterar
  `splash-v1.4.0` nem `splash-v1.4.1`.
- **Contexto.** Os dois servidores sobem com `--max-context 131072`, como o `k2c1` dos `kcc*` de 29/10. Escolha
  minha: o driver diário roda a 262144, mas o custo do turno quente quase não muda com o teto (7.9 s a 32K,
  8.6 s a 128K) e a 131072 os pares a+b ficam comparáveis aos `kcc*` já publicados.
- **Claude Code.** `claude -p`, `CLAUDE_CODE_EFFORT_LEVEL=xhigh`, o mesmo modelo como principal e rápido,
  `--permission-mode default`, `--setting-sources project`, `--strict-mcp-config`. Tarefas a, b: `--max-turns 40`.
  Tarefas c, d: `--max-turns 60`. Timeout 1800 s por sessão (`CLAUDE_PAIR_TIMEOUT`).
- **Reps.** Pares: 3 reps. Solo (`rc1`, `rm1`): cada tarefa 2 vezes. Tag dos arquivos: `<braço>r<rep>`
  (`cc-rc2r1-c.json`, `req-rc2sr3-d.jsonl`).
- **Métricas.** Sem gate de razão. O resultado é a posição nas faixas de experiência do report (resposta começa
  ≤ 2 s / 2–5 / > 5; geração ≥ 60 tok/s / 30–60 / < 30; primeiro prompt ≤ 30 s / 30–60 / > 60; chamada lateral
  p95 ≤ 5 s / 5–60 / > 60) mais o funcional: `task_done` em todas as sessões, zero erros HTTP, swap Δ ≤ 0.5 GB.
- **TTFT.** `ttft_s` = tempo até o primeiro `content_block_delta` com `text_delta` ou `thinking_delta`, não até o
  primeiro byte (`message_start` sai antes do prefill). Mesma definição do `TTFT` do log do Splash.
- **Esquema por request** (o do `claude_requests.py`, sem mudança): `{"t_start_s", "ttft_s", "t_end_s",
  "input_tokens", "cached_tokens", "output_tokens", "tps", "status", "stream"}`. `t_start_s` e `t_end_s` são
  relativos a um `t0` comum às sessões da mesma rep.
- **Rig.** Um modelo por vez. A fila para o driver diário da 11234 e o religa no fim (`logs/chain.sh`, não
  rastreado). **Antes de parar a 11234, avisar a sessão "Atualizações de stack preferidas"**
  (`local_c66a0c2c-2e01-4be6-9205-af8c5824a877`). Janela combinada: depois do Terminal-Bench do `k3f` e antes do
  `t5r`; aquela sessão avisa quando 11234 e 8585 ficarem livres. O waiter `wait-t5r.sh` dela fica vivo. Checkout no
  rig: o worktree `~/LocalProjects/macstudio-local-llm-splashconc`, na branch desta campanha; o checkout principal
  do rig não muda.
- **Idioma e commits.** Prosa deste plano e dos `results/*.md` em pt-BR; código, nomes de arquivo e commits em
  inglês. Commits `bench(claude-code-concurrency): ...` terminando com
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Push e PR só na Task 10.
- **Testes.** Cada pasta de testes roda em separado (cada uma tem seu `conftest.py`):
  `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests -q`,
  idem `bench/claude-code-concurrency-2026-11/tests` e `bench/splash-concurrency-2026-10/tests`.
- **Arquivos rastreados.** `results/` rastreado (JSON, JSONL de requests, `*.md`); `logs/` ignorado
  (saídas `*.out.json`, `*.err.log`, logs de servidor, filas).

## Review Focus

1. **O mlx-serve não informa `cache_read_input_tokens` no `message_start`.** O proxy grava `cached_tokens: null`
   e o `summarize_requests` classifica o request como prefill quando `ttft_s > 5.0`. Teste na Task 2.
2. **Resposta sem `content_block_delta` (erro HTTP, `max_tokens` 0, stream abortado pelo cliente).** O proxy
   grava o registro com `ttft_s: null`, `status` real e `output_tokens: 0`; o `summarize_requests` ignora
   `ttft_s` nulo e conta `status != 200` em `errors`. Teste na Task 1.
3. **Os dois `Agent` da variante `--subagents` saem em série, não em paralelo.** O `run-claude-pair.sh` conta as
   mensagens do assistente com ≥ 2 `tool_use` chamados `Agent` (`parallel_agent_calls`) e o `max_concurrent` do
   proxy mede o N real. O report escreve o N medido; nunca "quatro". Teste na Task 4; checagem no rig na Task 6.
4. **Tarefa c ou d fora da faixa (menos de 20 turnos ou mais de 120K de contexto, timeout).** A Task 6 calibra com
   uma rep solo no Splash antes das filas; a tarefa só entra nas filas dentro da faixa. Uma sessão com timeout vira
   erro (`_failed`), não tempo.
5. **O par c+d fica com a primeira rep no mesmo prefix cache da rep anterior.** Cada rep sobe o servidor de novo
   (um `run-candidate.sh` por rep), como nos `kcc*`; o primeiro prompt de cada sessão é frio. O `prefill_turns`
   do resumo confirma (≥ 1 por sessão). Teste na Task 5 (`--print`).

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `bench/claude-code-concurrency-2026-11/plan.md` | Create | este runbook |
| `bench/claude-code-concurrency-2026-11/scripts/run-arm.sh` | Create | `run-candidate.sh` com `FLASHNEXT_RESULTS_DIR`/`FLASHNEXT_LOGS_DIR` desta campanha |
| `bench/claude-code-concurrency-2026-11/tests/conftest.py`, `test_arms.py` | Create | `--print` dos braços `rc*`, `rm*` |
| `bench/claude-code-concurrency-2026-11/results/` | Create | `cc-*.json`, `req-*.jsonl`, `claude-summary-splash.json`, `claude-summary-mlx.json`, `summary.md` |
| `bench/flashnext-concurrency-2026-10/scripts/request_log.py` | Create | proxy HTTP que grava um registro por request |
| `bench/flashnext-concurrency-2026-10/scripts/claude_requests.py` | Modify | `cached_tokens` nulo e `ttft_s` nulo no `summarize_requests` |
| `bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py` | Modify | `--variants`; chaves `subagents` e `decode_share` |
| `bench/flashnext-concurrency-2026-10/scripts/claude-tasks/task-c.md`, `repo-c/`, `check-c.sh`, `solutions/c.patch` | Create | tarefa c (pacote Python) |
| `bench/flashnext-concurrency-2026-10/scripts/claude-tasks/task-d.md`, `repo-d/`, `check-d.sh`, `solutions/d.patch` | Create | tarefa d (scripts shell) |
| `bench/flashnext-concurrency-2026-10/scripts/claude-tasks/subagents-preamble.md` | Create | parágrafo da variante `--subagents` |
| `bench/flashnext-concurrency-2026-10/scripts/run-claude-pair.sh` | Modify | `--pair`, `--task c\|d`, `--subagents`, `--proxy`, `--max-turns`, stream-json, `check-*.sh` |
| `bench/flashnext-concurrency-2026-10/tests/test_request_log.py`, `test_tasks.py` | Create | proxy; checagens das tarefas c, d |
| `bench/flashnext-concurrency-2026-10/tests/test_claude_requests.py`, `test_summarize_claude.py`, `test_claude_pair.py` | Modify | regras novas |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify | braços `rc1\|rc2\|rc2s\|rc2d\|rm1\|rm2\|rm2s` |
| `bench/flashnext-concurrency-2026-10/scripts/render_report.py`, `report_sections.py` | Modify | `subagents` e `decode_share` do par real nas seções 3 e 4 e na matriz |
| `bench/flashnext-concurrency-2026-10/tests/test_render_report.py` | Modify | payload com campanha B |
| `reports/qwen38-flashnext-concurrency.html`, `reports/index.html`, `reports/README.md`, `docs/models/qwen3.8-flash-next.md` | Regenerate / Modify | números da campanha B |

## Braços

| braço | sessões | servidor | tarefas | subagentes | flag extra | rig |
|---|---:|---|---|---|---|---:|
| `rc1` | 1 | Splash 1.5.0 | a, b, c, d, cada uma 2× | não | — | ~1.5 h |
| `rc2` | 2 | Splash 1.5.0 | par a+b (3×) e par c+d (3×) | não | — | ~1.5 h |
| `rc2s` | 2 | Splash 1.5.0 | par c+d (3×) | 2 Explore em paralelo por sessão | — | ~1 h |
| `rc2d` | 2 | Splash 1.5.0 | par c+d (3×) | não | `--decode-share 1.0` | ~1 h |
| `rm1` | 1 | mlx-serve 26.10.3 | a, b, c, d, cada uma 2× | não | — | ~2.5 h |
| `rm2` | 2 | mlx-serve 26.10.3 | par a+b (3×) e par c+d (3×) | não | — | ~2.5 h |
| `rm2s` | 2 | mlx-serve 26.10.3 | par c+d (3×) | 2 Explore em paralelo por sessão | — | ~1.5 h |

Estimativa total ~12–14 h de rig, com boots (um por rep) e 120 s entre reps. O mlx-serve leva ~1.8× o tempo
do Splash por tarefa (campanha de 18/10 × 29/10).

## Modelo de resultados

`claude-summary-<server>.json` = saída do `summarize_claude.py --prefix rc|rm --variants s=subagents,d=decode_share`:

```json
{"prefix": "rc",
 "profiles": {"small": {...}, "realistic": {...}},
 "requests": {"alone": {...}, "pair": {...}},
 "subagents": {"profile": {...como um profile, só pair_s/pair_wall_s/time_saved...}, "requests": {...},
               "parallel_agent_calls": 6, "subagents_spawned": 12},
 "decode_share": {"profile": {...}, "requests": {...}}}
```

`profiles`, `requests` são os de hoje (os `kcc*` de 29/10 têm só `small`). `subagents` vem dos arquivos
`rc2s*`; `decode_share` dos `rc2d*`; `serial_sum_s` dos dois usa o `rc1` realista. No `rm` não há
`decode_share`. `results/summary.md` tem a tabela por braço, tarefa e rep, e termina com `## Veredito` e
`## Leitura`.

---

### Task 1: Proxy `request_log.py`

**Files:**
- Create: `bench/flashnext-concurrency-2026-10/scripts/request_log.py`
- Test: `bench/flashnext-concurrency-2026-10/tests/test_request_log.py`

**Interfaces:**
- Produces: CLI `python3 request_log.py --listen PORT --upstream http://HOST:PORT --out FILE.jsonl --stream LABEL
  --t0 EPOCH`. Função pura `parse_sse(events: list[tuple[str, dict]], t_start: float, times: list[float]) -> dict`
  que recebe `(event_name, data)` com o instante de cada evento e devolve o registro do esquema. Uma linha JSON por
  request no `--out`, `t_start_s = t_start - t0`.

- [ ] **Step 1: Teste do parser de SSE**

```python
# tests/test_request_log.py
import json, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import request_log as RL

EVENTS = [("message_start", {"type": "message_start", "message": {"usage": {"input_tokens": 19297, "cache_read_input_tokens": 16032}}}),
          ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking"}}),
          ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "x"}}),
          ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "y"}}),
          ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 110}}),
          ("message_stop", {"type": "message_stop"})]

def test_parse_sse_ttft_is_first_content_delta_not_message_start():
    times = [100.1, 100.2, 123.7, 123.8, 125.0, 125.0]
    rec = RL.parse_sse(EVENTS, t_start=100.0, times=times, t0=90.0, stream="c", status=200)
    assert rec["t_start_s"] == 10.0 and rec["ttft_s"] == 23.7 and rec["t_end_s"] == 35.0
    assert rec["input_tokens"] == 19297 and rec["cached_tokens"] == 16032 and rec["output_tokens"] == 110
    assert abs(rec["tps"] - 110 / (125.0 - 123.7)) < 0.01 and rec["status"] == 200 and rec["stream"] == "c"

def test_parse_sse_without_cache_field_writes_null_cached():
    ev = [("message_start", {"type": "message_start", "message": {"usage": {"input_tokens": 500}}})] + EVENTS[1:]
    rec = RL.parse_sse(ev, 0.0, [0.0, 0.1, 1.0, 1.1, 2.0, 2.0], t0=0.0, stream="c", status=200)
    assert rec["cached_tokens"] is None

def test_parse_sse_without_content_delta_has_null_ttft():
    ev = [EVENTS[0], EVENTS[4], EVENTS[5]]
    rec = RL.parse_sse(ev, 0.0, [0.0, 1.0, 1.0], t0=0.0, stream="c", status=529)
    assert rec["ttft_s"] is None and rec["tps"] is None and rec["status"] == 529 and rec["output_tokens"] == 110
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests/test_request_log.py -q`
Expected: FAIL com `ModuleNotFoundError: request_log`

- [ ] **Step 3: Implementar `parse_sse(events, t_start, times, t0, stream, status) -> dict` em `request_log.py`**

`ttft_s = times[i] - t_start` do primeiro `content_block_delta` cujo `delta.type` é `text_delta` ou
`thinking_delta`; `t_end_s = times[-1] - t0`; `tps = output_tokens / (times[-1] - times[i])` quando o
denominador > 0, senão `None`; `input_tokens` de `message_start.message.usage.input_tokens`; `cached_tokens` de
`cache_read_input_tokens` quando presente, senão `None`; `output_tokens` do último `message_delta.usage`, senão 0.
Arredondar `ttft_s`, `t_start_s`, `t_end_s` a 3 casas e `tps` a 1.

- [ ] **Step 4: Rodar e ver passar**

Run: o mesmo comando. Expected: 3 passed.

- [ ] **Step 5: Teste de ponta a ponta do proxy com um upstream falso**

```python
class FakeUpstream(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
        for name, data in EVENTS:
            self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode()); self.wfile.flush()
            time.sleep(0.05)
    def log_message(self, *a): pass

def test_proxy_forwards_stream_and_writes_one_record(tmp_path):
    up = ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream); threading.Thread(target=up.serve_forever, daemon=True).start()
    out = tmp_path / "req.jsonl"
    px = RL.make_server("127.0.0.1", 0, f"http://127.0.0.1:{up.server_port}", out, stream="d", t0=time.time())
    threading.Thread(target=px.serve_forever, daemon=True).start()
    req = urllib.request.Request(f"http://127.0.0.1:{px.server_port}/v1/messages", data=b'{"stream":true}',
                                 headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01"})
    body = urllib.request.urlopen(req).read().decode()
    assert "event: message_stop" in body  # the client gets the whole stream, unchanged
    px.shutdown(); up.shutdown()
    recs = [json.loads(l) for l in out.read_text().splitlines()]
    assert len(recs) == 1 and recs[0]["stream"] == "d" and recs[0]["input_tokens"] == 19297
    assert 0.05 < recs[0]["ttft_s"] < 1.0 and recs[0]["status"] == 200
```

- [ ] **Step 6: Rodar e ver falhar**

Expected: FAIL com `AttributeError: module 'request_log' has no attribute 'make_server'`

- [ ] **Step 7: Implementar `make_server(host, port, upstream, out, stream, t0) -> ThreadingHTTPServer` e `main(argv)`**

`ThreadingHTTPServer` + handler que repassa método, caminho, query, cabeçalhos (menos `Host`, `Content-Length`
recalculado) e corpo via `http.client.HTTPConnection`, copia status e cabeçalhos da resposta, e lê o corpo em
blocos: cada bloco vai ao cliente na hora (`wfile.write` + `flush`) e ao parser de SSE (acumula linhas, separa
eventos por linha vazia, marca `time.time()` por evento). `Content-Type` sem `text/event-stream`: repassa o corpo
inteiro e grava um registro com `ttft_s: null`, tokens do JSON da resposta se houver `usage`. Escrita no `--out`
protegida por `threading.Lock`, `open(..., "a")` por registro. `main` lê `--listen`, `--upstream`, `--out`,
`--stream`, `--t0` (default `time.time()`) e chama `serve_forever()`. Só stdlib; sem f-strings aninhadas com a
mesma aspa.

- [ ] **Step 8: Rodar e ver passar; compilar para 3.9**

Run: o mesmo comando; depois `python3 -m py_compile bench/flashnext-concurrency-2026-10/scripts/request_log.py`
Expected: 4 passed; compile sem saída.

- [ ] **Step 9: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/scripts/request_log.py bench/flashnext-concurrency-2026-10/tests/test_request_log.py
git commit -m "bench(claude-code-concurrency): request_log.py proxy records one line per request"
```

### Task 2: `summarize_requests` com `cached_tokens` e `ttft_s` nulos; `summarize_claude --variants`

**Files:**
- Modify: `bench/flashnext-concurrency-2026-10/scripts/claude_requests.py:94-111`
- Modify: `bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py`
- Test: `bench/flashnext-concurrency-2026-10/tests/test_claude_requests.py`, `tests/test_summarize_claude.py`

**Interfaces:**
- Consumes: registros da Task 1 (`cached_tokens` pode ser `None`; `ttft_s` pode ser `None`; `status` ≠ 200).
- Produces: `summarize_requests` ganha a chave `"errors"` (requests com `status != 200`).
  `summarize_claude(results_dir, prefix, variants: dict[str, str] | None = None)`; `_rep(name, prefix, kind,
  variant="")` casa `^(?:cc|req)-{prefix}{kind}{variant}r(\d+)(?:-[^.]+)?\.jsonl?$`. Saída ganha, por variante,
  `{"profile": {"tasks", "pair_s", "pair_wall_s", "serial_sum_s", "time_saved", "turns", "task_done", "errors"},
  "requests": {...}, "parallel_agent_calls": int, "subagents_spawned": int}` sob a chave do nome da variante.

- [ ] **Step 1: Testes do `summarize_requests`**

```python
def test_null_cached_counts_as_prefill_only_when_ttft_is_long():
    reqs = [dict(WARM, t_start_s=0.0, ttft_s=12.0, t_end_s=15.0, cached_tokens=None),
            dict(WARM, t_start_s=20.0, ttft_s=1.5, t_end_s=22.0, cached_tokens=None)]
    s = CR.summarize_requests(reqs)
    assert s["prefill_turns"] == 1 and s["warm"]["n"] == 1 and s["warm"]["ttft_p50"] == 1.5

def test_null_ttft_and_non_200_are_errors_not_samples():
    reqs = [dict(WARM, t_start_s=0.0, ttft_s=None, tps=None, t_end_s=1.0, status=529),
            dict(WARM, t_start_s=5.0, ttft_s=1.0, t_end_s=7.0)]
    s = CR.summarize_requests(reqs)
    assert s["errors"] == 1 and s["warm"]["n"] == 1 and s["n"] == 2
```

(`WARM` = o registro quente que o arquivo já usa como base, com `cached_tokens` 19264; os testes constroem
registros com `dict(WARM, ...)`, como os existentes.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests/test_claude_requests.py -q`
Expected: FAIL (`TypeError` na comparação com `None`, e `KeyError: 'errors'`)

- [ ] **Step 3: Implementar.** `prefill(r)`: `cached is None → ttft_s is not None and ttft_s > PREFILL_TTFT_S (5.0)`;
  senão a regra atual. Amostras com `ttft_s` nulo saem de `warm` e de `cold`; `"errors": sum(status != 200)`.

- [ ] **Step 4: Rodar e ver passar.** Expected: todos os testes do arquivo passam (8 + 2).

- [ ] **Step 5: Testes do `summarize_claude` com variantes**

```python
def test_variant_files_are_not_counted_in_the_main_pair(tmp_path):
    _cc(tmp_path, "rc2r1-c", 300, "c", 25); _cc(tmp_path, "rc2r1-d", 280, "d", 22)
    _cc(tmp_path, "rc2sr1-c", 400, "c", 25); _cc(tmp_path, "rc2sr1-d", 390, "d", 22)
    s = summarize_claude(tmp_path, "rc")
    assert s["profiles"]["realistic"]["pair_wall_s"] == 300 and "subagents" not in s

def test_variants_get_their_own_key_with_serial_from_the_main_alone(tmp_path):
    _cc(tmp_path, "rc1r1-c", 200, "c", 25); _cc(tmp_path, "rc1r1-d", 200, "d", 22)
    _cc(tmp_path, "rc2sr1-c", 300, "c", 25, parallel_agent_calls=3, subagents_spawned=6)
    _cc(tmp_path, "rc2sr1-d", 380, "d", 22, parallel_agent_calls=3, subagents_spawned=6)
    _req(tmp_path, "rc2sr1-c", [COLD, WARM, WARM, WARM]); _req(tmp_path, "rc2sr1-d", [COLD, WARM, WARM, WARM])
    s = summarize_claude(tmp_path, "rc", variants={"s": "subagents", "d": "decode_share"})
    sub = s["subagents"]
    assert sub["profile"]["pair_wall_s"] == 380 and sub["profile"]["serial_sum_s"] == 400
    assert abs(sub["profile"]["time_saved"] - (1 - 380 / 400)) < 1e-9
    assert sub["parallel_agent_calls"] == 6 and sub["subagents_spawned"] == 12 and sub["requests"]["n"] == 8
    assert "decode_share" not in s  # no rc2d files in this dir

def test_rep_regex_with_variant_letter():
    from summarize_claude import _rep
    assert _rep("cc-rc2sr3-c.json", "rc", "2", "s") == "3" and _rep("cc-rc2sr3-c.json", "rc", "2") is None
```

(`_cc(results, name, wall, task, turns, **extra)`: o helper existente ganha `**extra`, gravado no JSON.)

- [ ] **Step 6: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests/test_summarize_claude.py -q`
Expected: FAIL (`TypeError: unexpected keyword 'variants'`; `_rep` sem o 4º argumento)

- [ ] **Step 7: Implementar.** `_rep(..., variant="")`; `_reps(results_dir, kind, task)` e `_requests(...)` recebem
  `variant` e usam glob `cc-{prefix}2{variant}r*-{task}.json`; o profile principal exclui nomes que `_rep` com
  `variant=""` não casa. `_variant(results_dir, prefix, variant, tasks=("c", "d"))` reaproveita a lógica de par de
  `_profile` (extrair `_pair_walls(...)`), soma `parallel_agent_calls` e `subagents_spawned` dos `cc-*.json`
  (default 0), `serial_sum_s` do `rc1` realista. CLI: `--variants s=subagents,d=decode_share`.

- [ ] **Step 8: Rodar e ver passar; compilar 3.9.** Expected: 7 + 3 passed; `py_compile` limpo nos dois scripts.

- [ ] **Step 9: Regerar os resumos de 29/10 e conferir que não mudaram**

Run: `python3 bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py --results-dir bench/splash-concurrency-2026-10/results --prefix kcc --out /tmp/kcc.json && diff /tmp/kcc.json bench/splash-concurrency-2026-10/results/claude-summary.json`
Expected: só a chave nova `"errors": 0` dentro de `requests.alone` e `requests.pair`; nada mais. Se igual, copiar
por cima e incluir no commit.

- [ ] **Step 10: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/scripts/claude_requests.py bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py bench/flashnext-concurrency-2026-10/tests/test_claude_requests.py bench/flashnext-concurrency-2026-10/tests/test_summarize_claude.py bench/splash-concurrency-2026-10/results/claude-summary.json
git commit -m "bench(claude-code-concurrency): summarize variants (subagents, decode-share) and proxy records"
```

### Task 3: Tarefas c e d

**Files:**
- Create: `bench/flashnext-concurrency-2026-10/scripts/claude-tasks/task-c.md`, `repo-c/`, `check-c.sh`,
  `solutions/c.patch`
- Create: `.../claude-tasks/task-d.md`, `repo-d/`, `check-d.sh`, `solutions/d.patch`
- Create: `.../claude-tasks/subagents-preamble.md`
- Test: `bench/flashnext-concurrency-2026-10/tests/test_tasks.py`

**Interfaces:**
- Produces: `check-c.sh REPO` e `check-d.sh REPO` imprimem `true`/`false` (mesmo contrato do `task_done` do
  `run-claude-pair.sh`); `solutions/<t>.patch` aplica em `repo-<t>` com `git apply`.

Conteúdo (escolha do builder dentro dos requisitos da spec: 20–40 turnos, 60–120K de contexto numa sessão só,
≥ 5 arquivos lidos, ≥ 2 deles com > 5K tokens, resultado checável):

- **repo-c** (~1.5K linhas de Python 3.9, stdlib): pacote `ledger` — `models.py` (dataclasses), `parse.py`
  (CSV e JSON), `rules.py` (≥ 450 linhas: tabela de regras de categoria, uma por linha), `store.py`, `report.py`,
  `cli.py` (`argparse`, subcomandos `import`, `report`), `tests/` (unittest, ≥ 25 testes passando),
  `fixtures/transactions.csv` (≥ 600 linhas). `README.md` com a sintaxe do CLI. Tarefa c: adicionar ao
  `report` a opção `--group-by month|category|account` com totais por grupo, saída `text` e `json`, mais ≥ 3
  testes novos, sem quebrar os existentes; o README documenta a opção.
  `check-c.sh`: suite passa e `python3 -m ledger.cli report --group-by month --format json fixtures/transactions.csv`
  devolve um objeto com ≥ 12 chaves `YYYY-MM` cujos totais somam o total geral (± 0.01); `grep -c group-by README.md ≥ 1`.
- **repo-d** (~1.2K linhas de bash 3.2): toolkit `backup/` — `backup.sh`, `rotate.sh`, `verify.sh`,
  `restore.sh`, `report.sh`, `lib/log.sh`, `tests/run_tests.sh` (`check` por caso, ≥ 6 casos passando) e
  `docs/USAGE.md` (> 5K tokens: descrição de cada script e flag). Três bugs plantados: (1) `rotate.sh` apaga o
  backup mais novo quando há exatamente `KEEP` arquivos; (2) `verify.sh` compara checksums com `==` em `[ ]` e
  quebra com nomes com espaço; (3) `report.sh` ordena tamanhos como texto. Refactor: os cinco scripts repetem as
  mesmas 40 linhas de parse de flags e de resolução de diretório; mover para `lib/common.sh`.
  Tarefa d: corrigir os três bugs, um teste por bug em `tests/run_tests.sh`, e o refactor para `lib/common.sh`.
  `check-d.sh`: `tests/run_tests.sh` passa com ≥ 9 `check`; `grep -l 'source.*lib/common.sh'` em ≥ 4 scripts;
  um caso de cada bug reproduzido pelo checker em um tmpdir (como o `task_done` de b).
- **subagents-preamble.md** (anteposto ao prompt quando `--subagents`): "Before you edit anything, map the
  repository with two Explore subagents running in parallel: call the `Agent` tool twice in the same message, one
  to list every file the change touches and its callers, one to list the tests and fixtures that exercise that
  code. Wait for both, then proceed." Texto fixo; `test_claude_pair.py` confere que ele entra no prompt.

- [ ] **Step 1: Testes das checagens**

```python
# tests/test_tasks.py
import subprocess, shutil
from conftest import SCRIPTS, run
TASKS = SCRIPTS / "claude-tasks"

def _copy(tmp_path, t):
    repo = tmp_path / f"repo-{t}"; shutil.copytree(TASKS / f"repo-{t}", repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True); return repo

def test_check_c_is_false_on_the_base_repo_and_true_after_the_solution(tmp_path):
    repo = _copy(tmp_path, "c")
    assert run("bash", TASKS / "check-c.sh", repo).stdout.strip() == "false"
    subprocess.run(["git", "apply", str(TASKS / "solutions/c.patch")], cwd=repo, check=True)
    assert run("bash", TASKS / "check-c.sh", repo).stdout.strip() == "true"

def test_check_d_is_false_on_the_base_repo_and_true_after_the_solution(tmp_path):
    repo = _copy(tmp_path, "d")
    assert run("bash", TASKS / "check-d.sh", repo).stdout.strip() == "false"
    subprocess.run(["git", "apply", str(TASKS / "solutions/d.patch")], cwd=repo, check=True)
    assert run("bash", TASKS / "check-d.sh", repo).stdout.strip() == "true"

def test_base_repos_pass_their_own_suites():
    assert subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=TASKS / "repo-c").returncode == 0
    assert subprocess.run(["bash", "tests/run_tests.sh"], cwd=TASKS / "repo-d").returncode == 0

def test_repos_meet_the_size_floor():
    big = [p for p in (TASKS / "repo-c").rglob("*") if p.is_file() and p.stat().st_size > 20_000]
    assert len(big) >= 2  # ~5K tokens each
    big = [p for p in (TASKS / "repo-d").rglob("*") if p.is_file() and p.stat().st_size > 20_000]
    assert len(big) >= 2
    assert sum(1 for _ in (TASKS / "repo-c").rglob("*.py")) >= 6 and sum(1 for _ in (TASKS / "repo-d").rglob("*.sh")) >= 6
```

- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL (`repo-c` não existe).
- [ ] **Step 3: Escrever `repo-c`, `task-c.md`, `check-c.sh`, `solutions/c.patch`** (o patch = a solução de
  referência, gerada com `git diff` numa cópia; a solução não entra em `repo-c`).
- [ ] **Step 4: Rodar; os dois testes de c passam.**
- [ ] **Step 5: Escrever `repo-d`, `task-d.md`, `check-d.sh`, `solutions/d.patch`.**
- [ ] **Step 6: Rodar e ver passar os 4 testes.** `bash -n` em cada `.sh` (sintaxe bash 3.2: sem `declare -A`,
  sem `${var,,}`, sem `mapfile`).
- [ ] **Step 7: Escrever `subagents-preamble.md`.**
- [ ] **Step 8: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/scripts/claude-tasks bench/flashnext-concurrency-2026-10/tests/test_tasks.py
git commit -m "bench(claude-code-concurrency): tasks c (ledger package) and d (backup toolkit) with checkers"
```

### Task 4: `run-claude-pair.sh` — `--pair`, `--task c|d`, `--subagents`, `--proxy`, `--max-turns`

**Files:**
- Modify: `bench/flashnext-concurrency-2026-10/scripts/run-claude-pair.sh`
- Test: `bench/flashnext-concurrency-2026-10/tests/test_claude_pair.py`

**Interfaces:**
- Consumes: `request_log.py` (Task 1), `check-c.sh`/`check-d.sh` e `subagents-preamble.md` (Task 3).
- Produces: `run-claude-pair.sh --sessions 1|2 --tag TAG [--task a|b|c|d] [--pair a,b|c,d] [--subagents]
  [--proxy BASEPORT] [--max-turns N] [--out DIR] [--dry-run]`. Arquivos: `cc-<tag>-<task>.json` com os campos
  de hoje mais `parallel_agent_calls`, `subagents_spawned`, `subagents` (bool); `req-<tag>-<task>.jsonl` quando
  `--proxy`. Defaults: `--pair a,b`; `--max-turns` 40 para a, b e 60 para c, d.

- [ ] **Step 1: Testes (dry-run)**

```python
def test_pair_cd_with_subagents_and_proxy_dry_run():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "2", "--pair", "c,d",
              "--subagents", "--proxy", "8686", "--tag", "rc2sr1").stdout
    assert out.count("claude -p") == 2 and "task-c.md" in out and "task-d.md" in out and "task-a.md" not in out
    assert "subagents-preamble.md" in out and " Agent " in out and "--max-turns 60" in out
    assert "request_log.py --listen 8686 " in out and "--listen 8687 " in out
    assert "--upstream http://127.0.0.1:11234 " in out and "--stream rc2sr1-c" in out and "--out" in out
    assert "ANTHROPIC_BASE_URL=http://127.0.0.1:8686" in out and "ANTHROPIC_BASE_URL=http://127.0.0.1:8687" in out
    assert "--output-format stream-json --verbose" in out

def test_single_task_c_without_subagents_keeps_agent_out():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "1", "--task", "c", "--tag", "rc1r1").stdout
    assert out.count("claude -p") == 1 and " Agent " not in out and "--max-turns 60" in out and "request_log" not in out

def test_default_pair_is_ab_with_40_turns():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "2", "--tag", "x").stdout
    assert "task-a.md" in out and "task-b.md" in out and "--max-turns 40" in out
```

- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL com `unknown option: --pair` (exit 64).
- [ ] **Step 3: Implementar as flags.** `--pair` substitui `RUN_TASKS` quando `--sessions 2`; `--task` aceita
  a|b|c|d; `--subagents` adiciona `Agent` ao `--allowedTools` e concatena `subagents-preamble.md` + `task-<t>.md`
  no prompt; `--proxy P` sobe `python3 request_log.py --listen $((P+i)) --upstream $ANTHROPIC_URL --out
  $OUT/req-$TAG-$t.jsonl --stream $TAG-$t --t0 $T0` por sessão (mesmo `T0` para as duas), aponta
  `ANTHROPIC_BASE_URL` para o proxy e mata o proxy no fim da sessão; `--output-format stream-json --verbose` em
  todos os braços (o último `type: result` continua sendo a última linha). `task_done` chama `check-c.sh`/
  `check-d.sh` para c, d. O Python do fim conta `parallel_agent_calls` (mensagens `assistant` com ≥ 2 blocos
  `tool_use` de `name == "Agent"`) e lê `subagent_stats.spawned` → `subagents_spawned`.
- [ ] **Step 4: Rodar e ver passar os 3 testes novos e os 4 antigos.**
- [ ] **Step 5: Teste com `claude` falso em stream-json**

```python
def test_stream_json_counts_parallel_agent_calls(tmp_path):
    fake = tmp_path / "claude"
    fake.write_text('#!/bin/bash\necho \'{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Agent","id":"1"},{"type":"tool_use","name":"Agent","id":"2"}]}}\'\n'
                    'echo \'{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","id":"3"}]}}\'\n'
                    'echo \'{"type":"result","is_error":false,"num_turns":4,"subagent_stats":{"spawned":2}}\'\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    out = tmp_path / "results"
    env = clean_env({"CLAUDE_BIN": str(fake), "CLAUDE_PAIR_WORK": str(tmp_path / "work"), "MODEL_ID": "m", "BASE_URL": "http://127.0.0.1:1/v1"})
    run("bash", SCRIPTS / "run-claude-pair.sh", "--sessions", "1", "--task", "c", "--subagents", "--tag", "t", "--out", out, env=env, check=False)
    c = json.loads((out / "cc-t-c.json").read_text())
    assert c["parallel_agent_calls"] == 1 and c["subagents_spawned"] == 2 and c["subagents"] is True and c["num_turns"] == 4
```

- [ ] **Step 6: Rodar e ver falhar, implementar o que faltar, ver passar.** Expected: 8 passed no arquivo.
- [ ] **Step 7: Teste do proxy dentro do par** — reutilizar `FakeUpstream` de `test_request_log.py`: `BASE_URL`
  aponta para o upstream falso, `--proxy 0` não serve (porta fixa): usar `--proxy 18686`; o `claude` falso faz um
  `curl -s -X POST $ANTHROPIC_BASE_URL/v1/messages -d '{}'` antes de imprimir o `result`. Asserts:
  `req-t-c.jsonl` tem 1 linha com `stream == "t-c"` e `status == 200`. Rodar, ver falhar (se falhar: corrigir a
  ordem de subida do proxy), ver passar.
- [ ] **Step 8: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/scripts/run-claude-pair.sh bench/flashnext-concurrency-2026-10/tests/test_claude_pair.py
git commit -m "bench(claude-code-concurrency): run-claude-pair --pair, --subagents, --proxy, --max-turns"
```

### Task 5: Braços `rc*` e `rm*` no `run-candidate.sh`

**Files:**
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` (lista de candidatos no
  `uso`, bloco novo depois do bloco `k2c*`)
- Create: `bench/claude-code-concurrency-2026-11/scripts/run-arm.sh` (cópia do `run-arm.sh` da
  splash-concurrency com `HERE` desta campanha)
- Create: `bench/claude-code-concurrency-2026-11/tests/conftest.py` (cópia do da splash-concurrency),
  `tests/test_arms.py`

**Interfaces:**
- Consumes: `run-claude-pair.sh` da Task 4.
- Produces: `run-arm.sh <rc1|rc2|rc2s|rc2d|rm1|rm2|rm2s> 131072 --tag r<rep>`; env `FLASHNEXT_CC_TASK=a|b|c|d`
  (só `rc1`, `rm1`) e `FLASHNEXT_CC_PAIR=a,b|c,d` (só `rc2`, `rm2`; default `c,d`). O `ARM_EXEC` chama
  `run-claude-pair.sh --out $RESULTS --proxy 8686 --tag ${CAND}${TAG}` com `--sessions`, `--task`/`--pair`,
  `--subagents` conforme o braço. `CLAUDE_BIN` vem do ambiente da fila.

- [ ] **Step 1: Testes `--print`**

```python
from conftest import run_candidate_print

def test_rc1_is_k2c1_server_with_one_claude_session():
    out = run_candidate_print("rc1", "131072", env_extra={"FLASHNEXT_CC_TASK": "c"})
    assert "splash-v1.5.0/bin/splash serve" in out and "--port 8585" in out and "--max-context 131072" in out
    assert "--verify-rows auto" in out and "--decode-share" not in out
    assert "run-claude-pair.sh" in out and "--sessions 1 --task c" in out and "--proxy 8686" in out and "--tag rc1r1" in out

def test_rc2_pairs_cd_by_default_and_ab_on_request():
    assert "--sessions 2 --pair c,d" in run_candidate_print("rc2", "131072")
    assert "--pair a,b" in run_candidate_print("rc2", "131072", env_extra={"FLASHNEXT_CC_PAIR": "a,b"})

def test_rc2s_adds_subagents_and_rc2d_adds_decode_share():
    out = run_candidate_print("rc2s", "131072")
    assert "--pair c,d --subagents" in out and "--decode-share" not in out
    out = run_candidate_print("rc2d", "131072")
    assert "--decode-share 1.0" in out and "--subagents" not in out and "--pair c,d" in out

def test_rm_arms_run_on_mlx_serve_26103_without_max_concurrent():
    out = run_candidate_print("rm2", "131072")
    assert "mlx-serve-v26.10.3" in out and "--port 11234" in out and "--max-concurrent" not in out
    assert "13839b7191e0973ff9fea58232267c395b76c6c0" in out and "--sessions 2 --pair c,d" in out
    assert "--subagents" in run_candidate_print("rm2s", "131072")
    assert "--sessions 1 --task a" in run_candidate_print("rm1", "131072", env_extra={"FLASHNEXT_CC_TASK": "a"})
```

(`run_candidate_print` do conftest ganha `env_extra=None` → `clean_env(env_extra)`; `--tag r1` fixo no helper
desta campanha em vez de `e1`.)

- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL com `candidato desconhecido: rc1`.
- [ ] **Step 3: Implementar o bloco.** `rc*`: copiar o launcher/env do bloco `k2c*` (`SPLASH_150`, `--verify-rows
  auto`, `--idle-release off`, `--offline`), `rc2d` acrescenta `--decode-share 1.0` em `QWEN38_SPLASH_EXTRA_ARGS`
  e `REV="v1.5.0-verify-auto-ds1.0"`. `rm*`: copiar o launcher/env do `w1zc1` (26.10.3, sem
  `QWEN38_MLX_EXTRA_ARGS`; o mlx-serve 26.10.3 faz batch no default, como nos `cc*` de 18/10). `ARM_EXEC` conforme
  Interfaces. Nenhum `cache_probe` roda nesses braços.
- [ ] **Step 4: Rodar e ver passar.** Também: `bench/splash-concurrency-2026-10/tests` e
  `bench/flashnext-concurrency-2026-10/tests/test_arms.py` continuam verdes (o bloco novo não toca os outros).
- [ ] **Step 5: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh bench/claude-code-concurrency-2026-11/scripts/run-arm.sh bench/claude-code-concurrency-2026-11/tests
git commit -m "bench(claude-code-concurrency): arms rc1/rc2/rc2s/rc2d and rm1/rm2/rm2s"
```

### Task 6: Rig — janela, smoke e calibração das tarefas c e d

**Files:**
- Create (não rastreados, no worktree do rig): `logs/chain.sh`, `logs/q-smoke.sh`
- Create: `results/calibration.md`

- [ ] **Step 1: Avisar a sessão "Atualizações de stack preferidas"** que o runbook está pronto e perguntar
  quando 11234 e 8585 ficam livres (janela entre o `k3f` e o `t5r`). Não parar nada antes da resposta dela.
- [ ] **Step 2: Levar a branch ao worktree do rig** (`~/LocalProjects/macstudio-local-llm-splashconc`:
  `git fetch && git checkout bench/claude-code-concurrency-2026-11`). Conferir `python3 -m py_compile` de
  `request_log.py`, `claude_requests.py`, `summarize_claude.py` no rig e `claude --version` (2.1.292).
- [ ] **Step 3: Com a janela aberta, parar o driver da 11234 via `logs/chain.sh`** (o `chain.sh` da
  splash-concurrency, copiado; para o driver, roda os steps, religa o driver, escreve `CHAIN-<label>: done`).
- [ ] **Step 4: Smoke do proxy com um request real:** `run-arm.sh rc1 131072 --tag smoke` com
  `FLASHNEXT_CC_TASK=a`. Expected: `cc-rc1smoke-a.json` com `task_done: true`; `req-rc1smoke-a.jsonl` com ≥ 5
  linhas, `cached_tokens` numérico, o primeiro request com `ttft_s` entre 15 e 40 s e os demais < 3 s;
  `max_concurrent == 1`. Repetir com `rm1` (mlx-serve): conferir se `cached_tokens` vem numérico ou nulo e anotar
  no `calibration.md` (Review Focus 1).
- [ ] **Step 5: Calibrar c e d:** `rc1` com `FLASHNEXT_CC_TASK=c`, depois `d`, tag `cal1`. Ler `num_turns`,
  `usage.input_tokens + cache_read_input_tokens` do último turno (contexto final) e `wall_s`. Faixa: 20–40
  turnos, 60–120K, `task_done: true`, sem timeout. Fora da faixa: ajustar o prompt ou o tamanho do repositório
  (uma mudança por vez), commitar, repetir. No máximo 3 rodadas por tarefa; se não calibrar, registrar a faixa
  obtida e seguir.
- [ ] **Step 6: Smoke dos subagentes:** `rc2s` 1 rep, tag `cal1`. Expected: `parallel_agent_calls ≥ 1` nas duas
  sessões e `max_concurrent ≥ 3` no par (Review Focus 3). Se `parallel_agent_calls == 0`, ajustar o
  `subagents-preamble.md` (uma vez) e repetir.
- [ ] **Step 7: `results/calibration.md`** com a tabela (tarefa, turnos, contexto final, wall_s, task_done,
  `cached_tokens` por servidor, N real com subagentes) e as decisões. Mover os `cc-*smoke*`/`*cal1*` para
  `results/calibration/`. Commit:

```bash
git add bench/claude-code-concurrency-2026-11/results
git commit -m "bench(claude-code-concurrency): smoke and calibration of tasks c and d on the rig"
```

### Task 7: Rig — filas

- [ ] **Step 1: Fila Splash** (`logs/q-splash.sh`, dentro do `chain.sh`): `rc1` (a, b, c, d × 2 reps, tags
  `r1`, `r2`), `rc2` a,b × 3, `rc2` c,d × 3, `rc2s` × 3, `rc2d` × 3; 120 s entre reps; um boot por rep.
  `CLAUDE_BIN=/opt/homebrew/bin/claude`. Rodar em background (`nohup`, log em `logs/`); acompanhar pelo log, sem
  poll curto.
- [ ] **Step 2: Resumo Splash:** `summarize_claude.py --results-dir results --prefix rc --variants
  s=subagents,d=decode_share --out results/claude-summary-splash.json --markdown`. Conferir: `errors == 0` em
  todos os profiles, `task_done` true, `requests.pair.max_concurrent == 2`, `subagents.requests.max_concurrent`
  anotado (é o N real).
- [ ] **Step 3: Fila mlx-serve** (`logs/q-mlx.sh`): `rm1` (a, b, c, d × 2), `rm2` a,b × 3, `rm2` c,d × 3,
  `rm2s` × 3. Mesmo chain.
- [ ] **Step 4: Resumo mlx:** idem com `--prefix rm --out results/claude-summary-mlx.json`.
- [ ] **Step 5: Religar o driver da 11234** (o `chain.sh` faz) e **avisar a sessão de stack** que 11234 e 8585
  estão livres.
- [ ] **Step 6: Commit** dos `cc-*.json`, `req-*.jsonl` e dos dois resumos:

```bash
git add bench/claude-code-concurrency-2026-11/results
git commit -m "bench(claude-code-concurrency): results of the rc* and rm* arms"
```

### Task 8: `results/summary.md`

- [ ] **Step 1: Escrever `results/summary.md`** (pt-BR): cabeçalho (rig, data, servidores, Claude Code), tabela por
  braço × tarefa × rep (`wall_s`, `num_turns`, contexto final, `task_done`, erros), tabela por braço (TTFT quente
  p50/p90, tok/s p50/min, primeiro prompt, `pair_wall_s`, tempo poupado, `max_concurrent`, swap Δ do
  `*-mem.jsonl`), posição nas faixas de experiência por servidor e cenário, respostas às três perguntas da spec,
  `## Veredito`, `## Leitura`, `## O que não foi medido`.
- [ ] **Step 2: Conferir cada número da tabela contra os JSON** (um script de uma linha por coluna, ou o
  `--markdown` do resumo). Commit:

```bash
git add bench/claude-code-concurrency-2026-11/results/summary.md
git commit -m "bench(claude-code-concurrency): summary"
```

### Task 9: Report, docs e card

**Files:**
- Modify: `bench/flashnext-concurrency-2026-10/scripts/render_report.py` (`collect_scenarios`: `two[key]`
  ganha `subagents` e `decode_share` do resumo; `worst[key]["best_setting"]` do Splash passa a vir do `rc2d`
  real quando existir, com o sintético `k2c2ad1` como fallback; a linha de cobertura "Claude Code with subagents"
  já lê `claude[key]["subagents"]`)
- Modify: `bench/flashnext-concurrency-2026-10/scripts/report_sections.py` (`many_sessions`: a linha
  "2 sessions + subagents (real Claude Code)" mostra `turn` = `subagents.requests.warm.ttft_p50` e o N medido;
  a nota passa a dizer "ran as N streams (measured)"; `two_sessions`: linha "with subagents" nos halteres quando
  houver dado)
- Modify: `bench/flashnext-concurrency-2026-10/tests/test_render_report.py`
- Regenerate: `results/report-data.json` e `reports/qwen38-flashnext-concurrency.html`
- Modify: `reports/index.html` (data e descrição do card), `reports/README.md`, `docs/models/qwen3.8-flash-next.md`
  (tabela "Concurrent sessions": linhas da tarefa realista e dos subagentes, com os dois servidores)

- [ ] **Step 1: Testes**

```python
def test_collect_scenarios_reads_subagents_and_decode_share(campaign_b_claude):
    sc = RR.collect_scenarios(DATA, campaign_b_claude, None)
    s = sc["two_sessions"]["splash"]
    assert s["subagents"]["max_concurrent"] == 3 and s["subagents"]["ttft_p50"] == 2.6
    assert sc["worst_case"]["splash"]["best_setting"]["label"] == "--decode-share 1.0 (real pair)"
    assert sc["coverage"][7]["cells"]["splash"] == "measured" and sc["coverage"][7]["cells"]["mlx"] == "measured"

def test_many_sessions_row_shows_measured_streams(campaign_b_html):
    assert "ran as 3 streams" in campaign_b_html and "Not measured with real Claude Code yet" not in campaign_b_html
```

(`campaign_b_claude` = fixture com `claude-summary-splash.json`/`-mlx.json` mínimos, `subagents.requests.
max_concurrent 3`, `warm.ttft_p50 2.6`; `campaign_b_html` = `render(collect(...))` com ela.)

- [ ] **Step 2: Rodar e ver falhar.** Expected: `KeyError: 'subagents'`.
- [ ] **Step 3: Implementar; rodar os 166 + 2 testes do render.** Expected: todos passam, inclusive os casos
  "sem campanha B" (hachuras continuam).
- [ ] **Step 4: Regerar** `report-data.json` e a página com `--campaign-b-dir bench/claude-code-concurrency-2026-11/results`;
  conferir no browser pane (`preview_start repo-static`, `http://localhost:8765/reports/qwen38-flashnext-concurrency.html`):
  seções 2, 3, 4 e a matriz sem `n/m` nas colunas Splash e mlx-serve 26.10.3 para tarefa realista e subagentes;
  claro, escuro e largura de celular. Parar o preview no fim.
- [ ] **Step 5: Docs:** tabela do `docs/models/qwen3.8-flash-next.md` com as linhas novas (valores do
  `claude-summary-*.json`, em segundos), data no card do `reports/index.html` e na linha do `reports/README.md`.
  `test_model_doc_numbers_match_payload` continua verde.
- [ ] **Step 6: Commit**

```bash
git add bench/flashnext-concurrency-2026-10 reports docs/models/qwen3.8-flash-next.md
git commit -m "report(flashnext-concurrency): real pair, subagents and decode-share from campaign B"
```

### Task 10: Revisão final e PR

- [ ] **Step 1:** rodar as três pastas de testes (Restrições globais). Expected: todas verdes.
- [ ] **Step 2:** revisão de branch inteira (superpowers:executing-plans, "Final Review") no modelo mais capaz;
  um passe de correções para Critical/Important com teste RED→GREEN; minors no ledger.
- [ ] **Step 3:** push e PR `bench/claude-code-concurrency-2026-11` → `main`, corpo com as três respostas da spec
  e o link do `summary.md`. Merge só com o sim do usuário.

## O que este plano não cobre

- Sessão interativa de Claude Code (permissões e títulos reais): pergunta aberta no apêndice do report.
- Terminal-Bench no Splash e a troca do daily driver.
- 256K com Claude Code real, 512K, 1M, mais de 4 streams, outros modelos.
