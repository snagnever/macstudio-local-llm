# Correções candidatas para os problemas da campanha (pesquisa web, 2026-10-08)

Esta nota junta, por problema, as correções, os parâmetros e os workarounds encontrados na web e no código dos
runtimes instalados. **Nenhum item foi medido no rig quando a nota foi escrita.** Resultado da Etapa F: o pin TTL 0, o header de sessão,
o `--no-memory-guard` e o `--draft-block-size 5` não corrigem os problemas. A causa do MTPLX era o prime de 1 token do
probe, e o `--prefix-cache-rungs 1024` corrige o mlx-dspark. A Etapa F
([../plan.md](../plan.md#etapa-f--ab-das-correções-2026-10-08)) testa os principais; o resultado fica em
[etapa-f-fixes.md](etapa-f-fixes.md).

## 1. MTPLX 2.12.x perde o prefix cache (m1 e m1b a 32K; m27 a 128K)

**Causa provável:** defeito conhecido do memory guard e do session bank.

- [Issue #567](https://github.com/youssofal/MTPLX/issues/567) (aberta, reproduzida em 128 GB): o shed de admissão
  não expulsa sessões ociosas com KV viva. O LRU pula as sessões ativas nos últimos 600 s
  (`DEFAULT_ACTIVE_SESSION_PIN_TTL_S`). Workarounds da issue: `MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0` ou
  `POST /admin/sessions/{session_id}/clear`.
- [Issue #454](https://github.com/youssofal/MTPLX/issues/454) (aberta): só a primeira conversa depois de um restart
  entra no bank; as seguintes re-prefilam com hit 0. Reproduzida no 2.11.1 e no 2.9.1. Sem workaround além de
  reiniciar.
- [Issue #456](https://github.com/youssofal/MTPLX/issues/456) e [PR #500](https://github.com/youssofal/MTPLX/pull/500):
  o guard media `active_bytes`, que passa do limite; o PR troca para `phys_footprint`. Não verifiquei se o PR
  entrou em release.

**Identidade da sessão.** No código do 2.12.2 (`engine_session.py`), o MTPLX resolve a sessão nesta ordem:

1. headers `x-mtplx-session-id`, `x-session-affinity`, `x-session-id`, `x-openwebui-chat-id`,
   `x-openwebui-user-id`;
2. campos de metadata `session_id`, `mtplx_session_id`, `chat_id`, `conversation_id`;
3. o campo `user`;
4. casamento pelo prefixo mais longo, com sessões `anon-…`.

As integrações oficiais (OpenCode, Pi) mandam `x-mtplx-session-id`. O `cache_probe.py` mandava só `Content-Type`,
então cada request do probe caía no passo 4.

**Knobs:**

| knob | fonte | efeito esperado |
| --- | --- | --- |
| `MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0` | #567; `session_bank.py` ("0 disables") | o LRU pode expulsar sessões ociosas |
| header `x-mtplx-session-id` por conversa | `engine_session.py` | o bank liga a request à sessão certa |
| `MTPLX_CLEAR_CACHE_AFTER_REQUEST=off` | [release 2.12.1](https://mtplx.com/releases/2.12.1) | mantém o buffer pool da GPU entre requests |
| `--memory-limit max` (ou `96G`) | release 2.12.1 | usa a RAM fora da reserva do macOS |
| `--paged-kv-quantization q8` | `--help` do 2.12.2 | KV menor; muda uma segunda variável contra o n2 |
| `MTPLX_SESSION_BANK_MAX_BYTES`, `_PER_SESSION_BYTES`, `_MAX_ENTRIES`, `_SHED_BOUNDARIES`, `_PROTECTED_TERMINAL`, `MTPLX_SESSION_STORE_ON_PREFILL` | código do 2.12.2 | tamanho e política do bank |

## 2. MTPLX recusa 128K com HTTP 507 (teto de 114 688 tokens)

- `--paged-kv-quantization q8`: a própria mensagem do 507 sugere ("or use q8 KV quantization").
- `--memory-limit max`: o `96G` não mudou o teto; o `max` não foi testado.
- `--context-window 114688`: serve só para uso real abaixo de 112K.

## 3. mlx-serve + DFlash2 perde decode a 128K (r27: 37.0 → 15.5 tok/s)

- `--draft-block-size 5`: a orientação da z-lab para alvos quantizados no MLX é bloco ≤ 5
  ([qwen38-dflash2-bench](https://github.com/chengyixu/qwen38-dflash2-bench)). O r27 rodou com o bloco 8 do config
  do drafter. No 26.10.1 a flag só reduz o valor ("an explicit value only clamps it DOWN").
- [PR #754](https://github.com/ddalcu/mlx-serve/pull/754) (merge em 2026-10-07, depois do 26.10.1): corrige o dtype e
  o load do DFlash2 e acelera o verify no M4. Mediu +78% no M4 base; sem dados de M4 Max nem de contexto longo.
- Drafter em 4-bit: receita do benchmark de referência. Não testado.
- [Issue #551](https://github.com/ddalcu/mlx-serve/issues/551) (aberta): o decode do 27B no mlx-serve cai com o
  contexto, contra o Splash do LM Studio.
- `--max-mtp-ctx` vale só para MTP, não para DFlash.

## 4. r27 errou 1 needle a 128K (`middle_mutation`)

Sem achado na web. Foi 1 erro em 39 a `temperature=1.0`. Leitura provável: ruído de amostragem. Teste: repetir o
`middle_mutation` a 128K.

## 5. mlx-dspark: reuso parcial no `append` a 32K (s27, hit 0.87)

Pelo `--help` do 0.20.3:

- `--no-memory-guard`: o guard (ligado por default) libera snapshots do prefix cache quando o macOS reporta pressão
  de memória. Isso explica um reuso parcial.
- `--prefix-cache-dir` + `--prefix-cache-max-ram-mb`: camada de cache em SSD. O s27 rodou só com RAM.
- `--mode dspark` (+ `--drafter-window`): o `doctor` recomenda esse modo nesta máquina. Não casa com o r27.

## 6. ds4 upstream: decode de 53.5 tok/s

- `--mtp-draft N`: default 1. Um draft maior pode subir o decode; a
  [doc do Qwen3.8](https://github.com/antirez/ds4/blob/main/docs/QWEN38_FLASH_NEXT.md) não recomenda valor.
- O ds4 aceita drafts gulosos que casam por default, inclusive com temperatura > 0. `--mtp-exact-sampling` iguala a
  regra dos outros runtimes, mas tende a baixar o decode.
- `--prefill-chunk` (default 8192) e `--mtp-margin` também existem.

## 7. n2 a 512K: `PrefillDoesNotFit` no `identical`

Sem achado na web. O log dá a causa: o prefill precisa de ~14.1 GB, restam ~13.6 GB, e ~8.95 GB ficam presos pelo
prefixo da própria request. Saída provável: `--prefix-cache-mem 8GB` só no perfil 512k, ou um `--prefill-chunk`
menor (`QWEN38_MLX_PREFILL_CHUNK`).

## 8. Harness e ambiente

- Aliases do ds4: resolvido com `MODEL_ID_PREF` (commit da campanha).
- Download do ds4 sem `hf`: a correção oficial é `pip install -U huggingface_hub hf_xet`. A campanha usou o `hf` do
  venv do oMLX.
- Truncamento em 4096 tokens: subir o `max_tokens` do probe. O card do modelo já diz que prompts difíceis pedem mais.
- Telemetria: a aceitação do oMLX está no boot log (`accept=x/y`) e cabe num parser como o `attach_mtp.py`. O valor
  que o harness lê do `/metrics` do MTPLX não é a taxa de aceitação.

## Fontes

- MTPLX: [#567](https://github.com/youssofal/MTPLX/issues/567), [#454](https://github.com/youssofal/MTPLX/issues/454),
  [#456](https://github.com/youssofal/MTPLX/issues/456), [PR #500](https://github.com/youssofal/MTPLX/pull/500),
  [#525](https://github.com/youssofal/MTPLX/issues/525), [2.12.1](https://mtplx.com/releases/2.12.1),
  [2.12.2](https://mtplx.com/releases/2.12.2), [releases](https://github.com/youssofal/MTPLX/releases),
  [CHANGELOG](https://github.com/youssofal/MTPLX/blob/main/CHANGELOG.md)
- mlx-serve: [PR #754](https://github.com/ddalcu/mlx-serve/pull/754), [#551](https://github.com/ddalcu/mlx-serve/issues/551)
- DFlash: [qwen38-dflash2-bench](https://github.com/chengyixu/qwen38-dflash2-bench), [z-lab/dflash](https://github.com/z-lab/dflash),
  [mlx-swift-lm PR #607](https://github.com/ml-explore/mlx-swift-lm/pull/607)
- ds4: [QWEN38_FLASH_NEXT.md](https://github.com/antirez/ds4/blob/main/docs/QWEN38_FLASH_NEXT.md)
