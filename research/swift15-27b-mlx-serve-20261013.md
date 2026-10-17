# Swift 1.5 27B no mlx-serve 26.10.x: packs, compatibilidade e braço proposto (13/10/2026)

**Resposta curta.** Existe pack MLX do Swift 1.5 27B que o mlx-serve 26.10.2 deve carregar com MTP, mas **ninguém publicou número de Swift 1.5 27B no mlx-serve**, e o rig também não mediu. O melhor candidato é o `scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp` @ `881dc1914f65`, que **já está no disco do rig** (download zero). O código do mlx-serve trata explicitamente trunks oQ4e densos com cabeça MTP embutida e detecta a convenção das normas da cabeça [vendor]. O rig confirmou que a cabeça MTP do pack Swift é a do base (fc e normas idênticos byte a byte ao pack Jundot do base) [verified on rig]. A compatibilidade de carga, a aceitação MTP e a aceitação do DFlash2 sobre o Swift **não estão verificadas** no mlx-serve. Um smoke de 8K responde as três perguntas.

Legenda: **[vendor]** = autor do runtime, do pack ou do modelo; **[community]** = terceiros (HF de usuários, issues, leaderboard); **[verified on rig]** = checado neste repo no Mac Studio M4 Max 128 GB, só leitura.

## 1. Packs MLX do Swift 1.5 27B no Hugging Face

Busca na API do HF (`search=Swift-1.5|Swift1.5|Swift 1.5`, com e sem `filter=mlx`) em 13/10. Tamanho = soma dos `.safetensors`. "MTP" = chaves `mtp.*` no índice.

