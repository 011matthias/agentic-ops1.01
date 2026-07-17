import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { db } from "@/lib/db"
import { docComments } from "@/lib/schema"
import { and, eq, asc } from "drizzle-orm"
import { cookieMatches, WIMMER_COOKIE } from "@/lib/wimmer-auth"
import { auth } from "@/lib/auth"

// Node runtime (Drizzle + Neon needs Node, not Edge).
export const runtime = "nodejs"

const DEFAULT_HOST = "warme-wimmer"
const MAX_BODY_LENGTH = 5000
const MAX_PAGE_SLUG_LENGTH = 200
const MAX_ANCHOR_TEXT_LENGTH = 1000  // each of exact/prefix/suffix capped; total ~3KB max

/** Validate + normalize an inline-highlight anchor. Returns the cleaned anchor
 *  or null (meaning "page-level comment, no anchor"). Throws nothing — invalid
 *  shapes coerce to null so callers don't have to handle errors. */
function normalizeAnchor(raw: unknown): {
  exact: string
  prefix?: string
  suffix?: string
} | null {
  if (!raw || typeof raw !== "object") return null
  const obj = raw as Record<string, unknown>
  const exact = typeof obj.exact === "string" ? obj.exact.trim() : ""
  if (!exact) return null
  if (exact.length > MAX_ANCHOR_TEXT_LENGTH) return null
  const prefix = typeof obj.prefix === "string" ? obj.prefix.slice(0, MAX_ANCHOR_TEXT_LENGTH) : undefined
  const suffix = typeof obj.suffix === "string" ? obj.suffix.slice(0, MAX_ANCHOR_TEXT_LENGTH) : undefined
  return { exact, ...(prefix ? { prefix } : {}), ...(suffix ? { suffix } : {}) }
}

/** Read+verify the wimmer-auth passcode cookie. Required for both reads and writes,
 * so the comment thread inherits the doc-site access gate. */
async function passcodeOk(): Promise<boolean> {
  const secret = process.env.WIMMER_AUTH_SECRET?.trim()
  if (!secret) return false
  const cookie = (await cookies()).get(WIMMER_COOKIE)?.value
  return cookieMatches(cookie, secret)
}

/** Allowlist for write authors. Default: any email under @waerme-wimmer.de
 * or @unpauseai.com. Override with comma-separated WIMMER_COMMENT_ALLOWLIST
 * (entries can be plain emails or @domain.tld patterns). */
function isAllowedEmail(email: string | null | undefined): boolean {
  if (!email) return false
  const raw = process.env.WIMMER_COMMENT_ALLOWLIST?.trim()
  const list = raw
    ? raw.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean)
    : ["@waerme-wimmer.de", "@unpauseai.com"]
  const e = email.toLowerCase()
  return list.some((entry) =>
    entry.startsWith("@") ? e.endsWith(entry) : e === entry
  )
}

export async function GET(req: Request) {
  if (!(await passcodeOk())) {
    return NextResponse.json({ error: "passcode_required" }, { status: 401 })
  }
  const url = new URL(req.url)
  const pageSlug = (url.searchParams.get("pageSlug") || "").slice(0, MAX_PAGE_SLUG_LENGTH)
  const docHost = (url.searchParams.get("docHost") || DEFAULT_HOST).slice(0, 50)
  if (!pageSlug) {
    return NextResponse.json({ error: "pageSlug_required" }, { status: 400 })
  }
  const rows = await db
    .select({
      id: docComments.id,
      parentId: docComments.parentId,
      authorId: docComments.authorId,
      authorEmail: docComments.authorEmail,
      authorName: docComments.authorName,
      bodyMd: docComments.bodyMd,
      selectionAnchor: docComments.selectionAnchor,
      deleted: docComments.deleted,
      editedAt: docComments.editedAt,
      createdAt: docComments.createdAt,
    })
    .from(docComments)
    .where(and(eq(docComments.docHost, docHost), eq(docComments.pageSlug, pageSlug)))
    .orderBy(asc(docComments.createdAt))

  // Soft-deleted comments: keep id + parentId + timestamps so threads still render
  // with placeholder text, but redact body + author email.
  const safe = rows.map((r) => {
    if (r.deleted) {
      return { ...r, authorEmail: "", authorName: "[entfernt]", bodyMd: "[entfernt]" }
    }
    // Hide full email; expose only the local part for display ("nico@..." → "nico").
    const local = r.authorEmail.split("@")[0] || ""
    return { ...r, authorEmail: local }
  })

  // Get current session for client-side "can I edit this?" check
  const session = await auth()
  const me = session?.user?.email ? {
    email: session.user.email,
    name: session.user.name,
    canPost: isAllowedEmail(session.user.email),
  } : null

  return NextResponse.json({ comments: safe, me })
}

export async function POST(req: Request) {
  if (!(await passcodeOk())) {
    return NextResponse.json({ error: "passcode_required" }, { status: 401 })
  }
  const session = await auth()
  const email = session?.user?.email
  if (!email) {
    return NextResponse.json({ error: "signin_required" }, { status: 401 })
  }
  if (!isAllowedEmail(email)) {
    return NextResponse.json({ error: "not_allowed" }, { status: 403 })
  }
  let body: Record<string, unknown>
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 })
  }
  const pageSlug = String(body.pageSlug || "").trim().slice(0, MAX_PAGE_SLUG_LENGTH)
  const docHost = String(body.docHost || DEFAULT_HOST).trim().slice(0, 50)
  const parentId = body.parentId ? String(body.parentId) : null
  const bodyMd = String(body.bodyMd || "").trim().slice(0, MAX_BODY_LENGTH)
  if (!pageSlug) {
    return NextResponse.json({ error: "pageSlug_required" }, { status: 400 })
  }
  if (!bodyMd) {
    return NextResponse.json({ error: "body_required" }, { status: 400 })
  }
  const anchor = normalizeAnchor((body as Record<string, unknown>).selection_anchor ?? (body as Record<string, unknown>).selectionAnchor)
  const [inserted] = await db
    .insert(docComments)
    .values({
      docHost,
      pageSlug,
      parentId,
      authorId: session.user?.id ?? null,
      authorEmail: email,
      authorName: session.user?.name ?? null,
      bodyMd,
      selectionAnchor: anchor,
    })
    .returning()
  // Strip email domain in response (matches GET shape)
  return NextResponse.json({
    comment: {
      ...inserted,
      authorEmail: (inserted.authorEmail || "").split("@")[0],
    },
  })
}
