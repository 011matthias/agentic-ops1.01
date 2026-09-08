# Improvement prompt (next optimization round)

Vom Owner am 2026-09-08 beauftragt und pastefertig abgenommen. Zugang auf
alles Noetige wurde vorab genehmigt (Web, YouTube, Browser-Automation,
lokale Dateien, DB-Schema, Config, Ship-Chain); Read-only-Hoeflichkeit
gegenueber Vinted bleibt unveraendert. Precondition (erledigt 2026-09-08):
Branch projects/vinted-session-fix ist gemerged.

Die zwei referenzierten WhatsApp-Videos lagen am 2026-09-08 unter
`C:\Users\neuma_p1qrsic\Desktop\Downloads\` - vor dem Lauf pruefen, dass sie
noch existieren.

---

```text
Verbessere die Ergebnisqualität des Vinted-Watchers. Projekt: workspace/projects/vinted-reselling/
(Watcher: watcher/vinted_watcher.py, Config: watcher/searches.yaml, Datenbank: data/vinted.db,
läuft als Windows-Task "VintedWatcher" alle 5 Min). Problem: Die bisherigen Deal-Alerts treffen
nicht — zu viele uninteressante Artikel erreichen mein Handy. Ziel ist Präzision der
Kaufvorschläge, nicht Volumen. Ich genehmige dir vorab Zugang auf alles, was du dafür brauchst
(Web, YouTube, Browser-Automation, lokale Dateien, DB-Schema-Änderungen, Config-Änderungen,
Ship-Chain). Read-only-Höflichkeit gegenüber Vinted bleibt: sanfte Poll-Raten, kein Auto-Kauf,
kein Auto-Listing.

Arbeite die folgenden 8 Punkte ab. Reihenfolge darfst du nach Abhängigkeiten optimieren, aber
alle 8 müssen am Ende umgesetzt oder mit klarer Begründung als blockiert markiert sein.

1) FAKE-ERKENNUNG (höchste Priorität — keine Fakes kaufen)
Baue pro überwachter Marke einen Authentizitäts-Leitfaden auf. Startquellen sind diese YouTube-
Videos; schau sie dir an (Transkript + wo nötig Frames), extrahiere die konkreten Prüfmerkmale
(Etiketten, Nähte, Logos, Stitching, Waschzettel, Seriennummern, RN-Nummern, Hologramme) und
fächere dann selbständig aus: suche pro Marke (Carhartt, Stone Island, Ralph Lauren, The North
Face, Patagonia, Levi's, Nike, Adidas + was in searches.yaml steht) mindestens 2-3 weitere
seriöse Legit-Check-Quellen (YouTube, Legit-Check-Guides, Foren):
https://youtu.be/YpE0oDzFXbE?si=TX9uVIGqeFtjYwTU
https://youtube.com/shorts/_1NtcjZ51Yk?si=lcF3Dl4LHzPB-JGM
https://youtube.com/shorts/S9rdlg5HzCM?si=1wTEZOPzWoGAU7ij
https://youtu.be/GvVH7qDxaoo?si=6ov5HoAaDaLdHC1B
https://youtu.be/3UPj5kUS3zg?si=MxM5jqpnvGNl-ito
https://youtu.be/gPcO1ym6et0?si=uDH1HKFUGe363dOO
https://youtu.be/h-A-lWW934U?si=AAcPvzwi0H7MjKjD
https://youtu.be/pmFNogIcUTQ?si=OSzZtBcaeTLpmYwv
Ergebnis in drei Ebenen:
  a) Pro Marke eine Checkliste als Markdown unter workspace/projects/vinted-reselling/authenticity/
     (menschlich lesbar, für den finalen Kauf-Check am Handy).
  b) Automatisierbare Risiko-Signale in den Watcher einbauen (Fake-Risk-Score pro Listing):
     Preis-zu-gut-um-wahr-Verhältnis, verdächtige Titel-/Beschreibungsmuster, Verkäuferprofil
     (neu, 0 Bewertungen, viele identische Hype-Artikel), Stock-Foto-Verdacht. Score in die DB,
     Alerts ab hoher Fake-Wahrscheinlichkeit unterdrücken bzw. markieren.
  c) Ein halbautomatischer Bildvergleichs-Workflow für alarmierte Artikel: Listing-Fotos per
     Google Lens / Bildersuche gegen Produktfotos echter Ware vergleichen (Browser-Automation wo
     stabil möglich, sonst als dokumentierter 2-Minuten-Handgriff mit vorbereiteten Links im
     Alert). Teste den Workflow an mindestens 3 echten alarmierten Listings und zeige mir die
     Ergebnisse.

