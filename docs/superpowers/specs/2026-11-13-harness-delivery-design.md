# Entrega por harness: 7 tarefas de código, 4 harnesses, 2 pesos — desenho

Data: 2026-11-13. Estado: rascunho para aprovação do usuário. Um leitor novo revisou o documento em 13/11.

## Por quê

O usuário suspendeu a Task 3 (bateria de qualidade) da campanha [swift-uncensored-2026-11](../../../bench/swift-uncensored-2026-11/plan.md). Ele quer duas respostas, nas palavras dele: "ter uma versão uncensored rápida na manga" e "avaliar o harness".

- **Pergunta 1.** O pack uncensored entrega tarefas de código no mesmo nível e no mesmo tempo que o driver diário?
- **Pergunta 2.** Com o mesmo peso, qual harness entrega mais tarefas prontas, e em quanto tempo?

O pack uncensored fica de reserva. O driver diário não muda nesta campanha.

## Metas

1. Rodar as mesmas tarefas de código, com o mesmo pedido e o mesmo check, em 4 harnesses.
2. Medir por sessão: tarefa pronta ou não, e tempo de parede.
3. Dar um veredito por par (harness, peso) e uma tabela que compara os dois eixos.

## Fora de escopo

- A bateria de qualidade (`run-battery.sh`), a sonda de tool calls e a sonda de contexto longo. Elas ficam suspensas.
- Sessões paralelas e subagentes. Cada sessão roda sozinha no servidor.
- Trocar o driver diário ou o launcher.
- O harness `codex`.

## O que faria o teste falhar mesmo rodando

- Um harness recebe uma condição diferente: outro pedido, outro limite de tempo, outro contexto, ou um repositório já usado.
- O check aceita trabalho com trapaça: teste editado, `# noqa`, marcador de skip, regra de lint removida.
- O texto de uma sessão entra no git. O repo é público.

## Decisões do usuário

- **Harnesses:** Claude Code, OpenCode, DeepSeek Harness (`dsh`) e Pi.
- **Tarefas:** as 4 tarefas do teste do Claude Code, mais tarefas difíceis.
- **Uso do resultado:** reserva uncensored e avaliação de harness.
- **Ambiente:** os 4 harnesses rodam isolados.

## Decisões do autor do desenho (o usuário pode trocar)

### Campanha

Uma campanha nova, `bench/harness-delivery-2026-11/`, com `plan.md`, `scripts/`, `tests/`, `results/` e `logs/`, pelas regras do [AGENTS.md](../../../AGENTS.md). Ela é separada da swift-uncensored porque a Pergunta 2 não depende do pack uncensored. O plano da swift-uncensored aponta para ela no lugar da Task 3.

### Tarefas

| id | origem | repositório | tipo | limite |
|---|---|---|---|---:|
| a | `bench/flashnext-concurrency-2026-10/scripts/claude-tasks/` | `repo-a` (`inventory`, Python) | feature `--format` | 15 min |
| b | idem | `repo-b` (`wc_report.sh`) | 2 bugs em shell | 15 min |
| c | idem | `repo-c` (`ledger`, Python) | feature `--group-by` | 15 min |
| d | idem | `repo-d` (toolkit de backup em bash) | 2 bugs em shell | 15 min |
| T1 | `bench/qwen3.8-harness-eval/tasks/T1-bugfix.md` | `fixtures/ledger` | 3 bugs por 4 testes falhando | 15 min |
| T5 | `tasks/T5-env-repair.md` | `fixtures/envfail` | `make check` verde | 20 min |
| T7 | `tasks/T7-chain.md` | `fixtures/ledger` | 5 passos em ordem | 30 min |

- O pedido de cada tarefa é o texto que já existe, sem mudança.
- As tarefas a–d reusam o check que o `run-claude-pair.sh` já aplica (`task_done`). Decisão do autor: o check ganha uma guarda, igual nas 7 tarefas. Os testes originais do fixture rodam a partir de uma cópia intacta contra o código da sessão. Um teste original apagado ou alterado não muda o veredito e fica registrado em `cheat`.
- T1, T5 e T7 ganham um check automático novo, derivado da seção "Verificação" de cada modelo. O check roda fora da sessão, sobre a cópia do repositório.
- O check de T1 exige `5 passed`, o saldo `2815.20` e nenhum arquivo de teste mudado.
- O check de T5 exige `make check` com saída 0, nenhum `noqa` ou `skip` em `app` e `tests`, nenhuma regra de lint removida, e a variável `SERVICE_NAME` no `README.md`. Como no modelo da tarefa, a sessão pode mudar no máximo um arquivo de teste ou `conftest`, e não pode remover a leitura de `os.environ`.
- O check de T7 verifica os 5 passos, um por um, e grava quantos passaram. A tarefa só conta como pronta com 5 de 5. Os testes originais ficam congelados; a sessão pode e deve adicionar testes novos (passos 2 e 3).
- T2, T3, T4 e T6 ficam de fora: T2 e T4 dependem do resultado de outra tarefa, T3 não tem check objetivo, e T6 mede contexto longo.

