# Mini-Checkpoint: KIT CDS Studienstart Fristen

**Date:** 2026-10-20
**Status:** Owner-Studienstart (privat, kein Kunde): Stundenplan, ILIAS und Fristen eingerichtet; nächster Schritt in neuem Chat
**Type:** mini

---

## Summary
Für den Studienstart Computational and Data Science (KIT, WS 26/27) ist der Stundenplan im iCloud-Kalender „KIT“ angelegt und an die ILIAS-Kursnachrichten angepasst; Fristen und Klausuren stehen dort mit Erinnerung. Persönliche Details liegen bewusst nur in der Memory `project_kit_studiengangwechsel.md` (öffentliches Repo).

## What Was Done
- 10 wöchentliche Lehrveranstaltungs-Serien per CalDAV angelegt; Lineare Algebra auf Owner-Entscheid auf die Informatik-Variante umgestellt (MHB: für CDS vorausgewählt).
- Prüfungsordnung, Modulhandbuch, ZIO und BAföG-Normen im Wortlaut geprüft; 5-seitiger Überblick und korrigierter Stundenplan als PDF an das iPhone-Postfach des Owners (je mit OK).
- Owner-Notizen aus der Fachbereichsinfo (Mail-PDF) plus ILIAS-Kursseiten und Merkblätter eingearbeitet: Analysis-Tests, abgesagte erste Termine, Praktikums- und Losverfahren-Fristen, drei Klausurtermine.
- ILIAS: drei Kursen beigetreten (Owner-OK), Mitgliedschaft per Dashboard zurückgelesen; Lesewerkzeug `kit_ilias.py course` schickte unbemerkt Formulare ab, jetzt rein lesend.

## What Did NOT Work (and why)
- **EXDATE auf die erste Instanz einer Serie (iCloud):** der Server-Expand zeigte den abgesagten ersten Termin weiter, obwohl EXDATE gespeichert war; Lösung: DTSTART auf das nächste echte Datum verschieben (Memory `reference_icloud_mail_imap_access.md`).
- **`kit_ilias.py course` auf nicht beigetretenen Kursen:** `accept_agreement` postete das Beitritts-Formular mit `cmd[save]`; wirkungslos (zurückgelesen), aber ein Lesewerkzeug mit Schreibpfad. Behoben: `course()` nur noch GET.
- **„pastaplace“ (Altklausuren) per Websuche:** kein Treffer; Fachschaft FSMI als Ersatzquelle genannt.

## Current Status
Kalender und ILIAS stimmen mit den Kursseiten vom 20.10. überein. Owner will die Stundenplan- und Fokus-PDFs löschen und eine Liste aller zeitnahen Anmeldungen und Entscheidungen; dafür liegt ein Fortsetzungs-Prompt vor (Chat-Antwort dieses Checkpoints).

## Next Steps
1. Neuer Chat mit dem Fortsetzungs-Prompt: zwei PDFs löschen, dann Anmelde- und Entscheidungsliste mit Fristen aus Primärquellen.
2. Offene Quellen nachziehen: Analysis-Klausurtermin und Tutorien-Einteilung, ILIAS-Aufnahme Theoretische Informatik, LA-Übungszeit (VVZ 11:30 gegen Merkblatt 12:30).

## Files to Read First
- Memory `project_kit_studiengangwechsel.md` (Stand, Kurs-IDs, Fristen)
- Memory `reference_icloud_mail_imap_access.md` (CalDAV, EXDATE-Falle)
- `C:\Users\neuma_p1qrsic\iCloudDrive\Studium\tools\kit_ilias.py`, `kit_campus.py` (Werkzeuge, außerhalb des Repos)
