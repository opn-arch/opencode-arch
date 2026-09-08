#!/usr/bin/env bash
# Opt-in pre-commit hook: refresh architecture model for staged changes.
#
# Install:
#   cp docs/templates/pre-commit.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Requires: `pip install opencode-arch` (exposes the `opencode-arch` CLI).

set -euo pipefail

CHANGED=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(py|ts|tsx|js)$' || true)
if [ -z "$CHANGED" ]; then
  exit 0
fi

echo "[architecture] refreshing model for staged changes..."
if command -v opencode-arch >/dev/null 2>&1; then
  # No incremental --changed flag exists yet; run a full extraction against
  # the repo root. Swap to a scoped refresh command when one is available.
  opencode-arch extract . || {
    echo "[architecture] pre-commit refresh failed; commit aborted"
    exit 1
  }
else
  echo "[architecture] opencode-arch CLI not found; skipping (pip install opencode-arch)"
fi
