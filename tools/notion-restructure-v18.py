# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""v18 restructure with audit fixes:

1. Consolidate 10 separate meeting pages into ONE page (M-meetings.md).
   Each meeting = H2 section with summary up top + collapsible <details> for raw notes.
2. Fix whitespace bloat: no blank lines inside markdown tables (Notion parser was
   silently dropping table rendering; confirmed via user screenshot of M-00).
3. Fix R-00 intra-zip links: old `01-aufgabe-erledigt.md` -> new `S-01-aufgabe-erledigt.md`.
4. Remove R-00 link to excluded `13-pre-meeting-fragen.md`.
5. Fix R-w2-04-* navigation pointers (Seite 04 / 04b -> R-w2-04-*).
6. Compress 4-line banner on detail pages to a 1-line status note.
7. Strip duplicate `## Flow-Diagramm` block from S-01..S-10 (Sabine + Audit blocks
   from earlier sweep already cover this; the original was kept for safety).
8. Mark R-00 Klaus-PDF-Drift section as resolved (links to consolidated meeting page).
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WW = Path("workspace/clients/warme-wimmer")
NDIR = WW / "context/hero-exports/notion-pages"
SHOTS_DIR = WW / "context/hero-exports/screenshots"
STORAGE_DIR = WW / "context/storage"
CREDITS_DIR = WW / "context/credits"
COMMS_LOG = WW / "context/comms-log.md"
PLAN_FILE = Path.home() / ".claude" / "plans" / "waerme-wimmer-all-right-i-m-glimmering-turing.md"
MEETING_NOTES_DIR = WW / "context/meeting-notes"
DOC_SITE_DIR = WW / "context/doc-site"
OUT_DIR = WW / "context/hero-exports"
TODAY = date.today().strftime("%Y-%m-%d")

# Extra pages outside notion-pages/ source dir (logs).
EXTRA_PAGES = {
    WW / "context/maintenance/team-updates.md": "R-team-updates.md",
}

# Existing notion-pages files: rename via map, exclude unwanted ones
RENAME_MAP = {
    "00-uebersicht.md": "R-00-uebersicht.md",
    "11-kosten-und-subscription.md": "R-kosten-und-subscription.md",
    "12-cross-reference.md": "R-hero-ids-und-connections.md",
    "14-hero-api-smoketest.md": "R-hero-api-smoketest.md",
    "04a-outlook-hero-ist-analyse.md": "R-w2-04-rewrite-design-ist.md",
    "04b-outlook-hero-rewrite-mockup.md": "R-w2-04-rewrite-design-mockup.md",
    "01-aufgabe-erledigt.md": "S-01-aufgabe-erledigt.md",
    "02-aufgaben-nach-statusaenderung.md": "S-02-aufgaben-nach-statuswechsel.md",
    "03-dokument-erstellt-statuswechsel.md": "S-03-dokument-erstellt.md",
    "04-outlook-hero-rewrite.md": "S-04-outlook-hero.md",
    "05-projekt-erstellt.md": "S-05-projekt-erstellt.md",
    "06-projekterinnerung.md": "S-06-projekterinnerung.md",
    "07-rechnungen-bezahlt.md": "S-07-rechnungen-bezahlt.md",
    "08-regiebericht-fehlt.md": "S-08-regiebericht-fehlt.md",
    "09-ueberfaellige-aufgaben.md": "S-09-ueberfaellige-aufgaben.md",
    "10-zahlung-erhalten.md": "S-10-zahlung-erhalten.md",
}
EXCLUDE = {"13-pre-meeting-fragen.md", "15-flowcharts-overview.md", "16-prozessdoku-klaus.md"}

# Old banner block (4 lines) to be replaced with a 1-liner on detail pages
OLD_BANNER_RE = re.compile(
    r"<!-- POST-GO-LIVE-BANNER -->\s*\n\n> ## Post-Go-Live Status .*?<!-- /POST-GO-LIVE-BANNER -->\n*",
    re.DOTALL,
)
ONE_LINE_BANNER = "> *Stand 2026-05-03 · 9/10 Hero-Szenarien live · W2-10 deferred zu n8n · Auto-Buy aktiv*\n\n"

# Old sequential `01-...md` -> new `S-01-...md` link rewrites for R-00
LINK_REWRITES = [
    (r"\(\./?01-aufgabe-erledigt\.md\)", "(S-01-aufgabe-erledigt.md)"),
    (r"\(\./?02-aufgaben-nach-status[äa]nderung\.md\)", "(S-02-aufgaben-nach-statuswechsel.md)"),
    (r"\(\./?03-dokument-erstellt-statuswechsel\.md\)", "(S-03-dokument-erstellt.md)"),
    (r"\(\./?04-outlook-hero-rewrite\.md\)", "(S-04-outlook-hero.md)"),
    (r"\(\./?04a-outlook-hero-ist-analyse\.md\)", "(R-w2-04-rewrite-design-ist.md)"),
    (r"\(\./?04b-outlook-hero-rewrite-mockup\.md\)", "(R-w2-04-rewrite-design-mockup.md)"),
    (r"\(\./?05-projekt-erstellt\.md\)", "(S-05-projekt-erstellt.md)"),
    (r"\(\./?06-projekterinnerung\.md\)", "(S-06-projekterinnerung.md)"),
    (r"\(\./?07-rechnungen-bezahlt\.md\)", "(S-07-rechnungen-bezahlt.md)"),
    (r"\(\./?08-regiebericht-fehlt\.md\)", "(S-08-regiebericht-fehlt.md)"),
    (r"\(\./?09-(?:ueberfaellige|überfällige)-aufgaben\.md\)", "(S-09-ueberfaellige-aufgaben.md)"),
    (r"\(\./?10-zahlung-erhalten\.md\)", "(S-10-zahlung-erhalten.md)"),
    (r"\(\./?11-kosten-und-subscription\.md\)", "(R-kosten-und-subscription.md)"),
    (r"\(\./?12-cross-reference\.md\)", "(R-hero-ids-und-connections.md)"),
    (r"\(\./?14-hero-api-smoketest\.md\)", "(R-hero-api-smoketest.md)"),
]


# ============ Meetings (consolidated) ============

# Fireflies recording URLs per meeting anchor. Populate as URLs become available.
# Source: `context/comms-log.md` and `context/meeting-notes/*.md` `transcript_source` fields.
# Two known so far; the other 8 transcripts exist in Fireflies but the URLs aren't in the repo yet.
# Pattern: https://app.fireflies.ai/view/{title-slug}-{hash} (paste full URL here when known).
FIREFLIES_BY_ANCHOR = {
    "m-04-08": None,
    "m-04-09": None,
    "m-04-15": None,
    "m-04-17": None,
    "m-04-21": "https://app.fireflies.ai/view/Automation-Hero-c2c0ade1-3b22",
    "m-04-22": None,
    "m-04-24": "https://app.fireflies.ai/view/20260423_Client_Wärme-Wimmer_Hero-Touchbase-57efba1c-880c",
    "m-04-25": None,
    "m-04-27": None,
    "m-04-30": None,
}