### Pesos e servidor

- **Pesos:** `k2` (driver diário, referência) e `z4` (jackjusko Heretic v2 com o indexer em `BF16`).
- **Condição:** se o `z4h` falhar na regra "Velocidade" da swift-uncensored, o `z2` entra no lugar dele. O primeiro passo do plano é um portão: a fila só começa com o veredito da Task 2 gravado e o rig livre.
- **Servidor:** Splash 1.6.1 no rig, braço `rc2`, contexto 131072, com `FLASHNEXT_SPLASH_PACK` trocando o peso. Um servidor por vez, uma sessão por vez.
- O servidor do usuário na porta 8585 para durante a fila e volta no fim.

### Onde os harnesses rodam

**Decisão do usuário (13/11, depois do plano):** os 4 harnesses rodam no rig, ao lado do servidor, e falam com ele em `127.0.0.1`. A primeira versão deste desenho rodava os harnesses no MacBook.

- O `pi` e o `dsh` não estavam no rig; a campanha instala as mesmas versões do MacBook (`pi` 0.85.1, `dsh` 0.1.0-rc.6).
- O Claude Code e o OpenCode usam a versão que o rig já tem. O preflight grava as versões.
- O harness e o servidor dividem a CPU e a memória do rig. Os tempos valem para comparar harnesses e pesos entre si nesta campanha.

Os launchers de `bench/qwen3.8-harness-eval/macbook/` servem de referência para os campos de configuração de cada harness.

### Sandbox

Cada harness roda com os pedidos de permissão desligados. Por isso cada sessão, e também o check, rodam dentro do `sandbox-exec` do macOS:

- Escrita: só na cópia do repositório, no `HOME` da sessão e nos diretórios temporários do sistema.
- Leitura em `/Users`: só a cópia, o `HOME` da sessão e os runtimes (`~/.local`, caches do `uv`). Os testes e as soluções de referência da campanha ficam ilegíveis para a sessão.
- `launchctl`, `open`, `osascript`, `ssh` e Apple Events: negados.
- A rede fica aberta: a T5 instala pacotes e todo harness chama o servidor.
- Sem `sandbox-exec`, o runner para com erro, a menos que o operador defina `HARNESS_SANDBOX=0`.

### Sessão

- **Isolamento (decisão do usuário).** Cada harness roda com um diretório de configuração novo e temporário: sem plugins, sem hooks, sem servidores MCP e sem instruções globais do usuário. O modelo é o que o `run-claude-pair.sh` já faz com o Claude Code (`CLAUDE_CONFIG_DIR` novo, `--setting-sources project`, `--strict-mcp-config`).
- A campanha não lê nem escreve os arquivos globais do usuário (`~/.claude`, `~/.config/opencode`, `~/.dsh`, `~/.pi`). Os launchers de `macbook/` servem de referência para os campos de configuração, e não rodam como estão.
- Nenhum harness tem limite de turnos próprio. O único limite é o tempo da tabela, igual para os 4.

- Uma sessão = um harness, uma tarefa, uma cópia nova do repositório, um pedido, nenhuma intervenção.
- Modo não interativo: `claude -p`, `opencode run`, `dsh --profile headless` e `pi -p`.
- Cada harness roda com as permissões de edição e de shell liberadas dentro da cópia.
- O limite de tempo da tabela mata a sessão. Uma sessão morta conta como não pronta, com o motivo `timeout`.
- O esforço de raciocínio é `xhigh` nos 4 harnesses, o padrão do `tools/scripts/serve-flashnext-splash.sh`. O `macbook/lib.sh` usa `medium` por padrão, então cada adaptador passa `EFFORT=xhigh`. O campo de cada harness está em `bench/qwen3.8-harness-eval/plan.md`, seção "Effort por harness".

