#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Activate ~/picenv first: source ~/picenv/bin/activate" >&2
  exit 2
fi

python -m pip install -e '.[dev]'

if ! /usr/bin/python3 -c 'import numpy, pyopenvdb' 2>/dev/null; then
  echo "System OpenVDB bindings are missing. Install them with:" >&2
  echo "  sudo apt update && sudo apt install python3-numpy python3-openvdb" >&2
fi

if ! command -v blender >/dev/null && [[ ! -x "$HOME/.local/opt/blender-4.5/blender" ]]; then
  echo "Blender was not found. Download the latest Blender 4.5 LTS Linux portable archive" >&2
  echo "from https://www.blender.org/download/lts/4-5/ and extract or symlink it as:" >&2
  echo "  $HOME/.local/opt/blender-4.5/blender" >&2
fi