MEETINGS = [
    {"date": "2026-04-08", "anchor": "m-04-08",
     "title": "Onboarding-Meeting", "channel": "Teams", "duration": "37 Min",
     "attendees": "Irina Dragunow, Raphael Woltz, Nicolas Neumann",
     "outcome": "Scope + Zugaenge geklaert",
     "decisions": [
        "Migration ist Zapier -> Make (nicht Make -> Make).",
        "Zweiter Workstream: Hero-E-Mail-Automatisierung uebernehmen.",
        "5 aktive Zapier-Szenarien identifiziert (Alarme, WP-Check, Rechnungsstellung, Qualifizierung, Messeformular).",
        "Make-/Zapier-Zugang erteilt; Jotform-Zugang ausstehend.",
        "Kommunikation: Upwork wird durch E-Mail + WhatsApp-Gruppe abgeloest.",
        "Kapazitaet 20 Std/Woche, flexibel.",
     ],
     "notes_source": MEETING_NOTES_DIR / "2026-04-08-onboarding.md",
    },
    {"date": "2026-04-09", "anchor": "m-04-09",
     "title": "Hero-Handover-Meeting (Raphael + Michael)", "channel": "Teams (ohne Nico)", "duration": "?",
     "attendees": "Raphael Woltz, Michael Klaus (Hero); Nico nicht dabei",
     "outcome": "Timeline locked: Hero schaltet 24.04 ab, Go-Live 28.04",
     "decisions": [
        "Hero-API-Token: Raphael generiert per Self-Service.",
        "Uebergabe-Zeitplan: Hero schaltet Do 2026-04-24 Feierabend ab; Wochenende Joint-Test; Mo 2026-04-28 Go-Live.",
        "Support nach Uebergabe: kein offizieller Hero-Support; nur Hero-Support-Email.",
        "TinyURL-Workaround entfaellt (Subdomain-Bug behoben).",
        "E-Mail-Szenario muss komplett neu aufgebaut werden (Mailgun-Rewrite, Phase 2).",
        "Hero-JSONs werden per E-Mail an Nico uebermittelt.",
     ],
     "notes_source": None,
     "comms_keywords": ["hero handover", "handover-meeting", "hero/michael", "michael", "hero-jsons"],
    },
    {"date": "2026-04-15", "anchor": "m-04-15",
     "title": "Aufplanungs-Meeting (Workstream 2 Kickoff)", "channel": "Teams", "duration": "47 Min",
     "attendees": "Raphael Woltz, Irina Dragunow, Nicolas Neumann",
     "outcome": "W2-Architektur + Make-Tier festgelegt",
     "decisions": [
        "Make-Abo: Core 10K aktiviert (Pro 80K abgelehnt; Auto-Buy als Puffer).",
        "W2-04-Rewrite: Mailgun + S3 Architektur bestaetigt; Implementation NACH Go-Live (Phase 2).",
        "Test-Strategie: Tests gegen Produktion mit Test-Konvention (Fibi Muster, Test--Prefix, archivieren).",
        "Hero-App-Variante 'internal' ist installiert in Team 1421610 (Annahme korrigiert).",
     ],
     "notes_source": None,
    },
    {"date": "2026-04-17", "anchor": "m-04-17",
     "title": "Live-Walkthrough mit Raphael", "channel": "Teams", "duration": "90 Min",
     "attendees": "Raphael Woltz, Nicolas Neumann",
     "outcome": "Walkthrough produktiv; Lastenheft-Anforderungen verschaerft",
     "decisions": [
        "Walkthrough-Script erfolgreich gelaufen (Rechnungsstellung-Demo).",
        "Best-Practices-Cross-Reference als Diskussionsbasis akzeptiert.",
        "5 Go-Live-MUSS-Fixes priorisiert (Break-Handler, Dedup-Store, Failure-Alert, Webhook-Secret, Make-Tier).",
        "Irina-Forderung: Lastenhefte muessen mit Make-Screenshots unterfuettert werden, kein Fliesstext.",
     ],
     "notes_source": None,
    },
    {"date": "2026-04-21", "anchor": "m-04-21",
     "title": "Hero-Token-Meeting + Wimmer-Assistent-Setup", "channel": "Teams", "duration": "?",
     "attendees": "Raphael Woltz, Nicolas Neumann",
     "outcome": "Hero-API-Auth final geklaert; Sammelbearbeiter-Frage gelaeutert",
     "decisions": [
        "Hero-API-Token via dediziertem System-User 'Wimmer Assistent' (ID 316312); Token in .env.",
        "Sammelbearbeiter (User-ID 270612) ist NICHT Sabine; Shared-Inbox-User. Sabines echter User: 255797.",
        "Hero-UI-Login fuer Nicolas: Produktivzugang erteilt, Passwort geaendert.",
        "Test-Instanz wird verworfen (ID-Mismatch); Tests laufen gegen Produktion mit Konvention.",
        "Separate Sabine-Token nicht noetig; Wimmer-Assistent-Token reicht.",
        "W2-04-Rewrite (Mailgun) bleibt Phase 2; IST-Zustand wird Freitag uebernommen.",
     ],
     "notes_source": None,
    },
    {"date": "2026-04-22", "anchor": "m-04-22",
     "title": "Mittwochs-Prep (Pre-Migration)", "channel": "Teams", "duration": "?",
     "attendees": "Raphael Woltz, Nicolas Neumann",
     "outcome": "Letzte Blocker vor Freitag geraeumt",
     "decisions": [
        "OpenAI-Key: bestehender Hero-Vertrag-Key bleibt aktiv im Uebergang; eigener WW-Key spaeter (Phase 2).",
        "Postfach hero.automation@waerme-wimmer.de existiert; OAuth-Consent-Plan fuer Freitag.",
        "Wimmer-Assistent-Token-Smoke-Tests: Tasks-Mutation + Document-Upload bestanden.",
     ],
     "notes_source": None,
    },
    {"date": "2026-04-24", "anchor": "m-04-24",
     "title": "Hero-Handover-Meeting mit Michael (final)", "channel": "Teams", "duration": "94 Min",
     "attendees": "Nicolas Neumann, Irina Dragunow, Michael Klaus (Hero)",
     "outcome": "Wichtigstes Meeting: Mythen geklaert, Schedule-Intervalle uebergeben",
     "decisions": [
        "OpenAI-Modell-Swap: gpt-4o-mini -> gpt-5-mini (Kosten-gleich, besser, schneller).",
        "W2-04 Cleanup: 3x Delete-E-Mail-Routen deaktivieren; Gmail-Fallback (Modul 43) entfernen; OpenAI-Modell-Swap; TinyURL-Modul 26 entfernen.",
        "Hero Custom-App wird NICHT freigegeben (final). Nur W2-01 Custom-Webhook, sonst public App.",
        "Schedule-Intervalle (verbal): W2-04 Mo-Fr 05:00-22:30 alle 15 min; W2-08 Mo-Fr 7h 05:00-19:00; W2-09 daily 06:00; W2-10 daily 06:00; W2-07 daily 05:00.",
        "6x W2-04-Ausfaelle: Root-Cause = Outlook-Postfach voll (50 GB vs GoBD 10y). Silent hang. Mitigation: 50 -> 500 GB Upgrade.",
        "Calendar-Invite-Loop: Regex zu lax -> Michael hat verschaerft, Loop nicht mehr aktiv.",
        "W2-05 'fehlender Filter': Misdiagnose. Echte Ursache = Hero-Webhook-Event-Selection wird beim JSON-Export nicht uebertragen. Fix Hero-UI-seitig.",
        "Sammelbearbeiter (270612) und hardcoded Status-IDs: intentional static per Sabines Spec. Keine Dynamisierung.",
        "Hero-Document-Type-IDs (1094611, 688384, 952733, etc.) per Hero-UI verifiziert.",
        "n8n-Migration ermutigt: 'fuer die Situation, in der ihr euch befindet, ist es eigentlich sogar das Beste'.",
     ],
     "notes_source": MEETING_NOTES_DIR / "2026-04-24-michael-handover.md",
    },
    {"date": "2026-04-25", "anchor": "m-04-25",
     "title": "Joint-Test mit Raphael (Pre-Go-Live)", "channel": "Teams", "duration": "120 Min",
     "attendees": "Raphael Woltz, Nicolas Neumann (Irina nicht dabei)",
     "outcome": "9/10 Szenarien als Go-Live-ready verifiziert",
     "decisions": [
        "9/10 Szenarien als funktional verifiziert (W2-01 bis W2-09).",
        "W2-10 deferred zur n8n-Migration: 50-Result-Hero-Pagination-Limit, hat seit Hero-Zeiten nie funktioniert.",
        "Live-Fix W2-03: Filter-Rule `_trigger = document:created` entfernt (unsatisfiable in public Hero-App).",
        "Live-Fix W2-04: Hero-Automation-Filter raus (redundant zu Outlook-Server-Regel).",
        "Mehrfach-Bug-Befund: leere Test-Router in W2-01, Material-bestellt-Filter-Mismatch (Imperativ vs. Partizip).",
     ],
     "notes_source": None,
    },
    {"date": "2026-04-27", "anchor": "m-04-27",
     "title": "Irina-Call (Post-Go-Live Alignment)", "channel": "Teams", "duration": "40 Min",
     "attendees": "Irina Dragunow, Nicolas Neumann",
     "outcome": "Action-Items fuer Doku + n8n-Migration abgestimmt",
     "decisions": [
        "Brasilien-Move-Decision: Nico bleibt unter Vorbehalt ($25/hr, n8n-Lernkurve bezahlt).",
        "n8n-Migrations-Timeline: nach Leonard-Setup, Self-Hosted vs Cloud Starter offen.",
        "Storage-Snapshot Outlook hero.automation@: 42% / 21,12 GB; 15,47 GB Altlast in Geloeschte Elemente.",
        "Flowchart-Deadline: Dienstag 2026-05-05.",
     ],
     "notes_source": None,
    },
    {"date": "2026-04-30", "anchor": "m-04-30",
     "title": "Leonard-Call (n8n-Strategie)", "channel": "Teams", "duration": "120 Min",
     "attendees": "Leonard, Nicolas Neumann",
     "outcome": "n8n-Test-Instanz live; Lizenz + OS-Neo-Strategie offen",
     "decisions": [
        "n8n-Test-Instanz auf Hetzner-VM aufgesetzt.",
        "Self-Hosted Community erlaubt nur 1 User; gemeinsamer Login oder Cloud Starter ($20/Monat) als Alternativen.",
        "Server-Redundanz: kein automatisches Failover; manuelle VM-Migration (~20 Min Downtime) reicht.",
        "Strategischer Hinweis: WW-eigenes OS-Neo-CRM soll Hero langfristig komplett abloesen.",
        "W2-05 Osneo-URL-Bug entdeckt (Hero-Projekt-ID statt Dokument-ID, plus fehlendes /download).",
        "W1-Zapier-Migration wird in n8n neu gebaut (LexOffice/GMaps/Placetel/Jotform).",
     ],
     "notes_source": None,
    },
]


