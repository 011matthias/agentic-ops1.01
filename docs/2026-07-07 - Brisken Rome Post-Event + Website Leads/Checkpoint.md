# Checkpoint: Brisken Rome Post-Event + Website Leads

**Date:** 2026-07-07
**Status:** Tier-1 drafts live in Dirk's Outlook; website-lead pipelines mapped; five workstreams queued

---

## Summary
Rebuilt the rejected Rome Tier-1 send pack from Dirk's own recorded words (v2 + register pass + owner directives), loaded seven ready-to-send drafts into his Outlook, and unraveled the website-lead story end to end: the old Wix pipeline produced two real unanswered leads (CrowdStrike, mbi GmbH; now spreadsheet-tracked + reply drafts staged), and the live brisken.com form logs into a Neon Postgres on the owner's own Vercel project.

---

## What Was Done This Session

### Rome send pack (p2)
1. Diagnosed the v1 rejection from artifacts (no verbatim feedback existed): Adidas mis-addressed, VW led with the wrong product, JTI broke Dirk's booth promise, old deck naming, sequence scaffolding.
2. Rebuilt v2 anchored on the raw booth transcripts; owner corrections applied same day: professional-not-personal register (all five notes swept), VW split (Michael solo no cc; Steinar separate generic German note), EPROX not APROX (web-confirmed eprox.de DEALMANAGER for 360T; converted en masse), JTI = Dirk's personal send, Adidas = Carol Tse (confirmed after LinkedIn review of all attendees).
3. Loaded 6 pack drafts + the Tejas reply into Dirk's Outlook via COM (SendUsingAccount routing; sync verified; umlauts intact). Pack PDF re-rendered and content-verified each revision.

### Website leads
4. Dirk's "spam?? phishing??" forward identified as a REAL inbound: Tejas Lokhande, Treasury Analyst II, CrowdStrike Pune (LinkedIn/TheOrg/ZoomInfo corroborated; VP Tax & Treasury above him = Dave Gaul; ERP signal = NetSuite, so the reply asks rather than assumes SAP).
5. Full Wix triage: 13 notifications -> 9 deduped submissions, 2 real leads (CrowdStrike 19d, mbi GmbH 10w), 0 replies ever sent. `tools/brisken-website-inquiries.py` now regenerates `context/lead-generation/website-inquiries.xlsx` on demand (re-checked end of session: no new entries).
6. brisken.com resolved: NOT Wix; owner's own Vercel project `brisken-onepilot` (matthias-neumanns-projects; token in context/.env, expires ~07-22). The live form's `/api/book-demo` works (anti-bot) and logs to the project's Neon Postgres `leads` table (migration in deployment source; owner confirmed). DB credential pull cancelled by owner; entries browsable in his Vercel dashboard.

