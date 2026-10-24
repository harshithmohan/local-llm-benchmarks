#!/usr/bin/env bash
#
# shoko-logs runtime acceptance harness — one-command entry point.
#
# Usage:
#   SHOKO_WEBUI_DIR=/path/to/Shoko-WebUI ./run.sh [extra playwright args]
#
# SHOKO_WEBUI_DIR is REQUIRED and is forwarded to Playwright (which boots that
# checkout's Vite dev server via scripts/dev-server.mjs). Exits non-zero if any
# assertion fails. Any extra args are passed straight to `playwright test`
# (e.g. a single spec path, --headed, --debug).
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HARNESS_DIR"

if [[ -z "${SHOKO_WEBUI_DIR:-}" ]]; then
  echo "error: SHOKO_WEBUI_DIR is not set." >&2
  echo "       Usage: SHOKO_WEBUI_DIR=/path/to/Shoko-WebUI ./run.sh" >&2
  exit 2
fi
if [[ ! -d "$SHOKO_WEBUI_DIR" ]]; then
  echo "error: SHOKO_WEBUI_DIR is not a directory: $SHOKO_WEBUI_DIR" >&2
  exit 2
fi
export SHOKO_WEBUI_DIR

if ! command -v pnpm >/dev/null 2>&1; then
  echo "error: pnpm not found on PATH." >&2
  exit 2
fi

# Install harness deps on first use. The harness keeps its own node_modules and
# never touches the checkout's dependencies.
if [[ ! -d node_modules ]]; then
  echo "[harness] installing harness dependencies..."
  pnpm install
fi

# Ensure the Chromium browser used by Playwright is present (idempotent; quick
# when already installed).
pnpm exec playwright install chromium

echo "[harness] running against SHOKO_WEBUI_DIR=$SHOKO_WEBUI_DIR"
exec pnpm exec playwright test "$@"
