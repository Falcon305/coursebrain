#!/usr/bin/env bash
# Install the coursebrain CLI.
#
# Safe to run from anywhere, including a bare `curl | bash` with no clone. A Claude
# Code plugin is markdown and JSON — it cannot install Python for you — so this does
# the one thing it can: put the CLI on PATH, or fail with the exact command to run.
#
#   scripts/bootstrap.sh              # install, or upgrade if already present
#   scripts/bootstrap.sh --force      # reinstall even if already present
set -euo pipefail

REPO="${COURSEBRAIN_REPO:-https://github.com/Falcon305/coursebrain}"
SPEC="coursebrain[rag] @ git+${REPO}"

say()  { printf '%s\n' "$*" >&2; }
die()  { printf '\nerror: %s\n' "$*" >&2; exit 1; }

force=0
[ "${1:-}" = "--force" ] && force=1

if [ "$force" -eq 0 ] && command -v coursebrain >/dev/null 2>&1; then
    say "coursebrain is already installed: $(coursebrain --version)"
    say "re-run with --force to reinstall"
    exec coursebrain doctor
fi

if ! command -v uv >/dev/null 2>&1; then
    die "uv is not installed, and it is the only prerequisite.

  Install it:
    curl -LsSf https://astral.sh/uv/install.sh | sh

  Then run this script again. (Prefer pip? \`pipx install 'coursebrain[rag]'\` also works
  once the package is on PyPI; until then use uv, which can install from git.)"
fi

# a local checkout wins over the remote: contributors test their own changes
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || true)"
if [ -n "$root" ] && [ -f "$root/pyproject.toml" ]; then
    say "installing from this checkout: $root"
    uv tool install --force "coursebrain[rag] @ ${root}"
else
    say "installing from ${REPO}"
    uv tool install --force "$SPEC"
fi

if ! command -v coursebrain >/dev/null 2>&1; then
    die "installed, but coursebrain is not on PATH yet.

  Run:  uv tool update-shell
  Then open a new shell, or add uv's tool bin directory to PATH manually."
fi

say ""
say "installed $(coursebrain --version)"
say ""
exec coursebrain doctor
