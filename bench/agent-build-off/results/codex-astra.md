# STATS — Hyper Runner (`hyper-runner-astra`)

Este relatório registra a sessão que criou o jogo.
Os valores vêm do repositório e dos registros locais do Codex.
O relatório não inclui os tokens usados para criar este arquivo.

## Sessão

| Campo | Valor |
| --- | --- |
| Data de criação | 6 de setembro de 2026 |
| Intervalo de atividade | 22:24–23:31 BRT (01:24–02:31 UTC) |
| Duração observada | 1 h 07 min |
| Sessão principal | `01a07976-adeb-72b0-9816-520e3afb007e` |
| Modelos | `gpt-6-astra`, `gpt-5.6-sol` e `codex-auto-review` |
| Agentes delegados | 5 |
| Chamadas de ferramenta | 187: 156 comandos, 16 mensagens entre agentes, 5 delegações, 4 retomadas, 3 perguntas, 2 esperas e 1 consulta de agentes |
| Resultado | Jogo 3D local completo, verificado e sem publicação pública |

O intervalo usa o primeiro e o último registro de uso de tokens.
Os agentes executaram tarefas em paralelo, portanto a duração não é a soma do tempo de cada agente.

## Tokens

Os registros têm 227 respostas únicas.
O campo de entrada inclui tokens atendidos pelo cache.

| Modelo | Entrada | Cache de entrada | Saída | Total |
| --- | ---: | ---: | ---: | ---: |
| `gpt-6-astra` | 11.394 M | 11.114 M | 54.035 | 11.448 M |
| `gpt-5.6-sol` | 6.255 M | 6.040 M | 42.146 | 6.297 M |
| `codex-auto-review` | 860.102 | 707.328 | 2.701 | 862.803 |
| **Total** | **18.509 M** | **17.861 M** | **98.882** | **18.608 M** |

O total contém 647.559 tokens de entrada sem cache.
Os registros também indicam 18.106 tokens de raciocínio, já incluídos nos tokens de saída.

## Custo

O custo real não está nos registros do Codex.
O preço depende do plano, da conta e da tabela de créditos ativa.

A tabela de créditos publicada para `gpt-6-astra` e `gpt-5.6-sol` estima **518,36 créditos** para os dois modelos identificados.
O cálculo exclui `codex-auto-review`, pois o registro não revela seu modelo faturado.
Créditos não são um valor fixo em dólares e a conta pode ter usado a franquia do plano.

| Modelo | Estimativa de créditos |
| --- | ---: |
| `gpt-6-astra` | 415,42 |
| `gpt-5.6-sol` | 102,94 |
| `codex-auto-review` | Não disponível |

