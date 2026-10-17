# 2026-10-12: Flash-Next testa runtime e agente antes de pesos novos

Os próximos testes do Qwen3.8-Flash-Next no rig devem começar pelo que não exige download. O primeiro é o mlx-serve 26.10.2-pre-release.1 com o driver secundário (ddalcu iQ-MLX-4.7bpw, `n2`), que tem a maior base de medições no repo. O segundo é o Swift 1.5 a 256K e 512K, que o repo nunca mediu. O terceiro é uma bateria agêntica curta sobre falhas que terceiros relatam em hardware igual ao nosso. Terminal-Bench continua sendo o gate decisivo para o papel de agente, mas fica adiado: depende de uma segunda máquina com Docker. Só depois vale gastar disco com pesos. O candidato de pesos mais forte mudou em 11/10: o Jundot reenviou o próprio `oQ4e-mtp` com o refit do oQe (`c4ddfb5`, 106.3 GB). Isso torna obsoleta a reconversão local de ~354 GB prevista no item 4d. A Qwen não publicou checkpoint, template ou config novos desde 27/08 (**fabricante**), então nenhum teste precisa refazer o modelo base. O driver só troca pela regra já em uso: `T_turno ≤ 0.97 × T_turno(n2)` a 32K e 128K, onde a referência agora é o Swift 1.5 no mlx-serve 26.10.1 (7.9 s e 8.6 s, **medido-no-rig**).

**Decisão de 2026-10-12 (usuário).** Driver principal: Swift 1.5 (`w1`, `Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` `13839b7`). Driver secundário: ddalcu iQ-MLX-4.7bpw (`n2`, `dafff5c`, HEAD do repo no HF em 12/10). O teste #1 roda no `n2`. O teste #4 (Terminal-Bench) fica adiado. Os testes #6 e #7 ficam condicionados ao #5, como descrito abaixo.

**Procedência.** Este relatório junta quatro notas de pesquisa de 12/10: o estado do repo (leitura local), a documentação oficial da Qwen, runtimes e quants (GitHub e API do HF) e relatos da comunidade (Reddit, fórum NVIDIA). Cada número leva uma marca: **fabricante** (Qwen), **terceiro** (card no HF, blog, Reddit, PR ou issue do GitHub, doc de runtime) ou **medido-no-rig** (campanhas deste repo). Nenhum peso foi baixado e nenhum teste rodou para este relatório. A sessão que leu o repo não roda no rig, então o estado de disco vem dos documentos.

Notas anteriores da série: [qwen38-flashnext-derivatives-20261009.md](qwen38-flashnext-derivatives-20261009.md) e [references.md](../bench/qwen38-flash-next/references.md). Card do driver: [docs/models/qwen3.8-flash-next.md](../docs/models/qwen3.8-flash-next.md).

## O rig já mediu velocidade em sete pilhas, mas não mediu agente

O repo cobre bem velocidade e cache. Os testes abaixo **já foram feitos** e não entram no plano:

| Já medido | Resultado | Fonte |
|---|---|---|
| mlx-serve 26.9.2 × 26.10.1, mesmo pack | T_turno 0.73× (aceitação MTP 0.50 → 0.81 a 32K) | [summary.md](../bench/qwen38-flashnext-updates-2026-10/results/summary.md) |
| ddalcu mixed-4/8 × iQ-MLX-4.7bpw | paridade ±1% | idem |
| iQ (`n2`) × Swift 1.5 (`w1`), com `reasoning_effort` xhigh | `w1` promovido em 11/10: 7.9 / 8.6 s, GPQA t1 em 0.35× do tempo | [swift15 summary](../bench/swift15-flashnext-2026-10/results/summary.md) |
| oMLX 0.6.4, 0.7.0.dev2, 0.7.0 com Jundot oQ4e antigo (`2615fc0`) | 0.7.0: 10.1 / 12.1 s (1.23× / 1.38× do iQ) | [flashnext-summary.md](../bench/engine-updates-2026-10/results/flashnext-summary.md) |
| MTPLX 2.11.2 e 2.12.2 | 2º só a 32K (1.07×), HTTP 507 a 256K | [etapa-g-page.md](../bench/engine-updates-2026-10/results/etapa-g-page.md) |
| ds4 upstream e fork | decode 53.5 tok/s a 32K, abaixo do gate 70 | idem |
| iQ a 256K e 512K (`--kv-quant 4` + YaRN 2.0) | 9.8 s e 13.0 s; livre mínimo 0.05 GB a 512K | [flashnext-summary.md](../bench/engine-updates-2026-10/results/flashnext-summary.md) |
| `--ple-gpu`, `--kv-quant 8/turbo4`, `--os-reserve-gib 2/4`, knobs do prefix cache, concorrência | recusado, mais lento, OOM, 16GB/100GB/64, MoE não faz batch | card e [references.md](../bench/qwen38-flash-next/references.md) |

Todos os números da tabela são **medido-no-rig**. Três lacunas sobram. Terminal-Bench nunca rodou em nenhum pack do Flash-Next. O Swift 1.5 não tem número acima de 128K. E as suítes de tool-calling (jdhodges, Veerman) rodaram sem reasoning efetivo: a mediana ficou em ~110 tokens por resposta (**medido-no-rig**, [swift15 summary](../bench/swift15-flashnext-2026-10/results/summary.md)). Fidelidade contra BF16 (KLD) também não existe no rig, porque o BF16 (~354 GB) não cabe em 128 GB.

