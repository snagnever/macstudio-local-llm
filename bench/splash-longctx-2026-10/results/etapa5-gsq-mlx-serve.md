# Etapa 5 — GSQ-RCO-Coder no mlx-serve, no Splash do main e no Splash 1.4.1 (2026-10-25, 2026-11-01)

O GSQ-RCO-Coder é o Flash Next podado para 256 dos 512 experts e ajustado para código (ISTA-DASLab). O `r1z` é o pack MLX `mbrown-uno` `50fa68c` no mlx-serve 26.10.3. O `k3ma` é o GGUF IQ1_M `bba8885` num pacote do Splash compilado do `main` em `3135ab4`, que contém a #561. A 1.4.0 recusa esse GGUF (#527), e nenhuma release com a #561 saiu até 25/10. Por decisão do usuário, o GSQ roda só até 256K.

## Velocidade (`cache_probe`, 3 reps, tag `lc`)

| braço | contexto | T_turno | cold TTFT | warm TTFT id/app/tool | hit id/app/tool | prefill | decode | wired peak | gates |
|---|---:|---:|---:|---|---|---:|---:|---:|---|
| r1z | 8K | 8.5 s | 3.2 s | 0.2/1.5/1.5 s | 0.99/0.72/0.71 | 842 | 73.9 | 57.3 GB | passa |
| k3ma | 8K | 5.9 s | 3.1 s | 0.1/1.3/1.3 s | 1.00/0.72/0.71 | 877 | 111.8 | 67.4 GB | passa |
| w1z | 8K | 7.7 s | 3.3 s | 0.2/1.6/1.6 s | 0.99/0.72/0.71 | 819 | 83.7 | 90.2 GB | passa |
| r1z | 256K | 11.0 s | 360.3 s | 0.8/2.4/2.5 s | 1.00/1.00/1.00 | 712 | 60.0 | 89.3 GB | passa |
| k3ma | 256K | 6.3 s | 335.3 s | 0.1/1.5/1.6 s | 1.00/1.00/1.00 | 765 | 107.2 | 79.9 GB | passa |

- No Splash, o GSQ decodifica 1.8× mais rápido que no mlx-serve a 256K e ocupa ~9 GB a menos. O `T_turno` a 256K (6.3 s) é o menor da campanha.
- Os números do `k3ma` vêm de um build não oficial (`1.4.0-main-3135ab4`). Uma release com a #561 pode mudar o resultado.
- O `k3ma` rodou só velocidade. A qualidade abaixo é do `r1z`, que usa outros pesos (o pack MLX, não o GGUF IQ1_M).

## Qualidade do `r1z` a 262144

Bateria t1, `reasoning_effort` xhigh, base `w1z` a 262144:

| suíte | w1z | r1z | G1 |
|---|---:|---:|---|
| HumanEval | 142/164 | 152/164 | passa |
| GPQA | 43/50 | 31/50 (7 trunc) | **falha** |
| LiveCodeBench | 47/50 | 46/50 | passa |
| IF | 19/20 | 19/20 | passa |
| jdhodges | 34/40 | 35/40 | passa |
| veerman | 10/12 | 9/12 | passa |

- O GSQ ganha 10 questões no HumanEval e perde 12 no GPQA. É o perfil esperado de um modelo podado para código. 7 respostas do GPQA esgotaram o limite de tokens.
- A fila foi interrompida no início do GPQA para rodar antes o teste do `k2m` (pedido do usuário). O HumanEval já estava completo, e o GPQA recomeçou do zero.

Longctx (`longctx_probe.py`, servidor de 262144): 7/8 na banda de 128K (errou a q08) e 8/8 na de 256K.

