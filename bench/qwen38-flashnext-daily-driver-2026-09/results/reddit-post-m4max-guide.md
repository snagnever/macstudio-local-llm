# Reddit post draft: the M4 Max guide

Page: https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-m4max-guide.html
Image for the post: `reports/assets/qwen38-flashnext-m4max-guide-post.png` (1400×1400 at 2×, four charts). Link-preview card: `reports/assets/qwen38-flashnext-m4max-guide-card.png`.
Carousel (gallery post, 9 square slides at 2400×2400): `reports/assets/slides/01-cover.png` … `09-conclusion.png`.
Subreddits, in order: r/LocalLLaMA (847k) first; r/LocalLLM (242k) one day later with a different opening line;
r/MacStudio (46k) with the hardware angle; r/oMLX (6k) is optional, oMLX is the runner-up there.

## Title

I benchmarked 4 stacks to serve Qwen3.8-Flash-Next on an M4 Max 128 GB to find the best for me, based on real agent interaction time

## Body

Four runtimes focused on speed (mlx-serve, oMLX, MTPLX, antirez's ds4), the same model, using weights released by its authors, contexts from 8K to 512K.

I measured what you wait for in an agent session, not only tokens per second: the time of one agent turn (TTFT on the
next turn + 512 tokens of reply), the prefix cache hit, and the memory the server locks.

TL;DR

- mlx-serve + ddalcu iQ-MLX 4.7 bpw had the shortest agent turn at every size: 8.8 s at 128K, 13.0 s at 512K.
- At 512K, the first message takes 13 min to prefill. With a cache hit, the next reply starts after 3.9 s.
- A 95% cache hit is not enough at long context: ds4 hits 94.5% at 512K and still prefills ~29K tokens, so its next reply starts after 50 s.
- MTPLX decodes almost as fast as mlx-serve at 128K (70 vs 74 tok/s) but its turn takes 15.1 s against 8.8 s. Decode speed is not the whole story.
- Peak memory: 97–114 GB locked by mlx-serve from 32K to 512K, no swap.

Caveats: one machine, one test prompt, 1 to 3 runs per point, each server on its own quant (4.7 to 5.97 bpw). It is a
personal test for my own daily use, not a lab benchmark. Commands, data and scripts are on the page.

Full page with charts and all values: <link>
