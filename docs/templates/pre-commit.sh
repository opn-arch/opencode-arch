#!/usr/bin/env bash
# Opt-in pre-commit hook: refresh architecture model for staged changes.
#
# Install:
#   cp docs/templates/pre-commit.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Requires: `pip install opencode-arch` (exposes the `opencode-arch` CLI).
#
# Behavior:
#   - By default the hook is warning-only: extraction failures (network,
#     auth, LLM errors) log a warning but do NOT block the commit. This
#     avoids `--no-verify` escape hatches becoming the default habit.
#   - Set OPENCODE_ARCH_STRICT=1 in your environment to make failures
#     abort the commit (recommended for CI-like local setups).

set -uo pipefail

CHANGED=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(py|ts|tsx|js)$' || true)
if [ -z "$CHANGED" ]; then
  exit 0
fi

echo "[architecture] refreshing model for staged changes..."
if command -v opencode-arch >/dev/null 2>&1; then
  # No incremental --changed flag exists yet; run a full extraction against
  # the repo root. Swap to a scoped refresh command when one is available.
  if ! opencode-arch extract .; then
    if [ "${OPENCODE_ARCH_STRICT:-0}" = "1" ]; then
      echo "[architecture] pre-commit refresh failed; commit aborted (OPENCODE_ARCH_STRICT=1)"
      exit 1
    fi
    echo "[architecture] pre-commit refresh failed; continuing (set OPENCODE_ARCH_STRICT=1 to abort)"
  fi
else
  echo "[architecture] opencode-arch CLI not found; skipping (pip install opencode-arch)"
fi
