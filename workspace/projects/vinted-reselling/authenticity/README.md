# Echtheits-Check: Leitfäden und Routine

Zwölf markenspezifische Prüflisten für den Moment vor dem Kauf, plus die
Bildvergleichs-Routine. Alles auf ein Handy ausgelegt: du hast die
Anzeigenfotos, vielleicht eine Rückfrage an den Verkäufer, und zwei
Minuten Zeit.

| Marke | Datei | Quellenlage |
|---|---|---|
| Carhartt / Carhartt WIP | [carhartt.md](carhartt.md) | mittel |
| Stone Island | [stone-island.md](stone-island.md) | gut |
| Ralph Lauren | [ralph-lauren.md](ralph-lauren.md) | mittel |
| The North Face | [the-north-face.md](the-north-face.md) | mittel |
| Patagonia | [patagonia.md](patagonia.md) | mittel |
| Levi's | [levis.md](levis.md) | gut |
| Nike | [nike.md](nike.md) | mittel |
| Adidas | [adidas.md](adidas.md) | mittel |
| AGOLDE | [agolde.md](agolde.md) | dünn |
| Citizens of Humanity | [citizens-of-humanity.md](citizens-of-humanity.md) | mittel |
| MOTHER Denim | [mother.md](mother.md) | mittel |
| 7 For All Mankind | [7-for-all-mankind.md](7-for-all-mankind.md) | mittel |

Die Dateinamen entsprechen den `brand_norm`-Schlüsseln des Watchers, ein
Alert lässt sich also direkt auf seinen Leitfaden abbilden.

## Wie die Leitfäden entstanden sind, und was das für ihr Gewicht heißt

Basis waren die acht vom Owner gelieferten Videos. Die haben sich beim
Auswerten als überwiegend **markenübergreifend** herausgestellt (Vinted
allgemein, Verkäuferprofile, Trikots), nicht als Marken-Legit-Checks.
Sie liefern deshalb die generische Ebene: Verkäufersignale, Preissignale,
Foto-Heuristiken. Die markenspezifische Tiefe kommt aus je zwei bis drei
zusätzlich recherchierten Quellen pro Marke.

Zwei Regeln halten die Leitfäden ehrlich:

- **Cross-Confirmation.** Ein Prüfmerkmal gilt nur als *bestätigt*, wenn
  mindestens zwei unabhängige Quellen es nennen. Sonst steht es drin mit
  dem Zusatz *unbestätigt, 1 Quelle*. Beides bleibt sichtbar, damit du
  weißt, worauf du dich stützt.
- **Ära-Scope.** Label-Generationen unterscheiden sich stark. Jeder
  Checkpoint nennt seinen Zeitraum oder sagt *Ära unklar*. Ein Merkmal,
  das bei aktueller Ware stimmt, ist bei einem 90er-Teil oft schlicht
  falsch.

Jeder Leitfaden lief zusätzlich durch eine unabhängige Gegenprüfung, die
gezielt nach Fehlern gesucht hat (RN-Nummern gegen die FTC-Datenbank,
Jahreszahlen, Modellnamen, und vor allem nach absoluten Aussagen).
Gefundene Widersprüche stehen am Ende der jeweiligen Datei unter
*Gegengeprüft*. Bei elf von zwölf Marken gab es Treffer, was die Regel
unten erklärt.

## Die wichtigste Regel

**Kein einzelnes Merkmal beweist Echtheit.** Fälscher kopieren Labels,
Nähte und sogar Zertifikatscodes inzwischen sehr gut. Jede Aussage der
Form "wenn X stimmt, ist es echt" ist praktisch immer falsch. Umgekehrt
gilt sie schon eher: ein klarer Fehler bei einem gut dokumentierten
Merkmal ist ein Ausschlussgrund.

Das gilt ausdrücklich auch für Certilogo bei Stone Island: ganze
Fälschungschargen tragen denselben gültigen Code und scannen anfangs als
echt.

## Der 2-Minuten-Bildvergleich

Jeder Alert trägt einen Google-Lens-Link direkt in der Nachricht. Für
eine Anzeige, die schon in der Datenbank steht:

```
uv run watcher/vinted_watcher.py --image-check <listing-id>
```

Das druckt Marke, Preis, Fake-Risiko und drei Links: Google Lens, Bing
Visual Search und Yandex. Keine Browser-Automation, weil Lens keine API
hat und die Oberfläche an Zustimmungsdialogen zerbricht; ein Deep-Link,
den das Handy direkt öffnet, funktioniert dagegen immer.

Die Routine:

1. **Lens-Link antippen.** Vergleiche die visuell ähnlichen Treffer mit
   dem Angebot. Suchst du nach dem echten Produkt, filtere auf
   Händlerseiten und die Marke selbst.
2. **Modell benennen.** Findest du das exakte Modell inklusive Farbe? Ein
   Teil, das es so nie gab, ist erledigt. Ein Teil, das nur auf
   Fälschungsmarktplätzen auftaucht, ebenfalls.
