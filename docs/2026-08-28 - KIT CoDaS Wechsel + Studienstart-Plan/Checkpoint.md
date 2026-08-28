# Checkpoint: KIT CoDaS Wechsel + Studienstart-Plan

**Date:** 2026-08-28
**Status:** Exmatrikulationsantrag beim Studierendenservice zur Genehmigung; Immatrikulation offen bis 30.09.2026

---

## Summary

Persönlicher Vorgang (kein Client): Matthias wechselt am KIT von Bauingenieurwesen B.Sc. in Computational and Data Science B.Sc. zum WS 2026/27. Die Session hat die blockierte Exmatrikulations- und Immatrikulationskette entwirrt, die Behörden-Mails entworfen, IMAP-Zugriff auf das KIT-Postfach eingerichtet und daraus einen Termin- und Networking-Plan für den Studienstart gebaut.

---

## What Was Done This Session

### Vorgang entwirrt
1. Kette rekonstruiert: Die Immatrikulation in CoDaS ist durch die fehlende Exmatrikulationsbescheinigung blockiert; die entsteht erst, wenn der Exmatrikulationsantrag im Campus Portal genehmigt ist; der hing an den Entlastungsvermerken.
2. Aus dem Formblatt alle fünf möglichen Stempelstellen enumeriert; nur zwei galten (KIT-Bibliothek, KIT-Card), beide inzwischen erteilt.
3. Geklärt, dass kein NEUER Exmatrikulationsantrag nötig ist: der bestehende steht auf "Antrag online gestellt / Genehmigung ausstehend", der Ablehnungsgrund-Banner ist der gespeicherte Kommentar der letzten Prüfung.
4. Zulassungs- und Gebührenbescheid gelesen und die zwei nicht dokumentenbezogenen Pflichten herausgezogen, die im Portal nirgends als "Fehlt" auftauchen: Semesterbeitrag 184,00 EUR (Verwendungszweck 226206825350) und Meldegrund 10 bei der Krankenkasse.

### Mails entworfen
5. Entwürfe für KIT-Bibliothek, Ausweisbüro und Studierendenservice, über mehrere Runden jeweils an den neuen Sachstand angepasst.

### Postfachzugriff
6. IMAP/SMTP-Zugang zu uonwv@student.kit.edu eingerichtet, Zugangsdaten in `~/.kit-mail.env` (chmod 600, außerhalb des Repos). Verifiziert durch echten Login: 12 Ordner, 395 Nachrichten.
7. Postfach ab April gescannt und die studienrelevanten Funde herausgezogen.

### Studienstart
8. `Studienstart-Plan.md` mit harten Terminen, Kanälen und leerem Kontaktregister angelegt; Networking-Plan über Vorkurs, O-Phase, Lerngruppe, Fachschaft und Hiwi entworfen.

---

## Key Decisions Made

### Postfachzugriff über IMAP statt Browser-Session
- **Choice:** IMAP mit KIT-Passwort in `~/.kit-mail.env`; Lesen autonom, Senden pro Nachricht freigegeben.
- **Rationale:** Der Nutzer hat den Zugang aktiv erteilt, nachdem der Behördenteil im Wesentlichen durch war. Das Passwort ist SSO für die gesamte Uni-Identität, daher Datei außerhalb des Repos und harte Sendesperre.

### Screenshot statt Bescheinigung im Bewerbungsportal
- **Choice:** Der geforderte Nachweis ist ein Screenshot des laufenden Exmatrikulationsantrags, nicht die vorhandene Bescheinigung.
- **Rationale:** SLE hat das in der Nachforderung ausdrücklich so verlangt. Vorteil: die Genehmigung muss nicht abgewartet werden.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `~/.kit-mail.env` | created | KIT IMAP/SMTP Zugangsdaten, chmod 600, nie committen |
| `memory/reference_kit_mail_imap_access.md` | created | Verbindungsdaten und Sendesperre dokumentiert |
| `memory/MEMORY.md` | appended | Indexzeile dazu |
| `iCloudDrive/.../DataScience/Studienstart-Plan.md` | created | Termine, Kanäle, Kontaktregister |
| `iCloudDrive/.../DataScience/Screenshot_Exmatrikulationsantrag_2026-08-19.png` | created | aus der Zwischenablage gezogen, für den Portal-Upload |
| `iCloudDrive/.../DataScience/Einladung-O-Phase.pdf` | created | Anhang aus der Mail extrahiert |
| `iCloudDrive/.../DataScience/Exmatrikulationsbescheinigung (auch mit Verlauf).pdf` | copied | aus Downloads neben die CoDaS-Unterlagen |
| `iCloudDrive/.../Exmatr.BauIng/Entlastungsvermerke_Neumann_2726711_vollstaendig.pdf` | copied | gestempelte Fassung, klar benannt, als Mailanhang |

---

## Current Status