def render_meetings_page() -> str:
    """Single consolidated Meetings page. Mind the no-blank-line-in-tables invariant."""
    parts = []
    parts.append("# Meetings; Hero-Automatisierungen\n")
    parts.append("> *Stand 2026-05-03 · 10 Meetings konsolidiert · jede Section enthaelt Outcome + Entscheidungen + Notizen-Toggle*\n")
    parts.append("Diese Seite ersetzt die fruehere `Pre-Meeting-Fragen`-Liste: was offen war, ist hier in der jeweiligen Meeting-Section unter \"Was hier entschieden wurde\" festgehalten.\n")

    # --- Chronologie table (NO blank lines inside the table block!) ---
    table_lines = ["## Chronologie"]
    table_lines.append("")  # one blank line BEFORE table; ok
    table_lines.append("| Datum | Meeting | Outcome | Springen |")
    table_lines.append("|---|---|---|---|")
    for m in MEETINGS:
        title_short = m["title"]
        if len(title_short) > 50:
            title_short = title_short[:47] + "..."
        outcome = m["outcome"]
        if len(outcome) > 50:
            outcome = outcome[:47] + "..."
        table_lines.append(f"| {m['date']} | {title_short} | {outcome} | [#{m['anchor']}](#{m['anchor']}) |")
    parts.append("\n".join(table_lines))
    parts.append("")  # blank line AFTER table; ok

    # --- Decision-Log ---
    parts.append("## Decision-Log (thematisch)\n")
    decisions_log = [
        ("Make-Tier", "Core 10K + Auto-Buy aktiv (statt Pro 80K)", "m-04-15"),
        ("Hero-API-Auth", "Dedizierter System-User `Wimmer Assistent` (ID 316312); Token in .env", "m-04-21"),
        ("Sammelbearbeiter", "User-ID 270612 ist NICHT Sabine; Shared-Inbox-User. Intentional static.", "m-04-21"),
        ("OpenAI", "gpt-4o-mini -> gpt-5-mini (Kosten-gleich, schneller)", "m-04-24"),
        ("W2-04 Rewrite", "Mailgun + S3 Architektur; Implementierung Phase 2 (post-Go-Live)", "m-04-15"),
        ("Hero Custom-App", "Wird NICHT freigegeben. Nur W2-01 Custom-Webhook, sonst public App.", "m-04-24"),
        ("W2-05 Bug", "Hero-Webhook-Event-Selection wird beim JSON-Export nicht uebertragen. Fix Hero-UI-seitig.", "m-04-24"),
        ("Schedule-Intervalle", "W2-04 Mo-Fr 05-22:30 / W2-08 Mo-Fr 7h / W2-09+W2-10 daily 06:00 / W2-07 daily 05:00", "m-04-24"),
        ("W2-10", "Deferred zur n8n-Migration (Hero-API 50-Result-Pagination-Limit)", "m-04-25"),
        ("Outlook-Speicher", "50 -> 500 GB Upgrade post-Go-Live; Geloeschte-Elemente Quick-Win 31% Speicher-Rueckgewinn", "m-04-24"),
        ("n8n-Migration", "Auf Leonards Hetzner-Self-Hosted; Lizenz-Frage offen (Cloud Starter $20/mo Alternative)", "m-04-30"),
        ("OS-Neo-Strategie", "WW-eigenes OS-Neo soll Hero langfristig abloesen (Leonards Hinweis)", "m-04-30"),
    ]
    for topic, decision, anchor in decisions_log:
        parts.append(f"- **{topic}:** {decision} ([Meeting](#{anchor}))")
    parts.append("")

    # --- Per-meeting sections ---
    parts.append("---\n")
    for m in MEETINGS:
        section = render_meeting_section(m)
        parts.append(section)

    return "\n".join(parts) + "\n"