3. **Fotoherkunft prüfen.** Tauchen genau diese Fotos woanders auf, sind
   es geklaute Bilder, unabhängig von der Echtheit der Ware.
4. **Leitfaden öffnen**, den 60-Sekunden-Check durchgehen.
5. **Nachfragen**, wenn ein Merkmal auf den Fotos nicht zu sehen ist. Der
   Abschnitt *Beim Verkäufer nachfragen* jedes Leitfadens hat die
   passenden Fragen. Ein Verkäufer, der ein Foto vom Waschzettel
   verweigert, hat dir gerade geantwortet.

Wenn der Lens-Link nichts hergibt (die Fotos sind zu unscharf, das ist
häufig), nimm Bing oder Yandex; Yandex ist bei Kleidung oft der stärkste.

## Abnahmetest der Routine, 2026-09-08

Drei echte Alerts von diesem Nachmittag, absichtlich über drei Marken und
drei Risikoklassen. Jeweils der Weg, den du am Handy gehen würdest.

| Listing | Anzeigentitel | Preis | Ergebnis der Bildsuche |
|---|---|---|---|
| 9932723613 | "Veste stone Islande magnifique et intemporelle" | 42,70 € | Bing: **Stone Island Zip-Up Hoodie**. Warenart und Marke bestätigt, Modelltyp präzisiert. |
| 9932759269 | "Polo Ralph Lauren Pullover" | 19,60 € | Yandex: **polo ralph lauren bear**, "джемпер polo ralph lauren с медведем". Der Titel verschweigt die Linie. |
| 9932717176 | "Levi's Jeans 501" | 13,30 € | Yandex: nur "джинсы мужской", "джинсы широкие". Warenart bestätigt, **501 nicht bestätigt**. |

Was die drei Fälle zeigen:

**Der Ralph-Lauren-Treffer ist der Grund, warum sich der Handgriff lohnt.**
Die Anzeige sagt "Pullover", die Bildsuche sagt Polo Bear. Das ist eine
deutlich wertvollere Linie, und gleichzeitig eine der am häufigsten
gefälschten. Beides ändert die Kaufentscheidung, und beides stand nicht im
Titel.

**Der Levi's-Fall ist ein Ergebnis, kein Fehlschlag.** Dass die Bildsuche nur
"Jeans" sagt und die 501 nicht bestätigt, heißt: die Fotos zeigen die
unterscheidenden Merkmale nicht. Das ist genau der Moment für die Rückfrage
aus [levis.md](levis.md) (Red Tab, Waschzettel, Lederpatch), nicht der Moment
zum Kaufen.

### Welcher Dienst wofür

- **Yandex ist bei Kleidung der stärkste.** Er benennt Modelllinien, wo die
  anderen bei der Warengattung bleiben. Sprache der Treffer ist oft Russisch;
  das stört nicht, die Markennamen stehen lateinisch drin.
- **Bing** liefert saubere Produktnamen und funktioniert zuverlässig.
- **Google Lens** verarbeitet das Vinted-Bild korrekt (im Test hat Lens die
  Bildmaße 600x800 aus der URL gelesen), zeigte dem automatisierten Browser
  danach aber einen Bot-Check. **Am Handy tritt das nicht auf**, dort ist Lens
  weiterhin die beste erste Wahl. Verifiziert ist damit, dass der Link gültig
  ist und Lens das Bild annimmt; das Endergebnis konnte aus der Automatisierung
  heraus nicht abgerufen werden.

Reihenfolge im Alert bleibt deshalb Lens zuerst; wenn er zickt, Yandex.

## Was der Watcher automatisch prüft

Der Fake-Risk-Score im Alert deckt die Signale ab, die aus den Daten
lesbar sind, und nur die:

| Signal | Was es bedeutet |
|---|---|
| Preis unter 25 bzw. 15 Prozent des Medians | zu gut, um wahr zu sein |
| Titelmarker (1:1, AAA, replica, mirror, dhgate ...) | Verkäufer sagt es selbst |
| Emoji-Spam im Titel | Massen-Reseller-Muster |
| Hype-Marke sehr billig | dort lohnt sich Fälschen |
| Identischer Titel bei mehreren Verkäufern | Stockfoto-Verdacht |
| Verkäufer ohne Bewertungen, Hype-Marke, billig | das klassische Muster |
| Schlechte Verkäuferreputation bei genug Bewertungen | dokumentierte Enttäuschungen |

Ab 40 Prozent trägt der Alert eine Warnzeile, ab 70 Prozent kommt er gar
nicht erst an. Was der Score **nicht** kann: Nähte, Etiketten,
Stickereien beurteilen. Dafür sind die Leitfäden da, und die brauchen
deine Augen.

Bewusst nicht eingebaut ist eine Bildanalyse im Watcher. Sie würde das
Anfragebudget gegenüber Vinted vervielfachen für ein schwaches Signal,
und der Bildvergleich mit einem Menschen davor ist ohnehin besser.
