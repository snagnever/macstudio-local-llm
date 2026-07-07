# Plan: Run DeepSeek V4 Flash via patched `mlx-lm.server` + Open WebUI / CLI

> Model card: [deepseek-v4-flash](README.md)


## Context

`mlx-community/DeepSeek-V4-Flash-2bit-DQ` is already downloaded to `/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ` (~93 GB across 19 shards), but it won't load in LM Studio today because:

1. LM Studio 0.4.14 bundles `mlx-lm 0.31.3` (released 2026-04-22), and DeepSeek V4 architecture support hasn't merged yet — it lives in [mlx-lm PR #1192](https://github.com/ml-explore/mlx-lm/pull/1192), still open as of 2026-05-19.
2. The shipped `config.json` declares `rope_theta: 10000` and `compress_rope_theta: 160000` as **int**, but the new `transformers` config dataclass (PR #45643, merged 2026-05-02) validates them as **float** and rejects ints.
3. LM Studio 0.4.x can serve local models but cannot consume an external OpenAI-compatible endpoint, so its chat UI can't be the front-end for an out-of-band runtime.

**Outcome:** Stand up a parallel patched `mlx-lm` runtime in an isolated `uv`-managed Python 3.12 venv, load the existing on-disk model (no re-download), serve it on an OpenAI-compatible port, and drive it from (a) Open WebUI in Docker, and (b) the `mlx_lm.chat` CLI for quick smoke tests. When PR #1192 merges and LM Studio bumps its bundled runtime, this whole detour can be retired and the model loaded natively.

---

## Approach

A self-contained venv at `/Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash` keeps the patched stack quarantined from LM Studio's bundled runtime. The model files are referenced in place (`--model <absolute-path>`) rather than re-cached, so there's no duplicate 93 GB on disk. `config.json` is patched in place after a backup. Open WebUI runs in Docker pointed at `host.docker.internal:8765` for the rich UI; `mlx_lm.chat` works directly inside the venv for fast iteration.

---

## Steps

### 1. Back up and patch `config.json` (int → float)

The model directory:

- `/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ/config.json`

Make a backup, then change two fields:

```
"rope_theta": 10000             →  "rope_theta": 10000.0
"compress_rope_theta": 160000   →  "compress_rope_theta": 160000.0
```

Commands:

```bash
MODEL_DIR="/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
cp "$MODEL_DIR/config.json" "$MODEL_DIR/config.json.bak"
# Use python -m json (load → dump) to avoid sed brittleness on a 180KB file:
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ/config.json")
cfg = json.loads(p.read_text())
cfg["rope_theta"] = float(cfg["rope_theta"])
cfg["compress_rope_theta"] = float(cfg["compress_rope_theta"])
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
PY
```

### 2. Create the venv with `uv` (Python 3.12)

System Python is 3.9.6 — too old for current `mlx-lm`. `uv 0.11.14` is already installed.

```bash
mkdir -p /Users/vitor/LocalProjects/local-llms/venvs
cd /Users/vitor/LocalProjects/local-llms/venvs
uv venv --python 3.12 mlx-v4-flash
source mlx-v4-flash/bin/activate
```

### 3. Install patched stack

`transformers` PR #45643 is **already merged into main** (2026-05-02), so a fresh `transformers` from PyPI ≥ the post-2026-05-02 release will have it; if it hasn't released yet, install from git main. `mlx-lm` PR #1192 is **still open**, so install from the PR branch.

```bash
# Inside the activated venv:
uv pip install --upgrade pip wheel

# transformers — prefer released wheel; fall back to git main if needed.
uv pip install "transformers>=4.50" || uv pip install "git+https://github.com/huggingface/transformers.git@main"

# mlx-lm from PR #1192 head:
uv pip install "git+https://github.com/ml-explore/mlx-lm.git@refs/pull/1192/head"

# Runtime deps that mlx-lm doesn't always pin tightly:
uv pip install "mlx>=0.31.2" "huggingface_hub" "sentencepiece" "protobuf"
```

If `mlx-lm` PR #1192's `setup.py` doesn't pull in everything, the import error in the smoke test (step 5) will tell us what's missing.

### 3a. Apply local vendor patches

Two patches are **required** for this model; a third is deprecated.

1. **`fixes/mlx-lm/mlx-lm-find-negative-start.patch`** — one-line fix for [ml-explore/mlx-lm#1326](https://github.com/ml-explore/mlx-lm/issues/1326): without it, `mlx_lm.server` returns `HTTP 404 {"error": "list index out of range"}` for any chat message whose templated prompt is shorter than 11 tokens (e.g. "hi", "hello"). The patch clamps a negative `start` in `TokenizerWrapper._find`. **Required** — apply unconditionally.

2. **`fixes/mlx-lm/mlx-lm-deepseek-v4-cache-materialize.patch`** — **the Metal OOM fix. Required.** One hunk in `DeepseekV4Model.__call__` that `mx.eval`s every per-layer cache array once per forward pass. Without it the per-layer caches (compressor/indexer `PoolingCache` + `RotatingKVCache`, single and batched) build un-detached lazy graphs that retain ~1 live Metal buffer per layer per decode step, hitting Metal's residency `resource_limit` (499000) at **~11,300 generated tokens regardless of prompt length** → `RuntimeError: [metal::malloc] Resource limit (499000) exceeded`. **Verified 2026-05-30:** forced-gen reproducer streamed 19,989 tokens clean at **31.3 t/s, 0 OOMs** (baseline died at 11,314; no throughput regression). Root cause + fix path in [`docs/deepseek-v4-flash-metal-oom-investigation.md`](metal-oom-investigation.md) §2 and [`docs/deepseek-v4-flash-metal-oom-fix-plan.md`](metal-oom-fix-plan.md) Phase 2-revised (R5).

3. **`fixes/mlx-lm/mlx-lm-deepseek-v4-indexer-chunk.patch`** — **DEPRECATED, do NOT apply.** Earlier attempt that chunked the indexer with `mx.eval`+`mx.clear_cache`; it does not fix the OOM (the cap counts *live* buffers, which `clear_cache` can't reclaim) and costs ~3–4× throughput. Superseded by patch 2. Kept only as a record.

Apply the two required patches against the installed package:

```bash
(cd "$VIRTUAL_ENV/lib/python3.12/site-packages" \
   && patch -p0 < /Users/vitor/LocalProjects/local-llms/fixes/mlx-lm/mlx-lm-find-negative-start.patch \
   && patch -p0 < /Users/vitor/LocalProjects/local-llms/fixes/mlx-lm/mlx-lm-deepseek-v4-cache-materialize.patch)
```

When upstream releases the fixes: delete the corresponding `.patch` file and remove its apply step.

### 4. Patch fallbacks (only if step 5 fails)

Two known footguns from the HF discussion thread:

- **`KeyError: 'deepseek_v4'`** at tokenizer load → upgrade `transformers` further, or add `trust_remote_code=True`. mlx-lm exposes this via `--trust-remote-code` on `mlx_lm.server` / `generate`.
- **`StrictDataclassFieldValidationError` on other config fields** → repeat the int→float pattern from step 1 for whichever field the error names. The thread flagged `n_group`, `first_k_dense_replace`, `rope_interleave`, `o_lora_rank`, `index_n_heads`, `index_head_dim`, `index_topk`, `partial_rotary_factor` as undocumented; some may also need float coercion.

Do not pre-emptively patch these — only touch what an actual error names. Each patch goes into the same `config.json`; the `.bak` from step 1 is the rollback.

### 5. CLI smoke test (`mlx_lm.generate`)

Per the HF thread, direct `generate` works even when the server doesn't, so this is the fastest signal that the stack is sound.

```bash
python -m mlx_lm.generate \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --prompt "Write one paragraph about quantum computing." \
  --max-tokens 200 \
  --temp 0.0
```

Expected: coherent, non-repeating paragraph at ~30–40 tok/s on the M4 Max. If this fails, iterate on step 4 before moving on.

### 6. Start `mlx_lm.server` on port 8765

Port 8765 is chosen to stay clear of LM Studio's default `1234`.

```bash
python -m mlx_lm.server \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --chat-template-args '{"enable_thinking":false}' \
  --host 0.0.0.0 --port 8765 \
  --max-tokens 4096 --temp 0.0
```

The HF thread reported a repetition bug in `server` mode at `temp 0.0`. If you reproduce it:

- Try `--temp 0.6` (DeepSeek's recommended default).
- Try omitting `--chat-template-args '{"enable_thinking":false}'` to let the chat template behave normally.
- Verify `mlx_lm.generate` doesn't repeat with the same prompt → confirms it's a server-path issue, not a model issue.

Keep this terminal running. The OpenAI-compatible base URL is `http://127.0.0.1:8765/v1`.

### 7a. CLI front-end (`mlx_lm.chat`)

For fast iteration without leaving the terminal:

```bash
python -m mlx_lm.chat \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --temp 0.6
```

This loads the model fresh into the CLI process (separate from the server). Useful for sanity checks; doesn't share KV cache with the server.

### 7b. Open WebUI front-end (Docker)

Run a single container, pointing it at the host's `:8765`. `host.docker.internal` is the standard way for a Docker-for-Mac container to reach the host.

```bash
docker run -d \
  --name openwebui \
  -p 3000:8080 \
  -v openwebui-data:/app/backend/data \
  -e OPENAI_API_BASE_URLS="http://host.docker.internal:8765/v1" \
  -e OPENAI_API_KEYS="not-needed" \
  -e WEBUI_AUTH=False \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main
```

Then open `http://localhost:3000`. The model should appear in the model picker as whatever `mlx_lm.server` advertises (typically the repo name). If the picker is empty, hit Settings → Connections in Open WebUI and confirm the base URL.

---

## Critical files / paths

- `/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ/config.json` — patched in place; `.bak` sibling is the rollback
- `/Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/` — isolated venv (delete to undo)
- Docker volume `openwebui-data` — chat history persistence (delete via `docker volume rm openwebui-data` to wipe)
- Nothing inside `/Users/vitor/.lmstudio/` other than the model's `config.json` is touched — LM Studio itself is unaffected.

---

## Verification

End-to-end checks, in order — stop at the first that fails and fix before continuing:

1. **Venv health:** `python -c "import mlx_lm, transformers, mlx; print(mlx_lm.__version__, transformers.__version__, mlx.__version__)"` — all import, versions print.
2. **Config patched:** `python -c "import json; c=json.load(open('/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ/config.json')); print(type(c['rope_theta']), type(c['compress_rope_theta']))"` — both print `<class 'float'>`.
3. **CLI generate (step 5):** coherent paragraph, no repetition, ≥ 25 tok/s.
4. **Server health:** with server running, `curl http://127.0.0.1:8765/v1/models` returns a JSON model list including the DeepSeek path.
5. **Server chat completion:** 

   ```bash
   curl http://127.0.0.1:8765/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"deepseek","messages":[{"role":"user","content":"Say hi in five words."}],"max_tokens":32}'
   ```
   Returns a normal chat completion JSON; the `content` is not a repetition loop.
6. **Open WebUI:** browser to `http://localhost:3000`, model picker shows the DeepSeek model, send "hello" and get a coherent reply.
7. **No interference with LM Studio:** open LM Studio, load any other model from the same models directory, confirm it still loads and chats normally.

If verification step 5 hits the repetition bug from the HF thread, file a note (don't deep-fix here) and use the CLI / `mlx_lm.chat` path until upstream fixes it.

---

## Known risks / not-handled-here

- **`bojiang`'s sanitize comment on PR #1192** (2026-05-19) flagged shape gaps on the `2/3/4/6/8bit` community conversions. The local weight map looks standard (`model.embed_tokens.weight/.scales/.biases`), so we likely dodge this — but if the smoke test fails with a shape/key error inside `sanitize`, that's the cause; the fix lives in PR #1192's review thread and would need to be applied as a patch on top.
- **Repetition at `temp=0.0` in server mode** — known issue, unresolved upstream. Mitigation listed in step 6.
- **No tests, no CI** — this is a local-only one-off runtime; the verification list is the test plan.

---

## Retirement plan

When `mlx-lm` PR #1192 merges and LM Studio ships an `mlx-engine` bump that includes it:

1. Stop the server, stop the Open WebUI container.
2. `rm -rf /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash`.
3. Restore `config.json` from `.bak` *only if* LM Studio's runtime requires it back as int — otherwise leave as float (newer transformers accept both).
4. Load the model normally in LM Studio.
