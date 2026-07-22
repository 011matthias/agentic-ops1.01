#!/usr/bin/env bash
# vercel-as.sh — run the Vercel CLI as a named identity, so this machine can
# work on BOTH unpauseai.com (akkton account) and the Brisken projects
# (matthias account) without either login evicting the other.
#
# THE PROBLEM THIS SOLVES
# -----------------------
# The Vercel CLI keeps ONE interactive session in its global config dir, and
# `--scope` only switches between TEAMS INSIDE the logged-in account. akkton
# and matthias are two separate ACCOUNTS, so scope cannot bridge them: whoever
# logged in last wins, and the other account's projects become invisible.
# Recorded live 2026-07-22: the session was matthias-5647, `vercel project ls`
# showed only the Brisken/personal projects, and the akkton org that owns
# `platform` (unpauseai.com) reported "scope does not exist" — so the platform
# force-deploy could not run at all. Deploying under the only visible scope
# would have created a phantom "platform" project under the wrong team.
#
# THE MECHANISM
# -------------
# `vercel -Q DIR` / `--global-config=DIR` (verified on CLI 53.2.0) relocates
# the CLI's global `.vercel` directory, and with it the auth store. Point each
# identity at its own directory and both stay logged in side by side,
# permanently. Logging in to one NEVER touches the other.
#
# SETUP (once per identity, interactive — a browser login only the account
# owner can complete):
#   tools/vercel-as.sh unpause login      # log in as akkton
#   tools/vercel-as.sh brisken login      # log in as matthias
#
# DAILY USE (identity is implied by the project, never by "who am I today"):
#   tools/vercel-as.sh unpause --prod --force --yes   # deploy unpauseai.com
#   tools/vercel-as.sh brisken project ls             # Brisken estate
#   tools/vercel-as.sh unpause whoami                 # -> akkton
#
# TOKEN MODE (headless / CI / agent use, no interactive login at all): set the
# identity's token env var and it is passed through as --token, which takes
# precedence over the stored session:
#   VERCEL_TOKEN_UNPAUSE=... tools/vercel-as.sh unpause --prod
#   VERCEL_TOKEN_BRISKEN=... tools/vercel-as.sh brisken deploy
#
# Identities are declared here, not guessed. Adding one is a two-line edit.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: tools/vercel-as.sh <identity> [vercel args...]

identities:
  unpause   akkton account      -> unpauseai.com (project: platform)
  brisken   matthias account    -> brisken.com, resources.brisken.com, etc.
              (scope: matthias-neumanns-projects)

examples:
  tools/vercel-as.sh unpause login
  tools/vercel-as.sh unpause --prod --force --yes
  tools/vercel-as.sh brisken project ls
  tools/vercel-as.sh unpause whoami

Each identity keeps its own auth store under ~/.vercel-<identity>, so the two
logins coexist. Set VERCEL_TOKEN_UNPAUSE / VERCEL_TOKEN_BRISKEN to run headless.
EOF
  exit 64
}

[ $# -ge 1 ] || usage
IDENTITY="$1"; shift

case "$IDENTITY" in
  unpause)
    CONFIG_DIR="${VERCEL_CONFIG_UNPAUSE:-$HOME/.vercel-unpause}"
    TOKEN="${VERCEL_TOKEN_UNPAUSE:-}"
    SCOPE=""            # akkton account's own scope is its default; no override
    ;;
  brisken)
    CONFIG_DIR="${VERCEL_CONFIG_BRISKEN:-$HOME/.vercel-brisken}"
    TOKEN="${VERCEL_TOKEN_BRISKEN:-}"
    SCOPE="matthias-neumanns-projects"
    ;;
  -h|--help|help) usage ;;
  *) echo "unknown identity: $IDENTITY" >&2; usage ;;
esac

[ $# -ge 1 ] || usage

mkdir -p "$CONFIG_DIR"

ARGS=(--global-config "$CONFIG_DIR")
[ -n "$TOKEN" ] && ARGS+=(--token "$TOKEN")
# `login` establishes the identity; a --scope on it is meaningless (there is no
# session yet to scope), so only pass scope to real commands.
if [ -n "$SCOPE" ] && [ "${1:-}" != "login" ] && [ "${1:-}" != "logout" ]; then
  ARGS+=(--scope "$SCOPE")
fi

echo "[vercel-as] identity=$IDENTITY config=$CONFIG_DIR${TOKEN:+ (token mode)}" >&2
exec vercel "${ARGS[@]}" "$@"
