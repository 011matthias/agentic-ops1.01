import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { db } from "@/lib/db"
import { triageFeedback } from "@/lib/schema"
import { cookieMatches, WIMMER_COOKIE } from "@/lib/wimmer-auth"

// Node runtime (Drizzle + Neon needs Node, not Edge).
export const runtime = "nodejs"

const MAX_MESSAGE_LENGTH = 2000
const MAX_NAME_LENGTH = 100
const VERDICTS = ["richtig", "falsch", "vorschlag"] as const
// Display names of the routing targets — the only values accepted for sollPerson.
const SOLL_PERSONEN = [
  "Katja Sonntag",
  "Yvonne Paulus",
  "Manuela Assmann",
  "Valentin Ulbrich",
  "Sabine Wimmer",
]

/** Same gate as the doc site itself: the wimmer passcode cookie. Deliberately
 * NO Auth.js session requirement — the WW team has passcode access only. */
async function passcodeOk(): Promise<boolean> {
  const secret = process.env.WIMMER_AUTH_SECRET?.trim()
  if (!secret) return false
  const cookie = (await cookies()).get(WIMMER_COOKIE)?.value
  return cookieMatches(cookie, secret)
}

export async function POST(req: Request) {
  if (!(await passcodeOk())) {
    return NextResponse.json({ error: "passcode_required" }, { status: 401 })
  }
  let body: Record<string, unknown>
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 })
  }
  const verdict = String(body.verdict || "")
  if (!VERDICTS.includes(verdict as (typeof VERDICTS)[number])) {
    return NextResponse.json({ error: "invalid_verdict" }, { status: 400 })
  }
  const logRowId = body.logRowId != null ? String(body.logRowId).slice(0, 50) : null
  const taskIdRaw = Number(body.taskId)
  const taskId = Number.isFinite(taskIdRaw) && taskIdRaw > 0 ? Math.floor(taskIdRaw) : null
  const sollPersonRaw = body.sollPerson ? String(body.sollPerson) : null
  const sollPerson = sollPersonRaw && SOLL_PERSONEN.includes(sollPersonRaw) ? sollPersonRaw : null
  const authorName = String(body.name || "").trim().slice(0, MAX_NAME_LENGTH) || null
  const message = String(body.message || "").trim().slice(0, MAX_MESSAGE_LENGTH) || null

  // Row-bound feedback needs a row; suggestions need text.
  if (verdict === "vorschlag" && !message) {
    return NextResponse.json({ error: "message_required" }, { status: 400 })
  }
  if (verdict !== "vorschlag" && !logRowId) {
    return NextResponse.json({ error: "logRowId_required" }, { status: 400 })
  }

  const [inserted] = await db
    .insert(triageFeedback)
    .values({ logRowId, taskId, verdict: verdict as (typeof VERDICTS)[number], sollPerson, authorName, message })
    .returning()

  return NextResponse.json({ ok: true, id: inserted.id })
}
