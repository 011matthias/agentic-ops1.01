import { NextResponse } from "next/server"
import {
  COOKIE_MAX_AGE_S,
  DOC_SITES,
  expectedCookie,
  parseSiteKey,
  safeFromUrl,
} from "@/lib/wimmer-auth"

// Edge runtime so this co-locates with middleware (single deployment region,
// no cold start, and we use Web Crypto in expectedCookie).
export const runtime = "edge"

export async function POST(req: Request) {
  const form = await req.formData()
  const submitted = String(form.get("code") ?? "")
  const siteKey = parseSiteKey(String(form.get("site") ?? ""))
  const site = DOC_SITES[siteKey]
  const from = safeFromUrl(String(form.get("from") ?? ""), siteKey)

  // Defensive: trim env vars in case the deploy step accidentally stored a
  // trailing newline (`echo "x" | vercel env add` does this — burned us once).
  const accessCode = process.env[site.codeEnv]?.trim()
  const secret = process.env.WIMMER_AUTH_SECRET?.trim()
  if (!accessCode || !secret) {
    return new NextResponse(
      `${site.codeEnv} / WIMMER_AUTH_SECRET not configured.`,
      { status: 500 },
    )
  }

  // Constant-time-ish compare. submitted may be longer/shorter than accessCode.
  const ok =
    submitted.length === accessCode.length &&
    timingSafeStringEqual(submitted, accessCode)

  const origin = new URL(req.url).origin
  if (!ok) {
    const url = new URL("/wimmer-login", origin)
    url.searchParams.set("site", siteKey)
    url.searchParams.set("from", from)
    url.searchParams.set("err", "1")
    return NextResponse.redirect(url, 303)
  }

  const cookieValue = await expectedCookie(secret, siteKey)
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

function timingSafeStringEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  return diff === 0
}