Consulte a [tabela de créditos do Codex](https://help.openai.com/en/articles/11481834-chatgpt-rate-card) para as taxas vigentes.
Consulte a página de uso da conta para o valor efetivamente cobrado.

## Projeto

| Métrica | Valor |
| --- | ---: |
| Linhas de código em `src/` | 1.435 |
| Linhas de teste | 536 |
| Arquivos de código | 16 |
| Arquivos de teste | 5 |
| Dependências diretas | 2 de execução e 4 de desenvolvimento |
| Pacotes no lockfile | 90 |
| Arquivos de ativos locais | 9 |
| Capturas de tela | 7 |
| Ativos locais | 2,2 MB |
| Build de produção | 5,7 MB, 180 arquivos |

O projeto usa Babylon.js, TypeScript, Vite, Vitest e Playwright.
Ele contém um personagem glTF local e cinco arquivos de áudio locais.

## Verificação registrada

| Verificação | Resultado |
| --- | --- |
| TypeScript | Aprovado |
| Vitest | 36 testes aprovados |
| Playwright | 14 testes de navegador aprovados |
| Build de produção | Aprovado |
| Medição de desktop | 60,00 quadros por segundo durante 125,076 s |
| Transferência medida | 2.886.555 bytes |

A medição usou Chromium 153, viewport de 1440 × 900, qualidade alta e Apple M5 Pro.
O repositório não registra teste em dispositivo móvel físico, Firefox, Safari ou saída audível.

## Validação deste relatório

Em 7 de setembro de 2026, `npm run typecheck`, `npm test` e `npm run build` foram aprovados.
O Playwright não executou neste ambiente porque o executável Chromium não está instalado.
O servidor local iniciou após autorização fora da sandbox, mas os 14 testes pararam antes de carregar o jogo.

## Fontes

- Registros de sessão do Codex em `~/.codex/sessions/2026/09/06/` e `~/.codex/archived_sessions/`.
- [Registro de verificação](docs/VERIFICATION.md).
- [Medição de desempenho](docs/performance.json).
- [Especificação](SPEC.md) e [plano](PLAN.md).

---

## Verification against the session logs

*Everything below this line was added when this file was adopted into the
`agent-build-off` campaign on 2026-09-07. It is not part of what the
`codex-astra` arm reported about itself — the arm's own report ends at
"Fontes" above.*

### Method

`bench/agent-build-off/scripts/verify_codex_stats.py` was run against every
Codex rollout file whose `session_meta.cwd` matches
`/Users/vitor/LocalProjects/hyper-runner-astra`:

```
cd /Users/vitor/LocalProjects/macstudio-local-llm
python3 bench/agent-build-off/scripts/verify_codex_stats.py \
  /Users/vitor/LocalProjects/hyper-runner-astra \
  $(grep -l '"cwd":"/Users/vitor/LocalProjects/hyper-runner-astra"' \
      ~/.codex/sessions/2026/09/0*/*.jsonl ~/.codex/archived_sessions/*.jsonl 2>/dev/null)
```

This matched 13 rollout files. The script sums each file's last recorded
`total_token_usage` (cumulative per rollout file — one file per delegated
agent/sub-session), which is the correct way to reconstruct the grand total
across all three models and five delegated agents, since `token_count` records
do not break down by model.

### Self-reported vs. log-derived totals

| Figure | Tokens | Notes |
| --- | ---: | --- |
| Self-reported grand total (STATS.md, all 3 models) | 18,608,000 (18.608 M) | States it excludes the session that wrote the file: *"O relatório não inclui os tokens usados para criar este arquivo."* |
| Log-derived total, all 13 matched rollout files | 21,121,999 | Full script output below. Includes every session the logs attribute to this `cwd`, including the one that wrote STATS.md. |
| — of which: the stats-writing session (`01a07ec3-...`, 2 rollout files, prompt confirmed below) | 3,471,614 | Identified by grepping the two files for their first user prompt (see below); their timestamps (2026‑09‑07T23:05 and 23:12 BRT) are a day after the ~1 h build session STATS.md describes. |
| Log-derived total **excluding** the stats-writing session | 17,650,385 | 21,121,999 − 3,471,614. |
| Gap: log (excl. stats session) − self-reported | **−957,615 (≈ −5.1%)** | Logs excluding the stats session read **lower**, not higher, than the self-report. |
| Gap: log (incl. stats session) − self-reported | +2,513,999 (≈ +13.5%) | Direction matches the stated exclusion (logs include more because they include the extra session), but the size of that session (3,471,614) is larger than this gap by 957,615 — the numbers do not cleanly reconcile purely on the stated exclusion. |

**Finding, stated plainly:** the direction of the discrepancy (full logs read
higher than the self-report) is consistent with the arm's stated exclusion of
the stats-writing session. But the magnitude does not reconcile: subtracting
the identified stats-writing session's tokens from the full log total leaves
17,650,385 — about 957,615 tokens (5.1%) *below* the self-reported 18.608 M,
not equal to it. So while the excluded-session explanation accounts for the
sign of the gap, it does not fully account for its size. Possible reasons
(not verified here): the arm's own per-model table may aggregate token counts
by a different method than "last cumulative `total_token_usage` per rollout
file" (e.g. summing per-response deltas, as its "227 unique responses" note
suggests), or some sessions counted by the arm are not present under this
exact `cwd` string in the logs this script can see. This is reported as an
open discrepancy, not resolved.

Confirmation that `01a07ec3-6900-7a01-b965-9788a00fc36f` is the stats-writing
session (first user prompt, machine-translated from Portuguese in the log):
*"Based on the file /Users/vitor/LocalProjects/hyper-runner-qwen-cc/STATS.md,
create a STATS.md for this repository..."*

### Full script output (all 13 matched rollout files)

