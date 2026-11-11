# Task 0: Smoke (2026-11-11)

**O smoke passa.** Os 5 braços saem com `rc=0`. A 1.5.0 sobe com `--offline` depois de um boot da 1.6.1, e o snapshot `0142554` fica com o mesmo tamanho em todos os boots. Os dois requests do `k2c2a` decodificam juntos na 1.6.1.

Fila: `logs/chain-t0.sh`, de 14:48 a 15:04 (relógio do rig). O servidor do usuário parou no início e voltou no fim.

| # | braço | release | contexto | até `pronto` | wall do braço | resultado |
|---:|---|---|---:|---:|---:|---|
| 1 | `k2h` cold | 1.6.1, PLE `auto` | 32768 | 35 s | 81 s | needle correta; cold TTFT 33.1 s |
| 2 | `k2f` cold | 1.5.0 | 32768 | 143 s | 197 s | needle correta; cold TTFT 34.6 s |
| 3 | `k2h` cold, `--ple-memory off` | 1.6.1 | 32768 | 28 s | 72 s | needle correta; cold TTFT 33.1 s |
| 4 | `k2c2a` 1 rep | 1.6.1 | 32768 | 21 s | 251 s | streams e gerador auxiliar com exit 0 |
| 5 | `rc1` tarefa `a` | 1.6.1 | 131072 | 137 s | 213 s | `task_done` true, 38.4 s, 6 requests |

- **Primeiro start da 1.6.1:** o warm-up tem 10 passos (`Warming up · 10 of 10 steps`), e o servidor fica pronto em 35 s. Ele não passa dos minutos que as notas citam para um M5 Pro.
- **Snapshot `0142554`:** 96278696 KiB antes e depois de cada boot. O update não apagou arquivos que a 1.5.0 lê.
- **PLE:** com `auto`, o boot registra que a tabela `per_layer_token_embd.weight` deixa 27465 MiB no SSD, com cache de linhas de 237 MiB. Com `--ple-memory off`, essa linha não aparece, e a tabela fica na RAM.
- **Dois streams na 1.6.1:** o `/status` do `k2c2a` conta 82 lotes de decode com largura 2 e 1504 com largura 1.
- **Log da 1.6.1:** as linhas têm `request N` depois de `Started ·` e de `Done ·`. A fixture [`tests/fixtures/splash-161-log.txt`](../tests/fixtures/splash-161-log.txt) guarda 3 pares delas.
- **Tracebacks do `attach_memory.py` e do `attach_mtp.py`** nos braços 4 e 5: esses passos procuram um JSONL único, e os braços de concorrência gravam um arquivo por stream ou por sessão. As filas da splash16 já filtravam essas linhas. Eles não mudam o resultado.
- **Livre mínimo:** 0.06 a 0.07 GB nos três braços cold, com swap Δ zero. O plano trata o livre mínimo como registro, não como gate.
