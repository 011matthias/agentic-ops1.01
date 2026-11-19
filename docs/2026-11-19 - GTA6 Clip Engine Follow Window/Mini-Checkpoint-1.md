# Mini-Checkpoint: GTA6 Clip Engine Follow Window

**Date:** 2026-11-19
**Status:** gameplay band filled by a window that follows the main object (PR #1774), caseoh_ layout (PR #1775), no blur in the band (PR #1776); m5-f1 and m15-f1 READY, previews sent, not posted
**Type:** mini

---

## Summary
The owner's rule "the gameplay fills the whole lower band AND the main object stays completely visible" is built: a 912x1080 window follows the main object, picked by a local detector. caseoh_ got a layout profile and moment 15 a GTA6 hook. After the m5 preview the owner ordered "unten den blur weg", and the duplicate-cam blur is gone.

## What Was Done
- `follow.py`: 4 fps samples (own cam blanked, padded 120 px), YOLOX-m ONNX on the CPU (`data/models/yolox_m.onnx`, Apache-2.0, sha256 `21ff6cfd...`, ~53 s per 55 s clip, no API cost, no GPU needed). Tracker with hysteresis (another object needs half the size and two picks in a row), despike (median of three, unconfirmed single boxes dropped), boxes the centre line runs through mirrored about it, continuous margin, smoothed path, `sendcmd` per frame into `crop@follow`.
- Stage-6 checks: object box inside the window in every sample (an object wider than the window fails, owner decides); no bars in the band (strip sharpness / middle, p90 < 0.2; calibrated on m5: fit layout 0.096, filled 0.41).
- caseoh_: facecam [0,134,402,302] from a 160x120 grid still at 0:09 of his clip; new `cam_crop` [0,182,402,238] cuts the top band inside the 4:3 frame. Moment 15 re-judged with "caseoh_ chasing Peggy on a mobility scooter in GTA6", rendered READY (21.9 s, -14.6 LUFS).
- Owner "unten den blur weg": the band blurs nothing; in m5 a sliver of ohnePixel's cam shows at the band's left edge. m5-f1 (55.7 s, x 504-597) and m15-f1 re-rendered READY; 720p previews sent.
- 78 offline tests; regress_check bit on all 7 wiring points. Spec v1.3.0 (stage 5/6, last_changes), status file, engine README, layouts.yaml.

## What Did NOT Work (and why)
- **Box-centred following:** the window followed the detector box centre and cut the jet's right wing at 24 s; the box held one wing only (528-1203 px, jet 540-1380 px). Fixed by mirroring about the centre line (the chase camera keeps the vehicle centred).
- **Margin steps and a hard mirrored/raw switch:** the camera jumped about 100 px per quarter second (504 to 605) at 2-6 s as the box crossed the thresholds; continuous margin and a clipped mirror leave x at 504 with steps under 30 px outside the crash.
- **Blanking only the calibrated facecam rect:** ohnePixel's arm, 120 px left of it, was picked as the main "person" at 29-32 s and 53-55 s.
- **Bar threshold 0.12:** the fit layout's top strip measured 0.096, too close; 0.2 separates it from the filled band's 0.41.
- **720p preview at cq 26:** 40.4 MB, over the 30 MB send limit; vbr 3 Mbit/s gives 21.7 MB.
- **Aliasing a fixture import (`from test_produce import kept as kept_fixture`):** pytest did not register it as `kept` (5 errors); a plain `make_kept()` helper plus a local fixture works.

## Current Status
`data/ready/m5-f1/` and `data/ready/m15-f1/` hold the current renders (main checkout); nothing posted. Owner verdict on both pending. Context at close: 413k.

## Next Steps
1. Band check for menus, map and dark stretches (m5 shows the weapon wheel around 34 s; m15 is near-black around 8 s; whole-frame blackdetect misses both).
2. Judge the 13 open review packages by contact sheet.
3. 22.11.: `uv run clipengine suggest --since 72h`, swap streamers who stopped playing GTA.

## Files to Read First
- `workspace/projects/gta6-clipping/engine/src/clipengine/follow.py`
- `workspace/projects/gta6-clipping/engine/src/clipengine/produce.py` (`band_bars`, `measure`, `check`)
- `workspace/projects/gta6-clipping/status/p1-clip-pipeline.md`

---

## Continuation prompt

````
/comd_resume gta6-clipping

GTA6-Clipping: Menüs, Karte und dunkle Strecken im Gameplay-Band erkennen, dann die offenen Prüfpakete (internes Projekt workspace/projects/gta6-clipping/).

## Stand (19.11.2026, nachmittags)

- Gemergt: #1774 (Gameplay füllt das untere Band, 912x1080-Ausschnitt folgt dem Hauptobjekt; neue Checks: Objektbox im Ausschnitt, keine Balken), #1775 (caseoh_-Layout mit cam_crop, Moment 15 mit GTA6-Hook), #1776 (Owner "unten den blur weg": im Band wird nichts mehr weichgezeichnet). Checkpoint: docs/2026-11-19 - GTA6 Clip Engine Follow Window/Mini-Checkpoint-1.md.
- Bereit, nicht gepostet: data/ready/m5-f1/m5-f1.mp4 (ohnePixel, Jet, 55,7 s, Ausschnitt x 504-597) und data/ready/m15-f1/m15-f1.mp4 (caseoh_, Scooter, 21,9 s). 720p-Vorschauen an den Owner geschickt. In m5 zeigt sich ohne Blur am linken Bandrand ein schmaler Streifen der doppelten Facecam.
- Detektor: YOLOX-m ONNX auf der CPU, Modell in engine/data/models/yolox_m.onnx des Haupt-Checkouts (nicht in git, sha256 21ff6cfd...), etwa 53 s Erkennung pro 55-s-Clip. Balkenschwelle 0,2 (alter Fit-Look 0,096, gefülltes Band 0,41).
- Live-Fakten: vod_offset ist das Clip-Ende; yt-dlp und Hugging Face nur über IPv4; NVENC läuft (Treiber 621.24); 720p-Vorschau mit -b:v 3M bleibt unter 30 MB.

## Feste Owner-Regeln

- Keine API-LLM-Kosten; Urteilsarbeit im Gespräch über das Abo. Clips auf Englisch. Jeder Titel nennt den Streamer.
- Länge etwa 1 Minute (cut_f1 zielt auf 55 s, max 60). Clip-only-Streamer (caseoh_, IShowSpeed) sind so lang wie der Clip.
- Der eingeblendete Hook nennt GTA6 (judge erzwingt es).
- Aufteilung (Facecam oben, Gameplay unten), Untertitel und Hook-Stil sind abgenommen.
- Das Gameplay füllt das ganze untere Band, das Hauptobjekt bleibt vollständig sichtbar. Ist ein Objekt breiter als der Ausschnitt, fällt der Check durch: dann beide Varianten als Standbild zeigen und per AskUserQuestion entscheiden lassen.
- Kein Blur im unteren Band, auch nicht auf der doppelten Facecam (Owner 19.11.).
- Kontakt-Adresse für die Kanalbeschreibung wird noch nicht gebraucht. Nichts posten.

## Aufgabe, in dieser Reihenfolge

1. Prüfung der Gameplay-Fläche auf Menüs, Karte und dunkle Strecken. Belege: m5 zeigt um 34 s das Waffenrad (Menü über verschwommenem Spielbild), der ursprüngliche m5-Anfang hatte eine offene Pause-Karte (bis 12,5 s der Section), m15 ist um 8 s fast schwarz (Kamera durchs Gebüsch). produce.measure macht blackdetect über das ganze Bild, die helle Facecam oben verdeckt dunkle Bänder. Ansatz: wie produce.band_bars nur das Band (crop 1080:1280:0:640) messen; dunkel = mittlere Helligkeit des Bands, Menü/Karte = Schärfe des Spielbilds bricht ein oder große einfarbige UI-Flächen. An m5 (34 s), m15 (8 s) und dem alten Pause-Karten-Stück eichen, gegen saubere Strecken abgrenzen. Kurze Stellen unter ~0,5 s eventuell zulassen; was die Schwelle ist, mit Messwerten begründen. Test über die CLI, regress_check mit Test-IDs.
2. Die 13 offenen Prüfpakete (data/review/{id}/) per Kontaktbogen beurteilen: Spoiler, Zwischensequenz, Ab-18, Kategorie, GTA6-Hook zuerst, Titel mit Streamer-Namen; `clipengine judge ID --file`. Behaltene Momente mit Layout-Profil rendern (neue Streamer brauchen ein Profil: Standbild mit drawgrid 160x120, gerahmte Cams mit cam_crop).
3. Am 22.11.: `uv run clipengine suggest --since 72h`, Streamer tauschen, die kein GTA mehr spielen.

## Wartet auf den Owner

Urteil zu m5-f1 (ohne Blur, Streifen der Facecam links) und m15-f1; Screenshot vom Kontostatus des alten TikTok-Kontos.

## Wie arbeiten

- Eigener Worktree off origin/main (z. B. ../agentic-ops1-gta6-p12, neuen Branch schneiden). Schwester-Sessions laufen im Haupt-Checkout. Nie git stash.
- Ein PR pro Thema; Ship-Kette autonom; `gh pr checks --watch` im Vordergrund; `gh pr merge N --repo 011matthias/agentic-ops1.01 --squash --delete-branch` als EIGENER Aufruf ohne vorangestelltes cd (ein Hook blockiert sonst).
- Tests offline gegen Fakes (tests/conftest.py, tests/test_produce.py mit gefälschtem ffmpeg, tests/test_follow.py mit gefälschtem Detektor). CI läuft mit `--extra dev` (numpy ist drin). Echte Exit-Codes: Ausgabe in eine Datei umleiten statt durch eine Pipe. `VIRTUAL_ENV=` voranstellen, sonst greift uv das Brisken-venv.
- Pro Fix mindestens ein Test über die CLI; `uv run tools/regress_check.py` mit Test-IDs (nicht -k) zeigt, dass er rot wird.
- `uv run --directory` ändert das Arbeitsverzeichnis: für die Datenbank absolute Pfade verwenden.
- Python-Skripte nie per Heredoc mit dreifachen Anführungszeichen oder doppelten Backslashes (Hook blockiert): mit dem Write-Werkzeug ins Scratchpad schreiben.
- Ergebnisse gegen eine zweite Quelle prüfen (ffprobe, Kontaktbogen ansehen), nicht gegen die eigene Ausgabe.
- Höchstens 3 Versuche pro Fehler, danach AskUserQuestion.
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
