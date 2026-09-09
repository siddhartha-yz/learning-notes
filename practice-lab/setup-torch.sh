#!/usr/bin/env bash
set -euo pipefail
runtime="${LEARNING_LAB_TORCH_RUNTIME:-$HOME/.local/share/learning-notes-lab/torch-runtime}"
uv_bin="$(command -v uv || true)"
if [ -z "$uv_bin" ] && [ -x "$HOME/.local/bin/uv" ]; then uv_bin="$HOME/.local/bin/uv"; fi
if [ -z "$uv_bin" ]; then echo '需要先安装 uv，再运行此脚本。' >&2; exit 1; fi
if [ ! -x "$runtime/bin/python" ]; then "$uv_bin" venv --python /usr/bin/python3 "$runtime"; fi
"$uv_bin" pip install --python "$runtime/bin/python" 'torch==2.14.0+cpu' --index-url https://download.pytorch.org/whl/cpu
