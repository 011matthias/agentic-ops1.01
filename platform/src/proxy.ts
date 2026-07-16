// Next.js 16 renamed `middleware.ts` to `proxy.ts`. This file is what runs
// on every request matching the `config.matcher` below.
//
// Server-side gate for every client doc site (registry: lib/gated-sites.ts).
// This is the ONLY sanctioned gating model — access codes and the master
// password live in env vars and are never shipped to the browser. The old
// in-page JS overlays (which shipped the passcode in plaintext) are gone.
//
// NOTE: NextAuth-based gating for /admin and /portal is a separate concern
// and intentionally out of scope here — see lib/auth.ts when that is picked
// up.

import { NextRequest, NextResponse } from "next/server"
import { cookieMatches, resolveSecret, siteForPath } from "./lib/gated-sites"

const LOGIN_PATH = "/gate-login"
const UNLOCK_PATH = "/api/gate-unlock"

export async function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname

  // Let the login page and unlock API through unconditionally.
  if (path === LOGIN_PATH || path === UNLOCK_PATH) {
    return NextResponse.next()
  }

  const site = siteForPath(path)
  if (!site) return NextResponse.next()

  // Case-insensitive doc URLs: 308 any uppercase request to canonical lower.
  const lower = path.toLowerCase()
  if (lower !== path) {
    const url = req.nextUrl.clone()
    url.pathname = lower
    return NextResponse.redirect(url, 308)
  }

  const secret = resolveSecret(process.env as Record<string, string | undefined>)
  if (!secret) {
    // Misconfiguration: fail closed but visibly.
    return new NextResponse(
      "Gate auth secret is not set on this deployment.",
      { status: 500 },
    )
  }

  const cookie = req.cookies.get(site.cookie)?.value
  if (await cookieMatches(cookie, secret, site.id)) {
    return NextResponse.next()
  }

  // Rewrite (not redirect) so the URL bar keeps the original path —
  // /api/gate-unlock reads `from` and bounces back on success.
  const url = req.nextUrl.clone()
  url.pathname = LOGIN_PATH
  url.search = ""
  url.searchParams.set("site", site.id)
  url.searchParams.set("from", path + req.nextUrl.search)
  return NextResponse.rewrite(url)
}

// The Next.js edge matcher must be a statically-analyzable literal (it is
// read at build time, not executed), so it cannot be derived from the
// GATED_SITES registry. Adding a new gated site = add a GATED_SITES entry
// AND add its two literal lines below. Keep this list in sync with the
// registry; the rule_gated_access.md standard documents this two-touch step.
export const config = {
  matcher: [
    "/docs/warme-wimmer",
    "/docs/warme-wimmer/:path*",
    "/docs/meji-media",
    "/docs/meji-media/:path*",
    "/docs/assessment-demo",
    "/docs/assessment-demo/:path*",
    "/gate-login",
    "/api/gate-unlock",
  ],
}
