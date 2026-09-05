# Templates de desafio

Cada arquivo é um template com quatro blocos fixos: **Prompt** (cole sem alterar),
**Verificação** (comandos que decidem `pass`/`fail`), **Follow-up** (a única mensagem de
correção permitida) e **Rubrica** (o que observar para as colunas `q_*`).

| ID | Nome | Fixture | Mede | Time-box |
|---|---|---|---|---|
| [T1](T1-bugfix.md) | Bugfix com testes falhando | `ledger` | leitura de código, disciplina de testes | 15 min |
| [T2](T2-feature.md) | Feature em código existente | `ledger` | escopo, testes novos, CLI | 20 min |
| [T3](T3-greenfield.md) | App do zero (task manager) | nenhum | escolha de stack, primeiro run correto | 25 min |
| [T4](T4-refactor.md) | Refactor multi-arquivo sem mudar comportamento | `ledger` | edição em vários arquivos, testes verdes | 25 min |
| [T5](T5-env-repair.md) | Consertar ambiente e deixar `make check` verde | `envfail` | feedback do ambiente, shell, diagnóstico | 20 min |
| [T6](T6-long-context.md) | Revisão de repositório grande | repo do usuário | contexto longo, alucinação | 30 min |
| [T7](T7-chain.md) | Cadeia de 5 subtarefas com checklist | `ledger` | "declara done" cedo, persistência | 30 min |

O brief ao modelo está em inglês para bater com o idioma dos dados de treino de agente.
As instruções ao executor estão em português.
