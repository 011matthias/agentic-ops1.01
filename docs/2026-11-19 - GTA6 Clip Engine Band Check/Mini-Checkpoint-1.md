# Mini-Checkpoint: GTA6 Clip Engine Band Check

**Date:** 2026-11-19
**Status:** band check shipped (#1778), owner decisions on wide objects and joke menus plus 13 packages judged (#1779), caption check by time (#1780); six videos READY, not posted
**Type:** mini

---

## Summary
The gameplay band is now checked for black, paused and menu stretches. All 13 open review packages are judged. The owner decided two open rules on stills, and four new videos rendered READY.

## What Was Done
- `produce.band_stretches` (#1778): per sample at 4 fps, caption rows left out. Black = 95th-percentile brightness under 10, paused = change under 0.25, menu = brightness over 60 with sharpness under 6 and change under 4; a stretch counts from 3 samples (0.75 s). Calibrated on 21 sections (7,260 samples), each flagged run checked on a contact sheet; the real functions were run on band-shaped cuts (paused map, fade, PS5 screen fail; night, dusk, dim red club pass).
- Owner, on stills (#1779): an object wider than the window keeps the band filled (`object_wider_s` recorded, no failure); a menu that belongs to the moment passes per video via `render ID --accept-band REASON`.
- 13 packages judged: kept 6 (xQc NPC), 9 (caseoh_ seaplane), 16 (jasontheween robbery, cut 22.9-48.58), 18 (caseoh_ respray, cut 0-37, menu accepted); rejected 2, 7, 11, 13, 14, 17, 19, 20, 21. Layout profiles xqc and jasontheween.
- READY in data/ready/: m5 (wheel accepted), m15, m6 (42.4 s), m9 (35.7 s), m16 (25.7 s), m18 (37.0 s); 720p previews and decision stills sent.
- `caption_drift` (#1780) matches the same word within 2 s instead of 6 heard words ahead; m16's old cut reproduced on real audio: 27.0 s before, 0.03 s after.
- 89 engine tests; regress_check bit on all 6 wiring points.

## What Did NOT Work (and why)
- **Mean band brightness as the dark signal:** night driving 8-29, a dim red club 11-18 and the bush 5-12 overlap; 95th-percentile brightness separates (fades 0, darkest night sample 14.6).
- **Share of texture-free 10x10 blocks as the map/menu signal:** fired on dusk skies, ocean, shower steam and letterbox cutscenes (corpus median 0.27) and still missed ohnePixel's zoomed map; dropped.
- **Sharpness under 8 with change under 4 as the menu rule:** night driving and the red club sit at sharpness 3-5; adding brightness over 60 (and sharpness under 6) fixed it.
- **caption_drift's 6-word lookahead:** Whisper heard 11 words of game dialogue first that the section transcript lacked; the caption "fucking" at 27.9 s paired with the game's at 0.9 s.
- **ffmpeg drawtext and `-pattern_type glob` on this machine:** drawtext segfaults (no Fontconfig), glob says "Function not implemented"; use the concat demuxer for contact sheets.
- **Test fake keyed on `-f null`:** it also answered render's loudnorm pass 1 ("loudnorm pass 1 failed"); keyed on `ebur128` instead.

## Current Status
Nothing posted. Six videos wait for the owner's verdict. Known gap in the band check: a map the streamer is zooming (moving, sharp) passes. jasontheween's chat overlay shows at the band's left edge when the window follows left. Context at close: about 440k.

## Next Steps
1. 22.11.: `uv run clipengine suggest --since 72h`, swap streamers who stopped playing GTA; settle LIRIK (no cam) and TheBurntPeanut (PNG avatar) with the owner there.
2. Second hand-started production run: fetch, analyze, judge, render for new moments (counts toward the three runs without intervention before p1.7).

## Files to Read First
- `workspace/projects/gta6-clipping/engine/src/clipengine/produce.py` (`band_stretches`, `check`, `caption_drift`)
- `workspace/projects/gta6-clipping/status/p1-clip-pipeline.md`
- `workspace/projects/gta6-clipping/engine/config/layouts.yaml`

---

## Continuation prompt

````
/comd_resume gta6-clipping

GTA6-Clipping: am 22.11. Streamer-Vorschläge prüfen und tauschen, dann ein zweiter Produktionslauf von Hand (internes Projekt workspace/projects/gta6-clipping/).

## Stand (19.11.2026, abends)

- Gemergt: #1778 (Band-Check: schwarze, stillstehende und Menü-Strecken ab 0,75 s im Gameplay-Band, Untertitelzeile ausgenommen; geeicht an 21 Abschnitten), #1779 (Owner-Entscheidungen: Objekt breiter als der Ausschnitt = Band bleibt gefüllt, nur vermerkt; Menü, das zum Moment gehört, darf pro Video mit Grund durch: `render ID --accept-band GRUND`; 13 Prüfpakete beurteilt; Layout-Profile xqc und jasontheween), #1780 (caption_drift ordnet Wörter nach Zeit zu, innerhalb 2 s). Checkpoint: docs/2026-11-19 - GTA6 Clip Engine Band Check/Mini-Checkpoint-1.md.
- READY, nicht gepostet, 720p-Vorschauen an den Owner geschickt: m5-f1 (ohnePixel Jet, Waffenrad akzeptiert), m15-f1 (caseoh_ Scooter), m6-f1 (xQc gegen NPC, 42,4 s), m9-f1 (caseoh_ Wasserflugzeug, 35,7 s), m16-f1 (jasontheween Überfall, 25,7 s, sein Chat-Overlay am linken Bandrand), m18-f1 (caseoh_ Lackiererei, 37,0 s, Menü akzeptiert).
- Alle 21 Momente beurteilt: 6 behalten, 15 verworfen. Keine offenen Prüfpakete.
- Band-Check-Lücke: eine Karte, die gerade gezoomt wird, fällt nicht auf (bewegt, scharf); im Kontaktbogen beim Urteil sichtbar.
- Live-Fakten: vod_offset ist das Clip-Ende; yt-dlp und Hugging Face nur über IPv4; NVENC läuft; 720p-Vorschau mit -b:v 3M bleibt unter 30 MB. Auf diesem Rechner segfaultet ffmpeg drawtext (kein Fontconfig) und `-pattern_type glob` geht nicht: Kontaktbögen über den concat-Demuxer.

## Feste Owner-Regeln

- Keine API-LLM-Kosten; Urteilsarbeit im Gespräch über das Abo. Clips auf Englisch. Jeder Titel nennt den Streamer.
- Länge etwa 1 Minute (cut_f1 zielt auf 55 s, max 60). Clip-only-Streamer (caseoh_, IShowSpeed) sind so lang wie der Clip.
- Der eingeblendete Hook nennt GTA6 (judge erzwingt es).
- Aufteilung (Facecam oben, Gameplay unten), Untertitel und Hook-Stil sind abgenommen.
- Das Gameplay füllt das ganze untere Band. Ist das Hauptobjekt breiter als der Ausschnitt, bleibt das Band gefüllt und die Ränder werden abgeschnitten (Owner 19.11.).
- Kein Blur im unteren Band. Menüs im Band fallen durch; gehört ein Menü zum Moment (Witz-Aufbau, kurzes Waffenrad), mit `--accept-band GRUND` durchlassen (Owner 19.11.).
- Kontakt-Adresse für die Kanalbeschreibung wird noch nicht gebraucht. Nichts posten.

## Aufgabe, in dieser Reihenfolge

1. Am 22.11. (nicht früher): `uv run clipengine suggest --since 72h`, Streamer tauschen, die kein GTA mehr spielen. Dabei mit dem Owner per AskUserQuestion klären: LIRIK hat keine Facecam und TheBurntPeanut nur einen PNG-Avatar; beide passen nicht ins Cam-oben-Format (tauschen oder eigenes Layout). Momente von beiden wurden deshalb verworfen (7, 21 LIRIK; 17, 19 TheBurntPeanut).
2. Zweiter Produktionslauf von Hand (zählt zu den drei Läufen ohne Eingriff vor p1.7): `clipengine fetch` für die Start-Streamer, `analyze`, Prüfpakete per Kontaktbogen beurteilen (Spoiler, Zwischensequenz, Ab-18, Kategorie, GTA6-Hook zuerst, Titel mit Streamer-Namen; `clipengine judge ID --file`), behaltene Momente mit Layout-Profil rendern. Neue Streamer brauchen ein Profil (Standbild mit drawgrid 160x120, gerahmte Cams mit cam_crop, Cam-Ausschnitt an echten Bildern prüfen). Fällt ein Render am Band-Check, Standbild ansehen: Schnitt verschieben, verwerfen oder bei Witz-Menü `--accept-band`.

## Wartet auf den Owner

Urteil zu den sechs READY-Videos; Entscheidung zu LIRIK und TheBurntPeanut (siehe oben); Screenshot vom Kontostatus des alten TikTok-Kontos.

## Wie arbeiten

- Eigener Worktree off origin/main (../agentic-ops1-gta6-p12 existiert, neuen Branch schneiden). Schwester-Sessions laufen im Haupt-Checkout. Nie git stash.
- Ein PR pro Thema; Ship-Kette autonom; `gh pr checks --watch` im Vordergrund; `gh pr merge N --repo 011matthias/agentic-ops1.01 --squash --delete-branch` als EIGENER Aufruf ohne vorangestelltes cd (ein Hook blockiert sonst).
- Engine-Befehle aus dem Worktree-engine-Ordner mit `env VIRTUAL_ENV= uv run --extra gpu --extra dev clipengine ...` (das Haupt-Checkout-engine hat kein numpy); die Daten liegen automatisch unter engine/data/ des Haupt-Checkouts.
- Tests offline gegen Fakes (tests/conftest.py, tests/test_produce.py mit gefälschtem ffmpeg, tests/test_follow.py mit gefälschtem Detektor und MeasuringFfmpeg für measure()). CI läuft mit `--extra dev`. Echte Exit-Codes: Ausgabe in eine Datei umleiten statt durch eine Pipe.
- Pro Fix mindestens ein Test über die CLI; `uv run tools/regress_check.py` mit Test-IDs (nicht -k) zeigt, dass er rot wird.
- Python-Skripte und Texte über 80 Zeilen nie per Heredoc (Hook blockiert): mit dem Write-Werkzeug ins Scratchpad schreiben oder per Edit anhängen.
- Ergebnisse gegen eine zweite Quelle prüfen (ffprobe, Kontaktbogen ansehen), nicht gegen die eigene Ausgabe.
- Höchstens 3 Versuche pro Fehler, danach AskUserQuestion. Owner-Entscheidungen mit Standbildern (SendUserFile) und AskUserQuestion.
- Daten nur unter engine/data/ des Haupt-Checkouts. Das Repo ist öffentlich: keine Adressen, Tokens, Kontodaten in getrackte Dateien.

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
