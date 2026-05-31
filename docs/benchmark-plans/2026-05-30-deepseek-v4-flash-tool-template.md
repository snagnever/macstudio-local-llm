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

## The fix (three pieces)

1. **`chat_template.jinja`** → [`assets/deepseek-v4-tool-template/chat_template.jinja`](../../assets/deepseek-v4-tool-template/chat_template.jinja):
   DeepSeek turn markers (`<｜User｜>/<｜Assistant｜>/</think>`) **+** a Hermes-style `<tools>` block
   (injects the function schemas + the `<tool_call>` output spec) and `<tool_call>` rendering for
   assistant tool calls / `<tool_response>` for tool results.
2. **Custom tool parser** → [`assets/deepseek-v4-tool-template/deepseek_json.py`](../../assets/deepseek-v4-tool-template/deepseek_json.py),
   deployed into `venvs/mlx-v4-flash/.../mlx_lm/tool_parsers/`. **This is the key piece** — see the
   token-merge finding below. Its start marker is `<tool_call` (no trailing `>`) and it extracts the
   first brace-balanced JSON object, surviving the BPE merge and the leftover `>`/`</tool_call>`.
3. **`tokenizer_config.json`** → `"tool_parser_type": "deepseek_json"`. Flips `has_tool_calling`
   True, selects the custom parser.

### The token-merge finding (why the stock `json_tools` parser fails)

The model emits *perfect* tool calls — `<tool_call>\n{"name": …, "arguments": …}\n</tool_call>` with
valid JSON. But mlx-lm's state machine detects tool calls by matching the **token sequence** of the
start marker. Stock `json_tools` uses `"<tool_call>"` → tokens `(30, 72461, 112042, 32)` = `<`,`tool`,
`_call`,`>`. When the model emits `<tool_call>\n`, BPE **greedily merges `>` + `\n` into one `>\n`
token (1018)**, so the 4-token marker is never a subsequence of the stream and the machine never
enters tool-capture mode → the call is returned as plain content, `tool_calls` stays null. The custom
parser matches on the stable `<tool_call` prefix (`30, 72461, 112042`) instead, which *is* always a
subsequence. (`>` only survives as token 32 at end-of-string; anything following it merges.)

## Verification status

- **Plumbing — DONE (in-process).** Patched tokenizer: `has_tool_calling=True`, tools injected.
  Evidence: [`inprocess-verify.txt`](../../assets/deepseek-v4-tool-template/inprocess-verify.txt).
- **Live emission — DONE ✅ (2026-05-30).** With the **custom `deepseek_json` parser**, a 4-prompt
  probe went from **0/4 → 4/4** tool calls, correct names + arguments, 0 OOMs:
  `get_weather({"city":"Tokyo"})`, `calculator({"expression":"4827 * 391"})`,
  `get_weather({"city":"Paris"})`, `calculator({"expression":"19^2 + 7"})`.
  (With the stock `json_tools` parser the model emitted identical *content* but the server returned
  it as text — `tool_calls` null — due to the token-merge above. The custom parser fixed it.)
- **Full tool benches (jdhodges 40 + Veerman 12) — running** to quantify vs the prose floor
  (8/40, 2/12). Results land in `M4_MAX_128GB_NOTES.md` + this section.

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
