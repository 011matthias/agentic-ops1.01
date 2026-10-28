# Checkpoint: BAfoeG Antrag und Nachzahlung

**Date:** 2026-09-24
**Status:** Schreiben ans Amt versendet; Neuantrag WS 2026/27 noch offen

---

## Summary

Personal-Session (kein Client): geklaert, was Matthias fuer den BAfoeG-Antrag zum
CoDaS-Studienstart braucht und ob das jetzt geht, und dabei einen zweiten,
wertvolleren Strang gefunden: der Antrag vom 05.09.2025 ist nie beschieden worden
und deckt rueckwirkend 10/2025 bis 03/2026 ab. Das Schreiben ans Amt ist raus.

---

## What Was Done This Session

### Sachlage rekonstruiert (ohne den Owner zu fragen)
1. Studienverlauf aus der Exmatrikulationsbescheinigung: BauIng 01.10.2025 bis
   31.03.2026, genau **1 Fachsemester**, Exmatrikulationsgrund "fehlende
   Rueckm./Krankv."; CoDaS ab WS 2026/27, Semesterstart 01.10.2026.
2. iCloud-Postfach (10 Ordner) und lokale Platte nach BAfoeG-Spuren durchsucht:
   Antrag **2025-302-1253828-2131865** vom 05.09.2025 per eID gestellt, Nachweise
   am 08.10., 28.10. und 17.11.2025 nachgereicht, **kein Bescheid auffindbar**.
3. BundID-Konto seit 06.08.2025 vorhanden; eigener Mietvertrag (KEMKO,
   gegengezeichnet 06.08.2026) belegt auswaerts wohnend.
4. Dirks Mails vom 01.08. und 21.08.2026 gelesen: 48-Monats-Topf zu 750 EUR,
   BAfoeG mindert die Auszahlung, die Differenz bleibt im Topf. BAfoeG ist fuer
   Matthias damit additiv, nicht neutral.