def render_meeting_section(m: dict) -> str:
    """One meeting as an H2 section with decisions + collapsible notes.

    Notes:
    - The H2 gets an explicit `{#anchor}` attr-list so chronology + decision-log links resolve.
    - The notes-dropdown uses `<details markdown="1">` so Python-markdown processes the
      inner markdown (headings, lists, tables) instead of dumping it as one paragraph.
    - The Fireflies URL (if known) is rendered after Outcome; placeholder if unknown so the
      gap is visible to Nico.
    """
    lines = []
    lines.append(f"## {m['date']}; {m['title']} {{#{m['anchor']}}}")
    lines.append("")
    lines.append(f"**Kanal · Dauer:** {m['channel']} · {m['duration']}  ")
    lines.append(f"**Teilnehmer:** {m['attendees']}  ")
    lines.append(f"**Outcome:** {m['outcome']}  ")

    fireflies = FIREFLIES_BY_ANCHOR.get(m["anchor"])
    if fireflies:
        lines.append(f"**Fireflies-Aufnahme:** [Notiz öffnen ↗]({fireflies})")
    else:
        lines.append("**Fireflies-Aufnahme:** _Link folgt; Nico backfillt aus Fireflies_")
    lines.append("")
    lines.append("### Was hier entschieden wurde")
    lines.append("")
    for d in m["decisions"]:
        lines.append(f"- {d}")
    lines.append("")

    # Collapsible detail-notes from source file (when available).
    # Strip both the YAML frontmatter and the H1 before injection so the dropdown
    # opens onto useful content, not the file's metadata.
    notes = ""
    src = m.get("notes_source")
    if src and src.is_file():
        notes = src.read_text(encoding="utf-8")
        notes = re.sub(r"^---\n.*?\n---\n+", "", notes, count=1, flags=re.DOTALL)  # frontmatter
        notes = re.sub(r"^# .+?\n+", "", notes, count=1)  # H1
        notes = notes.strip()
    if notes:
        lines.append('<details markdown="1">')
        lines.append("<summary>Notizen aus Meeting-File (zum Aufklappen)</summary>")
        lines.append("")
        lines.append(notes)
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    return "\n".join(lines)


# ============ S-* / R-* edits ============

def compress_banner(text: str) -> str:
    return OLD_BANNER_RE.sub(ONE_LINE_BANNER, text, count=1)


def rewrite_links(text: str) -> str:
    for pattern, repl in LINK_REWRITES:
        text = re.sub(pattern, repl, text)
    return text


def strip_old_flow_diagramm(text: str) -> str:
    """Remove the original `## Flow-Diagramm` block from S-* pages.

    The earlier sweep injected `## Flowcharts / ### Sabine-Version / ### Audit-Version`
    which supersedes the old `## Flow-Diagramm` single-mermaid block. Drop the original
    to avoid 3-mermaid-blocks-of-the-same-flow-on-one-page redundancy.
    """
    pattern = re.compile(r"## Flow-Diagramm\n+```mermaid\n.*?```\n+", re.DOTALL)
    return pattern.sub("", text, count=1)


def fix_r00_header(text: str) -> str:
    """Replace the pre-Go-Live framing at the top of R-00 with post-Go-Live compact state.

    Original (pre-Go-Live):
      **Stand:** 2026-04-15 EOD
      **Autor:** Nicolas Neumann (UnpauseAI)
      **Ziel-Go-Live:** Mo 2026-04-28 (intern); Hero schaltet Do 2026-04-24 Feierabend ab

    Post-Go-Live: collapse into 2-line factual state.
    """
    new_header = (
        "**Stand:** 2026-05-03 (post-Go-Live, Tag 6)  ·  **Status:** 9/10 Hero-Szenarien live, W2-10 deferred zur n8n-Migration  \n"
        "**Historie:** initial 2026-04-15 verfasst (Pre-Go-Live Lastenheft); Go-Live erfolgte planmaessig 2026-04-28."
    )
    return re.sub(
        r"\*\*Stand:\*\* 2026-04-15 EOD[^\n]*\n"
        r"\*\*Autor:\*\* Nicolas Neumann \(UnpauseAI\)\n"
        r"\*\*Ziel-Go-Live:\*\* Mo 2026-04-28[^\n]*",
        new_header,
        text,
        count=1,
    )


