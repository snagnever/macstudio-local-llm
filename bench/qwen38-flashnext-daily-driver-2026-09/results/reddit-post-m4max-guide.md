# Reddit post draft: the M4 Max guide

Page: https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-m4max-guide.html
Inline images: `reports/assets/post/01-turn.png` to `06-memory.png` (2400 px wide, PNG), rendered by `render_m4max_guide.py --png`. They carry no title: the post headings name the section.
Link-preview card: `reports/assets/qwen38-flashnext-m4max-guide-card.png`.
Subreddits, in order: r/LocalLLaMA first; r/LocalLLM one day later with a different opening line;
r/MacStudio with the hardware angle; r/oMLX is optional, oMLX is the runner-up there.

## How to post with inline images

1. Open the Reddit web editor, choose **Text** post. Keep the editor in **Rich Text** mode (the default), not Markdown. Markdown mode cannot upload images.
2. Paste the body below. Tables and bold survive the paste. If a table breaks, switch to Markdown mode, paste the table block there, and switch back.
3. At each `[image: ...]` marker, delete the marker, click the **image icon** in the toolbar and upload the PNG. Reddit inserts it at the cursor. Add the one-line caption in the image's caption field.
4. Limit: 20 images per text post, 20 MB each. The slides are ~250 KB each.
5. Preview on mobile before posting. A 7-column table scrolls sideways on the app; that is fine.
6. One link only, at the end.

Fallback: if the subreddit blocks inline images, post as a **gallery** with the square slides `reports/assets/slides/03-turn.png` to `08-memory.png` and put the body in the first comment.

## Title

I tested four runtimes for Qwen3.8-Flash-Next on an M4 Max 128 GB against decode speed, cache performance, prefill and total time per agent turn.

## Body

Four runtimes for the same model: mlx-serve, oMLX, MTPLX and antirez's ds4. Each one runs the quant its author publishes for it, so this compares stacks (server + quant), not servers alone. 

I tested 8K to 512K; the numbers below are at **256K, the model's native max context**, unless stated.

I use this model as a daily driver for coding agents, so I measured what I actually wait for in a session:

* **Agent turn**: TTFT on the next turn + a 512-token reply. An agent pays this at every step.
* **Prefix cache hit** on the next turn, and how many tokens get prefilled again.
* **Prefill and decode speed.**
* **Peak memory** the server locks.

One machine, one test prompt, 1 to 3 runs per point. Personal test, not a lab benchmark.

**TL;DR**

* **mlx-serve 26.10.1 + ddalcu iQ-MLX 4.7 bpw wins overall.** Shortest agent turn at every context size. At 256K: 9.8 s per turn, 2.1 s to start the next reply from cache, 67 tok/s decode.
* **oMLX 0.7.0 is second** at 256K: 14.5 s per turn, 4.3 s TTFT, 50 tok/s. Same cache hit as mlx-serve (99.6%). It has no YaRN, so 256K is its ceiling.
* **MTPLX 2.12.2 does not reach 256K.** Its memory plan fits 237K tokens on 128 GB. At 128K it decodes at 70 tok/s but takes 15.1 s per turn, because prefill runs at 274 tok/s and TTFT is 7.8 s.
* **ds4 reaches 256K and 512K** but its turn is 30.7 s at 256K and 61.9 s at 512K. Its cache hit is 95.4% at 256K, which still means ~12K tokens prefilled again at every step.
* **The first message is slow everywhere.** A cold 256K prompt takes 5.8 min on mlx-serve, 9.2 min on oMLX, 6.8 min on ds4. What you feel in daily use is the cache hit, and there mlx-serve starts the next reply in 2.1 s.

**The four stacks**

| Stack | Quant | Disk | Prefix cache | Spec. decoding | Largest context on 128 GB |
|---|---|---|---|---|---|
| mlx-serve 26.10.1 | ddalcu iQ-MLX 4.7 bpw | 107 GB | RAM (16 GB) + disk (100 GB) | MTP + n-gram | 512K (YaRN 2.0 + 4-bit KV) |
| oMLX 0.7.0 | Jundot oQ4e-mtp 5.97 bpw | 132 GB | paged, spills to SSD | MTP | 256K (no YaRN) |
| MTPLX 2.12.2 | MTPLX Optimized-Speed 5.43 bpw | 120 GB | session bank, RAM + SSD | MTP depth 3 | 128K (`--memory-limit max`) |
| ds4 (antirez) | antirez Q4 GGUF | 177 GB | disk (100 GB) | MTP, 1 draft | 512K (YaRN 2.0) |

Same sampling everywhere: temp 1.0, top_p 0.95, top_k 20, reasoning effort xhigh, max 4,096 output tokens. All four use the model's MTP head and a prefix cache. Why these four: in October 2026 they were the servers that ran Flash-Next on Apple Silicon with MTP and a prefix cache. llama.cpp, LM Studio and mlx-vlm are not in this round.

**Agent turn time**

[image: post/01-turn.png] · caption: Agent turn per context size. Lower is better. 256K shaded.

* mlx-serve stays almost flat: 7.8 s at 8K, 8.8 s at 128K, 9.8 s at 256K, 13.0 s at 512K.
* oMLX: 9.4 s at 8K, 12.1 s at 128K, 14.5 s at 256K. Stops there.
* MTPLX: 8.2 s at 8K, 15.1 s at 128K. Refuses 256K.
* ds4: 12.7 s at 8K, 16.4 s at 128K, 30.7 s at 256K, 61.9 s at 512K.

