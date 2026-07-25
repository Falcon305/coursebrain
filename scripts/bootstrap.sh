#!/usr/bin/env bash
# Install coursebrain so the plugin's commands have something to call.
#
# A Claude Code plugin is markdown and JSON — it cannot install Python for you.
# This script does the one thing it can: put the CLI on PATH, or fail with the
# exact command you need to run.
set -euo pipefail

say() { printf '%s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

if command -v coursebrain >/dev/null 2>&1; then
    say "coursebrain already installed: $(coursebrain --version)"
    exec coursebrain doctor
fi

if ! command -v uv >/dev/null 2>&1; then
    die "uv is not installed.

  Install it:  curl -LsSf https://astral.sh/uv/install.sh | sh
  Then re-run: ${BASH_SOURCE[0]}

(uv is the fastest way to get an isolated Python tool. If you would rather use
pip: pipx install 'coursebrain[rag]')"
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$root/pyproject.toml" ]; then
    say "installing coursebrain from $root"
    uv tool install --force --with-editable "$root" "coursebrain[rag] @ $root" 2>/dev/null \
        || uv tool install --force "$root"'[rag]'
else
    say "installing coursebrain from PyPI"
    uv tool install --force 'coursebrain[rag]'
fi

command -v coursebrain >/dev/null 2>&1 || die "install finished but coursebrain is not on PATH.
Add uv's tool directory to your shell profile:  uv tool update-shell"

say "installed: $(coursebrain --version)"
exec coursebrain doctor
