# Checkpoint: WW W2-14 Startknopf und Hero-Reiter

**Date:** 2026-10-14
**Status:** Original auf Release 7; Duplikat im Nur-Matthias-Modus mit R21 → „Termin bestätigt“; Matthias' Probedurchlauf und Release 8 stehen aus

---

## Summary
Seit dem Checkpoint vom 13.10. laufen Release 6 und 7 am Original. Das Duplikat hat einen Testtag (1 Tag = 5 s) und eine Startseite für Tobias und Sabine, auf der jeder Klick genau einen Lauf startet. Die Hero-Reiter von Typ 72627 heißen jetzt wie auf der Vertriebstafel, „Termin bestätigt“ ist neu dazugekommen. R21 schiebt Projekte bisher nur am Duplikat dorthin.

Arbeitsort: Clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops`, Branch `client/warme-wimmer/w2-14-sales-process-72627`, PR akkton/agentic-ops#305, gepusht bis `0600897`.

---

## What Was Done This Session
### Original W2-14 (`NPHbbRF2NVAbUyzF`)
1. Release 6 `12367bfd`: R20-Titel ohne `;`. Abnahmelauf 54135, Record `9b184e4`.
2. Release 7 `a9f98291`: Logbuch- und Aufgabentexte nennen die Tafelnamen (R3, R9, R14, R15, R16), Owner-Entscheid für Duplikat und Original. Abnahmelauf 54172, Record `581ee13`. Beide Releases liefen mit Suiten, Trockenlauf und unabhängiger Prüfung: Code = Kandidat, HUK-106488 unverändert, Ledger 13.

### Duplikat (`tB5anuCbpmYsrA7K`) und Testtag
1. `tagMs(cfg)` in `tools/ww-vertrieb-logic.mjs`: `test_tag_sekunden` verkürzt nur `nach_tagen` und gilt nur im Testmodus. `konfigPruefen` verlangt dafür 1..86400, das Release-Tool verweigert das Feld fürs Original (`71d8898`, Tests: Logik +8, Guards +3, Release +1).
2. `T --sofort` im Starter: Er wartet nicht mehr auf das sichere Fenster. Zwei Prüfungen bleiben: kein offener Lauf bei Original oder Duplikat, und die Startminuten des Originals bleiben gesperrt.
3. `duplikat-umbauen.mjs` (`.scratch`): Das Skript ersetzt nur die vier Code-Knoten durch einen frischen Build. Vor jedem PUT legt es eine Sicherung an, danach liest es den veröffentlichten Graphen zurück. Mit `--nur-matthias` gehen Mails und Aufgaben nur an Matthias.
4. Stand jetzt `464cf15e`, Nur-Matthias-Modus, R21 = Logbuch + Status 857884.

### Startknopf (`t1lRfYjuqU9THsaf`)
1. v2 (Owner): 26 Knöpfe, ein Klick = ein Lauf wie ein `T`-Befehl. Jeder Knopf hat einen festen Regelfilter, der auf dem Server liegt; so löst ein langsamer Klick bei 5-s-Tagen kein R2 oder R3 aus. Die Seite ist als Baum nach den orangen Status der Tafel aufgebaut. „Letzte Läufe“ und die grauen Hero-Namen sind entfernt. Records `a7598f2`, `5a309a2`.
2. Prüfung: Alle 26 Knöpfe offline gegen die echte Logik durchgespielt, mit 10 s und 180 s Pause: 0 Abweichungen, 0 doppelte Aktionen. Echter Klick auf der Seite: Lauf 55382 success, 0 Aktionen. Die Seite habe ich kalt mit Python Playwright (`channel="chrome"`) gefahren.

### Hero-Reiter Typ 72627
1. Matthias hat die Reiter im Hero-UI umbenannt (Firmeneinstellungen > Projekttypen > Wärmepumpen 2.0 Test), ich habe ihn Schritt für Schritt geführt. Nach jedem Speichern per API zurückgelesen: IDs und Status-Codes unverändert. Neu: „Termin bestätigt“ 857884 (Code 1101). Record `0600897`.
2. R21 schreibt jetzt Logbuch + Status 857884 (Regeldatei, Tests `2578ea5`, Logik 332 PASS; mit der alten Regeldatei werden genau die 3 neuen Tests rot).

---

## Key Decisions Made
### Testtag nur am Duplikat
- **Choice:** 1 Tag = 5 s. Hero-Fälligkeiten bleiben echte Tage. Das Original verweigert das Feld.
- **Rationale:** Tobias und Sabine sollen den Ablauf in Minuten durchspielen, und das Original darf nie mit Testzeit laufen.

### Reiter wie auf der Tafel
- **Choice:** Namen exakt wie die Tafel, ohne Emojis, nur „Termin bestätigt“ neu. Planung, Angebotserstellung und Abgeschlossen bleiben.
- **Rationale:** Owner-Antworten. Hero sortiert nach Status-Code, dann nach Reihenfolge, deshalb lassen sich Reiter nicht frei verschieben.

### Reihenfolge bis zur Übergabe
- **Choice:** Erst Duplikat (nur an Matthias), dann sein Probedurchlauf, dann Empfänger zurück und Release 8 am Original.
- **Rationale:** Owner will vor dem Verschicken selbst einmal durch.

---

## What Did NOT Work (and why)
- **Laufdaten über den n8n-HTTP-Knoten auf der Seite anzeigen:** Umlaute kamen als falsche Bytes an (`E7 9B B2` statt „ä“). v1 ging mit diesem Fehler als „bekannte Grenze“ raus. v2 nimmt die Texte aus der Regeldatei, danach wurde der Abschnitt ganz entfernt.
- **Playwright MCP:** `ECONNREFUSED :9222`, weil kein CDP lief. Python Playwright mit `channel="chrome"` funktionierte.
- **`process.exit` mit offenen fetch-Handles (Windows):** libuv-Assertion. Ersetzt durch if/else ohne exit.
- **Erstes Fahrskript mit `reload`:** kollidierte mit dem Meta-Refresh der Seite. Ersetzt durch eine `goto`-Schleife, die nur liest.
- **Override für das sichere Fenster im Auto-Modus:** Der Klassifizierer hat es abgelehnt. Nicht umgangen, gebaut erst nach dem Moduswechsel durch den Owner.
- **`duplikat-umbauen.mjs` mit neuem Hero-Schritt:** Die Wache verweigerte die CFG-Änderung `schritte`, bevor etwas geschrieben wurde. `schritte` ist jetzt erlaubt.
- **`T --abnahme` im Nur-Matthias-Modus:** Der Starter verlangt die Team-Empfänger und verweigert deshalb (so gewollt). Abnahme stattdessen über einen harmlosen Seitenklick.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| agentic-ops: tools/ww-vertrieb-logic.mjs | edit | `tagMs`, Prüfung `test_tag_sekunden` |
| agentic-ops: tools/ww-vertrieb-release-72627.mjs | edit | Testtag fürs Original verweigert |
| agentic-ops: tools/ww-vertrieb-{logic,guards,release-72627}-test.mjs | edit | Testtag- und R21-Tests |
| agentic-ops: workspace/clients/warme-wimmer/{infrastructure.yaml, specs/1-spec/a5-vertriebsprozess.md, automations/w2-14-*.n8n.json} | edit | Release 6/7, Duplikat, Startknopf, Hero-Reiter |
| agentic-ops: workspace/clients/warme-wimmer/context/vertrieb-rules.json (gitignored) | edit | R7-Texte, R21 → 857884, Schritt 857884 |
| agentic-ops: .scratch/ww-sales-72627/tools/{testlauf-duplikat,duplikat-umbauen,startknopf-bauen}.mjs (gitignored) | create/edit | `--sofort`, Duplikat-Umbau, Startseite |
| memory/project_ww_w214_test_duplicate.md | edit | aktueller Stand |

---

## Current Status
Lesend um 22:00 Berlin geprüft: Original `a9f98291` aktiv, R21 nur Logbuch, Team-Empfänger. Duplikat `464cf15e` aktiv, Empfänger nur Matthias, Testtag 5 s, R21 Logbuch + Status 857884. Startknopf `bf19b2f4` aktiv. Entwurf = veröffentlicht bei allen dreien. PR #305 offen. Ops-Status: In diesem Repo gibt es keine infrastructure.yaml, sie liegt in agentic-ops.

---

## Next Steps
1. Matthias' Probedurchlauf: HUK-106489 zurücksetzen (Termin löschen, 6 TEST-Aufgaben vom 12.10. abhaken, Status Erstgespräch), dann die Seite von oben. Nach jedem Abschnitt Hero und Duplikat zurücklesen.
2. Nach „fertig“: `node .scratch/ww-sales-72627/tools/duplikat-umbauen.mjs --tag-sekunden 5 --apply`, dann `node .scratch/ww-sales-72627/tools/startknopf-bauen.mjs --apply`. Prüfen: Die Seite nennt Sabine, Tobias und Matthias, und `T --abnahme --sofort` läuft wieder.
3. Release 8 am Original (Mo–Fr ab 20:00 Berlin): `node tools/ww-deploy-vertrieb.mjs --aus .scratch/ww-sales-72627/candidate-r8.json` bauen. Trockenlauf mit `--pins-aus-bericht workspace/clients/warme-wimmer/context/maintenance/2026-10-13-w214-72627-release-auf-12367bfd.json --kandidat .scratch/ww-sales-72627/candidate-r8.json`, dann `--apply … --testlauf-cred-id DWE4TI9mE7L9Gsmb`. Danach prüfen und in Spec, infrastructure.yaml und Export eintragen.
4. Den Eintrag `test_duplikat_2026_10_13` in infrastructure.yaml nachziehen (Duplikat-Version, Knopf b2, Empfänger), dann gibt Matthias den Link an Tobias und Sabine.
5. `MEMORY.md` auf unter 17 KB kürzen (jetzt 22,2 KB).
6. Noch offen von früher: Notiz „3 Entscheiden“ verweist noch auf die gelöschte Kopfnotiz; bei W2-06 ist unbelegt, ob `end` Ortszeit oder UTC ist.

---

## Context for Next Session
### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md`
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\infrastructure.yaml` (Einträge `test_duplikat_2026_10_13`, `hero_typ_72627_reiter_2026_10_14`)

### Open Questions
- Soll die Spec a5 von `1-spec/` nach `3-test/`?

### Working Notes
- Startseite: Der Link steht nur lokal in `.scratch/ww-sales-72627/startknopf.json`. Er gehört nicht ins öffentliche Repo, weil jeder mit dem Link Läufe auslösen kann.
- Der Startknopf liest n8n über die Credential `WW Watchdog n8n API` (`lWs8LWuYYPMCcgoC`). Sie läuft am 13.12. ab, dann geht der Knopf nicht mehr.
- Offline-Simulation aller Knöpfe: `knopf-sim.mjs` im Scratchpad dieser Sitzung (liest `.scratch/ww-sales-72627/work/startknopf-kandidat.json`). Bei einem neuen Knopf die Soll-Zeilen ergänzen.
- Aufräumen nach der Testphase (nicht jetzt): beide Workflows deaktivieren, Testtabelle `nnnYVH7709ySG347` löschen, TEST-Aufgaben weich löschen, HUK-106489 zurück auf Erstgespräch.

### Reference Materials
- PR https://github.com/akkton/agentic-ops/pull/305

---

## How to Continue
In `C:\Users\neuma_p1qrsic\Repo\agentic-ops` arbeiten. Auf Matthias' „fertig“ warten, dann Next Steps 2 bis 4 in dieser Reihenfolge.

---

## Strategic Feedback

### What Worked Well This Session
- Jeden Knopf vor der Auslieferung offline gegen die echte Logik mit zwei Klickpausen simuliert. So fiel auf, dass erst ein Regelfilter pro Knopf langsame Klicks bei 5-s-Tagen sicher macht.
- Hero-Umbenennung im UI: nach jedem Speichern per API gegengelesen statt am Ende einmal.

### Suggestions
- Eine Seite, die Daten aus n8n anzeigt, nie mit einem bekannten Anzeigefehler ausliefern. Die Texte von Anfang an aus der Quelle (Regeldatei) nehmen, nicht aus Laufdaten.

### System Health
- Autonomy: 2 Eingriffe (Moduswechsel für den Fenster-Override; Hero-Reiter nur im UI änderbar, Matthias hat geklickt). Dazu Owner-Entscheidungen zu Testtag, Seite, Texten, Reitern und Reihenfolge.
