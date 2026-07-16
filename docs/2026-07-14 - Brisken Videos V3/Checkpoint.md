# Checkpoint: Brisken Videos V3

**Date:** 2026-07-14
**Status:** Built + QC-verified + committed; SharePoint re-upload blocked on a writable session (user opens Edge, or the app gets a Sites write grant)

---

## Summary
Rebuilt both Brisken AI films to Dirk's feedback ("overview is missing", "a better voice (male)", "more informative monologue"): male Kokoro `am_michael` narrator, a real overview beat in each film (MDH: deck slide 2's Functional Overview Diagram, BTP-cropped; Calvin: new 10s "Meet Calvin" intro card), and denser claim-gated narration. All four masters rendered and pass QC; committed in video-gen (main) and agentic-ops1 (`leadgen/task-6`, pushed); the SharePoint overwrite could not complete because no writable session was reachable.

---

## What Was Done This Session
### Video revision (video-gen repo)
1. Fetched male Kokoro voices `am_michael` / `bm_george` / `am_fenrir` (one-time gated download, authorized by the owner directive); audition wavs in the session scratchpad `voice-audition/`.
2. Measured every draft line's real `am_michael` speech duration before writing the spec (holds = speech + >=0.5s air with drift margin).
3. MDH spec v3: narrator `am_michael`, new shot1 = `composition/public/brisken/p02_overview.png` (slide 2 diagram, cropped to exclude the SAP-BTP-branded title/footer per the 2026-07-08 BTP ban), denser narration for all 10 scenes, film 62.5s -> 88.5s. Rendered 16x9 + 1x1; QC PASS all 7 stills gates (176/178 words ASR-heard, 10/10 lines in scene, -14.9 LUFS).
4. `specs/brisken-mdh.gen.narration.yaml` rewritten as the v3 copy-review artifact with measured timings.

### Calvin clip (agentic-ops1, worktree `agentic-ops1-calvin-clip` on `leadgen/task-6`)
1. New `#intro` overview card in `clip.html` (Meet Calvin / "An agent on OnePilot, running inside your SAP landscape." / "A funding request, start to finish."); the original 90s story renders unchanged at `t-10` via a `renderStory(t-INTRO)` wrapper — zero internal timestamps touched.
2. `render.py` DURATION 100.0; preview frames verified in both ratios; both silent masters re-rendered (3000 frames each, ffprobe-verified).
3. `narrate-calvin.mjs` v3: SRC repointed to the new worktree, TOTAL 100.0, `am_michael`, intro line + denser read/cash/book/conf lines, `appr` endBy 63.0 keeps ~4.4s deliberate silence before the Approve click (66.3s). Mux + QC PASS both formats (142/154 words, 10/10 lines in scene, -14.6 LUFS).
4. `video/README.txt` updated to v3 (100s, silent-master convention made explicit).

### Ship + upload attempt
1. video-gen committed to main `6f03a34` (owner order); Calvin committed `bf496f8` on `leadgen/task-6` and pushed.
2. Upload probe: app-only Graph token READS the MARKETING drive (target folder + all four filenames confirmed live) but createUploadSession -> 403 (no write grant). Delegated token expired (15h old); Edge CDP `:9222` down; permission classifier then required the tenant write to run where the user sees the prompt. Upload script is staged: `scratchpad/graph_upload_videos.py` (Graph upload-session variant) + the proven `.scratch/cdp_sp_upload_{mdh,calvin_rev}.py` (CDP-cookie SP REST, sources already point at the v3 masters).

---

## Key Decisions Made
### Overview = the client's own diagram, cropped, not a motion-graphics invention
- **Choice:** MDH shot1 uses deck slide 2's "Functional Overview Diagram", cropped to the diagram band only.
- **Rationale:** Product truth (real Brisken asset, downscale-only) AND the BTP ban: the slide's title/footer say "SAP Business Technology Platform", which Dirk banned from demo material; the crop removes exactly that and nothing else. Verified in pixels in both formats.

