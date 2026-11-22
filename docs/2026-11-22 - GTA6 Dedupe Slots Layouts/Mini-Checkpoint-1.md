# Mini-Checkpoint: GTA6 Dedupe Slots Layouts

**Date:** 2026-11-22
**Status:** p1 production, p2 publishing on fixed slots
**Type:** mini

---

## Summary
Fetch and publish no longer let a clip-path moment come back once its VOD turns public; the next three slots carry owner-approved videos; the six 19.11. YouTube descriptions are fixed; the first Analytics pull shows the Shorts are barely distributed (0 to 4 views each).

## What Was Done
- #1800: `fetch` skips a VOD interval whose clips a fetched clip-path section holds (note line "N already fetched as clips before the VOD was public"); `publish` refuses a video whose top clip or VOD stretch matches a posted video or an earlier one in the same run, and refuses when a posted video's `edl.json` is gone. CLI tests, regress_check red/green on both wiring points, live read-only check matched m40/m47/m53 to m9/m15/m18.
- #1802: `config/layouts.yaml` Lacy (cam `[0, 0, 494, 278]`), ohnePixel gameplay `[680, 0, 1240, 1080]` (his cut-out cam had shown in the band of m76).
- Judged 24 moments. Kept m50 (caseoh_, bridge throwers, cut 36.5 to 72.2 s), m46 (Lacy and the dog, 47.5 to 99.5 s), m76 (ohnePixel dirt bike race, 11.5 to 71 s, `--accept-edge` at the start lineup). Rejected (adult, cutscene, IRL, trailer) and recorded via `judge`: 36, 37, 39, 41, 43, 49, 58, 60, 63, 67, 68, 70, 72, 75; 45, 52, 55, 62 (Lacy: shower, body joke, story dialogue) read but not yet recorded.
- Owner OK per video, then `clipengine publish`: m46 22.11. 20:00, m50 23.11. 00:00, m76 23.11. 02:00 (YouTube read back private + publishAt, files + captions in the iCloud TikTok folder). Slots 21.11. 20:00 to 22.11. 02:00 went unused (the session waited on the owner's answer).
- force-ssl consent granted 20.11. evening (token renewed, all four scopes); six descriptions set to title + 4 hashtags via `videos.update`, read back without Twitch link, tags kept.
- Analytics 22.11.: nine public Shorts, 0 to 4 views each, 12 in total; per-video average view 25 to 28 %; Analytics rows only through 19.11., no country or retention rows yet.
- KaiCenat: watch + `fetch --top 15` on 22.11.: VOD 2934866208 15 sections (top 2,877 / 2,177 views), VOD 2935613960 6 sections (top 1,390 / 1,247); VOD 2936683310 still live with lagging counts.

## What Did NOT Work (and why)
- **ffmpeg drawtext on contact sheets:** Fontconfig has no default config here, every drawtext call segfaults; tile unlabelled frames in a known order.
- **Planning Kai's live VOD on 20.11.:** fresh clips showed at most 29 views, so no interval reached 50; two days later the same VOD planned 15 sections.
- **Trusting the render checks:** m50 passed while ending 3.5 s into a blurred pause menu, m76 passed with ohnePixel's cam in the band; stills caught both (item 7).

## Current Status
Booked through 23.11. 02:00; nothing READY beyond. 21 KaiCenat sections fetched, not analyzed. YouTube token valid to about 27.11. (test-mode app, 7 days from 20.11.). Status file updated 2026-11-22.

## Next Steps
1. Analyze and judge the 21 new KaiCenat sections; check his cam position on stills first (`earlier` in layouts.yaml if it moved).
2. Fill slots from 23.11. 20:00 (preview 720p, owner OK per video, `clipengine publish`).
3. Raise with the owner: Shorts at 0 to 4 views after 3 days.
4. `suggest --since 72h`, swap streamers; LIRIK and TheBurntPeanut owner questions.
5. Segment download past 26:30 h; band check for blurred pause menus and a second cam.

## Files to Read First
- workspace/projects/gta6-clipping/status/p1-clip-pipeline.md
- workspace/projects/gta6-clipping/engine/README.md (publish paragraph)

---

## Continuation prompt

````
/comd_resume gta6-clipping

GTA6-Clipping: drei Videos am Tag zu festen Zeiten (YouTube + TikTok synchron), Nachschub ab 23.11. 20:00, Reichweite der Shorts klären (internes Projekt workspace/projects/gta6-clipping/).

## Stand (22.11.2026, ~05:00)

- Gemergt diese Sitzung: #1800 (fetch überspringt VOD-Intervalle, deren Clips schon über den Clip-Pfad geholt sind; publish sperrt ein Video, dessen Top-Clip oder VOD-Strecke einem geposteten oder einem früheren im selben Lauf gleicht, und sperrt, wenn ein gepostetes Video kein edl.json mehr hat), #1802 (Layout Lacy neu, ohnePixel-Gameplay rechts seiner Cam). Checkpoint: docs/2026-11-22 - GTA6 Dedupe Slots Layouts/Mini-Checkpoint-1.md.
- Eingeplant mit Owner-OK: m46 (Lacy und der Hund) 22.11. 20:00, m50 (caseoh_, Brückenwerfer) 23.11. 00:00, m76 (ohnePixel, Dirtbike-Rennen) 23.11. 02:00. Nächster freier Slot: 23.11. 20:00. Kein READY-Video auf Halde. Die Slots 21.11. 20:00 bis 22.11. 02:00 blieben leer.
- Beschreibungen der sechs Shorts vom 19.11. korrigiert (Titel + 4 Hashtags, zurückgelesen). Token seit 20.11. mit force-ssl; Testmodus, also bis etwa 27.11. erneuern (engine/data/publish/yt_consent.py mit CONTEXT_DIR, im Hintergrund mit timeout).
- Zahlen 22.11.: neun öffentliche Shorts, je 0 bis 4 Aufrufe (zusammen 12) nach 1 bis 3 Tagen, durchschnittlich 25 bis 28 % gesehen; Analytics hat Zeilen nur bis 19.11., keine Länder- oder Retention-Zeilen. Skript: Scratchpad yt_stats.py der Sitzung 3bb5b61f (liest posts, maxResults + sort, Retention pro Video).
- Beurteilt und verworfen (per judge eingetragen): 36, 37, 39, 41, 43, 49, 58, 60, 63, 67, 68, 70, 72, 75 (Nacktheit, Stripclub, Zwischensequenz, IRL, Trailer). Gelesen, aber noch nicht eingetragen: 45, 52, 55, 62 (Lacy: Dusche, Körper-Witz, Story-Dialog) → reject. Noch offen ohne Urteil: 51, 61, 65, 69 (stableronaldo, ohne Layout), 57, 64, 71 (TheBurntPeanut), 66, 73, 74 (LIRIK), 77-79 (IShowSpeed, wenig Aufrufe).
- KaiCenat abgerufen 22.11.: VOD 2934866208 15 Abschnitte (stärkste 2.877 und 2.177 Aufrufe), VOD 2935613960 6 Abschnitte (1.390 und 1.247); nicht analysiert. VOD 2936683310 läuft noch (frische Clips zeigen stundenlang fast 0 Aufrufe, deshalb plant fetch dort nichts).
- Live-Fakten: ffmpeg drawtext stürzt ab (kein Fontconfig): Kontaktbögen ohne Beschriftung kacheln; der Band-Check übersieht ein verschwommenes Pausenmenü (m50) und eine zweite Cam im Band (m76): Standbilder bleiben Pflicht; `--accept-edge` für ohnePixel, wenn der Fahrer am linken Rand des neuen Rechtecks steht.

## Feste Owner-Regeln

- Keine API-LLM-Kosten; Urteilsarbeit im Gespräch. Clips auf Englisch. Titel nennt den Streamer wie im Register.
- Länge etwa 1 Minute (max 60 s). Hook nennt GTA6. Gameplay füllt das Band, Hauptobjekt ganz sichtbar, kein Blur. Menüs fallen durch (Witz-Menü per `--accept-band GRUND`); Objekt am Rand vor einem Overlay per `--accept-edge GRUND`. Clips ohne Worte erlaubt.
- Posten nur mit Owner-OK pro Video (Vorschau 720p per SendUserFile + AskUserQuestion). Beschreibungen ohne Twitch-Link; Namensschild im Video bleibt.
- Drei Videos pro Tag, feste Slots 20:00, 00:00, 02:00 deutsche Zeit, TikTok und YouTube synchron. Veröffentlichen nur über `clipengine publish ID` (Probelauf, dann `--go`). Der Owner postet TikTok selbst vom iPhone aus dem iCloud-Ordner zur Uhrzeit im Dateinamen.

## Aufgabe, in dieser Reihenfolge

1. Kai-Nachschub: `analyze` für die 21 neuen Abschnitte, Cam-Position auf Standbildern der neuen VODs prüfen (rückt sie, Eintrag unter `earlier` in config/layouts.yaml), Kontaktbögen per concat-Demuxer, judge, render, Standbilder + Hook prüfen, Vorschau, Owner-OK, `clipengine publish` ab 23.11. 20:00. Vorher 45, 52, 55, 62 als reject eintragen.
2. Owner fragen, mit Zahlen: die Shorts bekommen 0 bis 4 Aufrufe, YouTube testet sie offenbar kaum (neuer Kanal, wiederverwendete Inhalte?). Wie laufen dieselben Videos auf TikTok? Weiter wie bisher oder Format ändern (eigener Kommentar, Zusammenschnitte)?
3. Ab 23.11. Analytics erneut (yt_stats.py): Länder, Retention-Kurve (elapsedVideoTimeRatio) erstmals; Länderanteil prüft die Slot-Annahme (US-Publikum).
4. Ab 22.11. abends: `suggest --since 72h`, Streamer tauschen; LIRIK (keine Cam) und TheBurntPeanut (PNG-Avatar) mit dem Owner klären; stableronaldo-Layout nur, wenn seine Momente taugen (bisher alle verworfen).
5. Token vor dem 27.11. erneuern (yt_consent.py).
6. Segmentweiser Download für VOD-Zeit über 26:30 h (Twitch chunked/N.ts direkt holen und zusammenfügen).
7. Band-Check-Lücke: verschwommenes Pausenmenü, doppelte Cam/Chat im Band, gezoomte Karte.

## Wartet auf den Owner

OK pro Video für jeden Slot; Antwort zur Reichweite (Punkt 2); LIRIK und TheBurntPeanut; Kontakt-E-Mail für Takedowns; Screenshot Kontostatus altes TikTok-Konto.

## Wie arbeiten

- Eigener Worktree off origin/main (../agentic-ops1-gta6-p12 existiert; vor jedem neuen Branch `git fetch origin`, dann `git switch -C <branch> origin/main`). Schwester-Sitzungen laufen im Haupt-Checkout. Nie git stash.
- Ein PR pro Thema; Ship-Kette autonom; `gh pr checks N --watch` im Vordergrund; `gh pr merge N --repo 011matthias/agentic-ops1.01 --squash --delete-branch` als EIGENER Aufruf ohne vorangestelltes cd.
- Engine-Befehle aus dem Worktree-engine-Ordner mit `env VIRTUAL_ENV= uv run --extra gpu --extra dev --extra publish clipengine ...`; Daten unter engine/data/ des Haupt-Checkouts.
- Tests offline gegen Fakes; pro Fix mindestens ein Test über die CLI; `uv run tools/regress_check.py` zeigt rot (Testbefehl in eine .cmd-Datei legen).
- Fertige Videos per Standbildern prüfen (Cam-Band, Overlay im Gameplay-Band, Hook in den ersten 3 s, Ende ohne Menü). Dubletten fängt publish jetzt selbst.
- Skripte und Texte über 80 Zeilen nie per Heredoc: Write oder Edit.
- Höchstens 3 Versuche pro Fehler, danach AskUserQuestion. Owner-Entscheidungen mit Standbildern und AskUserQuestion; Deutsch, Alltagssprache.
- Das Repo ist öffentlich: keine Adressen, Tokens, Kontodaten, Kanal- oder Video-IDs in getrackte Dateien.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume gta6-clipping`; where it stands (what shipped this session with PR numbers, what is in flight and why, what waits on the owner); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any other paste-ready prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty, do not write another prompt: say the loop is done and list what shipped and what waits on the owner.
````
