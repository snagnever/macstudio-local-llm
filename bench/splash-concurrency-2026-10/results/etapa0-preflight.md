# Etapa 0 — pré-voo (2026-10-29)

## Rig

- A sessão "Atualizações de stack preferidas" parou o Terminal-Bench do `w1z` às 09:56 CET, em 51 de 89 tarefas. Ela retoma quando esta campanha avisar.
- O checkout desta campanha no rig é um worktree próprio: `~/LocalProjects/macstudio-local-llm-splashconc`. O checkout principal fica na branch da outra sessão, com o waiter `wait-t5r.sh` dela.
- macOS 26.6.2, M4 Max 40 GPU cores, 128 GB. Disco: 632 GB livres.

## Splash 1.5.0

- Instalado em `~/.local/opt/qwen38/splash-v1.5.0/` a partir do `splash-1.5.0-arm64-macos26.tar.gz` da release. SHA-256 `1ddc28bf…d6ee2`, igual ao `.sha256` da release. A 1.4.0 e a 1.4.1 não mudaram.
- O tarball já traz o Python com as dependências. O `bin/splash` é o mesmo wrapper da 1.4.1.
- `splash --version`: `Splash 1.5.0`. Help completo em [splash-150-help.txt](splash-150-help.txt).
- Flags da campanha: `--queue-size` (default 32), `--decode-share` (default 0.5) e `--verify-rows` (default `auto`). Não existe `--max-concurrent`.

## `/status`

`GET /status` devolve JSON (`schema_version` 6). Os campos que a campanha usa:

- `scheduler`: contagem de requests por fase (`queued`, `waiting_resources`, `prefilling`, `decoding`, ...);
- `active_requests`: uma linha por request, com `phase`, `prompt_tokens` e `prompt_processed`;
- `admission`: `waiting_memory`, `waiting_concurrency`, `held_behind_refusal`, `oldest_wait_ms`.

O `run-parallel-probes.sh --status-url` grava uma amostra a cada 10 s em `logs/<arm>-<ctx>-<tag>-status.jsonl`.

## Smoke de batch (`k2c1` a 32K, `scripts/batch_smoke.py`)

| tentativa | prompt | saída | resultado |
|---|---:|---:|---|
| 1 | ~21.7K tokens | 1 frase | sem conclusão: o decode de cada request durou < 1 s |
| 2 | ~2K tokens | 1024 tokens | **batch confirmado**: `max_decoding` 2, janelas de decode sobrepostas |

Leitura:

- **O prefill é serial.** Na tentativa 1, o request 2 ficou em `queued` enquanto o request 1 fazia o prefill (`prefilling` 1, `queued` 1). O prefill do request 2 começou só depois do fim do prefill do request 1.
- **O decode é em batch.** Na tentativa 2, os dois requests decodificaram juntos a 44 e 54 chunks/s (stream SSE; com o DFlash2 um chunk pode ter mais de um token). Sozinho, o `k2a` decodifica a ~107 tok/s a 32K (1.4.0). A soma fica perto do decode solo, como no mlx-serve. A Etapa 1 mede isso com o `cache_probe`.

Arquivo: [etapa0-batch-smoke.jsonl](etapa0-batch-smoke.jsonl) (tentativa 2).

## Decisão

O Splash faz batch para o Flash-Next. A campanha segue para a Etapa 1.