Tool calls (`toolcall-probe.sh --sessions 20 --max-tokens 2048`): com `frequency_penalty` 0, 20/20 sessões e 100/100 turnos. Com penalidade 1, 4/20 sessões e 70/91 turnos (#912).

## Swift 1.5 MLX no Splash (`k2m`)

O braço `k2m` tentou servir os pesos do `w1z` (Dankpaws Swift 1.5 MLX 4.7 bpw) no Splash 1.4.0, para separar o efeito do runtime do efeito do formato. O Splash recusa no boot: `Qwen3.8-Flash-Next loads from a GGUF only`. A regra está no engine (`runtime/model/QwenTargetLoader.hpp`) e continua no `main`. A comparação `k2a` × `w1z` mistura runtime e formato, e o Splash não permite isolar os dois.

## GSQ no Splash 1.4.1 (`k3r`, 2026-11-01)

O `k3r` é o mesmo GGUF IQ1_M `bba8885` do `k3ma`, na release 1.4.1 do Splash (`v1.4.1-verify-auto`), a primeira com a #561. A tarefa `t5r` rodou de 01/11 00:02 a 07:42 (hora do rig): as bandas de 8K e 256K (3 reps) e a bateria t1 a 262144.

### Velocidade (`decide.py`, 3 reps, tag `lc`)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit app/tool | decode | wired peak | needles |
|---|---:|---:|---:|---:|---|---:|---:|---|
| k3ma | 8K | 5.9 s | 3.1 s | 1.30 s | 0.72/0.71 | 111.8 | 67.4 GB | 12/13 (1 trunc) |
| k3r | 8K | 5.9 s | 3.1 s | 1.30 s | 0.72/0.71 | 112.9 | 67.5 GB | 9/13 (4 trunc) |
| k3ma | 256K | 6.3 s | 335.3 s | 1.60 s | 1.00/1.00 | 107.2 | 79.9 GB | 10/13 (3 trunc) |
| k3r | 256K | 6.1 s | 335.3 s | 1.60 s | 1.00/1.00 | 112.4 | 79.8 GB | 11/13 (2 trunc) |

- A release dá o mesmo resultado que o build do `main`. A 256K, a razão `T_turno(k3r) / T_turno(k3ma)` é 0.968. Ela fica 0.002 fora da faixa de paridade (±0.03), do lado mais rápido.
- Os gates do `summarize_driver` passam nas duas bandas. As needles que faltam são truncamentos em `max_tokens` 4096, não respostas erradas.
- A 256K, o `k3r` ocupa 36.6 GB de wired a menos que o `k2a` (116.4 GB) e tem `T_turno` 0.5 s menor (6.6 s).

### Qualidade a 262144

Bateria t1, `reasoning_effort` xhigh, `summarize_ab.py`:

| suíte | w1z | r1z | k3r | G1 contra o `w1z` |
|---|---:|---:|---:|---|
| HumanEval | 142/164 | 152/164 | 149/164 | passa |
| GPQA | 43/50 | 31/50 (7 trunc) | 25/50 (8 trunc) | **falha** |
| LiveCodeBench | 47/50 | 46/50 | 48/50 | passa |
| IF | 19/20 | 19/20 | 19/20 | passa |
| jdhodges | 34/40 | 35/40 | 36/40 (1 trunc) | passa |
| veerman | 10/12 | 9/12 | 10/12 | passa |

- O GGUF IQ1_M repete o perfil do pack MLX: ganha no código e perde 18 questões no GPQA. O G1 contra o `r1z` também falha no GPQA (25 contra 31).
- No GPQA, o `k3r` raciocina 78 mil chars por questão na mediana, contra 3.7 mil do `w1z`. A mediana de tempo é 223 s por questão, contra 15 s. 8 respostas esgotaram o limite de 65536 tokens.
- No LiveCodeBench, o `k3r` leva 24 s por questão na mediana, contra 19 s do `w1z` e 51 s do `r1z`.

## Veredito

| perfil | velocidade | qualidade | uso |
|---|---|---|---|
| r1z 262144 (mlx-serve) | passa, mais lento que o `w1z` | falha no G1 do GPQA | só código, se a memória menor importar |
| k3ma 262144 (Splash do main) | o mais rápido da campanha | não medida | substituído pelo `k3r` |
| k3r 262144 (Splash 1.4.1) | igual ao `k3ma`, o mais rápido da campanha | falha no G1 do GPQA (25/50) | só código; no Terminal-Bench 2.1 o mesmo GGUF (`k3f`, Splash 1.5.0) fica em 58.4% |