### Matriz e ordem

- 7 tarefas × 4 harnesses × 2 pesos × 2 repetições = **112 sessões**.
- Teto de tempo de parede: 2 × 2 × 4 × 125 min = 33 h. A duração real não foi medida.
- Ordem dos pesos: repetição 1 roda `k2` e depois `z4`; repetição 2 roda `z4` e depois `k2`.
- Dentro de um peso, a ordem alterna os harnesses por tarefa (a tarefa a nos 4 harnesses, depois a tarefa b, e assim por diante), com rotação do primeiro harness.
- A fila é retomável: uma sessão com resultado gravado não roda de novo.

### Medidas por sessão

Um registro JSON por sessão em `results/`, sem o texto da sessão:

- `harness`, `harness_version`, `pack`, `task`, `rep`, `model_id`
- `task_done` (check), `steps_passed` (T7), `cheat` (qual regra do check a sessão quebrou, se alguma)
- `wall_s`, `exit`, `timeout`
- `claimed_done`: o harness terminou por conta própria antes do limite
- `turns`, `input_tokens`, `output_tokens`: quando o harness ou o servidor informam; senão `null`

O transcript e a cópia do repositório ficam em `logs/` e não entram no git.

### Regras de decisão

A campanha só recomenda.

| regra | condição |
|---|---|
| **Reserva** | somando os 4 harnesses, o `z4` tem tarefas prontas ≥ `k2` − 3 (de 56), e a mediana de `wall_s` das sessões prontas ≤ 1.25 × a do `k2` |
| **Harness** | ordem por tarefas prontas somando os 2 pesos (de 28); empate em 1 tarefa: menor mediana de `wall_s` das sessões prontas |
| **Válido** | o `k2` fecha pelo menos 1 tarefa difícil em algum harness; senão as tarefas difíceis não separam nada e a página diz isso |

Se a matriz encolher (um harness sai no preflight), a tolerância da regra "Reserva" fica proporcional: 5% das sessões por peso, arredondado para cima. A regra "Harness" usa o total que sobrar.

Com 2 repetições, uma diferença de 1 tarefa entre dois harnesses não dá veredito. A página de resultado diz isso ao lado da tabela.

### Resultado

- `bench/harness-delivery-2026-11/results/summary.md`: tabela harness × peso (prontas, mediana de tempo), tabela por tarefa, motivos de falha, veredito das 3 regras.
- `bench/harness-matrix/results/<harness>/<modelo>.md`: um veredito por par, no formato que o `bench/harness-matrix/plan.md` define.
- Sem página nova em `reports/` nesta campanha.

## Restrições

- Layout e fronteira de `results/` e `logs/` do [AGENTS.md](../../../AGENTS.md).
- Nenhum texto de sessão no git.
- Nenhum `git pull` no rig enquanto uma fila roda.
- TDD para o código novo: checks, adaptadores de harness, fila, resumo.
- Sem push, PR ou merge sem pedido do usuário.

## Preflight obrigatório antes da fila

1. O Splash do rig responde em `127.0.0.1`, nas APIs `/v1/chat/completions` e `/v1/messages`.
2. Cada harness fecha a tarefa b em modo não interativo contra o `k2`, uma vez. Esse smoke não conta na matriz.
3. Cada harness sai com código de erro quando o servidor está fora, em vez de esperar para sempre.
4. O check de T1, T5 e T7 passa com a solução de referência e falha com o fixture intacto e com cada trapaça listada.

Se um harness falhar no item 2 ou 3 e a causa não tiver correção em 1 h de trabalho, ele sai da matriz e a página registra o motivo.

## O que fica com quem constrói

- A forma do adaptador por harness e dos arquivos de configuração temporários.
- Como obter `turns` e tokens de cada harness (saída JSON do harness, log do Splash, ou o proxy `request_log.py`).
- A solução de referência de T1, T5 e T7 usada pelos testes do check.
- O ambiente Python de T5 (`make venv` precisa de rede para o `pip`).
- O nome dos arquivos em `results/` e o formato do `summary.md`.

## Não verificado

- O `dsh` e o `pi` em modo não interativo contra o Splash 1.6.1.
- Uma sessão real de cada harness dentro do sandbox.
- Se os 4 harnesses aceitam o mesmo esforço de raciocínio.
- A duração real de uma sessão por harness.
