#!/usr/bin/env bash
# Unattended runner of the Qwen3.8-27B next-steps campaign: speed phases P0..P6, then the quality
# battery PQ. Resumable: an arm whose results file already exists is skipped. Writes results/gates.env,
# results/campaign-log.md and etapa<N>-*.md. Start on the rig with:
#   nohup caffeinate -i bash $C/scripts/run-campaign.sh > $C/logs/campaign.log 2>&1 &
# usage: run-campaign.sh [--dry-run] [--from P<N>|PQ] [--only P<N>|PQ] [--skip-battery]
# bash 3.2 compatible (the rig's /bin/bash). --dry-run only prints: no sleep, ssh, server or file write.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
FN="$REPO/bench/flashnext-next-steps-2026-10/scripts"; S="$HERE/scripts"; R="$HERE/results"; L="$HERE/logs"
# shellcheck source=phases.sh
source "$S/phases.sh"
# decide.py globs go through eval unquoted: run from the campaign root, which holds no *.jsonl,
# so they always reach decide.py literally.
cd "$HERE" || exit 1
USAGE="usage: $0 [--dry-run] [--from P<N>|PQ] [--only P<N>|PQ] [--skip-battery]"
DRY=""; FROM=""; ONLY=""; BATTERY=1
while [[ $# -gt 0 ]]; do case "$1" in
  --dry-run) DRY=1; shift ;; --from) FROM="${2:?--from needs a phase}"; shift 2 ;; --only) ONLY="${2:?--only needs a phase}"; shift 2 ;;
  --skip-battery) BATTERY=""; shift ;; *) echo "$USAGE" >&2; exit 64 ;;
esac; done
for v in "$FROM" "$ONLY"; do
  [[ -z "$v" || " ${PHASES[*]} PQ " == *" $v "* ]] || { echo "unknown phase: $v" >&2; echo "$USAGE" >&2; exit 64; }
done
[[ -n "$DRY" ]] || mkdir -p "$R" "$L"
say() { echo "$(date '+%F %T') $*"; }
run() { if [[ -n "$DRY" ]]; then echo "$*"; else say "run: $*"; eval "$@"; fi; }
gate_set() { [[ -n "$DRY" ]] && { echo "gates.env: $1=$2"; return; }; grep -v "^$1=" "$R/gates.env" 2>/dev/null > "$R/gates.env.tmp" || true; echo "$1=$2" >> "$R/gates.env.tmp"; mv "$R/gates.env.tmp" "$R/gates.env"; }
gate_get() { grep "^$1=" "$R/gates.env" 2>/dev/null | tail -1 | cut -d= -f2; }
# an arm/band/tag is done only when its JSONL is complete: 3 reps x 4 scenarios + 1 middle_mutation
MIN_LINES=13
have_result() { local f="$R/$1-$2-t1.0-$3.jsonl"; [[ -z "$DRY" && -s "$f" ]] && (( $(grep -c . "$f") >= MIN_LINES )); }
pause() { run "sleep 120"; }  # cool-down between arms; printed, not slept, in dry-run

idle_gate() {  # retry the thermal/memory gate three times; return 75 if the band must be skipped
  local i; for i in 1 2 3; do run "bash $FN/idle-gate.sh --minutes 10" && return 0; say "idle-gate failed ($i/3)"; [[ $i == 3 ]] || sleep 300; done; return 75
}
stop_driver() { [[ -n "$DRY" ]] && echo "stop daily driver"; run "P=\$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true); [ -n \"\$P\" ] && kill \$P; sleep 5; true"; }
restart_driver() { [[ -n "$DRY" ]] && printf 'restart daily driver: '; run "nohup bash $REPO/tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &"; }

run_arm() {  # arm ctx tag effort
  if have_result "$1" "$2" "$3"; then say "skip $1@$2 $3 (exists)"; return 0; fi
  run "FLASHNEXT_EFFORT=$4 bash $S/run-arm.sh $1 $2 --repeat 3 --tag $3"; local rc=$?
  [[ -n "$DRY" ]] || echo "| $(date -u +%FT%TZ) | $1 | $2 | $3 | $4 | $rc |" >> "$R/campaign-log.md"
  pause; return $rc
}

run_think() {  # think_turn_probe on every arm of a phase at one ctx, both efforts
  local arm eff ctx="$2"; [[ -n "$DRY" ]] || mkdir -p "$R/think"
  for arm in $1; do for eff in xhigh medium; do
    [[ -z "$DRY" && -s "$R/think/$arm-$eff.jsonl" ]] && continue
    run "FLASHNEXT_EFFORT=$eff bash $S/run-arm.sh $arm $ctx --tag think$eff --exec \"python3 $FN/think_turn_probe.py --base-url \\\$BASE_URL --model \\\$MODEL_ID --arm $arm --context $ctx --reasoning-effort $eff --repeat 3 --output $R/think/$arm-$eff.jsonl\""
    pause
  done; done
}

