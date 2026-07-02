# Hermes-4-70B on LM Studio: `Cannot perform operation + on undefined values`

**Symptom (exact):** a tool-calling request to `nousresearch/hermes-4-70b` (the
`lmstudio-community/Hermes-4-70B-MLX-6bit` build) fails before any tokens are generated:

```
[nousresearch/hermes-4-70b] Running chat completion on conversation with 14 messages.
[nousresearch/hermes-4-70b] Streaming response...
[nousresearch/hermes-4-70b] Error rendering prompt with jinja template:
  "Cannot perform operation + on undefined values".
```

No output, every time. LM Studio's generic advice ("search under lmstudio-community for a fixed
template") doesn't help here — **this is already the lmstudio-community build**, and its template is
the thing that breaks.

## It is not what the error makes it look like

The reflex reads are all wrong:

- **Not the quant** — nothing has been decoded yet; this is prompt *rendering*, upstream of the model.
- **Not null `content` in your messages** — the assistant tool-call turns carry `content: ""` (empty
  string), which is a valid, truthy-or-not-it-doesn't-matter string. `"" + x` is fine.
- **Not the weights.**

It's a **chat-template bug**: the template performs `+` (string concatenation) on a variable that the
runtime never defined.

## Why minja and not Python

LM Studio renders chat templates with **minja**, a C++ Jinja engine. minja and Python's Jinja2 differ
on undefined values:

- Missing *attribute* access (`message.tool_calls` on a message that has no such key) is treated as
  falsy by minja — no error. (Jinja2 `StrictUndefined` would throw here; that's a red herring.)
- But **arithmetic / concatenation** on an undefined value (`undefined + "str"`) throws
  `Cannot perform operation + on undefined values`.

So the error is specifically a `+` whose left or right operand is undefined.

## Locating the exact `+`

The Hermes-4 template (`chat_template.jinja`) opens **both** of its branches with `bos_token`:

```jinja
{%- if tools %}
    {{- bos_token + '<|start_header_id|>system<|end_header_id|>\n' }}   {# tools branch #}
    ...
{%- else %}
    {{- bos_token + '<|start_header_id|>system<|end_header_id|>\n\n' + ... }}   {# plain chat #}
{%- endif %}
```

A tool-calling request takes the **tools** branch and hits `bos_token + '...'` on the very first line
of output. If LM Studio's render context doesn't define `bos_token`, that's `undefined + string` →
the error. Every message's `content` was present, `thinking` was off, so nothing else in the template
touches an undefined operand.

## Reproducing it (proof, not guesswork)

Render the **actual** payload (pulled from `~/.lmstudio/server-logs/`) against the real template, once
with `bos_token` defined and once without. Approximating minja with Jinja2's default `Undefined`
(missing attr = falsy, arithmetic on undefined = raises):

```python
import jinja2
tpl = jinja2.Environment(undefined=jinja2.Undefined).from_string(
    open("chat_template.jinja").read())

messages = [  # the 14-message tool-calling conversation, shape-faithful
    {"role": "system", "content": "You are Hermes Agent..."},
    {"role": "user", "content": "Create a plan..."},
    {"role": "assistant", "content": "",
     "tool_calls": [{"id": "1", "type": "function",
                     "function": {"name": "search_files", "arguments": "{\"q\":\"x\"}"}}]},
    {"role": "tool", "name": "search_files", "content": "{\"ok\":1}", "tool_call_id": "1"},
    # ... more assistant/tool pairs ...
    {"role": "assistant", "content": "The browser encountered an issue..."},
    {"role": "user", "content": "can you use a playwright?"},
]
tools = [{"type": "function", "function": {"name": "search_files", "parameters": {}}}]

tpl.render(messages=messages, tools=tools, add_generation_prompt=True,
           bos_token="<|begin_of_text|>")   # -> OK
tpl.render(messages=messages, tools=tools, add_generation_prompt=True)   # -> 'bos_token' is undefined
```

With `bos_token` supplied it renders (~2.1k chars); without it, exactly the LM Studio error. That
pins the cause with no ambiguity.

## The fix

Add a guarded fallback near the top of `chat_template.jinja` (alongside the existing `thinking` /
`keep_cots` defaults):

```jinja
{%- if not bos_token is defined %}{% set bos_token = '<|begin_of_text|>' %}{% endif %}
```

- The literal `<|begin_of_text|>` matches this build's `special_tokens_map.json` (Llama-3.1 base), and
  the template was clearly written to emit BOS explicitly (both branches start with it).
- The `if not ... is defined` guard means it's a **no-op when LM Studio does provide `bos_token`** — it
  never overwrites a supplied value, so there's no double-BOS regression.
- `tokenizer_config.json` has `add_bos_token: true`, but LM Studio tokenizes the rendered chat string
  with special tokens already inlined; the single BOS from the template is correct (verified: exactly
  one `<|begin_of_text|>` in the rendered output, tools and plain-chat paths alike).

Then **eject and reload the model** in LM Studio (it caches the template at load), or restart the
server, and re-run.

Only `chat_template.jinja` matters for MLX models — LM Studio prefers it over the copy embedded in
`tokenizer_config.json`, so that embedded copy can be left alone.

## Bottom line

`+ on undefined` from a chat template is almost always the runtime not injecting a variable the
template assumes — here `bos_token`, on the tools branch of an agent conversation. It's the template's
dependency on the render context, not the quant, not your messages. The one-line guarded fallback
makes the template self-sufficient without changing behavior when the variable *is* present.