**First message vs next turn**

[image: post/02-first-message.png] · caption: mlx-serve at 256K. Tokens prefilled again and the wait, per case.

In an agent session every step resends the whole conversation. With a cache hit the server prefills only the new part. mlx-serve at 256K:

| Case | Tokens prefilled again | Wait |
|---|---|---|
| First message (cold) | 256K | 5.8 min |
| History edited halfway (fork, compaction, new system prompt) | ~137K | 3.2 min |
| Next turn (tool result at the end) | ~1K | 2.1 s |

In daily use the context grows step by step and each step prefills only the new part, so you rarely pay the cold prefill at once. The thing to avoid is editing the history halfway.

**Cache hit rate**

[image: post/03-ttft-next-turn.png] · caption: TTFT on the next turn, with a cache hit. Lower is better.

[image: post/04-cache-miss.png] · caption: Tokens prefilled again on the next turn at 256K. Shorter is better.

* mlx-serve and oMLX both hit 99.6% at 256K and prefill ~1K tokens again. ds4 hits 95.4% and prefills ~12K.
* That 4% gap is why ds4's TTFT on the next turn is 19.9 s at 256K against 2.1 s and 4.3 s.
* Rule of thumb at 256K on this machine: each 1% of cache miss ≈ 2.6K tokens ≈ 3.5 s of extra wait.

**Decode speed vs turn time**

[image: post/05-decode-prefill.png] · caption: Decode and prefill speed per context size. Higher is better.

* Decode at 256K: mlx-serve 67, oMLX 50, ds4 48 tok/s. MTPLX at 128K: 70.
* Prefill at 256K: mlx-serve 732, ds4 630, oMLX 465 tok/s. MTPLX at 128K: 274.
* MTPLX shows why tok/s alone misleads: it decodes as fast as mlx-serve but takes 15.1 s per turn at 128K against 8.8 s. Compare on turn time and cache behavior.

**Memory**

[image: post/06-memory.png] · caption: Peak memory locked by the server, GB of 128.

* At 256K: mlx-serve 112 GB, oMLX 101 GB, ds4 96 GB. No server used swap.
* mlx-serve keeps the KV and the prefix cache in memory on purpose. Close other large apps before a long session.

**All three at 256K**

| Stack | Agent turn | TTFT next turn | First message | Decode tok/s | Prefill tok/s | Cache hit next turn | Peak memory |
|---|---|---|---|---|---|---|---|
| mlx-serve 26.10.1 | **9.8 s** | **2.1 s** | **5.8 min** | **67** | **732** | 99.6% | 112 GB |
| oMLX 0.7.0 | 14.5 s | 4.3 s | 9.2 min | 50 | 465 | 99.6% | 101 GB |
| ds4 (antirez) | 30.7 s | 19.9 s | 6.8 min | 48 | 630 | 95.4% | 96 GB |

MTPLX refuses 256K. At 128K: 15.1 s per turn, 7.8 s TTFT, 7.6 min first message, 70 / 274 tok/s, 99.2% hit, 110 GB. The 256K points are single runs; the 128K points are medians of 3 and show the same order.

**Quality sanity check**

Same model, different quants, so I checked that no stack breaks it. HumanEval (164) / tool calls A (40) / tool calls B (12): mlx-serve 158 / 35 / 10, oMLX 157 / 36 / 10, MTPLX 151 / 35 / 10. One run each, small samples. Read it as a sanity check, not a ranking. ds4 was not checked.

**The command I run**

```
mlx-serve --model ~/models/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw \
  --serve --host 127.0.0.1 --port 11234 \
  --ctx-size 262144 --mtp --ssm-checkpoint-max 16 \
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64
```

The prefix cache flags matter. With the default 2 GB cache a 128K session did not fit and every turn reread the whole prompt. 512K needs YaRN 2.0 and `--kv-quant 4`; that command and the 512K numbers are on the page.

**Tips from daily use**

* Keep the start of the prompt stable: system prompt, tool list, project rules first. A change there invalidates everything after it.
* Add to the end. A fork, a compaction or an edit of an earlier message at 256K costs about 3 min.
* Keep working in the same session. The cold prefill is paid in small parts as the context grows.
* Use the context you need. 128K runs at 8.8 s per turn, 256K at 9.8 s.

**Caveats**

* One machine, one test prompt, 1 to 3 runs per point. The 256K points are single runs. Small differences can be noise.
* Each server on its own quant (4.7 to 5.97 bpw). The quants are close but not identical.
* Speed, cache and memory only. Agent reliability over many turns is not measured.
* One request at a time. No concurrency, no power or fan noise.
* Numbers are for this M4 Max. They do not transfer to an M3 Ultra or an M5 Max.

**Bonus: Swift 1.5**

Swift 1.5 is a community fine-tune of Flash-Next that thinks less before answering. On the same mlx-serve setup it scored the same within noise (GPQA 43 vs 45 of 50, LiveCodeBench 42 vs 41, HumanEval 158 vs 158) and reached the final answer 2.9× faster on GPQA and 2.0× faster on LiveCodeBench. The agent turn is the same, because prefill and cache do not change. It is what I run now.

Full page with interactive charts, all values from 8K to 512K, the prompt generator and the scripts: https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-m4max-guide.html
