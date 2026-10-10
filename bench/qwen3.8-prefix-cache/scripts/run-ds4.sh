#!/usr/bin/env bash
# ds4 upstream (antirez/ds4) servindo Qwen3.8 Flash Next pelo GGUF qwen38-q4k (MTP embutida).
# O ds4 compila os shaders Metal em runtime a partir do cwd: o comando roda dentro do repo.
# --kv-disk-dir é o prefix cache em disco do ds4; o diretório é limpo a cada subida para o
# cold ser frio. --mtp-timing liga a MTP embutida e imprime os contadores de aceitação.
set -euo pipefail
ARM="${1:-}"; OPTION="${2:-}"
DS4_DIR="${QWEN38_DS4_DIR:-$HOME/.local/opt/qwen38/ds4-upstream}"
KV_DIR="${QWEN38_DS4_KV_DIR:-$HOME/.ds4/engine-updates-kv}"
CTX="${QWEN38_CTX_SIZE:-32768}"
case "$ARM" in FD) ;; *) echo "usage: $0 {FD} [--print]" >&2; exit 64;; esac
case "$OPTION" in ""|--print) ;; *) echo "unknown option: $OPTION" >&2; exit 64;; esac
COMMAND=(env ${DS4_QWEN4_YARN_FACTOR:+"DS4_QWEN4_YARN_FACTOR=$DS4_QWEN4_YARN_FACTOR"} ./ds4-server -m ds4flash.gguf --metal --mtp-timing -c "$CTX"
  --kv-disk-dir "$KV_DIR" --kv-disk-space-mb 102400 --host 0.0.0.0 --port 11234)
if [[ "$OPTION" == "--print" ]]; then echo "cd $DS4_DIR &&"; printf '%q ' "${COMMAND[@]}"; printf '\n'; exit 0; fi
[[ -x "$DS4_DIR/ds4-server" && -e "$DS4_DIR/ds4flash.gguf" ]] || { echo "ds4 upstream incompleto em $DS4_DIR" >&2; exit 66; }
rm -rf "$KV_DIR"; mkdir -p "$KV_DIR"
cd "$DS4_DIR"
exec "${COMMAND[@]}"
