# Splash até 1M — runbook de velocidade, qualidade e relatórios

> **Status (2026-10-24): pronto para executar.** Branch `bench/splash-longctx-2026-10`, criada sobre `flashnext/daily-256k` (PR #71). Depois do merge do #71, fazer rebase na `main`.
>
> **Para agentes:** use superpowers:executing-plans. Execute as tasks em ordem, sem pedir confirmação entre elas. Marque cada step (`- [ ]` → `- [x]`). Pare só nas condições de parada da seção "Execução autônoma".

**Objetivo:** medir velocidade, cache e qualidade do Splash 1.4.0 com o Swift 1.5, com o Flash-Next base e com o GSQ-RCO-Coder, de 8K até 1M tokens. A campanha termina com:
- os parâmetros aceitáveis para 512K e para 1M;
- os relatórios públicos atualizados;
- o Terminal-Bench 2.1 dos candidatos.

**Pedido (usuário, 24/10), que serve de spec deste plano:**
1. Testar velocidade e desempenho do Splash com o Swift e com o Flash-Next, e atualizar os relatórios de velocidade e desempenho até 1M, com cache e tempos: [m4max-guide](https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-m4max-guide.html) e [perf-lines](https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-perf-lines.html).
2. Rodar de forma autônoma.
3. Determinar os parâmetros para rodar 512K, e depois 1M, com qualidade e velocidade aceitáveis.
4. Medir a qualidade do Splash com o Swift com testes leves, até o Terminal-Bench 2.1.
5. Fazer os mesmos testes com o GSQ-RCO-Coder no Splash. Se o Splash não carregar o modelo, usar o mlx-serve.

| pergunta | braços | task |
|---|---|---|
| Como o `T_turno`, o cache e o prefill do Splash crescem de 8K a 1M? | `k1a`, `k2a`, `k3a` × `w1z` | 1, 2, 3 |
| Que parâmetros do Splash dão 512K e 1M com folga de memória? | `k2a`, `k2ab`, `k2as` | 2, 3 |
| O YaRN do Splash a 512K e a 1M mantém a qualidade do contexto nativo? | `k2a` (e `k3a`) em 262144, 524288 e 1000000 | 4 |
| O Splash com o Swift passa no Terminal-Bench 2.1 como o `w1z`? | `k2a` × `w1z` × `k3a` | 6 |

**Arquitetura:**
- A campanha reusa o `run-candidate.sh` de [bench/qwen38-flashnext-daily-driver-2026-09](../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh), o `cache_probe.py`, o `toolcall-probe.sh` de [stack-updates](../stack-updates-2026-10/scripts/toolcall-probe.sh), e o `run-battery.sh`, `decide.py`, `fetch_pack.py` e `idle-gate.sh` de [flashnext-next-steps](../flashnext-next-steps-2026-10/plan.md).
- Código novo:
  - um probe de contexto longo (`longctx_probe.py`);
  - um runner do Terminal-Bench que roda no MacBook e aponta para o rig;
  - um launcher do Splash com perfis 256k, 512k e 1m.
- Os relatórios saem do `consolidate_reports.py --profile 2026-10`, que passa a ler os resultados desta campanha.

## Restrições globais

As restrições de [bench/flashnext-next-steps-2026-10/plan.md](../flashnext-next-steps-2026-10/plan.md#global-constraints) valem aqui: rig, métrica `T_turno`, sampling (`temperature 1.0`, `top_p 0.95`, `top_k 20`, reasoning `xhigh`), protocolo térmico, reserva de disco, idioma e testes. As diferenças:

- **Runtimes:**
  - Splash 1.4.0 (`~/.local/opt/qwen38/splash-v1.4.0/bin/splash`);
  - mlx-serve 26.10.3 (`~/.local/opt/qwen38/mlx-serve-v26.10.3/mlx-serve`).
  - Não instalar outra versão no meio da campanha.
- **Bandas:**

  | banda | tokens | reps |
  |---|---|---|
  | 8K | 8192 | 3 |
  | 32K | 32768 | 3 |
  | 128K | 131072 | 3 |
  | 256K | 262144 | 3 |
  | 512K | 524288 | 3 |
  | 1M | 1000000 | 1, e 2 no braço escolhido |

- **Limite de 1M.** O Splash aceita `--max-context` até 1010000. A banda "1M" usa 1000000 tokens em todos os braços, e os relatórios a rotulam "1M".
- **YaRN.** Acima de 262144, o Splash liga YaRN sozinho. O YaRN é estático: muda as respostas em qualquer comprimento. Por isso, a qualidade de 512K e de 1M roda no servidor subido com aquele `--max-context`.
- **Gates de velocidade** (iguais aos das campanhas anteriores):
  - swap Δ ≤ 0.5 GB;
  - cache hit ≥ 0.90;
  - needles corretos;
  - 0 erros HTTP.
- **Gate de folga, novo.** O livre mínimo do `*-mem.jsonl` deve ficar ≥ 2 GB. Um braço que passa nos outros gates, mas não neste, é registrado como "passa, sem folga".
- **Aceitável a 512K e a 1M**, usado nos Tasks 2, 3 e 7:
  - todos os gates de velocidade e o gate de folga passam;
  - `T_turno` ≤ 13.3 s, o `w1q4` a 512K medido em [etapa2-swift-long](../flashnext-next-steps-2026-10/results/etapa2-swift-long.md);
  - G1 do `summarize_ab.py` passa contra o mesmo braço a 262144;
  - o `longctx_probe` acerta ≥ 80% e fica no máximo 15 pontos abaixo do mesmo braço a 262144.
- **Sem persistência de cache.** Nada de `--persistent-cache`. O cold de cada rep precisa ser cold.
- **Commits:** prefixo `bench(splash-longctx): ...`, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push só no Task 9.

## Review Focus

1. **Prompt maior que o contexto.** A 1000000, o `cache_probe` e o `longctx_probe` precisam deixar espaço para a saída. Teste: o prompt gerado tem ≤ `ctx − 8192` tokens.
2. **Splash recusa o boot a 512K ou 1M** por falta de memória. A fila registra a recusa, com a mensagem do plano de memória, e segue para o próximo braço. Teste: `--print` do braço `k2as` mostra `--state-format bf16`.
3. **Splash recusa o GGUF do GSQ-RCO-Coder.** A 1.4.0 recusa com `GGUF metadata does not match the target: expert_count 256 (expected 512)` ([#527](https://github.com/incoai/splash/issues/527)). A correção ([#561](https://github.com/incoai/splash/pull/561)) entrou no `main` em 23/10 e ainda não saiu numa release. O Task 5 assume no mlx-serve, e o Task 5b roda o `k3` numa release nova, se ela sair. Teste: o smoke do Task 0 grava `results/etapa0-k3-load.md` com "carrega" ou "recusa" e a mensagem do Splash.
4. **Laptop dorme ou o Docker para** no meio do Terminal-Bench. O runner usa `caffeinate -i`, e um job parado volta com `harbor job resume`. Teste: `--print` do runner mostra `caffeinate -i harbor run`.
5. **Tool call cortada pelo `max_tokens`.** O Task 10 da stack-updates mostrou falhas com `finish_reason: length` a 512 tokens. O probe ganha `--max-tokens`. Teste: o payload carrega o valor passado.

## Execução autônoma

- **Onde rodar.** Velocidade e qualidade rodam no rig: `ssh vitor@100.110.87.118`, porque o nome `mac-studio` pode não resolver. O checkout fica em `~/LocalProjects/macstudio-local-llm`. O Terminal-Bench roda neste MacBook (24 GB, Docker 29.6, harbor) contra o rig.
- **Código.** Commit no laptop. Leve o commit ao rig com `git bundle`, porque o rig não puxa da `origin` sem push: `git bundle create`, `scp` e `git pull --ff-only <bundle> bench/splash-longctx-2026-10`.
- **Filas.** Cada fila roda com `nohup bash logs/chain-tN.sh > logs/chain-tN.log 2>&1 &`. A fila para o driver diário no início e o religa no fim, como o `chain-t10.sh` da stack-updates.
- **Falhas.** Um braço que falha não para a fila. Registre o erro no `etapa<N>` e siga.
- **Pare e espere o usuário só se:**
  1. o disco livre ficar abaixo de download + 150 GB;
  2. swap Δ > 2 GB ou kernel panic;
  3. o driver diário não voltar no fim de uma fila;
  4. o Terminal-Bench falhar duas vezes seguidas por causa do Docker ou da rede.
- **Commit no fim de cada task**, com os `results/` daquela task.

## Mapa de arquivos

| arquivo | ação | responsabilidade |
|---|---|---|
| `bench/splash-longctx-2026-10/plan.md` | Create | este runbook |
| `bench/splash-longctx-2026-10/scripts/run-arm.sh`, `run-seq.sh` | Create (Task 0) | cópias dos da stack-updates, com `HERE` nesta campanha |
| `bench/splash-longctx-2026-10/scripts/longctx_probe.py` | Create (Task 0) | perguntas de busca, soma e dois saltos sobre um haystack de N tokens |
| `bench/splash-longctx-2026-10/scripts/run-tbench-remote.sh` | Create (Task 0) | roda no laptop: harbor + Terminal-Bench 2.1 contra um braço no rig |
| `bench/splash-longctx-2026-10/scripts/hold-arm.sh` | Create (Task 0) | roda no rig: sobe um braço e o mantém até existir um arquivo-flag |
| `bench/splash-longctx-2026-10/tests/test_campaign.py` | Create (Task 0) | `--print` dos braços novos, do runner e do probe |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify (Task 0) | braços `k3 k3a k3ab k2as w1zq4 r1zy` |
| `bench/qwen3.8-prefix-cache/scripts/tool_loop.py` | Modify (Task 0) | flag `--max-tokens` (default 512) |
| `bench/stack-updates-2026-10/scripts/toolcall-probe.sh` | Modify (Task 0) | repassa `--max-tokens` |
| `tools/scripts/serve-flashnext-splash.sh` | Create (Task 7) | launcher do Splash com os perfis 256k, 512k e 1m |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/consolidate_reports.py` | Modify (Task 8) | lê esta campanha; séries Splash; banda de 1M |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py`, `render_m4max_guide.py` | Modify (Task 8) | coluna e linha de 1M; textos do Splash |
| `reports/qwen38-flashnext-perf-lines.html`, `reports/qwen38-flashnext-m4max-guide.html` | Regenerate (Task 8) | páginas públicas |

## Braços

| braço | pesos | runtime e flags | porta |
|---|---|---|---|
| `w1z` | Swift 1.5 MLX `13839b7` | mlx-serve 26.10.3, flags do driver diário | 11234 |
| `w1zq4` | igual ao `w1z` | o `w1q4` (YaRN 2 + KV 4-bit) com o binário 26.10.3 | 11234 |
| `k1a` | unsloth Flash-Next `UD-IQ4_XS` `766911a` | Splash 1.4.0, `--verify-rows auto` | 8585 |
| `k2a` | ukisai Swift 1.5 `IQ4_XS` `0142554` | Splash 1.4.0, `--verify-rows auto` | 8585 |
| `k2ab` | igual ao `k2a` | + `--kv-format bf16` (já existe) | 8585 |
| `k2as` | igual ao `k2a` | + `--state-format bf16` | 8585 |
| `k3`, `k3a`, `k3ab` | ISTA `Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF:IQ1_M` `bba8885` (58.4 GB, 256 de 512 experts) | como `k2`, `k2a`, `k2ab`; a 1.4.0 recusa (#527), então eles só rodam no Task 5b | 8585 |
| `r1zy` | mbrown-uno GSQ-RCO-Coder-MLX `50fa68c` | o `r1z` + YaRN + KV 4-bit (só no Task 5) | 11234 |

O draft DFlash2 que o Splash escolhe é o `incoai/Qwen3.8-Flash-Next-DFlash2` `a22a174`, que já está no cache do rig. Com `--offline`, ele não muda durante a campanha.

Os dados já medidos entram sem nova run:
- `k1a` e `k2a` a 32K e 128K (Tasks 5 e 8 da stack-updates);
- `w1z` a 32K, 128K e 256K (Task 1);
- `r1z` a 32K e 128K (Task 9).

---

### Task 0: Pré-voo, código e smoke

**Files:** todos os `Create (Task 0)` e `Modify (Task 0)` do mapa.

**Interfaces:**
- Produces:
  - braços `k3 k3a k3ab k2as w1zq4 r1zy` em `run-candidate.sh`;
  - `longctx_probe.py --base-url URL --model ID --context N --output PATH [--seed 0]`, que grava uma linha JSON por pergunta e uma linha `verdict` com `accuracy` e `prompt_tokens`;
  - `hold-arm.sh <arm> <ctx> <flag-file>`, que chama o `run-arm.sh <arm> <ctx> --tag hold --exec "until [ -f <flag-file> ]; do sleep 60; done"`;
  - `run-tbench-remote.sh <arm> <base-url> [--print]`, que roda no laptop;
  - `tool_loop.py --max-tokens N`.

- [ ] **Step 1: Estado do rig e versões.** Gravar tudo em `results/etapa0-preflight.md`, com uma tabela "componente | versão | onde".
  - **Rig:** rodar `df -g /` e `idle-gate.sh --minutes 0`.
  - **Runtimes.** Conferir as releases de `incoai/splash` e `ddalcu/mlx-serve` com `gh api repos/<repo>/releases`.
    - Em 24/10, as últimas eram Splash 1.4.0 (20/10) e mlx-serve 26.10.3 (22/10), as mesmas que a campanha fixa.
    - O `main` do Splash tinha 29 commits depois da 1.4.0. A única mudança de runtime que afeta a campanha é a #561 (GGUF com menos experts). As #562 e #564 mexem só nas ferramentas de release.
    - Uma versão nova não substitui a 1.4.0 nos braços `k1*` e `k2*`, porque os dados de 32K e 128K da stack-updates usam a 1.4.0. Ela entra só no Task 5b.
  - **Harbor no laptop.**
    - Fixar a versão: `uv tool install --force harbor==0.24.0` (o laptop tinha a 0.18.0). Os flags que o runner usa continuam na 0.24.0: `--agent-timeout-multiplier`, `--environment-build-timeout-multiplier`, `-n`, `--ak`, `--jobs-dir` e `--job-name`.
    - Registrar a versão do agente `terminus-2` que vem com o harbor. Os runs antigos do repo usaram a 0.8.0, então um número novo não compara 1:1 com eles.
  - **Terminal-Bench 2.1 no laptop.**
    - Confirmar que `harbor dataset list` mostra `terminal-bench/terminal-bench-2-1`.
    - Baixar as tarefas antes com `harbor download terminal-bench/terminal-bench-2-1`.
    - Conferir se o Docker Desktop responde (`docker info`), se há ≥ 100 GB livres para as imagens amd64 (o laptop tinha 1.3 TB) e se o Docker tem ≥ 16 GB de RAM.
  - **Bateria no rig.** O `ab-battery.sh` roda com `uv run --with openai --with pyyaml`, sem versão fixa. Registrar as versões que o `uv` resolve (`uv run --no-project --with openai --with pyyaml python -c 'import openai, yaml; print(openai.__version__, yaml.__version__)'`) e não mudar mais durante a campanha. Os datasets (HumanEval 164, GPQA-Diamond 50, LiveCodeBench v6 50, IF 20, tool calls A 40 e B 12) são os da swift15, sem atualização.
  - **Renderização:** confirmar que o Chrome existe no laptop, porque o `render_m4max_guide.py --png` usa o Chrome headless.
- [ ] **Step 2: Download do GSQ-RCO-Coder GGUF no rig.** `fetch_pack.py` com `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revisão `bba88856f8c3c0c9e40e45f82d05e228b814ac43`, pasta `IQ1_M/`. Não baixar o `mmproj` (`--language-only`). São 58.4 GB.
- [ ] **Step 3: Testes que falham** em `tests/test_campaign.py`:
  - `test_k3_arms_are_the_ista_gguf_with_the_k2_flags`: `--model ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF:IQ1_M`, `--revision bba88856...`, `k3` termina em `--verify-rows all`, `k3a` em `auto`, `k3ab` em `auto --kv-format bf16`;
  - `test_k2as_adds_bf16_state`: o comando do `k2as` é o do `k2a` + ` --state-format bf16`;
  - `test_w1zq4_is_w1q4_on_26103`: o binário é `mlx-serve-v26.10.3` e o env tem `QWEN38_MLX_KV_QUANT=4`;
  - `test_splash_1m_band_uses_1000000`: `run-arm.sh k2a 1000000 --print` mostra `--max-context 1000000`;
  - `test_longctx_prompt_leaves_room_for_output`: para `context` 1000000, o prompt estimado tem ≤ 991808 tokens, e as respostas esperadas estão no haystack;
  - `test_longctx_is_deterministic`: o mesmo `seed` gera o mesmo haystack e as mesmas respostas;
  - `test_tbench_runner_uses_21_and_caffeinate`: o `--print` contém `caffeinate -i harbor run`, `--dataset terminal-bench/terminal-bench-2-1`, `--agent terminus-2`, `-n 1`, `--agent-timeout-multiplier 1.0` e `--environment-build-timeout-multiplier 3.0` (o build amd64 sob emulação é lento);
  - `test_tool_loop_max_tokens_reaches_payload` (em `test_tool_loop.py`): `--max-tokens 2048` vira `payload["max_tokens"] == 2048`, e o default continua 512.
- [ ] **Step 4: Rodar os testes e ver que falham.** `uvx pytest -q bench/splash-longctx-2026-10/tests`.
- [ ] **Step 5: Implementar.**
  - `longctx_probe.py`:
    - O haystack usa linhas de log sintéticas.
    - Ele planta 16 registros `ledger: <conta> moved <n> units to <conta>` em profundidades uniformes de 5% a 95%.
    - As 8 perguntas cobrem: 3 buscas diretas, 3 somas por conta e 2 cadeias de dois saltos.
    - As respostas são inteiros ou nomes, comparados de forma exata.
    - O haystack é um prefixo fixo, e as perguntas vêm no fim. Assim, só a primeira pergunta paga o prefill a frio.
    - O tamanho alvo é `0.9 × context` tokens, estimado a 3.6 caracteres por token. O probe grava o `prompt_tokens` real de cada resposta.
  - `run-tbench-remote.sh`:
    - Segue o `run-tbench-ds4-udq2kxl-REMOTE.sh`.
    - Lê o model id em `<base-url>/models`.
    - Usa os kwargs do perfil t1 do `run-tbench-flashnext.sh`, com `--job-name tb21-<arm>` e `--jobs-dir bench/splash-longctx-2026-10/logs/tbench-runs`.
- [ ] **Step 6: Rodar os testes e ver que passam.** As suítes de `bench/stack-updates-2026-10/tests` e `bench/qwen38-flashnext-daily-driver-2026-09/tests` também passam.
- [ ] **Step 7: Smoke no rig.** Uma fila curta com o driver parado:
  1. `k3a` a 32768, só o cenário cold. O esperado na 1.4.0 é a recusa da #527. Gravar a mensagem em `results/etapa0-k3-load.md`. Se o GGUF carregar, os braços `k3*` seguem nos Tasks 1 a 4, e o Task 5 não roda;
  2. `k2a` a 1000000, só o boot. Copiar do boot log o plano de memória do Splash (`/status`, contexto aceito, memória reservada);
  3. o `longctx_probe` contra o `k2a` a 32768, para conferir o formato da saída.
- [ ] **Step 8: Commit.** `bench(splash-longctx): Task 0 — arms, long-context probe, remote Terminal-Bench runner`.

### Task 1: Bandas nativas, 8K a 256K

- [ ] **Step 1: Fila `chain-t1.sh`.** Rodar o `cache_probe` com 3 reps em cada banda:
  - `k1a`: 8K e 256K;
  - `k2a`: 8K e 256K (o 256K de 23/10 teve só 1 rep);
  - `k3a`: 8K, 32K, 128K e 256K;
  - `w1z`: 8K.

  Rodar `idle-gate.sh` entre as bandas. Tempo estimado: ~4 h.
- [ ] **Step 2: Resumo.** Gerar `summarize_driver` e `decide.py --mode le --threshold 0.97` contra o `w1z` em cada banda. Gravar `results/etapa1-native.md` com a tabela de `T_turno`, cold TTFT, warm TTFT, hit, decode, wired peak, livre mínimo e swap Δ.
- [ ] **Step 3: Commit.**

### Task 2: 512K e escolha dos parâmetros

- [ ] **Step 1: Varredura a 524288, 1 rep.** Braços `k2a`, `k2ab` e `w1zq4`. Se o Splash recusar o boot do `k2ab` por memória, registrar a recusa e seguir.
- [ ] **Step 2: Escolha.**
  - O formato de KV do Swift a 512K (`kv512`) é o `bf16` quando o `k2ab` passa nos gates e no gate de folga com `T_turno` ≤ 1.05 × o do `k2a`. Nos outros casos, é o `int8`.
  - Gravar a escolha e o motivo em `results/etapa2-512k.md`.
- [ ] **Step 3: 3 reps a 524288.** Rodar o braço Swift escolhido, o `w1zq4`, o `k1a` e o `k3a` (ou o `k3ab`, se o `kv512` for `bf16`).
- [ ] **Step 4: Resumo e veredito.** Aplicar a regra "aceitável a 512K" só com os critérios de velocidade e de folga. O critério de qualidade fecha no Task 4.
- [ ] **Step 5: Commit.**

### Task 3: 1M (1000000 tokens)

- [ ] **Step 1: 1 rep a 1000000.** Rodar o braço Swift com o `kv512`, o `k1a` e o `k3a`. Um cold a 1M leva ~25–30 min (extrapolação de 351 s a 256K), então cada braço leva ~1–1.5 h.
- [ ] **Step 2: Escada de recuo, só para o braço Swift.**
  1. Se o boot for recusado ou o gate de folga falhar, rodar o `k2as` (`--state-format bf16`).
  2. Se o `k2as` também falhar, rodar 786432 com o `kv512`, para localizar o maior contexto que passa.
  3. Gravar cada degrau.
- [ ] **Step 3: Segunda rep do braço Swift que passou.**
- [ ] **Step 4: `w1z` a 1M não roda.** O perfil 512k do mlx-serve já fica com 0.01 GB livres. Registrar como `não rodou: 512K já no limite de memória`.
- [ ] **Step 5: Resumo.** Gravar `results/etapa3-1m.md` com as tabelas, a escada e o veredito de velocidade e folga.
- [ ] **Step 6: Commit.**

### Task 4: Qualidade leve do Splash com o Swift (e do GSQ)

Cada linha sobe o servidor com o `--max-context` da coluna. A bateria usa `run-battery.sh --suites "humaneval gpqa livecodebench if jdhodges veerman"` (perfil t1, xhigh).

O `if` é a sonda de instruction following do `if_probe.py`: 20 prompts no estilo IFEval, verificados por código. Ela custa minutos e tem pouca resolução: o `w1` fez 20/20 e o `n2` 19/20 na [swift15](../swift15-flashnext-2026-10/results/summary.md). Mesmo assim, ela pega a regressão que mais importa aqui. Com o YaRN estático, o servidor de 512K e o de 1M também mudam as respostas a prompts curtos, e um erro de formato aparece nessa sonda antes de aparecer em código.

| braço | 262144 | 524288 | 1000000 |
|---|---|---|---|
| `w1z` | bateria, longctx, toolcall | — | — |
| `w1zq4` | — | longctx | — |
| Swift escolhido (`k2a`/`k2ab`/`k2as`) | bateria, longctx, toolcall | bateria, longctx | bateria, longctx |
| `k3a` | bateria, longctx, toolcall | longctx (se passou no Task 2) | longctx (se passou no Task 3) |

- [ ] **Step 1: Fila `chain-t4.sh` com a tabela acima.**
  - O longctx roda nas bandas 128K, 256K, 512K e 1M que cada servidor aceita.
  - O `toolcall-probe.sh` roda com `--sessions 20 --suffix t4 --max-tokens 2048`.
- [ ] **Step 2: Resumo.**
  - Rodar `summarize_ab.py` (G1 e G2) de cada coluna YaRN contra a coluna 262144 do mesmo braço, e do Swift escolhido contra o `w1z`.
  - Gravar `results/etapa4-quality.md`. Ele fecha a regra "aceitável" de 512K e de 1M.
- [ ] **Step 3: Commit.**

### Task 5: GSQ-RCO-Coder no mlx-serve (se o Splash recusou o `k3` no Task 0)

- [ ] **Step 1: Bandas.** Rodar o `r1z` a 8K e 256K (3 reps). Em 25/10, o usuário limitou o GSQ a 256K: o `r1zy` (512K e 1M) não roda.
- [ ] **Step 2: Qualidade.** Rodar a bateria do `r1z` a 262144, o probe de tool calls e o longctx no servidor de 262144 (bandas 128K e 256K). A bateria de 131072 do Task 6 da stack-updates continua valendo como referência.
- [ ] **Step 3: Gravar `results/etapa5-gsq-mlx-serve.md` e commitar.** Se o Splash carregou o `k3`, gravar só uma linha dizendo que o Task 5 não rodou e por quê.

### Task 5b: GSQ-RCO-Coder numa release nova do Splash (condicional)

Roda só se, antes do Task 6, o Splash publicar uma release que contenha a #561. Conferir com `gh api repos/incoai/splash/releases` e com as notas da release.

- [ ] **Step 1: Instalar** em `~/.local/opt/qwen38/splash-v<versão>/` com o `install-runtime.sh`, que confere o digest. A 1.4.0 continua instalada e serve os outros braços.
- [ ] **Step 2: Controle de versão.** Rodar o `k2a` a 32768 na versão nova, com 1 rep. Se o `T_turno` ficar fora de ±5% do `k2a` na 1.4.0, registrar a diferença: os números do `k3` não comparam 1:1 com os do `k2a`.
- [ ] **Step 3: Braços `k3n`, `k3na`, `k3nab`** (o `k3` na versão nova). Rodar os Tasks 1 a 4 com eles: bandas, 512K, 1M e qualidade. Gravar `results/etapa5b-gsq-splash.md`.
- [ ] **Step 4: Commit.** No Task 6, o braço GSQ passa a ser o `k3na`, em vez do `r1z`.

### Task 6: Terminal-Bench 2.1, do MacBook contra o rig

Ordem: o Swift escolhido a 262144, depois o `w1z` (o driver diário), depois o `k3a` (ou o `r1z`). Cada run tem 89 tarefas, `-n 1` e timeout 1.0×, e leva ~12–24 h.

- [ ] **Step 1: Rig.** Rodar `hold-arm.sh <arm> 262144 logs/tb21-<arm>.done` com `nohup`. Para o `w1z`, o driver diário serve na porta 11234 e não precisa do hold.
- [ ] **Step 2: Laptop.**
  - Rodar `run-tbench-remote.sh <arm> http://100.110.87.118:<porta>/v1` com `nohup`.
  - Se o harbor parar, rodar `harbor job resume -p bench/splash-longctx-2026-10/logs/tbench-runs/tb21-<arm>`.
- [ ] **Step 3: Fim.** Fazer `ssh ... touch logs/tb21-<arm>.done`. Ler o resultado do job e gravar `results/tbench21-<arm>.md`:
  - taxa de sucesso;
  - tarefas com erro de ambiente, contadas à parte;
  - tempo total;
  - pico de memória do rig.
- [ ] **Step 4: Resumo e commit.** Gravar `results/etapa6-tbench21.md` com os três braços e a nota de que o gate antigo, 32.6%, vem do Terminal-Bench 2.0. Commitar.

### Task 7: Parâmetros de 512K e 1M e launcher

- [ ] **Step 1: Tabela de decisão.** Gravar `results/params-512k-1m.md`. Para cada braço e banda, ela traz:
  - os flags exatos;
  - os gates;
  - o veredito "aceitável" (velocidade, folga, qualidade);
  - se 1M não passou, o maior contexto que passou.
- [ ] **Step 2: Launcher.**
  - Teste antes: `tools/tests/test_serve_flashnext_splash.py`, em que o `--print` de cada perfil mostra os flags da tabela.
  - Depois, `tools/scripts/serve-flashnext-splash.sh [256k|512k|1m] [--print]`, no estilo do `serve-flashnext-daily-driver.sh`: porta 8585 e `--idle-release off`.
  - Só entram perfis aceitáveis. Um perfil reprovado sai do script, e o motivo fica num comentário.
- [ ] **Step 3: Commit.** O driver diário não muda: a troca fica com o usuário.

### Task 8: Relatórios até 1M

- [ ] **Step 1: Testes que falham.**
  - `test_consolidate_reports.py`: o perfil 2026-10 inclui grupos de `bench/splash-longctx-2026-10/results`, as séries `w1z`, `k2s` (Swift no Splash), `k1s` (Flash-Next no Splash) e `k3s` (GSQ no Splash ou no mlx-serve), e a banda 1000000.
  - `test_render_perf_lines.py`: `LINE_CTX` termina em 1000000, e a tabela mostra o rótulo "1M".
  - `test_render_m4max_guide.py`: `CTX` inclui 1000000, e a página tem a linha de comando do perfil Splash escolhido.
- [ ] **Step 2: Implementar.**
  - No `consolidate_reports.py`, o mapa braço → série passa a incluir as séries da Step 1, e os grupos ganham notas por banda.
  - Nas páginas:
    - "cache" usa o hit e o warm TTFT;
    - "tempos" usa cold TTFT, `T_turno` e decode;
    - a qualidade vem do `etapa4` e do `etapa6`;
    - as bandas não medidas entram em `ABSENT`/`MISSING`, com o motivo.
- [ ] **Step 3: Gerar.** Rodar `consolidate_reports.py --profile 2026-10`, `render_perf_lines.py` e `render_m4max_guide.py --png`.
- [ ] **Step 4: Conferir.**
  - As suítes do `bench/qwen38-flashnext-daily-driver-2026-09/tests` passam.
  - As duas páginas abrem no browser do app sem erro no console, em 1280 px e em 375 px.
- [ ] **Step 5: Commit.** `bench(splash-longctx): reports to 1M with Splash series`.

### Task 9: Fechamento

- [ ] **Step 1: `results/summary.md`.** Uma tabela por pergunta do topo, as recomendações e os desvios do plano.
- [ ] **Step 2: Nota.** Acrescentar a seção "Resultado no rig" em `research/splash-speed-tradeoffs-20261024.md`.
- [ ] **Step 3: Conferir o driver diário.** Ele deve estar no ar com o comando de `serve-flashnext-daily-driver.sh` e responder `/health`.
- [ ] **Step 4: Push e PR.**
  - Fazer push da branch e abrir o PR para a `main`, com o corpo terminando em `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
  - Não fazer merge. O merge publica as páginas, e o usuário decide.