```json
{
  "session_count": 13,
  "model": "gpt-5.6-sol",
  "first_timestamp": "2026-09-07T01:23:37.135Z",
  "last_timestamp": "2026-09-08T02:13:46.801Z",
  "tokens": {
    "input_tokens": 21018527,
    "cached_input_tokens": 20247168,
    "cache_write_input_tokens": 0,
    "output_tokens": 103472,
    "reasoning_output_tokens": 23543,
    "total_tokens": 21121999
  },
  "user_prompts": 53,
  "tool_calls_total": 223
}
```

(`session_count` counts rollout files, not distinct session IDs — several
files share a session ID because delegated sub-agents and resumed/compacted
segments each get their own rollout file. `model` only reflects the last
`model` field the script observed, not a breakdown; the arm's own per-model
split — gpt-6-astra 11.448 M / gpt-5.6-sol 6.297 M / codex-auto-review
862,803 — is finer than these logs expose to this script, per the brief.)

### `statsSessionIncluded`

**`false`.** The arm states plainly that its totals exclude the session used
to produce the file: *"O relatório não inclui os tokens usados para criar
este arquivo."* This matches `opencode-qwen38` (excludes) and differs from
`opencode-qwen38-superpowers` (includes); `claude-opus5` states nothing
(`null`, "not stated").

### Structural caveats for the roster

- **Multi-model, multi-agent.** `codex-astra`'s 18.608 M tokens span three
  models (`gpt-6-astra`, `gpt-5.6-sol`, `codex-auto-review`) across 5
  delegated agents. The other three arms (`opencode-qwen38`,
  `opencode-qwen38-superpowers`, `claude-opus5`) each ran a single model in a
  single agent. This makes `codex-astra`'s token total **not comparable** to
  the other three arms' totals — a larger caveat than the stats-session
  convention above.
- **Reported in Portuguese.** This is the only arm whose STATS.md is written
  in Portuguese, with headings that do not match the other three arms
  (Sessão, Tokens, Custo, Projeto, Verificação registrada, Validação deste
  relatório, Fontes vs. the other arms' Session, Compactions, Tokens, Code,
  Libraries, Build output, Process, Defects found during verification and
  fixed, Not verified, Other metrics worth adding). It is kept as the arm
  wrote it, per the campaign's global constraints; dashboard-facing figures
  are translated into `arms.json`, not into this file.
- **Heading gap.** This arm's file has no "Compactions" heading and no
  section quoting its first prompt verbatim, both of which the sibling
  `hyper-runner-claude/STATS.md` has. The first prompt was recovered directly
  from the Codex rollout log instead (see below) — this is a gap in what
  `codex-astra` reported, not something papered over.
- **Only arm with a measured frame rate.** `docs/VERIFICATION.md` records 36
  Vitest tests and 14 Playwright tests (Chromium 153.0.8010.12) with a
  17-row acceptance table containing two partial rows, and
  `docs/performance.json` records a 125.076 s sample at a mean 60.00 fps
  (median frame 16.70 ms, p95 17.10 ms), 1,199 meshes, 137–169 draw calls, on
  an Apple M5 Pro through ANGLE Metal. `codex-astra` is the **only** one of
  the four arms with a measured frame rate — the other three record frame
  rate as not collected. That is a gap in the other three arms' verification,
  not a win to credit to this one.

### First prompt: same brief as the other arms

`codex-astra`'s STATS.md does not quote its first prompt. Recovered from
`rollout-2026-09-06T22-23-36-01a07976-adeb-72b0-9816-520e3afb007e.jsonl`, the
first substantive user turn reads:

> You are going to create a complete and impressive 3D demo runner game,
> using modules and libraries to reduce the need of new code.
> You should search the web for most updated information, stack and best
> practices
> Select the stack based on easiness to implement a functional demo on
> reduced time.
> Question me for decisions and ambiguities while creating the plan.
>
> - SAVE a detailed SPEC AND PLAN to SPEC.md and PLAN.md on the folder before
>   building
> - Create an AGENTS.md explaining the repo objective, poiting to both PLAN
>   and SPEC files

This is the same brief `hyper-runner-claude/STATS.md` quotes under "The first
prompt, verbatim" (word-for-word, including the "poiting" typo), so the four
arms did receive a like-for-like starting prompt even though `codex-astra`
does not itself record that fact.
