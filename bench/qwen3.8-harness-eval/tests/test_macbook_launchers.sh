#!/usr/bin/env bash
# Contract of the MacBook launchers: every harness receives the run's effort
# level from EFFORT (default medium) and points at the rig endpoint of TARGET
# (27b -> mlx-dspark:8484, fn -> mlx-serve:11234).
# `--print` after the run dir echoes the env lines and the command instead of
# executing the harness.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MB="$ROOT/bench/qwen3.8-harness-eval/macbook"
MODEL_ID="mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
FN_MODEL_ID="ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"

bash -n "$MB/lib.sh"
for h in cc oc qc pi dsh; do
  bash -n "$MB/run-$h.sh"
  bash -n "$MB/run-$h-27b.sh"
  bash -n "$MB/run-$h-fn.sh"
done

T="$(mktemp -d /tmp/qwen38-macbook-launcher.XXXXXX)"
trap 'rm -rf "$T"' EXIT

# Claude Code: effort travels as CLAUDE_CODE_EFFORT_LEVEL (overrides /effort and settings.json).
CC_DEFAULT="$(bash "$MB/run-cc-27b.sh" "$T" --print)"
grep -q -- '^CLAUDE_CODE_EFFORT_LEVEL=medium$' <<<"$CC_DEFAULT"
grep -q -- '^ANTHROPIC_BASE_URL=http://mac-studio:8484$' <<<"$CC_DEFAULT"
grep -q -- "^ANTHROPIC_MODEL=$MODEL_ID\$" <<<"$CC_DEFAULT"
grep -q -- '^CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072$' <<<"$CC_DEFAULT"
[[ "$(tail -n 1 <<<"$CC_DEFAULT")" == "claude" ]]
CC_XHIGH="$(EFFORT=xhigh bash "$MB/run-cc-27b.sh" "$T" --print)"
grep -q -- '^CLAUDE_CODE_EFFORT_LEVEL=xhigh$' <<<"$CC_XHIGH"
CC_PORT="$(RIG_PORT=8000 bash "$MB/run-cc-27b.sh" "$T" --print)"
grep -q -- '^ANTHROPIC_BASE_URL=http://mac-studio:8000$' <<<"$CC_PORT"

# OpenCode: the TUI has no --variant flag; the variant rides in OPENCODE_CONFIG_CONTENT.
OC_LOW="$(EFFORT=low bash "$MB/run-oc-27b.sh" "$T" --print)"
grep -q -- "^OPENCODE_CONFIG_CONTENT=.*\"variant\":\"low\"" <<<"$OC_LOW"
grep -q -- "^OPENCODE_CONFIG_CONTENT=.*\"model\":\"rig/$MODEL_ID\"" <<<"$OC_LOW"
grep -q -- '"baseURL":"http://mac-studio:8484/v1"' <<<"$OC_LOW"
[[ "$(tail -n 1 <<<"$OC_LOW")" == "opencode --model rig/$MODEL_ID" ]]
OC_RUN="$(bash "$MB/run-oc-27b.sh" "$T" --print run hi)"
[[ "$(tail -n 1 <<<"$OC_RUN")" == "opencode run hi --model rig/$MODEL_ID" ]]
OC_DEFAULT="$(bash "$MB/run-oc-27b.sh" "$T" --print)"
grep -q -- '"variant":"medium"' <<<"$OC_DEFAULT"

# Qwen Code: effort lives in the workspace settings file of the run dir.
QC_XHIGH="$(EFFORT=xhigh bash "$MB/run-qc-27b.sh" "$T" --print)"
grep -q -- '^OPENAI_BASE_URL=http://mac-studio:8484/v1$' <<<"$QC_XHIGH"
grep -q -- "^OPENAI_MODEL=$MODEL_ID\$" <<<"$QC_XHIGH"
[[ "$(tail -n 1 <<<"$QC_XHIGH")" == "qwen -m $MODEL_ID" ]]
python3 - "$T/.qwen/settings.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["model"]["reasoningEffort"] == "xhigh", d
assert d["model"]["generationConfig"]["extra_body"]["reasoning_effort"] == "xhigh", d
EOF
bash "$MB/run-qc-27b.sh" "$T" --print >/dev/null
grep -q -- '"reasoningEffort": "medium"' "$T/.qwen/settings.json"

# Pi: --thinking carries the level; the model is the rig provider entry.
PI_LOW="$(EFFORT=low bash "$MB/run-pi-27b.sh" "$T" --print)"
[[ "$(tail -n 1 <<<"$PI_LOW")" == "pi --model rig/$MODEL_ID --thinking low" ]]
PI_DEFAULT="$(bash "$MB/run-pi-27b.sh" "$T" --print)"
grep -q -- '--thinking medium$' <<<"$PI_DEFAULT"