def fix_r00_special(text: str) -> str:
    """R-00 specific: drop link to excluded `13-pre-meeting-fragen.md`,
    mark stale Klaus-PDF-Drift section as resolved, fix pre-Go-Live header.
    """
    text = fix_r00_header(text)
    # Replace the row pointing to 13-pre-meeting-fragen with a resolved-link to consolidated meetings
    text = re.sub(
        r"\| 13 \| \[Pre-Meeting-Fragen\]\([^)]+\) \|[^|]*\|[^|]*\| 63 Fragen für Fr-Meeting \|",
        "| - | ~~Pre-Meeting-Fragen~~ obsolet, in [M-meetings](M-meetings.md) aufgegangen | | | |",
        text,
    )
    # Remove the Klaus-PDF-Drift HIGH/MEDIUM/LOW block (it was pre-Go-Live, all 3 resolved at M-04-24)
    drift_re = re.compile(
        r"\*\*Klaus-PDF-Drift \(3 Findings, vor Klaus-Klärung Mo\):\*\*\n.*?(?=\n\n|\n---|\n## )",
        re.DOTALL,
    )
    text = drift_re.sub(
        "**Klaus-PDF-Drift (RESOLVED 2026-04-24):** Alle 3 Findings am 2026-04-24 mit Michael geklaert. "
        "s2 +7 Tage = intentional, s1 Entry-Filter mit 5 Aufgaben-Titeln korrigiert, s6 Regex-Strict bestaetigt. "
        "Siehe [M-meetings · 2026-04-24](M-meetings.md#m-04-24).",
        text,
    )
    return text


def fix_r_w2_04_navigation(text: str) -> str:
    """Replace `Seite 04` / `Seite 04b` references with new R-* names."""
    text = re.sub(
        r"\*\*Seite 04:\*\*", "**[R-w2-04-rewrite-design (SOLL)](R-w2-04-rewrite-design-mockup.md):**",
        text,
    )
    text = re.sub(
        r"\*\*Seite 04b:\*\*", "**[Mockup](R-w2-04-rewrite-design-mockup.md):**",
        text,
    )
    text = re.sub(
        r"durch den Rewrite auf \[Seite 04\]\([^)]+\)", "durch den Rewrite (siehe [R-w2-04-rewrite-design-mockup.md](R-w2-04-rewrite-design-mockup.md))",
        text,
    )
    return text


def render_start_here_page() -> str:
    """Persona-based landing page that orients a fresh reader.

    Three persona cards (Sabine / Raphael / Auditor) → each links to the right starting page.
    Embedded HTML (passing through Python-markdown) so we get the same `.persona-cards` styling
    as the rest of the site.
    """
    return (
        "# Start hier; Hero-Automatisierungen Doku\n"
        "\n"
        "> **Was ist hier?** 10 Make.com-Automatisierungen, die seit 2026-04-28 die Hero-Workflows von Wärme Wimmer abdecken; vorher von Hero gehostet, jetzt bei uns. Diese Seiten erklären jede Automatisierung, was im Hintergrund läuft, wer welche Frage beantwortet, und was zu tun ist wenn etwas kippt.\n"
        "\n"
        "## Wo gehst du hin?\n"
        "\n"
        "<div class=\"persona-cards\">\n"
        "  <a class=\"persona-card\" href=\"s-00-flowcharts-overview.html\">\n"
        "    <h3>Sabine / Operativ</h3>\n"
        "    <p>Du siehst eine Aufgabe, willst wissen ob die richtige Automatisierung angesprungen ist und wo sie steht.</p>\n"
        "    <span class=\"persona-target\">→ Flowcharts-Übersicht (alle 10 Szenarien auf einer Seite)</span>\n"
        "  </a>\n"
        "  <a class=\"persona-card\" href=\"index.html\">\n"
        "    <h3>Raphael / Technisch</h3>\n"
        "    <p>Du willst wissen ob die Operations-Quote unter Limit ist, ob alle Szenarien aktiv laufen, und wo die letzten Fehler aufgetreten sind.</p>\n"
        "    <span class=\"persona-target\">→ Dashboard mit Live-Make-Daten</span>\n"
        "  </a>\n"
        "  <a class=\"persona-card\" href=\"r-00-uebersicht.html\">\n"
        "    <h3>Auditor / Später-Eingestiegener</h3>\n"
        "    <p>Du willst die Geschichte verstehen; warum so gebaut, welche Entscheidungen, was war Phase 1 vs Phase 2.</p>\n"
        "    <span class=\"persona-target\">→ Lastenheft (Hintergrund)</span>\n"
        "  </a>\n"
        "  <a class=\"persona-card\" href=\"r-runbook.html\">\n"
        "    <h3>03:00 Uhr-Eskalation</h3>\n"
        "    <p>Etwas ist kaputt. Du brauchst einen Diagnose-Pfad und einen Erst-Fix.</p>\n"
        "    <span class=\"persona-target\">→ Incident-Runbook</span>\n"
        "  </a>\n"
        "</div>\n"
        "\n"
        "## Drei Gruppen, eine Logik\n"
        "\n"
        "**Automatisierungen (S-* )**; Pro W2-Automatisierung eine Seite mit Status-Card, Was-tut-es, Trigger, Branching, Modul-Inventar, Risiko-Bewertung, Quick-Fix. **S-00-flowcharts-overview** ist die Sammelseite mit allen Flow-Diagrammen.\n"
        "\n"
        "**Referenz (R-* )**; Querschnitts-Themen, die mehr als ein Szenario betreffen: Hero-IDs, Connections, Kosten, Lastenheft (Hintergrund), Phase-2-Mockups, Runbook, FAQ, Glossar, Kontakte.\n"
        "\n"
        "**Aktivität (M-, R-team-updates)**; Was passiert ist: Meetings (chronologisch + thematisch), Wartungs-Updates an Raphael/Irina/Sabine.\n"
        "\n"
        "## Wie nutze ich die Suche?\n"
        "\n"
        "**Ctrl+K** (oder Cmd+K) öffnet eine Suche über alle Seiten und Abschnitte. Tippe `Sammelbearbeiter`, `W2-04`, `Mailgun`, oder einen anderen Begriff; Enter springt zur Stelle.\n"
        "\n"
        "## Pflege\n"
        "\n"
        "Quelle der Wahrheit: das Repo `workspace/clients/warme-wimmer/`. Diese HTML-Seiten werden daraus gebaut. Ad-hoc-Edits direkt im Notion-Space gehen beim nächsten Re-Import verloren; Änderungen also ins Repo.\n"
    )


def filter_comms_section_for_meeting(section: str, meeting_keywords: list[str]) -> str:
    """Best-effort filter: keep only sub-sections of a comms-log entry that mention meeting keywords.

    Comms-log entries are organized by date with sub-headings (### sub-headings).
    Many sub-headings are unrelated chat that happened on the same day. This function
    keeps sub-sections whose heading or first paragraph contains any of the meeting keywords.
    """
    # Split into sub-sections at level-3 (### ...) headings
    chunks = re.split(r"(?m)^(### .+)$", section)
    if len(chunks) < 3:
        return section.strip()
    # chunks now alternates: [pre-heading-text, heading, body, heading, body, ...]
    out = [chunks[0].strip()]
    for i in range(1, len(chunks) - 1, 2):
        heading = chunks[i]
        body = chunks[i + 1]
        keep = any(kw.lower() in heading.lower() or kw.lower() in body.lower()[:300] for kw in meeting_keywords)
        if keep:
            out.append(heading)
            out.append(body.rstrip())
    return "\n".join(p for p in out if p).strip()


