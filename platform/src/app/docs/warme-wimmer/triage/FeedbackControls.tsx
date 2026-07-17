"use client"

// Client islands for the triage status page: per-row Passt/Falsch buttons,
// the suggestion box, and the theme toggle (same localStorage key as the
// static doc site, 'wimmer-docs-theme', so the theme follows across pages).

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

const SOLL_PERSONEN = [
  "Katja Sonntag",
  "Yvonne Paulus",
  "Manuela Assmann",
  "Valentin Ulbrich",
  "Sabine Wimmer",
]

const NAME_KEY = "ww-triage-name"

function storedName(): string {
  if (typeof window === "undefined") return ""
  return window.localStorage.getItem(NAME_KEY) ?? ""
}

async function postFeedback(payload: Record<string, unknown>): Promise<boolean> {
  try {
    const res = await fetch("/api/wimmer-triage-feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    return res.ok
  } catch {
    return false
  }
}

export function FeedbackControls({
  logRowId,
  taskId,
  existing,
}: {
  logRowId: string
  taskId: number
  existing: { verdict: string; sollPerson: string | null } | null
}) {
  const router = useRouter()
  const [mode, setMode] = useState<"chip" | "buttons" | "falsch-form" | "busy">(
    existing ? "chip" : "buttons",
  )
  const [sollPerson, setSollPerson] = useState("")
  const [note, setNote] = useState("")
  const [name, setName] = useState("")
  const [fehler, setFehler] = useState(false)

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- SSR-safe hydration: localStorage is only readable after mount
    setName(storedName())
  }, [])

  async function send(verdict: "richtig" | "falsch") {
    setMode("busy")
    setFehler(false)
    if (name.trim()) window.localStorage.setItem(NAME_KEY, name.trim())
    const ok = await postFeedback({
      verdict,
      logRowId,
      taskId,
      sollPerson: verdict === "falsch" && sollPerson ? sollPerson : undefined,
      message: verdict === "falsch" && note.trim() ? note.trim() : undefined,
      name: name.trim() || undefined,
    })
    if (ok) {
      router.refresh()
      setMode("chip")
    } else {
      setFehler(true)
      setMode(verdict === "falsch" ? "falsch-form" : "buttons")
    }
  }

  if (mode === "chip" || (existing && mode !== "buttons" && mode !== "falsch-form" && mode !== "busy")) {
    const chip = existing ?? { verdict: "richtig", sollPerson: null }
    return (
      <span className="tri-fb">
        {chip.verdict === "richtig" ? (
          <span className="tri-fb-chip ok">Bestätigt</span>
        ) : (
          <span className="tri-fb-chip bad">
            Falsch gemeldet{chip.sollPerson ? ` (richtig: ${chip.sollPerson})` : ""}
          </span>
        )}
        <button className="tri-fb-aendern" onClick={() => setMode("buttons")}>
          ändern
        </button>
      </span>
    )
  }

  if (mode === "busy") {
    return <span className="tri-fb-chip">Sende…</span>
  }

  if (mode === "falsch-form") {
    return (
      <div className="tri-fb-form">
        <select value={sollPerson} onChange={(e) => setSollPerson(e.target.value)}>
          <option value="">Wäre richtig gewesen bei…</option>
          {SOLL_PERSONEN.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
          <option value="">Weiß nicht</option>
        </select>
        <input
          placeholder="Kurze Anmerkung (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={500}
        />
        <input
          placeholder="Ihr Name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={80}
        />
        <div className="tri-fb">
          <button className="tri-btn tri-btn-red" onClick={() => send("falsch")}>
            Melden
          </button>
          <button className="tri-btn" onClick={() => setMode("buttons")}>
            Abbrechen
          </button>
        </div>
        {fehler ? <span className="tri-fb-chip bad">Senden fehlgeschlagen, bitte nochmal.</span> : null}
      </div>
    )
  }

  return (
    <span className="tri-fb">
      <button className="tri-btn tri-btn-green" onClick={() => send("richtig")}>
        Passt
      </button>
      <button className="tri-btn tri-btn-red" onClick={() => setMode("falsch-form")}>
        Falsch
      </button>
      {fehler ? <span className="tri-fb-chip bad">Fehler, nochmal versuchen.</span> : null}
    </span>
  )
}

type MailRow = {
  id: string
  ts: string
  von: string
  betreff: string
  begruendung: string
  katLabel: string
  katCls: string
  sollUser: string
  taskId: number
  veraltet: boolean
}

const KAT_FILTER = ["Alle", "Förderung", "Wartung", "Termin", "Persönlich", "Einordnen"]
const SEITE = 25

