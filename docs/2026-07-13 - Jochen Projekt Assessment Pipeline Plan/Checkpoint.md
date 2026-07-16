# Checkpoint: Jochen Projekt Assessment Pipeline Plan

**Date:** 2026-07-13
**Status:** Plan approved; Phase 0 (housekeeping) complete; Phase 1 (vertical slice) not started — deliberately deferred to a fresh session

---

## Summary

Discovered, scoped, and got approval for a new client project: automate Jochen Stiebe's (ConVista/Target Network) SAP Treasury Assessment pipeline — ingest questionnaire + client docs + workshop audio, map into his Treasury Component Framework (TCF) matrix, analyze, and render his Ergebnispräsentation deck. Ingested the full ConVista corpus (4 worked client examples + 89 min of methodology audio, transcribed locally), derived the data model (the TCF matrix is the pivot artifact), wrote and got approval on a phased build plan, and completed Phase 0 housekeeping.

---

## What Was Done This Session

### Discovery + verification (OneProposal thread, start of session)
1. Re-verified OneProposal live state (engine /health 200 all upstreams, app live, /pricing still 404, paid proposal page live); wrote positives/negatives ledger on request
2. Verified the akkton-access assumption FALSE: gh + GitHub MCP authed as 011matthias; both akkton repos 404; akkton is a User account, no org membership — collaborator invite or engine secret needed for any OneProposal-engine work
3. Prepared Jochen demo strategy (later superseded when true scope emerged: pipeline replication, not OneProposal itself)

### Corpus ingestion (Jochen Projekt)
1. Extracted text from all Office files (decks, questionnaires, agenda) — UTF-8 re-run after cp1252 mojibake/charmap crash
2. Transcribed `Jochen 1.m4a` (60 min, German, faster-whisper small/int8/CPU, ~2.2x realtime) — full read; build-relevant content at 04:00–21:00 + 58:35–60:12
3. Identified the data model from the Alfred Ritter files: TCF matrix sheets "Gaps by OM dimension" / "Gaps by function", columns As-Is | Reife | Prio | Gap | Risiko | Growth | Dig./Auto. | Theme of action; the 134-slide deck renders FROM the matrix
4. Background re-transcription of `Jochen Präsentation.m4a` + `New Recording 2.m4a` launched (writes transcripts INTO `Methodology briefings/`; detached, survives session end)

### Planning
1. Explore-agent inventory of reusable repo assets (expense-recon LLM pattern, deckgen, templates, platform precedents)
2. Wrote plan; user locked both forks: vertical slice first; greenfield on the expense-recon pattern (no OneProposal-engine dependency). Plan approved via plan mode.

### Phase 0 housekeeping (done)
1. Sorted corpus into `CITTI/ STAEDTLER/ Nagarro SE/ Alfred Ritter/ Methodology briefings/ Reference/` — no loose files
2. `.gitignore` protection added, then FIXED after the user's folder rename (OneProposal → Jochen Projekt) silently broke it; verified with `git check-ignore` both times
3. Copied `Jochen 1.transcript.txt` from ephemeral scratchpad into `Methodology briefings/` (durable)
4. Wrote the fresh-session continuation prompt (delivered in chat)

---

## Key Decisions Made

### Scope = replicate + automate Jochen's assessment pipeline (not sell OneProposal)
- **Choice:** Product = information overload in → TCF-structured deliverable out, abiding by Jochen's given structure
- **Rationale:** User + Dirk + Jochen all confirmed; Jochen's briefing names the mapping ("read a document, assign it into the matrix") as the heavy lift; the business model is cheap mass assessments → implementation projects

### First increment = vertical slice (user-locked)
- **Choice:** One client end-to-end: questionnaire → LLM-filled TCF matrix (confidence + source snippets) → one draft deck section
- **Rationale:** Fastest proof on real data; doubles as the Jochen demo; Alfred Ritter preferred (cleanest golden TCF list)

### Foundation = greenfield Python reusing expense-recon LLM pattern (user-locked)
- **Choice:** Model on `expense-reconciliation/src/expense_recon/llm/client.py` (strict json_schema, confidence<0.6→REVIEW, cost tracking)
- **Rationale:** OneProposal engine is inaccessible (404 for our identity) and built for a different deliverable; the in-repo pattern maps ~1:1

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `C:\Users\neuma_p1qrsic\.claude\plans\task-notification-task-id-b9nkyzmeu-tas-virtual-bird.md` | Created | The approved build plan (source of truth for Phase 1) |
| `.gitignore` | Modified (2x) | Protect confidential ConVista corpus; line 147 now `workspace/clients/Jochen Projekt/` |
| `workspace/clients/Jochen Projekt/**` | Reorganized | Corpus sorted into 6 subfolders (gitignored, untracked) |
| `workspace/clients/Jochen Projekt/Methodology briefings/Jochen 1.transcript.txt` | Created | Durable transcript of the 60-min methodology briefing |
| `workspace/clients/Jochen Projekt/Methodology briefings/Jochen Präsentation.transcript.txt` | Being written | Background job in progress at checkpoint time |

