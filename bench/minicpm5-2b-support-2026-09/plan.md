# 2026-09-15 — MiniCPM5-2B: modelo de suporte em paralelo ao Flash-Next

> **Objetivo:** decidir se um modelo de 2B residente ao lado do driver
> [qwen3.8-flash-next](../../docs/models/qwen3.8-flash-next.md) paga o próprio custo. O 2B absorve
> turnos curtos e sem raciocínio (título de sessão, commit, classificação, resumo curto, tool call
> simples) que hoje entram na fila do driver, porque o mlx-serve não faz batched decode no MoE.
> **A métrica que decide é o `T_turno` do driver sob concorrência**, não a velocidade do 2B.
> **Fora de escopo:** trocar o driver, speculative decoding (o Flash-Next já roda MTP com aceitação
> 0.50–0.67), contexto longo no 2B (HashHop 24% no card da quant), qualidade de agente do 2B
> (Terminal-Bench), quants GGUF/GPTQ/oQ4e.
>
> Card do modelo: [docs/models/minicpm5-2b.md](../../docs/models/minicpm5-2b.md).
> Baseline do driver: [../qwen38-flashnext-daily-driver-2026-09/results/summary.md](../qwen38-flashnext-daily-driver-2026-09/results/summary.md).
> **Status (2026-09-16): CONCLUÍDA.** Veredito: **não adotar** como suporte residente do
> driver diário (perda de `T_turno` +43–66% na carga contínua; a 128K não há margem de
> memória). Viável só em contexto ≤32K com turnos intermitentes (gap ≥1 s → +12%). A Etapa 3
> foi reduzida ao s1. Ver [results/summary.md](results/summary.md).

## Baseline que esta campanha não re-mede

Da campanha do driver (2026-09-13, mesma máquina, perfil do vendor): `T_turno` **11.03 s a 32K** e
**12.35 s a 128K**, decode quente 55.9 / 49.7 tok/s, prefill ~700–735 tok/s, wired 97.3 / 108.1 GB,
swap 0. Esses números são o **solo** do driver. Toda comparação aqui é contra eles, medida na mesma
fixture e na mesma sessão — não reuso número arquivado quando a comparação for o veredito.

## Os candidatos

| # | Quant (SHA) | Disk | Papel |
|---|---|---:|---|
| s1 | `mlx-community/MiniCPM5-2B-OptiQ-4bit` (`d139292`) | 1.8 GB | primeira escolha, quant mista 4/8 |
| s2 | `mlx-community/MiniCPM5-2B-8bit` (`2d20e8e`) | 2.5 GB | referência de qualidade |
| s3 | `gemma-4-e4b-it-mlx` (8-bit, `c63b2f9`) | 8.97 GB | incumbente do slot pequeno, já no rig |

Os dois primeiros já estão em `~/.cache/local-llms/minicpm5-2b-support/`. O s3 entra só na etapa de
qualidade e na de concorrência, como controle: é o que o rig usaria hoje.

## Decisão de runtime (Etapa 0 resolve)

O MiniCPM5 emite tool call no formato próprio `<function name="...">`. Quem converte isso em
`tool_calls` OpenAI:

| Servidor | Parser de tool call | Custo |
|---|---|---|
| `optiq serve` (pacote `mlx-optiq`) | sim, nativo; aceita sufixo `:think` / `:no-think` | runtime novo no rig, em venv isolado |
| `mlx_lm.server` | não | já existe no rig |

Instalar em venv isolado, como o oMLX. **Não** tocar no ambiente do mlx-serve que serve o driver.
Se o `optiq serve` não subir, o plano segue sem tool call: o 2B fica só com tarefas de texto e a
Etapa 3 marca o item como bloqueado.

## Protocolo

- **Driver:** o launcher de sempre, [serve-flashnext-daily-driver.sh](../../tools/scripts/serve-flashnext-daily-driver.sh),
  porta 11234, 131K, MTP on, prefix-cache 16 GB.
- **Suporte:** porta **11235** (1234 é o LM Studio, 11234 é o driver).
- **Sonda do driver:** [cache_probe.py](../qwen3.8-prefix-cache/scripts/cache_probe.py), cenários
  `cold → identical → append → tool_turn`, perfil do vendor (`temperature=1.0`, `top_p=0.95`,
  `top_k=20`, xhigh, limite 4096). Mesma fixture da campanha do driver.
