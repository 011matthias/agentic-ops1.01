// Server-side fetcher for the Wärme Wimmer triage log.
//
// Source of truth is an n8n DATA TABLE on the client's German-hosted instance
// (n8n.osneo.de) — customer mail metadata (sender, subject) deliberately never
// touches Neon. Read path is the token-gated read-only workflow W2-12
// ("Triage-Log lesen", GET webhook + x-log-token header), NOT the n8n admin
// API — Vercel only ever holds the narrow read token, not an instance key.
//
// Fails soft: any error returns null so the page can render its static
// explainer sections with a "Live-Daten momentan nicht erreichbar" note.

export type TriageLogRow = {
  id: number // n8n data-table row id
  execution_id: string
  ts_utc: string
  ts_berlin: string
  absender_email: string
  absender_name: string
  betreff: string
  kategorie: string
  begruendung: string
  soll_user: string
  soll_user_id: number
  task_id: number
  task_title: string
  ok: boolean
  test_mode: boolean
  quelle: "live" | "fixture" | "backfill" | string
  effektiv_user_id: number
  vertretung_fuer: string
  alternativ: string
  prompt_version: string
}

export type TriageLog = {
  count: number
  rows: TriageLogRow[]
  generated_at: string
}

export async function fetchTriageLog(): Promise<TriageLog | null> {
  const url = process.env.WW_TRIAGE_LOG_URL?.trim()
  const token = process.env.WW_TRIAGE_LOG_TOKEN?.trim()
  if (!url || !token) return null
  try {
    const res = await fetch(url, {
      headers: { "x-log-token": token },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    })
    if (!res.ok) return null
    const data = (await res.json()) as TriageLog
    if (!Array.isArray(data.rows)) return null
    return data
  } catch {
    return null
  }
}
