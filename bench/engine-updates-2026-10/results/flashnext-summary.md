# Flash-Next — veredito (2026-10-07)

**O n2 (mlx-serve 26.10.1 + iQ-MLX-4.7bpw) continua como driver diário.** Nenhum runtime atualizado chega a
`T_turno ≤ 0.97 × n2`. O oMLX 0.7.0 passa nos gates mas fica 23% mais lento a 32K e 38% a 128K. O MTPLX 2.12.2
perde o cache a 32K e recusa 128K com HTTP 507. O ds4 upstream não passou o gate de decode.

> **Correção (Etapa F):** o MTPLX 2.12.2 com prime de 64 tokens (m1p) reusa o cache e passa nos gates a 32K:
> `T_turno` 8.8 s, 1.07× o n2, 2º colocado. A perda de cache abaixo vinha do prime de 1 token do probe. O n2 segue
> driver. Ver [etapa-f-fixes.md](etapa-f-fixes.md).

Rig: M4 Max 128 GB. Probe: `temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning `xhigh`, limite 4096 tokens,
3 reps a 32K e 128K.

## 32K e 128K

| banda | braço | runtime | T_turno | cold TTFT | warm TTFT tool_turn | hit append / tool_turn | decode | wired pico | gates |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 32K | **n2** | mlx-serve 26.10.1 | **8.2 s** | 34.5 s | 1.9 s | 0.96 / 0.96 | 80.4 | 96.8 GB | passa |
| 32K | o1 | oMLX 0.7.0 | 10.1 s | 49.6 s | 2.4 s | 0.96 / 0.96 | 66.6 | 91.2 GB | passa |
| 32K | m1 | MTPLX 2.12.2 | 52.7 s | 44.2 s | 46.2 s | 0.00 / 0.00 | 78.6 | 99.4 GB | hit |
| 32K | m1b | MTPLX 2.12.2 + limite 96G | 10.4 s | 44.1 s | 3.8 s | 0.00 / 0.94 | 77.5 | 100.3 GB | hit_append |
| 128K | **n2** | mlx-serve 26.10.1 | **8.8 s** | 165.6 s | 1.9 s | 0.99 / 0.99 | 74.0 | 110.6 GB | passa |
| 128K | o1 | oMLX 0.7.0 | 12.1 s | 248.5 s | 3.2 s | 0.99 / 0.99 | 57.4 | 98.0 GB | passa |
| 128K | m1 | MTPLX 2.12.2 | — | — | — | — | — | 88.3 GB | HTTP 507 |
| 128K | m1b | MTPLX 2.12.2 + limite 96G | — | — | — | — | — | 88.1 GB | HTTP 507 |

| razão `T_turno(cand) / T_turno(n2)` | 32K | 128K | critério (≤ 0.97) |
| --- | ---: | ---: | --- |
| o1 | 1.23 | 1.38 | não |
| m1b | 1.27 | — | não |

O swap delta foi 0 em todos os braços. O n2 repete os números da campanha anterior (8.3 / 8.9 s).

## Por braço

- **oMLX 0.7.0 (o1).** Grande ganho sobre a 0.7.0.dev2 de setembro (13.5 / 15.0 s → 10.1 / 12.1 s; decode
  ~50 → 57–67 tok/s), e usa ~6–13 GB menos de wired que o n2. Ainda perde no prefill (550 contra 790 tok/s a 32K)
  e no decode. É o 2º colocado.
- **MTPLX 2.12.2 (m1, m1b).** O decode é o do n2 (~78 tok/s). O memory guard do 2.12.x planeja 90 GB de engine
  com 77.3 GB de pesos e descarta o prefixo reusável (`prefill_admission_shed`, `reusable_prefix_tokens: 0`), então
  cada turno re-prefila tudo. Com `MTPLX_MEMORY_LIMIT_BYTES=96G` o `tool_turn` volta a reusar (hit 0.94), mas o
  `append` não. A 128K os dois recusam: `--context-window 131072 exceeds this machine's memory-plan fit of 114688
  tokens` — o mesmo teto do 2.11.2.
- **ds4 upstream (d1).** Decode 53.5 tok/s a 32K, abaixo do gate de 70 (ver `etapa0-smoke.md`). Melhor que o fork
  de setembro (~40 tok/s), e o `--kv-disk-dir` dá reuso (hit 0.94).

## Funil

| braço | banda | T_turno | cold TTFT | warm TTFT id / app / tool | hit | decode | wired | resultado |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- |
| n2 | 256K | 9.8 s | 350.4 s | 1.1 / 2.0 / 2.1 s | 1.00 / 1.00 / 1.00 | 67.0 | 111.7 GB | passa |
| o1 | 256K | 14.5 s | 552.3 s | 1.4 / 4.2 / 4.3 s | 1.00 / 1.00 / 1.00 | 50.2 | 100.5 GB | passa |
| n2 | 512K (YaRN 2.0, KV 8-bit) | — | 785 s | — / 3.0 / 2.8 s | — | 46–55 | — | 4 de 5 cenários |

A 512K o `identical` recebeu `PrefillDoesNotFit` (o pedido precisa de ~14.1 GB e restam ~13.6 GB); `append`,
`tool_turn` e `middle_mutation` foram servidos. É o mesmo limite de memória já documentado para o perfil 512k:
capacidade, não uso diário. O MTPLX não entra em 256K/512K (recusa 128K); o oMLX não tem YaRN.

Dados: `*-t1.0-fn.jsonl`, `summary-fn.json`, `*-262144-t1.0-fnx256.jsonl`, `n2-524288-t1.0-yarn2.jsonl`.

**Re-run a 512K (2026-10-10, `n2-524288-t1.0-yarn2r.jsonl`, 1 rep).** O `identical` passou (hit 1.00), mas o
`PrefillDoesNotFit` voltou num prime de 1 token: pediu ~14 083 MB com ~10 886 MB disponíveis. Nos dois runs, o log
diz que a entrada do hot cache estava "shared with a live request". Em `src/server.zig` (v26.10.1), `WarmPrefix`
só desconta as linhas restauradas quando a requisição tira a entrada do cache (`will_donate`); uma entrada
compartilhada é copiada inteira no primeiro append, e a cópia (~9 GB de KV) mais os transientes não cabem. A falha
cai no turno que pegar a memória mais apertada, por isso mudou de cenário. Próximo teste: braço `n2o`
(`--os-reserve-gib 4`, default 8 GB), script `scripts/run-n2o-512k.sh`. O `middle_mutation` do re-run truncou em
4096 tokens de reasoning (limite do probe, não memória).

**Braço n2o (`--os-reserve-gib 4`, 2026-10-10, `n2o-524288-t1.0-osr.jsonl`, 1 rep).** Os 5 cenários medidos foram
servidos (`identical` 1.00, `append` 1.00, `tool_turn` 1.00; `middle_mutation` truncou em 4096 tokens, como no
yarn2r). Wired pico 111.0 GB, livre mínimo 0.02 GB, swap 0. Mas o log ainda tem um `PrefillDoesNotFit` num prime:
~14 083 MB pedidos contra ~13 793 MB disponíveis. A folga subiu ~2.9 GB (de 10 886 MB no yarn2r) e faltaram ~0.3 GB.
O knob reduz a falta, mas não a elimina.

**Braço n2o2 (`--os-reserve-gib 2`, 2026-10-10, `n2o2-524288-t1.0-osr2.jsonl`, 1 rep).** Nenhum `prefill refused` no
log, nem em turno medido nem em prime. Os 5 cenários foram servidos com as needles certas (`identical` 1.00,
`append` 1.00, `tool_turn` 1.00; o `middle_mutation` não truncou desta vez). Wired pico 114.0 GB, livre mínimo
0.01 GB, compressor até 10.8 GB, swap 0. Com 1 rep, isto mostra que a reserva de 2 GB cabe neste run, não que a
recusa sumiu: a folga do macOS fica pequena e o compressor subiu. Para o perfil de 512K, `--os-reserve-gib 2` é o
knob recomendado; confirmar com mais reps antes de chamar de estável.

**n2o2 com 3 reps (2026-10-11, `n2o2-524288-t1.0-osr2x3.jsonl`): o knob não é seguro.** Nenhum `prefill refused`,
mas um `tool_turn` falhou no meio do prefill com OOM de Metal
(`kIOGPUCommandBufferCallbackErrorOutOfMemory` → `GenerationOutOfMemory`). Wired pico 120.4 GB, livre mínimo
0.01 GB, compressor até 59 GB, swap 0. Um `append` truncou em 4096 tokens e um `identical` errou needle. A recusa da
admissão protegia a memória real: baixar a reserva troca uma recusa limpa, antes do prefill, por uma falha no meio
dele. O resultado de 1 rep foi sorte. **Veredito: o perfil 512k fica com o default de `--os-reserve-gib`; 512K
segue capacidade, com recusa intermitente.** Próximo teste para reduzir a memória de verdade: `--kv-quant 4`.
