# T3 — App do zero (task manager)

**Fixture:** nenhum; diretório vazio. **Time-box:** 25 min. **Mede:** escolha de stack e
primeiro run correto. O brief é o mesmo de [bench/coding-task/README.md](../../coding-task/README.md),
o que permite comparar com os artefatos dos modelos anteriores.

## Prompt

```text
Build a small task manager: add tasks, mark complete, delete, persist state. Pick the stack
you would reach for. Ship something that runs. Include a README with the exact command to
run it. Do not ask me questions; make reasonable choices and state them in the README.
```

## Verificação

1. Siga o README à risca. Sem edições manuais.
2. Adicione uma tarefa, marque como concluída, apague outra, recarregue (ou reinicie) e confira
   se o estado persistiu.

`pass` = os quatro passos funcionam sem editar nada. Registre a stack escolhida em `notes`.

## Follow-up

```text
It does not run as documented. Here is the error I got: <cole o erro>. Fix it and update the
README if the command changed.
```

## Rubrica

- `q_scope`: stack proporcional ao problema? (Next.js + SQLite para um TODO conta contra.)
- `q_correct`: entrada vazia, tarefa duplicada, persistência após reload.
- `q_clarity`: organização dos arquivos e README direto.
- Guarde o artefato em `bench/coding-task/<modelo>-<harness>/` se ele rodar. Sem `node_modules/`.
