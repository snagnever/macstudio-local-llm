#!/usr/bin/env bash
# Run on the rig: start one arm through run-arm.sh and keep it serving until <flag-file> exists (the Terminal-Bench
# runner on the laptop touches it at the end). run-candidate.sh records memory samples and stops the server after.
# usage: hold-arm.sh <arm> <ctx> <flag-file> [--print]
set -euo pipefail
ARM="${1:?usage: $0 <arm> <ctx> <flag-file> [--print]}"; CTX="${2:?ctx}"; FLAG="${3:?flag-file}"; shift 3
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$FLAG" == /* ]] || FLAG="$HERE/$FLAG"  # the --exec shell does not run in this folder
exec bash "$HERE/scripts/run-arm.sh" "$ARM" "$CTX" --tag hold --exec "until [ -f $FLAG ]; do sleep 60; done" "$@"
