# Qwen3.8-Flash-Next vs Qwen3.8-27B: qual rodar local para código, agentes e raciocínio (outubro de 2026)

**Em qualidade, o Qwen3.8-Flash-Next (MoE de 125B com 6B ativos) supera o Qwen3.8-27B denso em quase todos os benchmarks, tanto nos da própria Qwen quanto nos independentes. Para rodar local, porém, o melhor custo-benefício depende da memória:** com uma GPU de 24–32 GB e até 64 GB de RAM, use o 27B. Com 96–128 GB de memória unificada (Mac, Strix Halo, DGX Spark) ou um PC com GPU de 24 GB+ e 128 GB de RAM, o Flash-Next passa a ser a melhor escolha, e em geral também a mais rápida.

## TL;DR
- **Nomes corretos:** não existe um "Qwen 3.8 Next" com esse nome exato. O modelo é o **Qwen3.8-Flash-Next** (pesos abertos em 26/08/2026, arquitetura `qwen4_exp`, apresentado como prévia do Qwen4). O denso é o **Qwen3.8-27B** (pesos em 14/08/2026). Nenhum dos dois tem variantes separadas Instruct/Thinking: ambos são "hybrid thinking", com `reasoning_effort` (low/medium/xhigh, sendo xhigh o padrão) e thinking desligável.
- **Qualidade:** pelos números da Qwen, o Flash-Next lidera em agentes de código (DeepSWE 1.1: 58,7 vs 42,2; SWE-bench Multilingual: 81,0 vs 73,8) e empata quase no SWE-bench Pro (62,5 vs 61,7). Em raciocínio, a vantagem é menor (GPQA 91,7 vs 89,2; HLE 35,9 vs 30,8). A Artificial Analysis confirma a ordem de forma independente: no Intelligence Index v4.3.2, o Flash-Next tem 39,82 (7º entre 118 modelos abertos) contra 34 do 27B, e no Terminal-Bench 4.0 marca 25% contra 6%.
- **Local:** o 27B em Q4 ocupa 17 GB de VRAM no Ollama (ComputingForGeeks) e cabe numa RTX 3090/4090 com cerca de 64K de contexto. Faz ~40–47 tok/s sem MTP e 102,8–113,2 tok/s com MTP numa RTX 4090 (ComputingForGeeks). O Flash-Next precisa de pelo menos 75 GB de RAM+VRAM (1-bit) e ~96–114 GB em 4-bit. Apesar do tamanho, decodifica mais rápido que o 27B em Macs de 128 GB e é ~5× mais rápido no prefill de contextos longos, porque ativa só 6B parâmetros por token e usa atenção híbrida/esparsa.

## Key Findings

### 1. Quais modelos estão sendo comparados (e por que o nome confunde)
- **Qwen3.8-Flash-Next:**
  - MoE multimodal (texto, imagem e vídeo) com 125B parâmetros no modelo principal, 6B ativos por token, 512 experts (10 roteados + 1 compartilhado).
  - Tem ainda uma tabela de **N-gram embeddings de 51B** e um módulo MTP de ~4B. Por isso a Artificial Analysis e o Hugging Face listam ~180B no total, e o vLLM, que exclui o MTP, conta 176B.
  - 48 camadas: 36 Gated DeltaNet (atenção linear) e 12 de Qwen Sparse Attention (QSA).
  - Contexto nativo de 262.144 tokens, extensível a 1M com YaRN.
  - Licença **Qwen Community License 1.0**. Uso comercial é permitido, mas serviços do tipo MaaS ou "AI work assistant" exigem licença separada.
- **Qwen3.8-27B:**
  - Denso, 64 camadas, com o mesmo padrão híbrido da Qwen3.5 (16 × [3 Gated DeltaNet → 1 Gated Attention]).
  - Encoder de visão nativo, MTP treinado, contexto nativo de 262.144 (até 1M com YaRN).
  - Licença **Apache 2.0**.
- Existe também o **Qwen3.8-Flash**, versão de produção só por API derivada do Flash-Next (1M de contexto por padrão, ferramentas embutidas). Ele não é o modelo que você roda local.
- Conflito de datas: a NVIDIA NGC e a Artificial Analysis dão 14/08/2026 para o 27B, e um agregador (Codersera) fala em 5/08. Para o Flash-Next, o repositório oficial no GitHub registra 26/08/2026.

### 2. Coding e tarefas agênticas

