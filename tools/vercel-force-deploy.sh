#!/usr/bin/env bash
# vercel-force-deploy.sh — force a production Vercel deploy and guard against
# concurrent git-integration rebuilds silently superseding it.
#
# Operationalizes the "Deploy verification gate" step 6 in rule_behaviors.md.
# Backed by the 2026-05-15 verification-theater incident (volume-forecast deploy):
# a concurrent Vercel git-integration rebuild replaced a known-good force-deploy
# AFTER a single 200 check, so the gate now requires confirming the production
# alias still points at the intended deployment over a window, not at one moment.
#
# Usage:
#   tools/vercel-force-deploy.sh [--dir platform] [--domain unpauseai.com]
#                                [--settle 45] [--no-verify]
#
# Env overrides: VFD_DIR, VFD_DOMAIN, VFD_SETTLE_SECONDS
#
# Exit codes: 0 = deployed and verified intended deployment is live
#             1 = deploy failed
#             2 = deployed but a superseding deployment could not be corrected
set -euo pipefail

DIR="${VFD_DIR:-platform}"
DOMAIN="${VFD_DOMAIN:-unpauseai.com}"
SETTLE="${VFD_SETTLE_SECONDS:-45}"
VERIFY=1
# Identity routing (2026-07-22). unpauseai.com lives in the akkton account
# while this machine's default CLI session is usually matthias; `--scope`
# cannot bridge two ACCOUNTS, so a plain `vercel` here either fails with
# "scope does not exist" or, worse, deploys into the wrong team and creates a
# phantom project. VFD_IDENTITY routes every CLI call through
# tools/vercel-as.sh, which keeps a per-identity auth store. Empty = legacy
# behavior (bare `vercel`, whatever session is active).
IDENTITY="${VFD_IDENTITY:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)    DIR="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --settle) SETTLE="$2"; shift 2 ;;
    --no-verify) VERIFY=0; shift ;;
    --identity) IDENTITY="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

log() { printf '%s\n' "[vfd] $*"; }

# Resolve the CLI invocation once, before the cd (the wrapper path is
# repo-relative). With no identity this is exactly the historical `vercel`.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -n "$IDENTITY" ]; then
  VC=(bash "$REPO_ROOT/tools/vercel-as.sh" "$IDENTITY")
  log "identity: $IDENTITY (via tools/vercel-as.sh)"
else
  VC=(vercel)
fi

cd "$DIR"

log "Forcing production deploy from $(pwd) ..."
# Deploy once. The CLI's output format varies by version (bare URL on older
# CLIs, JSON on 53.x where `tail -1` returns `}`), so don't assume the URL
# is the last line — extract the first *.vercel.app URL from combined output.
DEPLOY_OUT="$("${VC[@]}" --prod --force --yes 2>&1 || true)"
DEPLOY_URL="$(printf '%s' "$DEPLOY_OUT" | grep -oE 'https://[a-z0-9-]+-[a-z0-9-]+\.vercel\.app' | head -1 || true)"
DEPLOY_URL="$(printf '%s' "$DEPLOY_URL" | tr -d '[:space:]')"

if [ -z "$DEPLOY_URL" ]; then
  log "ERROR: deploy produced no URL"
  exit 1
fi
log "Deployed: $DEPLOY_URL"

if [ "$VERIFY" -eq 0 ]; then
  log "--no-verify set; skipping post-deploy checks"
  exit 0
fi

# 1. Production domain returns 200.
log "Checking https://$DOMAIN ..."
CODE="$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN" || echo 000)"
if [ "$CODE" != "200" ]; then
  log "WARNING: https://$DOMAIN returned $CODE (expected 200)"
fi

# 2. Let any concurrent git-integration rebuild settle, then confirm the
#    deployment we just created is the current production deployment.
log "Settling ${SETTLE}s for concurrent rebuilds ..."
sleep "$SETTLE"

# Short host of our deployment, e.g. platform-ggrn59zmm-...
WANT="$(printf '%s' "$DEPLOY_URL" | sed -E 's#https?://##; s#/.*##')"
# `vercel ls` prints the deployment table to STDERR, so capture 2>&1 (not
# 2>/dev/null, which discards the very output we parse). The status column
# contains a UTF-8 bullet (●) before "Ready"; match on "Production" alone.
TOP_LINE="$("${VC[@]}" ls --prod 2>&1 | grep -E 'Ready[[:space:]]+Production' | head -1 || true)"
TOP_URL="$(printf '%s' "$TOP_LINE" | grep -oE 'https://[a-z0-9.-]+\.vercel\.app' | head -1 || true)"

if [ -z "$TOP_URL" ]; then
  log "WARNING: could not read current production deployment from 'vercel ls --prod'"
  log "Manual check required: vercel ls --prod"
  exit 2
fi

if [ "$TOP_URL" = "$DEPLOY_URL" ] || printf '%s' "$TOP_URL" | grep -q "$WANT"; then
  log "Verified: intended deployment is live in production ($TOP_URL)"
  exit 0
fi

log "SUPERSEDED: production now points at $TOP_URL, not $DEPLOY_URL"
log "Promoting intended deployment back to production ..."
if "${VC[@]}" promote "$DEPLOY_URL" --yes 2>/dev/null; then
  sleep 10
  CODE="$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN" || echo 000)"
  log "Promoted. https://$DOMAIN -> $CODE"
  exit 0
fi

log "ERROR: promote failed; production may be serving a stale build"
log "Manual recovery: vercel promote $DEPLOY_URL --yes"
exit 2