### Builds + tooling
7. onepilot-site app: public `/inquiry` form + `/api/book-demo` endpoint (fixing the platform page's dead modal) + gated `/inquiry-log` + `/inquiries.xlsx`; 12+ behavior checks passed; Fly deploys PARKED (owner: target is brisken.com).
8. `tools/md-to-pdf.py` patched: Edge silent-fail now detected (temp-file write + verify) with automatic Chrome fallback; verified live.
9. Registered workstreams from owner + Dirk inbounds: SAP PartnerFinder re-spine, 1Proposal synopsis, gated proposal slot, Discovery Center rework, Tiers 2-4 outreach.

---

## Key Decisions Made

### Rejection rework anchored on Dirk's own words, not assumptions
- **Choice:** With no verbatim feedback available, diagnose from raw transcripts + DN-Edits master and fix only evidence-backed errors.
- **Rationale:** The found errors (wrong recipient, broken promise, wrong lead product) hold under any feedback; owner directive "look over it and find out".

### Client-voice register: professional, not personal
- **Choice:** Strip intimacy-performance lines ("me keeping that promise" class) from all ghost-written emails; saved as `feedback_client_voice_emails_not_personal`.
- **Rationale:** Owner correction; performed closeness repels recipients.

### Drafts-only Outlook automation
- **Choice:** COM loads drafts into Dirk's account, never sends; duplicate-subject guard + readback verification every time.
- **Rationale:** Explicit owner instruction; no-invasive-action rule stays intact.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| deliverables/lead-generation/rome-2026/dirk-send-pack/README.md + .pdf | Rewritten x3 | v2 pack, register pass, owner directives; PDF re-rendered + verified |
| context/lead-generation/Rome-Event/booth-meeting-notes.md | Modified | EPROX confirmation; Adidas = Carol Tse resolution |
| context/lead-generation/Rome-Event/post-event-sequences.md | Modified | v1-rejected status, VW split, Adidas confirmed |
| context/comms-log.md | Modified | Full 2026-07-07 trail: rejection diagnosis, Dirk inbounds x3, Wix lead triage, brisken.com resolution |
| context/lead-generation/website-inquiries.xlsx | Created | Checkable spreadsheet of all Wix form submissions |
| context/.env | Modified | + VERCEL_BRISKEN_TOKEN (gitignored) |
| workspace/clients/brisken/onepilot-site/app.py, README.md, requirements.txt | Modified | /inquiry + /api/book-demo + /inquiry-log + /inquiries.xlsx (undeployed) |
| tools/brisken-website-inquiries.py | Created | Wix-notification -> xlsx sweep tool (+ INDEX.md row) |
| tools/md-to-pdf.py | Modified | Silent-fail detection + Chrome fallback |
| memory: feedback_client_voice_emails_not_personal, reference_dirk_outlook_com_drafts | Created | Register rule; Outlook COM pattern |
| Dirk's Outlook Drafts (live) | Created | 7 drafts: VW Michael, VW Steinar (DE), JTI, Roche, Adidas Carol, LSEG, Tejas reply |

---

## Current Status
Seven drafts sit ready in Dirk's Outlook; his inputs: JTI volume info (+ Domenic email), read Tejas's PDF via the Wix dashboard. Tier-1 otherwise send-ready. Website leads: both pipelines mapped and checkable (Wix history = xlsx; live = Neon table in owner's Vercel dashboard). onepilot-site inquiry build is verified but undeployed (Fly parked). Working tree on `client/brisken/lead-gen-onepilot` carries uncommitted changes (deliberate; owner batches commits).

## Next Steps
1. SAP PartnerFinder profile (0001663611): paste-ready copy on the repositioning spine (pairs with Discovery Center work).
2. 1Proposal synopsis for Dirk (confirm = OneProposal reading first).
3. Gated proposal slot for Dirk's finished proposal (needs his file + which-site decision).
4. SAP Discovery Center rework: mission 3904 re-spine + listing gaps (2026-06-17 audit anchor).
5. Tiers 2-4 outreach after Tier-1 approval (DN-Edits reconcile first; register memory binds).
6. mbi GmbH reply draft when Dirk decides.

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/context/comms-log.md (2026-07-07 entries: the full trail)
- workspace/clients/brisken/deliverables/lead-generation/rome-2026/dirk-send-pack/README.md
- workspace/clients/brisken/context/lead-generation/Rome-Event/post-event-sequences.md

### Open Questions
- Does "1Proposal" = OneProposal (UnpauseAI product)? Owner to confirm before the synopsis goes out.
- Which site carries the gated interim proposal slot (brisken.com Vercel vs OnePilot Fly)?
- Wix form retirement: two live form pipelines exist in parallel; whose call and when?

### Working Notes
- Zoho CRM token lacks Leads-module scope (OAUTH_SCOPE_MISMATCH); recent Zoho contacts are email auto-capture, not form capture. New Self-Client grant needed for Leads read/write.
- Auto-mode classifier blocks external-system writes (live TEST POST) and credential pulls (vercel env pull) even after verbal greenlights; those need explicit per-command approval or non-auto mode.
- Vercel API with the stored token CAN read: project config, env var NAMES, deployment file TREE. It cannot decrypt sensitive env values; file-content endpoint 404s on this deployment.
- md-to-pdf Edge silent-fail: reproduced twice before the patch; Chrome fallback now automatic.

### Reference Materials
- Vercel project: https://vercel.com/matthias-neumanns-projects/brisken-onepilot
- Wix submissions dashboard: link inside any notification email (manage.wix.app/forms/submissions/561edf08-.../9cf4f4c7-...)
- Build spec for the live form: Desktop/Downloads/book-demo-form-prompt.md

---

## How to Continue
`/resume brisken`, read the comms-log 2026-07-07 entries, then pick up the Next Steps list (PartnerFinder + Discovery Center pair well as one SAP-surfaces pass). A fresh-chat continuation prompt was handed to the owner at checkpoint time.

---

## Strategic Feedback

### What Worked Well This Session
- "Look over it and find out" unlocked the strongest work of the session: diagnosing the rejection from Dirk's own recorded words beat waiting for feedback, and every fix survived owner review.
- Handing over the Vercel URL + scoped token mid-flow converted a hard blocker into a resolved question in minutes.

### Suggestions
- The two real website leads sat unanswered for 19 days and 10 weeks because notifications landed in an unwatched inbox. A weekly 10-minute "inbound sweep" ritual (or a scheduled run of the new sweep tool) would keep the Neon table and the Wix xlsx from going stale the same way.

### System Health
- Autonomy score: 3 human interventions this session (register correction, deploy-target redirect, credential-pull cancellation).
- The auto-mode classifier and the no-invasive-action rule overlapped correctly this session, but verbal greenlights don't reach the classifier; a settings allowlist for named, user-approved one-shot commands would remove that friction class.
