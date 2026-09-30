#!/usr/bin/env bash
# One-shot setup for a fresh clone: checks the toolchain, installs dependencies, regenerates the
# git-ignored parser output, builds the module, and runs the validator and tests.
#
#   ./setup.sh            # full setup
#   ./setup.sh --no-check # skip validate and test (just install, parse, build)
#
# Works in Git Bash on Windows as well as Linux and macOS. Run it from anywhere; it cds to the repo root.

set -euo pipefail
cd "$(dirname "$0")"

run_checks=1
[ "${1:-}" = "--no-check" ] && run_checks=0

fail() { printf 'setup: %s\n' "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }

step "checking toolchain"
command -v node >/dev/null 2>&1 || fail "node not found; install Node 18 or newer (https://nodejs.org)"
command -v npm  >/dev/null 2>&1 || fail "npm not found; it ships with Node"
node_major=$(node -p 'process.versions.node.split(".")[0]')
[ "$node_major" -ge 18 ] || fail "Node 18 or newer is required, found $(node --version)"

# The npm scripts call python3 by name, so that is what must resolve.
command -v python3 >/dev/null 2>&1 || fail "python3 not found; install Python 3 (https://python.org)"
printf 'node %s, npm %s, %s\n' "$(node --version)" "$(npm --version)" "$(python3 --version)"

[ -f data/corgo-77-v3.md ] || fail "data/corgo-77-v3.md is missing; the build reads Corgo's document from there"

step "installing node dependencies"
npm ci

step "parsing the document into data/*.parsed.json"
npm run parse

step "building src/packs and dist/corgo-77-collection"
npm run build

if [ "$run_checks" -eq 1 ]; then
  step "validating the built packs against CPR 0.92.4"
  npm run validate

  step "running the original-text tests"
  npm test
fi

step "done"
echo "The installable module is in dist/corgo-77-collection."
echo "See CLAUDE.md for the tooling."