- **Carga do 2B:** `scripts/support-load.py` (a escrever) — gera turnos curtos em laço, com prompt
  de 200–800 tokens e resposta de até 256 tokens, e grava decode tok/s e TTFT por turno.
- **Amostragem do 2B:** `enable_thinking=False`, `temperature=0.7`, `top_p=0.95`, `min_p=0.0`
  (o perfil no-think do card). O thinking fica fora: num teste com Ollama o raciocínio consumiu o
  limite de tokens e a resposta não saiu.

## Etapas

### Etapa 0 — subir e falar (custo: minutos)

Sem o driver no ar. Para s1 e s2: carregar, responder um prompt curto, medir tempo de carga, decode
solo e memória. Confirmar no `optiq serve`: um tool call simples vira `tool_calls` OpenAI e o
sufixo `:no-think` suprime o bloco `<think>`. Candidato que não carrega sai aqui.

### Etapa 1 — solo (custo: ~1 h)

Cada quant sozinho na máquina, prompts de 1K e 8K, 3 repetições: TTFT, decode tok/s, memória de
pico. Dá o teto de velocidade de cada um e o custo de KV a 8K. É a referência para medir quanto a
concorrência tira do 2B.

### Etapa 2 — concorrência (a etapa que decide)

Driver no ar e sondado pelo `cache_probe.py`; o 2B gerando em laço ao mesmo tempo.

| Arranjo | O que mede |
|---|---|
| A — driver sozinho | re-confirma o baseline na sessão de hoje |
| B — driver + s1 | perda do `T_turno` com a quant mista |
| C — driver + s2 | perda com 8-bit (mais bytes por token) |
| D — driver + s3 | perda com o incumbente de 8.97 GB |

Bandas 32K e 128K, 3 repetições por arranjo, ordem por banda (todos a 32K, depois todos a 128K),
mesma sessão e mesmo estado térmico. Registrar também o decode do 2B sob carga, `wired`, memória
livre mínima e **swap** — com o driver a 108 GB a 128K, a margem é o que sobra.

Higiene herdada da campanha do driver: `cold` tem que ser frio (limpar `~/.mlx-serve/kv-cache` antes
de cada `cold` e registrar a limpeza), esperar memória livre ≥ 82 GB antes de subir o próximo
servidor, GPU < 50 °C entre bandas.

### Etapa 3 — qualidade nas tarefas reais, em português

20 tarefas curtas, 5 por tipo: título de sessão, mensagem de commit, classificação de intenção,
resumo de saída de tool. Mais 10 tool calls simples se a Etapa 0 liberar o parser. Rodar em s1, s2 e
s3 com a mesma entrada. Avaliação por rubrica de 3 pontos (formato correto, conteúdo correto,
idioma correto), dois passes cegos ao modelo. **O eixo do idioma é obrigatório:** o card lista só
inglês e chinês, e as tarefas aqui rodam em português.

### Etapa 4 — veredito

`results/summary.md` com o ranking, os gates aplicados e a decisão. Atualizar o card do modelo e a
tabela de [docs/models/README.md](../../docs/models/README.md). Se a resposta for sim, escrever o
launcher em `tools/scripts/` e registrar o par porta/model-id.

## Gates

1. **Perda do driver ≤ 15% no `T_turno`** a 32K e a 128K (≤ 12.7 s e ≤ 14.2 s). Acima disso, a fila
   de um slot custa menos que a concorrência e a resposta é não.
2. **Swap = 0** e memória livre mínima > 2 GB nos dois arranjos. Swap invalida o arranjo.
3. **Formato e idioma ≥ 90%** na Etapa 3. Um título em inglês ou um commit malformado quebra o uso.
4. **Ganho real de latência:** a resposta do 2B tem que sair mais rápido que a espera na fila do
   driver. Se o turno do driver já está em 11 s, um suporte de 8 s não resolve nada.

## Riscos conhecidos

- O `optiq serve` é um runtime novo no rig, com 4 dias de repo. Venv isolado, e o driver não muda.
- O ganho pode ser só de fila, não de velocidade: o 2B em MLX 4-bit fez 141–143 tok/s num M1 Max
  (medição preliminar de terceiro), contra 50–56 do driver. Sob concorrência esse número cai.
- A quant mista lê 5.34 bpw contra ~4.5 do 4-bit uniforme, então deve perder ~15% de decode para o
  4-bit oficial. É estimativa, não medição; se a Etapa 1 mostrar perda maior, o 4-bit oficial entra
  como candidato s4.
