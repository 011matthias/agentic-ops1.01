---
project: vinted-reselling
workstream: watcher
group: ""
spec: ""
state: active
updated: 2026-09-10
---

Sourcing watcher + price/demand database. Polls the Vinted catalog API for
staple-brand searches, records every listing to SQLite, and pushes deal alerts
via ntfy with one-tap rating buttons.

## Wo der Watcher laeuft

Der Windows-Task `VintedWatcher` zeigt seit 2026-09-08 auf einen **eigenen,
festen Worktree**:

```
C:\Users\neuma_p1qrsic\Repo\agentic-ops1-watcher
```

Vorher lief er aus dem Haupt-Checkout. Das ging so lange gut, wie dort `main`
stand, und ging schief, sobald eine parallele Session den Baum auf ihren
Feature-Branch stellte: an dem Abend, an dem dieses Upgrade lief, wechselte eine
Brisken-Session den Branch, und der Watcher hätte ab diesem Moment die alte
Version gegen die bereits migrierte Datenbank gefahren. Neue Zeilen haetten
`brand_norm` und `size_class` als NULL bekommen, und weil der Backfill als
erledigt markiert ist, dauerhaft.

Der Worktree ist auf `origin/main` festgenagelt (detached), und `data/` sowie
`context/` sind Verzeichnis-Junctions auf die kanonischen Ordner im
Haupt-Checkout. Es gibt also weiterhin genau eine Datenbank und genau eine
`.env`; nur der Code kommt jetzt aus einem Baum, den niemand umschaltet.

**Nach jedem Merge, der den Watcher betrifft**, den Worktree nachziehen:

```
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1-watcher checkout --detach origin/main
```

## Der Aufzeichnungs-Ausfall vom 2026-09-08 (behoben)

Der Owner hat auf dem Handy einen Bewertungsknopf gedrückt und nichts passierte.
Die Knöpfe waren in Ordnung; die Aufzeichnung dahinter nicht.

`alerts.quality` kam in die DDL, aber `CREATE TABLE IF NOT EXISTS` tut an einer
bestehenden Tabelle nichts, und die Migrationsschleife lief nur über `listings`.
Die Produktionstabelle bekam die Spalte nie, also scheiterte ab diesem Moment
jedes INSERT in `alerts`. Vier Dinge mussten zusammenkommen, damit das zwei
Stunden unsichtbar blieb:

1. Das INSERT steht **hinter** dem ntfy-Aufruf, also kamen die Alerts weiter an.
2. Der Fehler landete im Handler "eine schlechte Suche darf nicht die anderen
   acht kosten" und wurde zur Warnung.
3. Die Warnung ging nach stdout, das `run-hidden.vbs` verwirft. Es gab keine
   Logdatei.
4. `ingest_feedback` verlangte eine `alerts`-Zeile, bevor es eine Bewertung
   speicherte, und schob seinen ntfy-Zeiger trotzdem weiter. Beide echten Taps
   wurden gelesen und verworfen.

Gemessener Schaden: von 26 Alerts mit Knöpfen wurden 5 aufgezeichnet und 21
nicht, dazu die zwei ersten echten Bewertungen des Owners.

Behoben in PR #749 (inhaltsgleich mit #748, den eine Parallel-Session aus
demselben Arbeitsbaum gemerged hat):

- `reconcile_ddl_columns()` liest die DDL selbst und ergänzt jeder bestehenden
  Tabelle die fehlenden deklarierten Spalten. Eine Stelle zum Ändern, der Rest
  leitet sich ab. Läuft über alle Tabellen, nicht nur `listings`.
- `alterable()` meldet die Spalten, die SQLite nicht nachträglich hinzufügen
  kann (PRIMARY KEY, UNIQUE, NOT NULL ohne Default, nicht-konstanter Default),
  statt im Verbindungsaufbau zu scheitern.
- Indizes werden einzeln angelegt: ein fehlender Index kostet Tempo, ein
  gescheiterter Verbindungsaufbau kostet den Zyklus.