2) DATENSAMMLUNG + AUSWAHL-OPTIMIERUNG
Der Bot soll aus Ergebnissen lernen. Baue einen Feedback-Kanal: jeder Alert muss von mir schnell
als gut/schlecht bewertbar sein (z. B. ntfy-Action-Buttons auf einen lokalen Endpoint, oder ein
einfaches Bewertungs-Kommando), Bewertung landet in der DB (alert_feedback). Nutze vorhandene
gone/sold-Daten plus mein Feedback, um die Alert-Kriterien (deal_ratio, min_comps, Klassen- und
Markengewichte) datengestützt nachzuziehen. Wenn genug Outcome-Daten da sind (~2 Wochen, einige
hundert echte gone-Events), bereite die Kalibrierung als /comd_optimize-Lauf mit Offline-
Backtest-Scorer vor (Plan steht in STRATEGY.md und status/watcher.md).

3) GRÖSSENFILTER
Alerts hauptsächlich auf S/M/L beschränken (inkl. äquivalente Zahlengrößen: 36-40 Damen, 46-52
Herren-DE, W29-W34 Jeans) — Ziel ist maximale Wiederverkaufs-Zielgruppe. Als Config in
searches.yaml (size_classes pro Search überschreibbar), nicht hart im Code. Alle Größen weiter
in die DB aufnehmen (Comp-Daten), nur das Alerting filtern.

4) FRAUEN-JEANS
Nimm Damen-Jeans als eigene Searches auf (mindestens: Levi's Damen 501, Agolde, Citizens of
Humanity, Mother, 7 for all mankind — prüfe per Datenlage, welche davon auf Vinted DE genug
Volumen und Nachfrage haben, und passe die Liste an). Größenfokus W26-W31.

5) STANDORT DEUTSCHLAND
Priorisiere Artikel aus Deutschland (Versandkosten minimieren). Enumeriere zuerst live, welche
Länder-/Versandfelder die Catalog-API tatsächlich liefert (user.country, Versandoptionen,
country_id-Parameter — nichts annehmen, API-Antwort lesen). Dann: DE-Artikel bevorzugt alarmieren;
Ausland nur, wenn der Preisvorteil eine konfigurierbare Schwelle überschreitet (Default: mindestens
8 EUR unter DE-Median, damit Versanddifferenz gedeckt ist). Land in die DB.

6) DATENGESTÜTZTE MARKENEINSCHRÄNKUNG
Konzipiere und implementiere Bedingungen, nach denen Marken im Watcher bleiben, fliegen oder
dazukommen. Pro Marke aus der DB berechnen: Angebotsvolumen, Median-Preis, Preisspanne,
Sell-Through-Proxy (gone-Rate + Zeit-bis-gone, sobald vertrauenswürdige Daten da sind),
Alert-Präzision (aus meinem Feedback), Fake-Risiko (aus Punkt 1), Comp-Tiefe (genug
Vergleichsangebote für stabile Mediane). Definiere daraus konkrete Keep/Drop/Add-Regeln mit
Schwellenwerten, dokumentiere sie in status/watcher.md und implementiere einen wöchentlichen
Report (--brand-report), der die Regeln gegen die DB auswertet und Empfehlungen ausgibt.
Entscheidung über tatsächliches Entfernen/Hinzufügen bleibt bei mir.

7) DB-SCHEMA
Erweitere die Datenbank so, dass alle obigen Punkte abgebildet sind: Größenklasse, Land,
Fake-Risk-Score, Alert-Feedback, Marken-Metriken (oder als Views/Abfragen), Herkunft der
gone-Verdicts. Migration in-place (migrate() existiert bereits), niemals die DB löschen — sie
ist das eigentliche Asset. Bestehende Zeilen rückwirkend befüllen, wo ableitbar.

8) HASHTAGS / PRODUKTBESCHREIBUNGEN
Schau dir die zwei lokalen Videos an und extrahiere die Referenz-Erkenntnisse zu Hashtags und
Produktbeschreibungen (Frames + Audio transkribieren):
C:\Users\neuma_p1qrsic\Desktop\Downloads\WhatsApp Video 2026-09-08 at 14.49.25.mp4
C:\Users\neuma_p1qrsic\Desktop\Downloads\WhatsApp Video 2026-09-08 at 14.49.25 (1).mp4
Ergebnis als Referenzdoku unter workspace/projects/vinted-reselling/listing-reference.md:
welche Keywords/Hashtags/Beschreibungsmuster Sichtbarkeit bringen — einerseits für unsere
späteren eigenen Listings, andererseits als zusätzliche Suchbegriffe/Signale für den Watcher,
falls sich daraus bessere Search-Queries ergeben.

VORGEHEN: Erst kurzer Plan mit Reihenfolge und was du pro Punkt konkret baust, dann umsetzen.
Alles Gebaute testen (die bestehende Suite tools/tests/test_vinted_watcher_session.py muss grün
bleiben und für neue Logik erweitert werden), über die normale Ship-Chain mergen und den Task
mit der neuen Version verifizieren. Am Ende: Zusammenfassung was live ist, was es kostet
(zusätzliche Requests/Politeness-Budget) und welche Punkte Daten brauchen, bevor sie greifen.
```
