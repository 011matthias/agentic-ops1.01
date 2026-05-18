import { NextResponse } from "next/server"
import {
  expectedCookie,
  safeFromUrl,
  WIMMER_COOKIE,
  COOKIE_MAX_AGE_S,
} from "@/lib/wimmer-auth"

// Edge runtime so this co-locates with middleware (single deployment region,
// no cold start, and we use Web Crypto in expectedCookie).
export const runtime = "edge"

export async function POST(req: Request) {
  const form = await req.formData()
  const submitted = String(form.get("code") ?? "")
  const from = safeFromUrl(String(form.get("from") ?? ""))

  // Defensive: trim env vars in case the deploy step accidentally stored a
  // trailing newline (`echo "x" | vercel env add` does this — burned us once).
  const accessCode = process.env.WIMMER_ACCESS_CODE?.trim()
  const secret = process.env.WIMMER_AUTH_SECRET?.trim()
  if (!accessCode || !secret) {
    return new NextResponse(
      "WIMMER_ACCESS_CODE / WIMMER_AUTH_SECRET not configured.",
      { status: 500 },
    )
  }

  // Master password works across every gated access surface on the site,
  // alongside the per-site code in WIMMER_ACCESS_CODE. Server-side only
  // (this route runs on the edge runtime; the value is never shipped to the
  // browser, so the proxy.ts "no plaintext passcode to the client" posture
  // is preserved).
  const MASTER_ACCESS_CODE = "Natthias07"

  // Constant-time-ish compare. submitted may be longer/shorter than either code.
  const ok =
    (submitted.length === accessCode.length &&
      timingSafeStringEqual(submitted, accessCode)) ||
    (submitted.length === MASTER_ACCESS_CODE.length &&
      timingSafeStringEqual(submitted, MASTER_ACCESS_CODE))

  const origin = new URL(req.url).origin
  if (!ok) {
    const url = new URL("/wimmer-login", origin)
    url.searchParams.set("from", from)
    url.searchParams.set("err", "1")
    return NextResponse.redirect(url, 303)
  }

  const cookieValue = await expectedCookie(secret)
  const res = NextResponse.redirect(new URL(from, origin), 303)
  res.cookies.set({
    name: WIMMER_COOKIE,
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
