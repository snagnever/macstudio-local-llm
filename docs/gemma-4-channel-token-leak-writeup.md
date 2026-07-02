# Gemma 4 26B-A4B leaks raw `<|channel|>thought` markers and loops on Hermes

**Symptom (exact):** `gemma-4-26b-a4b-it-mlx@6bit` on Hermes emits nothing but repeated
channel headers —

```
<|channel>thought <channel|>

<|channel>thought <channel|>

<|channel>thought <channel|>
```

— and never reaches any answer. No useful text, just the markers, looping.

This looks like the 2-bit DeepSeek looping we documented, but it is **not** the same failure.
That one loops on *real content* (restarts the story/list) and is the quant quality floor. This one
loops on *structural markers* with **empty bodies** — a completely different signature. It's a
**chat-template / special-token mismatch on the client side**, and at 6-bit there is no quant excuse.

## Why this model in particular gives it away

In our lineup `gemma-4-26b-a4b` is the **"raw decode + tool-calling, no reasoning"** slot
(see [`local-llm-reference.md`](local-llm-reference.md) — fast-coder row). It was **never trained
to emit a `thought`/reasoning channel.** So when you see it produce a `thought` channel header and
nothing inside it, the model isn't reasoning badly — it's being *wrapped* in a harmony/gpt-oss-style
channel template it has no learned behavior for. It parrots the header it was handed, has nothing to
put in the channel, and re-emits → the empty-`thought` loop.

## The tell is in the brackets

The correct harmony marker is a **single atomic special token**: `<|channel|>`. What's on screen is

```
<|channel>thought <channel|>
        ^^                ^^   broken — opening "<|channel>" + closing "<channel|>"
```

Those are **not** the real tokens. The tokenizer is splitting `< | channel >` into ordinary text
pieces, which means two things at once:

1. The markers are **not being consumed** as special tokens, so they leak into visible output.
2. The model emits the `thought` header, produces nothing, and repeats → the loop.

So this is a **parsing** failure, not degeneration. Three orthogonal things can cause the split; check
in this order.

## Fixes, in order of likelihood

### 1. Turn off (or fix) Hermes' reasoning wrapper — most common

Hermes is injecting a channel/reasoning template onto a model that doesn't speak it. Either:

- **Disable the reasoning format** for this model (set response format to *plain* / none). Gemma 4
  26B-A4B is a no-reasoning model — it should never be in harmony mode. This alone fixes it in the
  large majority of cases.
- **Or**, if you *want* a thinking model in that slot, set Hermes' reasoning parser to `harmony` so it
  actually *consumes* `<|channel|>…<|message|>…` instead of leaking it — but then use a model trained
  for channels (this Gemma build is not one).

### 2. Verify the special tokens are single IDs in the build

If the markers tokenize as several pieces, no template can work. Test:

```python
from mlx_lm import load
_, tok = load("gemma-4-26b-a4b-it-mlx@6bit")
print(tok.encode("<|channel|>"))   # must be ONE id, not 4–5
```

If it comes back as multiple IDs, `<|channel|>` / `<|message|>` / `<|start|>` / `<|end|>` are missing
from `additional_special_tokens` in this conversion — the channel template can't render no matter what
the client does. Re-pull a build that has them, or add them to the tokenizer config.

### 3. Update mlx-lm

Older `mlx-lm` doesn't know the harmony/channel format and won't apply the reasoning template cleanly.
`pip install -U mlx-lm` and re-check before blaming the build.

## Fastest way to localize it

Run the **same** model + prompt through the CLI with the default template:

```bash
mlx_lm.generate --model gemma-4-26b-a4b-it-mlx@6bit --prompt "hello, one sentence."
```

- **Clean on CLI, broken in Hermes** → it's Hermes' reasoning wrapper. Fix #1.
- **Broken in both** → it's the tokenizer/template in the build itself. Fixes #2 / #3.

## Bottom line

The empty-`thought` loop is the client putting a reasoning costume on a no-reasoning model; the leaked
`<|channel>` text is the tokenizer not treating the markers as special tokens. **It's the template,
not the quant** — the exact inverse of the DeepSeek-V4 2-bit looping, where it *was* the quant and no
template/sampling change helped.