# ============ Page intros (Was / Wann callouts) + Quick-Fix blocks ============


# 1-2 line "Was / Wer / Wann"-callouts injected after the H1 of each R-* / M-* page.
# Helps a fresh reader orient in 3 seconds without a glossary lookup.
PAGE_INTROS = {
    "M-meetings.md": (
        "**Was ist das?** Chronik aller 10 Meetings vom Onboarding bis Post-Go-Live, plus thematischer Decision-Log oben. "
        "**Wann brauchst du das?** Wenn du wissen willst, *warum* eine Entscheidung getroffen wurde; der Decision-Log verlinkt direkt ins Meeting."
    ),
    "R-team-updates.md": (
        "**Was ist das?** Append-only-Chronik der Status-Updates an Raphael / Irina / Sabine; was wurde wann kommuniziert, mit Screenshots. "
        "**Wann brauchst du das?** Bei der Frage 'haben wir das schon angekündigt?' oder für den Audit-Trail."
    ),
    "R-hero-ids-und-connections.md": (
        "**Was ist das?** Referenz-Tabelle aller Hero-IDs, Tokens, Connection-IDs, Webhook-IDs in einem Dokument. "
        "**Wann brauchst du das?** Bei Connection-Brüchen, Token-Rotation, oder wenn du eine ID in Make-Modul wiederfinden musst."
    ),
    "R-kosten-und-subscription.md": (
        "**Was ist das?** Make-Tier, OpenAI-Verbrauch, Mailgun-Kosten; alle Komponenten mit Stand-pro-Monat. "
        "**Wann brauchst du das?** Bei Operations-Spike, Tier-Upgrade-Frage, oder Kosten-Rechtfertigung."
    ),
    "R-w2-04-rewrite-design-ist.md": (
        "**Was ist das?** IST-Analyse des aktuellen Outlook-nach-Hero-Szenarios (W2-04); alle 24 Module, alle bekannten Schwächen. "
        "**Wann brauchst du das?** Vor dem Phase-2-Rewrite, oder wenn das aktuelle Szenario kippt und du verstehen willst, was unten drunter läuft."
    ),
    "R-w2-04-rewrite-design-mockup.md": (
        "**Was ist das?** SOLL-Architektur des Phase-2-Rewrites (Mailgun + S3 + 13 Module statt 24). Noch nicht gebaut. "
        "**Wann brauchst du das?** Wenn die Phase-2-Frage aufkommt, oder wenn das aktuelle Szenario zu fragil wird."
    ),
    "R-runbook.md": "",  # Runbook hat eigenen Vorspann.
    "R-faq.md": "",       # FAQ hat eigenen Vorspann.
    "R-glossary.md": "",  # Glossary hat eigenen Vorspann.
    "R-contacts.md": "",  # Contacts hat eigenen Vorspann.
}


def inject_page_intro(filename: str, text: str) -> str:
    """Inject a `> **Was ist das?** …` blockquote callout right after the H1.

    No-op if the page key isn't in PAGE_INTROS or its value is empty (already has its own intro).
    """
    intro = PAGE_INTROS.get(filename)
    if not intro:
        return text
    # Find H1 line and inject after it (preserving any blockquotes that follow)
    return re.sub(
        r"^(# [^\n]+\n)",
        lambda m: m.group(1) + "\n> " + intro + "\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )


# Per-scenario Quick-Fix block; injected right under the status card on each S-XX page.
# Keep it short and scannable. Each entry is markdown.
QUICK_FIX_BY_SCENARIO = {
    "S-01-aufgabe-erledigt.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. Im Make-UI das Szenario manuell **deaktivieren + reaktivieren**; triggert Webhook-Re-Sync.\n"
        "2. Eine Test-Aufgabe in Hero erledigen → Webhook-Modul → Payload sichtbar?\n"
        "3. Wenn keine Payload kommt: Hero-Custom-App-Webhook defekt → [Runbook · W2-01](r-runbook.md#w2-01).\n"
    ),
    "S-02-aufgaben-nach-statuswechsel.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. Make-UI History öffnen → letzten Failed-Run prüfen.\n"
        "2. **Status-ID-Drift** ist die häufigste Ursache (Hero hat Status umbenannt). Cross-Reference: [R-hero-ids-und-connections](r-hero-ids-und-connections.md).\n"
        "3. Eskalation: [Runbook · scenario-error](r-runbook.md#scenario-error).\n"
    ),
    "S-03-dokument-erstellt.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. **Filter prüfen**: W2-03 nutzt Document-**Name** für Rechnungs-Filter (Schwachstelle, falls Name geändert wird).\n"
        "2. Make-UI History → letzten Failed-Run.\n"
        "3. Eskalation: [Runbook](r-runbook.md#scenario-error).\n"
    ),
    "S-04-outlook-hero.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. **Outlook-Speicher** prüfen (Dashboard-KPI). Wenn 75%+: Gelöschte Elemente leeren oder Upgrade.\n"
        "2. **OpenAI-Modell** prüfen; soll `gpt-5-mini` sein, nicht `gpt-4o-mini`. Verifiziert bei [m-04-24](m-meetings.md#m-04-24).\n"
        "3. Stale Chain ohne Fehlermeldung? Klassisches Outlook-Voll-Symptom; Phase-2-Mailgun-Rewrite löst das strukturell ([R-w2-04-rewrite-design-mockup](r-w2-04-rewrite-design-mockup.md)).\n"
        "4. Eskalation: [Runbook](r-runbook.md#scenario-error).\n"
    ),
    "S-05-projekt-erstellt.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. **Hero-Webhook-Event-Selection** in Hero-UI prüfen; muss \"Projekt erstellt\" sein, nicht \"alle\". Bekannte Drift-Quelle.\n"
        "2. Webhook in Hero-UI neu registrieren falls nötig; kein Make-Side-Filter.\n"
        "3. Hintergrund: [m-04-24 W2-05-Bug](m-meetings.md#m-04-24).\n"
    ),
    "S-06-projekterinnerung.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. Schedule prüfen: läuft täglich, daher max 1× Fehler pro Tag.\n"
        "2. Make-UI History → Wenn `Hero API 4xx`: Token rotieren prüfen.\n"
        "3. Eskalation: [Runbook](r-runbook.md#scenario-error).\n"
    ),
    "S-07-rechnungen-bezahlt.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. Schedule: täglich 05:00; verifiziert in [m-04-24](m-meetings.md#m-04-24).\n"
        "2. Make-UI History → letzten Failed-Run.\n"
        "3. Eskalation: [Runbook](r-runbook.md#scenario-error).\n"
    ),
    "S-08-regiebericht-fehlt.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. Schedule: alle 7h Mo-Fr 05:00-19:00 (= 2 Runs/Tag).\n"
        "2. Make-UI History → letzten Failed-Run, Fehler-Snippet prüfen.\n"
        "3. Eskalation: [Runbook](r-runbook.md#scenario-error).\n"
    ),
    "S-09-ueberfaellige-aufgaben.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "1. Schedule: täglich 06:00.\n"
        "2. Make-UI History → letzten Failed-Run.\n"
        "3. Eskalation: [Runbook](r-runbook.md#scenario-error).\n"
    ),
    "S-10-zahlung-erhalten.md": (
        "## Wenn das Szenario kippt {#quick-fix}\n"
        "\n"
        "**Status: deaktiviert**; gewollt. W2-10 ist deferred zur n8n-Migration wegen 50-Result-Hero-Pagination-Limit. "
        "Siehe [Runbook · W2-10](r-runbook.md#w2-10) und [m-04-25](m-meetings.md#m-04-25).\n"
    ),
}