| Repo @ rev | Data | Formato | Tamanho | MTP | Observação |
|---|---|---|---|---|---|
| [scottlowry/…-27b-oQ4e-mtp](https://huggingface.co/scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp) @ `881dc1914f65` | 12/10 | oQ4e (oMLX 0.7.1.dev1, refit): affine 4-bit gs64 + 166 tensores a 5-bit; ~4.9 bpw | 16.97 GB | sim, 29 chaves `language_model.mtp.*`, quantizada | **No rig** [verified on rig] |
| [scottlowry/…-27b-oQ5e-mtp](https://huggingface.co/scottlowry/Swift-1.5-Qwen3.8-27b-oQ5e-mtp) @ `4e318a235c61` | 12/10 | 5-bit + overrides 6/8 | 20.29 GB | sim | [community] |
| [scottlowry/…-27b-oQ6e-mtp](https://huggingface.co/scottlowry/Swift-1.5-Qwen3.8-27b-oQ6e-mtp) @ `5612c1068a36` | 12/10 | 6-bit + 33 a 8-bit | 23.72 GB | sim | [community] |
| [scottlowry/…-27b-oQ8e-mtp](https://huggingface.co/scottlowry/Swift-1.5-Qwen3.8-27b-oQ8e-mtp) @ `c7dfaa06079e` | 12/10 | 8-bit gs64 uniforme | 30.00 GB | sim | Par natural do ddalcu 8bit (r27d/r27m) [community] |
| scottlowry `-fp16-mtp` (oQ4e/5e/6e/8e) | 12/10 | idem, tensores sensíveis em fp16 | idem | sim | Para M1/M2; o M4 Max usa a variante bf16 [community] |
| [dicksondickson/…-oQ5e/6e/8e-bf16-mtp-MLX](https://huggingface.co/dicksondickson/Swift-1.5-Qwen3.8-27b-oQ6e-bf16-mtp-MLX) (`f1e9409e`, `a71e37ae`, `d8a5b019`) | 29/09 | oMLX 0.7.0rc1, **antes do refit** | 20.3 / 23.7 / 30.0 GB | sim | Superados pelos scottlowry de 12/10 [community] |
| [yottle/…-27b-oQ4e-mtp](https://huggingface.co/yottle/Swift-1.5-Qwen3.8-27b-oQ4e-mtp) @ `cc32ae870716`; jongstra fp16 | 24–26/09 | oQ4e pré-refit | 16.97 GB | sim | Superado [community] |
| [billziss/…-27b-oQ8e-mtp](https://huggingface.co/billziss/Swift-1.5-Qwen3.8-27b-oQ8e-mtp) @ `80b81b65ded8` | 26/09 | oQ8e pré-refit | 30.00 GB | sim | [community] |
| [ukisai/Swift-1.5-4bit-MLX](https://huggingface.co/ukisai/Swift-1.5-4bit-MLX) @ `82276731e47e` (e 5bit `79bf5dd3`) | 25/09 | mlx-lm affine 4-bit gs64 uniforme | 15.83 GB (5bit 19.28) | chaves `mtp.*` sem prefixo `language_model.`, `mtp.fc` quantizado | O card exige patch do mlx-lm 0.32.0 (rejeita 501 entradas de visão) e não declara MTP especulativo de ponta a ponta [vendor] |
| [ukisai/Swift-1.5-3bit-MLX-TextOnly](https://huggingface.co/ukisai/Swift-1.5-3bit-MLX-TextOnly) | 24/09 | 3-bit | 11.77 GB | **não** | [vendor] |
| [GazTrab/…-RCO-DWQ-MLX](https://huggingface.co/GazTrab/Swift-1.5-Qwen3.8-27b-RCO-DWQ-MLX) @ `a01865942890` | 02/10 | ~3-bit misto RCO+DWQ | 13.53 GB | sim, mas o próprio card mede **0 de 22 drafts aceitos** no oMLX e texto quebrado no LM Studio | [community] |
| [AutomatosX/AX-Swift-1.5-…-MXFP4-MTP](https://huggingface.co/AutomatosX/AX-Swift-1.5-Qwen3.8-27B-MLX-AXQ-MXFP4-MTP) @ `f05ba22fbfe3` (e MXFP8 `4a24d2af`) | 13/10 | mxfp4 gs32, 4.84 bpw | 17.41 GB (+0.85 GB `mtp.safetensors`) | sidecar bf16 | Publicado hoje, sem número de velocidade; suporte a `mode: mxfp4` em modelo denso no mlx-serve não verificado [vendor] |
| [SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash](https://huggingface.co/SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash) @ `44c96f13` | 26/09 | formato Splash (repack do ukisai 4bit) + DFlash2 do base | 17.4 GB | drafter DFlash2 | Só Splash/LM Studio; não carrega em MLX [vendor] |

Os repos `Swift-Qwen3.8-27b-*` sem "1.5" (majentik, npario, kylar, andosen, airagrp) são do **Swift 1.0** e ficam fora. **Não existe pack ddalcu "MLX-Serve" do Swift 1.5 27B** (lista do autor no HF, 13/10); a ddalcu publica só o base (4bit, 6bit, 8bit, iQ-3.8bpw) [vendor]. Também não existe o equivalente ao Dankpaws 4.7bpw do Flash-Next para o 27B.

## 2. O que o mlx-serve 26.10.2 carrega e quais caminhos de especulação servem a um fine-tune

**Formato.** Os packs oQ densos são safetensors MLX padrão: `quantization` com `mode: affine`, `group_size` 64 e overrides por camada (`bits` 5, 6 ou 8) [verified on rig]. As normas do trunk do pack Swift oQ4e já vêm com o `+1` dobrado, iguais às do ddalcu 8bit e do mlx-community 8bit [verified on rig]. A diferença está na cabeça MTP: o ddalcu guarda as normas da cabeça em delta (`mtp.norm` média 1.16), e o oQ guarda dobradas (média 2.16, exatamente +1.0) [verified on rig]. O `src/mtp.zig` do mlx-serve detecta a convenção pela fração de pesos negativos e só soma `+1` quando a norma está em delta (`mtpNormsAreDeltaEncoded`, limiar 0.05) [vendor]. O mesmo arquivo diz que "oMLX oQ4e-class conversions ship `[language_model.]mtp.*` in the trunk shards" e tem um perfil de custo próprio para "mixed-q4/q5/q6 oQ4e trunks" (`g17_nax_oq4e_q4_gs64`, só para M5 NAX; no M4 cai em `generic`) ([mtp.zig](https://github.com/ddalcu/mlx-serve/blob/v26.10.2/src/mtp.zig)) [vendor]. O doc de gotchas do mlx-serve cita o `jundot-oQ4e` como barra de KL no shootout do 27B e explica que um loader sem detecção "drafts at ~0% acceptance while looking healthy" ([models-media.md](https://github.com/ddalcu/mlx-serve/blob/main/docs/gotchas/models-media.md)) [vendor]. As notas do 26.10.2 citam carga nativa dos packs oMLX **do Flash-Next**; não citam o 27B denso ([release v26.10.2](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.2)) [vendor]. A PR #665 mostra o risco concreto: um pack oQ do Swift Flash-Next carregava e gerava lixo com 0 de 26 drafts aceitos até corrigir as normas ([PR #665](https://github.com/ddalcu/mlx-serve/pull/665)) [community]. A issue #120 mostra o outro risco: chaves MTP com prefixo inesperado são ignoradas em silêncio e o servidor cai para PLD ([#120](https://github.com/ddalcu/mlx-serve/issues/120)) [community]. Conclusão: a carga do oQ4e denso com MTP é **provável pelo código, não verificada no rig**.

**MTP.** O mlx-serve carrega a cabeça MTP sozinho quando ela está no checkpoint; `--no-mtp` desliga e a prioridade é MTP > DFlash > drafter > PLD (`mlx-serve --help`, [mlx-serve-26102-help.txt](../bench/qwen38-27b-next-steps-2026-10/results/mlx-serve-26102-help.txt)) [verified on rig]. A cabeça MTP do Swift 1.5 é a do base sem retreino: o card da ukisai diz que os pesos "include the base model's MTP head" ([card](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)) [vendor], e no rig `mtp.fc.weight` (bf16), `mtp.norm` e `mtp.pre_fc_norm_hidden` têm o mesmo SHA-256 no Swift oQ4e e no Jundot oQ4e do base. As projeções quantizadas diferem só pela calibração [verified on rig]. As normas do trunk também são idênticas; o fine-tune mudou as matrizes lineares [verified on rig]. A aceitação deve cair um pouco, porque o trunk muda e a cabeça não. Ninguém publicou o número no mlx-serve.

**DFlash2.** O drafter `incoai/Qwen3.8-27B-DFlash2` lê os estados ocultos das camadas 5, 19, 33, 47 e 61 de um alvo de 64 camadas (`drafter/config.json` no pack ddalcu) [verified on rig]. Ele foi treinado no base, mas a arquitetura do Swift é idêntica. O mlx-serve aceita um drafter externo com `--drafter <dir>` [vendor]. O pacote Splash do Swift 1.5 usa o mesmo DFlash2 e mede **aceitação 0.44**, igual à do Swift 1.0, num M5 Max sob Splash 1.0.2. O card não traz o número do base para comparar ([card Splash](https://huggingface.co/SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash)) [community]. No rig, o r27d (base 8bit + DFlash2) registrou aceitação 0.788 a 8K na métrica do harness, e o r27m (só MTP, profundidade 3) registrou 0.888 ([etapa1-smokes.md](../bench/qwen38-27b-next-steps-2026-10/results/etapa1-smokes.md), jsonl) [verified on rig]. As duas métricas não são comparáveis com a do Splash.

**Outros caminhos.** A `--mlx-gguf` serve GGUF do Qwen3.8 denso no motor MLX [vendor], e existem GGUF do Swift 1.5 27B (ex.: `ukisai/Swift-1.5-Qwen3.8-27B-GGUF`, `jordi123/…-i1-GGUF`) [community]. O braço GGUF fica fora deste escopo.

## 3. Números publicados de velocidade

- **mlx-serve + Swift 1.5 27B: nenhum número publicado.** A busca no HF, nas issues do mlx-serve, no Google e no r/LocalLLaMA (100 posts novos) não achou nenhum.
- oMLX 0.7.0rc1, M5 Max 40c 64 GB, Swift oQ4e-mtp (pré-refit), Lightning MTP profundidade 3, thinking off, 4K: **PP 977 tok/s, TG 70.9 tok/s, TTFT 4.2 s**, pico 19.5 GB ([omlx.ai w09nk2iy](https://omlx.ai/benchmarks/performance/w09nk2iy), 29/09) [community]. Não há linha de M4 Max para o Swift.
- Splash 1.0.2, M5 Max 128 GB, Swift 1.5 4-bit + DFlash2: **decode 75–84 tok/s** em respostas de 1024 tokens, prefill 993/920/825/723 tok/s a 2K/8K/31K/62K, aceitação 0.44 ([card Splash](https://huggingface.co/SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash)) [community].
- mlx-serve 26.9.5, M3 Max 48 GB: o base ddalcu 4bit deu 59.6 tok/s contra 96.4 do Swift-Splash. O mantenedor disse que a comparação misturava checkpoints, drafters e KV. Depois, com `--kv-quant 8` e DFlash, o autor mediu ~91.5 tok/s ([#551](https://github.com/ddalcu/mlx-serve/issues/551)) [community].
- Base 27B no mlx-serve, M4 Max 128 GB, temp 0: o 4bit faz **75.3 tok/s** com MTP e o 8bit **53.6** em "write a class" ([card ddalcu 8bit](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-8bit)) [vendor].
- Rig, smoke de 8K: r27d 83.6, r27m 51.5, o27q4 (oMLX + Jundot oQ4e do base) 81.4 tok/s [verified on rig].

## 4. Recomendação

**Pack.** `scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp` @ `881dc1914f65e37a51f1e26dc0b6a49995e6cf37`, já presente em `~/.cache/local-llms/qwen3.8-prefix-cache/scottlowry-Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc1914f65e37a51f1e26dc0b6a49995e6cf37`. O pack não custa download, usa o mesmo quantizador do o27q4 (Jundot oQ4e refit `49c1d603`) e isola o efeito do fine-tune. O segundo passo, só se o oQ4e passar, é o `scottlowry/…-oQ8e-mtp` @ `c7dfaa06079e` (30 GB), par direto do ddalcu 8bit de r27d/r27m.

**Dois braços** em `run-candidate.sh`, copiando o bloco `r27d|r27m` com `MODEL_DIR` trocado:

| Braço | Flags do mlx-serve 26.10.2 | Compara com |
|---|---|---|
| `w27m` (Swift, só MTP) | `--no-drafter --mtp-max-depth 3` | r27m (0.888, 51.5 tok/s) e o27q4 |
| `w27d` (Swift, DFlash2) | `--no-mtp --drafter <ddalcu-27B-8bit>/drafter` (ou o diretório `incoai--Qwen3.8-27B-DFlash2` já no disco) | r27d (0.788, 83.6 tok/s) |

O resto das flags fica igual a r27d/r27m (`QWEN38_CTX_SIZE`, prefix cache, `--metrics`), com esforço `medium` via `chat_template_kwargs` e a referência `xhigh` do P4.

**O smoke de 8K precisa confirmar:**
1. `--version` = 26.10.2. O log de carga mostra a cabeça MTP lida do checkpoint (`[mtp] loaded native MTP head`, com quant por peso) e **sem** fold `+1` nas normas da cabeça. O `/props` mostra `mtp.loaded: true` em w27m e `drafter: dflash` em w27d.
2. Texto coerente: needles 10/50/90 corretos, `reasoning_chars > 0`, zero respostas vazias, zero HTTP 4xx/5xx.
3. `[spec-stats] mode=mtp` com aceitação ≥ 0.71 (0.8× r27m) e `mode=dflash` com aceitação ≥ 0.63 (0.8× r27d). Aceitação perto de 0 indica normas da cabeça aplicadas em dobro ou chaves ignoradas; nesse caso o braço para.
4. Decode mediano a 8K ≥ 84 tok/s (r27d) no melhor dos dois braços, para que valha rodar 32K/128K. Depois disso, `T_turno` contra s27r (16.7 / 25.7 s) e o tempo até a resposta final do P4.
5. Wired peak e swap Δ ≤ 0.5 GB. O pack tem 17 GB, então memória não deve limitar.

**Riscos.** A carga do oQ4e denso no mlx-serve não tem nenhuma medição pública. A cabeça MTP é obsoleta para o trunk do Swift. A aceitação do DFlash2 no Swift só tem um número (0.44, Splash, sem o base ao lado). Pela conta do plano de 13/10, o decode sozinho não fecha a distância para o Flash-Next a 128K: o termo dominante é o TTFT quente do `tool_turn` ([qwen38-27b-next-steps-20261013.md](qwen38-27b-next-steps-20261013.md)). O ganho real do Swift está em pensar menos (−58.5% de tokens de thinking no GPQA-D, segundo o fornecedor), e o `T_turno` com 512 tokens fixos não capta isso [vendor]. Licença: Swift Open License, teto de US$1M de receita [vendor].