smoke_gate() {  # phase arms -> sets SMOKE_ARMS to the arms that may run; each PHASE_<P>_SMOKE arm:mode[:min decode] runs an 8K smoke first
  local p="$1" arms="$2" n="${1#P}" spec arm mode min rest f rc ok key
  for spec in $(eval echo "\${PHASE_${p}_SMOKE:-}"); do
    arm="${spec%%:*}"; rest="${spec#*:}"; mode="${rest%%:*}"; min="$SMOKE_MIN_DECODE"
    [[ "$rest" == *:* ]] && min="${rest#*:}"
    f="$R/$arm-8192-t1.0-p${n}s.jsonl"; ok=1
    if [[ -z "$DRY" && -s "$f" ]]; then say "smoke $arm 8192 p${n}s (exists)"; else
      say "smoke $arm 8192 p${n}s"
      run "FLASHNEXT_EFFORT=medium bash $S/run-arm.sh $arm 8192 --repeat 1 --tag p${n}s"; rc=$?
      [[ -n "$DRY" ]] || echo "| $(date -u +%FT%TZ) | $arm | 8192 | p${n}s | medium | $rc |" >> "$R/campaign-log.md"
      pause; [[ $rc == 0 ]] || ok=0
    fi
    if [[ $ok == 1 ]]; then
      run "python3 $S/smoke_check.py --jsonl $f --boot-log $L/$arm-8192-t1.0-p${n}s-boot.log --mode $mode --min-decode $min" || ok=0
    fi
    [[ " $arms " == " $arm " ]] && key="${p}_SMOKE" || key="${p}_SMOKE_${arm}"
    gate_set "$key" "$ok"
    [[ $ok == 1 ]] || arms="$(echo " $arms " | sed "s/ $arm / /")"
  done
  SMOKE_ARMS="$(echo $arms)"
}

run_phase() {  # P<N>
  local p="$1" n="${1#P}" arms ctxs base rule skip ordered ctx arm eff tag
  arms="$(eval echo "\$PHASE_${p}_ARMS")"; ctxs="$(eval echo "\$PHASE_${p}_CTXS")"; base="$(eval echo "\$PHASE_${p}_BASE")"
  rule="$(eval echo "\$PHASE_${p}_RULE")"; skip="$(eval echo "\$PHASE_${p}_SKIP")"
  echo "=== phase $p: arms [$arms] ctx [$ctxs]"
  # A phase whose base is not the reference arm compares against that arm's xhigh results in the phase that ran it
  # (P4 o27sw vs o27q4 in P2, P7 w27d vs r27d in P3): both bands must be complete.
  local bn="" q
  if [[ -n "$base" && "$base" != "$REF_ARM" ]]; then
    for q in "${PHASES[@]}"; do [[ " $(eval echo "\$PHASE_${q}_ARMS") " == *" $base "* ]] && { bn="${q#P}"; break; }; done
    if [[ -z "$DRY" ]]; then
      for ctx in $ctxs; do have_result "$base" "$ctx" "p${bn}x" || {
        say "$p skipped: $base p${bn}x results incomplete"; gate_set "${p}_PASS" skipped; return; }; done
    fi
  fi
  smoke_gate "$p" "$arms"; arms="$SMOKE_ARMS"
  [[ -n "$arms" ]] || { say "phase $p skipped (smoke)"; gate_set "${p}_PASS" skipped; return; }
  local first=1
  for ctx in $ctxs; do
    # alternate order: first band reference -> candidate, later bands candidate -> reference
    if [[ $first == 1 ]]; then ordered="$arms"; else ordered="$(echo $arms | tr ' ' '\n' | tail -r | tr '\n' ' ')"; fi; first=0
    idle_gate || { say "band $ctx of $p skipped (idle-gate)"; continue; }
    for eff in xhigh medium; do
      [[ $eff == xhigh ]] && tag="p${n}x" || tag="p${n}m"
      for arm in $ordered; do run_arm "$arm" "$ctx" "$tag" "$eff"; done
    done
  done
  [[ -z "$base" ]] && return
  # think probes before the verdict so the empty-answer table below has data; P6 (llama.cpp) at 64K
  # because of llama.cpp #27756, every other phase at 128K.
  run_think "$arms" "$( [[ "$p" == P6 ]] && echo 65536 || echo 131072 )"
  local bglob skipflag="" ctxlist; ctxlist="$(echo $ctxs | tr ' ' ',')"
  if [[ "$base" == "$REF_ARM" ]]; then bglob="${base}-*-${REF_TAG}.jsonl"; else bglob="${base}-*-p${bn}x.jsonl"; fi
  [[ -n "$skip" ]] && skipflag="--skip-gates $skip"
  local md="$R/etapa${n}-$(echo $arms | cut -d' ' -f1).md"; local pass=1 best=""
  for arm in $arms; do
    local ok=1
    run "python3 $FN/decide.py --results-dir $R --logs-dir $L --glob $bglob --glob ${arm}-*-p${n}x.jsonl --base $base --cand $arm $rule $skipflag --title 'Etapa $n: $arm vs $base (xhigh)' --out-md $md" || { ok=0; pass=0; }
    # one effort per call: decide.py groups records by (arm, ctx), so mixing the globs would blend efforts
    run "python3 $FN/decide.py --results-dir $R --logs-dir $L --glob ${arm}-*-p${n}x.jsonl --ctx $ctxlist --title 'Etapa $n: $arm (xhigh)' --out-md $md || true"
    run "python3 $FN/decide.py --results-dir $R --logs-dir $L --glob ${arm}-*-p${n}m.jsonl --ctx $ctxlist --title 'Etapa $n: $arm (medium)' --out-md $md || true"
    [[ $ok == 1 && -z "$best" ]] && best="$arm"
  done
  [[ -n "$DRY" ]] || { echo; echo "## Respostas vazias (think_turn_probe)"; } >> "$md"
  for arm in $arms; do run "python3 $S/empty_answers.py $R/think/$arm-*.jsonl >> $md 2>&1 || true"; done
  gate_set "${p}_PASS" "$pass"; [[ -n "$best" ]] && gate_set "${p}_BEST" "$best"
}

