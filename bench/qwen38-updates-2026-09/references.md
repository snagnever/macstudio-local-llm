# Inventário das atualizações Qwen — setembro 2026

> Levantado em 2026-09-12 por busca na web, API do Hugging Face e r/LocalLLaMA.
> Marcar a procedência de cada item: **release** (notas oficiais do runtime), **HF** (API do
> Hugging Face), **reddit** (r/LocalLLaMA), **web** (blog/card de terceiro).

## Runtimes

### mlx-serve — 26.9.1 (instalado) → 26.9.2

- 26.9.2, início de setembro. Declara: speculative decoding na velocidade cheia já na 1ª request
  (antes ~15ª); draft por shortlist; `--max-mtp-ctx`; `--prefix-cache-disk`. **release**
- Cuidado: parte dos ganhos usa kernels NAX de M5. Não se aplica ao M4 Max. **release**
- O que **já** está na 26.9.1 instalada, logo fora de escopo: contexto 1M (YaRN, verificado além da
  janela treinada), +10% decode (63→69 tok/s curto, 55→61 a 8,5k num M4 Max), n-gram aquecido no boot
  (1º prompt longo deixa de custar 3x). **release** (ver `../qwen38-flash-next/results/refresh-20260904-releases.json`)
- CHANGELOG: <https://github.com/ddalcu/mlx-serve/blob/main/CHANGELOG.md>
- Config de 1M usada pela comunidade no build ddalcu (mesmo pesos de vocês): **reddit**
  `--ctx-size 1048576 --kv-quant 8 --mtp --prefix-cache-mem 10GB --prefix-cache-entries 1 --ssm-checkpoint-max 16 --metrics`
  <https://www.reddit.com/r/LocalLLaMA/comments/1wb7p70/>

### MTPLX — 2.11.1 (instalado) → 2.11.2

- 2.11.2, 2026-09-06. Corrige o guard de memória para recusar antes do swap em 128 GB; visão no
  Flash-Next; flash-decoding verify gated para M5+. **release / HF**
- <https://github.com/youssofal/MTPLX/releases>

### oMLX — 0.6.4 (instalado) → 0.7.0.dev2

- 0.7.0.dev1 (10/09) e dev2 (11/09), pré-release. Declara +8–20% de prefill no Qwen3.8 com PLE via
  SSD; Flash-Next de primeira classe (qwen4_exp), oQ2–oQ8. **release / HF**
- No M2 Ultra, um usuário reporta Flash-Next oQ6-MTP a ~444 tok/s prefill e ~25 decode na 0.7 dev;
  nos comentários, mlx-serve no mesmo chip dá ~50 decode e ~250 prefill. Confirma o padrão medido no
  rig: mlx-serve ganha decode, oMLX ganha prefill. **reddit**
  <https://www.reddit.com/r/LocalLLaMA/comments/1wei63j/>
- <https://github.com/jundot/omlx/releases>

## Quants / modelos novos (mesmos autores dos que usamos)

### Trio 27B MTPLX (Youssofal) — 03/09

- `Optimized-Speed`, `Optimized-Quality`, `Bare-Speed`. Mudou só `mtplx_runtime.json`; os pesos
  (`U32 26893352960`, total `27356723952`) são os mesmos do baseline. **HF**
  (já capturado em `../qwen38-flash-next/results/quant-refresh-20260904.json`)

### DFlash2 — densa 27B

- `incoai/Qwen3.8-27B-DFlash2` e GGUF `z-lab/Qwen3.8-27B-DFlash2-GGUF`. Cabeça de draft nova para a
  densa 27B, candidata a MTP no caminho GGUF. Não testada. **HF / web**

### ddalcu Qwen3.6-35B-A3B-MLX-Serve-4bit — 08/09

- Quant nova na linha MoE 3.6, no runtime mlx-serve. **HF**

## Fora de escopo

- **Re-baixar os quants Qwen3.8 em uso:** SHA idêntico no HF. `ddalcu/…mixed-4-8bit` `ef5b919d`;
  `Jundot/…oQ4e-mtp` `2615fc0e`; `Jundot/Qwen3.8-27B-oQ8e-mtp` `c99e5aad`. **HF**
- **Qwen4:** sem release nem data. Boato aponta Apsara, 22–24/09. **web**
- **DeepSeek-V4.1-Flash:** ~763B; não cabe residente em 128 GB. Fora desta campanha (só Qwen).
