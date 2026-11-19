# Mini-Checkpoint: GTA6 Clip Engine P1.1 And Channels

**Date:** 2026-11-19
**Status:** p1.1 live in the repo, channels set up, first video (p1.2 to p1.6) not started
**Type:** mini

---

## Summary
Built and merged the p1.1 watch engine, recorded the owner's rights/channel/autonomy decisions, connected read access to the new YouTube channel cl1pmaxxers, and shipped its channel art. Next session builds the first finished video by hand.

## What Was Done
- PR #1758: `engine/` uv project (SQLite, register, Twitch VODs + viewer clips in 6 h chunks, YouTube feed, `suggest` / `approve` / `reject`), 38 offline tests, CI job `gta6-engine-tests`; live match against twitch.tv for LIRIK and KaiCenat.
- PR #1759: owner decisions (clip any streamer, drop on complaint; channels now, nothing posted; autonomy gates; learning-loop plan).
- PR #1760: Google Cloud project + Desktop OAuth client, consent (youtube.readonly, yt-analytics.readonly); Analytics 403 before the channel existed, 200 after.
- PR #1761: channel art in `workspace/projects/gta6-clipping/deliverables/channel-branding/` (profile with/without CL1P, banner, watermark, upload steps, channel texts).
- Status file `status/p1-clip-pipeline.md` brought current.

## What Did NOT Work (and why)
- **Single Twitch Get Clips query per window:** caps near 1,000 results and repeats clips; KaiCenat 7 days gave ~800 distinct in one query vs 1,914 in 6 h chunks.
- **Filtering VODs by created_at:** dropped KaiCenat's 35 h marathon that began before the window but carried 1,772 clips inside it; replaced with an overlap test.
- **Splitting two watch runs by minute to find run-2-only clips:** both runs fell in the same minute, so the probe returned a confident false negative; split by the largest time gap instead.
- **Playwright MCP for the cold Twitch check:** CDP on 9222 refused; agent-browser `open` hung on Twitch, `eval location.href=...` plus `wait` worked.
- **Publishing the OAuth app:** greyed out while the Branding page is incomplete; test mode with the owner as test user instead (refresh token expires 7 days after consent).

## Current Status
Register `engine/config/streamers.yaml` is empty; GTA VI launched today, so `suggest` can run on real data. Nothing posted anywhere. Owner-pending: upload the channel art and pick the profile variant, a takedown contact email for `[KONTAKT-E-MAIL]`, the TikTok Kontostatus screenshot of the old account (last post 2025-04-07). No ops status: internal project without an orchestrator.

## Next Steps
1. `uv run clipengine suggest --since 24h`, owner approves start streamers, `watch`.
2. p1.2 fetch (intervals from viewer clips, muted segments excluded, section download via yt-dlp).
3. p1.3 to p1.6 minimal for one F1 video into `engine/data/ready/`, shown to the owner, not posted.

## Files to Read First
- `workspace/projects/gta6-clipping/specs/2-build/p1-clip-engine.md`
- `workspace/projects/gta6-clipping/status/p1-clip-pipeline.md`
- `workspace/projects/gta6-clipping/engine/README.md`

## Continuation prompt

````markdown
/comd_resume gta6-clipping

GTA6-Clipping: erstes fertiges Video bauen (internes Projekt workspace/projects/gta6-clipping/).

## Stand (19.11.2026, GTA-VI-Launch-Tag)