run_battery() {  # PQ: Swift-style quality and time/tokens per task on the finalists
  echo "=== phase PQ: quality battery"
  local arms="o27q4 o27sw" best arm
  if [[ -n "$DRY" ]]; then best=k27; else best="$(gate_get P1_BEST)"; [[ -n "$best" ]] || best="$(gate_get P3_BEST)"; fi
  [[ -n "$best" && " $arms " != *" $best "* ]] && arms="$arms $best"
  for arm in $arms; do
    # resume: a label is done when its first suite's file exists (humaneval for medium, gpqa for xhigh)
    local med_done="" hi_done=""
    [[ -z "$DRY" && -s "$R/q/t1/$arm-medium/humaneval.jsonl" ]] && med_done=1
    [[ -z "$DRY" && -s "$R/q/t1/$arm-xhigh/gpqa.jsonl" ]] && hi_done=1
    if [[ -n "$med_done" && -n "$hi_done" ]]; then say "skip battery $arm (exists)"; continue; fi
    idle_gate || { say "battery $arm skipped (idle-gate)"; continue; }
    if [[ -n "$med_done" ]]; then say "skip battery $arm-medium (exists)"; else
      run "FLASHNEXT_EFFORT=medium BATTERY_CAMPAIGN_DIR=$HERE bash $FN/run-battery.sh $arm q --effort medium --ctx 131072 --label $arm-medium --loops"
      pause
    fi
    if [[ -n "$hi_done" ]]; then say "skip battery $arm-xhigh (exists)"; else
      run "FLASHNEXT_EFFORT=xhigh BATTERY_CAMPAIGN_DIR=$HERE bash $FN/run-battery.sh $arm q --suites 'gpqa livecodebench' --effort xhigh --ctx 131072 --label $arm-xhigh"
      pause
    fi
  done
  run "python3 $REPO/bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $R/q/t1 --base o27q4-medium --cand o27sw-medium --out $R/etapaq-swift-vs-base.md"
  run "python3 $REPO/bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $R/q/t1 --base o27q4-xhigh --cand o27q4-medium --out $R/etapaq-effort-o27q4.md"
  run "python3 $S/empty_answers.py $R/q/t1/*/*.jsonl --json > $R/etapaq-empty.json"
}

# QWEN38_CAMPAIGN_LIB=1 + source: define the functions only (tests); no trap, no driver stop, no phases.
[[ -n "${QWEN38_CAMPAIGN_LIB:-}" ]] && return 0
trap '[[ -n "$DRY" ]] || say "exit: restarting driver"; restart_driver' EXIT
echo "=== campaign start $(date -u +%FT%TZ) dry=${DRY:-0} from=${FROM:-} only=${ONLY:-}"
stop_driver
# speed phases to run (plain string: an empty array trips set -u on bash 3.2)
if [[ -z "$ONLY" ]]; then sel="${PHASES[*]}"; elif [[ "$ONLY" == PQ ]]; then sel=""; else sel="$ONLY"; fi
started=""; [[ -z "$FROM" ]] && started=1
for p in $sel; do
  [[ "$p" == "$FROM" ]] && started=1; [[ -n "$started" ]] || continue
  run_phase "$p"
done
if [[ "$ONLY" == PQ || ( -z "$ONLY" && -n "$BATTERY" ) ]]; then run_battery; fi
# Driver gate for P5 (manual, needs the MacBook + Docker): any arm with T_turno <= 1.25 x w1 on both bands.
run "python3 $S/driver_gate.py --results-dir $R --w1 $W1_T32 $W1_T128 --ratio $DRIVER_RATIO --skip-gates-arms $DRIVER_SKIP_HIT_ARMS --out $R/gates.env"
[[ -n "$ONLY" ]] || gate_set CAMPAIGN_DONE "$(date -u +%FT%TZ)"
