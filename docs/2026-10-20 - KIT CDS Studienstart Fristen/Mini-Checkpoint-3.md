# Mini-Checkpoint: KIT CDS Studienstart Fristen

**Date:** 2026-10-20
**Status:** Owner-Studienstart (privat, kein Kunde): HoC-Los beworben, LA-Übungsschein im Campus gewählt, Kalender mit To-dos und Links
**Type:** mini

---

## Summary
Auf Owner-OK pro Aktion: vier HoC-Bewerbungen abgeschickt und dreifach verifiziert, im Campus die LA-I-Übungsschein-Teilleistung gewählt; alle Anmelde- und Frist-Termine im iCloud-Kalender tragen jetzt „Zu tun“ plus Link, sechs neue Termine mit Alarm. Persönliches nur in der Memory `project_kit_studiengangwechsel.md`.

## What Was Done
- Recherche aus Primärquellen: SPZ-Regeln (ein Kurs pro Semester gratis, Englisch nur nach Einstufungstest), Erasmus der Mathe-Fakultät (Bewerbung bis 31.01., Kriterien Schnitt und Mathe-Module des 1. Jahrs), SPO § 16 (ÜQ mind. 6 LP), SoSe-2027-Termine (SLE).
- Kalender: 6 neue Einträge (Tutorien Analysis/LA, Klausuranmeldung, Rückmeldefrist, SPZ/HoC SoSe 2027); 12 Beschreibungen per CalDAV mit If-Match umgeschrieben (nur DESCRIPTION/URL, Alarme erhalten), zurückgelesen.
- SignMeUp (alte Instanz): Login über `/api/user/oidc-login`, Formular `/event/{id}/register`; vier Bewerbungen, Nachweis über „Meine Anmeldungen“, API-Zähler +1, vier Bestätigungsmails.
- Campus: Auswahlseiten nur gelesen, dann genau eine Checkbox per Zeilen-Guard gesetzt und gespeichert; Studienablaufplan zurückgelesen.

## What Did NOT Work (and why)
- **Campus-Auswahlseite per cascampus-URL direkt:** landet im Vorlesungsverzeichnis; nur die Wrapper-Route `registration.php?pguid=…#!campus/student/…` lädt sie, und mehrere `#!`-Ziele in einem Lauf laden nicht neu (alle zeigten die erste Seite).
- **Frame-Suche über die gguid:** traf die Hauptseite, weil die gguid auch im `#!`-Teil steht; erst Filter auf `cascampus.studium.kit.edu` traf den richtigen Frame (Guard brach vorher sicher ab).
- **SignMeUp-Kursliste nach Links durchsuchen:** Zeilen sind keine Anker; Detailroute `/event/{id}` direkt testen.

## Current Status
HoC-Losziehung Fr 23.10. 12:00 ausstehend. Programmieren-Modul (IAM oder Programmieren 1) wartet auf die Owner-Entscheidung nach der SEE-Info 26.10.; Hackathon II zeigt im Campus eine Anmeldefrist 03.11., Eignung fürs 1. Semester unklar (Frage im SEE-Termin).

## Next Steps
1. Nach 23.10. 12:00: HoC-Zusagen aus dem KIT-Postfach lesen und Termine der gezogenen Kurse in den Kalender.
2. Nach SEE-Info: Programmieren-Wahl und ggf. Hackathon II im Campus eintragen (nur mit OK).
3. IAM-Praktikum 26.-28.10. bewerten (Owner oder nach OK); LA-Übungsschein-Anmeldung, sobald angeboten.

## Files to Read First
- Memory `project_kit_studiengangwechsel.md` (Abschnitte vom 20.10.)
- Memory `reference_kit_two_signmeup_instances.md` (SignMeUp-Mechanik)
