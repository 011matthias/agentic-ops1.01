# Checkpoint: WW W2-14 Testseite Jetzt pruefen

**Date:** 2026-10-21 (Arbeit vom 14./15.10.2026, Checkpoint erst jetzt geschrieben)
**Status:** Testseite fuer Tobias und Sabine fertig, Duplikat sendet nur an die beiden; Einladungsmail entworfen, Versand unbestaetigt; Release 8 am Original offen.

---

## Summary
Probedurchlauf des Vertriebsablaufs (Typ 72627) mit Matthias von Hand, danach die Startseite des Duplikats zu einer Selbsttest-Seite fuer Tobias und Sabine umgebaut: "Jetzt pruefen" statt Zeitplan, An/Aus-Schalter, zwei Reiter, Empfaenger nur Sabine und Tobias. Die Arbeit liegt im Klon `agentic-ops` (nicht hier), Branch `client/warme-wimmer/w2-14-sales-process-72627`, PR #305 offen.

---

## What Was Done This Session
### Probedurchlauf HUK-106489 (14./15.10.)
1. Hauptweg Erstgespraech bis Termin bestaetigt (R1 bis R23) mit Einzelknoepfen, nach jedem Schritt Hero-Readback (Status, Logbuch, Aufgaben) plus IMAP-Abgleich der Testmails: jede Regel im getesteten Pfad wie erwartet, ein Statuseintrag je Wechsel, nie ein Doppelsprung.
2. Seitenast Archivieren (R3) gefahren; Faelligkeiten aller Aufgaben gegen die Regeldatei geprueft: R17 (So 18.10.) und R3 (Sa 17.10.) landen auf Wochenenden, weil feste Tage ohne Wochenendlogik.
3. Hero-Reiter geklaert: Planung, Angebotserstellung, Abgeschlossen (evtl. auch Umsetzung Abschlagsrechnung, Schlussrechnung) haben keine Regel; Entfernen nur im Hero-UI, Entscheidung offen.

### Startseite `t1lRfYjuqU9THsaf` (34 Knoten)
1. Reiter "Testen": Statuskasten mit Schalter (aktiviert/deaktiviert nur das Duplikat, Id und Name zur Laufzeit geprueft), Erklaerung, "Jetzt pruefen" (leerer Body, alle freigegebenen Testprojekte, wiederholt bis keine Aktion mehr faellig, max 6 Durchgaenge), Zeitraffer-Hinweis.
2. Reiter "Zeitspruenge und einzelne Regeln" (`?tab=zeit`, serverseitig, Redirect behaelt den Reiter): 26 Einzelknoepfe wie zuvor.
3. Abschnitt "Was zuletzt passiert ist" gebaut und auf Owner-Wunsch wieder entfernt.
4. Kalt gefahren: beide Reiter geladen, Schalter aus/an, Redirect mit Reiter, "Jetzt pruefen" auf archiviertem Projekt (0 Aktionen), Aufruf ohne projekt_id am Duplikat (Lauf 0 Aktionen), Erstgespraech-Lauf mit Mail R1 an Matthias.

### Duplikat `tB5anuCbpmYsrA7K`
1. `duplikat-umbauen.mjs` um `--nur-team` ergaenzt. Zwischenstaende: nur Team (b02e8bac), nur Matthias fuer seinen Test (150523b8), dann zurueck auf nur Sabine und Tobias, veroeffentlicht 28675485. Original unberuehrt auf a9f98291.

### Kommunikation
1. Einladungsmail an Tobias und Sabine als Entwurf `workspace/clients/warme-wimmer/context/drafts/2026-10-15-tobias-sabine-testseite.md` (Klon agentic-ops), Kritiker-Pass durchlaufen, Du-Form ist Annahme.

---

## Key Decisions Made
### Uhr von "Jetzt pruefen"
- **Choice:** 1 Tag = 5 Sekunden (Owner), gegen meine Empfehlung echte Uhr.
- **Rationale:** Tests in Minuten statt Wochen. Folge: R2 nach rund 2 Minuten, R3 (Archivieren) nach rund 3 Minuten, der naechste Klick handelt auf dem Zustand zum Klickzeitpunkt.