# DeepSeek Harness: the run's effort is the agent-default-model section of
# $DSH_HOME/settings.yaml; other sections survive the rewrite.
DSH_T="$T/dsh-home"
mkdir -p "$DSH_T"
printf 'agent-presets:\n  default: code\nagent-default-model:\n  provider: old\n  model: old-model\n  reasoningEffort: xhigh\nllm-pi-ai:\n  providers: {}\n' >"$DSH_T/settings.yaml"
DSH_LOW="$(EFFORT=low DSH_HOME="$DSH_T" bash "$MB/run-dsh-27b.sh" "$T" --print)"
grep -q -- '^DSH_TELEMETRY_MODE=DISABLED$' <<<"$DSH_LOW"
grep -q -- '^RIG_API_KEY=local$' <<<"$DSH_LOW"
grep -q -- "^DSH_HOME=$DSH_T\$" <<<"$DSH_LOW"
[[ "$(tail -n 1 <<<"$DSH_LOW")" == "dsh --profile web" ]]
grep -q -- '^agent-presets:$' "$DSH_T/settings.yaml"
grep -q -- '^llm-pi-ai:$' "$DSH_T/settings.yaml"
[[ "$(grep -c -- '^agent-default-model:$' "$DSH_T/settings.yaml")" -eq 1 ]]
grep -q -- '^  provider: rig$' "$DSH_T/settings.yaml"
grep -q -- "^  model: $MODEL_ID\$" "$DSH_T/settings.yaml"
grep -q -- '^  reasoningEffort: low$' "$DSH_T/settings.yaml"
! grep -q -- 'old' "$DSH_T/settings.yaml"
DSH_HEADLESS="$(DSH_PROFILE=headless DSH_HOME="$DSH_T" bash "$MB/run-dsh-27b.sh" "$T" --print)"
grep -q -- '--profile headless$' <<<"$DSH_HEADLESS"
grep -q -- '^  reasoningEffort: medium$' "$DSH_T/settings.yaml"
DSH_BIN_OVERRIDE="$(DSH_BIN=/opt/dsh DSH_HOME="$DSH_T" bash "$MB/run-dsh-27b.sh" "$T" --print)"
grep -q -- '^/opt/dsh --profile' <<<"$DSH_BIN_OVERRIDE"
DSH_FRESH="$(DSH_HOME="$T/dsh-fresh" bash "$MB/run-dsh-27b.sh" "$T" --print)"
grep -q -- '^  provider: rig$' "$T/dsh-fresh/settings.yaml"

# Target fn: Flash-Next on mlx-serve, port 11234, provider rigfn.
FN_CC="$(bash "$MB/run-cc-fn.sh" "$T" --print)"
grep -q -- '^ANTHROPIC_BASE_URL=http://mac-studio:11234$' <<<"$FN_CC"
grep -q -- "^ANTHROPIC_MODEL=$FN_MODEL_ID\$" <<<"$FN_CC"
FN_OC="$(EFFORT=none bash "$MB/run-oc-fn.sh" "$T" --print)"
grep -q -- '"baseURL":"http://mac-studio:11234/v1"' <<<"$FN_OC"
grep -q -- "\"model\":\"rigfn/$FN_MODEL_ID\"" <<<"$FN_OC"
grep -q -- '"variant":"none"' <<<"$FN_OC"
[[ "$(tail -n 1 <<<"$FN_OC")" == "opencode --model rigfn/$FN_MODEL_ID" ]]
FN_QC="$(EFFORT=high bash "$MB/run-qc-fn.sh" "$T" --print)"
grep -q -- '^OPENAI_BASE_URL=http://mac-studio:11234/v1$' <<<"$FN_QC"
grep -q -- "^OPENAI_MODEL=$FN_MODEL_ID\$" <<<"$FN_QC"
grep -q -- '"reasoningEffort": "high"' "$T/.qwen/settings.json"
FN_PI="$(EFFORT=minimal bash "$MB/run-pi-fn.sh" "$T" --print)"
[[ "$(tail -n 1 <<<"$FN_PI")" == "pi --model rigfn/$FN_MODEL_ID --thinking minimal" ]]
DSH_FN="$T/dsh-fn"
FN_DSH="$(EFFORT=xhigh DSH_HOME="$DSH_FN" bash "$MB/run-dsh-fn.sh" "$T" --print)"
grep -q -- '^  provider: rigfn$' "$DSH_FN/settings.yaml"
grep -q -- "^  model: $FN_MODEL_ID\$" "$DSH_FN/settings.yaml"
grep -q -- '^  reasoningEffort: xhigh$' "$DSH_FN/settings.yaml"

# The implementation scripts default to TARGET=27b.
CORE_DEFAULT="$(bash "$MB/run-cc.sh" "$T" --print)"
grep -q -- '^ANTHROPIC_BASE_URL=http://mac-studio:8484$' <<<"$CORE_DEFAULT"

# Every launcher accepts the six efforts the model exposes and rejects anything
# else. The runtime does not validate the string, so this is the only guard.
for h in cc oc qc pi dsh; do
  for target in 27b fn; do
    for effort in none minimal low medium high xhigh; do
      if ! EFFORT="$effort" DSH_HOME="$T/dsh-matrix" bash "$MB/run-$h-$target.sh" "$T" --print >/dev/null 2>&1; then
        echo "run-$h-$target.sh rejected EFFORT=$effort" >&2
        exit 1
      fi
    done
    if EFFORT=bogus DSH_HOME="$T/dsh-matrix" bash "$MB/run-$h-$target.sh" "$T" --print >/dev/null 2>&1; then
      echo "run-$h-$target.sh accepted EFFORT=bogus" >&2
      exit 1
    fi
  done
  if TARGET=bogus DSH_HOME="$T/dsh-matrix" bash "$MB/run-$h.sh" "$T" --print >/dev/null 2>&1; then
    echo "run-$h.sh accepted TARGET=bogus" >&2
    exit 1
  fi
done

echo "macbook launchers: ok"
