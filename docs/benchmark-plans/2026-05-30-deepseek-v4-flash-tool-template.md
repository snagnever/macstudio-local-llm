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
- **Full tool benches — DONE ✅.** With the template + `deepseek_json` parser:
  **jdhodges 33/40 (82 %)** (was 8/40) and **Veerman 6/12 (50 %)** (was 2/12) — combined
  **39/52 (75 %)**, 0 OOMs. The model's tool calls are well-formed; every miss is a
  reasoning/coverage issue, not a format/parse one.

### Failure-pattern analysis (13 misses / 52)

| Mode | # | Notes |
|---|---|---|
| Partial multi-tool (1 of N parallel) | 5 | the call made is correct; it just stops after the first |
| Wrong tool selected | 3 | genuine 2-bit reasoning slips |
| No call (asked to clarify) | 2 | defensible on ambiguous prompts |
| Over-called (restraint) | 2 | fired a tool when none was needed |
| Right tool, missing arg | 1 | dropped `units: celsius` |

### Multi-tool template tweak — TRIED, REVERTED ❌

Hypothesis: the 5 partial-multi-tool misses were a template gap (single-call example). Tweaked the
instruction to demand "emit ALL parallel calls as consecutive `<tool_call>` blocks" + a two-block
example, re-ran both suites. **Result: no improvement** — jdhodges **33/40 (identical)**, Veerman
7/12 (+1 via an unrelated ambiguous case). All 4 genuinely-parallel cases **still emitted only the
first call**, and one single-call case (`multi_paris`) *regressed* to no-call from the longer
instruction. **Conclusion: parallel multi-tool emission is a 2-bit capability ceiling, not a
template gap** — the model understands the instruction, emits a perfect first call, then stops.
Reverted to the simpler original template (33/40, 6/12 stand as the result).

> **⚠️ CORRECTION (2026-05-31): that "2-bit ceiling" conclusion was WRONG.** It was a *format
> tax*, not a quant limit — see below.

## Native DSML — the real fix (disproves the "ceiling" above)

The Hermes `<tool_call>` format is **not** what DeepSeek-V4 was trained on. Its native tool format is
**DSML** (`<｜DSML｜tool_calls>` / `<｜DSML｜invoke name=…>` / `<｜DSML｜parameter name=… string=…>`),
with multiple `<｜DSML｜invoke>` inside one `<｜DSML｜tool_calls>` block — i.e. **parallel calls are
native**. The official template is [deepseek-ai/DeepSeek-V4-Flash#16](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/discussions/16).

Ported that template into the MLX conversion + wrote a `deepseek_dsml` parser (modeled on
`minimax_m2`), thinking OFF (`thinking_mode=chat`), re-benched:

| Suite | Hermes (workaround) | **Native DSML** | Δ |
|---|---|---|---|
| jdhodges | 33/40 (82 %) | **39/40 (98 %)** | +16pp |
| Veerman | 6/12 (50 %) | **9/12 (75 %)** | +25pp |
| Combined | 39/52 (75 %) | **48/52 (92 %)** | +17pp |
| multi_tool category | 3/8 | **8/8** | every parallel case fixed |

jdhodges per-category under DSML: tool_selection 8/8, argument_accuracy 8/8, **multi_tool 8/8**,
format_compliance 8/8, edge_cases 7/8 (the single miss is one restraint case). 0 OOMs.

**The corrected conclusion:** the partial-multi-tool failures were entirely a **format tax** from
forcing the model into a non-native format. In its native DSML format the 2-bit model emits parallel
calls correctly and reaches **98 % jdhodges — matching the best full-size local on this rig**
(qwen3.6-35b-a3b, also 98 %). The model's true tool-calling ability was far higher than the Hermes
82 % suggested. Artifacts: [`assets/deepseek-v4-dsml/`](../../assets/deepseek-v4-dsml/)
(template + `deepseek_dsml.py` parser + install). This is the configuration to use going forward.

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
