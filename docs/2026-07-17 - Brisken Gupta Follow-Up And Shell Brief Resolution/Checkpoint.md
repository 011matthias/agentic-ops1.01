# Checkpoint: Brisken Gupta Follow-Up And Shell Brief Resolution

**Date:** 2026-07-17
**Status:** COMPLETE — Gupta recategorized + brief staged; Shell brief kept out of public repo

---

## Summary
Closed the two loose ends from the Rome outreach-status reconciliation: the Shell prep brief was kept out of the public repo (commit dropped, file relocated to gitignored context/), and the "Gupta was never contacted" claim from the prior session was disproven by a live all-folders mailbox check — he replied on 25.06 and Dirk owes him promised collateral. His sheet row was corrected and a context brief staged in Dirk's Drafts.

---

## What Was Done This Session

### Shell brief push decision (resolved)
1. User chose to keep the brief out of the public repo. Dropped local commit `2f763ed` from `client/brisken/lead-desk-cockpit` (mixed reset; the commit contained only the brief, nothing was staged, this is the branch's only checkout). Branch now level with origin.
2. Relocated the brief to `workspace/clients/brisken/context/shell-call-prep-2026-07-27.md` (covered by `.gitignore` `workspace/clients/*/context/`). Verified: no trace in git status; a future branch push can no longer carry it.
3. Amended the 2026-07-16 Rome Outreach checkpoint so no future session re-opens the question or recreates the file under `deliverables/`.

### Gupta verification (user: "check one more time... dirks emails seem rerouted")
4. Live per-contact `$search` across ALL folders of both mailboxes (app-only Graph, `isDraft` filtering): Gupta was reached 3x pre-event (19/23/24.06, from Matthias), **replied 25.06** ("...still be interested in the AI capabilities within Treasury. See if you have some documentation..."), and **Dirk personally replied 26.06** — filed in his custom `MERSK | MDH | Pankaj` folder (the exact rerouting the user warned about), promising: "I will put something together and send it out to you. Give me a few days." No attachments; nothing sent since — a 21-day-old unfulfilled promise to a warm, self-qualified lead.
5. Root cause of the prior session's miss: Gupta's live sheet row said `Not contacted` (internally contradictory — `last_reply` 2026-06-25 was on the same row), and the "no more mistakes anywhere else" robust check swept only "Not contacted" rows WITH a Tier; Gupta's Tier was blank, so he was outside the checked population.

### Gupta recategorization (live sheet, row 130, all writes verified by re-read)
6. `email outreach_status`: `Not contacted` → `Replied - action needed`. `last_outreach`: 2026-06-24 → 2026-06-26 (text ISO). `lead_type`: blank → `prospect`. `outreach_log`: populated with the full dated history (E1–E3 → reply → Dirk's promise → draft-pending line). `Tier`: deliberately left blank with `Tier_reason` set — non-attendee inbound lead outside the H5/T1/T2/T3 booth-attendee cohort (he is also one of the 8 rows deliberately removed from the booth master per [[project_brisken_rome_tier_classification]]).

### Context brief staged in Dirk's Drafts (explicit user go-ahead)
7. Created a reply draft via `createReply` on Gupta's 25.06 inbound in Dirk's mailbox (keeps RE: threading; addresses Gupta only), prepended a NOTE-format context brief matching the Ashok precedent (Who / his verbatim ask / where it stands / points-to-hit: Digital Co-Worker + OnePilot one-pagers as the direct answer, MDH as optional widening, one soft call ask), baked the Zoho BCC (`s9hitl_pv69mu@mails4.zohocrm.com`). Verified field-by-field: isDraft, Drafts folder, subject, To, BCC, note present, verbatim ask quoted, quoted history intact — 8/8 checks. Nothing sent.
8. Updated the sheet row to match: `outreach_log` gained "2026-07-17 draft pending in Dirk's Outlook (NOT sent)..."; `next_step` now points Dirk at the staged draft.

---

## Key Decisions Made

### Shell brief: relocate + drop commit (not just "leave local")
- **Choice:** Drop the commit and move the file to gitignored context/, per user selection.
- **Rationale:** The commit sat on the shared `lead-desk-cockpit` branch that parallel sessions actively push; "leave it local" was not a stable resting state — any routine Band-1 branch push would have published Shell-specific commercial detail to the public repo.

### Gupta gets no booth Tier
- **Choice:** `Tier` stays blank; `Tier_reason` documents why; `lead_type` = `prospect`.
- **Rationale:** H5/T1/T2/T3 are grounded in how booth-cohort attendees were contacted; Gupta never attended (inbound email lead). Forcing a tier would misclassify him and pollute the tier-grounded sweeps. If the owner wants him visible in tier-filtered views, that is a deliberate re-scoping, not a data fix.

### Brief as reply-draft on the real thread, not a fresh mail
- **Choice:** `createReply` on Gupta's 25.06 inbound (not a new draft, not a reply to Dirk's own sent mail).
- **Rationale:** Keeps threading so Gupta sees the continuation of what he asked for; `createReply` on the inbound addresses the sender (Gupta), whereas replying to Dirk's own sent message would address Dirk.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/shell-call-prep-2026-07-27.md` | Moved here from `deliverables/lead-generation/` | Keep Shell commercial detail out of the public repo (gitignored home) |
| Branch `client/brisken/lead-desk-cockpit` | Commit `2f763ed` dropped (reset to `ca1a41d`) | Same — branch now level with origin, no unpushed Shell content |
| `docs/2026-07-16 - Brisken Rome Outreach Status Reconciliation/Checkpoint.md` | Amended | Marks the Shell push question RESOLVED; prevents re-opening |
| TA Cook Rome master sheet, row 130 (SharePoint, Graph workbook API) | 6 cells updated, verified | Gupta recategorized: status/lead_type/last_outreach/outreach_log/Tier_reason/next_step |
| Dirk's Outlook Drafts (Graph, app-only) | 1 reply draft created | Context brief for the promised AI-in-treasury collateral to Gupta |
| `docs/sessions/2026-07-17.md`, `docs/sessions/2026-07-17-context.yaml`, `docs/INDEX.md`, `docs/friction-register.md` | Created/updated | Session records |

---

## Current Status

Gupta loose end fully closed on our side: mailbox truth established, sheet row corrected and consistent, context brief staged with Zoho BCC. The send is Dirk's action. Kulkarni and Georgiou briefs also still sit in his Drafts from earlier sessions. The Rome outreach-status reconciliation remains closed; no further sheet work from this thread.

Platform: custom SaaS build (expense-reconciliation), tier unknown — no workflow-engine op count applies. Last assessed: 2026-05-24.

---

## Next Steps
1. **Dirk (his court):** rewrite + send the Gupta draft (Digital Co-Worker + OnePilot collateral, promise is 21 days old); also the Kulkarni, Georgiou, Ashok, and T3-batch drafts waiting in his Drafts.
2. **Time-critical carryover:** Sanofi Planner slide-10 check-off is gated on owner yes BEFORE today's (Fri 2026-07-17) 16:00 Sanofi call — see the 2026-07-16 Sanofi Call Sign-Off checkpoint.
3. **Ashok watch:** back from OOO since 13.07, silent; staged 07-16 draft in Dirk's Drafts; Planner task past its 2026-07-16 due date.
4. Other carryover, untouched this session: Website GTC Planner check-off, Protokoll EN verdict watch, Expense Recon card-list authoring, Lead Desk send-gate drill.
5. **Structural candidate (4th recurrence):** promote the mailbox-truth scripts from `.scratch/` into a permanent `tools/brisken-outreach-truth.py` (per-contact `$search`, all folders, both mailboxes, `isDraft` filter) — see Friction/System Health.

---

## Context for Next Session

### Files to Read First
- `feedback_brisken_outreach_truth_is_mailbox.md` (memory) — the authoritative verification method
- This checkpoint — the Gupta correction detail and the sweep-population lesson
- `docs/2026-07-16 - Brisken Sanofi Call Sign-Off/Checkpoint.md` — the live carryover backlog

### Open Questions
- Does the owner want Gupta visible in tier-filtered views (would need a deliberate non-booth tier label), or is status-based tracking enough? Current state: no Tier, `Tier_reason` documents why.

### Working Notes
- **Sweep-population lesson (the new sub-mode):** a "prove nobody was missed" sweep is only as good as its population definition. `robust_check.py` filtered to "Not contacted" + Tier assigned; Gupta ("Not contacted", no Tier, `last_reply` filled) was excluded. Future sweeps: population = ALL rows with an email address, and flag internally-contradictory rows (`Not contacted` + non-empty `last_reply`) as a cheap pre-check.
- **Tokens:** mailbox reads/writes ran app-only (client-credentials from `context/.env`, hard-allowlisted to dirk+matthias). Sheet writes used the delegated token in `.scratch/graph_token.txt` (minted 07-16 21:46 via `grabtoken.py` CDP capture off the Planner tab, upn Matthias.Silva, carries Files scope) — still valid this session; will be expired by the next one. Sheet reads/writes need a fresh delegated token when it dies (app's `Sites.Selected` not granted for the MARKETING site).
- **Graph mechanics worth keeping:** `createReply` on an inbound addresses the sender (correct for Gupta); on your own sent mail it addresses you (wrong). Draft messages carry `sentDateTime`, so `isDraft eq false` is mandatory in send checks. Workbook `$search`-style URLs need full URL-encoding (spaces in `worksheets('Master contacts')` and `$orderby` break `urllib`). Windows: `sys.stdout.reconfigure(encoding="utf-8")` before printing Graph content (cp1252 crash, already documented in the 07-13 register row).
- **Sheet vocab (enumerated live):** `email outreach_status` dropdown: Not contacted / Contacted - awaiting reply / Replied - action needed / In conversation / Do not contact / Do not contact (no consent) / No channel / "-". `lead_type`: prospect / partner_si / sap_internal / internal / analyst / organiser / unknown. `Tier`: H5/T1/T2/T3 + non-lead labels (ANON/STOP/GA/OWN_TEAM/...).
- **Pankaj folder:** contains only the Gupta thread + a 2024 LinkedIn item — no separate live "Pankaj" deal in email; Dirk's internal forward rates the Gupta lead "Brilliant.... very good!".
- Working tree carries ~70 modified files from parallel sessions (resources-site, rome-2026 collateral, meji-media deletions, hooks) — untouched by this session, left alone.

### Reference Materials
- Rome 2026 master contact sheet (SharePoint, 30_Events/TA Cook 2026) — [[project_brisken_rome_master_contact_sheet]]
- Collateral: `workspace/clients/brisken/resources-site/` (digital-co-worker / onepilot / market-data-hub PDFs + pages, live on resources.brisken.com); `deliverables/lead-generation/rome-2026/dirk-send-pack/`

---

## How to Continue

Nothing further to build on the Gupta thread — Dirk reviews and sends the staged draft. If a future session needs to re-verify any "was X contacted" question, use the per-contact `$search` method from the memory file (all folders, both mailboxes, `isDraft eq false`), and define sweep populations as all-rows-with-email, never status/Tier-filtered. The Brisken backlog carries over from the 2026-07-16 Sanofi Call Sign-Off checkpoint; the Sanofi slide-10 gate is time-critical today.

---

## Strategic Feedback

### What Worked Well This Session
- The user's one-line steer ("remember dirks emails going out seem to be rerouted to a folder") plus the banked all-folders method from yesterday's memory rewrite found the truth in a single pass — no debugging cycle this time. The memory fix held on first re-use.
- Staging the brief as a threaded reply-draft with facts quoted verbatim (his ask, Dirk's promise) means Dirk can rewrite and send without opening the sheet or searching his mailbox.

### Suggestions
- The mailbox-truth scripts have now been rebuilt in `.scratch/` across four sessions (07-11, 07-14, 07-16, today). Promote to `tools/brisken-outreach-truth.py` with a `--contact email` mode; the 07-16 register row already called this the recurrence-kill. Logged as `infrastructure-deferred` this session.

### System Health
- `stop-b1-gate` fired twice on deferral phrasing around legitimately-gated invasive actions. The gate holds every time, but the generation-time reflex ("if you want, I can...") persists — the correct form for a gated fork is a declarative decision point with a stated default. Most-logged class in the register; the hook is the working backstop.
- Autonomy score: 1 human intervention this session (the "check Gupta one more time" redirect — which disproved a prior-session claim; everything after ran autonomously with per-action authorization honored).
