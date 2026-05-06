import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export const proxy = auth((req) => {
  const { auth: session, nextUrl } = req
  const path = nextUrl.pathname
  const isApiRoute = path.startsWith("/api/")

  // Wärme Wimmer doc site: case-insensitive URLs.
  // Lowercase the path so URLs typed with the M-/S-/R- prefix uppercase
  // (matching our internal naming) resolve to the lowercase canonical files.
  if (path.startsWith("/docs/warme-wimmer/")) {
    const lower = path.toLowerCase()
    if (lower !== path) {
      const url = nextUrl.clone()
      url.pathname = lower
      return NextResponse.redirect(url, 308)
    }
  }

  // Admin routes: require admin role
  if (path.startsWith("/admin") || path.startsWith("/api/admin")) {
    if (!session?.user) {
      if (isApiRoute) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
      return NextResponse.redirect(new URL("/login", nextUrl))
    }
    if (session.user.role !== "admin") {
      if (isApiRoute) return NextResponse.json({ error: "Forbidden" }, { status: 403 })
      return NextResponse.redirect(new URL("/portal", nextUrl))
    }
  }

  // Portal routes: require authenticated user (client or admin)
  if (path.startsWith("/portal") || path.startsWith("/api/portal")) {
    if (!session?.user) {
      if (isApiRoute) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
      return NextResponse.redirect(new URL("/login", nextUrl))
    }
  }

  return NextResponse.next()
})

export const config = {
  matcher: [
    "/admin/:path*",
    "/portal/:path*",
    "/api/admin/:path*",
    "/api/portal/:path*",
    "/docs/warme-wimmer/:path*",
  ],
}
