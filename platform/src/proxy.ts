import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export const proxy = auth((req) => {
  const { auth: session, nextUrl } = req
  const path = nextUrl.pathname
  const isApiRoute = path.startsWith("/api/")

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
  ],
}
