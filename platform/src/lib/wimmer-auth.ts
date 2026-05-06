// Edge-runtime safe (no node:crypto). Used by middleware AND by the unlock API route.

export const WIMMER_COOKIE = "wimmer-auth"
export const WIMMER_PATH_PREFIX = "/docs/warme-wimmer/"
export const COOKIE_MAX_AGE_S = 60 * 60 * 24 * 30 // 30 days

const ENCODER = new TextEncoder()

export async function expectedCookie(secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    ENCODER.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  )
  const sig = await crypto.subtle.sign("HMAC", key, ENCODER.encode("granted-v1"))
  return bufToHex(sig)
}

export async function cookieMatches(value: string | undefined, secret: string): Promise<boolean> {
  if (!value) return false
  const expected = await expectedCookie(secret)
  if (value.length !== expected.length) return false
  // Constant-time compare — XOR each byte, accumulate, return false on any mismatch.
  let diff = 0
  for (let i = 0; i < value.length; i++) {
    diff |= value.charCodeAt(i) ^ expected.charCodeAt(i)
  }
  return diff === 0
}

export function safeFromUrl(raw: string | null | undefined): string {
  if (!raw) return WIMMER_PATH_PREFIX
  if (!raw.startsWith(WIMMER_PATH_PREFIX)) return WIMMER_PATH_PREFIX
  if (raw.includes("\n") || raw.includes("\r")) return WIMMER_PATH_PREFIX
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
