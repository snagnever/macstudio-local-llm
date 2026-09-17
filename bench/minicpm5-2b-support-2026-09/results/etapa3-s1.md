# Etapa 3 — qualidade em português, s1 (2026-09-16)

O card do MiniCPM5-2B lista só inglês e chinês; as tarefas de suporte rodam em português.
Avaliação por rubrica — **formato**, **conteúdo**, **idioma** — nas tarefas reais: 20 de
texto (5 títulos, 5 commits, 5 classificações, 5 resumos) e 10 tool calls simples.

Método: `scripts/quality-run.py` com `:no-think`, `temperature=0.7`, `top_p=0.95`,
`max_tokens=128` (texto) / `256` (tool). 1 passe, 30 tarefas, s1 sozinho (sem driver).

## Resultado

| rubrica | acertos | gate ≥90% |
|---|---:|---|
| formato | 30/30 (100%) | passa |
| idioma (texto de saída) | 30/30 (100%) | passa |
| conteúdo/instrução | 28/30 (93%) | passa |
| tool calls (nome + argumentos válidos) | 10/10 | passa |

## Amostras

- **Título:** "Servidor MLX" · "Limpeza cache" · "Reiniciar Servidor" — curtos e em PT.
- **Commit:** "Corrigido o parser para converter chamadas de ferramenta do MiniCPM5 em tool_calls da API OpenAI, substituindo XML por texto puro."
- **Tool call:** `get_weather({"city": "Paris"})`, `write_file({"path":"notas.md","content":"rascunho"})`.

## Problemas encontrados

1. **Classificação (1/5):** `intent-03` ("Roda a etapa de concorrência... e me manda o
   resultado") foi rotulado **informação** em vez de **pedido**. As outras 4 corretas.
2. **Idioma em argumento de tool (1):** `tool-09` traduziu o assunto para inglês —
   `subject: "Report"` em vez de `"Relatório"` (o corpo ficou em PT). Não pega no gate de
   idioma do texto, mas é um vazamento.
3. **Tipos no schema (2):** `tool-04` mandou `port` como string (`"11234"`) e `tool-08`
   `limit` como string (`"3"`), onde o schema pede inteiro. O resto dos argumentos casa.
4. **Commit-04** ficou longo e começou com gerúndio ("Removido a limpeza... movendo..."),
   não uma linha imperativa enxuta — estilo, não erro.

## Leitura

Formato e idioma passam com folga — os títulos, commits e resumos em PT são utilizáveis.
Os defeitos são de **conteúdo fino** (uma classificação, uma tradução, tipos de argumento),
não de formato ou idioma. Com ressalva de que o gate do plano é justamente formato+idioma
≥90%, o s1 atende.

## Limites

- Um passe; sem os dois passes cegos do plano (não há segundo modelo para comparar).
- `s2` e `s3` não rodaram a Etapa 3 (escopo reduzido ao s1).
- A checagem de idioma é heurística (CJK/ASCII); a leitura das 30 saídas foi manual.

Dados: `results/etapa3-s1.jsonl`. Relatório: `scripts/report_quality.py`.
