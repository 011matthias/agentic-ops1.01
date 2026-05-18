import { NextResponse } from "next/server"
import {
  codeAccepted,
  expectedCookie,
  resolveSecret,
  safeFromUrl,
  siteById,
  COOKIE_MAX_AGE_S,
  MASTER_ACCESS_CODE_ENV,
} from "@/lib/gated-sites"

// Edge runtime: co-locate with the proxy, use Web Crypto in expectedCookie.
export const runtime = "edge"

export async function POST(req: Request) {
  const form = await req.formData()
  const submitted = String(form.get("code") ?? "")
  const site = siteById(String(form.get("site") ?? ""))
  const origin = new URL(req.url).origin

  if (!site) {
    // Unknown site param: send back to a generic login with an error.
    const url = new URL("/gate-login", origin)
    url.searchParams.set("err", "1")
    return NextResponse.redirect(url, 303)
  }

  const from = safeFromUrl(String(form.get("from") ?? ""), site)

  const env = process.env as Record<string, string | undefined>
  // Trim env vars: `echo "x" | vercel env add` stores a trailing newline.
  const siteCode = env[site.accessCodeEnv]?.trim()
  const masterCode = env[MASTER_ACCESS_CODE_ENV]?.trim()
  const secret = resolveSecret(env)

  if ((!siteCode && !masterCode) || !secret) {
    return new NextResponse(
      `Gate not configured: ${site.accessCodeEnv} / ${MASTER_ACCESS_CODE_ENV} / gate secret.`,
      { status: 500 },
    )
  }

  if (!codeAccepted(submitted, siteCode, masterCode)) {
    const url = new URL("/gate-login", origin)
    url.searchParams.set("site", site.id)
    url.searchParams.set("from", from)
    url.searchParams.set("err", "1")
    return NextResponse.redirect(url, 303)
  }

  const cookieValue = await expectedCookie(secret, site.id)
  const res = NextResponse.redirect(new URL(from, origin), 303)
  res.cookies.set({
    name: site.cookie,
    value: cookieValue,
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE_S,
  })
  return res
}
