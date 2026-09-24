# Checkpoint: KIT Radar und tmbstud-l Austragung

**Date:** 2026-09-24
**Status:** Vorkurs P2 bestätigt und bezahlt; tmbstud-l-Austragung beim Owner beantragt, seither still

---

## Summary

Persönlicher Vorgang (kein Client). Zwei Anläufe: ein Radar-Sweep über
KIT-Postfach, Fristen und Repo, der eine 6-Tage-Frist und eine offene
Matrikelnummer-Frage auflöste; danach die Austragung aus der alten
BauIng-Verteilerliste, bei der der Selbstbedienungsweg eine falsche
Erfolgsmeldung lieferte und erst die Bestätigungsmail den wahren Stand zeigte.

---

## What Was Done This Session

### Radar-Sweep (14.09.)
1. KIT-Postfach, `origin/main` (40+ Commits aus 5 Parallelsessions), offene PRs
   und die Owner-blockierten Status-Elemente über Brisken / Meji / UWI gelesen.
2. MINT-Mathe-Vorkurse A1/A2 gefunden (Frist 20.09., je 30 EUR, am 14.09.
   gestartet) und gegen das CoDaS-Dekanatsschreiben geprüft, das namentlich den
   Fakultäts-Vorkurs ab 12.10. anbietet. Empfehlung: auslassen, angenommen.
3. Wartelistenstand Vorkurs P2 von 16-30 auf **#7** (Kapazität 140 -> 150).
4. Offene Frage geschlossen: es kommt **keine neue Matrikelnummer**, 2726711
   läuft weiter, SignMeUp führt sie mit "CoDaS Bachelor 2025 (1. FS)".
5. EPICUR (Frist 21.09.) als nicht zutreffend ausgeschlossen (ab 2. Studienjahr).

### tmbstud-l-Austragung (14./15.09.)
6. Sympa-Signoff über die Weboberfläche ausgeführt; Banner meldete
   "signoff: action completed".
7. Die Bestätigungsmail widersprach: "Allerdings haben Sie diese Liste nicht
   abonniert." Ursache gefunden: `tmbstud-l` wird aus einer Institutsdatenquelle
   befüllt ("alle aktuellen Vertiefer" des TMB), erscheint deshalb nicht in
   Sympas "My lists" und kennt keinen Selbstbedienungs-Austrag.
8. Zweitadressen-Hypothese ausgeschlossen: 429 Nachrichten-Header gescannt (kein
   Namensalias) und das SCC-Portal bestätigt, dass Aliase Mitarbeitern
   vorbehalten sind. `uonwv@student.kit.edu` ist die einzige Adresse.
9. Austragung beim Listen-Owner beantragt (`tmbstud-l-request@lists.kit.edu`,
   Harald Schneider), kein Bounce, Kopie in "Sent Items" abgelegt.

### Nachkontrolle (24.09.)
10. Seit dem 15.09. **null** TMB-Listenmails. Vorkurs P2 ist durch: Teilnahme
    bestätigt 16.09., Kursstart-Mail von Pascal Zschumme 21.09., ILIAS-Aufnahme
    22.09., Zahlung bestätigt 24.09.

---

## Key Decisions Made

