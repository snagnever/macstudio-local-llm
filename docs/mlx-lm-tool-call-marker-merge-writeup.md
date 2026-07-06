# mlx-lm: tool calls silently dropped when the tokenizer merges the `<tool_call>` closing `>`

> Model card: [deepseek-v4-flash](models/deepseek-v4-flash.md) (affects any model with multi-token tool-call markers)


**Audience:** mlx-lm maintainers (`ml-explore/mlx-lm`).
**Environment:** mlx-lm 0.31.3, mlx 0.31.2, Apple M4 Max / macOS 26.3, model
`mlx-community/DeepSeek-V4-Flash-2bit-DQ` (any model whose `<tool_call>` markers are **not**
single special tokens and whose tokenizer merges `>` with the following byte).
**Reproducer:** [`assets/mlx-lm-tool-marker-fix/repro_marker_merge.py`](../assets/mlx-lm-tool-marker-fix/repro_marker_merge.py)
(tokenizer-only, no GPU, deterministic).

> **✅ Submitted 2026-05-31:** issue [ml-explore/mlx-lm#1335](https://github.com/ml-explore/mlx-lm/issues/1335),
> PR [ml-explore/mlx-lm#1336](https://github.com/ml-explore/mlx-lm/pull/1336) (against `main`, 2 files,
> +60/−2; existing tool-parser tests + new merge-case tests pass).

---

## Summary

mlx-lm detects tool calls during generation with an Aho-Corasick `SequenceStateMachine` that
matches **exact token-id sequences**. The `json_tools` parser's start marker `"<tool_call>"` is
encoded **in isolation** into `tool_call_start_tokens`, which ends in a **standalone `>` token**.
But a model emitting the standard Hermes shape — `<tool_call>\n{ ... }` — produces `>\n` as a
**single merged BPE token**, so the precomputed marker is never a contiguous subsequence of the
generated stream. The state machine never enters the `tool` capture state, and the (perfectly
valid) tool call is returned as assistant **content** with `tool_calls = null`.

Net effect: a model that emits flawless `<tool_call>{json}</tool_call>` appears to "not call
tools" through the OpenAI-compatible server. On our model this was the difference between **0 and
82%** on a tool-calling benchmark.

---

## 1. Problem

With `tokenizer.has_tool_calling` true and `tool_parser_type = json_tools`, an OpenAI-style
request with `tools=[...]` returns the tool call as plain text instead of structured `tool_calls`:

```
POST /v1/chat/completions  {tools:[get_weather], messages:[{user:"weather in Tokyo?"}]}
->  finish_reason: stop
    tool_calls:  None
    content:    'Tool call: \n<tool_call>\n{"name": "get_weather", "arguments": {"city": "Tokyo"}}\n</tool_call>'
```

The model's output is **correct and well-formed** — valid JSON, right function, right args — but
it never reaches the parser.

## 2. Diagnostic

**Detection is token-id matching.** `server.py` wires tool calling as state transitions
(`mlx_lm/server.py`, `_make_state_machine`): `normal --tool_call_start_tokens--> tool` and
`tool --tool_call_end_tokens--> normal`. `SequenceStateMachine` (`mlx_lm/generate.py`) builds one
Aho-Corasick trie per state over those **token-id sequences**, so a transition fires only when the
marker's exact token-id run appears contiguously in the generated tokens.

**The marker is encoded in isolation.** `mlx_lm/tokenizer_utils.py` derives the markers from the
parser module's strings; `json_tools.tool_call_start = "<tool_call>"`. For this tokenizer:

```
encode("<tool_call>")   = (30, 72461, 112042, 32)     #  <  tool  _call  >
```

The trailing `>` is token **32**.

**BPE merges `>` with the next byte.** The `>` only survives as a standalone token at
end-of-string. The moment the model emits a following character, it merges:

```
encode("<tool_call>\n") = (30, 72461, 112042, 1018)   # ">\n" is ONE token (1018)
encode("<tool_call>{")  = (30, 72461, 112042, 31923)  # ">{" is ONE token (31923)
encode("<tool_call> ")  = (30, 72461, 112042, 32, 223)# (a SPACE happens not to merge)
```

The Hermes/Qwen convention puts a newline right after `<tool_call>`, so the model emits the `>\n`
merged token (1018). The precomputed marker `(…, 32)` is therefore **never** a subsequence of the
real stream.

**Confirmed against the real state machine** (the reproducer, no model weights needed):

```
emitted = encode('<tool_call>\n{"name":"get_weather","arguments":{"city":"Paris"}}\n</tool_call>')
stock  marker <tool_call>  = (30,72461,112042,32)  -> enters 'tool' state: False
prefix marker <tool_call   = (30,72461,112042)     -> enters 'tool' state: True
```

So the call is generated, generation stays in `normal`, and the server emits it as content.

**Why it has gone unnoticed:** models that currently use `json_tools` successfully (Qwen2.5 /
Hermes-style) either register `<tool_call>` such that the runtime tokens match, or their tokenizer
doesn't merge `>` with the following newline. It only bites tokenizers where `<tool_call>` is an
ordinary multi-token string **and** `>` merges with the next byte — increasingly common as new
checkpoints (DeepSeek-V4, others) get OpenAI-compatible tool templates bolted on at conversion
time.

## 3. Solution

Make the start-marker matching independent of the volatile trailing `>`. Recommended minimal
change to `mlx_lm/tool_parsers/json_tools.py`:

```python
tool_call_start = "<tool_call"          # was "<tool_call>": drop the '>' so the start marker's
                                         # token run stays stable regardless of the next byte
tool_call_end   = "</tool_call>"

def parse_tool_call(text, tools=None):
    # The captured segment now begins with the leftover ">" (+ newline) before the JSON.
    # Extract the first brace-balanced object so we're robust to that and to a trailing
    # "</tool_call>" if the end marker likewise merges.
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in tool call segment")
    depth = 0; in_str = False; esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            esc = (c == "\\" and not esc); 
            if c == '"' and not esc: in_str = False
            continue
        if   c == '"': in_str = True
        elif c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i+1])
    raise ValueError("unbalanced JSON in tool call segment")
```

This is what we deployed (as a separate `deepseek_json` parser) to take the model from **0/4 → 4/4**
on a probe and **8/40 → 33/40 (82%)** on jdhodges tool-calling.

**Backward-compatibility:** the prefix `<tool_call` is a subsequence of the full-marker emission,
so models where the stock marker currently matches still match; the brace-balanced extractor
tolerates the leftover `>`/newline that the wider capture now includes. It should be validated
against the Qwen2.5/Hermes models that rely on `json_tools` today before merging.

**Alternative approaches** (maintainer's call):
1. Match tool-call markers on **detokenized text** rather than token-id sequences — fully general,
   but a larger change to the hot generation path.
2. Allow `tool_parser_type` configs to **override the start/end marker strings** (and/or supply
   their own token sequences), so a model can opt into `<tool_call` without a new parser module.
3. Keep `json_tools` as-is and **ship a robust variant** (e.g. `json_tools_lenient`) plus docs —
   least invasive, no behavior change for existing users.

## 4. Known limitations / non-goals

- **Not** a fix for the end marker if it *also* merges. We saw `</tool_call>` match in practice
  for this tokenizer, but the brace-balanced parser is deliberately tolerant of a trailing
  `</tool_call>` left inside the captured segment, so a merged end marker degrades gracefully
  (the JSON is still extracted) rather than failing.
- **Multiple / parallel tool calls** are unaffected by this fix and remain a *model* behavior:
  weak checkpoints emit only the first of N calls regardless of parser. (On our 2-bit model this
  was a quant ceiling, not a parser issue.)
- **Streaming**: verified safe. The server generation loop accumulates the *entire* `tool` segment
  (`tool_text`) while in the tool state and only runs `parse_tool_call` after the transition back to
  `normal` (`server.py` ~L1462–1466), in both streaming and non-streaming paths. So the leftover
  `>` never leaks into a streamed delta — it is part of the accumulated segment that brace-extraction
  strips. Backward-compat unit test: the new parser returns **identical** output to the stock
  `json.loads(text.strip())` for clean Qwen/Hermes input and for nested-brace/`}`-in-string cases,
  and additionally parses the merged-`>` and trailing-`</tool_call>` cases the stock parser errors on.
- **Special-token tokenizers unaffected:** models that register `<tool_call>`/`</tool_call>` as
  atomic special tokens never hit this and need no change.
- This is **orthogonal** to whether a model *should* do tool calling and to quantization quality —
  it only ensures that calls the model *does* emit in the documented format are parsed.

---

## Suggested issue / PR (paste-ready summary)

> **Title:** Tool calls dropped when tokenizer merges the `<tool_call>` closing `>` (json_tools
> start-marker never matches)
>
> mlx-lm matches tool-call markers as exact token-id sequences. `json_tools`'s `"<tool_call>"`
> encodes to a run ending in a standalone `>` token, but models emitting `<tool_call>\n{...}`
> produce a merged `>\n` token, so the marker is never a subsequence and the call is returned as
> content (`tool_calls=null`). Repro + token IDs attached. Fix: match on the `<tool_call` prefix +
> brace-balanced JSON extraction (backward-compatible; validate vs Qwen/Hermes). Took our model
> from 0 → 82% on a tool-calling bench.