### Rechtslage im Wortlaut geprueft (B4)
1. **§ 15 Abs. 1 BAföG** traegt die Antragsmonats-Regel, nicht § 15b. Der
   WebFetch-Summarizer behauptete zu § 15b das Gegenteil ("Antragsmonat ist
   irrelevant"); erst der Abgleich mit sw-ka.de und ein Wortlaut-Zitat klaerten es.
2. **§ 7 Abs. 3**: Wechsel nach dem 1. FS, wichtiger Grund wird vermutet.
3. **§ 22**: eigenes Einkommen zaehlt im Bewilligungszeitraum, nicht im Vorjahr.
4. **§ 11 Abs. 4**: anrechenbares Elterneinkommen wird zu gleichen Teilen auf die
   Geschwister in foerderungsfaehiger Ausbildung verteilt.
5. **§ 37 Abs. 2 S. 3 + § 44 SGB X** (anwendbar ueber § 68 Nr. 1 SGB I):
   Zugangsbeweislast bei der Behoerde, Ueberpruefung auch bestandskraeftiger
   Bescheide bis 4 Jahre rueckwirkend.
6. Formblatt-Nummern verifiziert; **FB8 ist Vorausleistung, nicht
   Studienstarthilfe** (Gedaechtnis lag daneben, vor dem Schreiben korrigiert).

### Versendet und abgelegt
1. Mail an `bafoeg@sw-ka.de` (23.09.2026): Sachstand, Bescheidung, hilfsweise
   Ueberpruefungsantrag nach § 44 SGB X, plus Hinweis auf die abweichende
   Anschrift. Kopie in "Sent Messages", kein Bounce.
2. Unterlagenliste fuer Dirk und Criss samt fertiger Mail abgelegt.

---

## Key Decisions Made

### Zwei getrennte Straenge statt einem
- **Choice:** Neuantrag WS 2026/27 und Nachzahlung 2025/26 laufen parallel.
- **Rationale:** Verschiedene Bewilligungszeitraeume, verschiedene
  Einkommensjahre (2024 gegen 2023), verschiedene Verfahren. Sie blockieren
  sich nicht.

### Ein Schreiben fuer alle drei moeglichen Zustaende
- **Choice:** Sachstandsanfrage, Bescheidungsantrag und hilfsweiser § 44 SGB X in
  einem Dokument.
- **Rationale:** Ob nie entschieden, entschieden-aber-nicht-zugestellt oder
  bestandskraeftig ist von aussen nicht erkennbar. Ein Schreiben deckt alle drei,
  statt auf Antwort zu warten und dann nachzulegen.

### Untaetigkeitsklage nicht im ersten Schreiben
- **Choice:** § 75 VwGO nur in der internen Notiz, nicht im Brief.
- **Rationale:** Eskalationsstufe fuer den Fall, dass nach drei Monaten nichts
  kommt; als Drohung im Erstkontakt kontraproduktiv.

---

## What Did NOT Work (and why)

- **Heredoc mit Python-Triple-Quotes:** `heredoc-size-gate` blockte
  `<<PYEOF` mit `BODY = """..."""` (72 Zeilen). Der Shell-Tokenizer bricht an
  verschachtelten Triple-Quotes. Gate hat korrekt gegriffen; Umstieg auf das
  Write-Tool loeste es.
- **Body-Extraktion per sed:** `/^BODY = """$/` matchte nicht, weil der Text in
  derselben Zeile wie die oeffnenden Quotes beginnt. Ergebnis war eine **leere**
  Archivkopie in "Sent Messages". Die Pruefung zaehlte nur Treffer, nicht Inhalt,
  und meldete deshalb Erfolg. Fix: Regex-Extraktion mit `re.S` plus Assertion auf
  "44 SGB X" im Body.
- **`tail -8` auf dem Sendeskript:** Der Traceback des nachgelagerten
  IMAP-APPEND verdraengte die SMTP-Bestaetigungszeile. Der Versand war korrekt,
  aber belegt war er danach nur noch ueber die Ausfuehrungsreihenfolge.
- **WebFetch auf die offizielle Formblatt-Uebersicht:** zweimal 404 bzw.
  ECONNRESET. Ueber Suchergebnisse ersetzt.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `iCloudDrive\Studium\Immatrikulation\BaFÖG\2026-09-23 Sachstandsanfrage Antrag 2025.md` | Created | Schreiben ans Amt plus Rechtsgrundlagen; als GESENDET markiert |
| `iCloudDrive\Studium\Immatrikulation\BaFÖG\2026-09-23 Unterlagen von Dirk und Criss.md` | Created | Unterlagenliste plus fertige, ungesendete Mail an die Eltern |
| `memory\project_bafoeg_antrag_ws2026.md` | Created | Projektgedaechtnis: Infrastruktur, drei Stellschrauben, beide Straenge |
| `memory\MEMORY.md` | Edited | Indexzeile |

---

## Current Status

Kein Client beruehrt, keine Ops-Status-Zeile. Der Brief ans Amt ist zugestellt
(SMTP angenommen, kein Bounce); die Antwort steht aus. Der Neuantrag fuer
WS 2026/27 ist noch **nicht** gestellt: es fehlen Dirks und Criss' Zahlen sowie
Matthias' eigene Einkommensprognose. Die Mail an die Eltern liegt fertig, aber
ungesendet, weil eine Vorfrage offen ist.

---

## Next Steps

1. **Vorfrage klaeren:** Ist Criss leibliche bzw. Adoptivmutter? Nur deren
   Einkommen zaehlt (§ 11 Abs. 2); ein Stiefelternteil bleibt aussen vor. Davon
   haengt ab, wer ueberhaupt Formblatt 3 ausfuellt.
2. Nach der Antwort die Eltern-Mail senden (gated).
3. Owner prueft "Mein Bereich" auf bafoeg-digital.de (braucht seine eID).
4. Neuantrag WS 2026/27 bis **spaetestens Ende Oktober** stellen, sonst faellt
   der Oktober weg. Notfalls formloser Fristwahrungs-Antrag an bafoeg@sw-ka.de.
5. Aktuelle Immatrikulationsbescheinigungen von Arthur und Nico fuer WS 2026/27
   besorgen (§ 11 Abs. 4, senkt den Anrechnungsanteil).
6. Antwort des Amts abwarten; bleibt sie drei Monate aus, ist § 75 VwGO dran.

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\iCloudDrive\Studium\Immatrikulation\BaFÖG\2026-09-23 Unterlagen von Dirk und Criss.md`
- `C:\Users\neuma_p1qrsic\iCloudDrive\Studium\Immatrikulation\BaFÖG\2026-09-23 Sachstandsanfrage Antrag 2025.md`
- `memory\project_bafoeg_antrag_ws2026.md`

### Open Questions
- Ist Criss rechtlicher Elternteil? (blockiert die Eltern-Mail)
- Wurde der Antrag von 2025 je beschieden, und wohin ging die Post?
- Wie hoch ist Matthias' prognostiziertes Honorar 10/2026 bis 09/2027? Das ist
  die Groesse, die den Anspruch auf null bringen kann.
- Ist er noch familienversichert? Entscheidet ueber 855 gegen 992 EUR Bedarf.

### Working Notes
Bedarf: 475 Grundbedarf plus 380 Wohnpauschale gleich 855 EUR; KV/PV-Zuschlag
137 EUR nur ohne Familienversicherung. Keine Satzerhoehung zum WS 2026/27, erst
zum 01.04.2027. Elternfreibetrag 2.540 EUR bei zusammenlebenden Eltern, dazu 50 %
des Rests. Anrechnungsfrei beim eigenen Einkommen rund 603 EUR/Monat ab 01/2026.
Familienadressen: Dirk `dirk.neumann@gtgroup.com`, Criss
`cavalcanticris@hotmail.com`, Nicolas `neumann.nicolas@outlook.com`, Arthur
`art.neumann@outlook.com`. Aktuelle Anschrift Georg-Friedrich-Strasse 18, 76131
Karlsruhe; die alte Ludwig-Marum-Strasse widerspricht sich zwischen KIT-Bescheid
(21) und Mietvertrag (2), was den verschwundenen Bescheid erklaeren koennte.

### Reference Materials
- Studierendenwerk Karlsruhe: Adenauerring 7, `bafoeg@sw-ka.de`, 0721 6909-177,
  Bearbeitung 2 bis 3 Monate
- `bafoeg-digital.de` (BundID vorhanden), Antrags-ID 2025-302-1253828-2131865
- gesetze-im-internet.de: § 15, § 11, § 22 BAföG; § 37, § 44 SGB X; § 68 SGB I

---

## How to Continue

Zuerst die Criss-Frage stellen, dann die fertige Eltern-Mail senden. Parallel den
Neuantrag in BAfoeG Digital starten, damit die Oktober-Kante haelt, auch wenn die
Elternzahlen noch fehlen; Nachweise lassen sich nachreichen.

---

## Strategic Feedback

### What Worked Well This Session
- Den Wortlaut zu holen statt der Zusammenfassung zu trauen: Der Summarizer
  behauptete zu § 15b, der Antragsmonat sei irrelevant, was der Aussage des
  Studierendenwerks widersprach. Der Widerspruch war das Signal, und das
  Wortlaut-Zitat fand die richtige Norm (§ 15 Abs. 1). Dieselbe Disziplin fing
  den Formblatt-8-Irrtum ab.
- Die Praemisse des Owners geprueft statt uebernommen: "ich hatte Anspruch" traegt
  juristisch nicht, "ich habe am 05.09.2025 fristgerecht beantragt" schon. Die
  staerkere Begruendung lag in seinem eigenen Postfach.
- Den Adresskonflikt vor dem Senden gefunden, statt den Brief an eine Anschrift zu
  schicken, an der schon einmal Post verlorenging.

### Suggestions
- Bei einem irreversiblen Send (Mail an eine Behoerde, Zahlung, Publish) nie durch
  `tail` pipen. Die Bestaetigungszeile ist der Beleg; verdeckt sie ein Traceback
  aus einem nachgelagerten Schritt, bleibt nur der Rueckschluss ueber die
  Ausfuehrungsreihenfolge. Skript so bauen, dass der Sendebeleg zuletzt gedruckt
  wird, oder ungefiltert lesen.

### System Health
- Die B4-Disziplin trug diese Session fast allein: sechs Normen und eine
  Formblatt-Liste im Wortlaut geprueft, zwei Fehler davon abgefangen, bevor sie in
  ein Behoerdenschreiben gerieten.
- Autonomy: 2 human interventions (Anschrift nachgereicht, Sendefreigabe).
