#!/usr/bin/env bash
#
# install-skills.sh — install opencode-arch skills into the global OpenCode
# skills directory so they load for any target repo.
#
# OpenCode discovers skills at ~/.config/opencode/skills/<name>/SKILL.md. The
# arch_* tools run against arbitrary target repos, so the skills must live in
# the GLOBAL dir (a project-local .opencode/skills/ would only be found inside
# this repo's worktree).
#
# Mechanism: COPY. This is re-runnable and self-contained — no dependency on
# this checkout staying on disk. Each skill dir under skills/ is copied to
# ~/.config/opencode/skills/<name>/.
#
# FOR LATER (deferred upgrade): symlink instead of copy, so edits here are
# picked up live without re-running the installer:
#
#     ln -snf "<repo>/skills/<name>" ~/.config/opencode/skills/<name>
#
# Symlinking is the eventually-recommended mechanism (single source of truth,
# zero drift) but is deferred until the skills stabilise.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC_DIR="${REPO_ROOT}/skills"
DEST_DIR="${HOME}/.config/opencode/skills"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "error: no skills/ directory at ${SRC_DIR}" >&2
  exit 1
fi

mkdir -p "${DEST_DIR}"

installed=0
for skill_path in "${SRC_DIR}"/*/; do
  [[ -d "${skill_path}" ]] || continue
  name="$(basename "${skill_path}")"
  if [[ ! -f "${skill_path}/SKILL.md" ]]; then
    echo "skip ${name}: no SKILL.md" >&2
    continue
  fi
  dest="${DEST_DIR}/${name}"
  rm -rf "${dest}"
  cp -R "${skill_path%/}" "${dest}"
  echo "installed ${name} -> ${dest}"
  installed=$((installed + 1))
done

echo "done: ${installed} skill(s) copied into ${DEST_DIR}"