// Interactive mail list: search + category filter + "nur zu prüfen" + paging.
// Keeps the page usable once the log grows past a screenful. All rows arrive from
// the server; filtering/paging is client-side (the read webhook caps at 500).
export function MailListe({
  rows,
  feedback,
}: {
  rows: MailRow[]
  feedback: Record<string, { verdict: string; sollPerson: string | null }>
}) {
  const [q, setQ] = useState("")
  const [kat, setKat] = useState("Alle")
  const [nurOffen, setNurOffen] = useState(false)
  const [limit, setLimit] = useState(SEITE)

  if (rows.length === 0) {
    return (
      <p className="tri-empty">
        Noch keine Mails sortiert. Sobald die erste Testmail eingeht, erscheint sie hier
        (die Seite bei Bedarf neu laden).
      </p>
    )
  }

  const qlc = q.trim().toLowerCase()
  const gefiltert = rows.filter((r) => {
    if (kat !== "Alle" && r.katLabel !== kat) return false
    if (nurOffen && feedback[r.id]) return false
    if (qlc && !`${r.betreff} ${r.von}`.toLowerCase().includes(qlc)) return false
    return true
  })
  const sichtbar = gefiltert.slice(0, limit)
  const reset = () => setLimit(SEITE)

  return (
    <>
      <div className="tri-filterbar">
        <input
          className="tri-search"
          placeholder="Suche (Betreff oder Absender)…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            reset()
          }}
        />
        {KAT_FILTER.map((k) => (
          <button
            key={k}
            className={`tri-chip${kat === k ? " active" : ""}`}
            onClick={() => {
              setKat(k)
              reset()
            }}
          >
            {k}
          </button>
        ))}
        <button
          className={`tri-chip${nurOffen ? " active" : ""}`}
          onClick={() => {
            setNurOffen((v) => !v)
            reset()
          }}
        >
          Nur zu prüfen
        </button>
      </div>

      {sichtbar.length === 0 ? (
        <p className="tri-empty">Keine Mails passen zum Filter.</p>
      ) : (
        <div className="tri-scroll">
          <table className="tri-table">
            <thead>
              <tr>
                <th>Zeit</th>
                <th>Von</th>
                <th>Betreff</th>
                <th>Kategorie</th>
                <th>Zugewiesen an</th>
                <th>Passt das?</th>
              </tr>
            </thead>
            <tbody>
              {sichtbar.map((r) => (
                <tr key={r.id} className={r.veraltet ? "tri-veraltet" : undefined}>
                  <td className="tri-nowrap">{r.ts}</td>
                  <td className="tri-nowrap">{r.von}</td>
                  <td className="tri-betreff" title={r.begruendung}>
                    {r.betreff.slice(0, 70)}
                    {r.betreff.length > 70 ? "…" : ""}
                  </td>
                  <td>
                    <span className={`badge ${r.katCls}`} title={r.begruendung}>
                      {r.katLabel}
                    </span>
                    {r.veraltet ? (
                      <span
                        className="badge badge-veraltet"
                        title="Vor der Regel-Änderung vom 15.07. sortiert (Thema vor Name). Die Zuordnung folgt noch der alten Logik und kann in Hero abweichen."
                      >
                        vor Update
                      </span>
                    ) : null}
                  </td>
                  <td className="tri-nowrap">{r.sollUser}</td>
                  <td>
                    <FeedbackControls
                      logRowId={r.id}
                      taskId={r.taskId}
                      existing={feedback[r.id] ?? null}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="tri-count">
        {gefiltert.length === rows.length
          ? `${rows.length} Mails`
          : `${gefiltert.length} von ${rows.length} Mails`}
        {sichtbar.length < gefiltert.length ? ` · ${sichtbar.length} angezeigt` : ""}
      </p>
      {sichtbar.length < gefiltert.length ? (
        <button className="tri-btn tri-more" onClick={() => setLimit((n) => n + SEITE)}>
          Mehr anzeigen (+{Math.min(SEITE, gefiltert.length - sichtbar.length)})
        </button>
      ) : null}
    </>
  )
}

export function VorschlagBox() {
  const [text, setText] = useState("")
  const [name, setName] = useState("")
  const [status, setStatus] = useState<"idle" | "busy" | "ok" | "fehler">("idle")

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- SSR-safe hydration: localStorage is only readable after mount
    setName(storedName())
  }, [])

  async function send() {
    if (!text.trim()) return
    setStatus("busy")
    if (name.trim()) window.localStorage.setItem(NAME_KEY, name.trim())
    const ok = await postFeedback({
      verdict: "vorschlag",
      message: text.trim(),
      name: name.trim() || undefined,
    })
    if (ok) {
      setStatus("ok")
      setText("")
    } else {
      setStatus("fehler")
    }
  }

  return (
    <div className="tri-vorschlag">
      <textarea
        placeholder="Was sollte das System besser machen? Welche Mail-Sorte fehlt?"
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          if (status === "ok") setStatus("idle")
        }}
        maxLength={2000}
      />
      <input
        placeholder="Ihr Name (optional)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={80}
      />
      <button className="tri-send" onClick={send} disabled={status === "busy" || !text.trim()}>
        {status === "busy" ? "Sende…" : "Abschicken"}
      </button>
      {status === "ok" ? <span className="tri-ok-note">Danke, ist angekommen.</span> : null}
      {status === "fehler" ? (
        <span className="tri-fb-chip bad">Senden fehlgeschlagen, bitte später nochmal.</span>
      ) : null}
    </div>
  )
}

export function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null)

  useEffect(() => {
    const stored = window.localStorage.getItem("wimmer-docs-theme")
    const initial =
      stored === "dark" ||
      (stored !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches)
    // eslint-disable-next-line react-hooks/set-state-in-effect -- SSR-safe hydration: theme is only known after mount
    setDark(initial)
    document.documentElement.dataset.theme = initial ? "dark" : "light"
  }, [])

  if (dark === null) return null

  return (
    <button
      className="tri-btn"
      onClick={() => {
        const next = !dark
        setDark(next)
        document.documentElement.dataset.theme = next ? "dark" : "light"
        window.localStorage.setItem("wimmer-docs-theme", next ? "dark" : "light")
      }}
    >
      {dark ? "Hell" : "Dunkel"}
    </button>
  )
}
