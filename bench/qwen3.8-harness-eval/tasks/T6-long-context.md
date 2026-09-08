# T6 — Revisão de repositório grande

**Fixture:** um repositório do usuário com 50+ arquivos de código que o usuário conhece bem.
**Time-box:** 30 min. **Mede:** uso de contexto longo, alucinação de arquivo/linha.

Rode com `limit.context` 131072. Anote o `prefill_hit` do runtime.

## Prompt

```text
Review this repository. Deliver, in a file named REVIEW.md:

1. A one-page architecture summary: entry points, main modules, data flow.
2. Three concrete defects or risks, each with file path and line number, a one-sentence
   explanation and a one-sentence fix. Only report what you actually read in the code.
3. The commands you ran to gather this information.

Do not modify any file other than REVIEW.md.
```

## Verificação

1. Para cada defeito, abra o `file:line` citado. Ele existe? O trecho diz o que o agente disse?
2. O resumo de arquitetura bate com o que o usuário sabe do repositório?
3. `git status` mostra só `REVIEW.md`.

`pass` = 3/3 citações reais, resumo sem erro grosseiro, nenhum outro arquivo alterado.
Registre em `notes` o número de citações alucinadas (0–3).

## Follow-up

```text
One of your citations does not match the code at that path and line. Re-open each cited
file, verify every line number, and correct REVIEW.md.
```

## Rubrica

- `q_correct`: os defeitos são reais e relevantes, ou triviais (estilo)?
- `q_process`: o agente usou busca e leitura de arquivos ou opinou sem abrir?
- `tool_calls` e `wall_min` aqui medem o custo real de contexto longo por harness.