| Benchmark | Flash-Next | 27B | Fonte / tipo |
|---|---|---|---|
| DeepSWE 1.1 | **58,7** | 42,2 | Qwen (model card do Flash-Next): melhor resultado entre os harnesses Claude Code e mini-SWE-agent |
| SWE-bench Pro | **62,5** | 61,7 | Qwen (harness Claude Code, benchmark "refinado" pela Qwen) |
| SWE-bench Multilingual | **81,0** | 73,8 | Qwen |
| NL2Repo-Bench | **48,1** | 42,3 | Qwen |
| Toolathlon Verified (tool use) | **73,5** | 67,1 | Qwen |
| CoWorkBench / JobBench | **73,9 / 55,7** | 70,7 / 33,4 | Qwen (benchmarks internos) |
| LiveCodeBench v6 | **91,9** | 90,3 | Qwen |
| Terminal-Bench 2.1 (Terminus) | não reportado | 73,0 | Qwen. Reproduzido de forma independente pela Quesma em BF16 e Q4_K_M |
| Terminal-Bench 4.0 | **25%** | 6% | Artificial Analysis (independente; 27B em xhigh) |
| AA Coding Index | n/d | 68,1 | Artificial Analysis via OpenRouter (27B xhigh) |
| Aider Polyglot (pass_rate_2) | **74,2%** (NVFP4, no-think) | sem registro público | Usuário no fórum da NVIDIA (2× DGX Spark). Não oficial |
| SWE-bench Verified | não reportado | não reportado | A Qwen deixou de publicar esse benchmark na geração 3.8 (o Qwen3.6-27B tinha 77,2) |

**Interpretação:**
- A diferença que importa para quem usa Claude Code, OpenCode ou Cline é o **DeepSWE (+16,5 pontos)** e o **Terminal-Bench independente (25% vs 6%)**. Os dois medem autonomia em loops longos com ferramentas, e é aí que o Flash-Next se destaca.
- Em geração de código "pontual" (LiveCodeBench, SWE-bench Pro), os dois ficam praticamente empatados.
- A Featherless resume bem: o 27B é excelente para escrever funções e mediano para conduzir loops agênticos de 20 passos, com 61,7 no SWE-bench Pro contra 42,2 no DeepSWE 1.1.
- **Discrepância a notar:** o Terminal-Bench 2.1 de 73,0 do 27B (Qwen, reproduzido pela Quesma) não se compara com os 6% do Terminal-Bench 4.0 da Artificial Analysis. São versões e harnesses diferentes. Não trate um número como desmentido do outro.
- Não encontrei tau-bench nem BFCL oficiais para nenhum dos dois na geração 3.8.

### 3. Raciocínio, matemática e lógica

| Benchmark | Flash-Next | 27B | Fonte / tipo |
|---|---|---|---|
| GPQA Diamond | **91,7** | 89,2 | Qwen |
| GPQA Diamond | n/d | 88,9 (Vals AI); 90,5 (AA, xhigh); 84,5 (AA, medium) | Independente |
| Humanity's Last Exam | **35,9** | 30,8 | Qwen (juiz GPT-4o) |
| Humanity's Last Exam | **38%** | 34% | Artificial Analysis |
| CritPt (física) | **11%** | 5% | Artificial Analysis |
| SciCode | **51%** | 47% | Artificial Analysis |
| AA-LCR (raciocínio em contexto longo) | 80% | **82%** | Artificial Analysis |
| AA-Omniscience (alucinação/conhecimento) | −10 | −10 | Artificial Analysis |
| IFBench (obediência a instruções) | **81,3** | 79,5 | Qwen |
| MMLU-Pro | n/d | 84,3 (Vals AI); 85,54 (ThinkingCap, terceiro) | Independente |
| AIME 2026 / HMMT fev. 2026 | n/d | 98,13 / 95,83 | ThinkingCap (bottlecapai, terceiro, 32 e 16 seeds) |
| MathVision (sem/com CI) | **90,6 / 95,7** | 90,0 / 94,6 | Qwen |
| AA Intelligence Index v4.3.2 | **39,82** (7º de 118 abertos) | 34 (xhigh) / 26 (low) / 20 (sem raciocínio) | Artificial Analysis |

