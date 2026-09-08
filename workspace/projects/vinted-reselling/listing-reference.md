# Listing-Referenz: Titel, Beschreibung, Keywords auf Vinted

Stand 2026-09-08. Quellen: zwei vom Owner gelieferte TikTok-Videos
(lokal transkribiert und Frame-für-Frame ausgelesen), die Vinted-Hilfe
und Katalogregeln als Primärquelle, plus eine Live-Untersuchung des im
Video beworbenen Tools vintagezai.com.

Dieses Dokument hat zwei Adressaten: unsere eigenen künftigen Anzeigen,
und die Frage, ob sich daraus bessere Suchbegriffe für den Watcher
ergeben.

## Die Kernkorrektur vorweg

Hashtags auf Vinted **existieren**, sind aber etwas anderes als auf
Instagram oder TikTok, und ihr Nutzen ist klein bei konkretem Risiko.

Was stimmt, jeweils selbst geprüft am 2026-09-08:

- **Es gibt keine Tag-Seite.** `vinted.de/hashtag/<wort>`,
  `vinted.com/hashtag/<wort>` und `vinted.de/tag/<wort>` antworten alle
  mit **404**. Kein eigener Feed, kein Tag-Index.
- **Aber Vinted verlinkt Hashtags trotzdem.** Im ausgelieferten HTML
  einer Anzeige wird jeder Tag zu einem Anker auf die normale Suche:
  `<a href="/catalog?search_text=%23jeudesociete">#jeudesociete</a>`.
  Verifiziert auf vinted.fr und vinted.de. Ein Hashtag ist also
  **verlinkte Kurzschrift für eine Volltextsuche nach dem Literal
  `#tag`**, kein eigener Index. Wer behauptet, die Raute sei reine
  Dekoration, liegt falsch.