### Empfaenger
- **Choice:** Mails nur an Sabine und Tobias, Aufgaben an Sabine 255797 und Tobias 255830 (Matthias nicht mehr).
- **Rationale:** Owner "NUR an tobias und sabine"; er testet kurz mit `--nur-matthias` und stellt zurueck.

### Umfang von "Jetzt pruefen"
- **Choice:** nur freigegebene Projekte (`cfg.test_projekte`, heute HUK-106489), nicht der ganze Typ.
- **Rationale:** Owner-Wahl nach Erklaerung der drei Varianten; HUK-106488 bleibt gesperrt.

### Schalter
- **Choice:** An/Aus des Duplikats bleibt auf der Seite, obwohl er ohne Zeitplan nur Klicks sperrt (Notbremse und Testende).

---

## What Did NOT Work (and why)
- **Erster "Jetzt pruefen"-Rueckleseversuch (R9-Logbuch):** Mein Filter `created > 22:48` verschluckte den Eintrag von 22:47:54; ich meldete kurz "nichts im Logbuch", bis der Lauf in n8n sichtbar war. Zeitfenster vor dem Klick legen, nicht danach.
- **IMAP-Suche `SUBJECT Wimmer`:** fand die R11-Mail nicht, weil der Betreff kein "Wimmer" enthaelt; Suche auf `TEST` umgestellt.
- **Hero-Reiter per API umbenennen oder entfernen:** `update_project_type` kennt keine Schritte (Memory reference_ww_hero_api_quirks); nur im UI.
- **Statusaenderung von HUK-106489 per API statt von Hand:** bewusst nicht gemacht, weil die Aenderung die Workflows ausloest; Owner setzt den Status in Hero.
- **Reiter per JavaScript:** haette beim 3-Sekunden-Refresh zurueckgesprungen; stattdessen `?tab=zeit` serverseitig.
- **Testlauf-Skript `testlauf-duplikat.mjs`:** prueft noch die alte Dreier-Empfaengerliste und verweigert; nicht angefasst (Owner wollte nur die Umstellung).
- **Heredoc mit dreifachen Anfuehrungszeichen in Bash:** vom heredoc-size-gate abgelehnt; Skript als Datei geschrieben.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `agentic-ops/.scratch/ww-sales-72627/tools/startknopf-bauen.mjs` | edited (gitignored) | Seite, Schalter, Schleife, Reiter |
| `agentic-ops/.scratch/ww-sales-72627/tools/duplikat-umbauen.mjs` | edited (gitignored) | Flag `--nur-team` |
| `agentic-ops/workspace/clients/warme-wimmer/infrastructure.yaml` | edited, 69eb8e9 gepusht | Stand 15.10. und Verifikation |
| `agentic-ops/workspace/clients/warme-wimmer/context/drafts/2026-10-15-tobias-sabine-testseite.md` | created (gitignored) | Einladungsmail, Entwurf |
| n8n `t1lRfYjuqU9THsaf` und `tB5anuCbpmYsrA7K` | published | Startseite 34 Knoten; Duplikat 28675485 |
| `memory/project_ww_w214_test_duplicate.md`, `MEMORY.md` | edited | Zustand und Zeigerzeile |
| `memory/feedback_manual_walkthrough_one_step.md` | edited | Ausnahme: ununterbrochene Klicks zusammen, exakte Knopfnamen |

---

## Current Status
HUK-106489 steht auf Abgeschlossen (847265, keine Regel); der erste echte Durchlauf von Tobias und Sabine beginnt mit "Status auf Erstgespraech". Duplikat aktiv, Mails nur an die beiden. Ob die Mail gesendet wurde, ist unbekannt. `platform`: kein Ops-Status (Klon agentic-ops hat kein `status/` fuer WW).

---

