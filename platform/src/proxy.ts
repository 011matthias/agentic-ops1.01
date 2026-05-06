// Next.js 16 renamed `middleware.ts` to `proxy.ts`. This file is what runs
// on every request matching the `config.matcher` below.
//
// Server-side gate for the Wärme Wimmer doc site. Replaces the previous
// in-page JS overlay (which shipped the passcode in plaintext) with an
// HMAC-cookie check enforced before the static HTML is served.
//
// NOTE: previously this file used NextAuth's `auth()` wrapper to gate
// /admin and /portal as well. That logic was never wired to a live
// `middleware.ts`, so it was dead code. Promoting NextAuth-based gating
// for /admin and /portal is a separate concern and is intentionally
// out of scope here — see `platform/src/lib/auth.ts` for the auth client
// when that work is picked up.

import { NextRequest, NextResponse } from "next/server"
import { cookieMatches, WIMMER_COOKIE, WIMMER_PATH_PREFIX } from "./lib/wimmer-auth"

const WIMMER_PATH_ROOT = "/docs/warme-wimmer" // Vercel cleanUrls strips trailing slash

function isDocSitePath(path: string): boolean {
  return path === WIMMER_PATH_ROOT || path.startsWith(WIMMER_PATH_PREFIX)
}

export async function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname

  // Case-insensitive URLs for the doc site. M-meetings.html / S-04-... are the
  // canonical filenames in the source repo (uppercase), but we serve them
  // lowercase. This 308's any uppercase request to the canonical lowercase URL.
  if (isDocSitePath(path)) {
    const lower = path.toLowerCase()
    if (lower !== path) {
      const url = req.nextUrl.clone()
      url.pathname = lower
      return NextResponse.redirect(url, 308)
    }
  }

  // Allow the login page and the unlock API through unconditionally.
  if (path === "/wimmer-login" || path === "/api/wimmer-unlock") {
    return NextResponse.next()
  }

  // Gate /docs/warme-wimmer (no trailing slash) AND /docs/warme-wimmer/* on cookie.
  if (isDocSitePath(path)) {
    const secret = process.env.WIMMER_AUTH_SECRET?.trim()
    if (!secret) {
      // Misconfiguration: fail closed but visibly. Surface 500 to ourselves
      // rather than letting unauthenticated traffic through silently.
      return new NextResponse(
        "WIMMER_AUTH_SECRET is not set on this deployment.",
        { status: 500 },
      )
    }
    const cookie = req.cookies.get(WIMMER_COOKIE)?.value
    if (await cookieMatches(cookie, secret)) {
      return NextResponse.next()
    }
    // Rewrite (not redirect) so the URL bar keeps the original path —
    // /api/wimmer-unlock can read the `from` field and bounce back on success.
    const url = req.nextUrl.clone()
    url.pathname = "/wimmer-login"
    url.searchParams.set("from", path + req.nextUrl.search)
    return NextResponse.rewrite(url)
  }

  return NextResponse.next()
}

export const config = {
  // Both the bare path (Vercel cleanUrls strips trailing slash on the root)
  // and any sub-path must run through the gate.
  matcher: [
    "/docs/warme-wimmer",
    "/docs/warme-wimmer/:path*",
    "/wimmer-login",
    "/api/wimmer-unlock",
  ],
}
