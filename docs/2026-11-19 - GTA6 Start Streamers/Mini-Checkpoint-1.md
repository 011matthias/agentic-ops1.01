# Mini-Checkpoint: GTA6 Start Streamers

**Date:** 2026-11-19
**Status:** start streamers registered, first video (p1.2 to p1.6) not started
**Type:** mini

---

## Summary
On launch day the owner signed off on ten start streamers from the engine's English clip-view ranking; they are in the register (PR #1765) and the first watch resolves all ten. Research added YouTube's age-restriction rule for game violence and sexual content to the p1.3 judgment.

## What Was Done
- `clipengine suggest --since 24h --top 20` on launch-day data (62 Twitch calls). One-hit names (Zoil, Clix, Dinah) and flagged ones (king_wolfe_ one clipper, Zerkaa self-clipped) left out; owner chose all ten recommended via AskUserQuestion.
- PR #1765: register with ohnePixel, xQc, Lacy, jasontheween, IShowSpeed, KaiCenat, TheBurntPeanut, LIRIK, caseoh_, stableronaldo; test fixture builds an empty register from the shipped header; spec p1.3 gains the Ab-18 check; status file current (owner uploaded the channel art, profile with CL1P).
- `clipengine watch --days 1`: ~15,600 clips, 358 Twitch calls; 8 streamers with a VOD. caseoh_ (1,193 of 1,318) and IShowSpeed (2,225 of 2,236) clips carry no vod_offset, xQc 0 of 1,652: they keep no public VOD.
- Web research: GTA 6 launch peaked ~3.06M Twitch viewers (StreamsCharts); alanzoka among the biggest streams and absent from the English list, consistent with the language filter. YouTube age-restricts unblurred graphic game violence since its pre-GTA-6 update (PC Gamer, Dexerto) and can age-restrict sexual content.

## What Did NOT Work (and why)
- **Committing the register change with `pytest ... | tail -2 && git commit`:** `tail` returned 0, so 9 red tests (fixture copied the real register and assumed it empty) went into a commit and PR #1765; caught from the output before merge, fixed, CI green on b3e52096. Self-detected verification-theater; rule for next time is in the prompt (real exit codes before commit).
- **Python edit via heredoc with triple quotes:** blocked by heredoc-size-gate; used Read + Edit instead.

## Current Status
Register holds ten streamers; nothing posted. Owner-pending: takedown contact email for `[KONTAKT-E-MAIL]`, TikTok Kontostatus screenshot if the old account stays. No ops status: internal project without an orchestrator. Merged worktrees ../agentic-ops1-gta6-p11 and ../agentic-ops1-gta6-streamers can be removed.

## Next Steps
1. p1.2 fetch on one finished stream (clip download is the only path for caseoh_ and IShowSpeed).
2. p1.3 to p1.6 for one F1 video into `engine/data/ready/`, shown to the owner, not posted.
3. 22.11: `suggest --since 72h`, swap streamers who stopped playing GTA.

## Files to Read First
- `workspace/projects/gta6-clipping/specs/2-build/p1-clip-engine.md`
- `workspace/projects/gta6-clipping/status/p1-clip-pipeline.md`
- `workspace/projects/gta6-clipping/engine/config/streamers.yaml`

## Continuation prompt

````markdown
/comd_resume gta6-clipping

GTA6-Clipping: erstes fertiges Video bauen (internes Projekt workspace/projects/gta6-clipping/).

## Stand (19.11.2026, GTA-VI-Launch-Tag)