Exmatrikulationsantrag: erfasst 30.03.2026, geändert 13.08.2026, "Antrag online gestellt / Genehmigung ausstehend", Exmatrikulationsdatum 31.03.2026. Im Pflichtfeld hängt noch die unvollständige Formblatt-Fassung mit nur dem Bibliotheksstempel; die vollständige mit beiden Stempeln kann der Nutzer nicht mehr selbst hochladen, sie muss per Mail an den Studierendenservice.

Bewerbung 7833468: HZB und Studienorientierungsverfahren stehen auf OK. Der Baustein Exmatrikulationsbescheinigung trägt fünf Uploads, drei auf "Fehlt" (alte Fehluploads, nicht löschbar) und zwei auf "Nachgereicht".

Kein Client und keine Orchestrator-Infrastruktur berührt; ein ops-status entfällt.

---

## Next Steps

1. Vollständigen Laufzettel per Mail an studserv-team5@sle.kit.edu, weil der Antrag für Uploads gesperrt ist.
2. Screenshot des Antrags im Bewerbungsportal hochladen; die Datei liegt bereit.
3. Semesterbeitrag 184,00 EUR, Verwendungszweck 226206825350, bis 30.09.2026.
4. Meldegrund 10 bei der Krankenkasse anfordern, Zulassungsbescheid als Vorlage.
5. Hiwi-Entscheidung FORUM: Frist war der 06.09.2026, Stand prüfen.
6. KIT-Passwort rotieren, sobald der Vorgang durch ist; danach `~/.kit-mail.env` nachziehen.
7. Nach der Immatrikulation `careerservice` und `students` neu abonnieren.

---

## Context for Next Session

### Files to Read First
- `iCloudDrive/Studium/Immatrikulation/DataScience/Studienstart-Plan.md`
- `memory/reference_kit_mail_imap_access.md`

### Open Questions
- Genügt dem Studierendenservice der Screenshot allein, oder wird nach der Genehmigung noch die neue Bescheinigung verlangt?
- Bleibt das Konto uonwv über den 28.09.2026 hinaus bestehen, wenn die Immatrikulation rechtzeitig gemeldet wird?

### Working Notes

Die harte Klippe ist der 28.09.2026: SCC sperrt das Postfach, Löschung einen Monat später. Die Immatrikulationsfrist ist der 30.09. Laut SCC-Mail unterbleibt die Deaktivierung, wenn der Studierendenservice korrigierte Daten meldet, eine frühe Immatrikulation schützt also das Konto.

Zwei Fehlschlüsse dieser Session, damit sie nicht wiederholt werden. Erstens die Empfehlung, das Exmatrikulationsdatum auf den 30.09.2026 zu setzen, aufgestellt bevor die Unterlagen gelesen waren, die die Exmatrikulation von Amts wegen zum 31.03.2026 belegen. Zweitens die als gesichert vorgetragene Erklärung, die Bescheinigung sei wegen der Zeile "fehlende Rückm./Krankv." abgelehnt worden; die Dateiliste machte danach die schlichtere Erklärung mindestens genauso wahrscheinlich, nämlich dass in dem Baustein einfach falsche Dateien lagen.

Der PowerShell-Tool-Kanal war die ganze Session tot, exit 1 auch bei trivialen Kommandos. Workaround: `powershell.exe` aus dem Bash-Tool mit `MSYS_NO_PATHCONV=1`. So lief auch der Zwischenablage-Grab für den Screenshot.

Das KIT-Passwort steht im Klartext in diesem Transkript, weil es per Screenshot geteilt wurde. Die Rotation steht in den Next Steps.

### Reference Materials
- Bewerbungsportal: https://bewerbung.studium.kit.edu
- Campus Portal: https://campus.studium.kit.edu
- O-Phase: https://o-phase.com, kontakt@o-phase.com
- Fachschaft Mathematik: mathe@fsmi.org, Geb. 20.30 Raum 0.002

---

## How to Continue

Postfach mit `~/.kit-mail.env` über imap.kit.edu:993 lesen, Login mit der vollen Adresse. Den Stand von Exmatrikulationsantrag und Bewerbung aus den Threads mit studserv-team5 ableiten. Termine und Kontakte in `Studienstart-Plan.md` fortschreiben.

---

## Strategic Feedback

### What Worked Well This Session
- Die Enumeration der fünf Stempelstellen aus dem Formblatt hat eine offene Frage in eine abgeschlossene Liste verwandelt und drei unnötige Behördenkontakte gespart.
- Belege statt Vermutungen: Matrikelnummer, IBAN, Verwendungszweck, Fristen und Kontaktnamen stammen alle aus gelesenen Dokumenten oder aus dem Postfach.

### Suggestions
- Bei fremden Vorgängen zuerst den Dateibestand durchsuchen, bevor Handlungsempfehlungen ausgesprochen werden. Der Bescheid über die Exmatrikulation von Amts wegen lag die ganze Zeit auf der Platte und hätte die erste Fehlempfehlung verhindert.

### System Health
- Der PowerShell-Kanal ist in dieser Umgebung unbrauchbar; Bash mit `powershell.exe` ist der verlässliche Weg zu Windows-APIs.
- Autonomy: 3 human interventions.
