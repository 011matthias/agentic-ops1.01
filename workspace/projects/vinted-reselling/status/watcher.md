---
project: vinted-reselling
workstream: watcher
group: ""
spec: ""
state: active
updated: 2026-09-08
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

## Elemente

| Element | Zustand | Stand | Nächster Schritt | Blocker |
|---|---|---|---|---|
| Laufzeit-Baum | live | Eigener Worktree `agentic-ops1-watcher`, Junctions auf data/ und context/ | Nach Watcher-Merges nachziehen | - |
| Poller + Comp-DB | live | v3 Präzisions-Upgrade 2026-09-08; ~33k Zeilen. **Backlog-Gate korrigiert**: zählte Artikel statt Zeit und liess 67% aller Listings ungeprüft | Datenqualität beobachten | - |
| Session-Handling | live | Clean-slate refresh, 45-Min-Renewal, 401/403-Split, jetzt auch 5xx-Backoff | - | - |
| Zustands-Mapping | live | **Defekt behoben 2026-09-08**: "Neu" / "Neu, mit Etikett" fielen auf `unknown`, 4.527 Zeilen waren von Alerts UND Comps ausgeschlossen. Rückwirkend repariert | - | - |
| Größenklassen | live | `size_class` normalisiert drei Notationen; Alert-Filter s/m/l + W29-W34, pro Search überschreibbar | XL/52 je Produkt aus `--brand-report` entscheiden | - |
| Marken-Normalisierung | live | `brand_norm` führt Ralph Lauren aus 6 Schreibweisen zu einem 2.069-Zeilen-Pool zusammen | - | - |
| Fake-Risk | live | Regelbasiert inkl. Verkäuferprofil; ab 0.4 Warnzeile, ab 0.7 unterdrückt. Unterdrückung braucht **zwei** unabhängige Signale, der Preis allein warnt nur | Schwellen nachziehen, sobald Bewertungen da sind | Feedback-Daten |
| Verkäuferprofil | live | `/api/v2/users/{id}` liefert Land + Reputation, gecacht pro Verkäufer, max 6 Abrufe/Zyklus | - | - |
| Standort DE | live | Land kommt aus dem Verkäuferprofil (Katalog-Antwort hat keins); Ausland braucht 8 EUR Vorsprung | Schwelle nach 1 Woche Länderdaten nachmessen | Länderdaten |
| Alert-Snapshots | live | Jede Entscheidung friert Comps, Schwellen und Risiko ein, auch die unterdrückten | - | - |
| Feedback-Kanal | live | 👍 / 👎 / Gekauft als ntfy-Buttons; Topic gesetzt, Rundlauf-Drill bestanden (publish → poll → ingest → dedupe) | Owner tippt einmal einen Knopf an, damit das Rendern am Handy belegt ist | Owner |
| Prioritäts-Stufen | live | **Relativ** statt absolut: laut wird nur, was die Konkurrenz der letzten 24h schlägt. Gemessen an einem echten Tag: 5% klingeln, 12% normal, 83% still | Nach einer Woche gegen echte Daten nachjustieren | - |
| Gone/Sold-Erkennung | live | Proven-session-Vorbedingung, Wall-Abbruch, 40%-Batch-Decke, `gone_source` | Vertrauenswürdige Outcomes sammeln | Zeit |
| Brand-Report | live | `--brand-report`: Volumen, Median, Spread, Marge am Gate, Größen-Nachfrage, Keep/Drop | Wöchentlich laufen lassen | - |
| Damen-Jeans | live | Probes gelaufen: agolde (Median 126,70) und mother-denim aufgenommen, citizens-of-humanity bei ratio 0.50, 7 for all mankind abgelehnt (Median 18,55). Alle drei geseedet | Nach 2 Wochen gegen R1-R3 bewerten | - |
| Backtest-Kalibrierung | geplant | Snapshot-Tabelle sammelt ab jetzt alles Nötige | `/comd_optimize` mit Offline-Scorer | ~300 gone-Events |
| Listing-Engine | live | `keyword_engine.py` (Titel/Beschreibung/Validator) + `keyword_research.py` (Korpus-Mining pro Marke und Klasse, Modellnamen per Lift) | An echten eigenen Listings erproben | - |

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

1. Owner tippt einmal einen Bewertungsknopf an. Der Rundlauf ist maschinell
   belegt; offen ist nur, ob die drei Buttons am Handy sauber rendern.
2. Nach einer Woche: Länderverteilung messen und die 8-EUR-Schwelle prüfen.
3. Nach 2 Wochen: die drei neuen Denim-Suchen gegen R1 bis R3 bewerten.
4. Nach ~300 vertrauenswürdigen gone-Events: Backtest-Scorer als eigener PR,
   dann `/comd_optimize`.
5. Aus der adversarialen Prüfung sind rund ein Dutzend Befunde ungeprüft
   geblieben (der Lauf brach beim Sitzungslimit ab, 38 von 71 Agenten).
   Bestätigt und behoben wurden: Wall-Verschlucken im Verkäufer-Abruf,
   fehlender Backoff im Recheck, Absturz durch Fremd-IDs im Feedback-Poll,
   nie wiederholter Backfill, Doppelzählung im Fake-Risk. Offen sind unter
   anderem: `brand_report` teilt gone-Rate über zwei Grundgesamtheiten,
   `poll_search` ist ungetestet, `refresh_session` umgeht den Backoff.
