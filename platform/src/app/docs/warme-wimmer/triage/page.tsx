// Team-facing live-status page for the Wärme Wimmer mail-triage automation (W2-11).
//
// Lives INSIDE the passcode-gated doc-site path: proxy.ts matches
// /docs/warme-wimmer/:path* and rewrites cookie-less requests to /wimmer-login,
// so this dynamic route inherits the exact same gate as the static HTML pages.
// Data: n8n data table via the token-gated W2-12 read webhook (see lib/triage-log.ts);
// team feedback lives in Neon (triage_feedback) and is joined here by logRowId.
//
// Design: matches the static doc site's tokens (see public/docs/warme-wimmer/index.html)
// including the wimmer-docs-theme localStorage key, NOT the marketing site's Tailwind.

import type { Metadata } from "next"
import { desc } from "drizzle-orm"
import { db } from "@/lib/db"
import { triageFeedback } from "@/lib/schema"
import { fetchTriageLog, type TriageLogRow } from "@/lib/triage-log"
import { MailListe, VorschlagBox, ThemeToggle } from "./FeedbackControls"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export const metadata: Metadata = {
  title: { absolute: "Sabine-Triage · Live-Status" },
  robots: "noindex, nofollow",
}

const KATEGORIE_LABEL: Record<string, { label: string; cls: string }> = {
  foerderung: { label: "Förderung", cls: "badge-blue" },
  wartung: { label: "Wartung", cls: "badge-green" },
  termin: { label: "Termin", cls: "badge-amber" },
  direkte_anrede: { label: "Persönlich", cls: "badge-purple" },
  sonstige: { label: "Einordnen", cls: "badge-grey" },
}

// Rows sorted under an older classifier prompt predate the 15.07. rule change
// (Thema vor Name). We flag them honestly instead of deleting them, so the shown
// assignment is not mistaken for how the system would route the mail today.
const CURRENT_PROMPT_VERSION = "v0.9"

const ROUTING_ERKLAERUNG: Array<[string, string, string]> = [
  ["Förderanfragen (KfW, BAFA, Zuschüsse)", "Katja Sonntag", "badge-blue"],
  ["Wartung und Wartungsverträge", "Yvonne Paulus", "badge-green"],
  ["Bestehende Termine bestätigen, verschieben, absagen", "Manuela Aßmann", "badge-amber"],
  ["Mails, die eine Person direkt ansprechen", "die genannte Person (z. B. Valentin Ulbrich)", "badge-purple"],
  ["Alles andere und alles Unklare", "Sabine Wimmer", "badge-grey"],
]

function relativeTime(tsUtc: string): string {
  const then = new Date(tsUtc).getTime()
  if (!Number.isFinite(then)) return ""
  const mins = Math.max(0, Math.round((Date.now() - then) / 60_000))
  if (mins < 1) return "gerade eben"
  if (mins < 60) return `vor ${mins} Min.`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `vor ${hours} Std.`
  const days = Math.round(hours / 24)
  return days === 1 ? "gestern" : `vor ${days} Tagen`
}

function anzeigeName(row: TriageLogRow): string {
  if (row.absender_name) return row.absender_name
  const local = (row.absender_email || "").split("@")[0]
  return local || "unbekannt"
}