### MINT-Mathe-Vorkurse A1/A2 ausgelassen
- **Choice:** Keine Anmeldung trotz ablaufender Frist.
- **Rationale:** Das Dekanatsschreiben bietet CoDaS namentlich den
  Fakultäts-Vorkurs ab 12.10. an, mit demselben Zweck ("Grundlagen auffrischen,
  erste Kontakte knüpfen"), aber mit der eigenen Kohorte statt 300 MINT-Erstis.

### Austragung über den Owner statt weiter Selbstbedienung
- **Choice:** Mail an `tmbstud-l-request@lists.kit.edu` statt weiterer
  Sympa-Versuche.
- **Rationale:** Die Listenbeschreibung nennt "Loeschung auf Antrag" als den
  vorgesehenen Weg; ein zweiter Signoff hätte dieselbe Fehlmeldung erzeugt.

---

## What Did NOT Work (and why)

- **Sympa-Selbstbedienungs-Signoff:** Die Weboberfläche meldete "signoff: action
  completed", die Bestätigungsmail sagte "Allerdings haben Sie diese Liste nicht
  abonniert". Die Liste hat keine statische Mitgliedschaft, die ein Signoff
  entfernen könnte.
- **Zweitadressen-Suche über Mail-Header:** 429 Header gescannt, kein
  Namensalias gefunden. Der Scan konnte die Frage grundsätzlich nicht
  beantworten, weil Envelope-Empfänger nicht im Header stehen; das SCC-Portal
  hat sie in einem Aufruf beantwortet (Aliase nur für Mitarbeiter).
- **`math.kit.edu/event/vorkurs/de` und `/studium/seite/vorkurs/`:** beide HTTP
  404; die Fakultäts-Vorkurstermine stehen auf keiner erreichbaren Seite,
  sondern nur im PDF-Dekanatsschreiben.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `C:\Users\neuma_p1qrsic\iCloudDrive\Studium\Immatrikulation\DataScience\Studienstart-Plan.md` | updated (2x) | Lage 14.09., Wartelistenstand, Mathe-Vorkurs-Entscheidung, Sympa-Befund, 8 echte Listen-Abos |
| `memory/reference_kit_mail_imap_access.md` | updated | Sympa-Abschnitt: "My lists" ist unvollständig, Owner-Weg, keine Zweitadresse |

---

## Current Status

Vorkurs Informatik P2 ist bestätigt und bezahlt, ILIAS-Kurs beigetreten.
`tmbstud-l` hat seit der Austragungsbitte nicht mehr zugestellt, eine
Owner-Antwort kam aber nicht; die Liste ist verkehrsarm, Stille allein beweist
die Löschung also nicht.

Kein Client und keine Orchestrator-Infrastruktur berührt; ein ops-status
entfällt.

---

## Next Steps

1. KIT-Passwort rotieren und `~/.kit-mail.env` nachziehen. Einziger Restpunkt
   aus dem Behördenvorgang, offen seit dem 28.08.-Checkpoint.
2. Beim nächsten TMB-Mailaufkommen: `listmaster@lists.kit.edu` als Eskalation.
   Ohne neues Aufkommen gilt die Austragung als erfolgt.
3. Neu über `cds-bachelor` am 22.09.: **Institutsvorstellungsmesse 21.10.26** in
   den Studienstart-Plan und in Welle 3 aufnehmen, sie liegt mitten in der
   O-Phase-Woche und versammelt die Institute.
4. Fakultäts-Vorkurs Mathematik 12.-16.10., ohne Anmeldung.

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\iCloudDrive\Studium\Immatrikulation\DataScience\Studienstart-Plan.md`
- `memory/reference_kit_mail_imap_access.md`

### Open Questions
- Hat der TMB-Owner die Löschung tatsächlich vollzogen, oder war die Liste nur
  still? Erst das nächste Listen-Aussenden beantwortet das.

### Working Notes

Die Sympa-Instanz unter `www.lists.kit.edu/sympa` ist die einzige; `lists.kit.edu`
und `/wws` leiten dorthin. Owner-Kontakt einer Liste ist immer
`<liste>-request@lists.kit.edu`. Mit `uonwv@` bestehen 8 statische Abos:
careerservice, cds-bachelor, cert-warnungen, forumnews,
notfall-info-mitarbeiter-und-studierende, notfall-info-studierende, stud_forum,
students.

`mitarbeiter@lists.kit.edu` taucht 36-mal in den Empfängern des Postfachs auf,
ist aber kein Abo: KIT-Rundmails adressieren students@ und mitarbeiter@
gemeinsam, zugestellt wird über students@. Bei solchen Funden also zuerst
prüfen, ob die Adresse nur im To-Header steht.

SMTP-Versand über `smtp.kit.edu` legt nichts in "Sent Items" ab; eine Kopie
muss per IMAP `APPEND` selbst hineingeschrieben werden, damit der Nutzer den
Beleg im eigenen Postfach hat.

### Reference Materials
- Sympa: https://www.lists.kit.edu/sympa (Liste: `/sympa/info/tmbstud-l`)
- Legacy-SignMeUp (Vorkurse): https://signmeup.studium.kit.edu/offer/MINT?group=VK
- SCC-Self-Service: https://my.scc.kit.edu

---

## How to Continue

Postfach über `~/.kit-mail.env` lesen (`iCloudDrive\Studium\tools\kit_mail.py`).
Vorkurs-Stand über die Legacy-SignMeUp-Instanz, alles andere über Campus+.
Termine und Kontakte im `Studienstart-Plan.md` fortschreiben.

---

## Strategic Feedback

### What Worked Well This Session
- Die Erfolgsmeldung der Weboberfläche wurde nicht als Beleg genommen. Genau
  dieser Schritt hat den Fehlschluss "ausgetragen" verhindert; die Wahrheit
  stand nur in der Bestätigungsmail.
- Der Radar-Sweep hat eine Frist gefunden, nach der niemand gefragt hatte, und
  sie mit dem Dekanatsschreiben als Autorität beantwortet statt mit Websuche.

### Suggestions
- Bei einer Identitäts- oder Kontofrage (welche Adressen, welche Konten, welche
  Rollen) zuerst das Verwaltungsportal des Systems fragen, dann erst aus
  Artefakten wie Mail-Headern schließen. Der 429-Header-Scan hier war ein Probe,
  der die Frage konstruktiv nicht beantworten konnte, während das SCC-Portal
  sie in einem Aufruf beantwortet hat.

### System Health
- agent-browser lief über zwei SSO-Anmeldungen (Shibboleth und OIDC mit
  Consent-Screen) stabil; Playwright-MCP war zu Sessionbeginn erneut nicht
  erreichbar.
- Autonomy: 0 human interventions.