- `log()` schreibt zusätzlich nach `data/watcher.log` (Rotation bei 2 MB).
- `is_schema_error()` trennt "Code und Datenbank sind sich über die Form uneins"
  von vorübergehenden SQLite-Fehlern; ersteres beendet den Zyklus mit Exit-Code
  ungleich 0, was das einzige Signal ist, das ein verborgener Task tragen kann.
- `feedback_target()` nimmt eine Bewertung für jedes Listing an, das diese
  Datenbank je gesehen hat, und speichert sie mit leerem `alert_id`, wenn kein
  Snapshot existiert. Der Tap ist das Knappe; ntfy vergisst ihn nach ~12 Stunden.

**Wiederherstellung:** 34 verlorene Alert-Zeilen wurden aus den zugestellten
ntfy-Nachrichten rekonstruiert und tragen in `settings_json` die Herkunft
`recovered-from-ntfy`; `quality` bleibt dort NULL, weil der Wert nie in der
Nachricht stand. Die zwei echten Bewertungen des Owners sind erfasst und an
ihre Snapshots gehängt (`bought 9934904203` Levi's 501 W31 für 9,10 EUR gegen
Median 26,95; `bad 9932861205` Agolde Shorts XS).

**Verifiziert am laufenden Task, nicht per Hand:** der 21:50-Lauf schrieb wieder
`alerts`-Zeilen samt `quality`, der 21:55-Lauf holte einen frisch
veröffentlichten Tap vom ntfy-Topic in die Datenbank (77 → 78 Zeilen).

## Post-Alter und "jung und schon gefragt" (2026-09-08)

Der Owner fragte, ob ein Verhaeltnis aus Likes zu Zeit-seit-Post als weiteres
Kriterium hilft. Als Verhaeltnis nein: der Bot pollt alle 5 Minuten
`newest_first`, also ist der Nenner eine Ziehung aus dem Poll-Intervall (Median
3,18 Min ueber 33.231 Live-Zeilen) und keine Marktgroesse; durch ihn zu teilen
sortiert die Spitze der Alarmliste nach Poll-Glueck. Ausserdem tragen 64% der
Kandidaten ueberhaupt kein Herz.

Die Frage hat aber etwas Schlimmeres freigelegt: **der Bot hielt jedes Listing
fuer brandneu.** `listing_age_min` misst die Zeit seit WIR es gesehen haben und
stand bei jedem einzelnen Alarm auf 0,0. Tatsaechlich waren 7 von 107 Alarmen
auf Listings zwischen 3,8 Stunden und 5,05 Tagen alt, vier davon gingen laut
raus.

**Die Uhr lag schon in der Datenbank.** Vinted liefert Fotos von einem Pfad, der
auf den Upload-Epoch endet, und `photo_url` steht auf jeder Zeile. Vier
unabhaengige Bestaetigungen:

1. 35.752 von 35.753 Zeilen lesbar (die eine hat gar keine Foto-URL).
2. Live gepollte Zeilen kommen mit Median 3,18 Min heraus, die Seed-Crawl-Zeilen
   mit Median 3,7 Tagen. Der Parser sieht das Seed-Flag nie.
3. Kein einziges negatives Alter, und die Reihenfolge stimmt mit Vinteds eigenen
   aufsteigenden Listing-IDs bei Spearman 0,993 ueberein.
4. Herzen wachsen monoton mit dem Alter und fallen nach 24 Stunden wieder:
   0,41 unter 5 Min, 1,31 bei 5-60 Min, 1,89 bei 1-24 Std, 1,13 darueber. Eine
   erfundene Uhr erzeugt diese Kurve nicht. Der Abfall nach 24 Stunden ist
   Survivorship: was dann noch dasteht, ist liegengeblieben.