## Next Steps
1. Klaeren, ob die Einladungsmail raus ist; dann Text ins `comms-log.md` (Klon agentic-ops), Entwurf loeschen. comms-log endet am 01.10.
2. "Jetzt pruefen" einmal mit echter Kette fahren (mehrere Aktionen, Schleife): nur dieser Pfad ist ungesehen, ebenso R2, R13/R14 und die Mailinhalte M1, M5, M19.
3. Hero-Reiter nach Tobias' PDF: Planung, Angebotserstellung, Abgeschlossen entfernen (Owner im UI); Umsetzung Abschlagsrechnung und Schlussrechnung klaeren.
4. Release 8 am Original (R21 nach 857884), Mo-Fr ab 20:00 Berlin, Trockenlauf mit Pins `2026-10-13-w214-72627-release-auf-12367bfd.json`, Cred `DWE4TI9mE7L9Gsmb`.
5. R17 und R3 Wochenendfaelligkeit mit Tobias besprechen.
6. `testlauf-duplikat.mjs` auf die Zweier-Empfaengerliste anpassen oder bewusst lassen.
7. PR #305 (keine CI-Checks gelistet) mergen oder Stand klaeren; MEMORY.md auf unter 17 KB kuerzen (22,8 KB).
8. Aufraeumen nach der Testphase: beide Workflows deaktivieren, Testtabelle `nnnYVH7709ySG347` loeschen, TEST-Aufgaben auf HUK-106489, Credential `WW Watchdog n8n API` laeuft am 13.12. ab.

---

## Context for Next Session
### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\infrastructure.yaml` (Abschnitt `stand_2026_10_15`)
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\tools\startknopf-bauen.mjs`
- `C:\Users\neuma_p1qrsic\.claude\projects\c--Users-neuma-p1qrsic-Repo-agentic-ops1\memory\project_ww_w214_test_duplicate.md`

### Open Questions
- Ist die Mail an Tobias und Sabine gesendet, und duzt Matthias die beiden?
- Spec a5 von 1-spec nach 3-test? (offen seit 14.10.)
- Welche Reiter sollen aus Hero verschwinden?

### Working Notes
- Start-Link nur in `.scratch/ww-sales-72627/startknopf.json`. Aenderung der Seite: `startknopf-bauen.mjs --apply`; Empfaengerwechsel: `duplikat-umbauen.mjs --tag-sekunden 5 --nur-team|--nur-matthias --apply`, danach Seite neu bauen.
- Rueckleser: `.scratch/ww-sales-72627/tools/hero-snapshot.mjs`; Zeitfenster der Logbuchabfrage vor dem Klick merken.
- Jeder echte Klick auf Seite oder Knopf mailt jetzt Sabine und Tobias; ohne Owner-Wort nicht ausloesen.

### Reference Materials
- Mail-Entwurf: Klon agentic-ops, `workspace/clients/warme-wimmer/context/drafts/2026-10-15-tobias-sabine-testseite.md`
- Vorheriger Checkpoint: `docs/2026-10-14 - WW W2-14 Startknopf und Hero-Reiter/Checkpoint.md`

---

## How to Continue
`/resume warme-wimmer`, dann im Klon `agentic-ops` arbeiten. Zuerst Punkt 1 und 2 der Next Steps.

---

## Strategic Feedback

### What Worked Well This Session
- Ein Schritt, ein Readback: bei 34 Schritten fiel jede Abweichung sofort auf (R9-Logbuch, fehlende Aufgabe, falscher Schalterzustand).
- Die Entscheidung "wen soll der Knopf abdecken" wurde nach Rueckfrage mit klarer Erklaerung getroffen, statt eine Schutzliste aufzuheben.

### Suggestions
- Vor jeder Anleitung, die Knopfnamen nennt, die Seite per `curl` lesen und die Namen woertlich nehmen; zweimal musste Matthias nach "wo" fragen, weil ich die Beschriftung nicht kannte.

### System Health
- Autonomy score: 4 menschliche Eingriffe (zwei abgelehnte Tool-Aufrufe, Wunsch nach exakten Knopfnamen, Wunsch nach gebuendelten Klicks) ohne die Handgriffe in Hero, die der Walkthrough vorsieht.
