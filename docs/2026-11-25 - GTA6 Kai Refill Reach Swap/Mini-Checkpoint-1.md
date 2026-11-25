# Mini-Checkpoint: GTA6 Kai Refill Reach Swap

**Date:** 2026-11-25
**Status:** p1 production, p2 publishing; booked through 26.11. 02:00
**Type:** mini

---

## Summary
Three KaiCenat videos are booked for 25./26.11. on owner OK, the YouTube reach problem is narrowed down (settings clean, TikTok gets thousands), the streamer register is swapped, and the OAuth app is in production, but the owner's new consent is still open.

## What Was Done
- Live read 25.11.: m46, m50, m76 went public on their slots; 12 public Shorts have 15 views together. Channel and video settings are clean (public, processed, Gaming, en, not age-restricted, not made for kids); `/shorts/ID` answers 200 for ours where a regular video redirects 303, so YouTube files them as Shorts and simply does not show them. Owner: the same videos reach thousands on TikTok.
- Recorded rejects 45, 52, 55, 62 (Lacy). Analyzed 33 KaiCenat moments (80-112): 4 kept (84 gas station 6 stars, 110 Lucia "UFC", 100 boat shootout, 94 Fleeca robbery), 22 rejected (strip club, sex scenes, cutscenes, finale spoilers, chatter, nude beach, menus), 98, 101, 104, 105, 108, 111, 112 left open.
- #1806: KaiCenat gameplay rect ends at x 1720; his new VODs carry a subathon timer (x 1755+, y 130-180) and counter (x 1732+, y 535-600) on the right edge. Cam position unchanged in both new VODs.
- Rendered m84 (`--accept-band` weapon wheel 1 s, `--accept-edge` shooter at the left edge before Kai's cam), m110 (clean pass), m100 (cut 26.0-70.5 s before the cutscene, `--accept-edge`). Stills checked. m94 fails (object at edge in 30 samples, captions 0.83 s off), not retried.
- Owner OK on all three; `clipengine publish --go`: m84 25.11. 20:00, m110 26.11. 00:00, m100 26.11. 02:00, read back private + publishAt, files and captions in the iCloud folder.
- #1809: register swap on owner order (Jerma985, CohhCarnage, AvoidingThePuddle, NickEh30 in; jasontheween, stableronaldo, TheBurntPeanut out; LIRIK stays as gameplay-only); status file updated.
- OAuth app: owner filled Branding (UnpauseAI homepage + privacy page, no logo) and published it to production, so a token from the next consent no longer expires after 7 days.

## What Did NOT Work (and why)
- **Consent flow started hidden with redirected stdout:** Python buffers stdout into a file, so the consent link never reached the log and the owner had nothing to click; restarted with `PYTHONUNBUFFERED=1`, which printed it at once.
- **Owner consent on 25.11.:** Google added an identity check on the iPhone and the consent was not completed in this session; the receiver on port 59141 dies with the session, so the next session needs a fresh link.
- **m94 render (Fleeca robbery):** main object outside the window in 30 samples and captions 0.83 s off the audio; left for the next session (in-game dialogue over Kai's voice is the likely cause of the drift).

## Current Status
Booked: m84 25.11. 20:00, m110 26.11. 00:00, m100 26.11. 02:00. Nothing READY beyond. YouTube token from 20.11. valid to about 27.11. 19:50; the app is in production now, one consent fixes it for good. No infrastructure.yaml / comms log for this internal project.

## Next Steps
1. New consent before 27.11. evening (fresh link via `yt_consent.py`, `PYTHONUNBUFFERED=1`).
2. Refill from 26.11. 20:00: fetch caseoh_'s four new public VODs and the new streamers, calibrate layouts for Jerma985, CohhCarnage, AvoidingThePuddle, NickEh30, analyze, judge, render, owner OK, publish.
3. Compilation test video (owner decision 25.11.).
4. LIRIK gameplay-only layout.
5. Analytics again from 27.11. (countries, retention).

## Files to Read First
- workspace/projects/gta6-clipping/status/p1-clip-pipeline.md
- workspace/projects/gta6-clipping/engine/README.md

---

## Continuation prompt

````
/comd_resume gta6-clipping

GTA6-Clipping: drei Videos am Tag zu festen Zeiten (YouTube + TikTok synchron), Nachschub ab 26.11. 20:00, YouTube-Zugang dauerhaft machen, Zusammenschnitt-Test (internes Projekt workspace/projects/gta6-clipping/).

## Stand (25.11.2026, ~15:45)

- Gemergt: #1806 (KaiCenat-Gameplay-Rechteck endet bei x 1720: in seinen neuen VODs stehen rechts ein Subathon-Timer x 1755+, y 130-180, und ein Zähler x 1732+, y 535-600; Cam-Position unverändert), #1809 (Register: Jerma985, CohhCarnage, AvoidingThePuddle, NickEh30 neu; jasontheween, stableronaldo, TheBurntPeanut raus; LIRIK bleibt, nur Spielbild). Checkpoint: docs/2026-11-25 - GTA6 Kai Refill Reach Swap/Mini-Checkpoint-1.md.
- Eingeplant mit Owner-OK: m84 (KaiCenat, Tankstelle, 6 Sterne) 25.11. 20:00, m110 (Lucia "UFC") 26.11. 00:00, m100 (Boot-Schießerei) 26.11. 02:00; zurückgelesen privat + publishAt, Dateien im iCloud-Ordner. Nächster freier Slot 26.11. 20:00. Nichts READY auf Halde. Die Slots 23.11. 20:00 bis 25.11. 02:00 blieben leer (keine Sitzung).
- Reichweite: 12 öffentliche Shorts, zusammen 15 Aufrufe. Einstellungen sauber (öffentlich, Gaming, en, nicht altersbeschränkt, nicht für Kinder; /shorts/ID antwortet 200, ein normales Video leitet 303 auf /watch um, also als Short erkannt). Owner: dieselben Videos haben auf TikTok Tausende. Arbeitsthese: YouTube testet wiederverwendete Momente eines neuen Kanals kaum, zumal wir Tage nach dutzenden Clip-Kanälen posten. Owner-Entscheidung: eine Woche weiter 3 am Tag plus EIN Testvideo "beste GTA6-Momente des Tages" aus mehreren Streamern.
- YouTube-Zugang: Owner hat die OAuth-App auf "In Produktion" gestellt (Branding mit unpauseai.com und unpauseai.com/privacy, kein Logo). Ein neuer Token verfällt damit nicht mehr nach 7 Tagen. Die Zustimmung selbst ist NOCH OFFEN (Google wollte eine Identitätsbestätigung am iPhone, nicht abgeschlossen). Der alte Token vom 20.11. hält bis etwa 27.11. 19:50.
- KaiCenat-Momente 80-112: behalten und gepostet 84, 110, 100; behalten, aber Render fällt durch: 94 (Fleeca-Bankraub; Objekt in 30 Samples am Rand, Untertitel 0,83 s versetzt); verworfen 22 (per judge eingetragen); offen ohne Urteil: 98, 101, 104, 105, 108, 111, 112 (wenige Clip-Aufrufe, 101 nächtliche Flucht mit Funken ist der beste davon). Weitere offene Pakete: 66, 73, 74 (LIRIK, warten auf das Spielbild-Layout), 77-79 (IShowSpeed), 57, 64, 71 (TheBurntPeanut, jetzt raus: als reject eintragen), 51, 61, 65, 69 (stableronaldo, raus: reject).
- caseoh_ hat seit 20.11. öffentliche VODs: vier noch nicht geholt (2935283335, 2937666104, 2938655753, 2940013635), Clips bis 44.627 Aufrufe. Der Dubletten-Schutz von fetch/publish (#1800) greift für schon gepostete Clip-Momente.
- Live-Fakten: ffmpeg drawtext stürzt ab (Kontaktbögen ohne Beschriftung). `yt_consent.py` versteckt gestartet braucht `PYTHONUNBUFFERED=1`, sonst landet der Link nie im Log. `--accept-edge` passt bei KaiCenat, wenn der Schütze beim Zielen am linken Rand vor Cam und Chat steht. Band-Check übersieht weiter verschwommene Pausenmenüs und zweite Cams: Standbilder bleiben Pflicht.

## Feste Owner-Regeln

- Keine API-LLM-Kosten; Urteilsarbeit im Gespräch. Clips auf Englisch. Titel nennt den Streamer wie im Register.
- Länge etwa 1 Minute (max 60 s). Hook nennt GTA6. Gameplay füllt das Band, Hauptobjekt ganz sichtbar, kein Blur. Menüs fallen durch (Witz-Menü oder kurzes Waffenrad mitten in der Action per `--accept-band GRUND`); Objekt am Rand vor einem Overlay per `--accept-edge GRUND`. Clips ohne Worte erlaubt. Keine Stripclubs, Sexszenen, Nacktheit, Zwischensequenzen, Finale-Spoiler.
- Posten nur mit Owner-OK pro Video (720p-Vorschau per Start-Process öffnen, dann AskUserQuestion). Beschreibungen ohne Twitch-Link; Namensschild im Video bleibt.
- Drei Videos pro Tag, feste Slots 20:00, 00:00, 02:00 deutsche Zeit, TikTok und YouTube synchron. Veröffentlichen nur über `clipengine publish ID` (Probelauf, dann `--go`). Der Owner postet TikTok selbst vom iPhone aus dem iCloud-Ordner zur Uhrzeit im Dateinamen.
- LIRIK: Spielbild füllt das ganze Hochformat, kein Cam-Band (Owner 25.11.).

## Aufgabe, in dieser Reihenfolge

1. YouTube-Zustimmung vor dem 27.11. abends: `yt_consent.py` (engine/data/publish/ des Haupt-Checkouts, Argument = context-Ordner) per Start-Process versteckt mit `$env:PYTHONUNBUFFERED='1'` starten, Link aus dem Log lesen und dem Owner im Chat geben (nur an diesem PC gültig), auf "token saved" warten (Empfänger läuft, bis die Zustimmung kommt). Hinweise für den Owner: Identitätsbestätigung am iPhone, dann "Erweitert" und "Zu gta6-clipengine wechseln (unsicher)", überall "Zulassen". Danach mit einem Lese-Aufruf prüfen, dass der neue Token geht.
2. Nachschub ab 26.11. 20:00: `watch`, `fetch --top 15` (caseoh_s vier neue VODs zuerst, dann die neuen Streamer), Cam-Position der neuen Streamer auf Standbildern messen und in config/layouts.yaml eintragen (Profil wie bei lacy/kaicenat), `analyze`, Kontaktbögen (concat-Demuxer, 4x2), judge, render, Standbilder + Hook prüfen, Vorschau, Owner-OK, `publish`. Vorher 57, 64, 71 und 51, 61, 65, 69 als reject eintragen.
3. Zusammenschnitt-Test: ein Video "beste GTA6-Momente des Tages" aus mehreren Streamern (je Ausschnitt 10 bis 15 s, insgesamt max 60 s, Namensschild je Ausschnitt). Braucht einen Render über mehrere Cut-Listen; als eigenes PR mit CLI-Test.
4. LIRIK-Layout nur Spielbild (Profil ohne facecam; Spielbild füllt 1080x1920, Folge-Fenster über die volle Höhe), dann 66, 73, 74 beurteilen.
5. Ab 27.11. Analytics erneut (Skript yt_stats.py im Scratchpad der Sitzung ea43fb4b, sonst aus 3bb5b61f): Länder, Retention-Kurve; plus TikTok-Zahlen beim Owner erfragen.
6. Segmentweiser Download für VOD-Zeit über 26:30 h.
7. Band-Check-Lücke: verschwommenes Pausenmenü, doppelte Cam/Chat im Band, gezoomte Karte.

## Wartet auf den Owner

YouTube-Zustimmung (Punkt 1); OK pro Video für jeden Slot; Kontakt-E-Mail für Takedowns; Screenshot Kontostatus altes TikTok-Konto.

## Wie arbeiten

- Eigener Worktree off origin/main (../agentic-ops1-gta6-p12 existiert; vor jedem neuen Branch `git fetch origin`, dann `git switch -C <branch> origin/main`). Schwester-Sitzungen laufen im Haupt-Checkout. Nie git stash.
- Ein PR pro Thema; Ship-Kette autonom; `gh pr checks N --watch` im Vordergrund; `gh pr merge N --repo 011matthias/agentic-ops1.01 --squash --delete-branch` als EIGENER Aufruf ohne vorangestelltes cd.
- Engine-Befehle: `uv run --directory <worktree>\workspace\projects\gta6-clipping\engine --extra gpu --extra dev --extra publish clipengine ...` mit `$env:VIRTUAL_ENV=''`; Daten unter engine/data/ des Haupt-Checkouts. In PowerShell kein Set-Location (cd-guard), Pfade absolut.
- Tests offline gegen Fakes; pro Fix mindestens ein Test über die CLI; `uv run tools/regress_check.py` zeigt rot (Testbefehl in eine .cmd-Datei legen).
- Fertige Videos per Standbildern prüfen (Cam-Band, Overlay im Gameplay-Band, Hook in den ersten 3 s, Ende ohne Menü). Dubletten fängt publish selbst.
- Skripte und Texte über 80 Zeilen nie per Heredoc: Write oder Edit.
- Höchstens 3 Versuche pro Fehler, danach AskUserQuestion. Owner-Entscheidungen mit Standbildern und AskUserQuestion; Deutsch, Alltagssprache.
- Das Repo ist öffentlich: keine Adressen, Tokens, Kontodaten, Kanal- oder eigenen Video-IDs in getrackte Dateien.

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