def inject_quick_fix(filename: str, text: str) -> str:
    """Inject the Quick-Fix block right after the one-line banner (or H1 if no banner).

    Searches for the canonical 1-line banner from compress_banner(). Falls back to inserting
    after the H1 if the banner isn't there.
    """
    quick = QUICK_FIX_BY_SCENARIO.get(filename)
    if not quick:
        return text
    # Try to insert after the 1-line banner.
    banner_match = re.search(
        r"(^> \*Stand 2026-05-03[^\n]+\n+)",
        text,
        flags=re.MULTILINE,
    )
    if banner_match:
        idx = banner_match.end()
        return text[:idx] + quick + "\n" + text[idx:]
    # Fall back: after the H1.
    return re.sub(
        r"^(# [^\n]+\n+)",
        lambda m: m.group(1) + quick + "\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )


def restructure_r00_audit_to_bottom(text: str) -> str:
    """Move the dense `Evidence-Verifikation 2026-04-15` block to the page footer.

    The block opens with that exact phrase and runs until the next `> Stand` blockquote
    or a `## ` H2. We pull it out, wrap in `<details markdown="1">`, and append at the end.
    """
    audit_re = re.compile(
        r"(>?\s*\*\*Evidence-Verifikation 2026-04-15:.*?)(?=\n+(?:>?\s*Stand 2026-05-03|## |---))",
        re.DOTALL,
    )
    m = audit_re.search(text)
    if not m:
        return text
    audit_block = m.group(1).strip()
    # Strip leading ">" so the markdown inside <details> is plain prose.
    audit_block = re.sub(r"^>\s?", "", audit_block, flags=re.MULTILINE).strip()
    text_without = text[: m.start()] + text[m.end():]
    appended = (
        text_without.rstrip()
        + "\n\n---\n\n"
        + '<details markdown="1">\n'
        + "<summary>Audit-Trail: Evidence-Verifikation 2026-04-15</summary>\n\n"
        + audit_block
        + "\n\n</details>\n"
    )
    return appended


def fix_r00_intro_callout(text: str) -> str:
    """Inject the 'Was ist das? / Wer / Wann' blockquote right after R-00's H1."""
    intro = (
        "> **Was ist das?** Das ursprüngliche Lastenheft aus der Bauphase, post-Go-Live aktualisiert.  \n"
        "> **Wer liest das?** Ein Auditor oder ein Später-Eingestiegener, der den Hintergrund verstehen will; nicht das Tagesgeschäft.  \n"
        "> **Wann brauchst du das?** Wenn du wissen willst, *warum* eine Automatisierung so gebaut wurde. Für tägliche Arbeit reicht die jeweilige S-XX-Seite oder [M-meetings](M-meetings.md).\n"
    )
    return re.sub(r"^(# [^\n]+\n)", lambda m: m.group(1) + "\n" + intro + "\n", text, count=1, flags=re.MULTILINE)


def build_pages() -> dict[str, str]:
    """Build the dict of {filename: markdown_content} that constitutes the Notion bundle.

    Reusable by both the zip-builder (this module's main) and the doc-site builder
    (`tools/build-doc-site.py`).
    """
    pages: dict[str, str] = {}
    pages["0-Start-Hier.md"] = render_start_here_page()
    pages["M-meetings.md"] = render_meetings_page()

    s00_src = NDIR / "15-flowcharts-overview.md"
    if s00_src.is_file():
        s00 = s00_src.read_text(encoding="utf-8")
        s00 = re.sub(
            r"Quelle der Sabine-Prozess-Spalte: \*\*Michael Klaus' Prozess-Dokumentation\*\*[^\n]+\n+",
            "", s00,
        )
        s00 = re.sub(
            r"Wo der Klaus-Zweck-Satz von der Sabine-Mermaid-Sicht abweicht, gilt \*\*Klaus als Wahrheit\*\*[^\n]+\n+",
            "", s00,
        )
        s00 = re.sub(r"lt\. Klaus", "lt. Hero-Doku", s00)
        s00 = re.sub(
            r"\*\*Prozess-Doku \(Klaus, kanonisch\):\*\* \[16 Prozessdoku Klaus, Section \d+\]\([^)]+\); siehe dort fuer Hero-IDs, Filter-Bedingungen, alle Routen mit Status-Codes\.\n+",
            "", s00,
        )
        s00 = re.sub(r"\| Prozess \(lt\. Hero-Doku\) \|", "| Prozess |", s00)
        s00 = re.sub(r"\| Prozess \(lt\. Klaus\) \|", "| Prozess |", s00)
        pages["S-00-flowcharts-overview.md"] = s00

    for src_md in sorted(NDIR.glob("*.md")):
        if src_md.name in EXCLUDE:
            continue
        new_name = RENAME_MAP.get(src_md.name)
        if new_name is None:
            continue
        text = src_md.read_text(encoding="utf-8")
        text = compress_banner(text)
        if new_name.startswith("S-"):
            text = strip_old_flow_diagramm(text)
            text = inject_quick_fix(new_name, text)
        if new_name.startswith("R-"):
            text = rewrite_links(text)
        if new_name == "R-00-uebersicht.md":
            text = fix_r00_special(text)
            text = fix_r00_intro_callout(text)
            text = restructure_r00_audit_to_bottom(text)
        if new_name.startswith("R-w2-04-"):
            text = fix_r_w2_04_navigation(text)
        # Inject Was/Wann callout (after H1) for all known pages with intros.
        text = inject_page_intro(new_name, text)
        pages[new_name] = text

    for src, target in EXTRA_PAGES.items():
        if src.is_file():
            text = src.read_text(encoding="utf-8")
            text = inject_page_intro(target, text)
            pages[target] = text

    # Doc-site-only pages (glossary, runbook, contacts, FAQ). Map plain filename -> R-* slug.
    docsite_map = {
        "glossary.md": "R-glossary.md",
        "runbook.md": "R-runbook.md",
        "contacts.md": "R-contacts.md",
        "faq.md": "R-faq.md",
    }
    if DOC_SITE_DIR.is_dir():
        for src_name, target_name in docsite_map.items():
            src_path = DOC_SITE_DIR / src_name
            if src_path.is_file():
                pages[target_name] = src_path.read_text(encoding="utf-8")

    return pages


def main() -> int:
    pages: dict[str, str] = {}

    # 0. Landing page (sorts above M-/R-/S- alphabetically because '0' < letters in ASCII)
    pages["0-Start-Hier.md"] = render_start_here_page()

    # 1. Single consolidated meetings page
    pages["M-meetings.md"] = render_meetings_page()

    # 2. S-00 flowcharts overview; reuse from prior generator if exists, else regenerate
    s00_src = NDIR / "15-flowcharts-overview.md"
    if s00_src.is_file():
        s00 = s00_src.read_text(encoding="utf-8")
        # Strip Klaus references the prior script left in (Process column / Klaus link section)
        s00 = re.sub(
            r"Quelle der Sabine-Prozess-Spalte: \*\*Michael Klaus' Prozess-Dokumentation\*\*[^\n]+\n+",
            "", s00,
        )
        s00 = re.sub(
            r"Wo der Klaus-Zweck-Satz von der Sabine-Mermaid-Sicht abweicht, gilt \*\*Klaus als Wahrheit\*\*[^\n]+\n+",
            "", s00,
        )
        s00 = re.sub(r"lt\. Klaus", "lt. Hero-Doku", s00)
        s00 = re.sub(
            r"\*\*Prozess-Doku \(Klaus, kanonisch\):\*\* \[16 Prozessdoku Klaus, Section \d+\]\([^)]+\); siehe dort fuer Hero-IDs, Filter-Bedingungen, alle Routen mit Status-Codes\.\n+",
            "", s00,
        )
        s00 = re.sub(
            r"\| Prozess \(lt\. Hero-Doku\) \|", "| Prozess |", s00,
        )
        # Remove "Prozess (lt. Klaus)" header if not yet caught
        s00 = re.sub(r"\| Prozess \(lt\. Klaus\) \|", "| Prozess |", s00)
        pages["S-00-flowcharts-overview.md"] = s00
    else:
        print("WARN: 15-flowcharts-overview.md missing; S-00 not produced", file=sys.stderr)

    # 3. Existing notion-pages files: rename + apply targeted edits
    for src_md in sorted(NDIR.glob("*.md")):
        if src_md.name in EXCLUDE:
            continue
        new_name = RENAME_MAP.get(src_md.name)
        if new_name is None:
            print(f"  WARN: no rename rule for {src_md.name} (skipped)")
            continue
        text = src_md.read_text(encoding="utf-8")
        # Compress 4-line banner -> 1-liner
        text = compress_banner(text)
        # S-* pages: also strip duplicate Flow-Diagramm block
        if new_name.startswith("S-"):
            text = strip_old_flow_diagramm(text)
        # R-* pages: rewrite intra-zip links
        if new_name.startswith("R-"):
            text = rewrite_links(text)
        # R-00 specific cleanup
        if new_name == "R-00-uebersicht.md":
            text = fix_r00_special(text)
        # R-w2-04-* navigation pointers
        if new_name.startswith("R-w2-04-"):
            text = fix_r_w2_04_navigation(text)
        pages[new_name] = text

    # 4. Extra pages (storage log, credits log) from outside notion-pages/
    for src, target in EXTRA_PAGES.items():
        if src.is_file():
            pages[target] = src.read_text(encoding="utf-8")
            print(f"  Included extra: {src} -> {target}")
        else:
            print(f"  WARN: extra page missing: {src} (not added)")

    # 5. Build zip
    out_name = f"hero-lastenheft-notion-{TODAY}-v18-clean.zip"
    out_path = OUT_DIR / out_name

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(pages.keys()):
            zf.writestr(name, pages[name])
        if SHOTS_DIR.is_dir():
            for png in sorted(SHOTS_DIR.glob("*.png")):
                zf.write(png, arcname=f"screenshots/{png.name}")
            per_module = SHOTS_DIR / "per-module"
            if per_module.is_dir():
                for png in sorted(per_module.glob("*.png")):
                    zf.write(png, arcname=f"screenshots/{png.name}")

    md_count = len(pages)
    png_count = sum(1 for _ in SHOTS_DIR.rglob("*.png")) if SHOTS_DIR.is_dir() else 0
    size_mb = out_path.stat().st_size / (1024 * 1024)

    print(f"Wrote: {out_path}  ({size_mb:.2f} MB)")
    print(f"  Pages: {md_count}  ·  Screenshots: {png_count}")
    print()
    m = sum(1 for k in pages if k.startswith("M-"))
    s = sum(1 for k in pages if k.startswith("S-"))
    r = sum(1 for k in pages if k.startswith("R-"))
    print(f"  Meetings (M-*):  {m}  (consolidated single page)")
    print(f"  Scenarios (S-*): {s}  (1 overview + {s-1} per-scenario)")
    print(f"  Reference (R-*): {r}")
    print()
    print(f"Excluded from zip: {sorted(EXCLUDE)}")
    print()
    print("v18 fixes applied:")
    print("  - Consolidated 10 separate meeting pages into M-meetings.md")
    print("  - Table rendering fix (no blank lines inside tables)")
    print("  - R-00 intra-zip links rewritten to S-/R- naming")
    print("  - Broken link to excluded 13-pre-meeting-fragen.md replaced with strikethrough")
    print("  - Klaus-PDF-Drift section marked resolved (link to M-04-24 section)")
    print("  - Banner compressed from 4 lines to 1 line on detail pages")
    print("  - S-* pages: duplicate `## Flow-Diagramm` block stripped (Sabine + Audit blocks remain)")
    print("  - R-w2-04-* navigation pointers fixed (`Seite 04` -> R-w2-04-*)")
    print("  - S-00 cross-reference column header simplified ('Prozess' instead of 'Prozess (lt. Klaus)')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
