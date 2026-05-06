import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

/**
 * Case-insensitive routing for the Wärme Wimmer docs path.
 *
 * Vercel + Linux serve static files with a case-sensitive file system, but
 * the M-/S-/R- prefix convention from the source markdown is uppercase, and
 * users naturally type URLs with the original casing. This middleware
 * 308-redirects any uppercase characters under /docs/warme-wimmer/* to the
 * lowercase canonical path so both work.
 */
export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl
  if (pathname.startsWith("/docs/warme-wimmer/")) {
    const lower = pathname.toLowerCase()
    if (lower !== pathname) {
      const url = request.nextUrl.clone()
      url.pathname = lower
      return NextResponse.redirect(url, 308)
    }
  }
  return NextResponse.next()
}

export const config = {
  matcher: "/docs/warme-wimmer/:path*",
}
