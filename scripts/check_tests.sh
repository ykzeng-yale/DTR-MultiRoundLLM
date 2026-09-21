#!/usr/bin/env bash
# Preserve pytest's exit status. Do not pipe this gate through tail/tee.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run --extra dev pytest "$@"
