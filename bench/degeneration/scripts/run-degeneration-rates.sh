#!/bin/bash
# Real stochastic loop-RATE measurement, after porting the #1331 seed fix
# (uncompiled sampling honors per-request mx.random.seed() + prompt-cache bypass
# for seeded stochastic requests). First proves seeds now actually vary (gate),
# then measures clean-vs-loop rate over 8 seeds for the key configs.
# Usage: nohup bash bench/degeneration/scripts/run-degeneration-rates.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
ORIG=$ROOT/fixes/deepseek-v4-flash/tool-template/original
SLOG=$ROOT/bench/degeneration/logs/server-degeneration.log
LOG=$ROOT/bench/degeneration/logs/degeneration-rates.log
BASE=http://127.0.0.1:8765/v1
export BASE MODEL

: > "$LOG"
echo "=== degeneration RATES run start $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server; pkill -f bench2.py; sleep 4

echo "--- restoring pristine plain chat template ---" | tee -a "$LOG"
cp "$ORIG/chat_template.jinja"    "$MODEL/chat_template.jinja"
cp "$ORIG/tokenizer_config.json"  "$MODEL/tokenizer_config.json"
echo "template now: $(wc -l < "$MODEL/chat_template.jinja") lines (24=plain)" | tee -a "$LOG"

: > "$SLOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 2048 --temp 0.0 >> "$SLOG" 2>&1 & disown
for i in $(seq 1 120); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== server up (seed fix loaded) $(date -Iseconds) ===" | tee -a "$LOG"

echo "--- SEED-VARIATION GATE: 2 seeds, same combo, must DIFFER ---" | tee -a "$LOG"
GATE=$("$BENCHPY" - <<'PY'
import json, urllib.request, os
BASE=os.environ["BASE"]; MODEL=os.environ["MODEL"]
def gen(seed):
    body={"model":MODEL,"messages":[{"role":"user","content":"você executa código"}],
          "max_tokens":200,"stream":False,"temperature":0.7,"min_p":0.02,
          "xtc_probability":0.5,"xtc_threshold":0.1,"presence_penalty":1.0,"seed":seed}
    req=urllib.request.Request(f"{BASE}/chat/completions",data=json.dumps(body).encode(),
                               headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=300) as r:
        return (json.loads(r.read())["choices"][0]["message"]["content"] or "")
a,b=gen(0),gen(1)
print("VARY" if a!=b else "IDENTICAL")
PY
)
echo "SEED VARIATION: $GATE" | tee -a "$LOG"
if [ "$GATE" != "VARY" ]; then
  echo "!! seeds still identical — fix did not take effect; ABORTING rate run." | tee -a "$LOG"
  echo "(server left up for inspection)" | tee -a "$LOG"
  exit 1
fi

echo "--- RATE sweep: 4 configs x 2 prompts x 8 seeds ---" | tee -a "$LOG"
cd "$ROOT"
export ONLY="ctrl_t0.6,combo_xtc_presence,abl_presence0.5,abl_noxtc"
export PROMPTS_ONLY="exec_pt,qa_fact"
export SEEDS="0,1,2,3,4,5,6,7"
export OUT="$ROOT/bench/degeneration/results/degeneration-rates.jsonl"
"$BENCHPY" bench/degeneration/scripts/degeneration_sweep.py screen 2>&1 | tee -a "$LOG"

echo "=== metal::malloc in server log: $(grep -c metal::malloc "$SLOG") (want 0) ===" | tee -a "$LOG"
echo "=== rates run done $(date -Iseconds) ===" | tee -a "$LOG"
echo "(server left up. Restore DSML tool calling: pkill -f mlx_lm.server && bash fixes/deepseek-v4-flash/dsml/install.sh)" | tee -a "$LOG"
