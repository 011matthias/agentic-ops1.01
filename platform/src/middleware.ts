import { NextRequest, NextResponse } from "next/server"
import { cookieMatches, WIMMER_COOKIE, WIMMER_PATH_PREFIX } from "./lib/wimmer-auth"

// Server-side gate for the Wärme Wimmer doc site. Replaces the previous
// in-page JS overlay (which shipped the passcode in plaintext) with an
// HMAC-cookie check enforced before the static HTML is served.
//
// Note: NextAuth-based access checks for /admin and /portal still live in
// `proxy.ts` (dead code, never wired). Promoting those is a separate PR.

export async function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname

  // Case-insensitive URLs for the doc site (revives the dormant proxy.ts feature).
  // M-meetings.md → m-meetings.html canonical; uppercase paths get 308'd.
  if (path.startsWith(WIMMER_PATH_PREFIX)) {
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

  // Gate /docs/warme-wimmer/* requests on the wimmer-auth cookie.
  if (path.startsWith(WIMMER_PATH_PREFIX)) {
    const secret = process.env.WIMMER_AUTH_SECRET
    if (!secret) {
      // Misconfiguration: fail closed but visibly. Surface a 500 to ourselves
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
  matcher: ["/docs/warme-wimmer/:path*", "/wimmer-login", "/api/wimmer-unlock"],
}
