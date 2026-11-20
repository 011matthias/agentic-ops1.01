# Mini-Checkpoint: GTA6 Publish Fixed Slots

**Date:** 2026-11-20
**Status:** p1 production running at three owner-approved videos a day; p2 publish built
**Type:** mini

---

## Summary

The owner set three posts a day at the best times for reach, TikTok and YouTube in sync. The engine now schedules a READY video on the next free slot (`clipengine publish`), and tonight's three slots are filled: m30 at 20:00, m23 at 00:00, m56 at 02:00. Two fetch failures seen live are fixed: a hung download blocked the whole run, and VOD time past 26:30 h could not be seeked.

## What Was Done

- Owner decisions: 3 a day at the best times. Slots are 20:00, 00:00 and 02:00 German time (14, 18 and 20 h US Eastern, from the 2026-11-19 research). m30 goes out "früher" than midnight. m23 and m56 were each approved from a 720p preview.
- m30-f1 scheduled 20:00 and m23-f1 00:00 by scratch script. m23 was re-cut to 45-105 s from the viewer-clip peaks (tackle 1860, scream 1870, taser 1880, swim 1882-1900 VOD s), with the edge accepted at 7.75 s (foot under the cam column) and 26 s (the game camera's own close-up). m56-f1 (caseoh_ swamp-buggy getaway, cut 7.6-67.6 s past the map and the pause blur) was READY on the first render and scheduled 02:00 through `clipengine publish`. All three are in iCloud and in sync.
- #1796 `clipengine publish`:
  - fixed slots, next free slot at least 20 min out, YouTube `publishAt`;
  - the same file plus caption goes into `~/iCloudDrive/GTA6 TikTok/` as `{slot} {id}.mp4`;
  - a `posts` table (one post per video and platform; the 8 `youtube.json` uploads imported) and a read-back after upload;
  - 11 CLI tests and 3 regress-checked guards. The live dry run refused m30 as already posted.
- #1797: a download timeout now kills yt-dlp's whole process tree. Tested with real processes and regress-checked.
- #1798: fetch leaves out clips past 26:25 h. Regress-checked.
- Judged 24 moments and kept only m56. The rejects broke down as:
  - licensed song or cutscene: m32;
  - nudity or sex: m34, m44, m48, m54;
  - too dark: m33;
  - no reaction from the streamer: m35;
  - menu: m38;
  - cam off: m42;
  - cafe cutscene: m59;
  - duplicates of posted videos: m40 = m9, m47 = m15, m53 = m18.
- The six Shorts had 0 to 4 views each after 20 h. Analytics returned no country or day rows yet.
- `yt_consent.py` now asks for `youtube.force-ssl`, because editing the six posted descriptions answered 403 "insufficient scopes". The consent page opened at 16:05 and waits until about 18:05. The six still carry the Twitch link.

## What Did NOT Work (and why)

- **subprocess.run timeout on yt-dlp:** it killed only yt-dlp. The orphaned ffmpeg held the pipes, and run() never returned (28 min on a 0-byte section). Fixed in #1797.
- **Fetching KaiCenat's 47.6 h VOD at 26:49 h and 29:03 h:** the MPEG-TS clock wraps at 2^33/90000 = 95443.7 s. ffmpeg opened segment 9654.ts, read wrapped timestamps and wrote nothing. Left out by #1798; segment-level download is not built.
- **Updating the posted descriptions with the upload token:** 403 insufficient scopes. Editing needs `youtube.force-ssl`.
- **Moving posted files into `iCloudDrive\GTA6 TikTok\gepostet\`:** within an hour iCloud put all six back at the top level, and the folder was empty.
- **regress_check with a bash `--test` command:** it runs through cmd.exe, which says "The system cannot find the path specified". The test command now goes in a .cmd wrapper.

## Current Status

Scheduled on YouTube (private until the slot) and in the iCloud folder: m30-f1 20 Nov 20:00, m23-f1 21 Nov 00:00, m56-f1 21 Nov 02:00. The next free slot is 21 Nov 20:00. No READY video is waiting. Unjudged layout-ready moments: m50, m58, m60, m63, m67, m68, m70, m72, m75, m76. stableronaldo (29k and 8k clip views) and TheBurntPeanut (19.5k) have sections but no layout. KaiCenat streams live on a new VOD, 2934866208.

## Next Steps

1. Fetch dedupe: m40, m47 and m53 came back because caseoh_'s VOD turned public, and judge was the only thing that caught them.
2. Fill the three 21 Nov slots.
3. Run analytics and the retention curve after the owner's consent.
4. Re-consent to fix the six descriptions.
5. On 22 Nov: `suggest`.

## Files to Read First

- workspace/projects/gta6-clipping/status/p1-clip-pipeline.md
- workspace/projects/gta6-clipping/engine/src/clipengine/publish.py
- workspace/projects/gta6-clipping/engine/src/clipengine/fetch.py (`plan_vod`, `_covered`, `run_killing_tree`)

## Continuation prompt

````text
/comd_resume gta6-clipping

GTA6-Clipping: drei Videos am Tag zu festen Zeiten (YouTube + TikTok synchron), Abruf-Dubletten schließen, Nachschub für die Slots ab 21.11. 20:00 (internes Projekt workspace/projects/gta6-clipping/).

## Stand (20.11.2026, ~17:10)

- Gemergt diese Sitzung: #1796 `clipengine publish` (feste Slots 20:00 / 00:00 / 02:00 deutsche Zeit, nächster freier Slot ≥ 20 min, YouTube privat mit publishAt, gleiche Datei + Text nach ~/iCloudDrive/GTA6 TikTok/ als "{Slot} {id}.mp4", Tabelle `posts`, die 8 früheren Uploads importiert, Rücklesen), #1797 (Download-Timeout killt yt-dlps ganzen Prozessbaum), #1798 (fetch lässt Clips nach 26:25 h aus: MPEG-TS-Uhr läuft bei 26:30 h über). Checkpoint: docs/2026-11-20 - GTA6 Publish Fixed Slots/Mini-Checkpoint-1.md.
- Eingeplant (je mit Owner-OK aus 720p-Vorschau, alle in iCloud synchron): m30-f1 20.11. 20:00, m23-f1 21.11. 00:00, m56-f1 (caseoh_ Sumpf-Buggy, "worst getaway vehicle") 21.11. 02:00. Nächster freier Slot: 21.11. 20:00. Kein READY-Video auf Halde.
- Die sechs Shorts vom 19.11.: nach 20 h je 0 bis 4 Aufrufe; Analytics ohne Länder-/Tageszeilen (YouTube liefert erst nach 1-2 Tagen). Ihre YouTube-Beschreibungen tragen noch den Twitch-Link: Bearbeiten braucht `youtube.force-ssl`; engine/data/publish/yt_consent.py fragt es jetzt mit ab; die Freigabeseite war 16:05-18:05 offen (scratchpad consent.log prüfen, ob der Owner bestätigt hat). Nach erteilter Freigabe: Beschreibungen per videos.update auf "Titel + 4 Hashtags" setzen (Muster: scratchpad yt_schedule.py, FIX-Teil), danach zurücklesen.
- iCloud: Verschieben der geposteten Dateien in einen Unterordner hält nicht (iCloud legt sie zurück); gepostete Dateien haben keinen Slot im Namen, fällige schon.
- Abruf 20.11.: 44 neue Momente. Beurteilt und verworfen: 32-35, 38, 40, 42, 44, 47, 48, 53, 54, 59 (Song/Zwischensequenz, Nacktheit, zu dunkel, kein Kommentar, Menü, Cam aus, Dubletten). Offen mit Layout: m50 (caseoh_ "Heroic case", Pausenmenü mitten im Schnitt), m58 (jasontheween "We like that"), m60 (xQc "refuses to leave the club", vermutlich Stripclub), m63 (caseoh_), m67/m75/m76 (ohnePixel, wenig Aufrufe), m68/m72 (jasontheween), m70 (xQc). Ohne Layout, aber stark: stableronaldo (29k und 8k Clip-Aufrufe), TheBurntPeanut (19,5k; PNG-Avatar, Owner-Frage offen). KaiCenat streamt live auf VOD 2934866208 (seit 20.11. 12:39 UTC).
- Live-Fakten: vod_offset = Clip-Ende; Twitch-VODs enden bei 48 h; Segmente über 26:30 h lassen sich per ffmpeg-Seek nicht holen; die Engine-.venv ist gesperrt, solange ein clipengine.exe läuft (Tests dann mit UV_PROJECT_ENVIRONMENT auf eine Scratch-venv); regress_check startet --test über cmd.exe (Befehl in .cmd-Datei legen); publish braucht `--extra publish`, immer zusammen mit `--extra gpu --extra dev`, damit uv die Umgebung nicht umbaut.

## Feste Owner-Regeln

- Keine API-LLM-Kosten; Urteilsarbeit im Gespräch. Clips auf Englisch. Titel nennt den Streamer wie im Register.
- Länge etwa 1 Minute (max 60 s). Hook nennt GTA6. Gameplay füllt das Band, Hauptobjekt ganz sichtbar, kein Blur. Menüs fallen durch (Witz-Menü per `--accept-band GRUND`); Objekt am Rand vor einem Overlay per `--accept-edge GRUND`. Clips ohne Worte erlaubt.
- Posten nur mit Owner-OK pro Video (Vorschau 720p per SendUserFile + AskUserQuestion). Beschreibungen ohne Twitch-Link; Namensschild im Video bleibt.
- NEU 20.11.: drei Videos pro Tag, feste Slots 20:00, 00:00, 02:00 deutsche Zeit, TikTok und YouTube synchron. Veröffentlichen nur über `clipengine publish ID` (Probelauf, dann `--go`). Der Owner postet TikTok selbst vom iPhone aus dem iCloud-Ordner zur Uhrzeit im Dateinamen.

## Aufgabe, in dieser Reihenfolge

1. Abruf-Dubletten schließen: Wird ein VOD öffentlich, plant fetch Clips erneut ein, die über den Clip-Pfad (Sections kind 'clip', video_id NULL) schon Momente haben (m40=m9, m47=m15, m53=m18; caseoh_ VOD 2932628190). fetch soll Intervalle überspringen, deren Top-Clip (oder ein Clip darin) schon zu einer Section gehört; zusätzlich publish gegen gleiche Quelle sperren. Test über die CLI, regress_check.
2. Nachschub für 21.11. 20:00 / 22.11. 00:00 / 02:00: offene Momente oben beurteilen (Kontaktbögen per concat-Demuxer), rendern, Standbilder + Hook prüfen, Vorschau, Owner-OK, `clipengine publish`. Neue Kai-Aufnahme: `watch --only kaicenat`, `fetch --streamer kaicenat --top 15`, Cam-Position per Standbilder prüfen (`earlier`). Für stableronaldo ein Layout an Standbildern kalibrieren (config/layouts.yaml), wenn seine Momente taugen.
3. 21.11.: Zahlen aller geposteten Shorts (YouTube Analytics: Views, averageViewPercentage, Länder; dimension video braucht maxResults + sort), Retention-Kurve (elapsedVideoTimeRatio) erstmals; Länderanteil prüft die Slot-Annahme (US-Publikum).
4. Freigabe: Hat der Owner force-ssl bestätigt, Beschreibungen der sechs korrigieren; sonst vor dem 26.11. erneut öffnen (yt_consent.py, läuft im Hintergrund mit timeout).
5. Am 22.11. (nicht früher): `suggest --since 72h`, Streamer tauschen; LIRIK (keine Cam) und TheBurntPeanut (PNG-Avatar) mit dem Owner klären.
6. Segmentweiser Download für VOD-Zeit über 26:30 h (Twitch chunked/N.ts direkt holen und zusammenfügen).
7. Band-Check-Lücke: doppelte Cam/Chat im Band und gezoomte Karte fallen nicht auf.

## Wartet auf den Owner

OK pro Video für jeden Slot; Freigabe force-ssl (erneuert auch den 7-Tage-Token); LIRIK und TheBurntPeanut; Kontakt-E-Mail für Takedowns; Screenshot Kontostatus altes TikTok-Konto.

## Wie arbeiten

- Eigener Worktree off origin/main (../agentic-ops1-gta6-p12 existiert; vor jedem neuen Branch `git fetch origin`, dann `git switch -C <branch> origin/main`). Schwester-Sessions laufen im Haupt-Checkout. Nie git stash.
- Ein PR pro Thema; Ship-Kette autonom; `gh pr checks --watch` im Vordergrund; `gh pr merge N --repo 011matthias/agentic-ops1.01 --squash --delete-branch` als EIGENER Aufruf ohne vorangestelltes cd.
- Engine-Befehle aus dem Worktree-engine-Ordner mit `env VIRTUAL_ENV= uv run --extra gpu --extra dev clipengine ...` (publish zusätzlich `--extra publish`); Daten unter engine/data/ des Haupt-Checkouts.
- Tests offline gegen Fakes; pro Fix mindestens ein Test über die CLI; `uv run tools/regress_check.py` zeigt rot.
- Fertige Videos per Standbildern prüfen (Cam-Band, Overlay im Gameplay-Band, Hook in den ersten 3 s). Dubletten gegen schon gepostete Quellen prüfen, bevor ein Moment behalten wird.
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
