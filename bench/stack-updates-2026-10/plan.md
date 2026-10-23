# Stack updates 2026-10-22 — runbook dos testes 1, 4, 5 e 6

> **Para agentes:** execute as tasks em ordem, sem pedir confirmação entre elas. Marque cada step (`- [ ]` → `- [x]`). Pare só nas condições de parada da seção "Execução autônoma".

**Objetivo:** rodar os testes 1, 4, 5 e 6 de [research/rig-stack-updates-20261022.md](../../research/rig-stack-updates-20261022.md). Cada teste termina com um arquivo `results/etapa<N>-*.md` e uma recomendação. Nenhum teste troca o driver diário. O usuário decide a troca.

| teste | pergunta | braços |
|---|---|---|
| 1 | O mlx-serve 26.10.3 pode substituir a 26.10.1 no driver diário? | `w1` × `w1z` |
| 4 | O twyx iQ-MLX-6.6bpw vale a memória a mais contra o iQ 4.7bpw? | `n2z` × `t6z` |
| 5 | O Splash 1.4.0 serve o GGUF do Flash-Next mais rápido que o `w1`? | `k1` (`--verify-rows all`), `k1a` (`auto`) × `w1` |
| 6 | O Flash-Next podado para código (GSQ-RCO, 256 experts) mantém a qualidade com metade da memória? | `r1` × `w1` |

**Arquitetura:** a campanha reusa o driver `run-candidate.sh` de [bench/qwen38-flashnext-daily-driver-2026-09](../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh) e os scripts de [bench/flashnext-next-steps-2026-10](../flashnext-next-steps-2026-10/plan.md): `install-runtime.sh`, `fetch_pack.py`, `idle-gate.sh`, `run-seq.sh`, `decide.py` e `run-battery.sh`. Os braços novos entram num bloco próprio do `run-candidate.sh`. Esta campanha só cria os wrappers que gravam em `bench/stack-updates-2026-10/results/` e `logs/`, mais um flag no probe de tool calls.

## Restrições globais

