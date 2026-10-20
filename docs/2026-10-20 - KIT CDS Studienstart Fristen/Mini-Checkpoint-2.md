# Mini-Checkpoint: KIT CDS Studienstart Fristen

**Date:** 2026-10-20
**Status:** Owner-Studienstart (privat, kein Kunde): Fristenliste aus Primärquellen geliefert; Anmeldungen liegen beim Owner
**Type:** mini

---

## Summary
Zwei überholte PDFs gelöscht, die Kopien der zugehörigen Mails auf Owner-Ja entfernt, und eine nach Frist sortierte Liste aller zeitnahen Anmeldungen und Entscheidungen erstellt, jeder Punkt live gegen Mail, ILIAS, Merkblatt, SignMeUp, Campus-Portal oder Fakultätsseite geprüft. Persönliche Details stehen nur in der Memory `project_kit_studiengangwechsel.md` (öffentliches Repo).

## What Was Done
- Zwei PDFs im iCloud-Studienordner gelöscht (vorher/nachher geprüft); zwei Mail-Kopien im Gesendet-Ordner per UID mit Betreff/Datum-Guard nach „Deleted Messages“ verschoben, Rest des Ordners unverändert.
- Fristenliste: SPZ-Los 21.10., HoC-Los 23.10., IAM-Praktikum 26.-28.10., Analysis-Tutorien 27.-29.10., LA-Tutorien erste Woche, BAföG 31.10., dazu Campus-Lücken und Späteres. HoC-Vorschläge per Abgleich aller 119 HoC-Termine gegen den Wochenplan.
- Neue Befunde: SPZ-Sprachkurse laufen ebenfalls per Los (Ziehung 21.10. 12:00); infotut zeigt noch das Sommersemester; im Campus-Studienablaufplan fehlen die LA-Übungsschein-Teilleistung und das IAM-Modul; ILIAS widerspricht sich bei der ersten Analysis-Übung.
- Kalender: Welcome Event 26.10. angelegt (Owner-Wahl), per CalDAV zurückgelesen.
- Memories aktualisiert: HoC/SPZ liegen auf der alten SignMeUp-Instanz mit öffentlicher JSON-API (Korrektur in `reference_kit_two_signmeup_instances.md`).

## What Did NOT Work (and why)
- **Playwright-MCP für den HoC-Katalog:** verbindet sich auf CDP :9222, dort lief kein Browser (ECONNREFUSED); stattdessen Python-Playwright mit eigenem Chrome, darüber die öffentliche SignMeUp-API gefunden.
- **Campus+ SignMeUp und HoC-Katalog per einfachem GET:** reine JS-Apps, liefern nur die Hülle; Daten nur über gerendertes Chrome bzw. `/api/events/public/{id}` der alten Instanz.
- **Welcome-Event-Anmeldeseite lesen:** leitet auf den KIT-IdP-Login; eine Frist ist öffentlich nirgends genannt.
- **Hackathon-Termin 12.-16.04.2027:** weder im öffentlichen SignMeUp-Katalog noch online gefunden; Modul selbst im Campus bestätigt.

## Current Status
Liste beim Owner. Keine Anmeldung, kein Kursbeitritt, kein Campus-Eintrag ausgeführt; alles weitere braucht sein OK pro Aktion.

## Next Steps
1. Owner wählt HoC-Kurse (bis Fr 23.10. 12:00) und IAM-Reihenfolge; Abschicken durch ihn oder nach seinem OK.
2. Campus: LA-Übungsschein als Teilleistung wählen, IAM-Modul unter Informatik prüfen (nur mit OK).
3. Ab 26.10. nachsehen: Link zur Analysis-Tutorienanmeldung in ILIAS, infotut auf WS 26/27, Aufnahme in den GTI-ILIAS-Kurs.

## Files to Read First
- Memory `project_kit_studiengangwechsel.md` (Abschnitt „Fristen-Check 20.10. abends“)
- Memory `reference_kit_two_signmeup_instances.md` (SignMeUp-API)
