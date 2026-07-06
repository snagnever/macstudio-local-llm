# Hermes-4-70B on LM Studio: `Cannot perform operation + on undefined values`

> Model card: [hermes-4-70b](models/hermes-4-70b.md)


**Symptom (exact):** a tool-calling request to `nousresearch/hermes-4-70b` (the
`lmstudio-community/Hermes-4-70B-MLX-6bit` build) fails before any tokens are generated:

```
[nousresearch/hermes-4-70b] Running chat completion on conversation with 14 messages.
[nousresearch/hermes-4-70b] Streaming response...
[nousresearch/hermes-4-70b] Error rendering prompt with jinja template:
  "Cannot perform operation + on undefined values".
```

No output, every time. LM Studio's generic advice ("search under lmstudio-community for a fixed
template") doesn't help — **this is already the lmstudio-community build**, and its `chat_template.jinja`
is the thing that breaks.

## It is not what the error makes it look like

The reflex reads are all wrong:

- **Not the quant** — nothing has been decoded yet; this is prompt *rendering*, upstream of the model.
- **Not null `content` in your messages** — the assistant tool-call turns carry `content: ""` (empty
  string), which is fine. `"" + x` works.
- **Not the weights.**

It's a **chat-template bug**: the template performs `+` (string concatenation) on a value the render
context leaves *undefined*. This template has **two independent ways** to do that, and they produce the
identical error message. Which one you hit depends on the request.

## Why minja and not Python

LM Studio renders chat templates with **minja**, a C++ Jinja engine that differs from Python's Jinja2:

- Missing *attribute* access (`message.tool_calls` on a message without that key) is falsy in minja — no
  error. (Jinja2 `StrictUndefined` throws here; that's a red herring — don't reproduce with it.)
- An **out-of-range list index** returns *undefined* rather than raising.
- But **`+` with an undefined operand** throws `Cannot perform operation + on undefined values`.

So the error is always a `+` whose operand resolved to undefined — either directly, or via an
out-of-range index that *became* undefined.

## Cause #1 (the one that actually bites agents): the CoT-strip index

Hermes-4 is a hybrid reasoning model. When **thinking mode is on**, the template rewrites each prior
assistant turn to drop its chain-of-thought (unless `keep_cots`):

```jinja
{%- if thinking %}
    {%- if not keep_cots %}
        {%- set content = '<think> </think>' + content.split('</think>', 1)[1] -%}
    {%- endif %}
{%- endif %}
```

`content.split('</think>', 1)[1]` **assumes every prior assistant message contains `</think>`.** A
normal assistant reply that has no chain-of-thought (e.g. *"The browser encountered an issue…"*) splits
into a **1-element list**, so `[1]` is out of range → undefined → `'<think> </think>' + undefined` →
the error.

**What turns thinking on:** the request. This build's `model.yaml` maps reasoning to the jinja
`thinking` variable, and an OpenAI-style **`reasoning_effort`** field (e.g. `hermes-agent` sends
`"reasoning_effort": "medium"`) flips it to `true`. With thinking `false` (the default) this branch
never runs — which is exactly why the bug is intermittent and why a naive repro "renders fine."

### Fix

Guard the strip so it only runs when there's actually a `</think>` to cut (both occurrences — the
assistant-with-tool-calls branch and the assistant-without branch):

```jinja
{%- if '</think>' in content %}{%- set content = '<think> </think>' + content.split('</think>', 1)[1] -%}{%- endif %}
```

Byte-identical behavior when `</think>` is present (CoT still stripped under `keep_cots=false`, still
kept under `true`); it simply skips the cut when there's nothing to strip.

## Cause #2 (latent): `bos_token` on the opening line

Both template branches open with `bos_token + '<|start_header_id|>…'`. If the render context doesn't
define `bos_token`, that's `undefined + string` → the same error, on the very first line. LM Studio
*does* usually supply `bos_token`, so this typically doesn't fire — but it's one runtime-config change
away from a hard failure, so guard it too:

```jinja
{%- if not bos_token is defined %}{% set bos_token = '<|begin_of_text|>' %}{% endif %}
```

The literal matches this build's `special_tokens_map.json` (Llama-3.1 base). The `if not … is defined`
guard is a **no-op when LM Studio does provide `bos_token`**, so there's no double-BOS risk. (`tokenizer_config.json`
has `add_bos_token: true`, but LM Studio tokenizes the rendered chat string with special tokens already
inlined — verified: exactly one `<|begin_of_text|>` in the output.)

## Reproducing it (proof, not guesswork)

Render the **actual** payload (pulled from `~/.lmstudio/server-logs/`) against the real template with
Jinja2's default `Undefined` (missing attr = falsy, out-of-range index = undefined, `+` on undefined =
raises — the closest match to minja):

```python
import jinja2
tpl = jinja2.Environment(undefined=jinja2.Undefined).from_string(open("chat_template.jinja").read())

messages = [  # …14-message tool-calling conversation…
    {"role": "assistant", "content": "",                       # tool-call turn: empty content, fine
     "tool_calls": [{"id": "1", "type": "function",
                     "function": {"name": "search_files", "arguments": "{\"q\":\"x\"}"}}]},
    {"role": "tool", "content": "{\"ok\":1}", "tool_call_id": "1"},
    {"role": "assistant", "content": "The browser encountered an issue... how to proceed?"},  # NO </think>
    {"role": "user", "content": "can you use a playwright?"},
]
tools = [{"type": "function", "function": {"name": "search_files", "parameters": {}}}]

tpl.render(messages=messages, tools=tools, add_generation_prompt=True,
           bos_token="<|begin_of_text|>", thinking=False)   # -> OK  (why a naive repro passes)
tpl.render(messages=messages, tools=tools, add_generation_prompt=True,
           bos_token="<|begin_of_text|>", thinking=True)    # -> ERROR: list object has no element 1
```

`thinking=True` is the tell: it hits the CoT-strip on the no-`</think>` assistant message. That maps to
minja's `+ on undefined`.

## After editing the template

LM Studio **caches** the parsed template (`~/.lmstudio/.internal/model-index-cache.json`,
`metadata.configJson.chatTemplate`) and serves this model as a **virtual model**
(`nousresearch/hermes-4-70b` → concrete `Hermes-4-70B-MLX-6bit`). Editing `chat_template.jinja` alone
isn't enough for the *running* instance — **eject and reload the model** (or restart the server) so it
re-reads the file and refreshes the cache. A plain "regenerate" without a reload keeps using the stale
cached template.

Only `chat_template.jinja` matters for MLX models — LM Studio prefers it over the copy embedded in
`tokenizer_config.json`, so that embedded copy can be left alone.

## Bottom line

`+ on undefined` from a chat template is the runtime hitting a value the template assumed was there.
For Hermes-4 on LM Studio there are two: the **CoT-strip index** (`split('</think>')[1]`) that fires
whenever a request enables thinking — via `reasoning_effort` — and a prior assistant turn has no
`</think>`; and a latent **`bos_token`** concat. Guard both. It's the template, not the quant, not your
messages.
