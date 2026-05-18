// Edge-runtime safe (no node:crypto). Shared by the proxy (gate enforcement),
// the /api/gate-unlock route, and the /gate-login page.
//
// Server-side gate model for every client doc site. The access code and the
// master password live in env vars and are never shipped to the browser.
// This is the ONLY sanctioned gating model (see rule_gated_access.md).
//
// Adding a new gated client site is two touches:
//   1. Add an entry to GATED_SITES below.
//   2. Add its `pathRoot` and `pathPrefix` to the matcher in proxy.ts.
// The per-site access code (its `accessCodeEnv`) and the shared master
// password are then enforced automatically — no per-site auth code.

export interface GatedSite {
  /** Stable id, used in the cookie payload and the login `?site=` param. */
  id: string
  /** Bare path with no trailing slash (Vercel cleanUrls strips it). */
  pathRoot: string
  /** Path prefix with trailing slash. */
  pathPrefix: string
  /** Cookie name holding the HMAC grant for this site. */
  cookie: string
  /** Env var holding this site's own access code. */
  accessCodeEnv: string
  /** Human label shown on the login screen. */
  label: string
}

export const GATED_SITES: GatedSite[] = [
  {
    id: "wimmer",
    pathRoot: "/docs/warme-wimmer",
    pathPrefix: "/docs/warme-wimmer/",
    cookie: "wimmer-auth",
    accessCodeEnv: "WIMMER_ACCESS_CODE",
    label: "Wärme Wimmer Documentation",
  },
  {
    id: "meji",
    pathRoot: "/docs/meji-media",
    pathPrefix: "/docs/meji-media/",
    cookie: "meji-auth",
    accessCodeEnv: "MEJI_ACCESS_CODE",
    label: "Meji Media Documentation",
  },
]

/** Env var holding the master password that unlocks every gated site. */
export const MASTER_ACCESS_CODE_ENV = "MASTER_ACCESS_CODE"
/** Shared HMAC secret for grant cookies. Falls back to the legacy Wimmer
 *  secret so a deploy that predates GATE_AUTH_SECRET still works. */
export const GATE_SECRET_ENVS = ["GATE_AUTH_SECRET", "WIMMER_AUTH_SECRET"]

export const COOKIE_MAX_AGE_S = 60 * 60 * 24 * 30 // 30 days

const ENCODER = new TextEncoder()

export function siteForPath(path: string): GatedSite | undefined {
  return GATED_SITES.find(
    (s) => path === s.pathRoot || path.startsWith(s.pathPrefix),
  )
}

export function siteById(id: string | null | undefined): GatedSite | undefined {
  if (!id) return undefined
  return GATED_SITES.find((s) => s.id === id)
}

export function resolveSecret(
  env: Record<string, string | undefined>,
): string | undefined {
  for (const name of GATE_SECRET_ENVS) {
    const v = env[name]?.trim()
    if (v) return v
  }
  return undefined
}

/** Grant token is bound to the site id so a cookie minted for one site
 *  cannot unlock another. */
export async function expectedCookie(
  secret: string,
  siteId: string,
): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    ENCODER.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  )
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    ENCODER.encode(`granted-v1:${siteId}`),
  )
  return bufToHex(sig)
}

export async function cookieMatches(
  value: string | undefined,
  secret: string,
  siteId: string,
): Promise<boolean> {
  if (!value) return false
  const expected = await expectedCookie(secret, siteId)
  if (value.length !== expected.length) return false
  let diff = 0
  for (let i = 0; i < value.length; i++) {
    diff |= value.charCodeAt(i) ^ expected.charCodeAt(i)
  }
  return diff === 0
}

/** Only allow bouncing back to a path inside the same gated site. */
export function safeFromUrl(
  raw: string | null | undefined,
  site: GatedSite,
): string {
  if (!raw) return site.pathPrefix
  if (!raw.startsWith(site.pathPrefix) && raw !== site.pathRoot) {
    return site.pathPrefix
  }
  if (raw.includes("\n") || raw.includes("\r")) return site.pathPrefix
  return raw
}

export function timingSafeStringEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  return diff === 0
}

/** True if `submitted` equals the site's own code or the master password.
 *  Both compared in constant-ish time; never short-circuits on the code. */
export function codeAccepted(
  submitted: string,
  siteCode: string | undefined,
  masterCode: string | undefined,
): boolean {
  let ok = false
  if (siteCode && submitted.length === siteCode.length) {
    ok = timingSafeStringEqual(submitted, siteCode) || ok
  }
  if (masterCode && submitted.length === masterCode.length) {
    ok = timingSafeStringEqual(submitted, masterCode) || ok
  }
  return ok
}

function bufToHex(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let hex = ""
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, "0")
  }
  return hex
}
