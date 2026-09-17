---
project: vinted-reselling
workstream: listing
group: 
spec: 
state: active
updated: 2026-09-17
---

# vinted-reselling / listing

Titel, Beschreibungen und Suchbegriffe der eigenen Anzeigen: der Generator im Repo
(`listing/keyword_engine.py`, `listing/keyword_research.py`) und die Texte, die
tatsaechlich live stehen.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Beschreibungs-Generator | live | Schreibt nur belegte Fakten: was es ist und wie es geschnitten ist, Details, eine "Maße flach"-Zeile, benannte Mängel, dann Suchwörter. Kein TBD, kein Feld-Dump. `validate()` blockt Verkäufer-Notizen ("siehe Foto 2") und warnt bei Werbefloskeln | - | - | PR #936 |
| Suchbegriffe aus Beschreibungen | in-progress | Watcher speichert Beschreibungen beim Recheck (Tabelle `descriptions`, ~25 Seiten/h); `--tags BRAND/CLASS` zerlegt Hashtags, eine Stimme pro Anzeige; Engine schreibt nur Begriffe, die die Fakten voll belegen, der Rest wird Kandidat | Ab 40 Beschreibungen pro Klasse liefert es Begriffe, ab 30 verkauften vergleicht `tag_demand` verkauft gegen alle | Datenmenge | PRs #928, #929, #930 |
| Live-Beschreibungen (v3) | live | Auf allen 19 offenen Anzeigen, per neu geladenem Bearbeiten-Formular verifiziert. 11 weitere und die Neueinstellung von #27 sind verkauft und nicht editierbar | - | - | lokal `.scratch/vinted/driver/descriptions-v3.json`, Backup `descriptions-backup-2026-09-16.json` |
| Suchwort-Zeilen (v4) | live | Aus Vinteds Suchvorschlägen für deutsche Käufer (`source: query_data`): 15 geändert, 4 unverändert, alle 19 verifiziert | Wirkung an Herzen/Verkäufen der 19 beobachten | - | lokal `.scratch/vinted/suggestions-2026-09-16.json`, `driver/build_v4_keywords.py` |
| Käufer-Suchen im Bot | not-started | Die v4-Zeilen wurden aus der Ernte zusammengestellt; der Bot fragt die Vorschläge noch nicht selbst ab | Suggestions-Abfrage in `keyword_research` einbauen, Rangfolge nach `total_score`, nur `query_data`, Entitäten (Marke/Kategorie) ausfiltern | - | Endpunkt `api.vinted.de/search-bar/v2/suggestions`, `locale: de-DE` |
| Prüfungen am Teil | blocked | #23 Größe S (Foto spricht dagegen), #29 Schwarz oder Navy, #30 Farbe (Titel Graugrün, Notiz beige, Foto grau), #18 Farbfeld nur Rot | Owner prüft am Teil; Titel/Farbfeld dann anpassen | Owner | Review 2026-09-16 |

States: not-started · in-progress · blocked · done · live · paused

## Open decisions / gates

- Jede Änderung an Live-Anzeigen braucht ein ausdrückliches Ja des Owners pro Durchgang.
- Nur Anzeigen mit `can_edit` und nicht `is_closed` bearbeiten: der eingeloggte Kleiderschrank-Feed listet verkaufte Anzeigen mit, deren Bearbeiten-Seite abstürzt.

## Pointers

- Code: `workspace/projects/vinted-reselling/listing/`
- Watcher-Seite: `status/watcher.md`
