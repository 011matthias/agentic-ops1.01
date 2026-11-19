# Mini-Checkpoint: GTA6 Clip Engine P1.2 Fetch

**Date:** 2026-11-19
**Status:** p1.2 (Twitch) merged; p1.3 to p1.6 for the first F1 video next
**Type:** mini

---

## Summary
Built and merged `clipengine fetch` (PR #1767): only the most-viewed stretches of finished Twitch VODs are downloaded, and 21 real sections now sit in `engine/data/`. Two live findings changed the design: `vod_offset` is a clip's end, and the laptop's IPv6 path resets ~40 % of requests.

## What Was Done
- `watch --days 1` on launch day: ~17,800 clips, 10 streamers; 5 VODs finished (lirik, ohnepixel, theburntpeanut, jasontheween, xqc), kaicenat / lacy / stableronaldo / caseoh_ / ishowspeed live.
- PR #1767: `intervals.py` (clip span, merge, muted exclusion, 120 s window around the top clip), `fetch.py` (live-skip, `sections` table = migration 2, yt-dlp sections + clip fallback, ffprobe length check, 50 GB guard), `clipengine fetch [--dry-run]`, 9 tests (47 total); regress_check: offset rule, retry loop, live-skip each bite.
- Live run `fetch --top 3`: 21 sections (15 VOD sections, 6 clips), lengths match the request by ffprobe; re-run downloads only what is missing.
- Removed merged worktrees `../agentic-ops1-gta6-p11` and `../agentic-ops1-gta6-streamers`.
- Drafts for the next PR sit untracked in `../agentic-ops1-gta6-p12`: `src/clipengine/analyze.py` (faster-whisper, F1 cut at sentence ends, review packages) and `src/clipengine/render.py` (ASS captions, facecam/gameplay stack, two-pass loudnorm, NVENC).

## What Did NOT Work (and why)
- **Taking `vod_offset` as the clip start (Twitch docs):** audio cross-correlation of 5 clips in their VODs put each clip at `vod_offset - duration` (within ~1 s); a section cut at `vod_offset` missed the clip.
- **yt-dlp / Hugging Face over IPv6:** WinError 10054 on ~40 % of first requests (2/5, 3/7, 4 fetch failures, the Whisper model download); `--force-ipv4` 0/15.
- **Retry backoff 3 s / 6 s:** two sections still failed all 3 attempts on IPv6; backoff now 5 / 10 s, the real fix was IPv4.
- **Audio-matching a clip by its first 10 s:** the jasontheween "Reset" clip opens at -51 dB, correlation 0.004; probing from 10 s or 50 s found it at 30.8 s (expected 30.0).
- **`regress_check.py --test "... -k 'a or b'"`:** the tool splits without shell quoting; pass test node ids instead.
- **Chaining `gh pr merge` after other commands:** blocked by the pattern gate; run the merge as its own call.

## Current Status
p1.2 Twitch half done and merged (spec criterion: Twitch half met, YouTube curve open). Sections on disk under the primary checkout's `engine/data/{streamer}/...`. Whisper large-v3 not yet in the HF cache (first download died on the IPv6 reset). No ops status: internal project without an orchestrator.

## Next Steps
1. p1.3: faster-whisper with CUDA DLLs on Windows (nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels), migration 3 (`transcripts`, `moments`), `clipengine analyze` + `judge`, review packages, measure VRAM and runtime; judge the packages (ohnePixel #1 at 472k views is a strip-club scene: reject or defuse).
2. p1.4 to p1.6: EDL JSON, facecam calibration (`config/layouts.yaml`), render, checks, one F1 video into `engine/data/ready/`, shown to the owner, not posted.
3. 22.11.: `suggest --since 72h`.

## Files to Read First
- `workspace/projects/gta6-clipping/engine/README.md`
- `workspace/projects/gta6-clipping/specs/2-build/p1-clip-engine.md` (stages 3 to 6)
- `workspace/projects/gta6-clipping/engine/src/clipengine/fetch.py`

## Continuation prompt

````markdown
/comd_resume gta6-clipping

GTA6-Clipping: erstes fertiges Video bauen, ab p1.3 (internes Projekt workspace/projects/gta6-clipping/).

## Stand (19.11.2026)

- p1.2 gemergt (PR #1767): `clipengine fetch` lädt nur die meistgesehenen Stellen fertiger Twitch-VODs (Intervalle aus Zuschauer-Clips, stumme Stellen und laufende Aufzeichnungen ausgeschlossen, max. 120 s um den Top-Clip, 5 s Puffer), für Streamer ohne VOD den Top-Clip pro Moment. Tabelle `sections` (Migration 2).
- Live gemessen: `vod_offset` ist das ENDE des Clips (Ton-Abgleich von 5 Clips). IPv6 bricht ~40 % der Anfragen ab, yt-dlp läuft mit --force-ipv4; gilt auch für Hugging Face (Whisper-Modell noch nicht geladen).
- 21 Abschnitte liegen unter engine/data/ des Haupt-Checkouts (lirik, ohnepixel, theburntpeanut, jasontheween, xqc je 3, caseoh_ und ishowspeed je 3 Clips). `uv run clipengine fetch --dry-run` zeigt sie.
- Entwürfe für p1.3/p1.5 liegen ungetrackt im Worktree ../agentic-ops1-gta6-p12: src/clipengine/analyze.py, src/clipengine/render.py.

## Aufgabe

p1.3 bis p1.6 wie im vorigen Prompt: Transkript (faster-whisper large-v3 int8 auf der GPU, CUDA-DLLs unter Windows), Prüfpakete, eigenes Urteil (Spoiler, Ab-18-Risiko: ohnePixels Top-Moment ist eine Strip-Club-Szene, Kategorie, Hooks, Titel), EDL, Facecam-Profil, Render 1080×1920, Checks, ein F1-Video nach engine/data/ready/, dem Owner zeigen (Start-Process + SendUserFile), nicht posten.

## Wie arbeiten

Wie im vorigen Prompt (eigener Worktree, ein PR pro Phase, `gh pr merge` als eigener Aufruf, Tests offline, regress_check mit Test-IDs statt -k, Daten nur unter engine/data/, Repo öffentlich).

## SESSION LOOP

(Unverändert aus dem vorigen Prompt übernehmen.)
````