## Desde 10/10, o que mudou foi runtime e quant, não o modelo

**A Qwen não mexeu no modelo.** O repo BF16 tem três commits, e o último (27/08) só altera CSS e um link do README (**fabricante**, [commits HF](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/commits/main)). O único artefato oficial novo é o FP8 (31/08), que não cabe no rig. A Qwen também não publicou RULER, needle ou MRCR a 262K ou 1M ([blog](https://www.alibabacloud.com/blog/qwen3-8-flash-next-a-new-architecture-towardsultimate-cost-efficiency_603501)). Qualidade em contexto longo, portanto, só se conhece medindo.

O card traz dois pontos que afetam o desenho dos testes (**fabricante**, [card HF](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)). O default de `reasoning_effort` é `xhigh`. O card avisa que effort menor pode **aumentar** a latência total em tarefas agênticas multi-turno. Um usuário no HF afirma que o default real do template é `medium` (**terceiro**, [HF #71](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/71)). O conflito se resolve lendo o `chat_template.jinja` local.

**Runtimes.** O mlx-serve publicou o **v26.10.2-pre-release.1** em 11/10 ([release](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.2-pre-release.1)). As notas declaram, sem número para M4 Max (**terceiro**): decode mais rápido do Flash-Next; fim da trava no primeiro prompt após carregar; carga nativa de packs oMLX (172 tok/s num M5 Ultra contra 133 no oMLX); llama.cpp 0.6.0 embutido para GGUF com MTP; "Qwen3.8 keeps its earlier reasoning"; e um corte de thinking repetitivo. O oMLX tem só o **0.7.1.dev1** (09/10). Ele traz o refit do oQe (#4385) e remove ~150 variáveis `OMLX_*`, entre elas `OMLX_MOE_EXPERT_OFFLOAD` ([release](https://github.com/jundot/omlx/releases/tag/v0.7.1.dev1)). O MTPLX não teve release depois do 2.12.2 (03/10). O mlx-lm ainda não suporta `qwen4_exp` (PR #1788 aberta).

**llama.cpp com MTP.** O primeiro build com a PR #29761 é o **b11330** (02/10). A release **v0.6.0** (05/10) consolida MTP `qwen4exp` e o mat-mul few-row em Metal ([v0.6.0](https://github.com/ggml-org/llama.cpp/releases/tag/v0.6.0)). O build útil para o rig é **≥ b11569**. Ele inclui as máscaras otimizadas (b11352), que corrigem a regressão de prefill longo, e o fix Metal de `mul_mat_id` com ids duplicados, que afeta MoE ([releases](https://github.com/ggml-org/llama.cpp/releases)). Ninguém publicou número de MTP `qwen4exp` em Apple Silicon. O ganho de 1.55× (28.36 → 43.88 tok/s) foi medido num DGX Spark (**terceiro**, [PR #29761](https://github.com/ggml-org/llama.cpp/pull/29761)). Em outro modelo (Qwen3.6-35B-A3B), o MTP em Metal caiu de 26.23 para 1.93 tok/s (**terceiro**, [issue #23011](https://github.com/ggml-org/llama.cpp/issues/23011)). A issue #30368 (12/10, M5 Max 128 GB) mostra que `draft-mtp` + `--kv-unified` + `--parallel >1` quebra todo request.

**Pesos.** O Jundot re-quantizou o `oQ4e-mtp` com refit em 11/10. O card declara 4.724 bpw e KLD contra BF16 de **0.0877 → 0.0776 em código (−11.6%)** e **0.1909 → 0.1713 em prosa (−10.2%)** (**terceiro**, [card](https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp)). É o único KLD do ecossistema MLX com método explícito. O umixer publicou o `oQ4e-mix6-mtp`: bordas, atenção, n-gram e MTP em 6-bit. Residente fica +5.8 GB sobre o oQ4e, com decode 84.4 contra 75.7 tok/s num M5 Max (**terceiro**, [card v1](https://huggingface.co/umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp)). A v2 (12/10) refaz o tronco com o oQ4e refit ([v2](https://huggingface.co/umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2)). O GBP-DE oQ5e (item 4a) não muda desde 08/09 e é anterior ao refit. O `GBP-DE/…-oQ4e-WLSRefit-MTP` ainda não tem safetensors. O scottlowry Swift oQ4e (item 4c) não muda desde 03/10.

**Falhas relatadas por terceiros, nenhuma com resposta da Qwen.** São quatro (**terceiro**):

- Alucinação depois de tool result: o modelo inventa tarefas e contradiz a saída do `ls`. Reportado num M5 Max 128 GB com Jundot oQ4e e oMLX, e persiste com MTP e prefix cache desligados ([HF #68](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/68)).
- Loop de contagem de caracteres no thinking: termina com `finish_reason: length` e content vazio. Reproduz em llama.cpp e vLLM ([issue #8](https://github.com/QwenLM/Qwen3.8-Flash-Next/issues/8)).
- Degeneração em "!!!!" a partir de ~140K em sessão agêntica (FP8/vLLM, [issue #12](https://github.com/QwenLM/Qwen3.8-Flash-Next/issues/12)).
- Troca de `reasoning_effort` no meio da sessão: muda o topo do prompt e invalida o KV inteiro ([HF #36](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/36)).

O Swift 1.5 economiza menos em `medium` do que em `xhigh`. A Ukisai declara GPQA −0.20 pt em xhigh e −2.62 pt em medium, e DeepSWE 1.1 cai de 54.87% para 48.97% (**terceiro**, [Ukisai](https://ukisai.com/swift-1-5-flash-next)). Para agentic coding, o DeepSWE pesa mais que o GPQA. É a razão para medir o Swift em harness antes de confiar nele como agente.

## Plano priorizado: oito testes ativos e um adiado, quatro sem download

As regras de gate valem para todo braço de velocidade. Elas vêm de [qwen38-flashnext-updates-2026-10/plan.md](../bench/qwen38-flashnext-updates-2026-10/plan.md) e [engine-updates-2026-10/plan.md](../bench/engine-updates-2026-10/plan.md):

- zero HTTP 4xx/5xx;
- needles corretas (truncado não é falha);
- hit ≥ 0.90 em `append` e `tool_turn`;
- swap Δ ≤ 0.5 GB;
- `[spec-stats]` presente no log.

O alerta de wired > 102 GB não é gate. A métrica é `T_turno = TTFT(tool_turn) + 512 / mediana(decode quente)`, com 3 reps a 32K e 128K. O driver troca só com `T_turno ≤ 0.97 × w1@26.10.1` nas duas bandas. Empate de ±3% mantém o incumbente. Regras marcadas como "proposta" são deste relatório e ainda não existem no repo.

| # | teste | pesos / runtime | download (GB) | o que mede | gate / regra de decisão | condição / custo |
|---|---|---|---:|---|---|---|
| 1 | Runtime novo com o driver secundário | `n2` (iQ `dafff5c`) / mlx-serve 26.10.2-pre-release.1 × 26.10.1 | ~0 (binário; tamanho não verificado) | T_turno, decode, aceitação MTP, TTFT frio e do 1º prompt pós-load, hit, wired a 32K/128K (gate) e 256K (informativo); variante do probe que reenvia o thinking anterior | gates padrão; adotar se `T_turno ≤ 0.97 ×` 26.10.1 nas duas bandas; ±3% mantém 26.10.1 (é prerelease); se adotar, smoke de gates do `w1` a 32K no runtime novo | instalação isolada em `~/.local/opt/qwen38/`; parar o driver; ~1 dia de rig (estimativa) |
| 2 | Swift 1.5 a 256K e 512K | `w1` / runtime vencedor do #1, perfil `serve-flashnext-daily-driver.sh 512k` | 0 | T_turno, cold TTFT, wired pico, livre mínimo, needles (13 registros) | gates padrão; se passar, o perfil 512k passa a usar `w1`; se falhar, o perfil 512k continua no iQ | ≥100 GB livres para `~/.mlx-serve/kv-cache`; cold 512K ~784 s por rep no iQ (**medido-no-rig**) |
| 3 | Bateria agêntica de regressão (sem Docker) | `w1` e `n2` (iQ `dafff5c`) / runtime do driver | 0 | contradição pós-tool, loop de contagem, degeneração ≥140K, sweep de effort (tempo total e acerto), custo de trocar effort, tool-calling com `reasoning_chars` | proposta: `w1` ≤ `n2` + 1 caso em 20 em loop e contradição; qualquer "!!!!" bloqueia sessão longa; effort default = o de menor tempo total com acerto ≥ xhigh − margem G1 | runner do submódulo ≥ `a4a95bb`; ~1 dia |
| 4 | Terminal-Bench 2.0 (**adiado**) | `w1` e `n2` / mlx-serve do driver | 0 no rig | taxa de sucesso em 89 tarefas | `w1` ≥ `n2` − margem; Flash-Next assume o papel de agente se superar 32.6% do `qwen3-coder-next` (**medido-no-rig**) | precisa de segunda máquina com Docker (`DOCKER_DEFAULT_PLATFORM=linux/amd64`) |
| 5 | Jundot oQ4e com refit | `c4ddfb5` × `2615fc0` / oMLX 0.7.1.dev1 isolado; `c4ddfb5` também no mlx-serve 26.10.2-pre | 106.3 | T_turno 32K/128K/256K, linha `Qwen4-Exp PLE forced to SSD`, bateria de qualidade da campanha Swift (t1), taxa de loop | vira pack padrão do oMLX se qualidade ≥ antigo − margem G1 e 256K sem swap (§11.5); vira driver só com `≤ 0.97 × w1` e G1 contra `w1` | depois de #1; migrar env `OMLX_*` para settings por modelo; conferir hash antes de qualquer hardlink |
| 6 | Swift 1.5 oQ4e (item 4c) | `scottlowry/…-oQ4e-mtp` `e8ed008` / oMLX ou mlx-serve 26.10.2 | 106.3 | T_turno e tempo até resposta final contra `w1` | proposta: rodar só se #5 mostrar pack oMLX no mlx-serve a ≤ 1.03× do `w1`; promover só com `≤ 0.97 × w1` | condição escrita ("se 4b ganhar") já atingida; pack anterior ao refit |
| 7 | Mix6 v2 contra oQ4e refit | `umixer/…-mix6-mtp-v2` / oMLX 0.7.1 | ~125 (v1 = 125.3; v2 não verificado) | qualidade da bateria t1, loops, wired a 256K | proposta: substitui o refit como pack padrão do oMLX se superar o refit além da margem G1 com swap Δ 0 a 256K | depois de #5; substitui 4a (GBP-DE oQ5e) e 4e (txgsync) |
| 8 | GGUF com MTP no Metal | `ggml-org` IQ4_NL (102.0) + `mtp-…-Q8_0.gguf` (4.1) / llama.cpp ≥ b11569 e mlx-serve 26.10.2 (llama.cpp 0.6.0) | ~106 | decode com e sem `--spec-type draft-mtp` a 32K; depois T_turno 32K/128K | smoke: decode ≥ 70 tok/s a 32K (gate do ds4), senão encerra; candidato a driver só com `≤ 0.97 × w1` | `--parallel 1`, sem `--kv-unified` (#30368); apagar os pesos se o smoke falhar |
| 9 | `--ple-gpu` com prefix cache menor | `w1` / mlx-serve do driver | 0 | se a tabela n-gram vai para a GPU; decode a 128K | regra do repo: ≥ 5% de ganho a 128K, swap ≤ 0.5 GB, nenhum cenário recusado | precisa de braço controle com o mesmo `--prefix-cache-mem` sem `--ple-gpu` |

### 1. mlx-serve 26.10.2-pre: o teste mais barato com chance de trocar o runtime

O 26.10.1 trouxe 0.73× de T_turno sobre o 26.9.2 com os mesmos pesos (**medido-no-rig**). Uma troca de runtime já moveu o driver mais do que qualquer troca de pack. As notas do 26.10.2-pre prometem decode mais rápido no Flash-Next (**terceiro**). O teste usa os pesos que já estão em disco.

O teste roda no driver secundário `n2` (iQ `dafff5c`), e não no Swift. Motivo: o iQ tem a série mais longa de medições no repo (26.9.2, 26.10.1, 256K, 512K, HumanEval, tool-calling), então um desvio do runtime novo aparece contra uma base conhecida. O Swift só tem uma campanha. A referência do `n2` no 26.10.1 é 8.1 / 8.9 s a 32K / 128K (re-medida em 11/10, **medido-no-rig**).

**Braços.** Referência: `n2@26.10.1`, rodada de novo na mesma sessão como controle. Candidato: `n2@26.10.2-pre` com o comando de lançamento idêntico. A ordem das bandas alterna: a 32K roda ref → cand, a 128K roda cand → ref. São 10 min ociosos entre bandas, GPU < 50 °C e ≥ 82 GB livres antes de subir.

**Métricas extras.** A primeira é o TTFT do primeiro prompt após load, porque as notas dizem que ele "no longer stalls". A segunda é uma variante do `cache_probe.py` que **reenvia o thinking anterior** no `tool_turn`. O motivo: o 26.10.2 declara "Qwen3.8 keeps its earlier reasoning", e o card da Qwen usa `preserve_thinking=True` por default (**fabricante**). O probe atual não reenvia thinking, então mede um prefixo que um harness real não produz. Se `--help` expuser um limite de profundidade do MTP ("MTP depth bounds"), vale varrer 1/2/3 a 32K. Os runtimes de NVIDIA usam 3 draft tokens (**terceiro**, [vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next), [TRT-LLM](https://nvidia.github.io/TensorRT-LLM/latest/deployment-guide/deployment-guide-for-qwen3.8-flash-next-on-trtllm.html)).

**Decisão.** A regra do repo para runtime é `≤ 1.03 ×`. Para uma prerelease, este relatório propõe exigir ganho: adotar só com `≤ 0.97 ×` nas duas bandas e todos os gates. Empate mantém o 26.10.1 até a release estável. Se o 26.10.2-pre for adotado, o `w1` faz um smoke de gates a 32K e 128K no runtime novo antes de o driver principal migrar.

### 2. Swift 1.5 acima de 128K: lacuna do driver, sem download

O card diz "512K with Swift 1.5 is not measured". O iQ a 512K já opera no limite: wired pico 113.9 GB e livre mínimo 0.05 GB (**medido-no-rig**). O Swift tem wired 0.5 GB maior que o iQ a 128K (111.17 contra 110.64 GB, **medido-no-rig**). O risco de recusa ou OOM a 512K é real. O teste roda no runtime vencedor do #1, com 3 reps a 256K e 512K. A comparação usa os números já medidos do iQ (9.8 s a 256K; 13.0 s a 512K), sem repetir o iQ. As needles continuam sendo a única checagem de qualidade do KV4. A Qwen não publica qualidade em contexto longo, e o card avisa que YaRN estático degrada texto curto (**fabricante**). Por isso o perfil 512k deve continuar separado do diário.

### 3. Bateria agêntica: medir no rig as falhas que terceiros relatam

Este teste fecha a maior parte da lacuna de agente sem Docker. Cada probe vem de uma falha relatada:

| Probe | Origem | Fixture | Métrica |
|---|---|---|---|
| 3a. contradição pós-tool | [HF #68](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/68) | 20 turnos com tool result conhecido (lista de arquivos, saída de teste) | resposta ou reasoning contradiz o tool result; tarefa inventada; turno vazio ([HF #50](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions)) |
| 3b. loop de contagem | [issue #8](https://github.com/QwenLM/Qwen3.8-Flash-Next/issues/8) | 20 prompts "about N characters" (pt, en, ko) | `finish_reason=length` com content vazio; tokens até a resposta |
| 3c. degeneração longa | [issue #12](https://github.com/QwenLM/Qwen3.8-Flash-Next/issues/12) | sessão multi-turno sintética até 150K e 200K com tool results | sequência de caractere repetido; resposta incoerente |
| 3d. sweep de effort | card (**fabricante**) e [Ukisai](https://ukisai.com/swift-1-5-flash-next) | tarefa multi-turno fixa + GPQA 50 e LCB 50 (seed 42) em `xhigh`, `medium`, `low` | tempo total da tarefa; acertos; tokens de reasoning |
| 3e. custo de trocar effort | [HF #36](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/36) | sessão a 128K que troca effort no meio | TTFT e hit após a troca |
| 3f. tool-calling com reasoning | lacuna da campanha Swift | jdhodges 40 e Veerman 12 com `reasoning_effort` explícito | acertos e `reasoning_chars` (não `n/d`) |

Os probes 3a, 3b, 3c e 3f rodam em `w1` e `n2`. O 3d e o 3e rodam só em `w1`. O sampling é o do vendor para thinking: temp 1.0, top_p 0.95, top_k 20, presence 0 (**fabricante**). São no mínimo 2 rodadas por braço, porque a campanha Swift usou 1 rodada e deixou empates de 1 a 3 questões sem resolver.

As regras de decisão são propostas. Primeira: se `w1` exceder `n2` em mais de 1 caso em 20 de loop ou contradição, o driver volta a ser candidato a revisão. Segunda: qualquer degeneração em "!!!!" bloqueia o uso em sessão longa até haver fix de runtime. Terceira: o effort default do harness passa a ser o de menor tempo total cujo acerto fica dentro da margem G1 do `xhigh`. O resultado do 3e define se o harness deve fixar o effort por sessão.

### 4. Terminal-Bench: continua o gate do papel de agente (adiado)

Adiado por decisão de 12/10, até haver a segunda máquina. O script existe: `bench/terminal-bench/scripts/run-tbench-flashnext.sh <n2|w1>` (Terminal-Bench 2.0, 89 tarefas, terminus-2 0.8.0). Falta a segunda máquina com Docker. A referência local é o `qwen3-coder-next` com 32.6% (**medido-no-rig**, [docs/local-llm-reference.md](../docs/local-llm-reference.md)). A Ukisai declara Terminal-Bench 2.1 de 67.64% (base BF16) e 69.66% (Swift) (**terceiro**). A versão e o harness diferem dos nossos, então o número não serve de referência. Este teste vem depois do #3 porque depende de infraestrutura. Ele continua sendo o único resultado que decide se o Flash-Next substitui o `qwen3-coder-next` como agente.

### 5. Jundot oQ4e com refit substitui a reconversão local do item 4d

O item 4d previa baixar o BF16 (~354 GB) e reconverter com oMLX 0.7.1. O Jundot fez isso e publicou o resultado com KLD medido contra BF16 (**terceiro**). O teste custa um download de 106.3 GB.

Há duas perguntas. A primeira é se o refit melhora a qualidade no mesmo runtime: braço `o1` (`2615fc0`, ainda em disco) contra `o1r` (`c4ddfb5`), ambos no oMLX 0.7.1.dev1 isolado ou num build do `main` posterior. O `main` já inclui #4070 (QSA batched decode/verify), #4410 e #4443. A segunda é se o pack oMLX roda mais rápido no mlx-serve 26.10.2, que agora carrega packs oMLX nativamente: braço `o1r@mlx-serve` contra `w1`.

O mantenedor do oMLX diz que o oQ4e de ~99 GB "may move the ~30GB PLE table to SSD" num Mac de 128 GB (**terceiro**, [issue #4429](https://github.com/jundot/omlx/issues/4429)). Cada run no oMLX deve registrar se a linha `Qwen4-Exp PLE forced to SSD` aparece no `server.log`. Sem isso, a diferença de memória confunde qualquer comparação. A mesma issue foi aberta num M4 Max 128 GB e alega +23% de decode trocando `_IMPL` para `blocked_seq`. O mantenedor contesta e pediu microbenchmark no M4 Max. O rig pode rodar esse microbenchmark como subproduto, sem decisão associada.

A qualidade usa a bateria t1 da campanha Swift (HumanEval 164, GPQA 50, LCB 50, IF 20), tool-calling com reasoning e a taxa de loop de [bench/degeneration](../bench/degeneration/plan-quant-validation.md). O antigo e o refit têm o mesmo tamanho e o mesmo quantizador, então a regra de pesos do repo vale para velocidade: `|r−1| ≤ 0.03`.

### 6 a 9. Testes condicionais

**#6, Swift oQ4e no oMLX (4c).** A condição escrita em [references.md](../bench/qwen38-flash-next/references.md) ("testar só se 4b ganhar") foi atingida em 11/10. O teste só tem valor se um pack oMLX puder competir em velocidade com o `w1`. O oMLX 0.7.0 ficou em 1.23× e 1.38× (**medido-no-rig**). Além disso, o pack `e8ed008` é anterior ao refit. Por isso o teste fica condicionado ao #5.

**#7, mix6 v2.** A comunidade relata que o mix6 supera o oQ5e com ~9 GB a menos (**terceiro**, [r/oMLX](https://www.reddit.com/r/oMLX/comments/1x2yu8o/built_a_ushaped_mixedprecision_pack/)). Ninguém mediu isso na mesma bateria, e o autor admite não ter KLD. O oQ5e tem relatos de recusa de carga no oMLX 0.7.x num M4 Max 128 GB ([issue #4349](https://github.com/jundot/omlx/issues/4349)). O mix6 v2 substitui o GBP-DE oQ5e (4a) e o txgsync (4e) como aposta de qualidade acima de 4 bpw.

**#8, GGUF com MTP.** É a primeira medição de llama.cpp do Flash-Next no rig. O pack sugerido é o `ggml-org` IQ4_NL (102.0 GB) com a cabeça MTP Q8_0 (4.1 GB). É o pack usado nos benchmarks das PRs upstream: a PR #29824 mediu TG de 31.9 a 32.1 tok/s com N_KV 65K num M2 Ultra (**terceiro**, [PR #29824](https://github.com/ggml-org/llama.cpp/pull/29824)). O smoke vem primeiro. O `references.md` registra ~36 tok/s sem MTP (**terceiro**), longe do decode de 84.6 do `w1` (**medido-no-rig**). O teste só segue se o MTP em Metal levar o decode a ≥ 70 tok/s a 32K. O 4f (GSQ-RCO IQ3_S, 83.6 GB) continua restrito ao caso em que a meta é memória.

**#9, `--ple-gpu`.** O log de 26.10.1 recusou a tabela por falta de 6.2 GB e cita `headroom 16 GB` (**medido-no-rig**, [etapa-p.md](../bench/qwen38-flashnext-updates-2026-10/results/etapa-p.md)). Se esse headroom for o prefix cache, `--prefix-cache-mem 8GB` admitiria a tabela. Um prefixo de 128K ocupa ~3.7 GB (**medido-no-rig**). O teste muda duas variáveis, então precisa do braço controle com 8 GB sem `--ple-gpu`. Ele vem por último porque a hipótese sobre o headroom não foi verificada no código.

## Fica fora do plano

Estes itens ficam fora, cada um por um motivo verificável:

- **MTPLX**: nenhuma release depois do 2.12.2 ([releases](https://github.com/youssofal/MTPLX/releases)).
- **Splash** (oMLX PR #4447): não serve o Flash-Next.
- **Ollama**: sem Flash-Next na biblioteca oficial, e falha ao importar GSQ-RCO ([issue #18817](https://github.com/ollama/ollama/issues/18817)).
- **mlx-lm**: sem suporte em release ([PR #1788](https://github.com/ml-explore/mlx-lm/pull/1788)).
- **LM Studio**: sem fonte primária.
- **Jundot oQ3.5e e oQ2.7e**: 3.990 e 3.305 bpw sem a tabela n-gram, abaixo da regra do repo de não descer de ~4 bpw.
- **oQ6e e oQ8e**: 150.6 e 194.9 GB, não cabem.
- **GBP-DE WLSRefit**: ainda sem pesos.
- **REAP, Coder-cut, Niwaki 141B, abliterated**: fora do papel de driver pela regra de 09/10.
- **INT8 activation prefill do oMLX**: exige tensor units do M5.
- **1M de contexto**: nenhum runtime MLX relatado; só o ds4, já reprovado no gate de decode.

## Correções de documentação que o repo precisa

1. [references.md](../bench/qwen38-flash-next/references.md), linha 5: o cabeçalho dizia "Driver do rig (2026-09-13): ddalcu mixed-4/8 no mlx-serve 26.9.2". **Corrigido em 12/10**: driver principal Swift 1.5 `13839b7`, driver secundário iQ `dafff5c`, ambos no mlx-serve 26.10.1.
2. [references.md](../bench/qwen38-flash-next/references.md), Próximos passos 4: o item **4b** aparecia pendente, mas foi executado em 11/10 e ganhou ([swift15 summary](../bench/swift15-flashnext-2026-10/results/summary.md)). A condição do **4c** foi atingida. O **4d** está obsoleto pelo `Jundot oQ4e @ c4ddfb5`. O **4a** e o **4e** apontam para o mix6 v2 como alternativa mais recente. **Corrigido em 12/10.**
3. [engine-updates-2026-10/plan.md](../bench/engine-updates-2026-10/plan.md) e [results/summary.md](../bench/engine-updates-2026-10/results/summary.md): o llama.cpp b11461 aparece como fora de escopo. O primeiro build com MTP `qwen4exp` é o b11330, e o mínimo recomendado para Metal é b11569 (teste #8). Não corrigido: são documentos de campanha fechada.
4. [docs/models/qwen3.8-flash-next.md](../docs/models/qwen3.8-flash-next.md), Known issues: dizia que o perfil 512k foi medido no 26.9.2 com mixed-4-8bit. A seção "Extended profile: 512K" do mesmo card cita o iQ no 26.10.1 em 11/10 (braço `n2q4`), e é esta a correta segundo [flashnext-summary.md](../bench/engine-updates-2026-10/results/flashnext-summary.md). **Corrigido em 12/10.**
5. [docs/models/qwen3.8-flash-next.md](../docs/models/qwen3.8-flash-next.md), Measured performance: dizia "256K and 512K were not re-measured on 26.10.1". O iQ foi medido a 256K (9.8 s) e 512K (13.0 s) no 26.10.1 ([etapa-g-page.md](../bench/engine-updates-2026-10/results/etapa-g-page.md)). **Corrigido em 12/10.** O card também passou a nomear o iQ como driver secundário, não só rollback.
6. [qwen38-flashnext-derivatives-20261009.md](qwen38-flashnext-derivatives-20261009.md) §11.5: o braço `s1` aparecia "opcional, depois da licença". A licença foi aprovada em 10/10, e o braço `o3` (reconversão) virou `Jundot oQ4e @ c4ddfb5`. **Corrigido em 12/10.**
7. Scripts de oMLX do rig: conferir se usam variáveis `OMLX_*` removidas no 0.7.1.dev1 antes do #5.
8. Default de `reasoning_effort`: conferir no `chat_template.jinja` local se é `xhigh` (card) ou `medium` (HF #71). Registrar o resultado no card do driver.

## O que não foi verificado

- **Estado do disco do rig.** A sessão que leu o repo não roda no rig. A conta "918 GiB livres em 10/10 menos 106.8 GB do Swift" vem dos documentos. Downloads de #5 a #8 somam ~444 GB e devem ser checados com `df` antes, conforme a regra do repo.
- **MTP do llama.cpp em Metal para o Flash-Next.** Não há número em fonte primária. Os únicos números são de DGX Spark e Strix Halo. Um resultado de busca sobre "1.77×" num M5 Max não teve o post original localizado.
- **Ganho do 26.10.2-pre num M4 Max.** As notas trazem números de M5 Ultra. Números de M5 não se transferem para o M4 Max, porque a NAX só existe no M5.
- **Flags do 26.10.2-pre.** Os nomes de flag de profundidade do MTP e do cache "SSD-only" não foram lidos no `--help`.
- **KLD do iQ e do Swift.** Não há KLD com método comparável ao do Jundot. Os KLDs do Jundot (0.0776 código) e da Unsloth (0.0836 UD-IQ4_XS) usam corpora e métodos diferentes e não se comparam.
- **Tamanho do mix6 v2** e KLD dos novos oQ3.5e/2.7e/6e/8e: não estavam publicados na coleta.
- **Cobertura do Reddit.** O MCP do Reddit não tem busca por texto. r/LocalLLaMA foi coberto só pelo top do mês. r/MacStudio, r/mlx e o HN não foram lidos. O corpo do post "Slipstream" não veio.
- **Blog qwen.ai.** É renderizado por JS. Este relatório usou a cópia da Alibaba Cloud, sem saber se o original foi editado.
- **Hipótese do `headroom 16 GB`** do `--ple-gpu`: não conferida no código do mlx-serve.
- **Custo em horas** dos testes 1 e 3: estimativa deste relatório, não medição.

## Conclusão

O gargalo do Flash-Next no rig deixou de ser velocidade. Sete pilhas e quatro packs já foram medidos, e a última troca de driver (11/10) ganhou por tokens de raciocínio, não por decode. O que falta é evidência de comportamento agêntico. Terceiros reportam falhas desse tipo em hardware quase idêntico, e o modelo base não recebe correção da Qwen desde agosto. Os testes 1 a 3 cabem no disco atual e respondem às duas perguntas que ainda movem decisão: se o runtime novo baixa o T_turno do driver secundário e se o Swift se comporta em sessão longa e em tool calls tão bem quanto o iQ. Desde 12/10 o repo nomeia os dois drivers: Swift 1.5 é o principal e o iQ do ddalcu é o secundário.

A segunda conclusão é sobre pesos. O refit do Jundot e a carga nativa de packs oMLX no mlx-serve 26.10.2 eliminam a separação "pack oMLX só no oMLX". Isso permite, pela primeira vez, comparar o melhor KLD declarado do ecossistema MLX com o driver no mesmo runtime. Se o #5 mostrar `o1r@mlx-serve` dentro de 0.97× do `w1` com qualidade igual, o repo passa a ter um driver base com fidelidade documentada. O Swift fica como opção para tarefas de raciocínio, onde sua economia de tokens já foi medida.

## Fontes

Repositório (caminhos relativos):

- [docs/models/qwen3.8-flash-next.md](../docs/models/qwen3.8-flash-next.md)
- [bench/qwen38-flash-next/references.md](../bench/qwen38-flash-next/references.md)
- [research/qwen38-flashnext-derivatives-20261009.md](qwen38-flashnext-derivatives-20261009.md)
- [bench/swift15-flashnext-2026-10/results/summary.md](../bench/swift15-flashnext-2026-10/results/summary.md) e [plan.md](../bench/swift15-flashnext-2026-10/plan.md)
- [bench/engine-updates-2026-10/results/flashnext-summary.md](../bench/engine-updates-2026-10/results/flashnext-summary.md), [etapa-g-page.md](../bench/engine-updates-2026-10/results/etapa-g-page.md), [plan.md](../bench/engine-updates-2026-10/plan.md)
- [bench/qwen38-flashnext-updates-2026-10/results/summary.md](../bench/qwen38-flashnext-updates-2026-10/results/summary.md), [etapa-p.md](../bench/qwen38-flashnext-updates-2026-10/results/etapa-p.md), [plan.md](../bench/qwen38-flashnext-updates-2026-10/plan.md)
- [bench/degeneration/plan-quant-validation.md](../bench/degeneration/plan-quant-validation.md)
- [docs/local-llm-reference.md](../docs/local-llm-reference.md)

Fabricante (Qwen):

- https://huggingface.co/Qwen/Qwen3.8-Flash-Next
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/commits/main
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next-FP8
- https://huggingface.co/Qwen
- https://github.com/QwenLM/Qwen3.8-Flash-Next
- https://www.alibabacloud.com/blog/qwen3-8-flash-next-a-new-architecture-towardsultimate-cost-efficiency_603501

Terceiro: docs de runtime, releases, PRs e issues:

- https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next
- https://nvidia.github.io/TensorRT-LLM/latest/deployment-guide/deployment-guide-for-qwen3.8-flash-next-on-trtllm.html
- https://docs.nvidia.com/dynamo/dev/recipes/qwen-3-8-flash-next
- https://github.com/ddalcu/mlx-serve/releases
- https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.2-pre-release.1
- https://github.com/jundot/omlx/releases
- https://github.com/jundot/omlx/releases/tag/v0.7.1.dev1
- https://github.com/jundot/omlx/pull/4385
- https://github.com/jundot/omlx/issues/4429
- https://github.com/jundot/omlx/issues/4349
- https://github.com/jundot/omlx/pulls?q=is%3Apr+is%3Amerged
- https://github.com/ggml-org/llama.cpp/pull/29761
- https://github.com/ggml-org/llama.cpp/pull/29824
- https://github.com/ggml-org/llama.cpp/releases
- https://github.com/ggml-org/llama.cpp/releases/tag/b11330
- https://github.com/ggml-org/llama.cpp/releases/tag/v0.6.0
- https://github.com/ggml-org/llama.cpp/issues/30368
- https://github.com/ggml-org/llama.cpp/issues/23011
- https://github.com/youssofal/MTPLX/releases
- https://github.com/ml-explore/mlx/releases/tag/v0.32.3
- https://github.com/ml-explore/mlx-lm/pull/1788
- https://github.com/ollama/ollama/issues/18817
- https://github.com/QwenLM/Qwen3.8-Flash-Next/issues/8
- https://github.com/QwenLM/Qwen3.8-Flash-Next/issues/12
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/36
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/68
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/71

Terceiro: pesos e cards:

- https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp
- https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp/commits/main
- https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ3.5e-mtp
- https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ6e-mtp
- https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ8e-mtp
- https://huggingface.co/umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp
- https://huggingface.co/umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2
- https://huggingface.co/GBP-DE/Qwen3.8-Flash-Next-oQ5e-mtp
- https://huggingface.co/GBP-DE/Qwen3.8-Flash-Next-oQ4e-WLSRefit-MTP
- https://huggingface.co/txgsync/Qwen3.8-Flash-Next-Dynamic-oQ5e-BF16-PLE-mtp
- https://huggingface.co/scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp
- https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw
- https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw
- https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF
- https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF
- https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF
- https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next
- https://unsloth.ai/docs/models/qwen3.8-next
- https://ukisai.com/swift-1-5-flash-next

Terceiro: comunidade:

- https://www.reddit.com/r/oMLX/comments/1x2yu8o/built_a_ushaped_mixedprecision_pack/
- https://www.reddit.com/r/oMLX/comments/1x2eoo6/omlx_071dev1_improved_oq_quantization_qwen/
- https://www.reddit.com/r/oMLX/comments/1x3d7f8/jundot_has_been_reuploading_quants_using_improved/
- https://www.reddit.com/r/oMLX/comments/1x28gwx/omlx_071dev1_vs_070_qwen38flashnext_oq4e_oq6e_and/
- https://www.reddit.com/r/oMLX/comments/1wqkqeu/qwen38_flash_next_with_omlx_pi_for_longrunning/
- https://www.reddit.com/r/oMLX/comments/1wp8mvi/i_do_not_get_the_love_for_qwen38flashnext/
- https://www.reddit.com/r/oMLX/comments/1ws1zlm/oq4e_quantization_of_qwen_flash_next_swift_edition/
- https://forums.developer.nvidia.com/t/swift-1-5-qwen3-8-flash-next-63-4-fewer-thinking-tokens/384473
