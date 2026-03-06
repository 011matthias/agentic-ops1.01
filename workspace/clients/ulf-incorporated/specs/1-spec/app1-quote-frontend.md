---
id: app1
name: Quote Frontend
type: app
stage: live
needs_fixes: false
version: 1.0.0
created: 2026-03-04
updated: 2026-03-04
orchestrator: n8n
trigger:
  type: manual
systems:
  - a2-webhook
owner: TBD
last_changes:
  - Initial spec created
next_steps:
  - Build A2 first (need webhook URL)
  - Then build HTML with real URL
  - Host locally or on static hosting
stage_history:
  - stage: spec
    date: 2026-03-04
---

# APP1 – Quote Frontend

## Goal

Erweiterte Version der bestehenden HTML-Zitate-App. Holt Zitate live via A2-Webhook, zeigt 3 auf einmal, erlaubt Filterung nach Kategorie und Sprache.

## Deliverable

Single-file HTML: `automations/app1-frontend/index.html`

## UI Layout

```
┌─────────────────────────────────────────────┐
│           Inspirierende Zitate              │
├─────────────────────────────────────────────┤
│  Kategorie: [Alle ▼]   Sprache: [Alle ▼]   │
│                [Neue Zitate laden]          │
├─────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────────┐ │
│ │ "Zitat 1..."    │ │ "Zitat 2..."        │ │
│ │ — Autor 1       │ │ — Autor 2           │ │
│ │ [motivation]    │ │ [wisdom]            │ │
│ └─────────────────┘ └─────────────────────┘ │
│ ┌─────────────────────────────────────────┐ │
│ │ "Zitat 3..."                            │ │
│ │ — Autor 3                               │ │
│ │ [success]                               │ │
│ └─────────────────────────────────────────┘ │
│ 847 Zitate in der Datenbank                 │
└─────────────────────────────────────────────┘
```

## Features

| Feature | Beschreibung |
|---------|-------------|
| Kategorie-Filter | Dropdown: Alle / Motivation / Weisheit / Erfolg / Humor / Glück |
| Sprache-Filter | Dropdown: Alle / Deutsch / Englisch |
| 3 Zitate gleichzeitig | Responsive Grid, 1-2 Karten pro Reihe |
| Live API-Abruf | `fetch()` an A2-Webhook beim Button-Click |
| Fallback | Statische deutsche Zitate wenn API nicht erreichbar |
| DB-Counter | Zeigt Gesamtanzahl der Zitate in der DB |
| Konfigurierbar | `WEBHOOK_URL` als Konstante oben in der Datei |

## Kategorie-Mapping (DE Labels)

| API-Wert | DE-Label |
|----------|----------|
| motivation | Motivation |
| wisdom | Weisheit |
| success | Erfolg |
| humor | Humor |
| happiness | Glück |

## Error Handling

- API nicht erreichbar → zeige statische Fallback-Zitate, zeige Fehlermeldung
- Leere Antwort → zeige "Keine Zitate gefunden für diese Filterung"

## Hosting

Kann lokal (Doppelklick) oder auf GitHub Pages / Netlify Drop gehostet werden. Kein Build-Tool nötig — pure HTML/CSS/JS.