**Interpretação:**
- Em matemática pura, os dois estão perto do teto dos benchmarks de competição, e o 27B já resolve praticamente todo o AIME 2026.
- A vantagem do Flash-Next aparece em raciocínio difícil e aberto (HLE, CritPt). A Qwen não publicou AIME/HMMT oficiais para nenhum dos dois na geração 3.8, então esses números do 27B vêm de terceiros.
- Em raciocínio sobre contexto longo (AA-LCR), o 27B denso empata ou fica levemente à frente (82% vs 80%). Isso é coerente com a atenção esparsa do Flash-Next.
- O Index de 39,82 da AA é da versão v4.3.2. Números "na casa dos 50" que circulam (por exemplo, o 56 citado pelo eesel.ai) são da v4.1.1 e não são comparáveis.
- Não encontrei avaliações de LiveBench nem de ARC-AGI para nenhum dos dois.

### 4. Arquitetura: o que muda na prática
- **Computação por token:** o 27B lê todos os ~27B parâmetros a cada token, e por isso é limitado pela largura de banda de memória. O Flash-Next lê ~6B, cerca de 4,5× menos. Em hardware com banda moderada (Mac, Strix Halo, RAM DDR5), isso compensa o tamanho total.
- **KV cache:**
  - **27B:** só 16 das 64 camadas têm atenção completa (as outras 48 são DeltaNet com estado fixo). Mesmo assim, o KV cresce: medições da Hardware Corner em Q4 dão 18 GB a 4K, 22 GB a 64K, 26 GB a 128K e 34 GB a 256K.
  - **Flash-Next:** só 12 camadas QSA mantêm cache, comprimido 4:1. A RunAIHome mediu ~6 GiB de KV para 250K tokens.
- **Tabela de N-gram (PLE/"engram"):** são 51B parâmetros, mas cada token lê só algumas linhas. Por isso a tabela pode ficar em mmap no SSD ou na RAM sem grande perda.
  - Um teste num Mac M4 Max mostrou que, com a tabela mapeada, o pico de memória cai de 111,5 GB para 79,5 GB. O custo foi a decodificação cair de 47,1 para 40,2 tok/s.
  - A Unsloth recomenda não quantizar essa tabela abaixo de 4-bit.
- **Custo da atenção esparsa:** um avaliador no YouTube relatou alucinações do Flash-Next numa CTF de segurança com dados reais do Splunk, e as atribuiu à janela QSA de 2.048 tokens. Aumentar para 4.096 reduziu o problema. É um relato isolado, mas plausível dado o desenho do modelo.

### 5. Execução local: requisitos, quantizações e runtimes