**Die Regel des Owners** (2026-09-08): "wenn junge posts schon paar like haben
solls laut klingeln". Herzen zaehlen nur, solange das Listing unter 60 Minuten
alt ist. Auf einem alten Listing heisst dieselbe Zahl, dass der Markt
hingeschaut und nicht gekauft hat; auf einem jungen, dass innerhalb von Minuten
Nachfrage da war. Die Herzen verdienen einen eigenen Term, statt den Rabatt zu
wiederholen: der mittlere Rabatt liegt bei 56,0% ohne Herz, 55,7% bei einem und
55,8% bei zwei.

Gebaut als begrenzte Anhebung **innerhalb** des bestehenden relativen
Klingel-Budgets, nicht als absolute Regel: 35% der Kandidaten tragen mindestens
ein Herz, ein absolutes "klingeln wenn geliked" wuerde den lauten Kanal fluten.
Der Boost ist bei +35% gedeckelt, damit ein einzelnes virales Listing den Kanal
nicht besetzt. Alte Listings bekommen keinen Abschlag, den der Owner nicht
verlangt hat; sie gewinnen die lauten Plaetze nur nicht mehr.

Verifiziert am laufenden Task: eine Meldung um 21:29 UTC trug "seit 1 Min.
online", Prio 5, mit den drei Bewertungsknoepfen.

Nebenbei repariert: `tools/preflight-hooks.py` startete pytest ohne httpx und
pyyaml, waehrend der CI-Job beide mitgibt. Jedes Modul hinter
`pytest.importorskip` wurde lokal stillschweigend uebersprungen, darunter die
gesamte 151er-Vinted-Suite, und das Werkzeug meldete trotzdem "der CI-hooks-Job
sollte durchgehen". Nach dem Angleichen steigt die lokale Zahl von 1178 auf
1329. Ein lokales Tor, das eine echte Teilmenge des entfernten ist, ist
schlimmer als keins, weil man ihm glaubt.

## Am laufenden Task verifiziert (2026-09-09)

Nicht per Handaufruf, sondern an den echten Zyklen des Windows-Tasks.

**Zeitreihen (Zyklus 22:55Z).** Der erste Lauf mit dem neuen Code schrieb 32
Zeilen nach `listing_events`, darunter zwei echte Preisbewegungen: ein
Juventus-Polo von 25,00 auf 20,00 (Senkung) und ein Nike Dunk von 40,00 auf
43,00 (Erhoehung), dazu 28 Favoriten-Zuwaechse. Kurz darauf: 13
Preisaenderungen und 231 Favoriten-Bewegungen.

