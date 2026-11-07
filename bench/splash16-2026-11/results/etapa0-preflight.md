# Etapa 0 — pré-voo e smoke (2026-11-07)

## Rig

| componente | valor |
|---|---|
| macOS | 26.6.2 |
| Disco livre | 728 GB |
| Claude Code | 2.1.292, igual aos baselines |
| `http_proxy` no ambiente da sessão SSH | nenhum |
| Swap antes da campanha | 1.75 GB em uso; os gates medem o delta |
| `gh` no rig | login inválido; a campanha não depende dele no rig |

**Servidor encontrado na porta 8585:** Splash 1.5.0 com o `k2` a 262144, iniciado em 06/11 às 18:32, ocioso. A porta 11234 estava livre. O usuário autorizou parar esse servidor em 07/11. O comando para religar:

```bash
~/.local/opt/qwen38/splash-v1.5.0/bin/splash serve --model ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS --port 8585 --host 0.0.0.0 --no-webui --max-context 262144 --idle-release off
```

## Splash 1.6.0

- Instalado em `~/.local/opt/qwen38/splash-v1.6.0/`. SHA-256 `da3aef0a…e5c4`, conferido com o digest da release.
- `splash --version`: `Splash 1.6.0`. Help em [splash-160-help.txt](splash-160-help.txt).
- A lista de flags de `serve` é igual à da 1.5.0.

## Smoke

| ordem | braço | versão | da subida até pronto | resultado |
|---:|---|---|---:|---|
| 1 | `k2g` 32K | 1.6.0 | 51 s | sobe com `--offline`; cold OK |
| 2 | `k2f` 32K | 1.5.0 | 28 s | sobe com `--offline`; cold OK |
| 3 | `k2g` 32K | 1.6.0 | 27 s | sobe com `--offline`; cold OK |
| 4 | `k3g` 32K | 1.6.0 | 111 s | o GSQ-RCO-Coder carrega; cold OK |
| 5 | `k2c2a` 32K | 1.6.0 | 148 s | `decode_batches_by_width` b2 = 64: batch confirmado |
| 6 | `k2g` 256K, 1 sessão | 1.6.0 | 27 s | prompt de 191021 tokens, dentro de ±2% |

- **Troca de versão:** o log mostra `Installing` em cada start depois de uma troca de versão. A troca custa segundos, então o ABBA é viável sem correção.
- **Triagem de GGUF:** a 1.6.0 aceita o `k2` e o `k3`.
- **Amostras do `/status` no `k2c2a`:** a amostra a cada 10 s viu no máximo 1 request em decode. O contador `b2` é a medida válida de batch, porque as janelas são curtas.
- **Sessão de 191K:** TTFT 257.7 s, decode 104.8 tok/s, maior gap 0.04 s.
- **Ruído da sonda curta:** com 1 rep, a sonda mediu 106.2, 98.6, 92.6 e 110.8 tok/s na mesma sessão, sem pool cheio. Esse intervalo é próximo do limite de 0.85. Por isso, a Task 3 usa 3 reps por sonda e repete o par com maior diferença antes do veredito.
- **Traceback no log:** o `attach_memory` falha nos braços com `--exec`, que não geram o arquivo do `cache_probe`. Os dois scripts rodam com `|| true`, e os braços saem com exit 0.

Fontes: [k2g-32768-t1.0-smoke1.jsonl](k2g-32768-t1.0-smoke1.jsonl), [aging-smoke.jsonl](aging-smoke.jsonl).