export default async function TriagePage() {
  const [log, feedbackRows] = await Promise.all([
    fetchTriageLog(),
    db.select().from(triageFeedback).orderBy(desc(triageFeedback.createdAt)),
  ])

  const rows = (log?.rows ?? []).filter((r) => r.quelle !== "fixture")
  const liveDown = log === null

  // Latest row-bound verdict per log row wins (feedbackRows is newest-first).
  const feedbackByRow = new Map<string, { verdict: string; sollPerson: string | null }>()
  for (const f of feedbackRows) {
    if (f.logRowId && !feedbackByRow.has(f.logRowId) && f.verdict !== "vorschlag") {
      feedbackByRow.set(f.logRowId, { verdict: f.verdict, sollPerson: f.sollPerson })
    }
  }
  const vorschlaege = feedbackRows.filter((f) => f.verdict === "vorschlag").length
  const bestaetigt = [...feedbackByRow.values()].filter((f) => f.verdict === "richtig").length
  const gemeldet = [...feedbackByRow.values()].filter((f) => f.verdict === "falsch").length

  const heuteBerlin = new Intl.DateTimeFormat("de-DE", {
    timeZone: "Europe/Berlin",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date())
  const mailsHeute = rows.filter((r) => (r.ts_berlin || "").startsWith(heuteBerlin)).length

  const proPerson = new Map<string, number>()
  const proKategorie = new Map<string, number>()
  for (const r of rows) {
    proPerson.set(r.soll_user, (proPerson.get(r.soll_user) ?? 0) + 1)
    proKategorie.set(r.kategorie, (proKategorie.get(r.kategorie) ?? 0) + 1)
  }
  const maxPerson = Math.max(1, ...proPerson.values())
  const neueste = rows[0]

  // Serializable rows for the interactive client list (search / filter / paging).
  const mailRows = rows.map((r) => {
    const kat = KATEGORIE_LABEL[r.kategorie] ?? { label: r.kategorie, cls: "badge-grey" }
    return {
      id: String(r.id),
      ts: r.ts_berlin,
      von: anzeigeName(r),
      betreff: r.betreff || "",
      begruendung: r.begruendung || "",
      katLabel: kat.label,
      katCls: kat.cls,
      sollUser: r.soll_user,
      taskId: r.task_id,
      veraltet: !!r.prompt_version && r.prompt_version !== CURRENT_PROMPT_VERSION,
    }
  })
  const feedbackObj = Object.fromEntries(feedbackByRow)

  return (
    <div className="tri-root">
      <style>{PAGE_CSS}</style>
      <div className="tri-shell">
        <header className="tri-header">
          <div>
            <a className="tri-back" href="/docs/warme-wimmer/">
              &larr; Zur Doku-Übersicht
            </a>
            <h1>Sabine-Triage · Live-Status</h1>
            <p className="tri-sub">
              Automatische E-Mail-Sortierung im Testbetrieb (Projekt TES-104547)
            </p>
          </div>
          <div className="tri-header-right">
            <span className="badge badge-live">
              <span className="badge-dot" />
              Aktiv
            </span>
            <ThemeToggle />
          </div>
        </header>

        {neueste ? (
          <p className="tri-lastmail">
            Letzte sortierte Mail: <strong>{relativeTime(neueste.ts_utc)}</strong> ({neueste.ts_berlin} Uhr)
          </p>
        ) : null}

        {liveDown ? (
          <div className="tri-warn">
            Live-Daten sind momentan nicht erreichbar. Die Übersicht unten erklärt trotzdem, wie das System funktioniert. Einfach später nochmal laden.
          </div>
        ) : null}

        <section className="tri-card">
          <h2>Was macht das System?</h2>
          <p>
            Das System liest neue E-Mails im Testpostfach, erkennt das Anliegen und legt automatisch
            eine Hero-Aufgabe bei der zuständigen Person an. Jede Aufgabe enthält eine kurze Begründung,
            warum die Mail so einsortiert wurde. In der Testwoche werden nur Mails der 7 Test-Absender
            mit dem Kürzel TES-104547 sortiert, echte Kundenmails sind noch nicht angeschlossen.
          </p>
          <p>
            Wichtig für die Testphase: Das bisherige System läuft absichtlich parallel weiter. Bei Sabine
            kann deshalb zur selben Mail zusätzlich eine allgemeine Aufgabe &quot;Neue Mail lesen&quot;
            auftauchen. Das ist kein Fehler, sondern die Gegenprobe, und verschwindet nach der Testphase
            von selbst.
          </p>
        </section>

        <section className="tri-card">
          <h2>Wer bekommt was?</h2>
          <table className="tri-table tri-routing">
            <tbody>
              {ROUTING_ERKLAERUNG.map(([was, wer, cls]) => (
                <tr key={was}>
                  <td>{was}</td>
                  <td>
                    <span className={`badge ${cls}`}>{wer}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="tri-card">
          <h2>Zuletzt sortierte Mails</h2>
          <p className="tri-hint">
            Bitte kurz Rückmeldung geben: Passt die Zuordnung? Ein Klick genügt. Bei einer falschen
            Zuordnung gern angeben, wo die Mail hingehört hätte. Mit &quot;vor Update&quot; markierte
            Zeilen wurden vor der Regel-Änderung vom 15.07. sortiert (Thema vor Name) und können in
            Hero abweichen.
          </p>
          <MailListe rows={mailRows} feedback={feedbackObj} />
        </section>

        <section className="tri-card">
          <h2>Zahlen</h2>
          <div className="tri-stats">
            <div className="tri-stat">
              <div className="tri-stat-num">{mailsHeute}</div>
              <div className="tri-stat-label">Mails heute</div>
            </div>
            <div className="tri-stat">
              <div className="tri-stat-num">{rows.length}</div>
              <div className="tri-stat-label">Mails gesamt</div>
            </div>
            <div className="tri-stat">
              <div className="tri-stat-num">
                {bestaetigt + gemeldet > 0 ? `${bestaetigt} / ${gemeldet}` : "0"}
              </div>
              <div className="tri-stat-label">Rückmeldungen (passt / falsch)</div>
            </div>
            <div className="tri-stat">
              <div className="tri-stat-num">{vorschlaege}</div>
              <div className="tri-stat-label">Vorschläge</div>
            </div>
          </div>
          {proPerson.size > 0 ? (
            <div className="tri-bars">
              <h3>Verteilung pro Person</h3>
              {[...proPerson.entries()]
                .sort((a, b) => b[1] - a[1])
                .map(([person, n]) => (
                  <div className="tri-bar-row" key={person}>
                    <span className="tri-bar-label">{person}</span>
                    <span className="tri-bar-track">
                      <span className="tri-bar-fill" style={{ width: `${(n / maxPerson) * 100}%` }} />
                    </span>
                    <span className="tri-bar-num">{n}</span>
                  </div>
                ))}
            </div>
          ) : null}
          {proKategorie.size > 0 ? (
            <p className="tri-katline">
              {[...proKategorie.entries()]
                .sort((a, b) => b[1] - a[1])
                .map(([k, n]) => `${(KATEGORIE_LABEL[k]?.label ?? k)}: ${n}`)
                .join(" · ")}
            </p>
          ) : null}
        </section>

        <section className="tri-card">
          <h2>Wie es weitergeht</h2>
          <ol className="tri-roadmap">
            <li className="done">System gebaut und mit 46 Testfällen geprüft</li>
            <li className="done">Erster Live-Durchlauf bestanden (5 von 5 Testmails korrekt sortiert)</li>
            <li className="done">Termin mit Sabine (14.07.): Sortierung folgt jetzt dem Thema statt dem Namen</li>
            <li className="now">Rückmeldungen aus dem Team sammeln (über Sabine), nächster Termin 21.07.</li>
            <li>Vertretungs- und Urlaubsregelung einbauen</li>
            <li>Einbau in den Hauptablauf, die doppelte Aufgabe &quot;Neue Mail lesen&quot; entfällt dann</li>
            <li>Umstellung auf alle echten Kundenmails</li>
          </ol>
        </section>

        <section className="tri-card">
          <h2>Verbesserung vorschlagen</h2>
          <p className="tri-hint">
            Fällt etwas auf? Eine Mail-Sorte, die das System noch nicht kennt? Einfach kurz notieren,
            jede Rückmeldung hilft beim Feinschliff.
          </p>
          <VorschlagBox />
        </section>

        <footer className="tri-footer">
          Stand: {log?.generated_at ? new Date(log.generated_at).toLocaleString("de-DE", { timeZone: "Europe/Berlin" }) + " Uhr" : "unbekannt"} ·
          Fragen an Nico (nicolas.neumann@waerme-wimmer.de)
        </footer>
      </div>
    </div>
  )
}

const PAGE_CSS = `
.tri-root{
  --bg:#f8fafc;--surface:#ffffff;--surface2:#f1f5f9;--border:#e2e8f0;
  --text:#0f172a;--text2:#475569;--text3:#94a3b8;
  --blue:#2563eb;--blue-light:#dbeafe;--blue-dark:#1e40af;
  --green:#16a34a;--green-light:#dcfce7;
  --amber:#d97706;--amber-light:#fef3c7;
  --purple:#7c3aed;--purple-light:#ede9fe;
  --red:#dc2626;--red-light:#fee2e2;
  --grey:#64748b;--grey-light:#f1f5f9;
  min-height:100vh;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  font-size:15px;line-height:1.6;
}
:root[data-theme="dark"] .tri-root{
  --bg:#0f172a;--surface:#1e293b;--surface2:#0f172a;--border:#334155;
  --text:#f1f5f9;--text2:#94a3b8;--text3:#475569;
  --blue:#3b82f6;--blue-light:#1e3a5f;--blue-dark:#93c5fd;
  --green:#22c55e;--green-light:#14532d;
  --amber:#f59e0b;--amber-light:#451a03;
  --purple:#a78bfa;--purple-light:#2e1065;
  --red:#f87171;--red-light:#450a0a;
  --grey:#94a3b8;--grey-light:#334155;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]) .tri-root{
    --bg:#0f172a;--surface:#1e293b;--surface2:#0f172a;--border:#334155;
    --text:#f1f5f9;--text2:#94a3b8;--text3:#475569;
    --blue:#3b82f6;--blue-light:#1e3a5f;--blue-dark:#93c5fd;
    --green:#22c55e;--green-light:#14532d;
    --amber:#f59e0b;--amber-light:#451a03;
    --purple:#a78bfa;--purple-light:#2e1065;
    --red:#f87171;--red-light:#450a0a;
    --grey:#94a3b8;--grey-light:#334155;
  }
}
.tri-shell{max-width:960px;margin:0 auto;padding:32px 20px 64px}
.tri-header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.tri-header h1{font-size:24px;font-weight:800;letter-spacing:-0.02em;margin-top:4px}
.tri-sub{color:var(--text2);font-size:14px}
.tri-back{font-size:13px;color:var(--blue);text-decoration:none}
.tri-back:hover{text-decoration:underline}
.tri-header-right{display:flex;align-items:center;gap:10px}
.tri-lastmail{margin-top:10px;color:var(--text2);font-size:14px}
.tri-warn{margin-top:16px;background:var(--amber-light);color:var(--amber);border:1px solid var(--amber);border-radius:10px;padding:10px 14px;font-size:14px}
.tri-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px 22px;margin-top:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.tri-card h2{font-size:17px;font-weight:700;margin-bottom:10px}
.tri-card h3{font-size:14px;font-weight:700;margin:16px 0 8px;color:var(--text2)}
.tri-hint{color:var(--text2);font-size:13.5px;margin-bottom:12px}
.tri-empty{color:var(--text2);background:var(--surface2);border-radius:10px;padding:14px;font-size:14px}
.tri-scroll{overflow-x:auto}
.tri-table{width:100%;border-collapse:collapse;font-size:13.5px}
.tri-table th{text-align:left;color:var(--text3);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;padding:8px 10px;border-bottom:1px solid var(--border)}
.tri-table td{padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:top}
.tri-table tr:last-child td{border-bottom:none}
.tri-routing td:first-child{color:var(--text2)}
.tri-nowrap{white-space:nowrap}
.tri-betreff{min-width:220px}
.tri-filterbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:2px 0 14px}
.tri-search{flex:1 1 200px;min-width:160px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:7px 11px;font-size:13.5px;color:var(--text);font-family:inherit}
.tri-chip{background:var(--surface2);border:1px solid var(--border);border-radius:20px;padding:4px 12px;font-size:12.5px;color:var(--text2);cursor:pointer;white-space:nowrap;transition:background .15s,color .15s}
.tri-chip:hover{background:var(--border)}
.tri-chip.active{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.tri-veraltet .tri-nowrap,.tri-veraltet .tri-betreff{opacity:.55}
.badge-veraltet{background:var(--surface2);color:var(--text3);border:1px dashed var(--border);font-weight:600;margin-left:6px}
.tri-count{font-size:12.5px;color:var(--text3);margin-top:10px}
.tri-more{margin-top:10px}
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}
.badge-blue{background:var(--blue-light);color:var(--blue-dark)}
.badge-green{background:var(--green-light);color:var(--green)}
.badge-amber{background:var(--amber-light);color:var(--amber)}
.badge-purple{background:var(--purple-light);color:var(--purple)}
.badge-grey{background:var(--grey-light);color:var(--grey)}
.badge-live{background:var(--green-light);color:var(--green)}
.badge-dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:tri-pulse 2s infinite}
@keyframes tri-pulse{0%,100%{opacity:1}50%{opacity:.5}}
.tri-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.tri-stat{background:var(--surface2);border-radius:10px;padding:14px;border-left:3px solid var(--blue)}
.tri-stat-num{font-size:26px;font-weight:800;letter-spacing:-0.02em}
.tri-stat-label{font-size:12px;color:var(--text2)}
.tri-bars{margin-top:6px}
.tri-bar-row{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.tri-bar-label{width:150px;font-size:13px;color:var(--text2);flex-shrink:0}
.tri-bar-track{flex:1;height:10px;background:var(--surface2);border-radius:6px;overflow:hidden}
.tri-bar-fill{display:block;height:100%;background:var(--blue);border-radius:6px}
.tri-bar-num{width:28px;text-align:right;font-size:13px;font-weight:700}
.tri-katline{margin-top:12px;font-size:13px;color:var(--text2)}
.tri-roadmap{list-style:none;padding:0;margin:0}
.tri-roadmap li{position:relative;padding:6px 0 6px 30px;color:var(--text2);font-size:14px}
.tri-roadmap li::before{content:"";position:absolute;left:6px;top:13px;width:10px;height:10px;border-radius:50%;background:var(--border)}
.tri-roadmap li.done{color:var(--text3)}
.tri-roadmap li.done::before{background:var(--green)}
.tri-roadmap li.now{color:var(--text);font-weight:600}
.tri-roadmap li.now::before{background:var(--blue);animation:tri-pulse 2s infinite}
.tri-footer{margin-top:24px;color:var(--text3);font-size:12.5px;text-align:center}
.tri-btn{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:4px 10px;cursor:pointer;font-size:12.5px;color:var(--text2);transition:background .15s}
.tri-btn:hover{background:var(--border)}
.tri-btn-green{color:var(--green);border-color:var(--green)}
.tri-btn-red{color:var(--red);border-color:var(--red)}
.tri-fb{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.tri-fb-form{margin-top:8px;display:flex;flex-direction:column;gap:6px;min-width:220px}
.tri-fb-form select,.tri-fb-form input,.tri-fb-form textarea{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:6px 8px;font-size:13px;color:var(--text);font-family:inherit}
.tri-fb-chip{font-size:12px;font-weight:600}
.tri-fb-chip.ok{color:var(--green)}
.tri-fb-chip.bad{color:var(--red)}
.tri-fb-aendern{font-size:11.5px;color:var(--text3);background:none;border:none;cursor:pointer;text-decoration:underline;padding:0}
.tri-vorschlag{display:flex;flex-direction:column;gap:8px;max-width:560px}
.tri-vorschlag textarea{min-height:80px;resize:vertical}
.tri-vorschlag input,.tri-vorschlag textarea{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:14px;color:var(--text);font-family:inherit}
.tri-send{align-self:flex-start;background:var(--blue);color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:13.5px;font-weight:600;cursor:pointer}
.tri-send:disabled{opacity:.5;cursor:default}
.tri-ok-note{color:var(--green);font-size:13.5px;font-weight:600}
`
