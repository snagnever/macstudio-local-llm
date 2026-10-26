# Etapa 5 — GSQ-RCO-Coder no mlx-serve e no Splash do main (2026-10-25)

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

## Veredito

| perfil | velocidade | qualidade | uso |
|---|---|---|---|
| r1z 262144 (mlx-serve) | passa, mais lento que o `w1z` | falha no G1 do GPQA | só código, se a memória menor importar |
| k3ma 262144 (Splash do main) | o mais rápido da campanha | não medida | esperar uma release com a #561 e medir a qualidade |
