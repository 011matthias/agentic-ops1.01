# Checkpoint: WW W2-14 Kalender-Ortszeit und R20-Titel

**Date:** 2026-10-13
**Status:** Release 5 live (Kalender-Ortszeit); Release 6 (R20-Titel) gebaut und getestet, NICHT veröffentlicht

---

## Summary
Zwei Fehler aus dem internen Testlauf auf W2-14 (Wärme Wimmer, Projekttyp 72627) behoben. Hero liefert Kalenderzeiten als Berliner Ortszeit mit falscher `+00:00`-Kennzeichnung (Release 5, live); Hero lehnt Aufgabentitel mit `;` ab (Release 6, wartet auf das Fenster).

Arbeitsort: Clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops`, Branch `client/warme-wimmer/w2-14-sales-process-72627`, PR akkton/agentic-ops#305. Dieses Repo (agentic-ops1) hat keinen WW-Ordner.

---

## What Was Done This Session
### Release 5: Kalenderzeiten
1. Ursache belegt: Termin 6511615 zeigt in Hero 10:00, API liefert `10:00:00+00:00`. Zweiter Beleg lesend: 400 Winter- und 400 Sommertermine haben beide die Spitze bei 08:00.
2. Fix `4549238`: `heroKalenderMs()` in `tools/ww-vertrieb-logic.mjs`, Europe/Berlin per Intl, nur `+00:00`/`Z` akzeptiert, sonst warten die Regeln. Logik-Suite 304 → 323 PASS, vorher 21 FAIL, `regress_check` 16 FAIL.
3. Veröffentlicht `0f6e58df-2d55-4291-8b55-153df4a78493` (Owner-Ja, 22:28 UTC), Abnahmelauf 52237 success, ledger 13, HUK-106488 unverändert. Veröffentlichter Knotencode auf der echten Nutzlast: 10:00 Uhr (Release-4-Code: 12:00).
4. Record `1f13f71` (Export, Spec a5, infrastructure.yaml; Release 3 und 4 nachgetragen).

### Release 6: R20-Titel
1. Ursache `;` im R20-Titel (Hero 422 `_noSpecialChars`). Belege lesend: 6000 Titel, keiner mit `;`; API-Titel (Autor 0, gleiche Mutation) mit `ü`. Kein `ü`-Test nötig, keiner ausgeführt.
2. Fix `8b49e5e`: `konfigPruefen` verweigert Titelzeichen außerhalb der belegten Allowlist; R20-Titel in der Regeldatei ohne `;`. Guards 154 → 167 PASS, `regress_check` 10 FAIL.
3. Kandidat `candidate-r6.json` (sha256 58dd874c…), Trockenlauf sauber (errors [], Diff nur Kandidaten + Faellige Aktionen).

---

## Key Decisions Made
### Kalenderzeit als Ortszeit lesen
- **Choice:** Kennzeichnung ignorieren, Uhrzeit als Europe/Berlin lesen; andere Kennzeichnung = unbekannt.
- **Rationale:** Beleg aus zwei Jahreszeiten; ein Formatwechsel bei Hero soll sichtbar werden statt still falsch zu laufen.

### Titelzeichen als Allowlist
- **Choice:** nur belegte Zeichen erlauben, nicht nur `;` verbieten.
- **Rationale:** `;` ist der einzige belegte Verursacher, aber ein ungeprüftes Zeichen scheitert erst live in Hero.

---

## What Did NOT Work (and why)
- **Worktree mit Standard-`autocrlf=true`:** zwei Verdrahtungstests der Release-Suite scheiterten ohne jede Änderung, weil die Quelle CRLF statt LF hatte. Worktree mit `-c core.autocrlf=false` neu angelegt, danach grün.
- **Hintergrundwarten auf die Testsperre bis 03:30 UTC:** die Sperre war nie fünf Minuten frei, das Ende wurde erst um 07:04 UTC gesehen (Rechner wahrscheinlich im Ruhezustand, nicht geprüft). Fenster Mo-Fr 06:00-19:59 zu, Release 6 nicht veröffentlicht.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| agentic-ops: tools/ww-vertrieb-logic.mjs | edit | heroKalenderMs, Titel-Allowlist |
| agentic-ops: tools/ww-vertrieb-logic-test.mjs, -build-test.mjs, -guards-test.mjs | edit | Regressionstests, Fixtures im Hero-Format |
| agentic-ops: workspace/clients/warme-wimmer/{infrastructure.yaml, specs/1-spec/a5-*.md, automations/w2-14-*.n8n.json} | edit | Release 5 protokolliert |
| agentic-ops: context/vertrieb-rules.json (gitignored) | edit | R20-Titel ohne `;` |
| agentic-ops: .scratch/ww-sales-72627/release-runbook.md | edit | Abschnitte 5d und 5e |

---

## Current Status
Original W2-14 `NPHbbRF2NVAbUyzF` steht auf `0f6e58df` (Release 5), Testmodus. Zeitplanläufe seit 06:05 Berlin alle success. Branch gepusht bis `8b49e5e`. PR #305 nicht gemergt. Das Duplikat `tB5anuCbpmYsrA7K` läuft noch mit altem Code. Ops-Status: keine infrastructure.yaml in diesem Repo.

---

## Next Steps
1. Release 6 ab Mo 20:00 Berlin: **neues Owner-Ja holen** (das Ja galt „sobald die Sperre frei ist“), Suiten und Trockenlauf wiederholen, Sperre frei und HUK-106489 in einem Regelschritt prüfen, dann `--apply` (Befehl in Runbook 5e, gepinnt auf `context/maintenance/2026-10-11-w214-72627-release-auf-7ec5e029.json`).
2. Bis dahin R20 (Runbook 8.12/8.13) nicht auf dem Original laufen lassen.
3. Nach Release 6: Runbook 5e auf DONE, Spec a5 `last_changes`, infrastructure.yaml, Export, Push.
4. Notiz „3 Entscheiden“ verweist noch auf die gelöschte Kopfnotiz (nächstes Release).
5. W2-06: ob der Webhook-`end` Ortszeit oder echtes UTC liefert, ist nicht belegt.

---

## Context for Next Session
### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (5d, 5e, 6, 7, 8)
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\specs\1-spec\a5-vertriebsprozess.md`