**Verkaufserkennung (Recheck 23:52Z).** `25 visited, 16 sold, 2 deleted, 0
closed, 0 unreadable, 2 price change(s)`. Jeder vorherige Lauf meldete
`0 gone`, seit es den Watcher gibt. Die 16 Verkaeufe tragen die Herkunft
`buyer_item_status:SUCCESS:Verkauft`; die 404er stehen weiter getrennt daneben
mit `sold_flag=0`. Erste Zeit-bis-Verkauf-Werte: 76,8 h (TNF Regenjacke),
78,3 h (Adidas Firebird), 86,3 h (Levi's 501 Damen).

Das ist genau das, was vorher verloren ging: eine verkaufte Anzeige antwortet
mit 200, also las der alte Code sie als "lebt" und schob `last_seen` vor. Jeder
Recheck-Durchlauf hat Verkaeufe geloescht.

**Entwurf aus dem Gekauft-Tipp.** Der vom Owner gekaufte Levi's 501
(9934904203, 9,10 EUR gegen Median 26,95) ergibt ohne eine einzige Eingabe:
Titel `Levi's 501 Jeans | Gr. W31`, Preisvorschlag 20,50 EUR (Kaeufer zahlt
22,22 EUR), Marge 11,40 EUR, Vergleich Median 25,90 / p25 18,55 / p75 37,45
ueber 94 Anzeigen der Zelle, plus drei offene Fragen (Farbe, Material, Masse).

## Der Volumen-Einbruch vom 2026-09-10

Der Owner meldete "kaum noch Benachrichtigungen". Er hat recht, und die Ursache
ist das Sende-Budget aus PR #781.

**Was das alte Volumen war.** `listings.alerted=1` pro Tag: 180 (09-06),
171 (09-07), 181 (09-08), 319 (09-09), 9 (09-10 bis 09:46Z). Das "50+" aus dem
Prompt war eine Untergrenze, keine Obergrenze; tatsaechlich liefen rund 177
Pushes am Tag und der Owner war damit zufrieden. `SEND_BUDGET_PER_DAY = 60` hat
das schon als Zielwert auf ein Drittel gekuerzt.

**Warum es dann 9 statt 60 wurden.** `alert_priority` vergleicht einen
Kandidaten nicht gegen einen Tageszaehler, sondern gegen die besten 60 der
letzten 24 Wanduhr-Stunden. Das ist nicht dasselbe wie "60 pro Tag", und der
Replay ueber alle 561 quality-tragenden Zeilen zeigt zwei Fehler:

1. **Der Balken steigt innerhalb eines Tages monoton**, weil der Pool sich
   fuellt: 50.9 um 20Z am 08., 88.5 um 12Z, 108.4 um 16Z, 114.7 um 19Z.
   Durchgelassen pro Stunde am 09-09: 40, 26, 19, 10, 13, 11, 3, 6, 1, 0, 0.
   Die letzten beiden Stunden des Tages senden nichts mehr.
2. **Das Fenster ist 24 Stunden lang, der aktive Tag rund 13.** Der Pool
   umfasst also immer zwei Wachphasen, und der naechste Morgen erbt den
   Spitzenbalken des Vortages. Um 09:37Z am 10.: Pool 519 Zeilen, davon 473 vom
   Vortag, Balken 114.8 = 88.5. Perzentil. Der Tagesdurchschnitt der Kandidaten
   liegt bei 91.1. Verworfen wurden unter anderem Kandidaten mit 112.4, 110.1
   und 105.8.

**Die ntfy-Wand steht bei 319, nicht bei 177.** Am 09-09 gingen 319 Pushes
durch, danach 147 Fehlschlaege zwischen 16Z und 20Z. Die drei Tage davor liefen
mit je rund 180 ohne einen einzigen Fehlschlag. Das Kontingent wurde vom
Nachhol-Schwall gesprengt, nie vom normalen Tag; 60 kuriert damit die falsche
Zahl.

**Richtige Form:** ein echter Tageszaehler (wie viele Pushes seit lokaler
Mitternacht wirklich rausgingen), Deckel in der Naehe von 180 mit Luft unter der
beobachteten Wand. Das Perzentil bleibt da, wo es hingehoert: auf der
Klingel-Stufe, bei der es um Unterbrechung geht, nicht um Menge.

### Zwei Nebenbefunde aus derselben Messung

**Das Laender-Gate ist ein Vorbestand, kein Ausloeser, aber teuer.** Nach echtem
Land (ueber `listings` gejoint): FR 415 Kandidaten / 42 gesendet, IT 160 / 12,
NL 86 / 11, BE 52 / 7, gegen DE 248 / 154. `foreign_advantage_eur: 8` ist ein
absoluter Betrag auf einen Vergleichsmedian von meist 25 bis 35 EUR und verlangt
damit rund 25 Prozentpunkte zusaetzlichen Rabatt. Ein Angebot zu 11.20 EUR gegen
Median 32.73, also 66% drunter, wird abgelehnt. Ein proportionaler Aufschlag
waere die richtige Form; ob ein Auslandsangebot ueberhaupt schlechter
weiterverkauft, ist mit 3 vertrauenswuerdigen gone-Events nicht messbar.

**`alerts.country` ist immer NULL.** `record_alert` liest das Land aus `rec`,
`score_and_alert` loest es aber in eine lokale Variable aus dem Verkaeuferprofil
auf und schreibt es nie zurueck. 5 gefuellte Zeilen stehen 726 ueber den Join
aufloesbaren gegenueber. Die Snapshot-Tabelle wurde gebaut, damit fuer den
Backtest nichts verloren geht; auf dieser Dimension liefert sie nichts.

### Was ausgeschlossen wurde

Die 120 Katalog-404er lagen alle am 09-09 zwischen 10Z und 11Z und kamen nicht
wieder. Der Zulauf ist gesund, rund 1000 neue Anzeigen pro Stunde. Der Task
steht auf Ready, letzter Lauf mit Ergebnis 0.

Die Naechte fehlen weiterhin: 671 Minuten Luecke von 21:10Z am 09. bis 08:21Z am
10., weil `WakeToRun` auf `False` steht. Das ist ein Vorbestand und kostet die
Nachtstunden, in denen ohnehin nur 1 bis 2 Pushes pro Stunde anfallen. Den
Laptop jede Nacht alle fuenf Minuten zu wecken widerspricht der Entscheidung des
Owners, den Laptop gerade NICHT zum Dauerlaeufer zu machen, also ist das seine
Wahl und keine stille Umstellung.

## Elemente

| Element | Zustand | Stand | Nächster Schritt | Blocker |
|---|---|---|---|---|
| Laufzeit-Baum | live | Eigener Worktree `agentic-ops1-watcher`, Junctions auf data/ und context/; Zyklen schreiben nach `data/watcher.log` | Nach Watcher-Merges nachziehen | - |
| Poller + Comp-DB | live | v3 Präzisions-Upgrade 2026-09-08; ~33k Zeilen. **Backlog-Gate korrigiert**: zählte Artikel statt Zeit und liess 67% aller Listings ungeprüft | Datenqualität beobachten | - |
| Session-Handling | live | Clean-slate refresh, 45-Min-Renewal, 401/403-Split, jetzt auch 5xx-Backoff | - | - |
| Zustands-Mapping | live | **Defekt behoben 2026-09-08**: "Neu" / "Neu, mit Etikett" fielen auf `unknown`, 4.527 Zeilen waren von Alerts UND Comps ausgeschlossen. Rückwirkend repariert | - | - |
| Größenklassen | live | `size_class` normalisiert drei Notationen; Alert-Filter s/m/l + W29-W34, pro Search überschreibbar | XL/52 je Produkt aus `--brand-report` entscheiden | - |
| Marken-Normalisierung | live | `brand_norm` führt Ralph Lauren aus 6 Schreibweisen zu einem 2.069-Zeilen-Pool zusammen | - | - |
| Fake-Risk | live | Regelbasiert inkl. Verkäuferprofil; ab 0.4 Warnzeile, ab 0.7 unterdrückt. Unterdrückung braucht **zwei** unabhängige Signale, der Preis allein warnt nur | Schwellen nachziehen, sobald Bewertungen da sind | Feedback-Daten |
| Verkäuferprofil | live | `/api/v2/users/{id}` liefert Land + Reputation, gecacht pro Verkäufer, max 6 Abrufe/Zyklus | - | - |
| Standort DE | live | Land kommt aus dem Verkäuferprofil (Katalog-Antwort hat keins); Ausland braucht 8 EUR Vorsprung | Schwelle nach 1 Woche Länderdaten nachmessen | Länderdaten |
| Post-Alter | live | Echte Post-Zeit aus der Foto-URL, rueckwirkend ueber 35.752 Zeilen, 0 zusaetzliche Vinted-Anfragen. Steht im Alert-Text und in jedem Snapshot | Nach 2 Wochen gegen Outcome-Daten pruefen | - |
| Jung + gefragt | live | Herzen auf einem Listing unter 60 Min heben die Qualitaet um bis zu 35%, gedeckelt, innerhalb des Klingel-Budgets. Auf aelteren Listings zaehlen sie nicht | Vorzeichen mit Outcome-Daten pruefen | Outcome-Daten |
| Alert-Snapshots | live | Jede Entscheidung friert Comps, Schwellen und Risiko ein, auch die unterdrückten. **2026-09-08 zwei Stunden ausgefallen** (fehlende Spalte `quality`), behoben und 34 Zeilen rekonstruiert | - | - |
| Feedback-Kanal | live | 👍 / 👎 / Gekauft; **am Handy des Owners bestätigt** (Knöpfe rendern, Tap erreicht ntfy). Eine Bewertung überlebt jetzt auch ohne Snapshot | Taste-Daten sammeln | - |
| Prioritäts-Stufen | live | **Relativ** statt absolut: laut wird nur, was die Konkurrenz der letzten 24h schlägt. Gemessen an einem echten Tag: 5% klingeln, 12% normal, 83% still | Nach einer Woche gegen echte Daten nachjustieren | - |
| Gone/Sold-Erkennung | live | **Verkauft wird jetzt von geloescht getrennt** (2026-09-09): 200 + Plugin `buyer_item_status` Theme SUCCESS = verkauft, 200 + `item_status` `is_closed:false` = lebt, 404 = geloescht. Der alte Marker `is_sold":true` stand auf keiner Seite, also war der Verkaufs-Zweig unerreichbar und jeder Verkauf wurde als "lebt" verbucht | Outcomes sammeln bis 100 je Zelle | Zeit |
| Recheck-Auswahl | live | Dasselbe Budget (25 Seiten/Stunde), andere Reihenfolge: erst Alert-Kandidaten, dann das Fenster 12h-10d, dann der alte Aeltester-zuerst-Lauf | - | - |
| Zeitreihen | live | `listing_events` haelt jede Bewegung von Preis, Favoriten, Aufrufen fest. Die Recheck-Seite liefert den zweiten Preispunkt Tage spaeter, den der Poll nie sieht (Median-Beobachtung 10 Minuten) | - | - |
| Brand-Report | live | `--brand-report`: Volumen, Median, Spread, Marge am Gate, Größen-Nachfrage, Keep/Drop | Wöchentlich laufen lassen | - |
| Damen-Jeans | live | Probes gelaufen: agolde (Median 126,70) und mother-denim aufgenommen, citizens-of-humanity bei ratio 0.50, 7 for all mankind abgelehnt (Median 18,55). Alle drei geseedet | Nach 2 Wochen gegen R1-R3 bewerten | - |
| Backtest-Kalibrierung | geplant | Snapshot-Tabelle sammelt ab jetzt alles Nötige | `/comd_optimize` mit Offline-Scorer | ~300 gone-Events |
| Listing-Engine | live | `keyword_engine.py` (Titel/Beschreibung/Hashtags/Validator, nachsichtige Eingabe) + `keyword_research.py` (Korpus-Mining, Modellnamen per Lift, Sprachfilter, Trend, Nachfrage) | An echten eigenen Listings erproben | - |
| Gekauft-zu-Entwurf | live | `inventory.py --draft`: der Gekauft-Tipp wird zum fertigen Entwurf samt Preisvorschlag; offene Achsen kommen als Fragen, nicht als TBD | - | - |
| Eigene Anzeigen | live | `my_listings` + `inventory.py --record/--mine/--sold`. Bis dort Zeilen stehen, ist jede Keyword-Rangfolge eine Hypothese ohne Rueckkanal | Erste eigene Anzeige eintragen | - |
| Sprachfilter | live | Der Korpus ist franzoesisch-lastig (28,7% fr gegen 15,3% de). `listings.country` war als Hebel unbrauchbar (0,46% gefuellt), also entscheidet die Titelsprache. `bleu`/`jean` fallen raus, `501`/`nano puff`/`torrentshell` bleiben | - | - |
| Trend | gebaut, wartet | Rechnet nur auf beobachteten Fenstern (Zeilen, die der Watcher frisch gesehen hat). Heute 3 Beobachtungstage von 14 noetigen; meldet den Fehlbetrag statt einer Zahl | 11 weitere Sammeltage | Zeit |
| Nachfrage-Gewichtung | gebaut, wartet | Begriffe nach echten Verkaeufen gewichtet. Schwellen aus dem Standardfehler: nichts unter 30, vorlaeufig bis 99, belastbar ab 100 je Zelle | Outcome-Daten | Verkaufsdaten |

## Keep / Drop / Add-Regeln

Wöchentlich per `--brand-report` ausgewertet, Entscheidung beim Owner. Drop
heißt `alerts_disabled: true`, nicht Search löschen: die Preisdaten laufen
weiter, sie sind das eigentliche Asset.

| # | Kennzahl | Keep verlangt | Drop-Flag bei | Herkunft |
|---|---|---|---|---|
| R1 | Comp-Abdeckung: Anteil der Kandidaten mit >= `min_comps` | >= 60% | < 40% in zwei Wochen | Urteilswert |
| R2 | Marge am Gate: `(1 - deal_ratio) * Median` | >= 15 EUR in mindestens einer Klasse | keine Klasse schafft 15 EUR auch bei 0.45 | 15 EUR = Owner-Mindestflip |
| R3 | Spread p75/p25 | >= 1.5 | < 1.3 (keine Fehlbepreisung möglich) | Urteilswert |
| R4 | Sell-Through: gone-Rate 7d + Median-Stunden bis gone | **offen bis Daten** | - | braucht ~100 Events/Marke |
| R5 | Alert-Präzision aus Bewertungen | >= 30% bei n >= 10 | < 20% bei n >= 10 nach einem Nachziehen | Urteilswert |
| R6 | Fake-Risiko (Durchschnitt) | - | nie Auto-Drop, sondern manuelle Prüfung ab 0.5 | Urteilswert |

Stand 2026-09-08 gegen die Live-DB: `the-north-face`, `carhartt`,
`stone-island`, `ralph-lauren`, `patagonia` sind KEEP. `adidas`, `nike` und
`levis` fallen bei R2 durch (Marge am Gate 11,65 bis 12,13 EUR statt 15), weil
ihr Median bei rund 26 EUR liegt. Das ist ein Schwellen-Thema, kein
Marken-Thema: ein `deal_ratio`-Override auf 0.45 für diese drei Tags hebt die
Marge über 15 EUR. Vorschlag, noch nicht gesetzt, weil er das Volumen drückt
und der Owner es vorerst bei ~50 Meldungen/Tag belassen wollte.

**Add-Kandidaten** kommen mit `alerts_disabled: true` herein, sammeln 7 bis 14
Tage Daten, und werden dann gegen R1 bis R3 bewertet.

## Größen-Nachfrage (die Grundlage der XL/52-Entscheidung)

Anteile je Marke aus dem Report, Fenster 45 Tage:

| Marke | m | s | l | xl | xxl |
|---|---|---|---|---|---|
| adidas | 30% | 24% | 23% | 12% | 3% |
| nike | 30% | 20% | 25% | 15% | 5% |
| the-north-face | 31% | 28% | 19% | 9% | 3% |
| carhartt | 31% | 25% | 20% | 11% | 7%* |
| stone-island | 33% | 26% | 22% | 11% | 4% |
| ralph-lauren | 32% | 29% | 18% | 9% | 2% |

*bei Carhartt steht an fünfter Stelle xs mit 7%, w32 folgt mit 6%.

Lesart: s/m/l decken 72 bis 79 Prozent des Angebots. XL trägt 9 bis 15 Prozent,
am meisten bei Nike und adidas (Streetwear), am wenigsten bei Ralph Lauren und
TNF. Wenn XL zugeschaltet wird, dann dort und per Search-Override, nicht global.
Das Angebot ist dabei nur der Proxy; echte Nachfrage misst erst R4.

## Politeness-Budget

| Quelle | Vorher | Jetzt |
|---|---|---|
| Katalog-Polls | 9 Requests / 5-Min-Zyklus | unverändert 9, plus überlebende Jeans-Searches |
| Recheck | <= 25 Item-Seiten / 60 Min | unverändert |
| Verkäuferprofile | - | <= 6/Zyklus, nur für Deal-Kandidaten, pro Verkäufer gecacht |
| Feedback-Poll | - | +1/Zyklus, gegen **ntfy.sh**, nicht Vinted |
| Probes | - | einmalig, jetzt mit Fehlerbehandlung statt Absturz |
| 5xx | wurde weitergepollt | 20 Min Backoff, eskalierend |

## Offene Punkte

1. Das erste 👎 traf eine Agolde-Shorts in XS. `xs` steht für die drei
   Damen-Denim-Suchen absichtlich in `size_classes` (die Probe zeigte, dass
   Premium-Damenjeans in XS/S/M gelistet werden). Ein Signal ist keine Regel;
   wiederholt sich das, ist es eine Zeile Config.
2. Nach einer Woche: Länderverteilung messen und die 8-EUR-Schwelle prüfen.
3. Nach 2 Wochen: die drei neuen Denim-Suchen gegen R1 bis R3 bewerten.
4. Nach ~300 vertrauenswürdigen gone-Events: Backtest-Scorer als eigener PR,
   dann `/comd_optimize`.
5. Das Vorzeichen der Herzen ist noch unbelegt. Trigger: sobald 100 alarmierte
   Listings ein gone-Event aus vertrauenswuerdiger Quelle haben, den Anteil
   "weg" bei 0 Herzen gegen >= 1 Herz testen, kontrolliert auf `search_tag`.
   Ab 10 Prozentpunkten Unterschied ist das Gewicht datengestuetzt statt
   gesetzt. Heute: 3 gone-Events, keines davon war je ein Alarm, und alle drei
   echten Bewertungen haben exakt 1 Herz, also nicht einmal Varianz.
6. Aus der adversarialen Prüfung sind rund ein Dutzend Befunde ungeprüft
   geblieben (der Lauf brach beim Sitzungslimit ab, 38 von 71 Agenten).
   Bestätigt und behoben wurden: Wall-Verschlucken im Verkäufer-Abruf,
   fehlender Backoff im Recheck, Absturz durch Fremd-IDs im Feedback-Poll,
   nie wiederholter Backfill, Doppelzählung im Fake-Risk. Offen sind unter
   anderem: `brand_report` teilt gone-Rate über zwei Grundgesamtheiten,
   `poll_search` ist ungetestet, `refresh_session` umgeht den Backoff.

7. **Kein zweiter Markt vor dem Round-Trip-Nachweis.** Der Vergleichsmedian ist
   ein Median von ANGEBOTS-Preisen. Ob er den realisierten Verkaufspreis
   vorhersagt, ist nie gemessen worden, auch nicht hier, wo als Einzigem beide
   Seiten sichtbar sind. Gate vor jeder Portierung auf ein anderes Handelsfeld:
   30 abgeschlossene Round Trips bis zum Endzustand (verkauft zu erfasstem
   Preis, oder nach 90 Tagen unverkauft), die gemessene Korrelation zwischen
   vorhergesagtem Median und realisiertem Preis, und ein vorab festgelegtes
   Abbruchkriterium (Durchverkaufsquote unter 50% oder mediane Nettomarge unter
   10 EUR heisst: die Auswahlfunktion ist falsch, und kein zweiter Markt
   repariert das). Dafuer fehlt ein Round-Trip-Ledger (Kauf, Landed Cost,
   Haltetage, Listung, realisierter Preis); `my_listings` ist die Tabelle, sie
   steht heute auf 0 Zeilen. Bei ~1 Kauf/Tag ist das rund ein Quartal.
   Herleitung im Checkpoint 2026-09-09.