- p1.1 ist gemergt (PR #1758): engine/ ist ein eigenes uv-Projekt mit SQLite, Streamer-Register, Twitch-VODs und Zuschauer-Clips (in 6-h-Stücken, weil jede Abfrage bei ~1.000 kappt), YouTube-Kanal-Feed und `suggest` / `approve` / `reject`. 38 Offline-Tests, CI-Job gta6-engine-tests (ruff + pytest).
- Der Zustand (SQLite) liegt immer im Haupt-Checkout unter workspace/projects/gta6-clipping/engine/data/, auch wenn die Engine aus einem Worktree läuft (Auflösung über git common dir; Overrides CLIPENGINE_DATA_DIR / CLIPENGINE_REGISTER / CLIPENGINE_ENV_FILE). Twitch-Zugang in context/.env des Haupt-Checkouts; GTA-VI-game_id 1867279146.
- Das Register engine/config/streamers.yaml ist noch leer.
- YouTube-Kanal cl1pmaxxers existiert, Lesezugriff auf Data und Analytics per OAuth geprüft (Token in context/, gitignored). Kanal-Design fertig (PR #1761). In dieser Aufgabe wird NICHTS gepostet.
- Masterplan mit allen Stufen, Datenmodell, Randfällen und Erfolgskriterien: specs/2-build/p1-clip-engine.md. Status: status/p1-clip-pipeline.md.
- Laptop: RTX 3060 Laptop 6 GB, ffmpeg 8.1 mit NVENC, claude CLI installiert.

## Feste Owner-Entscheidungen

- Keine API-LLM-Kosten. Urteilsarbeit (Spoiler, Kategorie, Hooks, Titel) machst du im Gespräch über das Abo.
- Nur die meistgesehenen Intervalle zählen: bei Twitch die Zuschauer-Clips (view_count, vod_offset, Dauer), bei YouTube die yt-dlp-heatmap. Nie ganze Streams laden.
- Clips auf Englisch. Jeder Streamer darf geclippt werden; bei Beschwerde fliegt er raus.
- Jedes Video nennt den Streamer im Titel (so steht es in der Kanalbeschreibung).

## Aufgabe, in dieser Reihenfolge

1. Start-Streamer: `uv run clipengine suggest --since 24h` (bei dünnen Daten 48h). Die Top 10 dem Owner in einfachem Deutsch vorlegen (wer, wie viele englische Clip-Aufrufe, Warnhinweise wie Selbstclipper oder bot-artige Konten) und per AskUserQuestion abnicken lassen. Dann `approve` / `reject`, danach `watch`.
2. p1.2 Holen: Intervalle aus den Zuschauer-Clips (überlappende verschmelzen, Gewicht = Summe der Aufrufe), muted_segments ausschließen, die stärksten N wählen, nur diese Abschnitte mit 5 s Puffer per `yt-dlp --download-sections` in bester Qualität laden. yt-dlp als Abhängigkeit im engine-Projekt. Eine abgeschlossene Aufzeichnung nehmen, keinen laufenden Stream. Zuerst prüfen (UNVERIFIED): ob yt-dlp Abschnitte aus Twitch-VODs sauber lädt, auch bei sehr langen VODs, und ob es Twitch-Clips lädt (Ersatz, wenn das VOD weg ist). Die YouTube-Kurve kann nach dem ersten Video kommen.
3. p1.3 Analysieren, minimal: faster-whisper (large-v3, int8, GPU; messen, ob 6 GB VRAM und die Laufzeit reichen) mit Wortzeiten, Schnitt an Satzgrenzen, Prüfpakete nach engine/data/review/{moment}/ (Transkript, 6 bis 8 Standbilder, Aufrufe, Streamer). Die Pakete beurteilst du selbst: Spoiler oder Zwischensequenz, Kategorie, 2 bis 3 Hooks, Titel, oder verwerfen. Story-Spoiler sind am Launch-Tag das größte Risiko. `claude -p` aus der Aufgabenplanung kommt später.
4. p1.4 bis p1.6 für EIN Video im Format F1 (Einzelmoment, 15 bis 60 s): Schnittliste als JSON, Facecam-Profil des Streamers einmal kalibrieren, 1080×1920 mit Facecam oben und Gameplay unten, ASS-Untertitel aus den Wortzeiten (2 bis 4 Wörter, gesprochenes Wort hervorgehoben), Hook-Zeile in den ersten ~3 s, Streamer-Name als Einblendung, loudnorm auf -14 LUFS, Render mit h264_nvenc. Checks: Maße, Dauer, Lautheit -14 ±1 LUFS, blackdetect/freezedetect, Untertitel-Stichprobe unter 0,2 s Abweichung. Ergebnis in engine/data/ready/.
5. Das Video dem Owner zeigen: lokal öffnen (Start-Process) und per SendUserFile schicken, dazu Titel, Hook-Varianten und Quelle (Streamer, VOD, Zeitstempel). Nicht posten.

## Wie arbeiten

- Eigener Worktree und Branch, weil Schwester-Sessions im Haupt-Checkout laufen: `git worktree add -b client/gta6-clipping/p1.2-first-clip ../agentic-ops1-gta6-p12 origin/main`. Nie git stash. Der alte Worktree ../agentic-ops1-gta6-p11 ist komplett gemergt und kann weg.
- Ein PR pro Phase (p1.2 zuerst, dann p1.3 bis p1.6). Die Ship-Kette läuft autonom: Commit, Push, PR, in derselben Runde `gh pr checks --watch` im Vordergrund, Merge bei Grün.
- Tests offline gegen httpx.MockTransport-Fakes wie in engine/tests/conftest.py. Pro Fix mindestens ein Test über die CLI, und mit `uv run tools/regress_check.py` zeigen, dass er rot wird, wenn der Fix fehlt.
- Live-Ergebnisse gegen eine zweite Quelle prüfen (Clipseite des Streamers auf twitch.tv, die Datei selbst per ffprobe), nicht gegen die eigene Ausgabe.
- Höchstens 3 Versuche pro Fehler, danach per AskUserQuestion eskalieren.
- Downloads und Zwischendaten nur unter engine/data/ (gitignored). Unter 50 GB freiem Speicher keine Downloads.
- Spec-Frontmatter (last_changes, Erfolgskriterien) und status/p1-clip-pipeline.md am Ende jeder Phase nachziehen.
- Das Repo ist öffentlich: keine E-Mail-Adressen, Tokens oder Kontodaten in getrackte Dateien.
- Erwarteter Umfang: hoch. Checkpoint nach dem p1.2-Merge und nach p1.3 einplanen.

## Wartet auf den Owner (blockiert diese Aufgabe nicht)

Kanal-Design hochladen und Profilvariante wählen; Kontakt-Adresse für [KONTAKT-E-MAIL] in der Kanalbeschreibung; Screenshot vom TikTok-Kontostatus des alten Kontos.

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