### Voice = am_michael, alternates staged
- **Choice:** `am_michael` @1.0 built in; `bm_george` (British) and `am_fenrir` fetched + auditioned as fallbacks.
- **Rationale:** Best-graded Kokoro male voice; measured pace 2.45 w/s drove all hold arithmetic. The Calvin brief's standing note stays live: a real Brisken voice can replace the TTS per scene without re-rendering frames.

### Calvin timeline extended by wrapper, not renumbering
- **Choice:** Intro occupies [0,10); `renderStory(Math.max(0, t-10))` plays the old timeline untouched.
- **Rationale:** ~60 hardcoded timestamps in `render()` stay verbatim -> no re-verification of the whole animation; the +10s shift is provably uniform.

### Film length allowed to grow (62.5 -> 88.5s / 90 -> 100s)
- **Choice:** Seat the overview + denser lines rather than compress copy to the old envelope.
- **Rationale:** Dirk's ask is more information; the male voice is ~10% slower; both destinations take minutes-long demos. Levers to shorten (trim overview hold / line density) noted if he pushes back.

### Graph-first honored, CDP kept as explicit fallback
- **Choice:** Tried app-only Graph write first (403), delegated token second (expired), CDP last (down) — then stopped with LIMITATION instead of asking the user to click.
- **Rationale:** rule_brisken_graph_first ordering; the write 403 also proves the rule's Sites.Selected table is right for writes but stale for reads (read now works).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| video-gen `specs/brisken-mdh.spec.yaml` | Modified (commit 6f03a34) | v3: am_michael, overview shot1, denser narration, measured holds |
| video-gen `specs/brisken-mdh.gen.narration.yaml` | Rewritten (6f03a34) | v3 copy-review artifact with measured timings |
| video-gen `composition/public/brisken/p02_overview.png` | Created (6f03a34) | Slide-2 overview diagram, BTP-free crop (2058x517) |
| video-gen `pipeline/narrate-calvin.mjs` | Modified (6f03a34) | v3 scenes (+10s), intro line, am_michael, SRC -> calvin-clip worktree |
| video-gen `docs/STATUS.md` | Modified (6f03a34) | v3 section = resume truth; supersedes brisken-narration-rollout.md |
| video-gen `out/brisken-mdh/{16x9,1x1}.mp4` | Rebuilt (gitignored) | 88.5s narrated masters, QC PASS |
| video-gen `out/brisken-calvin/{16x9,1x1}.mp4` | Rebuilt (gitignored) | 100.0s narrated masters, QC PASS |
| agentic-ops1 `output/leadgen-task-6/clip/clip.html` | Modified (bf496f8, pushed) | Intro overview card + renderStory wrapper |
| agentic-ops1 `output/leadgen-task-6/clip/render.py` | Modified (bf496f8) | DURATION 100.0, preview times |
| agentic-ops1 `output/leadgen-task-6/video/*` | Rebuilt (bf496f8) | 100s silent masters + v3 README |
| memory `project_brisken_mdh_demo_film.md` + MEMORY.md | Updated | v3 state, gates, artifact locations |

---

## Current Status
All four v3 masters exist, QC-green, pixel- and ASR-verified; both repos committed (video-gen main local-only by design; `leadgen/task-6` pushed). The owner approved copy + upload ("go ahead with all") and has the two 16:9 masters open for viewing. The SharePoint overwrite is the ONLY incomplete step: no writable path was reachable (app token read-only on MARKETING, delegated token expired, Edge CDP down), and the permission layer requires the tenant write to run with a visible prompt.

