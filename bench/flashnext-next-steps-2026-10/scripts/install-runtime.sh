#!/usr/bin/env bash
# Install one runtime of the campaign under ~/.local/opt/qwen38/, isolated, without touching ~/.local/bin.
# usage: install-runtime.sh <mlx-serve|omlx|llama> [--print]
#   mlx-serve  ddalcu/mlx-serve v26.10.2-pre-release.1, asset mlx-serve-bin-macos-arm64.tar.gz, extracted with
#              --strip-components=1 (same layout as v26.10.1) into mlx-serve-v26.10.2-pre-release.1/
#   omlx       jundot/omlx tag v0.7.1.dev1 in a uv venv (python 3.13) at omlx-v0.7.1.dev1/ (pattern of 0.7.0)
#   llama      ggml-org/llama.cpp release $LLAMA_TAG (default b11569), macOS arm64 asset, into llama-<tag>/
# Binary assets are checked against the SHA256 digest GitHub publishes for the asset. When GitHub has no
# digest, the script stops (exit 65); compare the hash it prints with the release page and rerun with
# INSTALL_EXPECTED_SHA256=<hex>.
set -euo pipefail
WHAT="${1:?usage: $0 <mlx-serve|omlx|llama> [--print]}"
PRINT="${2:-}"
OPT="${QWEN38_OPT:-$HOME/.local/opt/qwen38}"
GH="${GH_BIN:-/opt/homebrew/bin/gh}"
MLX_TAG=v26.10.2-pre-release.1
OMLX_TAG=v0.7.1.dev1
LLAMA_TAG="${LLAMA_TAG:-b11569}"

case "$WHAT" in
  mlx-serve) DEST="$OPT/mlx-serve-$MLX_TAG" ;;
  omlx) DEST="$OPT/omlx-$OMLX_TAG" ;;
  llama) DEST="$OPT/llama-$LLAMA_TAG" ;;
  *) echo "usage: $0 <mlx-serve|omlx|llama> [--print]" >&2; exit 64 ;;
esac
if [[ "$PRINT" == --print ]]; then
  case "$WHAT" in
    mlx-serve) echo "gh release download $MLX_TAG -R ddalcu/mlx-serve -p mlx-serve-bin-macos-arm64.tar.gz -> $DEST" ;;
    omlx) echo "uv venv --python 3.13 $DEST && uv pip install 'omlx @ git+https://github.com/jundot/omlx.git@$OMLX_TAG'" ;;
    llama) echo "gh release download $LLAMA_TAG -R ggml-org/llama.cpp -p '*bin-macos-arm64*' -> $DEST" ;;
  esac
  exit 0
fi
[[ -n "$PRINT" ]] && { echo "unknown option: $PRINT" >&2; exit 64; }
[[ -e "$DEST" ]] && { echo "install-runtime: $DEST already exists; remove it first to reinstall" >&2; exit 73; }

# Download one release asset and check it against the digest GitHub publishes (or INSTALL_EXPECTED_SHA256).
fetch_asset() {  # fetch_asset <repo> <tag> <asset> <dir>
  local repo="$1" tag="$2" asset="$3" dir="$4" want got
  "$GH" release download "$tag" -R "$repo" -p "$asset" -D "$dir"
  want="$("$GH" api "repos/$repo/releases/tags/$tag" --jq ".assets[] | select(.name==\"$asset\") | .digest" || true)"
  want="${want#sha256:}"
  [[ "$want" == null ]] && want=""
  want="${INSTALL_EXPECTED_SHA256:-$want}"
  got="$(shasum -a 256 "$dir/$asset" | cut -d' ' -f1)"
  echo "asset: $asset"; echo "sha256: $got"
  if [[ -z "$want" ]]; then
    echo "install-runtime: no published digest for $asset; check the hash above on the release page and rerun with INSTALL_EXPECTED_SHA256" >&2
    exit 65
  fi
  [[ "$got" == "$want" ]] || { echo "install-runtime: sha256 mismatch (want $want)" >&2; exit 65; }
  echo "sha256 check: OK"
}

TMP="$(mktemp -d -t install-runtime)"
trap 'rm -rf "$TMP"' EXIT
case "$WHAT" in
  mlx-serve)
    fetch_asset ddalcu/mlx-serve "$MLX_TAG" mlx-serve-bin-macos-arm64.tar.gz "$TMP"
    mkdir -p "$DEST"
    tar -xzf "$TMP/mlx-serve-bin-macos-arm64.tar.gz" -C "$DEST" --strip-components=1
    "$DEST/mlx-serve" --version ;;
  omlx)
    uv venv --python 3.13 "$DEST"
    uv pip install --python "$DEST/bin/python" "omlx @ git+https://github.com/jundot/omlx.git@$OMLX_TAG"
    "$DEST/bin/omlx" --version
    "$DEST/bin/python" -c 'import mlx.core as mx; print("mlx", mx.__version__)' ;;
  llama)
    ASSET="$("$GH" release view "$LLAMA_TAG" -R ggml-org/llama.cpp --json assets --jq '.assets[].name' \
      | grep -E 'bin-macos-arm64\.(zip|tar\.gz)$' | head -1)"
    [[ -n "$ASSET" ]] || { echo "install-runtime: no macOS arm64 asset in llama.cpp $LLAMA_TAG" >&2; exit 66; }
    fetch_asset ggml-org/llama.cpp "$LLAMA_TAG" "$ASSET" "$TMP"
    mkdir -p "$TMP/x"
    case "$ASSET" in
      *.zip) unzip -q "$TMP/$ASSET" -d "$TMP/x" ;;
      *) tar -xzf "$TMP/$ASSET" -C "$TMP/x" ;;
    esac
    SRV="$(find "$TMP/x" -type f -name llama-server | head -1)"
    [[ -n "$SRV" ]] || { echo "install-runtime: llama-server not found in $ASSET" >&2; exit 66; }
    mkdir -p "$DEST"
    cp -R "$(dirname "$SRV")/." "$DEST/"
    "$DEST/llama-server" --version 2>&1 | tail -2 ;;
esac
echo "installed: $DEST"