### Open Questions
- Gilt das Owner-Ja für Release 6 nach der Pause noch?
- Soll die Spec von `1-spec/` nach `3-test/` (Stage-Wache meldet Mismatch, schon vorher so)?

### Working Notes
- Hero schreibt Kalenderzeiten als Ortszeit mit `+00:00`; `created` und Status-Zeitstempel sind echtes UTC.
- Hero-Aufgabentitel: belegt sind Buchstaben, Ziffern, Leerzeichen, Umlaute, ß und `. , : ( ) - / [ ] + ? !` sowie `→`.
- Release-Tooling: Sperrdatei `.scratch/ww-sales-72627/w214-testlauf.lock` gehört der Testsitzung, nie löschen.
- Rot-Nachweise liegen in `.scratch/ww-sales-72627/work/` (`tz-rot-vor-fix.txt`, `r6-rot-*.txt`).

### Reference Materials
- PR https://github.com/akkton/agentic-ops/pull/305

---

## How to Continue
In `C:\Users\neuma_p1qrsic\Repo\agentic-ops` arbeiten, Runbook 5e lesen, Owner-Ja für Release 6 einholen.

---

## Strategic Feedback

### What Worked Well This Session
- Beleg vor Fix: zweiter Datenpunkt (800 Termine) und 6000 Titel lesend ausgewertet, bevor der Code geändert wurde.
- Red-vor-Fix, `regress_check` auf den Aufrufer, und der veröffentlichte Knotencode wurde offline auf der echten Nutzlast gegen den alten Code gegengeprobt.

### Suggestions
- Wartefenster nicht als Schleife mit Zeitlimit bauen, die bei Ruhezustand still ausläuft; besser eine geplante Wiederaufnahme oder ein Hinweis, dass nach dem Limit neu zu bestätigen ist.

### System Health
- Autonomy: 0 Eingriffe zum Entsperren; 2 Owner-Freigaben (Release 5, 6) und 1 Zusatzauftrag. Fully autonomous bis auf die Freigaben.
