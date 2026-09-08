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