---

## Current Status

Plan approved and durable. Corpus organized, protected, and largely transcribed (background job finishing the last two recordings directly into the client folder). No code written yet — Phase 1 deliberately deferred to a fresh session because this one ran very long (context pressure critical). No infrastructure.yaml yet for this client (comes with the Phase-1 scaffold from `workspace/templates/client-automation`).

---

## Next Steps

1. **Fresh session: build Phase 1 vertical slice** — paste the continuation prompt (in chat) or read the plan file; scaffold `workspace/clients/Jochen Projekt/automations/`, port the LLM client pattern, ingest the Alfred Ritter questionnaire, fill the TCF matrix, render one deck section
2. Verify the two background transcripts completed (`Methodology briefings/*.transcript.txt`); re-run transcription if truncated (recipe in the continuation prompt)
3. Write the Phase-1 spec under `workspace/clients/Jochen Projekt/specs/1-spec/` at build start (spec-drives-implementation)

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\.claude\plans\task-notification-task-id-b9nkyzmeu-tas-virtual-bird.md` (the approved plan — read FIRST)
- `workspace/clients/Jochen Projekt/Alfred Ritter/ConVista_Treasury_Assessment_List_Alfred Ritter_JS_Abstimmversion 3.xlsx` (the golden TCF matrix)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/llm/client.py` (the pattern to port)
- `workspace/clients/Jochen Projekt/Methodology briefings/Jochen 1.transcript.txt` (Jochen's own words on the pipeline)

### Open Questions
- What "New Recording 2.m4a" contains (transcript landing via background job)
- Commercials/timeline with Jochen — nothing agreed yet; he charges DE/AT clients €15k per assessment, does US ones free as loss-leaders (briefing 14:00–18:00)
- Whether the OneProposal-engine collaborator invite (011matthias) is still worth doing — not needed for this build

### Working Notes
- **The TCF matrix IS the architecture pivot:** inputs → fill matrix → render deck. Deck sections map to matrix columns (heat-map ← Reife; initiatives ← Prio/Gap; appendix ← per-function detail).
- **Corpus is 4 complete worked examples** (CITTI, STAEDTLER, Nagarro, Alfred Ritter): filled questionnaire + TCF list + result deck each → few-shot grounding + eval fixtures. Alfred Ritter cleanest.
- **Jochen's business model** (why automation matters): 95/120 Nagarro public-cloud customers don't know features they already own; cheap assessments at scale → implementation projects; automating kills the RFP-leakage failure mode; generalizes beyond treasury to any SAP module.
- **Failed approaches this session:** cp1252 stdout redirect for Office extraction (use `sys.stdout.reconfigure(encoding="utf-8")`); moving files while a background transcription job references their paths (FileNotFoundError — files at final homes BEFORE starting long jobs).
- **Transcription recipe that works locally:** uv script, deps `["faster-whisper"]`, `WhisperModel("small", device="cpu", compute_type="int8")`, `vad_filter=True`, German auto-detected at 1.00 prob, ~2.2x realtime on CPU.
- The corpus folder is **gitignored** → ripgrep needs `--no-ignore`.

### Reference Materials
- `workspace/clients/Jochen Projekt/Reference/oneproposal-handoff-2026-07-10.txt` (architecture discipline: repair-then-validate, contracts, cost ceilings)
- Live OneProposal (pattern proof): `https://oneproposal.app`, engine `https://web-production-b5679.up.railway.app/health`

---

## How to Continue

Open a fresh session and paste the continuation prompt from the end of this session's chat (or: read the plan file above, then start Phase 1 per its "Phased scope"). Everything needed is durable: plan file, sorted corpus, transcripts, gitignore protection.

---

## Strategic Feedback

### What Worked Well This Session
- The user's mid-session context drops (handoff doc → audio + corpus files → "he wants the pipeline replicated") let the scope converge fast; each drop was ingested fully before re-planning, so no build effort was wasted on the earlier demo-prep framing.

### Suggestions
- When adding files to `workspace/clients/Jochen Projekt/`, drop them into the right client subfolder directly — loose root files get classified by content inspection, which costs a pass. And if the folder gets renamed again, ping me: gitignore entries don't follow renames (that's what silently exposed the corpus today).

### System Health
- Autonomy score: 2 human interventions this session.
- Local audio transcription (faster-whisper via uv) worked first try at 2.2x realtime on CPU and is now a proven capability for the workshop-capture stage of this very product — worth promoting to a `tools/transcribe.py` utility when Phase 3 needs it, rather than re-writing the scratch script per session.
