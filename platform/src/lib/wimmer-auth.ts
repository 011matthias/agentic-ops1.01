// Edge-runtime safe (no node:crypto). Used by middleware AND by the unlock API route.
//
// Generalized 2026-06-11 to gate multiple client doc sites (wimmer + meji) with
// per-site cookies and per-site access codes. The HMAC secret is shared
// (WIMMER_AUTH_SECRET); the signed message is site-scoped so a cookie for one
// site never unlocks another.

export const COOKIE_MAX_AGE_S = 60 * 60 * 24 * 30 // 30 days

export type DocSiteKey = "wimmer" | "meji"

export type DocSite = {
  pathRoot: string // bare path (Vercel cleanUrls strips trailing slash)
  pathPrefix: string
  cookie: string
  codeEnv: string
  title: string
}

export const DOC_SITES: Record<DocSiteKey, DocSite> = {
  wimmer: {
    pathRoot: "/docs/warme-wimmer",
    pathPrefix: "/docs/warme-wimmer/",
    cookie: "wimmer-auth",
    codeEnv: "WIMMER_ACCESS_CODE",
    title: "Wärme Wimmer Documentation",
  },
  meji: {
    pathRoot: "/docs/meji-media",
    pathPrefix: "/docs/meji-media/",
    cookie: "meji-auth",
    codeEnv: "MEJI_ACCESS_CODE",
    title: "Meji Media Documentation",
  },
}

// Back-compat exports (pre-generalization callers).
export const WIMMER_COOKIE = DOC_SITES.wimmer.cookie
export const WIMMER_PATH_PREFIX = DOC_SITES.wimmer.pathPrefix

export function siteKeyForPath(path: string): DocSiteKey | null {
  for (const key of Object.keys(DOC_SITES) as DocSiteKey[]) {
    const site = DOC_SITES[key]
    if (path === site.pathRoot || path.startsWith(site.pathPrefix)) return key
  }
  return null
}

export function parseSiteKey(raw: string | null | undefined): DocSiteKey {
  return raw === "meji" ? "meji" : "wimmer"
}

const ENCODER = new TextEncoder()

export async function expectedCookie(
  secret: string,
  siteKey: DocSiteKey = "wimmer",
): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    ENCODER.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  )
  // Site-scoped message: a wimmer cookie must never validate for meji.
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    ENCODER.encode(`granted-v1:${siteKey}`),
  )
  return bufToHex(sig)
}

export async function cookieMatches(
  value: string | undefined,
  secret: string,
  siteKey: DocSiteKey = "wimmer",
): Promise<boolean> {
  if (!value) return false
  const expected = await expectedCookie(secret, siteKey)
  if (value.length !== expected.length) return false
  // Constant-time compare — XOR each byte, accumulate, return false on any mismatch.
  let diff = 0
  for (let i = 0; i < value.length; i++) {
    diff |= value.charCodeAt(i) ^ expected.charCodeAt(i)
  }
  return diff === 0
}

export function safeFromUrl(
  raw: string | null | undefined,
  siteKey: DocSiteKey = "wimmer",
): string {
  const prefix = DOC_SITES[siteKey].pathPrefix
  if (!raw) return prefix
  if (!raw.startsWith(prefix)) return prefix
  if (raw.includes("\n") || raw.includes("\r")) return prefix
  return raw
}

function bufToHex(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let hex = ""
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, "0")
  }
  return hex
}