| Item | Qwen3.8-27B | Qwen3.8-Flash-Next |
|---|---|---|
| BF16 | ~55 GB | ~355 GB |
| FP8 oficial | Sim (Qwen/Qwen3.8-27B-FP8) | Sim, 172,78 GiB. A receita do vLLM pede ≥250 GB de VRAM agregada (TP2 em GB300, TEP8 em 8×H200) |
| 4-bit | Q4_K_M ~17 GB; UD-Q4_K_XL 17,9 GB; MLX 4-bit 16,1 GB | UD-Q4_K_XL 111,3 GB (96–114 GB de memória); MLX 4-bit ~111,5 GB |
| Mínimo prático | IQ2_XXS ~8,4 GiB. 1-bit (~6 GB) existe, mas é inútil | 1-bit 75 GB; 2-bit 79 GB; 3-bit 90 GB |
| Outros formatos | NVFP4 (Unsloth, ~1,5× mais rápido que BF16), GGUF (Unsloth, bartowski, ggml-org, LM Studio), MLX, AWQ/GPTQ da comunidade | NVFP4 (RadixArk), MXFP4/GPTQ, MLX oQ4, GGUF Unsloth |
| llama.cpp | Sim (arquitetura `qwen35`), com MTP via `--spec-type draft-mtp` | Sim desde 27/08/2026 (PR #27742, `qwen4exp`). Builds antigos dão "unknown model architecture" |
| Ollama | Sim (`qwen3.8:27b`). Há issues abertas de `/v1/chat/completions` travando com tools | Só a tag MLX `:125b-mlx` (105 GB), ou seja, **só Apple Silicon** |
| LM Studio | Sim (GGUF e MLX 4-bit) | Via GGUF/MLX, desde que o motor embutido seja recente |
| vLLM / SGLang | Sim, receitas oficiais | Sim, mas pensados para servidores multi-GPU |
| MLX | Sim | Sim (mlx-vlm, mlx-serve, MTPLX) |

**Degradação por quantização:**
- **27B:**
  - A Quesma (Piotr Migdał) mediu de forma independente: Q4_K_M empata com BF16 em Terminal-Bench 2.1, GPQA Diamond e IFBench.
  - UD-Q2_K_XL perde um pouco no Terminal-Bench e gasta ~25% mais tokens.
  - 1-bit desaba para nível de chute aleatório no GPQA.
  - A Kingy relata 96,02% de concordância top-1 para o UD-Q4_K_XL.
  - Num teste independente de KLD no Hugging Face, o UD-IQ2_XXS (8,39 GiB) teve 82,98% de concordância top-1.
- **Flash-Next:**
  - O KLD da Unsloth mostra top-1 de 92,3% no UD-Q4_K_XL, 88,3% no UD-Q3_K_XL e 79,7% no UD-IQ1_M.
  - O "1-bit" do Flash-Next aguenta melhor que o de modelos densos, porque a tabela de N-gram fica em 4-bit.
  - **Cuidado com versões podadas (REAP):** no teste da kiarina, a REAP-288 (73,5 GB) acertou só 1 de 16 perguntas de conhecimento em japonês, contra 16/16 do build completo. Também reescreveu strings japonesas como chinês dentro do código.

### 6. Velocidade em hardware de consumo (medições de terceiros)

| Hardware | Qwen3.8-27B (Q4) | Qwen3.8-Flash-Next |
|---|---|---|
| RTX 3090 24 GB | 40,3 tok/s a 4K, 34,0 a 64K (Hardware Corner, sem MTP) | 19 tok/s de decode e 65 tok/s de prefill (UD-Q4_K_XL, 128 GB DDR4, `--n-cpu-moe 41`, sem MTP, HF/Unsloth). Strata com IQ3_XXS: 78 tok/s sem draft e 119,5 com draft (insiderllm, prompt de 32K; só snippet) |
| RTX 4090 24 GB | 46,2 tok/s a 4K, 38,4 a 64K (Hardware Corner). 102,8–113,2 tok/s com MTP (ComputingForGeeks) | 124 tok/s com 128 GB DDR5 (comentário no Hacker News, não verificado). ~21–27 tok/s em llama.cpp padrão com offload (relatos citados pela qwe.edu.pl) |
| RTX 5090 32 GB | 78 tok/s vazio, 71 a 32K (witcheer). ~95 tok/s sustentado no Claude Code com MTP e 128K (Medium). ~123 tok/s com vLLM NVFP4 + MTP (HF) | UD-Q2_K_XL, 128 GB DDR5: 31,9 → 12,2 tok/s de decode de 2K a 239K no llama.cpp padrão. Um fork com cache de experts fez 47–62 tok/s (HF/Unsloth) |
| Mac M4 Max 128 GB | 34,3 tok/s de decode (MLX 4-bit). Prefill de 217 caindo para 114 tok/s; 240K tokens levam 35,2 min | 40,2 tok/s com tabela mapeada (47,1 residente). Prefill estável em 530–580 tok/s; 240K tokens levam 7,5 min (kiarina). ~60 tok/s, 78 com MTP (mlx-serve, ddalcu) |
| Mac M5 Max 128 GB | 31,4 tok/s a 4K, 18,2 a 64K (Hardware Corner) | 63,5 tok/s de decode após prompt de 65K (MTPLX) |
| Strix Halo 128 GB | — | 22 tok/s em prosa, 66–82 tok/s em código com MTP (abliter8-ai) |
| API (AA) | 46 tok/s, TTFT 3,79 s | 51 tok/s, TTFT 2,02 s |

**O MoE é mais rápido na prática? Depende do hardware:**
- **Memória unificada:** sim. Num Mac de 128 GB, o Flash-Next decodifica 15–80% mais rápido que o 27B e lê prompts longos ~4,7× mais rápido.
- **GPU de 24 GB com offload para RAM:** usando llama.cpp padrão, normalmente não. A queda para ~15–27 tok/s deixa o 27B inteiro na VRAM com MTP (100+ tok/s) bem à frente. Motores especializados como o Strata e forks com cache de experts invertem esse quadro, mas são menos maduros.
- **Discrepância de medição:** a Hardware Corner viu o 27B na RTX 5090 cair de 74,8 para 29 tok/s a 32K, enquanto o witcheer mediu 71 tok/s a 32K. Isso provavelmente vem de diferenças de build ou configuração. Teste no seu próprio setup.

### 7. Relatos qualitativos
- **27B, pontos positivos:**
  - Simon Willison: "excelente", dirige agentes de código (Pi) com chamadas de ferramenta confiáveis e é muito bom em visão e bounding boxes.
  - O 27B tem placements independentes no Arena: 1º entre modelos abertos (7º geral) no Image-to-WebDev e 9º no Code Arena.
- **27B, problemas:**
  - O padrão `xhigh` faz o modelo **pensar demais de forma absurda**. Willison levou 21 minutos e 22.276 tokens de raciocínio num SVG, e o contexto padrão de 8K do LM Studio estoura. Ele recomenda começar em low ou sem raciocínio.
  - Há relatos de loops alucinatórios no OpenCode + MTPLX (issue #459) e de erros de template Jinja com plugins do OpenCode no llama.cpp (issue #29947).
  - O model card do Qwen3.8-27B avisa que, em tarefas agênticas multi-turno, um esforço de raciocínio menor nem sempre reduz o tempo total, por causa de falhas e retries.
- **Flash-Next, pontos positivos:**
  - Usuários no Hacker News dizem que é "way better than 27B" e que, no esforço low, é melhor e mais rápido que o 27B.
  - No teste da kiarina, resolveu 4/4 correções de repositório e 32/32 itens em japonês, contra 30/32 do 27B.
- **Flash-Next, problemas:**
  - Loops de repetição em tool loops agênticos (issue #388 do gufo).
  - Loop no token ID 0 com thinking + parser `qwen3_coder` no SGLang (issue #36537).
  - Tende a chamar ferramentas até para um "Olá", então convém desligar isso via system prompt.
  - É muito verboso: 245M tokens de saída para rodar o Index da AA, contra 198M do 27B.
  - A AA mediu um tempo por tarefa maior (1.855,56 s vs 1.095,31 s) e mais tokens de saída por tarefa (108k vs 67k), embora o custo para rodar o Index tenha sido menor ($363 vs $1.336).

## Recommendations
1. **GPU única de 24 GB (3090/4090) e até 64 GB de RAM:** use o **Qwen3.8-27B UD-Q4_K_XL ou Q4_K_M** no llama.cpp com MTP (`--spec-type draft-mtp`) e KV em q8. Use 32K–64K de contexto e `reasoning_effort` medium no dia a dia, deixando xhigh para problemas difíceis. Confiança: alta.
2. **RTX 5090 32 GB:** o 27B continua sendo a escolha principal (NVFP4 + MTP no vLLM, ou Q5/Q6 com 128K). Só migre para o Flash-Next se tiver ≥128 GB de DDR5 e aceitar usar Strata ou forks. Confiança: média-alta.
3. **Mac com 128 GB+ (M4/M5 Max, M3 Ultra), Strix Halo 128 GB ou DGX Spark:** use o **Flash-Next em 4-bit**, com tabela de N-gram em mmap se a memória estiver justa, e MTP ligado. Nessas máquinas ele é mais inteligente, decodifica mais rápido e é muito superior em prompts longos e agentes. Confiança: alta.
4. **Mac de 64–96 GB:** use o 27B (8-bit ou 4-bit). O Flash-Next só cabe em 1–2 bit e com pouca folga. Confiança: média.
5. **Agentes de código com sessões longas (Claude Code/OpenCode/Cline):**
   - Se o hardware permitir, prefira o Flash-Next (DeepSWE +16,5 pontos, Terminal-Bench independente 25% vs 6%).
   - Fixe o build do llama.cpp ou do SGLang e monitore loops.
   - Para o 27B, use o template Jinja corrigido e contexto ≥64K.
6. **Evite** versões REAP/podadas do Flash-Next fora de uso só em inglês e só para código, e evite quants de 1-bit do 27B.
7. **Uso comercial:** o 27B (Apache 2.0) é mais simples. O Flash-Next exige ler a Qwen Community License antes de usar em produtos.

## Caveats
- Quase todos os números de coding e agentes são **autorreportados pela Qwen**, muitos em benchmarks internos (CoWorkBench, JobBench, QwenSWEBench) ou "refinados" pela própria Qwen (SWE-bench Pro). As evidências independentes mais sólidas são a Artificial Analysis, a Vals AI, a Quesma (só do 27B) e o Arena (placements do 27B).
- Não há números oficiais de AIME/HMMT, SWE-bench Verified, BFCL, tau-bench, LiveBench ou ARC-AGI para a geração 3.8. O Aider Polyglot do Flash-Next (74,2%) vem de um único usuário.
- As medições de velocidade são de terceiros, muitas vezes de uma única execução, e variam bastante com build, MTP, quantização do KV e velocidade da RAM. Números de "100+ tok/s" do Flash-Next em GPUs de 24 GB dependem de motores experimentais. As estimativas de sites como willitrunai e llmcheck **não** são medições.
- O Flash-Next é oficialmente uma **prévia experimental**. O suporte em runtimes ainda está amadurecendo, com bugs de parser, de MTP e de cache de prefixo com imagens, e GGUFs antigos saíram sem a cabeça MTP.

## Fontes

### Oficiais (Qwen e parceiros)
- [Qwen/Qwen3.8-Flash-Next — Hugging Face](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
- [Qwen/Qwen3.8-27B — Hugging Face](https://huggingface.co/Qwen/Qwen3.8-27B)
- [QwenLM/Qwen3.8-Flash-Next — GitHub](https://github.com/QwenLM/Qwen3.8-Flash-Next)
- [qwen3.8-flash-next — Ollama](https://ollama.com/library/qwen3.8-flash-next)
- [Qwen3.8-Flash-Next — NVIDIA NeMo docs](https://docs.nvidia.com/nemo/automodel/model-coverage/large-language-models/qwen/Qwen3.8-Flash-Next)
- [Qwen3.8-27B — NVIDIA NGC](https://catalog.ngc.nvidia.com/orgs/nim/qwen/models/qwen3.8-27b/-)

### Avaliações independentes
- [Artificial Analysis — Flash-Next vs 27B](https://artificialanalysis.ai/models/comparisons/qwen3-8-flash-next-vs-qwen3-8-27b)
- [Artificial Analysis — Qwen3.8 27B](https://artificialanalysis.ai/models/qwen3-8-27b)
- [BenchLM — Qwen3.8-27B](https://benchlm.ai/models/qwen3-8-27b)
- [Quesma — quantizações do 27B benchmarkadas](https://quesma.com/blog/qwen38-27b-quantizations-benchmarked/)
- [bottlecapai/ThinkingCap-Qwen3.8-27B — AIME/HMMT/MMLU-Pro](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B)
- [KLD independente: unsloth/Qwen3.8-27B-GGUF discussão #49](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/discussions/49)
- [Fórum NVIDIA — Flash-Next NVFP4 em 2× DGX Spark, Aider Polyglot](https://forums.developer.nvidia.com/t/multi-agent-workload-qwen3-8-flash-next-nvfp4-on-2x-dgx-spark-174-t-s-aggregate-74-aider-polyglot-262k-context/385731)

### Execução local, quantização e velocidade
- [Unsloth — Qwen3.8-Flash-Next: how to run locally](https://unsloth.ai/docs/models/qwen3.8-next)
- [unsloth/Qwen3.8-Flash-Next-GGUF — "Share your model speed"](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/discussions/3)
- [RunAIHome — Flash-Next for local AI](https://www.runaihome.com/blog/qwen38-flash-next-local-ai-hardware-guide-2026/)
- [kiarina (dev.to) — Flash-Next num Mac de 128 GB](https://dev.to/kiarina/running-qwen38-flash-next-on-a-128-gb-mac-the-expert-pruning-trap-and-a-memory-mapped-n-gram-182m)
- [Hardware Corner — testes de GPU/VRAM do 27B](https://www.hardware-corner.net/qwen3-8-27b-hardware-tests/)
- [ComputingForGeeks — rodar o 27B local](https://computingforgeeks.com/run-qwen3-8-27b-locally/)
- [witcheer (X) — 27B na RTX 5090](https://x.com/witcheer/status/2088316316205907970)
- [Medium — 27B com Claude Code na RTX 5090](https://medium.com/@mehmetalisepici/running-qwen3-8-27b-locally-with-claude-code-on-an-rtx-5090-9ccbea8ae49c)
- [Qwen/Qwen3.8-27B discussão #132 — NVFP4 na 5090 com vLLM](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/132)
- [insiderllm — Strata vs llama.cpp na RTX 3090](https://insiderllm.com/guides/strata-vs-llama-cpp-rtx-3090/)
- [insiderllm — Best Qwen models ranked](https://insiderllm.com/guides/qwen-models-guide/)
- [Developers Digest — Flash-Next com Strata](https://www.developersdigest.tech/blog/qwen-3-8-flash-next-strata-run-locally-2026)
- [Hacker News — Flash-Next na RTX 4090 a 100 T/s](https://news.ycombinator.com/item?id=49953495)
- [qwe.edu.pl — tutorial Flash-Next na RTX 4090](https://www.qwe.edu.pl/tutorial/qwen-3-8-flash-next-rtx-4090-100ts/)
- [Startup Fortune — Strata](https://startupfortune.com/strata-lets-a-125-billion-parameter-model-run-on-a-gaming-gpu/)
- [ddalcu — Flash-Next MLX mixed 4-8bit](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit)
- [Youssofal — Flash-Next MTPLX](https://huggingface.co/Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed)
- [Kingy — VRAM e vLLM do Flash-Next](https://kingy.ai/blog/qwen3-8-flash-next-hardware-requirements-vram-vllm/)
- [Kingy — melhor GGUF do 27B](https://kingy.ai/blog/qwen3-8-27b-best-quantization-gguf/)
- [Akash — arquitetura e requisitos do Flash-Next](https://akash.network/the-bid/qwen3-8-flash-next-architecture-gpu-requirements/)
- [IntuitionLabs — arquitetura e memória do Flash-Next](https://intuitionlabs.ai/articles/qwen3-8-flash-next-architecture-memory)
- [willitrunai — Flash-Next VRAM](https://willitrunai.com/models/qwen-3.8-flash-next)
- [willitrunai — Flash-Next no M4 Max 64 GB](https://willitrunai.com/can-run/qwen-3.8-flash-next-on-m4-max-64gb)
- [LLMCheck — Flash-Next no Mac e a licença](https://llmcheck.net/blog/qwen3-8-flash-next-on-mac/)
- [redreamality — Qwen3.8 como coding agent local em 16 GB](https://redreamality.com/cn/blog/local-qwen3-8-replace-claude-code-vram-quant-harness-2026/)
- [AI Weekly — Unsloth GGUFs do 27B](https://aiweekly.co/alerts/unsloth-ships-1-bit-to-bf16-gguf-quants-of-qwen38-27b)

### Reviews e análises
- [Simon Willison — Qwen 3.8 27B is excellent, but overthinks](https://simonwillison.net/2026/Aug/16/qwen-38-27b/)
- [AceCloud — 27B vs Flash-Next](https://acecloud.ai/blog/qwen3-8-27b-vs-flash-next/)
- [Featherless — GLM-5.3-Flash vs Flash-Next vs 27B](https://featherless.ai/blog/glm-5-3-flash-vs-qwen-3-8-flash-next-vs-qwen-3-8-27b)
- [OrcaRouter — Flash-Next vs 27B: weights or throughput?](https://www.orcarouter.ai/blog/qwen-3-8-flash-next-vs-qwen-3-8-27b)
- [OrcaRouter — which open Qwen to run?](https://www.orcarouter.ai/blog/qwen-3-8-next-vs-qwen-3-8)
- [OrcaRouter — 27B benchmarks](https://www.orcarouter.ai/blog/qwen-3-8-27b-benchmarks)
- [Codersera — Qwen 3.8 model lineup](https://codersera.com/blog/qwen-3-8-model-lineup-2026/)
- [Codersera — Qwen 3.8 Flash guide](https://codersera.com/blog/qwen-3-8-flash-complete-guide-2026/)
- [DataCamp — Flash-Next features e benchmarks](https://www.datacamp.com/blog/qwen3-8-flash-next)
- [eesel.ai — Flash-Next review](https://www.eesel.ai/blog/qwen38-flash-next-review)
- [sozai — Flash-Next hallucination fix (transcrição)](https://sozai.app/transcript/qwen38-flash-next-hallucination-fix/)

### Issues em runtimes
- [llama.cpp #29947 — 27B + OpenCode, erro de template](https://github.com/ggml-org/llama.cpp/issues/29947)
- [MTPLX #459 — 27B MTP3 em loops no OpenCode](https://github.com/youssofal/MTPLX/issues/459)
- [gufo #388 — Flash-Next, loops em tool loops agênticos](https://github.com/gufo-org/gufo/issues/388)
- [SGLang #36537 — Flash-Next thinking + qwen3_coder parser](https://github.com/sgl-project/sglang/issues/36537)