- p1.1 ist gemergt (PR #1758): engine/ ist ein eigenes uv-Projekt mit SQLite, Streamer-Register, Twitch-VODs und Zuschauer-Clips (in 6-h-Stücken, weil jede Abfrage bei ~1.000 kappt), YouTube-Kanal-Feed und `suggest` / `approve` / `reject`. 38 Offline-Tests, CI-Job gta6-engine-tests (ruff + pytest).
- Der Zustand (SQLite) liegt immer im Haupt-Checkout unter workspace/projects/gta6-clipping/engine/data/, auch wenn die Engine aus einem Worktree läuft (Auflösung über git common dir; Overrides CLIPENGINE_DATA_DIR / CLIPENGINE_REGISTER / CLIPENGINE_ENV_FILE). Twitch-Zugang in context/.env des Haupt-Checkouts; GTA-VI-game_id 1867279146.
- Start-Streamer sind im Register (PR #1765, vom Owner abgenickt): ohnePixel, xQc, Lacy, jasontheween, IShowSpeed, KaiCenat, TheBurntPeanut, LIRIK, caseoh_, stableronaldo. Erster `watch --days 1` am 19.11.: rund 15.600 Clips, 8 Streamer mit VOD. caseoh_ und IShowSpeed haben keine öffentlichen VODs (fast alle Clips ohne vod_offset), ihre Momente kommen also aus dem Clip selbst.
- YouTube-Kanal cl1pmaxxers existiert, Lesezugriff auf Data und Analytics per OAuth geprüft (Token in context/, gitignored). Kanal-Design ist auf YouTube und TikTok hochgeladen. In dieser Aufgabe wird NICHTS gepostet.
- Masterplan mit allen Stufen, Datenmodell, Randfällen und Erfolgskriterien: specs/2-build/p1-clip-engine.md. Status: status/p1-clip-pipeline.md.
- Laptop: RTX 3060 Laptop 6 GB, ffmpeg 8.1 mit NVENC, claude CLI installiert.

## Feste Owner-Entscheidungen

- Keine API-LLM-Kosten. Urteilsarbeit (Spoiler, Ab-18-Risiko, Kategorie, Hooks, Titel) machst du im Gespräch über das Abo.
- Nur die meistgesehenen Intervalle zählen: bei Twitch die Zuschauer-Clips (view_count, vod_offset, Dauer), bei YouTube die yt-dlp-heatmap. Nie ganze Streams laden.
- Clips auf Englisch. Jeder Streamer darf geclippt werden; bei Beschwerde fliegt er raus.
- Jedes Video nennt den Streamer im Titel (so steht es in der Kanalbeschreibung).

## Aufgabe, in dieser Reihenfolge

1. `uv run clipengine watch --days 1`, damit die Clips aktuell sind. Neu auswerten (`suggest --since 72h`) erst am 22.11.
2. p1.2 Holen: Intervalle aus den Zuschauer-Clips (überlappende verschmelzen, Gewicht = Summe der Aufrufe), muted_segments ausschließen, die stärksten N wählen, nur diese Abschnitte mit 5 s Puffer per `yt-dlp --download-sections` in bester Qualität laden. yt-dlp als Abhängigkeit im engine-Projekt. Eine abgeschlossene Aufzeichnung nehmen, keinen laufenden Stream. Zuerst prüfen (UNVERIFIED): ob yt-dlp Abschnitte aus Twitch-VODs sauber lädt, auch bei sehr langen VODs, und ob es Twitch-Clips lädt. Für caseoh_ und IShowSpeed ist der Clip-Download der einzige Weg. Die YouTube-Kurve kann nach dem ersten Video kommen.
3. p1.3 Analysieren, minimal: faster-whisper (large-v3, int8, GPU; messen, ob 6 GB VRAM und die Laufzeit reichen) mit Wortzeiten, Schnitt an Satzgrenzen, Prüfpakete nach engine/data/review/{moment}/ (Transkript, 6 bis 8 Standbilder, Aufrufe, Streamer). Die Pakete beurteilst du selbst: Spoiler oder Zwischensequenz, Ab-18-Risiko (drastische Gewalt oder sexuelle Inhalte wie Strip-Club-Szenen verwerfen oder entschärfen, weil YouTube sie ab 18 einstuft und sie dann kaum jemand sieht), Kategorie, 2 bis 3 Hooks, Titel, oder verwerfen. Story-Spoiler sind in der Launch-Woche das größte Risiko. `claude -p` aus der Aufgabenplanung kommt später.
4. p1.4 bis p1.6 für EIN Video im Format F1 (Einzelmoment, 15 bis 60 s): Schnittliste als JSON, Facecam-Profil des Streamers einmal kalibrieren, 1080×1920 mit Facecam oben und Gameplay unten, ASS-Untertitel aus den Wortzeiten (2 bis 4 Wörter, gesprochenes Wort hervorgehoben), Hook-Zeile in den ersten ~3 s, Streamer-Name als Einblendung, loudnorm auf -14 LUFS, Render mit h264_nvenc. Checks: Maße, Dauer, Lautheit -14 ±1 LUFS, blackdetect/freezedetect, Untertitel-Stichprobe unter 0,2 s Abweichung. Ergebnis in engine/data/ready/.
5. Das Video dem Owner zeigen: lokal öffnen (Start-Process) und per SendUserFile schicken, dazu Titel, Hook-Varianten und Quelle (Streamer, VOD oder Clip, Zeitstempel). Nicht posten.

## Wie arbeiten

- Eigener Worktree und Branch, weil Schwester-Sessions im Haupt-Checkout laufen: `git worktree add -b client/gta6-clipping/p1.2-first-clip ../agentic-ops1-gta6-p12 origin/main`. Nie git stash. Die alten Worktrees ../agentic-ops1-gta6-p11 und ../agentic-ops1-gta6-streamers sind komplett gemergt und können weg.
- Ein PR pro Phase (p1.2 zuerst, dann p1.3 bis p1.6). Die Ship-Kette läuft autonom: Commit, Push, PR, in derselben Runde `gh pr checks --watch` im Vordergrund, `gh pr merge` als eigener Aufruf bei Grün.
- Tests vor jedem Commit mit echtem Exit-Code laufen lassen (nicht hinter `| tail` verstecken). Tests offline gegen httpx.MockTransport-Fakes wie in engine/tests/conftest.py; die Fixture `env` baut ein leeres Register, das echte Register enthält die Start-Streamer. Pro Fix mindestens ein Test über die CLI, und mit `uv run tools/regress_check.py` zeigen, dass er rot wird, wenn der Fix fehlt.
- Live-Ergebnisse gegen eine zweite Quelle prüfen (Clipseite des Streamers auf twitch.tv, die Datei selbst per ffprobe), nicht gegen die eigene Ausgabe.
- Höchstens 3 Versuche pro Fehler, danach per AskUserQuestion eskalieren.
- Downloads und Zwischendaten nur unter engine/data/ (gitignored). Unter 50 GB freiem Speicher keine Downloads.
- Spec-Frontmatter (last_changes, Erfolgskriterien) und status/p1-clip-pipeline.md am Ende jeder Phase nachziehen.
- Das Repo ist öffentlich: keine E-Mail-Adressen, Tokens oder Kontodaten in getrackte Dateien.
- Erwarteter Umfang: hoch. Checkpoint nach dem p1.2-Merge und nach p1.3 einplanen.

## Wartet auf den Owner (blockiert diese Aufgabe nicht)

Kontakt-Adresse für [KONTAKT-E-MAIL] in der YouTube-Kanalbeschreibung; Screenshot vom TikTok-Kontostatus, falls das alte Konto weiter genutzt wird.

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
