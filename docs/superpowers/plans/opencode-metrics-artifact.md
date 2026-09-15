# Plano: artefato atualizável de métricas do opencode

## Objetivo

Gerar um dashboard HTML autocontido em `reports/` que mostra desempenho por
modelo e provider ao longo do tempo, incluindo TTFT, prefill, TPS, TPS por
contexto e contexto total. Reexecutar um comando atualiza o artefato.

## Realidade dos dados

Toda métrica sai do SQLite local `~/.local/share/opencode/opencode.db`. Não há
plugin oficial nem endpoint de streaming que grave o primeiro token com
precisão. Os timestamps disponíveis são:

| Fonte | Campo | Uso |
| --- | --- | --- |
| `message.data` | `time.created`, `time.completed` | início e fim do request |
| `message.data` | `tokens.input/output/reasoning/total/cache.read/write` | contagem |
| `part` (linha) | `time_created`, `time_updated` | timing por step |
| `part.data` (step-start) | linha `time_created` | envio do request do step |
| `part.data` (text/reasoning) | `time.start`, `time.end` | primeiro conteúdo do step |

Confirmei as fórmulas no banco real. Elas produzem valores plausíveis.

## Papel do opencode-usage

O opencode-usage lê o mesmo banco e agrega token e custo por modelo, provider,
agente, sessão e dia, com saída JSON. Ele reduz código apenas na metade de
token e custo. Ele não calcula TTFT, prefill nem TPS, porque latência não está
no escopo dele.

Decisão: usar o JSON do opencode-usage para a dimensão token/custo e SQL
próprio contra a tabela `part` para a dimensão de latência e throughput. Se a
dependência não valer a pena, uma única query SQL cobre as duas dimensões.

## Catálogo de métricas

Por mensagem do assistente, escopo ao **primeiro step** para não misturar tempo
de tool call. `first_tok` = menor `time.start` entre os parts `text`/`reasoning`
do primeiro step. `req` = `time_created` do `step-start`.

| Métrica | Fórmula | Confiança |
| --- | --- | --- |
| TTFT (ms) | `first_tok - req` | média: proxy, não é o primeiro token real do stream |
| Prefill (tok/s) | `input / (TTFT/1000)` | baixa: aproximação do processamento do prompt |
| TPS | `output / ((t_done - first_tok)/1000)` | alta |
| TPS por contexto | `TPS / total_tokens` | alta |
| Contexto total | `tokens.total` | alta |
| Cache hit ratio | `cache.read / (input + cache.read)` | alta |
| Reasoning ratio | `reasoning / output` | alta |
| Custo por 1k output | `cost / output * 1000` | alta, mas `$0` em provider custom sem preço |
| Latência de tool | `time_updated - time_created` do part `tool` | alta |

Séries temporais: agregar cada métrica por dia e por modelo. Medianas, não
médias, porque a distribuição de TPS tem cauda longa.

## Arquitetura

Segue o padrão do repo: coletor em `tools/`, dashboard autocontido em
`reports/`, sem dado-fonte solto.

1. **Coletor** `tools/opencode_metrics.py`
   - Abre o banco em modo somente leitura.
   - Uma query deriva por mensagem: modelo, provider, dia, tokens, TTFT, TPS,
     contexto, custo.
   - Agrega por (dia, modelo) e por (modelo) all-time: mediana, p90, soma,
     contagem.
   - Emite um único `metrics.json`.
   - Flag `--days N` e `--project` espelham o `opencode stats`.
2. **Dashboard** `reports/opencode-metrics.html`
   - Chart.js, igual aos outros reports.
   - JSON embutido inline no build para ficar autocontido no GitHub Pages.
   - Painéis: TPS por modelo ao longo do tempo, TTFT por modelo, contexto médio
     por dia, custo acumulado, tabela all-time por modelo.
   - Seletor de janela (7/30/all) e de modelo.
3. **Atualização** `tools/build_opencode_metrics.sh`
   - Roda o coletor, injeta o JSON no HTML, escreve em `reports/`.
   - Reexecutar atualiza o artefato. Sem servidor, sem estado.

## Passos

1. Escrever a query única e validar contra `opencode stats --models` na
   dimensão token/custo.
2. Escrever o coletor e o `metrics.json`.
3. Decidir opencode-usage: instalar e comparar JSON, ou manter só SQL. Manter só
   SQL se a query já cobre tudo sem perda.
4. Construir o HTML com Chart.js e o JSON embutido.
5. Script de build que regenera o artefato.
6. Documentar as aproximações de TTFT e prefill no rodapé do dashboard.

## Limitações a declarar no artefato

- TTFT e prefill são proxies. O opencode não grava o primeiro token real do
  stream. O valor inclui setup do step.
- Custo é `$0` para provider custom fora do models.dev.
- TTFT de um step pode incluir espera de fila do provider remoto.
