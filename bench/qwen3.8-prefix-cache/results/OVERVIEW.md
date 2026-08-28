# Overview da campanha — dados consolidados e dashboard

Este diretório mantém um resumo consolidado para evitar varrer os JSONL brutos
toda vez que alguém pede um overview.

## Arquivos

| Arquivo | Papel |
|---|---|
| `overview.json` | Dados consolidados (fonte única). Gerado, não editar à mão. |
| `overview.html` | Dashboard autocontido. Gerado a partir do `overview.json`. |
| `../scripts/consolidate.py` | Lê os JSONL + gates uma vez e escreve `overview.json`. |
| `../scripts/render_overview.py` | Lê `overview.json` e escreve `overview.html`. |

## Fluxo de atualização

Rode os dois, nesta ordem, sempre que novos resultados chegarem:

```bash
python3 bench/qwen3.8-prefix-cache/scripts/consolidate.py
python3 bench/qwen3.8-prefix-cache/scripts/render_overview.py
```

Depois republique o artefato com o **mesmo** `file_path`
(`bench/qwen3.8-prefix-cache/results/overview.html`) para manter a mesma URL.

## Para o agente: como responder "overview" sem varrer tudo

1. Rode `consolidate.py` (rápido; lê os JSONL uma vez).
2. Leia `overview.json` — ele já tem, por braço: `decode_tps`, `ttft_identical_ms`,
   `e2e_identical_ms`, `cache_hit_identical`, `correct/total`, `mode`
   (`canonical`/`greedy`), mais `tool_loop`, `gates`, `verdicts` e `queue`.
3. Não releia `cache-probe.jsonl` inteiro para montar tabelas — use o `overview.json`.

## O que é editorial (atualizar à mão no `consolidate.py`)

- `VERDICTS`: vereditos de gate (T promovido, X não, etc.).
- `QUEUE`: estado de cada estágio (`done`/`running`/`pending`).

Os agregados de desempenho e os arquivos de gate são derivados automaticamente.

## Cuidados de leitura embutidos no dashboard

- **Decode** (tok/s) é comparável entre todos os braços.
- **E2E** não compara entre classes de conteúdo: `code` gera resposta curta,
  `audit` gera raciocínio longo. Compare E2E só dentro da mesma classe.
- `mode=greedy` é diagnóstico (`temp=0`), não a métrica de decisão. Só
  `mode=canonical` (amostragem do vendor) conta para o veredito.
