# DeepSeek-V4-Flash — enable tool calling via a tool-aware chat template

**Goal:** make `mlx-community/DeepSeek-V4-Flash-2bit-DQ` actually receive + emit tool calls on
this rig, so tool-calling benches measure the *model*, not a template gap.
**Branch:** `deepseek-v4-tool-template`. **Model dir:** `~/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ` (not in git; managed by the install/uninstall scripts).

## Root cause (recap)

`mlx_lm.server` logs *"Received tools but model does not support tool calling"* and **drops the
`tools` array** on every request, because:
- mlx-lm sets `tokenizer.has_tool_calling = (_tool_call_start is not None)`, and `_tool_call_start`
  is set only when a `tool_parser_type` resolves — from `tokenizer_config.json["tool_parser_type"]`
  or inferred from the chat template by `_infer_tool_parser()`.
- This conversion ships a **24-line `chat_template.jinja` with no tools branch** → inference returns
  `None` → no parser → tools dropped → the model never sees a tool schema → prose only
  (`no_tool_called`).
- There is **no DeepSeek tool parser** in mlx-lm, and DeepSeek's native `<｜tool▁calls▁begin｜>`
  special tokens **aren't present** in this conversion — so the native format is a dead end here.

mlx-lm *does* ship a generic **`json_tools`** parser (Hermes/Qwen2.5 `<tool_call>{json}</tool_call>`
format, markers `<tool_call>`/`</tool_call>`). That's the route.

## The fix (two files in the model dir)

1. **`chat_template.jinja`** → [`assets/deepseek-v4-tool-template/chat_template.jinja`](../../assets/deepseek-v4-tool-template/chat_template.jinja):
   DeepSeek turn markers (`<｜User｜>/<｜Assistant｜>/</think>`) **+** a Hermes-style `<tools>` block
   (injects the function schemas + the `<tool_call>` output spec) and `<tool_call>` rendering for
   assistant tool calls / `<tool_response>` for tool results.
2. **`tokenizer_config.json`** → add `"tool_parser_type": "json_tools"` (robust; doesn't rely on
   `_infer_tool_parser` substring matching). This flips `has_tool_calling` True and selects the
   parser that round-trips `<tool_call>…</tool_call>` back into OpenAI `tool_calls`.

## Verification status

- **Plumbing — DONE (in-process, no GPU/server, queue untouched).** Loaded the patched tokenizer
  on a temp copy: `has_tool_calling=True`, `tool_call_start='<tool_call>'`, and
  `apply_chat_template(..., tools=[...])` injects the `<tools>` schema + `<tool_call>` spec. Evidence:
  [`assets/deepseek-v4-tool-template/inprocess-verify.txt`](../../assets/deepseek-v4-tool-template/inprocess-verify.txt).
- **Live emission — PENDING (needs the server; deferred until the running DROP/MATH/LCB queue
  finishes so it isn't disrupted).**

## Live-test runbook (run AFTER the benchmark queue completes)

1. Stop the benchmark queue (server + driver): `pkill -f mlx_lm.server; pkill -f bench2.py`.
2. **Install:** `bash assets/deepseek-v4-tool-template/install.sh` (backs up the live files, copies
   the new template, patches `tokenizer_config.json`).
3. **Test:** `nohup bash .bench-logs/test-deepseek-v4-tool-template.sh >/dev/null 2>&1 & disown`
   — starts a server (cap 2048, temp 0, thinking OFF), confirms the *"does not support tool calling"*
   warning is **gone**, runs a 4-prompt tool probe + the 12-case Veerman suite, logs everything.
4. **Read** `.bench-logs/tool-template-test.log`: tool-call emission rate + Veerman score + the
   `metal::malloc` count (must stay 0 — the OOM fix is orthogonal and still in force).

### Pass / fail

| Check | Pass condition |
|---|---|
| Detection | no *"does not support tool calling"* warning in the server log |
| Emission | model emits ≥1 parseable `<tool_call>` → response has `tool_calls` (vs **0** before) |
| Parsing | server returns OpenAI `tool_calls` objects, not raw `<tool_call>` text in content |
| Regression | 0 `metal::malloc`; non-tool chat still coherent |
| Score | Veerman / jdhodges > the prose-floor (2/12, 8/40) — *bonus, not required* |

## Expectations (calibrated)

- Detection/injection/parsing: **certain** (already proven).
- Whether the **2-bit** weights reliably emit `<tool_call>` JSON: **low–moderate**. DeepSeek-V4 was
  trained on its *own* tool format; we steer it to Hermes via in-context instructions. Expect a jump
  from "0 %, never asked" to "emits some, sometimes malformed" — *usable*, not benchmark-competitive.
- If emission is poor, try: (a) a few-shot tool example in the system block, (b) `temp 0.3–0.6` (the
  2-bit degenerates at temp 0), (c) tightening the format spec wording.

## Rollback

`bash assets/deepseek-v4-tool-template/uninstall.sh` restores the pristine
`assets/deepseek-v4-tool-template/original/{chat_template.jinja,tokenizer_config.json}` into the
model dir. The benchmark queue can then be resumed (DROP/MATH/LCB).

## Upstream follow-up (separate from the OOM fix)

The clean fix belongs in the `mlx-community` conversion (ship a tool-aware template) and/or mlx-lm
(a real `deepseek` tool parser using the native `<｜tool▁calls▁begin｜>` format + tokens). Candidate
contribution once this local template is validated.