Platform note: brisken `infrastructure.yaml` platform section is the expense-recon STANDALONE decision record (no ops caps applicable to this session's work).

---

## Next Steps
1. **Upload the five files to SharePoint** once a writable session exists: user opens Edge (CDP `:9222`) -> run `.scratch/cdp_sp_upload_mdh.py` + `.scratch/cdp_sp_upload_calvin_rev.py` (sources already point at v3) + push the updated `calvin-clip-README.txt`; or grant the Graph app write on /sites/MARKETING and run `scratchpad/graph_upload_videos.py` headless.
2. **Request the Sites.Selected WRITE grant** for app `79d33e4a-...` on /sites/MARKETING (read is already live — verified this session) — kills the Edge dependency for all future uploads.
3. **Update `rule_brisken_graph_first`** table: app-only READ of the MARKETING drive now works (verified 2026-07-14); write still 403.
4. After upload: byte-verify (both scripts do), then tell Dirk the revised cuts are in his folder.
5. If Dirk still wants a different voice: audition wavs are staged; a real-voice swap needs no re-render (per-scene wav drop-in).

---

## Context for Next Session
### Files to Read First
- `~/Repo/video-gen/docs/STATUS.md` (v3 section at the end — the resume truth)
- `~/Repo/video-gen/specs/brisken-mdh.gen.narration.yaml` (the approved v3 copy + timings)
- `.scratch/cdp_sp_upload_mdh.py` + `.scratch/cdp_sp_upload_calvin_rev.py` (upload path A)

### Open Questions
- Does Dirk accept the 88.5s/100s lengths, the am_michael voice, and the copy? (He approved internally via Matthias; Dirk's own read is pending the upload.)
- Sites.Selected write grant for the Graph app: request now or keep CDP-with-Edge as the upload path?

### Working Notes
- **Graph surface (live-probed 2026-07-14):** app-only token: MARKETING site lookup 200, folder children 200 (read OK), createUploadSession 403 (no write). The rule's "Sites.Selected not granted for MARKETING" is now HALF-stale.
- **am_michael pace:** ~2.45 w/s incl. sentence pauses (af_heart ~2.7). All v3 holds derived from measured speech; TTS clips are content-hash-cached, so re-renders reuse identical takes (no drift risk until copy changes).
- **Kokoro voice weights:** am_michael/bm_george/am_fenrir now in the HF cache; narration.mjs offline pin still holds for builds.
- **MDH overview crop recipe:** slide2 image2.png `crop=2058:517:0:398` removes title row + BTP banner, keeps the full 3-column diagram. PII-clean.
- **Calvin QC word-match 142/154 (92%)**: normal ASR fuzz (S/4HANA, "four point two million"); threshold passes; every line located in its scene.
- **Failed approach:** app-only Graph upload session (403 write) — do not retry until the write grant lands.

### Reference Materials
- SharePoint destination: `MARKETING / Shared Documents / 20_Assets / BRISKEN VIDEOS / 2026_NEW AI GENERATED VIDEOS`
- video-gen commit `6f03a34`; agentic-ops1 `leadgen/task-6` commit `bf496f8` (pushed)
- Voice auditions: session scratchpad `voice-audition/{am_michael,bm_george,am_fenrir}.wav`

---

## How to Continue
Open Edge (normal CDP setup) or land the Sites write grant, then run the two upload scripts (plus the README push) and byte-verify — everything else is already committed and QC-green. If Dirk returns further feedback, edit copy in the spec / SCENES table, re-run `render-brisken.mjs` / `narrate-calvin.mjs --render` (fit gate re-measures automatically), and re-upload.

---

## Strategic Feedback

### What Worked Well This Session
- "go ahead with all" against an explicitly enumerated decision list made the approval unambiguous — the three gates (copy, upload, commit) each mapped to a named action, so autonomy resumed instantly without re-asking.

### Suggestions
- Keep Edge's CDP session (or better: grant the Graph app Sites write on MARKETING) so tenant file-writes stop depending on a browser being open; this is the third session where an upload path hinged on Edge state.

### System Health
- Autonomy score: 2 (1 B1 stop-hook closing-deferral, hook-caught + self-corrected; 1 ext-limit stop on the tenant write; 0 user corrections of the work itself). `rule_brisken_graph_first` written this morning already has a stale capability row — rules that encode third-party grant state need a "verified as of" convention or a live-probe habit before each cited use (B7 caught it this time).