As restrições globais de [bench/flashnext-next-steps-2026-10/plan.md](../flashnext-next-steps-2026-10/plan.md#global-constraints) valem aqui sem mudança: rig, métrica `T_turno`, gates, sampling, probe `cache_probe.py`, protocolo térmico, harness, reserva de disco, idioma, commits e testes. As diferenças:

- Runtimes novos em `~/.local/opt/qwen38/`: `mlx-serve-v26.10.3/`, `omlx-v0.7.2/`, `splash-v1.4.0/`. `~/.local/bin` e `tools/scripts/serve-flashnext-daily-driver.sh` não mudam.
- Bandas de velocidade: 32K e 128K com 3 reps; 256K com 1 rep (o perfil diário serve 262144 desde o commit `1a3b8c4`).
- A referência `w1` roda de novo nesta campanha, no mesmo dia dos candidatos. Não reusar os números de 14/10.
- Commits: `bench(stack-updates): ...`, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Execução autônoma

- Rode tudo no rig: `ssh vitor@mac-studio`, checkout em `~/LocalProjects/local-llms`. Faça `git pull` antes do Task 0.
- Rode cada fila com `nohup ... &` e grave o log em `logs/`. Uma fila de 128K leva horas.
- Um braço que falha não para a fila. Registre o erro no `etapa<N>` e siga para o próximo teste.
- **Pare e espere o usuário** só nestes casos:
  1. disco livre abaixo de download + 150 GB (o `fetch_pack.py` recusa);
  2. digest SHA256 ausente ou diferente no `install-runtime.sh` (exit 65);
  3. swap Δ > 2 GB ou kernel panic em qualquer braço;
  4. o driver diário não volta a subir no fim da campanha.
- Commit no fim de cada task, com os `results/` daquela task.

## Mapa de arquivos

| arquivo | ação | responsabilidade |
|---|---|---|
| `bench/stack-updates-2026-10/plan.md` | Create | este runbook |
| `bench/stack-updates-2026-10/scripts/run-arm.sh` | Create (Task 0) | cópia do `run-arm.sh` de next-steps; `HERE` aponta para esta campanha |
| `bench/stack-updates-2026-10/scripts/run-seq.sh` | Create (Task 0) | cópia do `run-seq.sh` de next-steps, chamando o `run-arm.sh` daqui |
| `bench/stack-updates-2026-10/scripts/toolcall-probe.sh` | Create (Task 0) | roda o `tool_loop.py` com `frequency_penalty` 0 e 1 contra um braço |
| `bench/qwen3.8-prefix-cache/scripts/tool_loop.py` | Modify (Task 0) | flag `--frequency-penalty` (default 0.0) |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify (Task 0) | braços `w1z n2z t6z k1 k1a r1` |
| `bench/qwen3.8-prefix-cache/scripts/run-splash.sh` | Modify (Task 0) | arm `KF` (GGUF do Flash-Next) |
| `bench/qwen3.8-prefix-cache/config/omlx-arms.json` | Modify (Task 0) | arm `FG` (GSQ-RCO-Coder) |
| `bench/stack-updates-2026-10/tests/test_arms.py` | Create (Task 0) | `--print` de cada braço novo |

## Braços

| braço | pesos | runtime | porta |
|---|---|---|---|
| `w1` | Swift 1.5 `13839b7` | mlx-serve 26.10.1 (já existe) | 11234 |
| `w1z` | Swift 1.5 `13839b7` | mlx-serve 26.10.3 | 11234 |
| `n2z` | ddalcu iQ-MLX-4.7bpw `dafff5c` | mlx-serve 26.10.3 | 11234 |
| `t6z` | twyx iQ-MLX-6.6bpw `884894d` | mlx-serve 26.10.3 | 11234 |
| `k1` | ggml-org IQ4_NL `91fb003` + `dflash-...-Q8_0.gguf` | Splash 1.4.0, `--verify-rows all` | 8585 |
| `k1a` | igual ao `k1` | Splash 1.4.0, `--verify-rows auto` | 8585 |
| `r1` | mbrown-uno GSQ-RCO-Coder-MLX `50fa68c` | oMLX 0.7.2 (arm `FG`) | 8000 |

Flags do `w1z`, `n2z` e `t6z`: as mesmas do `w1` e do `n2`. Só o binário e os pesos mudam.

---

### Task 0: Pré-voo

- [ ] **Step 1: Estado do rig.** Parar o driver diário. Rodar `df -g /`, `sysctl hw.memsize` e `idle-gate.sh --minutes 0`. Gravar em `results/etapa0-preflight.md`.
- [ ] **Step 2: Runtimes.** Instalar com o `install-runtime.sh` de next-steps:

```bash
MLX_TAG=v26.10.3 bash bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh mlx-serve
OMLX_TAG=v0.7.2 bash bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh omlx
SPLASH_TAG=1.4.0 bash bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh splash
```

Gravar `--version` de cada binário e o hash de cada asset em `results/install-runtimes.md`. A release 26.10.3 publica digest para `mlx-serve-bin-macos-arm64.tar.gz`, e a 1.4.0 publica digest para `splash-1.4.0-arm64-macos26.tar.gz`.

- [ ] **Step 3: Packs.** Para cada pack, rodar `fetch_pack.py --dry-run` e depois sem `--dry-run`, com `--receipt bench/stack-updates-2026-10/results/downloads.json`:

| pack | revisão | `--include` | download |
|---|---|---|---|
| `twyx/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-6.6bpw` | `884894d` | — | ~138 GB |
| `mbrown-uno/Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX` | `50fa68c` | — | ~81 GB |
| `ggml-org/Qwen3.8-Flash-Next-GGUF` | `91fb003` | `*IQ4_NL*`, `dflash-*Q8_0*`, `*.md`, `*.json` | ~102 GB; com `--link-from` no pack GGUF antigo, só os arquivos que mudaram |

Se o disco não comporta os três, baixar na ordem dos tasks e apagar o pack de um task antes do download do próximo. Apagar só packs desta campanha.

- [ ] **Step 4: Flag `--frequency-penalty` no `tool_loop.py`.** Escrever primeiro um teste em `bench/qwen3.8-prefix-cache/tests/test_tool_loop.py` que confere o campo no corpo do request. Depois adicionar o flag (default 0.0). O valor substitui `SAMPLING_CONTROLS["frequency_penalty"]` só neste probe.
- [ ] **Step 5: Wrappers.** Criar `scripts/run-arm.sh` e `scripts/run-seq.sh` desta campanha. Criar `scripts/toolcall-probe.sh <arm>`: sobe o braço a 65536 com `run-arm.sh <arm> 65536 --exec`, roda `tool_loop.py --turns 20` duas vezes (`--frequency-penalty 0` e `1`) e grava `results/toolcall/<arm>-fp{0,1}.jsonl`.
- [ ] **Step 6: Braços.** Adicionar `w1z n2z t6z k1 k1a r1` ao `run-candidate.sh`, num bloco com comentário `stack-updates-2026-10`. Para o `k1`/`k1a`, rodar `splash --help` antes: se o Splash 1.4.0 não aceita um GGUF local, usar o Hub ID `ggml-org/Qwen3.8-Flash-Next-GGUF` com a revisão `91fb003`. Gravar a forma usada em `results/etapa5-splash-launch.md`.
- [ ] **Step 7: Testes.** `test_arms.py` confere o `--print` de cada braço novo: binário, versão esperada, porta, diretório de pesos e revisão. Rodar `uv run --no-project --with pytest python -m pytest bench/stack-updates-2026-10/tests bench/qwen3.8-prefix-cache/tests/test_tool_loop.py -q`.
- [ ] **Step 8: Smoke.** Subir cada braço novo a 32768 com `--scenarios cold --repeat 1`. Um braço que não carrega sai da fila e ganha uma linha em `results/etapa0-preflight.md`.
- [ ] **Step 9: Commit.**

### Task 1: mlx-serve 26.10.3 no driver principal (`w1` × `w1z`)

- [ ] **Step 1: Tool calls.** `toolcall-probe.sh w1` e `toolcall-probe.sh w1z`.
- [ ] **Step 2: Velocidade.**

```bash
bash bench/stack-updates-2026-10/scripts/run-seq.sh w1:32768:3:e1 w1z:32768:3:e1
bash bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh
bash bench/stack-updates-2026-10/scripts/run-seq.sh w1z:131072:3:e1 w1:131072:3:e1
bash bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh
bash bench/stack-updates-2026-10/scripts/run-seq.sh w1:262144:1:e1 w1z:262144:1:e1
```

- [ ] **Step 3: Resultado.** `decide.py --base w1 --cand w1z` gera a tabela fixa. Escrever `results/etapa1-mlx-serve-26103.md` com a tabela, as taxas de tool call e o veredito.

**Regra de decisão.** Recomendar a 26.10.3 quando todas as condições valem:

- tool calls estruturadas em 20/20 turnos com `frequency_penalty` 0 e com 1;
- gates da campanha nas três bandas;
- `T_turno(w1z) ≤ 1.03 × T_turno(w1)` a 32K e a 128K.

A 26.10.3 é uma release estável que corrige defeitos, por isso a regra aceita empate (±3%). A regra de 0.97 da campanha anterior valia para um prerelease. Se a 26.10.3 falha uma condição, a recomendação é manter a 26.10.1.

### Task 4: twyx iQ-MLX-6.6bpw (`n2z` × `t6z`)

O KLD contra o bf16 não roda no rig: o bf16 do Flash-Next não cabe em 128 GB. O task usa o KLD do card do pack e mede o resto.

- [ ] **Step 1: Velocidade e memória.** `n2z` e `t6z` a 32K e 128K (3 reps) e a 256K (1 rep), com o `idle-gate.sh` entre bandas e a ordem alternada.
- [ ] **Step 2: Qualidade.** `run-battery.sh t6z e4 --suites "humaneval livecodebench if"` e o mesmo para `n2z`.
- [ ] **Step 3: Resultado.** `results/etapa4-twyx66.md` com a tabela fixa, o wired peak e o livre mínimo a 256K, as notas da bateria e o veredito.

**Regra de decisão.** O `t6z` é candidato a driver secundário quando todas as condições valem:

- gates nas três bandas, incluindo 256K sem swap;
- `T_turno(t6z) ≤ 1.10 × T_turno(n2z)` a 128K;
- nota da bateria ≥ a do `n2z` em pelo menos duas das três suítes.

Se uma condição falha, o veredito é "não adotar" e a nota registra qual.

### Task 5: Splash 1.4.0 com o GGUF do Flash-Next (`k1`, `k1a` × `w1`)

- [ ] **Step 1: Velocidade.** `k1` e `k1a` a 32K e 128K (3 reps). A referência é o `w1` medido no Task 1.
- [ ] **Step 2: Determinismo.** Rodar o `cache_probe.py` com `temperature 0` duas vezes no `k1` e no `k1a`, cenários `cold,identical`. Registrar se o texto do `identical` é igual ao do `cold`. O `k1a` pode divergir (issue #483); o `k1` não deve.
- [ ] **Step 3: Resultado.** `results/etapa5-splash140.md` com a tabela fixa, o resultado do determinismo e o veredito.

**Regra de decisão.** Resultado informativo. Recomendar o Splash só quando `T_turno(k1 ou k1a) ≤ 0.97 × T_turno(w1)` a 32K e a 128K, com gates. O Splash ainda não carrega o Swift 1.5 MLX (issue #471), então uma troca usaria outros pesos (IQ4_NL).

### Task 6: GSQ-RCO-Coder-MLX no oMLX 0.7.2 (`r1` × `w1`)

- [ ] **Step 1: Velocidade.** `r1` a 32K e 128K (3 reps). Registrar o livre mínimo: o pack ocupa ~43 GB, então a folga é grande.
- [ ] **Step 2: Qualidade de código.** `run-battery.sh r1 e6 --suites "humaneval livecodebench"` e o mesmo para `w1`.
- [ ] **Step 3: Tool calls.** `toolcall-probe.sh r1`.
- [ ] **Step 4: Resultado.** `results/etapa6-gsq-coder.md` com a tabela fixa, as notas, a taxa de tool call e o veredito.

**Regra de decisão.** O `r1` é candidato a perfil "código" quando todas as condições valem:

- HumanEval e LiveCodeBench a no máximo 2 pontos do `w1`;
- tool calls estruturadas em 20/20 turnos;
- `T_turno(r1) ≤ 0.97 × T_turno(w1)` a 32K.

### Task 8: Swift 1.5 GGUF no Splash 1.4.0 (`k2`, `k2a` × `w1`) — adicionado em 2026-10-23

O Task 5 mediu o Splash com os pesos do Flash-Next base (UD-IQ4_XS). A comparação com o `w1` misturava runtime e pesos. O Task 8 usa os pesos do `w1` em GGUF: `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF` `IQ4_XS` `0142554` (97.7 GB, repo gated, pasta `IQ4_XS/`). `k2` usa `--verify-rows all`, e `k2a` usa `auto`.

- [ ] **Step 1: Download.** `snapshot_download` para o cache do HF com `allow_patterns=["IQ4_XS/*", "*.json"]`. O token do HF do rig já tem acesso ao repo.
- [ ] **Step 2: Fila.** Parar o driver diário. `run-tasks.sh t8`: `k2`/`k2a` a 32K e 128K (3 reps), `k2a` a 256K (1 rep), `toolcall-probe.sh k2a` e bateria `humaneval livecodebench` do `k2a` com o rótulo `e6` (mesma pasta da bateria do `w1`).
- [ ] **Step 3: Resultado.** `results/etapa8-splash-swift.md`: tabela fixa com `w1`, `k1a`, `k2` e `k2a`, razão contra o `w1`, wired a 256K, notas da bateria (`summarize_ab.py --ab-dir results/e6/t1 --base w1 --cand k2a`) e tool calls.

**Regra de decisão.** O `k2a` (ou o `k2`) é candidato a driver diário quando todas as condições valem:

- `T_turno ≤ 0.97 ×` o `w1` a 32K e a 128K, com gates;
- 256K sem swap (Δ ≤ 0.5 GB);
- HumanEval e LiveCodeBench a no máximo 2 pontos do `w1`;
- tool calls em 20/20 com `frequency_penalty` 0.

A troca do driver fica com o usuário.

### Task 9: GSQ-RCO-Coder no mlx-serve 26.10.3 (`r1z` × `r1`, `w1`) — adicionado em 2026-10-23

O `r1` ficou 31–40% atrás do `w1` no oMLX 0.7.2. O `r1z` roda o mesmo pack no mlx-serve 26.10.3, que carrega packs oMLX nativamente (o `o1rm` da campanha next-steps rodou assim) e lê a tabela n-gram 8-bit g32 desde a #936. O teste separa o efeito do runtime do efeito do modelo.

- [ ] **Step 1: Fila.** Depois do Task 8, com o driver diário parado: `run-tasks.sh t9` (`r1z` a 32K e 128K, 3 reps, e `toolcall-probe.sh r1z`).
- [ ] **Step 2: Resultado.** `results/etapa9-gsq-coder-mlx-serve.md`: tabela fixa com `w1`, `r1` e `r1z`, aceitação MTP do `r1z` e tool calls. A qualidade vem da bateria do `r1` (Task 6), porque os pesos são os mesmos.

**Regra de decisão.** A mesma do Task 6, com a qualidade do `r1`: o `r1z` é candidato a perfil "código" quando `T_turno ≤ 0.97 ×` o `w1` a 32K e as tool calls ficam em 20/20 com `frequency_penalty` 0.

### Task 7: Fechamento

- [ ] **Step 1: Resumo.** Escrever `results/summary.md`: uma linha por teste, com o veredito, os números que decidem e o link para o `etapa<N>`.
- [ ] **Step 2: Nota.** Adicionar uma seção "Resultado no rig" ao fim de [research/rig-stack-updates-20261022.md](../../research/rig-stack-updates-20261022.md), com um link para o `summary.md`.
- [ ] **Step 3: Rig.** Religar o driver diário com o perfil de antes, sem mudança.
- [ ] **Step 4: Commit.** Commit final da campanha. Não fazer push sem pedido do usuário.
