# Entrega por harness — auditoria

Complemento do [summary.md](summary.md), escrito à mão. O `summary.md` sai do `summarize.py`.

## Falhas por causa

As 7 sessões que falham declaram a tarefa pronta: o harness sai com código 0 e sem estourar o limite. Li a cópia do repositório de cada uma no rig.

| tarefa | causa | sessões |
|---|---|---:|
| T5 | sai sem corrigir o lint | 2 |
| T5 | corrige o lint e deixa o teste falhar por falta de `SERVICE_NAME` | 1 |
| d | deixa 1 dos 2 bugs sem correção | 2 |
| d | não cumpre a estrutura pedida (`lib/common.sh` ou 8 checks) | 1 |
| b | apaga um teste original | 1 |

- As 3 falhas da T5 são do OpenCode: 2 com o peso `z4`, que saem sem corrigir o lint, e 1 com o `k2`.
- As 3 falhas da tarefa d são da repetição 2 do `z4`, em 3 dos 4 harnesses. A repetição 1 do `z4` fecha 4/4. A causa do bloco não foi investigada.

## A regra da T5 mudou depois da matriz

- O plano exigia `Makefile` igual ao original na T5. O prompt da T5 não diz isso ao modelo: ele proíbe enfraquecer lint ou teste, `noqa` e `skip`.
- 7 sessões passam `SERVICE_NAME` pelo `Makefile`. Nelas o `make check` sai com 0 e o `README.md` documenta a variável. Conferi as 7 cópias no rig.
- Em 2026-11-14 o usuário escolheu a leitura do prompt. O commit `031f63c` conta essas 7 sessões como prontas; o registro guarda a nota `makefile_changed`.
- **Leitura do prompt (a do `summary.md`):** `k2` 54, `z4` 51. A regra "Reserva" passa no limite da tolerância.
- **Leitura do plano:** `k2` 51, `z4` 47. A regra "Reserva" falharia por 1 tarefa.
- Com 2 repetições, a margem de 1 tarefa não separa os dois pesos.

## Como a matriz rodou

- A matriz rodou no rig em 2026-11-14, de 01:55 a 04:48. As 16 sessões da T5 rodaram de novo de 04:57 a 05:16, depois das outras 96 e não intercaladas com elas.
- **T5 repetida.** Na primeira rodada, as 16 sessões da T5 falharam por defeito do sandbox, e 15 das 16 sessões mudaram a configuração do lint para passar: ele esconde o `.git` do repositório que contém a cópia, e o `ruff` falha com `E902`. O commit `4715df3` move as cópias para fora do repositório. Os 16 registros antigos ficam em `logs/t5-invalid/`, fora do git.
- **Check refeito 3 vezes nas cópias guardadas.** O commit `4715df3` deixa de marcar `tests_modified` por linha de import mudada: 20 registros perderam a marca. O commit `04e46d9` separa `makefile_changed` de `lint_config_changed`: 7 registros trocaram de marca. Até aí nenhum `task_done` mudou. O commit `031f63c` muda o `task_done` desses 7 registros para verdadeiro. Os scripts das duas passagens ficam em `logs/`, fora do git.
- O OpenCode do rig é o 1.15.10; o do MacBook é o 1.18.31.

## Limites conhecidos da medição

- O check da T7 não confere se a sessão adicionou testes, e aceita `make test` vazio.
- O check restaura só os arquivos originais de `tests/`. Um `conftest.py` escrito pela sessão roda junto. Nas 112 cópias, só 4 sessões da T5 escreveram `conftest.py`, e a T5 permite isso.
- No limite de tempo, o runner mata o grupo de processos do harness. Um processo filho em outro grupo sobrevive. Nenhuma sessão estourou o limite.
- A regra de sinais do sandbox entrou no commit `04e46d9`, depois da matriz. Os 4 harnesses não rodaram com ela.
- Na matriz, o check rodou com o `HOME` da sessão, e o diretório temporário do check ficava dentro dele. Uma sessão podia deixar ali um arquivo de configuração, ou um processo vivo que mexesse na cópia dos testes originais. Depois da matriz, o check passou a usar um `HOME` próprio e vazio e um Python que ignora o user site. Não procurei sinal desse tipo de manipulação nas 112 sessões.
- Ainda vale: o check executa código da sessão, e esse código roda no mesmo sandbox que guarda a cópia dos testes originais.
