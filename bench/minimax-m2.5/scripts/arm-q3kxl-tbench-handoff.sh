#!/usr/bin/env bash
# ── RUN THIS ON THE MBP, DETACHED (PID 1). Arms the UD-Q3_K_XL T-Bench hand-off. ──
# Polls until BOTH are true, then launches the q3_k_xl remote driver under caffeinate:
#   A. the in-flight IQ2_M job is complete (all 89 trials resolved), so the rig is free, and
#   B. the rig's /api/v0/models shows minimax-m2.5@q3_k_xl LOADED
#      (i.e. someone ran the rig speed probe — run-minimax-q3kxl-speedprobe.sh — on the rig).
# This self-synchronises with the rig speed probe whenever it happens; no SSH needed.
#
# Launch (detached so the harness can't reap it — the failure mode that killed IQ2_M twice):
#   ( nohup bash bench/minimax-m2.5/scripts/arm-q3kxl-tbench-handoff.sh >/dev/null 2>&1 & disown )
set -u

REPO="$HOME/LocalProjects/macstudio-local-llm"
cd "$REPO" || exit 1
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

RIG=http://macstudio.local:1234
IQ2M_JOB="$REPO/bench/terminal-bench/logs/tbench-runs/minimax-m2.5-iq2m-remote"
NEXT_MODEL="minimax-m2.5@q3_k_xl"
DRIVER="$REPO/bench/terminal-bench/scripts/run-tbench-minimax-q3kxl-REMOTE.sh"
LOG="$REPO/bench/minimax-m2.5/logs/q3kxl-arm.log"
mkdir -p "$(dirname "$LOG")"
say(){ echo "=== $* $(date -Iseconds) ===" >> "$LOG"; }

say "ARMED — waiting for [IQ2_M complete] AND [$NEXT_MODEL loaded on rig]"

iq2m_done(){
  python3 - "$IQ2M_JOB/result.json" <<'PY' 2>/dev/null
import json,sys
try:
    s=json.load(open(sys.argv[1]))['stats']
    ok = s['n_pending_trials']==0 and s['n_running_trials']==0
    sys.exit(0 if ok else 1)
except Exception:
    sys.exit(1)
PY
}

q3kxl_loaded(){
  python3 - "$RIG/api/v0/models" "$NEXT_MODEL" <<'PY' 2>/dev/null
import json,sys,urllib.request
url,mid=sys.argv[1],sys.argv[2]
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        d=json.load(r)
    for m in d.get('data',[]):
        if m.get('id')==mid and m.get('state')=='loaded':
            sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
PY
}

# --- wait for both conditions ---
a_logged=0; b_logged=0
while true; do
  if iq2m_done; then [ $a_logged -eq 0 ] && { say "condition A met: IQ2_M job complete"; a_logged=1; }
  fi
  if q3kxl_loaded; then [ $b_logged -eq 0 ] && { say "condition B met: $NEXT_MODEL loaded on rig"; b_logged=1; }
  fi
  if iq2m_done && q3kxl_loaded; then break; fi
  sleep 60
done

say "BOTH conditions met — launching UD-Q3_K_XL Terminal-Bench under caffeinate"
caffeinate -i -s bash "$DRIVER" >> "$LOG" 2>&1
say "UD-Q3_K_XL T-Bench driver returned rc=$?"

# On a silent kill mid-run, resume with:
#   harbor job resume -p bench/terminal-bench/logs/tbench-runs/minimax-m2.5-q3kxl-remote -y
say "ARM SCRIPT DONE"