- **Die Beschreibung wird durchsucht.**
  [help/409](https://www.vinted.de/help/409) nennt
  "Artikelbeschreibungen" als Ranking-Parameter, und zwei unabhängige
  Tests bestätigen es: eine Suche findet ein Listing über ein Wort, das
  ausschließlich in dessen Beschreibung steht.
- **Die Raute ist kein reiner No-op.** Bei einem *einzigartigen* Token
  (ein persönlicher Sortier-Tag) grenzt sie das Ergebnis präzise ein;
  bei einem Alltagswort sind Suche mit und ohne Raute praktisch gleich.

Was daraus folgt: Der reale Nutzen von Hashtags ist die
**Selbstsortierung eines großen eigenen Kleiderschranks** (Käufer klickt
`#meinname_gr38` und sieht alle passenden Teile des Verkäufers), nicht
zusätzliche Reichweite. Alle glaubwürdigen "hilft mir"-Berichte aus der
französischen, deutschen und englischen Community beschreiben genau
diesen Fall. Für neue Reichweite trägt das **Wort**, nicht das Zeichen
davor.

Dazu kommt: Sortier-Hashtags sind unzuverlässig. Französische Verkäufer
melden wiederholt, dass die Hashtag-Suche ausfällt (Dez 2024, Apr bis Jun
2025, Feb 2026, Apr 2026); Vinted behandelt das als Bug, was nebenbei
bestätigt, dass die Verlinkung beabsichtigt ist.

**Die eigentliche Falle liegt aber tiefer:** Das Risiko hängt nicht an
der Raute, sondern an der *Irrelevanz*.
[catalog-rules](https://www.vinted.de/catalog-rules) verbietet fremde
Marken formatunabhängig, "im Markenfeld, im Titel, in der
Artikelbeschreibung und/oder in den Hashtags". Wer aus einem
Hashtag-Block nur die Rauten entfernt und `nike adidas` als Klartext
stehen lässt, hat einen Hashtag-Verstoß in einen Beschreibungs-Verstoß
umgewandelt. Das Wort muss weg, nicht das Zeichen.

Belege, wörtlich:

> "Nenne in deiner Beschreibung keine anderen Markennamen oder Hashtags
> als die, die du im Markenfeld ausgewählt hast. Gemäß unseren
> Katalogregeln müssen wir Artikel verstecken oder löschen, falls sich
> in ihrer Beschreibung irrelevante Markennamen befinden."
> ([help/49](https://www.vinted.de/help/49))

> "Angaben zu Preis, Zustand, Größe oder die Hashtags sind ungenau,
> unklar oder bewusst irreführend. Zum Beispiel: es werden mehrere
> (nicht zugehörige) Markennamen in einem Angebot genannt / es werden
> besonders viele oder nicht zugehörige Hashtags verwendet"
> ([help/62](https://www.vinted.de/help/62))

Und die Kostenseite: wird ein Artikel deswegen versteckt, werden bezahlte
Pushes und Vitrinen **nicht erstattet** (help/62).

## Was in den beiden Videos tatsächlich gezeigt wird

### Video 1 (@teo.resellt.immer, 42s)

Gesprochen: zwei Tipps gegen schlechte Views. Erstens Keywords und
Hashtags, "damit kannst du ziemlich gut lenken, wem der Artikel angezeigt
wird", mit der Warnung, nicht wahllos zu taggen, weil man sonst in der
falschen Zielgruppe landet. Zweitens ein Shadowban-Trick: einen sehr
guten Artikel sehr billig einstellen, um Traffic auf den Account zu
ziehen.

Am Bildschirm (Frames 19 bis 24) läuft die Chrome-Erweiterung
**VintagezAI**, die aus einem Foto Titel, Beschreibung, Hashtags,
Preisvorschlag und Kategorie erzeugt und per Autofill in
`vinted.de/items/new` überträgt. Der übertragene Block enthält
**27 Hashtags im Beschreibungsfeld**, der Titel bleibt hashtagfrei.

Der aufschlussreichste Teil ist ein Fehler im Beispiel selbst: Der
Artikel ist eine Polo-Ralph-Lauren-Sweatjacke, die letzten fünf Tags
lauten `#vintagesergio #vintagesergiotacchini #sergio #tracksuit
#vintagetrack`. Das ist genau der Tatbestand aus help/49.

Der zweite Tipp (Shadowban) ist unbelegt. Vinted dokumentiert keine
Shadowban-Schwellen; help/409 dokumentiert dagegen, dass Massen-Uploads
proportional gedrosselt werden, und dass neue Verkäufer einen
Sichtbarkeitsbonus bekommen. Wir übernehmen den Trick nicht.

### Video 2 (@vintify.selling, 35s)

Der brauchbarere der beiden. Zeigt Segment für Segment (roter Marker) den
Aufbau eines Titels an einem eigenen, live stehenden Listing:

```
Polo Ralph Lauren Poloshirt | Rosa Hellblau | Preppy Vintage Style | Gr. M
```

| Position | Segment | Inhalt |
|---|---|---|
| 1 | `Polo Ralph Lauren Poloshirt` | Marke plus Artikelart |
| 2 | `Rosa Hellblau` | Farben, ein Segment, ohne Komma |
| 3 | `Preppy Vintage Style` | Stil |
| 4 | `Gr. M` | Größe |

Begründung im Video: "Der Algorithmus kann so deinen Artikel in die
richtige Kategorie stecken, und er wird nur den Leuten angezeigt, die
wirklich danach suchen." Keine Hashtags im ganzen Video.

Das deckt sich mit dem, was Vinted selbst dokumentiert, und ist die
Formel, an der wir uns orientieren.

## Was wirklich Sichtbarkeit steuert

Aus [help/409](https://www.vinted.de/help/409), wörtlich:

> "Die wichtigsten Parameter sind: die Filter, die Mitglieder anwenden
> und die Filter, die unser System anwendet. Sobald gefiltert wurde,
> ordnet unser System die Angebote nach Relevanz."

**Erst Filter, dann Ranking.** Das ist der meistunterschätzte Hebel.
Filter lesen ausschließlich die strukturierten Katalogfelder, niemals den
Fließtext. Ein leeres oder falsches Feld bei Kategorie, Marke, Größe,
Farbe oder Material nimmt den Artikel aus der gefilterten Suche heraus,
egal wie gut der Titel formuliert ist.

Zusatzbefund aus dem Test: das **Markenfeld ist eigenständig
durchsuchbar**. Ein Artikel mit dem Titel "Babyschuhe" und der Marke
"Sterntaler" erscheint bei der Freitextsuche nach "Sterntaler", obwohl
das Wort weder im Titel noch in der Beschreibung steht. Die Marke im
Titel zu wiederholen ist also nicht das, was auffindbar macht.

Dokumentierte Ranking-Parameter, absteigend nach dem, was wir
beeinflussen können:

| Parameter | Was es für uns heißt |
|---|---|
| Filter (Nutzer + System) | Alle strukturierten Felder befüllen. Hartes Tor. |
| Artikel-Ontologie | Kategorie, Marke, Größe, Farbe, Fotos, Attribute |
| Artikelbeschreibung | Relevanz zur Suchanfrage; hier wirken Keywords |
| Zeit seit Upload | Neue Angebote werden gefördert |
| Interaktionen | Impressions, Favoriten, Klicks |
| Preis | Bessere Deals werden bevorzugt |
| Listing-Frequenz | Massen-Uploads werden gedrosselt: über den Tag verteilen |
| Nutzerhistorie | Neue Verkäufer bekommen einen Bonus |

Nicht belegt und als Folklore einzustufen: optimale Upload-Uhrzeit
(Sekundärquellen widersprechen sich direkt), Shadowban-Schwellen, und die
kursierenden Fotostatistiken.

Technischer Hinweis mit Konsequenz: Vinted ist 2024 von Elasticsearch auf
Vespa migriert und hat 2025 embedding-basiertes Dense Retrieval
ausgerollt ([vinted.engineering](https://vinted.engineering/2024/09/05/goodbye-elasticsearch-hello-vespa/)).
Semantisches Matching heißt, exaktes Keyword-Stopfen hat weniger Hebel
als die Ratgeber annehmen, korrekte strukturierte Attribute mehr. Ein
Ratgeber, der noch vom reinen Stichwort-Index ausgeht, ist veraltet.

## Das Tool aus dem Video, live geprüft

vintagezai.com, gestartet am 19.07.2026, Anbieter Teo Graf, Hamburg. Vier
damit erzeugte Listings waren live auffindbar. Was die Prüfung ergab:

- **Die Tags sind markenweit, nicht artikelspezifisch.** Ein live
  stehendes **Tank Top** trägt exakt denselben 22er-Block wie die
  **Zip-Jacke** aus dem Werbe-Screenshot des Anbieters, inklusive
  `#lonsdalejacke`, `#trackjacket`, `#trainingsjacke`. Die Startseite
  verspricht "auf den Artikel angepasste Hashtags"; im Feld ist das nicht
  nachweisbar.
- **Fremdmarken-Kontamination ist systematisch:** Nike und Adidas auf
  Lonsdale-Ware, `#nikevintage` auf einem Adidas-Trainingsanzug.
- **Dubletten und Tippfehler:** `#adidas` zweimal im selben Block,
  `#niktracksuit` als Vertipper.
- **Material und Maße fehlen komplett** — beides sind die häufigsten
  Käuferrückfragen, und Material ist ein strukturiertes Filterfeld.
- Fehlerhafte Template-Slots: `Condition: Neu/10`, und bei einem
  Zweiteiler `Size: S Hose &M Anzug`.
- Der Anbieter schreibt auf der Startseite, ein Bann sei "quasi
  unmöglich", und in den eigenen AGB §3(3), dass die Nutzung gegen die
  AGB von Vinted verstoßen kann und er für Sperrungen nicht haftet.

Brauchbar als Vorlage sind die Titel-Formel und die Idee der gestuften
Preisermittlung. Die Keyword-Mechanik ist eher eine Warnung als ein
Vorbild.

Methodischer Vorbehalt: alle vier gefundenen Listings stammen aus einem
einzigen Verkäufer-Closet, das Tool hat sehr geringe Verbreitung. Dass
der Block byte-identisch mit dem Anbieter-Screenshot ist, spricht für den
Generator, beweist aber nicht, dass nicht der Verkäufer manuell kopiert
hat.

## Unser Standard

### Titel

```
{Marke} {Modell?} {Typ} | {Schnitt oder Stil-Detail} | {Farbe} | Gr. {Größe}
```

Rund 70 Zeichen, Marke zuerst, eine Sprache, eine Größenschreibweise. Ein
Modellname (501, Nuptse, Detroit, Air Force 1) nutzt den Platz besser als
eine generische Ära-Angabe und wird bevorzugt.

### Beschreibung

1. Ein Hook-Satz mit Ära oder Besonderheit
2. Ein Stil-Absatz, der Schnitt, Waschung und Passform in Prosa nennt.
   Hier landen die Keywords von selbst, im Fließtext statt als Block
3. Detailblock: Marke, Modell, Größe, Material, Farbe, Zustand
4. Maße flach gemessen
5. Optional eine Zeile Synonyme im Klartext: "Wird auch gesucht als:
   Chunky Sneaker, Dad Shoes, Plateausohle."

Der Maßstab ist nicht der Tool-Output, sondern ein handgeschriebenes
Listing wie dieses (live gefunden, derselbe Verkäufer): Hook,
Stil-Absatz, Detailblock mit Modell und Material, Maße, dreizehn eng am
Artikel liegende Keywords, keine Fremdmarke.

### Hashtags: belegt gegen Kandidaten

Der Bot waehlt nur Tags aus Feldern, die du selbst angegeben hast (Marke plus
Modell, Schnitt, Aera). Korpus-Begriffe werden NICHT uebernommen, sondern als
Kandidaten zum Bestaetigen ausgegeben. Grund: ein Hashtag ist eine Behauptung
ueber das Teil, kein Suchwort. Der erste Entwurf bot "#cargo #knee #chino" fuer
eine einzige Hose an und "#nuptse" fuer eine North-Face-Jacke, deren Modell
niemand eingetragen hatte. Beides ist genau der Ausblendungsgrund "nicht
zugehoerige Hashtags", nicht Keyword-Strategie. Obergrenze bleibt 3.

### Keywords: an Vinteds Dimensionen verankert

Fünf bis acht Begriffe, ohne Raute, und jeder muss aus einer von Vinteds
eigenen Dimensionen stammen, nicht aus Social-Media-Gewohnheit:

| Dimension | Woher | Beispiel |
|---|---|---|
| Kategorie / Warentyp | Vinteds Katalogbaum | Sweatjacke, Straight-Leg-Jeans |
| Marke | Markenfeld, nur die eigene | Levi's, 501 |
| Größe | Größenfeld | W32 L32 |
| Farbe | Vinteds Farbfilterwerte | Dunkelblau |
| Material | Materialfeld (Waschetikett) | 100% Baumwolle |
| Zustand | Zustandsfeld | Sehr gut |
| Schnitt / Stil | klassenspezifisches Vokabular | Straight Leg, Mid Rise, Stonewashed |
| Ära | nur wenn das Teil sie wirklich trägt | 90s, y2k |

Harte Regeln, als Validator implementiert in
`listing/keyword_engine.py`:

- Keine fremde Marke, in keinem Feld
- Hoechstens drei Hashtags, und nur wenn sie das eigene Sortiment
  sortieren; fuer Reichweite bringen sie nichts
- Höchstens acht Keywords und höchstens drei Hashtags ("besonders viele
  Hashtags" ist Ausblendungsgrund)
- Jedes Attribut muss aus einem Foto oder einer Eingabe belegbar sein
- Keine Dubletten, keine Zahlenslots mit Wörtern gefüllt
- Eine Sprache pro Listing
- Material und Maße vorhanden oder ausdrücklich als fehlend markiert

### Beim Fotografieren

Das **Waschetikett** ist die wertvollste Aufnahme im ganzen Set: es
liefert Marke, Größe und Material in einem Bild und speist damit drei
strukturierte Filterfelder. Immer mit fotografieren.

## Der Keyword-Recherche-Bot

Die statische Vokabelliste in `keyword_engine.py` weiss, dass eine Jeans einen
Schnitt und eine Waschung hat. Sie weiss nicht, dass Carhartts Hosen Newel, Sid,
Landon und Aviation heissen oder dass Patagonias Jacken Torrentshell und Nano
Puff sind. Genau diese Namen tippt ein Kaeufer ein, und keine handgepflegte
Liste bleibt damit aktuell.

`listing/keyword_research.py` liest sie deshalb vom Markt ab. Die
Watcher-Datenbank enthaelt zehntausende echte Anzeigentitel, nach Markenfamilie
und Warenklasse sortiert. Das ist ein Korpus davon, wie Verkaeufer in genau
dieser Nische genau diese Ware beschreiben.

### Warum Lift und nicht Haeufigkeit

Der entscheidende Kniff ist die Bewertung. "Jacke" kommt ueberall vor und sagt
nichts. "Torrentshell" kommt in Patagonia-Jacken 71-mal haeufiger vor als im
Korpus insgesamt und identifiziert damit das Teil. Der Lift misst genau diese
Spezifik, der Anteil misst die Gelaeufigkeit, und die Rangfolge gewichtet
beides. Modellnamen bekommen eine eigene Bandbreite, weil sie auf Anteil nie
gewinnen koennen: jeder benennt ein Produkt aus einem ganzen Katalog.

Die Lift-Obergrenze ist dabei nicht willkuerlich. Ein Begriff, der
ausschliesslich in einer Zelle vorkommt, erreicht genau Korpusgroesse geteilt
durch Zellgroesse. Deshalb prueft der Bot relativ zu dieser Obergrenze statt
gegen eine feste Zahl; eine feste Schwelle hoert genau dann auf, Modellnamen zu
erkennen, wenn eine Marke gross genug wird, um sich zu lohnen.

### Was das gegenueber dem Vorbild besser macht

Zwei Carhartt-Hosen, durch den Bot gelaufen:

```
Carhartt WIP Single Knee Pant Hamilton Brown
  -> pant, single knee, knee pant, single knee pant, knee, brown

Carhartt Newel Pant Relaxed Fit Dunkelblau
  -> pant, newel, newel pant, relaxed, relaxed fit, fit
```

Eine einzige Ueberschneidung, und zwar das Kategoriewort. Zum Vergleich: bei
vintagezai trug ein Tank Top denselben 22er-Block wie eine Zip-Jacke derselben
Marke, Wort fuer Wort.

### Was aussortiert wird, und warum

| Klasse | Beispiel | Grund |
|---|---|---|
| `size` | `w32` | gehoert ins Groessenfeld, wo Vinted danach filtern kann |
| `brand` | `carhartt` | steht schon im Markenfeld, das eigenstaendig durchsuchbar ist |
| `brand-padded` | `carhartt hose` | Marke plus Allerweltswort; beides steht schon einzeln da |
| `kids` | `12 jahre` | anderer Markt, zieht das Vokabular seitwaerts |
| `foreign` | `broek`, `pantalon` | auf vinted.de schmaelert eine fremde Sprache die Zielgruppe |
| `fake-slang` | `reps`, `replica` | Faelscher-Vokabular; Signal, aber kein Wort fuer eine Anzeige |

Jeder aussortierte Begriff wird mit Grund ausgegeben, nicht stillschweigend
verschluckt.

### Nebenprodukt: gemessenes Faelschungsrisiko

Weil der Bot das Faelscher-Vokabular ohnehin erkennt, faellt eine Messung ab,
die vorher nur eine Annahme war (`--fake-vocab`, Stand 2026-09-08):

| Marke | Anzeigen | Treffer | Quote | Begriffe |
|---|---|---|---|---|
| stone-island | 2.439 | 11 | 0,451% | reps x10, batch x1 |
| adidas | 5.694 | 4 | 0,070% | inspired x3, replica x1 |
| nike | 5.181 | 3 | 0,058% | replica x3 |
| ralph-lauren | 2.024 | 1 | 0,049% | fake x1 |

Stone Island fuehrt mit dem 6,4-fachen der adidas-Quote. Die `HYPE_BRANDS`-Liste
im Watcher hat das bisher angenommen; jetzt ist es gemessen. Die Quoten sind
Untergrenzen: nur wer sein Vokabular offen hinschreibt, wird hier gezaehlt.

### Bedienung

```
# Welche Zellen genug Daten haben
uv run listing/keyword_research.py --cells

# Keywords fuer eine Zelle, mit Belegen
uv run listing/keyword_research.py --research patagonia/jacket

# Faelscher-Vokabular pro Marke
uv run listing/keyword_research.py --fake-vocab

# Vollstaendiges Listing; nutzt den Korpus automatisch
uv run listing/keyword_engine.py --suggest '{"brand":"Carhartt", ...}'
uv run listing/keyword_engine.py --no-corpus --suggest '...'   # nur statische Achsen
```

Die Recherche ist eine Anreicherung, keine Abhaengigkeit: fehlt die Datenbank,
faellt `--suggest` auf die statischen Achsen zurueck und sagt das dazu.

### Grenzen

Der Korpus ist ein Angebots-Korpus, kein Nachfrage-Korpus. Er sagt, welche
Begriffe Verkaeufer benutzen, nicht welche Kaeufer eintippen. Die beiden fallen
oft zusammen, aber nicht immer. Sobald genug vertrauenswuerdige gone-Daten da
sind, laesst sich das nachschaerfen: Begriffe, die in schnell verkauften
Anzeigen ueberproportional vorkommen, sind der bessere Nachfrage-Proxy. Das ist
bewusst noch nicht eingebaut, weil die Outcome-Uhr erst am 2026-09-08 neu
gestartet ist.

## Folgerungen für den Watcher

Aus den Videos ergeben sich keine neuen Suchbegriffe, die wir übernehmen
sollten. Die dort genannten Marken decken sich mit dem, was schon in
`searches.yaml` steht.

Zwei Beobachtungen sind trotzdem verwertbar:

1. **Die Titel-Formel ist ein Kaufsignal, kein Verkaufssignal.** Ein
   Listing im Pipe-Format mit `Size L | Schwarz | y2k` stammt mit hoher
   Wahrscheinlichkeit von einem Reseller, der bereits optimiert hat, also
   selten von einem unterbewertenden Privatverkäufer. Als Signal noch
   nicht implementiert, aber ein Kandidat für den Fake-Risk-Nachbarn
   "Profi-Verkäufer, wenig Marge".
2. **Der Hashtag-Block ist ein Erkennungsmerkmal.** Zwanzig und mehr
   Rauten in der Beschreibung markieren einen Massen-Reseller. Ebenfalls
   ein Ranking-Kandidat, nicht als Fake-Signal, sondern als
   Margen-Signal.

Beides ist bewusst noch nicht eingebaut: dafür fehlt die
Beschreibungs-Rückgabe der Katalog-API, und ein Signal, das wir nicht
messen können, gehört nicht in den Score.

## Quellen

| Key | Quelle |
|---|---|
| V1 | TikTok @teo.resellt.immer, 42s, lokal transkribiert und 42 Frames ausgelesen |
| V2 | TikTok @vintify.selling, 35s, lokal transkribiert und 35 Frames ausgelesen |
| S1 | [vinted.de/help/409](https://www.vinted.de/help/409) Suchergebnis-Reihenfolge |
| S2 | [vinted.de/help/49](https://www.vinted.de/help/49) Markennamen in der Beschreibung |
| S3 | [vinted.de/help/62](https://www.vinted.de/help/62) Gründe für Ausblendung |
| S4 | [vinted.de/catalog-rules](https://www.vinted.de/catalog-rules) Katalogregeln |
| S5 | [vintagezai.com](https://www.vintagezai.com/) und /agb, Anbieter-Angaben |
| S6 | [vinted.engineering](https://vinted.engineering/2024/09/05/goodbye-elasticsearch-hello-vespa/) Vespa-Migration |
| S7 | Eigene Live-Tests gegen vinted.de am 2026-09-08 (404-Test, Suchvergleiche, vier Tool-Listings) |
